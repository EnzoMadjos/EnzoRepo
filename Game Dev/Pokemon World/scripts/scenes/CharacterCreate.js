class CharacterCreate extends Phaser.Scene {
  constructor() {
    super({ key: 'CharacterCreate' });
  }

  preload() {
    const outfitNames = ['red', 'blue', 'green'];
    ['boy', 'girl'].forEach(g => {
      outfitNames.forEach(o => {
        this.load.spritesheet(`trainer_${g}_${o}`,
          `/assets/sprites/trainer/${g}_${o}.png`,
          { frameWidth: 64, frameHeight: 64 });
      });
    });
  }

  create() {
    const W = SETTINGS.SCREEN_W;
    const H = SETTINGS.SCREEN_H;

    this.profile = { gender: 'boy', outfit: 0, name: '' };
    this._nameActive = false;
    this._ready = false;

    // --- Background ---
    this.add.rectangle(W / 2, H / 2, W, H, 0x0a0a1a);
    this._addStars();

    // --- Title ---
    this.add.text(W / 2, 42, '✦  POKEMON WORLD  ✦', {
      fontSize: '26px', color: '#FFD700', fontFamily: 'monospace', fontStyle: 'bold',
    }).setOrigin(0.5);
    this.add.text(W / 2, 78, 'CREATE YOUR TRAINER', {
      fontSize: '13px', color: '#445566', fontFamily: 'monospace',
    }).setOrigin(0.5);
    this.add.rectangle(W / 2, 100, W - 80, 1, 0x1a2a3a);

    // ===================== LEFT PANEL (x~220) =====================

    // Gender
    this.add.text(60, 120, 'GENDER', { fontSize: '11px', color: '#445566', fontFamily: 'monospace' });
    this._genderGroup = this._createToggleGroup(
      [{ label: '♂  BOY', value: 'boy' }, { label: '♀  GIRL', value: 'girl' }],
      60, 140, 158, 42,
      (v) => { this.profile.gender = v; this._refreshPreview(); }
    );

    // Outfit
    this.add.text(60, 210, 'OUTFIT COLOR', { fontSize: '11px', color: '#445566', fontFamily: 'monospace' });
    this._outfitSwatches = SETTINGS.OUTFIT_COLORS.map((c, i) => {
      return this._createOutfitSwatch(80 + i * 110, 270, c, i);
    });

    // Name
    this.add.text(60, 322, 'TRAINER NAME', { fontSize: '11px', color: '#445566', fontFamily: 'monospace' });
    this._nameBox = this._createNameBox(60, 342, 360, 46);
    this.add.text(60, 400, 'Click the box above, then type  (max 10 chars, A-Z 0-9)', {
      fontSize: '10px', color: '#2a3a4a', fontFamily: 'monospace',
    });

    // Keyboard handler
    this.input.keyboard.on('keydown', this._onKey, this);

    // Deactivate name box when clicking elsewhere
    this.input.on('pointerdown', (_ptr, objs) => {
      if (!objs.includes(this._nameBox.bg)) {
        this._nameActive = false;
        this._nameBox.border.setStrokeStyle(1, this.profile.name ? 0x2a5aaa : 0x1a2a3a);
      }
    });

    // ===================== RIGHT PANEL (x~710) =====================

    this.add.rectangle(710, 310, 380, 420, 0x0d1525);
    this.add.rectangle(710, 310, 380, 420, 0, 0).setStrokeStyle(1, 0x1a2a3a);
    this.add.text(710, 118, 'TRAINER PREVIEW', { fontSize: '11px', color: '#445566', fontFamily: 'monospace' }).setOrigin(0.5);

    this.trainerContainer = this.add.container(710, 270);

    this.previewNameText = this.add.text(710, 420, '???', {
      fontSize: '22px', color: '#FFD700', fontFamily: 'monospace', fontStyle: 'bold',
    }).setOrigin(0.5);

    this.previewInfoText = this.add.text(710, 456, '', {
      fontSize: '11px', color: '#4a6688', fontFamily: 'monospace',
    }).setOrigin(0.5);

    // ===================== START BUTTON =====================
    this._startBtn = this._createStartButton(W / 2, H - 42);

    // ===================== Initial selections =====================
    this._genderGroup.select('boy');
    this._selectOutfit(0);
  }

  // ─── Stars ────────────────────────────────────────────────────────
  _addStars() {
    for (let i = 0; i < 80; i++) {
      const x = Phaser.Math.Between(0, SETTINGS.SCREEN_W);
      const y = Phaser.Math.Between(0, SETTINGS.SCREEN_H);
      this.add.circle(x, y, Phaser.Math.Between(1, 2), 0xffffff, Phaser.Math.FloatBetween(0.05, 0.35));
    }
  }

  // ─── Toggle group (gender) ────────────────────────────────────────
  _createToggleGroup(options, x, y, w, h, onChange) {
    const buttons = {};
    let currentVal = null;

    options.forEach((opt, i) => {
      const bx = x + i * (w + 10) + w / 2;
      const by = y + h / 2;
      const bg = this.add.rectangle(bx, by, w, h, 0x111122).setInteractive();
      const border = this.add.rectangle(bx, by, w, h, 0, 0).setStrokeStyle(1, 0x1a2a3a);
      const text = this.add.text(bx, by, opt.label, {
        fontSize: '14px', color: '#334455', fontFamily: 'monospace',
      }).setOrigin(0.5);

      bg.on('pointerdown', () => group.select(opt.value));
      bg.on('pointerover', () => { if (currentVal !== opt.value) bg.setFillStyle(0x1a1a33); });
      bg.on('pointerout', () => { if (currentVal !== opt.value) bg.setFillStyle(0x111122); });

      buttons[opt.value] = { bg, border, text };
    });

    const group = {
      select(value) {
        currentVal = value;
        Object.entries(buttons).forEach(([v, b]) => {
          const active = v === value;
          b.bg.setFillStyle(active ? 0x1a3a8a : 0x111122);
          b.border.setStrokeStyle(2, active ? 0x3a7aff : 0x1a2a3a);
          b.text.setColor(active ? '#ffffff' : '#334455');
        });
        onChange(value);
      },
    };

    return group;
  }

  // ─── Outfit swatches ──────────────────────────────────────────────
  _createOutfitSwatch(x, y, outfit, index) {
    const bg = this.add.rectangle(x, y, 80, 80, outfit.primary).setInteractive();
    const border = this.add.rectangle(x, y, 80, 80, 0, 0).setStrokeStyle(2, 0x1a2a3a);
    const label = this.add.text(x, y + 50, outfit.name, {
      fontSize: '11px', color: '#ffffff', fontFamily: 'monospace',
    }).setOrigin(0.5);

    bg.on('pointerdown', () => this._selectOutfit(index));
    bg.on('pointerover', () => { if (this.profile.outfit !== index) bg.setAlpha(0.7); });
    bg.on('pointerout', () => bg.setAlpha(1));

    return { bg, border, label };
  }

  _selectOutfit(index) {
    this.profile.outfit = index;
    this._outfitSwatches.forEach((s, i) => {
      s.border.setStrokeStyle(3, i === index ? 0xFFD700 : 0x1a2a3a);
    });
    this._refreshPreview();
  }

  // ─── Name box ─────────────────────────────────────────────────────
  _createNameBox(x, y, w, h) {
    const cx = x + w / 2;
    const cy = y + h / 2;
    const bg = this.add.rectangle(cx, cy, w, h, 0x0d1020).setInteractive();
    const border = this.add.rectangle(cx, cy, w, h, 0, 0).setStrokeStyle(1, 0x1a2a3a);
    const text = this.add.text(x + 12, cy, 'Click here to enter name...', {
      fontSize: '16px', color: '#2a3a4a', fontFamily: 'monospace',
    }).setOrigin(0, 0.5);

    bg.on('pointerdown', () => {
      this._nameActive = true;
      border.setStrokeStyle(2, 0x3a7aff);
      this._updateNameDisplay();
    });

    return { bg, border, text };
  }

  _onKey(event) {
    if (!this._nameActive) return;
    if (event.key === 'Backspace') {
      this.profile.name = this.profile.name.slice(0, -1);
    } else if (event.key === 'Enter' || event.key === 'Escape') {
      this._nameActive = false;
      this._nameBox.border.setStrokeStyle(1, this.profile.name ? 0x2a5aaa : 0x1a2a3a);
    } else if (event.key.length === 1 && this.profile.name.length < 10) {
      const c = event.key.toUpperCase();
      if (/[A-Z0-9 ]/.test(c)) this.profile.name += c;
    }
    this._updateNameDisplay();
  }

  _updateNameDisplay() {
    const name = this.profile.name;
    const cursor = this._nameActive ? '_' : '';
    const display = (name + cursor) || (this._nameActive ? '_' : 'Click here to enter name...');
    this._nameBox.text.setText(display);
    this._nameBox.text.setColor(name ? '#ffffff' : (this._nameActive ? '#4a90d9' : '#2a3a4a'));
    this.previewNameText?.setText(name || '???');
    this._checkReady();
  }

  // ─── Preview ──────────────────────────────────────────────────────
  _refreshPreview() {
    if (this.previewSprite) { this.previewSprite.destroy(); this.previewSprite = null; }
    const outfitNames = ['red', 'blue', 'green'];
    const key = `trainer_${this.profile.gender}_${outfitNames[this.profile.outfit]}`;
    this.previewSprite = this.add.sprite(710, 255, key, 0).setScale(2.5).setDepth(5);
    const gLabel = this.profile.gender === 'boy' ? '♂ BOY' : '♀ GIRL';
    const oLabel = SETTINGS.OUTFIT_COLORS[this.profile.outfit]?.name ?? '';
    this.previewInfoText?.setText(`${gLabel}  •  ${oLabel} OUTFIT`);
  }

  _drawTrainer(container) {
    // Superseded by _refreshPreview() using real sprites. Kept as stub.
    const outfit = SETTINGS.OUTFIT_COLORS[this.profile.outfit];
    const isBoy = this.profile.gender === 'boy';
    const g = this.make.graphics({ add: false });

    // Shadow
    g.fillStyle(0x000000, 0.2);
    g.fillEllipse(0, 72, 44, 12);

    // Shoes
    g.fillStyle(0x3d2b1f);
    g.fillRect(-22, 58, 18, 10);
    g.fillRect(4, 58, 18, 10);

    // Legs
    g.fillStyle(0x2c3e50);
    g.fillRect(-20, 28, 16, 34);
    g.fillRect(4, 28, 16, 34);

    // Body
    g.fillStyle(outfit.primary);
    g.fillRect(-22, -4, 44, 34);

    // Arms
    g.fillStyle(outfit.primary);
    g.fillRect(-38, -4, 18, 28);
    g.fillRect(20, -4, 18, 28);

    // Hands
    g.fillStyle(0xf5c6a0);
    g.fillRect(-38, 22, 18, 12);
    g.fillRect(20, 22, 18, 12);

    // Head
    g.fillStyle(0xf5c6a0);
    g.fillCircle(0, -26, 22);

    // Hat base
    g.fillStyle(outfit.secondary);
    g.fillRect(-24, -44, 48, 18);

    // Hat brim
    g.fillRect(2, -30, 22, 8);

    // Eyes
    g.fillStyle(0x1a1a2e);
    g.fillCircle(-8, -24, 4);
    g.fillCircle(8, -24, 4);

    // Eye shine
    g.fillStyle(0xffffff);
    g.fillCircle(-6, -26, 1.5);
    g.fillCircle(10, -26, 1.5);

    // Girl hair
    if (!isBoy) {
      g.fillStyle(outfit.secondary);
      g.fillRect(-32, -22, 10, 26);
      g.fillRect(22, -22, 10, 26);
    }

    container.add(g);
  }

  // ─── Start button ─────────────────────────────────────────────────
  _createStartButton(x, y) {
    const bg = this.add.rectangle(x, y, 280, 50, 0x0a1a0a).setInteractive();
    const border = this.add.rectangle(x, y, 280, 50, 0, 0).setStrokeStyle(2, 0x1a2a1a);
    const text = this.add.text(x, y, '▶  START ADVENTURE', {
      fontSize: '15px', color: '#1a3a1a', fontFamily: 'monospace', fontStyle: 'bold',
    }).setOrigin(0.5);

    bg.on('pointerdown', () => {
      if (!this._ready) return;
      this.cameras.main.fadeOut(400, 0, 0, 0);
      this.cameras.main.once('camerafadeoutcomplete', () => {
        localStorage.setItem('pw_profile', JSON.stringify(this.profile));
        this.scene.start('Overworld', { profile: this.profile });
      });
    });
    bg.on('pointerover', () => { if (this._ready) bg.setFillStyle(0x143a14); });
    bg.on('pointerout', () => { if (this._ready) bg.setFillStyle(0x0a2a0a); });

    return { bg, border, text };
  }

  _checkReady() {
    const ready = this.profile.name.trim().length >= 2;
    this._ready = ready;
    this._startBtn.bg.setFillStyle(ready ? 0x0a2a0a : 0x0a1a0a);
    this._startBtn.border.setStrokeStyle(2, ready ? 0x44cc44 : 0x1a2a1a);
    this._startBtn.text.setColor(ready ? '#44cc44' : '#1a3a1a');
  }
}
