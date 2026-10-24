"""Subtitle translation module.

Multi-tier fallback translate subtitle cues (orkestrasi di main._translate_with_fallback):
  Tier 1: AI Fansub LLM (OpenAI-compatible: Ollama Cloud free / Gemini / Groq / OpenRouter /
          Ollama lokal). Format ber-ID `N|teks`, batch paralel, rotasi model saat limit,
          baris yang gagal diisi Google GTX (hybrid) — tidak lagi all-or-nothing.
  Tier 2: Google GTX Web RPC (zero-key, terjemahan literal/kaku)
  Tier 3: MyMemory REST API publik (gratis, 5000 char/day per IP, soft limit 4500)
  Tier 4: source English original (no translation)

Signature utama:
    translated_cues, stats = await call_openai_translate(cues, src, tgt, apikey, model, apiurl)
"""
import re as _re
import html as _html
import json as _json
import time as _time
import asyncio as _asyncio
import collections as _collections
import datetime as _dt
import httpx as _httpx

TRANSLATE_LOGS = _collections.deque(maxlen=100)


def log_translate(msg: str):
    """Catat pesan log translasi ke ring-buffer in-memory dan stdout (flush)."""
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {msg}"
    TRANSLATE_LOGS.append(entry)
    print(f"[TRANSLATE] {entry}", flush=True)


def get_translate_logs():
    """Ambil list log translasi terbaru."""
    return list(TRANSLATE_LOGS)



_ASS_TAG_RE = _re.compile(r"\{[^}]*\}")
_ASS_DIALOGUE_RE = _re.compile(
    r"^\s*Dialogue:\s*[^,]*,\s*([0-9]+:[0-5]?\d:[0-5]?\d[.,]\d+)\s*,\s*([0-9]+:[0-5]?\d:[0-5]?\d[.,]\d+)\s*,"
    r"[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,(.*)$",
    _re.I,
)


def clean_ass_tags(text: str) -> str:
    """Bersihkan tag override ASS/SSA ({\\an8}, {\\pos(x,y)}, {\\fad(...)}) dan konversi \\N / \\n / \\h."""
    if not text:
        return ""
    t = _ASS_TAG_RE.sub("", text)
    t = t.replace("\\N", "\n").replace("\\n", "\n").replace("\\h", " ")
    return t


def parse_vtt(text):
    """Parse WEBVTT, SRT, atau ASS/SSA text ke list[{start:float, end:float, text:str}].
    Mendukung pembersihan tag HTML (<...>) maupun ASS override ({\\an8}, \\N)
    serta penggabungan cue simultan (overlapping dialogue + sign)."""
    out = []
    raw_text = (text or "").lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    lines = raw_text.split("\n")

    # Deteksi format ASS / SSA ([Events] / Dialogue:)
    if any(ln.strip().lower().startswith("dialogue:") for ln in lines[:250]):
        for ln in lines:
            m = _ASS_DIALOGUE_RE.match(ln)
            if not m:
                continue
            s_ts = _vtt_ts(m.group(1).strip())
            e_ts = _vtt_ts(m.group(2).strip())
            if s_ts < 0 or e_ts <= s_ts:
                continue
            cleaned_ass = clean_ass_tags(m.group(3))
            text_lines = [
                _html.unescape(_re.sub(r"<[^>]*>", "", sub_ln)).strip()
                for sub_ln in cleaned_ass.split("\n")
            ]
            text_lines = [x for x in text_lines if x]
            if text_lines:
                out.append({"start": s_ts, "end": e_ts, "text": "\n".join(text_lines)})
        return merge_overlapping_cues(out)

    i = 0
    if lines and lines[0].startswith("WEBVTT"):
        i = 1
    start = -1.0
    end = -1.0
    buf = []
    flush = None

    def _flush():
        nonlocal start, end, buf, out
        if start >= 0 and end > start and buf:
            # Plain text: buang tag ASS ({\an8}, \N) dan VTT/HTML (<i>, <c.x>, <00:01.000>) lalu decode entity.
            text_lines = []
            for ln in buf:
                cleaned_ln = clean_ass_tags(ln)
                for part in cleaned_ln.split("\n"):
                    plain = _html.unescape(_re.sub(r"<[^>]*>", "", part)).strip()
                    if plain:
                        text_lines.append(plain)
            if text_lines:
                out.append({"start": start, "end": end, "text": "\n".join(text_lines)})
        start = -1.0
        end = -1.0
        buf = []

    flush = _flush
    while i < len(lines):
        ln = lines[i].strip()
        if not ln:
            _flush()
            i += 1
            continue
        if "-->" in ln:
            _flush()
            p = ln.split("-->")
            start = _vtt_ts(p[0].strip())
            end = _vtt_ts((p[1] or "").strip().split(" ")[0])
            i += 1
            continue
        if _re.match(r"^(NOTE|STYLE|REGION)", ln):
            i += 1
            continue
        if start >= 0:
            # Abaikan nomor urut SRT jika berdiri sendiri sebelum timestamp berikutnya
            if ln.isdigit() and (i + 1 < len(lines)) and "-->" in lines[i + 1]:
                _flush()
                i += 1
                continue
            buf.append(ln)
        i += 1
    _flush()
    return merge_overlapping_cues(out)


def merge_overlapping_cues(cues):
    """Gabungkan cue yang memiliki rentang timestamp identik/hampir identik (selisih <= 0.05s)
    dan deduplikasi baris teks yang sama agar dialog & sign simultan tidak saling menimpa."""
    if not cues or len(cues) <= 1:
        return cues
    sorted_cues = sorted(cues, key=lambda c: (c["start"], c["end"]))
    merged = []
    for c in sorted_cues:
        if merged and abs(c["start"] - merged[-1]["start"]) <= 0.05 and abs(c["end"] - merged[-1]["end"]) <= 0.05:
            prev_lines = merged[-1]["text"].split("\n")
            for ln in c["text"].split("\n"):
                if ln and ln not in prev_lines:
                    prev_lines.append(ln)
            merged[-1]["text"] = "\n".join(prev_lines[:4])
        else:
            merged.append({"start": c["start"], "end": c["end"], "text": c["text"]})
    return merged


def build_bilingual_vtt(translated_cues, source_cues):
    """Bangun teks WEBVTT dwibahasa (Baris atas: Terjemahan, Baris bawah: Teks Asli)."""
    if not translated_cues:
        return build_vtt(source_cues or [])
    if not source_cues or len(source_cues) != len(translated_cues):
        return build_vtt(translated_cues)
    combined = []
    for tr_c, src_c in zip(translated_cues, source_cues):
        tr_txt = (tr_c.get("text") or "").strip()
        src_txt = (src_c.get("text") or "").replace("\n", " ").strip()
        if src_txt and tr_txt.lower() != src_txt.lower():
            text_out = f"{tr_txt}\n{src_txt}"
        else:
            text_out = tr_txt
        combined.append({"start": tr_c["start"], "end": tr_c["end"], "text": text_out})
    return build_vtt(combined)


def estimate_optimal_offset(builtin_cues: list, os_cues: list, max_shift: float = 15.0) -> float:
    """Hitung offset waktu optimal (detik) untuk menyelaraskan os_cues terhadap builtin_cues anime.
    Menggunakan cross-correlation histogram selisih waktu mulai (start onset) dengan presisi 0.2 detik."""
    if not builtin_cues or not os_cues:
        return 0.0
    buckets = _collections.Counter()
    b_starts = [float(c["start"]) for c in builtin_cues[:400]]
    o_starts = [float(c["start"]) for c in os_cues[:400]]

    for bs in b_starts:
        for os_t in o_starts:
            diff = bs - os_t
            if -max_shift <= diff <= max_shift:
                q = round(diff * 5.0) / 5.0
                buckets[q] += 1

    if not buckets:
        return 0.0

    best_q, best_cnt = buckets.most_common(1)[0]
    # Hitung rata-rata tertimbang di sekitar puncak (best_q +- 0.2s)
    total_w = 0
    weighted_sum = 0.0
    for q_val in (round((best_q - 0.2) * 5.0) / 5.0, best_q, round((best_q + 0.2) * 5.0) / 5.0):
        w = buckets.get(q_val, 0)
        total_w += w
        weighted_sum += q_val * w

    n_min = min(len(b_starts), len(o_starts))
    min_required = max(2, min(n_min, int(n_min * 0.15))) if n_min >= 10 else max(2, int(n_min * 0.5))
    if total_w < min_required:
        return 0.0

    refined = round(weighted_sum / max(1, total_w), 2)
    return refined if abs(refined) >= 0.20 else 0.0


def _cues_overlap(a_start: float, a_end: float, b_start: float, b_end: float, tol: float = 0.25) -> bool:
    """True jika dua rentang waktu cue saling berimpitan atau sangat berdekatan."""
    overlap = min(a_end, b_end) - max(a_start, b_start)
    if overlap >= -tol:
        return True
    return abs(a_start - b_start) <= 0.65


def find_unmatched_builtin_cues(builtin_cues: list, os_cues: list, offset: float = 0.0) -> tuple:
    """Temukan cue pada subtitle bawaan anime (seperti Sign, OP/ED, Preview) yang belum ada di OpenSubtitles.
    Mengembalikan (list_index_builtin, list_cue_builtin)."""
    if not builtin_cues:
        return ([], [])
    if not os_cues:
        return (list(range(len(builtin_cues))), list(builtin_cues))

    shifted_os = [
        {"start": max(0.0, float(c["start"]) + offset), "end": max(0.1, float(c["end"]) + offset)}
        for c in os_cues
    ]
    unmatched_idx = []
    unmatched_cues = []
    for idx, bc in enumerate(builtin_cues):
        bs, be = float(bc["start"]), float(bc["end"])
        has_match = False
        for oc in shifted_os:
            if _cues_overlap(bs, be, oc["start"], oc["end"], tol=0.20):
                has_match = True
                break
        if not has_match:
            unmatched_idx.append(idx)
            unmatched_cues.append(bc)
    return (unmatched_idx, unmatched_cues)


def merge_opensubtitles_with_builtin(
    builtin_cues: list,
    os_cues: list,
    merge_mode: str = "hybrid",
    translated_gaps: dict = None,
    offset: float = None,
) -> tuple:
    """Gabungkan (merge) subtitle yang diunduh dari OpenSubtitles dengan subtitle bawaan anime.

    Mekanisme:
      1. Auto-Sync Offset: Menyelaraskan timeline os_cues dengan builtin_cues.
      2. Timestamp Snapping: Menempelkan waktu cue OpenSubtitles ke timestamp presisi milik subtitle bawaan.
      3. Gap Filling (Hybrid): Mengisi cue yang hilang di OpenSubtitles (Signs/OP/ED/Preview) dari subtitle bawaan.
      4. Bilingual Mode (os_dual): Menyusun teks OpenSubtitles di baris atas & teks bawaan anime di baris bawah.

    Mengembalikan (merged_cues, stats_dict).
    """
    from api.opensubtitles import strip_opensubtitles_ads

    clean_os = strip_opensubtitles_ads(os_cues or [])
    clean_builtin = list(builtin_cues or [])

    if not clean_os and not clean_builtin:
        return ([], {"offset": 0.0, "os_count": 0, "gap_filled": 0, "snapped": 0})
    if not clean_os:
        return (clean_builtin, {"offset": 0.0, "os_count": 0, "gap_filled": len(clean_builtin), "snapped": 0})
    if not clean_builtin:
        return (clean_os, {"offset": 0.0, "os_count": len(clean_os), "gap_filled": 0, "snapped": 0})

    if offset is None:
        offset = estimate_optimal_offset(clean_builtin, clean_os)

    translated_gaps = translated_gaps or {}
    merged = []
    snapped_count = 0
    gap_filled_count = 0
    matched_builtin_indices = set()

    for oc in clean_os:
        os_s = max(0.0, float(oc["start"]) + offset)
        os_e = max(os_s + 0.1, float(oc["end"]) + offset)
        os_txt = (oc.get("text") or "").strip()
        if not os_txt:
            continue

        # Cari cue bawaan yang berimpitan paling dekat
        best_b_idx = -1
        best_dist = 999.0
        overlapping_b_texts = []

        for b_idx, bc in enumerate(clean_builtin):
            bs, be = float(bc["start"]), float(bc["end"])
            if _cues_overlap(os_s, os_e, bs, be, tol=0.20):
                matched_builtin_indices.add(b_idx)
                b_txt = (bc.get("text") or "").replace("\n", " ").strip()
                if b_txt and b_txt not in overlapping_b_texts:
                    overlapping_b_texts.append(b_txt)
                dist = abs(os_s - bs) + abs(os_e - be)
                if dist < best_dist:
                    best_dist = dist
                    best_b_idx = b_idx

        final_s, final_e = os_s, os_e
        if best_b_idx >= 0:
            bc_best = clean_builtin[best_b_idx]
            bs, be = float(bc_best["start"]), float(bc_best["end"])
            if abs(os_s - bs) <= 0.85 and abs(os_e - be) <= 1.10:
                final_s, final_e = bs, be
                snapped_count += 1

        if merge_mode == "bilingual" and overlapping_b_texts:
            base_line = " / ".join(overlapping_b_texts[:2])
            if base_line.lower() != os_txt.replace("\n", " ").strip().lower():
                final_txt = f"{os_txt}\n{base_line}"
            else:
                final_txt = os_txt
        else:
            final_txt = os_txt

        merged.append({"start": final_s, "end": final_e, "text": final_txt})

    # Isi celah cue dari subtitle bawaan yang tidak ada di OpenSubtitles (Signs, OP/ED, Preview)
    if merge_mode in ("hybrid", "bilingual"):
        for b_idx, bc in enumerate(clean_builtin):
            if b_idx in matched_builtin_indices:
                continue
            bs, be = float(bc["start"]), float(bc["end"])
            orig_b_txt = (bc.get("text") or "").strip()
            if not orig_b_txt:
                continue
            tr_b_txt = (translated_gaps.get(b_idx) or orig_b_txt).strip()
            if merge_mode == "bilingual" and tr_b_txt.lower() != orig_b_txt.lower():
                gap_txt = f"{tr_b_txt}\n{orig_b_txt.replace(chr(10), ' ')}"
            else:
                gap_txt = tr_b_txt
            merged.append({"start": bs, "end": be, "text": gap_txt})
            gap_filled_count += 1

    final_cues = merge_overlapping_cues(merged)
    stats = {
        "offset": offset,
        "os_count": len(clean_os),
        "builtin_count": len(clean_builtin),
        "snapped": snapped_count,
        "gap_filled": gap_filled_count,
        "total_merged": len(final_cues),
    }
    return (final_cues, stats)


def _vtt_ts(s):
    """Parse VTT timestamp (HH:MM:SS.mmm or MM:SS.mmm) to seconds."""
    m = _re.match(r"^(?:(\d+):)?([0-5]?\d):([0-5]\d)(?:[.,](\d{1,3}))?$", (s or "").strip())
    if not m:
        return -1.0
    ms = int((m.group(4) + "000")[:3]) if m.group(4) else 0
    return (int(m.group(1)) * 3600 if m.group(1) else 0) + int(m.group(2)) * 60 + int(m.group(3)) + ms / 1000.0


def build_vtt(cues):
    """Reconstruct WEBVTT text dari cues."""
    out = ["WEBVTT", ""]
    for c in cues:
        s = c["start"]
        e = c["end"]
        out.append(f"{_fmt_ts(s)} --> {_fmt_ts(e)}")
        out.append(c["text"])
        out.append("")
    return "\n".join(out)


def _fmt_ts(seconds):
    seconds = max(0.0, seconds)
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds - h * 3600 - m * 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


LANG_NAMES = {
    "en": "English",
    "id": "Indonesian",
    "ja": "Japanese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "ru": "Russian",
    "th": "Thai",
    "vi": "Vietnamese",
    "tr": "Turkish",
    "hi": "Hindi",
}


def _extract_err(resp):
    """Ekstrak pesan error dari response HTTP OpenAI/Gemini/Groq."""
    raw_msg = ""
    try:
        j = resp.json()
        if isinstance(j, list) and len(j) > 0:
            j = j[0]
        if isinstance(j, dict):
            err = j.get("error")
            if isinstance(err, dict):
                raw_msg = err.get("message") or err.get("code") or str(err)
            elif err:
                raw_msg = str(err)
            elif "message" in j:
                raw_msg = str(j["message"])
    except Exception:
        pass
    if not raw_msg:
        txt = (resp.text or "").strip()
        raw_msg = txt[:120] if txt else f"HTTP {resp.status_code}"

    # Deteksi pesan error spesifik Google AI Studio key
    low = raw_msg.lower()
    if "api key not valid" in low or "pass a valid api key" in low or "api_key_invalid" in low or "invalid auth key" in low:
        return "API Key Google tidak valid. Dapatkan kunci terbaru (awalan AQ...) di aistudio.google.com"
    return raw_msg


# ---------------------------------------------------------------------------
# Tier 1: AI Fansub (LLM, OpenAI-compatible)
# ---------------------------------------------------------------------------

# Model Ollama Cloud yang masuk Free plan (khusus gpt-oss)
OLLAMA_FREE_MODELS = ["gpt-oss:20b", "gpt-oss:120b"]

# Normalisasi penamaan model lama ke model aktif
_LEGACY_MODEL_UPGRADE = {
    "ollama": {
        "gemma4:31b": "gpt-oss:20b",
        "gemma3:12b": "gpt-oss:20b",
        "gemma4": "gpt-oss:20b",
        "gpt-oss:20b-cloud": "gpt-oss:20b",
        "gpt-oss-20b": "gpt-oss:20b",
    },
    "google": {
        "gemini-3.1-flash-lite": "gemini-2.0-flash",
        "gemini-3.8-flash": "gemini-2.0-flash",
        "gemini-1.5-flash-latest": "gemini-1.5-flash",
    },
}

_DEFAULT_MODEL = {
    "ollama": "gpt-oss:20b",
    "ollama_local": "gpt-oss:20b",
    "google": "gemini-2.0-flash",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "google/gemini-2.0-flash-exp:free",
    "openai": "gpt-4o-mini",
    "custom": "gpt-4o-mini",
}

# batch = jumlah cue per request, conc = request paralel.
_PROVIDER_CFG = {
    "google": {"batch": 80, "conc": 2},
    "ollama": {"batch": 50, "conc": 3},
    "ollama_local": {"batch": 20, "conc": 1},
    "groq": {"batch": 40, "conc": 2},
    "openrouter": {"batch": 40, "conc": 2},
    "openai": {"batch": 60, "conc": 3},
    "custom": {"batch": 40, "conc": 2},
}

_PROVIDER_LABEL = {
    "google": "Google AI Studio", "ollama": "Ollama Cloud", "ollama_local": "Ollama Lokal",
    "groq": "Groq", "openrouter": "OpenRouter", "openai": "OpenAI", "custom": "OpenAI-compatible",
}


def is_local_llm(apiurl: str) -> bool:
    """True kalau endpoint LLM berjalan di mesin lokal (tidak butuh API key)."""
    u = (apiurl or "").lower()
    return any(h in u for h in ("://localhost", "://127.0.0.1", "://0.0.0.0", "://[::1]"))


def detect_provider(apiurl: str) -> str:
    u = (apiurl or "").lower()
    if "googleapis.com" in u:
        return "google"
    if "ollama.com" in u:
        return "ollama"
    if is_local_llm(u):
        return "ollama_local"
    if "groq.com" in u:
        return "groq"
    if "openrouter.ai" in u:
        return "openrouter"
    if "openai.com" in u:
        return "openai"
    return "custom"


def detect_provider_from_key(key: str) -> tuple:
    """Mengembalikan (provider, default_model, default_apiurl) menyesuaikan apikey dari user."""
    k = (key or "").strip().strip("\"'").strip()
    if not k:
        return ("google", "gemini-2.0-flash", "https://generativelanguage.googleapis.com/v1beta/openai")
    if k.startswith("gsk_"):
        return ("groq", "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1")
    if k.startswith("AQ.") or k.startswith("AIza") or k.startswith("AQ"):
        return ("google", "gemini-2.0-flash", "https://generativelanguage.googleapis.com/v1beta/openai")
    if k.startswith("sk-or-"):
        return ("openrouter", "google/gemini-2.0-flash-exp:free", "https://openrouter.ai/api/v1")
    if k.startswith("ollama_") or k.startswith("ol_") or (len(k) > 35 and "." in k):
        return ("ollama", "gpt-oss:20b", "https://ollama.com/v1")
    if k.startswith("sk-") or k.startswith("sk_"):
        return ("openai", "gpt-4o-mini", "https://api.openai.com/v1")
    return ("custom", "gpt-4o-mini", "https://api.openai.com/v1")


