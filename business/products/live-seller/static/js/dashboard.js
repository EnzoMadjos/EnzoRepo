/* ── Mine Tracker — Dashboard JS ────────────────────────────────────── */

let ws = null;
let sessionId = null;
let mineCount = 0;
let products = [];   // cached from /api/inventory/active

// ── WebSocket ──────────────────────────────────────────────────────────

function connectWS() {
  ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    const handler = wsHandlers[msg.type];
    if (handler) handler(msg.data);
  };

  ws.onclose = () => setTimeout(connectWS, 2000);
}

const wsHandlers = {
  tiktok_connected:    (d) => setTikTokStatus(true, d.username),
  tiktok_disconnected: ()  => setTikTokStatus(false),
  // Pin event from TikTok — auto-open capture modal pre-filled
  pin: (d) => openCapture(d),
};

// ── TikTok connection ──────────────────────────────────────────────────

async function connectTikTok() {
  const username = document.getElementById('input-username').value.trim();
  if (!username) { alert('Enter a TikTok username first'); return; }
  const res = await api('POST', '/api/connect', { username });
  if (!res) return;
  document.getElementById('btn-disconnect').classList.remove('hidden');
}

async function disconnectTikTok() {
  await api('POST', '/api/disconnect');
  setTikTokStatus(false);
}

function setTikTokStatus(connected, username = '') {
  const el = document.getElementById('tiktok-status');
  el.textContent = connected ? `● @${username}` : '● Disconnected';
  el.className = 'status-badge ' + (connected ? 'status-on' : 'status-off');
  document.getElementById('btn-disconnect').classList.toggle('hidden', !connected);
}

// ── Session ────────────────────────────────────────────────────────────

async function startSession() {
  const username = document.getElementById('input-username').value.trim() || 'unknown';
  const res = await api('POST', '/api/sessions/start', { tiktok_user: username });
  if (!res) return;
  applySession(res);
  document.getElementById('mine-log').innerHTML = '';
  mineCount = 0;
  setEl('mine-count', 0);
}

async function endSession() {
  if (!confirm('End session and close mine log?')) return;
  await api('POST', '/api/sessions/end');
  sessionId = null;
  setEl('session-info', '');
  document.getElementById('btn-start-session').classList.remove('hidden');
  document.getElementById('btn-end-session').classList.add('hidden');
}

function applySession(s) {
  sessionId = s.id;
  setEl('session-info', `Session #${s.id} — @${s.tiktok_user}`);
  document.getElementById('btn-start-session').classList.add('hidden');
  document.getElementById('btn-end-session').classList.remove('hidden');
}

// ── Products ───────────────────────────────────────────────────────────

async function loadProducts() {
  const data = await api('GET', '/api/inventory/active');
  products = data || [];
  const sel = document.getElementById('cap-product');
  // Keep first placeholder option
  sel.innerHTML = '<option value="">— select product —</option>';
  for (const p of products) {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.dataset.price = p.price;
    opt.dataset.name  = p.name;
    const stockLabel  = p.stock > 0 ? ` (${p.stock} left)` : ' (out of stock)';
    opt.textContent   = `${p.name} — PHP ${p.price.toLocaleString(undefined, {minimumFractionDigits:2})}${stockLabel}`;
    sel.appendChild(opt);
  }
}

function onProductSelect() {
  const sel = document.getElementById('cap-product');
  const opt = sel.options[sel.selectedIndex];
  if (opt.value) {
    document.getElementById('cap-price').value = opt.dataset.price;
  }
}

// ── Capture modal ──────────────────────────────────────────────────────

// Called by pin event (pre-filled, from TikTok)
function openCapture(d) {
  if (!sessionId) { alert('Start a session first!'); return; }

  document.getElementById('cap-uid').value    = d.tiktok_uid || '';
  document.getElementById('cap-name').value   = d.display_name || '';
  document.getElementById('cap-handle').value = d.handle ? '@' + d.handle : '';
  document.getElementById('cap-raw').value    = d.text || '';
  document.getElementById('cap-price').value  = '';
  document.getElementById('cap-product').value = '';
  document.getElementById('capture-warning').classList.add('hidden');
  document.getElementById('modal-capture').classList.remove('hidden');

  setTimeout(() => document.getElementById('cap-price').focus(), 80);
}

