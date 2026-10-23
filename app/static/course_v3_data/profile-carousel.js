(function(){
  "use strict";
  /* Presentation only: existing server-owned link, course and checkout actions. */
  var current=1,timer=null,root=null,track=null,resizeObserver=null,settleTimer=null;
  var suppressClickUntil=0,interacting=false,hovered=false;
  var ORDER=["apps","hsk30","pro"],order=ORDER.slice();
  var LABELS=(window.HSKAILocaleMap||function(_,fallback){return fallback})("ui.profile_carousel.LABELS.copy1",{
    ru:{apps:"Приложения HSK AI",appsBody:"Android, MacBook и Windows — учитесь на своём устройстве",appsCta:"Смотреть приложения",newBody:"Новые учебники HSK 1–3. Ваш прогресс сохранится.",versionCta:"Выбрать версию",proActive:"Подписка активна",proAction:"Тарифы HSK AI Pro",carousel:"Возможности аккаунта",slide:"Карточка",linkTitle:"Подключить {provider}",linkBody:"Входите в этот аккаунт через {provider}. Прогресс и подписка сохранятся.",linkCta:"Подключить",linkWait:"Ожидаем подтверждения…"},
    uz:{apps:"HSK AI ilovalari",appsBody:"Android, MacBook va Windows — o'zingizga qulay qurilmada o'qing",appsCta:"Ilovalarni ko'rish",newBody:"HSK 1–3 yangi darsliklari. Progressingiz saqlanadi.",versionCta:"Versiyani tanlash",proActive:"Obuna faol",proAction:"HSK AI Pro tariflari",carousel:"Akkaunt imkoniyatlari",slide:"Karta",linkTitle:"{provider}’ni ulash",linkBody:"Shu akkauntga {provider} orqali ham kiring. Progress va obunangiz saqlanadi.",linkCta:"Ulash",linkWait:"Tasdiqlash kutilmoqda…"},
    tj:{apps:"Барномаҳои HSK AI",appsBody:"Android, MacBook ва Windows — дар дастгоҳи худ омӯзед",appsCta:"Дидани барномаҳо",newBody:"Китобҳои нави HSK 1–3. Пешрафти шумо нигоҳ дошта мешавад.",versionCta:"Интихоби версия",proActive:"Обуна фаъол аст",proAction:"Тарифҳои HSK AI Pro",carousel:"Имкониятҳои ҳисоб",slide:"Корт",linkTitle:"Пайваст кардани {provider}",linkBody:"Ба ҳамин ҳисоб тавассути {provider} ворид шавед. Пешрафт ва обуна нигоҳ дошта мешаванд.",linkCta:"Пайваст кардан",linkWait:"Интизори тасдиқ…"}
  });
  function strings(){return LABELS[LANG]||LABELS.ru}
  function reduced(){return window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches}
  function stop(){if(timer!==null){clearTimeout(timer);timer=null}}
  function live(){return root&&root.isConnected&&document.getElementById("s-profile")?.classList.contains("on")&&!document.hidden}
  function busy(){return typeof SIGNIN_STATE!=="undefined"&&!!SIGNIN_STATE.busy}
  function availableOrder(){
    var next=ORDER.slice();
    if(typeof SIGNIN_STATE==="undefined"||!SIGNIN_STATE.loaded)return next;
    ["google","apple"].forEach(function(provider){
      if(SIGNIN_STATE.providers.indexOf(provider)>=0&&!SIGNIN_STATE.identities.some(function(it){return it.provider===provider}))next.push("link-"+provider);
    });
    return next;
  }
  function start(){
    stop();
    if(!live()||interacting||hovered||busy()||reduced()||root.contains(document.activeElement)||document.getElementById("sheet")?.classList.contains("on"))return;
    timer=setTimeout(function(){advance(current+1)},4800);
  }
  function proDetails(){
    var t=T(),p=pl(),u=(MAP&&MAP.user)||{},plan=u.plan||(isPaidUser()?"pro":"free"),until=u.access_ends_at||null;
    if(plan==="pro"||plan==="temp"){
      var status=plan==="pro"?p.statusPro:p.statusTemp;
      return {title:status,body:until?String(p.statusUntil).replace("{d}",fmtAccessDate(until)):strings().proActive,cta:plan==="pro"?p.renew:t.unlockBtn,action:"pay",renew:plan==="pro"};
    }
    if(plan==="trial")return {title:p.statusTrial,body:trialLeftText(until)||t.trialActive,cta:strings().proAction,action:"pay"};
    return {title:t.unlockTitle,body:t.unlockSub,cta:TRIAL_LOADED&&trialEligible()?t.trialCta:t.unlockBtn,action:TRIAL_LOADED&&trialEligible()?"trial":"pay"};
  }
  function slideInfo(kind){
    var copy=strings();
    if(kind==="apps")return {title:copy.apps,body:copy.appsBody,cta:copy.appsCta,icon:"devices",tone:"apps"};
    if(kind==="hsk30")return {title:"HSK 3.0",body:copy.newBody,cta:copy.versionCta,icon:"book-2",tone:"version"};
    if(kind.indexOf("link-")===0){
      var provider=kind.slice(5),name=provider==="google"?"Google":"Apple";
      return {title:copy.linkTitle.replace("{provider}",name),body:copy.linkBody.replace("{provider}",name),cta:typeof SIGNIN_STATE!=="undefined"&&SIGNIN_STATE.busy===provider?copy.linkWait:copy.linkCta,icon:"brand-"+provider,tone:kind,provider:provider};
    }
    var pro=proDetails();pro.icon="star";pro.tone="pro";return pro;
  }
  function setActive(index){
    if(!root||!track||!Number.isFinite(index))return;
    current=Math.max(0,Math.min(order.length-1,index));
    var kind=order[current],info=slideInfo(kind);
    root.classList.add("hp-promo");
    ["apps","version","pro","link-google","link-apple"].forEach(function(tone){root.classList.toggle("hp-promo-"+tone,tone===info.tone)});
    root.dataset.promoKind=kind;
    track.querySelectorAll(".hp-promo-slide").forEach(function(slide,i){
      slide.setAttribute("aria-hidden",i===current?"false":"true");
      slide.querySelector(".hp-promo-action").tabIndex=i===current?0:-1;
    });
    root.querySelectorAll("[data-promo-dot]").forEach(function(dot,i){
      dot.classList.toggle("on",i===current);dot.setAttribute("aria-current",i===current?"true":"false");
    });
    if(kind==="apps"&&live()&&window.PompDesktopDownload&&typeof PompDesktopDownload.noteProfileAppsVisible==="function")PompDesktopDownload.noteProfileAppsVisible();
  }
  function advance(to,instant){
    if(!track||!track.clientWidth)return;
    var index=(to+order.length)%order.length;
    stop();
    track.scrollTo({left:index*track.clientWidth,behavior:instant||reduced()?"auto":"smooth"});
    if(instant||reduced())setActive(index);
    start();
  }
  function doAction(explicitCta,kind){
    if(Date.now()<suppressClickUntil)return;
    kind=kind||order[current];
    if(kind.indexOf("link-")===0){
      if(availableOrder().indexOf(kind)<0||busy())return;
      App.connectIdentity(kind.slice(5));return;
    }
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
    openProfileCourseVersionBook();
  }
  function render(){
    var copy=strings();
    root.innerHTML='<div class="hp-promo-track">'+order.map(function(kind,i){
      var s=slideInfo(kind);
      return '<article class="hp-promo-slide hp-promo-'+s.tone+'" data-promo-kind="'+kind+'" role="group" aria-roledescription="'+esc(copy.slide)+'" aria-label="'+esc((i+1)+' / '+order.length+'. '+s.title)+'">'
        +'<div class="hp-promo-content"><span class="hp-promo-icon" aria-hidden="true"><i class="ti ti-'+s.icon+'"></i></span>'
        +'<div class="hp-promo-copy"><strong>'+esc(s.title)+'</strong><p>'+esc(s.body||"")+'</p></div>'
        +'<i class="ti ti-chevron-right hp-promo-chevron" aria-hidden="true"></i></div>'
        +'<div class="hp-promo-footer"><button type="button" class="hp-promo-action"'+(s.provider&&busy()?' disabled':'')+'>'+esc(s.cta)+'</button></div></article>';
    }).join("")+'</div><div class="hp-promo-dots" role="group" aria-label="'+esc(copy.carousel)+'">'+order.map(function(kind,i){
      return '<button type="button" data-promo-dot="'+i+'" aria-label="'+esc(slideInfo(kind).title)+'"></button>';
    }).join("")+'</div>';
    root.style.setProperty("--hp-dots-width",(order.length>1?19+(order.length-1)*11+12:0)+"px");
    track=root.querySelector(".hp-promo-track");
    var mountedTrack=track,mountedRoot=root;
    track.querySelectorAll(".hp-promo-slide").forEach(function(slide){
      slide.addEventListener("click",function(event){
        if(event.target.closest("button")||Date.now()<suppressClickUntil)return;
        doAction(false,slide.dataset.promoKind);
      });
      slide.querySelector(".hp-promo-action").addEventListener("click",function(event){event.stopPropagation();doAction(true,slide.dataset.promoKind)});
    });
    root.querySelectorAll("[data-promo-dot]").forEach(function(dot){dot.addEventListener("click",function(){advance(Number(dot.dataset.promoDot))})});
    track.addEventListener("scroll",function(){
      if(track!==mountedTrack||!mountedRoot.isConnected||!track.clientWidth)return;
      setActive(Math.round(track.scrollLeft/track.clientWidth));
      clearTimeout(settleTimer);settleTimer=setTimeout(start,180);
    },{passive:true});
    // Touch/trackpad motion stays native, including momentum and interruptions.
    var touchStart=null;
    track.addEventListener("touchstart",function(event){
      if(track!==mountedTrack||!mountedRoot.isConnected)return;
      interacting=true;stop();touchStart=event.touches.length===1?{x:event.touches[0].clientX,y:event.touches[0].clientY}:null;
    },{passive:true});
    track.addEventListener("touchmove",function(event){
      if(track!==mountedTrack||!mountedRoot.isConnected)return;
      if(!touchStart||event.touches.length!==1)return;
      var dx=event.touches[0].clientX-touchStart.x,dy=event.touches[0].clientY-touchStart.y;
      if(Math.abs(dx)>8&&Math.abs(dx)>Math.abs(dy))suppressClickUntil=Date.now()+450;
    },{passive:true});
    function endTouch(){if(track!==mountedTrack||!mountedRoot.isConnected)return;interacting=false;touchStart=null;start()}
    track.addEventListener("touchend",endTouch,{passive:true});track.addEventListener("touchcancel",endTouch,{passive:true});
    // Mouse dragging complements native touch/trackpad scroll in Telegram Desktop.
    var drag=null;
    track.addEventListener("pointerdown",function(event){
      if(track!==mountedTrack||!mountedRoot.isConnected)return;
      if(event.pointerType!=="mouse"||event.button!==0||event.target.closest("button"))return;
      stop();drag={id:event.pointerId,x:event.clientX,y:event.clientY,left:track.scrollLeft,moved:false};
    });
    track.addEventListener("pointermove",function(event){
      if(track!==mountedTrack||!mountedRoot.isConnected)return;
      if(!drag||event.pointerId!==drag.id)return;
      var dx=event.clientX-drag.x,dy=event.clientY-drag.y;
      if(!drag.moved&&(Math.abs(dx)<8||Math.abs(dx)<=Math.abs(dy)))return;
      if(!drag.moved){drag.moved=true;interacting=true;track.setPointerCapture(drag.id);track.style.scrollSnapType="none"}
      event.preventDefault();track.scrollLeft=drag.left-dx;suppressClickUntil=Date.now()+450;
    });
    function endDrag(event){
      if(track!==mountedTrack||!mountedRoot.isConnected||!drag||event.pointerId!==drag.id)return;
      var moved=drag.moved,delta=event.clientX-drag.x,startIndex=Math.round(drag.left/track.clientWidth);
      drag=null;interacting=false;track.style.scrollSnapType="";
      if(moved){suppressClickUntil=Date.now()+450;advance(Math.abs(delta)>=35?startIndex+(delta<0?1:-1):Math.round(track.scrollLeft/track.clientWidth))}else start();
    }
    track.addEventListener("pointerup",endDrag);track.addEventListener("pointercancel",endDrag);
    advance(current,true);setActive(current);
  }
  function mount(){
    var candidate=document.getElementById("hsk-profile-promo-root");
    if(!candidate)return;
    stop();clearTimeout(settleTimer);if(resizeObserver)resizeObserver.disconnect();
    var selected=order[current],previous=current;
    order=availableOrder();current=order.indexOf(selected);if(current<0)current=Math.min(previous,order.length-1);
    root=candidate;hovered=false;interacting=false;
    root.tabIndex=0;root.setAttribute("role","region");root.setAttribute("aria-roledescription","carousel");root.setAttribute("aria-label",strings().carousel);
    render();
    root.onkeydown=function(event){
      if(event.target!==root)return;
      if(event.key==="ArrowLeft"||event.key==="ArrowRight"){event.preventDefault();advance(current+(event.key==="ArrowRight"?1:-1))}
      if(event.key==="Enter"||event.key===" "){event.preventDefault();doAction()}
    };
    root.onfocusin=stop;root.onfocusout=function(){setTimeout(start,0)};
    root.onmouseenter=function(){hovered=true;stop()};root.onmouseleave=function(){hovered=false;start()};
    if(window.ResizeObserver){
      var observedRoot=root,observedWidth=root.clientWidth;
      resizeObserver=new ResizeObserver(function(){
        if(root!==observedRoot||!root.isConnected)return;
        var width=root.clientWidth;
        if(width>0&&Math.abs(width-observedWidth)>.5){observedWidth=width;advance(current,true)}
      });
      resizeObserver.observe(root);
    }
    start();
  }
  document.addEventListener("visibilitychange",function(){if(document.hidden)stop();else start()});
  window.HskProfileCarousel={
    mount:mount,pause:stop,
    select:function(kind){var n=order.indexOf(kind);if(n>=0)advance(n)},
    openApps:function(){var n=order.indexOf("apps");if(n>=0)advance(n);if(window.PompDesktopDownload)PompDesktopDownload.openProfileApps()}
  };
  if(document.getElementById("hsk-profile-promo-root"))mount();
  if(window.PompDesktopDownload&&PompDesktopDownload.renderProfile)PompDesktopDownload.renderProfile();
})();
