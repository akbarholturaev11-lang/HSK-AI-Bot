(function(){
"use strict";

const META_KEY="hsk_v2_meta_v1";
const ONBOARDING_KEY="hsk_v2_onboarding_v1";
const MISTAKES_KEY="hsk_v2_mistakes_v1";
const LEVELS=["hsk1","hsk2","hsk3","hsk4a","hsk4b"];
const copy={
  ru:{
    home:"Главная",course:"Курс",voice:"AI Voice",tests:"Тесты",profile:"Профиль",
    welcome:"Продолжим китайский",today:"Сегодня",continue:"Продолжить урок",dailyGoal:"Дневная цель",minutes:"минут",
    missions:"Задания на сегодня",lessonMission:"Завершить урок",wordMission:"Повторить 5 слов",voiceMission:"Поговорить с AI",
    yourProgress:"Ваш прогресс",league:"Лига",achievements:"Достижения",reward:"Награда",openChest:"Открыть сундук",
    path:"Учебный путь",pathSub:"Короткие интерактивные уроки по порядку HSK",completed:"завершено",lesson:"Урок",
    current:"Текущий урок",done:"Пройдено",locked:"Сначала завершите предыдущий урок",review:"Повторение",boss:"Контрольная",
    start:"Начать",words:"Слова",grammar:"Грамматика",practice:"Практика",lessonReady:"Выберите формат тренировки",
    testsSub:"Проверьте уровень и подготовьтесь к экзамену",placement:"Определение уровня",placementSub:"10 вопросов и автоматическая рекомендация уровня",
    mock:"Пробный экзамен",mockSub:"Задания на базе текущего курса",startTest:"Начать тест",
    training:"Тренировка",trainingSub:"Отдельная работа над конкретным навыком",listening:"Аудирование",speaking:"Разговор",
    writing:"Письмо",characters:"Иероглифы",mistakes:"Мои ошибки",mistakesSub:"Слабые места из ваших последних квизов",
    settings:"Настройки",language:"Язык интерфейса",level:"Уровень курса",subscription:"Подписка",subscriptionSub:"Управление доступом в существующем разделе",
    support:"Поддержка",notifications:"Уведомления",streak:"дней",xp:"XP",noMistakes:"Ошибок пока нет. Завершите квиз, и здесь появится персональная тренировка.",
    mistakesCount:"ошибок",recommended:"Рекомендуемый уровень",rewardReady:"Сундук готов",rewardLocked:"Заработайте ещё XP",
    onboardingTitle:"Китайский для реального общения",onboardingSub:"Соберём короткий план и сразу откроем первый урок.",
    chooseGoal:"Зачем вы учите китайский?",chooseLevel:"Какой у вас уровень?",chooseTime:"Сколько минут в день?",chooseStart:"Откуда начать?",
    next:"Далее",back:"Назад",finish:"Начать обучение",saving:"Сохраняем...",onboardingError:"Не удалось сохранить настройки. Попробуйте ещё раз.",goalHsk:"Сдать HSK",goalStudy:"Учиться в Китае",goalWork:"Работать в Китае",goalTravel:"Путешествовать",goalDaily:"Общаться каждый день",startLesson1:"Начать с урока 1",continueProgress:"Продолжить текущий прогресс",takePlacement:"Пройти тест уровня"
  },
  uz:{
    home:"Asosiy",course:"Kurs",voice:"AI Voice",tests:"Testlar",profile:"Profil",
    welcome:"Xitoy tilini davom ettiramiz",today:"Bugun",continue:"Darsni davom ettirish",dailyGoal:"Kunlik maqsad",minutes:"daqiqa",
    missions:"Bugungi vazifalar",lessonMission:"Darsni tugatish",wordMission:"5 ta so'zni takrorlash",voiceMission:"AI bilan gaplashish",
    yourProgress:"Progressingiz",league:"Liga",achievements:"Yutuqlar",reward:"Mukofot",openChest:"Sandiqni ochish",
    path:"O'quv yo'li",pathSub:"HSK tartibidagi qisqa interaktiv darslar",completed:"tugallandi",lesson:"Dars",
    current:"Joriy dars",done:"Tugallangan",locked:"Avval oldingi darsni tugating",review:"Takrorlash",boss:"Nazorat",
    start:"Boshlash",words:"So'zlar",grammar:"Grammatika",practice:"Mashq",lessonReady:"Mashq turini tanlang",
    testsSub:"Darajangizni tekshiring va imtihonga tayyorlaning",placement:"Darajani aniqlash",placementSub:"10 savol va avtomatik level tavsiyasi",
    mock:"Sinov imtihoni",mockSub:"Joriy kurs materiallari asosida",startTest:"Testni boshlash",
    training:"Mashqlar",trainingSub:"Alohida ko'nikmani mustaqil rivojlantirish",listening:"Tinglash",speaking:"Gapirish",writing:"Yozish",characters:"Ierogliflar",
    mistakes:"Xatolarim",mistakesSub:"Quizlarda aniqlangan zaif joylaringiz",settings:"Sozlamalar",language:"Interfeys tili",level:"Kurs darajasi",
    subscription:"Obuna",subscriptionSub:"Mavjud bo'limda accessni boshqarish",support:"Yordam",notifications:"Bildirishnomalar",streak:"kun",xp:"XP",
    noMistakes:"Hozircha xato yo'q. Quizni tugating, personal mashqlar shu yerda paydo bo'ladi.",mistakesCount:"xato",recommended:"Tavsiya etilgan daraja",
    rewardReady:"Sandiq tayyor",rewardLocked:"Yana XP yig'ing",onboardingTitle:"Real muloqot uchun xitoy tili",onboardingSub:"Qisqa reja tuzamiz va birinchi darsni darhol ochamiz.",
    chooseGoal:"Xitoy tilini nima uchun o'rganyapsiz?",chooseLevel:"Darajangiz qaysi?",chooseTime:"Kuniga necha daqiqa?",chooseStart:"Qayerdan boshlaysiz?",
    next:"Keyingi",back:"Orqaga",finish:"O'qishni boshlash",saving:"Saqlanmoqda...",onboardingError:"Sozlamalarni saqlab bo'lmadi. Qayta urinib ko'ring.",goalHsk:"HSK topshirish",goalStudy:"Xitoyda o'qish",goalWork:"Xitoyda ishlash",goalTravel:"Sayohat",goalDaily:"Har kuni gaplashish",startLesson1:"1-darsdan boshlash",continueProgress:"Joriy progressdan davom etish",takePlacement:"Daraja testini topshirish"
  },
  tj:{
    home:"Асосӣ",course:"Курс",voice:"AI Voice",tests:"Тестҳо",profile:"Профил",
    welcome:"Омӯзиши чиниро идома медиҳем",today:"Имрӯз",continue:"Идомаи дарс",dailyGoal:"Ҳадафи рӯз",minutes:"дақиқа",
    missions:"Вазифаҳои имрӯз",lessonMission:"Анҷоми дарс",wordMission:"Такрори 5 калима",voiceMission:"Сӯҳбат бо AI",
    yourProgress:"Пешрафти шумо",league:"Лига",achievements:"Дастовардҳо",reward:"Мукофот",openChest:"Кушодани сандуқ",
    path:"Роҳи омӯзиш",pathSub:"Дарсҳои кӯтоҳи интерактивӣ бо тартиби HSK",completed:"анҷом шуд",lesson:"Дарс",
    current:"Дарси ҷорӣ",done:"Анҷомшуда",locked:"Аввал дарси пешинаро анҷом диҳед",review:"Такрор",boss:"Санҷиш",
    start:"Оғоз",words:"Калимаҳо",grammar:"Грамматика",practice:"Машқ",lessonReady:"Навъи машқро интихоб кунед",
    testsSub:"Сатҳи худро санҷед ва ба имтиҳон омода шавед",placement:"Муайян кардани сатҳ",placementSub:"10 савол ва тавсияи автоматии сатҳ",
    mock:"Имтиҳони санҷишӣ",mockSub:"Дар асоси маводи курси ҷорӣ",startTest:"Оғози тест",
    training:"Машқҳо",trainingSub:"Кор бо малакаи алоҳида",listening:"Шунидан",speaking:"Гуфтугӯ",writing:"Навиштан",characters:"Иероглифҳо",
    mistakes:"Хатоҳои ман",mistakesSub:"Ҷойҳои суст аз квизҳои шумо",settings:"Танзимот",language:"Забони интерфейс",level:"Сатҳи курс",
    subscription:"Обуна",subscriptionSub:"Идораи дастрасӣ дар бахши мавҷуда",support:"Дастгирӣ",notifications:"Огоҳиҳо",streak:"рӯз",xp:"XP",
    noMistakes:"Ҳоло хато нест. Квизро анҷом диҳед, машқи шахсӣ дар ин ҷо пайдо мешавад.",mistakesCount:"хато",recommended:"Сатҳи тавсияшуда",
    rewardReady:"Сандуқ тайёр",rewardLocked:"Боз XP гиред",onboardingTitle:"Забони чинӣ барои муоширати воқеӣ",onboardingSub:"Нақшаи кӯтоҳ месозем ва дарси аввалро мекушоем.",
    chooseGoal:"Барои чӣ забони чинӣ меомӯзед?",chooseLevel:"Сатҳи шумо кадом аст?",chooseTime:"Дар як рӯз чанд дақиқа?",chooseStart:"Аз куҷо оғоз мекунед?",
    next:"Баъдӣ",back:"Бозгашт",finish:"Оғози омӯзиш",saving:"Нигоҳ дошта мешавад...",onboardingError:"Танзимот нигоҳ дошта нашуд. Аз нав кӯшиш кунед.",goalHsk:"Супоридани HSK",goalStudy:"Таҳсил дар Чин",goalWork:"Кор дар Чин",goalTravel:"Саёҳат",goalDaily:"Ҳар рӯз гуфтугӯ кардан",startLesson1:"Аз дарси 1 оғоз кардан",continueProgress:"Идомаи пешрафти ҷорӣ",takePlacement:"Супоридани тести сатҳ"
  }
};

const today=()=>new Date().toLocaleDateString("en-CA");
const yesterday=()=>{const d=new Date();d.setDate(d.getDate()-1);return d.toLocaleDateString("en-CA")};
const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key)||JSON.stringify(fallback))}catch(_){return fallback}};
const write=(key,value)=>localStorage.setItem(key,JSON.stringify(value));
const tx=key=>(copy[lang]||copy.ru)[key]||copy.ru[key]||key;
const labelLevel=value=>value==="hsk4a"?"HSK 4 上":value==="hsk4b"?"HSK 4 下":String(value||LEVEL_KEY).toUpperCase().replace("HSK","HSK ");
const launchCurrent=Number(launchLesson)||0;
const lessonIsDone=number=>state.done.includes(number)||(launchCurrent>1&&number<launchCurrent);
const completedCount=()=>LESSONS.filter(item=>lessonIsDone(item.n)).length;
const currentLesson=()=>LESSONS.find(item=>item.n===launchCurrent&&!lessonIsDone(item.n))||LESSONS.find(item=>!lessonIsDone(item.n))||LESSONS[LESSONS.length-1];

