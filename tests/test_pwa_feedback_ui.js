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
assert(originalCourse.includes('window.HskPwaFeedback&&window.HskPwaFeedback.open()'));
assert(css.includes("#hsk-pwa-feedback-root[hidden]"));
assert(!source.includes("X-Telegram-Init-Data"));

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
  let root;
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
    "/api/v3/pwa/feedback/ordinary/prepare": {ok:true,ordinary:prepared},
    "/api/v3/pwa/feedback/ordinary/submit": {ok:true,completed:true},
    "/api/v3/pwa/feedback/release/respond": {ok:true,response_id:9}
  };
  async function fetch(url,opt){
    requests.push({url,opt});
    assert.equal(opt.credentials,"same-origin");
    assert.equal(opt.cache,"no-store");
    assert.equal(opt.redirect,"error");
    if(url==="/api/v3/pwa-auth/session")return {ok:true,json:async()=>({ok:true,user_id:account,csrf:"csrf-token"})};
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
    LANG:"uz",App:{},Number,Promise,Array,String,JSON,Set
  },{filename:"iphone-pwa-feedback.js",timeout:1000});
  return {root:()=>root,window,requests,navigation,
    form:()=>root.querySelector("#hsk-pwa-feedback-form"),
    status:()=>root.querySelector("#hsk-pwa-feedback-status").textContent,
    send:()=>root.querySelector("#hsk-pwa-feedback-submit").listeners.click(),
    selects:()=>root.querySelector("#hsk-pwa-feedback-form").children
      .filter(e=>e.tag==="label").map(e=>({symbol:e.children[0].textContent,input:e.children[1]})),
    choose(symbol,code){
      const field=this.selects().find(e=>e.symbol===symbol);
      assert(field,"field missing: " + symbol);
      assert.equal(field.input.tag,"select");
      field.input.value=code;field.input.listeners.change();
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
  const mini=makeHarness({page:"/course-v3.html"});
  assert.equal(mini.root(),undefined);
  assert.equal(mini.window.HskPwaFeedback,undefined,"Mini App retains its original UX");

  const idle=makeHarness();
  assert(idle.root().hidden,"PWA feedback does not auto-open");
  assert.equal(idle.requests.length,0,"no background feedback reads or writes");

  const none=makeHarness({prepared:null});
  await none.window.HskPwaFeedback.open();
  assert.equal(none.requests.filter(r=>r.url.endsWith("/ordinary/prepare")).length,1);
  assert.equal(none.root().querySelector("#hsk-pwa-feedback-submit").hidden,true);
  assert(none.status().includes("notFoundAlert"));
  assert.equal(none.requests.filter(r=>r.url.endsWith("/submit")).length,0);

  const campaign=makeHarness({release:[{
    campaign_id:31,title:"New feature",message_text:"Stored announcement"
  }]});
  await campaign.window.HskPwaFeedback.open();
  assert.equal(campaign.root().querySelector("#hsk-pwa-feedback-title").textContent,"New feature");
  assert.equal(campaign.stars().length,5);
  await campaign.send();
  assert.equal(campaign.requests.filter(r=>r.url.endsWith("/respond")).length,0,"rating required");
  campaign.stars()[0].listeners.click();
  await campaign.send();
  assert.equal(campaign.requests.filter(r=>r.url.endsWith("/respond")).length,0,"1-star rating requires comment");
  campaign.type("bot.releaseFeedback.commentButton","An issue");
  await campaign.send();
  const releasePost=campaign.requests.filter(r=>r.url.endsWith("/respond"));
  assert.equal(releasePost.length,1);
  assert.equal(JSON.parse(releasePost[0].opt.body).rating,1);
  assert.equal(JSON.parse(releasePost[0].opt.body).campaign_id,31);
  assert.equal(campaign.status(),"bot.releaseFeedback.thanks");
  await campaign.send();
  assert.equal(campaign.requests.filter(r=>r.url.endsWith("/respond")).length,1,"success cannot resubmit");

  const ordinary=makeHarness({ordinary:{
    feedback_id:41,paid:false,choices:{
      liked:choices([["course","Course"],["other","Other"]]),
      liked_sub:{course:choices([["lessons","Lessons"],["other","Other"]])},
      disliked:choices([["price","Price"],["other","Other"]]),
      disliked_detail_required:["other"]
    }
  }});
  await ordinary.window.HskPwaFeedback.open();
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
  await partial.window.HskPwaFeedback.open();
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
  await paid.window.HskPwaFeedback.open();
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

  console.log("PWA feedback UI: 8 authorization/ordinary/release/validation scenarios passed");
}
main().catch(err=>{console.error(err);process.exitCode=1;});
