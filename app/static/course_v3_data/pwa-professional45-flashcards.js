/* UIUX-008: optional in-lesson self-assessment card from previously taught canonical words.
   No server grade, XP, hearts, lesson positions, content JSON, or mistake/SRS writes. */
(function(){
"use strict";
if(location.pathname!=="/iphone-pwa/course")return;
var installed=false,baseRender=null,session=null;
var COPY={
 ru:{heading:"Повторим слово",hint:"Сначала попробуйте вспомнить значение",show:"Показать ответ",again:"Повторить",know:"Знаю",listen:"Прослушать",self:"Самооценка не влияет на результат урока",example:"Пример",dismiss:"Продолжить урок"},
 uz:{heading:"So‘zni takrorlaymiz",hint:"Avval ma'nosini eslang",show:"Javobni ko‘rsatish",again:"Takrorlash",know:"Bilaman",listen:"Tinglash",self:"O‘z-o‘zini baholash dars natijasiga ta’sir qilmaydi",example:"Misol",dismiss:"Darsni davom ettirish"},
 tj:{heading:"Калимаро такрор мекунем",hint:"Аввал маънои онро ба ёд оред",show:"Дидани ҷавоб",again:"Такрор",know:"Медонам",listen:"Шунидан",self:"Худбаҳодиҳӣ ба натиҷаи дарс таъсир намекунад",example:"Мисол",dismiss:"Идома додани дарс"}
};
function words() {return (COPY[typeof LANG!=="undefined"?LANG:"ru"]||COPY.ru)}
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
   root.appendChild(btn("🔊 "+dict.listen,function(){if(typeof speak==="function")speak(word.zh)}, "p45-lesson-flash-audio"));
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