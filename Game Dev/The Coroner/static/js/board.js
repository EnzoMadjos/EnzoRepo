/**
 * board.js — HTML5 canvas board with debounced server sync.
 * Tools: pen, eraser, sticky note text, clear.
 * State synced to /api/board/{case_id} every 3s on change.
 */

(function (global) {
  'use strict';

  class Board {
    constructor(canvasEl, caseId) {
      this.canvas = canvasEl;
      this.ctx    = canvasEl.getContext('2d');
      this.caseId = caseId;

      this.tool    = 'pen';
      this.color   = '#c8b89a';
      this.lineWidth = 2;
      this.drawing  = false;
      this.lastX    = 0;
      this.lastY    = 0;
      this.dirty    = false;
      this.serverVersion = 0;
      this._syncTimer = null;
      this._notes = [];   // {x, y, text, color}

      this._bindEvents();
      this._load();
    }

    // ── Tool / color setters ────────────────────────────────────────────
    setTool(t)  { this.tool = t; this.canvas.style.cursor = t === 'eraser' ? 'cell' : 'crosshair'; }
    setColor(c) { this.color = c; }
    setLineWidth(w) { this.lineWidth = w; }

    // ── Event binding ───────────────────────────────────────────────────
    _bindEvents() {
      const c = this.canvas;
      c.addEventListener('mousedown',  e => this._start(e));
      c.addEventListener('mousemove',  e => this._move(e));
      c.addEventListener('mouseup',    () => this._end());
      c.addEventListener('mouseleave', () => this._end());
      // Touch
      c.addEventListener('touchstart', e => { e.preventDefault(); this._start(e.touches[0]); }, { passive: false });
      c.addEventListener('touchmove',  e => { e.preventDefault(); this._move(e.touches[0]); },  { passive: false });
      c.addEventListener('touchend',   () => this._end());
    }

    _pos(e) {
      const r = this.canvas.getBoundingClientRect();
      const scaleX = this.canvas.width  / r.width;
      const scaleY = this.canvas.height / r.height;
      return {
        x: (e.clientX - r.left) * scaleX,
        y: (e.clientY - r.top)  * scaleY,
      };
    }

    _start(e) {
      const { x, y } = this._pos(e);
      if (this.tool === 'note') {
        const text = prompt('Note text:');
        if (text && text.trim()) {
          this._notes.push({ x, y, text: text.trim(), color: this.color });
          this._redraw();
          this._markDirty();
        }
        return;
      }
      this.drawing = true;
      this.lastX = x; this.lastY = y;
      this.ctx.beginPath();
      this.ctx.moveTo(x, y);
    }

    _move(e) {
      if (!this.drawing) return;
      const { x, y } = this._pos(e);
      const ctx = this.ctx;

      if (this.tool === 'eraser') {
        ctx.save();
        ctx.globalCompositeOperation = 'destination-out';
        ctx.beginPath();
        ctx.arc(x, y, 12, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      } else {
        ctx.strokeStyle  = this.color;
        ctx.lineWidth    = this.lineWidth;
        ctx.lineCap      = 'round';
        ctx.lineJoin     = 'round';
        ctx.globalCompositeOperation = 'source-over';
        ctx.lineTo(x, y);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(x, y);
      }

      this.lastX = x; this.lastY = y;
      this._markDirty();
    }

    _end() { this.drawing = false; }

    // ── Notes rendering ─────────────────────────────────────────────────
    _redraw() {
      // Notes are rendered on top of the current pixel state
      // We snapshot then restore — notes are stored separately
      // For simplicity: notes just rendered on top, can't erase individually
      const ctx = this.ctx;
      ctx.save();
      ctx.font = '11px "Courier New", monospace';
      for (const n of this._notes) {
        ctx.fillStyle   = this.color + 'cc';
        ctx.strokeStyle = '#111';
        ctx.lineWidth   = 2;
        const lines = n.text.split('\n');
        const pad = 4;
        const w = Math.max(...lines.map(l => ctx.measureText(l).width)) + pad * 2;
        const h = lines.length * 14 + pad * 2;
        ctx.fillRect(n.x, n.y, w, h);
        ctx.strokeRect(n.x, n.y, w, h);
        ctx.fillStyle = '#111';
        lines.forEach((line, i) => ctx.fillText(line, n.x + pad, n.y + pad + 11 + i * 14));
      }
      ctx.restore();
    }

    // ── Dirty / sync ────────────────────────────────────────────────────
    _markDirty() {
      this.dirty = true;
      if (this._syncTimer) clearTimeout(this._syncTimer);
      this._syncTimer = setTimeout(() => this._sync(), 3000);
    }

    async _sync() {
      if (!this.dirty) return;
      const state = {
        imageData: this.canvas.toDataURL('image/webp', 0.6),
        notes: this._notes,
      };
      const stateJson = JSON.stringify(state);
      if (stateJson.length > 512 * 1024) {
        console.warn('[Board] State too large, skipping sync');
        return;
      }
      try {
        const r = await fetch(`/api/board/${this.caseId}/sync`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            case_id: this.caseId,
            state_json: stateJson,
            client_version: this.serverVersion,
          }),
        });
        const data = await r.json();
        if (data.conflict) {
          // Server has newer state — load it
          console.info('[Board] Conflict — loading server state');
          await this._applyState(data.server_state_json);
          this.serverVersion = data.server_version;
        } else {
          this.serverVersion = data.server_version;
          this.dirty = false;
        }
      } catch (e) {
        console.warn('[Board] Sync failed:', e);
      }
    }

    async _load() {
      try {
        const r = await fetch(`/api/board/${this.caseId}`);
        const data = await r.json();
        this.serverVersion = data.server_version;
        if (data.state_json && data.state_json !== '{}') {
          await this._applyState(data.state_json);
        }
      } catch (e) {
        console.warn('[Board] Load failed:', e);
      }
    }

    async _applyState(stateJson) {
      try {
        const state = typeof stateJson === 'string' ? JSON.parse(stateJson) : stateJson;
        this._notes = state.notes || [];
        if (state.imageData) {
          const img = new Image();
          await new Promise((res, rej) => {
            img.onload  = res;
            img.onerror = rej;
            img.src = state.imageData;
          });
          this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
          this.ctx.drawImage(img, 0, 0);
        }
        this._redraw();
      } catch (e) {
        console.warn('[Board] Apply state failed:', e);
      }
    }

    clear() {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this._notes = [];
      this._markDirty();
    }

    forceSave() {
      if (this._syncTimer) clearTimeout(this._syncTimer);
      return this._sync();
    }
  }

  global.Board = Board;
})(window);
