function apiBase(){
  var s = localStorage.getItem("tatap_server");
  if(s) return s.replace(/\/+$/,"");
  if(location.protocol === "file:" || !location.origin || location.origin === "null"){
    return "http://127.0.0.1:8767";
  }
  return "";
}
async function jget(u){var r=await fetch(apiBase()+u);return r.json();}
async function jpost(u,b){var r=await fetch(apiBase()+u,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b||{})});return r.json();}
async function jdel(u){var r=await fetch(apiBase()+u,{method:"DELETE"});return r.json();}
window.Tatap={
search:function(q,source,page){return jget("/api/search?q="+encodeURIComponent(q)+(source?"&source="+encodeURIComponent(source):"")+(page?"&page="+page:""));},
catalog:function(p){return jget("/api/catalog?page="+(p||1));},
seasonNow:function(p){return jget("/api/seasonal?which=now&page="+(p||1));},
stillAiring:function(p){return jget("/api/seasonal?which=airing&page="+(p||1));},
seasonBy:function(name,year,page){return jget("/api/seasonal?season="+encodeURIComponent(name)+"&year="+(year||0)+"&page="+(page||1));},
upcoming:function(days,day){return jget("/api/upcoming-episodes?days="+(days||7)+"&day="+(day||"today"));},
schedule:function(day){return jget("/api/schedule?day="+(day||"today"));},
filters:function(){return jget("/api/filters");},
browse:function(params,page){
  var qs = "";
  for (var k in params) if (params[k]) qs += "&"+encodeURIComponent(k)+"="+encodeURIComponent(params[k]);
  return jget("/api/browse?page="+(page||1)+qs);
},
episodes:function(slug){return jget("/api/anime/"+encodeURIComponent(slug)+"/episodes");},
animeDetail:function(slug){return jget("/api/anime/"+encodeURIComponent(slug)+"/detail");},
relations:function(slug,title){return jget("/api/anime/"+encodeURIComponent(slug)+"/relations?title="+encodeURIComponent(title||""));},
resolve:function(slug,ep,mode,q,source,force,title){return jget("/api/stream/resolve?slug="+encodeURIComponent(slug)+"&ep="+ep+"&mode="+(mode||"sub")+"&q="+(q||"best")+(source?"&source="+encodeURIComponent(source):"")+(force?"&force=true":"")+(title?"&title="+encodeURIComponent(title):""));},
genres:function(){return jget("/api/genres");},
ping:function(){return jget("/api/ping");},
health:function(){return jget("/api/health");},
history:function(){return jget("/api/history");},
saveHist:function(b){return jpost("/api/history",b);},
getProgress:function(slug,ep){return jget("/api/progress?slug="+encodeURIComponent(slug)+"&ep="+encodeURIComponent(ep));},
saveProgress:function(slug,ep,progress,duration){return jpost("/api/progress",{slug:slug,episode:ep,progress:progress,duration:duration||0});},
deleteProgress:function(slug,ep){return jdel("/api/progress?slug="+encodeURIComponent(slug)+"&ep="+encodeURIComponent(ep));},
bookmarks:function(){return jget("/api/bookmarks");},
addBookmark:function(b){return jpost("/api/bookmarks",b);},
removeBookmark:function(slug){return jdel("/api/bookmarks/"+encodeURIComponent(slug));},
checkBookmark:function(slug){return jget("/api/bookmarks/check?slug="+encodeURIComponent(slug));},
playMPV:function(b){return jpost("/api/play-mpv",b);},
// Settings (termasuk sub_lang).
getSettings:function(){return jget("/api/settings");},
setSetting:function(b){return jpost("/api/settings",b);},
checkUpdate:function(force){return jget("/api/update/check"+(force?"?force=true":""));},
uploadCustomSub:function(b){return jpost("/api/player/sub_custom",b);},
// OpenSubtitles: cari daftar rilis subtitle & unduh + merge dengan subtitle bawaan anime.
searchOpenSubtitles:function(title,slug,ep,lang){return jget("/api/subtitles/opensubtitles?title="+encodeURIComponent(title||"")+"&slug="+encodeURIComponent(slug||"")+"&ep="+encodeURIComponent(ep||1)+"&lang="+encodeURIComponent(lang||"id"));},
mergeOpenSubtitle:function(b){return jpost("/api/player/sub_opensubtitles_merge",b);}
};

