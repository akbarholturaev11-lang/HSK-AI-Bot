(function(global){
"use strict";

var CAST={
  panda:{name:"Panda",zh:"熊猫",role:"main_coach",weight:46},
  dragon:{name:"Longlong",zh:"龙龙",role:"energy_milestone",weight:16},
  crane:{name:"Hehe",zh:"鹤鹤",role:"grammar_precision",weight:13},
  monkey:{name:"Wuwu",zh:"悟悟",role:"drill_dialogue",weight:13},
  rabbit:{name:"Yueyue",zh:"月月",role:"memory_warning",weight:12}
};
var MOODS=["idle","talk","correct","wrong","celebrate","proud","dismissive","one-heart","loading"];

function safeMood(m){
  m=String(m||"idle").toLowerCase();
  return MOODS.indexOf(m)>=0?m:"idle";
}
function safeId(id){return CAST[id]?id:"panda"}
function svgWrap(id,mood,viewBox,inner,label){
  return '<svg class="hsk-character hsk-character--'+id+' hsk-mood-'+mood+'" viewBox="'+viewBox+'" role="img" aria-label="'+label+'">'
    +inner+'</svg>';
}
function sparks(){
  return '<path class="hc-spark" d="M0 -5 L1.4 -1.4 L5 0 L1.4 1.4 L0 5 L-1.4 1.4 L-5 0 L-1.4 -1.4 Z" transform="translate(18 16)" fill="#E9A916"/>'
    +'<path class="hc-spark" d="M0 -4 L1.1 -1.1 L4 0 L1.1 1.1 L0 4 L-1.1 1.1 L-4 0 L-1.1 -1.1 Z" transform="translate(88 12)" fill="#E9A916"/>'
    +'<path class="hc-spark" d="M0 -3 L.8 -.8 L3 0 L.8 .8 L0 3 L-.8 .8 L-3 0 L-.8 -.8 Z" transform="translate(77 88)" fill="#F2A9B5"/>';
}
function eyes(mood,x1,x2,y,ink){
  if(mood==="celebrate"||mood==="proud"){
    return '<path d="M'+(x1-5)+' '+(y+1)+' q5 -6 10 0" fill="none" stroke="'+ink+'" stroke-width="2.7" stroke-linecap="round"/>'
      +'<path d="M'+(x2-5)+' '+(y+1)+' q5 -6 10 0" fill="none" stroke="'+ink+'" stroke-width="2.7" stroke-linecap="round"/>';
  }
  if(mood==="wrong"||mood==="one-heart"){
    return '<ellipse cx="'+x1+'" cy="'+y+'" rx="3.3" ry="4.4" fill="'+ink+'"/><ellipse cx="'+x2+'" cy="'+y+'" rx="3.3" ry="4.4" fill="'+ink+'"/>'
      +'<path d="M'+(x1-5)+' '+(y-7)+' q5 -3 10 0" stroke="'+ink+'" stroke-width="2" fill="none"/>'
      +'<path d="M'+(x2-5)+' '+(y-7)+' q5 -3 10 0" stroke="'+ink+'" stroke-width="2" fill="none"/>';
  }
  if(mood==="dismissive"){
    return '<path d="M'+(x1-5)+' '+y+' h10" stroke="'+ink+'" stroke-width="2.5" stroke-linecap="round"/>'
      +'<ellipse cx="'+(x2+1)+'" cy="'+y+'" rx="3.2" ry="4" fill="'+ink+'"/>';
  }
  return '<ellipse class="hc-eye" cx="'+x1+'" cy="'+y+'" rx="3.5" ry="4.5" fill="'+ink+'"/>'
    +'<ellipse class="hc-eye" cx="'+x2+'" cy="'+y+'" rx="3.5" ry="4.5" fill="'+ink+'"/>'
    +'<circle cx="'+(x1+1)+'" cy="'+(y-1)+'" r="1" fill="#fff"/><circle cx="'+(x2+1)+'" cy="'+(y-1)+'" r="1" fill="#fff"/>';
}
function mouth(mood,cx,cy,ink,accent){
  if(mood==="talk")return '<g class="hc-mouth"><ellipse cx="'+cx+'" cy="'+cy+'" rx="5.3" ry="4.8" fill="'+accent+'"/><ellipse cx="'+cx+'" cy="'+(cy+2)+'" rx="2.8" ry="1.6" fill="#F49B91"/></g>';
  if(mood==="celebrate"||mood==="correct")return '<path class="hc-mouth" d="M'+(cx-7)+' '+(cy-2)+' q7 10 14 0 q-7 4 -14 0 z" fill="'+accent+'"/>';
  if(mood==="wrong"||mood==="one-heart")return '<path class="hc-mouth" d="M'+(cx-6)+' '+(cy+3)+' q6 -6 12 0" fill="none" stroke="'+ink+'" stroke-width="2.3" stroke-linecap="round"/>';
  if(mood==="dismissive")return '<path class="hc-mouth" d="M'+(cx-6)+' '+cy+' q6 2 12 0" fill="none" stroke="'+ink+'" stroke-width="2.2" stroke-linecap="round"/>';
  return '<path class="hc-mouth" d="M'+(cx-6)+' '+cy+' q6 5 12 0" fill="none" stroke="'+ink+'" stroke-width="2.3" stroke-linecap="round"/>';
}
function loadingBook(x,y){
  return '<g class="hc-loading-prop" transform="translate('+x+' '+y+')"><path d="M-19 -10 q10 -5 19 1 v25 q-9 -6 -19 -1z" fill="#FFF8E8" stroke="#A8782B" stroke-width="2"/>'
    +'<path d="M19 -10 q-10 -5 -19 1 v25 q9 -6 19 -1z" fill="#FFF8E8" stroke="#A8782B" stroke-width="2"/>'
    +'<path d="M0 -9 v25" stroke="#D5A84C" stroke-width="1.5"/></g>';
}

function panda(mood){
  var I="#29241F",F="#FFFDF7",D="#D9BE94",C="#FFF2D9",A="#9A4036";
  var armL='<path d="M34 70 q-13 3 -14 17 q7 5 13 0 q1 -9 5 -13z" fill="'+I+'"/>';
  var armR='<path d="M66 70 q13 3 14 17 q-7 5 -13 0 q-1 -9 -5 -13z" fill="'+I+'"/>';
  if(mood==="celebrate"||mood==="correct"){armL='<path d="M35 69 q-17 -8 -18 -26 q7 -5 12 1 q2 12 12 18z" fill="'+I+'"/>';armR='<path d="M65 69 q17 -8 18 -26 q-7 -5 -12 1 q-2 12 -12 18z" fill="'+I+'"/>'}
  if(mood==="proud"){armL='<path d="M34 70 q4 14 16 12 q-5 -8 -11 -15z" fill="'+I+'"/>';armR='<path d="M66 70 q-4 14 -16 12 q5 -8 11 -15z" fill="'+I+'"/>'}
  var prop=mood==="loading"?loadingBook(50,82):"";
  var body='<ellipse class="hc-shadow" cx="50" cy="103" rx="27" ry="5" fill="#211D17"/>'
    +'<g class="hc-core"><g>'+armL+armR+'<ellipse cx="38" cy="98" rx="9" ry="6" fill="'+I+'"/><ellipse cx="62" cy="98" rx="9" ry="6" fill="'+I+'"/></g>'
    +'<path class="hc-depth" d="M31 96 q-6 -28 9 -39 h22 q16 10 9 39 q-20 9 -40 0z" fill="'+D+'"/>'
    +'<path d="M28 94 q-4 -26 9 -35 h26 q13 9 9 35 q-22 8 -44 0z" fill="'+F+'" stroke="'+I+'" stroke-width="3"/>'
    +'<ellipse cx="50" cy="80" rx="14" ry="10" fill="'+C+'"/><ellipse class="hc-highlight" cx="43" cy="71" rx="9" ry="4" fill="#fff"/>'
    +'<circle cx="28" cy="18" r="12" fill="'+I+'"/><circle cx="72" cy="18" r="12" fill="'+I+'"/>'
    +'<circle cx="50" cy="40" r="29" fill="'+F+'" stroke="'+I+'" stroke-width="3"/>'
    +'<path class="hc-depth" d="M62 14 q17 13 16 28 q-2 18 -19 25 q12 -18 3 -53z" fill="'+D+'"/>'
    +'<ellipse cx="38" cy="38" rx="9" ry="12" fill="'+I+'" transform="rotate(-12 38 38)"/><ellipse cx="62" cy="38" rx="9" ry="12" fill="'+I+'" transform="rotate(12 62 38)"/>'
    +eyes(mood,38,62,38,"#fff")+'<ellipse cx="50" cy="53" rx="11" ry="8" fill="'+C+'"/>'
    +'<path d="M46 49 q4 -3 8 0 q-2 4 -4 4 q-2 0 -4 -4z" fill="'+I+'"/>'+mouth(mood,50,57,I,A)
    +'<ellipse cx="30" cy="50" rx="4.5" ry="3" fill="#F2B4BC"/><ellipse cx="70" cy="50" rx="4.5" ry="3" fill="#F2B4BC"/>'
    +prop+(mood==="celebrate"?sparks():"")+'</g>';
  return svgWrap("panda",mood,"0 0 100 110",body,"HSK AI panda");
}

function dragon(mood){
  var R="#D84A3F",R2="#A92F2A",G="#F1BE4A",I="#30251F",C="#FFF3D7";
  var body='<ellipse class="hc-shadow" cx="61" cy="104" rx="34" ry="5" fill="#211D17"/>'
    +'<g class="hc-core"><path d="M79 95 C42 107 24 89 36 72 C48 56 80 70 74 52 C68 34 40 42 34 58" fill="none" stroke="'+R2+'" stroke-width="21" stroke-linecap="round"/>'
    +'<path d="M79 92 C46 102 31 87 41 74 C51 62 75 73 69 53 C64 39 45 44 39 58" fill="none" stroke="'+R+'" stroke-width="15" stroke-linecap="round"/>'
    +'<path d="M77 91 C49 97 39 86 46 76 C52 68 69 76 64 54" fill="none" stroke="'+G+'" stroke-width="4" stroke-linecap="round" opacity=".8"/>'
    +'<path d="M31 58 q-12 -9 -8 -22 l8 6 q-2 -13 8 -20 l4 10 q6 -13 17 -11 l-1 11 q14 -6 20 4 l-9 7 q11 4 8 14 l-12 -2" fill="'+R+'" stroke="'+R2+'" stroke-width="2.5" stroke-linejoin="round"/>'
    +'<ellipse cx="50" cy="51" rx="23" ry="19" fill="'+R+'"/><ellipse class="hc-highlight" cx="42" cy="43" rx="10" ry="6" fill="#F37A6D"/>'
    +'<path d="M34 34 l-8 -13 l14 7 M63 33 l9 -14 l-2 16" fill="'+G+'" stroke="'+I+'" stroke-width="2" stroke-linejoin="round"/>'
    +'<ellipse cx="39" cy="48" rx="7" ry="8" fill="'+C+'"/><ellipse cx="61" cy="48" rx="7" ry="8" fill="'+C+'"/>'
    +eyes(mood,40,60,48,I)
    +'<ellipse cx="50" cy="61" rx="14" ry="9" fill="'+C+'"/><circle cx="44" cy="59" r="1.6" fill="'+I+'"/><circle cx="56" cy="59" r="1.6" fill="'+I+'"/>'
    +mouth(mood,50,65,I,"#742820")
    +'<path d="M30 58 q-14 1 -20 -6 M31 62 q-14 6 -21 3 M70 58 q14 1 20 -6 M69 62 q14 6 21 3" fill="none" stroke="'+I+'" stroke-width="1.4" stroke-linecap="round"/>'
    +(mood==="loading"?loadingBook(57,87):"")+(mood==="celebrate"?sparks():"")+'</g>';
  return svgWrap("dragon",mood,"0 0 110 112",body,"HSK AI Chinese dragon");
}

function crane(mood){
  var W="#FFFDF8",S="#D8D7D2",I="#28231F",R="#D74A42",B="#E8B84B";
  var wing=mood==="celebrate"?'<path d="M48 69 q-27 -20 -34 -3 q15 12 35 15z" fill="'+W+'" stroke="'+I+'" stroke-width="2"/><path d="M55 69 q28 -20 35 -3 q-16 12 -36 15z" fill="'+W+'" stroke="'+I+'" stroke-width="2"/>':'<path d="M42 71 q-20 3 -22 19 q16 2 29 -7z" fill="'+W+'" stroke="'+I+'" stroke-width="2"/><path d="M59 71 q18 4 20 18 q-14 3 -27 -6z" fill="'+W+'" stroke="'+I+'" stroke-width="2"/>';
  var body='<ellipse class="hc-shadow" cx="51" cy="105" rx="25" ry="4" fill="#211D17"/><g class="hc-core">'
    +'<path d="M50 93 q-4 11 -3 15 M58 92 q3 11 2 16" stroke="#9E7040" stroke-width="3" stroke-linecap="round"/>'
    +'<path d="M44 108 h-10 M46 108 h8 M60 108 h-7 M60 108 h11" stroke="#9E7040" stroke-width="2" stroke-linecap="round"/>'
    +wing+'<ellipse cx="52" cy="77" rx="23" ry="20" fill="'+W+'" stroke="'+I+'" stroke-width="2.4"/>'
    +'<path class="hc-depth" d="M57 59 q18 8 18 23 q-8 14 -24 15 q12 -17 6 -38z" fill="'+S+'"/>'
    +'<path d="M53 64 C44 49 46 34 52 25 C57 17 65 18 69 25 C62 31 61 42 64 58" fill="'+W+'" stroke="'+I+'" stroke-width="2.5"/>'
    +'<circle cx="61" cy="25" r="10" fill="'+W+'" stroke="'+I+'" stroke-width="2.4"/><path d="M55 17 q7 -8 14 0" fill="'+R+'"/>'
    +eyes(mood,59,64,25,I)
    +'<path d="M70 25 l18 4 l-18 5z" fill="'+B+'" stroke="'+I+'" stroke-width="1.7"/>'
    +mouth(mood,62,33,I,R)
    +(mood==="loading"?loadingBook(48,83):"")+(mood==="celebrate"?sparks():"")+'</g>';
  return svgWrap("crane",mood,"0 0 100 112",body,"HSK AI red-crowned crane");
}

function monkey(mood){
  var F="#D7A250",D="#9D6B35",I="#30251E",C="#FFE4BB",A="#8C3E32";
  var tail='<path d="M76 78 q23 -7 18 12 q-5 17 -21 8" fill="none" stroke="'+D+'" stroke-width="9" stroke-linecap="round"/>';
  var arms=mood==="celebrate"?'<path d="M34 70 q-15 -10 -13 -26" stroke="'+D+'" stroke-width="10" stroke-linecap="round"/><path d="M66 70 q15 -10 13 -26" stroke="'+D+'" stroke-width="10" stroke-linecap="round"/>':'<path d="M34 70 q-12 6 -10 18" stroke="'+D+'" stroke-width="10" stroke-linecap="round"/><path d="M66 70 q12 6 10 18" stroke="'+D+'" stroke-width="10" stroke-linecap="round"/>';
  var body='<ellipse class="hc-shadow" cx="50" cy="104" rx="28" ry="5" fill="#211D17"/><g class="hc-core">'+tail+arms
    +'<ellipse cx="50" cy="79" rx="25" ry="23" fill="'+F+'" stroke="'+I+'" stroke-width="2.6"/>'
    +'<ellipse class="hc-depth" cx="60" cy="82" rx="13" ry="18" fill="'+D+'"/>'
    +'<ellipse cx="38" cy="99" rx="9" ry="6" fill="'+D+'"/><ellipse cx="62" cy="99" rx="9" ry="6" fill="'+D+'"/>'
    +'<circle cx="25" cy="39" r="10" fill="'+D+'"/><circle cx="75" cy="39" r="10" fill="'+D+'"/>'
    +'<ellipse cx="50" cy="43" rx="27" ry="25" fill="'+F+'" stroke="'+I+'" stroke-width="2.6"/>'
    +'<path class="hc-highlight" d="M31 35 q19 -22 38 0 q-6 -7 -10 1 q-9 -8 -18 0 q-5 -8 -10 -1z" fill="#F0C77D"/>'
    +'<ellipse cx="50" cy="47" rx="18" ry="17" fill="'+C+'"/>'
    +eyes(mood,42,58,43,I)+'<ellipse cx="50" cy="51" rx="4" ry="3" fill="'+I+'"/>'
    +mouth(mood,50,57,I,A)
    +(mood==="loading"?loadingBook(51,84):"")+(mood==="celebrate"?sparks():"")+'</g>';
  return svgWrap("monkey",mood,"0 0 105 112",body,"HSK AI golden monkey");
}

function rabbit(mood){
  var W="#F8F3E8",D="#DDD0BD",I="#302A24",P="#E9A8B2",J="#55A47A",A="#8D4038";
  var ears='<ellipse cx="37" cy="20" rx="10" ry="22" fill="'+W+'" stroke="'+I+'" stroke-width="2.4" transform="rotate(-8 37 20)"/><ellipse cx="63" cy="20" rx="10" ry="22" fill="'+W+'" stroke="'+I+'" stroke-width="2.4" transform="rotate(8 63 20)"/><ellipse cx="37" cy="20" rx="4" ry="15" fill="'+P+'" opacity=".7"/><ellipse cx="63" cy="20" rx="4" ry="15" fill="'+P+'" opacity=".7"/>';
  var body='<ellipse class="hc-shadow" cx="50" cy="105" rx="27" ry="5" fill="#211D17"/><g class="hc-core">'+ears
    +'<ellipse cx="50" cy="80" rx="25" ry="23" fill="'+W+'" stroke="'+I+'" stroke-width="2.6"/><path class="hc-depth" d="M58 59 q18 10 16 29 q-9 11 -24 14 q12 -20 8 -43z" fill="'+D+'"/>'
    +'<ellipse cx="34" cy="100" rx="10" ry="6" fill="'+W+'" stroke="'+I+'" stroke-width="2"/><ellipse cx="66" cy="100" rx="10" ry="6" fill="'+W+'" stroke="'+I+'" stroke-width="2"/>'
    +'<circle cx="50" cy="48" r="27" fill="'+W+'" stroke="'+I+'" stroke-width="2.6"/><ellipse class="hc-highlight" cx="41" cy="37" rx="10" ry="6" fill="#fff"/>'
    +eyes(mood,41,59,47,I)+'<path d="M46 55 q4 -3 8 0 q-2 4 -4 4 q-2 0 -4 -4z" fill="'+P+'"/>'
    +mouth(mood,50,62,I,A)
    +'<path d="M69 71 q12 4 15 15 q-8 4 -15 -2z" fill="'+W+'" stroke="'+I+'" stroke-width="2"/>'
    +'<circle cx="80" cy="89" r="7" fill="'+J+'"/><path d="M80 82 v14 M73 89 h14" stroke="#D9F0E3" stroke-width="1.5" opacity=".7"/>'
    +(mood==="loading"?loadingBook(49,84):"")+(mood==="celebrate"?sparks():"")+'</g>';
  return svgWrap("rabbit",mood,"0 0 100 112",body,"HSK AI jade rabbit");
}

function render(id,mood,opts){
  id=safeId(id);mood=safeMood(mood);opts=opts||{};
  if(id==="dragon")return dragon(mood);
  if(id==="crane")return crane(mood);
  if(id==="monkey")return monkey(mood);
  if(id==="rabbit")return rabbit(mood);
  return panda(mood);
}
function mount(el,id,mood,opts){
  if(typeof el==="string")el=document.querySelector(el);
  if(!el)return null;
  el.innerHTML=render(id,mood,opts);
  return el.querySelector(".hsk-character");
}
function info(id){id=safeId(id);var out={};for(var k in CAST[id])out[k]=CAST[id][k];out.id=id;return out}
function list(){return Object.keys(CAST).map(info)}

global.HSKCharacters={
  version:"1.0.0-phase1",
  cast:CAST,
  moods:MOODS.slice(),
  list:list,
  info:info,
  render:render,
  mount:mount
};
})(window);