def _model_chain(prov: str, model: str):
    """Urutan model yang dicoba; model berikutnya dipakai saat limit/402/404."""
    chain = [model]
    if prov == "ollama":
        chain += OLLAMA_FREE_MODELS
    elif prov == "google":
        chain += ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]
    elif prov == "groq":
        chain.append("llama-3.3-70b-versatile")
    seen, out = set(), []
    for m in chain:
        if m and m not in seen:
            seen.add(m)
            out.append(m)
    return out


_FANSUB_PROMPT_ID = """Kamu adalah penerjemah fansub anime Indonesia berpengalaman. Terjemahkan subtitle {src} menjadi bahasa Indonesia yang luwes, enak dibaca, dan adaptif mengikuti situasi adegan (scene) — BUKAN bahasa kaku ala mesin penerjemah.

Aturan Nada Bahasa Sesuai Konteks Adegan:
1. Adegan Formal / Berwibawa / Kerajaan / Militer:
   - Situasi: Audiensi raja/bangsawan/tetua, ksatria melapor ke komandan, pidato resmi, pelayan/maid melayani tuannya, adegan ritual.
   - Kata ganti: "Saya/Anda", "Tuan/Nona", "Paduka/Yang Mulia", "Hamba", "Pangeran/Tuan Putri".
   - Nada bicara: Baku, sopan, berwibawa, dan elegan ("tidak", "sudah", "hanya", "mohon", "baiklah").
   - DILARANG menyisipkan partikel gaul santai ("nggak", "kok", "sih", "deh", "dong") ke dalam dialog formal ini.

2. Adegan Santai / Sehari-hari / Komedi / Sekolah:
   - Situasi: Percakapan teman sebaya, keluarga, interaksi di kedai, komedi/romansa.
   - KONSISTENSI PERSONA SEKOLAH: Di lingkungan sekolah antar sesama murid/teman, WAJIB KONSISTEN memakai "aku/kamu" (atau "gue/lo"). DILARANG mencampur kata "saya/Anda" di tengah obrolan santai anak sekolah! (Contoh SALAH: "dia di kelas saya" -> BENAR: "dia di kelasku").
   - Nada bicara: Bahasa lisan santai fansub ("nggak", "udah", "aja", "banget", "kok", "sih", "deh", "kan", "nih", "lho", "gimana", "kenapa", "kayak", "emang", "beneran", "dengerin", "liat").
   - Panggilan pihak ketiga: "cowok itu", "cewek itu", "dia" (JANGAN gunakan "lelaki itu", "wanita itu", "gadis tersebut").

3. Adegan Kasar / Preman / Musuh:
   - Situasi: Karakter berandalan/kasar, musuh meremehkan lawan, umpatan pertarungan.
   - Kata ganti: "gue/lo", dengan umpatan wajar ("brengsek", "sialan", "kurang ajar").

Kosakata Game, Isekai & Job System:
- Terjemahkan istilah game & isekai secara wajar dan alami (bisa memakai padanan umum Indonesia yang lazim di fansub):
  * "Quest / Mission" -> "Misi" (atau "quest")
  * "Party" -> "Kelompok" / "Tim" (atau "party")
  * "Skill" -> "Keahlian" / "Jurus" / "Kemampuan" / "Skill"
  * "Magic" -> "Sihir"
  * "Item" -> "Barang" / "Item"
  * "Dungeon" -> "Dungeon" / "Labirin" (JANGAN gunakan istilah kaku "penjara bawah tanah")
  * "Monster" -> "Monster"
  * "Level up" -> "Naik level"
  * "Inventory" -> "Penyimpanan" / "Inventori"
  * "Boss" -> "Bos" / "Boss"
  * "Guild" -> "Guild"
- Sistem Profesi / Job System:
  * "Job / Class" -> "Kelas" / "Profesi" / "Job" (misal: "What is your job/class?" -> "Apa kelasmu? / Apa profesimu?")
  * "Job change / Class advancement" -> "Ganti job" / "Pindah kelas" / "Naik kelas"
  * "Role" -> "Peran" (Tank, DPS, Healer, Support)
  * "Warrior / Fighter" -> "Pejuang" / "Petarung" / "Warrior"
  * "Knight / Paladin" -> "Ksatria" / "Paladin"
  * "Swordsman" -> "Pendekar Pedang" / "Ahli Pedang"
  * "Berserker" -> "Berserker"
  * "Tank / Guardian" -> "Tank" / "Pelindung"
  * "Archer / Hunter" -> "Pemanah" / "Pemburu"
  * "Ranger" -> "Ranger" / "Pengembara"
  * "Thief / Rogue" -> "Pencuri" / "Rogue"
  * "Assassin" -> "Pembunuh bayaran" / "Assassin"
  * "Mage / Wizard" -> "Penyihir" / "Mage"
  * "Necromancer" -> "Necromancer" / "Pembangkit mayat"
  * "Sage" -> "Sage" / "Orang Bijak"
  * "Healer / Priest / Cleric" -> "Penyembuh" / "Pendeta" / "Cleric" / "Healer"
  * "Saint / Saintess" -> "Orang Suci" / "Santa"
  * "Tamer / Beast Tamer" -> "Penjinak" / "Penjinak Monster"
  * "Summoner" -> "Pemanggil" / "Summoner"
  * "Blacksmith" -> "Pandai Besi"
  * "Alchemist" -> "Alkemis"
  * "Hero" -> "Pahlawan"
  * "Demon Lord" -> "Raja Iblis"
  * "Novice" -> "Pemula" / "Novice"

Kosakata Mecha & Pertempuran Robot / Taktis Militer (Mecha & Tactical Sci-Fi):
- "All units, sortie! / Sortie immediately!" -> "Semua unit, segera meluncur / berangkat bertempur / bersiap berangkat!" (JANGAN: "segera keluar").
- "Target locked on / lock-on" -> "Target terkunci!"
- "Take evasive action!" -> "Lakukan manuver menghindar! / Menghindar!" (JANGAN: "Ambil tindakan menghindar").
- "Direct hit / took a direct hit" -> "Kena telak! / Terkena tembakan langsung!" (JANGAN: "Pukulan langsung").
- "Emergency ejection system / eject!" -> "Sistem ejeksi darurat / lontarkan diri!" (JANGAN: "Sistem peluncuran darurat").
- "Energy filler / energy pack" -> "Energy filler / paket energi / cadangan energi" (JANGAN: "Penampung energi").
- "Fire at will!" -> "Bebas tembak! / Tembak sesuka hati!" (JANGAN: "Tembak sesuai keinginan").
- "All hail [Empire/Britannia]!" -> "Hidup [Britannia]! / Jayalah [Britannia]!" (JANGAN: "Semua bersorak").
- "Checkmate" -> "Skakmat" (JANGAN biarkan "Checkmate" jika teks dialog fansub).
- "Caught in the crossfire" -> "Terjebak dalam baku tembak / terkena baku tembak" (JANGAN: "Tertangkap dalam tembakan silang").
- "Surrender unconditionally" -> "Menyerahlah tanpa syarat!" (JANGAN: "Tundukkan tanpa syarat").
- "In the belly of the beast" -> "Di sarang musuh / di mulut singa" (JANGAN harfiah: "Di perut binatang").
- "Dance right into my trap" -> "Masuk tepat ke dalam jebakanku / masuk ke perangkapku" (JANGAN: "Menari ke jebakan").
- "Pulling the strings / who is pulling the strings?" -> "Mengendalikan semuanya / siapa dalang di balik semua ini?" (JANGAN: "memegang tali").
- "Honorary citizen" -> "Warga kehormatan" (JANGAN: "warga harta karun").
- "Ceasefire / cease fire!" -> "Gencatan senjata! / Hentikan tembakan!"

Kosakata Dunia Ninja & Pertarungan Shonen (Ninja / Shinobi - e.g. Naruto):
- "Rogue Ninja / missing-nin" -> "Ninja pelarian / nukenin" (JANGAN: "Rouge Ninjas").
- "Ninja Art / Ninpo" -> "Jutsu / Seni Ninja / Ninpo" (JANGAN kaku harfiah: "Seni Ninja").
- "Barrier / sealing barrier" -> "Kekai / dinding penghalang / segel penghalang" (JANGAN kaku: "Penghalang" jika konteks jutsu kekai).
- "Chakra" -> "Cakra / Chakra".
- "Kunoichi" -> "Kunoichi / ninja wanita".
- "Genin / Chunin / Jonin / Anbu" -> "Genin / Chunin / Jonin / Anbu" (tetap gunakan istilah resmi ninja).
- "Lord Hokage / Hokage-sama" -> "Tuan Hokage / Yang Mulia Hokage".
- "Substitute / Body Replacement Technique" -> "Jutsu Pengganti Tubuh / Kawarimi no Jutsu".
- "Shadow Clone" -> "Kage Bunshin / Klon Bayangan".
- "Hand signs / seals" -> "Segel tangan / segel jari".
- "Taijutsu / Ninjutsu / Genjutsu" -> "Taijutsu / Ninjutsu / Genjutsu".
- "Curse Mark / Cursed Seal" -> "Segel Gaib / Tanda Kutukan / Juin".
- "Leaf Village / Hidden Leaf" -> "Desa Konoha / Desa Daun Tersembunyi".
- "Sand Village / Hidden Sand" -> "Desa Suna / Desa Pasir Tersembunyi".
- "Sound Village / Hidden Sound" -> "Desa Otogakure / Desa Bunyi Tersembunyi".
- "Mist Village / Hidden Mist" -> "Desa Kirigakure / Desa Kabut Tersembunyi".
- "Once in a lifetime request / request of a lifetime" -> "Permintaan sekali seumur hidup" (JANGAN kaku harfiah: "sekali seumur hidup permintaanku").
- "Bring [someone] back" -> "Membawa [seseorang] kembali / pulangkan [dia]" (JANGAN: "Bawakan kembali").

Kosakata Dunia Kutukan & Penyihir Modern (Jujutsu / Sorcery - e.g. Jujutsu Kaisen):
- "Cursed Object / Cursed Item" -> "Benda terkutuk / jimat kutukan".
- "Cursed Spirit / Curse" -> "Kutukan / roh terkutuk" (JANGAN: "roh" biasa jika roh jahat kutukan).
- "Cursed Energy" -> "Energi terkutuk / hawa kutukan".
- "Domain Expansion" -> "Ryoiki Tenkai / Perluasan Domain".
- "Jujutsu High / Jujutsu Tech" -> "SMK Jujutsu / SMA Jujutsu".
- "Jujutsu Sorcerer" -> "Penyihir Jujutsu".
- "Occult Research Club / Occult Club" -> "Klub Penelitian Ilmu Gaib / Klub Gaib".
- "Secret execution" -> "Eksekusi rahasia" (JANGAN: "eksekusi secara diam-diam").
- "Stevenson screen" -> "Kotak Stevenson / sangkar cuaca Stevenson" (JANGAN: "Layar Stevenson").
- "Sea angel / clione" -> "Clione / malaikat laut".
- "Council president" -> "Ketua OSIS" (JANGAN: "Presiden" jika konteks sekolah).
- "Leave me alone!" -> "Jangan ganggu aku! / Biarkan aku sendiri!" (JANGAN: "Tinggalkan aku sendiri").

Kosakata Petualangan Fantasi Abadi & Elf (High Fantasy / Elf - e.g. Frieren):
- "Beyond Journey's End" -> "Melampaui Akhir Perjalanan / Setelah Akhir Petualangan".
- "Hero Himmel" -> "Himmel sang Pahlawan".
- "Warrior Eisen" -> "Eisen sang Kesatria / Eisen sang Pejuang".
- "Priest Heiter" -> "Heiter sang Pendeta".
- "Mage Frieren" -> "Frieren sang Penyihir".
- "Mimic" -> "Mimic / monster peti".
- "Corrupt priest" -> "Pendeta bejat / pendeta pemabuk" (JANGAN: "pendeta yang korup").
- "Now, now... / There, there..." -> "Sudahlah... / Tenanglah..." (JANGAN diterjemahkan harfiah: "Sekarang, sekarang...").
- "Equal / call it even" -> "Impang / kita impas" (JANGAN: "kita setara").
- "Take [someone] down a peg / teach a lesson" -> "Memberi mereka pelajaran" (JANGAN: "mencuci sepatu").
- "Wash your shoes" -> "Menjilat sepatu / mencuci sepatu".
- "Old school building / old schoolhouse" -> "Gedung sekolah lama / gedung sekolah tua"
- "Ghost journal / spiritual diary" -> "Buku harian hantu / jurnal hantu / buku catatan hantu" (JANGAN: "Buku spiritual").
- "Put [evil spirits / ghosts] to sleep / put to rest" -> "Menidurkan / menenangkan [roh / arwah / hantu]" (JANGAN: "Ngendang roh supaya tidur").
- "Seal [a ghost / spirit / demon]" -> "Menyegel [hantu / roh / siluman]" (JANGAN: "Tutup hantu / tutup nasib").
- "Spiritual seal / talisman" -> "Segel spiritual / jimat pengusir arwah / jimat" (JANGAN biarkan "talisman" kaku).
- "Possess / possessed" -> "Merasuki / kerasukan / merasuk ke dalam" (JANGAN: "Memikat").
- "Demon / fiend / youkai" -> "Siluman / iblis / monster / youkai" (JANGAN acak jadi "naga").
- "Camphor tree" -> "Pohon kamper / pohon kapur barus" (JANGAN: "Pohon kapur tulis").
- "Scaredy-cat" -> "Penakut / pengecut" (JANGAN: "Kucing takut").
- "Pull yourself together!" -> "Kuatkan dirimu! / Tenangkan dirimu! / Sadarlah!" (JANGAN: "Kumpulin diri!").
- "Echoing" (in empty hallway) -> "Bergema" (JANGAN: "Yang gema").

Kosakata Dunia Sihir, Fantasi Klasik & Atelier Sihir (Magic Atelier, Witch & Sorcery - e.g. Witch Hat Atelier, Frieren, Little Witch Academia):
- "Cast / cast a spell / cast magic" -> "Merapal sihir / menggunakan sihir / mengeluarkan mantra" (JANGAN terjemahkan kaku: "melakukan casting").
- "Casting seal" -> "Segel sihir / segel mantra" (JANGAN: "casting seal").
- "Conjuring ink / magic ink" -> "Tinta sihir / tinta mantra" (JANGAN: "tinta sulap").
- "Magic stationer / magic stationer's" -> "Toko alat sihir / toko pena sihir" (JANGAN: "toko alat tulis ajaib").
- "Wand / crack in my wand" -> "Tongkat sihir / retakan di tongkatku" (JANGAN: "celah di tongkat").
- "Apprentice / apprentice witch" -> "Murid sihir / murid penyihir" (JANGAN: "magang / pemagang").
- "Brimmed hat / pointed hat / witch hat" -> "Topi bertepi / topi runcing / topi penyihir".
- "Brimhat / brimhats" -> "Penyihir bertopi / kaum penyihir bertopi".
- "Magic circle / spell crest" -> "Lingkaran sihir / lambang mantra / pola sihir".
- "Quill / magic quill" -> "Pena bulu / pena sihir".
- "Consent of the Crown" -> "Ujian Mahkota / Persetujuan Mahkota".
- "Diadem Herb / herb" -> "Herba Mahkota / tanaman obat" (JANGAN: "memilih ramuan" saat memetik tanaman).
- "Pegasus Carriage" -> "Kereta Pegasos / kereta kuda terbang".
- "Outsiders don't belong here" -> "Orang luar tidak pantas berada di sini / orang luar tak boleh ada di sini".
- "They have nothing to offer the world of magic" -> "Mereka tak punya tempat di dunia sihir".
- "Draw spells reliably" -> "Menggambar mantra dengan sangat mantap / menggambar mantra dengan lancar" (JANGAN glitched: "sangat baik andal").
- "Sold out in no time" -> "Langsung ludes dalam sekejap / habis seketika" (JANGAN tertukar tiket: "tiketnya terjual habis").
- "It's on me / my fault" -> "Salahku sendiri / ini salahku" (JANGAN harfiah: "aku bertanggung jawab atas berdirinya").
- "Do you think you could fix it?" -> "Kira-kira bisa kamu perbaiki nggak? / Kamu rasa kamu bisa memperbaikinya?".

Kosakata Misteri Sekolah & Klub Sastra (School Mystery / Club Anime - e.g. Hyouka):
- "Classic Lit Club / Classic Literature Club" -> "Klub Sastra Klasik" (JANGAN biarkan "Classic Lit").
- "Pay my respects" (kunjungan ke klub/salam kenal) -> "Memberi salam / menyapa" (JANGAN diartikan "ngelamun").
- "Energy conservation / energy-conserving / energy saver" -> "Hemat energi / menghemat energi"
- "Energy-consuming" -> "Boros energi / menghabiskan banyak energi" (JANGAN tertukar jadi "hemat energi").
- "I'm curious! / I am curious" -> "Aku penasaran! / Aku penasaran sekali!"
- "A database cannot draw conclusions" -> "Database tidak bisa menarik kesimpulan"
- "Peeping Tom" -> "Tukang intip / pengintip"
- "After-school rendezvous" -> "Pertemuan sepulang sekolah / kencan sepulang sekolah"
- "Checkout period" (in library) -> "Masa peminjaman / batas pinjam buku" (JANGAN: "waktu cekout").
- "Sharp tongue" -> "Bicaranya pedas / mulutnya cukup pedas" (JANGAN: "punya lidah tajam").
- "Declare legally dead / legally dead" -> "Dinyatakan telah meninggal secara hukum / dinyatakan meninggal" (JANGAN kaku: "resmi mati").
- "Student body" -> "Seluruh murid / seluruh siswa" (JANGAN diterjemahkan harfiah: "tubuh siswa").
- "Sacrificial lamb" -> "Tumbal / kambing hitam" (JANGAN: "domba korban").
- "Punks" (in school/delinquent context) -> "Berandalan / preman" (JANGAN biarkan "para punks").
- "Took the blame alone" -> "Menanggung semua kesalahan sendirian / memikul kesalahan sendirian"
- "After all" -> "Lagipula / Bagaimanapun juga" (JANGAN: "Setelah semua").
- "[N]th period / fifth period" (jadwal pelajaran sekolah) -> "Jam pelajaran ke-[N] / jam ke-[N]" (JANGAN: "periode ke-[N]").
- "Open-air bath / rotenburo" -> "Pemandian terbuka / pemandian luar ruangan" (JANGAN: "bath open-air").
- "Gave me chills / chills" -> "Bikin merinding / membuatku merinding" (JANGAN acak seperti "bikin kudetas").
- "Paper screen / shoji" -> "Pintu geser kertas / sekat kertas / shoji" (JANGAN: "layar kertas").
- "Transom / wooden transom" -> "Ventilasi kayu / kisi-kisi kayu"
- Karakter perempuan anggun/sopan (seperti Chitanda): Wajib bertutur kata sopan ("aku/kamu", santun), JANGAN gunakan "gue/lo".

Kosakata Kuliner & Duel Memasak (Cooking Battle / Gourmet - e.g. Shokugeki no Souma):
- "Order up! / Order's up!" -> "Pesanan siap! / Silakan dinikmati!" (JANGAN biarkan "Order up!").
- "It wasn't much! / Glad you liked it! (Osomatsusama)" -> "Bukan apa-apa kok! / Selamat menikmati hidanganku!" (JANGAN kaku harfiah: "Gak banyak juga").
- "Satisfy your palate" -> "Memanjakan lidahmu / memuaskan seleramu".

Kosakata Historis, Peperangan Viking & Ksatria (Historical / Viking - e.g. Vinland Saga):
- "Plunder / pillage" -> "Menjarah / merampas" (JANGAN: "mencuri / pencurilah").
- "Longship" -> "Kapal perang Viking / kapal panjang".
- "True warrior" -> "Prajurit sejati / kesatria sejati".

Kosakata Cyberpunk & Kepolisian Futuristik (Cyberpunk - e.g. Psycho-Pass):
- "Latent criminal" -> "Kriminal laten / penjahat laten".
- "Crime Coefficient" -> "Koefisien Kejahatan / Koefisien Kriminal".
- "Enforcement mode" -> "Mode penindakan / mode penegakan hukum".

Kosakata Romansa Elit & Perang Pikiran OSIS (Psychological Rom-Com - e.g. Kaguya-sama):
- "How cute... (O-kawaii koto)" -> "Manis sekali... / Betapa menggemaskannya..." (JANGAN diterjemahkan "Keren banget").
- "Got on his/her knees" -> "Berlutut / bersujud" (JANGAN: "ngelamun").
- "Confess / confession of love" -> "Menyatakan cinta / nembak" (JANGAN: "mengaku").
- "Student Council" -> "OSIS / Dewan Siswa".

Kosakata Anime Olahraga (Sports Anime):
- "Match" -> "Pertandingan" (JANGAN biarkan "match" jika mengacu ke permainan).
- "View" -> "Pemandangan" (JANGAN biarkan "view").
- "Looms in front of me" -> "Menjulang di depanku" (JANGAN: "Ngeliat di depan aku").
- "Coach" -> "Pelatih" (JANGAN biarkan "coach").
- "Off course" (in ball set/pass) -> "Melenceng / meleset" (JANGAN: "Off course").
- "Blow past [blockers]" -> "Menembus / menerobos [pemblokir]" (JANGAN: "Ngelupas blok").
- Istilah teknis voli/olahraga (Toss, Spike, Serve, Libero, Setter, Block, Match point, Time out) boleh tetap digunakan sesuai tradisi fansub olahraga.

Dilarang Terjemahkan Idiom Secara Harfiah (Gunakan Padanan Fansub Alami):
- "Aiming high" -> "Incaranmu tinggi juga" / "Seleramu tinggi juga" / "Pasang target tinggi" (JANGAN: "Banjir tinggi").
- "If you ask me" -> "Kalau menurutku sih" / "Menurutku" (JANGAN: "Kalau dengerin saya").
- "Hotties / Cuties" -> "Cewek-cewek cakep / cewek-cewek manis" (JANGAN: "Koleksi hot").
- "It goes without saying" -> "Nggak usah ditanya lagi" / "Sudah jelas" (JANGAN: "Gak usah dikira").
- "High school debut" -> "Awal baru di SMA" / "Mulai masa SMA" (JANGAN: "Debut SMA saya").
- "Plug the hole / plug" -> "Menutup lubang / menyumbat" (JANGAN: "Ngeplug").
- "How dare you [do X]!" -> "Beraninya kamu [lakukan X]!" / "Kurang ajar!" (JANGAN: "Gimana sih kamu boleh [X]").
- "How dare [an amateur]..." -> "Berani-beraninya [seorang amatir]..." (JANGAN: "Gimana sih amatir bisa...").
- "Middle of nowhere" -> "Pelosok / tempat terpencil / antah-berantah" (JANGAN: "Di tengah-tengah hutan").
- "Throw a tantrum / throw tantrums" -> "Tanteum / merajuk / ngambek" (JANGAN: "Lagi marah" tanpa emosi).
- "Big baby" -> "Kayak anak kecil / cengeng banget" (JANGAN: "Anak kecil banget").
- "See? Told ya!" -> "Tuh, kan! Apa kubilang!" (JANGAN: "Lihat? Katanya!").
- "Cool your head / cool off" -> "Menenangkan pikiran / mendinginkan kepala" (JANGAN: "Dinginkan kepala di pulau").
- "Talk back to [elders]" -> "Membantah / melawan [orang tua]" (JANGAN: "Ngomong balas").
- "Secret base" -> "Markas rahasia" (JANGAN: "Basis rahasia").
- "Cicadas" -> "Tonggeret / garengpung" (JANGAN: "Katak katak").
- "Bug" (in nature context) -> "Serangga / kumbang" (JANGAN biarkan "bug" atau "kutu komputer").
- "Like hell I would! / As if!" -> "Ogah banget! / Mana sudi!" (JANGAN: "Gak bakal, bro" kaku).
- "There is no way / no way in hell" -> "Nggak mungkin banget / mana mungkin" (JANGAN: "Gak ada cara aku ngelakuin").
- "Pervert" -> "Mesum / cowok mesum / cabul" (JANGAN biarkan "pervert").
- "Defenseless" -> "Gampang tersingkap / nggak ada pertahanan" (JANGAN: "Gak aman").
- "You guys tricked me!" -> "Kalian ngerjain aku, ya?!" (JANGAN: "Kalian ngapain ngapain!").
- "The wind is troubled today..." -> "Sepertinya angin hari ini sedang resah..." (gaya puitis/dramatis).
- "Hurry, let us make haste" -> "Ayo cepat, mari bergegas" (gaya puitis komedi).
- "How suspicious is that?" / "How suspicious!" -> "Mencurigakan banget, kan?" / "Mencurigakan sekali" (JANGAN: "Berapa curiga itu").
- "How [adjective] / How [suspicious/cute/etc.]" -> "Betapa / Begitu / Banget / Sekali" (JANGAN diterjemahkan "Berapa [kata sifat]").
- "How long was I out?" / "pass out / knock out" -> "Berapa lama aku pingsan / tak sadarkan diri?" (JANGAN: "Berapa lama aku keluar").
- "Make a fortune" -> "Kaya mendadak / untung besar / dapet banyak uang" (JANGAN: "Ngasih duit jahat").
- "At this rate" -> "Kalau begini terus / kalau kayak gini terus" (JANGAN: "Dengan kecepatan kayak gini").
- "Roger that / Copy that" -> "Dimengerti / Siap / Terima" (JANGAN: "Sanggah").
- "Optical decoy" -> "Umpan optik / ilusi optik" (JANGAN: "Penipu optik").
- "Paint the coordinates" -> "Tandai / kunci koordinatnya" (JANGAN: "Cat koordinat").
- "Wipe [them] off the map" -> "Ratakan [mereka] dengan tanah / lenyapkan mereka" (JANGAN: "Hapus mereka dari peta").
- "Corporal" -> "Kopral" (JANGAN: "Korpul").
- "Sick prank" -> "Lelucon keterlaluan / lelucon menjijikkan" (JANGAN: "Lelucon aneh").
- "Childish murderer" -> "Pembunuh kekanak-kanakan" (JANGAN: "Pembunuh anak kecil").
- "The only bad guy left" -> "Satu-satunya penjahat yang tersisa" (JANGAN: "Satu-satunya jahat").
- "I will see you executed" -> "Aku akan memastikanmu dieksekusi" (JANGAN: "Aku akan melihatmu dieksekusi").
- "Righteous people" -> "Orang-orang saleh / orang-orang jujur" (JANGAN: "Orang-orang yang benar").
- "Heart failure / heart attack" -> "Serangan jantung" (JANGAN: "Gagal jantung" jika konteks death note serangan mendadak).
- "In a pool of blood" -> "Bersimbah darah / tergenang darah" (JANGAN: "Di kolam darah").
- "Blow my cover" -> "Membongkar penyamaranku / membocorkan identitasku" (JANGAN: "Bocor rahasia aku").
- "In broad daylight" -> "Di siang bolong / terang-terangan" (JANGAN: "Di siang hari" kaku).
- "Stabbed to death" -> "Ditusuk sampai mati / ditikam hingga tewas" (JANGAN: "Disayat sampai mati").
- "Caught onto our trail" -> "Menemukan jejak kita / mengendus jejak kita" (JANGAN: "Menangkap jejak kita").
- "Jellyfied / gelatinous" -> "Berubah jadi agar-agar / jadi jeli" (JANGAN: "Jellyguy").
- "Have you lost your mind?" -> "Kamu sudah gila? / Kamu kehilangan akal sehat?" (JANGAN: "Kamu kehilangan akal" tanpa 'sehat').
- "Pale as a ghost" -> "Pucat pasi / pucat bagai mayat" (JANGAN: "Pucat kayak hantu").
- "Morgue" -> "Kamar jenazah / kamar mayat" (JANGAN biarkan "morgue").
- "My poor [someone] / other half" -> "[Seseorang]ku yang malang / belahan jiwaku yang malang" (JANGAN: "yang miskin").
- "Hate being questioned" -> "Benci ditanya-tanya / tidak suka diinterogasi" (JANGAN: "Susah dipengetan").
- "Don't say that out loud" -> "Jangan katakan itu keras-keras / jangan bicara sembarangan" (JANGAN: "Jangan bilang di luar").
- "Second basement level / B2" -> "Lantai bawah tanah kedua / lantai B2" (JANGAN: "Lantai bawah dua").
- "Ghosting someone / act like someone doesn't exist" -> "Mengabaikan / menganggapnya tak kasat mata" (JANGAN biarkan "ghosting").
- "On a royal tear / on a tear / on a rampage" -> "Mengamuk hebat / bikin onar tak terkendali" (JANGAN: "Kemarahan kerajaan").
- "Harm [someone] / do harm" -> "Melukai / menyakiti [seseorang]" (JANGAN: "Ngelakuin luka").
- "Eliminate [an opponent in battle]" -> "Menghabisi / melenyapkan" (JANGAN: "Menghapus Anda").
- "Profane [God]" -> "Menodai / menistakan" (JANGAN: "Memfitnah Tuhan").
- "Brother" (in anime sibling context) -> "Kakak / Kak / Abang" (JANGAN: "Bro").
- "Face aside / [X] aside" -> "Terlepas dari wajahnya / kesampingkan soal wajahnya" (JANGAN: "Tinggalkan wajah").
- "Sustain heavy damage / heavy casualties" -> "Mengalami kerugian/kerusakan besar" (JANGAN: "Menanggung kerusakan").
- "Solo player" -> "Pemain solo" (JANGAN: "Saya sendiri").
- "Pry into" -> "Mencari tahu / ikut campur urusan" (JANGAN: "Nanya ke").
- "Clowning around / acting stupid" -> "Bercanda / main-main / konyol" (JANGAN gunakan kata terlalu kasar/aneh seperti "ngegoblok").
- "Butt heads" -> "Berselisih / bentrok / bersitegang" (JANGAN: "Bertembung kepala").
- "Rot in hell" -> "Persetan / mampus sana / pergi ke neraka" (JANGAN: "Berputus di neraka").
- "There you go again!" -> "Mulai lagi, kan!" / "Kamu kumat lagi!" (JANGAN: "Kamu lagi!").
- "Packed you a lunch / pack a lunch" -> "Membawakanmu bekal" (JANGAN: "Bungkus makan siang").
- "Mongrel" (as anime insult) -> "Anjing kampung / hewan buduk" (JANGAN: "Anjing campuran").
- "At first sight / glance" -> "Pandangan pertama / saat pertama kali bertemu" (JANGAN: "Mata pertama").
- "Miss each other / pass by" -> "Berpapasan / saling melewatkan" (JANGAN: "Kelewatan satu sama lain").
- "I see" / "I get it" -> "Begitu rupanya" / "Ooh, begitu ya" / "Paham" (JANGAN: "Aku melihat").
- "Hold on" / "Wait" -> "Tunggu sebentar!" / "Tunggu dulu!" (JANGAN: "Bertahanlah").
- "Shut up" -> "Diem!" / "Berisik!" / "Diam!" (JANGAN: "Tutup mulutmu").
- "Are you alright?" -> "Kamu nggak apa-apa?" (JANGAN: "Apakah kamu baik-baik saja").
- "Damn it" / "Damn" -> "Sial!" / "Brengsek!" / "Cih!" (JANGAN: "Terkutuklah").
- "No way" -> "Nggak mungkin!" / "Mustahil!" (JANGAN: "Tidak ada jalan").
- "Never mind" -> "Lupakan saja" / "Bukan apa-apa" / "Nggak jadi".
- "Get lost" -> "Pergi sana!" / "Enyah!".
- "Bring it on!" -> "Sini maju kalau berani!" / "Ayo lawan!".
- "Give me a break" -> "Yang bener aja!" / "Jangan bercanda!".
- "Make a move" -> "Mendekati dia" / "Mengambil tindakan".
- "Cut it out" -> "Sudahlah!" / "Hentikan!".
- "You know" (sebagai pengisi dialog lisan) -> "Tahu nggak" / "Kan" / "Sih" / atau hilangkan jika hanya filler (JANGAN kaku harfiah: "kamu tahu").
- "Like [someone] so much / like very much" -> "Suka banget sama [dia]" (JANGAN harfiah: "menyukai Sakura sangat banyak").
- "As expected" -> "Sesuai dugaan / sudah kuduga / seperti dugaanku" (JANGAN kaku: "seperti yang diharapkan").
- "Get hit" -> "Kena serangan / terpukul / terluka" (JANGAN: "kena terbentur").
- "Decide on a password" -> "Menentukan kata sandi" (JANGAN: "memutuskan yang mana kata sandi").
- "In the end" -> "Pada akhirnya / ujung-ujungnya" (sesuaikan gaya bicara karakter).
- "Hidden Leaf / Leaf Village" -> "Desa Konoha" (JANGAN: "Desa Daun").
- "Revert to your original form" -> "Kembali ke wujud asli kalian" (JANGAN: "kembali ke bentuk semula").
- "What are you talking about?" -> "Ngomong apa sih kamu? / Apa maksudmu?" (JANGAN kaku: "Apa yang kamu bicarakan?").
- DILARANG MEMBIARKAN KATA SIFAT INGGRIS TANPA TERJEMAHAN:
  * "Embarrassing" -> "Memalukan" / "Bikin malu" (DILARANG: "sangat embarrassing").
  * "Gross" -> "Jijik" / "Menjijikkan".

Kamus Idiom & Ungkapan Khas Fansub Anime (Anti-Terjemahan Kaku):
- "It can't be helped / shouganai / shikataganai" -> "Mau gimana lagi / Mau bagaimana lagi" (JANGAN diterjemahkan kaku: "Itu tidak bisa ditolong").
- "Mendokusai / What a drag" -> "Merepotkan sekali / Bikin malas saja / Ribet banget" (JANGAN: "Seretan / Itu merepotkan").
- "Sasuga / As expected" -> "Sudah kuduga / Memang bisa diandalkan / Emang paling bisa" (JANGAN: "Seperti yang diharapkan").
- "Give me a break" -> "Yang benar saja! / Ampun deh! / Jangan bercanda!" (JANGAN: "Beri aku istirahat").
- "Serves you right" -> "Rasakan itu! / Syukurin! / Makanya jangan macam-macam!" (JANGAN: "Melayanimu dengan benar").
- "I'll take care of this / leave it to me" -> "Biar aku yang urus ini / Serahkan ini padaku" (JANGAN: "Aku akan merawat ini").
- "Take care of him (combat)" -> "Habisi dia! / Bereskan dia!" (JANGAN: "Rawat dia").
- "Don't let your guard down / stay alert" -> "Jangan lengah! / Tetap waspada!" (JANGAN: "Jangan biarkan penjagamu turun").
- "Lower your guard" -> "Lengah / Menurunkan kewaspadaan" (JANGAN: "Menurunkan penjaga").
- "Watch your back" -> "Hati-hati di belakangmu! / Waspadalah!" (JANGAN: "Perhatikan punggungmu").
- "Stand back!" -> "Mundur! / Menjauhlah!" (JANGAN: "Berdiri kembali!").
- "Back down / Back off" -> "Mundur! / Menjauh!" (JANGAN: "Kembali ke bawah").
- "Take this! / Kurae!" -> "Rasakan ini! / Terima ini!" (JANGAN: "Ambil ini!").
- "You bastard! / Kisama / Teme" -> "Brengsek! / Sialan kau! / Kurang ajar!".
- "I will never forgive you!" -> "Tidak akan kumaafkan! / Takkan kuampuni!" (JANGAN: "Aku tidak pernah memaafkanmu").
- "Are you hitting on me?" -> "Kamu lagi menggodaku ya? / Mau merayuku ya?" (JANGAN: "Apakah kamu memukulku?").
- "Don't get cocky" -> "Jangan sombong! / Jangan besar kepala!" (JANGAN: "Jangan sombong ayam").
- "You're blushing" -> "Mukamu merah / Kamu tersipu, ya?".
- "Don't get the wrong idea" -> "Jangan salah paham ya! / Bukan berarti begitu ya!".
- "I'm heading out" -> "Aku berangkat ya!".
- "I'm home / I'm back" -> "Aku pulang!".
- "Welcome home" -> "Selamat datang kembali / Selamat pulang".
- "Good grief / Yare yare" -> "Ya ampun... / Ampun deh... / Astaga...".
- "Make up your mind" -> "Tentukan pilihanmu! / Cepat putuskan!" (JANGAN: "Bentuk pikiranmu").
- "Change of heart" -> "Berubah pikiran" (JANGAN: "Perubahan hati").
- "I can't take it anymore" -> "Aku sudah tidak tahan lagi!" (JANGAN: "Aku tidak bisa mengambilnya lagi").
- "Crossed my mind" -> "Terlintas di pikiranku" (JANGAN: "Menyeberangi pikiranku").
- "Keep it to yourself" -> "Jangan bilang siapa-siapa / Rahasiakan ini" (JANGAN: "Simpan untuk dirimu sendiri").
- "Over my dead body" -> "Langkahi dulu mayatku!" (JANGAN: "Di atas tubuh matiku").
- "Who is in charge?" -> "Siapa penanggung jawabnya? / Siapa yang memimpin?" (JANGAN: "Siapa yang mengisi daya?").
- "Bite your tongue" -> "Jaga ucapanmu!" (JANGAN: "Gigit lidahmu").
- "Turn a blind eye" -> "Tutup mata / Pura-pura tidak tahu" (JANGAN: "Putar mata buta").
- "Cold feet" -> "Ragu-ragu / Ciut nyali" (JANGAN: "Kaki dingin").
- "On the house" -> "Gratis / Traktiran kedai" (JANGAN: "Di atas rumah").
- "Rule of thumb" -> "Pedoman umum / Patokan dasarnya" (JANGAN: "Aturan jempol").
- "Take for granted" -> "Menganggap remeh / Menyia-nyiakan" (JANGAN: "Ambil untuk diberikan").
- "Piece of cake" -> "Gampang banget / Sangat mudah" (JANGAN: "Sepotong kue").
- "Lost in thought" -> "Melamun / Tenggelam dalam pikiran" (JANGAN: "Hilang dalam pikiran").
- "Spill the beans / tea" -> "Bocorkan rahasianya / Ceritakan semuanya" (JANGAN: "Tumpahkan kacang / teh").
- "Under the weather" -> "Kurang enak badan / Sedang sakit" (JANGAN: "Di bawah cuaca").
- "Face the music" -> "Menanggung akibatnya" (JANGAN: "Menghadapi musik").
- "Bite the bullet" -> "Tabahkan dirimu / Pasrah menelan pil pahit" (JANGAN: "Gigit peluru").
- "Speak of the devil" -> "Panjang umur, baru saja diomongin" (JANGAN: "Bicara tentang iblis").
- "Hit the nail on the head" -> "Tepat sasaran" (JANGAN: "Pukul paku di kepala").
- "Beat around the bush" -> "Berbelit-belit" (JANGAN: "Memukul semak-semak").
- "Hang in there!" -> "Bertahanlah! / Semangat!" (JANGAN: "Gantung di sana").
- "Under your nose" -> "Tepat di depan matamu" (JANGAN: "Di bawah hidungmu").
- "Take it easy" -> "Santai saja / Tenang saja" (JANGAN: "Ambil dengan mudah").
- "Count me in / out" -> "Aku ikut! / Aku nggak ikut" (JANGAN: "Hitung aku masuk/keluar").
- "Not on my watch" -> "Tidak akan kubiarkan!" (JANGAN: "Bukan di jam tanganku").
- "Get a grip" -> "Sadarlah! / Tenangkan dirimu!" (JANGAN: "Dapatkan pegangan").
- "Keep your head down" -> "Tiarap! / Jaga sikap" (JANGAN: "Tundukkan kepalamu").
- "No offense / None taken" -> "Tanpa mengurangi rasa hormat / Nggak apa-apa kok" (JANGAN: "Tidak ada pelanggaran / Tidak diambil").
- "Have my back" -> "Lindungi punggungku / Selalu mendukungku" (JANGAN: "Miliki punggungku").
- "Cross the line" -> "Melampaui batas / Kelewatan" (JANGAN: "Menyeberangi garis").
- "Don't flatter yourself" -> "Jangan kepedean / Jangan terlalu percaya diri" (JANGAN: "Jangan menyanjung dirimu").
- "None of your business" -> "Bukan urusanmu!" (JANGAN: "Bukan bisnis Anda").
- "Take your time" -> "Santai saja, jangan terburu-buru" (JANGAN: "Ambil waktumu").
- "Right away" -> "Sekarang juga / Segera" (JANGAN: "Tepat pergi").
- "All of a sudden" -> "Tiba-tiba / Sekonyong-konyong" (JANGAN: "Semua tiba-tiba").
- Pertahankan nama orang, tempat, honorifik Jepang (-san, -kun, -chan, -sama, Senpai, Sensei), gagap & interjeksi emosi ("A-Apa?!", "Tch", "Hmph").
- Pertahankan token <br> untuk ganti baris dalam 1 cue.

Format Keluaran (WAJIB):
- Satu baris per input, format persis "N|terjemahan" (N = nomor input yang sama).
- DILARANG mengulang teks bahasa Inggris asal (JANGAN: "N|Teks Inggris|Terjemahan"). Cukup "N|terjemahan".
- Jumlah & nomor baris harus sama persis dengan input. Tanpa penjelasan atau markdown.

Contoh Multi-Scene:
Input:
1|Your Majesty, the vanguard knights are ready. We shall not fail your trust.
2|Great collection of hotties, huh? Aiming high, aren't you? Nibutani, huh?
3|Pretty sweet, if you ask me. It goes without saying, it was so embarrassing!
Output:
1|Yang Mulia, pasukan ksatria garis depan telah bersiap. Kami tidak akan mengecewakan kepercayaan Anda.
2|Cewek-cewek cakepnya mantap, kan? Incaranmu tinggi juga ya? Nibutani, kan?
3|Kalau menurutku sih cakep banget. Nggak usah ditanya lagi, itu memalukan banget!"""

