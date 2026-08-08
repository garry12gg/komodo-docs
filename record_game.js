// Escape Tyrannia playthrough recorder — drives headless Chromium via CDP,
// captures frames, plays the game adaptively until victory (or retries).
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const FRAME_DIR = '/workspace/frames';
const URL = 'https://cdn.talkie-ai.com/talkie/47956520751168/383625282932867/html/2026_04_23/00_06_47_504f6a72279b461b.html';

fs.mkdirSync(FRAME_DIR, { recursive: true });
for (const f of fs.readdirSync(FRAME_DIR)) fs.unlinkSync(path.join(FRAME_DIR, f));

const chrome = spawn('chromium', [
  '--headless=new', '--no-sandbox', '--disable-gpu', '--hide-scrollbars',
  '--remote-debugging-port=9222', '--window-size=480,920',
  '--disable-background-timer-throttling', '--disable-renderer-backgrounding',
  '--mute-audio', 'about:blank'
], { stdio: 'ignore' });

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function getWsUrl() {
  for (let i = 0; i < 50; i++) {
    try {
      const res = await fetch('http://127.0.0.1:9222/json/list');
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

const STATE_EXPR = `(() => {
  const vis = id => !document.getElementById(id).classList.contains('hidden');
  const txt = id => { const e = document.getElementById(id); return e ? e.textContent : null; };
  return {
    explore: vis('explore-screen'), battle: vis('battle-screen'),
    over: vis('gameover-screen'), vic: vis('victory-screen'),
    hp: +txt('hp-text'), potions: +txt('pot-count'), np: +txt('np-display'), floor: +txt('floor-display'),
    enemyHp: txt('enemy-hp-text') ? +txt('enemy-hp-text') : null,
    enemyName: txt('enemy-name'),
    choices: Array.from(document.querySelectorAll('#choices .btn')).map(b => b.textContent),
    cont: !document.getElementById('battle-continue').classList.contains('hidden')
  };
})()`;

async function getState() { return js(STATE_EXPR); }

function clickId(id) { return js(`document.getElementById('${id}').click()`); }

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
async function waitExplore() {
  for (let i = 0; i < 100; i++) {
    const s = await getState();
    if (s.explore && s.choices.length > 0) return s;
    await sleep(250);
  }
  throw new Error('never reached explore');
}

function pickChoice(s, want) {
  // want: 'fight' | 'fire' | 'treasure' | 'intimidate' | any
  let idx = -1;
  const prefixes = { fight: '⚔️', fire: '🔥', treasure: '💰', intimidate: '🛡️' };
  if (want !== 'any' && prefixes[want]) {
    idx = s.choices.findIndex(c => c.trim().startsWith(prefixes[want]));
  }
  if (idx === -1) idx = 0;
  return idx;
}

async function battle(s) {
  let turns = 0;
  while (true) {
    s = await getState();
    if (!s.battle) return s;
    if (s.cont) {
      await sleep(700);            // let defeat log / NP float settle
      console.log('battle won vs ' + s.enemyName + ' -> continue');
      await clickId('btn-continue');
      await sleep(1500);
      return await getState();
    }
    if (s.over) return s;
    const hp = s.hp, pot = s.potions, ehp = s.enemyHp;
    if (ehp === null) { await sleep(400); continue; }
    if (hp <= 22 && pot > 0) await clickId('btn-potion');
    else if (hp <= 13) await clickId('btn-defend');
    else if (ehp <= 12) await clickId('btn-attack');
    else await clickId('btn-fire');
    await sleep(1400);
    if (++turns > 30) throw new Error('battle loop stuck');
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
    await sleep(4000);

    // wait for game to init
    let s = null;
    for (let i = 0; i < 60; i++) {
      try { s = await getState(); if (s.explore) break; } catch (e) {}
      await sleep(500);
    }
    if (!s || !s.explore) throw new Error('game did not load');

    // Fix the author's clipped enemy sprite: absolute w/o top/left sits below the
    // scene img and is cut by overflow:hidden. Place it over the scene as intended.
    await js(`(() => {
      const st = document.createElement('style');
      st.textContent = '#enemy-sprite { left: 16px !important; top: 24px !important; }';
      document.head.appendChild(st);
    })()`);

    captureLoop();   // start capturing
    await sleep(3000); // hold on opening screen

    const wantSeq = ['fight', 'fire', 'fight', 'treasure', 'fight']; // last = boss
    let enc = 0;
    let t0 = Date.now();

    while (true) {
      s = await getState();
      if (s.vic) break;
      if (s.over) {
        console.log('GAME OVER at floor ' + s.floor + ' — retrying');
        await clickId('btn-retry');
        await sleep(2000);
        continue;
      }
      if (s.battle) { s = await battle(s); continue; }
      if (s.explore && s.choices.length > 0) {
        const want = enc < wantSeq.length ? wantSeq[enc] : 'fight';
        const idx = pickChoice(s, want);
        console.log('encounter ' + enc + ' (floor ' + s.floor + ') -> ' + s.choices[idx].slice(0, 30));
        await js(`document.querySelectorAll('#choices .btn')[${idx}].click()`);
        await sleep(2200);
        // if a Continue button appeared, advance
        const s2 = await getState();
        if (s2.explore && s2.choices.length === 1 && s2.choices[0].includes('Continue')) {
          await sleep(1200);
          console.log('  ...skip narrative, continue');
          await js(`document.querySelectorAll('#choices .btn')[0].click()`);
          await sleep(1600);
        }
        enc++;
        continue;
      }
      await sleep(400);
      if (Date.now() - t0 > 240000) throw new Error('global timeout');
    }

    await sleep(4500); // hold victory screen
    capturing = false;
    await sleep(300);
    const dur = (Date.now() - captureStart) / 1000;
    console.log(JSON.stringify({ frames: frameCount, seconds: dur.toFixed(1), fps: (frameCount / dur).toFixed(2), np: s.np, hp: s.hp, floor: s.floor }));
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
