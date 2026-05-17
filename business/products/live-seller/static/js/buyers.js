/* ── Mine Tracker — Buyers JS ───────────────────────────────────────── */

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  if (!res.ok) return null;
  return res.json();
}

function fmt(ts) {
  if (!ts) return '—';
  return new Date(ts * 1000).toLocaleString();
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function loadBuyers() {
  const buyers = await api('GET', '/api/buyers') || [];
  const tbody = document.getElementById('buyers-tbody');

  if (!buyers.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--text2);text-align:center;padding:32px">No buyers yet.</td></tr>';
    return;
  }

  tbody.innerHTML = buyers.map(b => `
    <tr class="${b.status === 'new' ? 'row-new' : ''}">
      <td>${esc(b.display_name)}</td>
      <td style="color:var(--text2)">@${esc(b.handle)}</td>
      <td><span class="status-pill ${b.status === 'new' ? 'pill-new' : 'pill-repeat'}">${b.status}</span></td>
      <td>${b.total_mines}</td>
      <td style="color:var(--text2);font-size:12px">${fmt(b.last_seen)}</td>
      <td>
        ${b.status === 'new'
          ? `<button class="btn btn-sm btn-green" onclick="promote(${b.id}, this)">✓ Mark as Repeat</button>`
          : ''}
      </td>
    </tr>
  `).join('');
}

async function promote(buyerId, btn) {
  const res = await api('POST', `/api/buyers/${buyerId}/promote`);
  if (!res) return;

  const row = btn.closest('tr');
  row.classList.remove('row-new');
  row.querySelector('.status-pill').className = 'status-pill pill-repeat';
  row.querySelector('.status-pill').textContent = 'repeat';
  btn.remove();
}

loadBuyers();
