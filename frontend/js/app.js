var cur = {slug:"", title:"", ep:1, mode:"sub", quality:"best", res:null, eps:[], watched:{}, lastWatchedEp:null,
            subLang:"English",    // preferensi bahasa user dari /api/settings
            activeSub:null,       // URL track subtitle yang sedang aktif (live switch)
            cues:[],              // cue subtitle hasil parse VTT (render overlay milik app)
            subSize:"m",          // ukuran subtitle overlay: s|m|l|xl
            subFont:"sans",       // jenis huruf font: sans|rounded|tahoma|serif|mono|impact
            subColor:"#ffffff",   // warna font subtitle: #ffffff|#facc15|#38bdf8|#4ade80|#f472b6
            subBg:"medium",       // background kapsul: medium|dark|light|frosted|none
            subPos:"normal",      // posisi vertikal: low|normal|medium|high
            subDelay:0.0,         // sinkronisasi waktu subtitle (detik, mis. -0.5, +0.5)
            translate:false,      // toggle translate subtitle Indonesia (persist localStorage)
            eps_counter:"",
            intro:null,           // {start, end} opening
            outro:null,           // {start, end} ending
            hasAutoSkippedIntro:false,
            hasAutoSkippedOutro:false,
            activeSkipTarget:0,
            autoSkip:false
           };

var FONT_MAP = {
  "sans": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif',
  "rounded": 'Trebuchet MS, "Nunito", "Quicksand", sans-serif',
  "tahoma": 'Tahoma, Verdana, "Segoe UI", sans-serif',
  "serif": 'Georgia, "Times New Roman", "Yu Mincho", serif',
  "mono": '"SF Mono", "Cascadia Code", "Fira Code", Menlo, monospace',
  "impact": 'Impact, "Arial Black", "Trebuchet MS", sans-serif'
};

function getSubFontName(f){
  var m = {
    "sans": "Modern Sans (Default)",
    "rounded": "Clean Rounded",
    "tahoma": "Anime Fansub (Tahoma)",
    "serif": "Cinematic Serif",
    "mono": "Cyber Monospace",
    "impact": "Action Impact"
  };
  return m[f] || "Modern Sans";
}

function getSubColorName(c){
  var m = {
    "#ffffff": "Putih Bersih",
    "#facc15": "Kuning Emas",
    "#38bdf8": "Cyan Cyber",
    "#4ade80": "Hijau Lembut",
    "#f472b6": "Sakura Pink"
  };
  return m[c] || "Putih Bersih";
}

function getSubBgName(b){
  var m = {
    "medium": "Transparan (55%)",
    "dark": "Gelap Pekat (85%)",
    "light": "Tipis Halus (22%)",
    "frosted": "Frosted Blur",
    "none": "Tanpa Kotak"
  };
  return m[b] || "Transparan";
}

function getSubPosName(p){
  var m = { "low": "Sangat Bawah (10px)", "normal": "Bawah Normal (28px)", "medium": "Sedang (48px)", "high": "Tinggi (72px)" };
  return m[p] || "Normal";
}

function sanitizePosterUrl(u){
  if(!u || typeof u !== "string") return "";
  var s = u.trim();
  if(!s || s === "undefined" || s === "null") return "";
  // Tangkal domain poster non-aktif / unresolvable yang memicu net::ERR_NAME_NOT_RESOLVED
  if(s.indexOf("img.hianime.to") !== -1 || s.indexOf("example.com") !== -1 || s.indexOf("bookmark123.jpg") !== -1 || s.indexOf("test123.jpg") !== -1) {
    return "";
  }
  return s;
}
window.App = window.App || {};
window.App.sanitizePosterUrl = sanitizePosterUrl;

window.settings = window.settings || {};
var _playTokenCounter = 0;
var PLAYBACK_SPEEDS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0];
var currentPlaybackSpeed = 1.0;

function setSubDelay(sec, notify){
  var val = parseFloat(sec);
  if(isNaN(val)) val = 0.0;
  val = Math.round(val * 4) / 4; // presisi 0.25s
  val = Math.max(-30.0, Math.min(30.0, val));
  cur.subDelay = val;
  var el = $("pm-sub-delay-val");
  if(el){
    var sign = val > 0 ? "+" : "";
    el.textContent = sign + val.toFixed(val % 0.5 === 0 ? 1 : 2) + "s";
    el.classList.toggle("active", Math.abs(val) > 0.01);
  }
  paintCue();
  if(cur._rawVtt || (cur.cues && cur.cues.length)){
    syncNativeTextTrack(cur._rawVtt, cur.cues, cur.subLang);
  }
  if(window.art && window.art.setting && window.art.setting.cache && window.art.setting.cache.has("subtitle-delay")){
    try{
      var sgn = val > 0 ? "+" : "";
      window.art.setting.update({ name: "subtitle-delay", tooltip: sgn + val.toFixed(2) + "s" });
    }catch(_){}
  }
  if(notify){
    var signStr = val > 0 ? "+" : "";
    toast("Sinkronisasi Subtitle: " + signStr + val.toFixed(2) + "s", 1500, "icon-subtitles");
  }
}

function adjustSubDelay(delta){
  setSubDelay((cur.subDelay || 0.0) + delta, true);
}

function setPlaySpeed(spd, notify){
  var num = parseFloat(spd);
  if(isNaN(num) || num <= 0) num = 1.0;
  currentPlaybackSpeed = num;
  var v = $("vid");
  if(window.art){
    try { window.art.playbackRate = currentPlaybackSpeed; } catch(e){}
  } else if(v){
    try {
      v.playbackRate = currentPlaybackSpeed;
    } catch(e){}
  }
  var sel = $("pm-speed-select");
  if(sel){
    sel.value = String(currentPlaybackSpeed);
  }
  if(notify){
    toast("Kecepatan: " + currentPlaybackSpeed + "x", 1200, "icon-zap");
  }
}

function adjustPlaySpeed(dir){
  var idx = 2; // default 1.0x (index 2)
  for(var i = 0; i < PLAYBACK_SPEEDS.length; i++){
    if(Math.abs(PLAYBACK_SPEEDS[i] - currentPlaybackSpeed) < 0.05){
      idx = i;
      break;
    }
  }
  var nextIdx = idx + dir;
  if(nextIdx < 0) nextIdx = 0;
  if(nextIdx >= PLAYBACK_SPEEDS.length) nextIdx = PLAYBACK_SPEEDS.length - 1;
  setPlaySpeed(PLAYBACK_SPEEDS[nextIdx], true);
}

function $(id){return document.getElementById(id);}
function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");}
function isPlayerOpen(){
  var pm = $("player-modal");
  return !!(pm && !pm.classList.contains("hidden") && window.art && window.art.template);
}

function parseToastContent(rawMsg, customIcon){
  if(!rawMsg) return { icon: "icon-info", text: "" };
  var msg = String(rawMsg);

  // Jika pesan sudah berupa HTML yang di-render khusus, jangan modifikasi
  if(msg.indexOf("<svg") !== -1 && msg.indexOf("toast-text") !== -1){
    return { isRawHtml: true, html: msg };
  }

  var icon = customIcon || null;
  if(!icon){
    if(/⏩|Lewati|Melompat ke/i.test(msg)){
      icon = "icon-skip";
    } else if(/⏪|Rewind|^-\d+s/i.test(msg)){
      icon = "icon-rewind";
    } else if(/Forward|^\+\d+s/i.test(msg)){
      icon = "icon-forward";
    } else if(/Translate|Terjemahan/i.test(msg)){
      icon = "icon-globe";
    } else if(/Volume|Muted|Unmuted/i.test(msg)){
      icon = /Muted/i.test(msg) ? "icon-volume-mute" : "icon-volume-high";
    } else if(/Kecepatan/i.test(msg)){
      icon = "icon-zap";
    } else if(/Subtitle|Sinkronisasi Subtitle|Offset Subtitle/i.test(msg)){
      icon = "icon-subtitles";
    } else if(/Resolusi/i.test(msg)){
      icon = "icon-disc";
    } else if(/Mode Terang/i.test(msg)){
      icon = "icon-sun";
    } else if(/Mode Gelap/i.test(msg)){
      icon = "icon-moon";
    } else if(/🚀|Pembaruan|Update/i.test(msg)){
      icon = "icon-update";
    } else if(/✨|AI Fansub/i.test(msg)){
      icon = "icon-sparkles";
    } else if(/✓|berhasil|sukses|siap|terhubung/i.test(msg)){
      icon = "icon-check";
    } else if(/Gagal|Error|tidak aktif|Koneksi gagal/i.test(msg)){
      icon = "icon-server-alert";
    } else if(/⏳|Memproses|Mengunduh|Memeriksa/i.test(msg)){
      icon = "icon-hourglass";
    } else if(/Episode|Picture-in-Picture|PiP/i.test(msg)){
      icon = "icon-tv";
    } else {
      icon = "icon-info";
    }
  }

  // Bersihkan emoji mentah/kasar dari teks
  var cleanText = msg
    .replace(/^[⏩⏪⏳✨🚀✓ℹ️⚠️🔊\s]+/g, "")
    .replace(/[⏩⏪⏳✨🚀✓ℹ️⚠️🔊]/g, "")
    .trim();

  return { icon: icon, text: cleanText };
}

function showArtNotice(htmlContent, durationMs){
  if(!window.art || !window.art.template || !window.art.template.$noticeInner) return false;
  var art = window.art;
  var $noticeInner = art.template.$noticeInner;
  var $player = art.template.$player;
  if(!$noticeInner || !$player) return false;

  $noticeInner.innerHTML = htmlContent;
  $player.classList.add("art-notice-show");
  clearTimeout(art._customNoticeTimer);
  art._customNoticeTimer = setTimeout(function(){
    if($player) $player.classList.remove("art-notice-show");
  }, durationMs || 2000);
  return true;
}

function toast(msg, ms, customIcon){
  if(!msg) return;
  if(window.TatapSfx) TatapSfx.play("notify");
  var parsed = parseToastContent(msg, customIcon);
  var html = "";
  if(parsed.isRawHtml){
    html = parsed.html;
  } else {
    var iconClass = "toast-icon-wrap";
    if(parsed.icon === "icon-check") iconClass += " toast-icon-success";
    else if(parsed.icon === "icon-server-alert" || parsed.icon === "icon-alert") iconClass += " toast-icon-error";
    else if(parsed.icon === "icon-sparkles") iconClass += " toast-icon-ai";
    else if(parsed.icon === "icon-sun" || parsed.icon === "icon-moon") iconClass += " toast-icon-theme";

    html = '<span class="' + iconClass + '"><svg class="ui-icon toast-icon"><use href="#' + parsed.icon + '"/></svg></span><span class="toast-text">' + esc(parsed.text) + '</span>';
  }

  // HILANGKAN TOAST GANDA:
  // Jika pemutar video sedang aktif/terbuka, tampilkan HANYA di Artplayer in-player notice HUD.
  // Jangan pernah memunculkan #toast di dokumen luar secara bersamaan!
  if(isPlayerOpen()){
    var shown = showArtNotice(html, ms || 2000);
    if(shown){
      var tBox = $("toast");
      if(tBox) tBox.classList.add("hidden");
      return;
    }
  }

  // Jika pemutar video tidak aktif, tampilkan di #toast global
  var tBox = $("toast");
  if(tBox){
    tBox.innerHTML = html;
    tBox.classList.remove("hidden");
    clearTimeout(window._toastT);
    window._toastT = setTimeout(function(){
      tBox.classList.add("hidden");
    }, ms || 2200);
  }
}

/* =====================================================================
 * TvNavigationManager: 10-Foot UI D-Pad Spatial Navigation & Focus Stack
 * ===================================================================== */
var TvNavigationManager = (function(){
  var activeZone = "grid"; // "tabs" | "search" | "chips" | "grid" | "detail-modal" | "player-hud" | "settings-modal"
  var focusHistoryStack = [];
  var currentFocusedElement = null;
  var lastBackPressTime = 0;
  var searchMode = "nav"; // "nav" | "typing"
  var hudTimer = null;
  var _isTvDetected = false;

  var PLAYER_IDLE = "PLAYER_IDLE";
  var PLAYER_HUD_ACTIVE = "PLAYER_HUD_ACTIVE";
  var PLAYER_MODAL_ACTIVE = "PLAYER_MODAL_ACTIVE";
  var playerState = PLAYER_IDLE;

  function isTvMode(){
    if(_isTvDetected) return true;
    var ua = navigator.userAgent || "";
    if(/Android TV|GoogleTV|Large Screen|SmartTV|HbbTV|AppleTV|BRAVIA/i.test(ua)){
      _isTvDetected = true;
      return true;
    }
    return _isTvDetected;
  }

  function setTvMode(val){
    _isTvDetected = !!val;
  }

  function clearFocus(){
    var focused = document.querySelectorAll(".tv-focus");
    for(var i = 0; i < focused.length; i++){
      focused[i].classList.remove("tv-focus");
    }
    if(document.activeElement && document.activeElement !== document.body){
      try { document.activeElement.blur(); } catch(_){}
    }
    currentFocusedElement = null;
  }

  function setFocus(el, zone, options){
    if(!el) return;
    options = options || {};
    var oldFocused = document.querySelectorAll(".tv-focus");
    for(var i = 0; i < oldFocused.length; i++){
      if(oldFocused[i] !== el) oldFocused[i].classList.remove("tv-focus");
    }
    if(isTvMode()){
      el.classList.add("tv-focus");
    }
    currentFocusedElement = el;
    if(zone) activeZone = zone;

    if(options.scroll !== false){
      try {
        el.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
      } catch(e){
        try { el.scrollIntoView(false); } catch(_){}
      }
    }
    try {
      el.focus({ preventScroll: true });
    } catch(e){
      try { el.focus(); } catch(_){}
    }
  }

  function pushFocus(zone, triggerEl, metadata){
    var meta = metadata || {};
    focusHistoryStack.push({
      zone: zone || activeZone,
      el: triggerEl || currentFocusedElement || document.activeElement,
      index: (meta.index !== undefined ? meta.index : -1),
      scrollX: window.scrollX || window.pageXOffset || 0,
      scrollY: window.scrollY || window.pageYOffset || 0
    });
  }

  function popFocus(){
    return focusHistoryStack.pop() || null;
  }

  function restoreFocusState(fallbackSelector){
    var frame = popFocus();
    if(frame){
      if(frame.el && document.body.contains(frame.el)){
        setFocus(frame.el, frame.zone, { scroll: true });
        if(frame.scrollY > 0){
          try { window.scrollTo({ top: frame.scrollY, behavior: "smooth" }); } catch(_){}
        }
        return true;
      }
      if(frame.index >= 0 && frame.zone === "grid"){
        var card = document.querySelector('[data-idx="' + frame.index + '"]');
        if(card){
          setFocus(card, "grid", { scroll: true });
          return true;
        }
      }
    }
    if(fallbackSelector){
      var fb = document.querySelector(fallbackSelector);
      if(fb){
        setFocus(fb, activeZone, { scroll: true });
        return true;
      }
    }
    return false;
  }

  function saveFocusedIndex(containerSelector, itemSelector){
    var container = document.querySelector(containerSelector);
    if(!container) return -1;
    var items = Array.prototype.slice.call(container.querySelectorAll(itemSelector));
    for(var i = 0; i < items.length; i++){
      if(items[i].classList.contains("tv-focus") || items[i] === document.activeElement){
        return i;
      }
    }
    return -1;
  }

  function restoreFocusedIndex(containerSelector, itemSelector, savedIndex, defaultIndex){
    var container = document.querySelector(containerSelector);
    if(!container) return;
    var items = Array.prototype.slice.call(container.querySelectorAll(itemSelector));
    if(!items.length) return;
    var targetIdx = 0;
    if(savedIndex >= 0){
      targetIdx = Math.min(savedIndex, items.length - 1);
    } else if(defaultIndex !== undefined){
      targetIdx = Math.min(defaultIndex, items.length - 1);
    }
    setFocus(items[targetIdx], activeZone);
  }

  /* Dynamic 2D spatial navigation with bounding client rect & row clamping */
  function getSpatialTarget(currentEl, candidateList, direction){
    if(!currentEl || !candidateList || !candidateList.length) return null;
    var curRect = currentEl.getBoundingClientRect();
    var curCenterX = curRect.left + curRect.width / 2;
    var curCenterY = curRect.top + curRect.height / 2;

    var candidates = [];
    for(var i = 0; i < candidateList.length; i++){
      var c = candidateList[i];
      if(c === currentEl || c.offsetParent === null) continue;
      var r = c.getBoundingClientRect();
      candidates.push({ el: c, rect: r, cx: r.left + r.width / 2, cy: r.top + r.height / 2 });
    }
    if(!candidates.length) return null;

    if(direction === "left"){
      var leftCands = candidates.filter(function(item){
        return (Math.abs(item.cy - curCenterY) < curRect.height * 0.48) && (item.cx < curCenterX);
      });
      if(!leftCands.length) return null;
      leftCands.sort(function(a, b){ return b.cx - a.cx; });
      return leftCands[0].el;
    }

    if(direction === "right"){
      var rightCands = candidates.filter(function(item){
        return (Math.abs(item.cy - curCenterY) < curRect.height * 0.48) && (item.cx > curCenterX);
      });
      if(!rightCands.length) return null;
      rightCands.sort(function(a, b){ return a.cx - b.cx; });
      return rightCands[0].el;
    }

    if(direction === "down"){
      var belowCands = candidates.filter(function(item){
        return (item.rect.top >= curRect.bottom - 8) || (item.cy > curCenterY + curRect.height * 0.4);
      });
      if(!belowCands.length) return null;
      var minTop = Infinity;
      belowCands.forEach(function(item){
        if(item.rect.top < minTop) minTop = item.rect.top;
      });
      var nextRow = belowCands.filter(function(item){
        return item.rect.top <= minTop + 18;
      });
      if(!nextRow.length) return null;
      nextRow.sort(function(a, b){
        return Math.abs(a.cx - curCenterX) - Math.abs(b.cx - curCenterX);
      });
      return nextRow[0].el;
    }

    if(direction === "up"){
      var aboveCands = candidates.filter(function(item){
        return (item.rect.bottom <= curRect.top + 8) || (item.cy < curCenterY - curRect.height * 0.4);
      });
      if(!aboveCands.length) return null;
      var maxBottom = -Infinity;
      aboveCands.forEach(function(item){
        if(item.rect.bottom > maxBottom) maxBottom = item.rect.bottom;
      });
      var prevRow = aboveCands.filter(function(item){
        return item.rect.bottom >= maxBottom - 18;
      });
      if(!prevRow.length) return null;
      prevRow.sort(function(a, b){
        return Math.abs(a.cx - curCenterX) - Math.abs(b.cx - curCenterX);
      });
      return prevRow[0].el;
    }

    return null;
  }

  /* Player HUD State Machine */
  function resetHudTimer(){
    clearTimeout(hudTimer);
    if(playerState === PLAYER_MODAL_ACTIVE) return;
    hudTimer = setTimeout(function(){
      var v = $("vid");
      if(v && !v.paused){
        hidePlayerControls();
      }
    }, 4000);
  }

  function showPlayerControls(focusTarget){
    var stage = document.querySelector(".ambient-stage");
    var shell = document.querySelector(".player-shell");
    if(stage) stage.classList.remove("idle");
    if(shell) shell.classList.remove("idle");
    playerState = PLAYER_HUD_ACTIVE;
    resetHudTimer();
    if(focusTarget){
      setFocus(focusTarget, "player-hud");
    }
  }

  function hidePlayerControls(){
    var stage = document.querySelector(".ambient-stage");
    var shell = document.querySelector(".player-shell");
    var pm = $("player-modal");
    if(pm){
      var focused = pm.querySelectorAll(".tv-focus");
      for(var i = 0; i < focused.length; i++){
        focused[i].classList.remove("tv-focus");
      }
      if(document.activeElement && pm.contains(document.activeElement)){
        try { document.activeElement.blur(); } catch(_){}
      }
    }
    if(stage) stage.classList.add("idle");
    if(shell) shell.classList.add("idle");
    playerState = PLAYER_IDLE;
  }

  function setPlayerModalState(active){
    if(active){
      playerState = PLAYER_MODAL_ACTIVE;
      clearTimeout(hudTimer);
    } else {
      playerState = PLAYER_HUD_ACTIVE;
      resetHudTimer();
    }
  }

  /* Two-Stage Search Focus vs Virtual Keyboard */
  function enterSearchTypingMode(){
    var inp = $("cmd");
    if(!inp) return;
    searchMode = "typing";
    inp.removeAttribute("readonly");
    setFocus(inp, "search");
  }

  function exitSearchTypingMode(moveToResults){
    var inp = $("cmd");
    if(!inp) return;
    searchMode = "nav";
    inp.setAttribute("readonly", "readonly");
    try { inp.blur(); } catch(_){}
    var wrap = $("search-input-wrap");
    if(moveToResults){
      var res = $("results");
      var firstCard = res ? res.querySelector(".poster-card, .trow") : null;
      if(firstCard){
        setFocus(firstCard, "grid");
        if(typeof Tui !== "undefined" && Tui.renderSel){
          var idx = parseInt(firstCard.getAttribute("data-idx"), 10);
          if(!isNaN(idx)){
            Tui.state().sel = idx;
            Tui.renderSel();
          }
        }
      } else if(wrap){
        setFocus(wrap, "search");
      }
    } else if(wrap){
      setFocus(wrap, "search");
    }
  }

  /* 6-Level Back Button Hierarchy */
  function handleBack(e){
    // Level 1: Close Virtual Keyboard / Exit IME Typing
    var inp = $("cmd");
    var isCmdTyping = (inp && (document.activeElement === inp || searchMode === "typing"));
    var epFlt = $("ep-filter");
    var isEpFlt = (epFlt && document.activeElement === epFlt);
    if(isCmdTyping){
      if(e) e.preventDefault();
      exitSearchTypingMode(false);
      return true;
    }
    if(isEpFlt){
      if(e) e.preventDefault();
      epFlt.blur();
      var epBox = $("tm-eps");
      var firstEp = epBox ? epBox.querySelector(".ep.last-watch") || epBox.querySelector(".ep") : null;
      if(firstEp) setFocus(firstEp, "detail-modal");
      return true;
    }

    // Level 2: Close active Dialog / Sub-Modal (Spotlight, Resume, Settings, Genre, Filter, Drawer)
    var spM = $("spotlight-modal");
    if(spM && !spM.classList.contains("hidden")){
      if(e) e.preventDefault();
      if(typeof App !== "undefined" && App.closeSpotlight) App.closeSpotlight();
      else spM.classList.add("hidden");
      restoreFocusState();
      return true;
    }
    var resM = $("resume-modal");
    if(resM && !resM.classList.contains("hidden")){
      if(e) e.preventDefault();
      if(typeof App !== "undefined" && App.dismissResumeModal) App.dismissResumeModal();
      else resM.classList.add("hidden");
      restoreFocusState();
      return true;
    }
    var drw = $("drawer-panel");
    if(drw && !drw.classList.contains("hidden")){
      if(e) e.preventDefault();
      if(typeof App !== "undefined" && App.closeDrawer) App.closeDrawer();
      else drw.classList.add("hidden");
      restoreFocusState();
      return true;
    }
    var genM = $("genre-modal");
    if(genM && !genM.classList.contains("hidden")){
      if(e) e.preventDefault();
      if(typeof Tui !== "undefined" && Tui.closeGenreModal) Tui.closeGenreModal();
      else genM.classList.add("hidden");
      restoreFocusState();
      return true;
    }
    var cfM = $("catalog-filter-modal");
    if(cfM && !cfM.classList.contains("hidden")){
      if(e) e.preventDefault();
      if(typeof Tui !== "undefined" && Tui.closeCatalogFilterModal) Tui.closeCatalogFilterModal();
      else cfM.classList.add("hidden");
      restoreFocusState();
      return true;
    }
    var updM = $("update-modal");
    if(updM && !updM.classList.contains("hidden")){
      if(e) e.preventDefault();
      if(typeof App !== "undefined" && App.closeUpdateModal) App.closeUpdateModal();
      else updM.classList.add("hidden");
      restoreFocusState();
      return true;
    }
    var aiM = $("ai-settings-modal");
    if(aiM && !aiM.classList.contains("hidden")){
      if(e) e.preventDefault();
      closeAiSettingsModal();
      restoreFocusState();
      return true;
    }
    var ssm = $("sub-style-modal");
    if(ssm && !ssm.classList.contains("hidden")){
      if(e) e.preventDefault();
      cancelSubStyleModal();
      restoreFocusState();
      return true;
    }
    var hlp = $("help-overlay");
    if(hlp && !hlp.classList.contains("hidden")){
      if(e) e.preventDefault();
      hlp.classList.add("hidden");
      restoreFocusState();
      return true;
    }
    var beO = $("backend-error-overlay");
    if(beO && !beO.classList.contains("hidden")){
      if(e) e.preventDefault();
      beO.classList.add("hidden");
      return true;
    }

    // Level 3: Hide Player HUD if active
    var pm = $("player-modal");
    var isPlayerOpen = (pm && !pm.classList.contains("hidden"));
    if(isPlayerOpen && playerState === PLAYER_HUD_ACTIVE){
      if(e) e.preventDefault();
      hidePlayerControls();
      return true;
    }

    // Level 4: Exit Player to Detail Modal
    if(isPlayerOpen){
      if(e) e.preventDefault();
      closePlayer();
      return true;
    }

    // Level 5: Close Detail Anime to Main Grid
    var dp = $("detail-page");
    var tm = $("title-modal");
    if((dp && !dp.classList.contains("hidden")) || (tm && !tm.classList.contains("hidden"))){
      if(e) e.preventDefault();
      closeTitle();
      restoreFocusState();
      return true;
    }

    // Level 6: Main Screen Double-Back Confirmation
    if(typeof Tui !== "undefined" && Tui.view){
      var curV = Tui.view();
      if(curV !== "musim" && curV !== "katalog"){
        if(e) e.preventDefault();
        Tui.setView("musim");
        return true;
      }
    }
    var now = Date.now();
    if(now - lastBackPressTime < 2000){
      return false; // Confirmed exit
    } else {
      lastBackPressTime = now;
      if(e) e.preventDefault();
      if(typeof toast === "function"){
        toast("Tekan sekali lagi untuk keluar dari Tatap", 2000);
      }
      return true;
    }
  }

  return {
    PLAYER_IDLE: PLAYER_IDLE,
    PLAYER_HUD_ACTIVE: PLAYER_HUD_ACTIVE,
    PLAYER_MODAL_ACTIVE: PLAYER_MODAL_ACTIVE,
    isTvMode: isTvMode,
    setTvMode: setTvMode,
    activeZone: function(){ return activeZone; },
    setActiveZone: function(z){ activeZone = z; },
    playerState: function(){ return playerState; },
    setPlayerState: function(s){ playerState = s; },
    getHudTimer: function(){ return hudTimer; },
    setFocus: setFocus,
    clearFocus: clearFocus,
    pushFocus: pushFocus,
    popFocus: popFocus,
    restoreFocusState: restoreFocusState,
    saveFocusedIndex: saveFocusedIndex,
    restoreFocusedIndex: restoreFocusedIndex,
    getSpatialTarget: getSpatialTarget,
    resetHudTimer: resetHudTimer,
    showPlayerControls: showPlayerControls,
    hidePlayerControls: hidePlayerControls,
    setPlayerModalState: setPlayerModalState,
    enterSearchTypingMode: enterSearchTypingMode,
    exitSearchTypingMode: exitSearchTypingMode,
    handleBack: handleBack
  };
})();
window.TvNavigationManager = TvNavigationManager;
function loadPrefs(){
  try{
    if(localStorage.getItem("tatap_crt") === "on"){
      document.body.classList.remove("no-crt");
    } else {
      document.body.classList.add("no-crt");
    }
    if(localStorage.getItem("tatap_ambient") === "off"){
      document.body.classList.add("no-ambient");
    }
  }catch(e){}
}

function updateBookmarkBtn(isBookmarked){
  var btn = $("tm-bookmark-btn") || $("bookmarkBtn");
  if(!btn) return;
  btn.classList.toggle("bookmarked", !!isBookmarked);
  var starSvg = isBookmarked ? '<svg class="ui-icon"><use href="#icon-star-filled"/></svg>' : '<svg class="ui-icon"><use href="#icon-star"/></svg>';
  btn.innerHTML = starSvg + " " + (isBookmarked ? "TERSIMPAN" : "+ FAVORIT");
  btn.title = isBookmarked ? "Klik untuk menghapus dari favorit" : "Klik untuk menyimpan ke favorit";
}

function checkModalBookmark(slug){
  window.Tatap.checkBookmark(slug).then(function(r){
    if(cur.slug !== slug) return;
    if(r && r.success && r.data){
      updateBookmarkBtn(!!r.data.bookmarked);
    }
  }).catch(function(){});
}

function toggleModalBookmark(){
  var slug = cur.slug;
  if(!slug) return;
  var btn = $("tm-bookmark-btn") || $("bookmarkBtn");
  var currentlyBookmarked = btn && btn.classList.contains("bookmarked");
  var nextState = !currentlyBookmarked;
  updateBookmarkBtn(nextState);
  if(nextState){
    window.Tatap.addBookmark({
      slug: slug,
      title: cur.title,
      poster: cur.poster || "",
      type: cur.type || "TV",
      score: 0.0
    }).then(function(){
      if(window.Tui && ((typeof window.Tui.view === "function" && window.Tui.view() === "favorit") || (typeof window.Tui.state === "function" && window.Tui.state().view === "favorit"))){
        window.Tui.setView("favorit");
      }
    });
  } else {
    window.Tatap.removeBookmark(slug).then(function(){
      if(window.Tui && ((typeof window.Tui.view === "function" && window.Tui.view() === "favorit") || (typeof window.Tui.state === "function" && window.Tui.state().view === "favorit"))){
        window.Tui.setView("favorit");
      }
      // Unbookmark Subtitle Auto-Recovery:
      // Jika saat unbookmark episode sedang aktif dengan cur.mode === "sub" tetapi subtitle kosong (cur.cues.length === 0),
      // panggil ulang pemuatan episode/subtitle dengan parameter forceRefresh=true (refresh=1)
      var pm = $("player-modal");
      if(pm && !pm.classList.contains("hidden") && cur.mode === "sub" && (!cur.cues || cur.cues.length === 0) && cur.ep){
        var curTime = 0;
        var v = $("vid");
        if(v && !isNaN(v.currentTime)) curTime = v.currentTime;
        openPlayer(cur.ep, curTime, true);
      }
    });
  }
}
var toggleBookmark = toggleModalBookmark;
window.toggleBookmark = toggleModalBookmark;

function renderDetailMeta(meta){
  var box = $("tm-detail-meta");
  if(!box) return;
  if(!meta){
    box.classList.add("hidden");
    return;
  }
  var hasAny = false;

  // Score
  var scoreEl = $("tm-score");
  var scoreVal = $("tm-score-val");
  if(scoreEl && scoreVal){
    var sc = meta.score ? parseFloat(meta.score) : 0;
    if(sc > 0){
      scoreVal.textContent = sc.toFixed(1);
      scoreEl.classList.remove("hidden");
      hasAny = true;
    } else {
      scoreEl.classList.add("hidden");
    }
  }

  // Status
  var statEl = $("tm-status");
  if(statEl){
    var st = (meta.status || meta.badge || "").toLowerCase();
    var isFin = st.indexOf("finish") !== -1 || st.indexOf("tamat") !== -1 || st.indexOf("completed") !== -1 || Boolean(meta.is_finished);
    if(!isFin && meta.eps_counter){
      var parts = String(meta.eps_counter).split("/");
      if(parts.length === 2 && parts[1] !== "?"){
        var cCur = parseInt(parts[0], 10);
        var cTot = parseInt(parts[1], 10);
        if(!isNaN(cCur) && !isNaN(cTot) && cTot > 0 && cCur >= cTot){
          isFin = true;
        }
      }
    }
    if(isFin){
      statEl.textContent = "TAMAT";
      statEl.className = "badge-status finished";
      hasAny = true;
    } else if(st.indexOf("releas") !== -1 || st.indexOf("airing") !== -1 || st.indexOf("ongoing") !== -1){
      statEl.textContent = "ONGOING";
      statEl.className = "badge-status ongoing";
      hasAny = true;
    } else {
      statEl.className = "badge-status hidden";
    }
  }

  // Info Line (Studio / Musim / Sumber)
  var infoEl = $("tm-info-line");
  if(infoEl){
    var parts = [];
    if(meta.studio) parts.push("Studio: " + meta.studio);
    if(meta.season){
      var sTxt = meta.season;
      if(meta.year && sTxt.indexOf(String(meta.year)) === -1){
        sTxt += " " + meta.year;
      }
      parts.push(sTxt);
    } else if(meta.year){
      parts.push(String(meta.year));
    }
    if(meta.source) parts.push("Sumber: " + meta.source);
    if(parts.length > 0){
      infoEl.textContent = parts.join(" · ");
      infoEl.classList.remove("hidden");
      hasAny = true;
    } else {
      infoEl.textContent = "";
      infoEl.classList.add("hidden");
    }
  }

  // Genres
  var genEl = $("tm-genres");
  if(genEl){
    genEl.innerHTML = "";
    var gList = meta.genres || [];
    if(typeof gList === "string"){
      try { gList = JSON.parse(gList); } catch(e){ gList = gList.split(","); }
    }
    var validGenres = [];
    if(Array.isArray(gList)){
      validGenres = gList.map(function(x){ return (x||"").trim(); }).filter(function(x){ return x && x.toLowerCase() !== "hentai"; });
    }
    if(validGenres.length > 0){
      validGenres.forEach(function(g){
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "genre-pill interactive";
        btn.textContent = g;
        btn.title = "Filter anime berdasarkan genre: " + g;
        btn.onclick = function(e){
          e.stopPropagation();
          closeTitle();
          if(window.Tui && window.Tui.applyGenreFilter){
            window.Tui.applyGenreFilter(g);
          }
        };
        genEl.appendChild(btn);
      });
      genEl.classList.remove("hidden");
      hasAny = true;
    } else {
      genEl.classList.add("hidden");
    }
  }

  // Synopsis
  var synBox = $("tm-synopsis-box");
  var synText = $("tm-synopsis");
  var synToggle = $("tm-synopsis-toggle");
  if(synBox && synText && synToggle){
    var desc = (meta.synopsis || "").trim();
    if(desc){
      synText.textContent = desc;
      synText.classList.remove("expanded");
      synText.classList.add("clamped");
      synToggle.textContent = "Selengkapnya ▼";
      synBox.classList.remove("hidden");
      hasAny = true;

      synToggle.onclick = function(){
        if(synText.classList.contains("clamped")){
          synText.classList.remove("clamped");
          synText.classList.add("expanded");
          synToggle.textContent = "Tutup Sinopsis ▲";
        } else {
          synText.classList.remove("expanded");
          synText.classList.add("clamped");
          synToggle.textContent = "Selengkapnya ▼";
        }
      };
    } else {
      synBox.classList.add("hidden");
    }
  }

  if(hasAny){
    box.classList.remove("hidden");
  } else {
    box.classList.add("hidden");
  }
}

var _savedScrollY = 0;
var _savedView = "";

function renderDetailCoverAndPoster(bannerUrl, posterUrl){
  var bannerImg = $("detail-banner-img");
  var bannerAmbient = $("detail-banner-ambient");
  var posterImg = $("detail-poster-img");

  if(posterImg && posterUrl){
    posterImg.src = posterUrl;
    posterImg.alt = cur.title || "Poster";
  }

  if(bannerUrl){
    if(bannerImg){
      bannerImg.src = bannerUrl;
      bannerImg.classList.remove("hidden");
    }
    if(bannerAmbient){
      bannerAmbient.style.backgroundImage = "none";
      bannerAmbient.style.opacity = "0";
    }
  } else if(posterUrl){
    if(bannerImg){
      bannerImg.src = posterUrl;
      bannerImg.classList.remove("hidden");
    }
    if(bannerAmbient){
      bannerAmbient.style.backgroundImage = "url('" + posterUrl + "')";
      bannerAmbient.style.opacity = "0.7";
    }
  } else {
    if(bannerImg) bannerImg.classList.add("hidden");
    if(bannerAmbient){
      bannerAmbient.style.backgroundImage = "none";
      bannerAmbient.style.opacity = "0";
    }
  }
}

function updateQuickPlayBtn(){
  var btn = $("btn-quick-play");
  var lbl = $("quick-play-label");
  if(!btn || !lbl) return;
  var ep = cur.lastWatchedEp || 1;
  if(cur.lastWatchedEp && cur.lastWatchedEp > 1){
    lbl.textContent = "Lanjutkan Ep " + cur.lastWatchedEp;
    btn.title = "Lanjutkan menonton episode " + cur.lastWatchedEp;
  } else {
    lbl.textContent = "Putar Episode 1";
    btn.title = "Mulai menonton dari episode 1";
  }
}

