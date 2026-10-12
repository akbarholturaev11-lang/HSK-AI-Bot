/* Shared panda preparing state for real lesson/practice startup only.
   Never use it for navigation, account bootstrapping or incidental requests. */
(function(global){
"use strict";
var COPY={
  uz:{title:"Mashq tayyorlanmoqda",subtitle:"Panda bilan boshlaymiz"},
  ru:{title:"Готовим упражнение",subtitle:"Начинаем вместе с пандой"},
  tj:{title:"Машқ омода мешавад",subtitle:"Бо панда оғоз мекунем"}
};
function render(language){
  var copy=COPY[language]||COPY.uz;
  var panda=global.HSKCharacters&&typeof global.HSKCharacters.render==="function"
    ?global.HSKCharacters.render("panda","loading")
    :'<span aria-hidden="true" style="font-size:80px">🐼</span>';
  /* Inline sizing protects Telegram WKWebView even when an older scene CSS
     file is cached. Typography remains two separate block lines. */
  return '<div class="hsk-study-preparing" role="status" aria-live="polite" style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:7px;text-align:center;width:100%;max-width:100%;box-sizing:border-box">'
    +'<div class="hsk-study-preparing-panda" aria-hidden="true" style="display:grid;place-items:center;width:110px;height:121px;max-width:30vw;flex:none;overflow:hidden">'+panda+'</div>'
    +'<b style="display:block;font-size:16px;line-height:1.35;margin:5px 0 0">'+copy.title+'</b>'
    +'<small style="display:block;font-size:13px;line-height:1.45;margin:0">'+copy.subtitle+'</small>'
    +'<span class="hsk-study-preparing-dots" aria-hidden="true"><i></i><i></i><i></i></span></div>';
}
global.HSKStudyPreparing={render:render};
})(window);
