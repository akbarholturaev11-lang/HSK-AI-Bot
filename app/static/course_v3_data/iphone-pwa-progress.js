/* Browser-PWA XP/Streak destination (selectively recovered from Professional45). */
/* Full-screen, server-backed XP/Streak destinations for the real learner PWA.
   UIUX-002: no fake XP history or inferred month-wide activity. */
(function () {
  "use strict";
  if(location.pathname!=="/iphone-pwa/course")return;
  var root = null, origin = null, originScreen = "course", active = null, saving = false, viewId = 0, wrapWasInert = false;
  /* Copy is read from the canonical course catalog (localization/ui/<lang>/course.json,
     pwaProgress keys); no inline translation dictionary. */
  var COPY_KEYS = ["back", "streak", "xp", "days", "dayOne", "dayFew", "dayMany", "total", "today", "week", "daily", "goal", "change", "choose", "calendar", "unknown", "legendYes", "legendNo", "legendToday", "legendOther", "legendFuture", "earned", "lesson", "other", "nohistory", "continue", "unavailable", "retry", "saveError", "left", "record", "save"];
  function lang() {
    var all = window.HSKAI_COURSE_I18N || {}, code = typeof LANG !== "undefined" ? LANG : "ru";
    var own = all[code] || {}, ru = all.ru || {}, out = {};
    COPY_KEYS.forEach(function (k) {
      var v = own["pwaProgress." + k];
      out[k] = typeof v === "string" && v ? v : (ru["pwaProgress." + k] || "");
    });
    return out;
  }
  function state() {return (typeof MAP !== "undefined" && MAP && MAP.progress) || null;}
  function setup() {return (typeof STUDY_SETUP !== "undefined" && STUDY_SETUP) || (typeof MAP !== "undefined" && MAP && MAP.study_setup) || {};}
  function safeNum(n) {return (typeof n === "number" && Number.isFinite(n) && n >= 0) ? Math.floor(n) : null;}
  function localeName() {return ({ru:"ru-RU",uz:"uz-UZ",tj:"tg-TJ"})[typeof LANG!=="undefined"?LANG:"ru"]||"ru-RU";}
  function fmt(n) {if(n==null)return "—";try{return n.toLocaleString(localeName())}catch(_){return String(n)}}
  function html(value) {return String(value==null?"":value).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}
  function dayUnit(n,t) {
    if((typeof LANG==="undefined"?"ru":LANG)!=="ru")return t.dayMany;
    try {var form=new Intl.PluralRules("ru-RU").select(Math.abs(n));return t[form==="one"?"dayOne":form==="few"?"dayFew":"dayMany"]||t.dayMany;}
    catch(_){return t.dayMany;}
  }
  function remainingText(t,n) {return t.left.replace("{count}",fmt(n)).replace("{unit}",dayUnit(n,t));}
  function iso(s) {
    if(typeof s!=="string"||!/^\d{4}-\d{2}-\d{2}$/.test(s))return null;
    var date=new Date(s+"T00:00:00Z");return Number.isFinite(date.getTime())&&date.toISOString().slice(0,10)===s?s:null;
  }
  function calendar(p) {
    var t=lang(),today=iso(p.local_date),week=iso(p.week_start);
    if(!today) return '<div class="p45-progress-empty">'+html(t.unavailable)+'</div>';
    var y=Number(today.slice(0,4)),m=Number(today.slice(5,7))-1,d=Number(today.slice(8,10));
    var count=new Date(Date.UTC(y,m+1,0)).getUTCDate(),offset=(new Date(Date.UTC(y,m,1)).getUTCDay()+6)%7;
    var hasWeek=Array.isArray(p.week_activity_dates)&&week&&week<=today&&new Date(today+"T00:00:00Z")-new Date(week+"T00:00:00Z")<7*86400000;
    var known=new Set(hasWeek?p.week_activity_dates.filter(iso):[]);
    var start=week, end=null;
    if(start) {var startDate=new Date(start+"T00:00:00Z");end=new Date(startDate.getTime()+6*86400000).toISOString().slice(0,10);}
    var locale=localeName(),head=Array.from({length:7},function(_,i){
      return '<div class="p45-cal-weekday" role="columnheader">'+html(new Date(Date.UTC(2024,0,1+i)).toLocaleDateString(locale,{weekday:"short",timeZone:"UTC"}))+'</div>';
    }).join("");
    var days="";
    for(var i=0;i<offset;i++) days+='<div class="p45-cal-pad" aria-hidden="true"></div>';
    for(var day=1;day<=count;day++){
      var key=y+"-"+String(m+1).padStart(2,"0")+"-"+String(day).padStart(2,"0");
      var todayFlag=day===d, future=day>d, inKnown=!!(hasWeek && start && end && key>=start && key<=end);
      var status=future?"future":inKnown&&known.has(key)?"active":inKnown&&!todayFlag?"missed":"unknown";
      var dateLabel=new Date(Date.UTC(y,m,day)).toLocaleDateString(locale,{weekday:"long",day:"numeric",month:"long",year:"numeric",timeZone:"UTC"});
      var stateLabel=status==="active"?t.legendYes:status==="missed"?t.legendNo:status==="unknown"?t.legendOther:t.legendFuture;
      days+='<div class="p45-cal-day '+status+(todayFlag?" today":"")+'" role="img" aria-label="'+html(dateLabel+(todayFlag?" · "+t.legendToday:"")+" · "+stateLabel)+'">'+day+'</div>';
    }
    var monthLabel=new Date(Date.UTC(y,m,1)).toLocaleDateString(locale,{month:"long",year:"numeric",timeZone:"UTC"});
    return '<div class="p45-progress-sub">'+html(monthLabel)+'</div>'
      +'<div class="p45-calendar" role="group" aria-label="'+html(t.calendar+" · "+monthLabel)+'">'+head.replace(/ role="columnheader"/g, ' aria-hidden="true"')+days+'</div>'
      +'<p class="p45-progress-note">'+html(t.unknown)+'</p>'
      +'<div class="p45-progress-legend"><span class="active">'+html(t.legendYes)+'</span><span class="missed">'+html(t.legendNo)+'</span><span class="unknown">'+html(t.legendOther)+'</span><span class="today">'+html(t.legendToday)+'</span><span class="future">'+html(t.legendFuture)+'</span></div>';
  }
  function copy() {
    var t=lang(),p=state(),st=setup();
    if(!p) return '<div class="p45-progress-empty" role="status">'+html(t.unavailable)+
      '</div><button class="p45-progress-primary" type="button" data-p45="retry">'+html(t.retry)+'</button>';
    if(active==="xp"){
      var total=safeNum(p.xp),daily=safeNum(p.daily_xp),weekly=safeNum(p.weekly_xp);
      var goal=safeNum(st.daily_goal_xp),width=goal&&daily!=null?Math.min(100,daily/goal*100):0;
      return '<div class="p45-progress-hero"><span class="p45-progress-kicker">'+html(t.total)+'</span><strong>'+fmt(total)+'</strong><small>XP</small></div>'
        +'<div class="p45-progress-stats"><section class="p45-progress-card"><h2>'+html(t.today)+'</h2><strong>'+fmt(daily)+' XP</strong>'+(goal&&daily!=null?'<div class="p45-progress-track"><i style="width:'+width+'%"></i></div>':'')+'<p>'+html(t.daily)+': '+fmt(goal)+' XP</p></section>'
        +'<section class="p45-progress-card"><h2>'+html(t.week)+'</h2><strong>'+fmt(weekly)+' XP</strong></section></div>'
        +'<h2 class="p45-progress-section">'+html(t.earned)+'</h2><div class="p45-progress-list"><div>'+html(t.lesson)+'</div><div>'+html(t.other)+'</div></div>'
        +'<p class="p45-progress-note">'+html(t.nohistory)+'</p>'
        +'<button type="button" class="p45-progress-primary" data-p45="continue">'+html(t.continue)+'</button>';
    }
    var now=safeNum(p.streak),longest=safeNum(p.longest_streak);
    var target=[7,14,30,50].includes(st.streak_target_days)?st.streak_target_days:null;
    var width=target && now!=null?Math.min(100,now/target*100):0;
    return '<div class="p45-progress-hero"><strong>'+fmt(now)+'</strong><small>'+html(now==null?t.days:dayUnit(now,t))+'</small></div>'
      +'<section class="p45-progress-card"><div class="p45-progress-line"><span>'+html(t.goal)+'</span><b>'+(target?fmt(target)+" "+html(dayUnit(target,t)):html(t.choose))+'</b></div>'
      +(target&&now!=null?'<div class="p45-progress-track"><i style="width:'+width+'%"></i></div>'
        +'<p>'+html(remainingText(t,Math.max(0,target-now)))+'</p>':'')
      +'<div class="p45-progress-line"><span>'+html(t.record)+'</span><b>'+fmt(longest)+' '+html(dayUnit(longest==null?0:longest,t))+'</b></div>'
      +'<button type="button" class="p45-progress-secondary" data-p45="select"'+(saving?' disabled aria-busy="true"':'')+'>'+html(saving?t.save:t.change)+'</button><div class="p45-progress-save-status" role="status"></div></section>'
      +'<h2 class="p45-progress-section">'+html(t.calendar)+'</h2><section class="p45-progress-card">'+calendar(p)+'</section>'
      +'<button type="button" class="p45-progress-primary" data-p45="continue">'+html(t.continue)+'</button>';
  }
  function refresh() {
    if(!root)return;
    var t=lang(),body=root.querySelector(".p45-progress-body"),focus=document.activeElement;
    var action=focus&&root.contains(focus)&&focus.getAttribute("data-p45");
    body.innerHTML=copy();
    root.querySelector(".p45-progress-title").textContent=active==="xp"?t.xp:t.streak;
    root.querySelector(".p45-progress-back").setAttribute("aria-label",t.back);
    root.setAttribute("aria-label",active==="xp"?t.xp:t.streak);
    if(action&&action!=="back"){
      var next=root.querySelector('[data-p45="'+(action==="goal"?"select":action)+'"]:not([disabled])');
      (next||root.querySelector(".p45-progress-back")).focus({preventScroll:true});
    }
  }
  function open(kind) {
    if(kind!=="xp" && kind!=="streak")return;
    if(!lang().streak||!lang().xp)return;
    if(root){active=kind;refresh();return;}
    active=kind;viewId++;origin=document.activeElement;originScreen=typeof SCREEN!=="undefined"?SCREEN:"course";
    root=document.createElement("section");
    root.id="p45-progress";root.className="on";root.setAttribute("role","main");
    root.setAttribute("aria-label",kind==="xp"?lang().xp:lang().streak);
    root.innerHTML='<div class="p45-progress-header"><button type="button" class="p45-progress-back" data-p45="back" aria-label="'+html(lang().back)+'"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg></button>'
      +'<h1 class="p45-progress-title"></h1></div><div class="p45-progress-body" tabindex="-1"></div>';
    document.body.appendChild(root);
    root.addEventListener("click",handleClick);
    document.addEventListener("keydown",handleKeydown);
    document.documentElement.classList.add("p45-detail-open");
    var wrap=document.querySelector(".wrap");if(wrap){wrapWasInert=wrap.inert;wrap.inert=true;}
    refresh();
    root.querySelector(".p45-progress-back").focus({preventScroll:true});
    if(typeof NavBack!=="undefined")NavBack.sync();
  }
  function close() {
    if(!root)return;
    var kind=active;root.remove();root=null;active=null;viewId++;
    document.removeEventListener("keydown",handleKeydown);
    document.documentElement.classList.remove("p45-detail-open");
    var wrap=document.querySelector(".wrap");if(wrap)wrap.inert=wrapWasInert;
    var target=origin&&origin.isConnected&&origin.matches('button,a[href],input,[tabindex]')?origin:document.querySelector('#s-'+originScreen+' [data-progress="'+kind+'"]')||document.querySelector('#nav button.on');
    if(target&&!wrapWasInert)target.focus({preventScroll:true});
    if(typeof NavBack!=="undefined")NavBack.sync();
  }
  function handleKeydown(event) {
    if(!root)return;
    if(event.key==="Escape"){event.preventDefault();event.stopPropagation();if(typeof NavBack!=="undefined")NavBack.goBack();else close();return}
    if(event.key!=="Tab"||!root)return;
    var controls=[].slice.call(root.querySelectorAll('button:not([disabled])'));
    if(!controls.length)return;
    if(!root.contains(document.activeElement)){controls[0].focus();event.preventDefault();return;}
    if(event.shiftKey&&document.activeElement===controls[0]){controls[controls.length-1].focus();event.preventDefault()}
    else if(!event.shiftKey&&document.activeElement===controls[controls.length-1]){controls[0].focus();event.preventDefault()}
  }
  function handleClick(event) {
    var button=event.target.closest("[data-p45]");if(!button)return;
    var act=button.getAttribute("data-p45");
    if(act==="back"){close();return}
    if(act==="continue"){close();if(typeof App!=="undefined")App.show("course");return}
    if(act==="retry"){
      if(button.disabled||typeof refreshCourseProgress!=="function")return;
      var retryView=viewId;button.disabled=true;button.setAttribute("aria-busy","true");
      refreshCourseProgress(true).then(function(){if(root&&viewId===retryView)refresh()});return;
    }
    if(act==="select"){
      if(saving)return;
      var existing=root.querySelector(".p45-progress-goals");
      if(existing){existing.remove();button.setAttribute("aria-expanded","false");return;}
      button.insertAdjacentHTML("afterend",
        '<div class="p45-progress-goals" role="group" aria-label="'+html(lang().choose)+'">'
        +[7,14,30,50].map(function(n){return '<button type="button" data-p45="goal" data-value="'+n+'" aria-pressed="'+(setup().streak_target_days===n)+'">'+n+' '+html(dayUnit(n,lang()))+'</button>';}).join("")+'</div>');
      button.setAttribute("aria-expanded","true");root.querySelector('[data-p45="goal"]').focus();return;
    }
    if(act==="goal"){
      var n=Number(button.getAttribute("data-value"));if(![7,14,30,50].includes(n)||saving)return;
      if(typeof savePreferences!=="function"){return}
      var saveView=viewId,saveRoot=root,map=typeof MAP!=="undefined"?MAP:null,owner=typeof PWA_COURSE_USER_ID!=="undefined"?PWA_COURSE_USER_ID:null;
      var controller=new AbortController(),timer=setTimeout(function(){controller.abort()},10000);
      saving=true;
      root.querySelectorAll('[data-p45="goal"],[data-p45="select"]').forEach(function(control){control.disabled=true});
      root.querySelector('.p45-progress-save-status').textContent=lang().save;
      savePreferences({streak_target_days:n},{signal:controller.signal}).then(function(j){
        if(typeof MAP!=="undefined"&&MAP!==map||typeof PWA_COURSE_USER_ID!=="undefined"&&PWA_COURSE_USER_ID!==owner)return;
        if(!j||!j.ok||!j.profile||j.profile.streak_target_days!==n)throw Error("goal_rejected");
        if(typeof MAP!=="undefined"&&MAP&&MAP.study_setup)MAP.study_setup.streak_target_days=n;
      }).catch(function(){
        if(root===saveRoot&&viewId===saveView){root.dataset.saveError="true";}
      }).finally(function(){
        clearTimeout(timer);saving=false;
        if(root&&typeof MAP!=="undefined"&&MAP===map&&typeof PWA_COURSE_USER_ID!=="undefined"&&PWA_COURSE_USER_ID===owner){
          var failed=root.dataset.saveError;delete root.dataset.saveError;refresh();
          var status=root.querySelector('.p45-progress-save-status');
          if(failed&&status&&root===saveRoot&&viewId===saveView){status.textContent=lang().saveError;}
          if(root===saveRoot&&viewId===saveView&&active==="streak"){root.querySelector('[data-p45="select"]').focus({preventScroll:true});}
        }
      });
    }
  }
  window.HskPwaProgress={open:open,close:close,back:close,backTarget:function(){return root},refresh:refresh};
})();