function openTitle(slug,title,poster,type,epsCounter,meta){
  if(window.TatapSfx) TatapSfx.play("select");
  var triggerCard = document.querySelector(".poster-card.sel, .poster-card.tv-focus, .trow.sel, .trow.tv-focus") || document.activeElement;
  TvNavigationManager.pushFocus("grid", triggerCard, { index: (typeof Tui !== "undefined" && Tui.state ? Tui.state().sel : -1) });
  TvNavigationManager.setActiveZone("detail-modal");
  cur.slug=slug;cur.title=title;cur.poster=poster||cur.poster||"";cur.type=type||cur.type||"";cur.eps=[];
  cur.eps_counter=epsCounter||"";
  cur.lastWatchedEp=null;
  cur.watched={};
  cur.activeEpRange=null;
  cur.meta=meta||null;
  cur.res=null; // Bersihkan stream cache lama agar snapshot bookmark tidak menimpa state stream
  if(meta && meta.sub){
    cur.subCount = meta.sub; // Simpan metadata jumlah episode subbed ke properti terpisah
  }
  if(meta && (meta.mode === "dub" || meta.mode === "sub")){
    cur.mode = meta.mode;
  } else if(!cur.mode || (cur.mode !== "dub" && cur.mode !== "sub")){
    cur.mode = "sub";
  }
  syncSeg("mode-seg", "mode", cur.mode);
  setPlaySpeed(1.0, false);
  renderSourceUI();
  $("tm-title").textContent=title;
  var subText = slug;
  if(meta){
    if(meta.title_romaji && meta.title_romaji !== title){
      subText = meta.title_romaji;
    } else if(meta.title_english && meta.title_english !== title){
      subText = meta.title_english;
    } else if(meta.title_native && meta.title_native !== title){
      subText = meta.title_native;
    }
  }
  $("tm-sub").textContent = subText;
  $("tm-eyebrow").textContent="DETAIL ANIME";
  $("tm-count").textContent="memuat...";
  $("tm-eps").innerHTML="";
  $("ep-filter").value="";
  var sBar=$("tm-seasons");if(sBar)sBar.classList.add("hidden");
  var sChips=$("tm-seasons-chips");if(sChips)sChips.innerHTML="";
  renderDetailMeta(meta);
  updateBookmarkBtn(false);
  checkModalBookmark(slug);

  // Simpan posisi scroll & tampilan sebelumnya
  _savedScrollY = window.scrollY || window.pageYOffset || 0;
  var sbView = $("sb-view");
  if(sbView) _savedView = sbView.textContent || "";

  // Sembunyikan katalog grid, buka dedicated detail page
  var searchSec = $("search-sec");
  if(searchSec) searchSec.classList.add("hidden");
  var contSec = $("continue-sec");
  if(contSec) contSec.classList.add("hidden");
  var pager = $("pager");
  if(pager) pager.classList.add("hidden");

  var detailPage = $("detail-page");
  if(detailPage) detailPage.classList.remove("hidden");
  document.body.classList.add("in-detail-view");
  window.scrollTo({ top: 0, behavior: "instant" });

  var crumbTitle = $("detail-nav-title");
  if(crumbTitle) crumbTitle.textContent = title || "Detail Anime";
  var typeBadge = $("detail-badge-type");
  if(typeBadge) typeBadge.textContent = (type || cur.type || "TV SERIES").toUpperCase();

  renderDetailCoverAndPoster(meta && meta.banner ? meta.banner : "", cur.poster);
  updateQuickPlayBtn();
  if(sbView) sbView.textContent = "detail: " + (title || slug);

  loadEps();
  loadRelations();
}
function loadRelations(){
  var thisSlug=cur.slug;
  window.Tatap.relations(thisSlug, cur.title).then(function(r){
    if(thisSlug!==cur.slug)return; // Stale modal
    var sBar=$("tm-seasons");
    var sChips=$("tm-seasons-chips");
    if(!sBar||!sChips)return;
    if(!r||!r.success||!r.data||!r.data.relations||!r.data.relations.length){
      sBar.classList.add("hidden");
      return;
    }
    var rels=r.data.relations;
    sChips.innerHTML="";
    var count=0;
    for(var i=0;i<rels.length;i++){
      (function(rel){
        if(!rel.slug || rel.slug === thisSlug)return; // Lewati jika belum termap ke sumber video atau menunjuk ke anime aktif
        count++;
        var b=document.createElement("button");
        b.type="button";
        var cls="season-chip vertical-item";
        var icon='<svg class="ui-icon"><use href="#icon-tv"/></svg>';
        var formatTag = rel.format || "TV";
        if(rel.format==="MOVIE"){cls+=" movie";icon='<svg class="ui-icon"><use href="#icon-film"/></svg>';formatTag="MOVIE";}
        else if(rel.format==="OVA"||rel.format==="SPECIAL"||rel.format==="ONA"){cls+=" special";icon='<svg class="ui-icon"><use href="#icon-disc"/></svg>';formatTag=rel.format;}
        else if(rel.relation==="PREQUEL"){cls+=" prequel";icon='<svg class="ui-icon"><use href="#icon-step-prev"/></svg>';formatTag="PREQUEL";}
        else if(rel.relation==="SEQUEL"){cls+=" sequel";icon='<svg class="ui-icon"><use href="#icon-step-next"/></svg>';formatTag="SEQUEL";}
        b.className=cls;
        b.title=rel.title+(rel.year?" ("+rel.year+")":"");
        b.innerHTML=
          '<div class="season-item-main">' +
            '<span class="season-badge-tag">'+icon+' '+esc(rel.label || formatTag)+'</span>' +
            '<span class="season-item-title">'+esc(rel.title)+'</span>' +
          '</div>' +
          (rel.year ? ('<span class="season-item-year">'+esc(rel.year)+'</span>') : '<span class="season-item-arrow">→</span>');
        b.addEventListener("click",function(e){
          if(e)e.stopPropagation();
          openTitle(rel.slug,rel.title);
        });
        sChips.appendChild(b);
      })(rels[i]);
    }
    if(count>0){
      sBar.classList.remove("hidden");
      var lbl=sBar.querySelector(".seasons-label");
      if(lbl) lbl.textContent="SEASON & TERKAIT ("+count+"):";
    }else{
      sBar.classList.add("hidden");
    }
  }).catch(function(){
    var sBar=$("tm-seasons");if(sBar)sBar.classList.add("hidden");
  });
}
var _epsMemCache = {};
cur.activeEpRange = null;

function recordEpisodeWatched(slug, ep){
  if(!slug || !ep) return;
  ep = parseInt(ep);
  if(isNaN(ep)) return;
  if(!cur.watched) cur.watched = {};
  if(cur.slug === slug){
    cur.watched[ep] = 1;
    cur.lastWatchedEp = ep;
  }

  try {
    localStorage.setItem("tatap_last_ep_" + slug, String(ep));
    var wKey = "tatap_watched_" + slug;
    var wObj = {};
    try { wObj = JSON.parse(localStorage.getItem(wKey) || "{}"); } catch(e){}
    wObj[ep] = 1;
    localStorage.setItem(wKey, JSON.stringify(wObj));
  } catch(e){}

  window.Tatap.saveHist({
    slug: slug,
    title: cur.title || slug,
    episode: ep,
    mode: cur.mode || "sub",
    progress: 0,
    poster: cur.poster || "",
    type: cur.type || ""
  }).then(function(){
    renderContinue();
  }).catch(function(){});
}

function renderEpRanges(){
  var bar = $("tm-ep-ranges");
  if(!bar) return;
  if(!cur.eps || cur.eps.length <= 100){
    bar.innerHTML = "";
    bar.classList.add("hidden");
    cur.activeEpRange = null;
    return;
  }
  bar.innerHTML = "";
  bar.classList.remove("hidden");
  var total = cur.eps.length;
  var step = 100;
  var lastWatchedEp = cur.lastWatchedEp || -1;
  if(lastWatchedEp <= 0 && cur.slug){
    try {
      var sLast = localStorage.getItem("tatap_last_ep_" + cur.slug);
      if(sLast) lastWatchedEp = parseInt(sLast);
    } catch(e){}
  }
  if(lastWatchedEp <= 0 && cur.watched){
    for(var w in cur.watched){
      var n = parseInt(w);
      if(n > lastWatchedEp) lastWatchedEp = n;
    }
  }
  if(lastWatchedEp > 0) cur.lastWatchedEp = lastWatchedEp;

  var ranges = [];
  for(var s = 1; s <= total; s += step){
    var e = Math.min(s + step - 1, total);
    ranges.push({start: s, end: e, label: s + " - " + e});
  }

  if(!cur.activeEpRange){
    cur.activeEpRange = ranges[0];
    if(lastWatchedEp > 0){
      for(var r = 0; r < ranges.length; r++){
        if(lastWatchedEp >= ranges[r].start && lastWatchedEp <= ranges[r].end){
          cur.activeEpRange = ranges[r];
          break;
        }
      }
    }
  } else {
    var found = false;
    for(var k = 0; k < ranges.length; k++){
      if(cur.activeEpRange.start === ranges[k].start){
        cur.activeEpRange = ranges[k];
        found = true;
        break;
      }
    }
    if(!found) cur.activeEpRange = ranges[0];
  }

  ranges.forEach(function(rng){
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "ep-range-chip" + (cur.activeEpRange && cur.activeEpRange.start === rng.start ? " active" : "");
    btn.textContent = rng.label;
    btn.addEventListener("click", function(e){
      if(e) e.stopPropagation();
      cur.activeEpRange = rng;
      renderEpRanges();
      renderEpGrid();
    });
    bar.appendChild(btn);
  });

  setTimeout(function(){
    var activeBtn = bar.querySelector(".ep-range-chip.active");
    if(activeBtn && typeof activeBtn.scrollIntoView === "function"){
      try { activeBtn.scrollIntoView({ inline: "nearest", block: "nearest", behavior: "smooth" }); } catch(_){}
    }
  }, 10);
}

function loadEps(){
  cur.activeEpRange = null;
  cur.lastWatchedEp = null;
  cur.watched = {};
  var thisSlug = cur.slug;
  if(thisSlug){
    try {
      var localWatched = JSON.parse(localStorage.getItem("tatap_watched_" + thisSlug) || "{}");
      cur.watched = Object.assign({}, localWatched);
      var s = localStorage.getItem("tatap_last_ep_" + thisSlug);
      if(s) cur.lastWatchedEp = parseInt(s);
    } catch(e){}
  }

  var countLabel = function(){
    var base = cur.eps.length + " episode";
    if(cur.eps_counter){
      var parts = cur.eps_counter.split('/');
      if(parts.length === 2 && parts[1] && parts[1] !== '?'){
        base = cur.eps.length + "/" + parts[1] + " episode rilis";
      } else {
        base = cur.eps.length + " episode rilis";
      }
    }
    return base + " · " + cur.mode.toUpperCase();
  };
  var cached = _epsMemCache[thisSlug];
  if(cached && thisSlug === cur.slug){
    cur.eps = cached;
    $("tm-count").textContent = countLabel();
    renderEpRanges();
    renderEpGrid();
  }

  window.Tatap.episodes(thisSlug, cur.title).then(function(r){
    if(thisSlug !== cur.slug) return;
    if(!r.success){
      if(!cached) $("tm-count").textContent = "error: " + r.error;
      return;
    }
    cur.eps = r.data.episodes || [];
    _epsMemCache[thisSlug] = cur.eps;
    if(r.data.detail || r.data.synopsis){
      var detail = Object.assign({}, cur.meta || {}, r.data.detail || {});
      if(r.data.synopsis && (!detail.synopsis || r.data.synopsis.length > detail.synopsis.length)){
        detail.synopsis = r.data.synopsis;
      }
      cur.meta = detail;
      renderDetailMeta(detail);

      var subText = cur.title;
      if(detail.title_romaji && detail.title_romaji !== cur.title){
        subText = detail.title_romaji;
      } else if(detail.title_english && detail.title_english !== cur.title){
        subText = detail.title_english;
      } else if(detail.title_native && detail.title_native !== cur.title){
        subText = detail.title_native;
      } else {
        subText = cur.slug;
      }
      var subEl = $("tm-sub");
      if(subEl) subEl.textContent = subText;
    }
    var respBanner = (r.data.banner || (r.data.detail && r.data.detail.banner)) || "";
    var respCover = (r.data.cover || (r.data.detail && r.data.detail.cover)) || "";
    var respPoster = (r.data.poster || (r.data.detail && r.data.detail.poster)) || respCover || "";
    if(!cur.poster && respPoster){
      cur.poster = respPoster;
    }
    if(respBanner && (!cur.meta || !cur.meta.banner)){
      if(!cur.meta) cur.meta = {};
      cur.meta.banner = respBanner;
    }
    renderDetailCoverAndPoster(respBanner || (cur.meta && cur.meta.banner), cur.poster);

    window.Tatap.history().then(function(h){
      if(thisSlug !== cur.slug) return;
      var foundInHist = false;
      (h.data || []).forEach(function(x){
        if(x.slug === thisSlug){
          foundInHist = true;
          if(!cur.poster && x.poster) cur.poster = x.poster;
          if(!cur.type && x.type) cur.type = x.type;
          if(!cur.watched) cur.watched = {};
          cur.watched[x.episode] = 1;
          cur.lastWatchedEp = x.episode;
        }
      });
      if(foundInHist && thisSlug === cur.slug && cur.lastWatchedEp){
        try {
          var wKey = "tatap_watched_" + thisSlug;
          var wObj = {};
          try { wObj = JSON.parse(localStorage.getItem(wKey) || "{}"); } catch(e){}
          for(var k in cur.watched){ wObj[k] = 1; }
          localStorage.setItem(wKey, JSON.stringify(wObj));
          localStorage.setItem("tatap_last_ep_" + thisSlug, String(cur.lastWatchedEp));
        } catch(e){}
      }
      updateQuickPlayBtn();
      $("tm-count").textContent = countLabel();
      renderEpRanges();
      renderEpGrid();
    }).catch(function(){
      if(thisSlug !== cur.slug) return;
      updateQuickPlayBtn();
      $("tm-count").textContent = countLabel();
      renderEpRanges();
      renderEpGrid();
    });
  });
}

function renderEpGrid(){
  var f = $("ep-filter").value.trim();
  var box = $("tm-eps");
  box.innerHTML = "";
  var shown = 0;
  var frag = document.createDocumentFragment();

  var epsToRender = cur.eps || [];
  var useRange = !f && cur.activeEpRange;

  if(!f && cur.activeEpRange && cur.eps && cur.eps.length > 100){
    var cntEl = $("tm-count");
    if(cntEl){
      cntEl.textContent = cur.eps.length + " ep (" + cur.activeEpRange.label + ") · " + (cur.mode||"SUB").toUpperCase();
    }
  }

  var lastEp = cur.lastWatchedEp;
  if(!lastEp && cur.slug){
    try {
      var storedLast = localStorage.getItem("tatap_last_ep_" + cur.slug);
      if(storedLast) lastEp = parseInt(storedLast);
    } catch(e){}
  }

  for(var i = 0; i < epsToRender.length; i++){
    var epObj = epsToRender[i];
    var ep = epObj.ep;
    if(f && String(ep).indexOf(f) < 0) continue;
    if(useRange && (ep < cur.activeEpRange.start || ep > cur.activeEpRange.end)) continue;

    shown++;
    var b = document.createElement("button");
    var isLast = (lastEp && ep === lastEp);
    var isWatched = (cur.watched && cur.watched[ep]);

    var cls = "ep";
    if(isLast){
      cls += " last-watch";
    } else if(isWatched){
      cls += " watched";
    }
    b.className = cls;

    if(isLast){
      b.innerHTML = '<span class="ep-num">' + ep + '</span><span class="ep-badge-last">TERAKHIR</span>';
      b.title = "Episode " + ep + " (Terakhir ditonton)";
    } else {
      b.textContent = ep;
      if(isWatched) b.title = "Episode " + ep + " (Sudah ditonton)";
    }

    (function(targetEp){
      b.addEventListener("click", function(e){
        if(e) e.stopPropagation();
        openPlayer(targetEp);
      });
    })(ep);
    frag.appendChild(b);
  }

  if(shown > 0){
    box.appendChild(frag);
    setTimeout(function(){
      var activeBtn = box.querySelector(".ep.last-watch") || box.querySelector(".ep");
      if(activeBtn){
        try {
          activeBtn.scrollIntoView({behavior: "smooth", block: "nearest", inline: "nearest"});
          activeBtn.focus({preventScroll: true});
          TvNavigationManager.setFocus(activeBtn, "detail-modal", { scroll: false });
        } catch(e){}
      }
    }, 50);
  } else {
    box.innerHTML = "<p class='dim'>Tidak ada episode cocok filter.</p>";
  }
}
function closeTitle(){
  if(window.TatapSfx) TatapSfx.play("back");
  document.body.classList.remove("in-detail-view");
  var detailPage = $("detail-page");
  if(detailPage) detailPage.classList.add("hidden");
  var titleModal = $("title-modal");
  if(titleModal) titleModal.classList.add("hidden");

  var searchSec = $("search-sec");
  if(searchSec) searchSec.classList.remove("hidden");
  var contSec = $("continue-sec");
  if(contSec && contSec.querySelector("#continue-row") && contSec.querySelector("#continue-row").children.length > 0){
    contSec.classList.remove("hidden");
  }
  var pager = $("pager");
  if(pager && window.Tui && window.Tui.state && window.Tui.state().lastPage > 1){
    pager.classList.remove("hidden");
  }

  if(_savedView && $("sb-view")){
    $("sb-view").textContent = _savedView;
  }

  window.scrollTo({ top: _savedScrollY || 0, behavior: "instant" });
  TvNavigationManager.restoreFocusState(".poster-card.sel, .poster-card");
  if(typeof Tui!=="undefined"&&Tui.renderSel){
    setTimeout(function(){ Tui.renderSel(); }, 30);
  }
}
function syncSeg(){
  document.querySelectorAll("#mode-seg button").forEach(function(x){x.classList.toggle("active",x.getAttribute("data-mode")===cur.mode);});
}

