/* HSK AI "Knot Thread" launch mark — a candidate minimalist opening effect.
 *
 * The two gold strands of the real HSK AI knot (branding/hsk-ai-logo.svg) are
 * drawn as one continuous thread, they weave at the crossings, one gold glint
 * crosses the seal and the wordmark settles. ~1.15 s, one play, no sound.
 *
 * Standalone and NOT wired into the app: the shipped "Golden Logo" splash in
 * course-v3.html / Android HskBrandLoader stays authoritative until the owner
 * approves a swap (see docs/design/LAUNCH_MARK_AND_PRO_PANDA.md).
 *
 * API: HSKLaunchMark.mount(el, {onDone}) -> {skip()}; HSKLaunchMark.TIMELINE.
 * prefers-reduced-motion: the finished mark is shown at once and onDone fires
 * on the next frame. Styles: /assets/brand/hsk-launch-mark.css
 */
(function(global){
  "use strict";
  if (global.HSKLaunchMark) return;
  // Shared with Android HskLaunchMark.kt (LaunchMarkTimeline). Keep in sync.
  var TIMELINE={seal:[0,260],strandA:[140,420],strandB:[260,420],weave:[640,80],glint:[760,300],word:[820,280],total:1150};
  var seq=0;
  var A="M39.5,35 H68.5 A4.5,4.5 0 0 1 73,39.5 V68.5 A4.5,4.5 0 0 1 68.5,73 H39.5 A4.5,4.5 0 0 1 35,68.5 V39.5 A4.5,4.5 0 0 1 39.5,35 Z";
  var B="M57.18,30.31 L77.69,50.82 A4.5,4.5 0 0 1 77.69,57.18 L57.18,77.69 A4.5,4.5 0 0 1 50.82,77.69 L30.31,57.18 A4.5,4.5 0 0 1 30.31,50.82 L50.82,30.31 A4.5,4.5 0 0 1 57.18,30.31 Z";
  var X="M39.5,35 H52.9 M73,39.5 V52.9 M68.5,73 H55.1 M35,68.5 V55.1";

  function reduced(){
    try { return !!(global.matchMedia && global.matchMedia("(prefers-reduced-motion: reduce)").matches); }
    catch (_) { return false; }
  }
  function strand(d,cls,cin,gold,len){
    var pl=len?" pathLength=\"100\"":"";
    return "<g class=\""+cls+"\"><path d=\""+d+"\""+pl+" stroke=\"url(#"+cin+")\" stroke-width=\"9.5\"/>"
      +"<path d=\""+d+"\""+pl+" stroke=\"url(#"+gold+")\" stroke-width=\"6\"/></g>";
  }
  function markup(){
    seq+=1;
    var cin="hlmCin"+seq,gold="hlmGold"+seq,clip="hlmClip"+seq,shine="hlmShine"+seq;
    return "<div class=\"hlm-stage\">"
      +"<svg class=\"hlm-seal\" viewBox=\"0 0 108 108\" aria-hidden=\"true\" focusable=\"false\"><defs>"
      +"<linearGradient id=\""+cin+"\" x1=\"0\" y1=\"0\" x2=\"108\" y2=\"108\" gradientUnits=\"userSpaceOnUse\"><stop offset=\"0\" stop-color=\"#F0614C\"/><stop offset=\"1\" stop-color=\"#C02F32\"/></linearGradient>"
      +"<linearGradient id=\""+gold+"\" x1=\"0\" y1=\"28\" x2=\"0\" y2=\"80\" gradientUnits=\"userSpaceOnUse\"><stop offset=\"0\" stop-color=\"#F7C948\"/><stop offset=\"1\" stop-color=\"#D9920F\"/></linearGradient>"
      +"<linearGradient id=\""+shine+"\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"0\"><stop offset=\"0\" stop-color=\"#FFF2C4\" stop-opacity=\"0\"/><stop offset=\".5\" stop-color=\"#FFF2C4\" stop-opacity=\".75\"/><stop offset=\"1\" stop-color=\"#FFF2C4\" stop-opacity=\"0\"/></linearGradient>"
      +"<clipPath id=\""+clip+"\"><rect width=\"108\" height=\"108\" rx=\"22\"/></clipPath></defs>"
      +"<g clip-path=\"url(#"+clip+")\"><rect class=\"hlm-bg\" width=\"108\" height=\"108\" rx=\"22\" fill=\"url(#"+cin+")\"/>"
      +"<g fill=\"none\" stroke-linejoin=\"round\" stroke-linecap=\"round\">"
      +strand(A,"hlm-a",cin,gold,true)+strand(B,"hlm-b",cin,gold,true)+strand(X,"hlm-x",cin,gold,false)+"</g>"
      +"<g transform=\"skewX(-18)\"><rect class=\"hlm-glint\" x=\"-40\" y=\"-20\" width=\"34\" height=\"148\" fill=\"url(#"+shine+")\"/></g></g></svg>"
      +"<div class=\"hlm-word\">HSK <b>AI</b></div></div>";
  }
  function mount(el,opts){
    opts=opts||{};
    var done=false,timer=null;
    function finish(){
      if (done) return;
      done=true;
      if (timer) global.clearTimeout(timer);
      if (el) el.classList.add("is-done");
      if (typeof opts.onDone==="function") opts.onDone();
    }
    if (!el) return {skip:function(){}};
    el.classList.add("hlm");
    el.setAttribute("role","img");
    el.setAttribute("aria-label","HSK AI");
    el.innerHTML=markup();
    if (reduced()) {
      el.classList.add("is-static");
      (global.requestAnimationFrame||global.setTimeout)(finish);
    } else {
      el.classList.add("is-playing");
      timer=global.setTimeout(finish,TIMELINE.total);
    }
    return {skip:finish};
  }
  global.HSKLaunchMark={mount:mount,TIMELINE:TIMELINE};
})(window);
