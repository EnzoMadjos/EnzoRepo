/**
 * Atlas Modal Dialog Animation
 * Uses anime.js v4 createLayout().update() for FLIP-style card-to-modal transitions.
 * Source: https://animejs.com/documentation/layout/usage/animate-modal-dialog
 *
 * Triggered by .wtile tiles in the orb overlay when the user clicks a widget tile.
 * The tile "morphs" from its on-screen position into a centered dialog showing
 * the full widget content.
 */

let _atlasLayout = null;
let _atlasDialog = null;
let _openTile = null;

/* ── Setup ─────────────────────────────────────────────────────────────────── */

function _initAtlasDialog() {
  if (_atlasDialog) return;

  // Create the native <dialog> element that acts as the expanded modal
  _atlasDialog = document.createElement('dialog');
  _atlasDialog.id = 'atlas-widget-dialog';
  document.body.appendChild(_atlasDialog);

  // Hook anime.js createLayout to track .wtile children inside the dialog root.
  // Specifying children is required since the elements are not yet inside the
  // dialog root at the time of createLayout() — they're cloned into it on open.
  if (window.anime && typeof window.anime.createLayout === 'function') {
    _atlasLayout = window.anime.createLayout(_atlasDialog, {
      children: ['.wtile', '.wtile-dot', '.wtile-name', '.wtile-val'],
      properties: ['--overlay-alpha'],
    });
  }

  // Close on native Escape or click-outside (clicking the backdrop area)
  _atlasDialog.addEventListener('cancel', closeAtlasModal);
  _atlasDialog.addEventListener('click', function (e) {
    if (e.target === _atlasDialog) closeAtlasModal();
  });
}

/* ── Open ──────────────────────────────────────────────────────────────────── */

/**
 * Open the atlas widget dialog with a FLIP animation from a .wtile source.
 * @param {Element} tileEl   The clicked .wtile DOM element (pass `this`).
 * @param {string}  widgetId Widget identifier (clock, weather, system, …).
 */
function openAtlasModal(tileEl, widgetId) {
  _initAtlasDialog();
  if (!_atlasDialog) return;

  _openTile = tileEl;

  // Clone the tile into the dialog (exact pattern from anime.js docs)
  const $clone = tileEl.cloneNode(true);
  $clone.removeAttribute('onclick');       // prevent clone from re-triggering
  $clone.removeAttribute('data-duration'); // cosmetic cleanup

  _atlasDialog.innerHTML = '';             // clear any previous clone
  _atlasDialog.appendChild($clone);        // append clone before calling update()

  const dur = parseInt(tileEl.dataset.duration || '600', 10);

  if (_atlasLayout && typeof _atlasLayout.update === 'function') {
    // ── Exact anime.js docs pattern ──
    // update() records positions BEFORE and AFTER the callback, then animates.
    _atlasLayout.update(() => {
      _atlasDialog.showModal();            // open the native modal
      tileEl.classList.add('is-open');     // hide the source tile
    }, { duration: dur });

    // After the FLIP animation completes, swap the clone for full widget content
    setTimeout(() => {
      if (_atlasDialog.open) _populateDialog(widgetId);
    }, dur + 50);

  } else {
    // Fallback: no animation, just open with content directly
    _atlasDialog.showModal();
    tileEl.classList.add('is-open');
    _populateDialog(widgetId);
  }
}

/* ── Content ───────────────────────────────────────────────────────────────── */

function _populateDialog(widgetId) {
  // _WEX_TITLES and _renderWEx are defined in chat.html's inline <script>
  // and are accessible here since all <script> blocks share the same global scope.
  const title =
    (typeof _WEX_TITLES !== 'undefined' && _WEX_TITLES[widgetId])
      ? _WEX_TITLES[widgetId]
      : widgetId.toUpperCase();

  const body =
    typeof _renderWEx === 'function'
      ? _renderWEx(widgetId)
      : '<p style="opacity:.5;font-size:.75rem">No data available.</p>';

  _atlasDialog.innerHTML = `
    <div class="atd-inner">
      <div class="atd-header">
        <span class="atd-title">${title}</span>
        <button class="atd-close" onclick="closeAtlasModal()">&#x2715;</button>
      </div>
      <div class="atd-body" id="atd-body">${body}</div>
    </div>`;
}

/* ── Close ─────────────────────────────────────────────────────────────────── */

function closeAtlasModal() {
  if (!_atlasDialog || !_atlasDialog.open) return;
  _atlasDialog.close();
  if (_openTile) {
    _openTile.classList.remove('is-open');
    _openTile.focus();
    _openTile = null;
  }
}

/* ── Globals ───────────────────────────────────────────────────────────────── */

window.openAtlasModal  = openAtlasModal;
window.closeAtlasModal = closeAtlasModal;

// Init on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _initAtlasDialog);
} else {
  _initAtlasDialog();
}
