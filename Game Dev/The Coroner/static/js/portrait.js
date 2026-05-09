/**
 * portrait.js — Deterministic procedural SVG portrait generator.
 * Seeded by a string (portrait_seed from DB). Same seed → same face always.
 * Returns an SVG string; caller inserts it into the DOM.
 *
 * Anatomy generated:
 *   skin tone, face shape, eyes (colour/shape), nose, mouth, hair (style/colour),
 *   eyebrows, optional features (glasses, stubble, scar, freckles)
 */

(function (global) {
  'use strict';

  // ── PRNG (mulberry32, seeded from string hash) ─────────────────────────
  function hashSeed(str) {
    let h = 2166136261;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = (h * 16777619) >>> 0;
    }
    return h;
  }

  function makePRNG(seed) {
    let s = typeof seed === 'string' ? hashSeed(seed) : (seed >>> 0);
    return function () {
      s += 0x6D2B79F5;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function pick(rng, arr) { return arr[Math.floor(rng() * arr.length)]; }
  function rngRange(rng, min, max) { return min + rng() * (max - min); }
  function rngInt(rng, min, max) { return Math.floor(rngRange(rng, min, max)); }

  // ── Palette pools ──────────────────────────────────────────────────────
  const SKINS = ['#f5d5b8','#e8c49a','#d4a97a','#c28b5a','#a0693a','#7a4a28','#5a3018'];
  const EYES  = ['#4a6a8a','#5a7a3a','#8a6a2a','#3a5a7a','#6a4a3a','#2a4a6a','#7a7a7a'];
  const HAIRS = ['#1a1008','#2a1a10','#6a4820','#9a7840','#c8a870','#e8d0a0','#e8e0d8','#3a2828','#d04828','#1a2038'];

  // ── SVG builder ────────────────────────────────────────────────────────
  function tag(name, attrs, children) {
    const attrStr = Object.entries(attrs).map(([k, v]) => `${k}="${v}"`).join(' ');
    if (children == null) return `<${name} ${attrStr}/>`;
    return `<${name} ${attrStr}>${children}</${name}>`;
  }

  function generatePortrait(seedStr) {
    const rng = makePRNG(seedStr || 'default');
    const W = 64, H = 64;
    const cx = 32, cy = 34;

    const skin = pick(rng, SKINS);
    const hairCol = pick(rng, HAIRS);
    const eyeCol  = pick(rng, EYES);

    // Face shape: oval vs round vs narrow
    const faceW = rngInt(rng, 18, 24);
    const faceH = rngInt(rng, 22, 28);

    // Hair style (0=short, 1=medium, 2=long, 3=bald, 4=ponytail)
    const hairStyle = rngInt(rng, 0, 5);

    // Eye shape
    const eyeRY = rngInt(rng, 3, 5);
    const eyeRX = rngInt(rng, 4, 6);
    const eyeY  = cy - 5;
    const eyeSpread = rngInt(rng, 7, 10);

    // Nose
    const noseLen = rngInt(rng, 4, 7);

    // Mouth width
    const mouthW = rngInt(rng, 6, 10);
    const mouthY = cy + 8;

    // Optional features
    const hasGlasses = rng() > 0.7;
    const hasFreckles = rng() > 0.65;
    const hasScar = rng() > 0.85;
    const hasStubble = rng() > 0.6;

    // Eyebrow angle (0=flat, +up, -down arched)
    const browAngle = rngRange(rng, -1.5, 1.5);

    let parts = [];

    // ── Hair (back layer for long/ponytail) ──────────────────────────────
    if (hairStyle === 1 || hairStyle === 2) {
      const hairH = hairStyle === 2 ? faceH + 12 : faceH + 4;
      parts.push(tag('ellipse', {
        cx, cy: cy + 4, rx: faceW + 2, ry: hairH,
        fill: hairCol
      }));
    }
    if (hairStyle === 4) {
      // Ponytail bun behind head
      parts.push(tag('circle', { cx: cx + faceW + 3, cy: cy - 8, r: 6, fill: hairCol }));
      parts.push(tag('rect', { x: cx + faceW - 2, y: cy - 10, width: 6, height: 14, fill: hairCol }));
    }

    // ── Neck ─────────────────────────────────────────────────────────────
    parts.push(tag('rect', {
      x: cx - 5, y: cy + faceH - 4, width: 10, height: 12,
      fill: skin
    }));

    // ── Face oval ────────────────────────────────────────────────────────
    parts.push(tag('ellipse', {
      cx, cy, rx: faceW, ry: faceH,
      fill: skin, stroke: '#00000030', 'stroke-width': '0.5'
    }));

    // ── Stubble ────────────────────────────────────────────────────────
    if (hasStubble) {
      parts.push(tag('ellipse', {
        cx, cy: cy + 10, rx: faceW - 4, ry: 9,
        fill: 'none', stroke: hairCol + '60', 'stroke-width': '2',
        'stroke-dasharray': '1 1.5'
      }));
    }

    // ── Eyebrows ─────────────────────────────────────────────────────────
    const brow = (side) => {
      const bx = cx + side * eyeSpread;
      const dy = browAngle * side;
      return tag('line', {
        x1: bx - eyeRX, y1: eyeY - eyeRY - 3 - dy,
        x2: bx + eyeRX, y2: eyeY - eyeRY - 3 + dy,
        stroke: hairCol, 'stroke-width': '1.5', 'stroke-linecap': 'round'
      });
    };
    parts.push(brow(-1), brow(1));

    // ── Eyes ─────────────────────────────────────────────────────────────
    const eye = (side) => {
      const ex = cx + side * eyeSpread;
      return [
        tag('ellipse', { cx: ex, cy: eyeY, rx: eyeRX, ry: eyeRY, fill: '#fff' }),
        tag('ellipse', { cx: ex, cy: eyeY, rx: eyeRX - 1, ry: eyeRY - 1, fill: eyeCol }),
        tag('circle',  { cx: ex, cy: eyeY, r: 1.5, fill: '#111' }),
        tag('circle',  { cx: ex - 1, cy: eyeY - 1, r: 0.8, fill: '#fff8' }),
        // Eyelids
        tag('path', {
          d: `M${ex - eyeRX},${eyeY} Q${ex},${eyeY - eyeRY - 1} ${ex + eyeRX},${eyeY}`,
          fill: 'none', stroke: skin, 'stroke-width': '1'
        }),
      ].join('');
    };
    parts.push(eye(-1), eye(1));

    // ── Glasses ──────────────────────────────────────────────────────────
    if (hasGlasses) {
      const gx1 = cx - eyeSpread, gx2 = cx + eyeSpread;
      const gr = eyeRX + 1, gy = eyeY;
      parts.push(
        tag('circle', { cx: gx1, cy: gy, r: gr, fill: 'none', stroke: '#888', 'stroke-width': '1' }),
        tag('circle', { cx: gx2, cy: gy, r: gr, fill: 'none', stroke: '#888', 'stroke-width': '1' }),
        tag('line', {
          x1: gx1 + gr, y1: gy, x2: gx2 - gr, y2: gy,
          stroke: '#888', 'stroke-width': '1'
        }),
        tag('line', { x1: gx1 - gr, y1: gy - 1, x2: gx1 - gr - 4, y2: gy, stroke: '#888', 'stroke-width': '1' }),
        tag('line', { x1: gx2 + gr, y1: gy - 1, x2: gx2 + gr + 4, y2: gy, stroke: '#888', 'stroke-width': '1' }),
      );
    }

    // ── Nose ─────────────────────────────────────────────────────────────
    const noseX = cx, noseTopY = eyeY + eyeRY + 1, noseBotY = noseTopY + noseLen;
    parts.push(
      tag('path', {
        d: `M${noseX},${noseTopY} L${noseX - 2},${noseBotY} Q${noseX},${noseBotY + 1} ${noseX + 2},${noseBotY}`,
        fill: 'none', stroke: skin + 'aa', 'stroke-width': '1', 'stroke-linecap': 'round'
      })
    );

    // ── Mouth ─────────────────────────────────────────────────────────────
    const smileAmount = rngRange(rng, -0.5, 1.5);
    const mouthX1 = cx - mouthW, mouthX2 = cx + mouthW;
    const cp1y = mouthY + smileAmount * 1.5, cp2y = mouthY + smileAmount * 1.5;
    parts.push(
      tag('path', {
        d: `M${mouthX1},${mouthY} Q${cx},${cp1y + 1} ${mouthX2},${mouthY}`,
        fill: 'none', stroke: '#88444488', 'stroke-width': '1.2', 'stroke-linecap': 'round'
      }),
      // Lower lip hint
      tag('path', {
        d: `M${mouthX1 + 2},${mouthY + 0.5} Q${cx},${cp2y + 2.5} ${mouthX2 - 2},${mouthY + 0.5}`,
        fill: 'none', stroke: '#88444430', 'stroke-width': '1', 'stroke-linecap': 'round'
      })
    );

    // ── Freckles ──────────────────────────────────────────────────────────
    if (hasFreckles) {
      for (let i = 0; i < 6; i++) {
        const fx = cx + rngRange(rng, -12, 12);
        const fy = eyeY + rngRange(rng, 4, 10);
        parts.push(tag('circle', { cx: fx.toFixed(1), cy: fy.toFixed(1), r: '0.8', fill: '#88441830' }));
      }
    }

    // ── Scar ──────────────────────────────────────────────────────────────
    if (hasScar) {
      const scarX = cx + rngRange(rng, -10, 10);
      const scarY = cy + rngRange(rng, -5, 8);
      parts.push(
        tag('line', {
          x1: scarX, y1: scarY - 4, x2: scarX + 2, y2: scarY + 4,
          stroke: '#884444aa', 'stroke-width': '1', 'stroke-linecap': 'round'
        })
      );
    }

    // ── Short hair / bald top ─────────────────────────────────────────────
    if (hairStyle === 0) {
      // Short hair cap
      parts.push(tag('path', {
        d: `M${cx - faceW},${cy} Q${cx},${cy - faceH - 5} ${cx + faceW},${cy}`,
        fill: hairCol
      }));
    } else if (hairStyle === 3) {
      // Bald — slight shine
      parts.push(tag('ellipse', {
        cx: cx - 4, cy: cy - faceH + 5, rx: 4, ry: 2,
        fill: '#ffffff18'
      }));
    } else if (hairStyle >= 1) {
      // Hair top cap
      parts.push(tag('path', {
        d: `M${cx - faceW},${cy - 3} Q${cx},${cy - faceH - 4} ${cx + faceW},${cy - 3}`,
        fill: hairCol
      }));
    }

    // ── Assemble SVG ──────────────────────────────────────────────────────
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" style="display:block">${parts.join('')}</svg>`;
  }

  // ── Export ────────────────────────────────────────────────────────────
  global.Portrait = { generate: generatePortrait };

})(typeof window !== 'undefined' ? window : this);
