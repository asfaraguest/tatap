var cur = {slug:"", title:"", ep:1, mode:"sub", quality:"best", res:null, eps:[], watched:{}, lastWatchedEp:null,
            subLang:"English",    // preferensi bahasa user dari /api/settings
            activeSub:null,       // URL track subtitle yang sedang aktif (live switch)
            cues:[],              // cue subtitle hasil parse VTT (render overlay milik app)
            subSize:"m",          // ukuran subtitle overlay: s|m|l
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
  if(notify){
    var signStr = val > 0 ? "+" : "";
    toast("Sinkronisasi Subtitle: " + signStr + val.toFixed(2) + " detik", 1500);
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
  if(v){
    try {
      v.playbackRate = currentPlaybackSpeed;
    } catch(e){}
  }
  var sel = $("pm-speed-select");
  if(sel){
    sel.value = String(currentPlaybackSpeed);
  }
  if(notify){
    toast("Kecepatan: " + currentPlaybackSpeed + "x");
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
function toast(msg,ms){
  $("toast-msg").textContent=msg;
  $("toast").classList.remove("hidden");
  clearTimeout(window._toastT);
  window._toastT=setTimeout(function(){$("toast").classList.add("hidden");},ms||2200);
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

    // Level 2: Close active Dialog / Sub-Modal (Resume, Settings, Genre, Filter, Drawer)
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
    if(isPlayerOpen && playerState === PLAYER_IDLE){
      if(e) e.preventDefault();
      if(typeof App !== "undefined" && App.closePlayer) App.closePlayer();
      else pm.classList.add("hidden");
      return true;
    }

    // Level 5: Close Detail Anime to Main Grid
    var tm = $("title-modal");
    if(tm && !tm.classList.contains("hidden")){
      if(e) e.preventDefault();
      if(typeof App !== "undefined" && App.closeTitle) App.closeTitle();
      else tm.classList.add("hidden");
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

function openTitle(slug,title,poster,type,epsCounter,meta){
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
  $("tm-sub").textContent=slug;
  $("tm-eyebrow").textContent="DETAIL ANIME";
  $("tm-count").textContent="memuat...";
  $("tm-eps").innerHTML="";
  $("ep-filter").value="";
  var sBar=$("tm-seasons");if(sBar)sBar.classList.add("hidden");
  var sChips=$("tm-seasons-chips");if(sChips)sChips.innerHTML="";
  renderDetailMeta(meta);
  updateBookmarkBtn(false);
  checkModalBookmark(slug);
  $("title-modal").classList.remove("hidden");
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
        var cls="season-chip";
        var icon='<svg class="ui-icon"><use href="#icon-tv"/></svg>';
        if(rel.format==="MOVIE"){cls+=" movie";icon='<svg class="ui-icon"><use href="#icon-film"/></svg>';}
        else if(rel.format==="OVA"||rel.format==="SPECIAL"||rel.format==="ONA"){cls+=" special";icon='<svg class="ui-icon"><use href="#icon-disc"/></svg>';}
        else if(rel.relation==="PREQUEL"){cls+=" prequel";icon='<svg class="ui-icon"><use href="#icon-step-prev"/></svg>';}
        else if(rel.relation==="SEQUEL"){cls+=" sequel";icon='<svg class="ui-icon"><use href="#icon-step-next"/></svg>';}
        b.className=cls;
        b.title=rel.title+(rel.year?" ("+rel.year+")":"");
        b.innerHTML="<span>"+icon+"</span> <b>"+rel.label+"</b>: "+esc(rel.title);
        b.addEventListener("click",function(e){
          if(e)e.stopPropagation();
          openTitle(rel.slug,rel.title);
        });
        sChips.appendChild(b);
      })(rels[i]);
    }
    if(count>0){
      sBar.classList.remove("hidden");
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
  ranges.push({start: 1, end: total, label: "Semua (" + total + ")", isAll: true});

  if(!cur.activeEpRange){
    cur.activeEpRange = ranges[0];
    if(lastWatchedEp > 0){
      for(var r = 0; r < ranges.length - 1; r++){
        if(lastWatchedEp >= ranges[r].start && lastWatchedEp <= ranges[r].end){
          cur.activeEpRange = ranges[r];
          break;
        }
      }
    }
  }

  ranges.forEach(function(rng){
    var btn = document.createElement("button");
    btn.className = "ep-range-chip" + (cur.activeEpRange && cur.activeEpRange.label === rng.label ? " active" : "");
    btn.textContent = rng.label;
    btn.addEventListener("click", function(){
      cur.activeEpRange = rng;
      renderEpRanges();
      renderEpGrid();
    });
    bar.appendChild(btn);
  });
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

  window.Tatap.episodes(thisSlug).then(function(r){
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
    }
    var respPoster = (r.data.poster || (r.data.detail && r.data.detail.poster)) || "";
    if(!cur.poster && respPoster){
      cur.poster = respPoster;
    }
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
      $("tm-count").textContent = countLabel();
      renderEpRanges();
      renderEpGrid();
    }).catch(function(){
      if(thisSlug !== cur.slug) return;
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
  var useRange = !f && cur.activeEpRange && !cur.activeEpRange.isAll;

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
  $("title-modal").classList.add("hidden");
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
  var v = $("vid");
  if(!v || !cur.slug || !cur.ep) return;
  var now = Date.now();
  if(!force && (now - _lastProgressSaveTime < 5000)) return;
  _lastProgressSaveTime = now;
  var curPos = Math.floor(v.currentTime || 0);
  var dur = Math.floor(v.duration || 0);
  if(curPos <= 0 && !force) return;
  window.Tatap.saveProgress(cur.slug, cur.ep, curPos, dur).then(function(){
    renderContinue();
  }).catch(function(){});
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
    var tm = $("title-modal");
    if(tm && tm.classList.contains("hidden")){
      openTitle(savedSlug, savedTitle, savedPoster, savedType, savedCounter);
    } else {
      if(tm) tm.classList.remove("hidden");
      renderEpGrid();
    }
  }
}

function openPlayer(ep, resumeTime, forceRefresh){
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
  closeTitle();
  closeResumeModal();
  $("player-modal").classList.remove("hidden");
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
  window.Tatap.searchOpenSubtitles(cur.title, cur.slug, cur.ep, "id").then(function(res){
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
function syncFullscreenSubtitles(){
  var isFs = isFullscreenActive();
  if(typeof window.tatap_set_fullscreen === "function"){
    try{ window.tatap_set_fullscreen(isFs); }catch(_){}
  }
  var v=$("vid");
  if(!v||!v.textTracks)return;
  var isVidFs=isVideoFullscreen();
  for(var i=0;i<v.textTracks.length;i++){
    var t=v.textTracks[i];
    if(t.label&&t.label.indexOf("Tatap")>=0){
      t.mode=(isVidFs && !isDesktopEnv())?"showing":"hidden";
    }
  }
  paintCue();
}
function syncNativeTextTrack(vttText, cues, langCode){
  var v=$("vid");
  if(!v)return;

  var oldTracks=v.querySelectorAll("track.tatap-sub-track");
  for(var i=0;i<oldTracks.length;i++){
    var trk=oldTracks[i];
    if(trk.src&&trk.src.indexOf("blob:")===0){
      try{URL.revokeObjectURL(trk.src);}catch(e){}
    }
    if(trk.parentNode)trk.parentNode.removeChild(trk);
  }

  if(v.textTracks){
    for(var j=0;j<v.textTracks.length;j++){
      var tt = v.textTracks[j];
      if(tt.label&&tt.label.indexOf("Tatap")>=0){
        tt.mode="disabled";
        if(tt.cues){
          for(var ci=tt.cues.length-1;ci>=0;ci--){
            try{tt.removeCue(tt.cues[ci]);}catch(_){}
          }
        }
      }
    }
  }

  if(!vttText&&(!cues||!cues.length))return;

  try{
    var trackEl=document.createElement("track");
    trackEl.className="tatap-sub-track";
    trackEl.kind="subtitles";
    trackEl.label="Tatap Subtitle";
    trackEl.srclang=langCode||"id";
    trackEl.default=false;

    if(vttText&&window.Blob&&window.URL&&window.URL.createObjectURL){
      var blob=new Blob([vttText],{type:"text/vtt"});
      trackEl.src=URL.createObjectURL(blob);
    }

    var applyMode=function(){
      if(trackEl.track){
        trackEl.track.mode=(isVideoFullscreen() && !isDesktopEnv())?"showing":"hidden";
      }
    };

    trackEl.addEventListener("load",applyMode);
    v.appendChild(trackEl);
    applyMode();

    setTimeout(function(){
      if(trackEl.track&&(!trackEl.track.cues||trackEl.track.cues.length===0)&&cues&&cues.length&&window.VTTCue){
        for(var k=0;k<cues.length;k++){
          var c=cues[k];
          var plain=c.plain||(c.html?c.html.replace(/<br\s*\/?>/gi,"\n").replace(/<[^>]+>/g,""):"");
          try{
            trackEl.track.addCue(new VTTCue(c.start,c.end,plain));
          }catch(e){}
        }
        applyMode();
      }
    },200);
  }catch(err){
    console.warn("syncNativeTextTrack error:",err);
  }
}
function toggleFullscreen(){
  var v=$("vid");
  var stage=document.querySelector(".ambient-stage");
  var fsEl=document.fullscreenElement||document.webkitFullscreenElement||document.mozFullScreenElement||document.msFullscreenElement;
  var isVideoFs=(v&&v.webkitDisplayingFullscreen);

  if(fsEl||isVideoFs){
    if(document.exitFullscreen){
      try{document.exitFullscreen().catch(function(){});}catch(e){}
    }else if(document.webkitExitFullscreen){
      try{document.webkitExitFullscreen();}catch(e){}
    }else if(document.mozCancelFullScreen){
      try{document.mozCancelFullScreen();}catch(e){}
    }else if(document.msExitFullscreen){
      try{document.msExitFullscreen();}catch(e){}
    }
    if(v&&v.webkitExitFullscreen&&v.webkitDisplayingFullscreen){
      try{v.webkitExitFullscreen();}catch(e){}
    }
    if(typeof window.tatap_set_fullscreen === "function"){
      try{ window.tatap_set_fullscreen(false); }catch(_){}
    }
    return;
  }

  // iOS Safari video native fullscreen
  if(v&&v.webkitEnterFullscreen&&(!stage||!stage.requestFullscreen)){
    try{
      v.webkitEnterFullscreen();
      return;
    }catch(err){
      console.warn("webkitEnterFullscreen error:",err);
    }
  }

  var enterVideoFs=function(){
    if(!v)return;
    if(v.requestFullscreen){
      try{v.requestFullscreen().catch(function(){if(v.webkitEnterFullscreen)v.webkitEnterFullscreen();});}catch(e){if(v.webkitEnterFullscreen)v.webkitEnterFullscreen();}
    }else if(v.webkitRequestFullscreen){
      try{v.webkitRequestFullscreen();}catch(e){if(v.webkitEnterFullscreen)v.webkitEnterFullscreen();}
    }else if(v.mozRequestFullScreen){
      try{v.mozRequestFullScreen();}catch(e){}
    }else if(v.msRequestFullscreen){
      try{v.msRequestFullscreen();}catch(e){}
    }else if(v.webkitEnterFullscreen){
      try{v.webkitEnterFullscreen();}catch(e){}
    }
  };

  if(stage&&(stage.requestFullscreen||stage.webkitRequestFullscreen||stage.mozRequestFullScreen||stage.msRequestFullscreen)){
    var p;
    try{
      if(stage.requestFullscreen){
        p=stage.requestFullscreen();
      }else if(stage.webkitRequestFullscreen){
        p=stage.webkitRequestFullscreen();
      }else if(stage.mozRequestFullScreen){
        p=stage.mozRequestFullScreen();
      }else if(stage.msRequestFullscreen){
        p=stage.msRequestFullscreen();
      }
      if(p&&p.catch){
        p.catch(function(err){
          console.warn("stage.requestFullscreen rejected, falling back to video:",err);
          enterVideoFs();
        });
      }
    }catch(err){
      console.warn("stage fullscreen exception, falling back to video:",err);
      enterVideoFs();
    }
  }else{
    enterVideoFs();
  }
}
function paintCue(){
  var box=$("pm-subs-overlay");
  var v=$("vid");
  if(!box||!v)return;
  var s=box.querySelector("span");
  if(!s)return;
  if($("player-modal").classList.contains("hidden")){s.innerHTML="";return;}
  var t=v.currentTime||0;
  var subTime = t - (cur.subDelay || 0.0);
  if(isVideoFullscreen() && !isDesktopEnv()){
    if(s._last!==""){s.innerHTML="";s._last="";}
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
    if(s._last!==html){s.innerHTML=html;s._last=html;}
  }
  checkSkipTimes(t);
}

function checkSkipTimes(currentTime){
  var btn=$("pm-skip-btn");
  var label=$("pm-skip-label");
  if(!btn){return;}
  var v=$("vid");
  var intro=cur.intro;
  var outro=cur.outro;
  var isAutoSkip = !!(window.settings && window.settings.autoSkip !== undefined ? window.settings.autoSkip : cur.autoSkip);

  var inIntro=(intro && intro.end > intro.start && intro.end > 0 && currentTime >= intro.start && currentTime < (intro.end - 0.5));
  var inOutro=(outro && outro.end > outro.start && outro.end > 0 && currentTime >= outro.start && currentTime < (outro.end - 0.5));

  if(inIntro){
    cur.activeSkipTarget = Math.min((v && v.duration) || Infinity, intro.end + 0.5);
    if(isAutoSkip && !cur.hasAutoSkippedIntro){
      cur.hasAutoSkippedIntro = true;
      if(v){
        v.currentTime = cur.activeSkipTarget;
        btn.classList.add("hidden");
        cur.activeSkipTarget = 0;
        toast("⏩ Lewati Opening otomatis", 1500);
        return;
      }
    }
    if(label) label.textContent = "Lewati Opening (S)";
    btn.classList.remove("hidden");
  }else if(inOutro){
    cur.activeSkipTarget = Math.min((v && v.duration) || Infinity, outro.end + 0.5);
    if(isAutoSkip && !cur.hasAutoSkippedOutro){
      cur.hasAutoSkippedOutro = true;
      if(v){
        v.currentTime = cur.activeSkipTarget;
        btn.classList.add("hidden");
        cur.activeSkipTarget = 0;
        toast("⏩ Lewati Ending otomatis", 1500);
        return;
      }
    }
    if(label) label.textContent = "Lewati Ending (S)";
    btn.classList.remove("hidden");
  }else{
    cur.activeSkipTarget = 0;
    btn.classList.add("hidden");
  }
}

function doSkip(){
  if(cur.activeSkipTarget && cur.activeSkipTarget > 0){
    var v=$("vid");
    if(v){
      var t = v.currentTime;
      if(cur.intro && t >= cur.intro.start && t < cur.intro.end){
        cur.hasAutoSkippedIntro = true;
      }
      if(cur.outro && t >= cur.outro.start && t < cur.outro.end){
        cur.hasAutoSkippedOutro = true;
      }
      v.currentTime = cur.activeSkipTarget;
      var btn=$("pm-skip-btn");
      if(btn) btn.classList.add("hidden");
      toast("⏩ Melompat ke "+formatTime(v.currentTime), 1500);
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
    qs += "&title=" + encodeURIComponent(cur.title || "") + "&slug=" + encodeURIComponent(cur.slug || "") + "&ep=" + encodeURIComponent(cur.ep || 1);
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
        }else if(res.tier === "tier3"){
          tierLabel = "MyMemory — kaku";
        }else if(res.tier === "cached"){
          tierLabel = "AI Fansub, tersimpan";
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
                if(uTier === "cached" || uTier === "tier1"){
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
    var v = $("vid");
    if(!stage || !v) return;

    var self = this;

    stage.addEventListener("touchstart", function(e){
      if(e.touches.length !== 1) return;
      var touch = e.touches[0];
      var rect = stage.getBoundingClientRect();
      self.startX = touch.clientX;
      self.startY = touch.clientY;
      self.mode = null;
      self.initVol = v.volume;
      self.initBright = self.currentBright;
      self.initTime = v.currentTime;
    }, {passive: true});

    stage.addEventListener("touchmove", function(e){
      if(e.touches.length !== 1) return;
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
        var dur = v.duration || 1400;
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
      if(self.mode === "seek" && self._targetSeek != null){
        v.currentTime = self._targetSeek;
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
          v.currentTime = Math.max(0, v.currentTime - 10);
          self.triggerRipple("left", "-10s");
        } else if(relX > 0.65){
          v.currentTime = Math.min(v.duration || 99999, v.currentTime + 10);
          self.triggerRipple("right", "+10s");
        } else {
          if(v.paused) v.play(); else v.pause();
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
    if(!v.hasAttribute("controls"))v.setAttribute("controls","");
    show();
  };
  ["mousemove","touchstart","click"].forEach(function(ev){stage.addEventListener(ev,wake,{passive:true});});
  v.addEventListener("play",show);
  v.addEventListener("pause",function(){
    clearTimeout(TvNavigationManager.getHudTimer && TvNavigationManager.getHudTimer());
    v.setAttribute("controls","");
    if(stage) stage.classList.remove("idle");
    if(shell) shell.classList.remove("idle");
    TvNavigationManager.setPlayerState(TvNavigationManager.PLAYER_HUD_ACTIVE);
  });
  v.addEventListener("seeking",show);
  show();
}
function playUrl(url,referrer,sub,subRef,resumeTime,token){
  var pm = $("player-modal");
  var v=$("vid");
  if(!pm || pm.classList.contains("hidden") || (token && cur.playToken !== token)){
    if(window._hls){try{window._hls.destroy();window._hls=null;}catch(e){}}
    if(v){try{v.pause();v.removeAttribute("src");v.load();}catch(e){}}
    return;
  }
  if(v){
    v.muted=false;
    if(v.volume===0) v.volume=1.0;
  }
  var b = (typeof apiBase === "function") ? apiBase() : "";
  var prox=b+"/api/player/video?url="+encodeURIComponent(url)+"&referer="+encodeURIComponent(referrer||"");
  try{
    var m=/^(.*\/)index-(f\d+-v\d+-a\d+)\.m3u8/.exec(url);
    if(m){
      for(var wi=1;wi<=2;wi++){
        (function(n){
          var seg=m[1]+"seg-"+n+"-"+m[2]+".jpg";
          fetch("/api/player/video?url="+encodeURIComponent(seg)+"&referer="+encodeURIComponent(referrer||""),{mode:"no-cors"}).catch(function(){});
        })(wi);
      }
    }
  }catch(e){}
  // Bersihkan <track> lama lalu pasang track subtitle aktif (live switch).
  // Fungsi switchSubtitleTrack() menhandle Off (hapus semua) dan replace.
  var validSub = (typeof sub === "string" && !/^\d+$/.test(sub.trim())) ? sub : null;
  switchSubtitleTrack(validSub);
  $("pm-spinner").classList.remove("hidden");
  $("pm-status").textContent="buffering...";
  var onCan=function(){
    $("pm-spinner").classList.add("hidden");
    if(resumeTime && resumeTime > 0){
      try{v.currentTime = resumeTime;}catch(e){}
    }
  };
  v.addEventListener("canplay",onCan,{once:true});
  var cleanPath = (url || "").split("?")[0].toLowerCase();
  var isSeg = cleanPath.endsWith(".ts") || cleanPath.endsWith(".ts.jpg") || cleanPath.endsWith(".mp4") || cleanPath.endsWith(".aac");
  var isHls = !isSeg && ((url.indexOf(".m3u8") >= 0) || (url.indexOf("format=m3u8") >= 0) || (url.indexOf("/api/hls") >= 0) || (url.indexOf("/hls/playlist") >= 0));
  if(window.Hls&&window.Hls.isSupported()&&isHls){
    if(window._hls){try{window._hls.destroy();}catch(e){}}
    var h=new Hls({
      maxBufferLength:30,
      maxMaxBufferLength:60,
      maxBufferSize:40*1000*1000,
      startLevel:-1,
      capLevelToPlayerSize:true,
      fragLoadingMaxRetry:6,
      manifestLoadingMaxRetry:4,
      levelLoadingMaxRetry:4,
      fragLoadingMaxRetryTimeout:12000,
      backBufferLength:30,
      liveSyncDurationCount:2,
      maxFragLookUpTolerance:0.5,
      nudgeOffset:0.1,
      nudgeMaxRetry:5,
      maxStarvationDelay:4,
      highBufferWatchdogPeriod:2,
      testBandwidth:false,
      progressive:true,
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
    h.on(Hls.Events.FRAG_BUFFERED,function(){
      try{
        var nxt=null;
        if(h.levels&&h.levelDetails&&h.levelDetails.fragments){
          var fr=h.levelDetails.fragments;
          for(var fi=0;fi<fr.length;fi++){if(!fr[fi].loaded){nxt=fr[fi];break;}}
        }
        if(nxt&&nxt.url){
          var fetchTarget = nxt.url;
          if(!fetchTarget.startsWith("/api/player/video") && !fetchTarget.startsWith("/api/")){
            fetchTarget = "/api/player/video?url="+encodeURIComponent(nxt.url)+"&referer="+encodeURIComponent(referrer||"");
          }
          fetch(fetchTarget,{mode:"no-cors",priority:"low"}).catch(function(){});
        }
      }catch(e){}
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
        try{
          if(!v.paused && v.readyState >= 2){
            v.currentTime += 0.08;
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
  if(pm.classList.contains("hidden") || (token && cur.playToken !== token)){
    if(window._hls){try{window._hls.destroy();window._hls=null;}catch(e){}}
    if(v){try{v.pause();v.removeAttribute("src");v.load();}catch(e){}}
    return;
  }
  v.play().catch(function(err){
    $("pm-spinner").classList.add("hidden");
    if(err && err.name === "NotAllowedError"){
      v.muted = true;
      v.play().catch(function(){});
    }
  });
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
        return;
      }
    }
  }

  // 2. Fallback: reload varian URL jika bukan live multi-level HLS.js
  if(!cur.res||!cur.res.variants)return;
  var curTime = ($("vid") && $("vid").currentTime) || 0;
  for(var i=0;i<cur.res.variants.length;i++){
    if(cur.res.variants[i].q.toLowerCase()===qLow){
      cur.res.picked=cur.res.variants[i];
      renderVariants();
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
  $("pm-prev").disabled=idx<=0;
  $("pm-next").disabled=idx<0||idx>=cur.eps.length-1;
}
function stepEp(d){
  if($("player-modal").classList.contains("hidden"))return;
  var idx=-1;
  for(var i=0;i<cur.eps.length;i++)if(cur.eps[i].ep===cur.ep)idx=i;
  var nxt=cur.eps[idx+d];
  if(nxt){
    cur.ep=nxt.ep;
    updatePrevNext();
    openPlayer(nxt.ep);
  }
  else toast(d>0?"Sudah episode terakhir":"Sudah episode pertama");
}
function closePlayer(){
  // 1. Invalidate all pending async playback tokens immediately
  cur.playToken = ++_playTokenCounter;
  TvNavigationManager.hidePlayerControls();
  closeOpenSubtitlesPicker();

  // 2. Safely stop and destroy video & HLS stream
  var v=$("vid");
  try{recordWatchProgress(true);}catch(e){}
  if(v){
    try{v.pause();}catch(e){}
    v.removeAttribute("src");
    try{v.load();}catch(e){}
  }
  if(window._hls){try{window._hls.destroy();window._hls=null;}catch(e){}}
  cur.cues=[];
  clearOverlay();
  syncNativeTextTrack("", [], "");

  // 3. Hide modal & spinner
  $("player-modal").classList.add("hidden");
  $("pm-spinner").classList.add("hidden");

  // 4. Exit fullscreen safely if active
  if(document.fullscreenElement || document.webkitFullscreenElement){
    try{
      if(document.exitFullscreen) document.exitFullscreen();
      else if(document.webkitExitFullscreen) document.webkitExitFullscreen();
    }catch(e){}
  }
  var stageEl = document.querySelector(".ambient-stage");
  if(stageEl) stageEl.classList.remove("is-fullscreen");
  if(typeof window.tatap_set_fullscreen === "function"){
    try{ window.tatap_set_fullscreen(false); }catch(e){}
  }

  // 5. Perilaku post-watch: kembalikan user ke list episode anime dengan marker last watch yang aktif
  var savedSlug = cur.slug;
  if(savedSlug){
    var tm = $("title-modal");
    if(cur.eps && cur.eps.length > 0){
      if(tm) tm.classList.remove("hidden");
      renderEpRanges();
      renderEpGrid();
      TvNavigationManager.restoreFocusState(".ep.last-watch");
    } else {
      openTitle(savedSlug, cur.title, cur.poster, cur.type, cur.eps_counter);
    }
  }
}
function playMPV(){
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

        if(x.poster){
          var img=document.createElement("img");
          img.className="hist-thumb";
          img.loading="lazy";
          img.decoding="async";
          img.alt=x.title||"";
          img.src=x.poster;
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
  var v=$("vid");
  v.setAttribute("crossorigin","anonymous");
  var tmp=document.createElement("canvas");
  tmp.width=48;tmp.height=27;
  var tctx=null;
  try{tctx=tmp.getContext("2d",{willReadFrequently:true});}catch(e){tctx=tmp.getContext("2d");}
  setInterval(function(){
    if(document.hidden)return;
    if(document.body.classList.contains("no-ambient"))return;
    if($("player-modal").classList.contains("hidden"))return;
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

  if(e.key === "/"){
    e.preventDefault();
    var flt = $("ep-filter");
    if(flt){ flt.focus(); flt.select(); }
    return;
  }

  if(e.key === "f" || e.key === "F"){
    var bm = $("tm-bookmark-btn");
    if(bm){ e.preventDefault(); bm.click(); }
    return;
  }

  if(e.key === "s" || e.key === "S"){
    var src = $("tm-source-btn");
    if(src){ e.preventDefault(); src.click(); }
    return;
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
  var t=(e.target&&e.target.tagName||"").toUpperCase();
  var isTextEditing=(t==="INPUT" && ["button","checkbox","color","file","hidden","image","radio","range","reset","submit"].indexOf(((e.target&&e.target.type)||"text").toLowerCase())===-1) ||
                    (t==="TEXTAREA") ||
                    (e.target&&e.target.isContentEditable);
  if(isTextEditing){
    if(e.key==="Escape"){e.target.blur();}
    return;
  }
  var v=$("vid");
  if(e.key==="Escape"){
    var fsEl=document.fullscreenElement||document.webkitFullscreenElement||document.mozFullScreenElement||document.msFullscreenElement;
    if(fsEl){
      // Fullscreen will be closed natively by browser, keep player modal open
      return;
    }
    if(TvNavigationManager.handleBack(e)) return;
    if(!$("player-modal").classList.contains("hidden"))closePlayer();
    else if(!$("title-modal").classList.contains("hidden"))closeTitle();
    return;
  }
  if($("player-modal").classList.contains("hidden")){
    if(!$("title-modal").classList.contains("hidden")){
      handleTitleModalKey(e);
    }
    return;
  }

  // Player State Machine Handling (Specification 3)
  var pState = TvNavigationManager.playerState();
  if(pState === TvNavigationManager.PLAYER_MODAL_ACTIVE){
    return;
  }

  var isSpace = e.key===" " || e.key==="Spacebar" || e.code==="Space" || e.keyCode===32;

  if(pState === TvNavigationManager.PLAYER_IDLE){
    if(e.key==="ArrowRight"){e.preventDefault();v.currentTime+=5;return;}
    if(e.key==="ArrowLeft"){e.preventDefault();v.currentTime-=5;return;}
    if(e.key==="Enter"||isSpace){
      e.preventDefault();
      if(document.activeElement && document.activeElement !== document.body && document.activeElement !== v){
        try { document.activeElement.blur(); } catch(_){}
      }
      var skipBtn = $("pm-skip-btn");
      if(skipBtn && !skipBtn.classList.contains("hidden") && (cur.activeSkipTarget > 0)){
        doSkip();
      } else {
        if(v.paused) v.play(); else v.pause();
      }
      return;
    }
    if(e.key==="ArrowUp"){
      e.preventDefault();
      if(TvNavigationManager.isTvMode()){
        TvNavigationManager.showPlayerControls($("pm-speed-select") || $("pm-close"));
        return;
      }
      v.volume=Math.min(1, Math.round(((v.volume||1)+0.1)*10)/10);
      toast("Volume: "+Math.round(v.volume*100)+"%", 1200);
      return;
    }
    if(e.key==="ArrowDown"){
      e.preventDefault();
      if(TvNavigationManager.isTvMode()){
        var skipBtn = $("pm-skip-btn");
        if(skipBtn && !skipBtn.classList.contains("hidden")){
          TvNavigationManager.showPlayerControls(skipBtn);
        } else {
          TvNavigationManager.showPlayerControls($("pm-prev") || $("pm-subs") || $("pm-next"));
        }
        return;
      }
      v.volume=Math.max(0, Math.round(((v.volume||1)-0.1)*10)/10);
      toast("Volume: "+Math.round(v.volume*100)+"%", 1200);
      return;
    }
  }

  if(pState === TvNavigationManager.PLAYER_HUD_ACTIVE){
    TvNavigationManager.resetHudTimer();

    if(TvNavigationManager.isTvMode()){
      var pm = $("player-modal");
      var hudBtns = Array.prototype.slice.call(pm.querySelectorAll(".player-head-btns button, .player-head-btns select, .player-foot button, .player-foot select, .sub-size button, .sub-translate, .pm-skip-btn:not(.hidden)"));
      var curFoc = document.activeElement;
      if(e.key==="ArrowDown"){
        var nextDown = TvNavigationManager.getSpatialTarget(curFoc, hudBtns, "down");
        if(nextDown){
          e.preventDefault();
          TvNavigationManager.setFocus(nextDown, "player-hud");
          return;
        }
      } else if(e.key==="ArrowUp"){
        var nextUp = TvNavigationManager.getSpatialTarget(curFoc, hudBtns, "up");
        if(nextUp){
          e.preventDefault();
          TvNavigationManager.setFocus(nextUp, "player-hud");
          return;
        }
      } else if(e.key==="ArrowRight"){
        var nextRight = TvNavigationManager.getSpatialTarget(curFoc, hudBtns, "right");
        if(nextRight){
          e.preventDefault();
          TvNavigationManager.setFocus(nextRight, "player-hud");
          return;
        }
      } else if(e.key==="ArrowLeft"){
        var nextLeft = TvNavigationManager.getSpatialTarget(curFoc, hudBtns, "left");
        if(nextLeft){
          e.preventDefault();
          TvNavigationManager.setFocus(nextLeft, "player-hud");
          return;
        }
      }
    }
  }

  if(isSpace || (!TvNavigationManager.isTvMode() && e.key==="Enter")){
    e.preventDefault();
    if(document.activeElement && document.activeElement !== document.body && document.activeElement !== v){
      try { document.activeElement.blur(); } catch(_){}
    }
    var skipBtn = $("pm-skip-btn");
    if(skipBtn && !skipBtn.classList.contains("hidden") && (cur.activeSkipTarget > 0)){
      doSkip();
    } else {
      if(v.paused) v.play(); else v.pause();
    }
    return;
  }
  else if(e.key==="f"||e.key==="F"){
    e.preventDefault();
    if(document.activeElement && document.activeElement !== document.body && document.activeElement !== v){
      try { document.activeElement.blur(); } catch(_){}
    }
    toggleFullscreen();
  }
  else if(e.key==="n"||e.key==="N"){e.preventDefault();stepEp(1);}
  else if(e.key==="p"||e.key==="P"){e.preventDefault();stepEp(-1);}
  else if(e.key===","||e.key==="<"){e.preventDefault();adjustSubDelay(-0.25);}
  else if(e.key==="."||e.key===">"){e.preventDefault();adjustSubDelay(0.25);}
  else if(e.key==="["||e.key==="{"){e.preventDefault();adjustPlaySpeed(-1);}
  else if(e.key==="]"||e.key==="}"){e.preventDefault();adjustPlaySpeed(1);}
  else if(e.key==="m"||e.key==="M"){
    e.preventDefault();
    v.muted=!v.muted;
    toast(v.muted ? "Muted" : "Unmuted ("+Math.round((v.volume||1)*100)+"%)", 1200);
  }
  else if(e.key==="s"||e.key==="S"){
    e.preventDefault();
    var skipBtn = $("pm-skip-btn");
    var isSkipActive = skipBtn && !skipBtn.classList.contains("hidden") && cur.activeSkipTarget > 0;
    if(isSkipActive){
      doSkip();
      return;
    }
    switchSource();
  }
  else if(e.key==="ArrowRight"){e.preventDefault();v.currentTime+=5;}
  else if(e.key==="ArrowLeft"){e.preventDefault();v.currentTime-=5;}
  else if(e.key==="ArrowUp"){
    e.preventDefault();
    v.volume=Math.min(1, Math.round(((v.volume||1)+0.1)*10)/10);
    toast("Volume: "+Math.round(v.volume*100)+"%", 1200);
  }
  else if(e.key==="ArrowDown"){
    e.preventDefault();
    v.volume=Math.max(0, Math.round(((v.volume||1)-0.1)*10)/10);
    toast("Volume: "+Math.round(v.volume*100)+"%", 1200);
  }
}

function syncSubSize(){
  var box=$("pm-subs-overlay");
  if(box){
    box.classList.remove("sz-s","sz-m","sz-l");
    box.classList.add("sz-"+(cur.subSize||"m"));
  }
  document.querySelectorAll(".sub-size button").forEach(function(b){
    b.classList.toggle("active",b.getAttribute("data-subsize")===(cur.subSize||"m"));
  });
}
function setSubSize(sz){
  if(sz!=="s"&&sz!=="m"&&sz!=="l")return;
  cur.subSize=sz;
  try{localStorage.setItem("tatap_subsize",sz);}catch(e){}
  syncSubSize();
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
  toast("Translate: "+(cur.translate?"ON":"OFF"));
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
  if(p) p.classList.remove("hidden");
}
function closeDrawer(){
  var p = $("drawer-panel");
  if(p) p.classList.add("hidden");
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
  openTitle:openTitle, openPlayer:openPlayer, playMPV:playMPV,
  renderContinue:renderContinue, onKeyPlayer:onKeyPlayer,
  formatTimeSec:formatTimeSec,
  switchSource:switchSource,
  setPlaySpeed:setPlaySpeed, adjustPlaySpeed:adjustPlaySpeed,
  setSubDelay:setSubDelay, adjustSubDelay:adjustSubDelay,
  openDrawer:openDrawer, closeDrawer:closeDrawer,
  openUpdateModal:openUpdateModal, closeUpdateModal:closeUpdateModal,
  checkForUpdate:checkForUpdate,
  closeResumeModal:closeResumeModal, dismissResumeModal:dismissResumeModal,
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

function init(){
  TatapTheme.set(TatapTheme.get());
  loadPrefs();
  try{
    var sz=localStorage.getItem("tatap_subsize");
    if(sz==="s"||sz==="m"||sz==="l")cur.subSize=sz;
  }catch(e){}
  syncSubSize();
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
  $("tm-close").addEventListener("click",function(){
    cur.playToken = ++_playTokenCounter;
    closeTitle();
  });
  var tmBmBtn=$("tm-bookmark-btn");
  if(tmBmBtn) tmBmBtn.addEventListener("click",toggleModalBookmark);
  $("title-modal").addEventListener("click",function(e){
    if(e.target===this){
      cur.playToken = ++_playTokenCounter;
      closeTitle();
    }
  });
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
    if(pop) pop.classList.add("hidden");
  }
  if(btnDrawerHead){
    btnDrawerHead.addEventListener("click", function(e){
      e.stopPropagation();
      if(window.innerWidth >= 769){
        var pop = $("apple-options-popover");
        if(pop) pop.classList.toggle("hidden");
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
      var cmd = $("cmd");
      if(cmd){
        cmd.removeAttribute("readonly");
        cmd.focus();
        cmd.select();
      }
    } else if((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "t"){
      e.preventDefault();
      var t = TatapTheme.toggle();
      toast(t === "light" ? "Mode Terang Aktif" : "Mode Gelap Aktif", 1200);
    } else if(e.key === "Escape"){
      closePopover();
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

  var drawerToggleTheme = $("drawer-toggle-theme");
  if(drawerToggleTheme) drawerToggleTheme.addEventListener("click", function(){
    closeDrawer();
    var t = TatapTheme.toggle();
    toast(t === "light" ? "Mode Terang Aktif" : "Mode Gelap Aktif", 1200);
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

  var rmClose = $("rm-close");
  if(rmClose) rmClose.addEventListener("click", dismissResumeModal);
  var rm = $("resume-modal");
  if(rm) rm.addEventListener("click", function(e){
    if(e.target === rm) dismissResumeModal();
  });
  window.addEventListener("beforeunload", function(){
    recordWatchProgress(true);
  });

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
init();