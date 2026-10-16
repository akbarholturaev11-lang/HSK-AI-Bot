// Mini App static MP3 / persisted TTS / server fallback contract.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const load = (file) => fs.readFileSync(path.join(root, file), 'utf8');
const index = load('app/static/audio/words-index.js');
const client = load('app/static/audio/words-client.js');
const tick = queueMicrotask;

// Small async IndexedDB double: models transaction read/write, index cursor,
// and storage persisting across new WebView/page JavaScript contexts.
function fakeDatabase() {
  const records = new Map();
  let currentDb;
  const storeNames = {
    contains: (name) => name === 'generated-v1' && !!currentDb.initialized
  };
  currentDb = {
    initialized: false,
    objectStoreNames: storeNames,
    createObjectStore() {
      this.initialized = true;
      return { createIndex() {} };
    },
    transaction(name, mode) {
      assert.equal(name, 'generated-v1');
      const tx = {};
      const objectStore = {
        get(key) {
          const req = {};
          tick(() => {req.result = records.get(key);req.onsuccess?.()});
          return req;
        },
        put(value) {
          tick(() => {records.set(value.key, value);tx.oncomplete?.()});
          return {};
        },
        index(name) {
          assert.equal(name, 'savedAt');
          return {openCursor(_key, direction) {
            assert.equal(direction, 'prev');
            const req = {};
            const values = [...records.values()].sort((a, b) => b.savedAt - a.savedAt);
            let position = 0;
            function next() {
              tick(() => {
                const value = values[position++];
                req.result = value ? {value, continue: next} : null;
                req.onsuccess?.();
              });
            }
            next();
            return req;
          }};
        }
      };
      tx.objectStore = () => objectStore;
      return tx;
    }
  };
  return {
    records,
    open() {
      const request = {result: currentDb};
      tick(() => {
        if (!currentDb.initialized) request.onupgradeneeded?.();
        request.onsuccess?.();
      });
      return request;
    }
  };
}

function browser(indexedDB, fetcher) {
  let ids = 0;
  const window = {
    indexedDB,
    URL: {createObjectURL() {return 'blob:local-' + ++ids}}
  };
  const context = {window, fetch: fetcher, encodeURIComponent, Date, Blob, URL, setTimeout};
  vm.createContext(context);
  vm.runInContext(index, context);
  vm.runInContext(client, context);
  return window.HSKOfflineAudio;
}

const audioBytes = new Blob([Buffer.alloc(560, 21)], {type: 'audio/mpeg'});
async function main() {
  const db = fakeDatabase();
  const requested = [];
  const fetcher = async (url) => {
    requested.push(url);
    const staticAsset = url.startsWith('/audio/words/');
    return {
      ok: !staticAsset,
      status: staticAsset ? 404 : 200,
      blob: async () => audioBytes
    };
  };
  const audio = browser(db, fetcher);
  assert.match(audio.url('大家好！'), /^\/audio\/words\/[0-9_]+\.mp3$/);
  const phraseWithHash = Object.keys((() => {
    const ctx={window:{},encodeURIComponent};
    vm.createContext(ctx);vm.runInContext(index,ctx);
    return ctx.window.HSK_OFFLINE_LONG_NAMES;
  })())[0];
  assert.match(audio.url(phraseWithHash), /^\/audio\/words\/sha1_[a-f0-9]{40}\.mp3$/);
  const novel = '未收录：这是昨天在火星建的新机场。';
  assert.match(audio.url(novel), /^\/api\/v3\/tts\?text=/);

  // A missing advertised static file still falls back to provider TTS.
  assert.equal(await audio.fetchAudio('大家好！'), audioBytes);
  assert.equal(requested.length, 2);
  assert.match(requested[0], /^\/audio\/words\//);
  assert.match(requested[1], /^\/api\/v3\/tts\?/);
  requested.length = 0;

  // New text: one server request, binary MP3 persisted on device.
  assert.equal(await audio.fetchAudio(novel), audioBytes);
  assert.equal(requested.length, 1);
  assert.equal(db.records.size, 2);
  assert.equal(db.records.get('zh-CN-XiaoxiaoNeural|-10%|' + novel).blob, audioBytes);
  requested.length = 0;
  assert.equal(await audio.fetchAudio(novel), audioBytes);
  assert.equal(requested.length, 0, 'Repeated phrase must not call server');
  assert.match(audio.cachedUrl(novel), /^blob:local-/);

  // Native Audio(...).play() first on iPhone; when server starts playing
  // capture bytes once in the background for future app opens.
  const directPlay = '这是今天才学会的一个新句子。';
  audio.rememberPlayed(directPlay, audio.serverUrl(directPlay));
  await audio.fetchAudio(directPlay);
  assert.equal(requested.length, 1);
  requested.length = 0;

  // The next Mini App launch must reopen previously generated audio,
  // even when the server is offline.
  const secondPage = browser(db, () => {throw new Error('SERVER CALLED ON REOPEN')});
  await secondPage.warmRecent();
  assert.match(secondPage.cachedUrl(novel), /^blob:local-/);
  assert.match(secondPage.cachedUrl(directPlay), /^blob:local-/);
  assert.equal(await secondPage.fetchAudio(novel), audioBytes);
  assert.equal(await secondPage.fetchAudio(directPlay), audioBytes);
  assert.equal(requested.length, 0);

  // No IndexedDB permission? Audio must still be playable from server.
  const noStorage = browser(null, fetcher);
  assert.equal(await noStorage.fetchAudio('新手机无法存储的句子。'), audioBytes);
  assert.equal(requested.length, 1);
  requested.length = 0;

  // A JSON error page must never poison local audio storage.
  const invalid = browser(fakeDatabase(), async (src) => ({
    ok: true, status: 200,
    blob: async () => new Blob(['{"error":"tts_failed"}'], {type:'application/json'})
  }));
  await assert.rejects(invalid.fetchAudio('新服务器的错误响应。'), /invalid_audio_data/);

  const pages = [
    'course-v3.html', 'course_v3_pronunciation.html',
    'course_v3_recognition.html', 'course_v3_memorize.html',
    'course_v3_test.html', 'hsk-lugat.html'
  ];
  for (const name of pages) {
    const html = load('app/static/' + name);
    assert.match(html, /\/audio\/words\/client\.js\?v=20261014-persist-1/);
    assert.match(html, /HSKOfflineAudio\.rememberPlayed/);
    const tags = /<script\b([^>]*)>([\s\S]*?)<\/script>/g;
    let m, count = 0;
    while ((m = tags.exec(html)) !== null) {
      if (m[1].includes('application/json') || !m[2].trim()) continue;
      new Function(m[2]);
      count++;
    }
    console.log('JS parsed:', name, count, 'inline scripts');
  }
  console.log('Persistent generated audio / no repeat server / Android-compatible static MP3 passed.');
}
main().catch(error => {console.error(error);process.exitCode=1});
