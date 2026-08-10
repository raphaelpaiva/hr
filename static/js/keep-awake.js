// Mantém a tela ligada enquanto o vocalista lê a letra.
// Estratégia em camadas (o hotspot do Pi serve HTTP, contexto inseguro):
//   1. Wake Lock API (requer HTTPS/localhost — melhoria progressiva)
//   2. Fallback "mídia silenciosa": Android → loop de áudio (Web Audio);
//      iOS → vídeo silencioso <video loop muted playsinline>.
// Precisa de um gesto do usuário (tap) para ativar no fallback.
const keepAwake = (() => {
  let wakeLock = null;
  let video = null;
  let audioCtx = null;
  let active = false;
  let listeners = [];

  // MP4 silencioso mínimo (quadro preto, ~3s, H.264 baseline) em base64.
  const SILENT_VIDEO =
    'data:video/mp4;base64,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';

  function notify() {
    listeners.forEach(fn => fn(active));
  }

  async function tryWakeLock() {
    if (!('wakeLock' in navigator)) return false;
    try {
      wakeLock = await navigator.wakeLock.request('screen');
      wakeLock.addEventListener('release', () => {
        wakeLock = null;
        if (active) engageFallback();
      });
      return true;
    } catch (e) {
      return false;
    }
  }

  function engageFallback() {
    if (isIOS()) {
      if (!video) {
        video = document.createElement('video');
        video.src = SILENT_VIDEO;
        video.setAttribute('playsinline', '');
        video.muted = true;
        video.loop = true;
        video.style.position = 'fixed';
        video.style.opacity = '0';
        video.style.pointerEvents = 'none';
        document.body.appendChild(video);
      }
      const playPromise = video.play();
      if (playPromise && playPromise.catch) playPromise.catch(() => {});
    } else {
      if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioCtx.createBufferSource();
        const buffer = audioCtx.createBuffer(1, 1, 22050);
        buffer.getChannelData(0)[0] = 0;
        source.buffer = buffer;
        source.loop = true;
        source.connect(audioCtx.destination);
        source.start();
      }
      if (audioCtx.state === 'suspended') {
        const resumePromise = audioCtx.resume();
        if (resumePromise && resumePromise.catch) resumePromise.catch(() => {});
      }
    }
  }

  function isIOS() {
    return /iPad|iPhone|iPod/.test(navigator.userAgent);
  }

  async function enable() {
    if (active) return;
    try {
      if (await tryWakeLock()) {
        active = true;
        notify();
        return;
      }
      engageFallback();
      active = true;
      notify();
    } catch (e) {
      active = false;
      notify();
    }
  }

  async function disable() {
    active = false;
    if (wakeLock) {
      try { await wakeLock.release(); } catch (e) {}
      wakeLock = null;
    }
    if (audioCtx && audioCtx.state !== 'closed') {
      try { await audioCtx.close(); } catch (e) {}
    }
    audioCtx = null;
    if (video) {
      video.pause();
      video.remove();
      video = null;
    }
    notify();
  }

  function onStatusChange(fn) {
    listeners.push(fn);
    return () => {
      listeners = listeners.filter(f => f !== fn);
    };
  }

  // Re-ativa ao voltar para a aba (a tela pode ter apagado).
  document.addEventListener('visibilitychange', () => {
    if (active && document.visibilityState === 'visible') {
      wakeLock = null;
      enable();
    }
  });

  return { enable, disable, onStatusChange };
})();
