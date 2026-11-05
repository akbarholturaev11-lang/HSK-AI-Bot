// Standalone deterministic DOM regression for the HSK AI dictionary.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("app/static/hsk-lugat.html", "utf8");
const marker = "  /* Render a bounded DOM window";
const start = source.indexOf(marker), end = source.indexOf("  /* ---------- stroke-order writer", start);
assert(start > 0 && end > start, "virtual window must be in the shipping dictionary");
const code = source.slice(start, end);
const fake = {
  clientHeight: 600, scrollTop: 0, innerHTML: "",
  addEventListener(type, fn) { this[type] = fn; }
};
const searchEl = {value:""};
const countEl = {textContent:"", setAttribute(){}};
const clear = {classList:{toggle(){}}};
let frame = null;
const words = Array.from({length:2400}, (_, i) => ({
  id:i, h:i===1377?"学习":"词"+i, p:i===1377?"xuéxí":"ci"+i,
  m:{uz:i===1377?"o'rganmoq":"so'z"+i},
  lv:"HSK1", _p:i===1377?"xuexi":"ci"+i,
  _m:i===1377?"o'rganmoq":"so'z"+i,
}));
const ctx = {
  listEl:fake, listResults:[],activeWords:words,searchEl,countEl,searchClear:clear,
  currentLang:"uz",UI:{uz:{emptyTitle:"No words",emptySub:"Try again",countResults:n=>n+" results",countAll:n=>n+" words"}},
  filterCountLabel:()=>"All", text:m=>m.uz,formatDictionaryLevel:lv=>lv,
  normPinyin:v=>v.toLowerCase(),escapeHtml:v=>String(v).replaceAll("&","&amp;").replaceAll("<","&lt;"),
  requestAnimationFrame:fn=>{frame=fn;return 1},
  window:{addEventListener(){}}
};
vm.createContext(ctx);
vm.runInContext(code,ctx,{filename:"hsk-lugat.html:dictionary-virtual-list"});
const rows = () => (fake.innerHTML.match(/class="row"/g)||[]).length;
ctx.renderList("");
assert.equal(countEl.textContent,"2400");
assert(rows()<=90 && rows()>0,"first paint bounded by window size");
assert(fake.innerHTML.includes('data-idx="0"'));
fake.scrollTop=88*1100;
fake.scroll();assert(frame,"scroll schedules one animation frame");frame();frame=null;
assert(rows()<=90,"scroll viewport does not construct thousands of nodes");
assert(fake.innerHTML.includes('data-idx="1100"'));
fake.scrollTop=88*2375;fake.scroll();frame();frame=null;
assert(fake.innerHTML.includes('data-idx="2399"'),"last word stays reachable");
assert(rows()<=90,"tail viewport bounded");
searchEl.value="学习";ctx.renderList(searchEl.value);
assert.equal(countEl.textContent,"1");
assert(fake.innerHTML.includes('data-idx="1377"'));
searchEl.value="xuexi";ctx.renderList(searchEl.value);
assert.equal(countEl.textContent,"1","pinyin search unchanged");
searchEl.value="o'rganmoq";ctx.renderList(searchEl.value);
assert.equal(countEl.textContent,"1","translation search unchanged");
searchEl.value="not-a-word";ctx.renderList(searchEl.value);
assert.equal(countEl.textContent,"0");
assert(fake.innerHTML.includes("No words"));
assert.equal(source.split("\n").length,1936,"frozen source line anchors preserved");
assert(source.includes("overflow-anchor:none"),"scroll anchoring cannot fight viewport replacement");
assert(source.includes("listEl.scrollTop = scrollPos; renderVisibleWindow(true);"),"detail return repaints original position");
console.log("Dictionary virtual list: 2400 words, bounded DOM, tail scroll, Chinese/pinyin/translation queries, empty results and back position PASS.");
