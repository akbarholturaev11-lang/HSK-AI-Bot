/* Li 23-state demo → trusted onboarding adapter.
 * No simulated login, course save, Pro grant, timer-based readiness or XP.
 * Both hosts use the same view, but different server-authenticated requests.
 */
(function(global){
"use strict";
var hostPwa=location.pathname.indexOf("/iphone-pwa/")===0;
var tg=global.Telegram&&global.Telegram.WebApp;
var initData=hostPwa?"":String(tg&&tg.initData||"");
var actor=null,identityKey="",trackStatus=null,launch=null;
var requestGeneration=0,requestBusy=false,initializing=true,trialEligibility=null;
var initialRender=global.render;
var originalLogin=global.loginScreen;
var originalBooks=global.books;
var originalSetTrack=global.setTrack;
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
  options=options||{};
  options.credentials=hostPwa?"same-origin":"omit";
  options.cache="no-store";
  options.redirect="error";
  options.headers=Object.assign({},actorHeaders(),options.headers||{});
  return fetch(path,options).then(function(response){
    if(!response.ok)throw errorFromResponse(response);
    return response.json();
  }).then(function(data){
    if(!data||data.ok!==true)throw new Error("server_response_invalid");
    return data;
  });
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
    focus:global.focus,streakGoal:global.streakGoal};
  try{sessionStorage.setItem("hsk_li_draft_v1:"+identityKey,JSON.stringify(payload))}catch(_){}
}
function restoreDraft(){
  if(!identityKey)return;
  try{
    var raw=sessionStorage.getItem("hsk_li_draft_v1:"+identityKey),obj=JSON.parse(raw||"null");
    if(!obj||Date.now()-Number(obj.at)>86400000||Number(obj.at)>Date.now())return;
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
  }catch(_){}
}
function clearDraft(){
  if(identityKey)try{sessionStorage.removeItem("hsk_li_draft_v1:"+identityKey)}catch(_){}
}
function setBusy(value){
  requestBusy=value;
  var buttons=document.querySelectorAll("#top button,#footer button,.choices button,.track-switch button");
  buttons.forEach(function(button){button.disabled=value});
  document.getElementById("stage").setAttribute("aria-busy",String(value));
}
function renderError(action){
  requestBusy=false;
  var stage=document.getElementById("stage");
  var box=document.createElement("div");
  box.className="li-remote-error";
  box.setAttribute("role","alert");
  box.textContent=safeMessage();
  stage.appendChild(box);
  var footer=document.getElementById("footer");
  footer.hidden=false;
  footer.replaceChildren();
  var button=document.createElement("button");
  button.type="button";button.className="cta";button.textContent=retryMessage();
  button.addEventListener("click",action);
  footer.appendChild(button);
  stage.setAttribute("aria-busy","false");
}
function isHsk30Live(levelValue){
  var t=trackStatus&&trackStatus.tracks&&trackStatus.tracks.hsk30;
  return !!(t&&Array.isArray(t.live_levels)&&t.live_levels.indexOf(levelValue)>=0);
}
function trackAvailable(){
  var t=trackStatus&&trackStatus.tracks&&trackStatus.tracks.hsk30;
  var a=t&&t.access;
  return !!(a&&a.feature_enabled!==false&&a.allowed===true&&
            Array.isArray(t.live_levels)&&t.live_levels.length);
}
function trackApi(){
  if(!hostPwa&&!initData)return Promise.reject(new Error("telegram_init_data_missing"));
  return session().then(function(){
    return api(hostPwa?"/api/v3/pwa/course-tracks":"/api/v3/course-tracks");
  });
}
function validateTrack(){
  if(!trackStatus)throw new Error("track_not_verified");
  if(global.track==="hsk30"&&!trackAvailable())throw new Error("hsk30_locked");
  if(global.track==="hsk30"&&global.level&&!isHsk30Live(global.level))
    throw new Error("hsk30_level_not_live");
}
function updateTrackUi(){
  if(global.screen!=="version")return;
  var t=document.querySelector('.track-switch button[onclick*="hsk30"]');
  if(t){
    var allowed=trackAvailable();t.disabled=!allowed;
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
    renderError(function(){loadingState(state,load,next)});
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
  var p;try{p=payload()}catch(e){renderError(saveProfile);return}
  requestBusy=true;setBusy(true);
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
  loadingState("loadLesson",function(){
    return trialStatus().then(function(result){trialEligibility=result.trial;});
  },"pro");
  // A disallowed, already-used or disabled trial must never produce a Pro CTA.
  var current=requestGeneration,ref=global.render;
  var after=global.render;
  // The actual branch decision happens in the loading completion hook below.
}
function beginTrial(){
  if(requestBusy||!trialEligibility||!trialEligibility.eligible){window.go("end");return}
  setBusy(true);
  var endpoint=hostPwa?"/api/v3/pwa/trial/start":"/api/v3/trial/start";
  guardedPost(endpoint,{}).then(function(result){
    if(!result.ok||!result.ends_at)throw new Error("trial_not_confirmed");
    requestBusy=false;global.trail.push(global.screen);global.screen="trialDone";global.render();
  }).catch(function(e){
    console.warn("[li-onboarding] trial activation",String(e&&e.message||"trial_denied").slice(0,100));
    renderError(function(){window.go("end")});
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
  return '<div class="li-real-books" role="group"><img src="/assets/'+source+
    '?v=20261003c" alt="'+alt+'" loading="eager" onerror="this.hidden=true;this.nextElementSibling.hidden=false">'+
    '<div hidden>'+originalBooks()+'</div></div>';
}
global.books=showLiveBooks;
global.loginScreen=function(mode){
  var html=originalLogin(mode);
  // Demo buttons formerly faked sign-in or unlocked Pro on click. Never ship
  // those actions. All providers use the canonical PWA auth page.
  html=html.replace(/onclick="(?:demoLogin\(\)|go\('pro'\))"/g,
    'onclick="LiRuntime.authenticate()"');
  html=html.replace(/<p class="status" role="status">[\s\S]*?<\/p>/,
    '<p class="status" role="status"></p>');
  return html;
};
global.render=function(animate){
  initialRender(animate);
  updateTrackUi();
  // Trial service has no 48-hour PWA Web Push guarantee today; show only the
  // proven server-granted state, not the demo's unimplemented push promise.
  if(global.screen==="trialDone"){
    var heading=document.querySelector("#stage .trial h2");
    if(heading)heading.textContent=word("trialOn");
  }
  if(global.screen==="profile"&&identityKey){
    var button=document.querySelector("#footer .cta");
    if(button)button.textContent=word("cont");
  }
  if(requestBusy)setBusy(true);
};
global.setTrack=function(v){
  if(requestBusy)return;
  if(v==="hsk30"&&!trackAvailable())return;
  originalSetTrack(v);saveDraft();
};
global.back=function(){
  if(requestBusy)return;
  ++requestGeneration;
  originalBack();
};
global.go=function(next){
  if(requestBusy)return;
  if(next==="login"){
    // The Mini App account is already proven by signed initData. Existing
    // learner? Enter the real course; don't ask for a fictitious sign-in.
    if(identityKey){location.assign(pageCourse());return}
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
  if(next==="signup"){saveProfile();return}
  if(next==="trialDone"){beginTrial();return}
  if(next==="pro"&&(!trialEligibility||!trialEligibility.eligible)){progress("end");return}
  if(READY_STATES.indexOf(next)>=0&&
     next==="level"&&!trackStatus){renderError(function(){window.go("loadCourse")});return}
  progress(next);
};
global.restart=toCourse;
global.LiRuntime={authenticate:function(){
  if(hostPwa)location.assign("/iphone-pwa?lang="+encodeURIComponent(global.LANG));
  else if(initData)location.assign(pageCourse());
},retryTrack:function(){window.go("loadCourse")}};
["pickLevel","toggleGoal","pickTime","pickFocus","pickStreak","setLang"].forEach(function(name){
  var method=global[name];
  if(typeof method!=="function")return;
  global[name]=function(){method.apply(this,arguments);saveDraft()};
});
async function bootstrap(){
  try{
    await session();
    var status=await statusApi();
    identityKey=userKey();
    if(status.saved){
      location.replace(pageCourse());return;
    }
    restoreDraft();
    requestBusy=false;
    global.render(false);
  }catch(e){
    console.warn("[li-onboarding] authentication/status",String(e&&e.message||"not_ready").slice(0,100));
    renderError(bootstrap);
  }finally{initializing=false}
}
global.addEventListener("pageshow",function(ev){
  if(hostPwa&&ev.persisted)session().catch(function(){location.replace("/iphone-pwa")});
});
document.addEventListener("visibilitychange",function(){
  if(hostPwa&&document.visibilityState==="visible"&&actor)
    session().catch(function(){location.replace("/iphone-pwa")});
});
// Replace pending offer UI only once status has been confirmed.
var previousOffer=offerIfEligible;
offerIfEligible=function(){
  if(requestBusy)return;
  ++requestGeneration;
  requestBusy=true;
  trialStatus().then(function(r){
    trialEligibility=r.trial||null;
    requestBusy=false;progress(trialEligibility&&trialEligibility.eligible?"pro":"end");
  }).catch(function(){
    trialEligibility=null;
    requestBusy=false;progress("end");
  });
};
global.render(false);
bootstrap();
})(window);