_FANSUB_PROMPT_GENERIC = """You are an experienced anime fansub translator. Translate {src} subtitles into natural, casual, spoken {tgt} as a popular fansub release would — not stiff, literal machine translation.
- Translate meaning and emotion, not word-for-word; keep lines short and readable.
- Keep names, honorifics (-san, -kun, -chan, Senpai, Sensei), skill names and common gamer/anime terms.
- Keep stutters, interjections and emotional punctuation (?!, ..., ~). Keep the <br> token (line break inside a cue).
Output format (MANDATORY): one line per input as "N|translation" with the same N, same count and numbering, no merging/splitting, no explanations or markdown."""


def _fansub_system_prompt(src_name: str, tgt: str, tgt_name: str) -> str:
    if (tgt or "").lower() == "id":
        return _FANSUB_PROMPT_ID.format(src=src_name)
    return _FANSUB_PROMPT_GENERIC.format(src=src_name, tgt=tgt_name)


def _prep_line(text: str) -> str:
    """Cue text -> satu baris untuk prompt (newline jadi token <br>)."""
    t = (text or "").replace("\r", "")
    t = " <br> ".join(p.strip() for p in t.split("\n") if p.strip())
    return _re.sub(r"\s+", " ", t).strip()


def _restore_line(text: str) -> str:
    """Hasil model -> cue text (token <br> jadi newline, normalisasi karakter aneh)."""
    t = (text or "").replace("\u2011", "-").replace("\u2010", "-").replace("\u00a0", " ")
    t = _re.sub(r"\s*<br\s*/?>\s*", "\n", t, flags=_re.I)
    lines = [_re.sub(r"[ \t]+", " ", x).strip() for x in t.split("\n")]
    return "\n".join(x for x in lines if x)


