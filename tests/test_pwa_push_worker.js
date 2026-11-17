"use strict";
// Run the real worker handlers, including notificationclick and badge state.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('app/static/iphone-pwa-sw.js', 'utf8');
const handlers = {}, shown = [], badges = [], opened = [], navigated = [];
const stored = new Map();
const cache = {match: async k => stored.get(k)?.clone(), put: async (k,v) => stored.set(k,v)};
let windows = [];
const self = {
  location: {origin:'https://hsk.test'},
  addEventListener: (name, fn) => {handlers[name] = fn;},
  registration: {showNotification: async (title, options) => {shown.push({title, ...options});}},
  navigator: {setAppBadge: async value => badges.push(value)}, caches: {},
  clients: {matchAll: async () => windows, openWindow: async url => opened.push(url)}
};
vm.runInNewContext(source, {self, URL, Response, caches:{open:async () => cache}});
async function push(value, corrupt = false) {
  let pending;
  handlers.push({data:{json:() => {if (corrupt) throw Error('bad JSON'); return value;}},
                 waitUntil:p => {pending = p;}});
  await pending;
  return shown.at(-1);
}
async function click() {
  let pending, closed = false;
  handlers.notificationclick({notification:{close:() => {closed = true;}},waitUntil:p => {pending=p;}});
  await pending;
  assert(closed);
}
(async () => {
  for (const [lang, label] of [['uz','📚 Darsni davom ettiramizmi?'],['ru','📚 Продолжим урок?'],['tj','📚 Дарсро идома медиҳем?']]) {
    const body = '学习 🎯 '.repeat(50);
    const out = await push({title:label, body, lang, tag:'hsk-event-1',url:'https://evil.test/private'});
    assert.equal(out.title,label);
    assert.equal(out.body,body); // was truncated at 160 characters
    assert.equal(out.lang,lang==='tj'?'tg':lang);
    assert.equal(out.tag,'hsk-event-1');
    assert.equal(out.data.url,'/iphone-pwa/course?notice=1');
  }
  assert.deepEqual(badges,[1,2,3]);
  for (const value of [null, 1, {}, {title:'HSK AI'}, {title:'  '}]) {
    assert.equal((await push(value)).title,'🔔');
  }
  assert.equal((await push({},true)).title,'🔔');
  const long = await push({title:'😀'.repeat(100),body:'😀'.repeat(1200),tag:'invalid tag'});
  assert.equal(Array.from(long.title).length,80);
  assert.equal(Array.from(long.body).length,1000);
  assert(!/[\uD800-\uDFFF]/u.test(long.body));
  assert.equal(long.tag,'hsk-pwa-notice');
  await click();
  assert.deepEqual(opened,['https://hsk.test/iphone-pwa/course?notice=1']);
  let focused = 0;
  windows = [{url:'https://evil.test/iphone-pwa/course',navigate:() => {throw Error('external');}},
             {url:'https://hsk.test/iphone-pwa/course',navigate:async url => {navigated.push(url); return null;},focus:async () => {focused++;}}];
  await click();
  assert.equal(focused,1);
  assert.deepEqual(navigated,['https://hsk.test/iphone-pwa/course?notice=1']);
  assert.equal(opened.length,1);
  console.log('PWA push worker: localized content, Unicode, badge, tags and safe click passed');
})().catch(error => {console.error(error); process.exitCode=1;});
