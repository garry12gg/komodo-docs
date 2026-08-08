// Wasabi Roulette (Deviled Egg Russian Roulette v1.3 by Dusty Sushi) recorder.
// Drives headless Chromium via CDP, captures frames, plays the plates with a
// scripted arc: clean plate 1, eat 3, take the wasabi, clean the rest, etc.
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FRAME_DIR = '/workspace/wframes';
const URL = 'https://public.ilands.ai/agent-bundles/334481135176257536/14448cbb39b38d8dfd41cf328f1ee56f706bb03c814850ac6e408514ae07e86d/index.html';

fs.mkdirSync(FRAME_DIR, { recursive: true });
for (const f of fs.readdirSync(FRAME_DIR)) fs.unlinkSync(path.join(FRAME_DIR, f));

const chrome = spawn('chromium', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
  '--remote-debugging-port=9223', '--window-size=480,920',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
  '--mute-audio', 'about:blank'
], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getWsUrl() {
  for (let i = 0; i < 50; i++) {
    try {
      const res = await fetch('http://127.0.0.1:9223/json/list');
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

// Game globals: st {sc,lv,pl,cu,nl,bs}, best, lg. Eggs carry .cr (cursed=wasabi).
const STATE_EXPR = `(() => {
  const vis = id => { const e = document.getElementById(id); return e && !e.classList.contains('hi'); };
  return {
    screen: vis('ts') ? 'ts' : (vis('os') ? 'os' : 'gs'),
    sc: st.sc, lv: st.lv, pl: st.pl, cu: st.cu, nl: st.nl, bs: st.bs, best: best,
    eggs: Array.from(document.querySelectorAll('#pt .eg')).map(e => ({ cr: !!e.cr }))
  };
})()`;

async function getState() { return js(STATE_EXPR); }

// ---------- frame capture ----------
let frameCount = 0;
let captureStart = null;
let capturing = true;

async function captureLoop() {
  while (capturing) {
    const t0 = Date.now();
    try {
      const r = await send('Page.captureScreenshot', { format: 'jpeg', quality: 85 });
      const file = path.join(FRAME_DIR, 'f_' + String(frameCount).padStart(5, '0') + '.jpg');
      fs.writeFileSync(file, Buffer.from(r.data, 'base64'));
      frameCount++;
      if (!captureStart) captureStart = t0;
    } catch (e) { /* keep going */ }
    const elapsed = Date.now() - t0;
    await sleep(Math.max(40, 100 - elapsed));
  }
}

// ---------- game driver ----------
async function waitScreen(want) {
  for (let i = 0; i < 120; i++) {
    const s = await getState();
    if (s.screen === want) return s;
    await sleep(250);
  }
  throw new Error('never reached screen ' + want);
}

// Ready to click: game screen, not busy, at least one egg on the plate.
async function waitReady() {
  for (let i = 0; i < 60; i++) {
    const s = await getState();
    if (s.screen === 'gs' && !s.bs && s.eggs.length > 0 && s.nl > 0) return s;
    await sleep(200);
  }
  throw new Error('never ready');
}

function clickEgg(idx) {
  return js(`document.querySelectorAll('#pt .eg')[${idx}].click()`);
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
    await sleep(4000);
    await waitScreen('ts');

    captureLoop();
    await sleep(2500); // hold the title screen

    console.log('START — tap the title');
    await js(`document.getElementById('ts').click()`);
    await sleep(1500);

    // Scripted arc. safe: eat N safe eggs. wasabi: eat the cursed egg on purpose.
    const actions = [
      { p: 1, safe: 5 },
      { p: 2, safe: 3 },
      { p: 2, wasabi: true },
      { p: 2, safe: 4 },
      { p: 3, safe: 3 },
      { p: 3, wasabi: true },
      { p: 3, safe: 4 },
      { p: 4, safe: 3 },
      { p: 4, wasabi: true },
    ];

    for (const a of actions) {
      if (a.safe) {
        for (let i = 0; i < a.safe; i++) {
          const s = await waitReady();
          const idx = s.eggs.findIndex(e => !e.cr);
          if (idx === -1) throw new Error('no safe egg on plate ' + s.pl);
          await clickEgg(idx);
          await sleep(800);
          const after = await getState();
          console.log('ate -> plate ' + after.pl + ', eggs ' + after.sc + ', lv ' + after.lv + ', nl ' + after.nl);
        }
      } else {
        const s = await waitReady();
        const idx = s.eggs.findIndex(e => e.cr);
        if (idx === -1) throw new Error('no wasabi egg on plate ' + s.pl);
        console.log('WASABI on plate ' + s.pl + ' (eggs ' + s.sc + ') — deliberate wrong pick');
        await clickEgg(idx);
        await sleep(2900); // burn anim: shake, flash, splash, heart loss, new plate
        const after = await getState();
        console.log('after burn -> lv ' + after.lv + ', plate ' + after.pl + ', eggs ' + after.sc);
        if (after.lv <= 0) break;
      }
    }

    await waitScreen('os');
    console.log('GAME OVER — the wasabi wins');
    await sleep(4200); // hold the ledger + record card

    capturing = false;
    await sleep(300);
    const dur = (Date.now() - captureStart) / 1000;
    const final = await getState();
    console.log(JSON.stringify({ frames: frameCount, seconds: dur.toFixed(1), fps: (frameCount / dur).toFixed(2), sc: final.sc, best: final.best }));
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