// Called by manual "New Mine" button — blank fields
function openManualCapture() {
  if (!sessionId) { alert('Start a session first!'); return; }

  document.getElementById('cap-uid').value    = 'manual_' + Date.now();
  document.getElementById('cap-name').value   = '';
  document.getElementById('cap-handle').value = '';
  document.getElementById('cap-raw').value    = '';
  document.getElementById('cap-price').value  = '';
  document.getElementById('cap-product').value = '';
  document.getElementById('capture-warning').classList.add('hidden');
  document.getElementById('modal-capture').classList.remove('hidden');

  setTimeout(() => document.getElementById('cap-name').focus(), 80);
}

function closeCapture() {
  document.getElementById('modal-capture').classList.add('hidden');
}

// Close modal on overlay click
document.getElementById('modal-capture').addEventListener('click', function (e) {
  if (e.target === this) closeCapture();
});

// Allow Enter key in price field to submit
document.getElementById('cap-price').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') saveMine();
});

async function saveMine() {
  const price = parseFloat(document.getElementById('cap-price').value);
  if (!price || price <= 0) {
    document.getElementById('cap-price').focus();
    return;
  }

  const sel        = document.getElementById('cap-product');
  const productId  = sel.value ? parseInt(sel.value, 10) : null;
  const productName = productId ? sel.options[sel.selectedIndex].dataset.name : '';

  const rawHandle  = document.getElementById('cap-handle').value.replace(/^@/, '');
  const rawName    = document.getElementById('cap-name').value.trim();

  if (!rawName) { document.getElementById('cap-name').focus(); return; }

  const payload = {
    tiktok_uid:   document.getElementById('cap-uid').value || 'manual_' + Date.now(),
    display_name: rawName,
    handle:       rawHandle,
    price,
    raw_comment:  document.getElementById('cap-raw').value,
    product_id:   productId,
    product_name: productName,
  };

  const res = await api('POST', '/api/mines', payload);
  if (!res) return;

  closeCapture();
  addMineToLog(res);

  // Refresh product list so stock counts stay current
  loadProducts();

  if (res.flagged) showFlagBanner(res);
}

// ── Mine log ───────────────────────────────────────────────────────────

function addMineToLog(mine) {
  const log = document.getElementById('mine-log');
  const ts  = new Date(mine.mined_at * 1000).toLocaleTimeString();
  const productLine = mine.product_name
    ? `<div class="mine-product">${esc(mine.product_name)}</div>`
    : '';

  const row = document.createElement('div');
  row.className = 'mine-row' + (mine.flagged ? ' mine-flagged' : '');
  row.innerHTML = `
    <div class="mine-meta">
      <span class="mine-name">${esc(mine.display_name)}</span>
      <span class="mine-handle">@${esc(mine.handle)}</span>
      <span class="mine-badge ${mine.status === 'new' ? 'badge-new' : 'badge-repeat'}">${mine.status}</span>
    </div>
    ${productLine}
    <div class="mine-price">PHP ${mine.price.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}</div>
    <div class="mine-footer">
      <span class="mine-time">${ts}</span>
      <button class="btn-reprint" onclick="reprintMine(${mine.id})">🖨 Reprint</button>
    </div>
  `;
  log.prepend(row);
  mineCount++;
  setEl('mine-count', mineCount);
}

function showFlagBanner(mine) {
  const logEl = document.getElementById('mine-log');
  const banner = document.createElement('div');
  banner.className = 'flag-banner';
  banner.innerHTML = `⚠️ <strong>${esc(mine.display_name)}</strong> is a NEW buyer — ${mine.session_mine_count} mines this session! Click to dismiss.`;
  banner.addEventListener('click', () => banner.remove());
  logEl.prepend(banner);
}

async function reprintMine(mineId) {
  const res = await api('POST', `/api/mines/${mineId}/reprint`);
  if (res && !res.print_ok) alert('Reprint failed — check printer connection');
}

// ── Utils ──────────────────────────────────────────────────────────────

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(path, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || `Error ${res.status}`);
      return null;
    }
    return res.json();
  } catch (e) {
    console.error(e);
    return null;
  }
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── Init ───────────────────────────────────────────────────────────────

