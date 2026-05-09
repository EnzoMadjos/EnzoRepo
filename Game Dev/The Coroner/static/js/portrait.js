/**
 * portrait.js — DiceBear Lorelei avatar wrapper.
 * Same API as before: Portrait.generate(seed) → HTML string to inject into DOM.
 * Seeded deterministically; same seed → same face always.
 * Style: https://www.dicebear.com/styles/lorelei/ (CC0)
 */
(function (global) {
  'use strict';

  var BASE = 'https://api.dicebear.com/9.x/lorelei/svg';

  function generate(seed) {
    var s = encodeURIComponent(seed != null ? String(seed) : 'unknown');
    return '<img src="' + BASE + '?seed=' + s + '" width="100%" height="100%" style="display:block;border-radius:50%;object-fit:cover" alt="portrait">';
  }

  global.Portrait = { generate: generate };

})(typeof window !== 'undefined' ? window : this);
