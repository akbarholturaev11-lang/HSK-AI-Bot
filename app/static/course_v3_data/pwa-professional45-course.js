/* Browser-PWA course enhancements, one cached asset (service-worker warm budget):
   1) UIUX-002 XP/Streak destinations, 2) UIUX-008 in-lesson self-rating card. */
/* Full-screen, server-backed XP/Streak destinations for the real learner PWA.
   UIUX-002: no fake XP history or inferred month-wide activity. */
(function () {
  "use strict";
  var root = null, origin = null, active = null, saving = false;
  /* Copy is read from the canonical course catalog (localization/ui/<lang>/course.json,
     pwaProgress keys); no inline translation dictionary. */
  var COPY_KEYS = ["back", "streak", "xp", "days", "total", "today", "week", "daily", "goal", "change", "choose", "calendar", "unknown", "legendYes", "legendNo", "legendToday", "legendOther", "earned", "lesson", "other", "nohistory", "continue", "unavailable", "retry", "saveError", "left", "realDays", "record", "save"];
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
  function fmt(n) {return n == null ? "—" : n.toLocaleString("ru-RU");}
  function iso(s) {return typeof s==="string" && /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : null;}
  function calendar(p) {
    var t=lang(),today=iso(p.local_date),week=iso(p.week_start);
    if(!today) return '<div class="p45-progress-empty">'+t.unavailable+'</div>';
    var y=Number(today.slice(0,4)),m=Number(today.slice(5,7))-1,d=Number(today.slice(8,10));
    var count=new Date(Date.UTC(y,m+1,0)).getUTCDate(),offset=(new Date(Date.UTC(y,m,1)).getUTCDay()+6)%7;
    var known=new Set((Array.isArray(p.week_activity_dates)?p.week_activity_dates:[]).filter(iso));
    var start=week, end=null;
    if(start) {var startDate=new Date(start+"T00:00:00Z");end=new Date(startDate.getTime()+6*86400000).toISOString().slice(0,10);}
    var labels={ru:["Пн","Вт","Ср","Чт","Пт","Сб","Вс"],uz:["Du","Se","Ch","Pa","Ju","Sh","Ya"],tj:["Дш","Сш","Чш","Пш","Ҷм","Шб","Яш"]};
    var lg=typeof LANG!=="undefined"?LANG:"ru",head=(labels[lg]||labels.ru).map(function(x){return '<div class="p45-cal-weekday">'+x+'</div>';}).join("");
    var days="";
    for(var i=0;i<offset;i++) days+='<div class="p45-cal-pad" aria-hidden="true"></div>';
    for(var day=1;day<=count;day++){
      var key=y+"-"+String(m+1).padStart(2,"0")+"-"+String(day).padStart(2,"0");
      var todayFlag=day===d, future=day>d, inKnown=!!(start && end && key>=start && key<=end);
      var status=future?"future":known.has(key)?"active":inKnown?"missed":"unknown";
      days+='<div class="p45-cal-day '+status+(todayFlag?" today":"")+'" aria-label="'+key+' · '+(status==="active"?t.legendYes:status==="missed"?t.legendNo:status==="unknown"?t.legendOther:t.legendToday)+'">'+day+'</div>';
    }
    var monthNames={ru:["Январь","Февраль","Март","Апрель","Май","Июнь","Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"],
      uz:["Yanvar","Fevral","Mart","Aprel","May","Iyun","Iyul","Avgust","Sentabr","Oktabr","Noyabr","Dekabr"],
      tj:["Январ","Феврал","Март","Апрел","Май","Июн","Июл","Август","Сентябр","Октябр","Ноябр","Декабр"]};
    return '<div class="p45-progress-sub">'+(monthNames[lg]||monthNames.ru)[m]+' '+y+'</div>'
      +'<div class="p45-calendar">'+head+days+'</div>'
      +'<p class="p45-progress-note">'+t.unknown+'</p>'
      +'<div class="p45-progress-legend"><span class="active">'+t.legendYes+'</span><span class="unknown">'+t.legendOther+'</span><span class="today">'+t.legendToday+'</span></div>';
  }
  function copy() {
    var t=lang(),p=state(),st=setup();
    if(!p) return '<div class="p45-progress-empty" role="status">'+t.unavailable+
      '</div><button class="p45-progress-primary" type="button" data-p45="retry">'+t.retry+'</button>';
    if(active==="xp"){
      var total=safeNum(p.xp),daily=safeNum(p.daily_xp),weekly=safeNum(p.weekly_xp);
      var goal=safeNum(st.daily_goal_xp),width=goal&&daily!=null?Math.min(100,daily/goal*100):0;
      return '<div class="p45-progress-hero"><span class="p45-progress-kicker">'+t.total+'</span><strong>'+fmt(total)+'</strong><small>XP</small></div>'
        +'<div class="p45-progress-stats"><section class="p45-progress-card"><h2>'+t.today+'</h2><strong>'+fmt(daily)+' XP</strong><div class="p45-progress-track"><i style="width:'+width+'%"></i></div><p>'+t.daily+': '+fmt(goal)+' XP</p></section>'
        +'<section class="p45-progress-card"><h2>'+t.week+'</h2><strong>'+fmt(weekly)+' XP</strong></section></div>'
        +'<h2 class="p45-progress-section">'+t.earned+'</h2><div class="p45-progress-list"><div>'+t.lesson+'</div><div>'+t.other+'</div></div>'
        +'<p class="p45-progress-note">'+t.nohistory+'</p>'
        +'<button type="button" class="p45-progress-primary" data-p45="continue">'+t.continue+'</button>';
    }
    var now=safeNum(p.streak),longest=safeNum(p.longest_streak);
    var target=[7,14,30,50].includes(st.streak_target_days)?st.streak_target_days:null;
    var width=target && now!=null?Math.min(100,now/target*100):0;
    return '<div class="p45-progress-hero"><span class="p45-progress-kicker">'+t.streak+'</span><strong><i class="ti ti-flame p45-progress-flame" aria-hidden="true"></i> '+fmt(now)+'</strong><small>'+t.days+'</small></div>'
      +'<section class="p45-progress-card"><div class="p45-progress-line"><span>'+t.goal+'</span><b>'+(target?target+" "+t.days:t.choose)+'</b></div>'
      +(target?'<div class="p45-progress-track"><i style="width:'+width+'%"></i></div>'
        +'<p>'+Math.max(0,target-(now||0))+' '+t.days+' '+t.left+'</p>':'')
      +'<div class="p45-progress-line"><span>'+t.record+'</span><b>'+fmt(longest)+' '+t.days+'</b></div>'
      +'<button type="button" class="p45-progress-secondary" data-p45="select">'+t.change+'</button></section>'
      +'<h2 class="p45-progress-section">'+t.calendar+'</h2><section class="p45-progress-card">'+calendar(p)+'</section>'
      +'<button type="button" class="p45-progress-primary" data-p45="continue">'+t.continue+'</button>';
  }
  function refresh() {
    if(!root)return;
    var t=lang();
    root.querySelector(".p45-progress-body").innerHTML=copy();
    root.querySelector(".p45-progress-title").textContent=active==="xp"?t.xp:t.streak;
  }
  function open(kind) {
    if(kind!=="xp" && kind!=="streak")return;
    if(typeof PWA_COURSE_HOST!=="undefined"&&!PWA_COURSE_HOST)return;
    if(root){active=kind;refresh();return;}
    active=kind;origin=document.activeElement;
    root=document.createElement("section");
    root.id="p45-progress";root.className="on";root.setAttribute("role","main");
    root.setAttribute("aria-label",kind==="xp"?lang().xp:lang().streak);
    root.innerHTML='<div class="p45-progress-header"><button type="button" class="p45-progress-back" data-p45="back" aria-label="'+lang().back+'"><i class="ti ti-chevron-left" aria-hidden="true"></i></button>'
      +'<h1 class="p45-progress-title"></h1></div><div class="p45-progress-body" tabindex="-1"></div>';
    document.body.appendChild(root);
    root.addEventListener("click",handleClick);
    root.addEventListener("keydown",handleKeydown);
    document.documentElement.classList.add("p45-detail-open");
    var wrap=document.querySelector(".wrap");if(wrap)wrap.inert=true;
    refresh();
    root.querySelector(".p45-progress-back").focus({preventScroll:true});
    if(typeof NavBack!=="undefined")NavBack.sync();
  }
  function close() {
    if(!root)return;
    root.remove();root=null;active=null;
    document.documentElement.classList.remove("p45-detail-open");
    var wrap=document.querySelector(".wrap");if(wrap)wrap.inert=false;
    if(origin&&origin.isConnected)origin.focus({preventScroll:true});
    if(typeof NavBack!=="undefined")NavBack.sync();
  }
  function handleKeydown(event) {
    if(event.key==="Escape"){event.preventDefault();close();return}
    if(event.key!=="Tab"||!root)return;
    var controls=[].slice.call(root.querySelectorAll('button:not([disabled])'));
    if(!controls.length)return;
    if(event.shiftKey&&document.activeElement===controls[0]){controls[controls.length-1].focus();event.preventDefault()}
    else if(!event.shiftKey&&document.activeElement===controls[controls.length-1]){controls[0].focus();event.preventDefault()}
  }
  function handleClick(event) {
    var button=event.target.closest("[data-p45]");if(!button)return;
    var act=button.getAttribute("data-p45");
    if(act==="back"){close();return}
    if(act==="continue"){close();if(typeof App!=="undefined")App.show("course");return}
    if(act==="retry"){if(typeof refreshCourseProgress==="function")refreshCourseProgress(true).then(refresh);return}
    if(act==="select"){
      if(saving)return;
      root.querySelector(".p45-progress-body").insertAdjacentHTML("beforeend",
        '<div class="p45-progress-goals" role="group" aria-label="'+lang().choose+'">'
        +[7,14,30,50].map(function(n){return '<button type="button" data-p45="goal" data-value="'+n+'">'+n+' '+lang().days+'</button>';}).join("")+'</div>');
      button.disabled=true;return;
    }
    if(act==="goal"){
      var n=Number(button.getAttribute("data-value"));if(![7,14,30,50].includes(n)||saving)return;
      if(typeof savePreferences!=="function"){return}
      saving=true;button.disabled=true;button.textContent=lang().save;
      savePreferences({streak_target_days:n}).then(function(j){
        if(!j||!j.ok||!j.profile||j.profile.streak_target_days!==n)throw Error("goal_rejected");
        if(typeof STUDY_SETUP!=="undefined"&&STUDY_SETUP)STUDY_SETUP.streak_target_days=n;
        if(typeof MAP!=="undefined"&&MAP&&MAP.study_setup)MAP.study_setup.streak_target_days=n;
        refresh();
      }).catch(function(){if(typeof toast==="function")toast(lang().saveError,2200);if(root)refresh()})
        .finally(function(){saving=false});
    }
  }
  window.HskPwaProgress={open:open,close:close,back:close,backTarget:function(){return root},refresh:refresh};
})();

