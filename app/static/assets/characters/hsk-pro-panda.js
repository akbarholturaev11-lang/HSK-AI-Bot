/* HSK AI Pro panda — reusable, visual-only Pro/Trial mascot with effects.
 *
 * The drawing is the canonical course panda exactly as the inline Pro sheet
 * draws it (course_v3_data/iphone-pwa-inline-pro.js pandaSvg; same head, ears,
 * body, colours and breathing). No new character is introduced.
 *
 * API (no globals other than window.HSKProPanda):
 *   HSKProPanda.render(pose)             -> markup string ("pro" | "celebrate" | "read")
 *   HSKProPanda.mount(el, {pose, burst}) -> fills el; burst:true plays the spark burst once
 *   HSKProPanda.burst(el)                -> one-time gold spark burst around el's panda
 *   HSKProPanda.glint(el)                -> one-time gold light sweep across any card/badge
 *
 * Effects play once and settle (motion guideline); under
 * prefers-reduced-motion everything renders static. Purely decorative:
 * aria-hidden, no text, no network, no entitlement logic.
 * Styles: /assets/characters/hsk-pro-panda.css (+ /assets/brand/hsk-pro-theme.css).
 */
(function(global){
  "use strict";
  if (global.HSKProPanda) return;
  var POSES=["pro","celebrate","read"];
  var seq=0;
  function reduced(){
    try { return !!(global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches); }
    catch (_) { return false; }
  }
  function pandaSvg(pose, uid) {
    var INK="#2B2620",MOUTH="#8E3A31",TONGUE="#E07B72",BLUSH="#F5B8C0",GOLD="#E9A916",FACE="#FFFDF7",CREAM="#FFF4DE",DEEP="#D4B27C";
    if (POSES.indexOf(pose)<0) pose="pro";
    var celebrate=pose==="celebrate", py=pose==="read"?36.2:34.8;
    function arm(d){return "<path d=\""+d+"\" fill=\"none\" stroke=\""+INK+"\" stroke-width=\"10\" stroke-linecap=\"round\"/>"}
    function paw(x,y,r){return "<ellipse cx=\""+x+"\" cy=\""+y+"\" rx=\"7\" ry=\"5.8\" fill=\""+INK+"\" transform=\"rotate("+r+" "+x+" "+y+")\"/>"}
    function star(x,y,s,delay){return "<path class=\"hpp-twinkle\" style=\"animation-delay:"+delay+"s\" transform=\"translate("+x+" "+y+") scale("+s+")\" d=\"M0 -5 L1.2 -1.2 L5 0 L1.2 1.2 L0 5 L-1.2 1.2 L-5 0 L-1.2 -1.2 Z\" fill=\""+GOLD+"\"/>"}
    var eyes=celebrate
      ? "<path d=\"M32 35 q6 -7 12 0\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\"/><path d=\"M56 35 q6 -7 12 0\" fill=\"none\" stroke=\"#fff\" stroke-width=\"3\" stroke-linecap=\"round\"/>"
      : "<circle cx=\"38\" cy=\"34\" r=\"4.8\" fill=\"#fff\"/><circle cx=\"62\" cy=\"34\" r=\"4.8\" fill=\"#fff\"/>"
        +"<circle cx=\"38.6\" cy=\""+py+"\" r=\"2.7\" fill=\""+INK+"\"/><circle cx=\"61.4\" cy=\""+py+"\" r=\"2.7\" fill=\""+INK+"\"/>"
        +"<circle cx=\"39.8\" cy=\""+(py-1.6)+"\" r=\"1.1\" fill=\"#fff\"/><circle cx=\"62.6\" cy=\""+(py-1.6)+"\" r=\"1.1\" fill=\"#fff\"/>"
        +"<rect class=\"hpp-blink\" x=\"32\" y=\"28\" width=\"12\" height=\"12\" rx=\"5\" fill=\""+INK+"\"/><rect class=\"hpp-blink\" x=\"56\" y=\"28\" width=\"12\" height=\"12\" rx=\"5\" fill=\""+INK+"\"/>";
    var mouth=(celebrate||pose==="gift")
      ? "<path d=\"M41 52 q9 11 18 0 q-9 5 -18 0 z\" fill=\""+MOUTH+"\"/><path d=\"M45.5 56.5 q4.5 3.5 9 0 q-4.5 3 -9 0 z\" fill=\""+TONGUE+"\"/>"
      : "<path d=\"M43 53 q7 5 14 0\" stroke=\""+INK+"\" stroke-width=\"2.6\" fill=\"none\" stroke-linecap=\"round\"/>";
    var back="",front="";
    if (pose==="celebrate") {
      back="<path d=\"M30 62 q-15 -7 -17 -23 q6 -6 12 -2 q3 11 11 18 z\" fill=\""+INK+"\"/><path d=\"M70 62 q15 -7 17 -23 q-6 -6 -12 -2 q-3 11 -11 18 z\" fill=\""+INK+"\"/>";
      front=star(10,16,1,0)+star(92,12,.8,.3)+star(52,0,.68,.6);
    } else if (pose==="pro"||pose==="gift") {
      // Both paws present a card from its lower corners: a gold Pro card on
      // the limit screen, a red ticket only for the server-verified offer.
      var gift=pose==="gift";
      back=arm("M31 68 Q24 82 34 88")+arm("M69 68 Q76 82 66 88");
      front="<defs><linearGradient id=\""+uid+"\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"1\">"
        +(gift?"<stop offset=\"0\" stop-color=\"#F0675C\"/><stop offset=\"1\" stop-color=\"#C93A31\"/>"
              :"<stop offset=\"0\" stop-color=\"#F8D376\"/><stop offset=\".55\" stop-color=\"#E9A916\"/><stop offset=\"1\" stop-color=\"#D18C0B\"/>")
        +"</linearGradient></defs>"
        +"<g transform=\"rotate(-4 50 79)\"><rect x=\"30\" y=\"66\" width=\"40\" height=\"24\" rx=\"5\" fill=\"url(#"+uid+")\" stroke=\""+(gift?"#A92E27":"#B9790A")+"\" stroke-width=\"1.2\"/>"
        +"<path d=\"M34 69.6 h32\" stroke=\""+(gift?"#FFC9C2":"#FFF1C4")+"\" stroke-width=\"1.2\" stroke-linecap=\"round\" opacity=\".8\"/>"
        +"<text x=\"50\" y=\"82\" text-anchor=\"middle\" font-size=\""+(gift?"10":"11")+"\" font-weight=\"900\" letter-spacing=\".4\" fill=\""+(gift?"#fff":"#4A3200")+"\" font-family=\"-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif\">"+(gift?"−20%":"PRO")+"</text></g>"
        +paw(34,89,10)+paw(66,88,-10)
        +star(11,22,.7,0)+star(90,18,.56,.45);
    } else if (pose==="read") {
      back=arm("M31 70 Q22 79 31 86")+arm("M69 70 Q78 79 69 86");
      front="<g transform=\"translate(50 82) scale(1.35)\"><path d=\"M-19 -10q10-5 19 1v25q-9-6-19-1Z\" fill=\"#FFF8E8\" stroke=\"#A8782B\" stroke-width=\"1.6\"/>"
        +"<path d=\"M19 -10q-10-5-19 1v25q9-6 19-1Z\" fill=\"#FFF8E8\" stroke=\"#A8782B\" stroke-width=\"1.6\"/><path d=\"M0 -9v25\" stroke=\"#D5A84C\" stroke-width=\"1.2\"/>"
        +"<path d=\"M-15 -4q6-2 11 1M-15 1q6-2 11 1M4 -3q6-3 11-1M4 2q6-3 11-1\" stroke=\"#D9C7A4\" stroke-width=\"1.1\" fill=\"none\" stroke-linecap=\"round\"/></g>"
        +paw(31,86,20)+paw(69,86,-20);
    }
    return "<svg class=\"hpp-char\" viewBox=\"-6 -8 112 116\" width=\"100%\" height=\"100%\" aria-hidden=\"true\" focusable=\"false\">"
      +"<ellipse class=\"hpp-ground\" cx=\"50\" cy=\"102\" rx=\"30\" ry=\"6\" fill=\"#211D17\" opacity=\".16\"/>"
      +"<g class=\"hpp-core "+(celebrate?"hpp-bounce":"hpp-breathe")+"\">"
      +back
      +"<ellipse cx=\"38\" cy=\"97\" rx=\"9.5\" ry=\"6.5\" fill=\""+INK+"\"/><ellipse cx=\"62\" cy=\"97\" rx=\"9.5\" ry=\"6.5\" fill=\""+INK+"\"/>"
      +"<path d=\"M31 96 q-7 -29 9 -40 h23 q17 10 10 40 q-20 10 -42 0 z\" fill=\""+DEEP+"\" opacity=\".34\"/>"
      +"<path d=\"M28 94 q-5 -28 9 -36 h26 q14 8 9 36 q-22 7 -44 0 z\" fill=\""+FACE+"\" stroke=\""+INK+"\" stroke-width=\"3\"/>"
      +"<path d=\"M61 61 q13 10 9 31 q-8 4 -18 5 q10 -13 9 -36 z\" fill=\"#B98442\" opacity=\".34\"/>"
      +"<ellipse cx=\"50\" cy=\"80\" rx=\"14\" ry=\"10.5\" fill=\""+CREAM+"\"/>"
      +"<circle cx=\"27\" cy=\"15\" r=\"12\" fill=\""+INK+"\"/><circle cx=\"73\" cy=\"15\" r=\"12\" fill=\""+INK+"\"/>"
      +"<circle cx=\"27\" cy=\"15\" r=\"5\" fill=\"#4A443C\"/><circle cx=\"73\" cy=\"15\" r=\"5\" fill=\"#4A443C\"/>"
      +"<circle cx=\"50\" cy=\"38\" r=\"30\" fill=\""+FACE+"\" stroke=\""+INK+"\" stroke-width=\"3\"/>"
      +"<path d=\"M61 12 q18 12 17 28 q-1 19 -20 27 q13 -17 3 -55 z\" fill=\""+DEEP+"\" opacity=\".34\"/>"
      +"<ellipse cx=\"40\" cy=\"24\" rx=\"13\" ry=\"8\" fill=\"#fff\" opacity=\".72\"/>"
      +"<ellipse cx=\"38\" cy=\"35\" rx=\"9\" ry=\"12\" fill=\""+INK+"\" transform=\"rotate(-12 38 35)\"/>"
      +"<ellipse cx=\"62\" cy=\"35\" rx=\"9\" ry=\"12\" fill=\""+INK+"\" transform=\"rotate(12 62 35)\"/>"
      +eyes
      +"<ellipse cx=\"50\" cy=\"51\" rx=\"11\" ry=\"8\" fill=\""+CREAM+"\" opacity=\".94\"/>"
      +"<path d=\"M46 46.5 q4 -3 8 0 q-2 4 -4 4 q-2 0 -4 -4 z\" fill=\""+INK+"\"/>"
      +"<path d=\"M50 50 v2.6\" stroke=\""+INK+"\" stroke-width=\"2\" stroke-linecap=\"round\"/>"
      +mouth
      +"<ellipse cx=\"29\" cy=\"46\" rx=\"4.8\" ry=\"3.2\" fill=\""+BLUSH+"\" opacity=\".85\"/><ellipse cx=\"71\" cy=\"46\" rx=\"4.8\" ry=\"3.2\" fill=\""+BLUSH+"\" opacity=\".85\"/>"
      +front
      +"</g></svg>";
  }

  function render(pose){
    pose=POSES.indexOf(pose)>=0?pose:"pro";
    seq+=1;
    return "<div class=\"hpp\" data-pose=\""+pose+"\" aria-hidden=\"true\">"
      +"<span class=\"hpp-halo\"></span>"
      +"<span class=\"hpp-figure\">"+pandaSvg(pose,"hppCard"+seq)+"</span>"
      +"<span class=\"hpp-sparks\"></span></div>";
  }
  function burst(el){
    var host=el&&el.querySelector?(el.classList&&el.classList.contains("hpp")?el:el.querySelector(".hpp")):null;
    var layer=host&&host.querySelector(".hpp-sparks");
    if (!layer||reduced()) return;
    layer.innerHTML="";
    for (var i=0;i<8;i++){
      var s=document.createElement("i");
      s.style.setProperty("--a",(i*45+22.5)+"deg");
      s.style.setProperty("--d",(i%2?46:60)+"px");
      layer.appendChild(s);
    }
    layer.classList.remove("is-on");
    void layer.offsetWidth;
    layer.classList.add("is-on");
    global.setTimeout(function(){layer.classList.remove("is-on");layer.innerHTML="";},900);
  }
  function glint(el){
    if (!el||!el.classList||reduced()) return;
    el.classList.remove("hpp-glint");
    void el.offsetWidth;
    el.classList.add("hpp-glint");
    global.setTimeout(function(){el.classList.remove("hpp-glint");},1100);
  }
  function mount(el,opts){
    if (!el) return null;
    opts=opts||{};
    el.innerHTML=render(opts.pose);
    if (opts.burst) burst(el);
    return el.firstChild;
  }
  global.HSKProPanda={render:render,mount:mount,burst:burst,glint:glint,poses:POSES.slice()};
})(window);
