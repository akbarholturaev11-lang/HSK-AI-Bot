(function(){
  "use strict";
  /* Compact profile-only carousel. Paywall and course switch remain server-owned. */
  var current=0, timer=null, root=null, suppressClickUntil=0;
  var ORDER=["apps","hsk30","pro"];
  var LABELS={
    ru:{apps:"Приложения HSK AI",appsBody:"Android, MacBook и Windows — учитесь на своём устройстве",appsCta:"Смотреть приложения",newBody:"Новые учебники HSK 1–3. Ваш прогресс сохранится.",versionCta:"Выбрать версию",confirmTitle:"Перейти на HSK 3.0?",confirmBody:"После подтверждения откроется сохранённый уровень или выбор уровня при первом переходе.",confirm:"Продолжить",cancel:"Отмена",proActive:"Подписка активна",proAction:"Тарифы HSK AI Pro",renew:"Продлить Pro",loading:"Проверяем доступ…"},
    uz:{apps:"HSK AI ilovalari",appsBody:"Android, MacBook va Windows — o'zingizga qulay qurilmada o'qing",appsCta:"Ilovalarni ko'rish",newBody:"HSK 1–3 yangi darsliklari. Progressingiz saqlanadi.",versionCta:"Versiyani tanlash",confirmTitle:"HSK 3.0 ga o'tasizmi?",confirmBody:"Tasdiqlagach oldingi darajangiz tiklanadi yoki birinchi kirishda daraja tanlaysiz.",confirm:"Davom etish",cancel:"Bekor qilish",proActive:"Obuna faol",proAction:"HSK AI Pro tariflari",renew:"Pro ni uzaytirish",loading:"Ruxsat tekshirilmoqda…"},
    tj:{apps:"Барномаҳои HSK AI",appsBody:"Android, MacBook ва Windows — дар дастгоҳи худ омӯзед",appsCta:"Дидани барномаҳо",newBody:"Китобҳои нави HSK 1–3. Пешрафти шумо нигоҳ дошта мешавад.",versionCta:"Интихоби версия",confirmTitle:"Ба HSK 3.0 гузарем?",confirmBody:"Пас аз тасдиқ сатҳи пешина барқарор мешавад ё ҳангоми бори аввал сатҳро интихоб мекунед.",confirm:"Идома",cancel:"Бекор кардан",proActive:"Обуна фаъол аст",proAction:"Тарифҳои HSK AI Pro",renew:"Тамдиди Pro",loading:"Дастрасӣ санҷида мешавад…"}
  };
  function strings(){return LABELS[LANG]||LABELS.ru}
  function stop(){if(timer!==null){clearInterval(timer);timer=null}}
  function live(){return document.getElementById("s-profile")?.classList.contains("on") && !document.hidden}
  function advance(to){current=(to+ORDER.length)%ORDER.length;render();start()}
  function start(){stop();if(!live()||!root)return;timer=setInterval(function(){current=(current+1)%ORDER.length;render()},4800)}
  function proDetails(){
    var t=T(),p=pl(),u=(MAP&&MAP.user)||{},plan=u.plan||(isPaidUser()?"pro":"free"),until=u.access_ends_at||null;
    if(plan==="pro"||plan==="temp"){
      var status=plan==="pro"?p.statusPro:p.statusTemp;
      return {title:status,body:until?String(p.statusUntil).replace("{d}",fmtAccessDate(until)):strings().proActive,cta:plan==="pro"?p.renew:t.unlockBtn,action:"pay",renew:plan==="pro"};
    }
    if(plan==="trial")return {title:p.statusTrial,body:trialLeftText(until)||t.trialActive,cta:strings().proAction,action:"pay"};
    return {title:t.unlockTitle,body:t.unlockSub,cta:TRIAL_LOADED&&trialEligible()?t.trialCta:t.unlockBtn,action:TRIAL_LOADED&&trialEligible()?"trial":"pay"};
  }
  function slideInfo(){
    var t=T(),copy=strings(),kind=ORDER[current];
    if(kind==="apps")return {title:copy.apps,body:copy.appsBody,cta:copy.appsCta,icon:"devices",tone:"apps",kind:kind};
    if(kind==="hsk30")return {title:"HSK 3.0",body:copy.newBody,cta:copy.versionCta,icon:"books",tone:"version",kind:kind};
    var pro=proDetails();pro.icon="star";pro.tone="pro";pro.kind="pro";return pro;
  }
  function render(){
    if(!root||!root.isConnected)return;
    var s=slideInfo(),html='<div class="hp-promo-content">'
      +'<span class="hp-promo-icon" aria-hidden="true"><i class="ti ti-'+(s.icon==="devices"?"devices":s.icon==="books"?"book-2":"star")+'"></i></span>'
      +'<div class="hp-promo-copy"><strong>'+esc(s.title)+'</strong><p>'+esc(s.body||"")+'</p></div>'
      +'<i class="ti ti-chevron-right hp-promo-chevron" aria-hidden="true"></i></div>'
      +'<div class="hp-promo-footer"><button type="button" class="hp-promo-action">'+esc(s.cta)+'</button>'
      +'<div class="hp-promo-dots" role="group" aria-label="Slides">'+ORDER.map(function(x,i){return '<button type="button" data-promo-dot="'+i+'" aria-label="'+(i+1)+'" aria-current="'+(i===current?'true':'false')+'" class="'+(i===current?"on":"")+'"></button>'}).join("")+'</div></div>';
    root.innerHTML=html;
    root.className="hp-promo hp-promo-"+s.tone;
    root.setAttribute("aria-label",s.title+". "+(s.body||""));
    var act=root.querySelector(".hp-promo-action");
    act.addEventListener("click",function(event){event.stopPropagation();doAction(true)});
    root.querySelectorAll("[data-promo-dot]").forEach(function(dot){
      dot.addEventListener("click",function(event){event.stopPropagation();advance(Number(dot.dataset.promoDot))});
    });
  }
  function doAction(explicitCta){
    if(Date.now()<suppressClickUntil)return;
    var kind=ORDER[current];
    if(kind==="apps"){
      if(window.PompDesktopDownload&&PompDesktopDownload.openProfileApps)PompDesktopDownload.openProfileApps();
      return;
    }
    if(kind==="hsk30"){openHsk30();return}
    var p=proDetails();
    if(p.action==="trial"&&explicitCta===true){if(!TRIAL_LOADED||!trialEligible())return;App.startTrial("profile");return}
    App.goPay(p.renew?"profile_renewal":"profile_subscription");
  }
  function openHsk30(){
    if(currentCourseTrack()==="hsk30"){App.show("course");return}
    var copy=strings();
    courseTrackStatus(true).then(function(status){
      var access=status&&status.tracks&&status.tracks.hsk30&&status.tracks.hsk30.access;
      if(!access||access.feature_enabled===false){renderHsk30AccessGate(status);return}
      var html='<h2 class="hp-confirm-title">'+esc(copy.confirmTitle)+'</h2>'
        +'<p class="hp-confirm-body">'+esc(copy.confirmBody)+'</p>'
        +'<div class="hp-confirm-buttons"><button type="button" onclick="HskProfileCarousel.confirmHsk30()">'+esc(copy.confirm)+'</button>'
        +'<button type="button" class="hp-confirm-cancel" onclick="App.closeSheet()">'+esc(copy.cancel)+'</button></div>';
      App.openSheet(html);
      document.getElementById("sheet").classList.add("profile-apps-choice");
    }).catch(function(){showHsk30AccessGate()});
  }
  function confirmHsk30(){
    App.closeSheet();
    // Centralized course-track flow restores saved band when has_state is true.
    openHsk30PromoLevelPicker();
  }
  function mount(){
    root=document.getElementById("hsk-profile-promo-root");
    if(!root)return;
    root.tabIndex=0;
    root.setAttribute("role","button");
    root.addEventListener("click",function(event){
      if(event.target.closest("button")||Date.now()<suppressClickUntil)return;
      doAction();
    });
    root.onkeydown=function(event){
      if(event.key==="ArrowLeft"||event.key==="ArrowRight"){event.preventDefault();advance(current+(event.key==="ArrowRight"?1:-1))}
      if((event.key==="Enter"||event.key===" ")&&event.target===root){event.preventDefault();doAction()}
    };
    var startX=null;
    root.addEventListener("touchstart",function(e){if(e.touches.length===1)startX=e.touches[0].clientX},{passive:true});
    root.addEventListener("touchend",function(e){
      if(startX===null)return;
      var delta=e.changedTouches[0].clientX-startX;startX=null;
      if(Math.abs(delta)>=35){suppressClickUntil=Date.now()+450;advance(current+(delta<0?1:-1))}
    },{passive:true});
    render();start();
  }
  document.addEventListener("visibilitychange",function(){if(document.hidden)stop();else start()});
  window.HskProfileCarousel={
    mount:mount,pause:stop,
    select:function(kind){var n=ORDER.indexOf(kind);if(n>=0){current=n;render();start()}},
    confirmHsk30:confirmHsk30,
    openApps:function(){current=0;render();if(window.PompDesktopDownload)PompDesktopDownload.openProfileApps()}
  };
  // On initial deep links, course-v3 may already have rendered profile.
  if(document.getElementById("hsk-profile-promo-root"))mount();
  if(window.PompDesktopDownload&&PompDesktopDownload.renderProfile)PompDesktopDownload.renderProfile();
})();