/* UIUX-008: optional in-lesson self-assessment card from previously taught canonical words.
   No server grade, XP, hearts, lesson positions, content JSON, or mistake/SRS writes. */
(function(){
"use strict";
if(location.pathname!=="/iphone-pwa/course")return;
var installed=false,baseRender=null,session=null;
/* Copy is read from the canonical course catalog (pwaFlashcards.*). */
var COPY_KEYS=["heading", "hint", "show", "again", "know", "listen", "self", "example", "dismiss"];
function words() {
 var all=window.HSKAI_COURSE_I18N||{},code=typeof LANG!=="undefined"?LANG:"ru",own=all[code]||{},ru=all.ru||{},out={};
 COPY_KEYS.forEach(function(k){var v=own["pwaFlashcards."+k];out[k]=typeof v==="string"&&v?v:(ru["pwaFlashcards."+k]||"")});
 return out;
}
function priorWord() {
 if(typeof Flow==="undefined"||!Array.isArray(Flow.queue))return null;
 var arr=Flow.queue.slice(0,Flow.i);
 for(var i=arr.length-1;i>=0;i--) {
  var c=arr[i],w=c&&c.word;
  if(c&&c.type==="active_word" && w && typeof w.zh==="string"&&w.zh.trim()&&
     typeof w.pinyin==="string"&&w.pinyin.trim()&&w.meaning&&typeof w.meaning==="object")return w;
 }
 return null;
}
function node(type,cls,text){var x=document.createElement(type);if(cls)x.className=cls;if(text!==undefined)x.textContent=text;return x}
function renderCard(word){
 var body=document.querySelector("#f-body"),cta=document.querySelector("#f-cta"),stage=document.querySelector("#f-stage");
 if(!body||!cta)return false;
 if(typeof hideBar==="function")hideBar();
 if(typeof setWriteBtn==="function")setWriteBtn("");
 if(typeof Flow!=="undefined")Flow.answered=false;
 cta.style.display="none";
 body.replaceChildren();
 var trn=(typeof tr==="function"?tr(word.meaning):word.meaning.ru)||"";
 var dict=words(),root=node("section","p45-lesson-flash");
 root.setAttribute("aria-label",dict.heading);
 root.appendChild(node("p","p45-lesson-flash-kicker",dict.heading));
 root.appendChild(node("p","p45-lesson-flash-hint",dict.hint));
 var han=node("div","p45-lesson-flash-hanzi",word.zh);han.lang="zh-CN";root.appendChild(han);
 var reveal=btn(dict.show,function(){
   reveal.remove();
   root.querySelector(".p45-lesson-flash-hint").textContent="";
   var answer=node("div","p45-lesson-flash-answer");
   answer.appendChild(node("p","p45-lesson-flash-pinyin",word.pinyin));
   answer.appendChild(node("strong","p45-lesson-flash-meaning",trn));
   root.appendChild(answer);
   var listen=btn(dict.listen,function(){if(typeof speak==="function")speak(word.zh)}, "p45-lesson-flash-audio");
   var listenIcon=document.createElement("i");listenIcon.className="ti ti-volume";listenIcon.setAttribute("aria-hidden","true");
   listen.insertBefore(listenIcon,listen.firstChild);
   root.appendChild(listen);
   var choice=node("div","p45-lesson-flash-actions");
   choice.appendChild(btn(dict.again,function(){dismiss("again")},"p45-lesson-flash-repeat"));
   choice.appendChild(btn(dict.know,function(){dismiss("know")},"p45-lesson-flash-know"));
   root.appendChild(node("p","p45-lesson-flash-disclaimer",dict.self));
   root.appendChild(choice);
 }, "p45-lesson-flash-reveal");
 root.appendChild(reveal);
 body.appendChild(root);
 if(stage)stage.textContent=dict.heading;
 reveal.focus({preventScroll:true});
 return true;
}
function btn(text,fn,cls){var b=node("button",cls||"",text);b.type="button";b.addEventListener("click",fn);return b}
function dismiss(choice){
 if(!session||typeof Flow==="undefined")return;
 session.shown=true;
 if(choice==="again"&&session.repeatCount===0)session.repeatAt=Flow.i+2;
 if(choice==="again")session.repeatCount++;
 session.reviews.push(choice);
 // The main engine resumes at exactly the same normal lesson card/index.
 if(typeof baseRender==="function")baseRender();
}
function wrapped(){
 if(typeof Flow==="undefined" || !Flow || Flow.test||Flow.challenge || !Array.isArray(Flow.queue) ||
   Flow.lessonIdx==null || Flow.i>=Flow.queue.length || Flow.i<4)return baseRender.apply(this,arguments);
 var start=Number(Flow.startedAt||0);
 if(!start)return baseRender.apply(this,arguments);
 if(!session||session.started!==start)session={started:start,shown:false,repeatAt:null,repeatCount:0,reviews:[]};
 var first=!session.shown;
 var repeat=session.repeatAt!==null && Flow.i>=session.repeatAt && session.repeatCount===1;
 if(first||repeat){
   var word=priorWord();
   if(word){
     if(repeat){session.repeatAt=null;session.repeatCount=2;}
     if(first)session.shown=true; // prevent auto-duplicate on rerender/error
     if(renderCard(word))return;
   }
 }
 return baseRender.apply(this,arguments);
}
function install(){
 if(installed||typeof window.renderFlowCard!=="function")return;
 baseRender=window.renderFlowCard;
 window.renderFlowCard=wrapped;installed=true;
}
if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",install,{once:true});
else install();
})();