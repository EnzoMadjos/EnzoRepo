/**
 * demo_mock.js — Frontend-only data layer for Demo Visitor sessions.
 * All data lives in sessionStorage (cleared when the tab closes).
 * No writes ever reach the backend.
 */
(function () {
  if (localStorage.getItem('pitogo_username') !== 'Demo Visitor') return;

  // ── Keys ────────────────────────────────────────────────────────────
  var SK = {
    residents:    'demo_residents',
    households:   'demo_households',
    certificates: 'demo_certificates',
    cert_types:   'demo_cert_types',
    seeded:       'demo_seeded',
  };

  // ── Seed data ────────────────────────────────────────────────────────
  function makeSeedData() {
    var now = new Date().toISOString();
    var ctypes = [
      { id: 'ct-bcl', code: 'BCL', name: 'Barangay Clearance',        template: 'clearance', created_at: now },
      { id: 'ct-cor', code: 'COR', name: 'Certificate of Residency',  template: 'residency', created_at: now },
      { id: 'ct-coi', code: 'COI', name: 'Certificate of Indigency',  template: 'indigency', created_at: now },
    ];
    var residents = [
      { id: 'r-001', first_name: 'Juan',  last_name: 'Dela Cruz', middle_name: '',        birthdate: '1985-03-14', contact_number: '09171234567', national_id: null, household_id: 'h-001', created_at: now, updated_at: now },
      { id: 'r-002', first_name: 'Maria', last_name: 'Santos',    middle_name: 'Reyes',   birthdate: '1992-07-22', contact_number: '09281234567', national_id: null, household_id: 'h-002', created_at: now, updated_at: now },
      { id: 'r-003', first_name: 'Jose',  last_name: 'Rizal',     middle_name: 'Protacio',birthdate: '1978-06-19', contact_number: null,          national_id: null, household_id: null,    created_at: now, updated_at: now },
      { id: 'r-004', first_name: 'Ana',   last_name: 'Bautista',  middle_name: '',        birthdate: '2000-01-05', contact_number: '09391234567', national_id: null, household_id: 'h-001', created_at: now, updated_at: now },
      { id: 'r-005', first_name: 'Pedro', last_name: 'Garcia',    middle_name: 'Lim',     birthdate: '1965-11-30', contact_number: null,          national_id: null, household_id: 'h-002', created_at: now, updated_at: now },
    ];
    var households = [
      { id: 'h-001', address_line: 'Purok 1, Sitio Mahayahay', barangay: 'Pitogo', city: 'Consolacion', zip_code: '6001', head_resident_id: 'r-001', created_at: now, updated_at: now },
      { id: 'h-002', address_line: 'Purok 3, Sitio Riverside',  barangay: 'Pitogo', city: 'Consolacion', zip_code: '6001', head_resident_id: 'r-002', created_at: now, updated_at: now },
    ];
    return { ctypes: ctypes, residents: residents, households: households };
  }

  function ensureSeed() {
    if (sessionStorage.getItem(SK.seeded)) return;
    var d = makeSeedData();
    sessionStorage.setItem(SK.cert_types,   JSON.stringify(d.ctypes));
    sessionStorage.setItem(SK.residents,    JSON.stringify(d.residents));
    sessionStorage.setItem(SK.households,   JSON.stringify(d.households));
    sessionStorage.setItem(SK.certificates, JSON.stringify([]));
    sessionStorage.setItem(SK.seeded, '1');
  }
  ensureSeed();

  // ── Storage helpers ──────────────────────────────────────────────────
  function load(key) {
    try { return JSON.parse(sessionStorage.getItem(key)) || []; } catch(e) { return []; }
  }
  function save(key, data) { sessionStorage.setItem(key, JSON.stringify(data)); }
  function uid() {
    return 'demo-' + Math.random().toString(36).slice(2, 10);
  }
  function now() { return new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC'; }

  // ── Mock response factory ────────────────────────────────────────────
  function ok(data, status) {
    return Promise.resolve(new Response(JSON.stringify(data), {
      status: status || 200,
      headers: { 'Content-Type': 'application/json' }
    }));
  }
  function notFound(msg) {
    return Promise.resolve(new Response(JSON.stringify({ detail: msg || 'Not found' }), {
      status: 404, headers: { 'Content-Type': 'application/json' }
    }));
  }

  // ── Route handlers ───────────────────────────────────────────────────

  function handleResidents(path, method, body) {
    var parts = path.replace(/\?.*/, '').split('/').filter(Boolean); // ['api','residents','<id>']
    var isCollection = parts.length === 2;
    var id = parts[2];

    if (method === 'GET' && isCollection) {
      var q = (path.split('q=')[1] || '').split('&')[0].toLowerCase();
      var list = load(SK.residents);
      if (q) list = list.filter(function(r) {
        return (r.first_name + ' ' + r.last_name + ' ' + (r.national_id || '')).toLowerCase().includes(q);
      });
      return ok(list);
    }
    if (method === 'POST' && isCollection) {
      var list = load(SK.residents);
      var item = Object.assign({ id: uid(), created_at: now(), updated_at: now(), national_id: null, household_id: null, middle_name: null, contact_number: null }, body);
      list.push(item);
      save(SK.residents, list);
      return ok(item, 201);
    }
    if (method === 'GET' && id) {
      var item = load(SK.residents).find(function(r) { return r.id === id; });
      return item ? ok(item) : notFound();
    }
    if ((method === 'PUT' || method === 'PATCH') && id) {
      var list = load(SK.residents);
      var idx = list.findIndex(function(r) { return r.id === id; });
      if (idx < 0) return notFound();
      list[idx] = Object.assign({}, list[idx], body, { updated_at: now() });
      save(SK.residents, list);
      return ok(list[idx]);
    }
    if (method === 'DELETE' && id) {
      var list = load(SK.residents).filter(function(r) { return r.id !== id; });
      save(SK.residents, list);
      return ok({ status: 'deleted' });
    }
    return ok([]);
  }

  function handleHouseholds(path, method, body) {
    var parts = path.replace(/\?.*/, '').split('/').filter(Boolean);
    var isCollection = parts.length === 2;
    var id = parts[2];

    if (method === 'GET' && isCollection) {
      return ok(load(SK.households));
    }
    if (method === 'POST' && isCollection) {
      var list = load(SK.households);
      var item = Object.assign({ id: uid(), created_at: now(), updated_at: now(), head_resident_id: null, zip_code: null }, body);
      list.push(item);
      save(SK.households, list);
      return ok(item, 201);
    }
    if (method === 'GET' && id) {
      var item = load(SK.households).find(function(h) { return h.id === id; });
      return item ? ok(item) : notFound();
    }
    if ((method === 'PUT' || method === 'PATCH') && id) {
      var list = load(SK.households);
      var idx = list.findIndex(function(h) { return h.id === id; });
      if (idx < 0) return notFound();
      list[idx] = Object.assign({}, list[idx], body, { updated_at: now() });
      save(SK.households, list);
      return ok(list[idx]);
    }
    if (method === 'DELETE' && id) {
      var list = load(SK.households).filter(function(h) { return h.id !== id; });
      save(SK.households, list);
      return ok({ status: 'deleted' });
    }
    return ok([]);
  }

  function handleCertTypes(path, method, body) {
    var parts = path.replace(/\?.*/, '').split('/').filter(Boolean);
    var id = parts[2];

    if (method === 'GET' && !id) return ok(load(SK.cert_types));
    if (method === 'GET' && id) {
      var item = load(SK.cert_types).find(function(t) { return t.id === id; });
      return item ? ok(item) : notFound();
    }
    if (method === 'POST') {
      var list = load(SK.cert_types);
      var item = Object.assign({ id: uid(), created_at: now() }, body);
      list.push(item);
      save(SK.cert_types, list);
      return ok(item, 201);
    }
    if (method === 'DELETE' && id) {
      save(SK.cert_types, load(SK.cert_types).filter(function(t) { return t.id !== id; }));
      return ok({ status: 'deleted' });
    }
    return ok([]);
  }

  function handleCertificates(path, method, body) {
    var parts = path.replace(/\?.*/, '').split('/').filter(Boolean);
    // ['api','certificates'] or ['api','certificates','<id>'] or ['api','certificates','<id>','preview']
    var id   = parts[2];
    var sub  = parts[3]; // 'preview' | 'generate' | 'render'

    // Collection
    if (method === 'GET' && !id) {
      var q = (path.split('q=')[1] || '').split('&')[0].toLowerCase();
      var list = load(SK.certificates);
      if (q) list = list.filter(function(c) {
        return (c.resident_name + ' ' + c.control_number + ' ' + c.certificate_type_name).toLowerCase().includes(q);
      });
      return ok(list);
    }
    if (path.includes('/recent')) {
      var recent = load(SK.certificates).slice(-10).reverse();
      return ok(recent);
    }
    if (path.includes('/export')) {
      return ok([]); // export not available in demo
    }

    // Create certificate
    if (method === 'POST' && !id) {
      var certTypes = load(SK.cert_types);
      var residents = load(SK.residents);
      var ct = certTypes.find(function(t) { return t.id === body.certificate_type_id; }) || certTypes[0] || {};
      var res = residents.find(function(r) { return r.id === body.resident_id; }) || {};
      var seq = load(SK.certificates).length + 1;
      var ctrl = 'DEMO-' + new Date().getFullYear() + '-' + String(seq).padStart(4, '0');
      var item = {
        id: uid(),
        control_number: ctrl,
        certificate_type_id: ct.id,
        certificate_type_name: ct.name,
        resident_id: res.id,
        resident_name: (res.first_name || '') + ' ' + (res.last_name || ''),
        issued_by: 'Demo Visitor',
        issued_at: new Date().toISOString(),
        finalized_at: null,
        voided_at: null,
        status: 'issued',
        meta: body.meta || {},
        pdf_path: null,
        _ct: ct,
        _res: res,
      };
      var list = load(SK.certificates);
      list.push(item);
      save(SK.certificates, list);
      return ok(item, 201);
    }

    var cert = id ? load(SK.certificates).find(function(c) { return c.id === id; }) : null;
    if (!cert && id && sub !== 'preview' && sub !== 'generate' && sub !== 'render') return notFound();

    // Preview — return rendered HTML blob
    if (sub === 'preview' || sub === 'render') {
      var html = _buildDemoCertHtml(cert);
      return ok({ html: html });
    }

    // Generate — open preview in new tab as blob, return fake download_url
    if (sub === 'generate' && method === 'POST') {
      var html = _buildDemoCertHtml(cert);
      var blob = new Blob([html], { type: 'text/html' });
      var blobUrl = URL.createObjectURL(blob);
      // Finalize in storage
      var list = load(SK.certificates);
      var idx = list.findIndex(function(c) { return c.id === cert.id; });
      if (idx >= 0) { list[idx].finalized_at = new Date().toISOString(); save(SK.certificates, list); }
      window.open(blobUrl, '_blank');
      return ok({ download_url: blobUrl, control_number: cert.control_number });
    }

    if (method === 'GET' && cert) return ok(cert);
    if (method === 'DELETE' && cert) {
      save(SK.certificates, load(SK.certificates).filter(function(c) { return c.id !== cert.id; }));
      return ok({ status: 'deleted' });
    }

    return ok({});
  }

  function _buildDemoCertHtml(cert) {
    var ct = (cert && cert._ct) || {};
    var res = (cert && cert._res) || {};
    var meta = (cert && cert.meta) || {};
    var resName = (res.first_name || '') + ' ' + (res.last_name || '');
    var ctName = ct.name || 'Certificate';
    var purpose = meta.purpose || 'General Purpose';
    var address = meta.address || 'Pitogo, Consolacion, Cebu';
    var issued = cert ? new Date(cert.issued_at).toLocaleDateString('en-PH', {year:'numeric',month:'long',day:'numeric'}) : '';
    var ctrl = cert ? cert.control_number : '';
    return '<!doctype html><html><head><meta charset="utf-8"><title>' + ctName + '</title>' +
      '<style>body{font-family:Georgia,serif;padding:48px;max-width:680px;margin:0 auto;color:#111}' +
      '.header{text-align:center;border-bottom:4px double #CE1126;padding-bottom:16px;margin-bottom:28px}' +
      '.seal{width:80px;height:80px;border-radius:50%;border:2px solid #CE1126;display:block;margin:0 auto 8px}' +
      'h1{color:#CE1126;margin:4px 0;font-size:1.3rem}' +
      'h2{color:#0038A8;font-size:.95rem;margin:2px 0;font-weight:normal}' +
      '.slogan{color:#0038A8;font-style:italic;font-size:.8rem}' +
      '.body{line-height:1.8;margin-bottom:32px}' +
      '.ctrl{font-size:.75rem;color:#888;text-align:right;margin-top:32px;border-top:1px solid #eee;padding-top:8px}' +
      '.demo-watermark{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%) rotate(-35deg);font-size:4rem;color:rgba(206,17,38,.1);font-weight:900;pointer-events:none;white-space:nowrap}' +
      '</style></head><body>' +
      '<div class="demo-watermark">DEMO ONLY</div>' +
      '<div class="header">' +
      '<img class="seal" src="/static/img/seal.png" onerror="this.style.display=\'none\'" />' +
      '<h1>Republic of the Philippines</h1>' +
      '<h2>Province of Cebu &bull; Municipality of Consolacion</h2>' +
      '<h1>Barangay Pitogo</h1>' +
      '<div class="slogan">#Asenso Pitogo — Office of the Punong Barangay</div>' +
      '</div>' +
      '<h1 style="text-align:center;color:#CE1126;font-size:1.5rem;margin-bottom:24px">' + ctName.toUpperCase() + '</h1>' +
      '<div class="body">' +
      '<p>To whom it may concern:</p><br>' +
      '<p>This is to certify that <strong>' + resName + '</strong>, ' +
      'a resident of <em>' + address + '</em>, ' +
      'is a bonafide resident of this barangay in good moral standing.</p><br>' +
      '<p>This certification is being issued upon request of the above-named individual for the purpose of <strong>' + purpose + '</strong>.</p><br>' +
      '<p>Issued this day <strong>' + issued + '</strong> at the Office of the Punong Barangay, Barangay Pitogo, Consolacion, Cebu.</p>' +
      '</div>' +
      '<p style="margin-top:48px">__________________________________<br><strong>Punong Barangay</strong><br>Barangay Pitogo</p>' +
      '<div class="ctrl">Control No: ' + ctrl + ' &nbsp;&bull;&nbsp; [DEMO — not an official document]</div>' +
      '</body></html>';
  }

  function handleDashboardStats() {
    var certs = load(SK.certificates);
    var residents = load(SK.residents);
    var households = load(SK.households);
    var today = new Date().toDateString();
    var thisMonth = new Date().getMonth();
    var recent = certs.slice(-10).reverse().map(function(c) {
      return {
        id: c.id,
        control_number: c.control_number,
        resident_name: c.resident_name,
        certificate_type_name: c.certificate_type_name,
        issued_by: c.issued_by,
        issued_at: c.issued_at,
        status: c.status,
        finalized_at: c.finalized_at,
      };
    });
    return ok({
      certs_today:      certs.filter(function(c) { return new Date(c.issued_at).toDateString() === today; }).length,
      certs_month:      certs.filter(function(c) { return new Date(c.issued_at).getMonth() === thisMonth; }).length,
      certs_total:      certs.length,
      residents_total:  residents.length,
      households_total: households.length,
      recent_certs:     recent,
    });
  }

  function handleUsers(path, method) {
    if (path.includes('/me')) {
      return ok({ id: 'demo-user', username: 'demo_visitor', full_name: 'Demo Visitor', role: 'clerk', active: true });
    }
    return ok([{ id: 'demo-user', username: 'demo_visitor', full_name: 'Demo Visitor', role: 'clerk', active: true }]);
  }

  function handleAudit() {
    return ok([]);
  }

  function handleAttachments(path, method) {
    if (method === 'POST') return ok({ id: uid(), original_filename: 'demo-upload.pdf', stored_path: '' }, 201);
    return ok([]);
  }

  // ── Fetch interceptor ────────────────────────────────────────────────
  var _realFetch = window.fetch;
  window.fetch = function (input, opts) {
    var url = typeof input === 'string' ? input : (input && input.url) || '';
    var method = ((opts && opts.method) || 'GET').toUpperCase();
    var body = {};
    if (opts && opts.body) {
      try { body = JSON.parse(opts.body); } catch(e) { body = {}; }
    }

    // Only intercept relative API paths
    if (!url.startsWith('/api/') && !url.match(/^https?:\/\/(localhost|127\.0\.0\.1)[:/]/)) {
      return _realFetch(input, opts);
    }
    // Normalise to path only
    var path = url.replace(/^https?:\/\/[^/]+/, '');

    // Feedback still goes to real backend (we want those!)
    if (path.startsWith('/api/feedback')) return _realFetch(input, opts);
    // Demo start not needed — we handle locally
    if (path.startsWith('/api/demo')) return ok({ token: 'demo-mode', username: 'Demo Visitor', role: 'clerk' });

    if (path.startsWith('/api/residents'))        return handleResidents(path, method, body);
    if (path.startsWith('/api/households'))        return handleHouseholds(path, method, body);
    if (path.startsWith('/api/certificate-types')) return handleCertTypes(path, method, body);
    if (path.startsWith('/api/certificates'))      return handleCertificates(path, method, body);
    if (path.startsWith('/api/dashboard'))         return handleDashboardStats();
    if (path.startsWith('/api/users'))             return handleUsers(path, method);
    if (path.startsWith('/api/audit'))             return handleAudit();
    if (path.startsWith('/api/attachments'))       return handleAttachments(path, method);

    // Pass through anything else
    return _realFetch(input, opts);
  };

})();
