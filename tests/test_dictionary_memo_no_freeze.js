const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("app/static/hsk-lugat.html","utf8");
const start=source.indexOf("  function renderMemo(word){");
const end=source.indexOf("  function renderExample(word){",start);
assert(start>0&&end>start,"renderMemo source must exist");
const active={h:"学习",lv:"N1"},memoBlock={innerHTML:""};
let requests=0;
const ctx={
  window:{},currentWord:active,
  document:{getElementById:id=>id==="memo-block"?memoBlock:null},
  hsk30MemoryFallback:()=>"<div>offline fallback</div>",
  loadMemoData:()=>{requests++;return {then(callback){callback();}}},
  memoLabels:{uz:{}},currentLang:"uz",memoText:()=>"",escapeHtml:v=>v
};
vm.createContext(ctx);
vm.runInContext(source.slice(start,end),ctx);
ctx.renderMemo(active);
assert.equal(requests,1,"missing memo.js must not schedule infinite Promise microtask recursion");
assert.equal(memoBlock.innerHTML,"<div>offline fallback</div>");
ctx.window.MEMO_DATA={};
ctx.renderMemo(active);
assert.equal(requests,1,"loaded memo data must not schedule another download");
assert.equal(memoBlock.innerHTML,"<div>offline fallback</div>");
console.log("Dictionary memo fallback: no promise retry loop, data-safe fallback PASS.");
