/* ── Session History Page JS ──────────────────────────────────────── */

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

function fmt(ts) {
  if (!ts) return '—';
  return new Date(ts * 1000).toLocaleString();
}

async function loadHistory() {
  const sessions = await api('GET', '/api/sessions') || [];
  const container = document.getElementById('history-list');
  if (!sessions.length) {
    container.innerHTML = '<p style="color:var(--text2);margin-top:24px">No sessions yet.</p>';
    return;
  }
  container.innerHTML = sessions.map(s => `
    <div class="product-card" style="margin-bottom:12px">
      <div class="product-card-header">
        <span class="product-card-name">${s.title || 'Untitled Session'}</span>
        <span class="product-card-price" style="color:${s.status === 'active' ? 'var(--green)' : 'var(--text2)'}">
          ${s.status === 'active' ? '🟢 Active' : '⭕ Ended'}
        </span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0;font-size:13px">
        <div style="color:var(--text2)">Orders<br><strong style="color:var(--text)">${s.total_orders ?? 0}</strong></div>
        <div style="color:var(--text2)">Revenue<br><strong style="color:var(--green)">₱${(s.total_revenue ?? 0).toLocaleString()}</strong></div>
        <div style="color:var(--text2)">Platform<br><strong style="color:var(--text)">${s.platform || 'manual'}</strong></div>
      </div>
      <div style="font-size:11px;color:var(--text2);margin-bottom:8px">
        Started: ${fmt(s.started_at)} &nbsp;|&nbsp; Ended: ${fmt(s.ended_at)}
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="btn btn-sm btn-gray" onclick="viewOrders(${s.id}, '${(s.title || 'Session').replace(/'/g, "&#39;")}')">View Orders</button>
        <a class="btn btn-sm btn-gray" href="/api/sessions/${s.id}/export.csv" download>⬇ Export CSV</a>
      </div>
    </div>
  `).join('');
}

async function viewOrders(sessionId, title) {
  const orders = await api('GET', `/api/sessions/${sessionId}/orders`) || [];
  document.getElementById('modal-orders-title').textContent = `${title} — Orders`;
  const body = document.getElementById('modal-orders-body');
  if (!orders.length) {
    body.innerHTML = '<p style="color:var(--text2)">No orders in this session.</p>';
  } else {
    body.innerHTML = `
      <table class="variants-table" style="width:100%">
        <thead>
          <tr><th>Buyer</th><th>Product</th><th>Qty</th><th>Total</th><th>Status</th></tr>
        </thead>
        <tbody>
          ${orders.map(o => `
            <tr>
              <td>${o.buyer_name || o.buyer_handle || '—'}</td>
              <td>${o.product_name || '—'}${o.variant_label ? ' / ' + o.variant_label : ''}</td>
              <td>${o.qty}</td>
              <td>₱${(o.total_price || 0).toLocaleString()}</td>
              <td style="color:${o.status === 'confirmed' ? 'var(--green)' : o.status === 'cancelled' ? 'var(--red)' : 'var(--text2)'}">
                ${o.status}
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    `;
  }
  document.getElementById('modal-orders').classList.remove('hidden');
}

loadHistory();
