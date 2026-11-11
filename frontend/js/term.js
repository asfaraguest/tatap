var Tui = (function () {
  var S = {view:"katalog",items:[],sel:-1,page:1,total:1,filter:{},promptFoc:false,seasonFilter:null,prevSel:-1,selApplied:-1,geom:null,cols:1};
  var MAXLOG = 200;

  function $(id){return document.getElementById(id);}
  function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");}
  function isModalOpen(){
    return ($("spotlight-modal") && !$("spotlight-modal").classList.contains("hidden")) ||
           ($("detail-page") && !$("detail-page").classList.contains("hidden")) ||
           (!$("title-modal").classList.contains("hidden")) ||
           (!$("player-modal").classList.contains("hidden")) ||
           ($("sub-style-modal") && !$("sub-style-modal").classList.contains("hidden")) ||
           ($("ai-settings-modal") && !$("ai-settings-modal").classList.contains("hidden")) ||
           ($("resume-modal") && !$("resume-modal").classList.contains("hidden")) ||
           ($("genre-modal") && !$("genre-modal").classList.contains("hidden")) ||
           ($("catalog-filter-modal") && !$("catalog-filter-modal").classList.contains("hidden")) ||
           ($("drawer-panel") && !$("drawer-panel").classList.contains("hidden")) ||
           ($("backend-error-overlay") && !$("backend-error-overlay").classList.contains("hidden")) ||
           ($("update-modal") && !$("update-modal").classList.contains("hidden")) ||
           ($("help-overlay") && !$("help-overlay").classList.contains("hidden"));
  }

  function log(msg,kind){
    var box=$("log");box.classList.remove("hidden");
    var d=document.createElement("div");d.className="log-line"+(kind?" log-"+kind:"");
    d.textContent=msg;box.appendChild(d);
    while(box.children.length>MAXLOG) box.removeChild(box.firstChild);
    box.scrollTop=box.scrollHeight;
  }

  // ==== Modality pin (input mode) ====
  // Navigasi keyboard mengunci highlight ke keyboard (.sel), bahkan saat idle.
  // Kursor mouse yang diam / bergulir di bawahnya tidak bisa mencuri fokus;
  // modus mouse hanya kembali setelah cursor benar-benar bergerak (mousemove/mousedown).
  function lockKbNav(){ document.body.classList.add("kb-nav"); }
  function unlockKbNav(){ document.body.classList.remove("kb-nav"); }
  function clearLog(){$("log").classList.add("hidden");$("log").innerHTML="";}

  function loadRecents(){try{return JSON.parse(localStorage.getItem("tatap_recent")||"[]");}catch(e){return [];}}
  function loadCmdHist(){try{return JSON.parse(localStorage.getItem("tatap_hist")||"[]");}catch(e){return [];}}
  function saveCmdHist(h){try{localStorage.setItem("tatap_hist",JSON.stringify(h.slice(0,50)));}catch(e){}}

  function cmdUsage(){
    return "perintah:\n  cari <judul> | :musim | :lanjutan | :favorit | :katalog\n  :terbaru | :season <winter|spring|summer|fall> <tahun>\n  :switch [hianime|otaku] (ganti sumber video HiAnime / Otakudesu)\n  :filter [key=val...] | :filter reset\n  :genre <slug|title> | :genre | :genre --list | :genre reset\n  :safe [on|off] (mode aman filter konten dewasa/ecchi)\n  :sfx [on|off] (efek suara taktil konsol PS5)\n  :subdelay <detik|reset> (sinkronisasi waktu subtitle, cth: :subdelay -0.5)\n  :substyle | :styler (buka dialog styler font & background subtitle)\n  :tema [toggle|terang|gelap] (ganti mode terang / gelap Apple)\n  :update (cek versi rilis terbaru secara on-demand)\n  :ai (buka modal pengaturan AI) | :apikey <key> | :model <nama> | :prompt <gaya/arahan>\n  :logs | :crt on|off|toggle | :ambient on|off|toggle\n  :riwayat | :favorit | :status | :bantuan | :q";
  }

  function applyFilter(){
    if(S.view!=="katalog"){log("filter hanya di katalog","err");return;}
    S.page=1;
    $("results-title").textContent=getCatalogFilterTitle();
    loadView();
  }

  var SCHEDULE_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];
  var SCHEDULE_LABELS = {
    monday: "Senin", tuesday: "Selasa", wednesday: "Rabu",
    thursday: "Kamis", friday: "Jumat", saturday: "Sabtu", sunday: "Minggu"
  };

  S.scheduleDay = S.scheduleDay || "today";

  function updateScheduleChips(currentServerDay){
    document.querySelectorAll("#schedule-days-bar button").forEach(function(b){
      var d = b.getAttribute("data-day");
      b.classList.toggle("active", d === S.scheduleDay);
      if(currentServerDay){
        b.classList.toggle("is-today", d === currentServerDay);
      }
    });
  }

  function setView(v){
    if(window.TatapSfx) TatapSfx.play("tab");
    document.body.classList.remove("in-detail-view");
    S.view=v;S.page=1;S.sel=-1;S.items=[];clearLog();
    S.prevSel=-1;S.selApplied=-1;S.geom=null;S.cols=1;
    var dp = $("detail-page");
    if(dp) dp.classList.add("hidden");
    var tm = $("title-modal");
    if(tm) tm.classList.add("hidden");
    var searchSec = $("search-sec");
    if(searchSec){
      searchSec.classList.remove("hidden");
      searchSec.classList.toggle("view-lanjutan", v === "lanjutan");
    }
    $("empty-state").style.display="none";
    $("results").innerHTML="";$("results-title").textContent="memuat...";$("results-meta").textContent="";
    $("pager").classList.add("hidden");
    var cSec = $("continue-sec");
    if(cSec) cSec.classList.add("hidden");
    var sBar = $("schedule-days-bar");
    if(sBar) sBar.classList.toggle("hidden", v !== "terbaru");
    if(v === "terbaru") updateScheduleChips();
    var cfBtn = $("btn-catalog-filter");
    if(cfBtn) cfBtn.classList.toggle("hidden", v !== "katalog");
    switch(v){
      case "cari":$("results-title").textContent="cari judul";$("empty-state").style.display="";break;
      case "musim":$("results-title").textContent="Tayang musim ini";break;
      case "lanjutan":$("results-title").textContent="Masih tayang (lanjut)";break;
      case "riwayat":$("results-title").textContent="Riwayat Menonton";break;
      case "favorit":$("results-title").textContent="Anime Favorit";break;
      case "katalog":$("results-title").textContent=getCatalogFilterTitle();break;
      case "terbaru":{
        var lblDay = SCHEDULE_LABELS[S.scheduleDay] || S.scheduleDay || "Hari Ini";
        $("results-title").textContent="Jadwal rilis (" + lblDay + ")";
        break;
      }
      case "season-custom":{
        var sf=S.seasonFilter||{season:"",year:""};
        $("results-title").textContent="Season: "+(sf.season||"?")+" "+sf.year;
        break;
      }
    }
    $("sb-view").textContent="view: "+v;
    updateNavTabs(v);
    loadView();
  }

  function updateNavTabs(v){
    document.querySelectorAll(".nav-tab-btn").forEach(function(btn){
      btn.classList.toggle("active", btn.getAttribute("data-view") === v);
    });
    document.querySelectorAll(".drawer-item[data-view]").forEach(function(item){
      item.classList.toggle("active", item.getAttribute("data-view") === v);
    });
  }

  var _genreList=null;
  function getGenreTitle(slug){
    if(!slug) return "";
    if(_genreList){
      var g = _genreList.find(function(x){ return x.slug === slug; });
      if(g) return g.title;
    }
    return slug.replace(/-/g, " ").replace(/\b\w/g, function(l){ return l.toUpperCase(); });
  }

  function getCatalogFilterTitle(){
    if(!S.catalogFilter) return "Katalog Populer";
    var f = S.catalogFilter;
    var parts = [];
    if(f.genre) {
      parts.push("Genre: " + getGenreTitle(f.genre));
    }
    if(f.sort && f.sort !== "popularity") {
      var sNames = {score: "Skor Tertinggi", latest: "Terbaru", trending: "Trending", az: "A-Z", most_favorite: "Favorit"};
      parts.push(sNames[f.sort] || f.sort);
    }
    if(f.year) parts.push(f.year);
    if(f.season) {
      var seasonNames = {spring: "Musim Semi", summer: "Musim Panas", fall: "Musim Gugur", winter: "Musim Dingin"};
      parts.push(seasonNames[f.season] || f.season);
    }
    if(f.month) {
      var mNames = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
      var mi = parseInt(f.month);
      parts.push((mi >= 1 && mi <= 12) ? mNames[mi] : ("Bln " + f.month));
    }
    if(f.type) parts.push(f.type.toUpperCase());
    if(f.status) parts.push(f.status === "releasing" ? "Airing" : "Tamat");
    if(!parts.length) return "Katalog Populer";
    return "Katalog (" + parts.join(" · ") + ")";
  }

  function apiCall(name){
    switch(name){
      case "musim":return window.Tatap.seasonNow(S.page);
      case "lanjutan":return window.Tatap.stillAiring(S.page);
      case "riwayat":return window.Tatap.history();
      case "favorit":return window.Tatap.bookmarks();
      case "katalog":{
        var f = S.catalogFilter || {};
        var hasFilter = (f.sort && f.sort !== "popularity") || f.year || f.season || f.month || f.type || f.status || f.genre;
        if(hasFilter) {
          return window.Tatap.browse(f, S.page);
        }
        return window.Tatap.catalog(S.page);
      }
      case "terbaru":return window.Tatap.schedule(S.scheduleDay || "today");
      case "season-custom":{
        if(!S.seasonFilter)return null;
        return window.Tatap.seasonBy(S.seasonFilter.season, S.seasonFilter.year, S.page);
      }
      case "cari":return null;
    }
    return null;
  }

  function updateResultsTitle(d){
    switch(S.view){
      case "musim":{
        var sName = (d && d.season) ? String(d.season).toUpperCase() : "";
        $("results-title").textContent = sName ? ("Tayang musim ini · " + sName) : "Tayang musim ini";
        break;
      }
      case "lanjutan":{
        $("results-title").textContent = "Masih tayang (lanjut)";
        break;
      }
      case "terbaru":{
        var lblDay = SCHEDULE_LABELS[S.scheduleDay] || S.scheduleDay || "Hari Ini";
        var isToday = d && (d.is_today || (d.current_day === S.scheduleDay));
        if(lblDay === "Hari Ini" || S.scheduleDay === "today"){
          $("results-title").textContent = "Jadwal rilis (Hari Ini)";
        } else {
          $("results-title").textContent = "Jadwal rilis (" + lblDay + (isToday ? " · Hari Ini" : "") + ")";
        }
        break;
      }
      case "katalog":{
        $("results-title").textContent = getCatalogFilterTitle();
        break;
      }
      case "riwayat":{
        $("results-title").textContent = "Riwayat Menonton";
        break;
      }
      case "favorit":{
        $("results-title").textContent = "Anime Favorit";
        break;
      }
      case "season-custom":{
        var sf = S.seasonFilter || {season: "", year: ""};
        var sUpper = String(sf.season || (d && d.season) || "").toUpperCase();
        var yVal = sf.year || (d && d.year) || "";
        $("results-title").textContent = "Season: " + (sUpper || "?") + (yVal ? (" " + yVal) : "");
        break;
      }
      case "cari":{
        break;
      }
      default:{
        if(d && d.season){
          $("results-title").textContent = S.view + " · " + String(d.season).toUpperCase();
        }
        break;
      }
    }
  }

  async function loadView(){
    if(S.view==="cari"){
      if(S.searchQuery){
        doSearch(S.searchQuery, S.page);
      } else {
        renderRecents();
      }
      return;
    }
    try{
      var r=await apiCall(S.view);
      if(!r){log("gagal load: response kosong","err");return;}
      if(!r.success){
        // FastAPI 422 unpacked — tampilkan detail pertama agar user tahu alasannya.
        var msg=r.error;
        if(Array.isArray(r.detail)&&r.detail[0]&&r.detail[0].msg){
          msg=r.detail[0].msg;
        }else if(r.detail&&r.detail.msg){
          msg=r.detail.msg;
        }
        log("gagal load: "+(msg||"??"),"err");
        return;
      }
      var d=r.data||{};
      if(S.view==="favorit" && Array.isArray(d)){
        S.rawBookmarks = d;
        var pageSize = 24;
        S.total = Math.max(1, Math.ceil(d.length / pageSize));
        if(S.page > S.total) S.page = S.total;
        var start = (S.page - 1) * pageSize;
        S.items = d.slice(start, start + pageSize);
        S.sel = -1;
      }else if(S.view==="riwayat" && Array.isArray(d)){
        S.rawHistory = d;
        var pageSize = 24;
        S.total = Math.max(1, Math.ceil(d.length / pageSize));
        if(S.page > S.total) S.page = S.total;
        var start = (S.page - 1) * pageSize;
        S.items = d.slice(start, start + pageSize);
        S.sel = -1;
      }else if(S.view==="terbaru"){
        var curDayKey = d.weekday || d.day || "";
        if(curDayKey && SCHEDULE_DAYS.indexOf(curDayKey) >= 0){
          S.scheduleDay = curDayKey;
        }
        var curIdx = SCHEDULE_DAYS.indexOf(S.scheduleDay || "");
        if(curIdx < 0) curIdx = 0;
        S.page = curIdx + 1;
        S.total = 7;
        S.items = d.items || (Array.isArray(d) ? d : []);
        S.sel = -1;
        if(d.current_day) updateScheduleChips(d.current_day);
        else updateScheduleChips();
      }else if(Array.isArray(d)){
        S.items=d;S.page=1;S.total=1;S.sel=-1;
      }else{
        S.items=d.items||[];S.page=d.page||1;S.total=d.total_pages||1;S.sel=-1;
      }
      updateResultsTitle(d);
      if(S.view === "riwayat"){
        var totalHist = S.rawHistory ? S.rawHistory.length : S.items.length;
        if(totalHist > 0){
          $("results-meta").innerHTML = totalHist + " judul ditonton · <button class='link-btn' id='btn-clear-history-view'>hapus semua</button>";
          var clrBtn = $("btn-clear-history-view");
          if(clrBtn){
            clrBtn.onclick = async function(e){
              e.stopPropagation();
              try{
                await fetch("/api/history", {method: "DELETE"});
                loadView();
                if(window.App && App.renderContinue) App.renderContinue();
                log("riwayat menonton berhasil dihapus", "ok");
              }catch(err){ log("err: " + (err && err.message || err), "err"); }
            };
          }
        } else {
          $("results-meta").textContent = "0 judul ditonton";
        }
      } else {
        $("results-meta").textContent=S.items.length+" item"+(d.cached?" · cached":"");
      }
      renderResults();renderPager();
    }catch(e){log("err: "+(e&&e.message||e),"err");}
  }

  function renderRecents(){
    S.items=[];S.sel=-1;var r=loadRecents();
    var box=$("results");box.innerHTML="";
    var sBar = $("schedule-days-bar");
    if(sBar) sBar.classList.add("hidden");
    if(!r.length){
      $("empty-state").style.display="";
      $("results-title").textContent="siap";
      $("results-meta").textContent="";
      renderPager();
      return;
    }
    $("empty-state").style.display="none";
    $("results-title").textContent="saran pencarian";$("results-meta").textContent=r.length+" recent";
    for(var i=0;i<r.length;i++){
      (function(q){
        var d=document.createElement("div");d.className="trow";
        d.innerHTML='<span class="tr-num">'+(i+1)+'</span><span class="tr-title">'+esc(q)+'</span>';
        d.addEventListener("click",function(){startSearch(q);});
        box.appendChild(d);
      })(r[i]);
    }
    renderPager();
  }

  function renderResults(){
    var box=$("results");
    var savedIdx = (window.TvNavigationManager ? window.TvNavigationManager.saveFocusedIndex("#results", ".poster-card, .trow") : -1);
    box.innerHTML="";
    var sBar = $("schedule-days-bar");
    if(sBar) sBar.classList.toggle("hidden", S.view !== "terbaru");
    if(!S.items.length){
      var emptyMsg = "Kosong.";
      if(S.view==="favorit"){
        emptyMsg = "Belum ada anime favorit tersimpan. Ketuk tombol + FAVORIT pada detail anime untuk menyimpannya ke sini.";
      }else if(S.view==="riwayat"){
        emptyMsg = "Belum ada riwayat menonton. Mulai tonton anime apa pun dan riwayat akan tercatat otomatis di sini.";
      }else if(S.view==="cari"){
        emptyMsg = "Tidak ada judul anime yang cocok dengan kata kunci pencarian tersebut.";
      }else if(S.view==="terbaru"){
        emptyMsg = "Tidak ada jadwal rilis anime pada hari ini.";
      }
      box.innerHTML="<p class='dim' style='padding:24px 6px;font-size:12.5px;'>"+emptyMsg+"</p>";
      return;
    }

    var grid=document.createElement("div");grid.className="poster-grid";
    for(var j=0;j<S.items.length;j++){
      (function(a,idx){
        if(a.is_header){
          var h=document.createElement("div");
          h.className="lane-header-banner";
          var isLong = a.lane === "long_running";
          var col = isLong ? "#F59E0B" : "#38BDF8";
          var isCompact = (S.view === "lanjutan");
          var mTop = isCompact ? "10px" : "16px";
          var mBtm = isCompact ? "4px" : "8px";
          var pY = isCompact ? "6px" : "8px";
          h.style.cssText="grid-column:1 / -1;width:100%;margin:"+mTop+" 0 "+mBtm+" 0;padding:"+pY+" 12px;background:rgba(15,23,42,0.8);border-left:4px solid "+col+";border-radius:4px;display:flex;align-items:center;justify-content:space-between;user-select:none;box-sizing:border-box;";
          h.innerHTML="<span style='font-weight:bold;font-size:"+(isCompact?"11.5px":"12px")+";letter-spacing:0.04em;color:"+col+"'>"+(a.header_title||a.title||"")+"</span><span style='font-family:monospace;font-size:10px;color:#64748B'>"+(isLong?"[CONTINUOUS]":"[SEASONAL]")+"</span>";
          grid.appendChild(h);
          return;
        }
        if(!a.id) a.id = a.slug;
        if(!a.badge && a.episode != null && a.episode !== undefined) a.badge = String(a.episode);
        else if(!a.badge && a.eps_counter) a.badge = a.eps_counter;

        var isUnavail=!a.id;
        var d=document.createElement("div");
        d.className="poster-card"+(idx===S.sel?" sel":"")+(isUnavail?" unmapped":"");
        d.tabIndex=0;
        d.setAttribute("data-idx",String(idx));
        d.addEventListener("focus",function(){
          if(!isUnavail){
            document.body.classList.remove("sidebar-hovered");
            if(S.sel!==idx){S.sel=idx;renderSel({skipScroll:true,skipFocus:true});}
          }
        });
        d.addEventListener("mouseenter",function(){
          if(!isUnavail){
            document.body.classList.remove("sidebar-hovered");
            if(!document.body.classList.contains("kb-nav")) S.sel=idx;
          }
        });
        d.addEventListener("keydown",function(e){
          if(e.key==="Enter"||e.key===" "){
            e.preventDefault();
            if(!isUnavail){
              App.openTitle(a.id||a.slug,a.title,a.poster,a.type,a.eps_counter,a);
            }
          }
        });

        var media=document.createElement("div");
        media.className="pc-media";

        var ph=document.createElement("div");
        ph.className="pc-thumb-ph";
        ph.innerHTML='<svg class="ui-icon pc-ph-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg><span>TATAP</span>';

        var cleanPoster = (window.App && window.App.sanitizePosterUrl) ? window.App.sanitizePosterUrl(a.poster) : ((a.poster && a.poster.indexOf("img.hianime.to") === -1 && a.poster.indexOf("bookmark123.jpg") === -1) ? a.poster : "");
        if(cleanPoster){
          var im=document.createElement("img");
          im.loading="lazy";
          im.decoding="async";
          im.alt=a.title||"";
          im.src=cleanPoster;
          im.onerror=function(){
            this.style.display="none";
            ph.style.display="flex";
          };
          ph.style.display="none";
          media.appendChild(im);
          media.appendChild(ph);
        } else {
          media.appendChild(ph);
        }

        var idxSpan=document.createElement("span");
        idxSpan.className="pc-idx";
        idxSpan.textContent=String(idx+1).padStart(2,"0");
        media.appendChild(idxSpan);

        if(isUnavail){
          var bad=document.createElement("span");
          bad.className="pc-bad";
          bad.textContent="?";
          bad.title="Tidak ada di hianime";
          media.appendChild(bad);
        }else if(a.score&&a.score>0){
          var sc=document.createElement("span");
          sc.className="pc-score";
          sc.textContent="★ "+a.score.toFixed(1);
          media.appendChild(sc);
        }

        if(S.view==="terbaru"&&a.time){
          var tmBadge=document.createElement("span");
          tmBadge.className="pc-badge-time";
          tmBadge.textContent=a.time+" WIB";
          media.appendChild(tmBadge);
        }

        if(a.badge){
          var bgTag=document.createElement("span");
          var isTam=a.badge==="TAMAT"||a.is_finished;
          var isLongB=a.badge==="SERIAL PANJANG"||a.is_long_running;
          var bCls=isTam?" pc-badge-tamat":(isLongB?" pc-badge-long":" pc-badge-ep");
          bgTag.className="pc-badge-tag"+bCls;
          var bText=a.badge;
          if(a.badge==="ONGOING"&&a.eps_counter){
            bText=a.eps_counter;
          } else if(S.view==="terbaru" && /^\d+$/.test(String(bText))){
            bText="EP "+bText;
          }
          bgTag.textContent=bText;
          media.appendChild(bgTag);
        }

        if(a.type){
          var tp=document.createElement("span");
          tp.className="pc-badge-type";
          tp.textContent=String(a.type).toUpperCase();
          media.appendChild(tp);
        }

        if(S.view==="riwayat"&&a.progress&&a.progress>=15){
          var progTrack=document.createElement("div");
          progTrack.className="pc-progress-track";
          var progFill=document.createElement("div");
          progFill.className="pc-progress-fill";
          var pct=Math.min(100,Math.max(5,Math.round((a.progress/1440)*100)));
          progFill.style.width=pct+"%";
          progTrack.appendChild(progFill);
          media.appendChild(progTrack);
        }

        d.appendChild(media);

        var body=document.createElement("div");
        body.className="poster-body";
        var b=document.createElement("b");
        b.textContent=a.title||"";
        b.title=a.title||"";
        body.appendChild(b);

        var meta=document.createElement("div");
        meta.className="poster-meta";
        var m=[];
        if(S.view==="riwayat"){
          if(a.episode)m.push("Ep "+a.episode);
          if(a.mode)m.push(String(a.mode).toUpperCase());
          if(a.progress&&a.progress>=15&&window.App&&App.formatTimeSec)m.push(App.formatTimeSec(a.progress));
        }else if(S.view==="terbaru"){
          if(a.time)m.push(a.time+" WIB");
          if(a.date)m.push(a.date);
          if(a.type)m.push(String(a.type).toUpperCase());
        }else{
          if(a.season){
            var sStr = a.season;
            if(a.year && sStr.indexOf(String(a.year)) === -1) sStr += " " + a.year;
            m.push(sStr);
          } else if(a.year){
            m.push(String(a.year));
          }
          if(a.eps_counter){
            m.push("Ep "+a.eps_counter);
          }else if(a.eps){
            m.push(a.eps+" ep");
          }
          if(a.type&&!a.season&&!a.year){
            m.push(String(a.type).toUpperCase());
          }
          if(a.duration)m.push(a.duration);
        }
        meta.textContent=m.join(" · ")||"Anime";
        body.appendChild(meta);
        d.appendChild(body);

        if(!isUnavail){
          d.addEventListener("click",function(){
            if(typeof App==="undefined"){log("App belum siap, coba lagi","err");return;}
            S.sel = idx;
            renderSel();
            var now = Date.now();
            if(App._lastCardClick && now - App._lastCardClick < 450) return;
            App._lastCardClick = now;
            App.openTitle(a.id||a.slug,a.title,a.poster,a.type,a.eps_counter,a);
          });
        }
        grid.appendChild(d);
      })(S.items[j],j);
    }
    box.appendChild(grid);
    // Bangun cache geometri sekali per render (offset-based, scroll-invariant) supaya
    // navigasi antar kartu tidak memaksa layout dihitung ulang tiap tekan tombol.
    buildGeom();
    S.prevSel=-1;
    S.selApplied=-1;
    if(window.TvNavigationManager && (savedIdx >= 0 || (window.TvNavigationManager.isTvMode && window.TvNavigationManager.isTvMode()))){
      window.TvNavigationManager.restoreFocusedIndex("#results", ".poster-card, .trow", savedIdx, S.sel >= 0 ? S.sel : 0);
    }
  }

  function renderPager(){
    var hasPagination = false;
    if(S.view === "terbaru"){
      hasPagination = !!(SCHEDULE_DAYS && SCHEDULE_DAYS.length > 1);
    } else {
      hasPagination = (S.total > 1);
    }

    var pagerEl = $("pager");
    if(!pagerEl) return;
    pagerEl.classList.toggle("hidden", !hasPagination);
    if(!hasPagination) return;

    var prevBtn = $("pg-prev");
    var nextBtn = $("pg-next");
    var info = $("pg-info");

    if(S.view === "terbaru"){
      var curIdx = SCHEDULE_DAYS.indexOf(S.scheduleDay || "");
      if(curIdx < 0) curIdx = 0;
      if(prevBtn) prevBtn.disabled = (curIdx <= 0);
      if(nextBtn) nextBtn.disabled = (curIdx >= SCHEDULE_DAYS.length - 1);
      var dayName = SCHEDULE_LABELS[SCHEDULE_DAYS[curIdx]] || SCHEDULE_DAYS[curIdx];
      if(info) info.textContent = dayName + " (" + (curIdx + 1) + "/7) · " + S.items.length + " anime";
      return;
    }

    if(prevBtn) prevBtn.disabled = (S.page <= 1);
    if(nextBtn) nextBtn.disabled = (S.page >= S.total);
    if(info){
      info.textContent = "Halaman " + S.page + " / " + S.total + " · [ ]";
    }
  }

  // ==== Cache geometri grid (scroll-invariant) ====
  // offsetTop/offsetLeft bersifat relatif terhadap offsetParent sehingga TIDAK berubah
  // saat container digulir -> aman di-cache dan dipakai untuk navigasi antar kartu tanpa
  // memaksa browser menghitung ulang layout (forced reflow) pada tiap tekan tombol.
  function buildGeom(){
    var box=$("results");
    if(!box){S.geom=null;S.cols=1;return;}
    var cards=box.querySelectorAll(".poster-card");
    var geom=[];
    for(var i=0;i<cards.length;i++){
      var c=cards[i];
      geom.push({
        idx:parseInt(c.getAttribute("data-idx"),10),
        top:c.offsetTop,left:c.offsetLeft,w:c.offsetWidth,h:c.offsetHeight
      });
    }
    S.geom=geom;
    // Jumlah kolom = kartu pertama yang berada di baris berikutnya
    var cols=1;
    if(geom.length>1){
      var firstTop=geom[0].top;
      for(var g=1;g<geom.length;g++){
        if(geom[g].top>firstTop+8){cols=g;break;}
      }
      if(cols===1)cols=geom.length;
    }
    S.cols=cols;
  }

  // Target spasial 2D berbasis cache geometri (setara getSpatialTarget, tanpa rect read)
  function spatialTarget(idx, direction){
    var geom=S.geom;
    if(!geom||!geom.length)return null;
    var cur=null;
    for(var i=0;i<geom.length;i++){ if(geom[i].idx===idx){cur=geom[i];break;} }
    if(!cur)return null;
    var curCX=cur.left+cur.w/2, curCY=cur.top+cur.h/2;

    var candidates=[];
    for(var j=0;j<geom.length;j++){
      var it=geom[j];
      if(it.idx===idx)continue;
      candidates.push({
        idx:it.idx,
        top:it.top,
        left:it.left,
        w:it.w,
        h:it.h,
        bottom:it.top+it.h,
        cx:it.left+it.w/2,
        cy:it.top+it.h/2
      });
    }
    if(!candidates.length)return null;

    if(direction==="left"){
      var leftCands=candidates.filter(function(c){
        return (Math.abs(c.cy-curCY)<cur.h*0.48) && (c.cx<curCX);
      });
      if(!leftCands.length)return null;
      leftCands.sort(function(a,b){ return b.cx-a.cx; });
      return leftCands[0];
    }

    if(direction==="right"){
      var rightCands=candidates.filter(function(c){
        return (Math.abs(c.cy-curCY)<cur.h*0.48) && (c.cx>curCX);
      });
      if(!rightCands.length)return null;
      rightCands.sort(function(a,b){ return a.cx-b.cx; });
      return rightCands[0];
    }

    if(direction==="down"){
      var belowCands=candidates.filter(function(c){
        return (c.top>=cur.top+cur.h-8)||(c.cy>curCY+cur.h*0.4);
      });
      if(!belowCands.length)return null;
      var minTop=Infinity;
      for(var b1=0;b1<belowCands.length;b1++){
        if(belowCands[b1].top<minTop) minTop=belowCands[b1].top;
      }
      var nextRow=belowCands.filter(function(c){
        return c.top<=minTop+28;
      });
      if(!nextRow.length)return null;
      nextRow.sort(function(a,b){
        return Math.abs(a.cx-curCX)-Math.abs(b.cx-curCX);
      });
      return nextRow[0];
    }

    if(direction==="up"){
      var aboveCands=candidates.filter(function(c){
        return (c.bottom<=cur.top+8)||(c.cy<curCY-cur.h*0.4);
      });
      if(!aboveCands.length)return null;
      var maxBottom=-Infinity;
      for(var a1=0;a1<aboveCands.length;a1++){
        if(aboveCands[a1].bottom>maxBottom) maxBottom=aboveCands[a1].bottom;
      }
      var prevRow=aboveCands.filter(function(c){
        return c.bottom>=maxBottom-28;
      });
      if(!prevRow.length)return null;
      prevRow.sort(function(a,b){
        return Math.abs(a.cx-curCX)-Math.abs(b.cx-curCX);
      });
      return prevRow[0];
    }
    return null;
  }

  function getGridCols(){
    if(S.cols&&S.cols>0)return S.cols;
    var box=$("results");
    if(!box)return 1;
    var cards=box.querySelectorAll(".poster-card");
    if(cards.length<2)return 1;
    var firstTop=cards[0].offsetTop;
    for(var c=1;c<cards.length;c++){
      if(cards[c].offsetTop > firstTop + 8){
        return c;
      }
    }
    return cards.length;
  }

  function moveSel(d){
    if(!S.items.length)return;
    lockKbNav();
    var count=S.items.length;
    var next;

    // Navigasi spasial 2D geometris untuk pergerakan vertikal (ArrowDown / ArrowUp)
    if(Math.abs(d) > 1 && S.sel >= 0){
      var box=$("results");
      var curCard = box ? box.querySelector('.poster-card[data-idx="' + S.sel + '"]') : null;
      var dir = (d > 0) ? "down" : "up";
      // Cache geometri (offset-based, tanpa forced layout) untuk path desktop;
      // TV memakai spatial manager (butuh rect real-time untuk D-Pad).
      var useTvSpatial = window.TvNavigationManager && window.TvNavigationManager.isTvMode && window.TvNavigationManager.isTvMode();
      var target = null;
      if(useTvSpatial && curCard && window.TvNavigationManager.getSpatialTarget){
        var allCards = Array.prototype.slice.call(box.querySelectorAll(".poster-card"));
        target = window.TvNavigationManager.getSpatialTarget(curCard, allCards, dir);
      } else {
        var geoHit = spatialTarget(S.sel, dir);
        if(geoHit) target = box ? box.querySelector('.poster-card[data-idx="' + geoHit.idx + '"]') : null;
      }
      if(target){
        var tIdx = parseInt(target.getAttribute("data-idx"), 10);
        if(!isNaN(tIdx) && S.items[tIdx] && !S.items[tIdx].is_header){
          S.sel = tIdx;
          renderSel();
          return;
        }
      } else {
          // Batas tepi atas atau bawah (clamping tanpa wrap-around)
          if(d > 0){
            if(window.TvNavigationManager && window.TvNavigationManager.isTvMode && window.TvNavigationManager.isTvMode()){
              window.TvNavigationManager.setFocus($("search-input-wrap"), "search");
            }
            return;
          } else {
            if(window.TvNavigationManager && window.TvNavigationManager.isTvMode && window.TvNavigationManager.isTvMode()){
              var sched = $("schedule-days-bar");
              if(sched && !sched.classList.contains("hidden")){
                var firstChip = sched.querySelector(".ep-range-chip");
                if(firstChip){ window.TvNavigationManager.setFocus(firstChip, "chips"); return; }
              }
              var actTab = document.querySelector(".nav-tab-btn.active") || document.querySelector(".nav-tab-btn");
              if(actTab){ window.TvNavigationManager.setFocus(actTab, "tabs"); return; }
            } else {
              var actTab = document.querySelector(".nav-tab-btn.active") || document.querySelector(".nav-tab-btn");
              if(actTab){ actTab.focus(); return; }
            }
            return;
          }
        }
      }

    if(d === 0){
      next = (S.sel >= 0) ? S.sel : 0;
    } else if(S.sel < 0){
      next = (d > 0) ? 0 : count - 1;
    } else {
      if(Math.abs(d) > 1){
        if(d > 0){
          if(S.sel + d >= count){
            if(S.sel >= count - getGridCols()){
              if(window.TvNavigationManager && window.TvNavigationManager.isTvMode && window.TvNavigationManager.isTvMode()){
                window.TvNavigationManager.setFocus($("search-input-wrap"), "search");
                return;
              }
            }
            next = count - 1;
          } else {
            next = S.sel + d;
          }
        } else {
          if(S.sel + d < 0){
            if(window.TvNavigationManager && window.TvNavigationManager.isTvMode && window.TvNavigationManager.isTvMode()){
              var sched = $("schedule-days-bar");
              if(sched && !sched.classList.contains("hidden")){
                var firstChip = sched.querySelector(".ep-range-chip");
                if(firstChip){
                  window.TvNavigationManager.setFocus(firstChip, "chips");
                  return;
                }
              }
              var actTab = document.querySelector(".nav-tab-btn.active") || document.querySelector(".nav-tab-btn");
              if(actTab){
                window.TvNavigationManager.setFocus(actTab, "tabs");
                return;
              }
            }
            next = 0;
          } else {
            next = S.sel + d;
          }
        }
      } else {
        next = (S.sel + d + count) % count;
      }
    }
    var stepDir = (d >= 0 ? 1 : -1);
    for(var step=0;step<count;step++){
      if(S.items[next] && !S.items[next].is_header){
        S.sel=next;
        renderSel();
        return;
      }
      next = (next + stepDir + count) % count;
    }
  }

  // Resolver item grid (kartu poster .poster-card maupun baris .trow) berdasarkan indeks.
  // Satu helper untuk kedua jenis item agar navigasi keyboard konsisten di semua tampilan.
  function itemEl(box, idx){
    if(!box || idx < 0) return null;
    return box.querySelector('.poster-card[data-idx="'+idx+'"], .trow[data-idx="'+idx+'"]');
  }

  function renderSel(opts){
    opts = opts || {};
    var box=$("results");
    if(!box)return;
    var isTv = !!(window.TvNavigationManager && window.TvNavigationManager.isTvMode && window.TvNavigationManager.isTvMode());
    // Update tersasar: hanya kartu yang benar-benar berubah state-nya yang disentuh.
    // Menyapu seluruh grid (44 kartu) per tekan tombol = hundreds classList ops per keypress.
    var prevIdx=S.prevSel;
    S.prevSel=S.sel;
    if(prevIdx===S.sel && S.selApplied===S.sel) return;
    if(prevIdx>=0 && prevIdx!==S.sel && S.sel>=0 && window.TatapSfx){
      TatapSfx.play("tick");
    }
    S.selApplied=S.sel;
    var touched=[];
    if(prevIdx>=0 && prevIdx!==S.sel){
      var prevEl=itemEl(box, prevIdx);
      if(prevEl)touched.push(prevEl);
    }
    if(S.sel>=0){
      var nextEl=itemEl(box, S.sel);
      if(nextEl && nextEl!==touched[0])touched.push(nextEl);
    }
    for(var i=0;i<touched.length;i++){
      var el=touched[i];
      var eIdx=parseInt(el.getAttribute("data-idx"),10);
      var isUnm=el.classList.contains("unmapped");
      var isThis=(eIdx===S.sel && !isUnm);
      if(el.classList.contains("sel")!==isThis)el.classList.toggle("sel",isThis);
      if(isTv){
        if(el.classList.contains("tv-focus")!==isThis)el.classList.toggle("tv-focus",isThis);
      }else if(el.classList.contains("tv-focus")){
        el.classList.remove("tv-focus"); // all[i].classList.remove("tv-focus");
      }
    }
    if(S.sel < 0) return;
    if(opts.skipScroll) return;
    var selEl = itemEl(box, S.sel);
    if(selEl){
      var container = $("search-sec");
      var shouldScroll = true;
      if(container){
        var cRect = container.getBoundingClientRect();
        var eRect = selEl.getBoundingClientRect();
        if(eRect.top >= cRect.top + 6 && eRect.bottom <= cRect.bottom - 6){
          shouldScroll = false;
        }
      }
      if(shouldScroll){
        selEl.scrollIntoView({block:"nearest", inline:"nearest"});
      }
      if(window.TvNavigationManager && isTv){
        window.TvNavigationManager.setFocus(selEl, "grid", { scroll: shouldScroll });
      }
      if(document.activeElement !== selEl){
        if(!opts.skipFocus){
          try{selEl.focus({preventScroll:true});}catch(_){}
        }
      }
    }
  }

  function blurCards(){
    if(document.activeElement && document.activeElement.classList && (document.activeElement.classList.contains("poster-card") || document.activeElement.classList.contains("trow"))){
      try{document.activeElement.blur();}catch(_){}
    }
    if(S.sel >= 0){
      S.sel = -1;
      renderSel({skipScroll:true, skipFocus:true});
    }
  }

  function openSelected(){
    if(!S.items.length||S.sel<0)return;
    var a=S.items[S.sel];
    if(!a||a.is_header)return;
    var targetId = a.id || a.slug;
    if(!targetId){log("judul ini belum tersedia di hianime","err");return;}
    App.openTitle(targetId,a.title,a.poster,a.type,a.eps_counter,a);
  }

  function startSearch(q){
    q=q.trim();if(!q)return;
    var recent=loadRecents().filter(function(x){return x!==q;});recent.unshift(q);
    try{localStorage.setItem("tatap_recent",JSON.stringify(recent.slice(0,6)));}catch(e){}
    setViewSilent("cari");
    $("empty-state").style.display="none";
    $("results-title").textContent="Mencari "+q+"...";$("results-meta").textContent="";
    doSearch(q);
  }

  async function doSearch(q, page){
    var p = page || 1;
    S.searchQuery = q;
    S.page = p;
    var t0=Date.now();
    var qlow=(q||"").trim().toLowerCase();
    if(qlow==="hentai"||qlow.indexOf("hentai")>=0){
      log("kata kunci 'hentai' diblokir","err");
      S.items=[];S.sel=-1;S.total=1;
      $("results-title").textContent="Kata kunci 'hentai' diblokir";
      $("results-meta").textContent="0 judul";
      renderResults();renderPager();
      return;
    }
    try{
      var src = (window.cur && window.cur.source) || "";
      var r = await window.Tatap.search(q, src, p);
      if(!r||!r.success){log("search error: "+(r&&r.error||"??"),"err");return;}
      var d = r.data || {};
      S.items=d.results||[];
      S.sel=-1;
      S.page=d.page||p;
      S.total=d.total_pages||1;
      var pageSuffix = S.page > 1 ? (" (Hal " + S.page + ")") : "";
      $("results-title").textContent=S.items.length?("Hasil untuk \""+q+"\""+pageSuffix):("Tidak ketemu \""+q+"\"");
      $("results-meta").textContent=S.items.length+" judul · "+(Date.now()-t0)+"ms"+(d.cached?" · cached":"");
      renderResults();renderPager();
    }catch(e){log("err: "+e.message,"err");}
  }

  function setViewSilent(v){
    S.view=v;S.page=1;
    $("pager").classList.add("hidden");
    var cSec = $("continue-sec");
    if(cSec) cSec.classList.add("hidden");
    var sBar = $("schedule-days-bar");
    if(sBar) sBar.classList.toggle("hidden", v !== "terbaru");
    updateNavTabs(v);
  }

  // ==== :filter (Catalog Cross-Filter) ====
  function openCatalogFilterModal(){
    var m = $("catalog-filter-modal");
    if(!m) return;
    m.classList.remove("hidden");
    syncCatalogFilterUI();
  }
  function closeCatalogFilterModal(){
    var m = $("catalog-filter-modal");
    if(m) m.classList.add("hidden");
  }
  function syncCatalogFilterUI(){
    var f = S.catalogFilter || {sort: "popularity", year: "", season: "", month: "", type: "", status: "", genre: ""};
    setGroupActive("cf-chips-sort", f.sort || "popularity");
    setGroupActive("cf-chips-year", f.year || "");
    setGroupActive("cf-chips-season", f.season || "");
    setGroupActive("cf-chips-month", f.month || "");
    setGroupActive("cf-chips-type", f.type || "");
    setGroupActive("cf-chips-status", f.status || "");

    var genreLabel = $("cf-btn-genre-label");
    var btnGenre = $("cf-btn-pick-genre");
    var btnClearGenre = $("cf-btn-genre-clear");
    var curGenre = f.genre || S.genreFilter || "";
    if(curGenre){
      var gTitle = getGenreTitle(curGenre);
      if(genreLabel) genreLabel.textContent = "Genre: " + gTitle;
      if(btnGenre) btnGenre.classList.add("active");
      if(btnClearGenre) btnClearGenre.classList.remove("hidden");
    } else {
      if(genreLabel) genreLabel.textContent = "Semua Genre (Pilih...)";
      if(btnGenre) btnGenre.classList.remove("active");
      if(btnClearGenre) btnClearGenre.classList.add("hidden");
    }
  }
  function setGroupActive(containerId, activeVal){
    var box = $(containerId);
    if(!box) return;
    box.querySelectorAll(".cf-chip").forEach(function(b){
      var v = b.getAttribute("data-val") || "";
      b.classList.toggle("active", v === activeVal);
    });
  }
  function getGroupActive(containerId){
    var box = $(containerId);
    if(!box) return "";
    var act = box.querySelector(".cf-chip.active");
    return act ? (act.getAttribute("data-val") || "") : "";
  }

  // ==== :genre ====
  function slugifyGenre(s){
    return String(s||"").trim().toLowerCase()
      .replace(/&/g,"and").replace(/[^a-z0-9]+/g,"-")
      .replace(/^-+|-+$/g,"");
  }
  async function loadGenres(){
    if(_genreList)return _genreList;
    var r=await window.Tatap.genres();
    var raw=(r&&r.success&&r.data&&r.data.list)||[];
    _genreList=raw.filter(function(g){
      return (g.slug||"").toLowerCase()!=="hentai" && (g.title||"").toLowerCase().indexOf("hentai")<0;
    });
    return _genreList;
  }
  async function openGenreModal(){
    $("genre-modal").classList.remove("hidden");
    $("genre-search").value="";
    var list=await loadGenres();
    updateGenreStatusUI();
    renderGenreList(list);
    setTimeout(function(){$("genre-search").focus();},30);
  }
  function closeGenreModal(){$("genre-modal").classList.add("hidden");}
  function updateGenreStatusUI(){
    var st = $("genre-active-status");
    if(!st) return;
    var activeSlug = (S.catalogFilter && S.catalogFilter.genre) || S.genreFilter || "";
    if(activeSlug){
      st.innerHTML = 'Genre aktif: <span class="active-label">' + esc(getGenreTitle(activeSlug)) + '</span>';
    } else {
      st.textContent = "Tidak ada genre aktif (semua anime)";
    }
  }
  function renderGenreList(list){
    var box=$("genre-list");box.innerHTML="";
    if(!list.length){
      var e=document.createElement("div");e.className="empty";e.textContent="(tidak ada hasil)";box.appendChild(e);return;
    }
    var activeSlug = (S.catalogFilter && S.catalogFilter.genre) || S.genreFilter || "";
    for(var i=0;i<list.length;i++){
      (function(g){
        var b=document.createElement("button");
        if(activeSlug && g.slug === activeSlug){
          b.className = "active";
        }
        b.innerHTML='<span class="g-slug">'+esc(g.slug)+'</span><span class="g-title">'+esc(g.title)+'</span>';
        b.addEventListener("click",function(){
          applyGenreFilter(g.slug);closeGenreModal();
        });
        box.appendChild(b);
      })(list[i]);
    }
  }
  function applyGenreFilter(slug){
    var s=(slug||"").toLowerCase();
    if(s==="hentai"||s.indexOf("hentai")>=0){
      log("genre 'hentai' tidak didukung / diblokir","err");return;
    }
    if(!S.catalogFilter) S.catalogFilter = {sort: "popularity", year: "", season: "", month: "", type: "", status: ""};
    S.catalogFilter.genre = slug;
    S.genreFilter = slug;
    S.filter = {genre: slug};
    S.page = 1;
    log("genre: "+getGenreTitle(slug),"ok");
    setViewSilent("katalog");
    var cfBtn = $("btn-catalog-filter");
    if(cfBtn) cfBtn.classList.remove("hidden");
    syncCatalogFilterUI();
    $("results-title").textContent = getCatalogFilterTitle();
    $("empty-state").style.display = "none";
    loadView();
  }
  function clearGenreFilter(){
    if(S.catalogFilter) delete S.catalogFilter.genre;
    delete S.genreFilter;
    if(S.filter && S.filter.genre) delete S.filter.genre;
    S.page = 1;
    log("genre filter dihapus","ok");
    syncCatalogFilterUI();
    updateGenreStatusUI();
    $("results-title").textContent = getCatalogFilterTitle();
    loadView();
  }
  async function cmdGenre(parts){
    if(parts.length<=1){openGenreModal();return;}
    var a=parts.slice(1);
    if(a[0]==="reset"){
      clearGenreFilter();
      return;
    }
    if(a[0]==="--list"||a[0]==="list"){
      var kw=a[1]&&a[1]!=="--search"?a[1]:(a[2]||"");
      var list=await loadGenres();
      if(!list.length){log("gagal load genre (lihat ?bak offline).","err");return;}
      var shown=0;
      for(var i=0;i<list.length;i++){
        var g=list[i];
        if(kw&&(g.title+" "+g.slug).toLowerCase().indexOf(kw.toLowerCase())<0)continue;
        log((""+g.slug).padEnd(28)+"  "+g.title);
        shown++;
      }
      if(!shown)log("tidak ada genre cocok '"+kw+"'","err");
      else log("total: "+shown+" genre","ok");
      return;
    }
    var slug=slugifyGenre(a.join(" "));
    if(!slug){log("usage: genre <slug|title> | genre | genre --list | genre reset","err");return;}
    if(slug.toLowerCase()==="hentai"||slug.toLowerCase().indexOf("hentai")>=0){
      log("genre 'hentai' tidak didukung / diblokir","err");return;
    }
    applyGenreFilter(slug);
  }

  // ==== :season ====
  var SEASONS = ["winter","spring","summer","fall"];
  function applySeasonFilter(name, year){
    S.seasonFilter = {season: name, year: year};
    S.page = 1;
    log("season: "+name+" "+year, "ok");
    setViewSilent("season-custom");
    $("results-title").textContent = "Season: "+name[0].toUpperCase()+name.slice(1)+" "+year;
    $("empty-state").style.display = "none";
    loadView();
  }
  function cmdSeason(rawArgs){
    var t = (rawArgs||"").trim();
    if(!t){
      log("usage: season <winter|spring|summer|fall> <tahun>","err");
      log("contoh: :season fall 2024","err");return;
    }
    var parts = t.split(/\s+/);
    if(parts.length < 2){
      log("usage: season <winter|spring|summer|fall> <tahun>","err");
      log("contoh: :season fall 2024","err");return;
    }
    var name = parts[0].toLowerCase();
    var year = parseInt(parts[1], 10);
    if(SEASONS.indexOf(name) < 0){
      log("season tak dikenal: "+name+" (winter/spring/summer/fall)","err");return;
    }
    if(!year || year < 1900 || year > 2100){
      log("tahun tak valid: "+parts[1],"err");return;
    }
    applySeasonFilter(name, year);
  }

  // ==== :apikey / :model / :apiurl / :ollama / :groq / :gemini / :prompt ====
  var TRANSLATE_KEYS = {
    apikey:     {field:"translate_apikey", label:"apikey"},
    gemini:     {field:"translate_apikey", label:"apikey (Google Gemini)"},
    groq:       {field:"translate_apikey", label:"apikey (Groq)"},
    openrouter: {field:"translate_apikey", label:"apikey (OpenRouter)"},
    cerebras:   {field:"translate_apikey", label:"apikey (Cerebras)"},
    openai:     {field:"translate_apikey", label:"apikey (OpenAI)"},
    ollama:     {field:"translate_apikey", label:"apikey (Legacy)"},
    model:  {field:"translate_model",  label:"model"},
    apiurl: {field:"translate_apiurl", label:"apiurl"},
    prompt: {field:"translate_custom_prompt", label:"custom prompt"},
    fansub: {field:"translate_custom_prompt", label:"custom prompt"}
  };
  function maskKey(v){
    if(!v) return "(kosong)";
    if(v.length <= 10) return "****";
    var prefixLen = (v.indexOf("AQ.") === 0) ? 6 : 8;
    return v.slice(0, prefixLen) + "..." + v.slice(-4);
  }
  async function cmdTranslateSetting(cmd, rawArgs){
    var info = TRANSLATE_KEYS[cmd];
    if(!info) return;
    var args = (rawArgs||"").trim();
    if(cmd === "apikey" || cmd === "ollama" || cmd === "groq" || cmd === "gemini" || cmd === "openai"){
      args = args.replace(/^["']|["']$/g, "").trim();
    }
    if(!args){
      // Status: tampilkan nilai translate (mask apikey).
      var r = await window.Tatap.getSettings();
      var d = (r && r.success && r.data) || {};
      if(cmd === "prompt" || cmd === "fansub"){
        log("custom prompt : "+(d.translate_custom_prompt||"(default fansub)"),"ok");
        return;
      }
      log("apikey : "+maskKey(d.translate_apikey||""),"ok");
      log("model  : "+(d.translate_model||"(default)"),"ok");
      log("apiurl : "+(d.translate_apiurl||"(default)"),"ok");
      log("prompt : "+(d.translate_custom_prompt||"(default fansub)"),"ok");
      if(!d.translate_apikey){
        log("Belum ada API key AI. Preset otomatis yang didukung (Free Tier):", "err");
        log("  • Google Gemini : :gemini AQ...      (model: gemini-3.1-flash-lite)", "dim");
        log("  • Groq          : :groq gsk_...      (model: llama-3.3-70b-versatile)", "dim");
        log("  • OpenRouter    : :openrouter sk-or... (model: gemini-2.0-flash-exp:free)", "dim");
        log("  • Cerebras      : :cerebras csk-...  (model: llama3.3-70b)", "dim");
        log("  • OpenAI        : :openai sk-...     (model: gpt-4o-mini)", "dim");
      }
      return;
    }
    if(args === "clear" || args === "reset"){
      var p1 = {}; p1[info.field] = "";
      try{ await window.Tatap.setSetting(p1); }catch(e){}
      log(info.label+" dihapus","ok");
      return;
    }
    // Set value.
    var payload = {};
    payload[info.field] = args;
    var extra = "";
    if(cmd === "apikey" || cmd === "ollama" || cmd === "groq" || cmd === "gemini" || cmd === "openrouter" || cmd === "cerebras" || cmd === "openai"){
      if(cmd === "gemini" || args.indexOf("AQ.") === 0 || args.indexOf("AIza") === 0 || args.indexOf("AQ") === 0){
        // Google Gemini key (Google AI Studio: AQ. baru / AIza legacy) -> auto-set apiurl + model Gemini Flash Lite.
        payload.translate_apiurl = "https://generativelanguage.googleapis.com/v1beta/openai";
        payload.translate_model = "gemini-3.1-flash-lite";
        extra = " (auto: apiurl=Google AI Studio, model=gemini-3.1-flash-lite)";
      }else if(cmd === "groq" || args.indexOf("gsk_") === 0){
        // Groq key -> auto-set apiurl + model Llama-3.3-70B
        payload.translate_apiurl = "https://api.groq.com/openai/v1";
        payload.translate_model = "llama-3.3-70b-versatile";
        extra = " (auto: apiurl=Groq, model=llama-3.3-70b-versatile)";
      }else if(cmd === "openrouter" || args.indexOf("sk-or-") === 0){
        payload.translate_apiurl = "https://openrouter.ai/api/v1";
        payload.translate_model = "google/gemini-2.0-flash-exp:free";
        extra = " (auto: apiurl=OpenRouter Free, model=gemini-2.0-flash-exp:free)";
      }else if(cmd === "cerebras" || args.indexOf("csk-") === 0){
        payload.translate_apiurl = "https://api.cerebras.ai/v1";
        payload.translate_model = "llama3.3-70b";
        extra = " (auto: apiurl=Cerebras, model=llama3.3-70b)";
      }else if(cmd === "openai" || args.indexOf("sk-") === 0 || args.indexOf("sk_") === 0){
        payload.translate_apiurl = "https://api.openai.com/v1";
        payload.translate_model = "gpt-4o-mini";
        extra = " (auto: apiurl=OpenAI, model=gpt-4o-mini)";
      }else if(cmd === "ollama" || args.indexOf("ollama_") === 0 || args.indexOf("ol_") === 0){
        payload.translate_apiurl = "https://ollama.com/v1";
        payload.translate_model = "gpt-oss:20b";
        extra = " (legacy: apiurl=Ollama Cloud)";
      }else{
        extra = " (provider kustom: gunakan juga :apiurl <url> dan :model <nama> bila perlu)";
      }
    }
    try{
      var res = await window.Tatap.setSetting(payload);
      if(res && res.success){
        var masked = (cmd === "apikey") ? (" (" + maskKey(args) + ")") : (" (" + args + ")");
        log(info.label + " disimpan" + masked + extra, "ok");
      }else{
        log("gagal menyimpan " + info.label + ": " + ((res && res.error) || "unknown error"), "err");
      }
    }catch(e){
      log("gagal menyimpan " + info.label + ": " + e.message, "err");
    }
  }

  async function cmdLogs(){
    try{
      var r = await fetch("/api/translate/logs").then(function(res){return res.json();});
      var logs = (r&&r.data&&r.data.logs)||[];
      if(!logs.length){
        log("Belum ada riwayat aktivitas translasi subtitle.", "dim");
        return;
      }
      log("--- Riwayat Log Translasi Subtitle ---", "ok");
      for(var i=0; i<logs.length; i++){
        var line = logs[i];
        var cls = "dim";
        if(line.indexOf("sukses")>=0 || line.indexOf("selesai")>=0 || line.indexOf("Cache HIT")>=0){
          cls = "ok";
        }else if(line.indexOf("GAGAL")>=0 || line.indexOf("gagal")>=0 || line.indexOf("ERROR")>=0 || line.indexOf("Rate limit")>=0){
          cls = "err";
        }
        log(line, cls);
      }
    }catch(e){
      log("Gagal membaca log translasi: " + e.message, "err");
    }
  }

  async function handleCommand(raw){
    var s=raw.trim();if(!s)return;
    var parts=s.split(/\s+/);
    var cmd=parts[0].toLowerCase();
    var args=parts.slice(1).join(" ");
    switch(cmd){
      case "cari":if(!args){log("usage: cari <judul>","err");}else{startSearch(args);}break;
      case "musim":setView("musim");break;
      case "lanjutan":setView("lanjutan");break;
      case "katalog":setView("katalog");break;
      case "filter":case "cf":
        if(!args){openCatalogFilterModal();break;}
        if(args==="reset"){
          S.filter={};S.page=1;log("filter direset","ok");applyFilter();break;
        }
        var f={};
        for(var i=0;i<parts.length-1;i++){
          var kv=parts[i+1].split("=");
          if(kv.length===2)f[kv[0]]=kv[1];
        }
        S.filter=f;S.page=1;log("filter: "+JSON.stringify(f),"ok");applyFilter();break;
      case "season":cmdSeason(args);break;
      case "jadwal":case "schedule":case "terbaru":case "airing":
        var dArg = (args || "").trim().toLowerCase();
        if(dArg) {
          var idMap = {senin:"monday",selasa:"tuesday",rabu:"wednesday",kamis:"thursday",jumat:"friday",sabtu:"saturday",minggu:"sunday",kemarin:"yesterday",besok:"tomorrow","hari ini":"today"};
          if(idMap[dArg]) dArg = idMap[dArg];
          if(SCHEDULE_DAYS.indexOf(dArg) >= 0 || dArg === "today" || dArg === "yesterday" || dArg === "tomorrow"){
            S.scheduleDay = dArg;
          }
        }
        setView("terbaru");break;
      case "switch":
        var target = (args || "").toLowerCase().trim();
        var curSrc = (window.cur && window.cur.source) || "hianime";
        var nxt = "";
        if(target === "otaku" || target === "otakudesu"){
          nxt = "otakudesu";
        }else if(target === "hi" || target === "hianime"){
          nxt = "hianime";
        }else if(target === "anichan" || target === "ani"){
          nxt = "anichan";
        }else if(!target){
          if(curSrc === "hianime") nxt = "otakudesu";
          else if(curSrc === "otakudesu") nxt = "anichan";
          else nxt = "hianime";
        }else{
          log("usage: :switch [hianime|otaku|anichan]","err");
          break;
        }
        if(window.App && window.App.switchSource){
          var resSrc = window.App.switchSource(nxt);
          var srcLabel = resSrc === "otakudesu" ? "Otakudesu (Sub Indo)" : (resSrc === "anichan" ? "AniChan (Failover Stream)" : "HiAnime");
          log("sumber streaming beralih ke: " + srcLabel, "ok");
        }else{
          if(window.Tatap && window.Tatap.setSetting){
            window.Tatap.setSetting({ preferred_source: nxt }).catch(function(){});
          }
          log("sumber streaming default: " + nxt, "ok");
        }
        break;
      case "genre":cmdGenre(parts);break;
      case "crt":
        if(!args){log("usage: crt on|off|toggle","err");break;}
        var v1=args==="on"?"on":args==="off"?"off":null;
        if(v1===null&&args!=="toggle"){log("usage: crt on|off|toggle","err");break;}
        var cur=localStorage.getItem("tatap_crt")||"off";
        var nxt=v1||(cur==="on"?"off":"on");
        try{localStorage.setItem("tatap_crt",nxt);}catch(e){}
        document.body.classList.toggle("no-crt",nxt!=="on");
        log("crt "+(nxt==="on"?"ON":"OFF"),"ok");break;
      case "ambient":
        if(!args){log("usage: ambient on|off|toggle","err");break;}
        var v2=args==="on"?"on":args==="off"?"off":null;
        if(v2===null&&args!=="toggle"){log("usage: ambient on|off|toggle","err");break;}
        var cur2=localStorage.getItem("tatap_ambient")||"on";
        var nxt2=v2||(cur2==="on"?"off":"on");
        try{localStorage.setItem("tatap_ambient",nxt2);}catch(e){}
        document.body.classList.toggle("no-ambient",nxt2==="off");
        log("ambient "+(nxt2==="on"?"ON":"OFF"),"ok");break;
      case "sfx":case "sound":case "suara":
        if(window.TatapSfx){
          var curSfx = TatapSfx.isEnabled();
          var nxtSfx = !curSfx;
          if(args === "on" || args === "aktif" || args === "1") nxtSfx = true;
          else if(args === "off" || args === "mati" || args === "0") nxtSfx = false;
          TatapSfx.setEnabled(nxtSfx);
          if(nxtSfx) TatapSfx.play("select");
          log("efek suara UI (PS5): " + (nxtSfx ? "AKTIF" : "MATI"), "ok");
          toast("Efek Suara UI (PS5): " + (nxtSfx ? "Aktif" : "Mati"), 1400);
        }
        break;
      case "safe":case "safemode":case "modeaman":
        if(window.TatapSafeMode){
          var curSafe = TatapSafeMode.isEnabled();
          var nxtSafe = !curSafe;
          if(args === "on" || args === "aktif" || args === "1") nxtSafe = true;
          else if(args === "off" || args === "mati" || args === "0") nxtSafe = false;
          TatapSafeMode.setEnabled(nxtSafe);
          if(window.TatapSfx) TatapSfx.play("select");
          var smLabel = nxtSafe ? "Aktif (Filter Dewasa)" : "Nonaktif (Semua Konten Non-Hentai)";
          log("mode aman: " + smLabel, "ok");
          toast("Mode Aman: " + smLabel, 1600);
          loadView();
        }
        break;
      case "riwayat":case "history":
        if(args === "hapus" || args === "clear" || args === "delete"){
          try{
            await fetch("/api/history",{method:"DELETE"});
            log("riwayat menonton berhasil dihapus","ok");
            if(S.view === "riwayat"){ loadView(); }
            if(window.App && App.renderContinue){ App.renderContinue(); }
          }catch(e){log("err: "+(e&&e.message||e),"err");}
        }else{
          setView("riwayat");
        }
        break;
      case "favorit":case "bookmark":case "bookmarks":
        setView("favorit");break;
      case "logs":case "translog":
        await cmdLogs();break;
      case "apikey":case "model":case "apiurl":case "prompt":case "fansub":
      case "ollama":case "groq":case "gemini":case "openai":
        await cmdTranslateSetting(cmd,args);break;
      case "ai":case "aisetting":case "aisettings":
        if(window.openAiSettingsModal){ window.openAiSettingsModal(); }
        else { await cmdTranslateSetting("apikey", ""); }
        break;
      case "server":
        if(!args){
          var curSrv = localStorage.getItem("tatap_server") || (location.origin && location.origin !== "null" ? location.origin : "http://127.0.0.1:8767");
          log("server backend saat ini: " + curSrv, "ok");
          log("usage: :server <http://ip-komputer:8767> atau :server reset", "dim");
        }else if(args === "reset" || args === "local"){
          localStorage.removeItem("tatap_server");
          log("server backend direset ke default (local)", "ok");
          location.reload();
        }else{
          var sUrl = args.trim().replace(/\/+$/, "");
          if(!/^https?:\/\//i.test(sUrl)) sUrl = "http://" + sUrl;
          localStorage.setItem("tatap_server", sUrl);
          log("server backend disetel ke: " + sUrl, "ok");
          setTimeout(function(){ location.reload(); }, 600);
        }
        break;
      case "status":
        var extra="";
        if(S.filter&&Object.keys(S.filter).length) extra+=" filter="+JSON.stringify(S.filter);
        if(S.seasonFilter) extra+=" season="+S.seasonFilter.season+" "+S.seasonFilter.year;
        log("view="+S.view+" page="+S.page+"/"+S.total+" items="+S.items.length+(S.sel>=0?" sel="+S.sel:"")+extra,"ok");break;
      case "update":case "upgrade":
        log("memeriksa rilis terbaru ke GitHub...","dim");
        if(window.App && window.App.checkForUpdate){
          window.App.checkForUpdate(true);
        } else {
          try{
            var ures = await window.Tatap.checkUpdate(true);
            if(ures && ures.success && ures.data){
              if(ures.data.has_update){
                log("pembaruan tersedia: v" + ures.data.latest_version + " — " + ures.data.release_name,"ok");
                log("kunjungi: " + ures.data.release_url,"ok");
              } else {
                log("Tatap v" + ures.data.current_version + " adalah versi terbaru. Tidak ada update.","ok");
              }
            } else {
              log("gagal cek update: " + (ures&&ures.error||"unknown"),"err");
            }
          }catch(err){
            log("koneksi gagal: " + (err&&err.message||err),"err");
          }
        }
        break;
      case "tema":case "theme":case "mode":
        if(window.TatapTheme && window.TatapTheme.toggle){
          var newTh = window.TatapTheme.toggle();
          log("Tema beralih ke: " + (newTh === "light" ? "Mode Terang (Apple Light)" : "Mode Gelap (Obsidian Dark)"), "ok");
        }
        break;
      case "subdelay":case "suboffset":
        if(!args || args === "reset"){
          if(window.App && window.App.setSubDelay) window.App.setSubDelay(0.0, true);
          log("sinkronisasi subtitle direset ke 0.0 detik", "ok");
        }else{
          var dVal = parseFloat(args);
          if(isNaN(dVal)){
            log("usage: :subdelay <detik|reset> (cth: :subdelay -0.5 atau :subdelay +0.75)", "err");
          }else{
            if(window.App && window.App.setSubDelay) window.App.setSubDelay(dVal, true);
            log("sinkronisasi subtitle disetel ke " + (dVal > 0 ? "+" : "") + dVal + " detik", "ok");
          }
        }
        break;
      case "substyle":case "styler":case "subgaya":
        if(window.openSubStyleModal) window.openSubStyleModal();
        break;
      case "bantuan":case "help":case "?":
        $("help-overlay").classList.remove("hidden");
        $("help-body").textContent=cmdUsage();
        break;
      case "q":case "clear":
        $("cmd").value="";updateSearchClearBtn();clearLog();break;
      default:
        if(cmd.indexOf(":")===0){log("perintah tak dikenal: "+cmd+"  (ketik :bantuan)","err");}
        else{startSearch(s);}
    }
  }

  function updateSearchClearBtn(){
    var btn=$("search-clear-btn");
    var inp=$("cmd");
    if(!btn||!inp)return;
    if(inp.value.length>0){
      btn.classList.remove("hidden");
    }else{
      btn.classList.add("hidden");
    }
  }

  function onKey(e){
    var t=(e.target.tagName||"");
    var typing = t==="INPUT"||t==="SELECT"||t==="TEXTAREA";
    if((e.metaKey || e.ctrlKey) && (e.key === "k" || e.key === "K")){
      e.preventDefault();
      if(typeof App !== "undefined"){
        var sm = $("spotlight-modal");
        if(sm && !sm.classList.contains("hidden")) App.closeSpotlight();
        else App.openSpotlight();
      }
      return;
    }
    if(e.key==="Escape"){
      var sm = $("spotlight-modal");
      if(sm && !sm.classList.contains("hidden")){
        e.preventDefault();
        if(typeof App !== "undefined" && App.closeSpotlight) App.closeSpotlight();
        else sm.classList.add("hidden");
        return;
      }
      if(isModalOpen()){App.onKeyPlayer(e);return;}
      if(typing){$("cmd").blur();S.promptFoc=false;return;}
      if(S.sel>=0){S.sel=-1;renderSel();return;}
      $("cmd").value="";updateSearchClearBtn();clearLog();e.preventDefault();return;
    }
    if(e.key==="Backspace"){
      if(!typing && window.TvNavigationManager && window.TvNavigationManager.handleBack(e)){return;}
      if(isModalOpen()){App.onKeyPlayer(e);return;}
      if(!typing && S.sel>=0){S.sel=-1;renderSel();return;}
      if(typing) return; // Mengizinkan penghapusan teks normal tanpa blur
    }
    if(isModalOpen()){App.onKeyPlayer(e);return;}
    if(e.key==="/"){e.preventDefault();focusPrompt();return;}
    if(typing){return;}
    lockKbNav();

    var isInteractiveTarget = e.target && (
      e.target.tagName === "BUTTON" ||
      e.target.tagName === "A" ||
      e.target.tagName === "SELECT" ||
      e.target.getAttribute("role") === "button" ||
      (e.target.closest && (e.target.closest(".app-sidebar") || e.target.closest(".bottom-bar") || e.target.closest(".pager") || e.target.closest(".cf-sheet") || e.target.closest(".genre-sheet")))
    );
    var isCatalogCard = e.target && e.target.classList && (e.target.classList.contains("poster-card") || e.target.classList.contains("trow"));

    // Quick View Switching via Number Keys 1 - 6
    if(!e.ctrlKey && !e.metaKey && !e.altKey && e.key >= "1" && e.key <= "6"){
      var viewMap = {"1":"katalog", "2":"musim", "3":"terbaru", "4":"lanjutan", "5":"riwayat", "6":"favorit"};
      if(viewMap[e.key]){
        e.preventDefault();
        setView(viewMap[e.key]);
        return;
      }
    }

    if(e.key==="Tab"){
      if(isInteractiveTarget && !isCatalogCard){
        // Biarkan Tab menavigasi antar elemen sidebar / statusbar secara wajar
        return;
      }
      e.preventDefault();
      cycleView(e.shiftKey ? -1 : 1);
      return;
    }

    var isTxt = false;
    var cols = getGridCols();

    // Grid Navigation Accelerators: Home, End, PageUp, PageDown
    if(e.key==="Home"){
      if(S.items.length){
        e.preventDefault();
        var firstValid = 0;
        while(firstValid < S.items.length && S.items[firstValid] && S.items[firstValid].is_header) firstValid++;
        S.sel = (firstValid < S.items.length) ? firstValid : 0;
        renderSel();
      }
      return;
    }
    if(e.key==="End"){
      if(S.items.length){
        e.preventDefault();
        var lastValid = S.items.length - 1;
        while(lastValid >= 0 && S.items[lastValid] && S.items[lastValid].is_header) lastValid--;
        S.sel = (lastValid >= 0) ? lastValid : (S.items.length - 1);
        renderSel();
      }
      return;
    }
    if(e.key==="PageDown"){
      if(S.items.length){ e.preventDefault(); moveSel(cols * 2); }
      return;
    }
    if(e.key==="PageUp"){
      if(S.items.length){ e.preventDefault(); moveSel(-cols * 2); }
      return;
    }

    if(e.key==="ArrowRight"){
      if(isInteractiveTarget && !isCatalogCard) return;
      e.preventDefault();
      if(S.items.length){
        var box = $("results");
        var curCard = (box && S.sel >= 0) ? box.querySelector('.poster-card[data-idx="' + S.sel + '"]') : null;
        var useTvSpatial = window.TvNavigationManager && window.TvNavigationManager.isTvMode && window.TvNavigationManager.isTvMode();
        var rightTarget = null;
        if(useTvSpatial && curCard && window.TvNavigationManager && window.TvNavigationManager.getSpatialTarget){
          var allCards = Array.prototype.slice.call(box.querySelectorAll(".poster-card"));
          rightTarget = window.TvNavigationManager.getSpatialTarget(curCard, allCards, "right");
        } else {
          var geoRight = spatialTarget(S.sel, "right");
          if(geoRight) rightTarget = box ? box.querySelector('.poster-card[data-idx="' + geoRight.idx + '"]') : null;
        }
        if(rightTarget){
          var rIdx = parseInt(rightTarget.getAttribute("data-idx"), 10);
          if(!isNaN(rIdx) && S.items[rIdx] && !S.items[rIdx].is_header){
            S.sel = rIdx;
            renderSel();
            return;
          }
        }
        moveSel(1);
      }
      return;
    }
    if(e.key==="ArrowLeft"){
      if(isInteractiveTarget && !isCatalogCard) return;
      if(S.items.length){
        var isLeftEdge = false;
        var box = $("results");
        var curCard = (box && S.sel >= 0) ? box.querySelector('.poster-card[data-idx="' + S.sel + '"]') : null;
        var useTvSpatial = window.TvNavigationManager && window.TvNavigationManager.isTvMode && window.TvNavigationManager.isTvMode();
        var leftTarget = null;
        if(useTvSpatial && curCard && window.TvNavigationManager && window.TvNavigationManager.getSpatialTarget){
          var allCards = Array.prototype.slice.call(box.querySelectorAll(".poster-card"));
          leftTarget = window.TvNavigationManager.getSpatialTarget(curCard, allCards, "left");
          if(!leftTarget) isLeftEdge = true;
        } else {
          // Cache geometri (tanpa rect read)
          var geoLeft = spatialTarget(S.sel, "left");
          if(geoLeft) leftTarget = box ? box.querySelector('.poster-card[data-idx="' + geoLeft.idx + '"]') : null;
          else isLeftEdge = true;
        }
        if(isLeftEdge){
          e.preventDefault();
          var actSb = document.querySelector(".sidebar-nav-item.active") || document.querySelector(".sidebar-nav-item");
          if(actSb){ blurCards(); actSb.focus(); return; }
        } else if(leftTarget){
          e.preventDefault();
          var lIdx = parseInt(leftTarget.getAttribute("data-idx"), 10);
          if(!isNaN(lIdx) && S.items[lIdx] && !S.items[lIdx].is_header){
            S.sel = lIdx;
            renderSel();
            return;
          }
        }
        e.preventDefault();
        moveSel(-1);
      }
      return;
    }
    if(e.key==="ArrowDown"){
      if(isInteractiveTarget && !isCatalogCard) return;
      e.preventDefault();
      if(!S.items.length){cmdHistory(1);}else{moveSel(cols);}
      return;
    }
    if(e.key==="ArrowUp"){
      if(isInteractiveTarget && !isCatalogCard) return;
      e.preventDefault();
      if(!S.items.length){cmdHistory(-1);}else{moveSel(-cols);}
      return;
    }
    if(e.key==="Enter"){
      if(isInteractiveTarget && !isCatalogCard){
        // Biarkan aksi klik asli browser pada tombol fokus berjalan
        return;
      }
      e.preventDefault();
      if(S.sel>=0){
        openSelected();
      }else if(S.promptFoc){
        submitPrompt();
      }else{
        focusPrompt();
      }
      return;
    }
    if(e.key===" "){
      if(isInteractiveTarget && !isCatalogCard){
        // Biarkan tombol fokus (misal toggle tema atau paginasi) tertekan normal
        return;
      }
      if(S.sel>=0){
        e.preventDefault();
        openSelected();
        return;
      }
    }
    if(e.key==="["||e.key===","){e.preventDefault();pagePrev();return;}
    if(e.key==="]"||e.key==="."){e.preventDefault();pageNext();return;}
    if(isInteractiveTarget && !isCatalogCard) return;
    if(!typing&&e.key.length===1&&!e.ctrlKey&&!e.metaKey){focusPrompt();}
  }

  function focusPrompt(){
    S.promptFoc=true;
    if(typeof App !== "undefined" && App.openSpotlight){
      App.openSpotlight();
    } else {
      var inp=$("cmd");if(inp) inp.focus();
    }
  }
  function submitPrompt(){
    var inp=$("cmd");var raw=inp.value.trim();
    if(!raw)return;
    log("tatap$ "+raw);
    if(typeof App !== "undefined" && App.closeSpotlight){
      App.closeSpotlight();
    }
    if(raw.indexOf(":")===0){
      inp.value="";
      updateSearchClearBtn();
      handleCommand(raw.slice(1));
    } else {
      updateSearchClearBtn();
      handleCommand("cari "+raw);
    }
  }

  var _hIdx=0,_hPos=0;
  function cmdHistory(dir){
    var h=loadCmdHist();if(!h.length)return;
    _hPos+=dir;
    if(_hPos<0)_hPos=0;
    if(_hPos>=h.length)_hPos=h.length-1;
    $("cmd").value=h[_hPos]||"";
    var inp=$("cmd");inp.selectionStart=inp.selectionEnd=inp.value.length;
  }
  function cycleView(dir){
    if(typeof dir !== "number") dir = 1;
    var ord=["cari","musim","terbaru","lanjutan","riwayat","favorit","katalog"];
    var idx=ord.indexOf(S.view);
    if(idx < 0) idx = 0;
    var nextIdx = (idx + dir + ord.length) % ord.length;
    setView(ord[nextIdx]);
  }
  function pagePrev(){
    if(S.view==="terbaru"){
      var curIdx = SCHEDULE_DAYS.indexOf(S.scheduleDay || "");
      if(curIdx < 0) curIdx = 0;
      if(curIdx > 0){
        S.scheduleDay = SCHEDULE_DAYS[curIdx - 1];
        S.sel = -1;
        updateScheduleChips();
        loadView();
      }
      return;
    }
    if(S.view==="cari" && S.searchQuery){
      if(S.page > 1){
        S.page--;
        S.sel = -1;
        doSearch(S.searchQuery, S.page);
        try{window.scrollTo({top:0,behavior:"smooth"});}catch(_){}
      }
      return;
    }
    if(S.view==="favorit" && S.rawBookmarks){
      if(S.page>1){
        S.page--;
        S.sel = -1;
        var pageSize=24;
        var start=(S.page-1)*pageSize;
        S.items=S.rawBookmarks.slice(start,start+pageSize);
        renderResults();renderPager();
        try{window.scrollTo({top:0,behavior:"smooth"});}catch(_){}
      }
      return;
    }
    if(S.view==="riwayat" && S.rawHistory){
      if(S.page>1){
        S.page--;
        S.sel = -1;
        var pageSize=24;
        var start=(S.page-1)*pageSize;
        S.items=S.rawHistory.slice(start,start+pageSize);
        renderResults();renderPager();
        try{window.scrollTo({top:0,behavior:"smooth"});}catch(_){}
      }
      return;
    }
    if(S.page>1){
      S.page--;
      S.sel = -1;
      loadView();
      try{window.scrollTo({top:0,behavior:"smooth"});}catch(_){}
    }
  }

  function pageNext(){
    if(S.view==="terbaru"){
      var curIdx = SCHEDULE_DAYS.indexOf(S.scheduleDay || "");
      if(curIdx < 0) curIdx = 0;
      if(curIdx < SCHEDULE_DAYS.length - 1){
        S.scheduleDay = SCHEDULE_DAYS[curIdx + 1];
        S.sel = -1;
        updateScheduleChips();
        loadView();
      }
      return;
    }
    if(S.view==="cari" && S.searchQuery){
      if(S.page < S.total){
        S.page++;
        S.sel = -1;
        doSearch(S.searchQuery, S.page);
        try{window.scrollTo({top:0,behavior:"smooth"});}catch(_){}
      }
      return;
    }
    if(S.view==="favorit" && S.rawBookmarks){
      if(S.page<S.total){
        S.page++;
        S.sel = -1;
        var pageSize=24;
        var start=(S.page-1)*pageSize;
        S.items=S.rawBookmarks.slice(start,start+pageSize);
        renderResults();renderPager();
        try{window.scrollTo({top:0,behavior:"smooth"});}catch(_){}
      }
      return;
    }
    if(S.view==="riwayat" && S.rawHistory){
      if(S.page<S.total){
        S.page++;
        S.sel = -1;
        var pageSize=24;
        var start=(S.page-1)*pageSize;
        S.items=S.rawHistory.slice(start,start+pageSize);
        renderResults();renderPager();
        try{window.scrollTo({top:0,behavior:"smooth"});}catch(_){}
      }
      return;
    }
    if(S.page<S.total){
      S.page++;
      S.sel = -1;
      loadView();
      try{window.scrollTo({top:0,behavior:"smooth"});}catch(_){}
    }
  }

  function onPromptFocus(){S.promptFoc=true;$("cmd").classList.add("focus");}
  function onPromptBlur(){S.promptFoc=false;$("cmd").classList.remove("focus");setTimeout(function(){if($("cmd").value.trim()&&S.items.length){/* keep sel visible */}},50);}

  function boot(){
    var inp=$("cmd");
    inp.addEventListener("keydown",function(e){
      var sm = $("spotlight-modal");
      var isSpotlight = sm && !sm.classList.contains("hidden");

      if(e.key==="Enter"){
        e.stopPropagation();
        e.preventDefault();
        _hPos=loadCmdHist().length;
        submitPrompt();
      }
      else if(e.key==="Escape"){
        e.stopPropagation();
        e.preventDefault();
        if(isSpotlight && typeof App !== "undefined" && App.closeSpotlight){
          App.closeSpotlight();
        } else {
          inp.blur();
          S.promptFoc=false;
        }
      }
      else if(isSpotlight && e.key==="Tab"){
        e.stopPropagation();
        e.preventDefault();
        if(typeof App !== "undefined" && App.trapSpotlightFocus){
          App.trapSpotlightFocus(e.shiftKey);
        }
      }
      else if(isSpotlight && (e.key==="ArrowDown" || e.key==="ArrowUp")){
        e.stopPropagation();
        e.preventDefault();
        cmdHistory(e.key==="ArrowDown" ? 1 : -1);
      }
      else if(e.key==="ArrowDown"){
        if(S.items.length){
          e.preventDefault();
          inp.blur();
          S.promptFoc=false;
          moveSel(1);
        } else {
          e.preventDefault();cmdHistory(1);
        }
      }
      else if(e.key==="ArrowUp"){
        if(S.items.length && S.sel > 0){
          e.preventDefault();
          inp.blur();
          S.promptFoc=false;
          moveSel(-1);
        } else if(!S.items.length){
          e.preventDefault();cmdHistory(-1);
        }
      }
      else if(!isSpotlight && e.key==="Tab"){
        e.stopPropagation();
        e.preventDefault();
        cycleView(e.shiftKey ? -1 : 1);
      }
    });
    inp.addEventListener("focus",onPromptFocus);
    inp.addEventListener("blur",onPromptBlur);
    inp.addEventListener("input",function(){
      updateSearchClearBtn();
      if(inp.value.indexOf(":")===0){/* could show command hints */}
    });
    document.addEventListener("keydown",onKey);

    // Modality pin: modus mouse kembali hanya saat cursor fisik bergerak / diklik.
    document.addEventListener("mousemove",unlockKbNav,{passive:true});
    document.addEventListener("mousedown",unlockKbNav,{passive:true});

    var clearBtn = $("search-clear-btn");
    if(clearBtn){
      clearBtn.addEventListener("click", function(e){
        e.stopPropagation();
        inp.value = "";
        updateSearchClearBtn();
        clearLog();
        inp.focus();
        if(S.view === "cari"){
          setView("musim");
        }
      });
    }

    var searchWrap = $("search-input-wrap");
    if(searchWrap){
      searchWrap.addEventListener("click", function(e){
        if(e.target === clearBtn || (clearBtn && clearBtn.contains(e.target))) return;
        if(window.TvNavigationManager) window.TvNavigationManager.enterSearchTypingMode();
        else focusPrompt();
      });
      searchWrap.addEventListener("keydown", function(e){
        if(e.target === inp || (e.target && e.target.tagName === "INPUT")) return;
        if(e.key === "Enter" || e.key === " "){
          e.preventDefault();
          if(window.TvNavigationManager) window.TvNavigationManager.enterSearchTypingMode();
          else focusPrompt();
        } else if(e.key === "ArrowUp"){
          e.preventDefault();
          if(S.items.length){
            if(window.TvNavigationManager){
              window.TvNavigationManager.restoreFocusedIndex("#results", ".poster-card, .trow", S.items.length - 1, S.items.length - 1);
            } else {
              moveSel(1);
            }
          }
        }
      });
    }

    var tabsBar = $("nav-tabs-bar");
    if(tabsBar){
      tabsBar.addEventListener("keydown", function(e){
        var tabBtns = Array.prototype.slice.call(tabsBar.querySelectorAll(".nav-tab-btn"));
        var curIdx = tabBtns.indexOf(document.activeElement);
        if(curIdx < 0){
          for(var t = 0; t < tabBtns.length; t++){
            if(tabBtns[t].classList.contains("tv-focus")){ curIdx = t; break; }
          }
        }
        if(e.key === "ArrowRight"){
          e.preventDefault();
          var nextIdx = (curIdx >= tabBtns.length - 1 || curIdx < 0) ? 0 : curIdx + 1;
          if(window.TvNavigationManager) window.TvNavigationManager.setFocus(tabBtns[nextIdx], "tabs");
          else tabBtns[nextIdx].focus();
        } else if(e.key === "ArrowLeft"){
          e.preventDefault();
          var prevIdx = (curIdx <= 0) ? tabBtns.length - 1 : curIdx - 1;
          if(window.TvNavigationManager) window.TvNavigationManager.setFocus(tabBtns[prevIdx], "tabs");
          else tabBtns[prevIdx].focus();
        } else if(e.key === "ArrowDown"){
          e.preventDefault();
          var sched = $("schedule-days-bar");
          if(sched && !sched.classList.contains("hidden")){
            var firstChip = sched.querySelector(".ep-range-chip");
            if(firstChip){
              if(window.TvNavigationManager) window.TvNavigationManager.setFocus(firstChip, "chips");
              else firstChip.focus();
              return;
            }
          }
          if(S.items.length){
            if(window.TvNavigationManager){
              window.TvNavigationManager.restoreFocusedIndex("#results", ".poster-card, .trow", 0, 0);
            } else {
              moveSel(1);
            }
          }
        }
      });
    }

    var schedBar = $("schedule-days-bar");
    if(schedBar){
      schedBar.addEventListener("keydown", function(e){
        var chips = Array.prototype.slice.call(schedBar.querySelectorAll(".ep-range-chip"));
        var curIdx = chips.indexOf(document.activeElement);
        if(curIdx < 0){
          for(var c = 0; c < chips.length; c++){
            if(chips[c].classList.contains("tv-focus")){ curIdx = c; break; }
          }
        }
        if(e.key === "ArrowRight"){
          e.preventDefault();
          var nextIdx = (curIdx >= chips.length - 1 || curIdx < 0) ? 0 : curIdx + 1;
          if(window.TvNavigationManager) window.TvNavigationManager.setFocus(chips[nextIdx], "chips");
          else chips[nextIdx].focus();
        } else if(e.key === "ArrowLeft"){
          e.preventDefault();
          var prevIdx = (curIdx <= 0) ? chips.length - 1 : curIdx - 1;
          if(window.TvNavigationManager) window.TvNavigationManager.setFocus(chips[prevIdx], "chips");
          else chips[prevIdx].focus();
        } else if(e.key === "ArrowUp"){
          e.preventDefault();
          var actTab = document.querySelector(".nav-tab-btn.active") || document.querySelector(".nav-tab-btn");
          if(actTab){
            if(window.TvNavigationManager) window.TvNavigationManager.setFocus(actTab, "tabs");
            else actTab.focus();
          }
        } else if(e.key === "ArrowDown"){
          e.preventDefault();
          if(S.items.length){
            if(window.TvNavigationManager){
              window.TvNavigationManager.restoreFocusedIndex("#results", ".poster-card, .trow", 0, 0);
            } else {
              moveSel(1);
            }
          }
        }
      });
    }
    $("help-close").addEventListener("click",function(){$("help-overlay").classList.add("hidden");});
    $("help-overlay").addEventListener("click",function(e){if(e.target===$("help-overlay"))$("help-overlay").classList.add("hidden");});
    // Genre modal listeners
    $("genre-close").addEventListener("click",closeGenreModal);
    var genreModalEl = $("genre-modal");
    if(genreModalEl){
      genreModalEl.addEventListener("click",function(e){if(e.target===genreModalEl)closeGenreModal();});
      genreModalEl.addEventListener("keydown", function(e){
        if(e.key === "Escape"){
          e.preventDefault();
          e.stopPropagation();
          closeGenreModal();
        } else if(e.key === "Tab"){
          var focusables = Array.prototype.slice.call(genreModalEl.querySelectorAll("input:not([disabled]), button:not([disabled])")).filter(function(el){ return el.offsetParent !== null; });
          if(focusables.length > 0){
            e.preventDefault();
            var idx = focusables.indexOf(document.activeElement);
            if(e.shiftKey){
              var prevIdx = (idx <= 0) ? (focusables.length - 1) : (idx - 1);
              focusables[prevIdx].focus();
            } else {
              var nextIdx = (idx < 0 || idx >= focusables.length - 1) ? 0 : (idx + 1);
              focusables[nextIdx].focus();
            }
          }
        }
      });
    }
    var btnGenreReset = $("genre-reset-btn");
    if(btnGenreReset){
      btnGenreReset.addEventListener("click", function(){
        clearGenreFilter();
        closeGenreModal();
      });
    }
    var genreInput = $("genre-search");
    if(genreInput){
      genreInput.addEventListener("input", function(){
        var kw = this.value.trim().toLowerCase();
        loadGenres().then(function(list){
          var filtered = kw ? list.filter(function(g){
            return (g.title + " " + g.slug).toLowerCase().indexOf(kw) >= 0;
          }) : list;
          renderGenreList(filtered);
        });
      });
      genreInput.addEventListener("keydown", function(e){
        if(e.key === "Enter"){
          e.preventDefault();
          var firstBtn = $("genre-list").querySelector("button");
          if(firstBtn) firstBtn.click();
        } else if(e.key === "ArrowDown"){
          e.preventDefault();
          var firstBtn = $("genre-list").querySelector("button");
          if(firstBtn) firstBtn.focus();
        } else if(e.key === "Escape"){
          e.preventDefault();
          closeGenreModal();
        }
      });
    }

    var genreListEl = $("genre-list");
    if(genreListEl){
      genreListEl.addEventListener("keydown", function(e){
        var btns = Array.prototype.slice.call(genreListEl.querySelectorAll("button"));
        var idx = btns.indexOf(document.activeElement);
        if(idx < 0) return;
        if(e.key === "ArrowRight"){
          e.preventDefault();
          btns[(idx + 1) % btns.length].focus();
        } else if(e.key === "ArrowLeft"){
          e.preventDefault();
          btns[(idx - 1 + btns.length) % btns.length].focus();
        } else if(e.key === "ArrowDown"){
          e.preventDefault();
          var nextIdx = Math.min(idx + 3, btns.length - 1);
          btns[nextIdx].focus();
        } else if(e.key === "ArrowUp"){
          e.preventDefault();
          if(idx <= 2){
            var gInp = $("genre-search");
            if(gInp) gInp.focus();
          } else {
            btns[Math.max(0, idx - 3)].focus();
          }
        }
      });
    }

    // Catalog filter modal listeners
    var cfClose = $("cf-close");
    if(cfClose) cfClose.addEventListener("click", closeCatalogFilterModal);
    var cfModal = $("catalog-filter-modal");
    if(cfModal){
      cfModal.addEventListener("click", function(e){ if(e.target === cfModal) closeCatalogFilterModal(); });
      cfModal.addEventListener("keydown", function(e){
        if(e.key === "Escape"){
          e.preventDefault();
          e.stopPropagation();
          closeCatalogFilterModal();
        } else if(e.key === "Tab"){
          var focusables = Array.prototype.slice.call(cfModal.querySelectorAll("button:not([disabled]), .cf-chip, [tabindex='0']")).filter(function(el){ return el.offsetParent !== null; });
          if(focusables.length > 0){
            e.preventDefault();
            var idx = focusables.indexOf(document.activeElement);
            if(e.shiftKey){
              var prevIdx = (idx <= 0) ? (focusables.length - 1) : (idx - 1);
              focusables[prevIdx].focus();
            } else {
              var nextIdx = (idx < 0 || idx >= focusables.length - 1) ? 0 : (idx + 1);
              focusables[nextIdx].focus();
            }
          }
        } else if(e.key === "Enter" && e.target && !e.target.closest("#cf-reset-btn") && !e.target.closest("#cf-close") && !e.target.closest("#cf-btn-pick-genre")){
          e.preventDefault();
          var cfApply = $("cf-apply-btn");
          if(cfApply) cfApply.click();
        } else if(e.key === "ArrowRight" || e.key === "ArrowLeft"){
          if(e.target && e.target.classList && e.target.classList.contains("cf-chip")){
            e.preventDefault();
            var parent = e.target.closest(".cf-chips");
            if(!parent) return;
            var chips = Array.prototype.slice.call(parent.querySelectorAll(".cf-chip"));
            var idx = chips.indexOf(e.target);
            var nextIdx = e.key === "ArrowRight" ? ((idx + 1) % chips.length) : ((idx - 1 + chips.length) % chips.length);
            chips[nextIdx].click();
            chips[nextIdx].focus();
          }
        }
      });
    }
    document.querySelectorAll("#catalog-filter-modal .cf-chip").forEach(function(chip){
      chip.addEventListener("click", function(){
        var parent = chip.closest(".cf-chips");
        if(!parent) return;
        parent.querySelectorAll(".cf-chip").forEach(function(c){ c.classList.remove("active"); });
        chip.classList.add("active");
      });
    });
    var btnPickGenre = $("cf-btn-pick-genre");
    if(btnPickGenre){
      btnPickGenre.addEventListener("click", function(){
        closeCatalogFilterModal();
        openGenreModal();
      });
    }
    var btnClearCfGenre = $("cf-btn-genre-clear");
    if(btnClearCfGenre){
      btnClearCfGenre.addEventListener("click", function(e){
        e.stopPropagation();
        if(S.catalogFilter) delete S.catalogFilter.genre;
        delete S.genreFilter;
        if(S.filter && S.filter.genre) delete S.filter.genre;
        syncCatalogFilterUI();
      });
    }
    var cfReset = $("cf-reset-btn");
    if(cfReset){
      cfReset.addEventListener("click", function(){
        S.catalogFilter = {sort: "popularity", year: "", season: "", month: "", type: "", status: "", genre: ""};
        delete S.genreFilter;
        if(S.filter && S.filter.genre) delete S.filter.genre;
        syncCatalogFilterUI();
        closeCatalogFilterModal();
        setView("katalog");
      });
    }
    var cfApply = $("cf-apply-btn");
    if(cfApply){
      cfApply.addEventListener("click", function(){
        var prevGenre = (S.catalogFilter && S.catalogFilter.genre) || S.genreFilter || "";
        S.catalogFilter = {
          sort: getGroupActive("cf-chips-sort") || "popularity",
          year: getGroupActive("cf-chips-year"),
          season: getGroupActive("cf-chips-season"),
          month: getGroupActive("cf-chips-month"),
          type: getGroupActive("cf-chips-type"),
          status: getGroupActive("cf-chips-status"),
          genre: prevGenre
        };
        closeCatalogFilterModal();
        setView("katalog");
      });
    }
    var btnCatFilter = $("btn-catalog-filter");
    if(btnCatFilter){
      btnCatFilter.addEventListener("click", function(){
        openCatalogFilterModal();
      });
    }
    $("clear-hist").addEventListener("click",async function(){
      try{await fetch("/api/history",{method:"DELETE"});}catch(e){}
      App.renderContinue();log("riwayat dihapus","ok");
    });
    document.querySelectorAll("#schedule-days-bar button").forEach(function(btn){
      btn.addEventListener("click", function(){
        var d = btn.getAttribute("data-day");
        S.scheduleDay = d;
        updateScheduleChips();
        setView("terbaru");
      });
    });
    var btnPgPrev = $("pg-prev");
    if(btnPgPrev) btnPgPrev.addEventListener("click", function(e){ e.preventDefault(); pagePrev(); });
    var btnPgNext = $("pg-next");
    if(btnPgNext) btnPgNext.addEventListener("click", function(e){ e.preventDefault(); pageNext(); });
    $("sb-view").textContent="view: "+S.view;
    setView("katalog");
  }

  return {boot:boot,log:log,clearLog:clearLog,setView:setView,loadView:loadView,moveSel:moveSel,renderSel:renderSel,blurCards:blurCards,openSelected:openSelected,startSearch:startSearch,doSearch:doSearch,renderResults:renderResults,renderPager:renderPager,renderRecents:renderRecents,cmdUsage:cmdUsage,openGenreModal:openGenreModal,closeGenreModal:closeGenreModal,openCatalogFilterModal:openCatalogFilterModal,closeCatalogFilterModal:closeCatalogFilterModal,getGridCols:getGridCols,applyGenreFilter:function(genreOrSlug){applyGenreFilter(slugifyGenre(genreOrSlug));},slugifyGenre:slugifyGenre,view:function(){return S.view;},state:function(){return S;},updateSearchClearBtn:updateSearchClearBtn,pageNext:pageNext,pagePrev:pagePrev,cycleView:cycleView};
})();