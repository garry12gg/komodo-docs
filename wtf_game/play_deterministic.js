// Wrong Tool First — narrated playthrough, v4 (observed-time presses).
// Page: seeded Math.random (mulberry32 17172, hardcoded in index_seeded.html)
// + ticker advanced externally via window.__gameTick (capture-paced) + spawn
// observer pushing events with wall times. Node: screenshot -> tick -> poll
// spawns -> press SPACE (CDP) 140-300ms after a correct spawn is OBSERVED.
// Robust to any page timer throttling: presses always hit the current tool.
const { spawn } = require('child_process');
const fs = require('fs');

const FRAME_DIR = '/workspace/wtf_game/frames';
const URL = 'file:///workspace/wtf_game/index_seeded.html';
const PORT = 9237;
const SEED = 17172;
const TITLE_HOLD = 1700;

fs.mkdirSync(FRAME_DIR, { recursive: true });
for (const f of fs.readdirSync(FRAME_DIR)) fs.unlinkSync(FRAME_DIR + '/' + f);

const chrome = spawn('chromium', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
  '--remote-debugging-port=' + PORT, '--window-size=480,920',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
  '--disable-backgrounding-occluded-windows', '--disable-ipc-flooding-protection',
  '--mute-audio', 'about:blank'
], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getWsUrl() {
  for (let i = 0; i < 50; i++) {
    try {
      const res = await fetch('http://127.0.0.1:' + PORT + '/json/list');
      const j = await res.json();
      const page = j.find(t => t.type === 'page');
      if (page && page.webSocketDebuggerUrl) return page.webSocketDebuggerUrl;
    } catch (e) { /* retry */ }
    await sleep(200);
  }
  throw new Error('no CDP page target');
}

let msgId = 0;
const pending = new Map();
let ws;

function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++msgId;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function js(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  if (r.exceptionDetails) throw new Error('JS error: ' + JSON.stringify(r.exceptionDetails).slice(0, 300));
  return r.result && r.result.value;
}

async function pressSpace() {
  await send('Input.dispatchKeyEvent', { type: 'keyDown', key: ' ', code: 'Space', windowsVirtualKeyCode: 32, nativeVirtualKeyCode: 32 });
  await send('Input.dispatchKeyEvent', { type: 'keyUp', key: ' ', code: 'Space', windowsVirtualKeyCode: 32, nativeVirtualKeyCode: 32 });
}

const audit = { presses: [], winAt: null, frameTimes: [], captureStart: null, spawns: [] };
let frameCount = 0;
let capturing = true;

async function captureLoop() {
  while (capturing) {
    const t0 = Date.now();
    try {
      const r = await send('Page.captureScreenshot', { format: 'jpeg', quality: 85 });
      const file = FRAME_DIR + '/f_' + String(frameCount).padStart(5, '0') + '.jpg';
      fs.writeFileSync(file, Buffer.from(r.data, 'base64'));
      if (!audit.captureStart) audit.captureStart = t0;
      audit.frameTimes.push(t0);
      frameCount++;
      try { await js('window.__gameTick ? window.__gameTick() : 0'); } catch (e) {}
    } catch (e) { /* keep going */ }
    const elapsed = Date.now() - t0;
    await sleep(Math.max(40, 100 - elapsed));
  }
}