# ---------------------------------------------------------------------------
# Post-Processing Lexicon Sanitizer (Normalisasi Diksi Fansub Indonesia)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Smart Scene Subtitle Detection (Multi-Domain Context Classifier)
# ---------------------------------------------------------------------------

_SCENE_MILITARY_RE = _re.compile(
    r"\b(jenderal|komandan|panglima|marsekal|laksamana|letnan|kapten|mayor|kolonel|sersan|kopral|"
    r"ajudan|perwira|inspektur|batalyon|batalion|regimen|divisi|peleton|brigade|skuadron|armada|"
    r"infantri|kavaleri|artileri|markas besar|pos komando|pos terdepan|garis depan|garis belakang|"
    r"garis pertahanan|benteng pertahanan|koordinat|radar|evakuasi|gencatan senjata|penyerahan tanpa syarat|"
    r"serangan udara|serangan fajar|manuver tempur|formasi tempur|protokol darurat|protokol keamanan|"
    r"pengadilan militer|dewan militer|otoritas militer|pasukan pengintai|pasukan pertahanan|pasukan penyerang|"
    r"baret|peluru kendali|rudal|peluncur roket|amunisi|senjata api|siap laksanakan|lapor, komandan)\b",
    _re.I
)

_SCENE_ROYAL_RE = _re.compile(
    r"\b(paduka|yang mulia|baginda|hamba|tuan putri|putri mahkota|pangeran|pangeran mahkota|"
    r"kaisar|permaisuri|ratu|raja|nobilitas|kaum bangsawan|bangsawan|adipati|duke|duchess|baron|"
    r"baroness|marquis|marquess|count|viscount|lord|lady|nona besar|tuan muda|tuanku|takhta|"
    r"istana kekaisaran|dewan kekaisaran|titah baginda|titah kaisar|uskup agung|paus|kardinal|"
    r"pendeta agung|santo|santa|kuil suci|ksatria suci|kesatria kekaisaran|sihir terlarang|sihir agung)\b",
    _re.I
)

_SCENE_GAMING_RE = _re.compile(
    r"\b(dungeon|guild|party|quest|raid|boss raid|monster bos|buff|debuff|hp|mp|mana|mana pool|"
    r"skill point|level up|drop rate|drop item|aggro|spawn|respawn|cooldown|magic circle|lingkaran sihir|"
    r"potion|ramuan penyembuh|guild master|petualang peringkat|status window|jendela status|papan peringkat|"
    r"tank|tanker|healer|dps|damage dealer|solo player|solo hunter|hunter rank|death game|vrmmo|"
    r"player killer|boss room|skill tree|dungeon break|spawn point)\b",
    _re.I
)

_FORMAL_INDICATORS_RE = _re.compile(
    _SCENE_MILITARY_RE.pattern + "|" + _SCENE_ROYAL_RE.pattern,
    _re.I
)

# ---------------------------------------------------------------------------
# Pre-GTX English Slang & Idiom Disambiguation (Stage 1 Normalizer)
# ---------------------------------------------------------------------------

_PRE_GTX_EN_SLANG_RULES = [
    (r"\bgotta bounce\b", "gotta go now"),
    (r"\bhave to bounce\b", "have to go now"),
    (r"\bno cap\b", "seriously, no lie"),
    (r"\bthat'?s cap\b", "that is a lie"),
    (r"\b(i'm|im|i am) down for that\b", "I agree to that"),
    (r"\b(i'm|im|i am) down\b", "I will join in"),
    (r"\bchill out\b", "calm down and relax"),
    (r"\bspill the tea\b", "reveal the secret"),
    (r"\bspill the beans\b", "reveal the secret"),
    (r"\bmy bad\b", "my mistake"),
    (r"\bcall it a day\b", "finish for today"),
    (r"\bbite the bullet\b", "endure the hardship"),
    (r"\bcold feet\b", "nervous hesitation"),
    (r"\bbreak a leg\b", "good luck"),
    (r"\bsaved by the bell\b", "saved at the critical moment"),
    (r"\btake a rain check\b", "reschedule for next time"),
    (r"\bspit it out\b", "say it right now"),
    (r"\bdon't sweat it\b", "do not worry about it"),
    (r"\bhold your horses\b", "wait a minute and be patient"),
    (r"\bcut to the chase\b", "get straight to the point"),
    (r"\bbeat around the bush\b", "talk evasively"),
    (r"\bzip your lip\b", "be quiet"),
    (r"\bthrow (?:someone )?under the bus\b", "betray a teammate"),
    (r"\bunder the weather\b", "feeling unwell"),
    (r"\bpiece of cake\b", "very easy task"),
    (r"\bon the house\b", "free from the shop"),
    (r"\bhit the sack\b", "go to sleep"),
    (r"\bzero rizz\b", "zero charisma"),
    (r"\bno rizz\b", "no charisma"),
    (r"\btouch grass\b", "face reality"),
    (r"\bdeadass\b", "completely serious"),
    (r"\bliving rent[- ]free in (?:my|your|his|her) head\b", "constantly on my mind"),
    (r"\bcaught in 4k\b", "caught red-handed with clear proof"),
    (r"\bdown bad\b", "desperately lovesick"),
    (r"\bmain character energy\b", "protagonist presence"),
    (r"\bplot armor\b", "invulnerable by script"),
    (r"\bvibe check\b", "mood check"),
    (r"\btake the (?:W|w)\b", "win the victory"),
    (r"\btake the (?:L|l)\b", "take the loss"),
    (r"\bcross the line\b", "go too far"),
    (r"\bface the music\b", "accept the consequences"),
    (r"\bcost an arm and a leg\b", "be extremely expensive"),
    (r"\bout of the blue\b", "out of nowhere unexpectedly"),
    (r"\bthrough thick and thin\b", "through good and bad times"),
    (r"\bjump the gun\b", "act too prematurely"),
    (r"\bshoot the breeze\b", "chat casually"),
    (r"\bburn bridges\b", "destroy relationships"),
    (r"\bblessing in disguise\b", "hidden blessing"),
    (r"\brule of thumb\b", "general guideline"),
    (r"\bin a nutshell\b", "in summary"),
    (r"\bsee eye to eye\b", "agree completely"),
    (r"\bwater under the bridge\b", "thing of the past"),
    (r"\bbreak the ice\b", "warm up the atmosphere"),
    (r"\bhit the nail on the head\b", "be completely accurate"),
    # Slang & Idiom Tambahan (Disambiguasi Sebelum Masuk GTX)
    (r"\b(are you )?for real\b", "seriously"),
    (r"\b(you're|you are) dead meat\b", "you are finished"),
    (r"\bdead meat\b", "in deep trouble"),
    (r"\bcut the (crap|bullshit|bs)\b", "stop the nonsense"),
    (r"\b(no way|not a chance) in hell\b", "impossible"),
    (r"\bfreaking out\b", "panicking"),
    (r"\bfreak out\b", "panic"),
    (r"\bmessing with (me|you|us|him|her|them)\b", r"tricking \1"),
    (r"\bfed up with\b", "sick and tired of"),
    (r"\bgo easy on (me|him|her|us|them)\b", r"be gentle with \1"),
    (r"\bwhat (on earth|in the world)\b", "what exactly"),
    (r"\b(are you|you gotta be) kidding (me)?\b", "are you joking"),
    (r"\bmake yourself at home\b", "feel comfortable as at home"),
    (r"\bbite me\b", "screw you"),
    (r"\b(piss|bug) off\b", "go away"),
    (r"\bjust drop it\b", "just forget about it"),
    (r"\bget over it\b", "move on from it"),
    (r"\bhave a crush on\b", "be attracted to"),
    (r"\bflexing\b", "showing off"),
    (r"\brage quit(ting)?\b", "quit in anger"),
    # Gaming & Dungeon Disambiguasi
    (r"\b(pull|draw|taking) aggro\b", "attracting enemy attention"),
    (r"\bspawn points?\b", "appearance location"),
    (r"\bdungeon crawl(er|ing)?\b", "dungeon exploration"),
    (r"\bdungeon break\b", "dungeon outbreak"),
    (r"\braid boss\b", "large-scale boss"),
    (r"\bparty leader\b", "group leader"),
    (r"\bparty members?\b", "group member"),
    (r"\bclear rewards?\b", "quest completion reward"),
    (r"\bepic (?:class|job)\b", "epic tier class"),
    (r"\blegendary job\b", "legendary class"),
    # Stage-1: Exclamation Openers & Interjeksi Pembuka (Cegah "Pria, ..." / "Anak laki-laki, ...")
    (r"^\s*oh\s+man,\s*", "oh gosh, "),
    (r"^\s*man,\s+", "gosh, "),
    (r"^\s*oh\s+boy,\s*", "oh my, "),
    (r"^\s*boy,\s+", "wow, "),
    (r"\bwhat the (?:heck|hell)\b", "what exactly"),
    (r"\bwho the (?:heck|hell)\b", "who exactly"),
    (r"\bwhere the (?:heck|hell)\b", "where exactly"),
    (r"\bhow the (?:heck|hell)\b", "how on earth"),
    (r"\bwhy the (?:heck|hell)\b", "why on earth"),
    (r"\bfor crying out loud\b", "seriously, goodness gracious"),
    (r"\bfor goodness'? sake\b", "for heaven's sake"),
    (r"\bfor pete'?s sake\b", "for heaven's sake"),
    (r"\bno wonder\b", "it is natural that"),
    (r"\bspeaking of which\b", "by the way about that"),
    (r"\bcome to think of it\b", "now that I think about it"),
    (r"\bnow that you mention it\b", "now that I think about it"),
    (r"\bas if!\b", "impossible!"),
    (r"\blike hell i (?:would|will)\b", "I definitely refuse to"),
    (r"\bmy ass!\b", "that is nonsense!"),
    # Stage-1: Phrasal Verbs & Colloquial Idioms (Anti-Calque Harfiah)
    (r"\bknock it off\b", "stop doing that"),
    (r"\bgive it a rest\b", "stop talking about it"),
    (r"\bpassed out cold\b", "fainted unconscious"),
    (r"\bpassed out\b", "fainted unconscious"),
    (r"\bpass out\b", "faint unconscious"),
    (r"\bblacked out\b", "fainted unconscious"),
    (r"\bblack out\b", "faint unconscious"),
    (r"\bhang(ing)? out with\b", "spending time together with"),
    (r"\bhang(ing)? out\b", "spending time together"),
    (r"\bhear (me|him|her|us|them) out\b", r"listen to \1 until the end"),
    (r"\bcheck (this|that|it) out\b", r"look at \1"),
    (r"\bwatch out\b", "be careful"),
    (r"\blook out\b", "be careful"),
    (r"\bin the nick of time\b", "just in time at the critical moment"),
    (r"\bget the hang of (it|this|that)\b", r"get used to mastering \1"),
    (r"\bgot the hang of (it|this|that)\b", r"got used to mastering \1"),
    (r"\bout of (my|your|his|her|our) league\b", r"far beyond \1 level"),
    (r"\bjump(ing)? to conclusions\b", "making hasty assumptions"),
    (r"\bgive it a (?:shot|try|whirl)\b", "try doing it"),
    (r"\bcall(ing)? the shots\b", "in full command"),
    (r"\bno biggie\b", "not a big problem"),
    (r"\bno big deal\b", "not a big problem"),
    (r"\blose track of time\b", "forget the time"),
    (r"\blost track of time\b", "forgot the time"),
    (r"\bdon't rub it in\b", "do not keep teasing about it"),
    (r"\brub(bing)? it in\b", "teasing about the mistake"),
    (r"\bkeep an eye on\b", "watch and guard"),
    (r"\bcatch (my|your|his|her|our) breath\b", r"rest and breathe for a moment"),
    (r"\bhold(ing)? a grudge\b", "keeping resentment"),
    (r"\bpull(ing)? (my|your|his|her) leg\b", r"joking and tricking"),
    (r"\bpull(ed|ing)? a fast one\b", "played a trick"),
    (r"\boff the hook\b", "free from trouble"),
    (r"\bthrow in the towel\b", "surrender and give up"),
    (r"\bthrew in the towel\b", "surrendered and gave up"),
    (r"\bchicken(ed|ing)? out\b", "lost courage and backed out"),
    (r"\bpush(ing)? (your|my|his|her) luck\b", "being too greedy and reckless"),
    (r"\byou asked for it\b", "you brought this upon yourself"),
    (r"\bmean(s)? business\b", "completely serious"),
    (r"\bbuy (some|us|me|them) time\b", "stall for time"),
    (r"\bplay(ing)? dumb\b", "pretending not to know"),
    (r"\bplay(ing)? innocent\b", "pretending to be innocent"),
    (r"\bplay(ing)? hard to get\b", "acting aloof and hard to win"),
    (r"\bthird wheel\b", "awkward extra person on a date"),
    (r"\bhead over heels\b", "deeply in love"),
    (r"\bbutterflies in (my|your|his|her) stomach\b", "feeling very nervous and fluttering"),
    (r"\b(spacing|spaced|zoning|zoned) out\b", "daydreaming blankly"),
    (r"\bspace out\b", "daydream blankly"),
    (r"\b(i'm|i am) all ears\b", "I am listening carefully"),
    (r"\b(my|our) hands are tied\b", "we have no other choice and cannot help"),
    (r"\bslipped my mind\b", "I completely forgot"),
    (r"\bslip of the tongue\b", "accidental spoken mistake"),
    (r"\bdoes that ring a bell\b", "does that sound familiar"),
    (r"\bring(s)? a bell\b", "sound familiar"),
    (r"\bgood[- ]for[- ]nothing\b", "completely useless"),
    (r"\bpain in the (?:neck|ass|butt)\b", "very annoying trouble"),
    (r"\bwrapped around (his|her|your|my) (?:little )?finger\b", "completely obedient to"),
    (r"\bbeat it!\b", "go away right now!"),
    (r"\bscram!\b", "get lost right now!"),
    (r"\bbuzz off!\b", "go away right now!"),
    (r"\bway to go!\b", "great job!"),
    (r"\blong time no see\b", "it has been a long time since we met"),
    (r"\beasier said than done\b", "easy to say but hard to do"),
    (r"\blet it slide\b", "forgive and ignore it this time"),
    (r"\bgot carried away\b", "got too excited"),
    (r"\bget carried away\b", "get too excited"),
    (r"\bgo(ing)? overboard\b", "acting too excessively"),
    (r"\byou have a point\b", "what you say makes sense"),
    (r"\bbeside the point\b", "irrelevant to the main issue"),
    (r"\bon second thought\b", "after thinking about it again"),
    (r"\bfor the time being\b", "for now temporarily"),
    (r"\bout of the question\b", "completely impossible to allow"),
    (r"\bcall it quits\b", "stop and end it now"),
    (r"\blose (my|your|his|her) temper\b", "get angry and lose patience"),
    (r"\blost (my|your|his|her) temper\b", "got angry and lost patience"),
    (r"\bget(s|ting)? on my nerves\b", "making me very annoyed"),
    (r"\bhit(s)? the spot\b", "feels very satisfying and refreshing"),
    (r"\btake a breather\b", "rest for a moment"),
    (r"\bpull(ed|ing)? an all[- ]nighter\b", "stayed awake all night"),
    (r"\bsleep like a log\b", "sleep very deeply"),
    (r"\bout like a light\b", "fast asleep immediately"),
    (r"\bin over (my|your|his|her) head\b", "facing a problem beyond ability"),
    (r"\boff the top of my head\b", "from spontaneous memory"),
    (r"\bby the skin of (my|your|his|her|our) teeth\b", "narrowly by a tiny margin"),
    (r"\bturn(ed|ing)? the tables\b", "reversed the situation"),
    (r"\bread between the lines\b", "understand the hidden meaning"),
    (r"\bin the same boat\b", "in the same difficult situation"),
    (r"\blet the cat out of the bag\b", "accidentally reveal the secret"),
    (r"\badd(ing)? fuel to the fire\b", "making the situation worse"),
    # Stage-1: Spoken English Contractions (Agar Struktur Kalimat Tidak Rusak di GTX)
    (r"\bwhatcha\b", "what are you"),
    (r"\bgotcha\b", "I understand"),
    (r"\blemme\b", "let me"),
    (r"\bgimme\b", "give me"),
    (r"\bdunno\b", "do not know"),
    (r"\bkinda\b", "kind of"),
    (r"\bsorta\b", "sort of"),
    (r"\boutta\b", "out of"),
    (r"\bhafta\b", "have to"),
    (r"\boughta\b", "ought to"),
]
_COMPILED_PRE_GTX_EN_SLANG = [(_re.compile(pat, _re.IGNORECASE), repl) for pat, repl in _PRE_GTX_EN_SLANG_RULES]

_STUTTER_EN_START_RE = _re.compile(r"^(\s*(?:-\s*)?)([A-Za-z])-\2([a-zA-Z]{2,})\b")
_STUTTER_EN_ANY_RE = _re.compile(r"\b([A-Za-z])-\1([a-zA-Z]{2,})\b")


