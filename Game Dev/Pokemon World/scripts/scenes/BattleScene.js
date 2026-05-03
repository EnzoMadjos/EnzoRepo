/**
 * BattleScene.js — Phase 3 Steps 6/7/8
 * Full Gen 3 wild battle — layout, combat loop, catch, EXP, end.
 */

class BattleScene extends Phaser.Scene {
  constructor() { super({ key: 'Battle' }); }

  // ---------------------------------------------------------------------------
  // Lifecycle
  // ---------------------------------------------------------------------------
  init(data) {
    this._enemyMon  = data.enemyPokemon;
    this._playerMon = data.playerPokemon;
    this._zone      = data.zone || 'tall_grass';
    this._returnPos = data.returnPos || null;
    this._profile   = data.profile || JSON.parse(localStorage.getItem('pw_profile') || '{}');
    this._state     = 'IDLE';
    this._inputEnabled = false;
    this._menuCursor   = 0;
    this._menuItems    = [];
    // UI refs cleared on each menu open
    this._menuBg         = null;
    this._menuTexts      = null;
    this._menuCursorText = null;
    this._moveMenuBg     = null;
    this._moveTexts      = null;
    this._moveCancelText = null;
  }

  preload() {
    const eid = this._enemyMon.id;
    const pid = this._playerMon.id;
    if (!this.textures.exists(`be_${eid}`))
      this.load.image(`be_${eid}`, SETTINGS.PATHS.BATTLE_SPRITE(eid));
    if (!this.textures.exists(`bp_${pid}`))
      this.load.image(`bp_${pid}`, SETTINGS.PATHS.BATTLE_SPRITE_BACK(pid));
    const cryKey = `cry_${eid}`;
    if (!this.cache.audio.exists(cryKey))
      this.load.audio(cryKey, SETTINGS.PATHS.CRY(eid));
  }

