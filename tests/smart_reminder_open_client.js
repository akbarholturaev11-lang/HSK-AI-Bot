// Execute the actual inline consumer; do not mirror its implementation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('app/static/course-v3.html', 'utf8');
const start = html.indexOf('(function observeSmartReminderOpen(){');
const end = html.indexOf('// End smart reminder open observation.', start);
assert(start > 0 && end > start);
const code = html.slice(start, end);
const job = '11111111-2222-3333-4444-555555555555';
const proof = 'a'.repeat(64);
let checks = 0;
function run({source='smart_study', fragment=`smart_job=${job}&smart_proof=${proof}`, auth='signed-synthetic', visible=true, fail=false}={}) {
  const calls = [], listeners = new Set();
  const document = {visibilityState:visible?'visible':'hidden',
    addEventListener:(_,fn)=>listeners.add(fn), removeEventListener:(_,fn)=>listeners.delete(fn)};
  const location = {search:'?source='+source, hash:'#'+fragment};
  vm.runInNewContext(code, {URLSearchParams, INIT_DATA:auth, location, document,
    fetch:(url, options)=>{calls.push({url,options}); return fail?Promise.reject(new Error('synthetic network')):Promise.resolve({ok:true})}});
  return {calls,document,location,listeners,show(){document.visibilityState='visible';for(const fn of [...listeners])fn()}};
}
const live = run();
assert.equal(live.calls.length,1); checks++;
const call = live.calls[0];
assert.equal(call.url,`/api/v3/smart-reminder/jobs/${job}/open`);
assert.deepEqual(JSON.parse(call.options.body),{version:1,proof}); checks++;
assert.equal(call.options.headers['X-Telegram-Init-Data'],'signed-synthetic'); checks++;
assert.equal(call.options.credentials,'omit'); assert.equal(call.options.redirect,'error'); checks++;
live.show(); live.show(); assert.equal(live.calls.length,1); checks++;
assert.equal(live.location.hash,`#smart_job=${job}&smart_proof=${proof}`); checks++;
const hidden = run({visible:false}); assert.equal(hidden.calls.length,0); hidden.show();assert.equal(hidden.calls.length,1);checks++;
for(const options of [
  {auth:''}, {source:'widget'}, {fragment:''}, {source:'smart_study&source=smart_study'},
  {fragment:`smart_job=${job}&smart_job=${job}&smart_proof=${proof}`},
  {fragment:`smart_job=${job}&smart_proof=${proof}&smart_proof=${proof}`},
  {fragment:`smart_job=invalid&smart_proof=${proof}`}, {fragment:`smart_job=${job}&smart_proof=${proof.toUpperCase()}`},
]) {assert.equal(run(options).calls.length,0);checks++;}
const extra = run({fragment:`smart_job=${job}&smart_proof=${proof}&tgWebAppData=keep%26unchanged`});
assert.equal(extra.calls.length,1);assert(extra.location.hash.endsWith('tgWebAppData=keep%26unchanged'));checks++;
run({fail:true}).show();checks++;
console.log(`SMART_OPEN_CLIENT_PASS checks=${checks}`);
