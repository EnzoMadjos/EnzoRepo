/* ── Miners JS ─────────────────────────────────────────────────────── */

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
  return String(str ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function fmtDate(ts) {
  if (!ts) return '—';
  return new Date(ts * 1000).toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric'
  });
}

async function loadMiners() {
  const data = await api('GET', '/api/miners');
  if (!data) return;
  const tbody = document.getElementById('miner-body');
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="color:var(--text2);text-align:center;padding:24px">No miners yet.</td></tr>';
    return;
  }
  tbody.innerHTML = data.map(m => `
    <tr class="${m.status === 'new' ? 'row-new' : ''}">
      <td>${esc(m.display_name)}</td>
      <td style="color:var(--text2)">@${esc(m.handle)}</td>
      <td><span class="status-pill ${m.status === 'new' ? 'pill-new' : 'pill-repeat'}">${m.status}</span></td>
      <td>${m.total_mines}</td>
      <td style="color:var(--text2)">${fmtDate(m.last_seen)}</td>
      <td class="action-cell">
        ${m.status === 'new'
          ? `<button class="btn btn-green btn-sm" onclick="promote(${m.id}, this)">Mark Repeat</button>`
          : `<span style="color:var(--text2);font-size:12px">repeat</span>`
        }
      </td>
    </tr>
  `).join('');
}

async function promote(buyerId, btn) {
  btn.disabled = true;
  btn.textContent = '...';
  const res = await api('POST', `/api/miners/${buyerId}/promote`);
  if (res) loadMiners();
}

loadMiners();
