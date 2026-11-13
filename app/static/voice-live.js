/* Browser audio transport for the authenticated, server-owned Live relay. */
(function (root) {
  "use strict";
  function supported() {
    return !!(root.isSecureContext && root.WebSocket && root.AudioWorkletNode &&
      (root.AudioContext || root.webkitAudioContext) && navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }
  // Client-side failures only (design D5). Server-sent codes, limits, a slow
  // network, a suspended audio context and a learner close are never reported.
  const REPORTED = new Set(["live_connection_timeout", "live_response_invalid", "live_audio_invalid", "live_socket_closed"]);
  function diag(code) {
    try { if (REPORTED.has(code) && root.HskDiag) root.HskDiag.report("voice_practice", "live_session_failed", code); } catch (_) {}
  }

  class LiveVoice {
    constructor(callbacks) {
      this.callbacks = callbacks || {};
      this.closed = false;
      this.ready = false;
      this.sources = new Set();
      this.nextPlay = 0;
    }

    async prepare() {
      const Audio = root.AudioContext || root.webkitAudioContext;
      this.context = new Audio();
      // Start the context within the microphone click's user activation, but
      // do not block on it: iOS may leave this promise pending until the
      // microphone is live, which used to hang Live in "connecting".
      const resuming = this.context.resume().catch(() => {});
      const stream = await navigator.mediaDevices.getUserMedia({ audio: {
        channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true
      }});
      if (this.closed) { stream.getTracks().forEach(track => track.stop()); throw new Error("cancelled"); }
      this.stream = stream;
      await Promise.race([resuming, new Promise(resolve => setTimeout(resolve, 4000))]);
      if (this.context.state !== "running") {
        try { await Promise.race([this.context.resume(), new Promise(resolve => setTimeout(resolve, 1500))]); } catch (_) {}
      }
      if (this.context.state !== "running") throw new Error("live_audio_suspended");
      await this.context.audioWorklet.addModule("/voice-live-worklet.js?v=1");
      if (this.closed) throw new Error("cancelled");
      this.capture = new AudioWorkletNode(this.context, "hsk-voice-capture");
      this.input = this.context.createMediaStreamSource(stream);
      this.silent = this.context.createGain();
      this.silent.gain.value = 0;
      this.input.connect(this.capture);
      this.capture.connect(this.silent).connect(this.context.destination);
      this.capture.port.onmessage = event => {
        if (!this.ready || this.closed) return;
        if (event.data.type === "speech") { this.interrupt(); return; }
        if (event.data.type !== "pcm") return;
        if (this.socket.bufferedAmount > 64000) { this.fail("live_network_slow"); return; }
        try { this.socket.send(event.data.data); } catch (_) { this.fail("live_voice_unavailable"); }
      };
    }

    connect(sessionId, initData, pwaCsrf) {
      if (this.closed) return Promise.reject(new Error("cancelled"));
      return new Promise((resolve, reject) => {
        let settled = false;
        this.rejectConnect = code => {
          if (!settled) { settled = true; reject(new Error(code)); }
        };
        const pwa = typeof pwaCsrf === "string" && pwaCsrf.length > 0;
        const url = new URL(pwa ? "/api/v3/pwa/voice/live" : "/api/voice-practice/live", root.location.href);
        url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
        const socket = this.socket = new WebSocket(url.href);
        this.timer = setTimeout(() => this.fail("live_connection_timeout"), 10000);
        socket.onopen = () => {
          if (this.closed) { socket.close(); return; }
          const proof = pwa ? { csrf: pwaCsrf } : { initData };
          socket.send(JSON.stringify({ type: "auth", session_id: sessionId, ...proof }));
        };
        socket.onmessage = event => {
          if (this.closed) return;
          let message;
          try { message = JSON.parse(event.data); } catch (_) { this.fail("live_response_invalid"); return; }
          if (message.type === "ready") {
            if (message.input_sample_rate !== 16000 || message.output_sample_rate !== 24000) {
              this.fail("live_response_invalid"); return;
            }
            clearTimeout(this.timer);
            this.ready = true;
            if (!settled) { settled = true; resolve(message); }
            this.state("listening");
          } else if (message.type === "audio") {
            try { this.play(message.data); } catch (_) { this.fail("live_audio_invalid"); }
          } else if (message.type === "interrupted") {
            this.interrupt();
          } else if (message.type === "turn_complete") {
            if (this.callbacks.onturn) this.callbacks.onturn(message);
          } else if (["time_limit", "budget_limit", "session_limit"].includes(message.type)) {
            this.fail(message.type, true);
          } else if (message.type === "error") {
            this.fail(message.code || "live_voice_unavailable", true);
          }
        };
        socket.onerror = () => this.lost();
        socket.onclose = () => { if (!this.closed) this.lost(); };
      });
    }

    state(value) { if (!this.closed && this.callbacks.onstate) this.callbacks.onstate(value); }

    play(data) {
      const bytes = atob(data || "");
      if (!bytes.length || bytes.length % 2) throw new Error("Invalid PCM");
      if (this.context.state !== "running") { this.fail("live_audio_suspended"); return; }
      if (this.nextPlay - this.context.currentTime > 20) { this.fail("live_network_slow"); return; }
      const buffer = this.context.createBuffer(1, bytes.length / 2, 24000);
      const samples = buffer.getChannelData(0);
      for (let i = 0; i < samples.length; i++) {
        let value = bytes.charCodeAt(i * 2) | (bytes.charCodeAt(i * 2 + 1) << 8);
        if (value >= 32768) value -= 65536;
        samples[i] = value / 32768;
      }
      const source = this.context.createBufferSource();
      source.buffer = buffer;
      const rate = this.callbacks.playbackRate ? Number(this.callbacks.playbackRate()) : 1;
      source.playbackRate.value = Math.max(0.6, Math.min(1.5, rate || 1));
      source.connect(this.context.destination);
      this.sources.add(source);
      source.onended = () => {
        source.disconnect();
        this.sources.delete(source);
        if (!this.sources.size) this.state("listening");
      };
      const at = Math.max(this.context.currentTime + 0.02, this.nextPlay);
      this.nextPlay = at + buffer.duration / source.playbackRate.value;
      source.start(at);
      this.state("speaking");
    }

    interrupt() {
      for (const source of this.sources) {
        source.onended = null;
        try { source.stop(); source.disconnect(); } catch (_) {}
      }
      this.sources.clear();
      this.nextPlay = 0;
      this.state("listening");
    }

    sendText(text) {
      if (!this.ready || this.closed) return false;
      this.interrupt();
      try {
        this.socket.send(JSON.stringify({ type: "text", text: String(text).slice(0, 200) }));
      } catch (_) {
        this.fail("live_voice_unavailable");
        return false;
      }
      this.state("analyzing");
      return true;
    }

    /* The socket dropped. Before "ready" it is a connect failure (not
       reported); after it the live session was cut off unexpectedly. */
    lost() {
      if (this.closed) return;
      if (this.ready) diag("live_socket_closed");
      this.fail("live_voice_unavailable");
    }

    fail(code, fromServer) {
      if (this.closed) return;
      if (!fromServer) diag(code);
      this.rejectConnect && this.rejectConnect(code);
      this.stop();
      if (this.callbacks.onerror) this.callbacks.onerror(code);
    }

    stop() {
      if (this.closed) return;
      this.closed = true;
      this.ready = false;
      clearTimeout(this.timer);
      this.rejectConnect && this.rejectConnect("cancelled");
      this.interrupt();
      if (this.socket) {
        this.socket.onclose = this.socket.onerror = this.socket.onmessage = null;
        if (this.socket.readyState === WebSocket.OPEN) {
          try { this.socket.send(JSON.stringify({ type: "stop" })); } catch (_) {}
        }
        try { this.socket.close(); } catch (_) {}
      }
      if (this.capture) { this.capture.port.onmessage = null; this.capture.disconnect(); }
      if (this.input) this.input.disconnect();
      if (this.silent) this.silent.disconnect();
      if (this.stream) this.stream.getTracks().forEach(track => track.stop());
      if (this.context) this.context.close().catch(() => {});
    }
  }
  root.PompLiveVoice = { supported: supported, create: callbacks => new LiveVoice(callbacks) };
})(window);