  create() {
    const W = SETTINGS.SCREEN_W; // 960
    const H = SETTINGS.SCREEN_H; // 640

    this._buildBG(W, H);

    // Enemy Pokémon sprite — top right
    this._enemySprite = this.add.image(640, 195, `be_${this._enemyMon.id}`)
      .setOrigin(0.5).setScale(2.2).setDepth(10);

    // Player Pokémon back sprite — bottom left
    this._playerSprite = this.add.image(215, 390, `bp_${this._playerMon.id}`)
      .setOrigin(0.5).setScale(2.5).setDepth(10);

    // HP boxes
    this._enemyBox  = this._buildHPBox(30,  55, this._enemyMon,  false);
    this._playerBox = this._buildHPBox(510, 390, this._playerMon, true);

    // Textbox (bottom strip)
    const TBH = 120;
    this._tbY = H - TBH;
    this._tbW = W;
    this._tbH = TBH;
    this._buildTextbox(W, H, TBH);

    // Keys
    this._keys = {
      up:    this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.UP),
      down:  this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.DOWN),
      left:  this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.LEFT),
      right: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.RIGHT),
      z:     this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.Z),
      x:     this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.X),
      enter: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.ENTER),
      space: this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE),
    };

    this.cameras.main.fadeIn(300);
    this.time.delayedCall(350, () => this._doIntro());
  }

  // ---------------------------------------------------------------------------
  // Background
  // ---------------------------------------------------------------------------
  _buildBG(W, H) {
    // Sky
    const sky = this.add.graphics();
    sky.fillGradientStyle(0x87ceeb, 0x87ceeb, 0x4a90d9, 0x4a90d9, 1);
    sky.fillRect(0, 0, W, H * 0.56);
    // Ground
    const gnd = this.add.graphics();
    gnd.fillStyle(0x6ab04c, 1);
    gnd.fillRect(0, H * 0.56, W, H * 0.44);
    // Divider
    this.add.graphics().fillStyle(0x4a7c2f).fillRect(0, H * 0.56 - 4, W, 8);
    // Enemy platform
    const ep = this.add.graphics();
    ep.fillStyle(0x8bc34a).fillEllipse(640, 268, 240, 40);
    ep.fillStyle(0x6ab04c).fillEllipse(640, 272, 220, 28);
    // Player platform
    const pp = this.add.graphics();
    pp.fillStyle(0x8bc34a).fillEllipse(215, 452, 200, 36);
    pp.fillStyle(0x6ab04c).fillEllipse(215, 456, 180, 24);
  }

  // ---------------------------------------------------------------------------
  // HP Box
  // ---------------------------------------------------------------------------
  _buildHPBox(x, y, mon, isPlayer) {
    const BW = isPlayer ? 400 : 340;
    const BH = isPlayer ? 92  : 72;
    const container = this.add.container(x, y).setDepth(20);

    const bg = this.add.graphics();
    bg.fillStyle(0xf0f0e0, 1);
    bg.fillRoundedRect(0, 0, BW, BH, 8);
    bg.lineStyle(3, 0x3c3c3c, 1);
    bg.strokeRoundedRect(0, 0, BW, BH, 8);

    const nameText = this.add.text(10, 8, mon.name.toUpperCase(), {
      fontFamily: 'monospace', fontSize: '15px', color: '#1a1a1a', fontStyle: 'bold',
    });
    const lvlText = this.add.text(BW - 10, 8, `Lv${mon.level}`, {
      fontFamily: 'monospace', fontSize: '13px', color: '#1a1a1a',
    }).setOrigin(1, 0);

    const trackY  = isPlayer ? 36 : 32;
    const trackX  = isPlayer ? 60 : 12;
    const trackW  = BW - trackX - 12;

    // "HP/" label (player only)
    const hpLabel = this.add.text(trackX - (isPlayer ? 54 : 0), trackY - 2, isPlayer ? 'HP/' : '', {
      fontFamily: 'monospace', fontSize: '12px', color: '#1a1a1a', fontStyle: 'bold',
    });

    const hpTrack = this.add.graphics();
    hpTrack.fillStyle(0x444444, 1);
    hpTrack.fillRect(trackX, trackY, trackW, 10);

    const ratio = mon.currentHp / mon.maxHp;
    const barColor = ratio > 0.5 ? 0x33cc33 : ratio > 0.2 ? 0xffcc00 : 0xff3300;
    const hpBarGfx = this.add.graphics();
    hpBarGfx.fillStyle(barColor, 1);
    hpBarGfx.fillRect(trackX, trackY, Math.floor(trackW * ratio), 10);

    container.add([bg, nameText, lvlText, hpLabel, hpTrack, hpBarGfx]);

    let hpNumText = null;
    if (isPlayer) {
      hpNumText = this.add.text(BW / 2 + 20, trackY + 14, `${mon.currentHp}/${mon.maxHp}`, {
        fontFamily: 'monospace', fontSize: '13px', color: '#1a1a1a',
      }).setOrigin(0.5, 0);
      container.add(hpNumText);
    }

    // EXP bar (player only)
    let expBarGfx = null;
    const expTrackY = trackY + 38;
    const expTrackX = 40;
    const expTrackW = BW - expTrackX - 12;
    if (isPlayer) {
      const expLabel = this.add.text(10, expTrackY - 2, 'EXP', {
        fontFamily: 'monospace', fontSize: '11px', color: '#4444aa', fontStyle: 'bold',
      });
      const expTrack = this.add.graphics();
      expTrack.fillStyle(0x555577, 1);
      expTrack.fillRect(expTrackX, expTrackY, expTrackW, 7);
      expBarGfx = this.add.graphics();
      expBarGfx.fillStyle(0x4466ff, 1);
      const expMin   = BattleEngine.expForLevel(mon.level);
      const expMax   = BattleEngine.expForLevel(mon.level + 1);
      const expRatio = Math.min(1, Math.max(0, ((mon.exp || expMin) - expMin) / (expMax - expMin)));
      expBarGfx.fillRect(expTrackX, expTrackY, Math.floor(expTrackW * expRatio), 7);
      container.add([expLabel, expTrack, expBarGfx]);
    }

    return {
      container, hpBarGfx, hpTrack, hpNumText, expBarGfx,
      trackX, trackY, trackW,
      expTrackX, expTrackY, expTrackW,
      currentBarW: Math.floor(trackW * ratio),
    };
  }

  // ---------------------------------------------------------------------------
  // Textbox
  // ---------------------------------------------------------------------------
  _buildTextbox(W, H, TBH) {
    const TBY = H - TBH;
    const bg = this.add.graphics().setDepth(30);
    bg.fillStyle(0xf0f0e0, 1);
    bg.fillRect(0, TBY, W, TBH);
    bg.lineStyle(3, 0x3c3c3c, 1);
    bg.lineBetween(0, TBY, W, TBY);

    this._tbText = this.add.text(20, TBY + 16, '', {
      fontFamily: 'monospace', fontSize: '16px', color: '#1a1a1a',
      wordWrap: { width: W - 210 },
    }).setDepth(31);
  }

  // ---------------------------------------------------------------------------
  // Intro
  // ---------------------------------------------------------------------------
  _doIntro() {
    const name = this._enemyMon.name.toUpperCase();
    this._showText(`Wild ${name} appeared!`, () => {
      const cryKey = `cry_${this._enemyMon.id}`;
      if (this.cache.audio.exists(cryKey)) this.sound.play(cryKey, { volume: 0.5 });
      this.time.delayedCall(900, () => this._setState('ACTION_MENU'));
    });
  }

  // ---------------------------------------------------------------------------
  // State machine
  // ---------------------------------------------------------------------------
  _setState(state) {
    this._state = state;
    this._clearMenu();

    if (state === 'ACTION_MENU') {
      this._showText(`What will\n${this._playerMon.name.toUpperCase()} do?`, null);
      this._buildActionMenu();
    } else if (state === 'MOVE_MENU') {
      this._buildMoveMenu();
    } else if (state === 'FLED') {
      this._showText('Got away safely!', () => this.time.delayedCall(700, () => this._endBattle('flee')));
    }
  }

  // ---------------------------------------------------------------------------
  // Action menu: FIGHT / BAG / POKéMON / RUN
  // ---------------------------------------------------------------------------
  _buildActionMenu() {
    const TBY = this._tbY, W = this._tbW;
    const MX  = W - 330, MY = TBY + 8;
    const labels = ['FIGHT', 'BAG', 'POKéMON', 'RUN'];
    this._menuItems = labels;
    this._menuCursor = 0;
    this._menuOriginX = MX;
    this._menuOriginY = MY;

    const bg = this.add.graphics().setDepth(32);
    bg.fillStyle(0xe8e8d0, 1);
    bg.fillRoundedRect(MX, MY, 320, 104, 6);
    bg.lineStyle(2, 0x3c3c3c, 1);
    bg.strokeRoundedRect(MX, MY, 320, 104, 6);
    this._menuBg = bg;

    this._menuTexts = labels.map((lbl, i) => {
      const col = i % 2, row = Math.floor(i / 2);
      return this.add.text(MX + 24 + col * 160, MY + 22 + row * 46, lbl, {
        fontFamily: 'monospace', fontSize: '16px', color: '#1a1a1a', fontStyle: 'bold',
      }).setDepth(33);
    });

    this._menuCursorText = this.add.text(0, 0, '▶', {
      fontFamily: 'monospace', fontSize: '16px', color: '#cc0000',
    }).setDepth(34);

    this._updateActionCursor();
    this._inputEnabled = true;
  }

  _updateActionCursor() {
    if (!this._menuCursorText) return;
    const col = this._menuCursor % 2;
    const row = Math.floor(this._menuCursor / 2);
    this._menuCursorText.setPosition(
      this._menuOriginX + 6 + col * 160,
      this._menuOriginY + 22 + row * 46
    );
  }

  // ---------------------------------------------------------------------------
  // Move menu
  // ---------------------------------------------------------------------------
  _buildMoveMenu() {
    const TBY = this._tbY, W = this._tbW;
    this._tbText.setText('');
    const moves = this._playerMon.moves;
    this._menuItems = moves.map((_, i) => i);
    this._menuCursor = 0;

    const bg = this.add.graphics().setDepth(32);
    bg.fillStyle(0xe8e8d0, 1);
    bg.fillRect(0, TBY, W - 200, this._tbH);
    bg.lineStyle(2, 0x3c3c3c, 1);
    bg.lineBetween(W - 200, TBY, W - 200, TBY + this._tbH);
    this._moveMenuBg = bg;

    // Move type panel (right side)
    this._moveTypePanel = this.add.graphics().setDepth(32);
    this._moveTypePanel.fillStyle(0xd0d0c0, 1);
    this._moveTypePanel.fillRect(W - 198, TBY, 198, this._tbH);

    this._moveTexts = moves.map((mv, i) => {
      const col = i % 2, row = Math.floor(i / 2);
      const tx = 20 + col * ((W - 200) / 2);
      const ty = TBY + 16 + row * 46;
      const nameT = this.add.text(tx + 20, ty, mv.name.toUpperCase(), {
        fontFamily: 'monospace', fontSize: '15px', color: '#1a1a1a', fontStyle: 'bold',
      }).setDepth(33);
      const ppT = this.add.text(tx + 20, ty + 22, `PP  ${mv.pp}/${mv.maxPP}`, {
        fontFamily: 'monospace', fontSize: '12px', color: '#555577',
      }).setDepth(33);
      return [nameT, ppT];
    });

    this._moveTypeLabel = this.add.text(W - 99, TBY + 28, '', {
      fontFamily: 'monospace', fontSize: '13px', color: '#1a1a1a', fontStyle: 'bold',
    }).setOrigin(0.5, 0).setDepth(33);

    this._movePowerLabel = this.add.text(W - 99, TBY + 54, '', {
      fontFamily: 'monospace', fontSize: '12px', color: '#333355',
    }).setOrigin(0.5, 0).setDepth(33);

    this._menuCursorText = this.add.text(0, 0, '▶', {
      fontFamily: 'monospace', fontSize: '16px', color: '#cc0000',
    }).setDepth(34);

    this._updateMoveCursor();
    this._inputEnabled = true;
  }

  _updateMoveCursor() {
    if (!this._menuCursorText) return;
    const i   = this._menuCursor;
    const TBY = this._tbY, W = this._tbW;
    const col = i % 2, row = Math.floor(i / 2);
    this._menuCursorText.setPosition(
      4 + col * ((W - 200) / 2),
      TBY + 16 + row * 46
    );
    // Update type/power panel
    const mv = this._playerMon.moves[i];
    if (mv && this._moveTypeLabel) {
      this._moveTypeLabel.setText(`TYPE/\n${mv.type.toUpperCase()}`);
      this._movePowerLabel.setText(`PWR: ${mv.power || '—'}`);
    }
  }

  // ---------------------------------------------------------------------------
  // Clear all menu UI
  // ---------------------------------------------------------------------------
  _clearMenu() {
    this._inputEnabled = false;
    if (this._menuBg)         { this._menuBg.destroy();         this._menuBg = null; }
    if (this._menuTexts)      { this._menuTexts.forEach(t => t.destroy()); this._menuTexts = null; }
    if (this._menuCursorText) { this._menuCursorText.destroy(); this._menuCursorText = null; }
    if (this._moveMenuBg)     { this._moveMenuBg.destroy();     this._moveMenuBg = null; }
    if (this._moveTypePanel)  { this._moveTypePanel.destroy();  this._moveTypePanel = null; }
    if (this._moveTexts)      { this._moveTexts.forEach(p => p.forEach(t => t.destroy())); this._moveTexts = null; }
    if (this._moveCancelText) { this._moveCancelText.destroy(); this._moveCancelText = null; }
    if (this._moveTypeLabel)  { this._moveTypeLabel.destroy();  this._moveTypeLabel = null; }
    if (this._movePowerLabel) { this._movePowerLabel.destroy(); this._movePowerLabel = null; }
  }

  // ---------------------------------------------------------------------------
  // update() — keyboard input
  // ---------------------------------------------------------------------------
  update() {
    if (!this._inputEnabled) return;
    const jd = k => Phaser.Input.Keyboard.JustDown(k);
    const confirm = jd(this._keys.z) || jd(this._keys.enter) || jd(this._keys.space);
    const cancel  = jd(this._keys.x);
    const maxIdx  = this._menuItems.length - 1;
    let moved = false;

    if (jd(this._keys.right)) { this._menuCursor = Math.min(this._menuCursor + 1, maxIdx); moved = true; }
    if (jd(this._keys.left))  { this._menuCursor = Math.max(this._menuCursor - 1, 0);      moved = true; }
    if (jd(this._keys.down))  { this._menuCursor = Math.min(this._menuCursor + 2, maxIdx); moved = true; }
    if (jd(this._keys.up))    { this._menuCursor = Math.max(this._menuCursor - 2, 0);      moved = true; }

    if (moved) {
      if (this._state === 'ACTION_MENU') this._updateActionCursor();
      if (this._state === 'MOVE_MENU')   this._updateMoveCursor();
    }

    if (confirm) {
      if (this._state === 'ACTION_MENU') this._onActionSelected(this._menuCursor);
      if (this._state === 'MOVE_MENU')   this._onMoveSelected(this._menuCursor);
    }
    if (cancel && this._state === 'MOVE_MENU') this._setState('ACTION_MENU');
  }

  // ---------------------------------------------------------------------------
  // Action selected
  // ---------------------------------------------------------------------------
  _onActionSelected(idx) {
    this._inputEnabled = false;
    const actions = ['FIGHT', 'BAG', 'POKEMON', 'RUN'];
    const action  = actions[idx] || 'RUN';
    if      (action === 'FIGHT')   { this._setState('MOVE_MENU'); }
    else if (action === 'BAG')     { this._onBagSelected(); }
    else if (action === 'POKEMON') { this._showText("Can't switch Pokémon yet!", () => this._setState('ACTION_MENU')); }
    else if (action === 'RUN')     { this._tryRun(); }
  }

  // ---------------------------------------------------------------------------
  // Move selected
  // ---------------------------------------------------------------------------
  _onMoveSelected(idx) {
    const move = this._playerMon.moves[idx];
    if (!move) { this._setState('ACTION_MENU'); return; }
    if (move.pp <= 0) { this._showText('No PP left!', () => this._setState('MOVE_MENU')); return; }
    this._inputEnabled = false;
    this._clearMenu();
    this._executeTurn(move);
  }

  // ---------------------------------------------------------------------------
  // Turn execution
  // ---------------------------------------------------------------------------
  _executeTurn(playerMove) {
    const pSpe = this._playerMon.stats.spe;
    const eSpe = this._enemyMon.stats.spe;
    const playerFirst = pSpe > eSpe || (pSpe === eSpe && Math.random() < 0.5);

    if (playerFirst) {
      this._doPlayerAttack(playerMove, () => {
        if (this._enemyMon.currentHp <= 0) { this._handleVictory(); return; }
        this._doEnemyAttack(() => {
          if (this._playerMon.currentHp <= 0) { this._handleDefeat(); return; }
          this._setState('ACTION_MENU');
        });
      });
    } else {
      this._doEnemyAttack(() => {
        if (this._playerMon.currentHp <= 0) { this._handleDefeat(); return; }
        this._doPlayerAttack(playerMove, () => {
          if (this._enemyMon.currentHp <= 0) { this._handleVictory(); return; }
          this._setState('ACTION_MENU');
        });
      });
    }
  }

  _doPlayerAttack(move, cb) {
    const pMon = this._playerMon, eMon = this._enemyMon;
    const physical = BattleEngine.isPhysical(move.type);
    const atkStat  = physical ? pMon.stats.atk : pMon.stats.spa;
    const defStat  = physical ? eMon.stats.def : eMon.stats.spd;
    const typeEff  = BattleEngine.getTypeEffectiveness(move.type, eMon.types);
    const stab     = pMon.types.includes(move.type);
    const crit     = Math.random() < (1 / 16);
    const randPct  = 85 + Math.floor(Math.random() * 16);
    move.pp        = Math.max(0, move.pp - 1);
    const dmg      = BattleEngine.calcDamage(pMon.level, move.power, atkStat, defStat, typeEff, stab, crit, randPct);

    this._showText(`${pMon.name.toUpperCase()} used\n${move.name.toUpperCase()}!`, () => {
      if (!BattleEngine.checkAccuracy(move.accuracy)) {
        this._showText("It missed!", cb); return;
      }
      this._flashSprite(this._enemySprite, () => {
        this._applyDamage(eMon, dmg, this._enemyBox, () => {
          const eff = this._effMsg(typeEff, crit);
          if (eff) this._showText(eff, cb); else cb();
        });
      });
    });
  }

  _doEnemyAttack(cb) {
    const eMon = this._enemyMon, pMon = this._playerMon;
    const move = BattleEngine.aiPickMove(eMon, pMon);
    if (!move) { cb(); return; }
    const physical = BattleEngine.isPhysical(move.type);
    const atkStat  = physical ? eMon.stats.atk : eMon.stats.spa;
    const defStat  = physical ? pMon.stats.def : pMon.stats.spd;
    const typeEff  = BattleEngine.getTypeEffectiveness(move.type, pMon.types);
    const stab     = eMon.types.includes(move.type);
    const crit     = Math.random() < (1 / 16);
    const randPct  = 85 + Math.floor(Math.random() * 16);
    move.pp        = Math.max(0, move.pp - 1);
    const dmg      = BattleEngine.calcDamage(eMon.level, move.power, atkStat, defStat, typeEff, stab, crit, randPct);

    this._showText(`Wild ${eMon.name.toUpperCase()} used\n${move.name.toUpperCase()}!`, () => {
      if (!BattleEngine.checkAccuracy(move.accuracy)) {
        this._showText("It missed!", cb); return;
      }
      this._flashSprite(this._playerSprite, () => {
        this._applyDamage(pMon, dmg, this._playerBox, () => {
          const eff = this._effMsg(typeEff, crit);
          if (eff) this._showText(eff, cb); else cb();
        });
      });
    });
  }

  _effMsg(typeEff, crit) {
    let msg = '';
    if      (typeEff === 0)        msg = "It doesn't affect the\nwild Pokémon…";
    else if (typeEff >= 2)         msg = "It's super effective!";
    else if (typeEff > 0 && typeEff < 1) msg = "It's not very effective…";
    if (crit) msg = msg ? msg + '\nA critical hit!' : 'A critical hit!';
    return msg;
  }

  // ---------------------------------------------------------------------------
  // Damage + HP bar animation
  // ---------------------------------------------------------------------------
  _applyDamage(mon, dmg, box, cb) {
    const prevHp = mon.currentHp;
    mon.currentHp = Math.max(0, mon.currentHp - dmg);
    this._animHPBar(mon, box, prevHp, cb);
  }

  _animHPBar(mon, box, prevHp, cb) {
    const ratio    = mon.currentHp / mon.maxHp;
    const prevRatio = prevHp / mon.maxHp;
    const targetW  = Math.floor(box.trackW * ratio);
    const startW   = Math.floor(box.trackW * prevRatio);
    const barColor = ratio > 0.5 ? 0x33cc33 : ratio > 0.2 ? 0xffcc00 : 0xff3300;
    const proxy    = { w: startW };

    this.tweens.add({
      targets: proxy, w: targetW, duration: 500, ease: 'Linear',
      onUpdate: () => {
        box.hpBarGfx.clear();
        box.hpBarGfx.fillStyle(barColor, 1);
        box.hpBarGfx.fillRect(box.trackX, box.trackY, Math.max(0, Math.floor(proxy.w)), 10);
      },
      onComplete: () => {
        box.currentBarW = targetW;
        if (box.hpNumText) box.hpNumText.setText(`${mon.currentHp}/${mon.maxHp}`);
        cb();
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Sprite flash (hit)
  // ---------------------------------------------------------------------------
  _flashSprite(sprite, cb) {
    let n = 0;
    this.time.addEvent({
      delay: 80, repeat: 5,
      callback: () => {
        sprite.setVisible(!sprite.visible);
        if (++n >= 6) { sprite.setVisible(true); cb(); }
      },
    });
  }

  // ---------------------------------------------------------------------------
  // Victory / Defeat / Flee
  // ---------------------------------------------------------------------------
  _handleVictory() {
    const eName = this._enemyMon.name.toUpperCase();
    this._showText(`Wild ${eName} fainted!`, () => this._handleExpGain(() => this._endBattle('win')));
  }

  _handleDefeat() {
    const pName = this._playerMon.name.toUpperCase();
    this._showText(`${pName} fainted!\nYou blacked out!`, () => this._endBattle('lose'));
  }

  _tryRun() {
    this._setState('FLED');
  }

  // ---------------------------------------------------------------------------
  // Bag / Catch
  // ---------------------------------------------------------------------------
  _onBagSelected() {
    this._clearMenu();
    this._showText('You threw a Poké Ball!', () => this._doCatchAnim());
  }

  _doCatchAnim() {
    const result = BattleEngine.calcCatch(
      this._enemyMon.maxHp, this._enemyMon.currentHp, this._enemyMon.catchRate, 1
    );

    // Fade enemy out (ball absorbs it)
    this.tweens.add({
      targets: this._enemySprite, alpha: 0, duration: 200,
      onComplete: () => {
        this.time.delayedCall(300, () => {
          this._enemySprite.setAlpha(1);
          this._doShakes(result, 0);
        });
      },
    });
  }

  _doShakes(result, shakesDone) {
    if (shakesDone >= result.shakes) {
      if (result.caught) {
        const eName = this._enemyMon.name.toUpperCase();
        this._showText(`Gotcha!\nWild ${eName} was caught!`, () => this._catchPokemon());
      } else {
        const msgs = [
          "Oh no! The Pokémon broke free!",
          "Aww! It appeared to be caught!",
          "Darn! The Pokémon broke free!",
        ];
        this._showText(msgs[Math.min(result.shakes, msgs.length - 1)], () => {
          this._doEnemyAttack(() => {
            if (this._playerMon.currentHp <= 0) { this._handleDefeat(); return; }
            this._setState('ACTION_MENU');
          });
        });
      }
      return;
    }

    this.tweens.add({
      targets: this._enemySprite, x: this._enemySprite.x + 10,
      duration: 80, yoyo: true, repeat: 1,
      onComplete: () => this.time.delayedCall(300, () => this._doShakes(result, shakesDone + 1)),
    });
  }

  _catchPokemon() {
    const caught = { ...this._enemyMon };
    caught.exp     = BattleEngine.expForLevel(caught.level);
    caught.expToNext = BattleEngine.expForLevel(caught.level + 1);
    const party = JSON.parse(localStorage.getItem('pw_party') || '[]');
    if (party.length < 6) {
      party.push(caught);
      localStorage.setItem('pw_party', JSON.stringify(party));
    }
    this._endBattle('caught');
  }

  // ---------------------------------------------------------------------------
  // EXP gain + level-up
  // ---------------------------------------------------------------------------
  _handleExpGain(cb) {
    const pMon = this._playerMon;
    const gain = BattleEngine.calcExpGain(this._enemyMon.baseExpYield, this._enemyMon.level);
    pMon.exp = (pMon.exp || BattleEngine.expForLevel(pMon.level)) + gain;

    this._showText(`${pMon.name.toUpperCase()} gained\n${gain} EXP. Points!`, () => {
      this._animExpBar(pMon, () => this._checkLevelUp(pMon, cb));
    });
  }

  _animExpBar(mon, cb) {
    const box = this._playerBox;
    if (!box.expBarGfx) { cb(); return; }
    const expMin = BattleEngine.expForLevel(mon.level);
    const expMax = BattleEngine.expForLevel(mon.level + 1);
    const ratio  = Math.min(1, Math.max(0, (mon.exp - expMin) / (expMax - expMin)));
    const targetW = Math.floor(box.expTrackW * ratio);
    const proxy   = { w: 0 };

    this.tweens.add({
      targets: proxy, w: targetW, duration: 800, ease: 'Linear',
      onUpdate: () => {
        box.expBarGfx.clear();
        box.expBarGfx.fillStyle(0x4466ff, 1);
        box.expBarGfx.fillRect(box.expTrackX, box.expTrackY, Math.max(0, Math.floor(proxy.w)), 7);
      },
      onComplete: cb,
    });
  }

  _checkLevelUp(mon, cb) {
    if (mon.exp >= BattleEngine.expForLevel(mon.level + 1)) {
      mon.level += 1;
      const species = window.GAME_DATA?.pokemonById?.get(mon.id);
      if (species) {
        const upgraded = BattleEngine.buildBattleMon(species, mon.level);
        const hpGain   = upgraded.maxHp - mon.maxHp;
        mon.stats    = upgraded.stats;
        mon.maxHp    = upgraded.maxHp;
        mon.currentHp = Math.min(mon.currentHp + hpGain, upgraded.maxHp);
        this._animHPBar(mon, this._playerBox, mon.currentHp - hpGain, () => {});
      }
      this._showText(`${mon.name.toUpperCase()} grew to\nlevel ${mon.level}!`, () => {
        this._saveParty();
        this._checkLevelUp(mon, cb);
      });
    } else {
      this._saveParty();
      cb();
    }
  }

  // ---------------------------------------------------------------------------
  // Save party
  // ---------------------------------------------------------------------------
  _saveParty() {
    try {
      const party = JSON.parse(localStorage.getItem('pw_party') || '[]');
      if (party.length > 0) {
        party[0] = this._playerMon;
        localStorage.setItem('pw_party', JSON.stringify(party));
      }
    } catch (_) {}
  }

  // ---------------------------------------------------------------------------
  // End battle
  // ---------------------------------------------------------------------------
  _endBattle(result) {
    this._saveParty();
    this._inputEnabled = false;
    this.cameras.main.fadeOut(400);
    this.cameras.main.once('camerafadeoutcomplete', () => this._returnToOverworld());
  }

  _returnToOverworld() {
    this.scene.start('Overworld', {
      profile: this._profile,
      returnPos: this._returnPos,
    });
  }

  // ---------------------------------------------------------------------------
  // Typewriter text
  // ---------------------------------------------------------------------------
  _showText(msg, cb) {
    this._inputEnabled = false;
    this._tbText.setText('');
    const chars = msg.split('');
    let i = 0;
    this.time.addEvent({
      delay: 28,
      repeat: chars.length - 1,
      callback: () => { this._tbText.setText(chars.slice(0, ++i).join('')); },
    });
    this.time.delayedCall(chars.length * 28 + 700, () => { if (cb) cb(); });
  }
}