function formatTimeSec(sec){
  sec = Math.max(0, Math.floor(sec || 0));
  var m = Math.floor(sec / 60);
  var s = sec % 60;
  if(m >= 60){
    var h = Math.floor(m / 60);
    m = m % 60;
    return h + ":" + (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }
  return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
}

var _lastProgressSaveTime = 0;
function recordWatchProgress(force){
  if(!cur.slug || !cur.ep) return;
  var now = Date.now();
  if(!force && (now - _lastProgressSaveTime < 5000)) return;
  _lastProgressSaveTime = now;
  var curPos = 0;
  var dur = 0;
  if(window.art && typeof window.art.currentTime === "number" && !isNaN(window.art.currentTime)){
    curPos = Math.floor(window.art.currentTime || 0);
    dur = Math.floor(window.art.duration || 0);
  } else {
    var v = $("vid");
    if(v && !isNaN(v.currentTime)){
      curPos = Math.floor(v.currentTime || 0);
      dur = Math.floor(v.duration || 0);
    }
  }
  if(curPos <= 0 && !force) return;
  window.Tatap.saveProgress(cur.slug, cur.ep, curPos, dur).then(function(){
    renderContinue();
  }).catch(function(){});

  // Predictive Next-Episode Pre-resolving:
  // Ketika tontonan mencapai >= 70% atau > 240 detik pemutaran stabil,
  // resolve episode berikutnya di background agar pergantian episode menjadi 0ms (instan).
  if(dur > 90 && curPos > 0 && (curPos / dur >= 0.70 || curPos >= 240)){
    var preKey = cur.slug + ":" + (cur.ep + 1);
    if(window._lastPreResolvedEp !== preKey){
      window._lastPreResolvedEp = preKey;
      var nextEp = cur.ep + 1;
      var canPre = true;
      if(cur.totalEps && nextEp > cur.totalEps) canPre = false;
      if(canPre && window.Tatap && window.Tatap.resolve){
        window.Tatap.resolve(cur.slug, nextEp, cur.mode, cur.quality, cur.source || "", false, cur.title).catch(function(){});
      }
    }
  }
}

var _activeResumeCleanup = null;
function closeResumeModal(){
  if(_activeResumeCleanup){
    _activeResumeCleanup();
    _activeResumeCleanup = null;
  }
  var rm = $("resume-modal");
  if(rm) rm.classList.add("hidden");
}

function dismissResumeModal(){
  cur.playToken = ++_playTokenCounter;
  var savedSlug = cur.slug;
  var savedTitle = cur.title;
  var savedPoster = cur.poster;
  var savedType = cur.type;
  var savedCounter = cur.eps_counter;

  closeResumeModal();

  if(savedSlug){
    var dp = $("detail-page");
    var tm = $("title-modal");
    if((dp && dp.classList.contains("hidden")) || (tm && tm.classList.contains("hidden"))){
      openTitle(savedSlug, savedTitle, savedPoster, savedType, savedCounter);
    } else {
      if(dp){
        dp.classList.remove("hidden");
        document.body.classList.add("in-detail-view");
      }
      if(tm) tm.classList.remove("hidden");
      renderEpGrid();
    }
  }
}

function openPlayer(ep, resumeTime, forceRefresh){
  if(window.TatapSfx) TatapSfx.play("select");
  if(resumeTime === undefined && !forceRefresh){
    var fetchToken = ++_playTokenCounter;
    cur.playToken = fetchToken;
    var reqSlug = cur.slug;
    window.Tatap.getProgress(reqSlug, ep).then(function(r){
      if(cur.playToken !== fetchToken || cur.slug !== reqSlug) return;
      if(r && r.success && r.data && r.data.should_resume && r.data.progress >= 15){
        var p = r.data.progress;
        var dur = r.data.duration || 0;
        var fTime = r.data.formatted || formatTimeSec(p);
        var fDur = (dur > 0) ? formatTimeSec(dur) : "--:--";
        var pct = (dur > 0) ? Math.min(100, Math.max(1, Math.round((p / dur) * 100))) : 0;
        var modal = $("resume-modal");
        if(modal){
          TvNavigationManager.pushFocus("detail-modal", document.querySelector(".ep.tv-focus") || document.activeElement);
          TvNavigationManager.setPlayerModalState(true);
          var animeTitle = cur.title || "Lanjutkan Menonton?";
          var titleEl = $("rm-title");
          if(titleEl){
            titleEl.textContent = animeTitle;
            titleEl.setAttribute("title", animeTitle);
          }
          $("rm-sub").innerHTML = "<span class='rm-badge-ep'>EP " + ep + "</span> Tersimpan pada " + fTime + (dur > 0 ? (" dari " + fDur) : "");
          $("rm-time").textContent = fTime;
          $("rm-resume-label").textContent = "Lanjutkan (" + fTime + ")";

          var fillEl = $("rm-progress-fill");
          if(fillEl) fillEl.style.width = pct + "%";
          var curEl = $("rm-time-current");
          if(curEl) curEl.textContent = fTime;
          var totEl = $("rm-time-total");
          if(totEl) totEl.textContent = (dur > 0) ? fDur : "";
          var badgeEl = $("rm-percent-badge");
          if(badgeEl){
            badgeEl.textContent = (pct > 0) ? (pct + "% selesai") : "Tersimpan";
          }

          var bResume = $("rm-btn-resume");
          var bRestart = $("rm-btn-restart");
          var bCancel = $("rm-btn-cancel");
          var bClose = $("rm-close");

          var btns = [bResume, bRestart, bCancel].filter(Boolean);
          var keyHandler = function(e){
            if(modal.classList.contains("hidden")) return;
            if(e.key === "ArrowLeft" || e.key === "ArrowUp"){
              e.preventDefault();
              var idx = btns.indexOf(document.activeElement);
              var prevIdx = (idx <= 0) ? btns.length - 1 : idx - 1;
              if(btns[prevIdx]) TvNavigationManager.setFocus(btns[prevIdx], "settings-modal");
            } else if(e.key === "ArrowRight" || e.key === "ArrowDown"){
              e.preventDefault();
              var idx = btns.indexOf(document.activeElement);
              var nextIdx = (idx >= btns.length - 1 || idx === -1) ? 0 : idx + 1;
              if(btns[nextIdx]) TvNavigationManager.setFocus(btns[nextIdx], "settings-modal");
            } else if(e.key === "Escape"){
              e.preventDefault();
              dismissResumeModal();
            }
          };

          var cleanupModal = function(){
            modal.classList.add("hidden");
            window.removeEventListener("keydown", keyHandler);
            TvNavigationManager.setPlayerModalState(false);
            if(bResume) bResume.onclick = null;
            if(bRestart) bRestart.onclick = null;
            if(bCancel) bCancel.onclick = null;
            if(bClose) bClose.onclick = null;
            _activeResumeCleanup = null;
          };
          _activeResumeCleanup = cleanupModal;

          if(bResume){
            bResume.onclick = function(){
              cleanupModal();
              openPlayer(ep, p);
            };
          }

          if(bRestart){
            bRestart.onclick = function(){
              cleanupModal();
              window.Tatap.saveProgress(reqSlug, ep, 0, dur).catch(function(){});
              openPlayer(ep, 0);
            };
          }

          if(bCancel){
            bCancel.onclick = function(e){
              if(e) e.stopPropagation();
              dismissResumeModal();
            };
          }

          if(bClose){
            bClose.onclick = function(e){
              if(e) e.stopPropagation();
              dismissResumeModal();
            };
          }

          window.addEventListener("keydown", keyHandler);
          modal.classList.remove("hidden");
          setTimeout(function(){
            if(bResume) TvNavigationManager.setFocus(bResume, "settings-modal");
          }, 50);
          return;
        }
      }
      if(cur.playToken === fetchToken && cur.slug === reqSlug) openPlayer(ep, 0);
    }).catch(function(){
      if(cur.playToken === fetchToken && cur.slug === reqSlug) openPlayer(ep, 0);
    });
    return;
  }

  cur.ep=ep;
  cur.intro=null;
  cur.outro=null;
  cur.hasAutoSkippedIntro=false;
  cur.hasAutoSkippedOutro=false;
  cur.activeSkipTarget=0;
  var initSkipBtn=$("pm-skip-btn");
  if(initSkipBtn) initSkipBtn.classList.add("hidden");
  cur.playerOpenedAt=Date.now();
  var token = ++_playTokenCounter;
  cur.playToken = token;
  var reqSlug = cur.slug;
  recordEpisodeWatched(cur.slug, ep);
  closeResumeModal();
  var tmModal = $("title-modal");
  if(tmModal) tmModal.classList.add("hidden");
  var dpModal = $("detail-page");
  if(dpModal) dpModal.classList.add("hidden");
  var searchSec = $("search-sec");
  if(searchSec) searchSec.classList.add("hidden");
  var contSec = $("continue-sec");
  if(contSec) contSec.classList.add("hidden");
  var pager = $("pager");
  if(pager) pager.classList.add("hidden");
  var pmModal = $("player-modal");
  if(pmModal){
    pmModal.classList.remove("hidden");
    pmModal.style.display = "flex";
  }
  if(TvNavigationManager.isTvMode()){
    TvNavigationManager.showPlayerControls($("pm-speed-select") || $("pm-close"));
  } else {
    TvNavigationManager.showPlayerControls();
    if(document.activeElement && document.activeElement !== document.body && $("player-modal").contains(document.activeElement)){
      try { document.activeElement.blur(); } catch(_){}
    }
  }
  $("pm-title").textContent=cur.title;
  $("pm-meta").textContent="ep "+ep+" · "+cur.mode.toUpperCase();
  $("pm-spinner").classList.remove("hidden");
  $("pm-status").textContent=forceRefresh ? "memulihkan ep "+ep+" (failover)..." : "resolving ep "+ep+"...";
  updatePrevNext();
  var t0=Date.now();
  var src=cur.source||"";
  window.Tatap.resolve(cur.slug,ep,cur.mode,cur.quality,src,forceRefresh,cur.title).then(function(r){
    if(cur.playToken !== token || cur.slug !== reqSlug || $("player-modal").classList.contains("hidden")) return;
    if(!r || !r.success){
      if(!forceRefresh){
        $("pm-status").textContent="gagal memuat, mencoba server cadangan...";
        setTimeout(function(){ openPlayer(ep, resumeTime, true); }, 400);
        return;
      }
      $("pm-spinner").classList.add("hidden");
      $("pm-status").innerHTML="ERROR: "+esc(r && r.error ? r.error : "gagal resolve stream")+" · <button id='pm-retry-btn' class='server-badge' style='background:rgba(255,255,255,0.1);border:1px solid var(--accent);color:var(--accent);cursor:pointer;border-radius:4px;padding:2px 8px;font:inherit;'>Coba Lagi ↻</button>";
      var rb=$("pm-retry-btn"); if(rb) rb.onclick=function(){ openPlayer(ep, resumeTime, true); };
      toast("Gagal resolve stream: "+(r && r.error ? r.error : "unknown"));
      return;
    }
    cur.res=r.data;
    if(r.data && r.data.is_failover){
      toast("CDN "+(r.data.failover_from==="otakudesu"?"Otakudesu":"HiAnime")+" tidak aktif · Otomatis memutar cadangan AniChan");
    }
    function isValidSkipInterval(inv){
      return !!(inv && typeof inv.start === "number" && typeof inv.end === "number" &&
                inv.end > inv.start && inv.end > 0 && (inv.end - inv.start) >= 5.0);
    }
    cur.intro=(r.data && isValidSkipInterval(r.data.intro)) ? r.data.intro : null;
    cur.outro=(r.data && isValidSkipInterval(r.data.outro)) ? r.data.outro : null;
    cur.activeSkipTarget=0;

    // Asynchronous AniSkip background recovery jika intro/outro belum ada di respons awal resolve
    if((!cur.intro || !cur.outro) && window.Tatap && window.Tatap.skipTimes){
      var skipMal = (r.data && r.data.mal_id) || cur.mal_id || "";
      window.Tatap.skipTimes(cur.slug, ep, cur.title, skipMal, 0).then(function(skRes){
        if(cur.playToken !== token || cur.ep !== ep) return;
        if(skRes && skRes.success && skRes.data){
          var hasNew = false;
          if(!cur.intro && isValidSkipInterval(skRes.data.intro)){
            cur.intro = skRes.data.intro;
            hasNew = true;
          }
          if(!cur.outro && isValidSkipInterval(skRes.data.outro)){
            cur.outro = skRes.data.outro;
            hasNew = true;
          }
          if(hasNew){
            checkSkipTimes();
          }
        }
      }).catch(function(){});
    }
    cur.source=r.data.source||"hianime";
    var picked=r.data.picked||(r.data.variants&&r.data.variants[0])||{q:"HD",url:r.data.master||""};
    var srvText=r.data.server||"";
    $("pm-meta").innerHTML="ep "+ep+" · "+cur.mode.toUpperCase()+" · "+picked.q+" · <button id='pm-source-btn' class='server-badge' title='Klik untuk switch sumber' style='background:none;border:1px solid rgba(255,255,255,0.25);color:var(--accent);cursor:pointer;border-radius:4px;padding:1px 6px;font:inherit;'>"+esc(srvText)+" ⇄</button>"+(r.data.cached?" · cached":" · "+(Date.now()-t0)+"ms");
    var srvBtn=$("pm-source-btn");
    if(srvBtn){
      srvBtn.onclick=function(){
        if(window.Tui&&window.Tui.switchSource){window.Tui.switchSource();}
        else{App.switchSource();}
      };
    }
    renderVariants();
    var subs = (r.data.subtitles && Array.isArray(r.data.subtitles)) ? r.data.subtitles : [];
    if(!subs.length && r.data.sub && typeof r.data.sub === "string" && !/^\d+$/.test(r.data.sub.trim())){
      subs = [{url: r.data.sub, lang: r.data.sub_lang || "English", label: r.data.sub_lang || "English", default: true}];
      r.data.subtitles = subs;
    }
    cur.activeSub = pickSubtitleUrl(subs, cur.subLang);
    renderSubtitles(subs, cur.activeSub);
    if(cur.activeSub){
      prefetchSubtitleTrack(cur.activeSub, r.data.referer);
    }
    var streamUrl = (r.data.master && (r.data.master.indexOf(".m3u8") >= 0 || r.data.master.indexOf("/hls") >= 0)) ? r.data.master : (picked ? picked.url : "");
    playUrl(streamUrl,r.data.referer,cur.activeSub,r.data.referer,resumeTime,token);
    window.Tatap.saveHist({
      slug: cur.slug,
      title: cur.title,
      episode: ep,
      mode: cur.mode,
      progress: resumeTime || 0,
      poster: cur.poster || "",
      type: cur.type || ""
    }).then(function(){ renderContinue(); });
  }).catch(function(err){
    if(cur.playToken !== token || cur.slug !== reqSlug || $("player-modal").classList.contains("hidden")) return;
    if(!forceRefresh){
      $("pm-status").textContent="koneksi terputus, mencoba server cadangan...";
      setTimeout(function(){ openPlayer(ep, resumeTime, true); }, 400);
      return;
    }
    $("pm-spinner").classList.add("hidden");
    $("pm-status").innerHTML="KONEKSI GAGAL: "+esc(err&&err.message||err)+" · <button id='pm-retry-btn-err' class='server-badge' style='background:rgba(255,255,255,0.1);border:1px solid var(--accent);color:var(--accent);cursor:pointer;border-radius:4px;padding:2px 8px;font:inherit;'>Coba Lagi ↻</button>";
    var rb2=$("pm-retry-btn-err"); if(rb2) rb2.onclick=function(){ openPlayer(ep, resumeTime, true); };
    toast("Koneksi gagal saat resolve: "+(err&&err.message||err));
  });
}
function renderVariants(){
  var box=$("pm-variants");if(box)box.innerHTML="";
  var sel=$("pm-quality-select");if(sel)sel.innerHTML="";
  var vs=(cur.res&&cur.res.hlsLevels&&cur.res.hlsLevels.length)?cur.res.hlsLevels:((cur.res&&cur.res.variants)||[]);
  var activeQ=(cur.res&&cur.res.picked&&cur.res.picked.q)||(vs[0]&&vs[0].q)||"";
  if(window._hls && cur.res && cur.res.hlsLevels && cur.res.hlsLevels.length){
    if(window._hls.autoLevelEnabled || window._hls.currentLevel === -1){
      activeQ = "Auto";
    }
  }

  for(var i=0;i<vs.length;i++){
    (function(v){
      if(box){
        var b=document.createElement("button");
        b.textContent=v.q;
        if(v.q.toLowerCase()===activeQ.toLowerCase())b.className="active";
        b.addEventListener("click",function(){switchQ(v.q);});
        box.appendChild(b);
      }
      if(sel){
        var opt=document.createElement("option");
        opt.value=v.q;
        opt.textContent=v.q.toUpperCase();
        if(v.q.toLowerCase()===activeQ.toLowerCase())opt.selected=true;
        sel.appendChild(opt);
      }
    })(vs[i]);
  }
  if(sel){
    if(vs.length<=1){
      sel.classList.add("hidden");
    } else {
      sel.classList.remove("hidden");
    }
  }
  syncArtplayerQuality();

  if(window.art && window.art.setting && cur.res && cur.res.variants && cur.res.variants.length > 1){
    try{
      var sList = cur.res.variants.map(function(sv, sidx){
        return {
          html: sv.q || ("Server " + (sidx+1)),
          variant: sv,
          default: cur.res.picked && cur.res.picked.url === sv.url
        };
      });
      var serverSetting = {
        name: "stream-server",
        width: 220,
        html: "Server Stream",
        tooltip: (cur.res.picked && cur.res.picked.q) || "Server",
        selector: sList,
        onSelect: function(item){
          switchQ(item.html);
          return item.html;
        }
      };
      if(window.art.setting.cache && window.art.setting.cache.has("stream-server")){
        window.art.setting.update(serverSetting);
      } else {
        window.art.setting.add(serverSetting);
      }
    }catch(_){}
  }
}


// ==== Multi-subtitle dropdown ====

function pickSubtitleUrl(subtitles, preferLang){
  // Pilih URL track subtitle yang cocok. Prioritas:
  //   1) Track dengan label == preferLang (case-insensitive).
  //   2) Track dengan lang code == preferLang (misal "English" → "en").
  //   3) Track AI Indonesian kalau user prefer Indonesian / translate aktif + ada track English.
  //   4) Track dengan default: true.
  //   5) Track English (hindari Arabic alfabetik pertama).
  //   6) Track pertama kalau tidak ada yang match.
  // Return null kalau subtitles kosong (UI akan sembunyikan dropdown).
  if(!subtitles||!subtitles.length)return null;
  if(preferLang){
    var low=String(preferLang).toLowerCase();
    for(var i=0;i<subtitles.length;i++){
      var s=subtitles[i];
      if((s.label||"").toLowerCase()===low)return s.url;
    }
    // Partial match di label (misal "Indonesian" cocok "Indonesian (Bahasa)").
    for(var j=0;j<subtitles.length;j++){
      if(((subtitles[j].label)||"").toLowerCase().indexOf(low)===0)return subtitles[j].url;
    }
    // Match kode bahasa (English → en/id/ja).
    var langMap={"english":"en","indonesian":"id","japanese":"ja","spanish":"es","portuguese":"pt",
                 "french":"fr","german":"de","italian":"it","korean":"ko","chinese":"zh","arabic":"ar",
                 "russian":"ru","thai":"th","vietnamese":"vi","turkish":"tr","hindi":"hi",
                 "czech":"cs","danish":"da","dutch":"nl","finnish":"fi","greek":"el","hungarian":"hu",
                 "norwegian":"no","polish":"pl","romanian":"ro","slovak":"sk","swedish":"sv",
                 "malay":"ms","tagalog":"tl"};
    var code=langMap[low];
    if(code){
      for(var k=0;k<subtitles.length;k++){
        if((subtitles[k].lang||"").toLowerCase()===code)return subtitles[k].url;
      }
    }
    // Kalau prefer Indonesian / translate on dan tidak ada track ID asli:
    // auto-pilih track Smart Fansub & Merge atau AI Fansub dari track English.
    if((low==="indonesian"||low==="id"||low==="indonesian (smart fansub & merge)"||low==="indonesian (opensubtitles)"||low==="indonesian (gtx+)"||low==="indonesian (gtx+ bilingual)"||low==="indonesian (aigtx)"||low==="indonesian (ai)"||low==="indonesian (gtx)"||low==="indonesian (opensubtitles bilingual)"||cur.translate)){
      var enTrack=null;
      for(var e=0;e<subtitles.length;e++){
        if(isExactEnglishSubTrack(subtitles[e])){
          enTrack=subtitles[e];break;
        }
      }
      if(!enTrack){
        for(var e2=0;e2<subtitles.length;e2++){
          if(isPureEnglishSubTrack(subtitles[e2])){
            enTrack=subtitles[e2];break;
          }
        }
      }
      if(enTrack&&enTrack.url){
        if(low==="indonesian (ai)") return "ai:"+enTrack.url;
        return "os_merge:"+enTrack.url;
      }
    }
  }
  // Prioritaskan exact English jika ada
  for(var nx=0;nx<subtitles.length;nx++){
    if(isExactEnglishSubTrack(subtitles[nx]))return subtitles[nx].url;
  }
  // Prioritaskan varian English jika ada
  for(var n=0;n<subtitles.length;n++){
    if(isPureEnglishSubTrack(subtitles[n]))return subtitles[n].url;
  }
  // Fallback: default:true (selama bukan Arabic)
  for(var m=0;m<subtitles.length;m++){
    var mlab=(subtitles[m].label||"").toLowerCase();
    var mlang=(subtitles[m].lang||"").toLowerCase();
    if(subtitles[m].default && mlang!=="ar" && mlab.indexOf("arab")===-1)return subtitles[m].url;
  }
  // Fallback: track pertama yang bukan Arabic
  for(var p=0;p<subtitles.length;p++){
    var plab=(subtitles[p].label||"").toLowerCase();
    var plang=(subtitles[p].lang||"").toLowerCase();
    if(plang!=="ar"&&plab.indexOf("arab")===-1)return subtitles[p].url;
  }
  return subtitles[0].url;
}

var _NON_EN_SUB_KEYWORDS = [
  "arabic", "arab", "indonesia", "bahasa", "spanish", "espanol", "español",
  "portuguese", "french", "francais", "german", "deutsch", "italian", "korean",
  "chinese", "russian", "thai", "vietnamese", "turkish", "hindi", "czech",
  "danish", "dutch", "finnish", "greek", "hungarian", "norwegian", "polish",
  "romanian", "slovak", "swedish", "malay", "tagalog", "filipino", "japanese"
];

function isPureEnglishSubTrack(s){
  if(!s)return false;
  var lab=((s.label||"")+"").toLowerCase().trim();
  var l=((s.lang||"")+"").toLowerCase().trim();
  for(var k=0;k<_NON_EN_SUB_KEYWORDS.length;k++){
    if(lab.indexOf(_NON_EN_SUB_KEYWORDS[k])!==-1)return false;
  }
  return l==="en"||lab.indexOf("english")===0||lab.indexOf("eng")===0;
}

function isExactEnglishSubTrack(s){
  if(!s)return false;
  var lab=((s.label||"")+"").toLowerCase().trim();
  return isPureEnglishSubTrack(s)&&(lab==="english"||lab==="english [full]"||lab==="eng");
}

function buildSubtitleControl(subtitles, activeUrl){
  subtitles = subtitles || (cur.res && cur.res.subtitles) || [];
  var trackList = [
    { name: "sub-off", html: "Off (Matikan Subtitle)", value: "", default: !activeUrl }
  ];
  var exactEn = null, anyEn = null;
  for(var i=0; i<subtitles.length; i++){
    var s = subtitles[i];
    if(!exactEn && isExactEnglishSubTrack(s)) exactEn = s;
    else if(!anyEn && isPureEnglishSubTrack(s)) anyEn = s;
    trackList.push({
      name: "sub-track-" + i,
      html: s.label || ("Subtitle " + (i+1)) + (s.default ? " (Default)" : ""),
      value: s.url || "",
      default: s.url === activeUrl
    });
  }
  var en = exactEn || anyEn;
  if(en && en.url){
    trackList.push({
      name: "sub-os-merge",
      html: "🇮🇩 Indonesian (Smart Fansub & Merge)",
      value: "os_merge:" + en.url,
      default: !!(activeUrl && (activeUrl.indexOf("os_merge:") === 0 || activeUrl.indexOf("gtx+:") === 0 || activeUrl.indexOf("gtx:") === 0))
    });
    trackList.push({
      name: "sub-ai",
      html: "🤖 Indonesian (AI Fansub)",
      value: "ai:" + en.url,
      default: !!(activeUrl && activeUrl.indexOf("ai:") === 0)
    });
  }
  trackList.push({
    name: "sub-search-os",
    html: "🔍 [+] Cari Subtitle Indonesia (OpenSubtitles)",
    value: "__opensubtitles_search__",
    default: false
  });
  trackList.push({
    name: "sub-load-file",
    html: "📁 [+] Muat File Subtitle (.srt / .vtt)",
    value: "__custom_file__",
    default: false
  });
  trackList.push({
    name: "sub-styler-trigger",
    html: "🎨 Atur Gaya Subtitle (Styler)...",
    value: "__open_styler__",
    default: false
  });

  return {
    name: "sub-control",
    position: "right",
    index: 12,
    style: { marginRight: "4px" },
    html: '<span class="art-ctrl-btn art-ctrl-sub-btn" title="Pilih Subtitle"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="3"></rect><path d="M7 15h3M14 15h3M7 11h10"></path></svg><span>SUB</span></span>',
    tooltip: "Pilih Subtitle",
    selector: trackList,
    onSelect: function(item){
      if(item.value === "__open_styler__"){
        openSubStyleModal();
        return '<span class="art-ctrl-btn art-ctrl-sub-btn" title="Pilih Subtitle"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="3"></rect><path d="M7 15h3M14 15h3M7 11h10"></path></svg><span>SUB</span></span>';
      }
      var sel = $("pm-subs");
      if(sel){
        sel.value = item.value;
        if(typeof sel.onchange === "function") sel.onchange();
      } else {
        switchSubtitleTrack(item.value);
      }
      if(window.art && window.art.notice) window.art.notice.show = "Subtitle: " + item.html;
      return '<span class="art-ctrl-btn art-ctrl-sub-btn" title="Pilih Subtitle"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="3"></rect><path d="M7 15h3M14 15h3M7 11h10"></path></svg><span>SUB</span></span>';
    },
    mounted: function($control){
      $control.addEventListener("click", function(e){
        if(e.target.closest(".art-selector-item")){
          $control.classList.remove("show");
          $control.classList.remove("art-selector-show");
          return;
        }
        $control.classList.toggle("show");
        $control.classList.toggle("art-selector-show");
      });
    }
  };
}

function syncArtplayerSubtitles(subtitles, activeUrl){
  if(!window.art) return;
  subtitles = subtitles || (cur.res && cur.res.subtitles) || [];
  var subCtrl = buildSubtitleControl(subtitles, activeUrl);
  var trackList = subCtrl.selector;

  try{
    if(window.art.controls){
      if(window.art.controls.cache && window.art.controls.cache.has("sub-control")){
        window.art.controls.remove("sub-control");
      }
      window.art.controls.add(subCtrl);
    }
  }catch(_){}

  var curActive = trackList.find(function(t){ return t.default; }) || trackList[0];
  var settingItem = {
    name: "subtitle-track",
    width: 290,
    html: "Pilih Subtitle",
    tooltip: curActive.html,
    selector: trackList,
    onSelect: function(item){
      var sel = $("pm-subs");
      if(sel){
        sel.value = item.value;
        if(typeof sel.onchange === "function") sel.onchange();
      } else {
        switchSubtitleTrack(item.value);
      }
      if(window.art && window.art.notice) window.art.notice.show = "Subtitle: " + item.html;
      return item.html;
    }
  };
  try{
    if(window.art.setting){
      if(window.art.setting.cache && window.art.setting.cache.has("subtitle-track")){
        window.art.setting.update(settingItem);
      } else {
        window.art.setting.add(settingItem);
      }
    }
    if(window.art.subtitle){
      try { window.art.subtitle.show = !!activeUrl; } catch(_){}
    }
    if(window.art.template && window.art.template.$player){
      window.art.template.$player.classList.toggle("art-subtitle-show", !!activeUrl);
    }
  }catch(_){}
}

function buildQualityControl(levels, activeQ){
  levels = levels || (cur.res && cur.res.hlsLevels && cur.res.hlsLevels.length ? cur.res.hlsLevels : (cur.res && cur.res.variants)) || [];
  activeQ = activeQ || "Auto";
  if(window._hls && (window._hls.autoLevelEnabled || window._hls.currentLevel === -1)){
    activeQ = "Auto";
  } else if(window._hls && window._hls.currentLevel >= 0 && levels.length){
    for(var i=0; i<levels.length; i++){
      if(levels[i].levelIdx === window._hls.currentLevel){
        activeQ = levels[i].q; break;
      }
    }
  } else if(cur.res && cur.res.picked && cur.res.picked.q){
    activeQ = cur.res.picked.q;
  }

  var selList = [];
  if(levels && levels.length > 0){
    selList = levels.map(function(l, lidx){
      var label = l.q || (l.height ? (l.height + "p") : ("Level " + (lidx + 1)));
      return {
        html: label,
        levelIdx: l.levelIdx !== undefined ? l.levelIdx : lidx,
        default: label.toLowerCase() === activeQ.toLowerCase()
      };
    });
  } else {
    selList = [{ html: "Auto", levelIdx: -1, default: true }];
  }

  return {
    name: "quality",
    position: "right",
    index: 10,
    style: { marginRight: "4px" },
    html: '<span class="art-ctrl-btn art-ctrl-quality-btn" id="art-quality-label" title="Pilih Resolusi Video"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg><span class="art-quality-text">' + activeQ.toUpperCase() + '</span></span>',
    tooltip: "Pilih Resolusi Video",
    selector: selList,
    onSelect: function(item){
      switchQ(item.html);
      if(window.art && window.art.notice) window.art.notice.show = "Resolusi: " + item.html;
      return '<span class="art-ctrl-btn art-ctrl-quality-btn" id="art-quality-label" title="Pilih Resolusi Video"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg><span class="art-quality-text">' + item.html.toUpperCase() + '</span></span>';
    },
    mounted: function($control){
      $control.addEventListener("click", function(e){
        if(e.target.closest(".art-selector-item")){
          $control.classList.remove("show");
          $control.classList.remove("art-selector-show");
          return;
        }
        $control.classList.toggle("show");
        $control.classList.toggle("art-selector-show");
      });
    }
  };
}

function syncArtplayerQuality(levels){
  if(!window.art) return;
  levels = levels || (cur.res && cur.res.hlsLevels && cur.res.hlsLevels.length ? cur.res.hlsLevels : (cur.res && cur.res.variants)) || [];
  
  var activeQ = "Auto";
  if(window._hls && (window._hls.autoLevelEnabled || window._hls.currentLevel === -1)){
    activeQ = "Auto";
  } else if(window._hls && window._hls.currentLevel >= 0 && levels.length){
    for(var i=0; i<levels.length; i++){
      if(levels[i].levelIdx === window._hls.currentLevel){
        activeQ = levels[i].q; break;
      }
    }
  } else if(cur.res && cur.res.picked && cur.res.picked.q){
    activeQ = cur.res.picked.q;
  }

  var qualityControl = buildQualityControl(levels, activeQ);

  try{
    if(window.art.controls){
      if(window.art.controls.cache && window.art.controls.cache.has("quality")){
        window.art.controls.remove("quality");
      }
      window.art.controls.add(qualityControl);
    }
  }catch(_){}

  try{
    var qualitySetting = {
      name: "video-quality",
      width: 220,
      html: "Kualitas Video",
      tooltip: activeQ.toUpperCase(),
      selector: qualityControl.selector,
      onSelect: function(item){
        switchQ(item.html);
        if(window.art && window.art.notice) window.art.notice.show = "Resolusi: " + item.html;
        return item.html;
      }
    };
    if(window.art.setting && window.art.setting.cache && window.art.setting.cache.has("video-quality")){
      window.art.setting.update(qualitySetting);
    } else if(window.art.setting){
      window.art.setting.add(qualitySetting);
    }
  }catch(_){}
}

function syncTranslateBtn(){
  if(!window.art || !window.art.controls) return;
  var trControl = {
    name: "tr-btn",
    position: "right",
    index: 14,
    style: { marginRight: "4px" },
    html: '<span class="art-ctrl-btn art-ctrl-tr-btn' + (cur.translate ? ' active' : '') + '" title="Terjemahan Bahasa Indonesia (ID)"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg><span>TR-ID</span></span>',
    tooltip: cur.translate ? "Terjemahan Indonesia: Aktif" : "Terjemahan Indonesia: Nonaktif",
    click: function(){
      setTranslate(!cur.translate);
    }
  };
  try{
    if(window.art.controls.cache && window.art.controls.cache.has("tr-btn")){
      window.art.controls.remove("tr-btn");
    }
    window.art.controls.add(trControl);
  }catch(_){}

  if(window.art.setting && window.art.setting.cache && window.art.setting.cache.has("subtitle-translate")){
    try{
      window.art.setting.update({
        name: "subtitle-translate",
        tooltip: cur.translate ? "Aktif" : "Nonaktif",
        switch: !!cur.translate
      });
    }catch(_){}
  }
}

function renderSubtitles(subtitles, activeUrl){
  var wrap=$("pm-subs-wrap");
  var sel=$("pm-subs");
  if(!wrap||!sel)return;
  subtitles = subtitles || [];
  wrap.classList.remove("hidden");
  sel.innerHTML="";
  // Opsi pertama: "Off" (matikan subtitle).
  var offOpt=document.createElement("option");
  offOpt.value="";
  offOpt.textContent="Off";
  sel.appendChild(offOpt);
  // Tambah opsi "Indonesian (AI)", "Indonesian (GTX+)", dan "Indonesian (Google GTX)" kalau ada track English.
  var exactEnTrack=null;
  var anyEnTrack=null;
  for(var i=0;i<subtitles.length;i++){
    (function(s){
      var o=document.createElement("option");
      o.value=s.url||"";
      o.textContent=s.label||("Subtitle "+(i+1));
      if(s.default)o.textContent+=" (Default)";
      if(activeUrl&&s.url===activeUrl)o.selected=true;
      sel.appendChild(o);
      // deteksi track English untuk AI-translate source
      if(!exactEnTrack && isExactEnglishSubTrack(s)){
        exactEnTrack=s;
      } else if(!anyEnTrack && isPureEnglishSubTrack(s)){
        anyEnTrack=s;
      }
    })(subtitles[i]);
  }
  var englishTrack=exactEnTrack||anyEnTrack;
  if(englishTrack&&englishTrack.url){
    // Smart Fansub & Merge: Cari AnimeTosho ID -> OpenSubtitles ID -> Builtin + GTX+,
    // seluruhnya terintegrasi Smart Lexicon + Smart Scene Detector + Smart Merge.
    var osMergeOpt=document.createElement("option");
    osMergeOpt.value="os_merge:"+englishTrack.url;
    osMergeOpt.textContent="Indonesian (Smart Fansub & Merge)";
    if(activeUrl&&(activeUrl===osMergeOpt.value||activeUrl.indexOf("os_merge:")===0||activeUrl.indexOf("gtx+:")===0||activeUrl.indexOf("gtx:")===0||activeUrl.indexOf("os_dual:")===0||activeUrl.indexOf("gtx+_dual:")===0)){
      osMergeOpt.selected=true;
    }
    sel.appendChild(osMergeOpt);

    var aiOpt=document.createElement("option");
    aiOpt.value="ai:"+englishTrack.url;
    aiOpt.textContent="Indonesian (AI Fansub)";
    aiOpt.setAttribute("data-ai-source",englishTrack.url);
    if(activeUrl&&(activeUrl===aiOpt.value||(activeUrl.indexOf("ai:")===0&&activeUrl.slice(3)===englishTrack.url))){
      aiOpt.selected=true;
    }
    sel.appendChild(aiOpt);
  }

  var optOsSearch=document.createElement("option");
  optOsSearch.value="__opensubtitles_search__";
  optOsSearch.textContent="🔍 [+] Cari Subtitle Bahasa Indonesia (AnimeTosho & OpenSubtitles)...";
  sel.appendChild(optOsSearch);

  // Opsi custom subtitle eksternal
  var optCustomFile=document.createElement("option");
  optCustomFile.value="__custom_file__";
  optCustomFile.textContent="📁 [+] Muat File Subtitle (.srt / .vtt / .ass)...";
  sel.appendChild(optCustomFile);

  var optCustomUrl=document.createElement("option");
  optCustomUrl.value="__custom_url__";
  optCustomUrl.textContent="🌐 [+] Masukkan URL Subtitle Kustom...";
  sel.appendChild(optCustomUrl);

  // Set value juga kalau match dari default tidak ketemu (URL di pickSubtitleUrl).
  if(activeUrl){
    sel.value=activeUrl;
  }else{
    sel.value="";  // Off
  }
  // Event listener: ganti track aktif seketika + simpan preferensi.
  sel.onchange=function(){
    if(!TvNavigationManager.isTvMode()){ try { sel.blur(); } catch(_){} }
    var url=sel.value;
    if(url==="__custom_file__"){
      sel.value=activeUrl||"";
      var fi=$("pm-custom-sub-file");
      if(fi){
        fi.value="";
        fi.onchange=function(){
          var file=fi.files&&fi.files[0];
          if(!file)return;
          var reader=new FileReader();
          reader.onload=function(e){
            var text=e.target.result;
            toast("Memproses file subtitle...");
            window.Tatap.uploadCustomSub({text:text,filename:file.name,lang:"en"}).then(function(res){
              if(res&&res.success&&res.data){
                toast("Subtitle dimuat: "+res.data.cues_count+" cue");
                var newTrack={label:res.data.label,url:res.data.url,lang:res.data.lang};
                subtitles.push(newTrack);
                cur.activeSub=res.data.url;
                renderSubtitles(subtitles,res.data.url);
                switchSubtitleTrack(res.data.url);
              }else{
                toast("Gagal memuat subtitle: "+((res&&res.error)||"Format tidak valid"));
              }
            }).catch(function(err){
              toast("Gagal upload subtitle: "+err);
            });
          };
          reader.readAsText(file);
        };
        fi.click();
      }
      return;
    }
    if(url==="__custom_url__"){
      sel.value=activeUrl||"";
      var inUrl=prompt("Masukkan URL Subtitle (.srt / .vtt / .ass):");
      if(inUrl&&inUrl.trim()){
        inUrl=inUrl.trim();
        toast("Mengunduh subtitle dari URL...");
        window.Tatap.uploadCustomSub({url:inUrl,filename:"URL Kustom",lang:"en"}).then(function(res){
          if(res&&res.success&&res.data){
            toast("Subtitle URL berhasil dimuat");
            var newTrack={label:res.data.label,url:res.data.url,lang:res.data.lang};
            subtitles.push(newTrack);
            cur.activeSub=res.data.url;
            renderSubtitles(subtitles,res.data.url);
            switchSubtitleTrack(res.data.url);
          }else{
            toast("Gagal memuat subtitle: "+((res&&res.error)||"Gagal mengambil URL"));
          }
        }).catch(function(err){
          toast("Gagal mengunduh subtitle: "+err);
        });
      }
      return;
    }

    if(url==="__opensubtitles_search__"){
      sel.value=activeUrl||"";
      openOpenSubtitlesPicker(subtitles, englishTrack ? englishTrack.url : "");
      return;
    }

    cur.activeSub=url||null;
    // Track Smart Fansub & Merge: synthetic URL "os_merge:<url>"
    if(url&&(url.indexOf("os_merge:")===0||url.indexOf("os_dual:")===0||url.indexOf("gtx+:")===0||url.indexOf("gtx:")===0||url.indexOf("gtx+_dual:")===0||url.indexOf("aigtx:")===0)){
      cur.translate=false;
      var cleanTarget="os_merge:"+url.replace(/^(os_merge|os_dual|gtx\+_dual|gtx\+|gtx|aigtx):/,"");
      switchSubtitleTrack(cleanTarget,"id");
      cur.subLang="Indonesian (Smart Fansub & Merge)";
      window.Tatap.setSetting({sub_lang:cur.subLang}).then(function(){}).catch(function(){});
      return;
    }
    // Track AI Fansub: synthetic URL "ai:<url>". Extract realUrl + panggil translate.
    if(url&&url.indexOf("ai:")===0){
      cur.translate=true;
      try{localStorage.setItem("tatap_translate","1");}catch(e){}
      syncTranslate();
      switchSubtitleTrack(url,"id");
      cur.subLang="Indonesian (AI)";
      window.Tatap.setSetting({sub_lang:"Indonesian (AI)"}).then(function(){}).catch(function(){});
      return;
    }
    // Update <track> live tanpa pause/reload video.
    switchSubtitleTrack(url);
    // Cari label untuk disimpan ke settings (server-side preference).
    var label="";
    if(url){
      for(var j=0;j<subtitles.length;j++){
        if(subtitles[j].url===url){label=subtitles[j].label||"";break;}
      }
    }
    if(label){
      cur.subLang=label;
      window.Tatap.setSetting({sub_lang:label}).then(function(){}).catch(function(){});
      toast("Subtitle: "+label);
    }else{
      cur.subLang="";
      window.Tatap.setSetting({sub_lang:""}).then(function(){}).catch(function(){});
      toast("Subtitle: Off");
    }
  };
  syncArtplayerSubtitles(subtitles, activeUrl);
}

function closeOpenSubtitlesPicker(){
  var old=document.getElementById("os-picker");
  if(old&&old.parentNode)old.parentNode.removeChild(old);
}

function openOpenSubtitlesPicker(subtitles, baseSubUrl){
  // Daftar rilis subtitle khusus Bahasa Indonesia (AnimeTosho & OpenSubtitles) untuk episode aktif.
  // Rilis yang dipilih diunduh lalu di-merge dengan subtitle bawaan anime (baseSubUrl) di backend.
  closeOpenSubtitlesPicker();
  var host=document.querySelector(".ambient-stage")||document.body;
  var box=document.createElement("div");
  box.id="os-picker";
  box.className="os-picker";
  box.setAttribute("role","dialog");
  box.innerHTML='<div class="os-picker-card"><div class="os-picker-head"><span>Subtitle Bahasa Indonesia · Ep '+esc(String(cur.ep||1))+'</span><button type="button" class="os-picker-close" aria-label="Tutup">✕</button></div><div class="os-picker-body"><div class="os-picker-status">Mencari subtitle di AnimeTosho & OpenSubtitles...</div></div></div>';
  host.appendChild(box);
  var body=box.querySelector(".os-picker-body");
  box.querySelector(".os-picker-close").onclick=closeOpenSubtitlesPicker;
  box.addEventListener("click",function(e){ if(e.target===box) closeOpenSubtitlesPicker(); });
  box.addEventListener("keydown",function(e){
    if(e.key==="Escape"){ e.preventDefault(); e.stopPropagation(); closeOpenSubtitlesPicker(); }
  });
  var token=cur.playToken;
  var altTitle=(cur.meta&&(cur.meta.title_romaji||cur.meta.title_english))||"";
  var seasonNum=0;
  if(cur.meta){
    if(typeof cur.meta.season_number==="number") seasonNum=cur.meta.season_number;
    else if(typeof cur.meta.season==="number") seasonNum=cur.meta.season;
    else if(typeof cur.meta.season==="string" && /^\d+$/.test(cur.meta.season.trim())) seasonNum=parseInt(cur.meta.season.trim(),10);
  }
  window.Tatap.searchOpenSubtitles(cur.title, cur.slug, cur.ep, "id", seasonNum, altTitle).then(function(res){
    if(cur.playToken!==token||!document.getElementById("os-picker"))return;
    var items=(res&&res.success&&res.data&&res.data.items)||[];
    if(!items.length){
      body.innerHTML='<div class="os-picker-status">Belum ada subtitle Bahasa Indonesia untuk episode ini di AnimeTosho maupun OpenSubtitles.</div>';
      return;
    }
    body.innerHTML="";
    var note=document.createElement("div");
    note.className="os-picker-status";
    note.textContent=baseSubUrl?"Pilih subtitle Bahasa Indonesia — akan di-merge otomatis dengan subtitle bawaan (sync waktu + isi sign/OP/ED).":"Pilih subtitle Bahasa Indonesia (stream ini tidak punya subtitle bawaan untuk di-merge).";
    body.appendChild(note);
    items.slice(0,25).forEach(function(it){
      var btn=document.createElement("button");
      btn.type="button";
      btn.className="os-picker-item";
      var provTag = (it.source || (it.id && it.id.indexOf("at_") === 0 ? "AnimeTosho" : "OpenSubtitles"));
      btn.innerHTML='<span class="os-lang">'+esc(provTag)+'</span><span class="os-name">'+esc(it.filename||("Subtitle #"+it.file_id))+'</span>'+(it.downloads?'<span class="os-dl">'+esc(String(it.downloads))+'×</span>':'');
      btn.onclick=function(){
        body.innerHTML='<div class="os-picker-status">Mengunduh & merge subtitle Bahasa Indonesia...</div>';
        window.Tatap.mergeOpenSubtitle({
          file_id:it.file_id, os_url:it.url, backup_url:it.backup_url,
          filename:it.filename, cand_lang:"id", lang:"id", source:provTag,
          base_sub_url:baseSubUrl||"", referer:(cur.res&&cur.res.referer)||"", merge_mode:"hybrid"
        }).then(function(r){
          closeOpenSubtitlesPicker();
          if(cur.playToken!==token)return;
          if(r&&r.success&&r.data){
            var st=r.data.stats||{};
            toast("Subtitle "+provTag+" dimuat: "+r.data.cues_count+" baris (offset "+(st.offset||0)+"s, "+(st.gap_filled||0)+" sign/OP/ED dari bawaan)",5000);
            var newTrack={label:r.data.label,url:r.data.url,lang:r.data.lang};
            subtitles.push(newTrack);
            cur.activeSub=r.data.url;
            renderSubtitles(subtitles,r.data.url);
            switchSubtitleTrack(r.data.url);
          }else{
            toast("Gagal merge subtitle: "+((r&&r.error)||"tidak diketahui"),5000);
          }
        }).catch(function(err){
          closeOpenSubtitlesPicker();
          toast("Gagal merge subtitle: "+err,5000);
        });
      };
      body.appendChild(btn);
    });
    var first=body.querySelector(".os-picker-item");
    if(first)try{first.focus();}catch(_){}
  }).catch(function(err){
    if(!document.getElementById("os-picker"))return;
    body.innerHTML='<div class="os-picker-status">Gagal mencari subtitle: '+esc(String(err))+'</div>';
  });
}

function vttTime(s){
  var m=/^(?:(\d+):)?([0-5]?\d):([0-5]\d)(?:[.,](\d{1,3}))?$/.exec((s||"").trim());
  if(!m)return -1;
  var ms=m[4]?parseInt((m[4]+"000").slice(0,3),10):0;
  return (m[1]?parseInt(m[1],10)*3600:0)+parseInt(m[2],10)*60+parseInt(m[3],10)+ms/1000;
}
function cleanAssLine(s){
  if(!s)return "";
  return String(s).replace(/\{[^}]*\}/g,"").replace(/\\N/g,"\n").replace(/\\n/g,"\n").replace(/\\h/g," ");
}
function parseVtt(text){
  var out=[];
  var lines=String(text||"").replace(/\r\n?/g,"\n").split("\n");
  var i=0;
  if(lines[0]&&lines[0].indexOf("WEBVTT")===0)i=1;
  var start=-1,end=-1,buf=[];
  var flush=function(){
    if(start>=0&&end>start&&buf.length){
      var cleaned=buf.map(cleanAssLine).join("\n").split("\n").map(function(x){return x.trim();}).filter(Boolean);
      if(cleaned.length){
        var plain=cleaned.map(function(x){return x.replace(/<[^>]+>/g,"");}).join("\n");
        var html=cleaned.map(function(x){return esc(x);}).join("<br>");
        html=html.replace(/&lt;[^&]*?&gt;/g,"");
        out.push({start:start,end:end,html:html,plain:plain});
      }
    }
    start=-1;end=-1;buf=[];
  };
  for(;i<lines.length;i++){
    var ln=lines[i].trim();
    if(!ln){flush();continue;}
    if(ln.indexOf("-->")>=0){
      flush();
      var p=ln.split("-->");
      start=vttTime(p[0]);end=vttTime((p[1]||"").trim().split(" ")[0]);
      continue;
    }
    if(/^(NOTE|STYLE|REGION)/.test(ln))continue;
    if(start>=0)buf.push(ln);
  }
  flush();
  return out;
}
function clearOverlay(){
  var box=$("pm-subs-overlay");
  if(!box)return;
  var s=box.querySelector("span");
  if(s){s.innerHTML="";s._last="";}
}
function isDesktopEnv(){
  if(typeof window.tatap_set_fullscreen === "function") return true;
  var ua = (navigator.userAgent || "").toLowerCase();
  var isMobile = /android|iphone|ipad|ipod|windows phone|blackberry|mobile/i.test(ua);
  return !isMobile;
}
function isVideoFullscreen(){
  var v=$("vid");
  if(!v)return false;
  var fsEl=document.fullscreenElement||document.webkitFullscreenElement||document.mozFullScreenElement||document.msFullscreenElement;
  if(fsEl&&fsEl===v)return true;
  if(v.webkitDisplayingFullscreen)return true;
  return false;
}
function isFullscreenActive(){
  var v=$("vid");
  var fsEl=document.fullscreenElement||document.webkitFullscreenElement||document.mozFullScreenElement||document.msFullscreenElement;
  if(fsEl)return true;
  if(v&&v.webkitDisplayingFullscreen)return true;
  return false;
}
function getActiveVideos(){
  var list = [];
  if(window.art && window.art.video && list.indexOf(window.art.video) === -1){
    list.push(window.art.video);
  }
  var fallbackVid = $("vid");
  if(fallbackVid && list.indexOf(fallbackVid) === -1){
    list.push(fallbackVid);
  }
  if(document.pictureInPictureElement && list.indexOf(document.pictureInPictureElement) === -1){
    list.push(document.pictureInPictureElement);
  }
  return list;
}

function isPipActive(){
  return !!(document.pictureInPictureElement || (window.art && window.art.pip) || window.tatapPipWindow || document.body.classList.contains("is-pip"));
}

function syncPipSubtitles(isPip){
  if(isPip === undefined){
    isPip = isPipActive();
  }
  document.body.classList.toggle("is-pip", !!isPip);
  var focusOverlay = $("pip-focus-overlay");
  if(focusOverlay){
    if(window.tatapPipWindow){
      focusOverlay.classList.add("hidden");
    } else {
      focusOverlay.classList.toggle("hidden", !isPip);
    }
  }
  var vids = getActiveVideos();
  var isVidFs = isVideoFullscreen();
  for(var vi = 0; vi < vids.length; vi++){
    var v = vids[vi];
    if(v && v.textTracks){
      for(var i = 0; i < v.textTracks.length; i++){
        var t = v.textTracks[i];
        if(t.label && t.label.indexOf("Tatap") >= 0){
          t.mode = isPip ? "showing" : ((isVidFs && !isDesktopEnv()) ? "showing" : "hidden");
        }
      }
    }
  }
}

function formatVttTimestamp(sec){
  var s = Math.max(0, sec);
  var hrs = Math.floor(s / 3600);
  var mins = Math.floor((s % 3600) / 60);
  var secs = (s % 60).toFixed(3);
  var pad = function(n, len){ return (n < 10 ? "0" : "") + n; };
  var padSec = parseFloat(secs) < 10 ? "0" + secs : secs;
  return pad(hrs, 2) + ":" + pad(mins, 2) + ":" + padSec;
}

function generateVttWithOffset(cues, delay){
  var lines = ["WEBVTT", ""];
  for(var i = 0; i < cues.length; i++){
    var c = cues[i];
    var start = Math.max(0, (c.start || 0) + delay);
    var end = Math.max(start + 0.1, (c.end || 0) + delay);
    var plain = c.plain || (c.html ? c.html.replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, "") : "");
    lines.push((i + 1).toString());
    lines.push(formatVttTimestamp(start) + " --> " + formatVttTimestamp(end));
    lines.push(plain || "...");
    lines.push("");
  }
  return lines.join("\n");
}

function getActiveSubtitleLines(currentTime){
  var t = (typeof currentTime === "number" && !isNaN(currentTime)) ? currentTime : ((window.art && !isNaN(window.art.currentTime)) ? window.art.currentTime : 0);
  var subTime = t - (cur.subDelay || 0.0);
  if(!cur.cues || !cur.cues.length) return [];
  var lines = [];
  for(var i = 0; i < cur.cues.length; i++){
    var c = cur.cues[i];
    if(subTime >= c.start && subTime <= c.end){
      var txt = c.plain || (c.html ? c.html.replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, "") : "");
      if(txt){
        var split = txt.split("\n");
        for(var j = 0; j < split.length; j++){
          var trimmed = split[j].trim();
          if(trimmed && lines.indexOf(trimmed) === -1){
            lines.push(trimmed);
          }
        }
      }
    }
  }
  return lines;
}

function drawCanvasSubtitles(ctx, lines, w, h){
  if(!lines || !lines.length) return;
  var sz = cur.subSize || "m";
  var szMultiplier = sz === "s" ? 0.036 : (sz === "l" ? 0.058 : (sz === "xl" ? 0.070 : 0.046));
  var fontSize = Math.max(14, Math.min(56, Math.round(h * szMultiplier)));
  var lineHeight = Math.round(fontSize * 1.35);
  var outlineWidth = Math.max(3, Math.round(fontSize * 0.14));

  var posMap = { "low": 0.035, "normal": 0.075, "medium": 0.13, "high": 0.19 };
  var posMult = posMap[cur.subPos || "normal"] || 0.075;
  var bottomMargin = Math.round(h * posMult);

  var bgMap = {
    "medium": "rgba(0, 0, 0, 0.65)",
    "dark": "rgba(0, 0, 0, 0.88)",
    "light": "rgba(0, 0, 0, 0.28)",
    "frosted": "rgba(13, 17, 26, 0.82)",
    "none": "transparent"
  };
  var bgFill = bgMap[cur.subBg || "medium"] || bgMap["medium"];
  var textColor = cur.subColor || "#ffffff";
  var fontVal = FONT_MAP[cur.subFont || "sans"] || FONT_MAP["sans"];

  ctx.save();
  ctx.font = "bold " + fontSize + "px " + fontVal;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.lineJoin = "round";
  ctx.miterLimit = 2;

  var totalHeight = lines.length * lineHeight;
  var startY = h - bottomMargin - totalHeight + (lineHeight / 2);

  for(var i = 0; i < lines.length; i++){
    var line = lines[i];
    var y = startY + (i * lineHeight);
    var x = w / 2;

    if(bgFill !== "transparent"){
      var textMetrics = ctx.measureText(line);
      var padX = Math.round(fontSize * 0.4);
      var padY = Math.round(fontSize * 0.18);
      ctx.fillStyle = bgFill;
      var rectX = x - (textMetrics.width / 2) - padX;
      var rectY = y - (lineHeight / 2) + padY;
      var rectW = textMetrics.width + (padX * 2);
      var rectH = lineHeight - (padY * 2);
      var radius = Math.min(6, rectH / 2);

      ctx.beginPath();
      ctx.moveTo(rectX + radius, rectY);
      ctx.lineTo(rectX + rectW - radius, rectY);
      ctx.quadraticCurveTo(rectX + rectW, rectY, rectX + rectW, rectY + radius);
      ctx.lineTo(rectX + rectW, rectY + rectH - radius);
      ctx.quadraticCurveTo(rectX + rectW, rectY + rectH, rectX + rectW - radius, rectY + rectH);
      ctx.lineTo(rectX + radius, rectY + rectH);
      ctx.quadraticCurveTo(rectX, rectY + rectH, rectX, rectY + rectH - radius);
      ctx.lineTo(rectX, rectY + radius);
      ctx.quadraticCurveTo(rectX, rectY, rectX + radius, rectY);
      ctx.closePath();
      ctx.fill();
    }

    // Dark stroke outline
    ctx.strokeStyle = "#000000";
    ctx.lineWidth = outlineWidth;
    ctx.strokeText(line, x, y);

    // Text fill with custom color
    ctx.fillStyle = textColor;
    ctx.fillText(line, x, y);
  }
  ctx.restore();
}

