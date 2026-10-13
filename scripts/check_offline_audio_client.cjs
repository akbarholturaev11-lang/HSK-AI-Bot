// Static-first Mandarin TTS contract across Course V3, practice and dictionary.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const load = (file) => fs.readFileSync(path.join(root, file), 'utf8');

async function main() {
  const index = load('app/static/audio/words-index.js');
  const client = load('app/static/audio/words-client.js');
  const context = { window: {}, fetch: null, encodeURIComponent };
  vm.createContext(context);
  vm.runInContext(index, context);
  vm.runInContext(client, context);
  assert.equal(context.window.HSK_OFFLINE_AUDIO.size, 4579);
  const resolver = context.window.HSKOfflineAudio;
  assert.match(resolver.url('大家好！'), /^\/audio\/words\/[0-9_]+\.mp3$/);
  const hashWord = Object.keys(context.window.HSK_OFFLINE_LONG_NAMES)[0];
  assert.ok(hashWord, 'Long-phrase mapping must exist');
  assert.match(resolver.url(hashWord), /^\/audio\/words\/sha1_[a-f0-9]{40}\.mp3$/);
  const unseen = '未收录：这是昨天在火星建的新机场。';
  assert.match(resolver.url(unseen), /^\/api\/v3\/tts\?text=/);

  // When the static route returns 404, the original server TTS stays available.
  const requests = [];
  context.fetch = (url) => {
    requests.push(url);
    return Promise.resolve({
      ok: url.startsWith('/api/v3/tts'),
      status: url.startsWith('/api/v3/tts') ? 200 : 404,
      blob: () => Promise.resolve('playable-tts-response')
    });
  };
  assert.equal(await resolver.fetchAudio('大家好！'), 'playable-tts-response');
  assert.equal(requests.length, 2);
  assert.match(requests[0], /^\/audio\/words\//);
  assert.match(requests[1], /^\/api\/v3\/tts\?/);
  requests.length = 0;
  assert.equal(await resolver.fetchAudio(unseen), 'playable-tts-response');
  assert.equal(requests.length, 1, 'An unseen sentence should not cause a static 404');

  const pages = [
    'course-v3.html', 'course_v3_pronunciation.html',
    'course_v3_recognition.html', 'course_v3_memorize.html',
    'course_v3_test.html', 'hsk-lugat.html'
  ];
  for (const name of pages) {
    const html = load('app/static/' + name);
    assert.match(html, /\/audio\/words\/index\.js/);
    const tags = /<script\b([^>]*)>([\s\S]*?)<\/script>/g;
    let m, count = 0;
    while ((m = tags.exec(html)) !== null) {
      if (m[1].includes('application/json') || !m[2].trim()) continue;
      new Function(m[2]);
      count++;
    }
    console.log('JavaScript parsed:', name, count, 'inline scripts');
  }
  console.log('All 4,579 offline audio lookup entries and server fallback verified.');
}
main().catch(error => {console.error(error);process.exitCode=1});
