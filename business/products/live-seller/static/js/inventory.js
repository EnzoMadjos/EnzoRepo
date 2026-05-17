/* ── Inventory Page JS ──────────────────────────────────────────── */

let allProducts = [];

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

async function loadProducts() {
  allProducts = await api('GET', '/api/products') || [];
  renderProducts();
}

function renderProducts() {
  const container = document.getElementById('products-list');
  container.innerHTML = '';
  if (!allProducts.length) {
    container.innerHTML = '<p style="color:var(--text2)">No products yet — add one above!</p>';
    return;
  }
  allProducts.forEach(p => {
    const card = document.createElement('div');
    card.className = 'product-card';
    const variantsRows = (p.variants || []).map(v => `
      <tr>
        <td>${v.label}</td>
        <td>
          <div class="stock-adj">
            <button class="btn btn-sm btn-gray" onclick="adjustStock(${v.id}, -1)">−</button>
            <span style="min-width:32px;text-align:center">${v.stock}</span>
            <button class="btn btn-sm btn-gray" onclick="adjustStock(${v.id}, 1)">+</button>
          </div>
        </td>
        <td>₱${(p.base_price + v.price_modifier).toLocaleString()}</td>
      </tr>
    `).join('');
    card.innerHTML = `
      <div class="product-card-header">
        <span class="product-card-name">${p.name}</span>
        <div style="display:flex;gap:8px;align-items:center">
          <span class="product-card-price">₱${p.base_price.toLocaleString()}</span>
          <button class="btn btn-sm ${p.is_active ? 'btn-gray' : 'btn-green'}" onclick="toggleProduct(${p.id})">
            ${p.is_active ? '🟢 Active' : '⭕ Inactive'}
          </button>
        </div>
      </div>
      ${p.description ? `<p style="color:var(--text2);font-size:12px;margin-bottom:8px">${p.description}</p>` : ''}
      ${p.variants?.length ? `
        <table class="variants-table">
          <thead><tr><th>Variant</th><th>Stock</th><th>Price</th></tr></thead>
          <tbody>${variantsRows}</tbody>
        </table>
      ` : '<p style="color:var(--text2);font-size:12px">No variants</p>'}
      <div style="margin-top:8px;display:flex;gap:8px">
        <button class="btn btn-sm btn-gray" onclick="openAddVariant(${p.id})">+ Add Variant</button>
        <button class="btn btn-sm btn-red" onclick="deleteProduct(${p.id}, '${p.name.replace(/'/g, "&#39;")}')">🗑 Delete</button>
      </div>
    `;
    container.appendChild(card);
  });
}

async function deleteProduct(productId, name) {
  if (!confirm(`Delete "${name}" and all its variants? This cannot be undone.`)) return;
  await api('DELETE', `/api/products/${productId}`);
  await loadProducts();
}

async function adjustStock(variantId, delta) {
  await api('PATCH', `/api/products/variants/${variantId}/stock`, { delta });
  await loadProducts();
}

async function toggleProduct(productId) {
  await api('PATCH', `/api/products/${productId}/toggle`);
  await loadProducts();
}

function openAddProduct() {
  document.getElementById('modal-add-product').classList.remove('hidden');
  document.getElementById('variants-input').innerHTML = `
    <div class="variant-row">
      <input type="text" placeholder="e.g. Red / M" class="v-label">
      <input type="number" placeholder="0" class="v-stock" value="0" min="0">
      <input type="number" placeholder="0" class="v-price" value="0">
    </div>
  `;
}

function addVariantRow() {
  const row = document.createElement('div');
  row.className = 'variant-row';
  row.innerHTML = `
    <input type="text" placeholder="e.g. Blue / L" class="v-label">
    <input type="number" placeholder="0" class="v-stock" value="0" min="0">
    <input type="number" placeholder="0" class="v-price" value="0">
  `;
  document.getElementById('variants-input').appendChild(row);
}

async function saveProduct() {
  const name  = document.getElementById('p-name').value.trim();
  const price = parseFloat(document.getElementById('p-price').value) || 0;
  const desc  = document.getElementById('p-desc').value.trim();
  if (!name) { alert('Product name required'); return; }

  const res = await api('POST', '/api/products', { name, base_price: price, description: desc });
  if (!res) return;
  const productId = res.id;

  // Save variants
  const rows = document.querySelectorAll('#variants-input .variant-row');
  for (const row of rows) {
    const label = row.querySelector('.v-label').value.trim();
    const stock = parseInt(row.querySelector('.v-stock').value) || 0;
    const mod   = parseFloat(row.querySelector('.v-price').value) || 0;
    if (label) {
      await api('POST', `/api/products/${productId}/variants`, { label, stock, price_modifier: mod });
    }
  }

  closeModal('modal-add-product');
  await loadProducts();
}

// Add variant to existing product
let addVariantProductId = null;
function openAddVariant(productId) {
  addVariantProductId = productId;
  const label = prompt('Variant label (e.g. Red / L):');
  if (!label) return;
  const stock = parseInt(prompt('Initial stock:', '0')) || 0;
  const mod   = parseFloat(prompt('Price modifier (+/-) :', '0')) || 0;
  api('POST', `/api/products/${productId}/variants`, { label, stock, price_modifier: mod })
    .then(() => loadProducts());
}

loadProducts();