async function toggleSmartPip(){
  // 1. Jika PiP aktif, tutup
  if(window.tatapPipWindow){
    try{ window.tatapPipWindow.close(); }catch(_){}
    window.tatapPipWindow = null;
    syncPipSubtitles(false);
    return;
  }
  if(document.pictureInPictureElement){
    try{ await document.exitPictureInPicture(); }catch(_){}
    syncPipSubtitles(false);
    return;
  }
  if(window.art && window.art.pip){
    try{ window.art.pip = false; }catch(_){}
    syncPipSubtitles(false);
    return;
  }

  var sourceVideo = (window.art && window.art.video) || $("vid");
  if(!sourceVideo) return;

  // Bersihkan sisa loop canvas terdahulu jika ada
  if(window._tatapPipRaf){
    cancelAnimationFrame(window._tatapPipRaf);
    window._tatapPipRaf = null;
  }
  if(window._tatapPipVideo){
    try{ window._tatapPipVideo.srcObject = null; }catch(_){}
  }

  // Inisialisasi tombol kembalikan fokus dari PiP
  var restoreBtn = $("pip-focus-restore-btn");
  if(restoreBtn && !restoreBtn._tatapInit){
    restoreBtn._tatapInit = true;
    restoreBtn.addEventListener("click", async function(e){
      e.preventDefault();
      e.stopPropagation();
      if(window.tatapPipWindow){
        try{ window.tatapPipWindow.close(); }catch(_){}
        window.tatapPipWindow = null;
      }
      if(document.pictureInPictureElement){
        try{ await document.exitPictureInPicture(); }catch(_){}
      }
      syncPipSubtitles(false);
    });
  }

  var focusOverlay = $("pip-focus-overlay");
  if(focusOverlay && !focusOverlay._tatapInit){
    focusOverlay._tatapInit = true;
    focusOverlay.addEventListener("click", async function(e){
      if(e.target === focusOverlay){
        if(window.tatapPipWindow){
          try{ window.tatapPipWindow.close(); }catch(_){}
          window.tatapPipWindow = null;
        }
        if(document.pictureInPictureElement){
          try{ await document.exitPictureInPicture(); }catch(_){}
        }
        syncPipSubtitles(false);
      }
    });
  }

  var hasActiveSub = !!(cur.cues && cur.cues.length && cur.activeSub && cur.activeSub !== "off");

  // 2. Prioritas 1: Document Picture-in-Picture API (Chrome 116+, Edge WebView2)
  // Menampilkan video hardware accelerated dengan subtitle DOM kustom (#pm-subs-overlay),
  // font kustom, translasi, dan styling penuh tanpa beban GPU berlebih (0% readback overhead).
  if(window.documentPictureInPicture && typeof window.documentPictureInPicture.requestWindow === "function"){
    try{
      var stage = document.querySelector(".ambient-stage");
      if(stage){
        var pipWidth = Math.min(640, window.innerWidth || 640);
        var pipHeight = Math.round(pipWidth * 9 / 16);
        var pipWindow = await window.documentPictureInPicture.requestWindow({
          width: pipWidth,
          height: pipHeight
        });

        // Kloning seluruh link css dan tag style ke dokumen PiP
        [].forEach.call(document.querySelectorAll("link[rel='stylesheet'], style"), function(sheet){
          try{ pipWindow.document.head.appendChild(sheet.cloneNode(true)); }catch(_){}
        });

        var stageParent = stage.parentNode;
        var stageSibling = stage.nextSibling;

        // Pasang placeholder di window utama agar tata letak tetap rapi
        var placeholder = document.getElementById("pip-stage-placeholder");
        if(!placeholder){
          placeholder = document.createElement("div");
          placeholder.id = "pip-stage-placeholder";
          placeholder.className = "pip-focus-placeholder";
          placeholder.innerHTML = '<div class="pip-focus-card">' +
            '<div class="pip-focus-icon-wrap"><svg class="ui-icon pip-focus-icon"><use href="#icon-fullscreen"/></svg></div>' +
            '<h3 class="pip-focus-title">Memutar di Picture-in-Picture</h3>' +
            '<p class="pip-focus-sub">Fokus visual dan subtitle dialihkan ke jendela mengambang PiP OS.</p>' +
            '<button type="button" class="pip-focus-restore-btn"><svg class="ui-icon"><use href="#icon-arrow-left"/></svg> <span>Kembalikan ke Jendela Ini</span></button>' +
            '</div>';
          var phBtn = placeholder.querySelector(".pip-focus-restore-btn");
          if(phBtn){
            phBtn.onclick = function(){
              if(window.tatapPipWindow){
                try{ window.tatapPipWindow.close(); }catch(_){}
              }
            };
          }
        }
        if(stageParent){
          stageParent.insertBefore(placeholder, stageSibling || null);
        }

        pipWindow.document.body.style.margin = "0";
        pipWindow.document.body.style.padding = "0";
        pipWindow.document.body.style.width = "100vw";
        pipWindow.document.body.style.height = "100vh";
        pipWindow.document.body.style.overflow = "hidden";
        pipWindow.document.body.style.background = "#000";

        var inStageOverlay = stage.querySelector("#pip-focus-overlay");
        if(inStageOverlay) inStageOverlay.classList.add("hidden");

        pipWindow.document.body.appendChild(stage);
        window.tatapPipWindow = pipWindow;
        syncPipSubtitles(true);

        var restoreFromDocPip = function(){
          if(placeholder && placeholder.parentNode){
            placeholder.parentNode.removeChild(placeholder);
          }
          if(stageParent){
            if(stageSibling) stageParent.insertBefore(stage, stageSibling);
            else stageParent.appendChild(stage);
          }
          window.tatapPipWindow = null;
          syncPipSubtitles(false);
          if(window.art && typeof window.art.resize === "function"){
            window.art.resize();
          }
        };

        pipWindow.addEventListener("pagehide", restoreFromDocPip, { once: true });
        pipWindow.addEventListener("unload", restoreFromDocPip, { once: true });
        pipWindow.addEventListener("resize", function(){
          if(window.art && typeof window.art.resize === "function"){
            window.art.resize();
          }
        });

        if(window.art && typeof window.art.resize === "function"){
          window.art.resize();
        }
        toast("Mode PiP Aktif (Subtitle Lengkap & Presisi)", 1500);
        return;
      }
    }catch(docPipErr){
      console.warn("Document Picture-in-Picture gagal, mencoba fallback:", docPipErr);
    }
  }

  // 3. Jika pengguna tidak menyalakan subtitle (Off/Raw), gunakan Direct Native Video PiP
  // Zero GPU Readback, 100% Hardware Accelerated DXVA/D3D11
  if(!hasActiveSub && typeof sourceVideo.requestPictureInPicture === "function"){
    try{
      await sourceVideo.requestPictureInPicture();
      syncPipSubtitles(true);
      toast("Mode PiP Aktif (Hardware Accelerated)", 1500);
      return;
    }catch(err){
      console.warn("Direct Native PiP request gagal, mencoba fallback canvas:", err);
    }
  }

  // 4. Fallback: True Native PiP via Canvas Stream (Subtitle di-burn langsung ke frame PiP dengan 640x360 @ 30fps)
  if(window.HTMLCanvasElement && typeof HTMLCanvasElement.prototype.captureStream === "function" && typeof document.createElement("video").requestPictureInPicture === "function"){
    try{
      if(!window._tatapPipCanvas){
        window._tatapPipCanvas = document.createElement("canvas");
        window._tatapPipCanvas.id = "tatap-pip-canvas";
        window._tatapPipCanvas.style.display = "none";
        document.body.appendChild(window._tatapPipCanvas);
      }
      if(!window._tatapPipVideo){
        window._tatapPipVideo = document.createElement("video");
        window._tatapPipVideo.id = "tatap-pip-video";
        window._tatapPipVideo.style.display = "none";
        window._tatapPipVideo.muted = true;
        window._tatapPipVideo.playsInline = true;
        document.body.appendChild(window._tatapPipVideo);
      }

      var pipCanvas = window._tatapPipCanvas;
      var pipVid = window._tatapPipVideo;

      // Downsampled target resolution 640x360 agar rendering sangat ringan di GPU/CPU
      var targetW = 640;
      var targetH = 360;
      if(sourceVideo.videoWidth && sourceVideo.videoHeight){
        var ratio = sourceVideo.videoWidth / sourceVideo.videoHeight;
        targetW = 640;
        targetH = Math.round(640 / ratio);
        if(targetH % 2 !== 0) targetH += 1;
      }
      pipCanvas.width = targetW;
      pipCanvas.height = targetH;

      var ctx = pipCanvas.getContext("2d");
      var pipRunning = true;
      var lastDraw = 0;
      var fpsInterval = 1000 / 30; // 30 FPS cap

      function drawPipLoop(now){
        if(!pipRunning) return;
        window._tatapPipRaf = requestAnimationFrame(drawPipLoop);
        if(now - lastDraw < fpsInterval) return;
        lastDraw = now;
        if(sourceVideo && sourceVideo.readyState >= 2){
          try{
            ctx.drawImage(sourceVideo, 0, 0, targetW, targetH);
            var lines = getActiveSubtitleLines(sourceVideo.currentTime);
            if(lines && lines.length){
              drawCanvasSubtitles(ctx, lines, targetW, targetH);
            }
          }catch(e){
            console.warn("Canvas PiP frame warning:", e);
          }
        }
      }

      drawPipLoop(performance.now());

      var stream = pipCanvas.captureStream(30);
      pipVid.srcObject = stream;
      await pipVid.play();

      var onLeavePip = function(){
        pipRunning = false;
        if(window._tatapPipRaf){
          cancelAnimationFrame(window._tatapPipRaf);
          window._tatapPipRaf = null;
        }
        try{ pipVid.srcObject = null; }catch(_){}
        syncPipSubtitles(false);
        pipVid.removeEventListener("leavepictureinpicture", onLeavePip);
      };
      pipVid.addEventListener("leavepictureinpicture", onLeavePip);

      pipVid.onplay = function(){
        if(sourceVideo && sourceVideo.paused) sourceVideo.play();
      };
      pipVid.onpause = function(){
        if(sourceVideo && !sourceVideo.paused) sourceVideo.pause();
      };

      await pipVid.requestPictureInPicture();
      syncPipSubtitles(true);
      toast("Mode PiP Aktif (Subtitle Burn-In)", 2000);
      return;
    }catch(err){
      console.warn("Canvas PiP fallback gagal:", err);
    }
  }

  // 5. Fallback terakhir: Direct Native Video PiP
  if(typeof sourceVideo.requestPictureInPicture === "function"){
    try{
      syncNativeTextTrack(cur._rawVtt, cur.cues, cur.subLang, true);
      await sourceVideo.requestPictureInPicture();
      syncPipSubtitles(true);
      toast("Mode PiP Aktif (Hardware Accelerated)", 1500);
      return;
    }catch(err){
      console.warn("Final Direct Native PiP request gagal:", err);
    }
  }

  toast("Picture-in-Picture tidak didukung di perangkat/peramban ini.", 2500);
}

function syncFullscreenSubtitles(){
  var isFs = isFullscreenActive();
  if(typeof window.tatap_set_fullscreen === "function"){
    try{ window.tatap_set_fullscreen(isFs); }catch(_){}
  }
  var vids = getActiveVideos();
  var isVidFs = isVideoFullscreen();
  var pipState = isPipActive();
  for(var vi = 0; vi < vids.length; vi++){
    var v = vids[vi];
    if(!v || !v.textTracks) continue;
    for(var i = 0; i < v.textTracks.length; i++){
      var t = v.textTracks[i];
      if(t.label && t.label.indexOf("Tatap") >= 0){
        t.mode=(isVidFs && !isDesktopEnv())?"showing":"hidden";
        if(pipState) t.mode = "showing";
      }
    }
  }
  paintCue();
}

function syncNativeTextTrack(vttText, cues, langCode, forceShow){
  cur._rawVtt = vttText || cur._rawVtt || "";
  cur.cues = cues || cur.cues || [];
  cur.subLang = langCode || cur.subLang || "id";

  var vids = getActiveVideos();
  if(!vids.length) return;

  var delay = cur.subDelay || 0;
  var pipState = isPipActive() || !!forceShow;
  var isVidFs = isVideoFullscreen();
  var targetMode = (pipState || (isVidFs && !isDesktopEnv())) ? "showing" : "hidden";

  for(var vi = 0; vi < vids.length; vi++){
    var v = vids[vi];
    if(!v) continue;

    var oldTracks = v.querySelectorAll("track.tatap-sub-track");
    for(var i = 0; i < oldTracks.length; i++){
      var trk = oldTracks[i];
      if(trk.parentNode) trk.parentNode.removeChild(trk);
    }

    if(v.textTracks){
      for(var j = 0; j < v.textTracks.length; j++){
        var tt = v.textTracks[j];
        if(tt.label && tt.label.indexOf("Tatap") >= 0){
          tt.mode = "disabled";
          if(tt.cues){
            for(var ci = tt.cues.length - 1; ci >= 0; ci--){
              try{ tt.removeCue(tt.cues[ci]); }catch(_){}
            }
          }
        }
      }
    }

    if(!cur._rawVtt && (!cur.cues || !cur.cues.length)) continue;

    try{
      var trackEl = document.createElement("track");
      trackEl.className = "tatap-sub-track";
      trackEl.kind = "captions";
      trackEl.label = "Tatap Subtitle (Indonesian)";
      trackEl.srclang = cur.subLang || "id";
      trackEl.default = true;

      var vttContent = cur._rawVtt;
      if(cur.cues && cur.cues.length){
        vttContent = generateVttWithOffset(cur.cues, delay);
      }

      if(vttContent && window.Blob && window.URL && window.URL.createObjectURL){
        var blob = new Blob([vttContent], {type: "text/vtt;charset=utf-8"});
        trackEl.src = URL.createObjectURL(blob);
      }

      var applyTrackMode = (function(tEl){
        return function(){
          if(tEl.track){
            var curPip = isPipActive() || !!forceShow;
            var curFs = isVideoFullscreen() && !isDesktopEnv();
            tEl.track.mode = (curPip || curFs) ? "showing" : "hidden";
          }
        };
      })(trackEl);

      trackEl.addEventListener("load", applyTrackMode);
      v.appendChild(trackEl);
      applyTrackMode();

      if(trackEl.track && cur.cues && cur.cues.length && window.VTTCue){
        for(var k = 0; k < cur.cues.length; k++){
          var c = cur.cues[k];
          var start = Math.max(0, (c.start || 0) + delay);
          var end = Math.max(start + 0.1, (c.end || 0) + delay);
          var plain = c.plain || (c.html ? c.html.replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]+>/g, "") : "");
          try{
            trackEl.track.addCue(new VTTCue(start, end, plain || "..."));
          }catch(e){}
        }
        applyTrackMode();
      }
    }catch(err){
      console.warn("syncNativeTextTrack error:", err);
    }
  }
}
function toggleFullscreen(){
  var fsEl = document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement;
  var isFs = !!fsEl || (window.art && window.art.fullscreen) || (window._isTatapDesktopFs === true);
  var targetState = !isFs;

  // 1. Sinkronkan ke native Go WebView2 jika ada (Windows Portable)
  window._isTatapDesktopFs = targetState;
  if(typeof window.tatap_set_fullscreen === "function"){
    try{ window.tatap_set_fullscreen(targetState); }catch(_){}
  }

  // 2. Jalankan fullscreen pada Artplayer jika aktif
  var artHandled = false;
  if(window.art){
    try {
      window.art.fullscreen = targetState;
      artHandled = true;
    } catch(e){
      console.warn("art.fullscreen toggle error:", e);
    }
  }

  // 3. Fallback browser HTML5 requestFullscreen jika Artplayer belum menangani fullscreen
  if(!artHandled){
    var stage = (window.art && window.art.template && window.art.template.$player) || document.getElementById("player-modal") || document.querySelector(".ambient-stage");
    if(targetState){
      if(!fsEl && stage){
        var req = stage.requestFullscreen || stage.webkitRequestFullscreen || stage.mozRequestFullScreen || stage.msRequestFullscreen;
        if(req){
          try{
            var p = req.call(stage);
            if(p && p.catch) p.catch(function(){});
          }catch(_){}
        }
      }
    } else {
      if(fsEl){
        var exit = document.exitFullscreen || document.webkitExitFullscreen || document.mozCancelFullScreen || document.msExitFullscreen;
        if(exit){
          try{
            var p = exit.call(document);
            if(p && p.catch) p.catch(function(){});
          }catch(_){}
        }
      }
    }
  }

  var pm = $("player-modal");
  if(pm){
    if(targetState) pm.classList.add("is-fullscreen");
    else pm.classList.remove("is-fullscreen");
  }

  var stageEl = document.querySelector(".ambient-stage");
  if(stageEl){
    if(targetState) stageEl.classList.add("is-fullscreen");
    else stageEl.classList.remove("is-fullscreen");
  }
  syncFullscreenSubtitles();
}
function paintCue(){
  var box=$("pm-subs-overlay");
  var v=$("vid");
  if(!box)return;
  var s=box.querySelector("span");
  if($("player-modal").classList.contains("hidden")){
    if(s){ s.innerHTML=""; s._last=""; }
    if(window.art && window.art.template && window.art.template.$subtitle){
      window.art.template.$subtitle.innerHTML="";
    }
    return;
  }
  var t = (window.art && typeof window.art.currentTime === "number" && !isNaN(window.art.currentTime))
          ? window.art.currentTime
          : ((v && !isNaN(v.currentTime)) ? v.currentTime : 0);
  var subTime = t - (cur.subDelay || 0.0);
  if(isVideoFullscreen() && !isDesktopEnv()){
    if(s && s._last!==""){s.innerHTML="";s._last="";}
    box.style.display="none";
  }else{
    box.style.display="";
    var activeParts=[];
    for(var i=0;i<cur.cues.length;i++){
      if(subTime>=cur.cues[i].start&&subTime<=cur.cues[i].end){
        var h=cur.cues[i].html;
        if(h && activeParts.indexOf(h)===-1) activeParts.push(h);
      }
    }
    var html=activeParts.join("<br>");
    if(s && s._last!==html){s.innerHTML=html;s._last=html;}
    if(window.art && window.art.template && window.art.template.$subtitle){
      var artSub = window.art.template.$subtitle;
      if(artSub._last !== html){
        artSub.innerHTML = html ? ("<div class='art-subtitle-inner'>" + html + "</div>") : "";
        artSub._last = html;
      }
    }
  }
  checkSkipTimes(t);
}

function isValidSkipInterval(inv){
  return !!(inv && typeof inv.start === "number" && typeof inv.end === "number" &&
            inv.end > inv.start && inv.end > 0 && (inv.end - inv.start) >= 5.0);
}

function checkSkipTimes(currentTime){
  var btn=$("pm-skip-btn");
  var label=$("pm-skip-label");
  var artBtn=$("art-aniskip-btn");
  var artLabel=$("art-aniskip-text");
  if(!btn && !artBtn){return;}
  var v=$("vid");
  var intro=cur.intro;
  var outro=cur.outro;
  var isAutoSkip = !!(window.settings && window.settings.autoSkip !== undefined ? window.settings.autoSkip : cur.autoSkip);
  var t = (typeof currentTime === "number" && !isNaN(currentTime)) ? currentTime : ((window.art && !isNaN(window.art.currentTime)) ? window.art.currentTime : (v ? v.currentTime : 0));
  var dur = (window.art && !isNaN(window.art.duration)) ? window.art.duration : (v ? v.duration : Infinity);

  var inIntro=(intro && intro.end > intro.start && intro.end > 0 && t >= intro.start && t < (intro.end - 0.5));
  var inOutro=(outro && outro.end > outro.start && outro.end > 0 && t >= outro.start && t < (outro.end - 0.5));

  if(inIntro){
    cur.activeSkipTarget = Math.min(dur, intro.end + 0.5);
    if(isAutoSkip && !cur.hasAutoSkippedIntro){
      cur.hasAutoSkippedIntro = true;
      if(window.art) window.art.currentTime = cur.activeSkipTarget;
      else if(v) v.currentTime = cur.activeSkipTarget;
      if(btn) btn.classList.add("hidden");
      if(artBtn) artBtn.classList.add("hidden");
      cur.activeSkipTarget = 0;
      toast("⏩ Lewati Opening otomatis", 1500);
      return;
    }
    if(label) label.textContent = "Lewati Opening (S)";
    if(artLabel) artLabel.textContent = "Lewati Opening (S)";
    if(btn) btn.classList.remove("hidden");
    if(artBtn) artBtn.classList.remove("hidden");
  }else if(inOutro){
    cur.activeSkipTarget = Math.min(dur, outro.end + 0.5);
    if(isAutoSkip && !cur.hasAutoSkippedOutro){
      cur.hasAutoSkippedOutro = true;
      if(window.art) window.art.currentTime = cur.activeSkipTarget;
      else if(v) v.currentTime = cur.activeSkipTarget;
      if(btn) btn.classList.add("hidden");
      if(artBtn) artBtn.classList.add("hidden");
      cur.activeSkipTarget = 0;
      toast("⏩ Lewati Ending otomatis", 1500);
      return;
    }
    if(label) label.textContent = "Lewati Ending (S)";
    if(artLabel) artLabel.textContent = "Lewati Ending (S)";
    if(btn) btn.classList.remove("hidden");
    if(artBtn) artBtn.classList.remove("hidden");
  }else{
    cur.activeSkipTarget = 0;
    if(btn) btn.classList.add("hidden");
    if(artBtn) artBtn.classList.add("hidden");
  }
}

function doSkip(){
  if(cur.activeSkipTarget && cur.activeSkipTarget > 0){
    var v=$("vid");
    if(window.art || v){
      var t = (window.art && !isNaN(window.art.currentTime)) ? window.art.currentTime : (v ? v.currentTime : 0);
      if(cur.intro && t >= cur.intro.start && t < cur.intro.end){
        cur.hasAutoSkippedIntro = true;
      }
      if(cur.outro && t >= cur.outro.start && t < cur.outro.end){
        cur.hasAutoSkippedOutro = true;
      }
      if(window.art) window.art.currentTime = cur.activeSkipTarget;
      else if(v) v.currentTime = cur.activeSkipTarget;
      var btn=$("pm-skip-btn");
      if(btn) btn.classList.add("hidden");
      var artBtn=$("art-aniskip-btn");
      if(artBtn) artBtn.classList.add("hidden");
      toast("⏩ Melompat ke "+formatTime(cur.activeSkipTarget), 1500);
      cur.activeSkipTarget = 0;
      return true;
    }
  }
  return false;
}

function formatTime(sec){
  var s=Math.floor(sec||0);
  var m=Math.floor(s/60);
  s=s%60;
  return (m<10?"0"+m:m)+":"+(s<10?"0"+s:s);
}
function prefetchSubtitleTrack(url, ref, langCode){
  if(!url)return null;
  var targetUrl = url;
  var targetLang = langCode || "";
  var mode = "";
  var isDual = false;
  var isOs = false;
  if(targetUrl.indexOf("os_merge:")===0){
    targetUrl = targetUrl.slice(9);
    if(!targetLang) targetLang = "id";
    mode = "os_merge";
    isOs = true;
  }else if(targetUrl.indexOf("os_dual:")===0){
    targetUrl = targetUrl.slice(8);
    if(!targetLang) targetLang = "id";
    mode = "os_dual";
    isOs = true;
  }else if(targetUrl.indexOf("gtx+_dual:")===0){
    targetUrl = targetUrl.slice(10);
    if(!targetLang) targetLang = "id";
    mode = "gtx+_dual";
    isDual = true;
  }else if(targetUrl.indexOf("gtx+:")===0){
    targetUrl = targetUrl.slice(5);
    if(!targetLang) targetLang = "id";
    mode = "gtx+";
  }else if(targetUrl.indexOf("aigtx:")===0){
    targetUrl = targetUrl.slice(6);
    if(!targetLang) targetLang = "id";
    mode = "gtx+";
  }else if(targetUrl.indexOf("ai:")===0){
    targetUrl = targetUrl.slice(3);
    if(!targetLang) targetLang = "id";
    mode = "ai";
  }else if(targetUrl.indexOf("gtx:")===0){
    targetUrl = targetUrl.slice(4);
    if(!targetLang) targetLang = "id";
    mode = "gtx";
  }
  var qs = "url=" + encodeURIComponent(targetUrl) + "&referer=" + encodeURIComponent(ref || "");
  if(targetLang) qs += "&lang=" + encodeURIComponent(targetLang);
  if(mode) qs += "&mode=" + encodeURIComponent(mode);
  if(isDual) qs += "&dual=true";
  if(isOs){
    // Konteks judul & episode agar backend dapat mencari rilis yang cocok di OpenSubtitles
    var altTitle=(cur.meta&&(cur.meta.title_romaji||cur.meta.title_english))||"";
    var seasonNum=0;
    if(cur.meta){
      if(typeof cur.meta.season_number==="number") seasonNum=cur.meta.season_number;
      else if(typeof cur.meta.season==="number") seasonNum=cur.meta.season;
      else if(typeof cur.meta.season==="string" && /^\d+$/.test(cur.meta.season.trim())) seasonNum=parseInt(cur.meta.season.trim(),10);
    }
    qs += "&title=" + encodeURIComponent(cur.title || "") + "&slug=" + encodeURIComponent(cur.slug || "") + "&ep=" + encodeURIComponent(cur.ep || 1);
    if(seasonNum) qs += "&season=" + encodeURIComponent(seasonNum);
    if(altTitle) qs += "&alt_title=" + encodeURIComponent(altTitle);
  }
  var prox = "/api/player/sub?" + qs;

  // Cek apakah promise untuk URL yang sama sudah berjalan
  if(cur._subPrefetch && cur._subPrefetch.prox === prox){
    return cur._subPrefetch.promise;
  }

  var p = fetch(prox).then(function(r){
    if(!r.ok)throw new Error("HTTP "+r.status);
    var tier=r.headers.get("X-Translate-Tier")||"";
    var trErr=r.headers.get("X-Translate-Error")||"";
    var trModel=r.headers.get("X-Translate-Model")||"";
    var trMixed=r.headers.get("X-Translate-Mixed")||"";
    var trBg=r.headers.get("X-Translate-Background")||"";
    var osFile=r.headers.get("X-OpenSubtitles-File")||"";
    var osMerge=r.headers.get("X-OpenSubtitles-Merge")||"";
    return r.text().then(function(t){
      return {text:t, tier:tier, error:trErr, model:trModel, mixed:trMixed, bg:trBg, osFile:osFile, osMerge:osMerge};
    });
  });

  cur._subPrefetch = {prox: prox, promise: p};
  return p;
}

function switchSubtitleTrack(url, langCode){
  // Render subtitle milik app (overlay div), bukan <track> native.
  // Style tidak lagi mengikuti setting caption Windows.
  // langCode opsional ("id", "ja", dst.) — backend akan translate kalau beda.
  var v=$("vid");
  if(!v)return;
  var token = cur.playToken;
  // Bersihkan track lama lalu kosongkan overlay.
  syncNativeTextTrack("", [], "");
  cur.cues=[];
  clearOverlay();
  if(cur._subUpgradeTimer){
    clearTimeout(cur._subUpgradeTimer);
    cur._subUpgradeTimer = null;
  }
  if(!url || typeof url !== "string") return;
  var cleanSubUrl = url.trim();
  if(/^\d+$/.test(cleanSubUrl)) return;
  var originalUrl = url;
  var trackMode = "none";
  if(url.indexOf("os_merge:")===0){
    url=url.slice(9);
    if(!langCode) langCode="id";
    trackMode = "os_merge";
  }else if(url.indexOf("os_dual:")===0){
    url=url.slice(8);
    if(!langCode) langCode="id";
    trackMode = "os_dual";
  }else if(url.indexOf("gtx+_dual:")===0){
    url=url.slice(10);
    if(!langCode) langCode="id";
    trackMode = "gtx+_dual";
  }else if(url.indexOf("gtx+:")===0){
    url=url.slice(5);
    if(!langCode) langCode="id";
    trackMode = "gtx+";
  }else if(url.indexOf("aigtx:")===0){
    url=url.slice(6);
    if(!langCode) langCode="id";
    trackMode = "gtx+";
  }else if(url.indexOf("ai:")===0){
    url=url.slice(3);
    if(!langCode) langCode="id";
    trackMode = "ai";
  }else if(url.indexOf("gtx:")===0){
    url=url.slice(4);
    if(!langCode) langCode="id";
    trackMode = "gtx";
  }
  if(langCode==="id"){
    var waitMsg = "Menerjemahkan subtitle AI ke bahasa Indonesia...";
    if(trackMode==="os_merge") waitMsg = "Mengunduh subtitle OpenSubtitles & merge dengan subtitle bawaan...";
    else if(trackMode==="os_dual") waitMsg = "Mengunduh OpenSubtitles & menyusun bilingual dengan subtitle bawaan...";
    else if(trackMode==="gtx+_dual") waitMsg = "Menerjemahkan subtitle GTX+ Bilingual (ID + EN)...";
    else if(trackMode==="gtx+"||trackMode==="aigtx") waitMsg = "Menerjemahkan subtitle GTX+ (Smart Fansub & Scene Detection)...";
    else if(trackMode==="gtx") waitMsg = "Menerjemahkan subtitle Google GTX...";
    toast(waitMsg, 3000);
    var obox=$("pm-subs-overlay");
    if(obox){
      var osp=obox.querySelector("span");
      if(osp){
        osp.textContent="[" + waitMsg + "]";
        osp._last=osp.textContent;
      }
    }
    if(window.art && window.art.template && window.art.template.$subtitle){
      window.art.template.$subtitle.innerHTML = "<div class='art-subtitle-inner' style='opacity:0.75;font-size:14px;'>[" + esc(waitMsg) + "]</div>";
      window.art.template.$subtitle._last = waitMsg;
    }
  }
  var ref=cur.res&&cur.res.referer||"";
  var subPromise = prefetchSubtitleTrack(originalUrl, ref, langCode);
  subPromise.then(function(res){
    if(cur.playToken !== token) return;
    clearOverlay();
    cur.cues=parseVtt(res.text);
    paintCue();
    syncNativeTextTrack(res.text, cur.cues, langCode);
    if(langCode==="id"){
      if(res.tier==="source"||res.tier==="source-fallback"){
        var msg="Gagal translate";
        if(res.error) msg+=": "+res.error;
        else msg+=" (menampilkan subtitle asli)";
        toast(msg, 6000);
      }else{
        var tierLabel = "AI Fansub" + (res.model ? " · "+res.model : "");
        if(res.tier === "os_merge" || res.tier === "os_dual" || res.tier === "smart_merge"){
          tierLabel = "Smart Fansub & Merge" + (res.osFile ? " · " + res.osFile : "");
        }else if(res.tier === "cached-os_merge" || res.tier === "cached-os_dual" || res.tier === "cached-smart_merge"){
          tierLabel = "Smart Fansub & Merge, tersimpan";
        }else if(res.tier === "os_fallback_gtx+"){
          tierLabel = "Smart GTX+ Bawaan";
        }else if(res.tier === "gtx+" || res.tier === "cached-gtx+" || res.tier === "aigtx" || res.tier === "cached-aigtx"){
          tierLabel = (res.tier === "cached-gtx+" || res.tier === "cached-aigtx") ? "GTX+, tersimpan" : "GTX+ Translate";
        }else if(res.tier === "tier2"){
          tierLabel = trackMode === "gtx" ? "Google GTX" : "GTX+ (Instan)";
        }else if(res.tier === "cached-mt" || res.tier === "cached-gtx"){
          tierLabel = trackMode === "gtx" ? "Google GTX, tersimpan" : "GTX+, tersimpan";
        }else if(res.tier === "ai" || res.tier === "tier3" || res.tier === "cached-llm" || res.tier === "cached"){
          tierLabel = "AI Fansub" + (res.model ? " · "+res.model : "");
        }
        var extra = "";
        if(res.mixed) extra = " · "+res.mixed+" baris via GTX";
        toast("Subtitle Indonesia siap ("+tierLabel+")! ("+cur.cues.length+" baris"+extra+")", 4000);

        // Jika mode AI Fansub dan disajikan instan via GTX+ / MT, upgrade di background saat AI selesai:
        if(trackMode === "ai" && (res.bg === "llm-translating" || res.tier === "tier2" || res.tier === "gtx+" || res.tier === "cached-gtx+" || res.tier === "aigtx" || res.tier === "cached-aigtx" || res.tier === "cached-mt")){
          var checkUpgrade = function(attempt){
            if(cur.playToken !== token) return;
            if(attempt > 20) return; // Maksimal ~5 menit
            cur._subUpgradeTimer = setTimeout(function(){
              if(cur.playToken !== token) return;
              var qs = "url=" + encodeURIComponent(url) + "&referer=" + encodeURIComponent(ref || "") + "&lang=id";
              fetch("/api/player/sub?" + qs).then(function(ur){
                if(cur.playToken !== token) return;
                var uTier = ur.headers.get("X-Translate-Tier") || "";
                var uModel = ur.headers.get("X-Translate-Model") || "";
                if(uTier === "cached" || uTier === "cached-llm" || uTier === "ai" || uTier === "tier3" || uTier === "tier1"){
                  ur.text().then(function(uText){
                    if(cur.playToken !== token) return;
                    cur.cues = parseVtt(uText);
                    paintCue();
                    syncNativeTextTrack(uText, cur.cues, "id");
                    var lbl = "AI Fansub" + (uModel ? " · " + uModel : "");
                    toast("✨ Subtitle berhasil di-upgrade ke " + lbl + "!", 5000);
                  });
                }else{
                  checkUpgrade(attempt + 1);
                }
              }).catch(function(){});
            }, 15000);
          };
          checkUpgrade(1);
        }
      }
    }
  }).catch(function(err){
    if(cur.playToken !== token) return;
    cur.cues=[];
    clearOverlay();
    syncNativeTextTrack("", [], "");
    if(langCode==="id"){
      toast("Gagal menerjemahkan subtitle: "+(err&&err.message||err));
    }
  });
}

var TouchGestures = {
  startX: 0,
  startY: 0,
  lastTap: 0,
  lastTapX: 0,
  mode: null,       // 'volume' | 'brightness' | 'seek' | null
  initVol: 1,
  initBright: 100,
  initTime: 0,
  currentBright: 100,
  osdTimer: null,
  armed: false,

  showOSD: function(icon, pct, text){
    var el = $("pm-gesture-osd");
    if(!el) return;
    var iconEl = $("pm-osd-icon");
    if(icon && (icon.indexOf("<svg") >= 0 || icon.indexOf("<") >= 0)){
      iconEl.innerHTML = icon;
    } else {
      iconEl.textContent = icon;
    }
    $("pm-osd-bar").style.width = Math.max(0, Math.min(100, pct)) + "%";
    $("pm-osd-val").textContent = text != null ? text : Math.round(pct) + "%";
    el.classList.remove("hidden");
    clearTimeout(this.osdTimer);
    this.osdTimer = setTimeout(function(){ el.classList.add("hidden"); }, 1200);
  },

  triggerRipple: function(side, text){
    var rip = $(side === "left" ? "pm-ripple-left" : "pm-ripple-right");
    if(!rip) return;
    if(text) {
      var t = rip.querySelector(".ripple-text");
      if(t) t.textContent = text;
    }
    rip.classList.remove("active");
    void rip.offsetWidth; // force reflow
    rip.classList.add("active");
    setTimeout(function(){ rip.classList.remove("active"); }, 400);
    // Haptic feedback via native bridge or Web Vibration API
    if(window.TatapNative && window.TatapNative.vibrate){
      window.TatapNative.vibrate(25);
    } else if(navigator.vibrate){
      try{ navigator.vibrate(25); }catch(e){}
    }
  },

  bind: function(){
    if(this.armed) return;
    this.armed = true;
    var stage = document.querySelector(".ambient-stage");
    if(!stage) return;

    var self = this;
    var getVid = function(){
      return (window.art && window.art.template && window.art.template.$video) || $("vid");
    };

    stage.addEventListener("touchstart", function(e){
      if(e.touches.length !== 1) return;
      var v = getVid();
      if(!v) return;
      var touch = e.touches[0];
      var rect = stage.getBoundingClientRect();
      self.startX = touch.clientX;
      self.startY = touch.clientY;
      self.mode = null;
      self.initVol = (window.art && typeof window.art.volume === "number") ? window.art.volume : (v.volume || 1);
      self.initBright = self.currentBright;
      self.initTime = (window.art && typeof window.art.currentTime === "number") ? window.art.currentTime : (v.currentTime || 0);
    }, {passive: true});

    stage.addEventListener("touchmove", function(e){
      if(e.touches.length !== 1) return;
      var v = getVid();
      if(!v) return;
      var touch = e.touches[0];
      var rect = stage.getBoundingClientRect();
      var dx = touch.clientX - self.startX;
      var dy = touch.clientY - self.startY;
      var relX = (self.startX - rect.left) / rect.width;

      if(!self.mode){
        if(Math.abs(dx) > 18 && Math.abs(dx) > Math.abs(dy)){
          self.mode = "seek";
        } else if(Math.abs(dy) > 18 && Math.abs(dy) > Math.abs(dx)){
          self.mode = (relX < 0.5) ? "brightness" : "volume";
        }
      }

      if(self.mode === "seek"){
        var dur = (window.art && window.art.duration) || v.duration || 1400;
        var scrub = (dx / rect.width) * 90; // geser penuh layar = +/- 90 detik
        var target = Math.max(0, Math.min(dur, self.initTime + scrub));
        var diff = Math.round(target - self.initTime);
        var sign = diff >= 0 ? "+" : "";
        var min = Math.floor(target / 60);
        var sec = Math.floor(target % 60);
        var timeStr = min + ":" + (sec < 10 ? "0" : "") + sec;
        self.showOSD('<svg class="ui-icon"><use href="#icon-forward"/></svg>', (target / dur) * 100, timeStr + " (" + sign + diff + "s)");
        self._targetSeek = target;
      } else if(self.mode === "volume"){
        var deltaV = (-dy / rect.height) * 1.5;
        var nv = Math.max(0, Math.min(1, self.initVol + deltaV));
        if(window.art) window.art.volume = nv;
        v.volume = nv;
        v.muted = (nv === 0);
        var ic = nv === 0 ? '<svg class="ui-icon"><use href="#icon-volume-mute"/></svg>' : (nv < 0.5 ? '<svg class="ui-icon"><use href="#icon-volume-mid"/></svg>' : '<svg class="ui-icon"><use href="#icon-volume-high"/></svg>');
        self.showOSD(ic, nv * 100);
      } else if(self.mode === "brightness"){
        var deltaB = (-dy / rect.height) * 120;
        var nb = Math.max(20, Math.min(150, self.initBright + deltaB));
        self.currentBright = nb;
        v.style.filter = "brightness(" + (nb / 100) + ")";
        if(window.TatapNative && window.TatapNative.setBrightness){
          window.TatapNative.setBrightness(nb / 100);
        }
        self.showOSD('<svg class="ui-icon"><use href="#icon-sun"/></svg>', (nb / 150) * 100, Math.round(nb) + "%");
      }
    }, {passive: true});

    stage.addEventListener("touchend", function(e){
      var v = getVid();
      if(self.mode === "seek" && self._targetSeek != null){
        if(window.art) window.art.currentTime = self._targetSeek;
        else if(v) v.currentTime = self._targetSeek;
        self._targetSeek = null;
        self.mode = null;
        return;
      }
      if(self.mode){
        self.mode = null;
        return;
      }

      // Deteksi tap & double-tap
      var now = Date.now();
      var rect = stage.getBoundingClientRect();
      var relX = (self.startX - rect.left) / rect.width;

      if(now - self.lastTap < 320 && Math.abs(self.startX - self.lastTapX) < 80){
        // Double Tap
        self.lastTap = 0; // reset
        if(relX < 0.35){
          if(window.art) window.art.seek = Math.max(0, window.art.currentTime - 10);
          else if(v) v.currentTime = Math.max(0, v.currentTime - 10);
          self.triggerRipple("left", "-10s");
          var cT = (window.art && window.art.currentTime) || (v && v.currentTime) || 0;
          toast("-10s (" + formatTimeSec(cT) + ")", 1000, "icon-rewind");
        } else if(relX > 0.65){
          var dur = (window.art && window.art.duration) || (v && v.duration) || 99999;
          if(window.art) window.art.seek = Math.min(dur, window.art.currentTime + 10);
          else if(v) v.currentTime = Math.min(dur, v.currentTime + 10);
          self.triggerRipple("right", "+10s");
          var cT2 = (window.art && window.art.currentTime) || (v && v.currentTime) || 0;
          toast("+10s (" + formatTimeSec(cT2) + ")", 1000, "icon-forward");
        } else {
          if(window.art) window.art.toggle();
          else if(v) { if(v.paused) v.play(); else v.pause(); }
        }
      } else {
        self.lastTap = now;
        self.lastTapX = self.startX;
      }
    }, {passive: true});
  }
};

