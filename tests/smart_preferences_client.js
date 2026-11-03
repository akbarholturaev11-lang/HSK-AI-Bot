// Exercise the actual nonblocking Mini App consumer, without a copied implementation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('app/static/course-v3.html', 'utf8');
const start = html.indexOf('/* D29 Smart zone bootstrap:');
const end = html.indexOf('/* End D29 Smart zone bootstrap. */', start);
assert(start > 0 && end > start);
const source = html.slice(start, end);
const id = '11111111-2222-4333-8444-555555555555';
const initial = {ok:true,revision:0,time_mode:'auto',timezone_name:null,master_enabled:false};
let checks = 0;
function fixture(pref=initial, options={}) {
  const calls=[];
  const context={INIT_DATA:'signed-synthetic',Promise,Number,AbortController,setTimeout,clearTimeout,
    Intl:{DateTimeFormat:()=>({resolvedOptions:()=>({timeZone:'Asia/Tashkent'})})},
    window:{crypto:{randomUUID:()=>id}},
    fetch:async(url,opts)=>{
      calls.push({url,opts});
      if(options.handler)return options.handler(url,opts);
      if(options.fail)throw new Error('synthetic offline');
      if(opts.method==='PATCH')return {ok:!options.conflict,json:async()=>({ok:true,request_id:id,applied_revision:1,dispatch_allowed:false})};
      return {ok:true,json:async()=>pref};
    }};
  vm.createContext(context);vm.runInContext(source,context);
  return {context,calls,run:()=>context._ensureSmartTimezone()};
}
(async()=>{
  const first=fixture();assert.equal(await first.run(),true);checks++;
  assert.equal(first.calls.length,2);checks++;
  const patch=first.calls[1];assert.equal(patch.url,'/api/v3/smart-reminder/preferences');
  assert.deepEqual(JSON.parse(patch.opts.body),{request_id:id,expected_revision:0,timezone_name:'Asia/Tashkent'});checks++;
  for(const call of first.calls){
    assert.equal(call.opts.headers['X-Telegram-Init-Data'],'signed-synthetic');
    assert.equal(call.opts.cache,'no-store');assert.equal(call.opts.credentials,'omit');assert.equal(call.opts.redirect,'error');
  }checks++;
  assert.equal(initial.master_enabled,false);assert.equal(await first.run(),false);assert.equal(first.calls.length,2);checks++;
  for(const pref of [
    {...initial,timezone_name:'Asia/Tokyo',time_mode:'manual_locked'},
    {...initial,timezone_name:'Asia/Tokyo'},
  ]){const f=fixture(pref);assert.equal(await f.run(),true);assert.equal(f.calls.length,1);checks++;}
  for(const pref of [
    {...initial,ok:'true'}, {...initial,revision:'0'}, {...initial,revision:-1},
    {...initial,time_mode:'unknown'}, {...initial,timezone_name:undefined},
    {...initial,time_mode:'manual_locked'},
  ]){const f=fixture(pref);assert.equal(await f.run(),false);assert.equal(f.calls.length,1);checks++;}
  const anonymous=fixture();anonymous.context.INIT_DATA='';assert.equal(await anonymous.run(),false);assert.equal(anonymous.calls.length,0);checks++;
  const offline=fixture(initial,{fail:true});assert.equal(await offline.run(),false);checks++;
  const conflict=fixture(initial,{conflict:true});assert.equal(await conflict.run(),false);assert.equal(conflict.calls.length,2);checks++;
  const parallel=fixture();const p=parallel.run();assert.equal(parallel.run(),p);await p;assert.equal(parallel.calls.length,2);checks++;
  let release;
  const switched=fixture(initial,{handler:()=>new Promise(resolve=>{release=resolve})});
  const pending=switched.run();switched.context.INIT_DATA='different-signed-session';
  release({ok:true,json:async()=>initial});assert.equal(await pending,false);assert.equal(switched.calls.length,1);checks++;
  const mapCode=html.slice(html.indexOf('function loadCourseMap(lv,tries){'),html.indexOf('function _retryCourseMap(',html.indexOf('function loadCourseMap(lv,tries){')));
  for(const allowed of [false,'true',true]){
    let finish;
    const f=fixture(initial,{handler:()=>new Promise(resolve=>{finish=()=>resolve({ok:false})})});
    f.context._fetchCourseMap=async()=>({_status:200,units:[{}],smart_preferences_available:allowed});
    f.context.isHsk30AccessError=()=>false;
    vm.runInContext(mapCode,f.context);
    const result=await f.context.loadCourseMap('hsk1');
    assert.equal(result.data.units.length,1);
    assert.equal(f.calls.length,allowed===true?1:0);checks++;
    if(finish){const pending=f.context._SMART_ZONE_PENDING.promise;finish();await pending;}
  }
  console.log(`SMART_PREFERENCES_CLIENT_PASS checks=${checks}`);
})().catch(error=>{console.error(error);process.exitCode=1});