def _preprocess_stutter_en(text: str):
    """Deteksi dan bersihkan gagap bahasa Inggris (mis. 'W-What?!' -> 'What?!') sebelum masuk GTX.
    Mengembalikan tuple (clean_text, had_leading_stutter)."""
    if not text:
        return text, False
    had_leading = bool(_STUTTER_EN_START_RE.search(text))
    cleaned = _STUTTER_EN_ANY_RE.sub(lambda m: m.group(1) + m.group(2), text)
    return cleaned, had_leading


def _postprocess_stutter_id(orig_en: str, translated_id: str) -> str:
    """Jika teks sumber bahasa Inggris memiliki gagap di awal kalimat ('W-What?!', 'S-Stop!'),
    pasangkan kembali awalan gagap bahasa Indonesia yang sesuai ('A-Apa?!', 'B-Berhenti!')."""
    if not orig_en or not translated_id:
        return translated_id
    if not _STUTTER_EN_START_RE.search(orig_en):
        return translated_id
    # Jangan gandakan jika sudah memiliki gagap (misal 'A-Apa')
    if _re.match(r"^\s*(?:-\s*)?[A-Za-z]-[A-Za-z]", translated_id):
        return translated_id
    m = _re.match(r"^(\s*(?:-\s*)?)([A-Za-z])([a-zA-Z]{1,})(.*)$", translated_id, _re.DOTALL)
    if not m:
        return translated_id
    prefix, first_char, rest_word, tail = m.group(1), m.group(2), m.group(3), m.group(4)
    return f"{prefix}{first_char}-{first_char}{rest_word}{tail}"


def _pre_normalize_en_slang(text: str) -> str:
    """Pra-pemrosesan teks sumber bahasa Inggris sebelum masuk ke Google Translate (GTX).
    Menggantikan idiom dan slang bahasa Inggris ambigu yang sering rusak saat diterjemahkan mesin."""
    if not text:
        return text
    result, _ = _preprocess_stutter_en(text)
    for rx, repl in _COMPILED_PRE_GTX_EN_SLANG:
        result = rx.sub(repl, result)
    return result

