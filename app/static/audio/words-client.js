/* Shared static Mandarin pronunciation route for course subpages and dictionary.
 * Recording exists: direct immutable /audio/words/<file>.mp3, no TTS generation.
 * Missing or broken recording: existing /api/v3/tts remains the fallback.
 */
(function(window){
  "use strict";
  function serverUrl(text){
    return "/api/v3/tts?text="+encodeURIComponent(String(text||"").trim());
  }
  function url(text){
    text=String(text||"").trim();
    var available=window.HSK_OFFLINE_AUDIO;
    if(available&&available.has(text)){
      var file=Array.from(text).map(function(ch){return ch.charCodeAt(0)}).join("_")+".mp3";
      if(file.length>240)file=(window.HSK_OFFLINE_LONG_NAMES||{})[text]||"";
      if(file)return "/audio/words/"+file;
    }
    return serverUrl(text);
  }
  function isDirect(src){return typeof src==="string"&&src.indexOf("/audio/words/")===0;}
  function fetchAudio(text){
    var src=url(text),server=serverUrl(text);
    return fetch(src).then(function(r){
      if(!r.ok)throw new Error("audio_http_"+r.status);
      return r.blob();
    }).catch(function(err){
      if(src===server)throw err;
      return fetch(server).then(function(r){
        if(!r.ok)throw new Error("audio_http_"+r.status);
        return r.blob();
      });
    });
  }
  window.HSKOfflineAudio={serverUrl:serverUrl,url:url,isDirect:isDirect,fetchAudio:fetchAudio};
})(window);