let meta=read(META_KEY,{xp:0,streak:0,lastActive:"",daily:{date:today(),xp:0,lesson:0,words:0,voice:0},chests:0,goal:"hsk_exam",minutes:10});
let testMode="";
let onboardingStep=0;
let onboardingSubmitting=false;
let onboarding={goal:["hsk_exam","study_china","work_china","daily_communication","travel"].includes(meta.goal)?meta.goal:"hsk_exam",level:LEVEL_KEY.startsWith("hsk4")?"hsk4":LEVEL_KEY,minutes:meta.minutes||10,startMode:"continue"};

function normalizeMeta(){
  if(meta.lastActive!==today()){
    meta.streak=meta.lastActive===yesterday()?Math.max(1,Number(meta.streak||0)+1):1;
    meta.lastActive=today();
    meta.daily={date:today(),xp:0,lesson:0,words:0,voice:0};
  }
  if(meta.daily?.date!==today())meta.daily={date:today(),xp:0,lesson:0,words:0,voice:0};
  const baseline=state.done.length*20+Object.values(state.quizScores||{}).reduce((sum,item)=>sum+Math.round(Number(item.percent||0)/10),0);
  meta.xp=Math.max(Number(meta.xp||0),baseline);
  write(META_KEY,meta);
}

function appMarkup(){
  return `<div class="v2-app">
    <header class="v2-topbar"><div class="v2-brand"><div class="v2-brand-mark">汉</div><div><strong>HSK AI</strong><small>${labelLevel(LEVEL_KEY)}</small></div></div><div class="v2-top-stats"><button class="v2-stat" data-tone="coral" onclick="V2.showPage('profile')" aria-label="Streak">◆ <span id="v2-streak">0</span></button><button class="v2-stat" data-tone="gold" onclick="V2.showPage('profile')" aria-label="XP">✦ <span id="v2-xp">0</span></button></div></header>
    <main class="v2-pages">
      <section id="page-home" class="v2-page"></section>
      <section id="page-course" class="v2-page"></section>
      <section id="page-flashcards" class="page v2-page"><header class="page-header"><button class="v2-back" onclick="V2.showPage('training')" aria-label="Back">‹</button><div class="eyebrow" id="fc-level-label"></div><h1 class="page-title" data-i18n="flashcards"></h1><p class="page-sub" data-i18n="flashcardSub"></p></header><div class="toolbar"><input id="search" class="search" data-placeholder="search" oninput="renderFlashcards()"></div><div class="filters" id="fc-filters"></div><main class="grid" id="fc-grid"></main></section>
      <section id="page-grammar" class="page v2-page"><header class="page-header"><button class="v2-back" onclick="V2.showPage('training')" aria-label="Back">‹</button><div class="eyebrow" id="grammar-level-label"></div><h1 class="page-title" data-i18n="grammar"></h1><p class="page-sub" data-i18n="grammarSub"></p></header><div class="filters" id="grammar-filters"></div><main class="list" id="grammar-list"></main></section>
      <section id="page-quiz" class="page v2-page"><header class="page-header"><button class="v2-back" onclick="V2.showPage('tests')" aria-label="Back">‹</button><div class="eyebrow" id="quiz-level-label"></div><h1 class="page-title" data-i18n="quiz"></h1><p class="page-sub" data-i18n="quizSub"></p></header><div class="filters" id="quiz-filters"></div><main class="quiz-wrap"><div id="quiz-box" class="quiz-box"></div><div id="score-box" class="score-box" style="display:none"></div></main></section>
      <section id="page-voice" class="page v2-page no-top-pad"><main class="voice-wrap"><iframe id="voice-frame" class="voice-frame" title="AI Voice" allow="microphone; autoplay"></iframe></main></section>
      <section id="page-tests" class="v2-page"></section>
      <section id="page-profile" class="v2-page"></section>
      <section id="page-training" class="v2-page"></section>
      <section id="page-mistakes" class="v2-page"></section>
      <section id="page-league" class="v2-page"></section>
      <section id="page-achievements" class="v2-page"></section>
      <div id="kpis" hidden></div><div id="lesson-list" hidden></div>
    </main>
    <nav class="v2-nav">
      ${navButton("home","⌂",tx("home"))}${navButton("course","◉",tx("course"))}${navButton("voice","◌",tx("voice"))}${navButton("tests","✓",tx("tests"))}${navButton("profile","◎",tx("profile"))}
    </nav>
  </div>`;
}

