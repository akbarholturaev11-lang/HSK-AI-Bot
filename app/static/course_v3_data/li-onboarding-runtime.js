/* Li 23-state demo → trusted onboarding adapter.
 * No simulated login, course save, Pro grant, timer-based readiness or XP.
 * Both hosts use the same view, but different server-authenticated requests.
 */
(function(global){
"use strict";
// The HTML already painted a visible, retryable failure when a public JS
// asset is missing. Do not run a session, fake a completed screen or throw
// while the exact localized demo copy/character bundle is unavailable.
if(!global.T||!global.T[global.LANG]||!global.HSKCharacters||
   typeof global.HSKCharacters.render!=="function")return;
var hostPwa=location.pathname.indexOf("/iphone-pwa/")===0;
var tg=global.Telegram&&global.Telegram.WebApp;
var initData=hostPwa?"":String(tg&&tg.initData||"");
if(hostPwa){
  // The shared Mini App document must only advertise a Home Screen install
  // identity from the browser PWA route. Reuse canonical course/login assets.
  var head=document.head;
  [["apple-mobile-web-app-capable","yes"],
   ["apple-mobile-web-app-status-bar-style","default"],
   ["apple-mobile-web-app-title","HSK AI"],
   ["theme-color","#FDF9F0"]].forEach(function(pair){
     if(head.querySelector('meta[name="'+pair[0]+'"]'))return;
     var meta=document.createElement("meta");
     meta.name=pair[0];meta.content=pair[1];head.appendChild(meta);
   });
  function installLink(rel,href,media){
    var link=document.createElement("link");
    link.rel=rel;link.href=href;if(media)link.media=media;
    head.appendChild(link);
  }
  if(!head.querySelector('link[rel="manifest"]'))
    installLink("manifest","/iphone-pwa/manifest.webmanifest");
  if(!head.querySelector('link[rel="apple-touch-icon"]'))
    installLink("apple-touch-icon","/assets/hsk-ai-logo-256.png");
  [[440,956,3],[430,932,3],[402,874,3],[393,852,3],[428,926,3],
   [390,844,3],[375,812,3],[414,896,3],[414,896,2],[414,736,3],[375,667,2]]
  .forEach(function(d){
    installLink("apple-touch-startup-image",
      "/assets/startup/hsk-startup-"+(d[0]*d[2])+"x"+(d[1]*d[2])+".png",
      "(device-width: "+d[0]+"px) and (device-height: "+d[1]+"px) and (-webkit-device-pixel-ratio: "+d[2]+") and (orientation: portrait)");
  });
}
var actor=null,identityKey="",trackStatus=null,launch=null;
var justResumedGuestRegistration=false;
var OAUTH_DRAFT_MARKER="hsk_li_auth_handoff_v1";
function clearAuthHandoff(){
  try{sessionStorage.removeItem(OAUTH_DRAFT_MARKER)}catch(_){}
}
function markAuthHandoff(provider){
  // A browser-only navigation intent, not OAuth proof or a user identity.
  // Canonical PWA auth still verifies the HttpOnly session and CSRF.
  try{sessionStorage.setItem(OAUTH_DRAFT_MARKER,
    JSON.stringify({at:Date.now(),provider:provider}))}catch(_){}
}
function validAuthHandoff(){
  try{
    var marker=JSON.parse(sessionStorage.getItem(OAUTH_DRAFT_MARKER)||"null");
    return !!(marker&&["google","telegram"].indexOf(marker.provider)>=0&&
      Date.now()>=Number(marker.at)&&Date.now()-Number(marker.at)<=900000);
  }catch(_){return false}
}
var supportedProviders=null; // null while the real provider availability loads
var providerRequest=null,publicTrackPromise=null,publicTrackSnapshot=null,publicTrackAt=0,publicTrackRevalidateAt=0;
var TELEGRAM_PENDING_KEY="hskai.pwa.telegram.pending";
var TELEGRAM_URL_KEY="hskai.li.telegram.url";
var telegramPoller=null,telegramClaimBusy=false,telegramStatusKey=null,telegramStatusError=false;
var requestGeneration=0,requestBusy=false,initializing=true,trialEligibility=null;
var initialRender=global.render;
var originalLogin=global.loginScreen;
var originalBooks=global.books;
var originalSetTrack=global.setTrack;
var originalLevels=global.levels;
var originalBack=global.back;
var READY_STATES=["version","level","goal","time","focus","ready","loadLesson",
                  "habit","streak","profile","signup","pro","trialIntro","trial1",
                  "trial2","trial3","trialDone","end"];
var ERR={
  uz:"Ulanishni tekshiring va qayta urinib ko'ring.",
  ru:"Проверьте подключение и попробуйте ещё раз.",
  tj:"Пайвастро санҷед ва боз кӯшиш кунед."
};
var TRY={uz:"Qayta urinish",ru:"Попробовать снова",tj:"Боз кӯшиш кардан"};
function word(key){var lang=global.T[global.LANG]||global.T.ru;return lang[key]||""}
function safeMessage(){return ERR[global.LANG]||ERR.ru}
function retryMessage(){return TRY[global.LANG]||TRY.ru}
function pageCourse(){return hostPwa?"/iphone-pwa/course":"/course-v3.html"}
function actorHeaders(){return hostPwa?{}:{"X-Telegram-Init-Data":initData}}
function errorFromResponse(response){return new Error("server_status_"+response.status)}
function api(path,options){
  options=Object.assign({},options||{});
  options.credentials=hostPwa?"same-origin":"omit";
  options.cache="no-store";
  options.redirect="error";
  options.headers=Object.assign({},actorHeaders(),options.headers||{});
  // A broken network connection must resolve into the retryable in-page UI.
  // The source fetch remains the only truth; no simulated successful response.
  var controller=typeof AbortController==="function"?new AbortController():null;
  if(controller)options.signal=controller.signal;
  var timeoutId=null;
  var bound=new Promise(function(_,reject){
    timeoutId=setTimeout(function(){
      if(controller)controller.abort();
      reject(new Error("li_remote_timeout"));
    },options.method==="POST"?20000:12000);
  });
  // Timeout covers both response headers AND the JSON body. A server can
  // send headers then stall forever halfway through its response stream;
  // racing fetch alone would leave onboarding stuck at a loading skeleton.
  var completed=fetch(path,options).then(function(response){
    if(!response.ok)throw errorFromResponse(response);
    return response.json();
  }).then(function(data){
    if(!data||data.ok!==true)throw new Error("server_response_invalid");
    return data;
  });
  return Promise.race([completed,bound]).finally(function(){clearTimeout(timeoutId)});
}
function guardedPost(path,payload){
  var headers={"Content-Type":"application/json"};
  if(hostPwa){
    if(!actor||!actor.csrf)throw new Error("pwa_actor_unverified");
    headers["X-HSK-PWA-CSRF"]=actor.csrf;
  }
  return api(path,{method:"POST",headers:headers,
    body:JSON.stringify(payload||{})});
}
function session(){
  if(!hostPwa){
    if(!initData)return Promise.reject(new Error("telegram_init_data_missing"));
    return Promise.resolve({ok:true});
  }
  return api("/api/v3/pwa-auth/session").then(function(data){
    if(!Number.isSafeInteger(Number(data.user_id))||Number(data.user_id)<=0||
       typeof data.csrf!=="string"||!data.csrf){
      throw new Error("pwa_actor_unverified");
    }
    if(actor&&Number(actor.user_id)!==Number(data.user_id)){
      location.replace("/iphone-pwa");
      throw new Error("pwa_actor_changed");
    }
    actor=data;return actor;
  });
}
function userKey(){
  if(hostPwa)return actor?"pwa:"+actor.user_id:"";
  var id=tg&&tg.initDataUnsafe&&tg.initDataUnsafe.user&&tg.initDataUnsafe.user.id;
  return id?"miniapp:"+String(id):"telegram:verified";
}
function saveDraft(){
  if(!identityKey||requestBusy)return;
  var payload={at:Date.now(),lang:global.LANG,track:global.track,
    level:global.level,goals:global.goals.slice(),minutes:global.minutes,
    focus:global.focus,streakGoal:global.streakGoal,step:global.screen};
  try{sessionStorage.setItem("hsk_li_draft_v1:"+identityKey,JSON.stringify(payload))}catch(_){}
}
function restoreDraft(){
  if(!identityKey)return;
  try{
    var key="hsk_li_draft_v1:"+identityKey;
    var raw=sessionStorage.getItem(key);
    var claimedGuest=false;
    if(!raw&&hostPwa&&actor&&validAuthHandoff()){
      // Adopt anonymous choices ONLY after a fresh, explicit login/signup
      // started in this very browser tab. A leftover guest draft must never
      // be silently attached to an unrelated later account.
      var guestKey="hsk_li_draft_v1:pwa:guest";
      var proposed=sessionStorage.getItem(guestKey);
      var parsed=JSON.parse(proposed||"null");
      if(parsed&&parsed.step==="signup"&&Date.now()>=Number(parsed.at)&&
         Date.now()-Number(parsed.at)<=900000){
        raw=proposed;
        sessionStorage.setItem(key,raw);
        sessionStorage.removeItem(guestKey);
        claimedGuest=true;
      }
      clearAuthHandoff();
    }
    var obj=JSON.parse(raw||"null");
    if(!obj||Date.now()-Number(obj.at)>86400000||Number(obj.at)>Date.now())return;
    if(claimedGuest&&obj.step==="signup"&&hostPwa&&actor)
      justResumedGuestRegistration=true;
    if(["uz","ru","tj"].indexOf(obj.lang)>=0)global.LANG=obj.lang;
    if(obj.track==="hsk20"||obj.track==="hsk30")global.track=obj.track;
    if(obj.level===null||typeof obj.level==="string")global.level=obj.level;
    if(Array.isArray(obj.goals)){
      var choices=global.GOALS.map(function(x){return x.k});
      global.goals=obj.goals.filter(function(k,i){return choices.indexOf(k)>=0&&obj.goals.indexOf(k)===i});
    }
    if([5,10,15,20,30].indexOf(Number(obj.minutes))>=0)global.minutes=Number(obj.minutes);
    if(global.FOCUS.some(function(x){return x.k===obj.focus}))global.focus=obj.focus;
    if([7,14,30,50].indexOf(Number(obj.streakGoal))>=0)global.streakGoal=Number(obj.streakGoal);
    global.render(false);
    return typeof obj.step==="string"?obj.step:null;
  }catch(_){}
  return null;
}
function clearDraft(){
  if(identityKey)try{sessionStorage.removeItem("hsk_li_draft_v1:"+identityKey)}catch(_){}
  clearAuthHandoff();
}
function syncPending(){
  var stage=document.getElementById("stage");
  if(!stage)return;
  stage.setAttribute("aria-busy",String(requestBusy));
  stage.classList.toggle("li-request-busy",
    requestBusy&&!stage.querySelector(".loading"));
}
function setBusy(value,section){
  requestBusy=value;
  var stage=document.getElementById("stage");
  if(stage){
    stage.querySelectorAll(".li-inline-pending").forEach(function(node){node.remove()});
    if(value&&section&&!stage.querySelector(".loading")){
      // Independent status block, not a full-screen overlay or fake
      // completion state. A save/trial action remains server-authoritative.
      var block=document.createElement("div");
      block.className="li-inline-pending";
      block.dataset.section=section;
      block.setAttribute("role","status");
      block.setAttribute("aria-label",safeMessage());
      block.setAttribute("aria-busy","true");
      block.innerHTML='<span class="li-skel" aria-hidden="true"></span>'+
        '<span class="li-skel" aria-hidden="true"></span>';
      stage.appendChild(block);
    }
  }
  if(value){
    var buttons=document.querySelectorAll("#top button,#footer button,.choices button,.track-switch button");
    buttons.forEach(function(button){
      // Reads can be cancelled while still allowing the learner to go back;
      // write operations (profile, OAuth, trial) remain atomic and locked.
      if(button.classList.contains("li-loading-back"))return;
      button.disabled=true;
    });
  }
  syncPending();
}
function renderError(action,continueFree,message,primaryLabel,secondaryLabel){
  requestBusy=false;
  var stage=document.getElementById("stage");
  // An access gate has its own clear message; do not leave a loading skeleton
  // behind or present a payment restriction as a network error.
  if(message){stage.replaceChildren();stage.setAttribute("aria-busy","false")}
  // Retrying a failed save/trial must not stack an additional red error
  // block on every attempt. Keep one current, actionable failure state.
  stage.querySelectorAll(".li-remote-error").forEach(function(node){node.remove()});
  stage.querySelectorAll(".li-inline-pending").forEach(function(node){node.remove()});
  var box=document.createElement("div");
  box.className="li-remote-error";
  box.setAttribute("role","alert");
  box.textContent=message||safeMessage();
  stage.appendChild(box);
  var footer=document.getElementById("footer");
  footer.hidden=false;
  footer.replaceChildren();
  var button=document.createElement("button");
  button.type="button";button.className="cta";button.textContent=primaryLabel||retryMessage();
  button.addEventListener("click",action);
  footer.appendChild(button);
  if(typeof continueFree==="function"){
    var skip=document.createElement("button");
    skip.type="button";skip.className="cta ghost";
    skip.textContent=secondaryLabel||word("later");
    skip.addEventListener("click",continueFree);
    footer.appendChild(skip);
  }
  syncPending();
  document.querySelectorAll("#top button").forEach(function(item){item.disabled=false});
}
function isHsk30Live(levelValue){
  var t=trackStatus&&trackStatus.tracks&&trackStatus.tracks.hsk30;
  return !!(t&&Array.isArray(t.live_levels)&&t.live_levels.indexOf(levelValue)>=0);
}
function trackSelectable(){
  var t=trackStatus&&trackStatus.tracks&&trackStatus.tracks.hsk30;
  // Browsing a published HSK 3.0 standard is not a course entitlement.
  return !!(t&&t.access&&t.access.feature_enabled===true&&
            Array.isArray(t.live_levels)&&t.live_levels.length);
}
function trackAvailable(){
  var t=trackStatus&&trackStatus.tracks&&trackStatus.tracks.hsk30;
  return !!(trackSelectable()&&t.access.allowed===true);
}
function showHsk30Locked(){
  // Direct the verified learner to the existing course unlock UI; never
  // submit HSK 3.0 course data or grant paid access from this page.
  renderError(function(){location.assign(pageCourse())},function(){
    global.track="hsk20";global.level=null;saveDraft();
    window.go("loadCourse");
  },word("hsk30AccessNeeded"),word("hsk30OpenInCourse"),word("hsk30Use20"));
}
function guestTrackMetadata(force){
  // Cache ONLY anonymous public metadata, in this page's memory. Never cache
  // PWA session, Pro/trial rights, subscriptions, saved progress or CSRF.
  var now=Date.now(),cacheAge=now-publicTrackAt;
  if(!force&&publicTrackSnapshot&&cacheAge>=0&&cacheAge<120000){
    // Public-only cache is safe for first paint. Revalidate at most once
    // after the first minute rather than making an extra API request on
    // every back/forward navigation through the version selector.
    // HSK 3.0 rights, session, payments and progress are never cached.
    if(cacheAge>=60000&&!publicTrackPromise&&
       now-publicTrackRevalidateAt>=30000){
      publicTrackRevalidateAt=now;
      Promise.resolve().then(function(){
        guestTrackMetadata(true).then(function(fresh){
          if(actor||global.screen!=="version")return;
          trackStatus=fresh;updateTrackUi();
        }).catch(function(){/* safe public preview remains; retry later */});
      });
    }
    return Promise.resolve(publicTrackSnapshot);
  }
  if(publicTrackPromise)return publicTrackPromise;
  publicTrackPromise=api("/api/v3/pwa/onboarding/public-tracks").then(function(data){
    if(!data.tracks||!data.tracks.hsk30||!data.tracks.hsk30.access||
       data.tracks.hsk30.access.allowed!==false)
      throw new Error("public_metadata_untrusted");
    publicTrackSnapshot=data;publicTrackAt=Date.now();
    return data;
  }).finally(function(){publicTrackPromise=null});
  return publicTrackPromise;
}
function trackApi(){
  if(!hostPwa&&!initData)return Promise.reject(new Error("telegram_init_data_missing"));
  if(hostPwa&&!actor)return guestTrackMetadata(false);
  // Personal access decisions are always fetched from the server.
  return session().then(function(){
    return api(hostPwa?"/api/v3/pwa/course-tracks":"/api/v3/course-tracks");
  });
}
function validateTrack(){
  if(!trackStatus)throw new Error("track_not_verified");
  if(global.track==="hsk30"&&!trackSelectable())throw new Error("hsk30_locked");
  // Anonymous guests may choose a standard and level, but an authenticated
  // actor (including Telegram Mini App) must still pass server-owned access.
  if(global.track==="hsk30"&&(!hostPwa||actor)&&!trackAvailable())
    throw new Error("hsk30_locked");
  if(global.track==="hsk30"&&global.level&&!isHsk30Live(global.level))
    throw new Error("hsk30_level_not_live");
}
function updateTrackUi(){
  if(global.screen!=="version")return;
  var t=document.querySelector('.track-switch button[onclick*="hsk30"]');
  if(t){
    var allowed=trackSelectable();t.disabled=!allowed;
    t.hidden=!trackStatus||!(trackStatus.tracks&&trackStatus.tracks.hsk30&&
                trackStatus.tracks.hsk30.access&&
                trackStatus.tracks.hsk30.access.feature_enabled);
    t.setAttribute("aria-disabled",String(!allowed));
  }
}
function progress(next){global.trail.push(global.screen);global.screen=next;global.render()}
function loadingState(state,load,next){
  var current=++requestGeneration;
  progress(state);
  setBusy(true);
  Promise.resolve().then(load).then(function(){
    if(current!==requestGeneration||global.screen!==state)return;
    requestBusy=false;global.trail.push(state);global.screen=next;global.render();
  }).catch(function(reason){
    if(current!==requestGeneration||global.screen!==state)return;
    console.warn("[li-onboarding] remote loading",String(reason&&reason.message||"unavailable").slice(0,80));
    if(reason&&reason.message==="hsk30_locked"&&hostPwa&&actor&&global.track==="hsk30")
      showHsk30Locked();
    else renderError(function(){loadingState(state,load,next)});
  });
}
function validateGoalData(){
  if(!global.level||!global.goals.length||!global.minutes||!global.focus||!global.streakGoal)
    throw new Error("onboarding_choices_missing");
  validateTrack();
}
function payload(){
  validateGoalData();
  return {
    level:global.level,
    goal:global.goals[0],
    goals:global.goals.slice(),
    daily_minutes:global.minutes,
    preferred_focus:global.focus,
    streak_target_days:global.streakGoal,
    start_mode:global.level==="beginner"?"lesson_1":"continue",
    activation_variant:"li_onboarding_v1",
    language:global.LANG,
    timezone_offset_minutes:-new Date().getTimezoneOffset()
  };
}
function statusApi(){
  // The status endpoint independently verifies the session cookie. Avoid a
  // redundant /pwa-auth/session request immediately after bootstrap proved
  // the actor; never cache or manufacture the user's saved profile state.
  if(hostPwa&&actor)return api("/api/v3/pwa/onboarding/status");
  return session().then(function(){
    return api(hostPwa?"/api/v3/pwa/onboarding/status":"/api/miniapp/onboarding/status");
  });
}
function matchesSaved(selected,data){
  if(!data||!data.saved||!data.profile)return false;
  var actual=data.profile;
  var selectedLevel=selected.level,got=String(data.level||"");
  var sameLevel=selectedLevel===got||(selectedLevel==="beginner"&&got==="hsk1")||
                (selectedLevel==="hsk1"&&got==="beginner");
  return sameLevel&&actual.goal===selected.goal&&
    actual.daily_minutes===selected.daily_minutes&&
    actual.start_mode===selected.start_mode&&
    actual.preferred_focus===selected.preferred_focus&&
    actual.streak_target_days===selected.streak_target_days&&
    Array.isArray(actual.goals)&&
    JSON.stringify(actual.goals)===JSON.stringify(selected.goals);
}
function saveProfile(){
  if(requestBusy)return;
  if(hostPwa&&!actor){progress("signup");loadProviders();return}
  var p;try{p=payload()}catch(e){
    if(e&&e.message==="hsk30_locked"&&hostPwa&&actor){showHsk30Locked();return}
    renderError(saveProfile);return
  }
  setBusy(true,"save");
  var path=hostPwa?"/api/v3/pwa/onboarding":"/api/miniapp/onboarding";
  var result,hadResponse=false;
  guardedPost(path,p).then(function(value){hadResponse=true;result=value;return value;})
  .catch(function(error){
    // A lost POST response is not proof of a failed transaction. Confirm
    // the durable selection rather than blindly repeating a destructive save.
    return statusApi().then(function(saved){
      if(!matchesSaved(p,saved))throw error;
      return {ok:true,reconciled:true,level:saved.level,
              tab:"course",foundation_required:!!saved.foundation_required};
    });
  }).then(function(value){
    launch=value;
    clearDraft();
    requestBusy=false;
    document.querySelectorAll("#stage .li-inline-pending").forEach(function(node){node.remove()});
    // Installation is a presentation-only prompt after a confirmed PWA
    // onboarding save, never a permission/Pro/account-grant operation.
    // A returning signed-in learner or Telegram Mini App must not see it.
    var guide=global.HSKAILiInstallGuide;
    if(hostPwa&&justResumedGuestRegistration&&guide&&typeof guide.open==="function"&&
       guide.open({userId:Number(actor&&actor.user_id),lang:global.LANG},offerIfEligible)){
      justResumedGuestRegistration=false;
      return;
    }
    justResumedGuestRegistration=false;
    offerIfEligible();
  }).catch(function(error){
    console.warn("[li-onboarding] save not confirmed",String(error&&error.message||"save_failed").slice(0,100));
    renderError(saveProfile);
  });
}
function trialStatus(){
  return hostPwa?api("/api/v3/pwa/trial/status"):
    guardedPost("/api/v3/trial/status",{});
}
function offerIfEligible(){
  if(requestBusy)return;
  setBusy(true,"trial-status");
  trialStatus().then(function(result){
    trialEligibility=result.trial||null;
    requestBusy=false;
    progress(trialEligibility&&trialEligibility.eligible?"pro":"end");
  }).catch(function(error){
    console.warn("[li-onboarding] eligibility unavailable",String(error&&error.message||"unknown").slice(0,100));
    trialEligibility=null;
    requestBusy=false;
    // Fail closed, but allow a real retry or a free-course continuation.
    // Never misrepresent a network outage as "trial not eligible".
    renderError(offerIfEligible,function(){progress("end")});
  });
}
function beginTrial(){
  if(requestBusy||!trialEligibility||!trialEligibility.eligible){window.go("end");return}
  setBusy(true,"trial-start");
  var endpoint=hostPwa?"/api/v3/pwa/trial/start":"/api/v3/trial/start";
  function confirmed(){
    requestBusy=false;global.trail.push(global.screen);global.screen="trialDone";global.render();
  }
  function failed(e){
    console.warn("[li-onboarding] trial activation",String(e&&e.message||"trial_denied").slice(0,100));
    // Retry remains available but never claim Pro based on a timeout or
    // client-side state. The real server holds the one-time entitlement.
    renderError(beginTrial,function(){progress("end")});
  }
  guardedPost(endpoint,{}).then(function(result){
    if(!result.ok||!result.ends_at)throw new Error("trial_not_confirmed");
    confirmed();
  }).catch(function(e){
    if(!hostPwa){failed(e);return}
    // A POST can commit even when its HTTP reply is lost. Check the signed-in
    // account's actual entitlement before asking for another one-time POST.
    trialStatus().then(function(result){
      if(result.trial&&result.trial.active===true&&
         typeof result.trial.ends_at==="string"&&result.trial.ends_at){
        confirmed();return;
      }
      failed(e);
    }).catch(function(){failed(e)});
  });
}
function toCourse(){
  // No preview may claim the first lesson is ready without a server save.
  if(!launch||!launch.ok){renderError(saveProfile);return}
  var q=new URLSearchParams(location.search);
  q.set("lang",global.LANG);
  if(launch.level)q.set("level",String(launch.level));
  q.set("tab",String(launch.tab||"course"));
  q.set("onboarded","1");
  if(launch.foundation_required)q.set("foundation","1");else q.delete("foundation");
  // Lost POST response: do not fabricate a lesson ID/autostart.
  if(!launch.reconciled&&global.track==="hsk20"&&
     Number(launch.lesson)>0&&!launch.placement){
    q.set("lesson",String(launch.lesson));q.set("autostart","1");
  }else{q.delete("lesson");q.delete("autostart")}
  location.assign(pageCourse()+"?"+q.toString());
}
function showLiveBooks(){
  var source=global.track==="hsk30"?"hsk30-course-books.jpg":"hsk20-course-books.jpg";
  var alt=global.track==="hsk30"?word("hsk30Note"):word("hsk20Note");
  // This book group is visible above the fold in Li's version/loading
  // screens. The browser's own HTTP image cache is safe to show immediately:
  // neither textbook artwork nor its local fallback is private account data.
  return '<div class="li-real-books" role="group" data-image-ready="false">'+
    '<span class="li-skel li-book-placeholder" aria-hidden="true"></span>'+
    '<img src="/assets/'+source+'?v=20261003c" alt="'+alt+
    '" width="340" height="255" loading="eager" decoding="async" fetchpriority="high"'+
    ' onload="this.parentElement.dataset.imageReady=\'true\'"'+
    ' onerror="this.hidden=true;this.parentElement.dataset.imageError=\'true\'">'+
    '<div class="li-book-fallback">'+originalBooks()+'</div></div>';
}
global.books=showLiveBooks;
// Only render live levels reported by the server; demo options are visual
// references, never entitlement or launch permission.
global.levels=function(){
  var source=originalLevels();
  if(global.track!=="hsk30"||!trackStatus)return source;
  return source.filter(function(value){return isHsk30Live(value.k)});
};
global.loginScreen=function(mode,inProfile){
  var html=originalLogin(mode,inProfile),providerIndex=0;
  // Provider identity is not a demo button: each click uses the real PWA
  // OAuth service or the existing Telegram verification page.
  var order=["telegram","google","apple"];
  html=html.replace(/onclick="(?:demoLogin\(\)|go\('pro'\))"/g,
    function(){return 'onclick="LiRuntime.authenticate(\''+order[providerIndex++]+'\')"';});
  html=html.replace(/<p class="status" role="status">[\s\S]*?<\/p>/,
    '<p class="status" role="status"></p>');
  return html;
};
function loadProviders(){
  if(!hostPwa)return Promise.resolve();
  if(providerRequest)return providerRequest; // one request for concurrent UI sections
  supportedProviders=null;
  if(global.screen==="login"||global.screen==="signup")global.render(false);
  providerRequest=api("/api/v3/pwa-auth/providers").then(function(data){
    var choices=Array.isArray(data.providers)?data.providers:[];
    // Provider availability is public; still never synthesize a login grant.
    // Telegram uses the verified browser/bot handshake, not native OAuth.
    // The OAuth provider endpoint intentionally enumerates only Google/Apple.
    supportedProviders=["telegram"].concat(choices.filter(function(p){return p==="google"}));
    if(global.screen==="login"||global.screen==="signup")global.render(false);
  }).catch(function(){
    // A temporary OAuth discovery failure must not hide the independent
    // canonical Telegram sign-in method.
    supportedProviders=["telegram"];
    if(global.screen==="login"||global.screen==="signup")global.render(false);
  }).finally(function(){providerRequest=null});
  return providerRequest;
}
// Start and claim the SAME browser-bound Telegram proof as iphone-pwa-login.js.
// This page never invents identity: the verified session cookie is issued by
// /telegram/claim only after the owner approves the official bot request.
function telegramUuid(value){
  return typeof value==="string"&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}
function telegramPendingId(){
  try{var id=sessionStorage.getItem(TELEGRAM_PENDING_KEY);return telegramUuid(id)?id:null}
  catch(_){return null}
}
function telegramBotUrl(value,id){
  try{
    var url=new URL(value);
    var start=url.searchParams.get("start"),base="pwa_link_"+id;
    return url.protocol==="https:"&&url.hostname==="t.me"&&
      !url.username&&!url.password&&!url.port&&
      (start===base||["uz","ru","tj"].some(function(l){return start===base+"_"+l}))?
      url.href:null;
  }catch(_){return null}
}
function telegramMessage(key,error){
  telegramStatusKey=key;telegramStatusError=!!error;
  var node=document.querySelector("#stage .status");
  if(!node)return;
  var shared=global.HSKAI_COMMON_I18N;
  var text=shared&&shared[global.LANG]&&shared[global.LANG][key];
  node.textContent=typeof text==="string"&&text?text:safeMessage();
  if(error)node.setAttribute("role","alert");else node.setAttribute("role","status");
}
function stopTelegramPoll(){
  if(telegramPoller!==null)clearInterval(telegramPoller);
  telegramPoller=null;
}
function clearTelegramPending(){
  stopTelegramPoll();
  telegramStatusKey=null;telegramStatusError=false;
  try{sessionStorage.removeItem(TELEGRAM_PENDING_KEY);
      sessionStorage.removeItem(TELEGRAM_URL_KEY)}catch(_){}
}
async function claimTelegram(){
  var id=telegramPendingId();
  if(!hostPwa||!id||actor||telegramClaimBusy||document.visibilityState==="hidden")return;
  telegramClaimBusy=true;
  var controller=typeof AbortController==="function"?new AbortController():null;
  var timeout=setTimeout(function(){if(controller)controller.abort()},20000);
  try{
    var response=await fetch("/api/v3/pwa-auth/telegram/claim",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({link_request_id:id}),credentials:"same-origin",
      cache:"no-store",redirect:"error",signal:controller?controller.signal:undefined
    });
    var result=await response.json();
    if(!response.ok||!result||result.ok!==true)
      throw new Error(result&&typeof result.error==="string"?result.error:"pwa_telegram_unavailable");
    if(telegramPendingId()!==id)return;
    if(result.status==="complete"){
      clearTelegramPending();
      telegramMessage("desktopAuth.linked",false);
      // Consume the existing HttpOnly Li resume cookie through the canonical
      // server route, which verifies this new session before showing a course.
      location.replace("/iphone-pwa");
    }else if(result.status==="pending"&&telegramStatusKey!=="pwaAuth.telegramPending"){
      telegramMessage("pwaAuth.telegramPending",false);
    }
  }catch(error){
    if(telegramPendingId()!==id)return;
    var reason=String(error&&error.message||"");
    var terminal=reason==="pwa_telegram_not_approved"||reason==="pwa_telegram_expired";
    if(terminal){clearTelegramPending();clearAuthHandoff()}
    telegramMessage(reason==="pwa_telegram_not_approved"?"desktopAuth.cancelled":
      reason==="pwa_telegram_expired"?"desktopAuth.expired":
      "desktopAuth.providerFailed",true);
  }finally{clearTimeout(timeout);telegramClaimBusy=false}
}
function resumeTelegram(){
  if(!hostPwa||!telegramPendingId())return;
  telegramMessage("pwaAuth.telegramPending",false);
  if(telegramPoller===null)telegramPoller=setInterval(claimTelegram,2500);
  claimTelegram();
}
function authenticate(provider){
  if(requestBusy)return;
  if(!hostPwa){
    if(initData)location.assign(pageCourse());
    return;
  }
  if(actor){location.assign(pageCourse());return}
  if(!supportedProviders||supportedProviders.indexOf(provider)<0)return;
  if(telegramPendingId()){
    if(provider!=="telegram"&&telegramClaimBusy){
      // Do not start a second provider while the server may be issuing a
      // Telegram session cookie for the first, already-approved identity.
      telegramMessage("pwaAuth.telegramPending",false);
      return;
    }
    if(provider==="telegram"){
      var url=null;
      try{url=telegramBotUrl(sessionStorage.getItem(TELEGRAM_URL_KEY),telegramPendingId())}catch(_){}
      resumeTelegram();
      if(url)location.assign(url);
      return;
    }
    // Switching from Telegram to Google must not leave a background claim
    // capable of taking over the other provider's verified browser session.
    clearTelegramPending();
  }
  // No browser action here grants an account: all identity comes from the
  // canonical verified Google OAuth or Telegram browser-bound link proof.
  saveDraft();
  setBusy(true,"provider");
  api("/api/v3/pwa/onboarding/li/resume",{method:"POST"}).then(function(){
    markAuthHandoff(provider);
    if(provider==="telegram"){
      // Keep the original progress bubble/panda in this tab: do not open the
      // unrelated "Welcome" login screen merely to launch the same API.
      return api("/api/v3/pwa-auth/telegram/start",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({language:global.LANG})
      }).then(function(data){
        if(!telegramUuid(data.link_request_id))throw new Error("invalid_telegram_link");
        var url=telegramBotUrl(data.authorize_url,data.link_request_id);
        if(!url)throw new Error("invalid_telegram_link");
        sessionStorage.setItem(TELEGRAM_PENDING_KEY,data.link_request_id);
        sessionStorage.setItem(TELEGRAM_URL_KEY,url);
        setBusy(false);
        // The launch is asynchronous but remains on this page until Telegram
        // opens. Restore the back control disabled during the resume POST.
        global.render(false);
        resumeTelegram();
        location.assign(url);
      });
    }
    return api("/api/v3/pwa-auth/start",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({provider:provider,language:global.LANG})
    }).then(function(data){
      if(typeof data.authorize_url!=="string"||!data.authorize_url.startsWith("https://"))
        throw new Error("provider_url_invalid");
      location.assign(data.authorize_url);
    });
  }).catch(function(error){
    clearAuthHandoff();
    if(provider==="telegram")clearTelegramPending();
    console.warn("[li-onboarding] provider launch",String(error&&error.message||"unavailable").slice(0,100));
    renderError(function(){authenticate(provider)});
  });
}
global.render=function(animate){
  initialRender(animate);
  updateTrackUi();
  // Trial service has no 48-hour PWA Web Push guarantee today; show only the
  // proven server-granted state, not the demo's unimplemented push promise.
  if(global.screen==="trialDone"){
    var heading=document.querySelector("#stage .trial h2");
    if(heading)heading.textContent=word("trialOn");
  }
  if(global.screen==="profile"&&identityKey&&(!hostPwa||actor)){
    var button=document.querySelector("#footer .cta");
    if(button)button.textContent=word("cont");
  }
  syncPending();
  if(global.screen==="signup"||global.screen==="login"){
    var actions=document.querySelector("#stage .actions");
    if(actions&&hostPwa&&supportedProviders===null){
      actions.setAttribute("aria-busy","true");
      actions.insertAdjacentHTML("beforeend",
        '<span class="li-skel li-provider-placeholder" aria-hidden="true"></span>'+
        '<span class="li-skel li-provider-placeholder" aria-hidden="true"></span>');
    }else if(actions)actions.setAttribute("aria-busy","false");
    var providerButtons=document.querySelectorAll("#stage .provider");
    ["telegram","google","apple"].forEach(function(provider,i){
      var button=providerButtons[i];if(!button)return;
      button.hidden=provider==="apple" || (hostPwa&&supportedProviders===null) || (
        supportedProviders!==null&&supportedProviders.indexOf(provider)<0
      );
      button.disabled=hostPwa&&(!supportedProviders||
        supportedProviders.indexOf(provider)<0);
    });
  }
  if(telegramStatusKey&&(global.screen==="signup"||global.screen==="login"))
    telegramMessage(telegramStatusKey,telegramStatusError);
  if(requestBusy)setBusy(true);
};
global.setTrack=function(v){
  if(requestBusy)return;
  if(v==="hsk30"&&!trackSelectable())return;
  originalSetTrack(v);saveDraft();
};
global.back=function(){
  if(hostPwa&&global.screen==="signup"&&telegramPendingId()){
    clearTelegramPending();telegramStatusKey=null;clearAuthHandoff();
  }
  if(requestBusy){
    if(global.screen!=="loadCourse"&&global.screen!=="loadLesson")return;
    // A slow read must not trap the learner. The generation check prevents
    // late JSON from moving a cancelled screen forward.
    ++requestGeneration;requestBusy=false;
    originalBack();syncPending();return;
  }
  ++requestGeneration;
  originalBack();
};
global.go=function(next){
  if(requestBusy)return;
  if(next==="login"){
    if(!hostPwa&&identityKey){location.assign(pageCourse());return}
    if(hostPwa&&actor){location.assign(pageCourse());return}
    progress("login");loadProviders();return;
  }
  if(next==="loadCourse"){
    loadingState("loadCourse",function(){
      return trackApi().then(function(d){trackStatus=d;
        if(global.track==="hsk30"&&!trackAvailable()){global.track="hsk20";global.level=null}
      });
    },"version");return;
  }
  if(next==="loadLesson"){
    loadingState("loadLesson",function(){
      return trackApi().then(function(d){trackStatus=d;validateTrack()});
    },"habit");return;
  }
  // PWA guests choose Telegram/Google directly on the last profile step.
  // Internally retain "signup" so same-tab draft/resume and verified OAuth
  // callbacks keep their existing protections; remove the redundant CTA page.
  if(next==="profile"&&hostPwa&&!actor){progress("signup");loadProviders();return}
  if(next==="signup"){
    if(hostPwa&&!actor){progress("signup");loadProviders();return}
    saveProfile();return
  }
  if(next==="trialDone"){beginTrial();return}
  if(next==="pro"&&(!trialEligibility||!trialEligibility.eligible)){progress("end");return}
  if(READY_STATES.indexOf(next)>=0&&
     next==="level"&&!trackStatus){renderError(function(){window.go("loadCourse")});return}
  progress(next);
};
global.restart=toCourse;
global.LiRuntime={authenticate:authenticate,
  retryTrack:function(){window.go("loadCourse")}};
