(function(){
"use strict";

const META_KEY="hsk_v2_meta_v1";
const ONBOARDING_KEY="hsk_v2_onboarding_v1";
const MISTAKES_KEY="hsk_v2_mistakes_v1";
const AVATAR_KEY="hsk_v2_avatar_v1";
const LEVELS=["hsk1","hsk2","hsk3","hsk4a","hsk4b"];
const copy={
  ru:{
    home:"Главная",course:"Уроки",voice:"Голос",tests:"Тесты",profile:"Профиль",
    welcome:"Продолжим китайский",today:"Сегодня",continue:"Продолжить урок",dailyGoal:"Дневная цель",minutes:"минут",
    missions:"Задания на сегодня",lessonMission:"Завершить урок",wordMission:"Повторить 5 слов",voiceMission:"Голосовая практика",
    yourProgress:"Ваш прогресс",league:"Рейтинг",achievements:"Достижения",reward:"Награда",openChest:"Открыть сундук",
    path:"Учебный путь",pathSub:"Короткие интерактивные уроки по порядку HSK",completed:"завершено",lesson:"Урок",
    current:"Текущий урок",done:"Пройдено",locked:"Сначала завершите предыдущий урок",review:"Повторение",boss:"Контрольная",
    start:"Начать",words:"Слова",grammar:"Грамматика",practice:"Практика",lessonReady:"Выберите формат тренировки",
    testCenter:"Центр тестов",testCenterSub:"Уровень, экзамен HSK, произношение, иероглифы и пиньинь",
    testsSub:"Проверьте уровень и подготовьтесь к экзамену",placement:"Тест уровня",placementSub:"10-20 вопросов и автоматическая рекомендация уровня",
    hskExams:"Тесты HSK",pronunciationTest:"Тест произношения",characterTest:"Тест иероглифов",pinyinTest:"Тест пиньиня",
    mock:"Пробный экзамен",mockSub:"HSK-структура, балл 0-100, сильные и слабые стороны",startTest:"Начать тест",
    training:"Тренировка",trainingSub:"Отдельная работа над конкретным навыком",listening:"Аудирование",speaking:"Разговор",
    writing:"Письмо",characters:"Иероглифы",mistakes:"Мои ошибки",mistakesSub:"Слабые места из ваших последних квизов",
    settings:"Настройки",language:"Язык интерфейса",level:"Уровень курса",subscription:"Подписка",subscriptionSub:"Управление доступом в существующем разделе",
    support:"Поддержка",supportSub:"Написать админу",notifications:"Уведомления",streak:"дней",xp:"очков",noMistakes:"Ошибок пока нет. Завершите квиз, и здесь появится персональная тренировка.",
    mistakesCount:"ошибок",recommended:"Рекомендуемый уровень",rewardReady:"Сундук готов",rewardLocked:"Заработайте ещё очки",
    energy:"Энергия",energySub:"Не блокирует уроки, только усиливает награды",leaguePoints:"очков рейтинга",weeklyReset:"Сброс в понедельник",leagueSize:"25 учеников в лиге",paidBadge:"Подписка",
    streakCalendar:"Календарь занятий",streakFreeze:"защита серии",milestones:"3 / 7 / 30 дней",rewardChest:"Сундук",
    freeLessonTitle:"Вы завершили бесплатный урок.",freeLessonText:"Продолжайте обучение с полным доступом ко всем урокам, голосовой практике, тестам и анализу ошибок.",subscribeAction:"💳 Оформить подписку",
    timeSpent:"Время",leagueMove:"Вы поднимаетесь в рейтинге",leaguePassed:"Вы обошли {name}!",leagueNeed:"Заработайте ещё {xp} очков, чтобы обойти {name}",leagueCta:"Я справлюсь",mistakesShort:"Ошибки",strengths:"Сильные стороны",weaknesses:"Слабые стороны",recommendedLessons:"Рекомендуемые уроки",
    onboardingTitle:"Китайский для реального общения",onboardingSub:"Соберём короткий план и сразу откроем первый урок.",
    chooseGoal:"Зачем вы учите китайский?",chooseLevel:"Какой у вас уровень?",chooseTime:"Сколько минут в день?",chooseStart:"Откуда начать?",
    next:"Далее",back:"Назад",finish:"Начать обучение",saving:"Сохраняем...",onboardingError:"Не удалось сохранить настройки. Попробуйте ещё раз.",goalHsk:"Сдать HSK",goalStudy:"Учиться в Китае",goalWork:"Работать в Китае",goalTravel:"Путешествовать",goalDaily:"Общаться каждый день",startLesson1:"Начать с урока 1",continueProgress:"Продолжить текущий прогресс",takePlacement:"Пройти тест уровня",
    loadingLesson:"Готовим урок...",lessonLoadError:"Не удалось открыть урок",sayAloud:"Произнесите вслух",said:"Я произнёс",check:"Проверить",reset:"Сбросить",correct:"Верно",incorrect:"Нужно повторить",lessonComplete:"Урок завершён",submitLesson:"Завершить урок",retryLesson:"Повторить урок",continueCourse:"Продолжить курс",unlockMore:"Открыть следующие уроки",reviewNow:"Повторить ошибки",loadingMistakes:"Загружаем слабые места...",
    sectionComplete:"Раздел завершён",chapterComplete:"Часть {chapter} завершена!",bookLessonComplete:"{level} Урок {lesson} завершён!",nextSection:"Следующий раздел",nextChapter:"Открыть следующую часть",claimXp:"Забрать очки",part:"часть",totalXp:"Всего очков",rewardTitle:"Отлично!",streakInRow:"{days} дней подряд",noMistakeTitle:"Без ошибок",keepGoing:"Продолжайте серию",
    traceHint:"Посмотрите порядок написания",traceDone:"Понятно",micReady:"Нажмите и произнесите",
    unitWords:"Слова",unitSound:"Звук",unitCharacter:"Иероглиф",unitDialog:"Диалог",unitBuild:"Сборка",unitSpeaking:"Произношение",unitReview:"Проверка",
    levelMetric:"ступень",uploadAvatar:"Сменить фото",userProfile:"Профиль ученика",beginnerLevel:"Новичок"
  },
  uz:{
    home:"Asosiy",course:"Darslar",voice:"Ovoz",tests:"Testlar",profile:"Profil",
    welcome:"Xitoy tilini davom ettiramiz",today:"Bugun",continue:"Darsni davom ettirish",dailyGoal:"Kunlik maqsad",minutes:"daqiqa",
    missions:"Bugungi vazifalar",lessonMission:"Darsni tugatish",wordMission:"5 ta so'zni takrorlash",voiceMission:"Ovozli mashq",
    yourProgress:"Progressingiz",league:"Reyting",achievements:"Yutuqlar",reward:"Mukofot",openChest:"Sandiqni ochish",
    path:"O'quv yo'li",pathSub:"HSK tartibidagi qisqa interaktiv darslar",completed:"tugallandi",lesson:"Dars",
    current:"Joriy dars",done:"Tugallangan",locked:"Avval oldingi darsni tugating",review:"Takrorlash",boss:"Nazorat",
    start:"Boshlash",words:"So'zlar",grammar:"Grammatika",practice:"Mashq",lessonReady:"Mashq turini tanlang",
    testCenter:"Test markazi",testCenterSub:"Daraja, HSK imtihon, talaffuz, iyeroglif va pin'in",
    testsSub:"Darajangizni tekshiring va imtihonga tayyorlaning",placement:"Daraja testi",placementSub:"10-20 savol va avtomatik daraja tavsiyasi",
    hskExams:"HSK testlari",pronunciationTest:"Talaffuz testi",characterTest:"Iyeroglif testi",pinyinTest:"Pin'in testi",
    mock:"Sinov imtihoni",mockSub:"HSK tuzilmasi, 0-100 ball, kuchli va zaif tomonlar",startTest:"Testni boshlash",
    training:"Mashqlar",trainingSub:"Alohida ko'nikmani mustaqil rivojlantirish",listening:"Tinglash",speaking:"Gapirish",writing:"Yozish",characters:"Ierogliflar",
    mistakes:"Xatolarim",mistakesSub:"Quizlarda aniqlangan zaif joylaringiz",settings:"Sozlamalar",language:"Interfeys tili",level:"Kurs darajasi",
    subscription:"Obuna",subscriptionSub:"Mavjud bo'limda imkoniyatni boshqarish",support:"Yordam",supportSub:"Adminga yozish",notifications:"Bildirishnomalar",streak:"kun",xp:"ochko",
    noMistakes:"Hozircha xato yo'q. Quizni tugating, personal mashqlar shu yerda paydo bo'ladi.",mistakesCount:"xato",recommended:"Tavsiya etilgan daraja",
    rewardReady:"Sandiq tayyor",rewardLocked:"Yana ochko yig'ing",energy:"Energiya",energySub:"Darsni bloklamaydi, faqat mukofotni kuchaytiradi",leaguePoints:"reyting ochko",weeklyReset:"Dushanba kuni yangilanadi",leagueSize:"Ligada 25 o'quvchi",paidBadge:"Obuna",
    streakCalendar:"Seriya kalendari",streakFreeze:"Seriya himoyasi",milestones:"3 / 7 / 30 kun",rewardChest:"Sandiq",
    freeLessonTitle:"Bepul darsingiz tugadi.",freeLessonText:"Barcha darslar, ovozli mashq, testlar va xatolar tahlili uchun to'liq imkoniyat bilan davom eting.",subscribeAction:"💳 Obuna olish",
    timeSpent:"Vaqt",leagueMove:"Reytingda yuqoriga chiqyapsiz",leaguePassed:"{name}dan o'tdingiz!",leagueNeed:"{name}dan o'tish uchun yana {xp} ochko oling",leagueCta:"Eplayman",mistakesShort:"Xatolar",strengths:"Kuchli tomonlar",weaknesses:"Zaif tomonlar",recommendedLessons:"Tavsiya darslar",
    onboardingTitle:"Real muloqot uchun xitoy tili",onboardingSub:"Qisqa reja tuzamiz va birinchi darsni darhol ochamiz.",
    chooseGoal:"Xitoy tilini nima uchun o'rganyapsiz?",chooseLevel:"Darajangiz qaysi?",chooseTime:"Kuniga necha daqiqa?",chooseStart:"Qayerdan boshlaysiz?",
    next:"Keyingi",back:"Orqaga",finish:"O'qishni boshlash",saving:"Saqlanmoqda...",onboardingError:"Sozlamalarni saqlab bo'lmadi. Qayta urinib ko'ring.",goalHsk:"HSK topshirish",goalStudy:"Xitoyda o'qish",goalWork:"Xitoyda ishlash",goalTravel:"Sayohat",goalDaily:"Har kuni gaplashish",startLesson1:"1-darsdan boshlash",continueProgress:"Joriy progressdan davom etish",takePlacement:"Daraja testini topshirish",
    loadingLesson:"Dars tayyorlanmoqda...",lessonLoadError:"Darsni ochib bo'lmadi",sayAloud:"Ovoz chiqarib ayting",said:"Aytdim",check:"Tekshirish",reset:"Tozalash",correct:"To'g'ri",incorrect:"Qayta mashq qiling",lessonComplete:"Dars tugallandi",submitLesson:"Darsni yakunlash",retryLesson:"Darsni qaytarish",continueCourse:"Kursni davom ettirish",unlockMore:"Keyingi darslarni ochish",reviewNow:"Xatolarni takrorlash",loadingMistakes:"Zaif joylar yuklanmoqda...",
    sectionComplete:"Bosqich tugadi",chapterComplete:"{chapter} qism tugadi!",bookLessonComplete:"{level} {lesson}-dars tugadi!",nextSection:"Keyingi bosqich",nextChapter:"Keyingi qismni ochish",claimXp:"Ochko olish",part:"qism",totalXp:"Jami ochko",rewardTitle:"Zo'r!",streakInRow:"{days} kun ketma-ket",noMistakeTitle:"Xatosiz",keepGoing:"Seriyani davom ettiring",
    traceHint:"Yozilish tartibini ko'ring",traceDone:"Tushundim",micReady:"Bosib talaffuz qiling",
    unitWords:"So'zlar",unitSound:"Tovush",unitCharacter:"Iyeroglif",unitDialog:"Dialog",unitBuild:"Yig'ish",unitSpeaking:"Talaffuz",unitReview:"Tekshiruv",
    levelMetric:"bosqich",uploadAvatar:"Rasmni almashtirish",userProfile:"O'quvchi profili",beginnerLevel:"Boshlovchi"
  },
  tj:{
    home:"Асосӣ",course:"Дарсҳо",voice:"Овоз",tests:"Тестҳо",profile:"Профил",
    welcome:"Омӯзиши чиниро идома медиҳем",today:"Имрӯз",continue:"Идомаи дарс",dailyGoal:"Ҳадафи рӯз",minutes:"дақиқа",
    missions:"Вазифаҳои имрӯз",lessonMission:"Анҷоми дарс",wordMission:"Такрори 5 калима",voiceMission:"Машқи овозӣ",
    yourProgress:"Пешрафти шумо",league:"Рейтинг",achievements:"Дастовардҳо",reward:"Мукофот",openChest:"Кушодани сандуқ",
    path:"Роҳи омӯзиш",pathSub:"Дарсҳои кӯтоҳи интерактивӣ бо тартиби HSK",completed:"анҷом шуд",lesson:"Дарс",
    current:"Дарси ҷорӣ",done:"Анҷомшуда",locked:"Аввал дарси пешинаро анҷом диҳед",review:"Такрор",boss:"Санҷиш",
    start:"Оғоз",words:"Калимаҳо",grammar:"Грамматика",practice:"Машқ",lessonReady:"Навъи машқро интихоб кунед",
    testCenter:"Маркази тест",testCenterSub:"Сатҳ, имтиҳони HSK, талаффуз, иероглиф ва пинйин",
    testsSub:"Сатҳи худро санҷед ва ба имтиҳон омода шавед",placement:"Тести сатҳ",placementSub:"10-20 савол ва тавсияи автоматии сатҳ",
    hskExams:"Тестҳои HSK",pronunciationTest:"Тести талаффуз",characterTest:"Тести иероглиф",pinyinTest:"Тести пинйин",
    mock:"Имтиҳони санҷишӣ",mockSub:"Сохтори HSK, хол 0-100, ҷиҳатҳои қавӣ ва суст",startTest:"Оғози тест",
    training:"Машқҳо",trainingSub:"Кор бо малакаи алоҳида",listening:"Шунидан",speaking:"Гуфтугӯ",writing:"Навиштан",characters:"Иероглифҳо",
    mistakes:"Хатоҳои ман",mistakesSub:"Ҷойҳои суст аз квизҳои шумо",settings:"Танзимот",language:"Забони интерфейс",level:"Сатҳи курс",
    subscription:"Обуна",subscriptionSub:"Идораи дастрасӣ дар бахши мавҷуда",support:"Дастгирӣ",supportSub:"Ба admin навиштан",notifications:"Огоҳиҳо",streak:"рӯз",xp:"хол",
    noMistakes:"Ҳоло хато нест. Квизро анҷом диҳед, машқи шахсӣ дар ин ҷо пайдо мешавад.",mistakesCount:"хато",recommended:"Сатҳи тавсияшуда",
    rewardReady:"Сандуқ тайёр",rewardLocked:"Боз хол гиред",energy:"Энергия",energySub:"Омӯзишро намебандад, танҳо мукофотро зиёд мекунад",leaguePoints:"холи рейтинг",weeklyReset:"Рӯзи душанбе нав мешавад",leagueSize:"25 омӯзанда дар лига",paidBadge:"Обуна",
    streakCalendar:"Тақвими силсила",streakFreeze:"Ҳимояи силсила",milestones:"3 / 7 / 30 рӯз",rewardChest:"Сандуқ",
    freeLessonTitle:"Дарси ройгони шумо анҷом шуд.",freeLessonText:"Барои ҳамаи дарсҳо, машқи овозӣ, тестҳо ва таҳлили хатоҳо бо дастрасии пурра идома диҳед.",subscribeAction:"💳 Обуна гирифтан",
    timeSpent:"Вақт",leagueMove:"Дар рейтинг боло меравед",leaguePassed:"Аз {name} гузаштед!",leagueNeed:"Барои гузаштан аз {name} боз {xp} хол гиред",leagueCta:"Метавонам",mistakesShort:"Хатоҳо",strengths:"Ҷиҳатҳои қавӣ",weaknesses:"Ҷиҳатҳои суст",recommendedLessons:"Дарсҳои тавсияшуда",
    onboardingTitle:"Забони чинӣ барои муоширати воқеӣ",onboardingSub:"Нақшаи кӯтоҳ месозем ва дарси аввалро мекушоем.",
    chooseGoal:"Барои чӣ забони чинӣ меомӯзед?",chooseLevel:"Сатҳи шумо кадом аст?",chooseTime:"Дар як рӯз чанд дақиқа?",chooseStart:"Аз куҷо оғоз мекунед?",
    next:"Баъдӣ",back:"Бозгашт",finish:"Оғози омӯзиш",saving:"Нигоҳ дошта мешавад...",onboardingError:"Танзимот нигоҳ дошта нашуд. Аз нав кӯшиш кунед.",goalHsk:"Супоридани HSK",goalStudy:"Таҳсил дар Чин",goalWork:"Кор дар Чин",goalTravel:"Саёҳат",goalDaily:"Ҳар рӯз гуфтугӯ кардан",startLesson1:"Аз дарси 1 оғоз кардан",continueProgress:"Идомаи пешрафти ҷорӣ",takePlacement:"Супоридани тести сатҳ",
    loadingLesson:"Дарс омода мешавад...",lessonLoadError:"Дарс кушода нашуд",sayAloud:"Бо овози баланд гӯед",said:"Гуфтам",check:"Санҷидан",reset:"Тоза кардан",correct:"Дуруст",incorrect:"Боз машқ кунед",lessonComplete:"Дарс анҷом шуд",submitLesson:"Анҷоми дарс",retryLesson:"Такрори дарс",continueCourse:"Идомаи курс",unlockMore:"Кушодани дарсҳои навбатӣ",reviewNow:"Такрори хатоҳо",loadingMistakes:"Ҷойҳои суст бор мешаванд...",
    sectionComplete:"Қисм анҷом шуд",chapterComplete:"Қисми {chapter} анҷом шуд!",bookLessonComplete:"{level} дарси {lesson} анҷом шуд!",nextSection:"Қисми баъдӣ",nextChapter:"Кушодани қисми баъдӣ",claimXp:"Гирифтани хол",part:"қисм",totalXp:"Ҳамагӣ хол",rewardTitle:"Офарин!",streakInRow:"{days} рӯз пай дар пай",noMistakeTitle:"Бе хато",keepGoing:"Силсиларо давом диҳед",
    traceHint:"Тартиби навиштро бинед",traceDone:"Фаҳмо",micReady:"Пахш карда талаффуз кунед",
    unitWords:"Калимаҳо",unitSound:"Овоз",unitCharacter:"Иероглиф",unitDialog:"Муколама",unitBuild:"Сохтан",unitSpeaking:"Талаффуз",unitReview:"Санҷиш",
    levelMetric:"зина",uploadAvatar:"Иваз кардани сурат",userProfile:"Профили омӯзанда",beginnerLevel:"Навомӯз"
  }
};

const today=()=>new Date().toLocaleDateString("en-CA");
const yesterday=()=>{const d=new Date();d.setDate(d.getDate()-1);return d.toLocaleDateString("en-CA")};
const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key)||JSON.stringify(fallback))}catch(_){return fallback}};
const write=(key,value)=>localStorage.setItem(key,JSON.stringify(value));
const tx=key=>(copy[lang]||copy.ru)[key]||copy.ru[key]||key;
const labelLevel=value=>value==="hsk4a"?"HSK 4 上":value==="hsk4b"?"HSK 4 下":String(value||LEVEL_KEY).toUpperCase().replace("HSK","HSK ");
function avatarMarkup(value,fallback="A"){
  const raw=String(value||"").trim();
  if(raw.startsWith("data:image/"))return `<img src="${esc(raw)}" alt="">`;
  return esc((raw||fallback||"A").slice(0,2).toUpperCase());
}
const launchCurrent=Number(launchLesson)||0;
const lessonByNumber=number=>LESSONS.find(item=>Number(item.n)===Number(number));
const chapterLabel=index=>String.fromCharCode(65+Math.max(0,Math.min(25,Number(index)||0)));
function sectionSize(){if(LEVEL_KEY==="hsk1"||LEVEL_KEY==="hsk2")return 2;if(LEVEL_KEY==="hsk3")return 3;return 4}
function lessonWords(number){return VOCAB.filter(word=>Number(word.l)===Number(number))}
function splitWords(words){
  const maxSize=sectionSize(),chunks=[];
  if(!words.length)return[[]];
  let count=Math.max(1,Math.ceil(words.length/maxSize));
  while(count>1&&Math.floor(words.length/count)<2)count-=1;
  const base=Math.floor(words.length/count),extra=words.length%count;
  let cursor=0;
  for(let index=0;index<count;index++){const size=base+(index<extra?1:0);chunks.push(words.slice(cursor,cursor+size));cursor+=size}
  return chunks.length?chunks:[[]];
}
function lessonSections(lesson){
  if(!lesson)return[];
  const chunks=splitWords(lessonWords(lesson.n));
  return chunks.map((words,index)=>{
    const no=index+1,chapterIndex=Math.floor(index/3),chapter=chapterLabel(chapterIndex);
    return{lesson:lesson.n,key:`${lesson.n}.${no}`,no,count:chunks.length,chapter,chapterIndex,chapterStart:chapterIndex*3+1,chapterEnd:Math.min(chapterIndex*3+3,chunks.length),words};
  });
}
function allCourseSections(){return LESSONS.flatMap(lesson=>lessonSections(lesson))}
function sectionStoreKey(section){return `${LEVEL_KEY}:${section.key}`}
function localSectionDone(section){return Boolean(meta.completedSections&&meta.completedSections[sectionStoreKey(section)])}
function bookLessonIsDone(number){
  if(state.done.includes(Number(number))||(launchCurrent>1&&Number(number)<launchCurrent))return true;
  const sections=lessonSections(lessonByNumber(number));
  return Boolean(sections.length&&sections.every(localSectionDone));
}
const lessonIsDone=number=>bookLessonIsDone(number);
function sectionIsDone(section){return bookLessonIsDone(section.lesson)||localSectionDone(section)}
function completedSectionCount(){return allCourseSections().filter(sectionIsDone).length}
function sectionProgress(){const all=allCourseSections();return Math.round(completedSectionCount()/Math.max(all.length,1)*100)}
function completedCount(){return LESSONS.filter(item=>bookLessonIsDone(item.n)).length}
function currentSection(){const all=allCourseSections();return all.find(section=>!sectionIsDone(section))||all[all.length-1]}
function jumpToCurrentSection(){const section=currentSection();if(section)openLesson(section.lesson,section.key)}
function currentLesson(){const section=currentSection();return lessonByNumber(section?.lesson)||LESSONS.find(item=>!bookLessonIsDone(item.n))||LESSONS[LESSONS.length-1]}
function completedLessonSectionKeys(lesson){
  if(!lesson)return[];
  const sections=lessonSections(lesson);
  if(bookLessonIsDone(lesson.n))return sections.map(section=>section.key);
  return sections.filter(localSectionDone).map(section=>section.key);
}
function markSectionDone(sectionKey){
  if(!sectionKey)return;
  meta.completedSections=meta.completedSections||{};
  meta.completedSections[`${LEVEL_KEY}:${sectionKey}`]=new Date().toISOString();
  write(META_KEY,meta);
}
function uploadAvatar(event){
  const file=event?.target?.files?.[0];
  if(!file)return;
  if(!String(file.type||"").startsWith("image/")){toast(tx("lessonLoadError"));return}
  const reader=new FileReader();
  reader.onload=()=>{write(AVATAR_KEY,String(reader.result||""));renderProfile();renderLeague();toast(tx("uploadAvatar"))};
  reader.readAsDataURL(file);
}

