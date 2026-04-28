(function(){
  function getToken(){ return localStorage.getItem('pitogo_token') || localStorage.getItem('token') || ''; }
  function authHeader(){ return { 'Authorization': 'Bearer ' + getToken() }; }
  function authHeaders(){ return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() }; }

  async function fetchJson(url, opts){
    const r = await fetch(url, opts);
    const txt = await r.text();
    if(!r.ok){ throw new Error(txt || r.status); }
    try{ return JSON.parse(txt); }catch(e){ return txt; }
  }

  function ensureToast(){
    let el = document.getElementById('toast');
    if(!el){
      el = document.createElement('div'); el.id = 'toast'; document.body.appendChild(el);
      el.style.position = 'fixed'; el.style.right = '18px'; el.style.bottom = '18px'; el.style.padding = '8px 12px';
      el.style.borderRadius = '8px'; el.style.zIndex = 9999; el.style.display = 'none'; el.style.color = '#fff'; el.style.background = '#333';
    }
    return el;
  }

  var _toastTimer = null;
  function showToast(msg, type){
    const el = ensureToast();
    el.textContent = msg;
    if(type === 'error') el.style.background = '#dc3545';
    else if(type === 'success') el.style.background = '#28a745';
    else if(type === 'warn') el.style.background = '#ffc107';
    else el.style.background = '#333';
    el.style.display = 'block';
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(function(){ el.style.display = 'none'; }, 3200);
  }

  function ensureConfirm(){
    var ov = document.getElementById('confirm-overlay');
    if(!ov){
      ov = document.createElement('div'); ov.id = 'confirm-overlay'; document.body.appendChild(ov);
      ov.style.position = 'fixed'; ov.style.inset = 0; ov.style.background = 'rgba(0,0,0,.45)'; ov.style.display = 'none';
      ov.style.alignItems = 'center'; ov.style.justifyContent = 'center'; ov.style.zIndex = 9998;
      var box = document.createElement('div'); box.className = 'confirm-box';
      box.style.background = '#fff'; box.style.padding = '18px'; box.style.borderRadius = '10px'; box.style.width = '94%'; box.style.maxWidth = '420px'; box.style.boxShadow = '0 6px 24px rgba(0,0,0,.12)';
      var msg = document.createElement('div'); msg.id = 'confirm-message'; msg.textContent = 'Are you sure?'; box.appendChild(msg);
      var actions = document.createElement('div'); actions.className = 'confirm-actions'; actions.style.display='flex'; actions.style.justifyContent='flex-end'; actions.style.gap='8px'; actions.style.marginTop='12px';
      var cancel = document.createElement('button'); cancel.id = 'confirm-cancel'; cancel.className='btn btn-ghost btn-sm'; cancel.textContent='Cancel';
      var ok = document.createElement('button'); ok.id = 'confirm-ok'; ok.className='btn btn-primary btn-sm'; ok.textContent='OK';
      actions.appendChild(cancel); actions.appendChild(ok); box.appendChild(actions); ov.appendChild(box);
    }
    return ov;
  }

  function showConfirm(message){
    return new Promise(function(resolve){
      var ov = ensureConfirm();
      ov.querySelector('#confirm-message').textContent = message;
      ov.style.display = 'flex';
      var ok = ov.querySelector('#confirm-ok');
      var cancel = ov.querySelector('#confirm-cancel');
      function cleanup(){ ov.style.display = 'none'; ok.onclick = null; cancel.onclick = null; }
      ok.onclick = function(){ cleanup(); resolve(true); };
      cancel.onclick = function(){ cleanup(); resolve(false); };
    });
  }

  if(!window.getAuthToken) window.getAuthToken = getToken;
  if(!window.authHeader) window.authHeader = authHeader;
  if(!window.authHeaders) window.authHeaders = authHeaders;
  if(!window.fetchJson) window.fetchJson = fetchJson;
  if(!window.showToast) window.showToast = showToast;
  if(!window.showConfirm) window.showConfirm = showConfirm;
})();
