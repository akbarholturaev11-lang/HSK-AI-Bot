"use strict";
/* No server mocks are compiled into the shipped UI. The harness below tests the
   real browser module under synthetic DOM/network and verifies its transport. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("app/static/course_v3_data/iphone-pwa-feedback.js", "utf8");
const originalCourse = fs.readFileSync("app/static/course-v3.html", "utf8");
const css = fs.readFileSync("app/static/course_v3_data/iphone-pwa-glass.css", "utf8");
assert(originalCourse.includes('src="/course_v3_data/iphone-pwa-feedback.js'));
assert(originalCourse.includes('HskPwaFeedback.open(lessonFeedback)'));
assert(!originalCourse.includes('class="pwa-feedback-button"'),"profile feedback icon is removed");
assert(css.includes("#hsk-pwa-feedback-root[hidden]"));
assert(!source.includes("X-Telegram-Init-Data"));
assert(!source.includes("bot.releaseFeedback.lowRatingComment"),
  "PWA text form must not promise screenshot or discount from validation hint");

class Element {
  constructor(tag = "div") {
    this.tag = tag; this.children = []; this.attributes = {}; this.listeners = {};
    this.hidden = false; this.value = ""; this.textContent = ""; this.tabIndex = 0;
    this.offsetParent = {}; this.isConnected = true;
  }
  appendChild(el) {this.children.push(el);}
  replaceChildren(){this.children = [];}
  setAttribute(k,v){this.attributes[k] = String(v);}
  addEventListener(k,v){this.listeners[k] = v;}
  focus(){}
  querySelector(q) {
    this.selectors ||= new Map();
    if(!this.selectors.has(q))this.selectors.set(q,new Element(q));
    return this.selectors.get(q);
  }
  querySelectorAll(){return Array.from(this.selectors?.values() || []);}
}
function makeHarness({page = "/iphone-pwa/course",ordinary = null,release = [],
                      prepared = null,account = 11} = {}) {
  const requests=[], navigation=[];
  let root, sessionGate = null, resumeSession = null;
  const doc={
    body:{appendChild:(node)=>{root=node;}},
    createElement:(tag)=>new Element(tag),
    activeElement:new Element("focus"),
    addEventListener:()=>{}
  };
  const location={pathname:page,replace:(v)=>navigation.push(v)};
  const window={};
  const routes={
    "/api/v3/pwa/feedback/available": {ok:true,ordinary,release},
    "/api/v3/pwa/feedback/lesson/prepare": {ok:true,ordinary:prepared===null?ordinary:prepared},
    "/api/v3/pwa/feedback/ordinary/prepare": {ok:true,ordinary:prepared===null?ordinary:prepared},
    "/api/v3/pwa/feedback/ordinary/submit": {ok:true,completed:true},
    "/api/v3/pwa/feedback/release/respond": {ok:true,response_id:9}
  };
  async function fetch(url,opt){
    requests.push({url,opt});
    assert.equal(opt.credentials,"same-origin");
    assert.equal(opt.cache,"no-store");
    assert.equal(opt.redirect,"error");
    if(url==="/api/v3/pwa-auth/session"){
      if(sessionGate) await sessionGate;
      return {ok:true,json:async()=>({ok:true,user_id:account,csrf:"csrf-token"})};
    }
    assert(routes[url],"unexpected route " + url);
    if(opt.method==="POST"){
      assert.equal(opt.headers["X-HSK-PWA-CSRF"],"csrf-token");
      assert.equal(opt.headers["Content-Type"],"application/json");
    }
    return {ok:true,json:async()=>routes[url]};
  }
  vm.runInNewContext(source,{
    document:doc,window,location,fetch,
    pwaCourseActor:async()=>({user_id:account}),
    commonMessage:(key)=>key, courseMessage:(key)=>key,
    LANG:"uz",App:{},Number,Promise,Array,String,JSON,Set,setTimeout
  },{filename:"iphone-pwa-feedback.js",timeout:1000});
  return {root:()=>root,window,requests,navigation,
    respond(path, data){routes[path]=data;},
    pauseSession(){sessionGate=new Promise(resolve=>{resumeSession=resolve;});},
    releaseSession(){if(resumeSession)resumeSession();sessionGate=null;resumeSession=null;},
    form:()=>root.querySelector("#hsk-pwa-feedback-form"),
    status:()=>root.querySelector("#hsk-pwa-feedback-status").textContent,
    send:()=>root.querySelector("#hsk-pwa-feedback-submit").listeners.click(),
    selects:()=>root.querySelector("#hsk-pwa-feedback-form").children
      .filter(e=>e.tag==="label"||e.tag==="div")
      .map(e=>({symbol:e.attributes["data-mark"]||e.children[0].textContent,input:e.children[1]})),
    choose(symbol,code){
      // Text variants are buttons (like the bot's inline keyboard), not a select.
      const field=this.selects().find(e=>e.symbol===symbol);
      assert(field,"field missing: " + symbol);
      const option=field.input.children.find(b=>b.attributes["data-code"]===code);
      assert(option,"option missing: " + code);
      assert.equal(option.attributes.role,"radio");
      option.listeners.click();
    },
    type(symbol,text){
      const field=this.selects().find(e=>e.symbol===symbol);
      assert(field,"detail missing for " + symbol);
      assert.equal(field.input.tag,"textarea");
      field.input.value=text;field.input.listeners.input();
    },
    stars:()=>root.querySelector("#hsk-pwa-feedback-form").children[0].children
  };
}
function choices(items) {return items.map(([code,label])=>({code,label}));}
async function main(){
  const lessonContext={confirmed:true,lessonId:3,level:"hsk1"};
  const mini=makeHarness({page:"/course-v3.html"});
  assert.equal(mini.root(),undefined);
  assert.equal(mini.window.HskPwaFeedback,undefined,"Mini App retains its original UX");

  const idle=makeHarness();
  assert(idle.root().hidden,"PWA feedback does not auto-open");
  assert.equal(idle.requests.length,0,"no background feedback reads or writes");

  const none=makeHarness({prepared:null});
  await none.window.HskPwaFeedback.open(lessonContext);
  assert.equal(none.requests.filter(r=>r.url.endsWith("/lesson/prepare")).length,1);
  assert.equal(none.root().hidden,true,"no eligible feedback closes silently instead of showing an empty alert");
  assert.equal(none.root().querySelector("#hsk-pwa-feedback-submit").hidden,true);
  assert.equal(none.requests.filter(r=>r.url.endsWith("/submit")).length,0);
  const contextless=makeHarness({ordinary:{feedback_id:20,paid:false,choices:{}}});
  await contextless.window.HskPwaFeedback.open();
  assert.equal(contextless.requests.length,0,"generic/profile entry cannot trigger feedback");
  assert(contextless.root().hidden);

  const campaignOnly=makeHarness({release:[{
    campaign_id:31,title:"New feature",message_text:"Stored announcement"
  }]});
  await campaignOnly.window.HskPwaFeedback.open(lessonContext);
  assert(campaignOnly.root().hidden,"unrelated feature campaign is not shown as feedback about a lesson");

  const ordinary=makeHarness({ordinary:{
    feedback_id:41,paid:false,choices:{
      liked:choices([["course","Course"],["other","Other"]]),
      liked_sub:{course:choices([["lessons","Lessons"],["other","Other"]])},
      disliked:choices([["price","Price"],["other","Other"]]),
      disliked_detail_required:["other"]
    }
  }});
  await ordinary.window.HskPwaFeedback.open(lessonContext);
  assert.equal(ordinary.root().querySelector("#hsk-pwa-feedback-title").textContent,"pwaFeedback.title");
  const contextRequest=ordinary.requests.find(r=>r.url.endsWith("/lesson/prepare"));
  assert.deepEqual(JSON.parse(contextRequest.opt.body),{lesson_id:3,level:"hsk1"},
    "feedback request is bound to the confirmed lesson context");
  await ordinary.send();
  assert.equal(ordinary.requests.filter(r=>r.url.endsWith("/ordinary/submit")).length,0);
  ordinary.choose("👍","course");
  ordinary.choose("›","lessons");
  ordinary.choose("👎","other");
  await ordinary.send();
  assert.equal(ordinary.requests.filter(r=>r.url.endsWith("/ordinary/submit")).length,0,"mandatory detail");
  ordinary.type("bot.releaseFeedback.commentButton","Better exercises");
  await ordinary.send();
  const freePost=ordinary.requests.filter(r=>r.url.endsWith("/ordinary/submit"));
  assert.equal(freePost.length,1);
  assert.equal(JSON.parse(freePost[0].opt.body).feedback_id,41);
  assert.equal(JSON.parse(freePost[0].opt.body).disliked_detail_text,"Better exercises");

  const partial=makeHarness({ordinary:{
    feedback_id:43,paid:false,liked_code:"course",disliked_code:"price",choices:{
      liked:choices([["course","Course"],["other","Other"]]),
      liked_sub:{course:choices([["lessons","Lessons"]])},
      disliked:choices([["price","Price"],["other","Other"]]),
      disliked_detail_required:["other"]
    }
  }});
  await partial.window.HskPwaFeedback.open(lessonContext);
  assert.equal(partial.selects().find(f=>f.symbol==="👍").input.value,"course");
  assert.equal(partial.selects().find(f=>f.symbol==="👎").input.value,"price");
  partial.choose("›","lessons");
  await partial.send();
  assert.equal(partial.requests.filter(r=>r.url.endsWith("/ordinary/submit")).length,1,
    "previous canonical selections should remain selectable without forcing a change");

  const paid=makeHarness({ordinary:{
    feedback_id:42,paid:true,choices:{
      paid:choices([["worth","Worth it"],["regret","Regret"]]),
      paid_sub_positive:choices([["lessons","Lessons"]]),
      paid_sub_negative:choices([["other","Other"]])
    }
  }});
  await paid.window.HskPwaFeedback.open(lessonContext);
  paid.choose("✓","regret");
  paid.choose("›","other");
  await paid.send();
  assert.equal(paid.requests.filter(r=>r.url.endsWith("/ordinary/submit")).length,0);
  paid.type("bot.releaseFeedback.commentButton","Slow");
  await paid.send();
  const paidPost=paid.requests.filter(r=>r.url.endsWith("/ordinary/submit"));
  assert.equal(paidPost.length,1);
  assert.equal(JSON.parse(paidPost[0].opt.body).paid_sub_code,"other");
  assert.equal(JSON.parse(paidPost[0].opt.body).paid_other_text,"Slow");

  const cancellation = makeHarness({ordinary:{
    feedback_id:45,paid:false,choices:{liked:choices([["course","Course"]]),disliked:choices([["price","Price"]])}
  }});
  await cancellation.window.HskPwaFeedback.open(lessonContext);
  cancellation.choose("👍","course");cancellation.choose("👎","price");
  cancellation.pauseSession();
  const pendingSubmit = cancellation.send();
  await Promise.resolve();
  await Promise.resolve();
  cancellation.window.HskPwaFeedback.close();
  cancellation.releaseSession();
  await pendingSubmit;
  assert.equal(cancellation.requests.filter(r=>r.url.endsWith("/ordinary/submit")).length,0,
    "a closed dialog must not submit after delayed authenticated session");
  await cancellation.window.HskPwaFeedback.open(lessonContext);
  assert.equal(cancellation.root().querySelector("#hsk-pwa-feedback-submit").disabled,false,
    "reopened dialog must not keep stale busy state");
  cancellation.choose("👍","course");cancellation.choose("👎","price");
  await cancellation.send();
  assert.equal(cancellation.requests.filter(r=>r.url.endsWith("/ordinary/submit")).length,1,
    "reopened dialog should still accept its authorized feedback");

  const activity={kind:"practice",level:"hsk1",confirmed:true};
  const canonical={feedback_id:51,paid:false,presentation:"bot",choices:{
    liked:choices([["practice","Practice"],["other","Other"]]),
    liked_sub:{practice:choices([["daily","Daily"],["other","Other"]])},
    disliked:choices([["limits","Limits"],["other","Other"]]),
    disliked_detail_required:["other"]
  }};
  const guided=makeHarness({ordinary:canonical});
  await guided.window.HskPwaFeedback.open(activity);
  assert.equal(guided.selects().length,1,"one bot question at a time");
  assert.deepEqual(JSON.parse(guided.requests.find(r=>r.url.endsWith("/ordinary/prepare")).opt.body),
    {context:{kind:"practice",level:"hsk1"},presentation:"bot"});
  guided.choose("👍","practice");
  assert.equal(guided.selects()[0].symbol,"›");
  guided.window.HskPwaFeedback.back();
  assert.equal(guided.selects()[0].symbol,"👍","back edits the previous answer");
  guided.choose("👍","practice");
  guided.choose("›","daily");
  assert.equal(guided.selects()[0].symbol,"👎");
  guided.choose("👎","limits");
  await new Promise(setImmediate);
  const guidedPost=guided.requests.filter(r=>r.url.endsWith("/ordinary/submit"));
  assert.equal(guidedPost.length,1,"last radio answer saves without extra confirmation");
  assert.equal(JSON.parse(guidedPost[0].opt.body).liked_sub_code,"daily");
  assert.equal(JSON.parse(guidedPost[0].opt.body).disliked_code,"limits");
  assert.equal(JSON.parse(guidedPost[0].opt.body).answer,undefined,"original bot codes are stored");
  guided.window.HskPwaFeedback.back(); // The success state dismisses safely.
  assert(guided.root().hidden);

  const guidedPaid=makeHarness({ordinary:{feedback_id:52,paid:true,presentation:"bot",choices:{
    paid:choices([["useful","Useful"],["regret","Regret"]]),
    paid_sub_positive:choices([["lessons","Lessons"]]),
    paid_sub_negative:choices([["other","Other"]])
  }}});
  await guidedPaid.window.HskPwaFeedback.open({...activity,kind:"voice"});
  assert.equal(guidedPaid.selects()[0].symbol,"✓");
  guidedPaid.choose("✓","useful");
  guidedPaid.choose("›","lessons");
  await new Promise(setImmediate);
  assert.equal(JSON.parse(guidedPaid.requests.find(r=>r.url.endsWith("/ordinary/submit")).opt.body).paid_code,"useful");

  const details=makeHarness({ordinary:canonical});
  await details.window.HskPwaFeedback.open(activity);
  details.choose("👍","other");
  assert(details.root().querySelector("#hsk-pwa-feedback-submit").disabled);
  details.type("bot.releaseFeedback.commentButton","Vocabulary");
  await details.send();
  assert.equal(details.selects()[0].symbol,"👎");
  details.choose("👎","other");
  details.type("bot.releaseFeedback.commentButton","Audio failed");
  details.respond("/api/v3/pwa/feedback/ordinary/submit",{ok:false,error:"temporary"});
  await details.send();
  assert.equal(details.status(),"subscriptionPage.error");
  assert.equal(details.selects()[0].input.value,"Audio failed","failed writes retain text");
  details.respond("/api/v3/pwa/feedback/ordinary/submit",{ok:true,completed:true});
  await details.send();
  const attempts=details.requests.filter(r=>r.url.endsWith("/ordinary/submit"));
  assert.equal(attempts.length,2);
  assert.equal(attempts[0].opt.body,attempts[1].opt.body,"retry preserves the complete answer");
  console.log("PWA feedback UI: 13 contextual/authentication/bot questionnaire scenarios passed");
}
main().catch(err=>{console.error(err);process.exitCode=1;});
