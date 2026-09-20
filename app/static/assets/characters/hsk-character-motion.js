(function(global){
"use strict";

var DUR={
  pop:560,
  jump:720,
  laugh:820,
  proud:620,
  dismiss:720,
  wrong:540,
  oneHeart:980,
  celebrate:1080,
  loader:1200,
  exit:520,
  land:820
};

function reduced(){
  try{return !!(global.matchMedia&&global.matchMedia("(prefers-reduced-motion: reduce)").matches)}
  catch(e){return false}
}
function host(target){
  if(typeof target==="string")target=document.querySelector(target);
  if(!target)return null;
  if(target.classList&&target.classList.contains("hsk-character"))return target.parentElement||target;
  return target;
}
function character(target){
  var h=host(target);
  if(!h)return null;
  return h.classList&&h.classList.contains("hsk-character")?h:h.querySelector(".hsk-character");
}
function core(target){
  var c=character(target);
  return c&&(c.querySelector(".hc-core")||c);
}
function animate(el,frames,opts){
  if(!el||reduced()||!el.animate)return Promise.resolve();
  try{
    var a=el.animate(frames,opts);
    return a.finished?Promise.resolve(a.finished).catch(function(){}):new Promise(function(r){setTimeout(r,Number(opts.duration||0))});
  }catch(e){return Promise.resolve()}
}
function stage(target){
  var h=host(target);
  if(!h)return null;
  if(h.classList&&h.classList.contains("hsk-character-stage"))return h;
  return h.closest&&h.closest(".hsk-character-stage")||h;
}
function cleanupNodes(root,selector){
  if(!root)return;
  root.querySelectorAll(selector).forEach(function(n){n.remove()});
}
function burst(target,count){
  var root=stage(target);if(!root||reduced())return;
  cleanupNodes(root,".hcm-burst");
  var colors=["#E04A40","#E9A916","#2FA06A","#2E86C1","#F2A9B5"];
  count=Math.max(8,Math.min(30,Number(count||16)));
  for(var i=0;i<count;i++){
    var p=document.createElement("i");p.className="hcm-burst";p.style.background=colors[i%colors.length];root.appendChild(p);
    var a=Math.random()*Math.PI*2,d=58+Math.random()*65,rot=Math.round(Math.random()*420-210);
    if(p.animate)p.animate([
      {opacity:0,transform:"translate(-50%,-50%) scale(.35) rotate(0)"},
      {opacity:1,offset:.18,transform:"translate(-50%,-50%) scale(1) rotate("+Math.round(rot*.25)+"deg)"},
      {opacity:0,transform:"translate(calc(-50% + "+Math.round(Math.cos(a)*d)+"px),calc(-50% + "+Math.round(Math.sin(a)*d)+"px)) scale(.72) rotate("+rot+"deg)"}
    ],{duration:760+Math.round(Math.random()*220),easing:"cubic-bezier(.2,.75,.25,1)"});
    setTimeout((function(node){return function(){node.remove()}})(p),1100);
  }
}
function warningRing(target){
  var root=stage(target);if(!root||reduced())return;
  cleanupNodes(root,".hcm-ring,.hcm-heart");
  var r=document.createElement("i");r.className="hcm-ring";root.appendChild(r);
  var h=document.createElement("span");h.className="hcm-heart";h.textContent="♥";h.style.color="#E04A40";root.appendChild(h);
  if(r.animate)r.animate([
    {opacity:0,transform:"scale(.55)"},
    {opacity:.65,offset:.25,transform:"scale(.9)"},
    {opacity:0,transform:"scale(1.55)"}
  ],{duration:900,easing:"ease-out"});
  if(h.animate)h.animate([
    {opacity:0,transform:"translateX(-50%) translateY(8px) scale(.55)"},
    {opacity:1,offset:.28,transform:"translateX(-50%) translateY(0) scale(1.18)"},
    {opacity:0,transform:"translateX(-50%) translateY(-16px) scale(.9)"}
  ],{duration:920,easing:"cubic-bezier(.2,.8,.3,1)"});
  setTimeout(function(){r.remove();h.remove()},1050);
}
function setBusy(target,on){
  var root=stage(target);if(root&&root.classList)root.classList.toggle("hcm-busy",!!on)
}
function play(target,kind,opts){
  opts=opts||{};kind=String(kind||"pop");
  var c=character(target),k=core(target);if(!c||!k)return Promise.resolve();
  if(reduced())return Promise.resolve();
  var p;
  setBusy(target,opts.busy===true);
  if(kind==="jump"){
    p=animate(k,[
      {transform:"translateY(0) scale(1)"},
      {transform:"translateY(5px) scaleY(.88) scaleX(1.08)",offset:.16},
      {transform:"translateY(-24px) scaleY(1.08) scaleX(.96)",offset:.48,easing:"cubic-bezier(.18,.8,.25,1)"},
      {transform:"translateY(2px) scaleY(.94) scaleX(1.04)",offset:.82},
      {transform:"translateY(0) scale(1)"}
    ],{duration:DUR.jump,easing:"ease-out"});
  }else if(kind==="laugh"){
    p=animate(k,[
      {transform:"translateY(0) rotate(0)"},
      {transform:"translateY(-4px) rotate(-4deg)",offset:.2},
      {transform:"translateY(0) rotate(4deg)",offset:.38},
      {transform:"translateY(-3px) rotate(-3deg)",offset:.56},
      {transform:"translateY(0) rotate(3deg)",offset:.74},
      {transform:"translateY(0) rotate(0)"}
    ],{duration:DUR.laugh,easing:"ease-in-out"});
  }else if(kind==="proud"){
    p=animate(k,[
      {transform:"translateY(0) rotate(0) scale(1)"},
      {transform:"translateY(-5px) rotate(3deg) scale(1.03)",offset:.38},
      {transform:"translateY(-4px) rotate(1deg) scale(1.025)",offset:.72},
      {transform:"translateY(0) rotate(0) scale(1)"}
    ],{duration:DUR.proud,easing:"cubic-bezier(.2,.75,.25,1)"});
  }else if(kind==="dismiss"){
    p=animate(k,[
      {transform:"translateX(0) rotate(0)"},
      {transform:"translateX(-5px) rotate(-5deg)",offset:.34},
      {transform:"translateX(-3px) rotate(-3deg)",offset:.7},
      {transform:"translateX(0) rotate(0)"}
    ],{duration:DUR.dismiss,easing:"ease-in-out"});
  }else if(kind==="wrong"){
    p=animate(k,[
      {transform:"translateX(0) rotate(0) scale(1)"},
      {transform:"translateX(-7px) rotate(-3deg) scale(.98)",offset:.23},
      {transform:"translateX(6px) rotate(2deg)",offset:.43},
      {transform:"translateX(-3px) rotate(-1deg)",offset:.62},
      {transform:"translateX(2px) rotate(0)",offset:.8},
      {transform:"translateX(0) scale(1)"}
    ],{duration:DUR.wrong,easing:"ease-out"});
  }else if(kind==="oneHeart"){
    warningRing(target);
    p=animate(k,[
      {transform:"scale(1) translateX(0)"},
      {transform:"scale(.96) translateX(-4px)",offset:.12},
      {transform:"scale(1.07) translateX(4px)",offset:.27},
      {transform:"scale(.98) translateX(-3px)",offset:.42},
      {transform:"scale(1.05) translateX(2px)",offset:.58},
      {transform:"scale(1) translateX(0)",offset:.78},
      {transform:"scale(1)"}
    ],{duration:DUR.oneHeart,easing:"ease-out"});
  }else if(kind==="celebrate"){
    burst(target,opts.particles||20);
    p=animate(k,[
      {transform:"translateY(0) scale(1) rotate(0)"},
      {transform:"translateY(6px) scaleY(.86) scaleX(1.09)",offset:.12},
      {transform:"translateY(-28px) scale(1.08) rotate(-5deg)",offset:.4,easing:"cubic-bezier(.16,.82,.26,1)"},
      {transform:"translateY(-8px) scale(1.02) rotate(4deg)",offset:.63},
      {transform:"translateY(3px) scaleY(.93) scaleX(1.05) rotate(0)",offset:.84},
      {transform:"translateY(0) scale(1)"}
    ],{duration:DUR.celebrate,easing:"ease-out"});
  }else if(kind==="loader"){
    p=animate(k,[
      {transform:"translateY(0) rotate(-1deg) scale(1)"},
      {transform:"translateY(-5px) rotate(1.5deg) scale(1.015)",offset:.5},
      {transform:"translateY(0) rotate(-1deg) scale(1)"}
    ],{duration:DUR.loader,easing:"ease-in-out",iterations:1});
  }else if(kind==="exit"){
    p=animate(c,[
      {opacity:1,transform:"translateY(0) scale(1)"},
      {opacity:1,transform:"translateY(-7px) scale(1.04)",offset:.28},
      {opacity:0,transform:"translateY(-24px) scale(.86)"}
    ],{duration:DUR.exit,easing:"cubic-bezier(.3,.1,.6,1)"});
  }else if(kind==="land"){
    p=animate(c,[
      {opacity:0,transform:"translateY(-110px) scale(.88)"},
      {opacity:1,transform:"translateY(7px) scaleY(.78) scaleX(1.15)",offset:.58},
      {transform:"translateY(-8px) scaleY(1.04) scaleX(.98)",offset:.78},
      {transform:"translateY(0) scale(1)"}
    ],{duration:DUR.land,easing:"cubic-bezier(.2,.75,.3,1)"});
  }else{
    p=animate(k,[
      {opacity:0,transform:"translateY(12px) scale(.62)"},
      {opacity:1,transform:"translateY(-7px) scale(1.08)",offset:.58},
      {transform:"translateY(0) scale(1)"}
    ],{duration:DUR.pop,easing:"cubic-bezier(.2,.85,.25,1)"});
  }
  return Promise.resolve(p).then(function(){setBusy(target,false)});
}
function moodForReaction(reaction){
  return {
    correct:"correct",
    jump:"correct",
    laugh:"celebrate",
    proud:"proud",
    dismiss:"dismissive",
    wrong:"wrong",
    oneHeart:"one-heart",
    celebrate:"celebrate",
    loader:"loading",
    land:"celebrate",
    pop:"idle"
  }[reaction]||"idle";
}
function effectForReaction(reaction){
  return {correct:"jump",oneHeart:"oneHeart"}[reaction]||reaction;
}
function react(target,id,reaction,opts){
  opts=opts||{};
  if(global.HSKCharacters&&typeof global.HSKCharacters.mount==="function"){
    global.HSKCharacters.mount(target,id,moodForReaction(reaction),opts);
  }
  return play(target,effectForReaction(reaction),opts);
}

global.HSKCharacterMotion={
  version:"1.0.0-phase2",
  durations:DUR,
  reduced:reduced,
  play:play,
  react:react,
  burst:burst,
  warningRing:warningRing
};
})(window);
