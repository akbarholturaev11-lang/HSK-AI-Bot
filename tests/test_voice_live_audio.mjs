import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

const script = readFileSync(new URL("../app/static/voice-live-worklet.js", import.meta.url), "utf8");
for (const rate of [16000, 44100, 48000, 96000]) {
  test(`capture produces 20 ms little-endian PCM16 chunks from ${rate} Hz`, () => {
    const messages = [];
    let Capture;
    vm.runInNewContext(script, {
      sampleRate: rate,
      AudioWorkletProcessor: class { constructor() { this.port = { postMessage: message => messages.push(message) }; } },
      registerProcessor: (_, type) => { Capture = type; }
    });
    const capture = new Capture();
    const input = new Float32Array(rate / 10).fill(-0.25); // 100 ms at the device rate
    for (let offset = 0; offset < input.length; offset += 128) capture.process([[input.slice(offset, offset + 128)]]);
    const pcm = messages.filter(message => message.type === "pcm");
    assert.equal(pcm.length, 5);
    for (const packet of pcm) {
      assert.equal(packet.data.byteLength, 640);
      const view = new DataView(packet.data);
      for (let i = 0; i < 320; i++) assert.equal(view.getInt16(i * 2, true), -8192);
    }
    assert.equal(messages.filter(message => message.type === "speech").length, 1);
  });
}
