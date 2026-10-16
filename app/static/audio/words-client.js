/* Shared Mandarin audio for Course V3, practice, dictionary and AI Voice.
 * Pre-rendered: immutable /audio/words/*.mp3, with browser HTTP caching.
 * New: Edge/Gemini generates once; store the validated response in IndexedDB.
 * Playback tries preloaded local audio, then the existing server fallback.
 * Private browsing / WebView storage eviction is possible: never depend on
 * IndexedDB availability for a learner to hear an audio prompt.
 */
(function(window){
  "use strict";

  var DB_NAME="hsk-ai-mandarin-audio", STORE="generated-v1";
  var RATE="-10%", VOICE="zh-CN-XiaoxiaoNeural";
  var MAX_BYTES=16*1024*1024;
  var MEMORY_BYTES=18*1024*1024, MEMORY_CLIPS=180;
  var dbTask=null, networkPending=Object.create(null);
  var memoryUrls=Object.create(null), memoryBytes=0;
  var remembered=Object.create(null);

  function clean(text){return String(text||"").trim();}
  function key(text){return VOICE+"|"+RATE+"|"+clean(text);}
  function isAudio(blob){
    return !!(blob&&typeof blob.size==="number"&&
      blob.size>=128&&blob.size<=MAX_BYTES&&
      (!blob.type||/^audio\/(?:mpeg|mp3|wav|x-wav|wave|ogg)(?:;|$)/i.test(blob.type)));
  }
  function serverUrl(text){
    return "/api/v3/tts?text="+encodeURIComponent(clean(text));
  }
  function url(text){
    text=clean(text);
    var available=window.HSK_OFFLINE_AUDIO;
    if(available&&available.has(text)){
      var file=Array.from(text).map(function(ch){return ch.charCodeAt(0)}).join("_")+".mp3";
      if(file.length>240)file=(window.HSK_OFFLINE_LONG_NAMES||{})[text]||"";
      if(file)return "/audio/words/"+file;
    }
    return serverUrl(text);
  }
  function isDirect(src){
    return typeof src==="string"&&src.indexOf("/audio/words/")===0;
  }

  function openDb(){
    if(dbTask)return dbTask;
    if(!window.indexedDB)return Promise.resolve(null);
    dbTask=new Promise(function(resolve){
      var request,done=false;
      function finish(value){if(!done){done=true;resolve(value);}}
      try{
        request=window.indexedDB.open(DB_NAME,1);
        request.onupgradeneeded=function(){
          var database=request.result;
          if(!database.objectStoreNames.contains(STORE)){
            var store=database.createObjectStore(STORE,{keyPath:"key"});
            store.createIndex("savedAt","savedAt");
          }
        };
        request.onsuccess=function(){
          request.result.onversionchange=function(){try{request.result.close()}catch(e){}dbTask=null;};
          finish(request.result);
        };
        request.onerror=function(){finish(null)};
        request.onblocked=function(){finish(null)};
      }catch(e){finish(null)}
    });
    return dbTask;
  }

  function stored(text){
    return openDb().then(function(database){
      if(!database)return null;
      return new Promise(function(resolve){
        try{
          var tx=database.transaction(STORE,"readonly");
          var request=tx.objectStore(STORE).get(key(text));
          request.onsuccess=function(){
            var value=request.result;
            resolve(value&&isAudio(value.blob)?value.blob:null);
          };
          request.onerror=function(){resolve(null)};
          tx.onabort=function(){resolve(null)};
        }catch(e){resolve(null)}
      });
    });
  }

  function save(text,blob){
    if(!isAudio(blob))return Promise.resolve(false);
    return openDb().then(function(database){
      if(!database)return false;
      return new Promise(function(resolve){
        try{
          var tx=database.transaction(STORE,"readwrite");
          tx.objectStore(STORE).put({key:key(text),blob:blob,savedAt:Date.now()});
          tx.oncomplete=function(){resolve(true)};
          tx.onerror=function(){resolve(false)};
          tx.onabort=function(){resolve(false)};
        }catch(e){resolve(false)}
      });
    });
  }

  function rememberUrl(text,blob){
    text=clean(text);
    if(memoryUrls[text])return memoryUrls[text];
    if(!isAudio(blob)||!window.URL||!window.URL.createObjectURL)return null;
    // Keep a small working set in RAM, but retain every successful download
    // in IndexedDB; past recordings are not automatically deleted.
    if(memoryBytes+blob.size>MEMORY_BYTES||Object.keys(memoryUrls).length>=MEMORY_CLIPS)return null;
    var src=window.URL.createObjectURL(blob);
    memoryUrls[text]=src;
    memoryBytes+=blob.size;
    return src;
  }
  function cachedUrl(text){return memoryUrls[clean(text)]||null;}

  // Open the most recently generated audio directly from device storage on
  // next Mini App launch. This avoids asynchronous work inside iOS play().
  function warmRecent(){
    return openDb().then(function(database){
      if(!database)return 0;
      return new Promise(function(resolve){
        var total=0;
        try{
          var tx=database.transaction(STORE,"readonly");
          var cursor=tx.objectStore(STORE).index("savedAt").openCursor(null,"prev");
          cursor.onsuccess=function(){
            var c=cursor.result;
            if(!c||total>=MEMORY_CLIPS||memoryBytes>=MEMORY_BYTES){resolve(total);return;}
            var value=c.value;
            if(value&&isAudio(value.blob)&&typeof value.key==="string"){
              var phrase=value.key.slice((VOICE+"|"+RATE+"|").length);
              if(value.key===key(phrase)&&rememberUrl(phrase,value.blob))total++;
            }
            c.continue();
          };
          cursor.onerror=function(){resolve(total)};
          tx.onabort=function(){resolve(total)};
        }catch(e){resolve(total)}
      });
    });
  }

  // Prefer the local MP3/WAV even if the originating Railway instance no
  // longer holds its synthesized file. No provider call on a cache hit.
  function fetchAudio(text){
    text=clean(text);
    if(!text||text.length>240)return Promise.reject(new Error("invalid_audio_text"));
    if(networkPending[text])return networkPending[text];
    networkPending[text]=stored(text).then(function(saved){
      if(saved){rememberUrl(text,saved);return saved;}
      var src=url(text),server=serverUrl(text);
      function download(address){
        return fetch(address).then(function(response){
          if(!response.ok)throw new Error("audio_http_"+response.status);
          return response.blob();
        }).then(function(blob){
          if(!isAudio(blob))throw new Error("invalid_audio_data");
          // Existing bundled MP3 files are already immutable and cacheable;
          // only *newly generated* audio needs a persistent device copy.
          if(address!==server)return blob;
          return save(text,blob).then(function(){return blob;});
        });
      }
      return download(src).catch(function(err){
        if(src===server)throw err;
        return download(server);
      });
    }).then(function(blob){
      rememberUrl(text,blob);
      return blob;
    }).finally(function(){delete networkPending[text]});
    return networkPending[text];
  }

  // The first iOS tap starts Audio.play() directly in the user gesture.
  // When the source is generated by the server, obtain the audio bytes
  // (usually from HTTP cache) and persist them without blocking playback.
  // No second Edge/Gemini generation: the backend coalesces and caches by key.
  function rememberPlayed(text,src){
    text=clean(text);
    if(!text||src!==serverUrl(text)||cachedUrl(text)||remembered[text])return;
    remembered[text]=true;
    fetchAudio(text).catch(function(){delete remembered[text]});
  }

  // Prime a given sentence in advance when lesson cards become visible.
  function prime(text){return fetchAudio(text).then(function(){return cachedUrl(text)})}

  window.HSKOfflineAudio={
    serverUrl:serverUrl,url:url,isDirect:isDirect,fetchAudio:fetchAudio,
    cachedUrl:cachedUrl,rememberPlayed:rememberPlayed,prime:prime,
    warmRecent:warmRecent
  };
  // Do not block app startup if WebView storage is unavailable.
  warmRecent().catch(function(){});
})(window);
