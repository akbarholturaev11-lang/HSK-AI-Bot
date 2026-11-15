/* Full-screen, server-backed XP/Streak destinations for the real learner PWA.
   UIUX-002: no fake XP history or inferred month-wide activity. */
(function () {
  "use strict";
  var root = null, origin = null, active = null, saving = false;
  var locale = {
    ru: {back:"Назад",streak:"Серия дней",xp:"Опыт XP",days:"дней",total:"Всего XP",today:"Сегодня",
      week:"На этой неделе",daily:"Дневная цель",goal:"Личная цель",change:"Изменить цель",
      choose:"Выберите цель",calendar:"Активность за месяц",unknown:"Данные за остальные дни месяца недоступны",
      legendYes:"Учились",legendNo:"Без занятий",legendToday:"Сегодня",legendOther:"Нет данных",
      earned:"За что начисляется XP",lesson:"Уроки и проверенные задания",other:"Практика и экзамены",
      nohistory:"История начислений пока недоступна",continue:"Продолжить обучение",
      unavailable:"Данные обучения ещё не загружены",retry:"Повторить",saveError:"Не удалось сохранить цель",
      left:"до цели осталось",realDays:"Доступные дни активности",record:"Рекорд",save:"Сохранение…"},
    uz: {back:"Orqaga",streak:"Ketma-ket kunlar",xp:"O‘quv tajribasi XP",days:"kun",total:"Jami XP",today:"Bugun",
      week:"Shu hafta",daily:"Kunlik maqsad",goal:"Shaxsiy maqsad",change:"Maqsadni o‘zgartirish",
      choose:"Maqsadni tanlang",calendar:"Oylik faollik",unknown:"Oyning boshqa kunlari bo‘yicha ma’lumot yo‘q",
      legendYes:"Faol kun",legendNo:"O‘qilmagan",legendToday:"Bugun",legendOther:"Ma’lumot yo‘q",
      earned:"XP qanday to‘planadi?",lesson:"Darslar va tekshirilgan topshiriqlar",other:"Mashqlar va testlar",
      nohistory:"XP hisoblash tarixi hozircha mavjud emas",continue:"O‘qishni davom ettirish",
      unavailable:"O‘quv ma’lumoti hali yuklanmagan",retry:"Qayta urinish",saveError:"Maqsad saqlanmadi",
      left:"maqsadga qoldi",realDays:"Tasdiqlangan faol kunlar",record:"Eng uzun seriya",save:"Saqlanmoqda…"},
    tj: {back:"Бозгашт",streak:"Рӯзҳои пайдарпай",xp:"Таҷрибаи XP",days:"рӯз",total:"Ҳамаи XP",today:"Имрӯз",
      week:"Ҳафтаи ҷорӣ",daily:"Ҳадафи ҳаррӯза",goal:"Ҳадафи шахсӣ",change:"Тағйири ҳадаф",
      choose:"Ҳадафро интихоб кунед",calendar:"Фаъолияти моҳ",unknown:"Маълумоти рӯзҳои дигари моҳ дастрас нест",
      legendYes:"Рӯзи фаъол",legendNo:"Бе машғулият",legendToday:"Имрӯз",legendOther:"Маълумот нест",
      earned:"XP аз куҷо меояд?",lesson:"Дарсҳо ва супоришҳои санҷидашуда",other:"Машқҳо ва санҷишҳо",
      nohistory:"Таърихи XP ҳоло дастрас нест",continue:"Идома додани омӯзиш",
      unavailable:"Маълумоти омӯзиш ҳанӯз бор нашудааст",retry:"Такрор",saveError:"Ҳадаф захира нашуд",
      left:"то ҳадаф мондааст",realDays:"Рӯзҳои фаъоли тасдиқшуда",record:"Рекорд",save:"Захира мешавад…"}
  };
  function lang() {return locale[typeof LANG !== "undefined" ? LANG : "ru"] || locale.ru;}
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
    return '<div class="p45-progress-hero"><span class="p45-progress-kicker">'+t.streak+'</span><strong>🔥 '+fmt(now)+'</strong><small>'+t.days+'</small></div>'
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
    root.id="p45-progress";root.className="on";root.setAttribute("role","dialog");root.setAttribute("aria-modal","true");
    root.setAttribute("aria-label",kind==="xp"?lang().xp:lang().streak);
    root.innerHTML='<div class="p45-progress-header"><button type="button" class="p45-progress-back" data-p45="back" aria-label="'+lang().back+'">‹</button>'
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