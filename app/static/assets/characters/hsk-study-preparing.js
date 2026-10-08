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
  return '<div class="hsk-study-preparing" role="status" aria-live="polite">'
    +'<div class="hsk-study-preparing-panda" aria-hidden="true">'+panda+'</div>'
    +'<b>'+copy.title+'</b><small>'+copy.subtitle+'</small>'
    +'<span class="hsk-study-preparing-dots" aria-hidden="true"><i></i><i></i><i></i></span></div>';
}
global.HSKStudyPreparing={render:render};
})(window);
