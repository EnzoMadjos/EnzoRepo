/**
 * StarterSelect.js
 * Professor Oak intro + pick Bulbasaur / Charmander / Squirtle.
 * Flow: CharacterCreate → StarterSelect → Overworld
 */

class StarterSelect extends Phaser.Scene {
  constructor() {
    super({ key: 'StarterSelect' });
  }

  init(data) {
    this._profile = data.profile || { gender: 'boy', outfit: 0, name: 'PLAYER' };
  }

  preload() {
    [1, 4, 7].forEach(id => {
      this.load.image(`starter_${id}`, `/assets/sprites/battle/main-sprites/emerald/${id}.png`);
    });
  }

  create() {
    const W = SETTINGS.SCREEN_W;
    const H = SETTINGS.SCREEN_H;

    this._starters = [
      { id: 1, name: 'Bulbasaur',  type1: 'GRASS',  type2: 'POISON', col: 0x4caf50 },
      { id: 4, name: 'Charmander', type1: 'FIRE',   type2: null,     col: 0xff6f20 },
      { id: 7, name: 'Squirtle',   type1: 'WATER',  type2: null,     col: 0x2196f3 },
    ];

    this._cursor    = 1; // default Charmander (center)
    this._confirmed = false;

    // Background
    this.add.rectangle(W / 2, H / 2, W, H, 0x0a0a1a);
    this._addStars();

    // Oak box
    this.add.rectangle(W / 2, 56, W - 80, 80, 0x0d1525).setStrokeStyle(1, 0x2a4a6a);
    this.add.text(60, 56,
      `Welcome, ${this._profile.name || 'Trainer'}!  I am Professor Oak.\nThis world is full of Pokemon! Choose your first partner!`,
      { fontFamily: 'monospace', fontSize: '14px', color: '#e8e8e8', wordWrap: { width: W - 130 } }
    ).setOrigin(0, 0.5);

    this.add.text(W / 2, 108,
      'Click a Pokemon to select   |   double-click or Z/Enter to confirm',
      { fontFamily: 'monospace', fontSize: '11px', color: '#2a5a6a' }
    ).setOrigin(0.5);

    // Pedestals
    const podY  = H / 2 + 30;
    const podXs = [W * 0.22, W * 0.5, W * 0.78];
    this._pods  = this._starters.map((s, i) => this._buildPod(podXs[i], podY, s, i));

    // Cursor arrow
    this._arrow = this.add.text(0, 0, 'v', {
      fontFamily: 'monospace', fontSize: '18px', color: '#FFD700', fontStyle: 'bold',
    }).setOrigin(0.5).setDepth(10);

    // Confirm bar
    this._confirmBar  = this.add.rectangle(W / 2, H - 36, W - 80, 44, 0x0d1525).setStrokeStyle(1, 0x2a4a6a);
    this._confirmText = this.add.text(W / 2, H - 36, '', {
      fontFamily: 'monospace', fontSize: '14px', color: '#FFD700',
    }).setOrigin(0.5);

    // Keys
    this._keys = this.input.keyboard.addKeys({
      left:  Phaser.Input.Keyboard.KeyCodes.LEFT,
      right: Phaser.Input.Keyboard.KeyCodes.RIGHT,
      z:     Phaser.Input.Keyboard.KeyCodes.Z,
      enter: Phaser.Input.Keyboard.KeyCodes.ENTER,
    });

    // Show initial selection right away
    this._updateSelection();
  }

