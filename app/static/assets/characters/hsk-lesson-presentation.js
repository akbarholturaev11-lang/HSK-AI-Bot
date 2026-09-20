(function(global){
"use strict";

var active=null;
function copy(lang){
  var M={
    uz:{title:"Dars tayyorlanmoqda",sub:"Panda siz bilan boshlaydi"},
    ru:{title:"Готовим урок",sub:"Панда уже ждёт вас"},
    tj:{title:"Дарс омода мешавад",sub:"Панда шуморо интизор аст"}
  };
  return M[lang]||M.uz;
}
function make(opts){
  opts=opts||{};
  if(active&&active.cancel)active.cancel(true);
  var lang=opts.lang||"uz",c=copy(lang),id=opts.character||"panda";
  var root=document.createElement("div");
  root.className="hsk-entry-overlay";
  root.setAttribute("role","status");
  root.setAttribute("aria-live","polite");
  root.innerHTML='<div class="hsk-entry-card"><div class="hsk-entry-character hsk-character-stage" data-entry-character></div>'
    +'<div class="hsk-entry-title">'+c.title+'</div><div class="hsk-entry-sub">'+c.sub+'</div>'
    +'<div class="hcm-loader-dots hsk-entry-dots" aria-hidden="true"><i></i><i></i><i></i></div></div>';
  document.body.appendChild(root);
  var charHost=root.querySelector("[data-entry-character]");
  if(global.HSKCharacters)global.HSKCharacters.mount(charHost,id,"loading");
  if(global.HSKCharacterMotion)global.HSKCharacterMotion.play(charHost,"pop");
  var started=Date.now(),finished=false,revealTimer=0,removeTimer=0;
  var api={
    root:root,
    reveal:function(build){
      if(finished)return;
      var minVisible=Math.max(0,720-(Date.now()-started));
      clearTimeout(revealTimer);
      revealTimer=setTimeout(function(){
        if(finished)return;
        if(typeof build==="function")build();
        if(global.HSKCharacterMotion)global.HSKCharacterMotion.play(charHost,"exit");
        requestAnimationFrame(function(){
          requestAnimationFrame(function(){
            if(finished)return;
            root.classList.add("is-revealing");
            removeTimer=setTimeout(function(){
              finished=true;
              if(root.parentNode)root.parentNode.removeChild(root);
              if(active===api)active=null;
            },430);
          });
        });
      },minVisible);
    },
    cancel:function(immediate){
      if(finished)return;
      finished=true;clearTimeout(revealTimer);clearTimeout(removeTimer);
      root.classList.add("is-cancelled");
      setTimeout(function(){
        if(root.parentNode)root.parentNode.removeChild(root);
        if(active===api)active=null;
      },immediate?0:190);
    }
  };
  active=api;return api;
}

global.HSKLessonPresentation={
  version:"1.0.0-phase3",
  beginLessonEntry:make,
  cancelEntry:function(){if(active&&active.cancel)active.cancel()},
  currentEntry:function(){return active}
};
})(window);