# Aturan universal: selalu dikoreksi (karena merupakan blunder/calque harfiah).
_UNIVERSAL_FANSUB_RULES = [
    (r"\bapakah kamu\b", "kamu"),
    (r"\bapakah kau\b", "kamu"),
    (r"\bapakah anda\b", "Anda"),
    (r"\bapakah dia\b", "dia"),
    (r"\bapakah mereka\b", "mereka"),
    (r"\bapakah kita\b", "kita"),
    (r"\bapakah ini\b", "ini"),
    (r"\bapakah itu\b", "itu"),
    (r"\bapakah ada\b", "ada"),
    (r"\bapakah bisa\b", "bisa"),
    (r"\bapakah benar\b", "beneran"),
    (r"\bapakah sungguh\b", "beneran"),
    (r"\bterkutuklah\b", "sial"),
    (r"\bbawalah itu\b", "sini maju"),
    (r"\bpenjara bawah tanah\b", "dungeon"),
    (r"\bserikat petualang\b", "guild petualang"),
    (r"\bbanjir tinggi\b", "incaranmu tinggi juga"),
    (r"\bsangat embarrassing\b", "memalukan banget"),
    (r"\bembarrassing\b", "memalukan"),
    (r"\bdiharamkan masuk\b", "dilarang masuk"),
    (r"\bdi mata pertama\b", "pada pandangan pertama"),
    (r"\bmata pertama\b", "pandangan pertama"),
    (r"\bngeplug\b", "menutup"),
    (r"\bngegoblok\b", "bertingkah konyol"),
    (r"\bkelewatan satu sama lain\b", "berpapasan"),
    (r"\bberapa curiga itu\b", "mencurigakan banget, kan"),
    (r"\bberapa curiganya\b", "mencurigakan"),
    (r"\bberapa curiga\b", "mencurigakan"),
    (r"\bberapa lama aku keluar\b", "berapa lama aku pingsan"),
    (r"\bduit jahat\b", "untung besar"),
    (r"\buang jahat\b", "untung besar"),
    (r"\bdengan kecepatan kayak gini\b", "kalau begini terus"),
    (r"\btinggalkan wajah\b", "terlepas dari wajah"),
    (r"\bbasis rahasia\b", "markas rahasia"),
    (r"\blihat\? katanya\b", "tuh, kan! Apa kubilang"),
    (r"\bkatanya\! kamu harus santai\b", "apa kubilang! Kamu harus santai"),
    (r"\bngomong balas\b", "membantah"),
    (r"\bbertembung kepala\b", "berselisih"),
    (r"\bbertembung\b", "bentrok"),
    (r"\bberputus di neraka\b", "mampus di neraka"),
    (r"\banjing campuran\b", "anjing buduk"),
    (r"\bkemarahan kerajaan\b", "mengamuk hebat"),
    (r"\bngelakuin luka\b", "melukai"),
    (r"\bmenghapus anda\b", "menghabisi Anda"),
    (r"\bmenghapus kamu\b", "menghabisi kamu"),
    (r"\bpenipu optik\b", "umpan optik"),
    (r"\bkorpul\b", "kopral"),
    (r"\bsanggah, ma'am\b", "siap, Ma'am"),
    (r"\bsanggah, sir\b", "siap, Sir"),
    (r"\bkalian ngapain ngapain\b", "kalian ngerjain aku ya"),
    (r"\bgak ada cara aku ngelakuin itu\b", "mana sudi aku ngelakuin itu"),
    (r"\bgak ada cara aku ngelakuin\b", "mana sudi aku ngelakuin"),
    (r"\bdasar kau pervert\b", "dasar mesum"),
    (r"\bdasar kamu pervert\b", "dasar mesum"),
    (r"\bkau pervert\b", "dasar mesum"),
    (r"\bkamu pervert\b", "dasar mesum"),
    (r"\bpervert\b", "mesum"),
    (r"\bpembunuh anak kecil\b", "pembunuh kekanak-kanakan"),
    (r"\bsatu-satunya jahat yang tersisa\b", "satu-satunya penjahat yang tersisa"),
    (r"\bsatu-satunya jahat\b", "satu-satunya penjahat"),
    (r"\bmelihatmu dieksekusi\b", "memastikanmu dieksekusi"),
    (r"\blantai bawah dua\b", "lantai bawah tanah kedua"),
    (r"\bmorgue\b", "kamar jenazah"),
    (r"\bjangan bilang itu di luar\b", "jangan katakan itu keras-keras"),
    (r"\bngelupas blok\b", "menerobos blok"),
    (r"\bngeliat di depan aku\b", "menjulang di depanku"),
    (r"\bngeliat di depanku\b", "menjulang di depanku"),
    (r"\bdi kolam darah\b", "bersimbah darah"),
    (r"\bterbaring di kolam darah\b", "terbaring bersimbah darah"),
    (r"\bdisayat sampai mati\b", "ditusuk sampai mati"),
    (r"\bmenegaskan nasib kita\b", "menentukan nasib kita"),
    (r"\bmenegaskan nasib\b", "menentukan nasib"),
    (r"\btutup nasib kita\b", "menentukan nasib kita"),
    (r"\btutup nasib\b", "menentukan nasib"),
    (r"\bmenegaskan begitu banyak hantu\b", "menyegel begitu banyak hantu"),
    (r"\bmenegaskan banyak hantu\b", "menyegel banyak hantu"),
    (r"\btutup banyak hantu\b", "menyegel banyak hantu"),
    (r"\bngendang roh jahat supaya tidur\b", "menenangkan roh jahat"),
    (r"\bngendang roh\b", "menenangkan roh"),
    (r"\bkucing takut\b", "penakut"),
    (r"\bkumpulin diri\b", "kuatkan dirimu"),
    (r"\byang gema di lorong\b", "yang bergema di lorong"),
    (r"\bsemua unit, segera keluar\b", "semua unit, segera meluncur"),
    (r"\bsegera keluar bertempur\b", "segera meluncur"),
    (r"\bambil tindakan menghindar\b", "lakukan manuver menghindar"),
    (r"\bterkena pukulan langsung\b", "terkena tembakan langsung"),
    (r"\bpukulan langsung ke\b", "tembakan telak ke"),
    (r"\bsistem peluncuran darurat\b", "sistem ejeksi darurat"),
    (r"\btembak sesuai keinginan\b", "bebas tembak"),
    (r"\bsemua bersorak britannia\b", "hidup Britannia"),
    (r"\btertangkap dalam tembakan silang\b", "terjebak dalam baku tembak"),
    (r"\btundukkan tanpa syarat\b", "menyerahlah tanpa syarat"),
    (r"\bdi perut binatang\b", "di sarang musuh"),
    (r"\bmenari langsung ke jebakan\b", "masuk langsung ke jebakan"),
    (r"\bmenari tepat ke perangkap\b", "masuk tepat ke perangkap"),
    (r"\bmenari ke perangkap\b", "masuk ke perangkap"),
    (r"\bmenari tepat ke jebakan\b", "masuk tepat ke jebakan"),
    (r"\bmenari ke jebakan\b", "masuk ke jebakan"),
    (r"\bmemegang tali\b", "mengendalikan semuanya"),
    (r"\bwarga harta karun\b", "warga kehormatan"),
    (r"\bcheckmate\b", "skakmat"),
    (r"\bCheckmate\b", "Skakmat"),
    (r"\bklub classic lit\b", "Klub Sastra Klasik"),
    (r"\bKlub Classic Lit\b", "Klub Sastra Klasik"),
    (r"\bdatang buat ngelamun\b", "datang untuk memberi salam"),
    (r"\bpeeping tom\b", "tukang intip"),
    (r"\bPeeping Tom\b", "tukang intip"),
    (r"\bwaktu cekout di perpustakaan\b", "masa peminjaman di perpustakaan"),
    (r"\bwaktu cekout\b", "masa peminjaman"),
    (r"\bpunya lidah tajam\b", "mulutnya cukup pedas"),
    (r"\blidah yang tajam\b", "mulut yang pedas"),
    (r"\blidah tajam\b", "mulut pedas"),
    (r"\bresmi mati\b", "dinyatakan meninggal"),
    (r"\bfavor pribadi\b", "permintaan pribadi"),
    (r"\bseluruh tubuh siswa\b", "seluruh siswa"),
    (r"\btubuh siswa\b", "para siswa"),
    (r"\bdomba korban\b", "tumbal"),
    (r"\bpara punks\b", "berandalan"),
    (r"\banthologi\b", "antologi"),
    (r"\bAnthologi\b", "Antologi"),
    (r"\bsetelah semua, marah\b", "lagipula, marah"),
    (r"\bsetelah semua\b", "lagipula"),
    (r"\bSetelah semua\b", "Lagipula"),
    (r"\bjam periode kelima\b", "jam kelima"),
    (r"\bperiode kelima\b", "jam kelima"),
    (r"\bbath open-air-nya\b", "pemandian terbukanya"),
    (r"\bbath open-air\b", "pemandian terbuka"),
    (r"\blayarnya kertas\b", "pintu geser kertas"),
    (r"\blayar kertas\b", "pintu geser kertas"),
    (r"\bbikin kudetas\b", "bikin merinding"),
    (r"\btransom kayu\b", "ventilasi kayu"),
    (r"\border up\b", "pesanan siap"),
    (r"\bOrder up\b", "Pesanan siap"),
    (r"\bgak banyak juga\b", "bukan apa-apa kok"),
    (r"\bpencurilah kapal\b", "jarahlah kapal"),
    (r"\bpencuri kapal\b", "penjarah kapal"),
    (r"\bngelamun dan memohon\b", "berlutut dan memohon"),
    (r"\bKeren banget\.\.\. Itu yang bakal dikatakan Shinomiya\b", "Manis sekali... Itu yang bakal dikatakan Shinomiya"),
    (r"\bkeren banget\.\.\. itu yang bakal dikatakan\b", "manis sekali... itu yang bakal dikatakan"),
    (r"\brouge ninjas\b", "Ninja Pelarian"),
    (r"\brouge ninja\b", "Ninja Pelarian"),
    (r"\bninja art:\b", "Jutsu:"),
    (r"\bNinja Art:\b", "Jutsu:"),
    (r"\btipe orochimaru\b", "antek Orochimaru"),
    (r"\bTipe Orochimaru\b", "Antek Orochimaru"),
    (r"\bsekali seumur hidup\.\.\.permintaanku\b", "permintaan sekali seumur hidupku"),
    (r"\btolong bawakan sasuke kembali\b", "tolong bawa Sasuke kembali"),
    (r"\bTolong bawakan Sasuke kembali\b", "Tolong bawa Sasuke kembali"),
    (r"\bdesa daun tersembunyi\b", "Desa Konoha"),
    (r"\bDesa Daun Tersembunyi\b", "Desa Konoha"),
    (r"\bdesa daun\b", "Desa Konoha"),
    (r"\bDesa Daun\b", "Desa Konoha"),
    (r"\bpencinta pertarungan\b", "Fighting Dreamers"),
    (r"\bPencinta Pertarungan\b", "Fighting Dreamers"),
    (r"\bjalur berkendara\b", "garis lurus"),
    (r"\bkembali ke bentuk semula\b", "kembali ke wujud semula"),
    (r"\bkena terbentur\b", "terkena serangan"),
    (r"\bseperti yang diharapkan\b", "sudah kuduga"),
    (r"\bSeperti yang diharapkan\b", "Sudah kuduga"),
    (r"\bmemutuskan yang mana kata sandi\b", "menentukan kata sandinya"),
    (r"\blayar stevenson\b", "kotak Stevenson"),
    (r"\bLayar Stevenson\b", "Kotak Stevenson"),
    (r"\bjujutsu tech\b", "SMK Jujutsu"),
    (r"\bJujutsu Tech\b", "SMK Jujutsu"),
    (r"\bpendeta yang korup\b", "pendeta bejat"),
    (r"\bPendeta yang korup\b", "Pendeta bejat"),
    (r"\bsekarang, sekarang, frieren\b", "sudahlah, Frieren"),
    (r"\bSekarang, sekarang, Frieren\b", "Sudahlah, Frieren"),
    (r"\bsekarang, sekarang\b", "sudahlah"),
    (r"\bSekarang, sekarang\b", "Sudahlah"),
    (r"\bkita bilang dia jebakan\b", "kan udah dibilang itu jebakan"),
    (r"\btuan tanah orochimaru\b", "antek Orochimaru"),
    (r"\btinggalkan aku sendiri\b", "jangan ganggu aku"),
    (r"\bTinggalkan aku sendiri\b", "Jangan ganggu aku"),
    (r"\bmembuat guru kita kabur demi uangnya\b", "memberikan perlawanan sengit kepada guru kita"),
    (r"\bkabur demi uangnya\b", "memberikan perlawanan sengit"),
    (r"\bberikan mereka neraka\b", "hajar mereka"),
    (r"\bBerikan mereka neraka\b", "Hajar mereka"),
    (r"\bmengirim lawannya menyerang setiap tahun\b", "membuat lawannya pulang tertunduk setiap tahun"),
    (r"\bmengirim lawannya menyerang\b", "membuat lawannya pulang tertunduk"),
    (r"\baku akan menyerahkannya padamu, raja pedang\b", "harus kuakui kehebatanmu, Raja Pedang"),
    (r"\baku akan menyerahkannya padamu, sword lord\b", "harus kuakui kehebatanmu, Sword Lord"),
    (r"\bsetiap kedua\b", "setiap detik"),
    (r"\bSetiap kedua\b", "Setiap detik"),
    (r"\biblis tuhan\b", "Raja Iblis"),
    (r"\bIblis Tuhan\b", "Raja Iblis"),
    (r"\bnaga berat\b", "Heavy Dragon"),
    (r"\bNaga Berat\b", "Naga Lapis Baja"),
    (r"\bpenguasa bawahan keluarga\b", "tuan feodal keluarga"),
    (r"\bsungguh pengalaman yang luar biasa dari masa lalu\b", "bikin bernostalgia banget"),
    (r"\bSangat kuat! Gunakan Pengganti\b", "Steely! Gunakan Substitute"),
    (r"\bSangat kuat! Gunakan\b", "Steely! Gunakan"),
    (r"\bruang bawah tanah peringkat ([A-Za-z0-9]+)\b", r"dungeon peringkat \1"),
    (r"\bruang bawah tanah peringkat-([A-Za-z0-9]+)\b", r"dungeon peringkat-\1"),
    (r"\bmenjelajahi ruang bawah tanah\b", "menjelajahi dungeon"),
    (r"\bmenaklukkan (\d+|satu|dua|tiga|empat|lima) ruang bawah tanah\b", r"menaklukkan \1 dungeon"),
    (r"\bmenaklukkan ruang bawah tanah\b", "menaklukkan dungeon"),
    (r"\bmenantang satu ruang bawah tanah lagi\b", "menantang satu dungeon lagi"),
    (r"\bmenantang ruang bawah tanah\b", "menantang dungeon"),
    (r"\bmenyelesaikan ruang bawah tanah\b", "menyelesaikan dungeon"),
    (r"\bbos ruang bawah tanah\b", "bos dungeon"),
    (r"\bmonster ruang bawah tanah\b", "monster dungeon"),
    (r"\blantai ruang bawah tanah\b", "lantai dungeon"),
    (r"\bmengulangi perintah itu\.\s*dungeon\b", "mengulang dungeon"),
    (r"\buntuk pesta itu\b", "untuk party"),
    (r"\bapakah sedang mengisi daya\b", "apakah dia sedang mengumpulkan kekuatan"),
    (r"\bsedang mengisi daya\b", "sedang mengumpulkan kekuatan"),
    (r"\bparty yang dimiliki oleh\b", "party tempat bergabungnya"),
    (r"\bpanggilanku tidak bisa digunakan untuk bertarung\b", "monster summon-ku sedang bertarung"),
    (r"\btanpa panggilan itu\b", "tanpa monster summon itu"),
    (r"\bmelakukan casting di depan\b", "merapal sihir di depan"),
    (r"\bmelakukan casting\b", "merapal sihir"),
    (r"\bmelakukan cast\b", "merapal sihir"),
    (r"\bcasting di depan orang\b", "merapal sihir di depan orang"),
    (r"\bcasting seal\b", "segel sihir"),
    (r"\btinta sulap\b", "tinta sihir"),
    (r"\btoko alat tulis ajaib\b", "toko alat sihir"),
    (r"\bcelah di tongkat\b", "retakan di tongkat"),
    (r"\bmenjadi magang penyihir\b", "menjadi murid penyihir"),
    (r"\bmenjadi magang\b", "menjadi murid sihir"),
    (r"\bmemilih ramuan mahkota\b", "memetik herba mahkota"),
    (r"\bmemilih ramuan\b", "memetik herba"),
    (r"\bramuan mahkota\b", "herba mahkota"),
    (r"\bpersetujuan mahkota\b", "Ujian Mahkota"),
    (r"\bpegasus carriage\b", "kereta Pegasos"),
    (r"\bsangat baik andal\b", "sangat mantap"),
    (r"\btidak ada yang perlu ditakutkan of\b", "tidak ada yang perlu ditakuti"),
    (r"\bperlu ditakutkan of\b", "perlu ditakuti"),
    (r"\bditakutkan of\b", "ditakuti"),
    (r"\btiketnya terjual habis dalam waktu singkat\b", "langsung ludes dalam sekejap"),
    (r"\bterjual habis dalam waktu singkat\b", "langsung ludes dalam sekejap"),
    (r"\bterjual habis dalam sekejap\b", "langsung ludes dalam sekejap"),
    (r"\btak punya apa pun untuk ditawarkan di dunia sihir\b", "tak punya tempat di dunia sihir"),
    (r"\btidak punya apa pun untuk ditawarkan di dunia sihir\b", "tidak punya tempat di dunia sihir"),
    (r"\btidak memiliki apa pun untuk ditawarkan di dunia sihir\b", "tidak punya tempat di dunia sihir"),
    (r"\baku bertanggung jawab atas berdirinya di dekat pintu\b", "salahku sendiri kok berdiri di dekat pintu"),
    (r"\bbertanggung jawab atas berdirinya di dekat pintu\b", "salah sendiri kok berdiri di dekat pintu"),
    (r"\bdi sini untuk mengambil pesanan\b", "mau ambil pesanan"),
    (r"\banda pikir anda bisa memperbaikinya\b", "kamu rasa kamu bisa memperbaikinya"),
    (r"\bapakah anda berpikir anda bisa\b", "apa kamu rasa kamu bisa"),
    # Kamus Idiom & Ungkapan Fansub Anime Universal
    (r"\bberi aku istirahat\b", "yang benar saja"),
    (r"\bitu melayanimu dengan benar\b", "rasakan itu"),
    (r"\bitu melayanimu dengan pas\b", "rasakan itu"),
    (r"\bmelayanimu dengan benar\b", "rasakan itu"),
    (r"\bmelayanimu dengan pas\b", "rasakan itu"),
    (r"\bitu melayanimu\b", "rasakan itu"),
    (r"\bitu tidak bisa ditolong\b", "mau bagaimana lagi"),
    (r"\btak bisa ditolong\b", "mau bagaimana lagi"),
    (r"\baku akan merawat ini\b", "biar aku yang urus ini"),
    (r"\baku akan merawatnya\b", "biar aku yang urus"),
    (r"\bmerawat ini\b", "mengurus ini"),
    (r"\bjangan biarkan penjagamu turun\b", "jangan lengah"),
    (r"\bmenurunkan penjagamu\b", "lengah"),
    (r"\bmenurunkan penjaga\b", "lengah"),
    (r"\bperhatikan punggungmu\b", "waspadalah di belakangmu"),
    (r"\bberdiri kembali\b", "mundur"),
    (r"\bkembali ke bawah\b", "mundur"),
    (r"\bkamu lagi memukulku\b", "kamu lagi merayuku ya"),
    (r"\blagi memukulku\b", "lagi menggodaku"),
    (r"\bjangan sombong ayam\b", "jangan besar kepala"),
    (r"\bbentuk pikiranmu\b", "tentukan pilihanmu"),
    (r"\bperubahan hati\b", "berubah pikiran"),
    (r"\baku tidak bisa mengambilnya lagi\b", "aku sudah tidak tahan lagi"),
    (r"\bmenyeberangi pikiranku\b", "terlintas di pikiranku"),
    (r"\bsimpan untuk dirimu sendiri\b", "rahasiakan ini"),
    (r"\bdi atas tubuh matiku\b", "langkahi dulu mayatku"),
    (r"\bsiapa yang mengisi daya\b", "siapa penanggung jawabnya"),
    (r"\bgigit lidahmu\b", "jaga ucapanmu"),
    (r"\bputar mata buta\b", "tutup mata"),
    (r"\bkaki dingin\b", "ciut nyali"),
    (r"\bdi atas rumah\b", "gratis dari kedai"),
    (r"\baturan jempol\b", "pedoman umum"),
    (r"\bambil untuk diberikan\b", "menganggap remeh"),
    (r"\bpotong itu\b", "hentikan itu"),
    (r"\bsepotong kue\b", "gampang banget"),
    (r"\bhilang dalam pikiran\b", "melamun"),
    (r"\btumpahkan kacang\b", "bocorkan rahasianya"),
    (r"\btumpahkan teh\b", "ceritakan gosipnya"),
    (r"\bdi air panas\b", "dalam masalah besar"),
    (r"\bdi bawah cuaca\b", "kurang enak badan"),
    (r"\bmenghadapi musik\b", "menanggung akibatnya"),
    (r"\bgigit peluru\b", "tabahkan dirimu"),
    (r"\bbicara tentang iblis\b", "panjang umur, baru diomongin"),
    (r"\bpukul paku di kepala\b", "tepat sasaran"),
    (r"\bmemukul semak-semak\b", "berbelit-belit"),
    (r"\bpatahkan kaki\b", "semoga sukses"),
    (r"\bbiaya lengan dan kaki\b", "harganya selangit"),
    (r"\bkeluar dari tangan\b", "lepas kendali"),
    (r"\bgantung di sana\b", "bertahanlah"),
    (r"\btarik kaki\b", "mengerjai"),
    (r"\bdi bawah hidungmu\b", "tepat di depan matamu"),
    (r"\bkehilangan kesejukan\b", "hilang kesabaran"),
    (r"\bambil dengan mudah\b", "santai saja"),
    (r"\bhitung aku masuk\b", "aku ikut"),
    (r"\bhitung aku keluar\b", "aku nggak ikut"),
    (r"\bbukan di jam tanganku\b", "tidak akan kubiarkan"),
    (r"\bdapatkan pegangan\b", "sadarlah"),
    (r"\btundukkan kepalamu\b", "tiarap"),
    (r"\btanpa pelanggaran\b", "tanpa mengurangi rasa hormat"),
    (r"\btidak ada pelanggaran\b", "tanpa mengurangi rasa hormat"),
    (r"\btidak diambil\b", "santai saja"),
    (r"\bmiliki punggungku\b", "lindungi punggungku"),
    (r"\bmenyeberangi garis\b", "melampaui batas"),
    (r"\bjangan menyanjung dirimu\b", "jangan kepedean"),
    (r"\bbukan bisnis anda\b", "bukan urusanmu"),
    (r"\bbukan bisnis kamu\b", "bukan urusanmu"),
    (r"\burus bisnismu sendiri\b", "urus urusanmu sendiri"),
    (r"\bambil waktumu\b", "santai saja, jangan terburu-buru"),
    (r"\bmaju ke depan\b", "silakan"),
    (r"\btepat pergi\b", "sekarang juga"),
    (r"\bsemua tiba-tiba\b", "tiba-tiba"),
    (r"\bpada akhirnya panjang\b", "setelah penantian panjang"),
    (r"\bhal pertama di pagi hari\b", "pagi-pagi buta"),
    (r"\btidur di atasnya\b", "pikirkan matang-matang besok"),
    (r"\bkembali ke kotak satu\b", "mulai dari awal lagi"),
    # Kamus Idiom & Slang Calque (Hasil Terjemahan Harfiah Google Translate)
    (r"\bharus memantul\b", "harus cabut"),
    (r"\btidak ada batasan,\s*itu\b", "beneran, itu"),
    (r"\btidak ada topi,\s*itu\b", "beneran, itu"),
    (r"\btidak ada topi\b", "beneran"),
    (r"\bbukan topi\b", "beneran"),
    (r"\baku turun untuk itu\b", "aku ikut"),
    (r"\baku turun untuk\b", "aku mau"),
    (r"\bsaya kecewa karena itu\b", "aku setuju dengan itu"),
    (r"\bmendingin keluar\b", "santai dulu"),
    (r"\bdisimpan oleh belnya\b", "selamat di saat kritis"),
    (r"\bdisimpan oleh bel\b", "selamat di saat kritis"),
    (r"\bdiselamatkan oleh bel\b", "selamat di saat kritis"),
    (r"\bsudah dimuntahkan\b", "cepat katakan"),
    (r"\bkeluarkan ludahmu\b", "cepat katakan"),
    (r"\bludahkan itu\b", "cepat katakan"),
    (r"\bpegang kudamu\b", "sabar dulu"),
    (r"\btahan kudamu\b", "tunggu sebentar"),
    (r"\bambil cek hujan\b", "lain kali saja"),
    (r"\btidak mendapat rimpang\b", "tidak punya pesona"),
    (r"\btanpa rimpang\b", "tidak punya pesona"),
    (r"\bnol rizz\b", "tidak punya karisma"),
    (r"\bsentuh rumput\b", "sadar realita"),
    (r"\bhubungi kenyataan\b", "sadar realita"),
    (r"\bkeluar dari biru\b", "tiba-tiba"),
    (r"\bmelalui tebal dan tipis\b", "dalam suka dan duka"),
    (r"\bmembakar jembatan\b", "memutus hubungan"),
    (r"\bmenembak angin\b", "mengobrol santai"),
    (r"\blempar ke bawah bus\b", "mengorbankan kawan"),
    (r"\bmelempar ke bawah bus\b", "mengorbankan kawan"),
    (r"\bdalam kulit kacang\b", "singkatnya"),
    (r"\bpotong untuk mengejar\b", "langsung ke intinya"),
    (r"\bberkah dalam penyamaran\b", "berkah tersembunyi"),
    (r"\bmelihat mata ke mata\b", "sependapat"),
    (r"\bair di bawah jembatan\b", "yang lalu biarlah berlalu"),
    (r"\bmemecahkan es\b", "mencairkan suasana"),
    (r"\bbaju besi plot\b", "kebal berkat skenario"),
    (r"\benergi karakter utama\b", "aura protagonis"),
    (r"\bhidup bebas sewa di kepalaku\b", "selalu terngiang di kepalaku"),
    (r"\bhidup bebas sewa\b", "selalu terngiang-ngiang"),
    (r"\bpantat mati\b", "bener-bener serius"),
    (r"\btertangkap di 4k\b", "tertangkap basah ada buktinya"),
    (r"\bturun buruk\b", "ngenes banget"),
    (r"\bpemeriksaan getaran\b", "cek suasana"),
    (r"\bmengambil w\b", "meraih kemenangan"),
    (r"\bambil w\b", "raih kemenangan"),
    (r"\bmengambil l\b", "menelan kekalahan"),
    (r"\bambil l\b", "telan kekalahan"),
    (r"\bbos penjara bawah tanah\b", "bos dungeon"),
    (r"\btuan serikat\b", "ketua guild"),
    (r"\bbersihkan pesta\b", "seluruh party gugur"),
    (r"\btingkat penurunan\b", "drop rate"),
    (r"\bkolam mana\b", "cadangan mana"),
    (r"\bperiode pendinginan\b", "waktu cooldown"),
    (r"\bsatu tembakan mati\b", "sekali serang tewas"),
    (r"\bsebut itu hari\b", "sudahi dulu hari ini"),
    (r"\bsebut itu sehari\b", "sudahi dulu hari ini"),
    (r"\bpanggil itu sehari\b", "sudahi dulu hari ini"),
    (r"\bpukul karung\b", "pergi tidur"),
    (r"\bmemukul karung\b", "pergi tidur"),
    (r"\bjangan berkeringat\b", "jangan dipikirkan"),
    (r"\bburukku\b", "salahku"),
    # Istilah Game, RPG, Dungeon & Eksplorasi
    (r"\binti ruang bawah tanah\b", "inti dungeon"),
    (r"\binti penjara bawah tanah\b", "inti dungeon"),
    (r"\bjebakan ruang bawah tanah\b", "jebakan dungeon"),
    (r"\bgerbang ruang bawah tanah\b", "gerbang dungeon"),
    (r"\bgerbang penjara bawah tanah\b", "gerbang dungeon"),
    (r"\bledakan ruang bawah tanah\b", "dungeon break"),
    (r"\bkebobolan ruang bawah tanah\b", "dungeon break"),
    (r"\bpenjelajahan ruang bawah tanah\b", "eksplorasi dungeon"),
    (r"\bpenjelajah ruang bawah tanah\b", "penjelajah dungeon"),
    (r"\bruang bawah tanah tingkat ([A-Za-z0-9]+)\b", r"dungeon tingkat \1"),
    (r"\bruang bawah tanah level ([A-Za-z0-9]+)\b", r"dungeon level \1"),
    (r"\bmasuk ke ruang bawah tanah\b", "masuk ke dungeon"),
    (r"\bkeluar dari ruang bawah tanah\b", "keluar dari dungeon"),
    (r"\bruang bos\b", "boss room"),
    (r"\bkamar bos\b", "boss room"),
    # Party, Guild & Peran Tempur
    (r"\bpesta penyerbuan\b", "party raid"),
    (r"\bpesta petualang\b", "party petualang"),
    (r"\banggota pesta\b", "anggota party"),
    (r"\bpemimpin pesta\b", "party leader"),
    (r"\bketua pesta\b", "party leader"),
    (r"\bmembubarkan pesta\b", "membubarkan party"),
    (r"\bpesta bubar\b", "party bubar"),
    (r"\bbergabung dengan pesta\b", "bergabung dengan party"),
    (r"\bbergabung ke pesta\b", "bergabung ke party"),
    (r"\bmencari pesta\b", "mencari party"),
    (r"\bmembentuk pesta\b", "membentuk party"),
    (r"\bkartu serikat\b", "kartu guild"),
    (r"\banggota serikat\b", "anggota guild"),
    (r"\bmisi serikat\b", "misi guild"),
    (r"\bpapan serikat\b", "papan misi guild"),
    (r"\bstaf serikat\b", "resepsionis guild"),
    (r"\bpegawai serikat\b", "resepsionis guild"),
    # Mekanik Pertarungan & Game Stats
    (r"\bmenarik kebencian\b", "menarik aggro"),
    (r"\bmengambil kebencian\b", "mengambil aggro"),
    (r"\bkehilangan kebencian\b", "kehilangan aggro"),
    (r"\btitik bertelur\b", "titik spawn"),
    (r"\btitik kemunculan\b", "titik spawn"),
    (r"\btitik bibit\b", "titik spawn"),
    (r"\bwaktu pendinginan\b", "waktu cooldown"),
    (r"\bmasa pendinginan\b", "waktu cooldown"),
    (r"\btingkat drop\b", "drop rate"),
    (r"\bbarang penurunan\b", "drop item"),
    (r"\bbarang drop\b", "item drop"),
    (r"\btetesan monster\b", "drop item monster"),
    (r"\bbilah kesehatan\b", "bar HP"),
    (r"\bpoin kesehatan\b", "HP"),
    (r"\btitik hit\b", "HP"),
    (r"\bbilah mana\b", "bar MP"),
    (r"\bpoin mana\b", "MP"),
    (r"\bbos serbuan\b", "raid boss"),
    (r"\bbos penyerbuan\b", "raid boss"),
    (r"\bjendela negara bagian\b", "jendela status"),
    (r"\bpohon keterampilan\b", "skill tree"),
    (r"\bpoin keterampilan\b", "skill point"),
    (r"\bpemburu peringkat ([SABCDE])\b", r"hunter rank \1"),
    (r"\bpemburu peringkat-([SABCDE])\b", r"hunter rank-\1"),
    (r"\bpemburu kelas ([SABCDE])\b", r"hunter kelas \1"),
    (r"\bpemain tunggal\b", "pemain solo"),
    (r"\bpemburu tunggal\b", "hunter solo"),
    (r"\bpembunuh pemain\b", "player killer"),
    (r"\bpermainan kematian\b", "death game"),
    (r"\bpenggemar status\b", "buff status"),
    (r"\bdiberi penggemar\b", "diberi buff"),
    (r"\bmendapat penggemar\b", "mendapat buff"),
    # Calque Harfiah Terjemahan Mesin (Anti-Terjemahan Kaku)
    (r"\bapakah kamu nyata\b", "beneran nih"),
    (r"\bkamu nyata\b", "kamu serius"),
    (r"\btidak ada cara di neraka\b", "mana mungkin"),
    (r"\btak ada cara di neraka\b", "mana mungkin"),
    (r"\bpotong omong kosong\b", "hentikan omong kosongmu"),
    (r"\bpotong kotoran itu\b", "jangan banyak omong"),
    (r"\bkamu daging mati\b", "mampus kau"),
    (r"\bdaging mati\b", "habis riwayatmu"),
    (r"\bketakutan keluar\b", "panik banget"),
    (r"\bkacau denganku\b", "mengerjaiku"),
    (r"\bkacau dengan aku\b", "mengerjaiku"),
    (r"\bdiberi makan dengan\b", "muak dengan"),
    (r"\bsudah diberi makan dengan\b", "sudah muak dengan"),
    (r"\bpergi mudah padaku\b", "jangan kejam-kejam ya"),
    (r"\bpergi mudah pada saya\b", "jangan kejam-kejam ya"),
    (r"\bapa di bumi\b", "sebenarnya apa"),
    (r"\bbuat dirimu di rumah\b", "anggap saja rumah sendiri"),
    (r"\bmerasa seperti di rumah\b", "anggap rumah sendiri"),
    (r"\bgigit aku\b", "persetan"),
    (r"\bjatuhkan itu\b", "sudahlah, lupakan saja"),
    (r"\batasi itu\b", "ikhlaskan saja"),
    (r"\bmelenturkan otot\b", "pamer kekuatan"),
    (r"\bberhenti melenturkan\b", "jangan pamer"),
    (r"\bkeluar dalam kemarahan\b", "keluar sambil ngamuk"),
    (r"\bkeluar karena marah\b", "cabut gara-gara emosi"),
    (r"\bhadiah yang jelas\b", "hadiah penyelesaian misi"),
    (r"\bkelas yang hebat\b", "kelas epik"),
    (r"\bpekerjaan yang luar biasa\b", "pekerjaan kelas epik"),

    # --- 16. Koreksi Terjemahan Kaku Literal (Calque Fixes) & Idiom Inggris ---
    (r"\bmembuat masuk akal\b", "masuk akal"),
    (r"\btidak membuat masuk akal\b", "tidak masuk akal"),
    (r"\bmembuat rasa\b", "masuk akal"),
    (r"\bambil perhatian\b", "hati-hati"),
    (r"\bambil hati-hati\b", "hati-hati"),
    (r"\bambil waktumu\b", "santai saja, tidak usah buru-buru"),
    (r"\bambil waktu anda\b", "silakan santai saja"),
    (r"\bmemegang kembali\b", "menahan diri"),
    (r"\bjangan memegang kembali\b", "jangan menahan diri"),
    (r"\bberdiri kembali\b", "mundur"),
    (r"\bmelangkah kembali\b", "mundur"),
    (r"\bmemanggil tembakan\b", "memegang kendali"),
    (r"\bmemanggil semua tembakan\b", "memegang semua keputusan"),
    (r"\bmengambil kesempatan\b", "mencoba peruntungan"),
    (r"\bmemberinya tembakan\b", "mencobanya"),
    (r"\bmemberi tembakan\b", "mencobanya"),
    (r"\bdi luar ligaku\b", "terlalu tinggi untukku"),
    (r"\bdi luar liga saya\b", "terlalu tinggi untuk saya"),
    (r"\bdi luar ligamu\b", "bukan tandinganmu"),
    (r"\bmelompat ke kesimpulan\b", "buru-buru menyimpulkan"),
    (r"\bmenarik kakiku\b", "mengerjaiku"),
    (r"\bmenarik kaki saya\b", "mengerjai saya"),
    (r"\bmelempar handuk\b", "menyerah"),
    (r"\bmelemparkan handuk\b", "menyerah"),
    (r"\bmendorong keberuntunganmu\b", "ngelunjak"),
    (r"\bmendorong keberuntungan anda\b", "bertindak terlalu jauh"),
    (r"\bmembeli waktu\b", "mengulur waktu"),
    (r"\bmembeli beberapa waktu\b", "mengulur waktu"),
    (r"\bbermain bodoh\b", "pura-pura tidak tahu"),
    (r"\broda ketiga\b", "obat nyamuk"),
    (r"\btergelincir pikiranku\b", "aku kelupaan"),
    (r"\btergelincir dari pikiranku\b", "aku kelupaan"),
    (r"\bmembunyikan lonceng\b", "terdengar tidak asing"),
    (r"\bmembalikkan meja\b", "membalikkan keadaan"),
    (r"\bkupu-kupu di perutku\b", "perutku rasanya mulas karena gugup"),
    (r"\bsemua telinga\b", "siap mendengarkan"),
    (r"\baku semua telinga\b", "aku siap mendengarkan"),
    (r"\bmenangkap napasku\b", "mengatur napasku"),
    (r"\bmenangkap napas\b", "mengatur napas"),

    # --- 17. Honorifik Jepang, Sapaan Keluarga & RomCom/School ---
    (r"\bonii-chan\b", "Kakak"),
    (r"\bonii-san\b", "Kakak"),
    (r"\bonee-chan\b", "Kakak"),
    (r"\bonee-san\b", "Kakak"),
    (r"\baniki\b", "Bang"),
    (r"\bojou-sama\b", "Nona Muda"),
    (r"\botou-san\b", "Ayah"),
    (r"\bokaa-san\b", "Ibu"),
    (r"\bojii-san\b", "Kakek"),
    (r"\bojii-chan\b", "Kakek"),
    (r"\bobaa-san\b", "Nenek"),
    (r"\bobaa-chan\b", "Nenek"),
    (r"\bosananajimi\b", "teman masa kecil"),
    (r"\bgyaru\b", "cewek gyaru"),
    (r"\bchuunibyou\b", "sindrom chuunibyou"),
    (r"\bkokuhaku\b", "nembak perasaan"),

    # --- 18. Kultivasi, Murim, Wuxia, Xianxia & Donghua ---
    (r"\binti emas\b", "Inti Emas (Golden Core)"),
    (r"\bpembentukan inti\b", "Pembentukan Inti"),
    (r"\bpembangunan fondasi\b", "Tahap Fondasi"),
    (r"\bjiwa baru lahir\b", "Jiwa Nascent"),
    (r"\bkesengsaraan surgawi\b", "Kesengsaraan Langit (Tribulation)"),
    (r"\bkesengsaraan petir\b", "Petir Kesengsaraan"),
    (r"\bsaudara senior\b", "Kakak Senior"),
    (r"\bsaudari senior\b", "Kakak Senior"),
    (r"\bsaudara junior\b", "Adik Junior"),
    (r"\bsaudari junior\b", "Adik Junior"),
    (r"\bsekte seni bela diri\b", "Sekte Bela Diri"),
    (r"\benergi sejati\b", "Qi Sejati"),
    (r"\benergi spiritual\b", "Qi Spiritual"),
    (r"\bqi dalam\b", "Tenaga Dalam"),
    (r"\bkaisar langit\b", "Kaisar Langit"),
    (r"\btetua agung\b", "Tetua Agung"),
    (r"\bpemimpin sekte\b", "Ketua Sekte"),

    # --- 19. Istana Dalam / Apothecary / Historical (Kusuriya dll.) ---
    (r"\bistana belakang\b", "Istana Dalam"),
    (r"\bselir tingkat tinggi\b", "Selir Utama"),
    (r"\bpencicip makanan\b", "Pencicip Racun"),
    (r"\bapoteker istana\b", "Tabib Istana"),
]