function navButton(page,icon,label){return `<button data-page="${page}" onclick="V2.showPage('${page}')"><b>${icon}</b><span>${esc(label)}</span></button>`}
function progress(){return Math.round(completedCount()/Math.max(LESSONS.length,1)*100)}
function xpLevel(){return Math.floor(meta.xp/250)+1}
function leagueName(){return ["Bronze","Silver","Gold","Diamond","Sapphire","Legend"][Math.min(5,Math.floor(meta.xp/500))]}
function missionDone(name,target){return Number(meta.daily?.[name]||0)>=target}
function missionRow(icon,title,current,target){const done=current>=target;return `<div class="v2-mission"><div class="v2-mission-icon">${icon}</div><div><b>${esc(title)}</b><small>${Math.min(current,target)} / ${target}</small></div><span class="v2-check ${done?"":"pending"}">${done?"✓":"○"}</span></div>`}

function renderHome(){
  const lesson=currentLesson();
  const goal=Math.max(5,Number(meta.minutes||10));
  const dailyProgress=Math.min(100,Math.round(Number(meta.daily.xp||0)/(goal*2)*100));
  const chestReady=meta.xp>0&&meta.xp%100>=80;
  document.getElementById("page-home").innerHTML=`
    <div class="v2-page-head"><div class="v2-kicker">${esc(tx("today"))}</div><h1 class="v2-title">${esc(tx("welcome"))}</h1></div>
    <section class="v2-hero"><div class="v2-hero-row"><div><div class="v2-kicker">${labelLevel(LEVEL_KEY)} · ${esc(tx("lesson"))} ${lesson?.n||1}</div><h1>${esc(tr(lesson?.t)||"")}</h1><p>${esc(tr(lesson?.sub)||"")}</p></div><div class="v2-progress-ring" style="--progress:${progress()}%" data-value="${progress()}%"></div></div><button class="v2-primary" onclick="V2.openLesson(${lesson?.n||1})">▶ ${esc(tx("continue"))}</button></section>
    <section class="v2-section"><div class="v2-section-head"><h2 class="v2-section-title">${esc(tx("dailyGoal"))}</h2><span class="v2-link">${goal} ${esc(tx("minutes"))}</span></div><div class="v2-goal"><div class="v2-goal-top"><b>${meta.daily.xp||0} XP</b><span>${dailyProgress}%</span></div><div class="v2-bar"><i style="width:${dailyProgress}%"></i></div></div></section>
    <section class="v2-section"><div class="v2-section-head"><h2 class="v2-section-title">${esc(tx("missions"))}</h2></div><div class="v2-missions">${missionRow("▦",tx("lessonMission"),meta.daily.lesson||0,1)}${missionRow("字",tx("wordMission"),meta.daily.words||0,5)}${missionRow("◌",tx("voiceMission"),meta.daily.voice||0,1)}</div></section>
    <section class="v2-section"><div class="v2-section-head"><h2 class="v2-section-title">${esc(tx("yourProgress"))}</h2></div><div class="v2-metrics"><div class="v2-metric" data-tone="gold"><strong>${meta.xp}</strong><span>${tx("xp")}</span></div><div class="v2-metric" data-tone="green"><strong>${meta.streak}</strong><span>${tx("streak")}</span></div><div class="v2-metric" data-tone="purple"><strong>${xpLevel()}</strong><span>Level</span></div></div></section>
    <section class="v2-section"><div class="v2-split"><button class="v2-feature" onclick="V2.showPage('league')"><span class="v2-feature-icon">◇</span><b>${esc(tx("league"))}</b><small>${leagueName()} · ${meta.xp%500}/500 XP</small></button><button class="v2-feature" onclick="V2.openChest()"><span class="v2-feature-icon">▣</span><b>${esc(chestReady?tx("rewardReady"):tx("reward"))}</b><small>${esc(chestReady?tx("openChest"):tx("rewardLocked"))}</small></button></div></section>`;
}

