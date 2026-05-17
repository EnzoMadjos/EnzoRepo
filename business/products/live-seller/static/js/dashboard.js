/* ── State ──────────────────────────────────────────────────────── */
let ws = null;
let wsReconnectDelay = 1000;
let activeSessionId = null;
let products = [];
let commentCount = 0;
let pendingCount = 0;
let bidTimers = {};  // bid_session_id → interval id

/* ── WebSocket ──────────────────────────────────────────────────── */
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws/dashboard`);

  ws.onopen = () => {
    document.getElementById('ws-status').classList.add('connected');
    wsReconnectDelay = 1000;
    // Heartbeat
    setInterval(() => { if (ws.readyState === 1) ws.send('ping'); }, 20000);
  };

  ws.onclose = () => {
    document.getElementById('ws-status').classList.remove('connected');
    setTimeout(connectWS, wsReconnectDelay);
    wsReconnectDelay = Math.min(wsReconnectDelay * 2, 15000);
  };

  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      handleEvent(msg.type, msg.data);
    } catch (_) {}
  };
}

function handleEvent(type, data) {
  switch (type) {
    case 'init':
      if (data.session) setSessionActive(data.session);
      products = data.products || [];
      renderInventory(products);
      break;
    case 'session_started':
      setSessionActive(data);
      break;
    case 'session_ended':
      setSessionInactive();
      break;
    case 'comment':
      addComment(data.text, 'normal');
      break;
    case 'comment_unmatched':
      addComment(`⚠️ No match: ${data.text}`, 'normal');
      break;
    case 'order_pending':
      addComment(`🟡 Order: ${data.raw_comment}`, 'order-candidate');
      addOrderCard(data, false);
      break;
    case 'order_confirmed':
      addComment(`✅ Confirmed: ${data.buyer_name} — ${data.product_name}`, 'confirmed');
      upsertOrderCard(data, true);
      updateStats();
      break;
    case 'order_cancelled':
      markOrderCancelled(data.order_id);
      break;
    case 'bid_opened':
      addComment(`🏷️ Bid opened: ${data.title || 'Item'} — starting ₱${data.starting_price}`, 'bid-candidate');
      fetchActiveBids();
      break;
    case 'bid_updated':
      updateBidCard(data);
      addComment(`💰 Bid ₱${data.amount}`, 'bid-candidate');
      break;
    case 'bid_closed':
      if (data.winner) {
        addComment(`🏆 Bid winner: @${data.winner.handle || data.winner.display_name} — ₱${data.winner.amount}`, 'confirmed');
      } else {
        addComment('🏷️ Bid closed — no bids', 'normal');
      }
      fetchActiveBids();
      break;
    case 'session_stats':
      renderStats(data);
      break;
    case 'inventory_update':
      fetchInventory();
      break;
  }
}

/* ── Session ────────────────────────────────────────────────────── */
function startSession() {
  document.getElementById('modal-start-session').classList.remove('hidden');
}

async function confirmStartSession() {
  const title    = document.getElementById('session-title').value;
  const platform = document.getElementById('session-platform').value;
  closeModal('modal-start-session');
  const res = await api('POST', '/api/sessions/start', { title, platform });
  if (!res) return;
  activeSessionId = res.session_id;
}

async function endSession() {
  if (!confirm('End the live session?')) return;
  await api('POST', '/api/sessions/end');
}

function setSessionActive(stats) {
  activeSessionId = stats.session_id;
  document.getElementById('session-info').textContent =
    `Session #${stats.session_id} — ${stats.title || 'Live'} 🔴`;
  document.getElementById('btn-start-session').classList.add('hidden');
  document.getElementById('btn-end-session').classList.remove('hidden');
  renderStats(stats);
}

function setSessionInactive() {
  activeSessionId = null;
  document.getElementById('session-info').textContent = 'No active session';
  document.getElementById('btn-start-session').classList.remove('hidden');
  document.getElementById('btn-end-session').classList.add('hidden');
}

/* ── Stats ──────────────────────────────────────────────────────── */
async function updateStats() {
  if (!activeSessionId) return;
  try {
    const data = await api('GET', '/api/sessions/stats');
    renderStats(data);
  } catch (_) {}
}

function renderStats(s) {
  if (!s || s.active === false) return;
  document.getElementById('stat-orders').textContent  = s.total_orders || 0;
  document.getElementById('stat-revenue').textContent = `₱${(s.total_revenue || 0).toLocaleString()}`;
  document.getElementById('stat-buyers').textContent  = s.unique_buyers || 0;
}

setInterval(updateStats, 10000);

/* ── Comments ───────────────────────────────────────────────────── */
function addComment(text, cls = 'normal') {
  const feed = document.getElementById('comment-feed');
  const div = document.createElement('div');
  div.className = `comment-item ${cls}`;
  div.textContent = text;
  feed.appendChild(div);
  feed.scrollTop = feed.scrollHeight;
  // Keep max 200 comments in DOM
  while (feed.children.length > 200) feed.removeChild(feed.firstChild);
  commentCount++;
  document.getElementById('comments-count').textContent = commentCount;
}