async function init() {
  connectWS();
  loadProducts();

  const status = await api('GET', '/api/status');
  if (!status) return;

  if (status.tiktok_connected) setTikTokStatus(true);

  if (status.session) {
    applySession(status.session);
    const mines = await api('GET', `/api/sessions/${status.session.id}/mines`) || [];
    mines.forEach(m => addMineToLog({ ...m, flagged: false }));
  }
}

init();


let ws = null;
let sessionId = null;
let commentCount = 0;
let mineCount = 0;
const MAX_COMMENTS = 300;

// ── WebSocket ──────────────────────────────────────────────────────────

function connectWS() {
  ws = new WebSocket(`ws://${location.host}/ws`);

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    const handler = wsHandlers[msg.type];
    if (handler) handler(msg.data);
  };

  ws.onclose = () => setTimeout(connectWS, 2000);
}

const wsHandlers = {
  tiktok_connected:    (d) => setTikTokStatus(true, d.username),
  tiktok_disconnected: ()  => setTikTokStatus(false),
  comment: (d) => addComment(d),
  // Pin event from TikTok — auto-open capture modal
  pin: (d) => {
    addComment(d);       // still show it in feed
    openCapture(d);      // immediately open modal
  },
};

// ── TikTok connection ──────────────────────────────────────────────────

async function connectTikTok() {
  const username = document.getElementById('input-username').value.trim();
  if (!username) { alert('Enter a TikTok username first'); return; }
  const res = await api('POST', '/api/connect', { username });
  if (!res) return;
  document.getElementById('btn-disconnect').classList.remove('hidden');
}

async function disconnectTikTok() {
  await api('POST', '/api/disconnect');
  setTikTokStatus(false);
}

function setTikTokStatus(connected, username = '') {
  const el = document.getElementById('tiktok-status');
  el.textContent = connected ? `● @${username}` : '● Disconnected';
  el.className = 'status-badge ' + (connected ? 'status-on' : 'status-off');
  document.getElementById('btn-disconnect').classList.toggle('hidden', !connected);
}

// ── Session ────────────────────────────────────────────────────────────

async function startSession() {
  const username = document.getElementById('input-username').value.trim() || 'unknown';
  const res = await api('POST', '/api/sessions/start', { tiktok_user: username });
  if (!res) return;
  applySession(res);
  document.getElementById('mine-log').innerHTML = '';
  mineCount = 0;
  setEl('mine-count', 0);
}

async function endSession() {
  if (!confirm('End session and close mine log?')) return;
  await api('POST', '/api/sessions/end');
  sessionId = null;
  setEl('session-info', '');
  document.getElementById('btn-start-session').classList.remove('hidden');
  document.getElementById('btn-end-session').classList.add('hidden');
}

function applySession(s) {
  sessionId = s.id;
  setEl('session-info', `Session #${s.id} — @${s.tiktok_user}`);
  document.getElementById('btn-start-session').classList.add('hidden');
  document.getElementById('btn-end-session').classList.remove('hidden');
}

// ── Comment feed ───────────────────────────────────────────────────────

function addComment(d) {
  const feed = document.getElementById('comment-feed');
  const isMine = /\bmine\b/i.test(d.text);

  const row = document.createElement('div');
  row.className = 'comment-row' + (isMine ? ' comment-mine' : '');

  // Encode data for onclick — use data attributes to avoid escaping hell
  const data = JSON.stringify(d);
  row.innerHTML = `
    <div class="comment-meta">
      <span class="comment-name">${esc(d.display_name)}</span>
      <span class="comment-handle">@${esc(d.handle)}</span>
    </div>
    <div class="comment-text">${esc(d.text)}</div>
    <button class="btn-mine" data-payload='${esc(data)}' onclick="handleMineBtn(this)">Mine!</button>
  `;

  feed.prepend(row);
  commentCount++;
  setEl('comment-count', commentCount);

  // Cap feed length
  while (feed.children.length > MAX_COMMENTS) feed.removeChild(feed.lastChild);
}

function handleMineBtn(btn) {
  try {
    const d = JSON.parse(btn.dataset.payload);
    openCapture(d);
  } catch (e) {
    console.error('Failed to parse mine data', e);
  }
}