(async () => {
  try {
    const wsUrl = await getWsUrl();
    ws = new WebSocket(wsUrl);
    await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
    ws.onmessage = ev => {
      const m = JSON.parse(ev.data);
      if (m.id && pending.has(m.id)) {
        const p = pending.get(m.id); pending.delete(m.id);
        if (m.error) p.reject(new Error(m.error.message)); else p.resolve(m.result);
      }
    };
    await send('Page.enable');
    await send('Runtime.enable');
    await send('Emulation.setDeviceMetricsOverride', { width: 480, height: 920, deviceScaleFactor: 1, mobile: false });

    await send('Page.navigate', { url: URL });
    await sleep(2500);
    try { await send('Page.setWebLifecycleState', { state: 'active' }); } catch (e) {}

    // sanity: seeded rng first draws (throwaway gen — does not consume page rng)
    const rndVerify = await js(`(function () {
      var a = ${SEED} >>> 0;
      var f = function () {
        a = (a + 0x6D2B79F5) >>> 0;
        var t = a;
        t = ((t << 15) | (t >>> 17)) >>> 0;
        t = (t * (a ^ (t >>> 11))) >>> 0;
        return ((t ^ (t >>> 8)) >>> 0) / 4294967296;
      };
      return [f(), f()];
    })()`);
    console.log('rnd check:', JSON.stringify(rndVerify));

    // spawn observer (class + data-emoji only; cheap) + win observer
    await js(`(() => {
      window.__spawns = [];
      window.__winAt = null;
      const tool = document.getElementById('tool');
      let lastEmoji = null;
      let lastPush = 0;
      new MutationObserver(() => {
        if (tool.style.display === 'flex') {
          const emoji = tool.dataset.emoji || '';
          const now = Date.now();
          if (emoji !== lastEmoji || now - lastPush > 2500) {
            lastEmoji = emoji;
            lastPush = now;
            window.__spawns.push({ t: now, emoji: emoji, job: document.getElementById('jobicon').textContent });
          }
        }
      }).observe(tool, { attributes: true, attributeFilter: ['class', 'data-emoji'] });
      const ov = document.getElementById('overlay');
      new MutationObserver(() => {
        if (!ov.className.includes('hidden') && ov.querySelector('h1').textContent.includes('WORKSHOP')) {
          window.__winAt = Date.now();
        }
      }).observe(ov, { attributes: true, subtree: true, childList: true });
      return true;
    })()`);

    captureLoop();

    // wait for first frame, title hold, start
    while (!audit.captureStart) await sleep(50);
    const t0 = audit.captureStart;
    await sleep(t0 + TITLE_HOLD - Date.now());
    audit.presses.push({ t: Date.now(), kind: 'start' });
    await pressSpace();

    // press loop: poll observed spawns; press on correct ones (emoji === job)
    let pendingPress = null;
    let lastSpawnCount = 0;
    let grabs = 0;
    let wrongs = 0;
    const tStart = Date.now();
    while (!audit.winAt && Date.now() - tStart < 150000) {
      // flush new spawn events
      const evs = await js('window.__spawns.splice(0, window.__spawns.length)');
      if (Array.isArray(evs)) {
        for (const ev of evs) {
          audit.spawns.push(ev);
          if (ev.emoji === ev.job) {
            pendingPress = { target: ev.t + 140 + Math.random() * 160 };
          } else {
            wrongs++;
          }
        }
      }
      if (pendingPress && Date.now() >= pendingPress.target) {
        audit.presses.push({ t: Date.now(), kind: 'grab' });
        await pressSpace();
        grabs++;
        pendingPress = null;
      }
      audit.winAt = await js('window.__winAt');
      if (!audit.winAt) await sleep(60);
    }

    if (!audit.winAt) throw new Error('win never detected');

    await sleep(5200); // hold victory screen
    capturing = false;
    await sleep(300);

    const dur = (Date.now() - t0) / 1000;
    const outcome = await js(`(() => ({
      h: document.getElementById('overlay').querySelector('h1').textContent.replace(/\\n/g,' '),
      sub: document.getElementById('overlay').querySelector('.sub').textContent,
      gag: document.getElementById('overlay').querySelector('.gag').textContent,
      score: document.getElementById('bigscore').textContent,
      strikes: document.getElementById('strikes').textContent
    }))()`);
    const res = {
      seed: SEED, frames: frameCount, seconds: dur.toFixed(1), fps: (frameCount / dur).toFixed(2),
      outcome, winAt: audit.winAt, captureStart: t0, grabs, wrongs,
      frameTimes: audit.frameTimes,
      pressTimes: audit.presses.map(p => ({ kind: p.kind, dt: p.t - t0 })),
      spawns: audit.spawns.map(s => ({ dt: s.t - t0, emoji: s.emoji, job: s.job }))
    };
    fs.writeFileSync('/workspace/wtf_game/audit.json', JSON.stringify(res));
    console.log('DONE', JSON.stringify({ frames: res.frames, seconds: res.seconds, fps: res.fps, winDt: res.winAt - t0, grabs, wrongs, outcome: res.outcome.h }));
  } catch (e) {
    console.error('FAIL:', e.message);
    process.exitCode = 1;
  } finally {
    capturing = false;
    try { await send('Page.stopScreencast'); } catch (e) {}
    chrome.kill();
    process.exit(process.exitCode || 0);
  }
})();
