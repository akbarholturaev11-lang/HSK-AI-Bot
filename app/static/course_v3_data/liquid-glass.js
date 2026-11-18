/* PWA bottom navigation: SVG pixel refraction of the shared scene wallpaper.
 * This is not an Apple native material nor refraction of arbitrary DOM content.
 * Exactly one small surface; the existing CSS blur is the safe fallback.
 */
const safari = /iP(hone|ad|od)/.test(navigator.userAgent) ||
  (/Safari\//.test(navigator.userAgent) && !/Chrome|Chromium|CriOS|Edg|OPR|Android/.test(navigator.userAgent));

export function liquidGlass(wall, selector) {
  if (!wall || !document.documentElement.classList.contains("hsk-pwa-browser")) return false;
  const nav = document.querySelector(selector);
  if (!nav || !window.SVGFEDisplacementMapElement || !window.ResizeObserver) return false;
  if (matchMedia("(prefers-reduced-transparency: reduce)").matches ||
      (navigator.connection && navigator.connection.saveData) ||
      (typeof navigator.deviceMemory === "number" && navigator.deviceMemory <= 2)) return false;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("width", "0");
  svg.setAttribute("height", "0");
  svg.style.cssText = "position:absolute;overflow:hidden;pointer-events:none";
  svg.innerHTML = '<defs><filter id="hsk-pwa-nav-refraction" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB">' +
    '<feGaussianBlur in="SourceAlpha" stdDeviation="5" result="edge"/>' +
    '<feDiffuseLighting in="edge" surfaceScale="7" diffuseConstant=".7071" result="lightX"><feDistantLight azimuth="0" elevation="45"/></feDiffuseLighting>' +
    '<feDiffuseLighting in="edge" surfaceScale="7" diffuseConstant=".7071" result="lightY"><feDistantLight azimuth="90" elevation="45"/></feDiffuseLighting>' +
    '<feColorMatrix in="lightX" values="1 0 0 0 0 0 0 0 0 0 0 0 0 0 .5 0 0 0 0 1" result="r"/>' +
    '<feColorMatrix in="lightY" values="0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 1" result="g"/>' +
    '<feComposite in="r" in2="g" operator="arithmetic" k2="1" k3="1" result="map"/>' +
    '<feDisplacementMap in="SourceGraphic" in2="map" scale="' + (safari ? 26 : -26) + '" xChannelSelector="R" yChannelSelector="G"/>' +
    '<feColorMatrix type="saturate" values="1.25"/></filter></defs>';
  const layer = document.createElement("span");
  layer.className = "hsk-pwa-liquid-refraction";
  layer.setAttribute("aria-hidden", "true");
  nav.insertBefore(layer, nav.firstChild);
  document.body.appendChild(svg);
  nav.classList.add("hsk-pwa-liquid-on");

  let frame = 0;
  function paint() {
    frame = 0;
    if (!wall.isConnected || !nav.isConnected) return;
    const w = wall.getBoundingClientRect();
    const r = nav.getBoundingClientRect();
    const bg = getComputedStyle(wall).backgroundImage;
    if (bg === "none" || !w.width || !w.height || !r.width || !r.height) return;
    layer.style.setProperty("--lg-image", bg);
    layer.style.setProperty("--lg-size", w.width + "px " + w.height + "px");
    layer.style.setProperty("--lg-position", (w.left - r.left) + "px " + (w.top - r.top) + "px");
  }
  function schedule() {
    if (!frame) frame = requestAnimationFrame(paint);
  }
  const observer = new ResizeObserver(schedule);
  observer.observe(wall);
  observer.observe(nav);
  const themeObserver = new MutationObserver(schedule);
  themeObserver.observe(document.documentElement, {attributes:true,attributeFilter:["data-hsk-theme"]});
  addEventListener("resize", schedule, {passive:true});
  addEventListener("orientationchange", schedule, {passive:true});
  if (window.visualViewport) window.visualViewport.addEventListener("resize", schedule, {passive:true});
  schedule();
  return true;
}