  _buildPod(cx, cy, starter, idx) {
    // Use Rectangle (not Graphics) as the clickable bg — reliable hit area
    const bg = this.add.rectangle(cx, cy + 40, 148, 130, 0x111827)
      .setStrokeStyle(1, starter.col)
      .setInteractive({ useHandCursor: true });

    const img = this.add.image(cx, cy - 22, `starter_${starter.id}`)
      .setScale(1.3).setOrigin(0.5, 1);

    const nameT = this.add.text(cx, cy + 8, starter.name.toUpperCase(), {
      fontFamily: 'monospace', fontSize: '15px', color: '#ffffff', fontStyle: 'bold',
    }).setOrigin(0.5);

    const typeStr = starter.type2 ? `${starter.type1} / ${starter.type2}` : starter.type1;
    const typeT = this.add.text(cx, cy + 34, typeStr, {
      fontFamily: 'monospace', fontSize: '11px', color: '#aabbcc',
    }).setOrigin(0.5);

    bg.on('pointerdown', () => {
      if (this._confirmed) return;
      this._cursor = idx;
      this._updateSelection();
    });
    bg.on('pointerdblclick', () => {
      if (this._confirmed) return;
      this._cursor = idx;
      this._updateSelection();
      this._onConfirm();
    });
    bg.on('pointerover', () => {
      if (!this._confirmed && this._cursor !== idx) bg.setFillStyle(0x1a2535);
    });
    bg.on('pointerout', () => {
      if (this._cursor !== idx) bg.setFillStyle(0x111827);
    });

    return { bg, img, nameT, typeT, starter, cx, cy };
  }

  _addStars() {
    for (let i = 0; i < 80; i++) {
      this.add.circle(
        Phaser.Math.Between(0, SETTINGS.SCREEN_W),
        Phaser.Math.Between(0, SETTINGS.SCREEN_H),
        Phaser.Math.Between(1, 2), 0xffffff,
        Phaser.Math.FloatBetween(0.05, 0.3)
      );
    }
  }

  _updateSelection() {
    const W     = SETTINGS.SCREEN_W;
    const podXs = [W * 0.22, W * 0.5, W * 0.78];
    const baseY = SETTINGS.SCREEN_H / 2 + 30;

    this._pods.forEach((p, i) => {
      const sel = i === this._cursor;
      const a   = sel ? 1 : 0.4;
      p.img.setAlpha(a).setScale(sel ? 1.5 : 1.3);
      p.nameT.setAlpha(a);
      p.typeT.setAlpha(a);
      p.bg.setAlpha(a).setStrokeStyle(sel ? 2 : 1, p.starter.col);
      if (sel) p.bg.setFillStyle(0x0d1e30);
      else     p.bg.setFillStyle(0x111827);
    });

    this._arrow.setPosition(podXs[this._cursor], baseY + 112);

    const s = this._starters[this._cursor];
    this._confirmText.setText(
      `> ${s.name.toUpperCase()}  (${s.type1}${s.type2 ? '/' + s.type2 : ''})     Z / Enter = YES     double-click = instant`
    );
  }

  _onConfirm() {
    if (this._confirmed) return;
    this._confirmed = true;

    const chosen  = this._starters[this._cursor];
    const species = window.GAME_DATA.pokemonById.get(chosen.id);
    const lvl     = SETTINGS.BATTLE.STARTER_LEVEL;

    const starter     = BattleEngine.buildBattleMon(species, lvl);
    starter.exp       = BattleEngine.expForLevel(lvl);
    starter.expToNext = BattleEngine.expForLevel(lvl + 1);
    localStorage.setItem('pw_party', JSON.stringify([starter]));

    const p = this._pods[this._cursor];
    this._confirmText.setText(`You chose  ${chosen.name.toUpperCase()}!`).setColor('#44ff88');

    this.tweens.add({
      targets: [p.img, p.bg, p.nameT, p.typeT],
      alpha: 0, scaleX: 1.2, scaleY: 1.2,
      duration: 350, ease: 'Power2',
      onComplete: () => {
        this.time.delayedCall(650, () => {
          this.cameras.main.fadeOut(400, 0, 0, 0);
          this.time.delayedCall(420, () => {
            this.scene.start('Overworld', { profile: this._profile });
          });
        });
      },
    });
  }

  update() {
    if (this._confirmed) return;
    const jd = k => Phaser.Input.Keyboard.JustDown(k);

    if (jd(this._keys.right)) { this._cursor = Math.min(this._cursor + 1, 2); this._updateSelection(); }
    if (jd(this._keys.left))  { this._cursor = Math.max(this._cursor - 1, 0); this._updateSelection(); }
    if (jd(this._keys.z) || jd(this._keys.enter)) { this._onConfirm(); }
  }
}