function armAutohide(){
  var stage=document.querySelector(".ambient-stage");
  var shell=document.querySelector(".player-shell");
  TouchGestures.bind();
  if(!stage||stage._armed)return;
  stage._armed=true;
  var v=$("vid");
  var show=function(){
    TvNavigationManager.showPlayerControls();
  };
  var wake=function(){
    var vid = $("vid");
    if(vid && vid.hasAttribute("controls")) vid.removeAttribute("controls");
    show();
  };
  ["mousemove","touchstart","click"].forEach(function(ev){stage.addEventListener(ev,wake,{passive:true});});
  if(v){
    v.removeAttribute("controls");
    v.addEventListener("play",show);
    v.addEventListener("pause",function(){
      clearTimeout(TvNavigationManager.getHudTimer && TvNavigationManager.getHudTimer());
      v.removeAttribute("controls");
      if(stage) stage.classList.remove("idle");
      if(shell) shell.classList.remove("idle");
      TvNavigationManager.setPlayerState(TvNavigationManager.PLAYER_HUD_ACTIVE);
    });
    v.addEventListener("seeking",show);
  }
  show();
}
function playUrl(url,referrer,sub,subRef,resumeTime,token){
  var pm = $("player-modal");
  var v=$("vid");
  if(!pm || pm.classList.contains("hidden") || (token && cur.playToken !== token)){
    if(window.art){try{window.art.destroy(false);window.art=null;}catch(e){}}
    if(window._hls){try{window._hls.destroy();window._hls=null;}catch(e){}}
    if(v){try{v.pause();v.removeAttribute("src");v.load();}catch(e){}}
    return;
  }
  if(window.art){
    try{window.art.destroy(false);window.art=null;}catch(e){}
  }
  if(v){
    v.muted=false;
    if(v.volume===0) v.volume=1.0;
  }
  var b = (typeof apiBase === "function") ? apiBase() : "";
  var prox=b+"/api/player/video?url="+encodeURIComponent(url)+"&referer="+encodeURIComponent(referrer||"");
  // Bersihkan <track> lama lalu pasang track subtitle aktif (live switch).
  // Fungsi switchSubtitleTrack() menhandle Off (hapus semua) dan replace.
  var validSub = (typeof sub === "string" && !/^\d+$/.test(sub.trim())) ? sub : null;
  switchSubtitleTrack(validSub);
  $("pm-spinner").classList.remove("hidden");
  $("pm-status").textContent="menyiapkan pemutar...";
  var onCan=function(){
    $("pm-spinner").classList.add("hidden");
    if(resumeTime && resumeTime > 0){
      try{
        if(window.art) window.art.currentTime = resumeTime;
        else if(v) v.currentTime = resumeTime;
      }catch(e){}
    }
  };
  if(v) v.addEventListener("canplay",onCan,{once:true});
  var cleanPath = (url || "").split("?")[0].toLowerCase();
  var isSeg = cleanPath.endsWith(".ts") || cleanPath.endsWith(".ts.jpg") || cleanPath.endsWith(".mp4") || cleanPath.endsWith(".aac");
  var isHls = !isSeg && ((url.indexOf(".m3u8") >= 0) || (url.indexOf("format=m3u8") >= 0) || (url.indexOf("/api/hls") >= 0) || (url.indexOf("/hls/playlist") >= 0) || (url.indexOf("/api/player/video") >= 0) || (url.indexOf("master") >= 0) || (url.indexOf("playlist") >= 0) || (cur.res && cur.res.variants && cur.res.variants.length > 0));

  var artContainer = $("artplayer-container");
  if(typeof Artplayer !== "undefined" && artContainer){
    Artplayer.FULLSCREEN_WEB_IN_BODY = false;
    if(window.art){
      try{
        if(window.art.fullscreenWeb) window.art.fullscreenWeb = false;
        if(window.art.fullscreen) window.art.fullscreen = false;
        if(window.art.template && window.art.template.$player && window.art.template.$player.parentNode){
          window.art.template.$player.parentNode.removeChild(window.art.template.$player);
        }
        window.art.destroy(true);
        window.art = null;
      }catch(_){}
    }
    document.querySelectorAll("body > .art-video-player").forEach(function(el){
      try{ el.parentNode.removeChild(el); }catch(_){}
    });
    document.body.classList.remove("art-fullscreen-web");
    artContainer.innerHTML = "";
    var epTitle = (cur.title || "") + (cur.ep ? (" - Episode " + cur.ep) : "");
    var initialSubCtrl = buildSubtitleControl((cur.res && cur.res.subtitles) || [], validSub);
    var initialQualityCtrl = buildQualityControl((cur.res && cur.res.hlsLevels) || (cur.res && cur.res.variants), cur.quality || "Auto");
    var initialSubLabel = (initialSubCtrl.selector.find(function(t){ return t.default; }) || {}).html || "Off";

    var art = new Artplayer({
      container: artContainer,
      url: prox,
      type: isHls ? "m3u8" : "mp4",
      title: epTitle,
      poster: sanitizePosterUrl(cur.poster),
      volume: (v && v.volume !== undefined) ? v.volume : 1.0,
      isLive: false,
      muted: false,
      autoplay: true,
      autoSize: false,
      autoMini: false,
      screenshot: true,
      setting: true,
      loop: false,
      flip: true,
      playbackRate: true,
      aspectRatio: true,
      hotkey: false,
      pip: true,
      fullscreen: true,
      fullscreenWeb: true,
      miniProgressBar: false,
      mutex: true,
      backdrop: true,
      playsInline: true,
      autoPlayback: true,
      theme: "#38bdf8",
      lang: "id",
      settings: [
        {
          name: "subtitle-track",
          width: 290,
          html: "Pilih Subtitle",
          tooltip: initialSubLabel,
          selector: initialSubCtrl.selector,
          onSelect: function(item){
            var sel = $("pm-subs");
            if(sel){ sel.value = item.value; if(typeof sel.onchange === "function") sel.onchange(); }
            else switchSubtitleTrack(item.value);
            if(window.art && window.art.notice) window.art.notice.show = "Subtitle: " + item.html;
            return item.html;
          }
        },
        {
          name: "video-quality",
          width: 220,
          html: "Kualitas Video",
          tooltip: (cur.quality || "Auto").toUpperCase(),
          selector: initialQualityCtrl.selector,
          onSelect: function(item){
            switchQ(item.html);
            if(window.art && window.art.notice) window.art.notice.show = "Resolusi: " + item.html;
            return item.html;
          }
        },
        {
          name: "subtitle-styler-modal",
          width: 260,
          html: "🎨 Buka Subtitle Styler...",
          tooltip: "Pratinjau & Kustomisasi",
          onClick: function(){
            if(window.art && window.art.setting) window.art.setting.show = false;
            openSubStyleModal();
            return "";
          },
          mounted: function($item){
            if($item){
              $item.addEventListener("click", function(e){
                e.stopPropagation();
                if(window.art && window.art.setting) window.art.setting.show = false;
                openSubStyleModal();
              });
            }
          }
        },
        {
          name: "subtitle-font",
          width: 250,
          html: "Jenis Huruf (Font)",
          tooltip: getSubFontName(cur.subFont || "sans"),
          selector: [
            { html: "Modern Sans (Default)", value: "sans", default: !cur.subFont || cur.subFont === "sans" },
            { html: "Clean Rounded", value: "rounded", default: cur.subFont === "rounded" },
            { html: "Anime Fansub (Tahoma)", value: "tahoma", default: cur.subFont === "tahoma" },
            { html: "Cinematic Serif", value: "serif", default: cur.subFont === "serif" },
            { html: "Cyber Monospace", value: "mono", default: cur.subFont === "mono" },
            { html: "Action Impact", value: "impact", default: cur.subFont === "impact" }
          ],
          onSelect: function(item){
            setSubFont(item.value);
            return item.html;
          }
        },
        {
          name: "subtitle-size",
          width: 230,
          html: "Ukuran Subtitle",
          tooltip: (cur.subSize || "m").toUpperCase(),
          selector: [
            { name: "sub-sz-s", html: "Kecil (S)", value: "s", default: cur.subSize === "s" },
            { name: "sub-sz-m", html: "Sedang (M)", value: "m", default: !cur.subSize || cur.subSize === "m" },
            { name: "sub-sz-l", html: "Besar (L)", value: "l", default: cur.subSize === "l" },
            { name: "sub-sz-xl", html: "Ekstra Besar (XL)", value: "xl", default: cur.subSize === "xl" }
          ],
          onSelect: function(item){
            setSubSize(item.value);
            return item.html;
          }
        },
        {
          name: "subtitle-color",
          width: 250,
          html: "Warna Subtitle",
          tooltip: getSubColorName(cur.subColor || "#ffffff"),
          selector: [
            { html: "⚪ Putih Bersih (Default)", value: "#ffffff", default: !cur.subColor || cur.subColor === "#ffffff" },
            { html: "🟡 Kuning Emas (Anime Classic)", value: "#facc15", default: cur.subColor === "#facc15" },
            { html: "🔵 Cyan Cyber (Tatap Neon)", value: "#38bdf8", default: cur.subColor === "#38bdf8" },
            { html: "🟢 Hijau Lembut", value: "#4ade80", default: cur.subColor === "#4ade80" },
            { html: "🌸 Sakura Pink", value: "#f472b6", default: cur.subColor === "#f472b6" }
          ],
          onSelect: function(item){
            setSubColor(item.value);
            return item.html;
          }
        },
        {
          name: "subtitle-bg",
          width: 260,
          html: "Background Kotak Subtitle",
          tooltip: getSubBgName(cur.subBg || "medium"),
          selector: [
            { html: "Transparan Sedang (55% Box)", value: "medium", default: !cur.subBg || cur.subBg === "medium" },
            { html: "Gelap Pekat (85% Box)", value: "dark", default: cur.subBg === "dark" },
            { html: "Tipis Halus (22% Box)", value: "light", default: cur.subBg === "light" },
            { html: "Frosted Glass Blur", value: "frosted", default: cur.subBg === "frosted" },
            { html: "Tanpa Kotak (Shadow Murni)", value: "none", default: cur.subBg === "none" }
          ],
          onSelect: function(item){
            setSubBg(item.value);
            return item.html;
          }
        },
        {
          name: "subtitle-pos",
          width: 250,
          html: "Posisi Vertikal Subtitle",
          tooltip: getSubPosName(cur.subPos || "normal"),
          selector: [
            { html: "Bawah Normal (Default 28px)", value: "normal", default: !cur.subPos || cur.subPos === "normal" },
            { html: "Sangat Bawah (Ergonomis 10px)", value: "low", default: cur.subPos === "low" },
            { html: "Sedang (48px)", value: "medium", default: cur.subPos === "medium" },
            { html: "Tinggi (72px)", value: "high", default: cur.subPos === "high" }
          ],
          onSelect: function(item){
            setSubPos(item.value);
            return item.html;
          }
        },
        {
          name: "subtitle-delay",
          width: 240,
          html: "Sinkronisasi Delay",
          tooltip: (cur.subDelay || 0).toFixed(2) + "s",
          selector: [
            { html: "-0.50 detik", value: -0.5 },
            { html: "-0.25 detik (Pintasan: ,)", value: -0.25 },
            { html: "0.0s (Reset Sinkron)", value: 0, default: true },
            { html: "+0.25 detik (Pintasan: .)", value: 0.25 },
            { html: "+0.50 detik", value: 0.5 }
          ],
          onSelect: function(item){
            if(item.value === 0) setSubDelay(0.0, true);
            else adjustSubDelay(item.value);
            return (cur.subDelay > 0 ? "+" : "") + (cur.subDelay || 0).toFixed(2) + "s";
          }
        },
        {
          name: "subtitle-translate",
          width: 240,
          html: "Terjemahan ID",
          tooltip: cur.translate ? "Aktif" : "Nonaktif",
          switch: !!cur.translate,
          onSwitch: function(state){
            setTranslate(state);
            return state;
          }
        },
        {
          name: "aniskip-auto",
          width: 250,
          html: "Lewati OP/ED Otomatis",
          tooltip: cur.autoSkip ? "Aktif" : "Nonaktif",
          switch: !!cur.autoSkip,
          onSwitch: function(state){
            cur.autoSkip = state;
            window.settings = window.settings || {};
            window.settings.autoSkip = state;
            if(window.Tatap && window.Tatap.saveSettings){
              window.Tatap.saveSettings({ auto_skip: state });
            }
            if(window.art && window.art.notice){
              window.art.notice.show = "Auto Skip OP/ED: " + (state ? "Aktif" : "Nonaktif");
            }
            return state;
          }
        },
        {
          name: "custom-sub-file",
          width: 260,
          html: "📁 Muat Subtitle Lokal (.srt/.vtt)",
          onClick: function(){
            if(window.art && window.art.setting) window.art.setting.show = false;
            var fi = $("pm-custom-sub-file");
            if(fi) fi.click();
            return "";
          },
          mounted: function($item){
            if($item){
              $item.addEventListener("click", function(e){
                e.stopPropagation();
                if(window.art && window.art.setting) window.art.setting.show = false;
                var fi = $("pm-custom-sub-file");
                if(fi) fi.click();
              });
            }
          }
        },
        {
          name: "ai-settings-modal",
          width: 260,
          html: "🤖 Pengaturan AI Fansub (:ai)",
          onClick: function(){
            if(window.art && window.art.setting) window.art.setting.show = false;
            openAiSettingsModal();
            return "";
          },
          mounted: function($item){
            if($item){
              $item.addEventListener("click", function(e){
                e.stopPropagation();
                if(window.art && window.art.setting) window.art.setting.show = false;
                openAiSettingsModal();
              });
            }
          }
        },
        {
          name: "launch-mpv",
          width: 240,
          html: "🚀 Putar di MPV Eksternal",
          onClick: function(){
            if(window.art && window.art.setting) window.art.setting.show = false;
            playMPV();
            return "";
          },
          mounted: function($item){
            if($item){
              $item.addEventListener("click", function(e){
                e.stopPropagation();
                if(window.art && window.art.setting) window.art.setting.show = false;
                playMPV();
              });
            }
          }
        }
      ],
      controls: [
        {
          name: "prev-btn",
          position: "left",
          index: 8,
          html: '<span class="art-ctrl-btn art-ctrl-ep-btn" id="art-ctrl-prev" title="Episode Sebelumnya (p)"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="19 20 9 12 19 4 19 20"></polygon><line x1="5" y1="19" x2="5" y2="5"></line></svg><span>PREV</span></span>',
          tooltip: "Episode Sebelumnya (p)",
          click: function(){ stepEp(-1); }
        },
        {
          name: "next-btn",
          position: "left",
          index: 12,
          html: '<span class="art-ctrl-btn art-ctrl-ep-btn" id="art-ctrl-next" title="Episode Berikutnya (n)"><span>NEXT</span><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 4 15 12 5 20 5 4"></polygon><line x1="19" y1="5" x2="19" y2="19"></line></svg></span>',
          tooltip: "Episode Berikutnya (n)",
          click: function(){ stepEp(1); }
        },
        initialQualityCtrl,
        initialSubCtrl,
        {
          name: "tr-btn",
          position: "right",
          index: 14,
          style: { marginRight: "4px" },
          html: '<span class="art-ctrl-btn art-ctrl-tr-btn' + (cur.translate ? ' active' : '') + '" title="Terjemahan Bahasa Indonesia (ID)"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg><span>TR-ID</span></span>',
          tooltip: cur.translate ? "Terjemahan Indonesia: Aktif" : "Terjemahan Indonesia: Nonaktif",
          click: function(){ setTranslate(!cur.translate); }
        },
        {
          name: "sep-1",
          position: "right",
          index: 15,
          html: '<span class="art-ctrl-divider"></span>'
        },
        {
          name: "ai-btn",
          position: "right",
          index: 20,
          html: '<span class="art-ctrl-btn art-ctrl-ai-btn" title="Pengaturan AI Fansub (:ai)"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="14" x2="23" y2="14"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="14" x2="4" y2="14"></line></svg><span>AI</span></span>',
          tooltip: "Pengaturan AI Fansub (:ai)",
          click: function(){ openAiSettingsModal(); },
          mounted: function($control){
            $control.addEventListener("click", function(e){
              e.stopPropagation();
              openAiSettingsModal();
            });
          }
        },
        {
          name: "mpv-btn",
          position: "right",
          index: 22,
          html: '<span class="art-ctrl-btn art-ctrl-mpv-btn" title="Putar di MPV Eksternal"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg><span>MPV</span></span>',
          tooltip: "Putar di MPV Eksternal",
          click: function(){ playMPV(); },
          mounted: function($control){
            $control.addEventListener("click", function(e){
              e.stopPropagation();
              playMPV();
            });
          }
        },
        {
          name: "sep-2",
          position: "right",
          index: 25,
          html: '<span class="art-ctrl-divider"></span>'
        },
        {
          name: "close-btn",
          position: "right",
          index: 95,
          html: '<span class="art-ctrl-btn art-ctrl-close-btn" title="Tutup Pemutar (Esc)"><svg class="art-ctrl-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></span>',
          tooltip: "Tutup Pemutar (Esc)",
          click: function(){ closePlayer(); },
          mounted: function($control){
            $control.addEventListener("click", function(e){
              e.stopPropagation();
              closePlayer();
            });
          }
        }
      ],
      layers: [
        {
          name: "header-layer",
          html: '<div class="art-header-layer" id="art-header-layer">' +
                  '<div class="art-header-title" id="art-header-title">' + esc(epTitle) + '</div>' +
                  '<button type="button" class="art-header-close" id="art-header-close" title="Tutup Pemutar Video (Esc)">✕</button>' +
                '</div>',
          style: {
            position: "absolute",
            top: "0",
            left: "0",
            right: "0",
            zIndex: 25,
            pointerEvents: "none"
          },
          mounted: function($layer){
            var btn = $layer.querySelector("#art-header-close");
            if(btn){
              btn.addEventListener("click", function(e){
                e.stopPropagation();
                closePlayer();
              });
            }
          },
          click: function(e){
            if(e.target && (e.target.id === "art-header-close" || e.target.closest("#art-header-close"))){
              closePlayer();
            }
          }
        },
        {
          name: "aniskip-layer",
          html: '<button id="art-aniskip-btn" class="art-aniskip-btn hidden" title="Lewati Opening/Ending (Tekan S)">' +
                '<svg style="width:14px;height:14px;vertical-align:middle;margin-right:6px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 4 15 12 5 20 5 4"></polygon><line x1="19" y1="5" x2="19" y2="19"></line></svg>' +
                '<span id="art-aniskip-text">Lewati Opening (S)</span>' +
                '</button>',
          style: {
            position: "absolute",
            bottom: "76px",
            right: "24px",
            zIndex: 25,
            pointerEvents: "auto"
          },
          click: function(){
            var artBtn = $("art-aniskip-btn");
            if(artBtn && !artBtn.classList.contains("hidden")){
              doSkip();
            }
          }
        }
      ],
      customType: {
        m3u8: function(video, playUrl, artInstance){
          if(window.Hls && window.Hls.isSupported()){
            if(window._hls){ try{ window._hls.destroy(); }catch(e){} }
            var h = new Hls({
              maxBufferLength: 60,
              maxMaxBufferLength: 120,
              maxBufferSize: 60 * 1000 * 1000,
              startLevel: -1,
              capLevelToPlayerSize: true,
              fragLoadingMaxRetry: 6,
              manifestLoadingMaxRetry: 4,
              levelLoadingMaxRetry: 4,
              fragLoadingRetryDelay: 800,
              fragLoadingMaxRetryTimeout: 16000,
              backBufferLength: 30,
              liveSyncDurationCount: 2,
              maxFragLookUpTolerance: 0.5,
              nudgeOffset: 0.1,
              nudgeMaxRetry: 5,
              maxStarvationDelay: 4,
              highBufferWatchdogPeriod: 2,
              testBandwidth: false,
              progressive: true,
              abrEwmaDefaultEstimate: 3 * 1000 * 1000,
              startBufferDuration: 2,
              startFragPrefetch: true,
              lowLatencyMode: false,
              defaultAudioCodec: "mp4a.40.2",
              enableWorker: true
            });
            window._hls = h;
            artInstance.hls = h;
            h._networkRetryCount = 0;
            h._mediaRetryCount = 0;
            h.on(Hls.Events.FRAG_LOADED, function(){
              h._networkRetryCount = 0;
              h._mediaRetryCount = 0;
            });
            h.on(Hls.Events.AUDIO_TRACKS_UPDATED, function(ev, data){
              if(data && data.audioTracks && data.audioTracks.length){
                var isDub = (cur.mode === "dub");
                var selectedIdx = -1;
                if(isDub){
                  for(var ai=0; ai<data.audioTracks.length; ai++){
                    var t = data.audioTracks[ai];
                    var lang = (t.lang || "").toLowerCase();
                    var name = (t.name || "").toLowerCase();
                    if(lang === "en" || name.indexOf("english") >= 0 || name.indexOf("dub") >= 0){
                      selectedIdx = ai; break;
                    }
                  }
                } else {
                  for(var ai=0; ai<data.audioTracks.length; ai++){
                    var t = data.audioTracks[ai];
                    var lang = (t.lang || "").toLowerCase();
                    var name = (t.name || "").toLowerCase();
                    if(lang === "ja" || lang === "jpn" || name.indexOf("japan") >= 0 || t.default){
                      selectedIdx = ai; break;
                    }
                  }
                }
                if(selectedIdx !== -1) h.audioTrack = selectedIdx;
                else if(h.audioTrack === -1 || h.audioTrack === undefined) h.audioTrack = 0;

                if(data.audioTracks.length > 1 && artInstance && artInstance.setting){
                  var aList = data.audioTracks.map(function(trk, ti){
                    return {
                      html: trk.name || trk.lang || ("Audio " + (ti+1)),
                      trackIdx: ti,
                      default: ti === (selectedIdx !== -1 ? selectedIdx : 0)
                    };
                  });
                  var activeAudioName = (data.audioTracks[h.audioTrack] && (data.audioTracks[h.audioTrack].name || data.audioTracks[h.audioTrack].lang)) || "Audio";
                  try{
                    var audioSettingItem = {
                      name: "audio-track",
                      width: 220,
                      html: "Trek Audio (Sulih Suara)",
                      tooltip: activeAudioName,
                      selector: aList,
                      onSelect: function(item){
                        h.audioTrack = item.trackIdx;
                        toast("Trek Audio: " + item.html);
                        return item.html;
                      }
                    };
                    if(artInstance.setting.cache && artInstance.setting.cache.has("audio-track")){
                      artInstance.setting.update(audioSettingItem);
                    } else {
                      artInstance.setting.add(audioSettingItem);
                    }
                  }catch(_){}
                }
              }
            });
            h.on(Hls.Events.MANIFEST_PARSED, function(ev, data){
              if(data && data.levels && data.levels.length > 1){
                var hlsVars = [];
                for(var li=0; li<data.levels.length; li++){
                  var lvl = data.levels[li];
                  var lHeight = lvl.height || 0;
                  var lLabel = lHeight ? (lHeight + "p") : ("Level " + (li+1));
                  hlsVars.push({ q: lLabel, levelIdx: li, height: lHeight, url: lvl.url || (lvl.details && lvl.details.url) || "" });
                }
                hlsVars.sort(function(a,b){ return b.height - a.height; });
                hlsVars.unshift({ q: "Auto", levelIdx: -1, height: 99999, url: "" });
                cur.res = cur.res || {};
                cur.res.hlsLevels = hlsVars;
                renderVariants();
                syncArtplayerQuality(hlsVars);
                if(cur.quality && cur.quality.toLowerCase() !== "auto" && cur.quality.toLowerCase() !== "best"){
                  var targetQ = cur.quality.toLowerCase();
                  for(var qk=0; qk<hlsVars.length; qk++){
                    if(hlsVars[qk].q.toLowerCase().indexOf(targetQ) >= 0 || targetQ.indexOf(hlsVars[qk].q.toLowerCase()) >= 0){
                      if(hlsVars[qk].levelIdx !== -1){
                        h.currentLevel = hlsVars[qk].levelIdx;
                        break;
                      }
                    }
                  }
                }
              }
            });
            h.on(Hls.Events.LEVEL_SWITCHED, function(ev, data){
              if(cur.res && cur.res.hlsLevels){
                var curIdx = h.currentLevel;
                var autoMode = (h.autoLevelEnabled || curIdx === -1);
                var activeLabel = "AUTO";
                if(!autoMode){
                  for(var hi=0; hi<cur.res.hlsLevels.length; hi++){
                    if(cur.res.hlsLevels[hi].levelIdx === curIdx){
                      activeLabel = cur.res.hlsLevels[hi].q.toUpperCase();
                      break;
                    }
                  }
                }
                var sel = $("pm-quality-select");
                if(sel && !sel.classList.contains("user-interacting")){
                  sel.value = autoMode ? "Auto" : activeLabel.toLowerCase();
                }
                syncArtplayerQuality();
              }
            });
            h.loadSource(playUrl);
            h.attachMedia(video);
            h.on(Hls.Events.ERROR, function(ev, d){
              if(!d) return;
              if(d.details === Hls.ErrorDetails.BUFFER_STALLED_ERROR || d.details === "bufferStalledError"){
                try{
                  if(video && video.buffered && video.buffered.length > 0 && !video.paused){
                    var ct = video.currentTime;
                    for(var bi = 0; bi < video.buffered.length; bi++){
                      var bStart = video.buffered.start(bi);
                      if(bStart > ct && (bStart - ct) <= 0.35){
                        video.currentTime = bStart + 0.05;
                        video.play().catch(function(){});
                        return;
                      }
                    }
                  }
                  h.startLoad();
                }catch(_){}
                return;
              }
              if(d.fatal){
                if(d.type === Hls.ErrorTypes.NETWORK_ERROR){
                  h._networkRetryCount = (h._networkRetryCount || 0) + 1;
                  if(h._networkRetryCount <= 4){
                    $("pm-status").textContent = "mencoba memulihkan koneksi stream (" + h._networkRetryCount + "/4)...";
                    setTimeout(function(){ try{ h.startLoad(); }catch(_){} }, 600);
                    return;
                  }
                } else if(d.type === Hls.ErrorTypes.MEDIA_ERROR){
                  h._mediaRetryCount = (h._mediaRetryCount || 0) + 1;
                  if(h._mediaRetryCount <= 3){
                    $("pm-status").textContent = "mencoba memulihkan codec media (" + h._mediaRetryCount + "/3)...";
                    setTimeout(function(){ try{ h.recoverMediaError(); }catch(_){} }, 500);
                    return;
                  }
                }
                $("pm-status").textContent = "player error: " + (d.type || "fatal") + " — " + (d.details || "");
                try{ h.destroy(); }catch(_){}
                return;
              }
              if(d.details === "fragLoadError" || d.details === "manifestLoadError" || d.details === "networkError"){
                $("pm-status").textContent = "gagal load: " + (d.details || "network");
              }
            });
          } else if(video.canPlayType("application/vnd.apple.mpegurl")){
            video.src = playUrl;
          }
        }
      }
    });

    window.art = art;

    // Hook notice.show agar setiap notifikasi Artplayer menggunakan format HTML vektor icon terpadu tanpa emoji kasar
    try{
      var _origNotice = art.notice;
      Object.defineProperty(_origNotice, "show", {
        set: function(val){
          if(!val){
            if(art.template && art.template.$player) art.template.$player.classList.remove("art-notice-show");
            return;
          }
          toast(val);
        },
        get: function(){
          return !!(art.template && art.template.$player && art.template.$player.classList.contains("art-notice-show"));
        },
        configurable: true
      });
    }catch(_){}

    // Pindahkan seekbar (.art-progress) ke dalam wadah dock tengah bilah kendali (.art-controls-center) secara presisi & idempoten
    function ensureDockSeekbar(instance){
      try{
        if(instance && instance.template && instance.template.$controlsCenter && instance.template.$progress){
          if(instance.template.$progress.parentNode !== instance.template.$controlsCenter){
            instance.template.$controlsCenter.appendChild(instance.template.$progress);
          }
        }
      }catch(_){}
    }
    ensureDockSeekbar(art);
    art.on("ready", function(){ ensureDockSeekbar(art); });
    art.on("video:loadedmetadata", function(){ ensureDockSeekbar(art); });
    art.on("resize", function(){ ensureDockSeekbar(art); });
    art.on("fullscreen", function(){ ensureDockSeekbar(art); });
    art.on("fullscreenWeb", function(){ ensureDockSeekbar(art); });
    art.on("control", function(){ ensureDockSeekbar(art); });

    if(art.template && art.template.$video){
      var oldV = $("vid");
      if(oldV && oldV !== art.template.$video && oldV.parentNode){
        try{ oldV.parentNode.removeChild(oldV); }catch(_){}
      }
      art.template.$video.id = "vid";
      art.template.$video.removeAttribute("controls");
      art.template.$video.setAttribute("controlsList", "nodownload nofullscreen noremoteplayback");
      art.template.$video.removeAttribute("disablePictureInPicture");
      art.template.$video.disablePictureInPicture = false;
      v = art.template.$video;
    }

    art.on("control", function(show){
      var hdr = $("art-header-layer");
      if(hdr){
        hdr.style.opacity = show ? "1" : "0";
      }
    });

    // Monitor Fullscreen Handler terintegrasi dengan launcher Windows Portable (1 Monitor)
    art.on("fullscreen", function(state){
      window._isTatapDesktopFs = !!state;
      if(typeof window.tatap_set_fullscreen === "function"){
        try{ window.tatap_set_fullscreen(state); }catch(_){}
      }
      var pm = $("player-modal");
      if(pm){
        if(state) pm.classList.add("is-fullscreen");
        else pm.classList.remove("is-fullscreen");
      }
      var stageEl = document.querySelector(".ambient-stage");
      if(stageEl){
        if(state) stageEl.classList.add("is-fullscreen");
        else stageEl.classList.remove("is-fullscreen");
      }
      syncFullscreenSubtitles();
    });

    art.on("fullscreenWeb", function(state){
      var pm = $("player-modal");
      if(pm){
        if(state) pm.classList.add("is-fullscreen-web");
        else pm.classList.remove("is-fullscreen-web");
      }
      var stageEl = document.querySelector(".ambient-stage");
      if(stageEl){
        if(state) stageEl.classList.add("is-fullscreen-web");
        else stageEl.classList.remove("is-fullscreen-web");
      }
      document.body.classList.toggle("is-webfs-locked", !!state);
      syncFullscreenSubtitles();
    });

    art.on("pip", function(state){
      if(state && typeof syncNativeTextTrack === "function"){
        syncNativeTextTrack(cur._rawVtt, cur.cues, cur.subLang, true);
      }
      syncPipSubtitles(state);
      toast(state ? "Masuk ke mode Picture-in-Picture (PiP)" : "Keluar dari mode Picture-in-Picture", 1500);
    });

    if(art.video){
      art.video.addEventListener("enterpictureinpicture", function(){
        if(typeof syncNativeTextTrack === "function"){
          syncNativeTextTrack(cur._rawVtt, cur.cues, cur.subLang, true);
        }
        syncPipSubtitles(true);
      });
      art.video.addEventListener("leavepictureinpicture", function(){ syncPipSubtitles(false); });
    }

    // Intercept tombol PiP Artplayer agar selalu mengeksekusi toggleSmartPip teroptimasi
    var interceptPipBtn = function(){
      var pipEl = artContainer.querySelector(".art-control-pip") || (art.template && art.template.$pip);
      if(pipEl && !pipEl._tatapSmartPip){
        pipEl._tatapSmartPip = true;
        pipEl.addEventListener("click", function(e){
          e.preventDefault();
          e.stopPropagation();
          e.stopImmediatePropagation();
          toggleSmartPip();
        }, true);
      }
    };
    interceptPipBtn();
    setTimeout(interceptPipBtn, 300);

    art.on("video:ratechange", function(){
      var sel = $("pm-speed-select");
      if(sel && art.playbackRate){
        sel.value = art.playbackRate.toString();
      }
    });

    syncSubStyle();
    updatePrevNext();
    syncArtplayerSubtitles((cur.res && cur.res.subtitles) || [], cur.activeSub);
    syncArtplayerQuality();
    syncTranslateBtn();
    if(cur._rawVtt || (cur.cues && cur.cues.length)){
      syncNativeTextTrack(cur._rawVtt, cur.cues, cur.subLang);
    }

    var showBufferSpinner = function(msg){
      var sp = $("pm-spinner");
      var st = $("pm-status");
      if(st && msg) st.textContent = msg;
      if(sp) sp.classList.remove("hidden");
    };
    var hideSpinner = function(){
      var sp = $("pm-spinner");
      if(sp) sp.classList.add("hidden");
    };

    // Tampilkan animasi pemuatan & buffering saat Artplayer inisiasi sampai video buffer siap berputar
    showBufferSpinner("memuat video & buffer...");

    art.on("video:waiting", function(){
      showBufferSpinner("buffering video...");
    });
    art.on("video:playing", hideSpinner);
    art.on("video:canplaythrough", hideSpinner);
    art.once("video:canplay", function(){
      hideSpinner();
      if(resumeTime && resumeTime > 0){
        try{ art.currentTime = resumeTime; }catch(e){}
        resumeTime = 0;
      }
    });

    art.once("video:loadedmetadata", function(){
      // Catatan: Jangan panggil hideSpinner di sini agar animasi loading tetap aktif
      // sampai frame video dan buffer pertama benar-benar siap diputar (canplay/playing).
      if((!cur.intro || !cur.outro) && window.Tatap && window.Tatap.skipTimes && art.duration > 0){
        var dur = Math.round(art.duration);
        var skipMal = (cur.res && cur.res.mal_id) || cur.mal_id || "";
        window.Tatap.skipTimes(cur.slug, cur.ep, cur.title, skipMal, dur).then(function(skRes){
          if(cur.playToken !== token) return;
          if(skRes && skRes.success && skRes.data){
            var hasNew = false;
            if(!cur.intro && typeof isValidSkipInterval === "function" && isValidSkipInterval(skRes.data.intro)){
              cur.intro = skRes.data.intro;
              hasNew = true;
            }
            if(!cur.outro && typeof isValidSkipInterval === "function" && isValidSkipInterval(skRes.data.outro)){
              cur.outro = skRes.data.outro;
              hasNew = true;
            }
            if(hasNew) checkSkipTimes();
          }
        }).catch(function(){});
      }
    });

    art.on("video:timeupdate", function(){
      paintCue();
      recordWatchProgress();
    });

    art.on("video:seeked", function(){
      paintCue();
    });

    art.on("video:ended", function(){
      var endedSlug = cur.slug;
      var endedEp = cur.ep;
      if(endedSlug && endedEp){
        var dur = Math.floor((window.art && window.art.duration) || 0);
        window.Tatap.saveProgress(endedSlug, endedEp, dur, dur).catch(function(){});
        recordEpisodeWatched(endedSlug, endedEp);
      }
      var idx = -1;
      for(var i=0; i<cur.eps.length; i++) if(cur.eps[i].ep === cur.ep) idx = i;
      if(idx >= 0 && idx < cur.eps.length - 1){
        toast("Episode " + cur.ep + " selesai. Memutar episode berikutnya...", 1500);
        stepEp(1);
      } else {
        closePlayer();
        toast("Episode " + cur.ep + " selesai diputar (episode terakhir)");
      }
    });

    art.on("video:play", function(){
      if(window.TvNavigationManager){
        window.TvNavigationManager.setPlayerState(window.TvNavigationManager.PLAYER_IDLE);
      }
    });

    art.on("video:pause", function(){
      recordWatchProgress(true);
    });
  } else {
    if(window.Hls&&window.Hls.isSupported()&&isHls){
      if(window._hls){try{window._hls.destroy();}catch(e){}}
      var h=new Hls({
        maxBufferLength:60,
        maxMaxBufferLength:120,
        maxBufferSize:60*1000*1000,
        startLevel:-1,
        capLevelToPlayerSize:true,
        fragLoadingMaxRetry:6,
        manifestLoadingMaxRetry:4,
        levelLoadingMaxRetry:4,
        fragLoadingRetryDelay:800,
        fragLoadingMaxRetryTimeout:16000,
        backBufferLength:30,
        liveSyncDurationCount:2,
        maxFragLookUpTolerance:0.5,
        nudgeOffset:0.1,
        nudgeMaxRetry:5,
        maxStarvationDelay:4,
        highBufferWatchdogPeriod:2,
        testBandwidth:false,
        progressive:true,
        abrEwmaDefaultEstimate:3*1000*1000,
        startBufferDuration:2,
        startFragPrefetch:true,
        lowLatencyMode:false,
        defaultAudioCodec:"mp4a.40.2",
        enableWorker:true
      });
      window._hls=h;
      h._networkRetryCount = 0;
      h._mediaRetryCount = 0;
      h.on(Hls.Events.FRAG_LOADED, function(){
        h._networkRetryCount = 0;
        h._mediaRetryCount = 0;
      });
      h.on(Hls.Events.AUDIO_TRACKS_UPDATED,function(ev,data){
        if(data&&data.audioTracks&&data.audioTracks.length){
          var isDub = (cur.mode === "dub");
          var selectedIdx = -1;
          if(isDub){
            for(var ai=0;ai<data.audioTracks.length;ai++){
              var t = data.audioTracks[ai];
              var lang = (t.lang || "").toLowerCase();
              var name = (t.name || "").toLowerCase();
              if(lang === "en" || name.indexOf("english") >= 0 || name.indexOf("dub") >= 0){
                selectedIdx = ai;
                break;
              }
            }
          } else {
            for(var ai=0;ai<data.audioTracks.length;ai++){
              var t = data.audioTracks[ai];
              var lang = (t.lang || "").toLowerCase();
              var name = (t.name || "").toLowerCase();
              if(lang === "ja" || lang === "jpn" || name.indexOf("japan") >= 0 || t.default){
                selectedIdx = ai;
                break;
              }
            }
          }
          if(selectedIdx !== -1){
            h.audioTrack = selectedIdx;
          } else if(h.audioTrack === -1 || h.audioTrack === undefined){
            h.audioTrack = 0;
          }
        }
      });
      h.on(Hls.Events.MANIFEST_PARSED,function(ev,data){
        if(data&&data.levels&&data.levels.length>1){
          var hlsVars=[];
          for(var li=0;li<data.levels.length;li++){
            var lvl=data.levels[li];
            var lHeight = lvl.height || 0;
            var lLabel = lHeight ? (lHeight + "p") : ("Level " + (li+1));
            hlsVars.push({q: lLabel, levelIdx: li, height: lHeight, url: lvl.url || (lvl.details && lvl.details.url) || ""});
          }
          // Urutkan dari tertinggi ke terendah
          hlsVars.sort(function(a,b){return b.height - a.height;});
          // Tambahkan opsi Auto di awal
          hlsVars.unshift({q: "Auto", levelIdx: -1, height: 99999, url: ""});
          cur.res = cur.res || {};
          cur.res.hlsLevels = hlsVars;
          renderVariants();
          // Terapkan kualitas yang cocok jika user memilih kualitas tertentu
          if(cur.quality && cur.quality.toLowerCase() !== "auto" && cur.quality.toLowerCase() !== "best"){
            var targetQ = cur.quality.toLowerCase();
            for(var qk=0; qk<hlsVars.length; qk++){
              if(hlsVars[qk].q.toLowerCase().indexOf(targetQ) >= 0 || targetQ.indexOf(hlsVars[qk].q.toLowerCase()) >= 0){
                if(hlsVars[qk].levelIdx !== -1){
                  h.currentLevel = hlsVars[qk].levelIdx;
                  break;
                }
              }
            }
          }
        }
      });
      h.on(Hls.Events.LEVEL_SWITCHED,function(ev,data){
        if(cur.res && cur.res.hlsLevels){
          var curIdx = h.currentLevel;
          var autoMode = (h.autoLevelEnabled || curIdx === -1);
          var activeLabel = "AUTO";
          if(!autoMode){
            for(var hi=0;hi<cur.res.hlsLevels.length;hi++){
              if(cur.res.hlsLevels[hi].levelIdx === curIdx){
                activeLabel = cur.res.hlsLevels[hi].q.toUpperCase();
                break;
              }
            }
          }
          var sel=$("pm-quality-select");
          if(sel && !sel.classList.contains("user-interacting")){
            sel.value = autoMode ? "Auto" : activeLabel.toLowerCase();
          }
        }
      });
      h.loadSource(prox);
      h.attachMedia(v);
      h.on(Hls.Events.ERROR,function(ev,d){
        if(!d)return;
        if(d.details === Hls.ErrorDetails.BUFFER_STALLED_ERROR || d.details === "bufferStalledError"){
          // Recovery stall cerdas: periksa apakah player terjebak pada micro-gap buffer
          try{
            if(v && v.buffered && v.buffered.length > 0 && !v.paused){
              var ct = v.currentTime;
              for(var bi = 0; bi < v.buffered.length; bi++){
                var bStart = v.buffered.start(bi);
                if(bStart > ct && (bStart - ct) <= 0.35){
                  v.currentTime = bStart + 0.05;
                  v.play().catch(function(){});
                  return;
                }
              }
            }
            h.startLoad();
          }catch(_){}
          return;
        }
        if(d.fatal){
          if(d.type===Hls.ErrorTypes.NETWORK_ERROR){
            h._networkRetryCount = (h._networkRetryCount || 0) + 1;
            if(h._networkRetryCount <= 4){
              $("pm-status").textContent="mencoba memulihkan koneksi stream ("+h._networkRetryCount+"/4)...";
              setTimeout(function(){ try{h.startLoad();}catch(_){} }, 600);
              return;
            }
          }else if(d.type===Hls.ErrorTypes.MEDIA_ERROR){
            h._mediaRetryCount = (h._mediaRetryCount || 0) + 1;
            if(h._mediaRetryCount <= 3){
              $("pm-status").textContent="mencoba memulihkan codec media ("+h._mediaRetryCount+"/3)...";
              setTimeout(function(){ try{h.recoverMediaError();}catch(_){} }, 500);
              return;
            }
          }
          $("pm-status").textContent="player error: "+(d.type||"fatal")+" — "+(d.details||"");
          try{h.destroy();}catch(_){}
          return;
        }
        // Non-fatal: fragLoadError / manifestLoadError / networkError — kalau host
        // mati (dramahot.top RST), proxy return 502; HLS.js fire ini. Beri pesan
        // jelas di spinner & stop setelah beberapa retry agar user tidak hang.
        var n=(h.config&&h.config.fragLoadingMaxRetry)||4;
        if(d.details==="fragLoadError"||d.details==="manifestLoadError"||d.details==="networkError"){
          $("pm-status").textContent="gagal load: "+(d.details||"network");
        }
      });
    }else{
      v.src=isHls?prox:url;
    }
  }
  if(pm.classList.contains("hidden") || (token && cur.playToken !== token)){
    if(window._hls){try{window._hls.destroy();window._hls=null;}catch(e){}}
    if(v){try{v.pause();v.removeAttribute("src");v.load();}catch(e){}}
    return;
  }
  if(v && !window.art){
    v.play().catch(function(err){
      $("pm-spinner").classList.add("hidden");
      if(err && err.name === "NotAllowedError"){
        v.muted = true;
        v.play().catch(function(){});
      }
    });
  }
  armAutohide();
}
function switchQ(q){
  var qLow = String(q||"").toLowerCase();
  // 1. Jika HLS.js aktif dan memiliki live levels, ganti level secara instan tanpa reload!
  if(window._hls && cur.res && cur.res.hlsLevels && cur.res.hlsLevels.length){
    for(var hi=0;hi<cur.res.hlsLevels.length;hi++){
      var hl = cur.res.hlsLevels[hi];
      if(hl.q.toLowerCase() === qLow){
        if(hl.levelIdx === -1){
          window._hls.currentLevel = -1; // Auto adaptive mode
          toast("Resolusi: AUTO (Adaptif)");
        } else {
          window._hls.currentLevel = hl.levelIdx;
          toast("Resolusi: " + hl.q.toUpperCase());
        }
        if(cur.res.picked) cur.res.picked.q = hl.q;
        renderVariants();
        syncArtplayerQuality();
        return;
      }
    }
  }

  // 2. Fallback: reload varian URL jika bukan live multi-level HLS.js
  if(!cur.res||!cur.res.variants)return;
  var curTime = (window.art && !isNaN(window.art.currentTime)) ? window.art.currentTime : (($("vid") && $("vid").currentTime) || 0);
  for(var i=0;i<cur.res.variants.length;i++){
    if(cur.res.variants[i].q.toLowerCase()===qLow){
      cur.res.picked=cur.res.variants[i];
      renderVariants();
      syncArtplayerQuality();
      var validFallbackSub = (cur.res && cur.res.sub && typeof cur.res.sub === "string" && !/^\d+$/.test(cur.res.sub.trim())) ? cur.res.sub : null;
      playUrl(cur.res.variants[i].url,cur.res.referer,cur.activeSub||validFallbackSub,cur.res.referer,curTime);
      toast("Resolusi: "+cur.res.variants[i].q.toUpperCase());
      return;
    }
  }
}

