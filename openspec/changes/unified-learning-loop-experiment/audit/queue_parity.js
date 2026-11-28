// Actual course-v3 queue projection, no UI/network/DB or content output.
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const root=process.cwd(),base=process.argv[2]||'/tmp/hsk-learning-queue-audit';
const html=fs.readFileSync('app/static/course-v3.html','utf8');
const queue=html.slice(html.indexOf('function lessonMaterialRef('),html.indexOf('/* N1 pilot transfer questions'));
const helpers=html.slice(html.indexOf('function lessonPlanOf('),html.indexOf('/* Navbat qoidasi:'));
const ctx=vm.createContext({LANG:'uz',PIC_REVIEW_MAX:10,MAP:{},normalizeLevel:x=>x,flowLessonOrder:()=>0,secNames:()=>[],courseMessage:(k,f)=>f});
vm.runInContext('function tr(v){return v&&typeof v==="object"?(v[LANG]||v.uz||""):String(v||"")};'+helpers+queue,ctx);
const cache=new Map();let checked=0,protectedErrors=0;
const records=JSON.parse(fs.readFileSync(base+'/planner-records.json'));
for(const r of records){
 const key=r.level+'/'+r.n;
 if(!cache.has(key))cache.set(key,JSON.parse(fs.readFileSync(`app/static/course_v3_data/${r.level}/lesson_${String(r.n).padStart(2,'0')}.json`)));
 const lesson=cache.get(key);
 for(const lang of ['uz','ru','tj']){
  ctx.LANG=lang;lesson.lesson_plan=r.plan;
  const q=ctx.buildQueue(lesson,{});
  const types=Array.from(q,c=>c.type);
  assert.deepEqual(types,r.expected_types,`${key}:${r.minutes}:${r.goal}:${lang}:types`);
  const refs=Array.from(q.filter(c=>c._materialRef),c=>[c._materialRef,c.type]);
  assert.deepEqual(refs,r.expected_ref_types,`${key}:${r.minutes}:${r.goal}:${lang}:refs`);
  checked++;
 }
}
console.log(JSON.stringify({actual_queue_checks:checked,parts:cache.size,languages:['uz','ru','tj'],configurations:records.length,passed:true,limits:'Function execution with catalog-label stubs; no UI, provider, auth, DB or physical-device acceptance.'},null,2));