function pathItem(lesson,index){
  const done=lessonIsDone(lesson.n),current=!done&&lesson.n===currentLesson()?.n,locked=!done&&!current;
  const cls=done?"done":current?"current":"";
  const status=done?tx("done"):current?tx("current"):tx("locked");
  return `<div class="v2-path-item"><div class="v2-node-copy"><b>${esc(tx("lesson"))} ${lesson.n}: ${esc(tr(lesson.t))}</b><small>${esc(status)}</small></div><button class="v2-node ${cls}" onclick="V2.openLesson(${lesson.n})" aria-label="${esc(tx("lesson"))} ${lesson.n}">${done?"✓":lesson.n}</button></div>`;
}
function milestoneItem(after,type){const boss=type==="boss";return `<div class="v2-path-item"><div class="v2-node-copy"><b>${esc(tx(type))}</b><small>${esc(tx("lesson"))} 1-${after}</small></div><button class="v2-node ${boss?"boss":"review"}" onclick="V2.startMock()" aria-label="${esc(tx(type))}">${boss?"★":"↻"}</button></div>`}
function renderCourse(){
  const nodes=[];
  LESSONS.forEach((lesson,index)=>{nodes.push(pathItem(lesson,index));if(lesson.n%5===0)nodes.push(milestoneItem(lesson.n,"boss"));else if(lesson.n%3===0)nodes.push(milestoneItem(lesson.n,"review"))});
  document.getElementById("page-course").innerHTML=`<div class="v2-page-head"><div class="v2-kicker">${labelLevel(LEVEL_KEY)}</div><h1 class="v2-title">${esc(tx("path"))}</h1><p class="v2-subtitle">${esc(tx("pathSub"))}</p></div><div class="v2-path-summary"><div><b>${completedCount()}/${LESSONS.length} ${esc(tx("completed"))}</b><div class="v2-bar"><i style="width:${progress()}%"></i></div></div><span>${progress()}%</span></div><div class="v2-path">${nodes.join("")}</div>`;
}