# Aturan khusus adegan kasual/santai (tidak diterapkan jika konteks formal/kerajaan).
_CASUAL_FANSUB_RULES = [
    (r"\bsaya tidak tahu anda ada di sana\b", "aku nggak tahu kamu ada di sana"),
    (r"\bsaya nggak tahu anda ada di sana\b", "aku nggak tahu kamu ada di sana"),
    (r"\baku tidak tahu anda ada di sana\b", "aku nggak tahu kamu ada di sana"),
    (r"\baku nggak tahu anda ada di sana\b", "aku nggak tahu kamu ada di sana"),
    (r"\bsaya tidak tahu kamu ada di sana\b", "aku nggak tahu kamu ada di sana"),
    (r"\bsaya nggak tahu kamu ada di sana\b", "aku nggak tahu kamu ada di sana"),
    (r"\baku tidak melakukan apa pun\b", "aku nggak ngelakuin apa-apa"),
    (r"\btidak melakukan apa pun\b", "nggak ngelakuin apa-apa"),
    (r"\bingin saya mengajari anda\b", "mau kuajari"),
    (r"\banda perlu baju ganti\b", "kamu butuh baju ganti"),
    (r"\bapa yang kamu bicarakan\b", "ngomong apa sih kamu"),
    (r"\bapa yang kau bicarakan\b", "ngomong apa sih kamu"),
    (r"\bkoleksi hotnya\b", "cewek-cewek cakepnya"),
    (r"\bkoleksi hot\b", "cewek-cewek cakep"),
    (r"\bkalau dengerin saya\b", "kalau menurutku sih"),
    (r"\bkalau dengerin aku\b", "kalau menurutku sih"),
    (r"\bgak usah dikira\b", "nggak usah ditanya lagi"),
    (r"\bbertahanlah\b", "tunggu sebentar"),
    (r"\baku melihat\b", "begitu rupanya"),
    (r"\bkulihat\b", "begitu rupanya"),
    (r"\btidak apa-apa\b", "nggak apa-apa"),
    (r"\btak apa-apa\b", "nggak apa-apa"),
    (r"\btak apa\b", "nggak apa-apa"),
    (r"\bbaik-baik saja\b", "nggak apa-apa"),
    (r"\btutup mulutmu\b", "diem"),
    (r"\btidak ada jalan\b", "nggak mungkin"),
    (r"\btidak mungkin\b", "nggak mungkin"),
    (r"\btidak bisa\b", "nggak bisa"),
    (r"\btak bisa\b", "nggak bisa"),
    (r"\btidak dapat\b", "nggak bisa"),
    (r"\btidak akan\b", "nggak bakal"),
    (r"\btak akan\b", "nggak bakal"),
    (r"\btidak tahu\b", "nggak tahu"),
    (r"\btak tahu\b", "nggak tahu"),
    (r"\btidak mau\b", "nggak mau"),
    (r"\btak mau\b", "nggak mau"),
    (r"\btidak pernah\b", "nggak pernah"),
    (r"\btak pernah\b", "nggak pernah"),
    (r"\btidak perlu\b", "nggak usah"),
    (r"\btak perlu\b", "nggak usah"),
    (r"\btidak usah\b", "nggak usah"),
    (r"\btidak boleh\b", "nggak boleh"),
    (r"\btak boleh\b", "nggak boleh"),
    (r"\btidak ada\b", "nggak ada"),
    (r"\btak ada\b", "nggak ada"),
    (r"\b(?:emang\s+)?(?:sudah|udah)\s+kuduga\b", "emang udah kuduga"),
    (r"\bhanya saja\b", "cuma"),
    (r"\bsudah\b", "udah"),
    (r"\bsaja\b", "aja"),
    (r"\bhanya\b", "cuma"),
    (r"\bmengapa kamu\b", "kenapa kamu"),
    (r"\bmengapa kau\b", "kenapa kamu"),
    (r"\bmengapa dia\b", "kenapa dia"),
    (r"\bmengapa\b", "kenapa"),
    (r"\bbagaimana kalau\b", "gimana kalau"),
    (r"\bbagaimana jika\b", "gimana kalau"),
    (r"\bbagaimana cara\b", "gimana cara"),
    (r"\bbagaimana bisa\b", "gimana bisa"),
    (r"\blelaki itu\b", "cowok itu"),
    (r"\bpria itu\b", "cowok itu"),
    (r"\bwanita itu\b", "cewek itu"),
    (r"\bgadis itu\b", "cewek itu"),
    (r"\bwanita tersebut\b", "cewek itu"),
    (r"\blelaki tersebut\b", "cowok itu"),
    (r"\btersesatlah\b", "pergi sana"),
    (r"\bjangan khawatir\b", "tenang aja"),
    (r"\btak perlu khawatir\b", "tenang aja"),
    (r"\bterima kasih banyak\b", "makasih banyak"),
    (r"\bterima kasih\b", "makasih"),
    (r"\bdengarkan aku\b", "dengerin aku"),
    (r"\bdengarkan\b", "dengerin"),
    (r"\bsangat banyak\b", "banget"),
    (r"\bbodoh sekali\b", "bodoh banget"),
    (r"\bbagus sekali\b", "hebat banget"),
    (r"\bdi sini untuk mengambil\b", "mau mengambil"),
    (r"\banda berpikir\b", "kamu rasa"),
    (r"\bmau bagaimana lagi\b", "mau gimana lagi"),
    (r"\bmau tak mau\b", "mau nggak mau"),
    (r"\bapa yang terjadi\b", "ada apa sih"),
    (r"\bkamu tahu\b", "tahu nggak"),
    (r"\bapakah kamu serius\b", "kamu serius"),
    (r"\bapakah kamu bercanda\b", "kamu bercanda ya"),
    (r"\bbukan urusanmu\b", "bukan urusanmu kok"),
    (r"\btidak akan kumaafkan\b", "nggak bakal kumaafkan"),
    (r"\btak akan kumaafkan\b", "nggak bakal kumaafkan"),
    (r"\bsungguh merepotkan\b", "merepotkan banget"),
    (r"\bapa yang kamu maksud\b", "maksudmu apa"),
    (r"\bapa maksudmu\b", "maksudmu apa"),
    (r"\bmana aku tahu\b", "mana kutahu"),
    (r"\bbagaimana aku bisa tahu\b", "mana kutahu"),
    (r"\bapakah itu benar\b", "beneran nih"),
    (r"\bpantas saja\b", "pantesan"),
    (r"\bjangan konyol\b", "yang bener aja"),
    (r"\bjangan bercanda\b", "jangan bercanda deh"),
    (r"\btentu saja\b", "tentu saja"),
    (r"\bsama sekali tidak\b", "sama sekali nggak"),
    (r"\bsama sekali tak\b", "sama sekali nggak"),
    (r"\bbiar aku yang urus ini\b", "biar aku yang urus"),
    (r"\bbiar aku yang menangani ini\b", "biar aku yang urus"),
    (r"\bgampang sekali\b", "gampang banget"),
    (r"\bmudah sekali\b", "gampang banget"),
    (r"\bapa-apaan ini\b", "ada apa-apaan nih"),
    (r"\bsedikit pun\b", "dikit pun"),
    # Diksi Percakapan & Slang Santai Tambahan
    (r"\bbercanda kan\b", "bercanda ya"),
    (r"\bjangan macam-macam\b", "jangan macam-macam deh"),
    (r"\bada apa sebenarnya\b", "ada apa sih sebenarnya"),
    (r"\bkan sudah kubilang\b", "kan udah kubilang"),
    (r"\bsudah kubilang\b", "kan udah kubilang"),
    (r"\btidak mungkin kan\b", "nggak mungkin kan"),
    (r"\btak mungkin kan\b", "nggak mungkin kan"),
    (r"\bapa yang salah denganmu\b", "kamu kenapa sih"),
    (r"\bapa yang salah denganku\b", "aku kenapa sih"),
    (r"\bapa yang salah\b", "ada apa sih"),
    (r"\bbukan urusanku\b", "bukan urusanku kok"),
    (r"\baku tidak peduli\b", "aku nggak peduli"),
    (r"\btak peduli\b", "nggak peduli"),
    (r"\bsampai jumpa nanti\b", "sampai ketemu lagi"),
    (r"\btenanglah sedikit\b", "santai dikit dong"),
    (r"\btenang sedikit\b", "santai dikit dong"),
    (r"\bapa maumu\b", "mau apa sih kamu"),
    (r"\bapa yang kamu inginkan\b", "kamu mau apa sih"),
    # Question tags & penghalusan kalimat tanya / perintah lisan
    (r",\s*bukan\s*\?", ", kan?"),
    (r",\s*tidakkah begitu\s*\?", ", kan?"),
    (r",\s*bukankah begitu\s*\?", ", kan?"),
    (r",\s*benar kan\s*\?", ", ya kan?"),
    (r"\bapakah kamu baik-baik saja\b", "kamu nggak apa-apa"),
    (r"\bapakah kamu nggak apa-apa\b", "kamu nggak apa-apa"),
    (r"\bapakah kau baik-baik saja\b", "kamu nggak apa-apa"),
    (r"\bapakah kamu yakin\b", "kamu yakin"),
    (r"\bapakah kau yakin\b", "kamu yakin"),
    (r"\bapakah kamu sudah gila\b", "kamu udah gila ya"),
    (r"\bapakah kamu gila\b", "kamu gila ya"),
    (r"\bapakah itu mungkin\b", "memangnya mungkin"),
    (r"\bapakah kamu mengerti\b", "kamu ngerti kan"),
    (r"\baku mengerti sekarang\b", "oh, sekarang aku paham"),
    (r"\baku tidak mengerti\b", "aku nggak ngerti"),
    (r"\bnggak mengerti\b", "nggak ngerti"),
    (r"\bcepatlah sedikit\b", "cepetan dikit dong"),
    (r"\btunggu aku\b", "tungguin aku"),
    (r"\blihat itu\b", "lihat deh itu"),
    (r"\bhentikan itu\b", "udah dong, hentikan"),
    (r"\bserahkan padaku\b", "serahin aja padaku"),
    (r"\bserahkan saja padaku\b", "serahin aja padaku"),
    (r"\bpercayalah padaku\b", "percaya deh sama aku"),
    (r"\bjangan khawatir tentang itu\b", "nggak usah dipikirin"),
    (r"\baku baru saja\b", "aku barusan"),
    (r"\bbaru saja\b", "barusan"),
    (r"\bbenar-benar hebat\b", "keren banget"),
    (r"\bluar biasa sekali\b", "keren banget"),
    (r"\bsangat keren\b", "keren banget"),
    (r"\bsangat manis\b", "manis banget"),
    (r"\bsangat imut\b", "imut banget"),
    (r"\bsangat kuat\b", "kuat banget"),
    (r"\bsangat cepat\b", "cepet banget"),
    (r"\bsangat lambat\b", "lambat banget"),
    (r"\bsangat lezat\b", "enak banget"),
    (r"\bsangat enak\b", "enak banget"),
    (r"\bsangat menakutkan\b", "serem banget"),
    (r"\bsangat aneh\b", "aneh banget"),
    (r"\bsangat berisik\b", "berisik banget"),
    (r"\baku sangat senang\b", "aku seneng banget"),
    (r"\baku sangat lelah\b", "aku capek banget"),
    (r"\bsangat lelah\b", "capek banget"),
    (r"\baku sangat lapar\b", "aku laper banget"),
    (r"\bsangat lapar\b", "laper banget"),
]

_AIGTX_SMOOTH_RULES = [
    (r"\baku melihat\b", "begitu rupanya"),
    (r"\bkulihat\b", "begitu rupanya"),
    (r"\btidak ada jalan\b", "tidak mungkin"),
    (r"\btak ada jalan\b", "tidak mungkin"),
    (r"\btersesatlah\b", "pergi sana"),
    (r"\btak perlu khawatir\b", "tenang saja"),
    (r"\bgak usah dikira\b", "tidak usah ditanya lagi"),
    (r"\bcelah di tongkat\b", "retakan di tongkat"),
    (r"\btinta sulap\b", "tinta sihir"),
    (r"\bmelakukan casting\b", "merapal sihir"),
    (r"\bcasting seal\b", "segel sihir"),
    (r"\bberi aku istirahat\b", "yang benar saja"),
    (r"\bmelayanimu dengan benar\b", "rasakan itu"),
    (r"\bitu tidak bisa ditolong\b", "mau bagaimana lagi"),
    (r"\bsepotong kue\b", "sangat mudah"),
    (r"\bdi bawah cuaca\b", "kurang enak badan"),
    (r"\bbukan di jam tanganku\b", "tidak akan kubiarkan"),
    (r"\bambil dengan mudah\b", "santai saja"),
    (r"\bdi atas rumah\b", "gratis dari kedai"),
    (r"\bdi atas tubuh matiku\b", "langkahi dulu mayatku"),
    (r"\bjangan biarkan penjagamu turun\b", "jangan lengah"),
    (r"\bperhatikan punggungmu\b", "waspadalah di belakangmu"),
]
_GTXPLUS_SMOOTH_RULES = _AIGTX_SMOOTH_RULES

_COMPILED_UNIVERSAL = [(_re.compile(pat, _re.IGNORECASE), repl) for pat, repl in _UNIVERSAL_FANSUB_RULES]
_COMPILED_CASUAL = [(_re.compile(pat, _re.IGNORECASE), repl) for pat, repl in _CASUAL_FANSUB_RULES]
_COMPILED_AIGTX_SMOOTH = [(_re.compile(pat, _re.IGNORECASE), repl) for pat, repl in _AIGTX_SMOOTH_RULES]
_COMPILED_GTXPLUS_SMOOTH = _COMPILED_AIGTX_SMOOTH


def _sanitize_fansub_id(text: str, force_formal: bool = False) -> str:
    """Normalisasi kata kaku/literal secara adaptif (menjaga adegan formal tetap sopan)."""
    if not text:
        return text

    def _replace_match(m, repl):
        expanded = m.expand(repl) if "\\" in repl else repl
        orig = m.group(0)
        if orig and orig.islower():
            words = expanded.split(" ")
            lowered = [w if (w.isupper() and len(w) >= 2) else w.lower() for w in words]
            return " ".join(lowered)
        if orig and orig[0].isupper():
            return expanded[0].upper() + expanded[1:]
        return expanded

    result = text
    # 1. Jalankan koreksi universal
    for rx, repl in _COMPILED_UNIVERSAL:
        result = rx.sub(lambda m, r=repl: _replace_match(m, r), result)

    # 2. Jalankan normalisasi santai jika BUKAN adegan formal/kerajaan
    is_formal = force_formal or bool(_FORMAL_INDICATORS_RE.search(result))
    if not is_formal:
        for rx, repl in _COMPILED_CASUAL:
            result = rx.sub(lambda m, r=repl: _replace_match(m, r), result)

    return result


def _sanitize_gtxplus_id(text: str, force_formal: bool = False) -> str:
    """GTX+ Sanitizer: Menggabungkan deteksi adegan (Scene Detection) adaptif
    dan kamus fansub percakapan santai (casual conversation) secara otomatis.
    Jika adegan santai/sekolah/komedi/isekai: terapkan leksikon anime universal,
    diksi lisan alami (aku/kamu, nggak, udah, cuma, banget, dll), dan perbaikan idiom.
    Jika adegan formal/kerajaan/militer: pertahankan kesantunan baku (Saya/Anda,
    Yang Mulia, Paduka) tanpa partikel santai gaul."""
    if not text:
        return text

    def _replace_match(m, repl):
        expanded = m.expand(repl) if "\\" in repl else repl
        orig = m.group(0)
        if orig and orig.islower():
            words = expanded.split(" ")
            lowered = [w if (w.isupper() and len(w) >= 2) else w.lower() for w in words]
            return " ".join(lowered)
        if orig and orig[0].isupper():
            return expanded[0].upper() + expanded[1:]
        return expanded

    result = text
    # 1. Koreksi istilah anime & blunder terjemahan mesin (Universal Glossary)
    for rx, repl in _COMPILED_UNIVERSAL:
        result = rx.sub(lambda m, r=repl: _replace_match(m, r), result)

    # 2. Scene detector: formal vs casual
    is_formal = force_formal or bool(_FORMAL_INDICATORS_RE.search(result))
    if not is_formal:
        for rx, repl in _COMPILED_CASUAL:
            result = rx.sub(lambda m, r=repl: _replace_match(m, r), result)
        for rx, repl in _COMPILED_GTXPLUS_SMOOTH:
            result = rx.sub(lambda m, r=repl: _replace_match(m, r), result)

    return result


_sanitize_aigtx_id = _sanitize_gtxplus_id


def sanitize_cues_with_context(cues, mode: str = "gtx+", window: int = 3, max_gap_sec: float = 15.0):
    """Sanitasi daftar cues dengan Sliding-Window Scene Context (±window cues dalam jarak waktu <= max_gap_sec).
    Jika terdapat indikator adegan formal/kerajaan/militer pada tetangga dekat dalam satu adegan,
    cue di sekitarnya tetap mempertahankan register sopan (tidak tiba-tiba berubah menjadi gaul/kasual)."""
    if not cues:
        return []
    n = len(cues)
    # 1. Deteksi indikator formal pada masing-masing cue terlebih dahulu
    direct_formal = []
    for c in cues:
        txt = c.get("text") or ""
        direct_formal.append(bool(_FORMAL_INDICATORS_RE.search(txt)))

    # 2. Propagasi konteks formal ke tetangga dalam jendela ±window dan selisih waktu <= max_gap_sec
    contextual_formal = list(direct_formal)
    for i in range(n):
        if direct_formal[i]:
            continue
        c_start = float(cues[i].get("start", 0.0))
        c_end = float(cues[i].get("end", c_start))
        for j in range(max(0, i - window), min(n, i + window + 1)):
            if j == i or not direct_formal[j]:
                continue
            n_start = float(cues[j].get("start", 0.0))
            n_end = float(cues[j].get("end", n_start))
            gap = max(0.0, c_start - n_end) if j < i else max(0.0, n_start - c_end)
            if gap <= max_gap_sec:
                contextual_formal[i] = True
                break

    out = []
    for i, c in enumerate(cues):
        txt = c.get("text") or ""
        is_f = contextual_formal[i]
        if mode in ("pure", "pure_gtx", "gtx"):
            sanitized = txt
        elif mode == "fansub":
            sanitized = _sanitize_fansub_id(txt, force_formal=is_f)
        else:
            sanitized = _sanitize_gtxplus_id(txt, force_formal=is_f)
        out.append({"start": c["start"], "end": c["end"], "text": sanitized})
    return out



_ID_LINE_RE = _re.compile(r"^\s*(?:\*\*)?(\d{1,4})(?:\*\*)?\s*[|｜]\s?(.*)$")


