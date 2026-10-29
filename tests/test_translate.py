"""Unit test engine translate subtitle (tanpa network)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from api import translate as T  # noqa: E402


def test_parse_vtt_plain_text_and_linebreak():
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<i>Tom &amp; Jerry</i>\nsecond line\n"
    cues = T.parse_vtt(vtt)
    assert cues == [{"start": 1.0, "end": 2.0, "text": "Tom & Jerry\nsecond line"}]


def test_prep_restore_roundtrip():
    assert T._prep_line("Hello\nworld") == "Hello <br> world"
    assert T._restore_line("Halo <br> dunia") == "Halo\ndunia"
    assert T._restore_line("A\u2011Apa?!") == "A-Apa?!"


def test_parse_id_lines_ignores_noise_and_out_of_range():
    content = "<think>hmm</think>\n```\n1|Hello|Hei!\n**2**| Kamu ngapain?\n9|nyasar\nteks bebas\n3|\n```"
    got = T._parse_id_lines(content, {1, 2, 3})
    assert got == {1: "Hei!", 2: "Kamu ngapain?"}


def test_detect_provider():
    assert T.detect_provider("https://ollama.com/v1") == "ollama"
    assert T.detect_provider("http://localhost:11434/v1") == "ollama_local"
    assert T.detect_provider("https://generativelanguage.googleapis.com/v1beta/openai") == "google"
    assert T._model_chain("ollama", "gpt-oss:20b") == ["gpt-oss:20b", "gpt-oss:120b"]


def _cues(n):
    return [{"start": float(i), "end": i + 0.9, "text": f"line {i}"} for i in range(n)]


def test_retry_missing_ids_and_gtx_fill(monkeypatch):
    calls = []

    async def fake_chat(client, apiurl, headers, payload):
        user = payload["messages"][1]["content"]
        ids = [int(l.split("|")[0]) for l in user.split("\n") if "|" in l and l.split("|")[0].isdigit()]
        calls.append(ids)
        # Batch pertama: "lupa" id 2 (model menggabung baris); retry: kirim semua.
        if len(calls) == 1:
            return "\n".join(f"{i}|terjemahan {i}" for i in ids if i != 2)
        return "\n".join(f"{i}|terjemahan {i}" for i in ids)

    monkeypatch.setattr(T, "_chat_completion", fake_chat)
    out, stats = asyncio.run(T.call_openai_translate(_cues(3), "en", "id", "k", "gpt-oss:20b", "https://ollama.com/v1"))
    assert [c["text"] for c in out] == ["terjemahan 1", "terjemahan 2", "terjemahan 3"]
    assert calls[1] == [2]  # hanya ID yang hilang di-retry
    assert stats["llm_lines"] == 3 and stats["gtx_lines"] == 0


def test_model_rotation_and_hybrid(monkeypatch):
    async def fake_chat(client, apiurl, headers, payload):
        if payload["model"] == "gpt-oss:20b":
            raise T._RateLimited("429")
        user = payload["messages"][1]["content"]
        ids = [int(l.split("|")[0]) for l in user.split("\n") if "|" in l and l.split("|")[0].isdigit()]
        return "\n".join(f"{i}|ok {i}" for i in ids if i != 1)  # id 1 selalu hilang

    async def fake_gtx(cues, src="en", tgt="id", timeout=20.0):
        return [{**c, "text": "gtx"} for c in cues]

    monkeypatch.setattr(T, "_chat_completion", fake_chat)
    monkeypatch.setattr(T, "call_gtx_translate", fake_gtx)
    out, stats = asyncio.run(T.call_openai_translate(_cues(3), "en", "id", "k", "gpt-oss:20b", "https://ollama.com/v1"))
    assert [c["text"] for c in out] == ["gtx", "ok 2", "ok 3"]
    assert stats["model"] == "gpt-oss:120b"
    assert stats["gtx_lines"] == 1


def test_fatal_key_raises(monkeypatch):
    async def fake_chat(client, apiurl, headers, payload):
        raise T._FatalLLMError("HTTP 401: bad key")

    monkeypatch.setattr(T, "_chat_completion", fake_chat)
    try:
        asyncio.run(T.call_openai_translate(_cues(2), "en", "id", "k", "", "https://ollama.com/v1"))
        assert False, "harus raise"
    except RuntimeError as e:
        assert "401" in str(e)


def test_sanitize_fansub_id():
    # 1. Kasual / Santai
    raw1 = "Apakah kamu baik-baik saja?"
    assert T._sanitize_fansub_id(raw1) == "Kamu nggak apa-apa?"

    raw2 = "Tutup mulutmu dan dengarkan aku!"
    assert T._sanitize_fansub_id(raw2) == "Diem dan dengerin aku!"

    raw3 = "Lelaki itu sudah pergi ke serikat petualang di penjara bawah tanah."
    assert T._sanitize_fansub_id(raw3) == "Cowok itu udah pergi ke guild petualang di dungeon."

    raw4 = "Mengapa kamu tidak mau makan? Tenang saja, tidak apa-apa."
    assert T._sanitize_fansub_id(raw4) == "Kenapa kamu nggak mau makan? Tenang aja, nggak apa-apa."

    # Idiom & Diksi aneh (Chuunibyou Ep 1 calque fixes & awkward slang)
    raw5 = "Banjir tinggi, ya? Kalau dengerin saya, koleksi hotnya sangat embarrassing."
    assert T._sanitize_fansub_id(raw5) == "Incaranmu tinggi juga, ya? Kalau menurutku sih, cewek-cewek cakepnya memalukan banget."

    raw6 = "Area ini diharamkan masuk! Mereka mau ngeplug lubang itu di mata pertama."
    assert T._sanitize_fansub_id(raw6) == "Area ini dilarang masuk! Mereka mau menutup lubang itu pada pandangan pertama."

    raw7 = "Berapa curiga itu? Berapa lama aku keluar? Kamu bakal dapat duit jahat dengan kecepatan kayak gini."
    assert T._sanitize_fansub_id(raw7) == "Mencurigakan banget, kan? Berapa lama aku pingsan? Kamu bakal dapat untung besar kalau begini terus."

    raw8 = "Ini basis rahasia kita! Jangan ngomong balas ke orang tua! Lihat? Katanya!"
    assert T._sanitize_fansub_id(raw8) == "Ini markas rahasia kita! Jangan membantah ke orang tua! Tuh, kan! Apa kubilang!"

    raw9 = "Kita bertembung kepala, dasar anjing campuran! Pergi dan berputus di neraka!"
    assert T._sanitize_fansub_id(raw9) == "Kita berselisih, dasar anjing buduk! Pergi dan mampus di neraka!"

    raw10 = "Musuh sedang dalam kemarahan kerajaan. Jangan ngelakuin luka pada warga, atau aku akan menghapus kamu!"
    assert T._sanitize_fansub_id(raw10) == "Musuh sedang dalam mengamuk hebat. Jangan melukai pada warga, atau aku akan menghabisi kamu!"

    raw11 = "Korpul, aktifkan penipu optik itu! Sanggah, Ma'am!"
    assert T._sanitize_fansub_id(raw11) == "Kopral, aktifkan umpan optik itu! Siap, Ma'am!"

    raw12 = "Gak ada cara aku ngelakuin itu, dasar kau pervert! Kalian ngapain ngapain?!"
    assert T._sanitize_fansub_id(raw12) == "Mana sudi aku ngelakuin itu, dasar mesum! Kalian ngerjain aku ya?!"

    raw13 = "Kira bukan dewa, dia pembunuh anak kecil dan satu-satunya jahat yang tersisa. Aku akan melihatmu dieksekusi!"
    assert T._sanitize_fansub_id(raw13) == "Kira bukan dewa, dia pembunuh kekanak-kanakan dan satu-satunya penjahat yang tersisa. Aku akan memastikanmu dieksekusi!"

    raw14 = "Kenapa kamu ke lantai bawah dua? Morgue ada di sana, jangan bilang itu di luar!"
    assert T._sanitize_fansub_id(raw14) == "Kenapa kamu ke lantai bawah tanah kedua? Kamar jenazah ada di sana, jangan katakan itu keras-keras!"

    raw15 = "Tembok tinggi ngeliat di depan aku. Aku pasti ngelupas blok mereka!"
    assert T._sanitize_fansub_id(raw15) == "Tembok tinggi menjulang di depanku. Aku pasti menerobos blok mereka!"

    raw16 = "Korban terbaring di kolam darah, disayat sampai mati oleh pelaku misterius."
    assert T._sanitize_fansub_id(raw16) == "Korban terbaring bersimbah darah, ditusuk sampai mati oleh pelaku misterius."

    raw17 = "Jangan jadi kucing takut, Keiichiro. Kumpulin diri! Buku ini bilang cara ngendang roh jahat supaya tidur dan tutup banyak hantu."
    assert T._sanitize_fansub_id(raw17) == "Jangan jadi penakut, Keiichiro. Kuatkan dirimu! Buku ini bilang cara menenangkan roh jahat dan menyegel banyak hantu."

    raw18 = "Semua unit, segera keluar! Ambil tindakan menghindar sebelum terkena pukulan langsung! Tembak sesuai keinginan! Semua bersorak Britannia!"
    assert T._sanitize_fansub_id(raw18) == "Semua unit, segera meluncur! Lakukan manuver menghindar sebelum terkena tembakan langsung! Bebas tembak! Hidup Britannia!"

    raw19 = "Siapa yang memegang tali di balik sel ini? Dia pikir seorang warga harta karun akan menari tepat ke perangkap musuh?!"
    assert T._sanitize_fansub_id(raw19) == "Siapa yang mengendalikan semuanya di balik sel ini? Dia pikir seorang warga kehormatan akan masuk tepat ke perangkap musuh?!"

    raw20 = "Aku gabung ke Klub Classic Lit, jadi datang buat ngelamun. Jangan jadi peeping tom di sini!"
    assert T._sanitize_fansub_id(raw20) == "Aku gabung ke Klub Sastra Klasik, jadi datang untuk memberi salam. Jangan jadi tukang intip di sini!"

    raw21 = "Waktu cekout di perpustakaan dua minggu. Dia punya lidah tajam, dan pamannya resmi mati."
    assert T._sanitize_fansub_id(raw21) == "Masa peminjaman di perpustakaan dua minggu. Dia mulutnya cukup pedas, dan pamannya dinyatakan meninggal."

    raw22 = "Dia jadi domba korban bagi seluruh tubuh siswa karena para punks mengacaukan anthologi itu."
    assert T._sanitize_fansub_id(raw22) == "Dia jadi tumbal bagi seluruh siswa karena berandalan mengacaukan antologi itu."

    raw23 = "Setelah semua, marah di jam periode kelima bikin capek. Mari kita nikmati bath open-air dan lihat bayangan di balik layar kertas itu."
    assert T._sanitize_fansub_id(raw23) == "Lagipula, marah di jam kelima bikin capek. Mari kita nikmati pemandian terbuka dan lihat bayangan di balik pintu geser kertas itu."

    raw24 = "Order up! Senang kamu suka, gak banyak juga! Pencurilah kapal musuh itu kalau dia ngelamun dan memohon."
    assert T._sanitize_fansub_id(raw24) == "Pesanan siap! Senang kamu suka, bukan apa-apa kok! Jarahlah kapal musuh itu kalau dia berlutut dan memohon."

    # 2. Formal / Kerajaan / Militer (Harus mempertahankan kata baku & sopan)
    raw_formal1 = "Yang Mulia, hamba tidak dapat menyetujui keputusan ini."
    assert T._sanitize_fansub_id(raw_formal1) == "Yang Mulia, hamba tidak dapat menyetujui keputusan ini."

    raw_formal2 = "Paduka, pasukan ksatria sudah bersiap di gerbang kota."
    assert T._sanitize_fansub_id(raw_formal2) == "Paduka, pasukan ksatria sudah bersiap di gerbang kota."

    raw_formal3 = "Letnan, kami tidak akan membiarkan musuh menembus garis pertahanan markas besar."
    assert T._sanitize_fansub_id(raw_formal3) == "Letnan, kami tidak akan membiarkan musuh menembus garis pertahanan markas besar."


def test_sanitize_gtxplus_id():
    # 1. Istilah Anime & Blunder Diperbaiki dengan gaya luwes casual fansub
    raw1 = "Rouge Ninja dari Desa Daun Tersembunyi sudah pergi ke Jujutsu Tech."
    assert T._sanitize_gtxplus_id(raw1) == "Ninja Pelarian dari Desa Konoha udah pergi ke SMK Jujutsu."

    raw2 = "Layar Stevenson dan pendeta yang korup itu terbaring di kolam darah."
    assert T._sanitize_gtxplus_id(raw2) == "Kotak Stevenson dan pendeta bejat itu terbaring bersimbah darah."

    # 2. Kalimat santai non-formal menerapkan kamus casual fansub (sudah -> udah, lelaki -> cowok)
    raw3 = "Lelaki itu sudah pergi ke serikat petualang di penjara bawah tanah."
    assert T._sanitize_gtxplus_id(raw3) == "Cowok itu udah pergi ke guild petualang di dungeon."

    # 3. Adegan Formal / Kerajaan dipertahankan 100% baku & sopan
    raw_formal = "Yang Mulia, hamba tidak dapat menyetujui keputusan ini."
    assert T._sanitize_gtxplus_id(raw_formal) == "Yang Mulia, hamba tidak dapat menyetujui keputusan ini."

    # 4. Idiom game / isekai (Hell Mode)
    raw4 = "Dia bisa membuat guru kita kabur demi uangnya."
    assert T._sanitize_gtxplus_id(raw4) == "Dia bisa memberikan perlawanan sengit kepada guru kita."

    raw5 = "Ini memulihkan 1% HP-nya setiap kedua saat melawan Iblis Tuhan."
    assert T._sanitize_gtxplus_id(raw5) == "Ini memulihkan 1% HP-nya setiap detik saat melawan Raja Iblis."

    raw6 = "Berikan mereka neraka!"
    assert T._sanitize_gtxplus_id(raw6) == "Hajar mereka!"

    # 5. Kontekstual "Ruang Bawah Tanah" vs "Dungeon" vs "Basement"
    raw_dungeon1 = "Panggilanku sedang bertarung di ruang bawah tanah peringkat A."
    assert T._sanitize_gtxplus_id(raw_dungeon1) == "Panggilanku sedang bertarung di dungeon peringkat A."

    raw_dungeon2 = "Kamu akan terus menjelajahi ruang bawah tanah dan menaklukkan tiga ruang bawah tanah?"
    assert T._sanitize_gtxplus_id(raw_dungeon2) == "Kamu akan terus menjelajahi dungeon dan menaklukkan tiga dungeon?"

    # Kasus arsitektur / rumah biasa (basement) -> tetap aman tidak diubah
    raw_basement = "Kunci ruang bawah tanah rumah Dr. Yeager ada di laci meja."
    assert T._sanitize_gtxplus_id(raw_basement) == "Kunci ruang bawah tanah rumah Dr. Yeager ada di laci meja."

    # 6. Blunder calque mesin lainnya
    raw_party = "Mungkin kita harus merekrut pengintai untuk pesta itu."
    assert T._sanitize_gtxplus_id(raw_party) == "Mungkin kita harus merekrut pengintai untuk party."

    raw_charge = "Aduh. Apakah sedang mengisi daya?!"
    assert T._sanitize_gtxplus_id(raw_charge) == "Aduh. Apakah dia sedang mengumpulkan kekuatan?!"

    raw_repeat = "Rencana hari ini adalah mengulangi perintah itu. dungeon dan tantang kemunculan monster bos."
    assert T._sanitize_gtxplus_id(raw_repeat) == "Rencana hari ini adalah mengulang dungeon dan tantang kemunculan monster bos."

    # 7. Backward compatibility alias _sanitize_aigtx_id
    assert T._sanitize_aigtx_id(raw3) == T._sanitize_gtxplus_id(raw3)


def test_call_gtx_translate_modes(monkeypatch):
    cues = [{"start": 0.0, "end": 2.0, "text": "Rouge Ninja in Desa Daun"}]

    def fake_fetch_sync(batch_lines):
        # Simulasikan hasil translasi mentah dari Google Translate
        return ["Rouge Ninja di Desa Daun"]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def fake_run_in_executor(executor, func):
        return fake_fetch_sync(None)

    monkeypatch.setattr(loop, "run_in_executor", fake_run_in_executor)
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: loop)

    # Mode pure gtx: tidak diubah
    res_pure = loop.run_until_complete(T.call_gtx_translate(cues, mode="gtx"))
    assert res_pure[0]["text"] == "Rouge Ninja di Desa Daun"

    # Mode gtx+ (default): menerapkan kamus anime & casual rules
    res_gtxplus = loop.run_until_complete(T.call_gtx_translate(cues, mode="gtx+"))
    assert res_gtxplus[0]["text"] == "Ninja Pelarian di Desa Konoha"

    # Mode aigtx (backward compatibility alias): menerapkan hasil yang sama
    res_aigtx = loop.run_until_complete(T.call_gtx_translate(cues, mode="aigtx"))
    assert res_aigtx[0]["text"] == "Ninja Pelarian di Desa Konoha"


def test_pre_normalize_en_slang():
    assert T._pre_normalize_en_slang("I gotta bounce right now.") == "I gotta go now right now."
    assert T._pre_normalize_en_slang("No cap, she was amazing.") == "seriously, no lie, she was amazing."
    assert T._pre_normalize_en_slang("I'm down for that mission.") == "I agree to that mission."
    assert T._pre_normalize_en_slang("Chill out, guys.") == "calm down and relax, guys."
    assert T._pre_normalize_en_slang("Bro has zero rizz.") == "Bro has zero charisma."
    assert T._pre_normalize_en_slang("Time to touch grass.") == "Time to face reality."
    assert T._pre_normalize_en_slang("She got caught in 4k.") == "She got caught red-handed with clear proof."
    assert T._pre_normalize_en_slang("Time to hit the sack.") == "Time to go to sleep."
    assert T._pre_normalize_en_slang("Don't sweat it.") == "do not worry about it."
    assert T._pre_normalize_en_slang("Hold your horses.") == "wait a minute and be patient."
    assert T._pre_normalize_en_slang("Defeating the boss is a piece of cake.") == "Defeating the boss is a very easy task."


def test_smart_scene_military_protection():
    # Dialog militer / taktikal tidak boleh diubah menjadi bahasa gaul kasual (seperti "nggak", "udah", "cowok")
    mil1 = "Batalyon 203, bersiaplah untuk serangan udara pada koordinat X-4."
    assert T._sanitize_gtxplus_id(mil1) == "Batalyon 203, bersiaplah untuk serangan udara pada koordinat X-4."

    mil2 = "Letnan Kolonel Tanya Degurechaff melaporkan situasi di garis depan."
    assert T._sanitize_gtxplus_id(mil2) == "Letnan Kolonel Tanya Degurechaff melaporkan situasi di garis depan."

    mil3 = "Pos komando telah hancur oleh artileri musuh. Saya tidak dapat menunda evakuasi ini."
    assert T._sanitize_gtxplus_id(mil3) == "Pos komando telah hancur oleh artileri musuh. Saya tidak dapat menunda evakuasi ini."


def test_smart_scene_royal_protection():
    # Dialog kerajaan / monarki harus menjaga kesopanan takzim baku
    royal1 = "Yang Mulia, hamba tidak dapat menyetujui keputusan pembubaran dewan kekaisaran."
    assert T._sanitize_gtxplus_id(royal1) == "Yang Mulia, hamba tidak dapat menyetujui keputusan pembubaran dewan kekaisaran."

    royal2 = "Tuan Putri menolak lamaran dari adipati utara."
    assert T._sanitize_gtxplus_id(royal2) == "Tuan Putri menolak lamaran dari adipati utara."

    royal3 = "Yang Mulia, gerbang ruang bawah tanah tingkat S telah dibuka oleh pasukan iblis."
    assert T._sanitize_gtxplus_id(royal3) == "Yang Mulia, gerbang dungeon tingkat S telah dibuka oleh pasukan iblis."


def test_smart_scene_casual_fansub():
    # Dialog kasual sekolah / sehari-hari dihaluskan menjadi diksi lisan alami fansub
    cas1 = "Tidak apa-apa, saya tidak tahu anda ada di sana."
    assert T._sanitize_gtxplus_id(cas1) == "Nggak apa-apa, aku nggak tahu kamu ada di sana."

    cas2 = "Lelaki itu sangat sombong, sudah kuduga dia penipu."
    assert T._sanitize_gtxplus_id(cas2) == "Cowok itu sangat sombong, emang udah kuduga dia penipu."


def test_slang_and_idioms_calque_sanitizer():
    # Memastikan calque harfiah dari Google Translate diubah ke bahasa fansub yang wajar
    assert T._sanitize_gtxplus_id("Aku harus memantul sekarang.") == "Aku harus cabut sekarang."
    assert T._sanitize_gtxplus_id("Tidak ada topi, itu keren sekali.") == "Beneran, itu keren sekali."
    assert T._sanitize_gtxplus_id("Kita diselamatkan oleh bel.") == "Kita selamat di saat kritis."
    assert T._sanitize_gtxplus_id("Cepat keluarkan ludahmu!") == "Cepat cepat katakan!"
    assert T._sanitize_gtxplus_id("Pegang kudamu sebentar.") == "Sabar dulu sebentar."
    assert T._sanitize_gtxplus_id("Dia tidak mendapat rimpang sama sekali.") == "Dia tidak punya pesona sama sekali."
    assert T._sanitize_gtxplus_id("Keluar dan sentuh rumput sana.") == "Keluar dan sadar realita sana."
    assert T._sanitize_gtxplus_id("Karakter itu punya baju besi plot.") == "Karakter itu punya kebal berkat skenario."
    assert T._sanitize_gtxplus_id("Dia memancarkan energi karakter utama.") == "Dia memancarkan aura protagonis."
    assert T._sanitize_gtxplus_id("Dia tertangkap di 4k kemarin.") == "Dia tertangkap basah ada buktinya kemarin."
    assert T._sanitize_gtxplus_id("Tim kita berhasil mengambil w!") == "Tim kita berhasil meraih kemenangan!"
    assert T._sanitize_gtxplus_id("Bos penjara bawah tanah telah bangkit.") == "Bos dungeon telah bangkit."
    assert T._sanitize_gtxplus_id("Tuan serikat memanggil kita ke aula.") == "Ketua guild memanggil kita ke aula."


def test_new_pre_gtx_slang_and_gaming():
    # Pre-GTX normalizer untuk slang dan terminologi game
    assert T._pre_normalize_en_slang("Are you for real right now?") == "seriously right now?"
    assert T._pre_normalize_en_slang("You're dead meat if he finds out.") == "you are finished if he finds out."
    assert T._pre_normalize_en_slang("Just cut the crap and tell me.") == "Just stop the nonsense and tell me."
    assert T._pre_normalize_en_slang("There is no way in hell we win.") == "There is impossible we win."
    assert T._pre_normalize_en_slang("Why are you freaking out?") == "Why are you panicking?"
    assert T._pre_normalize_en_slang("Are you messing with me?") == "Are you tricking me?"
    assert T._pre_normalize_en_slang("I am fed up with your excuses.") == "I am sick and tired of your excuses."
    assert T._pre_normalize_en_slang("Go easy on me today.") == "be gentle with me today."
    assert T._pre_normalize_en_slang("What on earth is that monster?") == "what exactly is that monster?"
    assert T._pre_normalize_en_slang("Are you kidding me?") == "are you joking?"
    assert T._pre_normalize_en_slang("Please make yourself at home.") == "Please feel comfortable as at home."
    assert T._pre_normalize_en_slang("Tank, pull aggro from the boss!") == "Tank, attracting enemy attention from the boss!"
    assert T._pre_normalize_en_slang("The monster returned to the spawn point.") == "The monster returned to the appearance location."
    assert T._pre_normalize_en_slang("A dungeon break occurred in city center.") == "A dungeon outbreak occurred in city center."
    assert T._pre_normalize_en_slang("Prepare to fight the raid boss.") == "Prepare to fight the large-scale boss."
    assert T._pre_normalize_en_slang("Talk to our party leader.") == "Talk to our group leader."


def test_new_gaming_and_dungeon_universal_rules():
    # 1. Dungeon & Ruang Bawah Tanah
    assert T._sanitize_gtxplus_id("Kita harus menghancurkan inti ruang bawah tanah itu.") == "Kita harus menghancurkan inti dungeon itu."
    assert T._sanitize_gtxplus_id("Hati-hati dengan jebakan ruang bawah tanah di depan.") == "Hati-hati dengan jebakan dungeon di depan."
    assert T._sanitize_gtxplus_id("Gerbang ruang bawah tanah tingkat A terbuka!") == "Gerbang dungeon tingkat A terbuka!"
    assert T._sanitize_gtxplus_id("Ini ledakan ruang bawah tanah, monster bermunculan!") == "Ini dungeon break, monster bermunculan!"
    assert T._sanitize_gtxplus_id("Para penjelajah ruang bawah tanah berkumpul di ruang bos.") == "Para penjelajah dungeon berkumpul di boss room."

    # 2. Party & Serikat/Guild
    assert T._sanitize_gtxplus_id("Semua anggota pesta siap memasuki lantai dungeon.") == "Semua anggota party siap memasuki lantai dungeon."
    assert T._sanitize_gtxplus_id("Pemimpin pesta kita memutuskan untuk membubarkan pesta.") == "Party leader kita memutuskan untuk membubarkan party."
    assert T._sanitize_gtxplus_id("Tunjukkan kartu serikat milikmu kepada staf serikat.") == "Tunjukkan kartu guild milikmu kepada resepsionis guild."
    assert T._sanitize_gtxplus_id("Kita harus membentuk pesta penyerbuan untuk melawan monster itu.") == "Kita harus membentuk party raid untuk melawan monster itu."

    # 3. Game Combat Mechanics & Stats
    assert T._sanitize_gtxplus_id("Tanker, segera menarik kebencian monster itu!") == "Tanker, segera menarik aggro monster itu!"
    assert T._sanitize_gtxplus_id("Monster itu muncul di titik bertelur.") == "Monster itu muncul di titik spawn."
    assert T._sanitize_gtxplus_id("Keahlian ini memiliki waktu pendinginan yang lama.") == "Keahlian ini memiliki waktu cooldown yang lama."
    assert T._sanitize_gtxplus_id("Tingkat drop item langka ini sangat rendah.") == "Drop rate item langka ini sangat rendah."
    assert T._sanitize_gtxplus_id("Bilah kesehatan dan bilah mana musuh sudah menipis.") == "Bar HP dan bar MP musuh udah menipis."
    assert T._sanitize_gtxplus_id("Bos serbuan telah dikalahkan oleh pemain tunggal itu.") == "Raid boss telah dikalahkan oleh pemain solo itu."
    assert T._sanitize_gtxplus_id("Dia adalah pemburu peringkat S yang terkenal.") == "Dia adalah hunter rank S yang terkenal."
    assert T._sanitize_gtxplus_id("Mage itu memberi penggemar status kepada seluruh tim.") == "Mage itu memberi buff status kepada seluruh tim."

    # 4. Calque MT Harfiah
    assert T._sanitize_gtxplus_id("Apakah kamu nyata? Kamu daging mati kalau bos melihatmu.") == "Kamu serius? Mampus kau kalau bos melihatmu."
    assert T._sanitize_gtxplus_id("Tidak ada cara di neraka kita bisa menang.") == "Mana mungkin kita bisa menang."
    assert T._sanitize_gtxplus_id("Potong omong kosong itu dan lawan aku!") == "Hentikan omong kosongmu itu dan lawan aku!"
    assert T._sanitize_gtxplus_id("Jangan ketakutan keluar, tenang saja.") == "Jangan panik banget, tenang aja."
    assert T._sanitize_gtxplus_id("Pergi mudah padaku, aku pemula.") == "Jangan kejam-kejam ya, aku pemula."
    assert T._sanitize_gtxplus_id("Silakan buat dirimu di rumah.") == "Silakan anggap aja rumah sendiri."


def test_new_casual_slang_smoothing():
    # Verifikasi penghalusan diksi lisan casual fansub
    assert T._sanitize_gtxplus_id("Kamu bercanda kan?") == "Kamu bercanda ya?"
    assert T._sanitize_gtxplus_id("Jangan macam-macam di depanku.") == "Jangan macam-macam deh di depanku."
    assert T._sanitize_gtxplus_id("Ada apa sebenarnya di sini?") == "Ada apa sih sebenarnya di sini?"
    assert T._sanitize_gtxplus_id("Kan sudah kubilang jangan ke sana.") == "Kan udah kubilang jangan ke sana."
    assert T._sanitize_gtxplus_id("Apa yang salah denganmu?") == "Kamu kenapa sih?"
    assert T._sanitize_gtxplus_id("Apa maumu datang ke mari?") == "Mau apa sih kamu datang ke mari?"
    assert T._sanitize_gtxplus_id("Aku tidak peduli dengan rumor itu.") == "Aku nggak peduli dengan rumor itu."
    assert T._sanitize_gtxplus_id("Tenanglah sedikit, jangan terburu-buru.") == "Santai dikit dong, jangan terburu-buru."


def test_fansub_prompt_id_tlc_master():
    """Memverifikasi Master Prompt Fansub & TLC Anime Indonesia."""
    prompt_id = T._fansub_system_prompt("English", "id", "Indonesian")
    
    # 1. Identitas & Persona TLC
    assert "penerjemah sekaligus editor (TLC/Translation Checker) fansub anime Indonesia" in prompt_id
    assert "Terjemahkan subtitle bahasa Inggris menjadi bahasa Indonesia" in prompt_id
    assert "PRINSIP UTAMA KELUWESAN FANSUB:" in prompt_id
    
    # 2. Aturan Nada Bahasa Sesuai Konteks Adegan
    assert "Adegan Formal / Berwibawa / Kerajaan / Militer:" in prompt_id
    assert "Adegan Santai / Sehari-hari / Komedi / Sekolah:" in prompt_id
    assert "KONSISTENSI PERSONA SEKOLAH:" in prompt_id
    assert "Adegan Kasar / Preman / Musuh:" in prompt_id
    
    # 3. Kosakata Tematik & Kamus
    assert "KOSAKATA GAME, ISEKAI & JOB SYSTEM:" in prompt_id
    assert "KOSAKATA MECHA & TAKTIS MILITER (Mecha & Tactical Sci-Fi):" in prompt_id
    assert "KOSAKATA DUNIA NINJA & SHONEN (Ninja / Shinobi - misal: Naruto):" in prompt_id
    assert "KOSAKATA DUNIA KUTUKAN, ROH & PENYIHIR MODERN (Jujutsu & Supernatural):" in prompt_id
    assert "KOSAKATA FANTASI ABADI, ELF & ATELIER SIHIR (Frieren, Witch Hat Atelier, dll.):" in prompt_id
    assert "KOSAKATA MISTERI SEKOLAH, KLUB SASTRA & ROM-COM OSIS (Hyouka, Kaguya-sama):" in prompt_id
    assert "KOSAKATA KULINER, OLAHRAGA, HISTORIS, CYBERPUNK & THRILLER:" in prompt_id
    assert "KAMUS IDIOM & UNGKAPAN KHAS FANSUB (DILARANG TERJEMAHKAN HARFIAH):" in prompt_id
    
    # 4. Contoh Multi-Scene & Format Keluaran
    assert "CONTOH MULTI-SCENE:" in prompt_id
    assert "1|Yang Mulia, pasukan ksatria garis depan telah bersiap." in prompt_id
    assert "5|What a drag... It can't be helped, I'll take care of this myself.<br>Just stand back!" in prompt_id
    assert "5|Merepotkan sekali... Mau gimana lagi, biar aku yang urus ini sendiri.<br>Kalian mundur saja!" in prompt_id

    # 5. Parsing & Round-trip output baris contoh
    sample_llm_out = (
        "1|Yang Mulia, pasukan ksatria garis depan telah bersiap. Kami tidak akan mengecewakan kepercayaan Anda.\n"
        "2|Cewek-cewek cakepnya mantap, kan? Incaranmu tinggi juga ya? Nibutani, kan?\n"
        "3|Kalau menurutku sih cakep banget. Nggak usah ditanya lagi, itu memalukan banget!\n"
        "4|Semua unit, segera meluncur! Lakukan manuver menghindar dan jangan lengah!\n"
        "5|Merepotkan sekali... Mau gimana lagi, biar aku yang urus ini sendiri.<br>Kalian mundur saja!"
    )
    parsed = T._parse_id_lines(sample_llm_out, {1, 2, 3, 4, 5})
    assert len(parsed) == 5
    assert "<br>" in parsed[5]
    restored_5 = T._restore_line(parsed[5])
    assert restored_5 == "Merepotkan sekali... Mau gimana lagi, biar aku yang urus ini sendiri.\nKalian mundur saja!"





