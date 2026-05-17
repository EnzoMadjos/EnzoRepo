/* ── Inventory JS ──────────────────────────────────────────────────── */

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

// ── Load ───────────────────────────────────────────────────────────────

async function loadProducts() {
  const data = await api('GET', '/api/inventory');
  if (!data) return;
  const tbody = document.getElementById('product-body');
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="5" style="color:var(--text2);text-align:center;padding:24px">No products yet — add one above.</td></tr>';
    return;
  }
  tbody.innerHTML = data.map(p => `
    <tr class="${p.active ? '' : 'row-inactive'}">
      <td>${esc(p.name)}</td>
      <td>PHP ${p.price.toLocaleString(undefined, {minimumFractionDigits:2})}</td>
      <td class="${p.stock === 0 ? 'stock-zero' : p.stock <= 3 ? 'stock-low' : ''}">${p.stock}</td>
      <td><span class="status-pill ${p.active ? 'pill-active' : 'pill-inactive'}">${p.active ? 'Active' : 'Hidden'}</span></td>
      <td class="action-cell">
        <button class="btn btn-ghost btn-sm" onclick="editProduct(${p.id}, ${JSON.stringify(esc(p.name))}, ${p.price}, ${p.stock})">Edit</button>
        <button class="btn btn-ghost btn-sm" onclick="toggleProduct(${p.id})">${p.active ? 'Hide' : 'Show'}</button>
        <button class="btn btn-red btn-sm" onclick="deleteProduct(${p.id}, '${esc(p.name)}')">Delete</button>
      </td>
    </tr>
  `).join('');
}

// ── Create / Update ────────────────────────────────────────────────────

async function submitProduct() {
  const name  = document.getElementById('f-name').value.trim();
  const price = parseFloat(document.getElementById('f-price').value);
  const stock = parseInt(document.getElementById('f-stock').value, 10) || 0;
  const editId = document.getElementById('f-edit-id').value;

  if (!name)          { alert('Product name is required'); return; }
  if (!price || price <= 0) { alert('Enter a valid price'); return; }
  if (stock < 0)      { alert('Stock cannot be negative'); return; }

  if (editId) {
    await api('PUT', `/api/inventory/${editId}`, { name, price, stock });
  } else {
    await api('POST', '/api/inventory', { name, price, stock });
  }

  clearForm();
  loadProducts();
}

function editProduct(id, name, price, stock) {
  document.getElementById('f-edit-id').value = id;
  document.getElementById('f-name').value    = name;
  document.getElementById('f-price').value   = price;
  document.getElementById('f-stock').value   = stock;
  document.getElementById('btn-cancel-edit').classList.remove('hidden');
  document.querySelector('.form-bar .btn-primary').textContent = 'Save Changes';
  document.getElementById('f-name').focus();
}

function cancelEdit() {
  clearForm();
}

function clearForm() {
  document.getElementById('f-edit-id').value = '';
  document.getElementById('f-name').value    = '';
  document.getElementById('f-price').value   = '';
  document.getElementById('f-stock').value   = '';
  document.getElementById('btn-cancel-edit').classList.add('hidden');
  document.querySelector('.form-bar .btn-primary').textContent = 'Add Product';
}

// ── Toggle / Delete ────────────────────────────────────────────────────

async function toggleProduct(id) {
  await api('PATCH', `/api/inventory/${id}/toggle`);
  loadProducts();
}

async function deleteProduct(id, name) {
  if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
  await api('DELETE', `/api/inventory/${id}`);
  loadProducts();
}

// ── Init ───────────────────────────────────────────────────────────────
loadProducts();