let meta=read(META_KEY,{xp:0,streak:0,lastActive:"",daily:{date:today(),xp:0,lesson:0,words:0,voice:0},chests:0,goal:"hsk_exam",minutes:10,completedSections:{}});
let testMode="";
let onboardingStep=0;
let onboardingSubmitting=false;
let onboarding={goal:["hsk_exam","study_china","work_china","daily_communication","travel"].includes(meta.goal)?meta.goal:"hsk_exam",level:LEVEL_KEY.startsWith("hsk4")?"hsk4":LEVEL_KEY,minutes:meta.minutes||10,startMode:"lesson_1"};
let lessonFlow=null,lessonCardIndex=0,lessonResponses={},lessonSubmitting=false,lessonOrderRemaining=[],lessonOrderSelected=[];
let practiceSession=null,mistakeReviewSession=null,serverMistakes=null,mistakesLoading=false,serverGamification=ACCESS.gamification||null,gamificationLoading=false,serverProfile=null,profileLoading=false;

function normalizeMeta(){
  if(!meta.completedSections||typeof meta.completedSections!=="object")meta.completedSections={};
  if(serverGamification){meta.xp=Number(serverGamification.xp||0);meta.streak=Number(serverGamification.streak||0);write(META_KEY,meta);return}
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
    <header class="v2-topbar"><div class="v2-brand"><div class="v2-brand-mark">汉</div><div><strong>HSK AI</strong><small>${labelLevel(LEVEL_KEY)}</small></div></div><div class="v2-top-stats"><button class="v2-stat" data-tone="coral" onclick="V2.showPage('profile')" aria-label="${esc(tx("streak"))}">◆ <span id="v2-streak">0</span></button><button class="v2-stat" data-tone="gold" onclick="V2.showPage('profile')" aria-label="${esc(tx("xp"))}">✦ <span id="v2-xp">0</span></button></div></header>
    <main class="v2-pages">
      <section id="page-home" class="v2-page"></section>
      <section id="page-course" class="v2-page"></section>
      <section id="page-lesson" class="v2-page"></section>
      <section id="page-flashcards" class="page v2-page"><header class="page-header"><button class="v2-back" onclick="V2.showPage('training')" aria-label="${esc(tx("back"))}">‹</button><div class="eyebrow" id="fc-level-label"></div><h1 class="page-title" data-i18n="flashcards"></h1><p class="page-sub" data-i18n="flashcardSub"></p></header><div class="toolbar"><input id="search" class="search" data-placeholder="search" oninput="renderFlashcards()"></div><div class="filters" id="fc-filters"></div><main class="grid" id="fc-grid"></main></section>
      <section id="page-grammar" class="page v2-page"><header class="page-header"><button class="v2-back" onclick="V2.showPage('training')" aria-label="${esc(tx("back"))}">‹</button><div class="eyebrow" id="grammar-level-label"></div><h1 class="page-title" data-i18n="grammar"></h1><p class="page-sub" data-i18n="grammarSub"></p></header><div class="filters" id="grammar-filters"></div><main class="list" id="grammar-list"></main></section>
      <section id="page-quiz" class="page v2-page"><header class="page-header quiz-header-compact"><button class="v2-back" onclick="V2.quizBack()" aria-label="${esc(tx("back"))}">‹</button><div class="eyebrow" id="quiz-level-label"></div></header><div class="filters" id="quiz-filters"></div><main class="quiz-wrap"><div id="quiz-box" class="quiz-box"></div><div id="score-box" class="score-box" style="display:none"></div></main></section>
      <section id="page-voice" class="page v2-page no-top-pad"><main class="voice-wrap"><iframe id="voice-frame" class="voice-frame" title="${esc(tx("voice"))}" allow="microphone; autoplay"></iframe></main></section>
      <section id="page-tests" class="v2-page"></section>
      <section id="page-profile" class="v2-page"></section>
      <section id="page-training" class="v2-page"></section>
      <section id="page-mistakes" class="v2-page"></section>
      <section id="page-league" class="v2-page"></section>
      <section id="page-achievements" class="v2-page"></section>
      <div id="kpis" hidden></div><div id="lesson-list" hidden></div>
    </main>
    <nav class="v2-nav">
      ${navButton("home","⌂",tx("home"))}${navButton("course","◉",tx("course"))}${navButton("league","🏆",tx("league"),"elevated")}${navButton("voice","◌",tx("voice"))}${navButton("profile","◎",tx("profile"))}
    </nav>
  </div>`;
}

function navButton(page,icon,label,extra=""){return `<button data-page="${page}" class="${extra}" onclick="V2.showPage('${page}')"><b>${icon}</b><span>${esc(label)}</span></button>`}
function progress(){return sectionProgress()}
function xpLevel(){return Math.floor(meta.xp/250)+1}
function leagueName(){return serverGamification?.league||["Bronze","Silver","Gold","Diamond","Sapphire","Legend"][Math.min(5,Math.floor(meta.xp/500))]}
function leagueLabel(value=leagueName()){
  const labels={
    ru:{Bronze:"Бронза",Silver:"Серебро",Gold:"Золото",Diamond:"Алмаз",Sapphire:"Сапфир",Legend:"Легенда"},
    uz:{Bronze:"Bronza",Silver:"Kumush",Gold:"Oltin",Diamond:"Olmos",Sapphire:"Safir",Legend:"Afsona"},
    tj:{Bronze:"Биринҷӣ",Silver:"Нуқра",Gold:"Тилло",Diamond:"Алмос",Sapphire:"Сафир",Legend:"Афсона"}
  };
  return labels[lang]?.[value]||labels.ru[value]||String(value||"");
}
function syncGamification(value,notify=false){if(!value)return;serverGamification={...(serverGamification||{}),...value};meta.xp=Number(value.xp??meta.xp);meta.streak=Number(value.streak??meta.streak);write(META_KEY,meta);if(notify&&Number(value.awarded_xp||0)>0)toast(`+${Number(value.awarded_xp)} ${tx("xp")}`)}
window.addEventListener("message",event=>{const data=event?.data||{};if(data.type==="hsk_voice_completed"){meta.daily.voice=1;write(META_KEY,meta);syncGamification(data.reward,true);renderAll()}else if(data.type==="hsk_voice_close"){showPage("home")}else if(data.type==="hsk_voice_subscribe"){openSubscription(data.source||"voice_limit")}});
async function loadServerGamification(){if(!bridge.hasAuth?.()||gamificationLoading)return;gamificationLoading=true;try{const result=await bridge.loadGamification?.();if(result?.ok){syncGamification(result);renderAll()}}catch(_){}finally{gamificationLoading=false}}
function featureAllowed(key){const item=ACCESS.course_features?.[key];return ACCESS.status==="active"||item?.allowed!==false}
function lockAction(key,action){return featureAllowed(key)?action:`V2.showPaywall('${key}_locked')`}
function lockSub(key,sub){return featureAllowed(key)?sub:tx("unlockMore")}
function isPaid(){return ACCESS.status==="active"||serverProfile?.subscription?.is_paid}
function energyState(){const energy=serverGamification?.energy||{};return{current:Number(energy.current??3),max:Number(energy.max??5),blocksStudy:energy.blocks_study===true}}
function chestState(){const chest=serverGamification?.reward_chest||{};const progress=Number(chest.progress??(meta.xp%100));return{ready:chest.ready??(meta.xp>0&&progress>=80),progress,nextXp:Number(chest.next_xp??Math.max(0,80-progress))}}
function paidBadge(item){return item?.is_paid?`<em class="v2-paid-badge">${esc(tx("paidBadge"))}</em>`:""}
function currentUserName(){return serverProfile?.user?.name||"Akbarshoh"}
function currentUserAvatar(){const uploaded=read(AVATAR_KEY,"");const raw=serverProfile?.user?.avatar;return uploaded||raw||String(currentUserName()).slice(0,1).toUpperCase()||"A"}
function leagueEntries(){
  const mine=Number(serverGamification?.weekly_xp??serverGamification?.league_points??meta.xp%700);
  const source=Array.isArray(serverGamification?.leaderboard)&&serverGamification.leaderboard.length?serverGamification.leaderboard:[
    {name:"Sun",xp:Math.max(mine+380,760),country:"🇯🇵"},
    {name:"Karen",xp:Math.max(mine+180,520),country:"🇺🇸",is_paid:true},
    {name:"谁陪你",xp:Math.max(mine+80,360),country:"🇺🇸"},
    {name:"david",xp:Math.max(mine+45,220),country:"🇯🇵"},
    {name:"卫会坤",xp:Math.max(mine-20,120),country:"🇺🇸"},
    {name:"manso",xp:Math.max(mine-60,85),country:"🇺🇸"}
  ];
  const rows=source.map(item=>({...item,xp:Number(item.xp??item.league_points??0),league_points:Number(item.league_points??item.xp??0)}));
  const hasMe=rows.some(item=>item.is_current_user);
  if(!hasMe)rows.push({name:currentUserName(),avatar:currentUserAvatar(),xp:mine,league_points:mine,is_current_user:true,country:"🇨🇳"});
  return rows.sort((a,b)=>Number(b.league_points??b.xp)-Number(a.league_points??a.xp)).map((item,index)=>({...item,rank:index+1}));
}
function hskMascot(type="default"){
  return `<div class="v2-hsk-mascot ${type}"><span class="v2-mascot-glow"></span><span class="v2-mascot-face">汉</span><i></i><i></i><i></i></div>`;
}
function streakDays(){
  const count=Math.max(1,Number(meta.streak||1));
  return Array.from({length:7},(_,index)=>index<Math.min(7,count));
}
function leaguePushHtml(reward){
  const gained=Number(reward?.awarded_xp||0);
  const rows=leagueEntries();
  const me=rows.find(item=>item.is_current_user)||rows[0];
  const before=Math.max(0,Number(me.league_points??me.xp??0)-gained);
  const passed=rows.filter(item=>!item.is_current_user&&Number(item.league_points??item.xp??0)<=Number(me.league_points??me.xp??0)&&Number(item.league_points??item.xp??0)>before)[0];
  const nextAhead=rows.find(item=>!item.is_current_user&&Number(item.league_points??item.xp??0)>Number(me.league_points??me.xp??0));
  const msg=passed
    ? tx("leaguePassed").replace("{name}",passed.name||"")
    : tx("leagueNeed").replace("{name}",nextAhead?.name||rows[0]?.name||"").replace("{xp}",String(Math.max(1,Number(nextAhead?.league_points??nextAhead?.xp??0)-Number(me.league_points??me.xp??0)+1)));
  const focus=[nextAhead,me,passed].filter(Boolean).filter((item,index,array)=>array.findIndex(other=>other.name===item.name)===index).slice(0,3);
  return `<section class="v2-reward-step v2-league-push"><div class="v2-mini-cup sapphire">◇</div><h3>${esc(tx("leagueMove"))}</h3><p>${esc(msg)}</p><div class="v2-league-mini">${focus.map(item=>`<div class="${item.is_current_user?"me":""}"><b>${Number(item.rank||0)}</b><span>${esc(item.name||"")}</span><strong>${Number(item.league_points??item.xp??0)} ${esc(tx("xp"))}</strong></div>`).join("")}</div></section>`;
}
function rewardSequenceHtml(result,reward,{title,xp,mistakes,action,actionLabel}){
  const streak=Number(reward?.streak||meta.streak||1);
  const days=streakDays();
  const percent=Number(result.percent||0);
  return `<div class="v2-lesson-shell v2-reward-shell"><section class="v2-reward-step main ${result.book_lesson_completed?"book":result.chapter_completed?"chapter":"section"}">${hskMascot(result.book_lesson_completed?"book":"section")}<div class="v2-kicker">${esc(lessonFlow.section_key||"")}${result.chapter_completed?` · ${esc(result.chapter_label||lessonFlow.chapter_label||"")} ${esc(tx("part"))}`:""}</div><h2>${esc(title)}</h2><div class="v2-reward-grid"><span><b>+${xp}</b><small>${esc(tx("xp"))}</small></span><span><b>${percent}%</b><small>${esc(tx("correct"))}</small></span><span><b>${mistakes}</b><small>${esc(tx("mistakesShort"))}</small></span><span><b>${Math.max(1,Math.ceil((lessonFlow.cards?.length||8)*0.6))}</b><small>${esc(tx("minutes"))}</small></span></div></section><section class="v2-reward-step v2-streak-reward">${hskMascot("streak")}<h3>${esc(tx("streakInRow").replace("{days}",String(streak)))}</h3><p>${esc(mistakes===0?tx("noMistakeTitle"):tx("keepGoing"))}</p><div class="v2-streak-week">${days.map(on=>`<i class="${on?"on":""}">✓</i>`).join("")}</div></section>${leaguePushHtml(reward)}<button class="v2-primary v2-claim-button" onclick="${action}">${esc(actionLabel)} ›</button></div>`;
}
function showPaywall(source="course_locked"){
  closeSheet();
  bridge.reportEvent?.("paywall_seen",{source,level:LEVEL_KEY,status:ACCESS.status});
  const root=document.createElement("div");root.id="v2-sheet";root.className="v2-sheet-backdrop";
  root.innerHTML=`<div class="v2-sheet v2-paywall-sheet" onclick="event.stopPropagation()"><div class="v2-sheet-handle"></div><div class="v2-result-mark">◆</div><h2>${esc(tx("freeLessonTitle"))}</h2><p>${esc(tx("freeLessonText"))}</p><button class="v2-primary" onclick="V2.openSubscription('${source}')">${esc(tx("subscribeAction"))}</button><button class="v2-secondary" onclick="document.getElementById('v2-sheet')?.remove()">${esc(tx("back"))}</button></div>`;
  root.onclick=()=>root.remove();document.body.appendChild(root);
}
async function loadServerProfile(){if(!bridge.hasAuth?.()||profileLoading)return;profileLoading=true;try{const result=await bridge.loadProfile?.();if(result?.ok){serverProfile=result;ACCESS={...ACCESS,course_features:result.course_features||ACCESS.course_features,gamification:result.gamification||ACCESS.gamification};syncGamification(result.gamification);renderProfile();renderTests();renderTraining()}}catch(_){}finally{profileLoading=false}}
function missionDone(name,target){return Number(meta.daily?.[name]||0)>=target}
function missionRow(icon,title,current,target){const done=current>=target;return `<div class="v2-mission"><div class="v2-mission-icon">${icon}</div><div><b>${esc(title)}</b><small>${Math.min(current,target)} / ${target}</small></div><span class="v2-check ${done?"":"pending"}">${done?"✓":"○"}</span></div>`}

function renderHome(){
  const lesson=currentLesson();
  const goal=Math.max(5,Number(meta.minutes||10));
  const dailyProgress=Math.min(100,Math.round(Number(meta.daily.xp||0)/(goal*2)*100));
  const chest=chestState();
  const energy=energyState();
  document.getElementById("page-home").innerHTML=`
    <div class="v2-page-head"><div class="v2-kicker">${esc(tx("today"))}</div><h1 class="v2-title">${esc(tx("welcome"))}</h1></div>
    <section class="v2-hero"><div class="v2-hero-row"><div><div class="v2-kicker">${labelLevel(LEVEL_KEY)} · ${esc(tx("lesson"))} ${lesson?.n||1}</div><h1>${esc(tr(lesson?.t)||"")}</h1><p>${esc(tr(lesson?.sub)||"")}</p></div><div class="v2-progress-ring" style="--progress:${progress()}%" data-value="${progress()}%"></div></div><button class="v2-primary" onclick="V2.openLesson(${lesson?.n||1})">▶ ${esc(tx("continue"))}</button></section>
    <section class="v2-section"><div class="v2-action-grid"><button class="v2-feature wide" onclick="V2.showPage('tests')"><span class="v2-feature-icon">✓</span><b>${esc(tx("testCenter"))}</b><small>${esc(tx("testCenterSub"))}</small></button><button class="v2-feature" onclick="V2.showPage('training')"><span class="v2-feature-icon">◫</span><b>${esc(tx("training"))}</b><small>${esc(tx("trainingSub"))}</small></button><button class="v2-feature" onclick="V2.showPage('mistakes')"><span class="v2-feature-icon">!</span><b>${esc(tx("mistakes"))}</b><small>${esc(tx("mistakesSub"))}</small></button></div></section>
    <section class="v2-section"><div class="v2-section-head"><h2 class="v2-section-title">${esc(tx("dailyGoal"))}</h2><span class="v2-link">${goal} ${esc(tx("minutes"))}</span></div><div class="v2-goal"><div class="v2-goal-top"><b>${meta.daily.xp||0} ${esc(tx("xp"))}</b><span>${dailyProgress}%</span></div><div class="v2-bar"><i style="width:${dailyProgress}%"></i></div></div></section>
    <section class="v2-section"><div class="v2-section-head"><h2 class="v2-section-title">${esc(tx("missions"))}</h2></div><div class="v2-missions">${missionRow("▦",tx("lessonMission"),meta.daily.lesson||0,1)}${missionRow("字",tx("wordMission"),meta.daily.words||0,5)}${missionRow("◌",tx("voiceMission"),meta.daily.voice||0,1)}</div></section>
    <section class="v2-section"><div class="v2-section-head"><h2 class="v2-section-title">${esc(tx("yourProgress"))}</h2></div><div class="v2-metrics"><div class="v2-metric" data-tone="gold"><strong>${meta.xp}</strong><span>${tx("xp")}</span></div><div class="v2-metric" data-tone="green"><strong>${meta.streak}</strong><span>${tx("streak")}</span></div><div class="v2-metric" data-tone="purple"><strong>${xpLevel()}</strong><span>${esc(tx("levelMetric"))}</span></div></div></section>
    <section class="v2-section"><button class="v2-feature wide" onclick="V2.openChest()"><span class="v2-feature-icon">▣</span><b>${esc(chest.ready?tx("rewardReady"):tx("rewardChest"))}</b><small>${esc(chest.ready?tx("openChest"):`${chest.progress}/80 ${tx("xp")}`)}</small></button><div class="v2-energy-strip"><b>${esc(tx("energy"))}: ${energy.current}/${energy.max}</b><span>${esc(tx("energySub"))}</span></div></section>`;
}

function sectionCurrent(section){const current=currentSection();return current&&current.key===section.key}
function sectionLocked(section){return !sectionIsDone(section)&&!sectionCurrent(section)}
function pathItem(section,index){
  const lesson=lessonByNumber(section.lesson),done=sectionIsDone(section),current=sectionCurrent(section),locked=sectionLocked(section);
  const premiumLocked=!done&&!featureAllowed("lesson")&&!(ACCESS.status==="active");
  const cls=done?"done":current&&!premiumLocked?"current":premiumLocked?"premium":"";
  const status=done?tx("done"):premiumLocked?tx("unlockMore"):current?tx("current"):tx("locked");
  return `<div class="v2-path-item"><div class="v2-node-copy"><b>${esc(tx("lesson"))} ${section.key}</b><small>${esc(tr(lesson?.t)||"")} · ${esc(status)}</small></div><button class="v2-node ${cls}" onclick="V2.openLesson(${section.lesson},'${section.key}')" aria-label="${esc(tx("lesson"))} ${section.key}">${done?"✓":premiumLocked?"◆":section.no}</button></div>`;
}
function milestoneItem(after,type){const boss=type==="boss";return `<div class="v2-path-item"><div class="v2-node-copy"><b>${esc(tx(type))}</b><small>${esc(tx("lesson"))} 1-${after}</small></div><button class="v2-node ${boss?"boss":"review"}" onclick="V2.startMock()" aria-label="${esc(tx(type))}">${boss?"★":"↻"}</button></div>`}
function renderCourse(){
  const nodes=[];
  LESSONS.forEach((lesson)=>{
    const sections=lessonSections(lesson);
    nodes.push(`<div class="v2-path-book"><b>${labelLevel(LEVEL_KEY).replace(" 上","").replace(" 下","")} ${esc(tx("lesson"))} ${lesson.n}</b><small>${esc(tr(lesson.t)||"")}</small></div>`);
    const groups={};
    sections.forEach(section=>{if(!groups[section.chapter])groups[section.chapter]=[];groups[section.chapter].push(section)});
    Object.entries(groups).forEach(([chapter,items])=>{
      const done=items.filter(sectionIsDone).length;
      nodes.push(`<div class="v2-path-chapter"><span>${chapter} ${esc(tx("part"))}</span><b>${done}/${items.length}</b></div>`);
      items.forEach((section)=>nodes.push(pathItem(section,nodes.length)));
    });
    if(lessonIsDone(lesson.n)){
      if(lesson.n%5===0)nodes.push(milestoneItem(lesson.n,"boss"));else if(lesson.n%3===0)nodes.push(milestoneItem(lesson.n,"review"));
    }
  });
  document.getElementById("page-course").innerHTML=`<div class="v2-page-head"><div class="v2-kicker">${labelLevel(LEVEL_KEY)}</div><h1 class="v2-title">${esc(tx("path"))}</h1><p class="v2-subtitle">${esc(tx("pathSub"))}</p></div><div class="v2-path-summary"><div><b>${completedCount()}/${LESSONS.length} ${esc(tx("completed"))}</b><div class="v2-bar"><i style="width:${progress()}%"></i></div></div><span>${progress()}%</span></div><button class="v2-course-jump" onclick="V2.jumpToCurrentSection()">⌖ ${esc(tx("current"))}</button><div class="v2-path">${nodes.join("")}</div>`;
}

function renderTests(){
  const cards=[
    `<button class="v2-row-card" onclick="${lockAction("placement","V2.startPlacement()")}"><span class="v2-row-icon">◎</span><span><b>${esc(tx("placement"))}</b><small>${esc(lockSub("placement",tx("placementSub")))}</small></span><span class="v2-arrow">›</span></button>`,
    `<div class="v2-test-group"><div class="v2-kicker">${esc(tx("hskExams"))}</div>${["hsk1","hsk2","hsk3","hsk4a"].map(level=>`<button class="v2-row-card" onclick="${lockAction("training_test",`V2.startMock('${level}')`)}"><span class="v2-row-icon">${level.replace(/[^0-9]/g,"")}</span><span><b>${labelLevel(level)} · ${esc(tx("mock"))}</b><small>${esc(lockSub("training_test",tx("mockSub")))}</small></span><span class="v2-arrow">›</span></button>`).join("")}</div>`,
    `<button class="v2-row-card" onclick="${lockAction("training_test","V2.startTraining('pronunciation')")}"><span class="v2-row-icon">声</span><span><b>${esc(tx("pronunciationTest"))}</b><small>${esc(lockSub("training_test",tx("speaking")))}</small></span><span class="v2-arrow">›</span></button>`,
    `<button class="v2-row-card" onclick="${lockAction("training_test","V2.startTraining('characters')")}"><span class="v2-row-icon">字</span><span><b>${esc(tx("characterTest"))}</b><small>${esc(lockSub("training_test",tx("characters")))}</small></span><span class="v2-arrow">›</span></button>`,
    `<button class="v2-row-card" onclick="${lockAction("training_test","V2.startTraining('pinyin')")}"><span class="v2-row-icon">拼</span><span><b>${esc(tx("pinyinTest"))}</b><small>${esc(lockSub("training_test",tx("pinyinTest")))}</small></span><span class="v2-arrow">›</span></button>`
  ];
  document.getElementById("page-tests").innerHTML=`<div class="v2-page-head"><button class="v2-back" onclick="V2.showPage('home')" aria-label="${esc(tx("back"))}">‹</button><div class="v2-kicker">HSK AI</div><h1 class="v2-title">${esc(tx("testCenter"))}</h1><p class="v2-subtitle">${esc(tx("testsSub"))}</p></div><div class="v2-test-list">${cards.join("")}</div>`;
}

function row(icon,title,sub,action){return `<button class="v2-row-card" onclick="${action}"><span class="v2-row-icon">${icon}</span><span><b>${esc(title)}</b><small>${esc(sub)}</small></span><span class="v2-arrow">›</span></button>`}
function renderProfile(){
  const stats=serverProfile?.stats||{};const user=serverProfile?.user||{};
  const mistakeCount=stats.mistakes??serverMistakes?.summary?.total??read(MISTAKES_KEY,[]).reduce((s,m)=>s+m.count,0);
  const doneCount=stats.completed_lessons??completedCount();const name=user.name||"HSK AI";const avatar=currentUserAvatar();
  const days=Array.from({length:7},(_,index)=>index<Math.min(7,Number(meta.streak||0)));
  document.getElementById("page-profile").innerHTML=`<div class="v2-profile-head"><button class="v2-avatar upload" onclick="document.getElementById('v2-avatar-input')?.click()" aria-label="${esc(tx("uploadAvatar"))}">${avatarMarkup(avatar,String(name).slice(0,1)||"A")}</button><input id="v2-avatar-input" type="file" accept="image/*" hidden onchange="V2.uploadAvatar(event)"><div><h1>${esc(name)}</h1><p>${meta.xp} ${esc(tx("xp"))} · ${meta.streak} ${esc(tx("streak"))}</p><span class="v2-badge">${leagueLabel()} ${isPaid()?`· ${esc(tx("paidBadge"))}`:""}</span></div></div><div class="v2-metrics v2-section"><div class="v2-metric" data-tone="gold"><strong>${meta.xp}</strong><span>${esc(tx("xp"))}</span></div><div class="v2-metric" data-tone="green"><strong>${doneCount}</strong><span>${esc(tx("done"))}</span></div><div class="v2-metric" data-tone="purple"><strong>${mistakeCount}</strong><span>${esc(tx("mistakes"))}</span></div></div><section class="v2-section"><div class="v2-streak-card"><div><b>${esc(tx("streakCalendar"))}</b><small>${esc(tx("milestones"))} · ${esc(tx("streakFreeze"))}</small></div><div class="v2-calendar">${days.map(on=>`<i class="${on?"on":""}"></i>`).join("")}</div></div></section><div class="v2-profile-list">${row("◫",tx("training"),tx("trainingSub"),"V2.showPage('training')")}${row("!",tx("mistakes"),tx("mistakesSub"),"V2.showPage('mistakes')")}${row("★",tx("achievements"),`${doneCount} / ${LESSONS.length}`,"V2.showPage('achievements')")}${row("?",tx("support"),tx("supportSub"),"V2.openSupport('profile_support')")}</div>`;
}

function renderTraining(){
  document.getElementById("page-training").innerHTML=`<div class="v2-page-head"><button class="v2-back" onclick="V2.showPage('profile')" aria-label="${esc(tx("back"))}">‹</button><div class="v2-kicker">${labelLevel(LEVEL_KEY)}</div><h1 class="v2-title">${esc(tx("training"))}</h1><p class="v2-subtitle">${esc(tx("trainingSub"))}</p></div><div class="v2-profile-list">${row("◖",tx("listening"),lockSub("training_test",tx("words")),lockAction("training_test","V2.startTraining('listening')"))}${row("声",tx("pronunciationTest"),lockSub("training_test",tx("speaking")),lockAction("training_test","V2.startTraining('pronunciation')"))}${row("✎",tx("writing"),lockSub("training_test",tx("grammar")),lockAction("training_test","V2.startTraining('writing')"))}${row("字",tx("characters"),lockSub("training_test",tx("characterTest")),lockAction("training_test","V2.startTraining('characters')"))}${row("拼",tx("pinyinTest"),lockSub("training_test",tx("pinyinTest")),lockAction("training_test","V2.startTraining('pinyin')"))}${row("◌",tx("speaking"),lockSub("voice",tx("voice")),lockAction("voice","V2.showPage('voice')"))}${row("!",tx("mistakes"),lockSub("training_test",tx("mistakesSub")),"V2.showPage('mistakes')")}</div>`;
}

function renderMistakes(){
  const localItems=read(MISTAKES_KEY,[]).sort((a,b)=>b.count-a.count).map(item=>({...item,correct_answer:item.correct}));
  const items=serverMistakes?.items||localItems;
  const loading=mistakesLoading&&!serverMistakes;
  const content=loading?`<div class="v2-empty">${esc(tx("loadingMistakes"))}</div>`:items.length?`<div class="v2-section"><button class="v2-primary v2-review-button" onclick="${lockAction("training_test","V2.startMistakeReview()")}">↻ ${esc(featureAllowed("training_test")?tx("reviewNow"):tx("subscription"))}</button>${items.map(item=>`<div class="v2-mistake"><div><b>${esc(item.question)}</b><p>${esc(item.correct_answer||"")}</p><small>${esc(item.category||item.source||"")}</small></div><span class="v2-count">${item.count} ${esc(tx("mistakesCount"))}</span></div>`).join("")}</div>`:`<div class="v2-empty">${esc(tx("noMistakes"))}</div>`;
  document.getElementById("page-mistakes").innerHTML=`<div class="v2-page-head"><button class="v2-back" onclick="V2.showPage('training')" aria-label="${esc(tx("back"))}">‹</button><div class="v2-kicker">HSK AI</div><h1 class="v2-title">${esc(tx("mistakes"))}</h1><p class="v2-subtitle">${esc(tx("mistakesSub"))}</p></div>${content}`;
}
async function loadServerMistakes(){
  if(!bridge.hasAuth?.()||mistakesLoading)return;
  mistakesLoading=true;renderMistakes();
  try{serverMistakes=await bridge.loadMistakes?.();renderProfile()}catch(_){serverMistakes=null}finally{mistakesLoading=false;renderMistakes()}
}
function renderLeague(){
  const rows=leagueEntries();
  const mine=rows.find(item=>item.is_current_user)||rows[0];
  const cupNames=["Bronze","Silver","Gold","Diamond","Sapphire","Legend"];
  const currentLeague=leagueName();
  const currentIndex=Math.max(0,cupNames.indexOf(currentLeague));
  const podiumNames=[
    cupNames[currentIndex>0?currentIndex-1:Math.min(1,cupNames.length-1)],
    currentLeague,
    cupNames[currentIndex<cupNames.length-1?currentIndex+1:Math.max(0,currentIndex-1)]
  ];
  const cupIcon=name=>name==="Diamond"?"◆":name==="Sapphire"?"◇":name==="Legend"?"★":"♜";
  const medals=["🥇","🥈","🥉"];
  document.getElementById("page-league").innerHTML=`<div class="v2-page-head"><div class="v2-kicker">${leagueLabel(currentLeague)} · ${esc(tx("weeklyReset"))}</div><h1 class="v2-title">${esc(tx("league"))}</h1><p class="v2-subtitle">${esc(tx("leagueSize"))} · ${Number(mine?.league_points??mine?.xp??0)} ${esc(tx("leaguePoints"))}</p></div><div class="v2-cup-podium">${podiumNames.map((name,index)=>`<div class="v2-cup-stage ${index===1?"large":index===0?"medium":"small"} ${name===currentLeague?"active":""}"><span>${cupIcon(name)}</span><small>${esc(leagueLabel(name))}</small></div>`).join("")}</div><div class="v2-league-list">${rows.map((item,index)=>{const rank=Number(item.rank||1);const points=Number(item.league_points??item.xp??0);return `<button class="v2-league-row ${item.is_current_user?"current":""} ${rank<=3?"top":""}" onclick="V2.openLeagueUser(${index})"><div class="v2-rank-medal">${rank<=3?medals[rank-1]:rank}</div><div class="v2-league-avatar">${avatarMarkup(item.avatar,String(item.name||"?").slice(0,1))}</div><div class="v2-league-user"><b>${esc(item.name||"")} ${paidBadge(item)}</b><small>${item.country?`${esc(item.country)} · `:""}${rank<=3?esc(tx("reward")):leagueLabel(currentLeague)}</small></div><strong>${points} ${esc(tx("xp"))}</strong></button>`}).join("")}</div>`;
}
function openLeagueUser(index){
  const item=leagueEntries()[Number(index)];
  if(!item)return;
  document.getElementById("v2-sheet")?.remove();
  const points=Number(item.league_points??item.xp??0);
  const root=document.createElement("div");root.id="v2-sheet";root.className="v2-sheet-backdrop";
  root.innerHTML=`<div class="v2-sheet v2-user-sheet" onclick="event.stopPropagation()"><div class="v2-sheet-handle"></div><div class="v2-league-avatar large">${avatarMarkup(item.avatar,String(item.name||"?").slice(0,1))}</div><h2>${esc(item.name||tx("userProfile"))}</h2><p>${esc(tx("league"))}: ${esc(leagueLabel())} · ${Number(item.rank||0)} · ${points} ${esc(tx("xp"))}</p><div class="v2-sheet-actions single"><button class="v2-primary" onclick="document.getElementById('v2-sheet')?.remove()">${esc(tx("back"))}</button></div></div>`;
  root.onclick=()=>root.remove();document.body.appendChild(root);
}
function renderAchievements(){
  const data=[["▦",tx("lessonMission"),completedCount(),1],["✦",`100 ${tx("xp")}`,meta.xp,100],["◆",`7 ${tx("streak")}`,meta.streak,7],["字",tx("wordMission"),meta.daily.words||0,5]];
  document.getElementById("page-achievements").innerHTML=`<div class="v2-page-head"><button class="v2-back" onclick="V2.showPage('profile')" aria-label="${esc(tx("back"))}">‹</button><div class="v2-kicker">HSK AI</div><h1 class="v2-title">${esc(tx("achievements"))}</h1></div><div class="v2-profile-list">${data.map(item=>`<div class="v2-row-card"><span class="v2-row-icon">${item[0]}</span><span><b>${esc(item[1])}</b><small>${Math.min(item[2],item[3])} / ${item[3]}</small></span><span class="v2-check ${item[2]>=item[3]?"":"pending"}">${item[2]>=item[3]?"✓":"○"}</span></div>`).join("")}</div>`;
}

function renderAll(){
  document.getElementById("v2-xp").textContent=meta.xp;
  document.getElementById("v2-streak").textContent=meta.streak;
  renderHome();renderCourse();renderTests();renderProfile();renderTraining();renderMistakes();renderLeague();renderAchievements();
}

function showPage(next){
  document.querySelector(".v2-app")?.classList.toggle("voice-focus",next==="voice");
  document.querySelectorAll(".v2-page,.page").forEach(el=>el.classList.toggle("active",el.id===`page-${next}`));
  const root=next==="tests"||next==="quiz"&&["placement","mock"].includes(testMode)?"home":["training","mistakes","achievements"].includes(next)||next==="quiz"&&["training","mistakes"].includes(testMode)?"profile":["flashcards","grammar","quiz","lesson"].includes(next)?"course":next;
  document.querySelectorAll(".v2-nav button").forEach(el=>el.classList.toggle("active",el.dataset.page===root));
  if(next==="flashcards")renderFlashcards();
  if(next==="grammar")renderGrammar();
  if(next==="quiz")renderQuizFilters();
  if(next==="mistakes")loadServerMistakes();
  if(next==="profile")loadServerProfile();
  if(["home","profile","league"].includes(next))loadServerGamification();
  if(next==="voice"){renderVoiceFrame();renderHome()}
  document.getElementById(`page-${next}`)?.scrollTo(0,0);
  bridge.reportEvent?.("v2_screen_opened",{screen:next,level:LEVEL_KEY});
}
function quizBack(){showPage(testMode==="mistakes"?"mistakes":testMode==="training"?"training":"tests")}

function openLesson(number,sectionKey=""){
  const lesson=LESSONS.find(item=>item.n===Number(number));if(!lesson)return;
  const section=lessonSections(lesson).find(item=>item.key===sectionKey)||lessonSections(lesson).find(item=>!sectionIsDone(item))||lessonSections(lesson)[0];
  if(ACCESS.status!=="active"&&meta.trialCourseCompleted&&!sectionIsDone(section)){showPaywall("course_trial_completed");return}
  if(!sectionIsDone(section)&&!featureAllowed("lesson")){showPaywall("lesson_locked");return}
  if(!sectionIsDone(section)&&section.key!==currentSection()?.key){toast(tx("locked"));return}
  document.getElementById("v2-sheet")?.remove();
  const root=document.createElement("div");root.id="v2-sheet";root.className="v2-sheet-backdrop";
  root.innerHTML=`<div class="v2-sheet" onclick="event.stopPropagation()"><div class="v2-sheet-handle"></div><div class="v2-kicker">${labelLevel(LEVEL_KEY)} · ${esc(tx("lesson"))} ${section.key} · ${section.chapter} ${esc(tx("part"))}</div><h2>${esc(tr(lesson.t))}</h2><p>${esc(tr(lesson.sub))}</p><div class="v2-sheet-actions single"><button class="v2-primary" onclick="V2.startLesson(${lesson.n},'${section.key}')">▶ ${esc(tx("start"))}</button></div></div>`;
  root.onclick=()=>root.remove();document.body.appendChild(root);
}
function closeSheet(){document.getElementById("v2-sheet")?.remove()}
function renderLessonLoading(){const root=document.getElementById("page-lesson");root.innerHTML=`<div class="v2-lesson-shell"><div class="v2-lesson-top"><button class="v2-back" onclick="V2.showPage('course')" aria-label="${esc(tx("back"))}">‹</button><div class="v2-lesson-progress"><i></i></div><span></span></div><div class="v2-lesson-card v2-lesson-loading"><div class="v2-loader-dot"></div><h2>${esc(tx("loadingLesson"))}</h2></div></div>`}
function lessonError(error){const code=String(error?.code||"");const locked=code==="free_feature_limit_reached";document.getElementById("page-lesson").innerHTML=`<div class="v2-lesson-shell"><div class="v2-lesson-top"><button class="v2-back" onclick="V2.showPage('course')" aria-label="${esc(tx("back"))}">‹</button><div></div><span></span></div><div class="v2-lesson-card v2-lesson-result"><div class="v2-result-mark">${locked?"◆":"!"}</div><h2>${esc(locked?tx("freeLessonTitle"):tx("lessonLoadError"))}</h2><p>${esc(locked?tx("freeLessonText"):code||tx("onboardingError"))}</p><button class="v2-primary" onclick="${locked?"V2.showPaywall('lesson_server_locked')":"V2.showPage('course')"}">${esc(locked?tx("subscribeAction"):tx("back"))}</button></div></div>`}
async function startLesson(number,sectionKey=""){
  closeSheet();quizLesson=Number(number);testMode="lesson";lessonFlow=null;lessonCardIndex=0;lessonResponses={};lessonSubmitting=false;showPage("lesson");renderLessonLoading();
  try{
    const result=await bridge.loadCourseLesson?.({level:LEVEL_KEY,lesson:quizLesson,section:sectionKey,lang,completed_sections:completedLessonSectionKeys(lessonByNumber(quizLesson))});
    if(!result?.flow)throw Object.assign(new Error("course_lesson_failed"),{code:"course_lesson_failed"});
    lessonFlow=result.flow;renderLessonCard();
  }catch(error){
    if(!bridge.hasAuth?.()){showPage("quiz");startQuiz();return}
    lessonError(error);
  }
}
function lessonProgress(){return lessonFlow?.cards?.length?Math.round((lessonCardIndex/lessonFlow.cards.length)*100):0}
function lessonFeedback(card,response){
  if(!response)return"";
  let correct=true;
  if(["meaning_guess","listening_choice","translation_choice","quick_quiz","dialog_context"].includes(card.type))correct=Number(response.selected_index)===Number(card.correct_index);
  if(["sentence_builder","word_order"].includes(card.type))correct=JSON.stringify(response.answer_tokens||[])===JSON.stringify(card.answer_tokens||[]);
  return `<div class="v2-answer-feedback ${correct?"correct":"incorrect"}"><b>${esc(tx(correct?"correct":"incorrect"))}</b>${card.explanation?`<p>${esc(card.explanation)}</p>`:""}</div>`;
}
function renderLessonCard(){
  const card=lessonFlow?.cards?.[lessonCardIndex],root=document.getElementById("page-lesson");if(!card){submitLessonFlow();return}
  const response=lessonResponses[card.id];
  if(["sentence_builder","word_order"].includes(card.type)&&!response&&lessonOrderRemaining.length+lessonOrderSelected.length===0){lessonOrderRemaining=[...(card.tokens||[])];lessonOrderSelected=[]}
  let body="";
  if(card.type==="active_word")body=`<div class="v2-word-hero">${esc(card.word.zh)}</div><div class="v2-word-pinyin">${esc(card.word.pinyin)}</div><div class="v2-word-meaning">${esc(card.word.meaning)}</div><button class="v2-audio-action" onclick="V2.playCurrentLessonAudio('word')">🔊</button>`;
  else if(card.type==="listening_choice")body=`<button class="v2-sound-tile" onclick="V2.playCurrentLessonAudio('audio')"><strong>${esc(card.audio_text||"声")}</strong><span>🔊</span></button>${card.sentence?`<div class="v2-card-sentence">${esc(card.sentence)}</div>`:""}<div class="v2-choice-grid">${card.options.map((option,index)=>`<button class="v2-card-choice ${response&&Number(response.selected_index)===index?"selected":""}" ${response?"disabled":""} onclick="V2.answerLessonChoice(${index})">${esc(option)}</button>`).join("")}</div>${lessonFeedback(card,response)}`;
  else if(["meaning_guess","translation_choice","quick_quiz"].includes(card.type))body=`${card.sentence?`<div class="v2-card-sentence">${esc(card.sentence)}</div>`:""}<div class="v2-choice-grid">${card.options.map((option,index)=>`<button class="v2-card-choice ${response&&Number(response.selected_index)===index?"selected":""}" ${response?"disabled":""} onclick="V2.answerLessonChoice(${index})">${esc(option)}</button>`).join("")}</div>${lessonFeedback(card,response)}`;
  else if(card.type==="dialog_context")body=`<div class="v2-dialog-card">${(card.dialog||[]).map(line=>`<p><b>${esc(line.speaker||"")}</b><span>${esc(line.text||"")}</span></p>`).join("")}</div><div class="v2-choice-grid">${card.options.map((option,index)=>`<button class="v2-card-choice ${response&&Number(response.selected_index)===index?"selected":""}" ${response?"disabled":""} onclick="V2.answerLessonChoice(${index})">${esc(option)}</button>`).join("")}</div>${lessonFeedback(card,response)}`;
  else if(["sentence_builder","word_order"].includes(card.type))body=`${card.sentence?`<div class="v2-card-sentence">${esc(card.sentence)}</div>`:""}<div class="v2-order-answer">${lessonOrderSelected.map((token,index)=>`<button onclick="V2.returnLessonToken(${index})">${esc(token)}</button>`).join("")||"<span>…</span>"}</div><div class="v2-token-bank">${lessonOrderRemaining.map((token,index)=>`<button onclick="V2.pickLessonToken(${index})">${esc(token)}</button>`).join("")}</div>${lessonFeedback(card,response)}${response?"":`<div class="v2-inline-actions"><button class="v2-secondary" onclick="V2.resetLessonOrder()">${esc(tx("reset"))}</button><button class="v2-primary" ${lessonOrderRemaining.length?"disabled":""} onclick="V2.checkLessonOrder()">${esc(tx("check"))}</button></div>`}`;
  else if(card.type==="character_trace")body=`<button class="v2-trace-stage ${response?"done":""}" onclick="V2.completePassiveLessonCard()"><i></i><strong>${esc(card.character||card.word||"汉")}</strong><span>↘</span></button><div class="v2-trace-meta"><b>${esc(card.word||"")}</b><small>${esc(card.pinyin||"")} · ${esc(card.translation||"")}</small></div><p class="v2-pronunciation-hint">${esc(response?tx("traceDone"):tx("traceHint"))}</p>`;
  else if(card.type==="pronunciation")body=`<div class="v2-speech-card"><strong>${esc(card.translation||card.phrase)}</strong><small>${esc(card.phrase)} · ${esc(card.pinyin)}</small><div><button class="v2-mic-button" onclick="V2.completePassiveLessonCard()">🎙</button><button class="v2-audio-action compact" onclick="V2.playCurrentLessonAudio('phrase')">↻</button></div></div><p class="v2-pronunciation-hint">${esc(tx("micReady"))}</p>`;
  const canContinue=["active_word","pronunciation","character_trace"].includes(card.type)||Boolean(response);
  root.innerHTML=`<div class="v2-lesson-shell"><div class="v2-lesson-top"><button class="v2-back" onclick="V2.showPage('course')" aria-label="${esc(tx("back"))}">‹</button><div class="v2-lesson-progress"><i style="width:${lessonProgress()}%"></i></div><span>${lessonCardIndex+1}/${lessonFlow.cards.length}</span></div><article class="v2-lesson-card"><div class="v2-lesson-unit"><span>${esc(card.unit||card.title||tx("lesson"))}</span><b>${esc(card.title||"")}</b></div><h2>${esc(card.prompt||card.title||"")}</h2>${body}${canContinue?`<button class="v2-primary v2-card-next" onclick="V2.continueLessonCard()">${esc(card.type==="pronunciation"?tx("said"):card.type==="character_trace"?tx("traceDone"):lessonCardIndex===lessonFlow.cards.length-1?tx("submitLesson"):tx("next"))} ›</button>`:""}</article></div>`;
  bridge.reportEvent?.("card_seen",{event_id:`${lessonFlow.id}:${card.id}`,lesson_id:lessonFlow.lesson_id,card_id:card.id,card_type:card.type});
}
function playLessonAudio(text){try{speechSynthesis.cancel();const item=new SpeechSynthesisUtterance(text);item.lang="zh-CN";item.rate=.82;speechSynthesis.speak(item)}catch(_){}}
function playCurrentLessonAudio(kind){const card=lessonFlow?.cards?.[lessonCardIndex]||{};const text=kind==="word"?card.word?.zh:kind==="phrase"?card.phrase:card.audio_text;playLessonAudio(String(text||""))}
function answerLessonChoice(index){const card=lessonFlow.cards[lessonCardIndex];lessonResponses[card.id]={card_id:card.id,selected_index:Number(index)};renderLessonCard()}
function pickLessonToken(index){lessonOrderSelected.push(lessonOrderRemaining.splice(index,1)[0]);renderLessonCard()}
function returnLessonToken(index){lessonOrderRemaining.push(lessonOrderSelected.splice(index,1)[0]);renderLessonCard()}
function resetLessonOrder(){const card=lessonFlow.cards[lessonCardIndex];lessonOrderRemaining=[...(card.tokens||[])];lessonOrderSelected=[];renderLessonCard()}
function checkLessonOrder(){const card=lessonFlow.cards[lessonCardIndex];if(lessonOrderRemaining.length)return;lessonResponses[card.id]={card_id:card.id,answer_tokens:[...lessonOrderSelected]};renderLessonCard()}
function completePassiveLessonCard(){const card=lessonFlow.cards[lessonCardIndex];lessonResponses[card.id]={card_id:card.id,completed:true};renderLessonCard()}
function continueLessonCard(){const card=lessonFlow.cards[lessonCardIndex];if(["active_word","pronunciation","character_trace"].includes(card.type))lessonResponses[card.id]={card_id:card.id,completed:true};lessonCardIndex+=1;lessonOrderRemaining=[];lessonOrderSelected=[];renderLessonCard()}
async function submitLessonFlow(){
  if(lessonSubmitting)return;lessonSubmitting=true;renderLessonLoading();
  try{
    const result=await bridge.completeCourseLesson?.({level:lessonFlow.level,lesson_id:lessonFlow.lesson_id,section_key:lessonFlow.section_key,lang,responses:Object.values(lessonResponses),client_completed_sections:completedLessonSectionKeys(lessonByNumber(lessonFlow.lesson_id))});
    if(!result?.ok)throw Object.assign(new Error(result?.error||"course_lesson_complete_failed"),{code:result?.error,result});
    serverMistakes=null;
    markSectionDone(result.section_key||lessonFlow.section_key);
    if(result.book_lesson_completed&&!state.done.includes(lessonFlow.lesson_id)){state.done.push(lessonFlow.lesson_id);saveState()}
    if(ACCESS.status!=="active"){meta.trialCourseCompleted=true;write(META_KEY,meta)}
    syncGamification(result.reward,true);renderAll();
    const paid=ACCESS.status==="active",next=result.next_lesson,nextSection=result.next_section;
    const mistakes=Math.max(0,Number(result.total||0)-Number(result.correct||0));
    const reward=result.book_lesson_reward||result.chapter_reward||result.section_reward||result.reward||{};
    const xp=Number(reward.awarded_xp||0);
    const title=result.book_lesson_completed
      ? tx("bookLessonComplete").replace("{level}",labelLevel(lessonFlow.level)).replace("{lesson}",String(lessonFlow.lesson_id))
      : result.chapter_completed
        ? tx("chapterComplete").replace("{chapter}",result.chapter_label||lessonFlow.chapter_label||"A")
        : tx("sectionComplete");
    const action=result.book_lesson_completed
      ? (next&&paid?`V2.openNextLesson(${Number(next)})`:"V2.showPage('course')")
      : (nextSection?(featureAllowed("lesson")?`V2.openNextSection('${nextSection}')`:"V2.showPaywall('section_completed')"):"V2.showPage('course')");
    const actionLabel=result.book_lesson_completed
      ? (next&&paid?tx("continueCourse"):tx("course"))
      : (nextSection&&!featureAllowed("lesson")?tx("unlockMore"):result.chapter_completed?tx("nextChapter"):tx("nextSection"));
    document.getElementById("page-lesson").innerHTML=rewardSequenceHtml(result,reward,{title,xp,mistakes,action,actionLabel});
  }catch(error){
    lessonSubmitting=false;const result=error?.result||{};if(result.wrong_items?.length)serverMistakes=null;
    document.getElementById("page-lesson").innerHTML=`<div class="v2-lesson-shell"><div class="v2-lesson-card v2-lesson-result"><div class="v2-result-mark">↻</div><h2>${esc(error?.code==="lesson_score_too_low"?tx("incorrect"):tx("lessonLoadError"))}</h2><p>${result.percent!==undefined?`${result.percent}% · ${result.correct||0}/${result.total||0}`:esc(error?.code||"")}</p><button class="v2-primary" onclick="V2.retryLessonFlow()">${esc(tx("retryLesson"))}</button></div></div>`;
  }
}
function retryLessonFlow(){lessonCardIndex=0;lessonResponses={};lessonOrderRemaining=[];lessonOrderSelected=[];lessonSubmitting=false;renderLessonCard()}
function openNextLesson(number){bridge.openRoute?.({level:LEVEL_KEY,lang,tab:"course",lesson:number})}
function openNextSection(sectionKey){const lesson=Number(String(sectionKey||"").split(".")[0]||quizLesson||1);openLesson(lesson,sectionKey)}
function openWords(listen=false,lesson){closeSheet();fcFilter=lesson?Number(lesson):"all";showPage("flashcards");if(listen)toast(tx("listening"))}
function openGrammar(lesson){closeSheet();grammarFilter=lesson?Number(lesson):"all";showPage("grammar")}

function buildExamQuestions(count){
  const pool=[];
  const step=Math.max(1,Math.floor(VOCAB.length/Math.max(count,1)));
  for(let index=0;index<VOCAB.length&&pool.length<count;index+=step){const word=VOCAB[index];pool.push(vocabQuestion(word,["meaning","hanzi","pinyin"][pool.length%3]))}
  for(const lesson of LESSONS){if(pool.length>=count)break;const question=grammarQuestion(lesson.n);if(question)pool.push(question)}
  return pool.slice(0,count);
}
async function beginCustomTest(mode,requestedLevel=LEVEL_KEY,skill=""){
  testMode=mode;quizLesson=currentLesson()?.n||1;practiceSession=null;showPage("quiz");document.getElementById("score-box").style.display="none";const box=document.getElementById("quiz-box");box.style.display="block";box.innerHTML=`<div class="v2-lesson-loading"><div class="v2-loader-dot"></div><h2>${esc(tx("loadingLesson"))}</h2></div>`;
  try{
    const result=await bridge.startPractice?.({mode,level:requestedLevel,lang,skill});
    if(!result?.session)throw Object.assign(new Error("practice_failed"),{code:"practice_failed"});
    practiceSession=result.session;questions=practiceSession.questions.map(item=>({serverId:item.id,q:item.prompt,opts:item.options,a:Number(item.answer_index),audioText:item.audio_text||"",sentence:item.sentence||"",explanation:item.explanation||""}));answers=Array(questions.length).fill(null);qIndex=0;renderQuizQuestion();
  }catch(error){
    if(!bridge.hasAuth?.()){questions=buildExamQuestions(10);answers=Array(questions.length).fill(null);qIndex=0;renderQuizQuestion();return}
    const locked=error?.code==="free_feature_limit_reached";box.innerHTML=`<div class="v2-lesson-result"><div class="v2-result-mark">${locked?"◆":"!"}</div><h2>${esc(locked?tx("unlockMore"):tx("lessonLoadError"))}</h2><button class="v2-primary" onclick="${locked?"V2.openSubscription()":"V2.showPage('tests')"}">${esc(locked?tx("subscription"):tx("back"))}</button></div>`;
  }
}
function startPlacement(){beginCustomTest("placement",LEVEL_KEY)}
function startMock(level){beginCustomTest("mock",level||LEVEL_KEY)}
function startTraining(skill){beginCustomTest("training",LEVEL_KEY,skill)}
async function startMistakeReview(){
  testMode="mistakes";practiceSession=null;mistakeReviewSession=null;showPage("quiz");document.getElementById("score-box").style.display="none";const box=document.getElementById("quiz-box");box.style.display="block";box.innerHTML=`<div class="v2-lesson-loading"><div class="v2-loader-dot"></div><h2>${esc(tx("loadingLesson"))}</h2></div>`;
  try{
    const result=await bridge.startMistakeReview?.();if(!result?.session)throw Object.assign(new Error("mistake_review_failed"),{code:"mistake_review_failed"});
    mistakeReviewSession=result.session;questions=result.session.questions.map(item=>({serverId:item.id,q:item.prompt,opts:item.options,a:Number(item.answer_index),explanation:item.explanation||""}));answers=Array(questions.length).fill(null);qIndex=0;renderQuizQuestion();
  }catch(error){
    const locked=error?.code==="free_feature_limit_reached";box.innerHTML=`<div class="v2-lesson-result"><div class="v2-result-mark">${locked?"◆":"!"}</div><h2>${esc(locked?tx("unlockMore"):tx("lessonLoadError"))}</h2><button class="v2-primary" onclick="${locked?"V2.openSubscription()":"V2.showPage('mistakes')"}">${esc(locked?tx("subscription"):tx("back"))}</button></div>`;
  }
}

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
  meta.xp+=value;meta.daily.xp+=value;if(kind==="lesson")meta.daily.lesson=1;write(META_KEY,meta);renderAll();toast(`+${value} ${tx("xp")}`);
}
async function openChest(){
  const chest=chestState();
  if(!chest.ready){toast(tx("rewardLocked"));return}
  if(bridge.hasAuth?.()&&bridge.openRewardChest){
    try{
      const result=await bridge.openRewardChest();
      if(result?.ok){syncGamification(result,true);renderAll();toast(`+${Number(result.reward_value||result.awarded_xp||0)} ${tx("xp")} · ${tx("rewardChest")}`);return}
    }catch(_){toast(tx("rewardLocked"));return}
  }
  meta.chests=Number(meta.chests||0)+1;meta.xp+=10;meta.daily.xp+=10;write(META_KEY,meta);renderAll();toast(`+10 ${tx("xp")} · ${tx("rewardChest")}`)
}

function openSettings(){
  document.getElementById("v2-sheet")?.remove();const root=document.createElement("div");root.id="v2-sheet";root.className="v2-sheet-backdrop";
  root.innerHTML=`<div class="v2-sheet" onclick="event.stopPropagation()"><div class="v2-sheet-handle"></div><h2>${esc(tx("settings"))}</h2><p>${esc(tx("language"))}</p><div class="v2-sheet-actions">${["ru","tj","uz"].map(value=>`<button class="v2-secondary" onclick="V2.changeLanguage('${value}')">${value.toUpperCase()}</button>`).join("")}</div><p>${esc(tx("level"))}</p><div class="v2-sheet-actions">${LEVELS.map(value=>`<button class="v2-secondary" onclick="V2.changeLevel('${value}')">${labelLevel(value)}</button>`).join("")}</div></div>`;root.onclick=()=>root.remove();document.body.appendChild(root);
}
function changeLanguage(value){localStorage.setItem("hsk_all_current_lang_v3",value);bridge.openRoute?.({lang:value,level:LEVEL_KEY,tab:"profile"})}
function changeLevel(value){bridge.openRoute?.({level:value,lang,tab:"course"})}
function openSubscription(source="v3_profile"){bridge.reportEvent?.("checkout_opened",{source,level:LEVEL_KEY,status:ACCESS.status});bridge.openSubscribe?.(source)}
function openExternalUrl(url){
  const target=String(url||"").trim();
  if(!target)return false;
  const tg=window.Telegram?.WebApp;
  if((target.includes("t.me/")||target.startsWith("tg://"))&&typeof tg?.openTelegramLink==="function"){tg.openTelegramLink(target);return true}
  if(typeof tg?.openLink==="function"){tg.openLink(target);return true}
  window.location.href=target;return true;
}
function openSupport(source="profile_support"){
  bridge.reportEvent?.("support_opened",{source,level:LEVEL_KEY});
  const url=serverProfile?.support_url||ACCESS.support_url||"";
  if(!openExternalUrl(url))toast(tx("supportSub"));
}

function toast(message){document.querySelector(".v2-toast")?.remove();const item=document.createElement("div");item.className="v2-toast";item.textContent=message;document.body.appendChild(item);setTimeout(()=>item.remove(),2200)}

async function showOnboarding(){
  const query=new URLSearchParams(parent.location.search||location.search);if(query.get("tab")||query.get("lesson"))return;
  const nextAccess=await bridge.ensureAccess?.();ACCESS=nextAccess||bridge.getAccess?.()||ACCESS;
  if(ACCESS.course_profile?.onboarding_completed)return;
  if(localStorage.getItem(ONBOARDING_KEY)&&!bridge.hasAuth?.()&&!ACCESS.course_profile)return;
  const profile=ACCESS.course_profile||{};
  meta.goal=profile.goal||meta.goal;meta.minutes=Number(profile.daily_minutes||meta.minutes||10);
  onboarding.goal=["hsk_exam","study_china","work_china","daily_communication","travel"].includes(meta.goal)?meta.goal:"hsk_exam";onboarding.minutes=meta.minutes;onboarding.startMode=profile.start_mode==="placement"?"placement":"lesson_1";
  renderOnboarding();
  bridge.reportEvent?.("onboarding_started",{event_id:`onboarding:${today()}`,level:onboarding.level});
}
function renderOnboarding(){
  document.getElementById("v2-onboarding")?.remove();const root=document.createElement("div");root.id="v2-onboarding";root.className="v2-onboarding";
  const steps=[
    {title:tx("chooseLevel"),sub:tx("pathSub"),values:[["beginner",tx("beginnerLevel")],["hsk1","HSK 1"],["hsk2","HSK 2"],["hsk3","HSK 3"],["hsk4","HSK 4"]],field:"level"},
    {title:tx("chooseGoal"),sub:tx("onboardingTitle"),values:[["hsk_exam",tx("goalHsk")],["study_china",tx("goalStudy")],["work_china",tx("goalWork")],["daily_communication",tx("goalDaily")]],field:"goal"},
    {title:tx("chooseTime"),sub:tx("dailyGoal"),values:[[10,`10 ${tx("minutes")}`],[15,`15 ${tx("minutes")}`],[20,`20 ${tx("minutes")}`],[30,`30 ${tx("minutes")}`]],field:"minutes"},
    {title:tx("chooseStart"),sub:tx("onboardingSub"),values:[["lesson_1",tx("startLesson1")],["placement",tx("takePlacement")]],field:"startMode"}
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
  const mode=testMode,session=practiceSession,reviewSession=mistakeReviewSession;legacyFinishQuiz();if(mode!=="mistakes")rememberMistakes(lastWrongItems);
  if(mode==="lesson"&&lastQuizPercent>=60&&ACCESS.status!=="active"){meta.trialCourseCompleted=true;write(META_KEY,meta)}
  if(!session&&!reviewSession){if(mode==="lesson"&&lastQuizPercent>=60&&!state.done.includes(quizLesson)){state.done.push(quizLesson);saveState();addXP(20+Math.round(lastQuizPercent/10),"lesson")}else addXP(Math.max(5,Math.round(lastQuizPercent/10)),"quiz")}
  if(mode==="lesson"&&lastQuizPercent>=60){
    bridge.reportEvent?.("v2_lesson_completed",{lesson_id:quizLesson,percent:lastQuizPercent,score:lastQuizScore,total:lastQuizTotal});
  }
  if(session&&["placement","mock","training"].includes(mode))submitPracticeResult(session);
  if(reviewSession&&mode==="mistakes")submitMistakeReview(reviewSession);
  renderAll();testMode="";
};
async function submitPracticeResult(session){
  try{
    const result=await bridge.completePractice?.({session_id:session.id,mode:session.mode,skill:session.skill||"",level:session.level,lang,answers:questions.map((question,index)=>({question_id:question.serverId,selected_index:answers[index]}))});
    if(!result?.ok)return;
    serverMistakes=null;
    syncGamification(result.reward,true);
    rememberMistakes(result.wrong_items||[]);
    const wrongCount=(result.wrong_items||[]).length;
    document.getElementById("score-box")?.insertAdjacentHTML("beforeend",`<div class="v2-result-analysis"><div><b>${esc(tx("strengths"))}</b><small>${result.percent>=70?esc(tx("correct")):esc(tx("reviewNow"))}</small></div><div><b>${esc(tx("weaknesses"))}</b><small>${wrongCount} ${esc(tx("mistakesCount"))}</small></div><div><b>${esc(tx("recommendedLessons"))}</b><small>${esc(result.recommendation||labelLevel(session.level))}</small></div></div>`);
    if(session.mode==="placement"){write("hsk_v2_placement",{percent:result.percent,recommended:result.recommendation,createdAt:new Date().toISOString()});document.getElementById("score-box")?.insertAdjacentHTML("beforeend",`<div class="v2-goal" style="margin-top:12px"><div class="v2-kicker">${esc(tx("recommended"))}</div><h2 style="margin-top:6px">${esc(result.recommendation)}</h2></div>`)}
  }catch(error){const locked=error?.code==="free_feature_limit_reached";document.getElementById("score-box")?.insertAdjacentHTML("beforeend",`<div class="v2-goal" style="margin-top:12px"><b>${esc(locked?tx("unlockMore"):tx("lessonLoadError"))}</b></div>`)}
}
async function submitMistakeReview(session){
  try{
    const result=await bridge.completeMistakeReview?.({session_id:session.id,answers:questions.map((question,index)=>({question_id:question.serverId,selected_index:answers[index]}))});
    if(!result?.ok)return;serverMistakes=null;syncGamification(result.reward,true);await loadServerMistakes();document.getElementById("score-box")?.insertAdjacentHTML("beforeend",`<div class="v2-goal" style="margin-top:12px"><b>${result.remaining} ${esc(tx("mistakesCount"))}</b></div>`);
  }catch(_){document.getElementById("score-box")?.insertAdjacentHTML("beforeend",`<div class="v2-goal" style="margin-top:12px"><b>${esc(tx("lessonLoadError"))}</b></div>`)}
}
flipFC=function(index){const card=document.querySelector(`[data-card="${index}"]`),was=card?.classList.contains("flipped");legacyFlipFC(index);setTimeout(()=>{const now=document.querySelector(`[data-card="${index}"]`)?.classList.contains("flipped");if(!was&&now){meta.daily.words=Math.min(5,Number(meta.daily.words||0)+1);write(META_KEY,meta);renderHome()}},80)};
renderKPIs=function(){renderHome()};
renderLessons=function(){renderCourse();renderHome()};

function applyLaunch(){
  const params=bridge.getLaunchParams?.()||{};
  const target=normalizeLaunchTab(params.tab);
  if(params.exam==="mock")setTimeout(()=>startMock(),0);
  else if(params.exam==="placement")setTimeout(()=>startPlacement(),0);
  else if(params.mode==="quiz"){quizLesson=Number(params.lesson)||quizLesson;showPage("quiz");startQuiz()}
  else if(target){if(params.lesson){if(target==="flashcards")fcFilter=Number(params.lesson);if(target==="grammar")grammarFilter=Number(params.lesson);if(target==="quiz")quizLesson=Number(params.lesson)}showPage(target);if(target==="course"&&params.lesson)setTimeout(()=>openLesson(Number(params.lesson),params.section||""),0)}
  else {const page=["home","course","league","voice","tests","profile"].includes(params.tab)?params.tab:"home";showPage(page);if(page==="course"&&params.lesson)setTimeout(()=>openLesson(Number(params.lesson),params.section||""),0)}
}

function mount(){
  normalizeMeta();document.body.innerHTML=appMarkup();
  window.V2={showPage,quizBack,openLesson,startLesson,openWords,openGrammar,startPlacement,startMock,startTraining,startMistakeReview,openChest,openSettings,changeLanguage,changeLevel,openSubscription,openSupport,showPaywall,toast,pickOnboarding,onboardingBack,onboardingNext,playCurrentLessonAudio,answerLessonChoice,pickLessonToken,returnLessonToken,resetLessonOrder,checkLessonOrder,completePassiveLessonCard,continueLessonCard,retryLessonFlow,openNextLesson,openNextSection,jumpToCurrentSection,uploadAvatar,openLeagueUser};
  window.setAppAccess=function(next){ACCESS=next||bridge.getAccess?.()||ACCESS;syncGamification(ACCESS.gamification);renderAll()};
  window.setAppLanguage=function(next){lang=["uz","ru","tj"].includes(next)?next:lang;setLabels();renderFlashcards();renderGrammar();renderQuizFilters();renderAll()};
  syncGamification(ACCESS.gamification);setLabels();renderFlashcards();renderGrammar();renderQuizFilters();renderAll();applyLaunch();showOnboarding();
}

mount();
})();