async function pasteComments() {
  const text = document.getElementById('paste-box').value.trim();
  if (!text) return;
  if (!activeSessionId) { alert('Start a session first'); return; }
  await api('POST', '/api/comments/paste', { text });
  document.getElementById('paste-box').value = '';
}

// Also allow Ctrl+V anywhere on the page → auto-send to paste endpoint
document.addEventListener('paste', async (e) => {
  if (document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'INPUT') return;
  const text = e.clipboardData.getData('text').trim();
  if (!text || !activeSessionId) return;
  await api('POST', '/api/comments/paste', { text });
  addComment(`📋 Pasted ${text.split('\n').length} lines`, 'normal');
});

/* ── Orders ─────────────────────────────────────────────────────── */
function addOrderCard(order, confirmed) {
  const list = document.getElementById('order-list');
  const card = buildOrderCard(order, confirmed);
  list.insertBefore(card, list.firstChild);
  if (!confirmed) {
    pendingCount++;
    document.getElementById('pending-count').textContent = pendingCount;
  }
}

function upsertOrderCard(order, confirmed) {
  const existing = document.getElementById(`order-${order.id}`);
  if (existing) {
    existing.outerHTML = buildOrderCard(order, true).outerHTML;
  } else {
    addOrderCard(order, confirmed);
  }
  if (confirmed && pendingCount > 0) {
    pendingCount--;
    document.getElementById('pending-count').textContent = pendingCount;
  }
}

function markOrderCancelled(orderId) {
  const el = document.getElementById(`order-${orderId}`);
  if (el) { el.className = 'order-card cancelled'; el.querySelector('.order-actions').innerHTML = '<span style="color:var(--red)">Cancelled</span>'; }
}

function buildOrderCard(o, confirmed) {
  const div = document.createElement('div');
  div.id = `order-${o.id}`;
  div.className = `order-card ${confirmed ? 'confirmed' : 'pending'}`;
  const conf = o.confidence ? `${Math.round(o.confidence * 100)}%` : '';
  const variant = o.variant_label ? ` [${o.variant_label}]` : '';
  div.innerHTML = `
    <div class="order-top">
      <span class="order-buyer">${o.buyer_name || 'Customer'}</span>
      <span class="order-price">₱${(o.total_price || 0).toLocaleString()}</span>
    </div>
    <div class="order-detail">${o.product_name}${variant} × ${o.qty}</div>
    <div class="order-raw">"${o.raw_comment || ''}"</div>
    ${conf ? `<div class="order-conf">AI confidence: ${conf}</div>` : ''}
    <div class="order-actions">
      ${!confirmed ? `
        <button class="btn btn-sm btn-green" onclick="confirmOrder(${o.id})">✓ Confirm</button>
        <button class="btn btn-sm btn-red" onclick="cancelOrder(${o.id})">✗ Cancel</button>
      ` : `<span style="color:var(--green);font-size:12px">✅ Confirmed</span>`}
    </div>
  `;
  return div;
}

async function confirmOrder(id) {
  await api('POST', `/api/orders/${id}/confirm`);
}

async function cancelOrder(id) {
  await api('POST', `/api/orders/${id}/cancel`);
}

/* ── Inventory ──────────────────────────────────────────────────── */
async function fetchInventory() {
  products = await api('GET', '/api/products');
  renderInventory(products);
}

function renderInventory(prods) {
  const el = document.getElementById('inventory-list');
  if (!el) return;
  el.innerHTML = '';
  prods.filter(p => p.is_active).forEach(p => {
    const div = document.createElement('div');
    div.className = 'inv-item';
    const maxStock = Math.max(...(p.variants.map(v => v.stock)), 1);
    const variantsHtml = (p.variants || []).map(v => {
      const pct = Math.round((v.stock / Math.max(maxStock, 1)) * 100);
      const low = v.stock <= 2;
      return `<div class="inv-variant-row">
        <span style="flex:1">${v.label}</span>
        <div class="inv-bar"><div class="inv-fill ${low ? 'low' : ''}" style="width:${pct}%"></div></div>
        <span class="inv-stock ${low ? 'style=color:var(--red)' : ''}">${v.stock}</span>
      </div>`;
    }).join('');
    div.innerHTML = `<div class="inv-name">${p.name}</div>${variantsHtml || '<div style="color:var(--text2);font-size:12px">No variants</div>'}`;
    el.appendChild(div);
  });
}

fetchInventory();