def _parse_id_lines(content: str, valid_ids) -> dict:
    """Parse respons "N|teks" -> {N: teks}. Abaikan reasoning, markdown, ID di luar batch.
    Jika model mengulang teks sumber (N|source|terjemahan), ambil bagian terakhir."""
    if not content:
        return {}
    text = _re.sub(r"<think>.*?</think>", "", content, flags=_re.S | _re.I)
    text = _re.sub(r"```[a-zA-Z]*", "", text)
    out = {}
    for line in text.split("\n"):
        m = _ID_LINE_RE.match(line)
        if not m:
            continue
        i = int(m.group(1))
        t = m.group(2).strip()
        # Jika model mengulang teks input: "1|English text|Terjemahan Indonesia"
        if "|" in t or "｜" in t:
            subparts = [p.strip() for p in _re.split(r"[|｜]", t) if p.strip()]
            if len(subparts) >= 2:
                t = subparts[-1]
        if i in valid_ids and i not in out and t:
            out[i] = t
    return out


class _FatalLLMError(RuntimeError):
    """Key invalid / akses ditolak — hentikan seluruh job LLM."""


class _ModelUnavailable(RuntimeError):
    """Model tidak ada / tidak termasuk plan gratis — pindah ke model berikutnya."""


class _RateLimited(RuntimeError):
    """429 — tunggu atau pindah model."""


async def _chat_completion(client, apiurl, headers, payload) -> str:
    r = await client.post(apiurl + "/chat/completions", json=payload, headers=headers)
    if r.status_code == 400 and any(k in payload for k in ("reasoning_format", "reasoning_effort")):
        payload = {k: v for k, v in payload.items() if k not in ("reasoning_format", "reasoning_effort")}
        r = await client.post(apiurl + "/chat/completions", json=payload, headers=headers)
    if r.status_code == 429:
        raise _RateLimited(f"Rate limit (429): {_extract_err(r)}")
    if r.status_code in (401, 403):
        raise _FatalLLMError(f"HTTP {r.status_code}: {_extract_err(r)}")
    if r.status_code in (402, 404):
        raise _ModelUnavailable(f"HTTP {r.status_code}: {_extract_err(r)}")
    if r.status_code == 400:
        msg = _extract_err(r)
        if "model" in msg.lower():
            raise _ModelUnavailable(f"HTTP 400: {msg}")
        if "api key" in msg.lower() or "api_key" in msg.lower():
            raise _FatalLLMError(f"HTTP 400: {msg}")
        raise RuntimeError(f"HTTP 400: {msg}")
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {_extract_err(r)}")
    d = r.json()
    msg = (d.get("choices") or [{}])[0].get("message") or {}
    return (msg.get("content") or "").strip()


async def call_openai_translate(cues, src, tgt, apikey, model, apiurl, timeout=120.0, fill_with_gtx=True):
    """Terjemahan gaya fansub via OpenAI-compatible /chat/completions.

    - Format ber-ID "N|teks" -> tidak ada pergeseran baris; ID yang hilang di-retry.
    - Batch paralel (per-provider), konteks 4 baris sebelumnya dikirim sebagai referensi.
    - Rotasi model saat 429/402/404 (mis. Ollama Cloud free: gpt-oss:20b -> gpt-oss:120b).
    - Cue yang tetap gagal diisi Google GTX (hybrid), bukan membuang seluruh episode.

    Return (translated_cues, stats). Raise RuntimeError kalau tidak ada satu baris pun
    yang berhasil diterjemahkan LLM.
    """
    stats = {"provider": "", "model": "", "models": {}, "llm_lines": 0, "gtx_lines": 0,
             "total": len(cues or []), "error": ""}
    if not cues:
        return cues, stats
    apikey = (apikey or "").strip().strip("\"'").strip()
    apiurl = (apiurl or "https://generativelanguage.googleapis.com/v1beta/openai").strip().rstrip("/")
    prov = detect_provider(apiurl)

    # Otomatis sesuaikan model & apiurl berdasarkan format apikey dari pengguna
    if apikey:
        inferred_prov, inferred_model, inferred_url = detect_provider_from_key(apikey)
        if inferred_prov != "custom" and (prov != inferred_prov or not model):
            prov = inferred_prov
            apiurl = inferred_url
            model = inferred_model

    model = (model or "").strip() or _DEFAULT_MODEL[prov]
    model = _LEGACY_MODEL_UPGRADE.get(prov, {}).get(model, model)
    cfg = _PROVIDER_CFG[prov]
    stats["provider"] = prov

    src_name = LANG_NAMES.get((src or "").lower(), src or "English")
    tgt_name = LANG_NAMES.get((tgt or "").lower(), tgt or "Indonesian")
    system_prompt = _fansub_system_prompt(src_name, tgt, tgt_name)

    headers = {"Content-Type": "application/json"}
    if apikey:
        headers["Authorization"] = "Bearer " + apikey
    if prov == "google":
        headers["x-goog-api-key"] = apikey
    if prov == "openrouter":
        headers["HTTP-Referer"] = "http://127.0.0.1"
        headers["X-Title"] = "Tatap"

    src_lines = [_prep_line(c["text"]) for c in cues]
    n = len(cues)
    B = cfg["batch"]
    ranges = [(lo, min(n, lo + B)) for lo in range(0, n, B)]
    state = {"models": _model_chain(prov, model), "fatal": "", "last_err": "",
             "used": _collections.Counter()}
    sem = _asyncio.Semaphore(cfg["conc"])
    t_start = _time.time()
    log_translate(
        f"Mulai AI Fansub {n} cues ({src_name} -> {tgt_name}) | Provider: {_PROVIDER_LABEL[prov]} | "
        f"Model: {' > '.join(state['models'])} | Batches: {len(ranges)} x{B} (paralel {cfg['conc']})"
    )

    def _payload(cur_model, ids, lo):
        ctx = [src_lines[j] for j in range(max(0, lo - 4), lo)]
        parts = []
        if ctx:
            parts.append("Konteks (baris sebelumnya, JANGAN diterjemahkan, hanya untuk pemahaman):\n"
                         + "\n".join("- " + x for x in ctx))
        parts.append(f"Terjemahkan {len(ids)} baris berikut:\n"
                     + "\n".join(f"{i}|{src_lines[lo + i - 1]}" for i in ids))
        reasoning = "gpt-oss" in cur_model
        # Direct instruction to prevent unnecessary chain-of-thought delay on reasoning models
        user_body = "\n\n".join(parts)
        if reasoning:
            user_body = "JANGAN sertakan penalaran/thinking. Langsung keluarkan format N|terjemahan secara ringkas.\n\n" + user_body
        p = {
            "model": cur_model,
            "messages": [{"role": "system", "content": system_prompt},
                         {"role": "user", "content": user_body}],
            "temperature": 0.3,
            "max_tokens": min(8192, len(ids) * 65 + 250),
        }
        if reasoning:
            p["reasoning_effort"] = "low"
            if prov == "groq":
                p["reasoning_format"] = "hidden"
        return p

    async def run_batch(bidx, lo, hi, client):
        async with sem:
            got = {}
            pending = list(range(1, hi - lo + 1))
            attempts = 0
            t_b = _time.time()
            while pending and attempts < 4 and not state["fatal"] and state["models"]:
                attempts += 1
                cur_model = state["models"][0]
                try:
                    content = await _chat_completion(client, apiurl, headers, _payload(cur_model, pending, lo))
                    parsed = _parse_id_lines(content, set(pending))
                    got.update(parsed)
                    state["used"][cur_model] += len(parsed)
                    pending = [i for i in pending if i not in got]
                    if not parsed:
                        state["last_err"] = f"{cur_model}: respon kosong / format tidak sesuai"
                except _FatalLLMError as e:
                    state["fatal"] = str(e)
                    state["last_err"] = str(e)
                except (_ModelUnavailable, _RateLimited) as e:
                    state["last_err"] = f"{cur_model}: {e}"
                    only_one = len(state["models"]) == 1
                    if isinstance(e, _RateLimited) and only_one:
                        await _asyncio.sleep(2.0 * attempts + 1.0)
                        continue
                    if cur_model in state["models"] and not only_one:
                        state["models"].remove(cur_model)
                        log_translate(f"Model {cur_model} tidak tersedia/limit -> pindah ke {state['models'][0]}")
                    elif only_one:
                        state["models"].clear()
                except Exception as e:
                    state["last_err"] = f"{cur_model}: {e}"
                    await _asyncio.sleep(1.0 * attempts)
            log_translate(
                f"Batch {bidx + 1}/{len(ranges)}: {len(got)}/{hi - lo} baris AI dalam {_time.time() - t_b:.1f}s"
                + (f" (sisa {len(pending)} -> GTX)" if pending else "")
            )
            return {lo + i - 1: got[i] for i in got}

    results = {}
    timeout_cfg = _httpx.Timeout(timeout, connect=20.0)
    async with _httpx.AsyncClient(timeout=timeout_cfg, trust_env=True) as client:
        parts = await _asyncio.gather(*[run_batch(b, lo, hi, client) for b, (lo, hi) in enumerate(ranges)])
    for p in parts:
        results.update(p)

    if not results:
        err = state["fatal"] or state["last_err"] or "Model tidak menghasilkan terjemahan"
        log_translate(f"AI Fansub GAGAL total: {err}")
        raise RuntimeError(err)

    missing = [i for i in range(n) if i not in results]
    gtx_filled = {}
    if missing and fill_with_gtx:
        try:
            sub = await call_gtx_translate([cues[i] for i in missing], src, tgt)
            gtx_filled = {i: sub[k]["text"] for k, i in enumerate(missing)}
        except Exception as e:
            log_translate(f"Isi GTX untuk {len(missing)} cue gagal: {e}")

    out = []
    for i, c in enumerate(cues):
        if i in results:
            txt = _restore_line(results[i])
        else:
            txt = gtx_filled.get(i, c["text"])
        if (tgt or "").lower() == "id":
            txt = _sanitize_fansub_id(txt)
        out.append({"start": c["start"], "end": c["end"], "text": txt or c["text"]})

    used = state["used"]
    stats.update({
        "model": used.most_common(1)[0][0] if used else model,
        "models": dict(used),
        "llm_lines": len(results),
        "gtx_lines": len(gtx_filled),
        "error": state["last_err"] if missing else "",
    })
    log_translate(
        f"AI Fansub selesai {n} cues dalam {_time.time() - t_start:.1f}s | AI: {len(results)} | "
        f"GTX: {len(gtx_filled)} | model: {dict(used)}"
    )
    return out, stats


def is_valid_translation(original_cues, translated_cues, tgt="id"):
    """Validasi apakah hasil terjemahan benar-benar bahasa sasaran dan bukan teks sumber."""
    if not translated_cues:
        return False
    if (tgt or "").lower() != "id":
        return True
    combined = " ".join([c.get("text", "") for c in translated_cues[:50]])
    marker_match = _re.search(r"\b(yang|dan|tidak|aku|kamu|di|ini|itu|bisa|ada|nggak|udah|cuma|banget|siapa|kenapa)\b", combined, _re.IGNORECASE)
    return bool(marker_match)


async def call_gtx_translate(cues, src="en", tgt="id", timeout=20.0, mode="gtx+"):
    """Translate via Google Translate Web RPC (Unmetered, Zero-Key, Super Cepat).
    Menggunakan HTTP POST form-encoded dengan HTML preservation (<p id="i">...</p>)
    dan multi-client pool failover (gtx, dict-chrome-ex, tw-ob).
    Tahan batas laju IP/CGNAT operator seluler dan tidak memotong URI."""
    if not cues:
        return cues
    import urllib.parse as _up
    
    BATCH_SIZE = 25
    batches = [cues[i:i + BATCH_SIZE] for i in range(0, len(cues), BATCH_SIZE)]
    all_translated = []
    t_start = _time.time()
    log_translate(f"Mulai translate Google (POST/Multi-Client): {len(cues)} cues | {len(batches)} batches | mode={mode}")
    
    from concurrent.futures import ThreadPoolExecutor

    def _restore_html_chunk(raw_chunk: str, fallback: str) -> str:
        val = _re.sub(r"<br\s*/?>", "\n", raw_chunk or "", flags=_re.IGNORECASE)
        val = _html.unescape(val).strip()
        return val if val else fallback

    def _fetch_single_chunk_sync(batch_lines):
        html_chunks = []
        for i, line in enumerate(batch_lines):
            if line:
                escaped_lines = [_html.escape(part) for part in line.split("\n")]
                safe_text = "<br>".join(escaped_lines)
            else:
                safe_text = ""
            html_chunks.append(f'<p id="{i}">{safe_text}</p>')
        joined = "".join(html_chunks)

        endpoints = [
            ("https://clients5.google.com/translate_a/t", {
                "client": "dict-chrome-ex", "sl": src, "tl": tgt
            }),
            ("https://clients5.google.com/translate_a/t", {
                "client": "tw-ob", "sl": src, "tl": tgt
            }),
            ("https://translate.google.com/translate_a/t", {
                "client": "dict-chrome-ex", "sl": src, "tl": tgt
            }),
            ("https://translate.googleapis.com/translate_a/single", {
                "client": "dict-chrome-ex", "sl": src, "tl": tgt, "dt": "t"
            }),
        ]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
            "Accept": "*/*"
        }

        body_data = {"q": joined}

        # 1. Coba via HTTP POST menggunakan httpx
        for ep_url, ep_params in endpoints:
            try:
                with _httpx.Client(timeout=6.0, follow_redirects=True) as client:
                    resp = client.post(ep_url, params=ep_params, data=body_data, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_out = ""
                        if isinstance(data, list) and data and isinstance(data[0], list):
                            raw_out = "".join([item[0] for item in data[0] if item and item[0]])
                        elif isinstance(data, list) and data and isinstance(data[0], str):
                            raw_out = "".join(data)
                        elif isinstance(data, str):
                            raw_out = data

                        matches = dict(_re.findall(r'<p\s+id=[\"\']?\s*(\d+)\s*[\"\']?\s*>(.*?)</p>', raw_out, _re.DOTALL))
                        if matches:
                            res = []
                            for i in range(len(batch_lines)):
                                res.append(_restore_html_chunk(matches.get(str(i), batch_lines[i]), batch_lines[i]))
                            return res, True
            except Exception:
                pass

        # 2. Coba fallback via httpx dengan unverified SSL (untuk Android Chaquopy lama)
        for ep_url, ep_params in endpoints[:2]:
            try:
                with _httpx.Client(timeout=6.0, verify=False, follow_redirects=True) as client:
                    resp = client.post(ep_url, params=ep_params, data=body_data, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_out = ""
                        if isinstance(data, list) and data and isinstance(data[0], list):
                            raw_out = "".join([item[0] for item in data[0] if item and item[0]])
                        elif isinstance(data, list) and data and isinstance(data[0], str):
                            raw_out = "".join(data)
                        elif isinstance(data, str):
                            raw_out = data

                        matches = dict(_re.findall(r'<p\s+id=[\"\']?\s*(\d+)\s*[\"\']?\s*>(.*?)</p>', raw_out, _re.DOTALL))
                        if matches:
                            res = []
                            for i in range(len(batch_lines)):
                                res.append(_restore_html_chunk(matches.get(str(i), batch_lines[i]), batch_lines[i]))
                            return res, True
            except Exception:
                pass

        # 3. Coba fallback via urllib.request (POST) dengan unverified SSL context
        try:
            import urllib.request as _ur
            import ssl
            ssl_ctx = ssl._create_unverified_context()
            encoded_body = _up.urlencode(body_data).encode("utf-8")
            for ep_url, ep_params in endpoints[:2]:
                url_full = ep_url + "?" + _up.urlencode(ep_params)
                req = _ur.Request(url_full, data=encoded_body, headers=headers)
                with _ur.urlopen(req, context=ssl_ctx, timeout=6.0) as resp:
                    if resp.status == 200:
                        data = _json.loads(resp.read().decode("utf-8"))
                        raw_out = ""
                        if isinstance(data, list) and data and isinstance(data[0], list):
                            raw_out = "".join([item[0] for item in data[0] if item and item[0]])
                        elif isinstance(data, list) and data and isinstance(data[0], str):
                            raw_out = "".join(data)
                        elif isinstance(data, str):
                            raw_out = data
                        matches = dict(_re.findall(r'<p\s+id=[\"\']?\s*(\d+)\s*[\"\']?\s*>(.*?)</p>', raw_out, _re.DOTALL))
                        if matches:
                            res = [
                                _restore_html_chunk(matches.get(str(i), batch_lines[i]), batch_lines[i])
                                for i in range(len(batch_lines))
                            ]
                            return res, True
        except Exception:
            pass

        return batch_lines, False

    def _fetch_batch_sync(batch_lines):
        _time.sleep(0.02)
        res, ok = _fetch_single_chunk_sync(batch_lines)
        if ok:
            return res, True

        # Jika batch 25 gagal, bagi dua menjadi mini-batch sebagai safety net
        if len(batch_lines) > 6:
            mid = len(batch_lines) // 2
            _time.sleep(0.05)
            p1, ok1 = _fetch_single_chunk_sync(batch_lines[:mid])
            _time.sleep(0.05)
            p2, ok2 = _fetch_single_chunk_sync(batch_lines[mid:])
            if ok1 or ok2:
                return p1 + p2, True

        return batch_lines, False

    loop = _asyncio.get_running_loop()
    def _prep_line(text: str) -> str:
        raw_lines = [ln.strip() for ln in (text or "").split("\n") if ln.strip()]
        if not raw_lines:
            return ""
        if (src or "").lower() == "en" and (tgt or "").lower() == "id" and mode not in ("pure", "pure_gtx", "gtx"):
            raw_lines = [_pre_normalize_en_slang(ln) for ln in raw_lines]
        return "\n".join(raw_lines)

    batch_lines_list = [[_prep_line(cue["text"]) for cue in b] for b in batches]
    with ThreadPoolExecutor(max_workers=3) as executor:
        tasks = [loop.run_in_executor(executor, lambda b=bl: _fetch_batch_sync(b)) for bl in batch_lines_list]
        batch_results = await _asyncio.gather(*tasks)

    success_count = 0
    for item in batch_results:
        if isinstance(item, tuple) and len(item) == 2:
            parts, ok_flag = item
        else:
            parts, ok_flag = item, True
        all_translated.extend(parts)
        if ok_flag:
            success_count += 1

    dur = _time.time() - t_start
    log_translate(f"Selesai translate Google: {len(cues)} cues | {success_count}/{len(batches)} batch sukses ({dur:.2f}s) | mode={mode}")

    # Jika seluruh batch gagal, lempar exception agar fallback ke tier berikutnya
    if len(batches) > 0 and success_count == 0:
        raise RuntimeError(f"Semua endpoint Google Translate gagal atau terblokir (0/{len(batches)} batch berhasil).")

    raw_cues = []
    for i, c in enumerate(cues):
        tr_text = all_translated[i] if i < len(all_translated) else c["text"]
        if (tgt or "").lower() == "id" and mode not in ("pure", "pure_gtx", "gtx"):
            tr_text = _postprocess_stutter_id(c.get("text", ""), tr_text)
        raw_cues.append({"start": c["start"], "end": c["end"], "text": tr_text})

    if (tgt or "").lower() == "id":
        return sanitize_cues_with_context(raw_cues, mode=mode, window=3)
    return raw_cues


async def call_mymemory_translate(cues, src, tgt, timeout=30.0):
    """Translate via MyMemory REST. Satu request per batch 1 cue.
    cues: list[{start,end,text}]. Returns translated cues."""
    if not cues:
        return cues
    out = []
    async with _httpx.AsyncClient(timeout=timeout) as c:
        for cue in cues:
            text = cue["text"]
            if (src or "").lower() == "en" and (tgt or "").lower() == "id":
                text = _pre_normalize_en_slang(text)
            try:
                r = await c.get(
                    "https://api.mymemory.translated.net/get",
                    params={"q": text[:500], "langpair": f"{src}|{tgt}"},
                )
                d = r.json()
                tr = (d.get("responseData") or {}).get("translatedText", text)
                if not tr or len(tr.strip()) == 0:
                    tr = text
            except Exception:
                tr = text
            if (tgt or "").lower() == "id":
                tr = _sanitize_fansub_id(tr)
            out.append({"start": cue["start"], "end": cue["end"], "text": tr})
    return out


def estimate_chars(cues):
    """Total chars for quota accounting."""
    return sum(len(c.get("text", "")) for c in (cues or []))