function updatePrevNext(){
  var idx=-1;
  for(var i=0;i<cur.eps.length;i++)if(cur.eps[i].ep===cur.ep)idx=i;
  var hasPrev = idx > 0;
  var hasNext = idx >= 0 && idx < cur.eps.length - 1;
  var btnP = $("pm-prev"); if(btnP) btnP.disabled = !hasPrev;
  var btnN = $("pm-next"); if(btnN) btnN.disabled = !hasNext;
  if(window.art && window.art.controls){
    try{
      var pBtn = window.art.controls["prev-btn"];
      if(pBtn){
        pBtn.style.opacity = hasPrev ? "1" : "0.35";
        pBtn.style.pointerEvents = hasPrev ? "auto" : "none";
        pBtn.classList.toggle("disabled", !hasPrev);
      }
      var nBtn = window.art.controls["next-btn"];
      if(nBtn){
        nBtn.style.opacity = hasNext ? "1" : "0.35";
        nBtn.style.pointerEvents = hasNext ? "auto" : "none";
        nBtn.classList.toggle("disabled", !hasNext);
      }
    }catch(_){}
  }
}
function stepEp(d){
  if($("player-modal").classList.contains("hidden"))return;
  var idx=-1;
  for(var i=0;i<cur.eps.length;i++)if(cur.eps[i].ep===cur.ep)idx=i;
  var nxt=cur.eps[idx+d];
  if(nxt){
    cur.ep=nxt.ep;
    updatePrevNext();
    var epLabel = nxt.ep ? ("Episode " + nxt.ep) : "";
    var dirLabel = d > 0 ? "Memuat episode berikutnya" : "Memuat episode sebelumnya";
    toast("⏳ " + dirLabel + (epLabel ? " (" + epLabel + ")" : "") + "...", 2000);
    openPlayer(nxt.ep);
  }
  else toast(d>0 ? "Sudah berada di episode terakhir" : "Sudah berada di episode pertama", 1500);
}
function closePlayer(){
  if(window.TatapSfx) TatapSfx.play("back");
  // 1. Invalidate all pending async playback tokens immediately
  cur.playToken = ++_playTokenCounter;
  TvNavigationManager.hidePlayerControls();
  TvNavigationManager.setPlayerModalState(false);
  TvNavigationManager.setPlayerState(TvNavigationManager.PLAYER_IDLE);
  closeOpenSubtitlesPicker();

  // Bersihkan Picture-in-Picture jika sedang aktif
  if(window.tatapPipWindow){
    try{ window.tatapPipWindow.close(); }catch(_){}
    window.tatapPipWindow = null;
  }
  if(document.pictureInPictureElement){
    try{ document.exitPictureInPicture(); }catch(_){}
  }
  if(window._tatapPipRaf){
    cancelAnimationFrame(window._tatapPipRaf);
    window._tatapPipRaf = null;
  }
  if(window._tatapPipVideo){
    try{ window._tatapPipVideo.srcObject = null; }catch(_){}
  }
  var pipPlaceholder = document.getElementById("pip-stage-placeholder");
  if(pipPlaceholder && pipPlaceholder.parentNode){
    try{ pipPlaceholder.parentNode.removeChild(pipPlaceholder); }catch(_){}
  }
  syncPipSubtitles(false);

  try{ recordWatchProgress(true); }catch(e){}

  if(window.art){
    try{
      if(window.art.fullscreenWeb) window.art.fullscreenWeb = false;
      if(window.art.fullscreen) window.art.fullscreen = false;
      if(window.art.template && window.art.template.$player && window.art.template.$player.parentNode){
        window.art.template.$player.parentNode.removeChild(window.art.template.$player);
      }
      window.art.destroy(true);
      window.art = null;
    }catch(e){}
  }
  document.querySelectorAll("body > .art-video-player").forEach(function(el){
    try{ el.parentNode.removeChild(el); }catch(_){}
  });
  document.body.classList.remove("art-fullscreen-web");
  var artCont = $("artplayer-container");
  if(artCont) artCont.innerHTML = "";

  // Restore placeholder dummy vid if needed for non-playing state
  var stage = document.querySelector(".ambient-stage");
  if(stage && !$("vid")){
    var placeholderVid = document.createElement("video");
    placeholderVid.id = "vid";
    placeholderVid.removeAttribute("controls");
    placeholderVid.setAttribute("controlsList", "nodownload nofullscreen noremoteplayback");
    placeholderVid.setAttribute("disablePictureInPicture", "");
    placeholderVid.style.cssText = "display:none !important; width:0; height:0;";
    stage.appendChild(placeholderVid);
  }

  // 2. Safely stop and destroy video & HLS stream
  var v=$("vid");
  if(v && v.style.display !== "none"){
    try{v.pause();}catch(e){}
    v.removeAttribute("src");
    try{v.load();}catch(e){}
  }
  if(window._hls){try{window._hls.destroy();window._hls=null;}catch(e){}}
  cur.cues=[];
  clearOverlay();
  syncNativeTextTrack("", [], "");

  // 3. Hide modal & spinner
  detachModalFromActiveLayer($("sub-style-modal"));
  detachModalFromActiveLayer($("ai-settings-modal"));
  var pmModalClose = $("player-modal");
  if(pmModalClose){
    pmModalClose.classList.add("hidden");
    pmModalClose.style.display = "none";
  }
  $("pm-spinner").classList.add("hidden");

  // 4. Exit fullscreen safely if active
  if(window.art){
    try{
      if(window.art.fullscreenWeb) window.art.fullscreenWeb = false;
      if(window.art.fullscreen) window.art.fullscreen = false;
    }catch(_){}
  }
  window._isTatapDesktopFs = false;
  var pm = $("player-modal");
  if(pm){
    pm.classList.remove("is-fullscreen");
    pm.classList.remove("is-fullscreen-web");
  }
  document.body.classList.remove("is-webfs-locked");
  if(document.fullscreenElement || document.webkitFullscreenElement){
    try{
      if(document.exitFullscreen) document.exitFullscreen();
      else if(document.webkitExitFullscreen) document.webkitExitFullscreen();
    }catch(e){}
  }
  var stageEl = document.querySelector(".ambient-stage");
  if(stageEl){
    stageEl.classList.remove("is-fullscreen");
    stageEl.classList.remove("is-fullscreen-web");
  }
  if(typeof window.tatap_set_fullscreen === "function"){
    try{ window.tatap_set_fullscreen(false); }catch(e){}
  }

  // 5. Perilaku post-watch: kembalikan user ke dedicated detail anime page (bukan main page)
  var savedSlug = cur.slug;
  if(savedSlug){
    var dp = $("detail-page");
    var tm = $("title-modal");
    var searchSec = $("search-sec");
    if(searchSec) searchSec.classList.add("hidden");
    var contSec = $("continue-sec");
    if(contSec) contSec.classList.add("hidden");
    var pager = $("pager");
    if(pager) pager.classList.add("hidden");

    if(dp){
      dp.classList.remove("hidden");
      document.body.classList.add("in-detail-view");
    }
    if(tm) tm.classList.remove("hidden");

    if(cur.eps && cur.eps.length > 0){
      var titleEl = $("tm-title");
      if(titleEl && cur.title) titleEl.textContent = cur.title;
      var subEl = $("tm-sub");
      if(subEl && cur.slug) subEl.textContent = cur.slug;
      var countEl = $("tm-count");
      if(countEl && cur.eps) countEl.textContent = cur.eps.length + " episode · " + (cur.mode||"SUB").toUpperCase();
      renderEpRanges();
      renderEpGrid();
      updateQuickPlayBtn();
      TvNavigationManager.restoreFocusState(".ep.last-watch");
    } else {
      openTitle(savedSlug, cur.title, cur.poster, cur.type, cur.eps_counter);
    }
  } else {
    // Jika tidak ada anime aktif terpilih, kembali ke katalog utama
    closeTitle();
  }
}
function playMPV(){
  if(window.art){
    try { window.art.pause(); } catch(_){}
  }
  window.Tatap.playMPV({slug:cur.slug,title:cur.title,ep:cur.ep||1,mode:cur.mode,quality:cur.quality}).then(function(r){
    toast(r.success?("MPV: "+r.data.picked.q):("ERROR: "+r.error));
  });
}
function renderContinue(){
  window.Tatap.history().then(function(r){
    var h=(r.data||[]).slice(0,10);
    var sec=$("continue-sec");
    if(sec){
      // Riwayat tontonan diisolasi eksklusif pada view "riwayat" (#results)
      sec.classList.add("hidden");
      sec.style.display="none";
    }
    if(!h.length) return;
    var box=$("continue-row");if(!box)return;
    box.innerHTML="";
    for(var i=0;i<h.length;i++){
      (function(x){
        var d=document.createElement("div");d.className="hist-card";
        d.tabIndex=0;

        // Container thumbnail 16:9
        var thumbWrap=document.createElement("div");
        thumbWrap.className="hist-thumb-wrap";

        // Fallback placeholder jika poster belum ada atau gagal load
        var ph=document.createElement("div");
        ph.className="hist-thumb-ph";
        ph.innerHTML='<svg class="ui-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg><span>TATAP</span>';

        var cleanPoster = sanitizePosterUrl(x.poster);
        if(cleanPoster){
          var img=document.createElement("img");
          img.className="hist-thumb";
          img.loading="lazy";
          img.decoding="async";
          img.alt=x.title||"";
          img.src=cleanPoster;
          img.onerror=function(){
            this.style.display="none";
            ph.style.display="flex";
          };
          ph.style.display="none";
          thumbWrap.appendChild(img);
          thumbWrap.appendChild(ph);
        } else {
          thumbWrap.appendChild(ph);
        }

        // Floating Episode Badge
        var epBadge=document.createElement("span");
        epBadge.className="hist-ep-badge";
        epBadge.textContent=String(x.episode||"1");
        thumbWrap.appendChild(epBadge);

        // Hover Play Badge
        var playBadge=document.createElement("div");
        playBadge.className="hist-play-badge";
        playBadge.innerHTML='<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 3 20 12 6 21 6 3"></polygon></svg>';
        thumbWrap.appendChild(playBadge);

        // Progress bar di bagian bawah thumbnail
        if(x.progress && x.progress >= 15){
          var progTrack=document.createElement("div");
          progTrack.className="hist-progress-track";
          var progFill=document.createElement("div");
          progFill.className="hist-progress-fill";
          var pct=Math.min(100, Math.max(5, Math.round((x.progress / 1440) * 100)));
          progFill.style.width=pct+"%";
          progTrack.appendChild(progFill);
          thumbWrap.appendChild(progTrack);
        }

        d.appendChild(thumbWrap);

        // Info container (Judul & Progres)
        var info=document.createElement("div");
        info.className="hist-info";
        var b=document.createElement("b");
        b.className="hist-title";
        b.textContent=x.title||"";
        b.title=x.title||"";
        info.appendChild(b);

        var s=document.createElement("span");
        s.className="hist-meta";
        var progStr=(x.progress&&x.progress>=15)?(" · "+formatTimeSec(x.progress)):"";
        var modeStr=x.mode?String(x.mode).toUpperCase():"SUB";
        s.textContent="Ep "+x.episode+progStr+" · "+modeStr+" · Lanjutkan ▶";
        info.appendChild(s);

        d.appendChild(info);

        var playAction=function(){
          cur.slug=x.slug;cur.title=x.title;cur.poster=x.poster||"";cur.type=x.type||"";cur.mode=x.mode||"sub";syncSeg();
          openTitle(x.slug,x.title,x.poster,x.type);
          openPlayer(x.episode,x.progress||0);
        };

        d.addEventListener("click",playAction);
        d.addEventListener("keydown",function(e){
          if(e.key==="Enter"||e.key===" "){
            e.preventDefault();
            playAction();
          }
        });

        box.appendChild(d);
      })(h[i]);
    }
  }).catch(function(){});
}
function setFallback(r,g,b){
  var fb=$("ambient-fallback");
  if(!fb)return;
  fb.style.background="radial-gradient(60% 90% at 50% 50%, rgb("+r+","+g+","+b+"), transparent 70%)";
}
function startAmbient(){
  var cv=$("ambient"),ctx=null;
  try{ctx=cv.getContext("2d",{willReadFrequently:true});}catch(e){ctx=cv.getContext("2d");}
  var tmp=document.createElement("canvas");
  tmp.width=48;tmp.height=27;
  var tctx=null;
  try{tctx=tmp.getContext("2d",{willReadFrequently:true});}catch(e){tctx=tmp.getContext("2d");}
  setInterval(function(){
    if(document.hidden)return;
    if(document.body.classList.contains("no-ambient"))return;
    if($("player-modal").classList.contains("hidden"))return;
    var v=(window.art && window.art.template && window.art.template.$video) || $("vid");
    if(!v)return;
    if(!v.hasAttribute("crossorigin")) v.setAttribute("crossorigin","anonymous");
    if(v.paused||v.ended||v.readyState<2||v.videoWidth===0)return;
    if(isVideoFullscreen())return;
    try{
      tctx.drawImage(v,0,0,48,27);
      var px;
      try{px=tctx.getImageData(0,0,48,27).data;}
      catch(taint){
        var h=0,s=String(cur.slug)+cur.ep;
        for(var k=0;k<s.length;k++)h=(h*31+s.charCodeAt(k))%360;
        setFallback(Math.round(90+80*Math.abs(Math.sin(h))),120,220);
        return;
      }
      var r=0,g=0,b=0,n=0;
      for(var i=0;i<px.length;i+=12){r+=px[i];g+=px[i+1];b+=px[i+2];n++;}
      r=Math.round(r/n);g=Math.round(g/n);b=Math.round(b/n);
      var g2=ctx.createLinearGradient(0,0,96,54);
      g2.addColorStop(0,"rgb("+r+","+g+","+b+")");
      g2.addColorStop(1,"rgb("+Math.round(b*.7)+","+Math.round(r*.6)+","+Math.round(g*.8)+")");
      ctx.fillStyle=g2;
      ctx.fillRect(0,0,96,54);
      setFallback(r,g,b);
    }catch(e){}
  },1200);
}
function getEpGridCols(){
  var box = $("tm-eps");
  if(!box) return 1;
  var btns = box.querySelectorAll(".ep");
  if(btns.length < 2) return 1;
  var firstTop = btns[0].offsetTop;
  for(var c=1; c<btns.length; c++){
    if(btns[c].offsetTop > firstTop + 5){
      return c;
    }
  }
  return btns.length;
}

function handleTitleModalKey(e){
  var isFilter = (e.target && e.target.id === "ep-filter");
  var epBox = $("tm-eps");
  if(!epBox) return;
  var epBtns = Array.prototype.slice.call(epBox.querySelectorAll(".ep"));

  if(isFilter){
    if(e.key === "Escape"){
      e.target.blur();
      return;
    }
    if(e.key === "Enter" || e.key === "ArrowDown"){
      e.preventDefault();
      e.target.blur();
      if(epBtns.length > 0){
        TvNavigationManager.setFocus(epBtns[0], "detail-modal");
      }
      return;
    }
    return;
  }

  if(e.key === "Escape" || e.key === "Backspace"){
    e.preventDefault();
    closeTitle();
    return;
  }

  if(e.key === "/"){
    e.preventDefault();
    var flt = $("ep-filter");
    if(flt){ flt.focus(); flt.select(); }
    return;
  }

  if(e.key === "p" || e.key === "P"){
    var qp = $("btn-quick-play");
    if(qp){ e.preventDefault(); qp.click(); return; }
  }

  if(e.key === "f" || e.key === "F"){
    var bm = $("tm-bookmark-btn");
    if(bm){ e.preventDefault(); bm.click(); return; }
  }

  if(e.key === "s" || e.key === "S"){
    var src = $("tm-source-btn");
    if(src){ e.preventDefault(); src.click(); return; }
  }

  if(e.key === "[" || e.key === "]"){
    var rChips = Array.prototype.slice.call(document.querySelectorAll("#tm-ep-ranges .ep-range-chip"));
    if(rChips.length > 1){
      e.preventDefault();
      var curRIdx = -1;
      for(var ri = 0; ri < rChips.length; ri++){
        if(rChips[ri].classList.contains("active")){ curRIdx = ri; break; }
      }
      var nextRIdx = e.key === "]" ? Math.min(curRIdx + 1, rChips.length - 1) : Math.max(0, curRIdx - 1);
      rChips[nextRIdx].click();
      return;
    }
  }

  if(!epBtns.length) return;

  var activeIdx = epBtns.indexOf(document.activeElement);
  if(activeIdx < 0){
    for(var k = 0; k < epBtns.length; k++){
      if(epBtns[k].classList.contains("tv-focus")){
        activeIdx = k;
        break;
      }
    }
  }
  var cols = getEpGridCols();

  if(e.key === "ArrowRight"){
    e.preventDefault();
    var nextIdx = (activeIdx < 0) ? 0 : Math.min(activeIdx + 1, epBtns.length - 1);
    TvNavigationManager.setFocus(epBtns[nextIdx], "detail-modal");
    return;
  }
  if(e.key === "ArrowLeft"){
    e.preventDefault();
    var prevIdx = (activeIdx <= 0) ? 0 : activeIdx - 1;
    TvNavigationManager.setFocus(epBtns[prevIdx], "detail-modal");
    return;
  }
  if(e.key === "ArrowDown"){
    e.preventDefault();
    if(activeIdx < 0){
      TvNavigationManager.setFocus(epBtns[0], "detail-modal");
    } else {
      var targetDown = TvNavigationManager.getSpatialTarget(epBtns[activeIdx], epBtns, "down");
      if(targetDown){
        TvNavigationManager.setFocus(targetDown, "detail-modal");
      } else {
        var downIdx = Math.min(activeIdx + cols, epBtns.length - 1);
        TvNavigationManager.setFocus(epBtns[downIdx], "detail-modal");
      }
    }
    return;
  }
  if(e.key === "ArrowUp"){
    e.preventDefault();
    if(activeIdx < 0){
      TvNavigationManager.setFocus(epBtns[0], "detail-modal");
    } else {
      var targetUp = TvNavigationManager.getSpatialTarget(epBtns[activeIdx], epBtns, "up");
      if(targetUp){
        TvNavigationManager.setFocus(targetUp, "detail-modal");
      } else if(activeIdx < cols){
        var flt = $("ep-filter");
        if(flt){ flt.focus(); flt.select(); }
        else {
          var bm = $("tm-bookmark-btn");
          if(bm) TvNavigationManager.setFocus(bm, "detail-modal");
        }
      } else {
        var upIdx = Math.max(0, activeIdx - cols);
        TvNavigationManager.setFocus(epBtns[upIdx], "detail-modal");
      }
    }
    return;
  }
  if(e.key === "Enter" || e.key === " "){
    if(activeIdx >= 0){
      e.preventDefault();
      epBtns[activeIdx].click();
    } else if(epBtns.length > 0){
      e.preventDefault();
      var defBtn = epBox.querySelector(".ep.last-watch") || epBtns[0];
      defBtn.click();
    }
    return;
  }
}

function onKeyPlayer(e){
  var spM = $("spotlight-modal");
  if(spM && !spM.classList.contains("hidden")){
    if(e.key === "Escape"){
      if(e) e.preventDefault();
      closeSpotlight();
      return;
    }
  }

  var t=(e.target&&e.target.tagName||"").toUpperCase();
  var isTextEditing=(t==="INPUT" && ["button","checkbox","color","file","hidden","image","radio","range","reset","submit"].indexOf(((e.target&&e.target.type)||"text").toLowerCase())===-1) ||
                    (t==="TEXTAREA") ||
                    (e.target&&e.target.isContentEditable);
  if(isTextEditing){
    if(e.key==="Escape"){e.target.blur();}
    return;
  }

  // 1. Penanganan Escape Terstruktur
  if(e.key==="Escape"){
    var aiM = $("ai-settings-modal");
    if(aiM && !aiM.classList.contains("hidden")){
      closeAiSettingsModal();
      return;
    }
    var ssm = $("sub-style-modal");
    if(ssm && !ssm.classList.contains("hidden")){
      cancelSubStyleModal();
      return;
    }
    var osBox = document.querySelector(".os-picker-box");
    if(osBox){
      closeOpenSubtitlesPicker();
      return;
    }
    var fsEl=document.fullscreenElement||document.webkitFullscreenElement||document.mozFullScreenElement||document.msFullscreenElement;
    if(fsEl){
      // Fullscreen keluar secara native via browser
      return;
    }
    if(window.art && window.art.fullscreenWeb){
      window.art.fullscreenWeb = false;
      return;
    }
    if(window._isTatapDesktopFs){
      toggleFullscreen();
      return;
    }
    if(!$("player-modal").classList.contains("hidden")){
      e.preventDefault();
      closePlayer();
      return;
    }
    var dpEl = $("detail-page");
    if((dpEl && !dpEl.classList.contains("hidden")) || (!$("title-modal").classList.contains("hidden"))){
      e.preventDefault();
      closeTitle();
      return;
    }
    if(TvNavigationManager.handleBack(e)) return;
    return;
  }

  // 2. Jika Player Modal Tertutup, serahkan ke Detail Modal handler
  var isPlayerActive = $("player-modal") && !$("player-modal").classList.contains("hidden");
  if(!isPlayerActive){
    if(!$("title-modal").classList.contains("hidden") || ($("detail-page") && !$("detail-page").classList.contains("hidden"))){
      handleTitleModalKey(e);
    }
    return;
  }

  // 3. Videoplayer Active Key Interactions (Artplayer + TV D-Pad)
  var isSpace = e.key===" " || e.key==="Spacebar" || e.code==="Space" || e.keyCode===32;

  // TV D-Pad Spatial Navigation jika dalam mode TV dan HUD aktif
  if(TvNavigationManager.isTvMode() && TvNavigationManager.playerState() === TvNavigationManager.PLAYER_HUD_ACTIVE){
    TvNavigationManager.resetHudTimer();
    var pm = $("player-modal");
    var hudBtns = Array.prototype.slice.call(pm.querySelectorAll(".player-head-btns button, .player-head-btns select, .player-foot button, .player-foot select, .sub-size button, .sub-translate, .pm-skip-btn:not(.hidden)"));
    var curFoc = document.activeElement;
    if(e.key==="ArrowDown"){
      var nextDown = TvNavigationManager.getSpatialTarget(curFoc, hudBtns, "down");
      if(nextDown){ e.preventDefault(); TvNavigationManager.setFocus(nextDown, "player-hud"); return; }
    } else if(e.key==="ArrowUp"){
      var nextUp = TvNavigationManager.getSpatialTarget(curFoc, hudBtns, "up");
      if(nextUp){ e.preventDefault(); TvNavigationManager.setFocus(nextUp, "player-hud"); return; }
    } else if(e.key==="ArrowRight"){
      var nextRight = TvNavigationManager.getSpatialTarget(curFoc, hudBtns, "right");
      if(nextRight){ e.preventDefault(); TvNavigationManager.setFocus(nextRight, "player-hud"); return; }
    } else if(e.key==="ArrowLeft"){
      var nextLeft = TvNavigationManager.getSpatialTarget(curFoc, hudBtns, "left");
      if(nextLeft){ e.preventDefault(); TvNavigationManager.setFocus(nextLeft, "player-hud"); return; }
    }
  }

  // Play / Pause Toggle
  if(isSpace || (!TvNavigationManager.isTvMode() && e.key==="Enter")){
    e.preventDefault();
    if(document.activeElement && document.activeElement !== document.body){
      try { document.activeElement.blur(); } catch(_){}
    }
    var skipBtn = $("pm-skip-btn");
    var artBtn = $("art-aniskip-btn");
    if(((skipBtn && !skipBtn.classList.contains("hidden")) || (artBtn && !artBtn.classList.contains("hidden"))) && (cur.activeSkipTarget > 0)){
      doSkip();
    } else if(window.art){
      window.art.toggle();
    } else {
      var v = $("vid");
      if(v){ if(v.paused) v.play(); else v.pause(); }
    }
    return;
  }

  // Seek Backward (ArrowLeft: mundur 5 detik)
  if(e.key==="ArrowLeft"){
    e.preventDefault();
    if(window.art){
      var curT = window.art.currentTime || 0;
      window.art.currentTime = Math.max(0, curT - 5);
      toast("-5s (" + formatTimeSec(window.art.currentTime) + ")", 1000, "icon-rewind");
    } else {
      var v = $("vid");
      if(v) {
        v.currentTime = Math.max(0, (v.currentTime || 0) - 5);
        toast("-5s (" + formatTimeSec(v.currentTime) + ")", 1000, "icon-rewind");
      }
    }
    return;
  }

  // Seek Forward (ArrowRight: maju 5 detik)
  if(e.key==="ArrowRight"){
    e.preventDefault();
    if(window.art){
      var curT = window.art.currentTime || 0;
      var durT = window.art.duration || Infinity;
      window.art.currentTime = Math.min(durT, curT + 5);
      toast("+5s (" + formatTimeSec(window.art.currentTime) + ")", 1000, "icon-forward");
    } else {
      var v = $("vid");
      if(v) {
        v.currentTime = Math.min(v.duration || Infinity, (v.currentTime || 0) + 5);
        toast("+5s (" + formatTimeSec(v.currentTime) + ")", 1000, "icon-forward");
      }
    }
    return;
  }

  // Volume Up (ArrowUp: naik 10%)
  else if(e.key==="ArrowUp"){
    e.preventDefault();
    v.volume=Math.min(1, Math.round(((v.volume||1)+0.1)*10)/10);
    if(window.art){
      var curVol = typeof window.art.volume === "number" ? window.art.volume : 1.0;
      var nextVol = Math.min(1, Math.round((curVol + 0.1) * 10) / 10);
      window.art.volume = nextVol;
      toast("Volume: " + Math.round(nextVol * 100) + "%", 1200);
    } else {
      toast("Volume: " + Math.round(v.volume * 100) + "%", 1200);
    }
    return;
  }

  // Volume Down (ArrowDown: turun 10%)
  else if(e.key==="ArrowDown"){
    e.preventDefault();
    v.volume=Math.max(0, Math.round(((v.volume||1)-0.1)*10)/10);
    if(window.art){
      var curVol = typeof window.art.volume === "number" ? window.art.volume : 1.0;
      var nextVol = Math.max(0, Math.round((curVol - 0.1) * 10) / 10);
      window.art.volume = nextVol;
      toast("Volume: " + Math.round(nextVol * 100) + "%", 1200);
    } else {
      toast("Volume: " + Math.round(v.volume * 100) + "%", 1200);
    }
    return;
  }

  // Mute / Unmute (M)
  else if(e.key==="m"||e.key==="M"){
    e.preventDefault();
    if(window.art){
      window.art.muted = !window.art.muted;
      toast(window.art.muted ? "Muted" : "Unmuted (" + Math.round((window.art.volume || 1) * 100) + "%)", 1200);
    } else {
      var vM = $("vid");
      if(vM){
        vM.muted = !vM.muted;
        toast(vM.muted ? "Muted" : "Unmuted (" + Math.round((vM.volume || 1) * 100) + "%)", 1200);
      }
    }
    return;
  }

  // Monitor Fullscreen (F)
  else if(e.key==="f"||e.key==="F"){
    e.preventDefault();
    toggleFullscreen();
    return;
  }

  // Web Fullscreen (W)
  else if(e.key==="w"||e.key==="W"){
    e.preventDefault();
    if(window.art){
      window.art.fullscreenWeb = !window.art.fullscreenWeb;
    }
    return;
  }

  // Picture-in-Picture (I)
  else if(e.key==="i"||e.key==="I"){
    e.preventDefault();
    toggleSmartPip();
    return;
  }

  // Next Episode (N)
  else if(e.key==="n"||e.key==="N"){
    e.preventDefault();
    stepEp(1);
    return;
  }

  // Prev Episode (P)
  else if(e.key==="p"||e.key==="P"){
    e.preventDefault();
    stepEp(-1);
    return;
  }

  // Subtitle Delay Offset (, / .)
  else if(e.key===","||e.key==="<"){
    e.preventDefault();
    adjustSubDelay(-0.25);
    return;
  }
  else if(e.key==="."||e.key===">"){
    e.preventDefault();
    adjustSubDelay(0.25);
    return;
  }

  // Playback Speed ([ / ])
  else if(e.key==="["||e.key==="{"){
    e.preventDefault();
    adjustPlaySpeed(-1);
    return;
  }
  else if(e.key==="]"||e.key==="}"){
    e.preventDefault();
    adjustPlaySpeed(1);
    return;
  }

  // Skip AniSkip / Switch Source (S)
  else if(e.key==="s"||e.key==="S"){
    e.preventDefault();
    var skipBtn = $("pm-skip-btn");
    var artBtn = $("art-aniskip-btn");
    var isSkipActive = ((skipBtn && !skipBtn.classList.contains("hidden")) || (artBtn && !artBtn.classList.contains("hidden"))) && cur.activeSkipTarget > 0;
    if(isSkipActive){
      doSkip();
      return;
    }
    switchSource();
    return;
  }
}