/* ── Bids ───────────────────────────────────────────────────────── */
function openNewBidModal() {
  if (!activeSessionId) { alert('Start a session first'); return; }
  const sel = document.getElementById('bid-product');
  sel.innerHTML = '';
  products.filter(p => p.is_active).forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id; opt.textContent = p.name;
    sel.appendChild(opt);
  });
  updateBidVariants();
  document.getElementById('modal-new-bid').classList.remove('hidden');
}

function updateBidVariants() {
  const pid = parseInt(document.getElementById('bid-product').value);
  const p = products.find(x => x.id === pid);
  const sel = document.getElementById('bid-variant');
  sel.innerHTML = '<option value="">No variant</option>';
  (p?.variants || []).forEach(v => {
    const opt = document.createElement('option');
    opt.value = v.id; opt.textContent = `${v.label} (stock: ${v.stock})`;
    sel.appendChild(opt);
  });
}
document.getElementById('bid-product')?.addEventListener('change', updateBidVariants);

async function confirmOpenBid() {
  const body = {
    product_id:       parseInt(document.getElementById('bid-product').value),
    variant_id:       document.getElementById('bid-variant').value ? parseInt(document.getElementById('bid-variant').value) : null,
    title:            document.getElementById('bid-title').value,
    starting_price:   parseFloat(document.getElementById('bid-start').value),
    min_increment:    parseFloat(document.getElementById('bid-increment').value),
    countdown_seconds: parseInt(document.getElementById('bid-countdown').value),
  };
  closeModal('modal-new-bid');
  await api('POST', '/api/bids/open', body);
}

async function fetchActiveBids() {
  if (!activeSessionId) return;
  const bids = await api('GET', '/api/bids/active');
  renderBids(bids);
}

function renderBids(bids) {
  const container = document.getElementById('bids-container');
  // Clear dead timers
  Object.keys(bidTimers).forEach(id => {
    if (!bids.find(b => b.id === parseInt(id))) {
      clearInterval(bidTimers[id]);
      delete bidTimers[id];
    }
  });
  container.innerHTML = '';
  if (!bids.length) {
    container.innerHTML = '<div style="color:var(--text2);font-size:12px;padding:8px">No active bids</div>';
    return;
  }
  bids.forEach(b => {
    const div = document.createElement('div');
    div.className = 'bid-card';
    div.id = `bid-${b.id}`;
    const remaining = b.ends_at ? Math.max(0, b.ends_at - Math.floor(Date.now() / 1000)) : '?';
    div.innerHTML = `
      <div class="bid-title">${b.title || b.product_name}</div>
      <div class="bid-top-row">
        <span class="bid-current">₱${(b.current_highest_bid || b.starting_price).toLocaleString()}</span>
        <span class="bid-countdown" id="bid-timer-${b.id}">${remaining}s</span>
      </div>
      <div class="bid-winner">Top: <span>${b.winner_name ? `@${b.winner_handle || b.winner_name}` : '—'}</span></div>
      <div id="bid-lb-${b.id}" class="leaderboard"></div>
      <button class="btn btn-sm btn-red" onclick="closeBid(${b.id})">Close Bid</button>
    `;
    container.appendChild(div);
    // Countdown timer
    if (b.ends_at && !bidTimers[b.id]) {
      bidTimers[b.id] = setInterval(() => {
        const el = document.getElementById(`bid-timer-${b.id}`);
        if (!el) { clearInterval(bidTimers[b.id]); return; }
        const left = Math.max(0, b.ends_at - Math.floor(Date.now() / 1000));
        el.textContent = `${left}s`;
        if (left === 0) { clearInterval(bidTimers[b.id]); delete bidTimers[b.id]; }
      }, 1000);
    }
    // Load leaderboard
    api('GET', `/api/bids/${b.id}/leaderboard`).then(lb => renderLeaderboard(b.id, lb));
  });
}

function renderLeaderboard(bidId, lb) {
  const el = document.getElementById(`bid-lb-${bidId}`);
  if (!el) return;
  el.innerHTML = lb.slice(0, 5).map((r, i) =>
    `<div class="leaderboard-row ${i === 0 ? 'top' : ''}">
      <span>${i + 1}. @${r.handle || r.display_name}</span>
      <span>₱${r.amount.toLocaleString()}</span>
    </div>`
  ).join('');
}

function updateBidCard(data) {
  const card = document.getElementById(`bid-${data.bid_session_id}`);
  if (!card) { fetchActiveBids(); return; }
  const cur = card.querySelector('.bid-current');
  if (cur) cur.textContent = `₱${data.amount.toLocaleString()}`;
  if (data.leaderboard) renderLeaderboard(data.bid_session_id, data.leaderboard);
}

async function closeBid(id) {
  await api('POST', `/api/bids/${id}/close`);
}

/* ── Utilities ──────────────────────────────────────────────────── */
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) { console.error(method, path, res.status); return null; }
  return res.json();
}

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

/* ── Boot ───────────────────────────────────────────────────────── */
connectWS();
fetchActiveBids();
