// AtlasFace — glowing neon ring orb for ATLAS UI
class AtlasFace {
  constructor(el, sz) {
    this.c = el;
    this.ctx = el.getContext('2d');
    this.sz = sz; this.cx = sz / 2; this.cy = sz / 2;
    this.t = 0; this.state = 'idle'; this.alive = true;
    this.arcAngle = 0;
    // Orbiting dot angles (9 slots, used 6–9 depending on state)
    this._dotAngles = Array.from({ length: 9 }, (_, i) => (Math.PI * 2 * i / 9));
    this._frame();
  }

  setState(s) { this.state = s; }

  _col() {
    switch (this.state) {
      case 'thinking': return { p: '#f5a623', s: '#c97c10', g: 'rgba(245,166,35,' };
      case 'speaking': return { p: '#6cb6ff', s: '#3a7abf', g: 'rgba(108,182,255,' };
      default:         return { p: '#9b6dff', s: '#5c30b0', g: 'rgba(155,109,255,' };
    }
  }

  _frame() {
    if (!this.alive) return;
    const { ctx, cx, cy, sz } = this;
    const t = ++this.t;
    const c = this._col();
    const spd = this.state === 'thinking' ? 2.8 : this.state === 'speaking' ? 1.8 : 1.0;

    ctx.clearRect(0, 0, sz, sz);

    // Arc rotation
    this.arcAngle += 0.011 * spd;

    const pulse = 1 + 0.022 * Math.sin(t * 0.024 * spd);
    const R = sz * 0.38 * pulse;

    // — Outer ambient halo —
    const halo = ctx.createRadialGradient(cx, cy, R * 0.55, cx, cy, sz * 0.5);
    halo.addColorStop(0, c.g + '0)');
    halo.addColorStop(0.45, c.g + '0.05)');
    halo.addColorStop(0.78, c.g + '0.07)');
    halo.addColorStop(1, 'transparent');
    ctx.beginPath(); ctx.arc(cx, cy, sz * 0.5, 0, Math.PI * 2);
    ctx.fillStyle = halo; ctx.fill();

    // — Thick glow bed (blurred ring underpainting) —
    ctx.save();
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.strokeStyle = c.p; ctx.globalAlpha = 0.11; ctx.lineWidth = 22; ctx.stroke();
    ctx.globalAlpha = 0.07; ctx.lineWidth = 34; ctx.stroke();
    ctx.restore();

    // — Dark base ring —
    ctx.save();
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2);
    ctx.strokeStyle = c.s; ctx.globalAlpha = 0.35; ctx.lineWidth = 2.5;
    ctx.setLineDash([]);
    ctx.stroke();
    ctx.restore();

    // — Dashed orbit (slowly counter-rotating) —
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(-this.arcAngle * 0.55);
    const circ = Math.PI * 2 * R * 0.94;
    ctx.beginPath(); ctx.arc(0, 0, R * 0.94, 0, Math.PI * 2);
    ctx.setLineDash([circ * 0.07, circ * 0.13]);
    ctx.strokeStyle = c.p; ctx.globalAlpha = 0.18; ctx.lineWidth = 1.2;
    ctx.stroke();
    ctx.restore();
    ctx.setLineDash([]);

    // — Main bright arc sweep —
    const arcLen = this.state === 'idle'
      ? Math.PI * 0.52
      : this.state === 'thinking'
        ? Math.PI * (0.75 + 0.22 * Math.sin(t * 0.065))
        : Math.PI * (0.65 + 0.38 * Math.sin(t * 0.085));
    const a0 = this.arcAngle;
    const a1 = a0 + arcLen;
    const x0 = cx + R * Math.cos(a0), y0 = cy + R * Math.sin(a0);
    const x1 = cx + R * Math.cos(a1), y1 = cy + R * Math.sin(a1);
    const ag = ctx.createLinearGradient(x0, y0, x1, y1);
    ag.addColorStop(0,   c.g + '0.08)');
    ag.addColorStop(0.42, c.p);
    ag.addColorStop(0.72, c.p);
    ag.addColorStop(1,   c.g + '0.2)');
    ctx.save();
    ctx.beginPath(); ctx.arc(cx, cy, R, a0, a1);
    ctx.strokeStyle = ag; ctx.lineWidth = 3; ctx.lineCap = 'round';
    ctx.shadowBlur = 18; ctx.shadowColor = c.p;
    ctx.globalAlpha = 0.92; ctx.stroke();
    // bloom pass
    ctx.strokeStyle = ag; ctx.lineWidth = 7;
    ctx.shadowBlur = 32; ctx.globalAlpha = 0.22; ctx.stroke();
    ctx.restore();