// ── Capture modal ──────────────────────────────────────────────────────

function openCapture(d) {
  if (!sessionId) { alert('Start a session first!'); return; }

  document.getElementById('cap-uid').value    = d.tiktok_uid;
  document.getElementById('cap-name').value   = d.display_name;
  document.getElementById('cap-handle').value = '@' + d.handle;
  document.getElementById('cap-raw').value    = d.text || '';
  document.getElementById('cap-price').value  = '';
  document.getElementById('capture-warning').classList.add('hidden');
  document.getElementById('modal-capture').classList.remove('hidden');

  // Small delay so modal renders before focus
  setTimeout(() => document.getElementById('cap-price').focus(), 80);
}

function closeCapture() {
  document.getElementById('modal-capture').classList.add('hidden');
}

// Close modal on overlay click
document.getElementById('modal-capture').addEventListener('click', function (e) {
  if (e.target === this) closeCapture();
});

// Allow Enter key in price field to submit
document.getElementById('cap-price').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') saveMine();
});

async function saveMine() {
  const price = parseFloat(document.getElementById('cap-price').value);
  if (!price || price <= 0) {
    document.getElementById('cap-price').focus();
    return;
  }

  const payload = {
    tiktok_uid:   document.getElementById('cap-uid').value,
    display_name: document.getElementById('cap-name').value,
    handle:       document.getElementById('cap-handle').value.replace(/^@/, ''),
    price,
    raw_comment:  document.getElementById('cap-raw').value,
  };

  const res = await api('POST', '/api/mines', payload);
  if (!res) return;

  closeCapture();
  addMineToLog(res);

  // Show flag banner if new buyer hit the limit
  if (res.flagged) showFlagBanner(res);
}

// ── Mine log ───────────────────────────────────────────────────────────

function addMineToLog(mine) {
  const log = document.getElementById('mine-log');
  const ts  = new Date(mine.mined_at * 1000).toLocaleTimeString();

  const row = document.createElement('div');
  row.className = 'mine-row' + (mine.flagged ? ' mine-flagged' : '');
  row.innerHTML = `
    <div class="mine-meta">
      <span class="mine-name">${esc(mine.display_name)}</span>
      <span class="mine-handle">@${esc(mine.handle)}</span>
      <span class="mine-badge ${mine.status === 'new' ? 'badge-new' : 'badge-repeat'}">${mine.status}</span>
    </div>
    <div class="mine-price">PHP ${mine.price.toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2})}</div>
    <div class="mine-footer">
      <span class="mine-time">${ts}</span>
      <button class="btn-reprint" onclick="reprintMine(${mine.id})">🖨 Reprint</button>
    </div>
  `;
  log.prepend(row);
  mineCount++;
  setEl('mine-count', mineCount);
}

function showFlagBanner(mine) {
  const logEl = document.getElementById('mine-log');
  const banner = document.createElement('div');
  banner.className = 'flag-banner';
  banner.innerHTML = `⚠️ <strong>${esc(mine.display_name)}</strong> is a NEW buyer — ${mine.session_mine_count} mines this session! Click to dismiss.`;
  banner.addEventListener('click', () => banner.remove());
  logEl.prepend(banner);
}

async function reprintMine(mineId) {
  const res = await api('POST', `/api/mines/${mineId}/reprint`);
  if (res && !res.print_ok) alert('Reprint failed — check printer connection');
}

// ── Utils ──────────────────────────────────────────────────────────────

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  try {
    const res = await fetch(path, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || `Error ${res.status}`);
      return null;
    }
    return res.json();
  } catch (e) {
    console.error(e);
    return null;
  }
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function setEl(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── Init ───────────────────────────────────────────────────────────────

async function init() {
  connectWS();

  const status = await api('GET', '/api/status');
  if (!status) return;

  if (status.tiktok_connected) setTikTokStatus(true);

  if (status.session) {
    applySession(status.session);
    // Load existing mines for this session
    const mines = await api('GET', `/api/sessions/${status.session.id}/mines`) || [];
    mines.forEach(m => addMineToLog({ ...m, flagged: false }));
  }
}

init();