function renderTests(){
  const cards=[`<button class="v2-row-card" onclick="V2.startPlacement()"><span class="v2-row-icon">◎</span><span><b>${esc(tx("placement"))}</b><small>${esc(tx("placementSub"))}</small></span><span class="v2-arrow">›</span></button>`];
  ["hsk1","hsk2","hsk3","hsk4a"].forEach(level=>cards.push(`<button class="v2-row-card" onclick="V2.startMock('${level}')"><span class="v2-row-icon">${level.replace(/[^0-9]/g,"")}</span><span><b>${labelLevel(level)} · ${esc(tx("mock"))}</b><small>${esc(tx("mockSub"))}</small></span><span class="v2-arrow">›</span></button>`));
  document.getElementById("page-tests").innerHTML=`<div class="v2-page-head"><div class="v2-kicker">HSK AI</div><h1 class="v2-title">${esc(tx("tests"))}</h1><p class="v2-subtitle">${esc(tx("testsSub"))}</p></div><div class="v2-test-list">${cards.join("")}</div>`;
}

function row(icon,title,sub,action){return `<button class="v2-row-card" onclick="${action}"><span class="v2-row-icon">${icon}</span><span><b>${esc(title)}</b><small>${esc(sub)}</small></span><span class="v2-arrow">›</span></button>`}
function renderProfile(){
  document.getElementById("page-profile").innerHTML=`<div class="v2-profile-head"><div class="v2-avatar">${labelLevel(LEVEL_KEY).replace(/\D/g,"")||"1"}</div><div><h1>HSK AI Student</h1><p>${meta.xp} XP · ${meta.streak} ${esc(tx("streak"))}</p><span class="v2-badge">${leagueName()} League</span></div></div><div class="v2-metrics v2-section"><div class="v2-metric" data-tone="gold"><strong>${meta.xp}</strong><span>XP</span></div><div class="v2-metric" data-tone="green"><strong>${completedCount()}</strong><span>${esc(tx("done"))}</span></div><div class="v2-metric" data-tone="purple"><strong>${read(MISTAKES_KEY,[]).reduce((s,m)=>s+m.count,0)}</strong><span>${esc(tx("mistakes"))}</span></div></div><div class="v2-profile-list">${row("◫",tx("training"),tx("trainingSub"),"V2.showPage('training')")}${row("◇",tx("league"),leagueName(),"V2.showPage('league')")}${row("★",tx("achievements"),`${completedCount()} / ${LESSONS.length}`,"V2.showPage('achievements')")}${row("◆",tx("subscription"),tx("subscriptionSub"),"V2.openSubscription()")}${row("⚙",tx("settings"),`${labelLevel(LEVEL_KEY)} · ${lang.toUpperCase()}`,"V2.openSettings()")}${row("?",tx("support"),"HSK AI", "V2.toast('Telegram: @hsk_ai_support')")}</div>`;
}

function renderTraining(){
  document.getElementById("page-training").innerHTML=`<div class="v2-page-head"><button class="v2-back" onclick="V2.showPage('profile')" aria-label="Back">‹</button><div class="v2-kicker">${labelLevel(LEVEL_KEY)}</div><h1 class="v2-title">${esc(tx("training"))}</h1><p class="v2-subtitle">${esc(tx("trainingSub"))}</p></div><div class="v2-profile-list">${row("◖",tx("listening"),tx("words"),"V2.openWords(true)")}${row("◌",tx("speaking"),tx("voice"),"V2.showPage('voice')")}${row("✎",tx("writing"),tx("grammar"),"V2.openGrammar()")}${row("字",tx("characters"),tx("words"),"V2.openWords(false)")}${row("!",tx("mistakes"),tx("mistakesSub"),"V2.showPage('mistakes')")}</div>`;
}

function renderMistakes(){
  const items=read(MISTAKES_KEY,[]).sort((a,b)=>b.count-a.count);
  const content=items.length?`<div class="v2-section">${items.map(item=>`<div class="v2-mistake"><div><b>${esc(item.question)}</b><p>${esc(item.correct||"")}</p></div><span class="v2-count">${item.count} ${esc(tx("mistakesCount"))}</span></div>`).join("")}</div>`:`<div class="v2-empty">${esc(tx("noMistakes"))}</div>`;
  document.getElementById("page-mistakes").innerHTML=`<div class="v2-page-head"><button class="v2-back" onclick="V2.showPage('training')" aria-label="Back">‹</button><div class="v2-kicker">HSK AI</div><h1 class="v2-title">${esc(tx("mistakes"))}</h1><p class="v2-subtitle">${esc(tx("mistakesSub"))}</p></div>${content}`;
}
function renderLeague(){
  const names=["Artem","Madina","Rustam","Dilnoza","Farid","Kamila","Akmal","Zarina"];
  const mine=meta.xp%500;
  const rows=names.map((name,index)=>({name,xp:Math.max(20,mine+140-index*38)}));rows.splice(3,0,{name:"You",xp:mine});rows.sort((a,b)=>b.xp-a.xp);
  document.getElementById("page-league").innerHTML=`<div class="v2-page-head"><button class="v2-back" onclick="V2.showPage('profile')" aria-label="Back">‹</button><div class="v2-kicker">${leagueName()}</div><h1 class="v2-title">${esc(tx("league"))}</h1><p class="v2-subtitle">Weekly ranking · ${mine}/500 XP</p></div><div class="v2-profile-list">${rows.map((item,index)=>`<div class="v2-row-card"><span class="v2-row-icon">${index+1}</span><span><b>${esc(item.name)}</b><small>${leagueName()}</small></span><strong>${item.xp} XP</strong></div>`).join("")}</div>`;
}
function renderAchievements(){
  const data=[["▦",tx("lessonMission"),completedCount(),1],["✦","100 XP",meta.xp,100],["◆",`7 ${tx("streak")}`,meta.streak,7],["字",tx("wordMission"),meta.daily.words||0,5]];
  document.getElementById("page-achievements").innerHTML=`<div class="v2-page-head"><button class="v2-back" onclick="V2.showPage('profile')" aria-label="Back">‹</button><div class="v2-kicker">HSK AI</div><h1 class="v2-title">${esc(tx("achievements"))}</h1></div><div class="v2-profile-list">${data.map(item=>`<div class="v2-row-card"><span class="v2-row-icon">${item[0]}</span><span><b>${esc(item[1])}</b><small>${Math.min(item[2],item[3])} / ${item[3]}</small></span><span class="v2-check ${item[2]>=item[3]?"":"pending"}">${item[2]>=item[3]?"✓":"○"}</span></div>`).join("")}</div>`;
}