    // — Glare point (bright spot on the arc) —
    const ga = a0 + arcLen * 0.55;
    const gx = cx + R * Math.cos(ga), gy = cy + R * Math.sin(ga);
    const gr = ctx.createRadialGradient(gx, gy, 0, gx, gy, 14);
    gr.addColorStop(0, 'rgba(255,255,255,.92)');
    gr.addColorStop(0.28, c.g + '.55)');
    gr.addColorStop(1, 'transparent');
    ctx.beginPath(); ctx.arc(gx, gy, 14, 0, Math.PI * 2);
    ctx.fillStyle = gr; ctx.fill();

    // — Counter-arc (depth / secondary) —
    if (this.state !== 'idle') {
      const a2 = -this.arcAngle * 1.25;
      ctx.save();
      ctx.beginPath(); ctx.arc(cx, cy, R * 0.91, a2, a2 + Math.PI * 0.28);
      ctx.strokeStyle = c.p; ctx.lineWidth = 1.4; ctx.lineCap = 'round';
      ctx.shadowBlur = 6; ctx.shadowColor = c.p;
      ctx.globalAlpha = 0.35; ctx.stroke();
      ctx.restore();
    }

    // — Thinking ripples —
    if (this.state === 'thinking') {
      for (let i = 0; i < 4; i++) {
        const rr = R * (0.74 - i * 0.11) + 3.5 * Math.sin(t * 0.055 + i * 0.95);
        ctx.beginPath(); ctx.arc(cx, cy, rr, 0, Math.PI * 2);
        ctx.strokeStyle = c.p; ctx.lineWidth = 0.8;
        ctx.globalAlpha = 0.055 + 0.028 * Math.sin(t * 0.07 + i); ctx.stroke();
        ctx.globalAlpha = 1;
      }
    }

    // — Speaking radial ticks —
    if (this.state === 'speaking') {
      const n = 24;
      for (let i = 0; i < n; i++) {
        const a = (Math.PI * 2 * i / n) + this.arcAngle * 0.18;
        const amp = 0.065 + 0.045 * Math.abs(Math.sin(t * 0.065 + i * 0.52));
        const r0 = R * 0.82, r1 = R * (0.82 + amp);
        ctx.beginPath();
        ctx.moveTo(cx + r0 * Math.cos(a), cy + r0 * Math.sin(a));
        ctx.lineTo(cx + r1 * Math.cos(a), cy + r1 * Math.sin(a));
        ctx.strokeStyle = c.p; ctx.lineWidth = 1;
        ctx.globalAlpha = 0.25 + 0.15 * Math.sin(t * 0.07 + i); ctx.stroke();
        ctx.globalAlpha = 1;
      }
    }

    // ── Scan-line waveform (inspired by animejs.com hero) ───────────────────
    this._drawWaveform(ctx, cx, cy, R, c, t, spd);

    // ── Orbiting signal dots ──────────────────────────────────────────────────
    this._drawDots(ctx, cx, cy, R, c, t, spd);

    // — Inner core soft glow —
    const ig = ctx.createRadialGradient(cx, cy, 0, cx, cy, R * 0.52);
    ig.addColorStop(0, c.g + '0.18)');
    ig.addColorStop(0.55, c.g + '0.06)');
    ig.addColorStop(1, 'transparent');
    ctx.beginPath(); ctx.arc(cx, cy, R * 0.52, 0, Math.PI * 2);
    ctx.fillStyle = ig; ctx.fill();

