
(() => {
  if (window.__keytarPatched) return 'already';
  window.__keytarPatched = true;
  window.__cap = null;
  window.__capErr = null;
  window.__captureStart = null;

  const origConnect = GainNode.prototype.connect;
  GainNode.prototype.connect = function (...args) {
    const r = origConnect.apply(this, args);
    try {
      const target = args[0];
      // The page's audio core does master.connect(actx.destination) once.
      if (target && target.context && !window.__cap && !this.__tapped) {
        this.__tapped = true;
        const ctx = target.context;
        const streamDest = ctx.createMediaStreamDestination();
        this.connect(streamDest);
        const rec = new MediaRecorder(streamDest.stream);
        const chunks = [];
        rec.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
        rec.onstop = () => {
          const blob = new Blob(chunks, { type: rec.mimeType || 'audio/webm' });
          const fr = new FileReader();
          fr.onload = () => { window.__audioB64 = fr.result; };
          fr.readAsDataURL(blob);
        };
        window.__cap = { ctx, rec, streamDest };
        window.__captureStart = performance.now();
        if (ctx.state === 'suspended') ctx.resume();
        rec.start();
      }
    } catch (e) { window.__capErr = String(e); }
    return r;
  };
  return 'patched';
})();