function renderAll(){
  document.getElementById("v2-xp").textContent=meta.xp;
  document.getElementById("v2-streak").textContent=meta.streak;
  renderHome();renderCourse();renderTests();renderProfile();renderTraining();renderMistakes();renderLeague();renderAchievements();
}

function showPage(next){
  document.querySelectorAll(".v2-page,.page").forEach(el=>el.classList.toggle("active",el.id===`page-${next}`));
  const root=next==="quiz"&&["placement","mock"].includes(testMode)?"tests":["flashcards","grammar","quiz"].includes(next)?"course":next;
  document.querySelectorAll(".v2-nav button").forEach(el=>el.classList.toggle("active",el.dataset.page===root));
  if(next==="flashcards")renderFlashcards();
  if(next==="grammar")renderGrammar();
  if(next==="quiz")renderQuizFilters();
  if(next==="voice"){meta.daily.voice=1;write(META_KEY,meta);renderVoiceFrame();renderHome()}
  document.getElementById(`page-${next}`)?.scrollTo(0,0);
  bridge.reportEvent?.("v2_screen_opened",{screen:next,level:LEVEL_KEY});
}

function openLesson(number){
  const lesson=LESSONS.find(item=>item.n===Number(number));if(!lesson)return;
  if(ACCESS.status!=="active"&&meta.trialCourseCompleted&&!lessonIsDone(lesson.n)){bridge.openSubscribe?.("course_trial_completed");return}
  if(!lessonIsDone(lesson.n)&&lesson.n!==currentLesson()?.n){toast(tx("locked"));return}
  document.getElementById("v2-sheet")?.remove();
  const root=document.createElement("div");root.id="v2-sheet";root.className="v2-sheet-backdrop";
  root.innerHTML=`<div class="v2-sheet" onclick="event.stopPropagation()"><div class="v2-sheet-handle"></div><div class="v2-kicker">${labelLevel(LEVEL_KEY)} · ${esc(tx("lesson"))} ${lesson.n}</div><h2>${esc(tr(lesson.t))}</h2><p>${esc(tr(lesson.sub))}</p><div class="v2-sheet-actions"><button class="v2-secondary" onclick="V2.openWords(false,${lesson.n})">字 ${esc(tx("words"))}</button><button class="v2-secondary" onclick="V2.openGrammar(${lesson.n})">≡ ${esc(tx("grammar"))}</button><button class="v2-primary" onclick="V2.startLesson(${lesson.n})">▶ ${esc(tx("start"))}</button></div></div>`;
  root.onclick=()=>root.remove();document.body.appendChild(root);
}
function closeSheet(){document.getElementById("v2-sheet")?.remove()}
function startLesson(number){closeSheet();quizLesson=Number(number);testMode="lesson";showPage("quiz");startQuiz()}
function openWords(listen=false,lesson){closeSheet();fcFilter=lesson?Number(lesson):"all";showPage("flashcards");if(listen)toast(tx("listening"))}
function openGrammar(lesson){closeSheet();grammarFilter=lesson?Number(lesson):"all";showPage("grammar")}

function buildExamQuestions(count){
  const pool=[];
  const step=Math.max(1,Math.floor(VOCAB.length/Math.max(count,1)));
  for(let index=0;index<VOCAB.length&&pool.length<count;index+=step){const word=VOCAB[index];pool.push(vocabQuestion(word,["meaning","hanzi","pinyin"][pool.length%3]))}
  for(const lesson of LESSONS){if(pool.length>=count)break;const question=grammarQuestion(lesson.n);if(question)pool.push(question)}
  return pool.slice(0,count);
}
function beginCustomTest(mode){
  testMode=mode;quizLesson=currentLesson()?.n||1;questions=buildExamQuestions(10);answers=Array(questions.length).fill(null);qIndex=0;showPage("quiz");document.getElementById("score-box").style.display="none";document.getElementById("quiz-box").style.display="block";renderQuizQuestion();
}
function startPlacement(){beginCustomTest("placement")}
function startMock(level){if(level&&level!==LEVEL_KEY){bridge.openRoute?.({level,tab:"tests",exam:"mock"});return}beginCustomTest("mock")}

