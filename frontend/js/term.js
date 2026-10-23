var Tui = (function () {
  var S = {view:"katalog",items:[],sel:-1,page:1,total:1,filter:{},promptFoc:false,seasonFilter:null};
  var MAXLOG = 200;

  function $(id){return document.getElementById(id);}
  function esc(s){return String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;");}
  function isModalOpen(){
    return (!$("title-modal").classList.contains("hidden")) ||
           (!$("player-modal").classList.contains("hidden")) ||
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
  function clearLog(){$("log").classList.add("hidden");$("log").innerHTML="";}

  function loadRecents(){try{return JSON.parse(localStorage.getItem("tatap_recent")||"[]");}catch(e){return [];}}
  function loadCmdHist(){try{return JSON.parse(localStorage.getItem("tatap_hist")||"[]");}catch(e){return [];}}
  function saveCmdHist(h){try{localStorage.setItem("tatap_hist",JSON.stringify(h.slice(0,50)));}catch(e){}}

  function cmdUsage(){
    return "perintah:\n  cari <judul> | :musim | :lanjutan | :favorit | :katalog\n  :terbaru | :season <winter|spring|summer|fall> <tahun>\n  :switch [hianime|otaku] (ganti sumber video HiAnime / Otakudesu)\n  :filter [key=val...] | :filter reset\n  :genre <slug|title> | :genre | :genre --list | :genre reset\n  :tema [toggle|terang|gelap] (ganti mode terang / gelap Apple)\n  :update (cek versi rilis terbaru secara on-demand)\n  :apikey <key> | :ollama <key> | :groq <key> | :gemini <key> | :model <nama> | :apiurl <url>\n  :logs | :crt on|off|toggle | :ambient on|off|toggle\n  :riwayat | :favorit | :status | :bantuan | :q";
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
    S.view=v;S.page=1;S.sel=-1;S.items=[];clearLog();
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
    var isTxt = S.view==="cari" || S.view==="terbaru";
    if(!S.items.length){
      var emptyMsg = "Kosong.";
      if(S.view==="favorit"){
        emptyMsg = "Belum ada anime favorit tersimpan. Ketuk tombol + FAVORIT pada detail anime untuk menyimpannya ke sini.";
      }else if(S.view==="riwayat"){
        emptyMsg = "Belum ada riwayat menonton. Mulai tonton anime apa pun dan riwayat akan tercatat otomatis di sini.";
      }
      box.innerHTML="<p class='dim'>"+emptyMsg+"</p>";
      return;
    }
    if(isTxt){
      var nowTs=Math.floor(Date.now()/1000);
      var frag=document.createDocumentFragment();
      for(var i=0;i<S.items.length;i++){
        (function(a,idx){
          if(S.view==="terbaru"){
            var d=document.createElement("div");
            var aheadSec=(a.airing_at||0)-nowTs;
            var cls="trow trow-up trow-media"+(idx===S.sel?" sel":"");
            if(aheadSec>0&&aheadSec<86400) cls+=" today";
            else if(aheadSec>=86400&&aheadSec<172800) cls+=" tomorrow";
            d.className=cls;

            // Thumbnail poster
            var thumbWrap=document.createElement("div");
            thumbWrap.className="tr-thumb-wrap";
            if(a.poster){
              var img=document.createElement("img");
              img.className="tr-thumb";
              img.loading="lazy";
              img.decoding="async";
              img.alt=a.title||"";
              img.src=a.poster;
              img.onerror=function(){
                this.style.display="none";
                thumbWrap.classList.add("no-img");
                var ph=document.createElement("span");
                ph.className="tr-thumb-ph";
                ph.textContent="▶";
                thumbWrap.appendChild(ph);
              };
              thumbWrap.appendChild(img);
            } else {
              thumbWrap.classList.add("no-img");
              var ph=document.createElement("span");
              ph.className="tr-thumb-ph";
              ph.textContent="▶";
              thumbWrap.appendChild(ph);
            }
            d.appendChild(thumbWrap);

            var metaCol=document.createElement("div");
            metaCol.className="tr-badge-col";
            var when=(a.date?a.date+" · ":"")+(a.time||"");
            var spanDay=document.createElement("span");
            spanDay.className="tr-day";
            spanDay.textContent=when;
            var spanEp=document.createElement("span");
            spanEp.className="tr-ep";
            spanEp.textContent="ep "+(a.episode==null||a.episode==undefined?"?":a.episode);
            metaCol.appendChild(spanDay);
            metaCol.appendChild(spanEp);
            d.appendChild(metaCol);

            var infoCol=document.createElement("div");
            infoCol.className="tr-info";
            var spanTitle=document.createElement("span");
            spanTitle.className="tr-title";
            spanTitle.textContent=a.title||"";
            infoCol.appendChild(spanTitle);

            if(a.type || a.score){
              var subMeta=document.createElement("div");
              subMeta.className="tr-meta";
              var sm=[];
              if(a.type) sm.push(a.type);
              if(a.score) sm.push("★ "+a.score);
              subMeta.textContent=sm.join(" · ");
              infoCol.appendChild(subMeta);
            }
            d.appendChild(infoCol);

            d.tabIndex=0;
            d.setAttribute("data-idx",String(idx));
            d.addEventListener("focus",function(){
              if(S.sel!==idx){S.sel=idx;renderSel();}
            });
            d.addEventListener("keydown",function(e){
              if(e.key==="Enter"||e.key===" "){
                e.preventDefault();
                if(typeof App==="undefined"){log("App belum siap, coba lagi","err");return;}
                App.openTitle(a.id||a.slug,a.title,a.poster,a.type,a.eps_counter,a);
              }
            });
            d.addEventListener("click",function(){
              if(typeof App==="undefined"){log("App belum siap, coba lagi","err");return;}
              App.openTitle(a.id||a.slug,a.title,a.poster,a.type,a.eps_counter,a);
            });
            frag.appendChild(d);
          } else {
            var d2=document.createElement("div");
            d2.className="trow trow-media"+(idx===S.sel?" sel":"");

            var spanNum=document.createElement("span");
            spanNum.className="tr-num";
            spanNum.textContent=idx+1;
            d2.appendChild(spanNum);

            var thumbWrap2=document.createElement("div");
            thumbWrap2.className="tr-thumb-wrap";
            if(a.poster){
              var img2=document.createElement("img");
              img2.className="tr-thumb";
              img2.loading="lazy";
              img2.decoding="async";
              img2.alt=a.title||"";
              img2.src=a.poster;
              img2.onerror=function(){
                this.style.display="none";
                thumbWrap2.classList.add("no-img");
                var ph2=document.createElement("span");
                ph2.className="tr-thumb-ph";
                ph2.textContent="▶";
                thumbWrap2.appendChild(ph2);
              };
              thumbWrap2.appendChild(img2);
            } else {
              thumbWrap2.classList.add("no-img");
              var ph2=document.createElement("span");
              ph2.className="tr-thumb-ph";
              ph2.textContent="▶";
              thumbWrap2.appendChild(ph2);
            }
            d2.appendChild(thumbWrap2);

            var infoCol2=document.createElement("div");
            infoCol2.className="tr-info";
            var spanTitle2=document.createElement("span");
            spanTitle2.className="tr-title";
            spanTitle2.textContent=a.title||"";
            infoCol2.appendChild(spanTitle2);

            var subMeta2=document.createElement("div");
            subMeta2.className="tr-meta";
            var sm2=[];
            if(a.season){
              var sStr = a.season;
              if(a.year && sStr.indexOf(String(a.year)) === -1) sStr += " " + a.year;
              sm2.push(sStr);
            } else if(a.year){
              sm2.push(String(a.year));
            }
            if(a.type) sm2.push(a.type);
            if(a.eps_counter){
              sm2.push("Ep " + a.eps_counter);
            } else {
              if(a.sub) sm2.push("SUB "+a.sub);
              if(a.dub) sm2.push("DUB "+a.dub);
              if(a.eps) sm2.push(a.eps+" ep");
            }
            if(a.duration) sm2.push(a.duration);
            subMeta2.textContent=sm2.join(" · ");
            infoCol2.appendChild(subMeta2);
            d2.appendChild(infoCol2);

            d2.tabIndex=0;
            d2.setAttribute("data-idx",String(idx));
            d2.addEventListener("focus",function(){
              if(S.sel!==idx){S.sel=idx;renderSel();}
            });
            d2.addEventListener("keydown",function(e){
              if(e.key==="Enter"||e.key===" "){
                e.preventDefault();
                if(typeof App==="undefined"){log("App belum siap, coba lagi","err");return;}
                App.openTitle(a.id||a.slug,a.title,a.poster,a.type,a.eps_counter,a);
              }
            });
            d2.addEventListener("click",function(){
              if(typeof App==="undefined"){log("App belum siap, coba lagi","err");return;}
              App.openTitle(a.id||a.slug,a.title,a.poster,a.type,a.eps_counter,a);
            });
            frag.appendChild(d2);
          }
        })(S.items[i],i);
      }
      box.appendChild(frag);
    } else {
      var grid=document.createElement("div");grid.className="poster-grid";
      for(var j=0;j<S.items.length;j++){
        (function(a,idx){
          if(a.is_header){
            var h=document.createElement("div");
            h.className="lane-header-banner";
            var isLong = a.lane === "long_running";
            var col = isLong ? "#F59E0B" : "#38BDF8";
            h.style.cssText="grid-column:1 / -1;width:100%;margin:16px 0 8px 0;padding:8px 12px;background:rgba(15,23,42,0.8);border-left:4px solid "+col+";border-radius:4px;display:flex;align-items:center;justify-content:space-between;user-select:none;box-sizing:border-box;";
            h.innerHTML="<span style='font-weight:bold;font-size:12px;letter-spacing:0.04em;color:"+col+"'>"+(a.header_title||a.title||"")+"</span><span style='font-family:monospace;font-size:10px;color:#64748B'>"+(isLong?"[CONTINUOUS]":"[SEASONAL]")+"</span>";
            grid.appendChild(h);
            return;
          }
          if(S.view==="riwayat" || S.view==="favorit"){
            if(!a.id) a.id = a.slug;
            if(!a.badge && a.episode) a.badge = String(a.episode);
          }
          var isUnavail=!a.id;
          var d=document.createElement("div");
          d.className="poster-card"+(idx===S.sel?" sel":"")+(isUnavail?" unmapped":"");
          d.tabIndex=0;
          d.setAttribute("data-idx",String(idx));
          d.addEventListener("focus",function(){
            if(!isUnavail && S.sel!==idx){S.sel=idx;renderSel();}
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

          if(a.poster){
            var im=document.createElement("img");
            im.loading="lazy";
            im.decoding="async";
            im.alt=a.title||"";
            im.src=a.poster;
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

          if(a.badge){
            var bgTag=document.createElement("span");
            var isTam=a.badge==="TAMAT"||a.is_finished;
            var isLongB=a.badge==="SERIAL PANJANG"||a.is_long_running;
            var bCls=isTam?" pc-badge-tamat":(isLongB?" pc-badge-long":" pc-badge-ep");
            bgTag.className="pc-badge-tag"+bCls;
            var bText=a.badge;
            if(a.badge==="ONGOING"&&a.eps_counter){
              bText=a.eps_counter;
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
            if(a.duration)m.push(a.duration);
          }
          meta.textContent=m.join(" · ")||"Anime";
          body.appendChild(meta);
          d.appendChild(body);

          if(!isUnavail){
            d.addEventListener("click",function(){App.openTitle(a.id||a.slug,a.title,a.poster,a.type,a.eps_counter,a);});
          }
          grid.appendChild(d);
        })(S.items[j],j);
      }
      box.appendChild(grid);
    }
    if(window.TvNavigationManager){
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

  function getGridCols(){
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
    var count=S.items.length;
    var next;
    if(S.sel < 0){
      next = (d > 0) ? 0 : count - 1;
    } else {
      if(Math.abs(d) > 1){
        if(d > 0){
          if(S.sel + d >= count){
            if(S.sel >= count - getGridCols()){
              if(window.TvNavigationManager){
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
            if(window.TvNavigationManager){
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
    for(var step=0;step<count;step++){
      if(S.items[next] && !S.items[next].is_header){
        S.sel=next;
        renderSel();
        return;
      }
      next = (next + (d > 0 ? 1 : -1) + count) % count;
    }
  }

  function renderSel(){
    var box=$("results");
    if(!box)return;
    var all=box.querySelectorAll(".poster-card, .trow");
    var isTv = !!(window.TvNavigationManager && window.TvNavigationManager.isTvMode && window.TvNavigationManager.isTvMode());
    for(var i=0;i<all.length;i++){
      var itemIdx = parseInt(all[i].getAttribute("data-idx"), 10);
      var isUnm=all[i].classList.contains("unmapped");
      var isThis = (itemIdx === S.sel && !isUnm);
      all[i].classList.toggle("sel", isThis);
      if(isTv){
        all[i].classList.toggle("tv-focus", isThis);
      } else {
        all[i].classList.remove("tv-focus");
      }
    }
    if(S.sel < 0) return;
    var selEl = box.querySelector('[data-idx="' + S.sel + '"]');
    if(selEl){
      selEl.scrollIntoView({block:"nearest", inline:"nearest"});
      if(window.TvNavigationManager && isTv){
        window.TvNavigationManager.setFocus(selEl, "grid", { scroll: true });
      }
      if(document.activeElement !== selEl){
        try{selEl.focus({preventScroll:true});}catch(_){}
      }
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

  // ==== :apikey / :model / :apiurl / :ollama / :groq / :gemini ====
  var TRANSLATE_KEYS = {
    apikey: {field:"translate_apikey", label:"apikey"},
    ollama: {field:"translate_apikey", label:"apikey (Ollama Cloud)"},
    groq:   {field:"translate_apikey", label:"apikey (Groq)"},
    gemini: {field:"translate_apikey", label:"apikey (Google AI Studio)"},
    openai: {field:"translate_apikey", label:"apikey (OpenAI)"},
    model:  {field:"translate_model",  label:"model"},
    apiurl: {field:"translate_apiurl", label:"apiurl"}
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
      // Status: tampilkan ketiga nilai translate (mask apikey).
      var r = await window.Tatap.getSettings();
      var d = (r && r.success && r.data) || {};
      log("apikey : "+maskKey(d.translate_apikey||""),"ok");
      log("model  : "+(d.translate_model||"(default)"),"ok");
      log("apiurl : "+(d.translate_apiurl||"(default)"),"ok");
      if(!d.translate_apikey){
        log("Belum ada API key AI. Preset otomatis yang didukung:", "err");
        log("  • Ollama Cloud : :apikey <key>     (gratis, model: gpt-oss:20b)", "dim");
        log("  • Groq (Gratis) : :apikey gsk_...    (model: llama-3.3-70b-versatile)", "dim");
        log("  • Google AI     : :apikey AQ...      (model: gemini-3.1-flash-lite)", "dim");
        log("  • OpenAI        : :apikey sk-...      (model: gpt-4o-mini)", "dim");
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
    if(cmd === "apikey" || cmd === "ollama" || cmd === "groq" || cmd === "gemini" || cmd === "openai"){
      // Deteksi Ollama Cloud:
      // 1) Command eksplisit :ollama
      // 2) Prefix: ollama_... atau ol_...
      // 3) Format API key resmi Ollama Cloud: 32 karakter hex + titik + alphanumeric secret token (misal: afd1045d...TYA04...)
      var isOllamaKey = cmd === "ollama" ||
                        args.indexOf("ollama_") === 0 ||
                        args.indexOf("ol_") === 0 ||
                        /^[a-f0-9]{32}\.[A-Za-z0-9_-]+$/.test(args);

      if(isOllamaKey){
        payload.translate_apiurl = "https://ollama.com/v1";
        payload.translate_model = "gpt-oss:20b";
        extra = " (auto: apiurl=Ollama Cloud, model=gpt-oss:20b, cadangan gpt-oss:120b)";
      }else if(cmd === "gemini" || args.indexOf("AQ.") === 0 || args.indexOf("AIza") === 0 || args.indexOf("AQ") === 0){
        // Google Gemini key (Google AI Studio: AQ. baru / AIza legacy) -> auto-set apiurl + model Gemini Flash Lite.
        payload.translate_apiurl = "https://generativelanguage.googleapis.com/v1beta/openai";
        payload.translate_model = "gemini-3.1-flash-lite";
        extra = " (auto: apiurl=Google AI Studio, model=gemini-3.1-flash-lite)";
      }else if(cmd === "groq" || args.indexOf("gsk_") === 0){
        // Groq key -> auto-set apiurl + model Llama-3.3-70B
        payload.translate_apiurl = "https://api.groq.com/openai/v1";
        payload.translate_model = "llama-3.3-70b-versatile";
        extra = " (auto: apiurl=Groq, model=llama-3.3-70b-versatile)";
      }else if(args.indexOf("sk-or-") === 0){
        payload.translate_apiurl = "https://openrouter.ai/api/v1";
        payload.translate_model = "google/gemini-2.0-flash-exp:free";
        extra = " (auto: apiurl=OpenRouter, model=gemini-2.0-flash-exp:free)";
      }else if(cmd === "openai" || args.indexOf("sk-") === 0 || args.indexOf("sk_") === 0){
        payload.translate_apiurl = "https://api.openai.com/v1";
        payload.translate_model = "gpt-4o-mini";
        extra = " (auto: apiurl=OpenAI, model=gpt-4o-mini)";
      }else{
        extra = " (provider kustom: gunakan juga :apiurl <url> dan :model <nama> bila perlu, atau ketik :ollama <key>)";
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
      case "apikey":case "model":case "apiurl":
      case "ollama":case "groq":case "gemini":case "openai":
        await cmdTranslateSetting(cmd,args);break;
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
    if(e.key==="Escape"){
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
    if(e.key==="Tab"){e.preventDefault();cycleView(e.shiftKey ? -1 : 1);return;}

    var isTxt = S.view==="cari" || S.view==="terbaru";
    var cols = isTxt ? 1 : getGridCols();

    if(e.key==="ArrowRight"){
      e.preventDefault();
      if(S.items.length){moveSel(1);}
      return;
    }
    if(e.key==="ArrowLeft"){
      e.preventDefault();
      if(S.items.length){moveSel(-1);}
      return;
    }
    if(e.key==="ArrowDown"){
      e.preventDefault();
      if(!S.items.length){cmdHistory(1);}else{moveSel(cols);}
      return;
    }
    if(e.key==="ArrowUp"){
      e.preventDefault();
      if(!S.items.length){cmdHistory(-1);}else{moveSel(-cols);}
      return;
    }
    if(e.key==="Enter"){
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
      if(S.sel>=0){
        e.preventDefault();
        openSelected();
        return;
      }
    }
    if(e.key==="["||e.key===","){e.preventDefault();pagePrev();return;}
    if(e.key==="]"||e.key==="."){e.preventDefault();pageNext();return;}
    if(!typing&&e.key.length===1&&!e.ctrlKey&&!e.metaKey){focusPrompt();}
  }

  function focusPrompt(){
    S.promptFoc=true;
    var inp=$("cmd");inp.focus();
  }
  function submitPrompt(){
    var inp=$("cmd");var raw=inp.value.trim();
    if(!raw)return;
    log("tatap$ "+raw);
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
      e.stopPropagation();
      if(e.key==="Enter"){e.preventDefault();_hPos=loadCmdHist().length;submitPrompt();}
      else if(e.key==="Escape"){inp.blur();S.promptFoc=false;}
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
      else if(e.key==="Tab"){e.preventDefault();cycleView(e.shiftKey ? -1 : 1);}
    });
    inp.addEventListener("focus",onPromptFocus);
    inp.addEventListener("blur",onPromptBlur);
    inp.addEventListener("input",function(){
      updateSearchClearBtn();
      if(inp.value.indexOf(":")===0){/* could show command hints */}
    });
    document.addEventListener("keydown",onKey);

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
    $("genre-modal").addEventListener("click",function(e){if(e.target===$("genre-modal"))closeGenreModal();});
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
        } else if(e.key === "Escape"){
          e.preventDefault();
          closeGenreModal();
        }
      });
    }

    // Catalog filter modal listeners
    var cfClose = $("cf-close");
    if(cfClose) cfClose.addEventListener("click", closeCatalogFilterModal);
    var cfModal = $("catalog-filter-modal");
    if(cfModal) cfModal.addEventListener("click", function(e){ if(e.target === cfModal) closeCatalogFilterModal(); });
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

  return {boot:boot,log:log,clearLog:clearLog,setView:setView,loadView:loadView,moveSel:moveSel,renderSel:renderSel,openSelected:openSelected,startSearch:startSearch,doSearch:doSearch,renderResults:renderResults,renderPager:renderPager,renderRecents:renderRecents,cmdUsage:cmdUsage,openGenreModal:openGenreModal,closeGenreModal:closeGenreModal,openCatalogFilterModal:openCatalogFilterModal,closeCatalogFilterModal:closeCatalogFilterModal,getGridCols:getGridCols,applyGenreFilter:function(genreOrSlug){applyGenreFilter(slugifyGenre(genreOrSlug));},slugifyGenre:slugifyGenre,view:function(){return S.view;},state:function(){return S;},updateSearchClearBtn:updateSearchClearBtn};
})();