/**
 * DialogueBox — reusable typewriter-style dialogue overlay.
 * Usage:
 *   const dlg = new DialogueBox(scene);
 *   dlg.show('PROF. OAK', ['Line one.', 'Line two.'], () => { onClose(); });
 *   // Call dlg.advance() on Space/Enter press to skip type or advance line.
 */
class DialogueBox {
  constructor(scene) {
    this.scene   = scene;
    this.active  = false;
    this._lines  = [];
    this._idx    = 0;
    this._typing = false;
    this._parts  = [];
    this._timer  = null;
    this._nameText = null;
    this._bodyText = null;
    this._arrow    = null;
    this._onClose  = null;
  }

  /** Show dialogue box with speaker name, lines array, optional onClose callback. */
  show(speaker, lines, onClose) {
    if (this.active) return;
    this._lines   = lines;
    this._idx     = 0;
    this._speaker = speaker;
    this._onClose = onClose || null;
    this.active   = true;
    this._build();
    this._typeNext();
  }

  /** Call on Space/Enter: skip typewriter or advance to next line. */
  advance() {
    if (!this.active) return;
    if (this._typing) {
      // Skip to end of current line immediately
      if (this._timer) { this._timer.remove(); this._timer = null; }
      this._bodyText.setText(this._lines[this._idx]);
      this._typing = false;
      this._arrow.setAlpha(1);
    } else {
      this._idx++;
      this._typeNext();
    }
  }

  // ── Private ────────────────────────────────────────────────────────
  _build() {
    const sc = this.scene;
    const W  = SETTINGS.SCREEN_W;
    const H  = SETTINGS.SCREEN_H;

    // Panel background
    const panel = sc.add.graphics().setScrollFactor(0).setDepth(300);
    panel.fillStyle(0x0a0a18, 0.96);
    panel.fillRoundedRect(20, H - 162, W - 40, 150, 10);
    panel.lineStyle(2, 0xFFD700, 1);
    panel.strokeRoundedRect(20, H - 162, W - 40, 150, 10);

    // Name badge
    const badge = sc.add.graphics().setScrollFactor(0).setDepth(300);
    badge.fillStyle(0x162036, 1);
    badge.fillRoundedRect(30, H - 184, 170, 30, 6);
    badge.lineStyle(1, 0xFFD700, 1);
    badge.strokeRoundedRect(30, H - 184, 170, 30, 6);

    this._nameText = sc.add.text(116, H - 169, this._speaker, {
      fontSize: '13px', color: '#FFD700', fontFamily: 'monospace', fontStyle: 'bold',
    }).setScrollFactor(0).setDepth(301).setOrigin(0.5, 0.5);

    this._bodyText = sc.add.text(36, H - 146, '', {
      fontSize: '15px', color: '#e8e8e8', fontFamily: 'monospace',
      lineSpacing: 6,
      wordWrap: { width: W - 80 },
    }).setScrollFactor(0).setDepth(301);

    // Blinking advance arrow
    this._arrow = sc.add.text(W - 38, H - 26, '▼', {
      fontSize: '14px', color: '#FFD700', fontFamily: 'monospace',
    }).setScrollFactor(0).setDepth(301).setOrigin(0.5).setAlpha(0);

    sc.tweens.add({
      targets: this._arrow, alpha: { from: 0.1, to: 1 },
      duration: 480, yoyo: true, repeat: -1,
    });

    this._parts = [panel, badge];
  }

  _typeNext() {
    if (this._idx >= this._lines.length) {
      this._close();
      return;
    }
    const text = this._lines[this._idx];
    this._bodyText.setText('');
    this._arrow.setAlpha(0);
    this._typing = true;
    let ci = 0;
    if (this._timer) { this._timer.remove(); }
    this._timer = this.scene.time.addEvent({
      delay: 26,
      repeat: text.length - 1,
      callback: () => {
        ci++;
        this._bodyText.setText(text.substring(0, ci));
        if (ci >= text.length) {
          this._typing = false;
          this._arrow.setAlpha(1);
        }
      },
    });
  }

  _close() {
    this.active  = false;
    this._typing = false;
    if (this._timer) { this._timer.remove(); this._timer = null; }
    [...this._parts, this._nameText, this._bodyText, this._arrow].forEach(o => {
      if (o && o.destroy) o.destroy();
    });
    this._parts    = [];
    this._nameText = this._bodyText = this._arrow = null;
    if (this._onClose) this._onClose();
  }
}