function recommendedLevel(percent){
  const base=LEVEL_KEY.startsWith("hsk4")?3:Math.max(0,["hsk1","hsk2","hsk3"].indexOf(LEVEL_KEY));
  const index=percent>=80?Math.min(3,base+1):percent<45?Math.max(0,base-1):base;
  return ["HSK 1","HSK 2","HSK 3","HSK 4"][index];
}
function rememberMistakes(items){
  const saved=read(MISTAKES_KEY,[]);
  items.forEach(item=>{const key=String(item.question||"").trim();if(!key)return;const found=saved.find(entry=>entry.question===key);if(found){found.count+=1;found.correct=item.correct_answer||found.correct}else saved.push({question:key,correct:item.correct_answer||"",count:1,lastSeen:new Date().toISOString()})});
  write(MISTAKES_KEY,saved.slice(-100));
}
function addXP(amount,kind){
  const value=Math.max(0,Math.round(amount));if(!value)return;
  meta.xp+=value;meta.daily.xp+=value;if(kind==="lesson")meta.daily.lesson=1;write(META_KEY,meta);renderAll();toast(`+${value} XP`);
}
function openChest(){
  if(!(meta.xp>0&&meta.xp%100>=80)){toast(tx("rewardLocked"));return}
  meta.chests=Number(meta.chests||0)+1;meta.xp+=20;meta.daily.xp+=20;write(META_KEY,meta);renderAll();toast("+20 XP · Reward Chest")
}

function openSettings(){
  document.getElementById("v2-sheet")?.remove();const root=document.createElement("div");root.id="v2-sheet";root.className="v2-sheet-backdrop";
  root.innerHTML=`<div class="v2-sheet" onclick="event.stopPropagation()"><div class="v2-sheet-handle"></div><h2>${esc(tx("settings"))}</h2><p>${esc(tx("language"))}</p><div class="v2-sheet-actions">${["ru","tj","uz"].map(value=>`<button class="v2-secondary" onclick="V2.changeLanguage('${value}')">${value.toUpperCase()}</button>`).join("")}</div><p>${esc(tx("level"))}</p><div class="v2-sheet-actions">${LEVELS.map(value=>`<button class="v2-secondary" onclick="V2.changeLevel('${value}')">${labelLevel(value)}</button>`).join("")}</div></div>`;root.onclick=()=>root.remove();document.body.appendChild(root);
}
function changeLanguage(value){localStorage.setItem("hsk_all_current_lang_v3",value);bridge.openRoute?.({lang:value,level:LEVEL_KEY,tab:"profile"})}
function changeLevel(value){bridge.openRoute?.({level:value,lang,tab:"course"})}
function openSubscription(){bridge.openSubscribe?.("v2_profile")}

function toast(message){document.querySelector(".v2-toast")?.remove();const item=document.createElement("div");item.className="v2-toast";item.textContent=message;document.body.appendChild(item);setTimeout(()=>item.remove(),2200)}

async function showOnboarding(){
  const query=new URLSearchParams(parent.location.search||location.search);if(query.get("tab")||query.get("lesson"))return;
  const nextAccess=await bridge.ensureAccess?.();ACCESS=nextAccess||bridge.getAccess?.()||ACCESS;
  if(ACCESS.course_profile?.onboarding_completed)return;
  if(localStorage.getItem(ONBOARDING_KEY)&&!bridge.hasAuth?.()&&!ACCESS.course_profile)return;
  const profile=ACCESS.course_profile||{};
  meta.goal=profile.goal||meta.goal;meta.minutes=Number(profile.daily_minutes||meta.minutes||10);
  onboarding.goal=["hsk_exam","study_china","work_china","daily_communication","travel"].includes(meta.goal)?meta.goal:"hsk_exam";onboarding.minutes=meta.minutes;onboarding.startMode=profile.has_progress?"continue":"lesson_1";
  renderOnboarding();
  bridge.reportEvent?.("onboarding_started",{event_id:`onboarding:${today()}`,level:onboarding.level});
}
function renderOnboarding(){
  document.getElementById("v2-onboarding")?.remove();const root=document.createElement("div");root.id="v2-onboarding";root.className="v2-onboarding";
  const steps=[
    {title:tx("chooseLevel"),sub:tx("pathSub"),values:[["beginner","Beginner"],["hsk1","HSK 1"],["hsk2","HSK 2"],["hsk3","HSK 3"],["hsk4","HSK 4"]],field:"level"},
    {title:tx("chooseGoal"),sub:tx("onboardingTitle"),values:[["hsk_exam",tx("goalHsk")],["study_china",tx("goalStudy")],["work_china",tx("goalWork")],["daily_communication",tx("goalDaily")],["travel",tx("goalTravel")]],field:"goal"},
    {title:tx("chooseTime"),sub:tx("dailyGoal"),values:[[5,"5 min"],[10,"10 min"],[15,"15 min"],[20,"20 min"]],field:"minutes"},
    {title:tx("chooseStart"),sub:tx("onboardingSub"),values:[["lesson_1",tx("startLesson1")],["continue",tx("continueProgress")],["placement",tx("takePlacement")]],field:"startMode"}
  ];
  const step=steps[onboardingStep];
  root.innerHTML=`<div class="v2-onboard-progress">${steps.map((_,i)=>`<i class="${i<=onboardingStep?"on":""}"></i>`).join("")}</div><div class="v2-onboard-body"><div class="v2-brand-mark">汉</div><h1>${esc(step.title)}</h1><p>${esc(step.sub)}</p><div class="v2-choice-list">${step.values.map(value=>`<button class="v2-choice ${String(onboarding[step.field])===String(value[0])?"selected":""}" onclick="V2.pickOnboarding('${step.field}','${value[0]}')">${esc(value[1])}</button>`).join("")}</div></div><div class="v2-onboard-footer">${onboardingStep?`<button class="v2-secondary" ${onboardingSubmitting?"disabled":""} onclick="V2.onboardingBack()">‹ ${esc(tx("back"))}</button>`:"<span></span>"}<button class="v2-primary" ${onboardingSubmitting?"disabled":""} onclick="V2.onboardingNext()">${esc(onboardingSubmitting?tx("saving"):onboardingStep===steps.length-1?tx("finish"):tx("next"))} ›</button></div>`;
  document.body.appendChild(root);
}
function pickOnboarding(field,value){onboarding[field]=field==="minutes"?Number(value):value;const events={level:"level_selected",goal:"goal_selected",minutes:"daily_time_selected",startMode:"start_point_selected"};bridge.reportEvent?.(events[field],{event_id:`onboarding:${field}:${value}`,level:onboarding.level,[field]:onboarding[field]});renderOnboarding()}
function onboardingBack(){onboardingStep=Math.max(0,onboardingStep-1);renderOnboarding()}
async function onboardingNext(){
  if(onboardingSubmitting)return;
  if(onboardingStep<3){onboardingStep+=1;renderOnboarding();return}
  onboardingSubmitting=true;renderOnboarding();
  const payload={level:onboarding.level,goal:onboarding.goal,daily_minutes:onboarding.minutes,start_mode:onboarding.startMode,timezone_offset_minutes:-new Date().getTimezoneOffset()};
  try{
    let result=null;
    try{result=await bridge.completeOnboarding?.(payload)}catch(error){if(bridge.hasAuth?.())throw error}
    if(!result){
      result={level:onboarding.level==="beginner"?"hsk1":onboarding.level==="hsk4"?"hsk4a":onboarding.level,lesson:onboarding.startMode==="lesson_1"?1:null,tab:onboarding.startMode==="placement"?"tests":"course",placement:onboarding.startMode==="placement"};
    }
    meta.goal=onboarding.goal;meta.minutes=onboarding.minutes;write(META_KEY,meta);localStorage.setItem(ONBOARDING_KEY,"1");
    const route={level:result.level||LEVEL_KEY,lang,tab:result.tab||"course"};if(result.lesson)route.lesson=result.lesson;if(result.placement)route.exam="placement";bridge.openRoute?.(route);
  }catch(_){onboardingSubmitting=false;renderOnboarding();toast(tx("onboardingError"))}
}