    requestAnimationFrame(() => this._frame());
  }

  // ── Scan-line waveform ──────────────────────────────────────────────────────
  // Draws horizontal scan lines filling a diamond/eye-shaped envelope,
  // plus the waveform edge curves — clipped inside the inner circle.
  _drawWaveform(ctx, cx, cy, R, c, t, spd) {
    const innerR = R * 0.64;

    const wAmp = this.state === 'speaking'
      ? 0.50 + 0.22 * Math.abs(Math.sin(t * 0.11))
      : this.state === 'thinking' ? 0.26 : 0.14;
    const wFreq = this.state === 'speaking' ? 0.13 * spd
      : this.state === 'thinking' ? 0.045 : 0.022;

    // Clip to inner circle so waveform never bleeds outside
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, innerR, 0, Math.PI * 2);
    ctx.clip();

    const halfW = innerR * wAmp;
    const scanCount = this.state === 'speaking' ? 36 : 28;

    // — Scan lines —
    for (let i = 0; i < scanCount; i++) {
      const fy  = (i / (scanCount - 1)) * 2 - 1;   // −1 … +1
      const y   = cy + fy * innerR * 0.78;
      const env = Math.pow(1 - fy * fy, 0.8);       // diamond envelope
      const lw  = halfW * env;
      if (lw < 1.5) continue;

      const phase  = t * wFreq + fy * 4.8;
      const wiggle = lw * 0.07 * Math.sin(phase);

      ctx.beginPath();
      ctx.moveTo(cx - lw + wiggle, y);
      ctx.lineTo(cx + lw + wiggle, y);
      ctx.strokeStyle = c.p;
      ctx.lineWidth   = 0.55;
      ctx.globalAlpha = (0.06 + 0.13 * env) * (this.state === 'idle' ? 0.45 : 1.0);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // — Edge outline curves (left & right silhouette) —
    const edgeAlpha = this.state === 'idle' ? 0.25 : 0.62;
    const steps = 90;

    for (const side of [-1, 1]) {
      ctx.beginPath();
      for (let i = 0; i <= steps; i++) {
        const fy  = (i / steps) * 2 - 1;
        const y   = cy + fy * innerR * 0.78;
        const env = Math.pow(1 - fy * fy, 0.8);
        const lw  = halfW * env;
        const wave = lw * 0.10 * Math.sin(fy * 5.2 + t * wFreq * 1.15 + (side < 0 ? Math.PI : 0));
        const x    = cx + side * (lw + wave);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = c.p;
      ctx.lineWidth   = 1.4;
      ctx.lineCap     = 'round';
      ctx.shadowBlur  = 10;
      ctx.shadowColor = c.p;
      ctx.globalAlpha = edgeAlpha;
      ctx.stroke();
      ctx.shadowBlur  = 0;
      ctx.globalAlpha = 1;
    }

    ctx.restore();
  }

  // ── Orbiting signal dots ────────────────────────────────────────────────────
  // Dots orbit at ~80% of R on a slightly wavy path.
  // Speed, count, and size react to state.
  _drawDots(ctx, cx, cy, R, c, t, spd) {
    const dotSpeed = this.state === 'speaking'  ? 0.055
      : this.state === 'thinking' ? 0.025 : 0.010;
    const dotCount = this.state === 'speaking' ? 9 : 6;
    const dotR     = R * 0.80;

    for (let i = 0; i < dotCount; i++) {
      this._dotAngles[i] += dotSpeed * spd;

      const base   = this._dotAngles[i] + (Math.PI * 2 * i / dotCount);
      const radVar = 1 + 0.11 * Math.sin(base * 2 + t * 0.035);
      const dr     = dotR * radVar;

      const dx = cx + dr * Math.cos(base);
      const dy = cy + dr * Math.sin(base);

      const dotSz = this.state === 'speaking'
        ? 2.4 + 1.3 * Math.abs(Math.sin(t * 0.09 + i))
        : 1.6 + 0.7 * Math.abs(Math.sin(t * 0.03 + i));

      const alpha = 0.28 + 0.38 * (0.5 + 0.5 * Math.sin(t * 0.055 + i * 1.1));

      ctx.beginPath();
      ctx.arc(dx, dy, dotSz, 0, Math.PI * 2);
      ctx.fillStyle   = c.p;
      ctx.globalAlpha = alpha;
      ctx.fill();
      ctx.globalAlpha = 1;
    }
  }

  destroy() { this.alive = false; }
}