function loadSubStylePrefs(){
  try {
    var sz = localStorage.getItem("tatap_subsize");
    if(sz === "s" || sz === "m" || sz === "l" || sz === "xl") cur.subSize = sz;
    var f = localStorage.getItem("tatap_sub_font");
    if(f && FONT_MAP[f]) cur.subFont = f;
    var c = localStorage.getItem("tatap_sub_color");
    if(c) cur.subColor = c;
    var b = localStorage.getItem("tatap_sub_bg");
    if(b) cur.subBg = b;
    var p = localStorage.getItem("tatap_sub_pos");
    if(p) cur.subPos = p;
  } catch(e){}
}

function syncSubStyle(){
  var sz = cur.subSize || "m";
  var fontKey = cur.subFont || "sans";
  var fontVal = FONT_MAP[fontKey] || FONT_MAP["sans"];
  var color = cur.subColor || "#ffffff";
  var bgKey = cur.subBg || "medium";
  var posKey = cur.subPos || "normal";

  var bgMap = {
    "medium": "rgba(0, 0, 0, 0.55)",
    "dark": "rgba(0, 0, 0, 0.85)",
    "light": "rgba(0, 0, 0, 0.22)",
    "frosted": "rgba(13, 17, 26, 0.75)",
    "none": "transparent"
  };
  var bgVal = bgMap[bgKey] || bgMap["medium"];

  var posMap = {
    "low": "10px",
    "normal": "28px",
    "medium": "48px",
    "high": "72px"
  };
  var posVal = posMap[posKey] || posMap["normal"];

  var isMobile = /android|iphone|ipad|ipod|windows phone|blackberry|mobile/i.test(navigator.userAgent || "") || window.innerWidth < 768;
  var szMap = {
    "s": isMobile ? "13px" : "15px",
    "m": isMobile ? "16px" : "21px",
    "l": isMobile ? "20px" : "27px",
    "xl": isMobile ? "24px" : "33px"
  };
  var szVal = szMap[sz] || szMap["m"];

  var playerEl = document.querySelector(".art-video-player");
  if(playerEl){
    playerEl.style.setProperty("--sub-font", fontVal);
    playerEl.style.setProperty("--sub-size", szVal);
    playerEl.style.setProperty("--sub-color", color);
    playerEl.style.setProperty("--sub-bg", bgVal);
    playerEl.style.setProperty("--sub-bottom", posVal);
    if(bgKey === "frosted"){
      playerEl.classList.add("sub-frosted");
    } else {
      playerEl.classList.remove("sub-frosted");
    }
  }

  if(window.art && window.art.subtitle){
    try {
      window.art.subtitle.style("fontFamily", fontVal);
      window.art.subtitle.style("color", color);
      window.art.subtitle.style("backgroundColor", bgVal);
      window.art.subtitle.style("fontSize", szVal);
    } catch(_){}
  }

  var box = $("pm-subs-overlay");
  if(box){
    box.style.setProperty("--sub-font", fontVal);
    box.style.setProperty("--sub-color", color);
    box.style.setProperty("--sub-bg", bgVal);
    box.style.bottom = posVal;
    box.classList.remove("sz-s","sz-m","sz-l","sz-xl");
    box.classList.add("sz-" + sz);
  }

  document.querySelectorAll(".sub-size button").forEach(function(b){
    b.classList.toggle("active", b.getAttribute("data-subsize") === sz);
  });

  updateSubStylePreview();
}

function syncSubSize(){
  syncSubStyle();
}

function setSubFont(f){
  if(!FONT_MAP[f]) return;
  cur.subFont = f;
  try{ localStorage.setItem("tatap_sub_font", f); }catch(e){}
  syncSubStyle();
  if(window.art && window.art.setting && window.art.setting.cache && window.art.setting.cache.has("subtitle-font")){
    try{ window.art.setting.update({ name: "subtitle-font", tooltip: getSubFontName(f) }); }catch(_){}
  }
}

function setSubSize(sz){
  if(sz!=="s"&&sz!=="m"&&sz!=="l"&&sz!=="xl") return;
  cur.subSize = sz;
  try{ localStorage.setItem("tatap_subsize", sz); }catch(e){}
  syncSubStyle();
  if(window.art && window.art.setting && window.art.setting.cache && window.art.setting.cache.has("subtitle-size")){
    try{ window.art.setting.update({ name: "subtitle-size", tooltip: sz.toUpperCase() }); }catch(_){}
  }
}

function setSubColor(c){
  cur.subColor = c;
  try{ localStorage.setItem("tatap_sub_color", c); }catch(e){}
  syncSubStyle();
  if(window.art && window.art.setting && window.art.setting.cache && window.art.setting.cache.has("subtitle-color")){
    try{ window.art.setting.update({ name: "subtitle-color", tooltip: getSubColorName(c) }); }catch(_){}
  }
}

function setSubBg(b){
  cur.subBg = b;
  try{ localStorage.setItem("tatap_sub_bg", b); }catch(e){}
  syncSubStyle();
  if(window.art && window.art.setting && window.art.setting.cache && window.art.setting.cache.has("subtitle-bg")){
    try{ window.art.setting.update({ name: "subtitle-bg", tooltip: getSubBgName(b) }); }catch(_){}
  }
}

function setSubPos(p){
  cur.subPos = p;
  try{ localStorage.setItem("tatap_sub_pos", p); }catch(e){}
  syncSubStyle();
  if(window.art && window.art.setting && window.art.setting.cache && window.art.setting.cache.has("subtitle-pos")){
    try{ window.art.setting.update({ name: "subtitle-pos", tooltip: getSubPosName(p) }); }catch(_){}
  }
}

function updateSubStylePreview(){
  var previewText = $("sub-preview-text");
  if(!previewText) return;

  var fontVal = FONT_MAP[cur.subFont || "sans"] || FONT_MAP["sans"];
  var color = cur.subColor || "#ffffff";
  var bgKey = cur.subBg || "medium";
  var bgMap = {
    "medium": "rgba(0, 0, 0, 0.55)",
    "dark": "rgba(0, 0, 0, 0.85)",
    "light": "rgba(0, 0, 0, 0.22)",
    "frosted": "rgba(13, 17, 26, 0.75)",
    "none": "transparent"
  };
  var bgVal = bgMap[bgKey] || bgMap["medium"];
  var szMap = { "s": "13px", "m": "17px", "l": "21px", "xl": "25px" };
  var szVal = szMap[cur.subSize || "m"] || "17px";
  var posMap = { "low": "8px", "normal": "20px", "medium": "36px", "high": "52px" };
  var posVal = posMap[cur.subPos || "normal"] || "20px";

  previewText.style.fontFamily = fontVal;
  previewText.style.color = color;
  previewText.style.backgroundColor = bgVal;
  previewText.style.fontSize = szVal;
  previewText.style.marginBottom = posVal;

  if(bgKey === "frosted"){
    previewText.classList.add("preview-frosted");
  } else {
    previewText.classList.remove("preview-frosted");
  }

  // Sync active classes on buttons
  var modal = $("sub-style-modal");
  if(modal){
    modal.querySelectorAll(".sub-styler-opt[data-sub-font]").forEach(function(b){
      b.classList.toggle("active", b.getAttribute("data-sub-font") === (cur.subFont || "sans"));
    });
    modal.querySelectorAll(".sub-styler-opt[data-sub-bg]").forEach(function(b){
      b.classList.toggle("active", b.getAttribute("data-sub-bg") === (cur.subBg || "medium"));
    });
    modal.querySelectorAll(".sub-styler-opt[data-sub-color]").forEach(function(b){
      b.classList.toggle("active", b.getAttribute("data-sub-color") === (cur.subColor || "#ffffff"));
    });
    modal.querySelectorAll(".sub-styler-opt[data-sub-size]").forEach(function(b){
      b.classList.toggle("active", b.getAttribute("data-sub-size") === (cur.subSize || "m"));
    });
    modal.querySelectorAll(".sub-styler-opt[data-sub-pos]").forEach(function(b){
      b.classList.toggle("active", b.getAttribute("data-sub-pos") === (cur.subPos || "normal"));
    });
  }
}

var _subStyleSnapshot = null;

function attachModalToActiveLayer(modalEl){
  if(!modalEl) return;
  var fsEl = document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement;
  if(fsEl){
    if(modalEl.parentNode !== fsEl){
      fsEl.appendChild(modalEl);
    }
    return;
  }
  var pm = $("player-modal");
  if(pm && !pm.classList.contains("hidden")){
    if(modalEl.parentNode !== pm){
      pm.appendChild(modalEl);
    }
    return;
  }
  if(modalEl.parentNode !== document.body){
    document.body.appendChild(modalEl);
  }
}

function detachModalFromActiveLayer(modalEl){
  if(!modalEl) return;
  if(modalEl.parentNode !== document.body){
    document.body.appendChild(modalEl);
  }
}

function openSubStyleModal(){
  var m = $("sub-style-modal");
  if(!m) return;
  if(window.art){
    try { window.art.pause(); } catch(e){}
    try { if(window.art.setting) window.art.setting.show = false; } catch(e){}
  } else {
    var v = $("vid");
    if(v && !v.paused){
      try { v.pause(); } catch(e){}
    }
  }
  attachModalToActiveLayer(m);
  // Simpan snapshot untuk rollback jika pengguna membatalkan
  _subStyleSnapshot = {
    font: cur.subFont || "sans",
    bg: cur.subBg || "medium",
    color: cur.subColor || "#ffffff",
    size: cur.subSize || "m",
    pos: cur.subPos || "normal"
  };
  m.classList.remove("hidden");
  m.style.display = "flex";
  updateSubStylePreview();
  if(window.TvNavigationManager) window.TvNavigationManager.setPlayerModalState(true);
  if(window.TatapSfx) TatapSfx.play("select");
}

function closeSubStyleModal(){
  var m = $("sub-style-modal");
  if(!m || m.classList.contains("hidden")) return;
  m.classList.add("hidden");
  m.style.display = "none";
  detachModalFromActiveLayer(m);
  if(window.TvNavigationManager) window.TvNavigationManager.setPlayerModalState(false);
  if(window.TatapSfx) TatapSfx.play("back");
}

function cancelSubStyleModal(){
  if(_subStyleSnapshot){
    setSubFont(_subStyleSnapshot.font);
    setSubBg(_subStyleSnapshot.bg);
    setSubColor(_subStyleSnapshot.color);
    setSubSize(_subStyleSnapshot.size);
    setSubPos(_subStyleSnapshot.pos);
    _subStyleSnapshot = null;
  }
  closeSubStyleModal();
}

function resetSubStyle(){
  setSubFont("sans");
  setSubColor("#ffffff");
  setSubBg("medium");
  setSubSize("m");
  setSubPos("normal");
  if(window.TatapSfx) TatapSfx.play("tick");
  toast("Pengaturan Subtitle Direset", 1400, "icon-subtitles");
}

function syncTranslate(){
  var btn=$("pm-translate");
  if(!btn)return;
  btn.setAttribute("data-on",cur.translate?"1":"0");
  btn.title="Translate ID: "+(cur.translate?"on":"off")+" (butuh track English sebagai source)";
}
function setTranslate(on){
  cur.translate=!!on;
  try{localStorage.setItem("tatap_translate",cur.translate?"1":"0");}catch(e){}
  syncTranslate();
  // Re-render dropdown agar opsi Indonesian (AI) muncul/hilang.
  var subs=(cur.res&&cur.res.subtitles)||[];
  if(cur.translate){
    var picked=pickSubtitleUrl(subs, "Indonesian");
    if(picked){
      cur.activeSub=picked;
      switchSubtitleTrack(picked);
    }
  }
  renderSubtitles(subs, cur.activeSub);
  syncArtplayerSubtitles(subs, cur.activeSub);
  syncTranslateBtn();
  toast("Terjemahan: " + (cur.translate ? "ON" : "OFF"), 1400, "icon-globe");
}

function renderSourceUI(){
  var s = cur.source || "hianime";
  var isOtaku = (s === "otakudesu");
  var isAnichan = (s === "anichan");
  var txt = isOtaku ? "src: otakudesu (sub indo) ⇄" : (isAnichan ? "src: anichan (failover) ⇄" : "src: hianime ⇄");
  var badgeTxt = isOtaku ? "OTAKUDESU (SUB INDO) ⇄" : (isAnichan ? "ANICHAN (FAILOVER) ⇄" : "HIANIME ⇄");
  var shortLabel = isOtaku ? "Otakudesu" : (isAnichan ? "AniChan" : "HiAnime");
  var sb = $("sb-source");
  if(sb){
    sb.textContent = txt;
    sb.classList.toggle("otaku", isOtaku);
  }
  var tm = $("tm-source-btn");
  if(tm){
    tm.textContent = "SRC: " + badgeTxt;
    tm.classList.toggle("otaku", isOtaku);
  }
  var popBadge = $("pop-src-badge");
  if(popBadge) popBadge.textContent = shortLabel;
  var drawerBadge = $("drawer-src-badge");
  if(drawerBadge) drawerBadge.textContent = shortLabel;
}

function switchSource(targetSource){
  var v=$("vid");
  var curTime = (v && !isNaN(v.currentTime)) ? v.currentTime : 0;
  var nextSource = targetSource;
  if(!nextSource){
    if(cur.source === "hianime") nextSource = "otakudesu";
    else if(cur.source === "otakudesu") nextSource = "anichan";
    else nextSource = "hianime";
  }
  cur.source = nextSource;
  renderSourceUI();
  if(window.Tatap && window.Tatap.setSetting){
    window.Tatap.setSetting({ preferred_source: nextSource }).catch(function(){});
  }
  var label = nextSource === "otakudesu" ? "Otakudesu (Sub Indo)" : (nextSource === "anichan" ? "AniChan (Failover)" : "HiAnime");
  toast("Sumber: " + label);
  if(!$("player-modal").classList.contains("hidden") && cur.ep){
    openPlayer(cur.ep, curTime);
  }
  return nextSource;
}

function openDrawer(){
  var p = $("drawer-panel");
  if(p){
    p.classList.remove("hidden");
    if(window.TatapSfx) TatapSfx.play("select");
  }
}
function closeDrawer(){
  var p = $("drawer-panel");
  if(p && !p.classList.contains("hidden")){
    p.classList.add("hidden");
    if(window.TatapSfx) TatapSfx.play("back");
  }
}

var _lastActiveBeforeSpotlight = null;

function getSpotlightFocusableElements(){
  var sm = $("spotlight-modal");
  if(!sm) return [];
  var selector = 'input:not([disabled]):not([readonly]), button:not([disabled]), [tabindex="0"]:not([disabled])';
  var all = Array.prototype.slice.call(sm.querySelectorAll(selector));
  return all.filter(function(el){
    return !el.classList.contains("hidden") && el.offsetParent !== null;
  });
}

function trapSpotlightFocus(shiftKey){
  var focusables = getSpotlightFocusableElements();
  if(!focusables.length){
    var cmd = $("cmd");
    if(cmd) cmd.focus();
    return;
  }
  var active = document.activeElement;
  var idx = focusables.indexOf(active);
  if(shiftKey){
    var prevIdx = (idx <= 0) ? (focusables.length - 1) : (idx - 1);
    focusables[prevIdx].focus();
  } else {
    var nextIdx = (idx < 0 || idx >= focusables.length - 1) ? 0 : (idx + 1);
    focusables[nextIdx].focus();
  }
}

function openSpotlight(){
  var sm = $("spotlight-modal");
  if(!sm) return;
  _lastActiveBeforeSpotlight = document.activeElement;
  document.body.classList.add("spotlight-open");
  sm.classList.remove("hidden");
  var cmd = $("cmd");
  if(cmd){
    cmd.removeAttribute("readonly");
    cmd.focus();
    if(cmd.select) cmd.select();
    if(window.Tui && window.Tui.S) window.Tui.S.promptFoc = true;
  }
}

function closeSpotlight(){
  var sm = $("spotlight-modal");
  if(!sm || sm.classList.contains("hidden")) return;
  sm.classList.add("hidden");
  document.body.classList.remove("spotlight-open");
  var cmd = $("cmd");
  if(cmd){
    cmd.setAttribute("readonly", "readonly");
    cmd.blur();
    if(window.Tui && window.Tui.S) window.Tui.S.promptFoc = false;
  }
  if(_lastActiveBeforeSpotlight && typeof _lastActiveBeforeSpotlight.focus === "function"){
    try{ _lastActiveBeforeSpotlight.focus(); }catch(_){}
  }
  _lastActiveBeforeSpotlight = null;
}

function initSidebar(){
  var sb = $("app-sidebar");
  if(!sb) return;
  var isCol = localStorage.getItem("tatap_sidebar_collapsed") === "1";
  if(isCol){
    sb.classList.add("collapsed");
  }

  function toggleSidebar(){
    sb.classList.toggle("collapsed");
    var collapsed = sb.classList.contains("collapsed");
    try { localStorage.setItem("tatap_sidebar_collapsed", collapsed ? "1" : "0"); }catch(_){}
  }

  var btnToggle = $("btn-toggle-sidebar");
  if(btnToggle){
    btnToggle.addEventListener("click", function(){
      toggleSidebar();
    });
  }

  // Sidebar Brand Home Navigation
  var sBrand = $("sidebar-brand");
  if(sBrand){
    sBrand.addEventListener("click", function(){
      if(window.Tui && window.Tui.setView) window.Tui.setView("musim");
    });
  }

  // Sidebar Search Button Trigger
  var sbSearch = $("sidebar-search-btn");
  if(sbSearch){
    sbSearch.addEventListener("click", function(e){
      e.stopPropagation();
      openSpotlight();
    });
  }

  // Cursor & Focus in Sidebar: blur focused anime cards & cancel zoom effect
  sb.addEventListener("mouseenter", function(){
    document.body.classList.add("sidebar-hovered");
    if(window.Tui && window.Tui.blurCards){
      window.Tui.blurCards();
    }
  });

  sb.addEventListener("mouseleave", function(){
    document.body.classList.remove("sidebar-hovered");
  });

  sb.addEventListener("focusin", function(){
    document.body.classList.add("sidebar-hovered");
    if(window.Tui && window.Tui.blurCards){
      window.Tui.blurCards();
    }
  });

  sb.addEventListener("focusout", function(e){
    if(!sb.contains(e.relatedTarget)){
      document.body.classList.remove("sidebar-hovered");
    }
  });

  // Sidebar internal arrow navigation
  sb.addEventListener("keydown", function(e){
    if(e.key === "ArrowDown" || e.key === "ArrowUp"){
      var focusables = Array.prototype.slice.call(
        sb.querySelectorAll("button:not([disabled]), .sidebar-nav-item, [tabindex='0']")
      ).filter(function(el){ return el.offsetParent !== null; });
      if(focusables.length === 0) return;
      var curIdx = focusables.indexOf(document.activeElement);
      e.preventDefault();
      if(e.key === "ArrowDown"){
        var nextIdx = (curIdx < 0 || curIdx >= focusables.length - 1) ? 0 : (curIdx + 1);
        focusables[nextIdx].focus();
      } else {
        var prevIdx = (curIdx <= 0) ? (focusables.length - 1) : (curIdx - 1);
        focusables[prevIdx].focus();
      }
    } else if(e.key === "ArrowRight"){
      e.preventDefault();
      if(window.Tui && window.Tui.moveSel){
        window.Tui.moveSel(0);
      }
    }
  });

  // Statusbar Hint Search Trigger
  var sbHintSearch = $("sb-hint-search");
  if(sbHintSearch){
    sbHintSearch.addEventListener("click", function(e){
      e.stopPropagation();
      openSpotlight();
    });
    sbHintSearch.addEventListener("keydown", function(e){
      if(e.key === "Enter" || e.key === " "){
        e.preventDefault();
        e.stopPropagation();
        openSpotlight();
      }
    });
  }

  var sbHintSidebar = $("sb-hint-sidebar");
  if(sbHintSidebar){
    sbHintSidebar.addEventListener("click", function(e){
      e.stopPropagation();
      toggleSidebar();
    });
    sbHintSidebar.addEventListener("keydown", function(e){
      if(e.key === "Enter" || e.key === " "){
        e.preventDefault();
        e.stopPropagation();
        toggleSidebar();
      }
    });
  }

  var sbHintTheme = $("sb-hint-theme");
  if(sbHintTheme){
    sbHintTheme.addEventListener("click", function(e){
      e.stopPropagation();
      var t = TatapTheme.toggle();
      toast(t === "light" ? "Mode Terang Aktif" : "Mode Gelap Aktif", 1200);
    });
    sbHintTheme.addEventListener("keydown", function(e){
      if(e.key === "Enter" || e.key === " "){
        e.preventDefault();
        e.stopPropagation();
        var t = TatapTheme.toggle();
        toast(t === "light" ? "Mode Terang Aktif" : "Mode Gelap Aktif", 1200);
      }
    });
  }

  var sbHintPager = $("sb-hint-pager");
  if(sbHintPager){
    sbHintPager.addEventListener("click", function(e){
      e.stopPropagation();
      if(window.Tui && window.Tui.pageNext) window.Tui.pageNext();
    });
    sbHintPager.addEventListener("keydown", function(e){
      if(e.key === "Enter" || e.key === " "){
        e.preventDefault();
        e.stopPropagation();
        if(window.Tui && window.Tui.pageNext) window.Tui.pageNext();
      }
    });
  }

  var sbHintHelp = $("sb-hint-help");
  if(sbHintHelp){
    sbHintHelp.addEventListener("click", function(e){
      e.stopPropagation();
      var ho = $("help-overlay");
      if(ho) ho.classList.remove("hidden");
      var hb = $("help-body");
      if(hb && window.Tui) hb.textContent = window.Tui.cmdUsage();
    });
    sbHintHelp.addEventListener("keydown", function(e){
      if(e.key === "Enter" || e.key === " "){
        e.preventDefault();
        e.stopPropagation();
        var ho = $("help-overlay");
        if(ho) ho.classList.remove("hidden");
        var hb = $("help-body");
        if(hb && window.Tui) hb.textContent = window.Tui.cmdUsage();
      }
    });
  }

  var sbView = $("sb-view");
  if(sbView){
    sbView.addEventListener("click", function(e){
      e.stopPropagation();
      if(window.Tui && window.Tui.cycleView) window.Tui.cycleView(1);
    });
    sbView.addEventListener("keydown", function(e){
      if(e.key === "Enter" || e.key === " "){
        e.preventDefault();
        e.stopPropagation();
        if(window.Tui && window.Tui.cycleView) window.Tui.cycleView(1);
      }
    });
  }

  // Sidebar Controls
  var sVal = $("sidebar-src-val");
  if(sVal){
    sVal.textContent = (cur.source || "hianime").toUpperCase();
  }

  var scf = $("sidebar-catalog-filter");
  if(scf) scf.addEventListener("click", function(){
    if(window.Tui && window.Tui.openCatalogFilterModal) window.Tui.openCatalogFilterModal();
  });

  var sgf = $("sidebar-genre-filter");
  if(sgf) sgf.addEventListener("click", function(){
    if(window.Tui && window.Tui.openGenreModal) window.Tui.openGenreModal();
  });

  var sss = $("sidebar-switch-source");
  if(sss) sss.addEventListener("click", function(){
    var src = switchSource();
    var sVal = $("sidebar-src-val");
    if(sVal) sVal.textContent = (src || "HiAnime").toUpperCase();
  });

  var saf = $("sidebar-ai-fansub");
  if(saf) saf.addEventListener("click", function(){
    openAiSettingsModal();
  });

  var stt = $("sidebar-toggle-theme");
  if(stt) stt.addEventListener("click", function(){
    var t = TatapTheme.toggle();
    toast(t === "light" ? "Mode Terang Aktif" : "Mode Gelap Aktif", 1200);
    var lbl = $("sidebar-theme-label");
    if(lbl) lbl.textContent = t === "light" ? "Mode Gelap" : "Mode Terang";
  });

  var sup = $("sidebar-update");
  if(sup) sup.addEventListener("click", function(){
    checkForUpdate(true);
  });

  var shp = $("sidebar-help");
  if(shp) shp.addEventListener("click", function(){
    var ho = $("help-overlay");
    if(ho) ho.classList.remove("hidden");
    var hb = $("help-body");
    if(hb && window.Tui) hb.textContent = window.Tui.cmdUsage();
  });

  // Spotlight Modal Triggers & Controls (Focus Lock & Cursor Containment)
  var spEsc = $("spotlight-esc-btn");
  if(spEsc){
    spEsc.addEventListener("click", function(e){
      e.preventDefault();
      e.stopPropagation();
      closeSpotlight();
    });
    spEsc.addEventListener("keydown", function(e){
      if(e.key === "Enter" || e.key === " "){
        e.preventDefault();
        e.stopPropagation();
        closeSpotlight();
      }
    });
  }

  // Penguncian fokus & kursor: Klik backdrop tidak membocorkan kursor keluar modal search
  var spBackdrop = $("spotlight-backdrop");
  if(spBackdrop){
    spBackdrop.addEventListener("mousedown", function(e){
      e.preventDefault(); // Mencegah hilangnya kursor/fokus dari input #cmd
      var cmd = $("cmd");
      if(cmd) cmd.focus();
    });
    spBackdrop.addEventListener("click", function(e){
      e.preventDefault();
      e.stopPropagation();
      var cmd = $("cmd");
      if(cmd) cmd.focus();
    });
  }

  var spModal = $("spotlight-modal");
  if(spModal){
    spModal.addEventListener("mousedown", function(e){
      if(e.target === spModal){
        e.preventDefault();
        var cmd = $("cmd");
        if(cmd) cmd.focus();
      }
    });
    spModal.addEventListener("click", function(e){
      if(e.target === spModal){
        e.preventDefault();
        e.stopPropagation();
        var cmd = $("cmd");
        if(cmd) cmd.focus();
      }
    });
    // Tab trap dan Escape listener pada kontainer modal
    spModal.addEventListener("keydown", function(e){
      if(e.key === "Tab"){
        e.preventDefault();
        e.stopPropagation();
        trapSpotlightFocus(e.shiftKey);
      } else if(e.key === "Escape"){
        e.preventDefault();
        e.stopPropagation();
        closeSpotlight();
      }
    });
  }

  // Kunci kursor saat klik area non-interaktif kartu spotlight
  var spCard = document.querySelector(".spotlight-card");
  if(spCard){
    spCard.addEventListener("mousedown", function(e){
      var t = (e.target && e.target.tagName || "").toUpperCase();
      if(t !== "INPUT" && t !== "BUTTON" && !e.target.closest("button") && !e.target.closest("input") && !e.target.closest(".spotlight-esc-btn")){
        e.preventDefault();
        var cmd = $("cmd");
        if(cmd) cmd.focus();
      }
    });
  }

  // Global boundary trap: Bila fokus berusaha bocor keluar dari modal search, kunci kembali
  document.addEventListener("focusin", function(e){
    var sm = $("spotlight-modal");
    if(sm && !sm.classList.contains("hidden")){
      if(!sm.contains(e.target)){
        e.stopPropagation();
        var cmd = $("cmd");
        if(cmd) cmd.focus();
      }
    }
  }, true);

  // Quick Tags inside Spotlight
  document.querySelectorAll(".spotlight-tag").forEach(function(tag){
    tag.addEventListener("click", function(){
      var cmd = tag.getAttribute("data-cmd");
      var inp = $("cmd");
      if(inp && cmd){
        inp.value = cmd;
        if(window.Tui && window.Tui.submitPrompt){
          window.Tui.submitPrompt();
        }
        closeSpotlight();
      }
    });
  });

  // Keyboard Shortcuts: Ctrl+B / Cmd+B (Toggle Sidebar) & Ctrl+K / Cmd+K (Spotlight)
  window.addEventListener("keydown", function(e){
    if((e.metaKey || e.ctrlKey) && (e.key === "b" || e.key === "B")){
      e.preventDefault();
      var sb = $("app-sidebar");
      if(sb){
        sb.classList.toggle("collapsed");
        var isCol = sb.classList.contains("collapsed");
        try { localStorage.setItem("tatap_sidebar_collapsed", isCol ? "1" : "0"); }catch(_){}
      }
    } else if((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")){
      e.preventDefault();
      var sm = $("spotlight-modal");
      if(sm && !sm.classList.contains("hidden")) closeSpotlight();
      else openSpotlight();
    }
  });
}

function openUpdateModal(data){
  var m = $("update-modal");
  if(!m) return;
  $("um-title").textContent = data.release_name || ("Tatap v" + data.latest_version);
  $("um-sub").textContent = "Rilis: " + (data.tag_name || "v" + data.latest_version) + " · Terpasang: v" + data.current_version;
  $("um-content").textContent = data.body || "Tidak ada catatan rilis.";
  
  var act = $("um-actions");
  act.innerHTML = "";
  
  // Deteksi OS user untuk tombol download utama
  var ua = (navigator.userAgent || "").toLowerCase();
  var isWin = ua.indexOf("windows") >= 0;
  var isLinux = ua.indexOf("linux") >= 0 && ua.indexOf("android") === -1;
  var isAndroid = ua.indexOf("android") >= 0;

  var primaryUrl = "";
  var primaryLabel = "Unduh Pembaruan";
  if(isWin && data.assets && data.assets.windows){
    primaryUrl = data.assets.windows;
    primaryLabel = "🪟 Unduh Windows Portable (.zip)";
  } else if(isLinux && data.assets && data.assets.linux){
    primaryUrl = data.assets.linux;
    primaryLabel = "🐧 Unduh Linux AppImage";
  } else if(isAndroid && data.assets && data.assets.android){
    primaryUrl = data.assets.android;
    primaryLabel = "📱 Unduh Signed APK Android";
  } else if(data.assets && data.assets.windows){
    primaryUrl = data.assets.windows;
    primaryLabel = "Unduh Rilis Resmi";
  }

  if(primaryUrl){
    var a = document.createElement("a");
    a.className = "update-btn";
    a.href = primaryUrl;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = primaryLabel;
    act.appendChild(a);
  }

  // Tombol buka halaman GitHub release
  if(data.release_url){
    var aRel = document.createElement("a");
    aRel.className = "update-btn secondary";
    aRel.href = data.release_url;
    aRel.target = "_blank";
    aRel.rel = "noopener noreferrer";
    aRel.textContent = "Buka di GitHub";
    act.appendChild(aRel);
  }

  m.classList.remove("hidden");
}

function closeUpdateModal(){
  var m = $("update-modal");
  if(m) m.classList.add("hidden");
}

async function openAiSettingsModal(){
  var m = $("ai-settings-modal");
  if(!m) return;
  if(window.art){
    try { window.art.pause(); } catch(e){}
    try { if(window.art.setting) window.art.setting.show = false; } catch(e){}
  } else {
    var v = $("vid");
    if(v && !v.paused){
      try { v.pause(); } catch(e){}
    }
  }
  attachModalToActiveLayer(m);
  m.classList.remove("hidden");
  m.style.display = "flex";
  if(window.TvNavigationManager) window.TvNavigationManager.setPlayerModalState(true);
  try{
    var r = await window.Tatap.getSettings();
    var d = (r && r.success && r.data) || {};
    var key = d.translate_apikey || "";
    var model = d.translate_model || "gemini-2.0-flash";
    var url = d.translate_apiurl || "https://generativelanguage.googleapis.com/v1beta/openai";
    var prompt = d.translate_custom_prompt || "";

    if($("ai-input-key")) $("ai-input-key").value = key;
    if($("ai-input-model")) $("ai-input-model").value = model;
    if($("ai-input-url")) $("ai-input-url").value = url;
    if($("ai-input-prompt")) $("ai-input-prompt").value = prompt;

    var provLabel = key ? (key.indexOf("gsk_")===0 ? "Groq" : (key.indexOf("AQ.")===0 || key.indexOf("AIza")===0) ? "Google Gemini" : key.indexOf("sk-")===0 ? "OpenAI" : "Aktif (Kustom)") : "Belum Disetel";
    if($("ai-status-prov")) {
      $("ai-status-prov").textContent = provLabel;
      $("ai-status-prov").className = "badge-status " + (key ? "completed" : "ongoing");
    }
    if($("ai-status-model")) $("ai-status-model").textContent = model;
  }catch(e){
    console.error("Gagal memuat setelan AI", e);
  }
}

function closeAiSettingsModal(){
  var m = $("ai-settings-modal");
  if(m){
    m.classList.add("hidden");
    m.style.display = "none";
    detachModalFromActiveLayer(m);
  }
  if(window.TvNavigationManager) window.TvNavigationManager.setPlayerModalState(false);
}

window.openAiSettingsModal = openAiSettingsModal;
window.closeAiSettingsModal = closeAiSettingsModal;

function checkForUpdate(manualTrigger){
  if(manualTrigger) toast("Memeriksa update ke GitHub…", 2000);
  window.Tatap.checkUpdate(!!manualTrigger).then(function(res){
    if(res && res.success && res.data){
      var d = res.data;
      if(d.has_update){
        openUpdateModal(d);
        toast("🚀 Pembaruan Tatap v" + d.latest_version + " tersedia!", 4000);
      } else {
        if(manualTrigger){
          toast("✓ Tatap v" + d.current_version + " adalah versi terbaru!", 3000);
        }
      }
    } else {
      if(manualTrigger){
        toast("Gagal memeriksa update: " + (res && res.error || "koneksi bermasalah"), 3000);
      }
    }
  }).catch(function(err){
    if(manualTrigger){
      toast("Error cek update: " + (err && err.message || err), 3000);
    }
  });
}

App = {
  TvNavigationManager: TvNavigationManager,
  openTitle:openTitle, closeTitle:closeTitle,
  openPlayer:openPlayer, closePlayer:closePlayer, playMPV:playMPV,
  renderContinue:renderContinue, onKeyPlayer:onKeyPlayer,
  formatTimeSec:formatTimeSec,
  switchSource:switchSource,
  setPlaySpeed:setPlaySpeed, adjustPlaySpeed:adjustPlaySpeed,
  setSubDelay:setSubDelay, adjustSubDelay:adjustSubDelay,
  openDrawer:openDrawer, closeDrawer:closeDrawer,
  openUpdateModal:openUpdateModal, closeUpdateModal:closeUpdateModal,
  openAiSettingsModal:openAiSettingsModal, closeAiSettingsModal:closeAiSettingsModal,
  checkForUpdate:checkForUpdate,
  closeResumeModal:closeResumeModal, dismissResumeModal:dismissResumeModal,
  openSpotlight:openSpotlight, closeSpotlight:closeSpotlight,
  trapSpotlightFocus:trapSpotlightFocus,
  initSidebar:initSidebar,
  openGenreModal:function(){
    if(typeof window.Tui!=="undefined"&&window.Tui.openGenreModal){
      window.Tui.openGenreModal();
    }
  }
};

var TatapTheme = (function(){
  function getTheme(){
    return localStorage.getItem("tatap_theme") || "dark";
  }
  function setTheme(t){
    var theme = (t === "light") ? "light" : "dark";
    localStorage.setItem("tatap_theme", theme);
    document.documentElement.setAttribute("data-theme", theme);
    document.body.setAttribute("data-theme", theme);

    var isLight = theme === "light";
    var popIcon = $("pop-theme-icon");
    if(popIcon) popIcon.innerHTML = '<use href="#icon-' + (isLight ? 'moon' : 'sun') + '"/>';
    var popLabel = $("pop-theme-label");
    if(popLabel) popLabel.textContent = isLight ? "Mode Gelap" : "Mode Terang";

    var drawerIcon = $("drawer-theme-icon");
    if(drawerIcon) drawerIcon.innerHTML = '<use href="#icon-' + (isLight ? 'moon' : 'sun') + '"/>';
    var drawerLabel = $("drawer-theme-label");
    if(drawerLabel) drawerLabel.textContent = isLight ? "Mode Gelap" : "Mode Terang";
    var drawerBadge = $("drawer-theme-badge");
    if(drawerBadge) drawerBadge.textContent = isLight ? "Terang" : "Gelap";

    var sidebarIcon = $("sidebar-theme-icon");
    if(sidebarIcon) sidebarIcon.innerHTML = '<use href="#icon-' + (isLight ? 'moon' : 'sun') + '"/>';
    var sidebarLabel = $("sidebar-theme-label");
    if(sidebarLabel) sidebarLabel.textContent = isLight ? "Mode Gelap" : "Mode Terang";

    var metaTheme = document.querySelector('meta[name="theme-color"]');
    if(metaTheme) metaTheme.setAttribute("content", isLight ? "#f5f5f7" : "#07080a");
    return theme;
  }
  function toggle(){
    return setTheme(getTheme() === "light" ? "dark" : "light");
  }
  return { get: getTheme, set: setTheme, toggle: toggle };
})();
window.TatapTheme = TatapTheme;

var TatapSfx = (function(){
  var audioCtx = null;
  var lastTick = 0;

  function isEnabled(){
    return localStorage.getItem("tatap_sfx_enabled") !== "0";
  }

  function setEnabled(val){
    var enabled = !!val;
    localStorage.setItem("tatap_sfx_enabled", enabled ? "1" : "0");
    syncUI();
    return enabled;
  }

  function toggle(){
    return setEnabled(!isEnabled());
  }

  function getCtx(){
    if(!audioCtx && (window.AudioContext || window.webkitAudioContext)){
      try {
        var AudioCtx = window.AudioContext || window.webkitAudioContext;
        audioCtx = new AudioCtx();
      } catch(e){}
    }
    if(audioCtx && audioCtx.state === "suspended"){
      audioCtx.resume().catch(function(){});
    }
    return audioCtx;
  }

  function syncUI(){
    var en = isEnabled();
    var popIcon = $("pop-sfx-icon");
    if(popIcon) popIcon.innerHTML = '<use href="#icon-' + (en ? 'volume-high' : 'volume-mute') + '"/>';
    var popBadge = $("pop-sfx-badge");
    if(popBadge) popBadge.textContent = en ? "Aktif" : "Mati";

    var drawerIcon = $("drawer-sfx-icon");
    if(drawerIcon) drawerIcon.innerHTML = '<use href="#icon-' + (en ? 'volume-high' : 'volume-mute') + '"/>';
    var drawerBadge = $("drawer-sfx-badge");
    if(drawerBadge) drawerBadge.textContent = en ? "Aktif" : "Mati";
  }

  function play(type){
    if(!isEnabled()) return;
    var ctx = getCtx();
    if(!ctx) return;

    var now = ctx.currentTime;

    if(type === "tick"){
      var tNow = Date.now();
      if(tNow - lastTick < 35) return;
      lastTick = tNow;

      try {
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.setValueAtTime(1760, now);
        osc.frequency.exponentialRampToValueAtTime(1200, now + 0.018);
        gain.gain.setValueAtTime(0.08, now);
        gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.018);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(now);
        osc.stop(now + 0.018);
      } catch(e){}
    }
    else if(type === "select"){
      try {
        var o1 = ctx.createOscillator();
        var g1 = ctx.createGain();
        o1.type = "sine";
        o1.frequency.setValueAtTime(523.25, now);
        o1.frequency.exponentialRampToValueAtTime(1046.5, now + 0.045);
        g1.gain.setValueAtTime(0.12, now);
        g1.gain.exponentialRampToValueAtTime(0.0001, now + 0.095);
        o1.connect(g1);
        g1.connect(ctx.destination);
        o1.start(now);
        o1.stop(now + 0.095);
      } catch(e){}
    }
    else if(type === "back"){
      try {
        var o2 = ctx.createOscillator();
        var g2 = ctx.createGain();
        o2.type = "sine";
        o2.frequency.setValueAtTime(587.33, now);
        o2.frequency.exponentialRampToValueAtTime(392.00, now + 0.05);
        g2.gain.setValueAtTime(0.10, now);
        g2.gain.exponentialRampToValueAtTime(0.0001, now + 0.085);
        o2.connect(g2);
        g2.connect(ctx.destination);
        o2.start(now);
        o2.stop(now + 0.085);
      } catch(e){}
    }
    else if(type === "tab"){
      try {
        var o3 = ctx.createOscillator();
        var g3 = ctx.createGain();
        o3.type = "triangle";
        o3.frequency.setValueAtTime(780, now);
        o3.frequency.exponentialRampToValueAtTime(940, now + 0.03);
        o3.frequency.exponentialRampToValueAtTime(820, now + 0.065);
        g3.gain.setValueAtTime(0.09, now);
        g3.gain.exponentialRampToValueAtTime(0.0001, now + 0.065);
        o3.connect(g3);
        g3.connect(ctx.destination);
        o3.start(now);
        o3.stop(now + 0.065);
      } catch(e){}
    }
    else if(type === "notify"){
      try {
        var freqs = [880, 1108.73, 1318.51];
        freqs.forEach(function(f, i){
          var o = ctx.createOscillator();
          var g = ctx.createGain();
          o.type = "sine";
          o.frequency.setValueAtTime(f, now + i * 0.02);
          g.gain.setValueAtTime(0.06, now + i * 0.02);
          g.gain.exponentialRampToValueAtTime(0.0001, now + i * 0.02 + 0.28);
          o.connect(g);
          g.connect(ctx.destination);
          o.start(now + i * 0.02);
          o.stop(now + i * 0.02 + 0.28);
        });
      } catch(e){}
    }
  }

  function initUnlock(){
    function unlock(){
      getCtx();
      window.removeEventListener("pointerdown", unlock);
      window.removeEventListener("keydown", unlock);
    }
    window.addEventListener("pointerdown", unlock, {once:true});
    window.addEventListener("keydown", unlock, {once:true});
  }

  return {
    isEnabled: isEnabled,
    setEnabled: setEnabled,
    toggle: toggle,
    syncUI: syncUI,
    play: play,
    initUnlock: initUnlock
  };
})();
window.TatapSfx = TatapSfx;