const legacyFinishQuiz=finishQuiz;
const legacyFlipFC=flipFC;
finishQuiz=function(){
  const mode=testMode;legacyFinishQuiz();rememberMistakes(lastWrongItems);
  if(mode==="lesson"&&lastQuizPercent>=60&&ACCESS.status!=="active"){meta.trialCourseCompleted=true;write(META_KEY,meta)}
  if(lastQuizPercent>=60&&!state.done.includes(quizLesson)){state.done.push(quizLesson);saveState();addXP(20+Math.round(lastQuizPercent/10),"lesson")}else addXP(Math.max(5,Math.round(lastQuizPercent/10)),"quiz");
  if(mode==="lesson"&&lastQuizPercent>=60){
    bridge.reportEvent?.("v2_lesson_completed",{lesson_id:quizLesson,percent:lastQuizPercent,score:lastQuizScore,total:lastQuizTotal});
  }
  if(mode==="placement"){
    const recommended=recommendedLevel(lastQuizPercent);write("hsk_v2_placement",{percent:lastQuizPercent,recommended,createdAt:new Date().toISOString()});
    document.getElementById("score-box")?.insertAdjacentHTML("beforeend",`<div class="v2-goal" style="margin-top:12px"><div class="v2-kicker">${esc(tx("recommended"))}</div><h2 style="margin-top:6px">${recommended}</h2></div>`);
  }
  renderAll();testMode="";
};
flipFC=function(index){const card=document.querySelector(`[data-card="${index}"]`),was=card?.classList.contains("flipped");legacyFlipFC(index);setTimeout(()=>{const now=document.querySelector(`[data-card="${index}"]`)?.classList.contains("flipped");if(!was&&now){meta.daily.words=Math.min(5,Number(meta.daily.words||0)+1);write(META_KEY,meta);renderHome()}},80)};
renderKPIs=function(){renderHome()};
renderLessons=function(){renderCourse();renderHome()};

function applyLaunch(){
  const params=bridge.getLaunchParams?.()||{};
  const target=normalizeLaunchTab(params.tab);
  if(params.exam==="mock")setTimeout(()=>startMock(),0);
  else if(params.exam==="placement")setTimeout(()=>startPlacement(),0);
  else if(params.mode==="quiz"){quizLesson=Number(params.lesson)||quizLesson;showPage("quiz");startQuiz()}
  else if(target){if(params.lesson){if(target==="flashcards")fcFilter=Number(params.lesson);if(target==="grammar")grammarFilter=Number(params.lesson);if(target==="quiz")quizLesson=Number(params.lesson)}showPage(target);if(target==="course"&&params.lesson)setTimeout(()=>openLesson(Number(params.lesson)),0)}
  else {const page=["home","course","voice","tests","profile"].includes(params.tab)?params.tab:"home";showPage(page)}
}

function mount(){
  normalizeMeta();document.body.innerHTML=appMarkup();
  window.V2={showPage,openLesson,startLesson,openWords,openGrammar,startPlacement,startMock,openChest,openSettings,changeLanguage,changeLevel,openSubscription,toast,pickOnboarding,onboardingBack,onboardingNext};
  window.setAppAccess=function(next){ACCESS=next||bridge.getAccess?.()||ACCESS;renderAll()};
  window.setAppLanguage=function(next){lang=["uz","ru","tj"].includes(next)?next:lang;setLabels();renderFlashcards();renderGrammar();renderQuizFilters();renderAll()};
  setLabels();renderFlashcards();renderGrammar();renderQuizFilters();renderAll();applyLaunch();showOnboarding();
}

mount();
})();