["pickLevel","toggleGoal","pickTime","pickFocus","pickStreak","setLang"].forEach(function(name){
  var method=global[name];
  if(typeof method!=="function")return;
  global[name]=function(){method.apply(this,arguments);saveDraft()};
});
async function bootstrap(){
  try{
    if(hostPwa){
      try{await session()}
      catch(error){
        if(error&&error.message==="server_status_401"){
          // This is a public panda-first UI, not a public user account.
          // All course writes remain inaccessible until verified OAuth.
          actor=null;identityKey="pwa:guest";
          var guestStep=restoreDraft();
          // Safari back/reload must keep the original speech/panda/provider
          // screen while a fresh, same-tab Telegram approval is pending.
          // A stale or unrelated draft cannot be used as login proof.
          if(telegramPendingId()){
            if(guestStep==="signup"&&validAuthHandoff()&&global.level&&
               global.goals.length&&global.minutes&&global.focus&&global.streakGoal)
              global.screen="signup";
            else {clearTelegramPending();clearAuthHandoff()}
          }
          requestBusy=false;global.render(false);
          loadProviders();
          resumeTelegram();
          return;
        }
        throw error;
      }
    }else{
      await session();
    }
    clearTelegramPending();
    var status=await statusApi();
    identityKey=userKey();
    if(status.saved){
      // Existing learners should not leave stale anonymous choices that
      // a later account could inadvertently inherit on this device.
      if(hostPwa){
        try{sessionStorage.removeItem("hsk_li_draft_v1:pwa:guest")}catch(_){}
      }
      clearDraft();
      location.replace(pageCourse());return;
    }
    var resumedStep=restoreDraft();
    requestBusy=false;
    if(hostPwa&&actor&&resumedStep==="signup"&&
       global.level&&global.goals.length&&global.minutes&&global.focus&&global.streakGoal){
      // Revalidate *personal* course access after OAuth before any saved
      // draft is attached to this verified actor. Do not trust anonymous
      // public track preview as an HSK 3.0 entitlement.
      loadingState("loadCourse",function(){
        return trackApi().then(function(data){
          trackStatus=data;validateGoalData();
        });
      },"profile");
    }else{
      global.render(false);
    }
  }catch(e){
    console.warn("[li-onboarding] authentication/status",String(e&&e.message||"not_ready").slice(0,100));
    renderError(bootstrap);
  }finally{initializing=false}
}
global.addEventListener("pageshow",function(ev){
  if(!hostPwa)return;
  if(!actor&&telegramPendingId()){resumeTelegram();return}
  if(ev.persisted&&actor)session().catch(function(){location.replace("/iphone-pwa")});
});
document.addEventListener("visibilitychange",function(){
  if(!hostPwa||document.visibilityState!=="visible")return;
  if(!actor&&telegramPendingId()){resumeTelegram();return}
  if(actor)session().catch(function(){location.replace("/iphone-pwa")});
});
global.addEventListener("focus",function(){
  if(hostPwa&&!actor&&telegramPendingId())resumeTelegram();
});
global.addEventListener("pagehide",stopTelegramPoll);
global.render(false);
bootstrap();
})(window);