var TatapSafeMode = (function(){
  function isEnabled(){
    if(window.Tatap && window.Tatap.getSafeMode) return window.Tatap.getSafeMode() === 1;
    var sm = localStorage.getItem("tatap_safe_mode");
    return (sm === "0" || sm === 0 || sm === "false") ? false : true;
  }
  function setEnabled(val){
    var res = 1;
    if(window.Tatap && window.Tatap.setSafeMode){
      res = window.Tatap.setSafeMode(val ? 1 : 0);
    } else {
      localStorage.setItem("tatap_safe_mode", val ? "1" : "0");
      res = val ? 1 : 0;
    }
    syncUI();
    return res === 1;
  }
  function toggle(){
    return setEnabled(!isEnabled());
  }
  function syncUI(){
    var en = isEnabled();
    var popBadge = $("pop-safemode-badge");
    if(popBadge) popBadge.textContent = en ? "Aktif" : "Nonaktif";
    var drawerBadge = $("drawer-safemode-badge");
    if(drawerBadge) drawerBadge.textContent = en ? "Aktif" : "Nonaktif";
  }
  return {
    isEnabled: isEnabled,
    setEnabled: setEnabled,
    toggle: toggle,
    syncUI: syncUI
  };
})();
window.TatapSafeMode = TatapSafeMode;

function init(){
  TatapTheme.set(TatapTheme.get());
  TatapSfx.initUnlock();
  TatapSfx.syncUI();
  TatapSafeMode.syncUI();
  loadPrefs();
  initSidebar();
  loadSubStylePrefs();
  syncSubStyle();
  // Toggle translate ID (persist localStorage tat_translate).
  try{
    var tr=localStorage.getItem("tatap_translate");
    if(tr==="1")cur.translate=true;
  }catch(e){}
  syncTranslate();
  var trBtn=$("pm-translate");
  if(trBtn) trBtn.addEventListener("click",function(){setTranslate(!cur.translate);});
  document.querySelectorAll(".sub-size button").forEach(function(b){
    b.addEventListener("click",function(){setSubSize(b.getAttribute("data-subsize"));});
  });
  var sdMinus=$("pm-sub-delay-minus");
  if(sdMinus) sdMinus.addEventListener("click",function(){adjustSubDelay(-0.25);});
  var sdPlus=$("pm-sub-delay-plus");
  if(sdPlus) sdPlus.addEventListener("click",function(){adjustSubDelay(0.25);});
  var sdVal=$("pm-sub-delay-val");
  if(sdVal) sdVal.addEventListener("click",function(){setSubDelay(0.0, true);});
  var v=$("vid");
  if(v){
    v.addEventListener("timeupdate",function(){
      paintCue();
      recordWatchProgress(false);
    });
    v.addEventListener("pause",function(){
      recordWatchProgress(true);
    });
    v.addEventListener("ended",function(){
      var endedSlug = cur.slug;
      var endedEp = cur.ep;

      if(endedSlug && endedEp){
        window.Tatap.saveProgress(endedSlug, endedEp, 0, Math.floor(v.duration||0)).catch(function(){});
        recordEpisodeWatched(endedSlug, endedEp);
      }

      closePlayer();
      toast("Episode " + endedEp + " selesai diputar");
    });
    v.addEventListener("seeked",paintCue);
    v.addEventListener("loadedmetadata",function(){
      if(currentPlaybackSpeed && v.playbackRate !== currentPlaybackSpeed){
        try{ v.playbackRate = currentPlaybackSpeed; }catch(e){}
      }
      if(v.videoWidth && v.videoHeight){
        v.style.aspectRatio = v.videoWidth + " / " + v.videoHeight;
      }
    });
    v.addEventListener("play",function(){
      if(currentPlaybackSpeed && v.playbackRate !== currentPlaybackSpeed){
        try{ v.playbackRate = currentPlaybackSpeed; }catch(e){}
      }
    });
    v.addEventListener("fullscreenchange",syncFullscreenSubtitles);
    v.addEventListener("webkitfullscreenchange",syncFullscreenSubtitles);
    v.addEventListener("webkitbeginfullscreen",syncFullscreenSubtitles);
    v.addEventListener("webkitendfullscreen",syncFullscreenSubtitles);
    v.addEventListener("dblclick",function(e){
      e.preventDefault();
      toggleFullscreen();
    });
    if(!v._tatapFsHooked){
      v._tatapFsHooked=true;
      var origFs=v.requestFullscreen||v.webkitRequestFullscreen||v.mozRequestFullScreen||v.msRequestFullscreen;
      var fsHandler=function(options){
        var stage=document.querySelector(".ambient-stage");
        if(stage&&(stage.requestFullscreen||stage.webkitRequestFullscreen)){
          var p;
          try{
            if(stage.requestFullscreen)p=stage.requestFullscreen(options);
            else if(stage.webkitRequestFullscreen)p=stage.webkitRequestFullscreen(options);
            if(p&&p.catch){
              return p.catch(function(){
                if(origFs)return origFs.call(v,options);
                if(v.webkitEnterFullscreen)try{v.webkitEnterFullscreen();}catch(e){}
              });
            }
            return p;
          }catch(e){
            if(origFs)return origFs.call(v,options);
            if(v.webkitEnterFullscreen)try{v.webkitEnterFullscreen();}catch(err){}
          }
        }
        if(origFs)return origFs.call(v,options);
        if(v.webkitEnterFullscreen)try{v.webkitEnterFullscreen();}catch(e){}
      };
      if(v.requestFullscreen)v.requestFullscreen=fsHandler;
      if(v.webkitRequestFullscreen)v.webkitRequestFullscreen=fsHandler;
      if(v.mozRequestFullScreen)v.mozRequestFullScreen=fsHandler;
      if(v.msRequestFullscreen)v.msRequestFullscreen=fsHandler;
    }
  }
  document.addEventListener("fullscreenchange",syncFullscreenSubtitles);
  document.addEventListener("webkitfullscreenchange",syncFullscreenSubtitles);
  document.addEventListener("mozfullscreenchange",syncFullscreenSubtitles);
  document.addEventListener("MSFullscreenChange",syncFullscreenSubtitles);
  var pmFs=$("pm-fs");
  if(pmFs)pmFs.addEventListener("click",toggleFullscreen);
  var skipBtn=$("pm-skip-btn");
  if(skipBtn)skipBtn.addEventListener("click",doSkip);
  renderSourceUI();
  var sbSrc=$("sb-source");
  if(sbSrc) sbSrc.addEventListener("click",function(){switchSource();});
  var tmSrc=$("tm-source-btn");
  if(tmSrc) tmSrc.addEventListener("click",function(){switchSource();});
  // Muat preferensi subtitle dari server (sub_lang). Kalau server gagal,
  // fallback ke default 'English' yang sudah di-set di var cur.
  if(window.Tatap&&window.Tatap.getSettings){
    window.Tatap.getSettings().then(function(r){
      if(r&&r.success&&r.data){
        if(r.data.sub_lang) cur.subLang=r.data.sub_lang;
        if(r.data.quality) cur.quality=r.data.quality;
        if(r.data.mode) {cur.mode=r.data.mode; syncSeg();}
        if(r.data.preferred_source) {cur.source=r.data.preferred_source; renderSourceUI();}
        if(r.data.auto_skip !== undefined) {
          cur.autoSkip = !!r.data.auto_skip;
          window.settings.autoSkip = cur.autoSkip;
        }
      }
    }).catch(function(){});
  }
  document.querySelectorAll("#mode-seg button").forEach(function(b){
    b.addEventListener("click",function(){
      document.querySelectorAll("#mode-seg button").forEach(function(x){x.classList.remove("active");});
      b.classList.add("active");cur.mode=b.getAttribute("data-mode");loadEps();
    });
  });
  document.querySelectorAll("#quality-seg button").forEach(function(b){
    b.addEventListener("click",function(){
      document.querySelectorAll("#quality-seg button").forEach(function(x){x.classList.remove("active");});
      b.classList.add("active");cur.quality=b.getAttribute("data-q");
    });
  });
  var tmClose = $("tm-close");
  if(tmClose){
    tmClose.addEventListener("click",function(){
      cur.playToken = ++_playTokenCounter;
      closeTitle();
    });
  }
  var btnBack = $("detail-btn-back");
  if(btnBack){
    btnBack.addEventListener("click",function(){
      cur.playToken = ++_playTokenCounter;
      closeTitle();
    });
  }
  var btnQuick = $("btn-quick-play");
  if(btnQuick){
    btnQuick.addEventListener("click",function(){
      var ep = cur.lastWatchedEp || 1;
      openPlayer(ep);
    });
  }
  var tmBmBtn=$("tm-bookmark-btn");
  if(tmBmBtn) tmBmBtn.addEventListener("click",toggleModalBookmark);
  var tmModal = $("title-modal");
  if(tmModal){
    tmModal.addEventListener("click",function(e){
      if(e.target===this){
        cur.playToken = ++_playTokenCounter;
        closeTitle();
      }
    });
  }
  $("pm-close").addEventListener("click",closePlayer);
  $("player-modal").addEventListener("click",function(e){
    if(Date.now() - (cur.playerOpenedAt || 0) < 500) return;
    if(e.target===this) closePlayer();
  });
  $("pm-prev").addEventListener("click",function(){stepEp(-1);});
  $("pm-next").addEventListener("click",function(){stepEp(1);});
  $("pm-mpv").addEventListener("click",playMPV);
  var qSel=$("pm-quality-select");
  if(qSel){
    qSel.addEventListener("change",function(){
      if(!TvNavigationManager.isTvMode()){ try { this.blur(); } catch(_){} }
      switchQ(this.value);
    });
  }
  var spdSel=$("pm-speed-select");
  if(spdSel){
    spdSel.addEventListener("change",function(){
      if(!TvNavigationManager.isTvMode()){ try { this.blur(); } catch(_){} }
      setPlaySpeed(parseFloat(this.value), true);
    });
  }
  startAmbient();
  renderContinue();

  // Listener Drawer Navigation & Update Modal
  var btnDrawer = $("btn-drawer");
  if(btnDrawer) btnDrawer.addEventListener("click", openDrawer);
  var btnDrawerHead = $("btn-drawer-head");
  function closePopover(){
    var pop = $("apple-options-popover");
    if(pop && !pop.classList.contains("hidden")){
      pop.classList.add("hidden");
      if(window.TatapSfx) TatapSfx.play("back");
    }
  }
  if(btnDrawerHead){
    btnDrawerHead.addEventListener("click", function(e){
      e.stopPropagation();
      if(window.innerWidth >= 769){
        var pop = $("apple-options-popover");
        if(pop){
          var isHidden = pop.classList.contains("hidden");
          pop.classList.toggle("hidden");
          if(window.TatapSfx) TatapSfx.play(isHidden ? "select" : "back");
        }
      } else {
        openDrawer();
      }
    });
  }
  document.addEventListener("click", function(e){
    var pop = $("apple-options-popover");
    if(pop && !pop.classList.contains("hidden")){
      if(!pop.contains(e.target) && e.target !== btnDrawerHead && !(btnDrawerHead && btnDrawerHead.contains(e.target))){
        pop.classList.add("hidden");
        if(window.TatapSfx) TatapSfx.play("back");
      }
    }
  });

  // Apple Options Popover button listeners
  var popCatFilter = $("pop-catalog-filter");
  if(popCatFilter) popCatFilter.addEventListener("click", function(){
    closePopover();
    if(window.Tui && window.Tui.openCatalogFilterModal) window.Tui.openCatalogFilterModal();
  });
  var popGenre = $("pop-genre-filter");
  if(popGenre) popGenre.addEventListener("click", function(){
    closePopover();
    if(window.Tui && window.Tui.openGenreModal) window.Tui.openGenreModal();
  });
  var popSafe = $("pop-toggle-safemode");
  if(popSafe) popSafe.addEventListener("click", function(){
    closePopover();
    var en = TatapSafeMode.toggle();
    if(window.TatapSfx) TatapSfx.play("select");
    var label = en ? "Aktif (Filter Dewasa)" : "Nonaktif (Semua Konten Non-Hentai)";
    toast("Mode Aman: " + label, 1500);
    if(window.Tui && window.Tui.loadView) window.Tui.loadView();
  });
  var popSrc = $("pop-switch-source");
  if(popSrc) popSrc.addEventListener("click", function(){
    closePopover();
    switchSource();
  });
  var popTheme = $("pop-toggle-theme");
  if(popTheme) popTheme.addEventListener("click", function(){
    closePopover();
    var t = TatapTheme.toggle();
    toast(t === "light" ? "Mode Terang Aktif" : "Mode Gelap Aktif", 1200);
  });
  var popSfx = $("pop-toggle-sfx");
  if(popSfx) popSfx.addEventListener("click", function(){
    closePopover();
    var en = TatapSfx.toggle();
    if(en) TatapSfx.play("select");
    toast("Efek Suara UI (PS5): " + (en ? "Aktif" : "Mati"), 1200);
  });
  var popUpdate = $("pop-update");
  if(popUpdate) popUpdate.addEventListener("click", function(){
    closePopover();
    checkForUpdate(true);
  });
  var popHelp = $("pop-help");
  if(popHelp) popHelp.addEventListener("click", function(){
    closePopover();
    var ho = $("help-overlay");
    if(ho) ho.classList.remove("hidden");
    var hb = $("help-body");
    if(hb && window.Tui && typeof window.Tui.cmdUsage === "function") hb.textContent = window.Tui.cmdUsage();
  });

  // Global ⌘K / Ctrl+K spotlight shortcut & ⌘T theme toggle
  window.addEventListener("keydown", function(e){
    if((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k"){
      e.preventDefault();
      var sm = $("spotlight-modal");
      if(sm && !sm.classList.contains("hidden")) closeSpotlight();
      else openSpotlight();
    } else if((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "t"){
      e.preventDefault();
      var t = TatapTheme.toggle();
      toast(t === "light" ? "Mode Terang Aktif" : "Mode Gelap Aktif", 1200);
    } else if(e.key === "Escape"){
      closePopover();
      var ssm = $("sub-style-modal");
      if(ssm && !ssm.classList.contains("hidden")) closeSubStyleModal();
    }
  });

  var btnDrawerClose = $("drawer-close");
  if(btnDrawerClose) btnDrawerClose.addEventListener("click", closeDrawer);
  var drawerBackdrop = $("drawer-backdrop");
  if(drawerBackdrop) drawerBackdrop.addEventListener("click", closeDrawer);

  // Navigasi menu di dalam Drawer
  document.querySelectorAll(".drawer-item[data-view]").forEach(function(b){
    b.addEventListener("click", function(){
      var v = b.getAttribute("data-view");
      closeDrawer();
      if(window.Tui && window.Tui.setView){
        window.Tui.setView(v);
      }
    });
  });

  // Navigasi tab bar Shiru di Header Atas
  document.querySelectorAll(".nav-tab-btn[data-view]").forEach(function(b){
    b.addEventListener("click", function(){
      var v = b.getAttribute("data-view");
      if(window.Tui && window.Tui.setView){
        window.Tui.setView(v);
      }
    });
  });

  // Interaktivitas Brand Logo Header (kembali ke Musim Ini)
  var headBrand = $("head-brand");
  if(headBrand){
    headBrand.addEventListener("click", function(){
      if(window.Tui && window.Tui.setView){
        window.Tui.setView("musim");
      }
      window.scrollTo({top:0, behavior:"smooth"});
    });
    headBrand.addEventListener("keydown", function(e){
      if(e.key === "Enter" || e.key === " "){
        e.preventDefault();
        headBrand.click();
      }
    });
  }

  // Desktop instant search interactivity
  var cmdInput = $("cmd");
  if(cmdInput && !(window.TvNavigationManager && window.TvNavigationManager.isTvMode())){
    cmdInput.removeAttribute("readonly");
    cmdInput.addEventListener("click", function(e){
      e.stopPropagation();
      cmdInput.removeAttribute("readonly");
      cmdInput.focus();
    });
  }

  var drawerGenre = $("drawer-genre");
  if(drawerGenre) drawerGenre.addEventListener("click", function(){
    closeDrawer();
    if(window.Tui && window.Tui.openGenreModal) window.Tui.openGenreModal();
  });

  var drawerCatFilter = $("drawer-catalog-filter");
  if(drawerCatFilter) drawerCatFilter.addEventListener("click", function(){
    closeDrawer();
    if(window.Tui && window.Tui.openCatalogFilterModal) window.Tui.openCatalogFilterModal();
  });

  var drawerSrc = $("drawer-switch-source");
  if(drawerSrc) drawerSrc.addEventListener("click", function(){
    switchSource();
  });

  var drawerHelp = $("drawer-help");
  if(drawerHelp) drawerHelp.addEventListener("click", function(){
    closeDrawer();
    var ho = $("help-overlay");
    if(ho) ho.classList.remove("hidden");
    var hb = $("help-body");
    if(hb && window.Tui) hb.textContent = window.Tui.cmdUsage();
  });

  var drawerSafe = $("drawer-toggle-safemode");
  if(drawerSafe) drawerSafe.addEventListener("click", function(){
    closeDrawer();
    var en = TatapSafeMode.toggle();
    if(window.TatapSfx) TatapSfx.play("select");
    var label = en ? "Aktif (Filter Dewasa)" : "Nonaktif (Semua Konten Non-Hentai)";
    toast("Mode Aman: " + label, 1500);
    if(window.Tui && window.Tui.loadView) window.Tui.loadView();
  });

  var drawerToggleTheme = $("drawer-toggle-theme");
  if(drawerToggleTheme) drawerToggleTheme.addEventListener("click", function(){
    closeDrawer();
    var t = TatapTheme.toggle();
    toast(t === "light" ? "Mode Terang Aktif" : "Mode Gelap Aktif", 1200);
  });

  var drawerSfx = $("drawer-toggle-sfx");
  if(drawerSfx) drawerSfx.addEventListener("click", function(){
    closeDrawer();
    var en = TatapSfx.toggle();
    if(en) TatapSfx.play("select");
    toast("Efek Suara UI (PS5): " + (en ? "Aktif" : "Mati"), 1200);
  });

  var drawerUpd = $("drawer-update");
  if(drawerUpd) drawerUpd.addEventListener("click", function(){
    closeDrawer();
    checkForUpdate(true);
  });

  var beRetry = $("be-retry-btn");
  if(beRetry) beRetry.addEventListener("click", manualRetryBackend);
  var beCopy = $("be-copy-debug-btn");
  if(beCopy) beCopy.addEventListener("click", copyBackendDebugInfo);

  var umClose = $("um-close");
  if(umClose) umClose.addEventListener("click", closeUpdateModal);
  var um = $("update-modal");
  if(um) um.addEventListener("click", function(e){
    if(e.target === um) closeUpdateModal();
  });

  // AI Settings Modal & Drawer Triggers
  var drawerAi = $("drawer-ai-settings");
  if(drawerAi) drawerAi.addEventListener("click", function(){
    closeDrawer();
    openAiSettingsModal();
  });
  var pmAiBtn = $("pm-ai-settings");
  if(pmAiBtn) pmAiBtn.addEventListener("click", function(){
    openAiSettingsModal();
  });
  var aiClose = $("ai-modal-close");
  if(aiClose) aiClose.addEventListener("click", closeAiSettingsModal);
  var aiCancel = $("ai-btn-cancel");
  if(aiCancel) aiCancel.addEventListener("click", closeAiSettingsModal);
  var aiModal = $("ai-settings-modal");
  if(aiModal) aiModal.addEventListener("click", function(e){
    if(e.target === aiModal) closeAiSettingsModal();
  });

  // AI Presets
  document.querySelectorAll(".ai-presets-row .btn-preset").forEach(function(btn){
    btn.addEventListener("click", function(){
      var prov = btn.getAttribute("data-provider");
      if(prov === "gemini"){
        if($("ai-input-model")) $("ai-input-model").value = "gemini-2.0-flash";
        if($("ai-input-url")) $("ai-input-url").value = "https://generativelanguage.googleapis.com/v1beta/openai";
      } else if(prov === "groq"){
        if($("ai-input-model")) $("ai-input-model").value = "llama-3.3-70b-versatile";
        if($("ai-input-url")) $("ai-input-url").value = "https://api.groq.com/openai/v1";
      } else if(prov === "ollama"){
        if($("ai-input-model")) $("ai-input-model").value = "gpt-oss:20b";
        if($("ai-input-url")) $("ai-input-url").value = "https://ollama.com/v1";
      } else if(prov === "openai"){
        if($("ai-input-model")) $("ai-input-model").value = "gpt-4o-mini";
        if($("ai-input-url")) $("ai-input-url").value = "https://api.openai.com/v1";
      }
    });
  });

  // Custom Prompt Templates
  var tplCasual = $("btn-tpl-casual");
  if(tplCasual) tplCasual.addEventListener("click", function(){
    if($("ai-input-prompt")) $("ai-input-prompt").value = "Gaya bahasa santai & casual anak muda (gunakan aku-kamu / gue-lu secara luwes sesuai karakter). Pertahankan istilah anime populer.";
  });
  var tplFormal = $("btn-tpl-formal");
  if(tplFormal) tplFormal.addEventListener("click", function(){
    if($("ai-input-prompt")) $("ai-input-prompt").value = "Gunakan bahasa Indonesia baku, sopan, dan terstruktur baik. Hindari bahasa gaul/slang.";
  });
  var tplWibu = $("btn-tpl-wibu");
  if(tplWibu) tplWibu.addEventListener("click", function(){
    if($("ai-input-prompt")) $("ai-input-prompt").value = "Pertahankan honorifik bahasa Jepang (-san, -kun, -chan, Senpai, Sensei, Sama), nama jurus/sihir, dan istilah anime tanpa diterjemahkan.";
  });
  var tplReset = $("btn-tpl-reset");
  if(tplReset) tplReset.addEventListener("click", function(){
    if($("ai-input-prompt")) $("ai-input-prompt").value = "";
  });

  // Reset API key
  var aiResetKey = $("ai-btn-reset-key");
  if(aiResetKey) aiResetKey.addEventListener("click", function(){
    window.Tatap.setSetting({ translate_apikey: "" }).then(function(){
      if($("ai-input-key")) $("ai-input-key").value = "";
      if($("ai-status-prov")) {
        $("ai-status-prov").textContent = "Belum Disetel";
        $("ai-status-prov").className = "badge-status ongoing";
      }
      toast("API Key AI berhasil dihapus", 2000);
    });
  });

  // Save AI Settings
  var aiSave = $("ai-btn-save");
  if(aiSave) aiSave.addEventListener("click", function(){
    var key = ($("ai-input-key") ? $("ai-input-key").value.trim() : "");
    var model = ($("ai-input-model") ? $("ai-input-model").value.trim() : "");
    var url = ($("ai-input-url") ? $("ai-input-url").value.trim() : "");
    var prompt = ($("ai-input-prompt") ? $("ai-input-prompt").value.trim() : "");

    var payload = {
      translate_apikey: key,
      translate_model: model || "gemini-2.0-flash",
      translate_apiurl: url || "https://generativelanguage.googleapis.com/v1beta/openai",
      translate_custom_prompt: prompt
    };

    window.Tatap.setSetting(payload).then(function(){
      toast("Pengaturan AI Fansub berhasil disimpan!", 2500);
      closeAiSettingsModal();
      if(!$("player-modal").classList.contains("hidden") && cur.subLang === "Indonesian (AI)"){
        cur._subPrefetch = null;
        if(cur.activeSub){
          switchSubtitleTrack(cur.activeSub, "id");
        }
      }
    }).catch(function(err){
      toast("Gagal menyimpan setelan: " + err, 3000);
    });
  });

  var rmClose = $("rm-close");
  if(rmClose) rmClose.addEventListener("click", dismissResumeModal);
  var rm = $("resume-modal");
  if(rm) rm.addEventListener("click", function(e){
    if(e.target === rm) dismissResumeModal();
  });

  // Subtitle Styler Modal Events & Interactivity
  var popSubStyle = $("pop-sub-style");
  if(popSubStyle) popSubStyle.addEventListener("click", function(){
    closePopover();
    openSubStyleModal();
  });
  var drawerSubStyle = $("drawer-sub-style");
  if(drawerSubStyle) drawerSubStyle.addEventListener("click", function(){
    closeDrawer();
    openSubStyleModal();
  });
  var subStyleClose = $("sub-style-close");
  if(subStyleClose) subStyleClose.addEventListener("click", cancelSubStyleModal);
  var subStyleCancel = $("btn-sub-cancel-style");
  if(subStyleCancel) subStyleCancel.addEventListener("click", cancelSubStyleModal);
  var subStyleApply = $("btn-sub-apply-style");
  if(subStyleApply) subStyleApply.addEventListener("click", function(){
    _subStyleSnapshot = null;
    closeSubStyleModal();
    if(window.TatapSfx) TatapSfx.play("select");
    toast("Gaya Subtitle Disimpan", 1200, "icon-check");
  });
  var subStyleReset = $("btn-sub-reset-style");
  if(subStyleReset) subStyleReset.addEventListener("click", resetSubStyle);
  var subStyleModal = $("sub-style-modal");
  if(subStyleModal){
    subStyleModal.addEventListener("click", function(e){
      if(e.target === subStyleModal) cancelSubStyleModal();
    });
  }

  document.querySelectorAll(".sub-styler-opt").forEach(function(opt){
    opt.addEventListener("click", function(){
      if(window.TatapSfx) TatapSfx.play("tick");
      if(opt.hasAttribute("data-sub-font")){
        setSubFont(opt.getAttribute("data-sub-font"));
      } else if(opt.hasAttribute("data-sub-bg")){
        setSubBg(opt.getAttribute("data-sub-bg"));
      } else if(opt.hasAttribute("data-sub-color")){
        setSubColor(opt.getAttribute("data-sub-color"));
      } else if(opt.hasAttribute("data-sub-size")){
        setSubSize(opt.getAttribute("data-sub-size"));
      } else if(opt.hasAttribute("data-sub-pos")){
        setSubPos(opt.getAttribute("data-sub-pos"));
      }
    });
  });

  window.openSubStyleModal = openSubStyleModal;
  window.closeSubStyleModal = closeSubStyleModal;
  window.cancelSubStyleModal = cancelSubStyleModal;
  window.resetSubStyle = resetSubStyle;
  window.setSubFont = setSubFont;
  window.addEventListener("beforeunload", function(){
    recordWatchProgress(true);
  });

  // Global interactive acoustic tick for PS5 tactile feeling
  document.addEventListener("mouseover", function(e){
    var target = e.target;
    if(!target) return;
    var el = target.closest(".poster-card, .nav-tab-btn, .popover-item, .drawer-item, .seg button, .ep, .pager-btn, .header-drawer-btn, .ep-range-chip");
    if(el && window.TatapSfx){
      TatapSfx.play("tick");
    }
  }, { passive: true });

  checkBackendStartup(function(){
    window.Tui.boot();
  }, function(){
    window.Tui.boot();
  });
}

var _autoReconnectTimer = null;

function updateBackendHealth(isOnline){
  var hEl = $("health");
  if(hEl){
    hEl.textContent = isOnline ? "Online" : "Offline";
    hEl.className = "health " + (isOnline ? "ok" : "bad");
  }
  var dHText = $("drawer-health-text");
  if(dHText){
    dHText.textContent = isOnline ? "Online" : "Offline";
  }
}

function startAutoReconnect(){
  if(_autoReconnectTimer) return;
  _autoReconnectTimer = setInterval(function(){
    if(!window.Tatap || !window.Tatap.ping) return;
    window.Tatap.ping().then(function(r){
      if(r && r.success){
        stopAutoReconnect();
        var beOverlay = $("backend-error-overlay");
        if(beOverlay) beOverlay.classList.add("hidden");
        updateBackendHealth(true);
        toast("Backend Tatap terhubung!");
        if(window.Tui && window.Tui.setView){
          window.Tui.setView("katalog");
        }
      }
    }).catch(function(){});
  }, 3000);
}

function stopAutoReconnect(){
  if(_autoReconnectTimer){
    clearInterval(_autoReconnectTimer);
    _autoReconnectTimer = null;
  }
}

function checkBackendStartup(onSuccess, onFail){
  var attempts = 0;
  var maxAttempts = 5;
  var intervalMs = 600;
  var beOverlay = $("backend-error-overlay");
  var beStatusText = $("be-status-text");

  function ping(){
    window.Tatap.ping().then(function(r){
      if(r && r.success){
        stopAutoReconnect();
        if(beOverlay) beOverlay.classList.add("hidden");
        updateBackendHealth(true);
        if(onSuccess) onSuccess();
      } else {
        retryOrFail();
      }
    }).catch(function(err){
      retryOrFail(err);
    });
  }

  function retryOrFail(err){
    attempts++;
    if(attempts < maxAttempts){
      if(beStatusText) beStatusText.textContent = "Menunggu backend (" + attempts + "/" + maxAttempts + ")...";
      setTimeout(ping, intervalMs);
    } else {
      updateBackendHealth(false);
      if(beOverlay) beOverlay.classList.remove("hidden");
      if(beStatusText) beStatusText.textContent = "Gagal terhubung ke localhost:8767. Memeriksa ulang otomatis setiap 3 detik...";
      startAutoReconnect();
      if(onFail) onFail(err);
    }
  }

  ping();
}

function manualRetryBackend(){
  var btn = $("be-retry-btn");
  var statusText = $("be-status-text");
  if(btn) btn.disabled = true;
  if(statusText) statusText.textContent = "Menghubungi http://127.0.0.1:8767/api/ping...";
  window.Tatap.ping().then(function(r){
    if(btn) btn.disabled = false;
    if(r && r.success){
      stopAutoReconnect();
      var beOverlay = $("backend-error-overlay");
      if(beOverlay) beOverlay.classList.add("hidden");
      updateBackendHealth(true);
      toast("Backend berhasil terhubung!");
      if(window.Tui && window.Tui.setView){
        window.Tui.setView("katalog");
      }
    } else {
      if(statusText) statusText.textContent = "Backend merespons error. Mencoba lagi...";
    }
  }).catch(function(e){
    if(btn) btn.disabled = false;
    if(statusText) statusText.textContent = "Gagal terhubung: " + (e && e.message || "Connection refused") + ". Mencoba lagi dalam 3 detik...";
    startAutoReconnect();
  });
}

function copyBackendDebugInfo(){
  var brandEl = $("brand-ver");
  var ver = brandEl ? brandEl.textContent : "v2.10.0";
  var apiHost = typeof apiBase === "function" ? (apiBase() || "http://127.0.0.1:8767 (origin)") : "http://127.0.0.1:8767";
  var info = [
    "=== Tatap Backend Debug Info ===",
    "Version: " + ver,
    "Location: " + window.location.href,
    "API Base: " + apiHost,
    "User Agent: " + navigator.userAgent,
    "Time: " + new Date().toISOString(),
    "Endpoint Tested: /api/ping",
    "Status: Connection refused or timeout"
  ].join("\n");
  try{
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(info).then(function(){
        toast("Info diagnostik disalin ke clipboard!");
      });
    } else {
      toast("Clipboard API tidak tersedia.");
      console.warn(info);
    }
  }catch(_){
    toast("Gagal menyalin, periksa console log.");
    console.error(info);
  }
}

document.addEventListener("enterpictureinpicture", function(){
  if(typeof syncNativeTextTrack === "function") syncNativeTextTrack(cur._rawVtt, cur.cues, cur.subLang, true);
  if(typeof syncPipSubtitles === "function") syncPipSubtitles(true);
});
document.addEventListener("leavepictureinpicture", function(){
  if(typeof syncPipSubtitles === "function") syncPipSubtitles(false);
});

// Clean macOS texture mode: random wallpaper disabled
function updateMainWallpaper(){ /* no-op: clean mac texture active */ }
window.updateMainWallpaper = updateMainWallpaper;

init();