/* HSK AI nav-only Liquid Glass pilot. No changes to routing, auth or course flow.
 * Requires locally hosted MIT assets: html2canvas.min.js, container.js.
 * Enabled only from /course-v3?liquid_glass=1; regular users remain untouched. */
(function(){
  'use strict';
  var nav=document.getElementById('nav');
  if(!nav || typeof Container!=='function' || typeof html2canvas!=='function')return;
  if(window.matchMedia && window.matchMedia('(prefers-reduced-transparency: reduce)').matches)return;
  var status={enabled:false,reason:'initializing',captures:0};
  window.HSKNavLiquidGlassPilot=status;
  var probe=document.createElement('canvas');
  var probeGL;
  try{probeGL=probe.getContext('webgl',{failIfMajorPerformanceCaveat:true})}catch(e){}
  if(!probeGL){status.reason='webgl-unavailable';return}
  var glass;
  try{
    glass=new Container({type:'pill',borderRadius:36,tintOpacity:0.12});
    glass.element.classList.add('hsk-lg-surface');
    glass.element.setAttribute('aria-hidden','true');
    nav.insertBefore(glass.element,nav.firstChild);
    glass.updateSizeFromDOM();
  }catch(e){status.reason='init-failed';return}
  var watchdog=window.setInterval(function(){
    if(glass.webglInitialized && glass.gl_refs && glass.gl_refs.gl){
      window.clearInterval(watchdog);
      nav.classList.add('hsk-lg-active');
      status.enabled=true;status.reason='ready';
      scheduleRefresh(550);
    }
  },100);
  window.setTimeout(function(){
    if(status.enabled)return;
    window.clearInterval(watchdog);
    if(glass.element && glass.element.parentNode)glass.element.remove();
    status.reason='snapshot-or-shader-unavailable';
  },5000);
  glass.canvas.addEventListener('webglcontextlost',function(e){
    e.preventDefault();
    nav.classList.remove('hsk-lg-active');
    status.enabled=false;status.reason='webgl-context-lost';
  });
  var refreshTimer=0,refreshing=false,lastCapture=0;
  function ignoreElement(element){
    return element.id==='nav'||element.id==='hsk-launch-splash'||
      element.classList.contains('glass-container')||
      element.classList.contains('glass-button')||
      element.classList.contains('glass-button-text');
  }
  function scheduleRefresh(delay){
    if(!status.enabled||document.visibilityState==='hidden')return;
    window.clearTimeout(refreshTimer);
    refreshTimer=window.setTimeout(refresh,delay||420);
  }
  function refresh(){
    if(!status.enabled||refreshing||document.visibilityState==='hidden')return;
    if(Date.now()-lastCapture<1100){scheduleRefresh(1100-(Date.now()-lastCapture));return}
    refreshing=true;lastCapture=Date.now();
    html2canvas(document.body,{
      scale:1,width:window.innerWidth,height:window.innerHeight,
      windowWidth:window.innerWidth,windowHeight:window.innerHeight,
      useCORS:true,allowTaint:false,backgroundColor:null,
      logging:false,ignoreElements:ignoreElement
    }).then(function(snapshot){
      return new Promise(function(resolve,reject){
        var image=new Image();
        image.onload=function(){resolve(image)};
        image.onerror=reject;
        try{image.src=snapshot.toDataURL('image/png')}catch(e){reject(e)}
      });
    }).then(function(image){
      if(!status.enabled)return;
      var r=glass.gl_refs,g=r.gl;
      if(!g||!r.texture)return;
      g.activeTexture(g.TEXTURE0);
      g.bindTexture(g.TEXTURE_2D,r.texture);
      g.texImage2D(g.TEXTURE_2D,0,g.RGBA,g.RGBA,g.UNSIGNED_BYTE,image);
      g.uniform2f(r.textureSizeLoc,image.width,image.height);
      g.uniform1f(r.pageHeightLoc,image.height);
      g.uniform1f(r.viewportHeightLoc,window.innerHeight);
      glass.render();
      status.captures++;
    }).catch(function(){
      /* Snapshot error is non-fatal; the old snapshot and original nav remain usable. */
      status.reason='refresh-failed';
    }).then(function(){refreshing=false});
  }
  nav.addEventListener('click',function(e){
    if(e.target.closest('button[data-s]'))scheduleRefresh(700);
  },{passive:true});
  document.querySelectorAll('.scr').forEach(function(screen){
    screen.addEventListener('scroll',function(){scheduleRefresh(430)},{passive:true});
  });
  window.addEventListener('resize',function(){
    glass.updateSizeFromDOM();
    window.requestAnimationFrame(function(){if(status.enabled)glass.render()});
    scheduleRefresh(620);
  },{passive:true});
  window.addEventListener('pageshow',function(e){if(e.persisted)scheduleRefresh(400)});
  document.addEventListener('visibilitychange',function(){
    if(document.visibilityState==='visible')scheduleRefresh(550);
  });
  status.refresh=function(){scheduleRefresh(20)};
})();
