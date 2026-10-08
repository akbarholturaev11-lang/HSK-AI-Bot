/* Mono 16 kHz PCM capture, independent of the device's actual sample rate. */
class HskVoiceCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / 16000;
    this.weight = 0;
    this.sum = 0;
    this.buffer = new ArrayBuffer(640); // 20 ms, PCM16 little-endian
    this.view = new DataView(this.buffer);
    this.position = 0;
    this.speechFrames = 0;
    this.speaking = false;
  }

  process(inputs) {
    const samples = inputs[0] && inputs[0][0];
    if (!samples) return true;
    let power = 0;
    for (const sample of samples) {
      power += sample * sample;
      let remaining = 1;
      while (remaining > 0.000001) {
        const take = Math.min(remaining, this.ratio - this.weight);
        this.sum += sample * take;
        this.weight += take;
        remaining -= take;
        if (this.weight >= this.ratio - 0.000001) {
          const value = Math.max(-1, Math.min(1, this.sum / this.ratio));
          this.view.setInt16(this.position * 2, Math.round(value * (value < 0 ? 32768 : 32767)), true);
          this.position++;
          this.weight = 0;
          this.sum = 0;
          if (this.position === 320) {
            this.port.postMessage({ type: "pcm", data: this.buffer }, [this.buffer]);
            this.buffer = new ArrayBuffer(640);
            this.view = new DataView(this.buffer);
            this.position = 0;
          }
        }
      }
    }
    // Echo cancellation is requested at capture. Local speech cuts queued
    // playback promptly; Gemini's VAD remains the authority for model turns.
    this.speechFrames = Math.sqrt(power / samples.length) > 0.045 ? this.speechFrames + samples.length : 0;
    const speaking = this.speechFrames >= sampleRate * 0.08;
    if (speaking && !this.speaking) this.port.postMessage({ type: "speech" });
    this.speaking = speaking;
    return true;
  }
}
registerProcessor("hsk-voice-capture", HskVoiceCapture);
