class Overworld extends Phaser.Scene {
  constructor() { super({ key: 'Overworld' }); }

  init(data) {
    this.profile = data.profile
      || JSON.parse(localStorage.getItem('pw_profile') || 'null')
      || { gender: 'boy', outfit: 0, name: 'TRAINER' };
  }

  create() {
    const TS = SETTINGS.TILE_SIZE;

    this.mapData = [
      '222222222222222222222222222222',
      '200000000000055555005555500002',
      '200044000000065555065555500002',
      '200044000000055555005555500002',
      '200000000000000000000000000002',
      '200011100000440000044400000002',
      '200011100444000000000000000002',
      '211111100011111111111111111112',
      '201111100011000000000111111112',
      '201111100011000000000100000002',
      '201111111111000222000100000002',
      '201111100011000202000100000002',
      '201111100011000202000111111112',
      '211111100011111111111111000002',
      '200000000011000000000000444002',
      '200000000011000000000000444002',
      '200044000011000000000000000002',
      '200044000011000000000000000002',
      '200000000011000000000000000002',
      '222222222211222222222222222222',
    ];

    this.ROWS = this.mapData.length;
    this.COLS = this.mapData[0].length;
    this.mapWidth  = this.COLS * TS;
    this.mapHeight = this.ROWS * TS;
    this.collidable = new Set(['2', '3', '5']);

    this.tileGfx = this.add.graphics();
    this._drawMap();

    this.playerTileX = 5;
    this.playerTileY = 10;
    this.facing    = 'down';
    this.walkFrame = 0;
    this.isMoving  = false;

    this.playerGfx = this.add.graphics();
    this.playerGfx.setPosition(this.playerTileX * TS + TS / 2, this.playerTileY * TS + TS / 2);
    this.playerGfx.setDepth(20);
    this._drawPlayer();

    this._spawnNPCs();

    this.cameras.main.setBounds(0, 0, this.mapWidth, this.mapHeight);
    this.cameras.main.startFollow(this.playerGfx, true, 0.12, 0.12);
    this.cameras.main.fadeIn(400);

    this.cursors  = this.input.keyboard.createCursorKeys();
    this.wasd     = this.input.keyboard.addKeys({
      up: Phaser.Input.Keyboard.KeyCodes.W, down: Phaser.Input.Keyboard.KeyCodes.S,
      left: Phaser.Input.Keyboard.KeyCodes.A, right: Phaser.Input.Keyboard.KeyCodes.D,
    });
    this.spaceKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE);
    this.enterKey = this.input.keyboard.addKey(Phaser.Input.Keyboard.KeyCodes.ENTER);

    this.dialogue = new DialogueBox(this);
    this._createHUD();
  }

  _drawMap() {
    const TS = SETTINGS.TILE_SIZE;
    const g  = this.tileGfx;
    g.clear();

    for (let row = 0; row < this.ROWS; row++) {
      for (let col = 0; col < this.COLS; col++) {
        const tile = this.mapData[row][col];
        const base = SETTINGS.TILE_COLORS[parseInt(tile)] ?? SETTINGS.TILE_COLORS[0];
        const x = col * TS, y = row * TS;

        g.fillStyle(base);
        g.fillRect(x, y, TS, TS);

        if (tile === '2') {
          g.fillStyle(0x145214);
          g.fillCircle(x + TS/2, y + TS/2 - 4, 17);
          g.fillStyle(0x6b3a2a);
          g.fillRect(x + TS/2 - 4, y + TS/2 + 8, 8, 14);
        } else if (tile === '4') {
          g.fillStyle(0x2e7d32);
          const seed = (col * 7 + row * 3) % 4;
          for (let b = 0; b < 4; b++) {
            const bx = x + 6 + ((b + seed) % 4) * 11;
            g.fillRect(bx, y + 8, 3, 22);
            g.fillRect(bx + 4, y + 16, 3, 16);
          }
        } else if (tile === '3') {
          g.fillStyle(0x5ba3e0, 0.45);
          g.fillRect(x + 4, y + TS/3, TS - 8, 4);
          g.fillRect(x + 10, y + TS/2 + 4, TS - 20, 4);
        } else if (tile === '1') {
          const px = x + 4 + ((col * 13 + row * 5) % 30);
          const py = y + 4 + ((col * 9  + row * 11) % 30);
          g.fillStyle(0xb8945e, 0.5);
          g.fillCircle(px, py, 2);
        } else if (tile === '5') {
          g.fillStyle(0xcc9955);
          g.fillRect(x, y, TS, TS);
          g.lineStyle(1, 0xaa7733, 0.7);
          for (let br = 0; br < 3; br++) {
            g.strokeRect(x + (br % 2) * (TS/2), y + br * 16, TS/2, 16);
          }
          if (row === 1) {
            g.fillStyle(0x87ceeb, 0.95);
            g.fillRect(x + 8,  y + 10, 13, 11);
            g.fillRect(x + 26, y + 10, 13, 11);
            g.lineStyle(1, 0x4466cc);
            g.strokeRect(x + 8,  y + 10, 13, 11);
            g.strokeRect(x + 26, y + 10, 13, 11);
          }
        } else if (tile === '6') {
          g.fillStyle(0xcc9955);
          g.fillRect(x, y, TS, TS);
          g.fillStyle(0xcc3333);
          g.fillRect(x, y, TS, 7);
          g.fillStyle(0x7a3b1e);
          g.fillRect(x + TS/4, y + TS/4, TS/2, TS * 3/4);
          g.lineStyle(2, 0x4a2010);
          g.strokeRect(x + TS/4, y + TS/4, TS/2, TS * 3/4);
          g.fillStyle(0xFFD700);
          g.fillCircle(x + TS/4 + TS/2 - 7, y + TS/2 + 4, 3);
        }

        g.lineStyle(1, 0x000000, 0.05);
        g.strokeRect(x, y, TS, TS);
      }
    }

    const TS2 = SETTINGS.TILE_SIZE;
    this.add.text(13 * TS2 + TS2, 4, "OAK'S LAB", {
      fontSize: '9px', color: '#ffffff', fontFamily: 'monospace', fontStyle: 'bold',
      stroke: '#000000', strokeThickness: 2,
    }).setDepth(50).setOrigin(0.5, 0);
    this.add.text(19 * TS2 + TS2, 4, 'POKÉMON CENTER', {
      fontSize: '9px', color: '#ffaaaa', fontFamily: 'monospace', fontStyle: 'bold',
      stroke: '#000000', strokeThickness: 2,
    }).setDepth(50).setOrigin(0.5, 0);
  }

  _drawPlayer() {
    const g      = this.playerGfx;
    const outfit = SETTINGS.OUTFIT_COLORS[this.profile.outfit];
    const isBoy  = this.profile.gender === 'boy';
    const f      = this.walkFrame;
    const s      = 0.78;
    const sr     = v => Math.round(v * s);
    g.clear();
    g.fillStyle(0x000000, 0.18);
    g.fillEllipse(0, sr(28), sr(32), sr(10));
    if      (this.facing === 'down')  this._pDown(g, sr, outfit, isBoy, f);
    else if (this.facing === 'up')    this._pUp  (g, sr, outfit, isBoy, f);
    else if (this.facing === 'left')  this._pSide(g, sr, outfit, isBoy, f, -1);
    else                              this._pSide(g, sr, outfit, isBoy, f,  1);
  }

  _pDown(g, sr, outfit, isBoy, f) {
    const ls = f === 0 ? 0 : -7;
    const rs = f === 0 ? 0 :  7;
    g.fillStyle(0x2c3e50);
    g.fillRect(sr(-13), sr(8 + ls), sr(10), sr(15));
    g.fillRect(sr(3),   sr(8 + rs), sr(10), sr(15));
    g.fillStyle(0x3d2b1f);
    g.fillRect(sr(-14), sr(21 + ls), sr(12), sr(8));
    g.fillRect(sr(2),   sr(21 + rs), sr(12), sr(8));
    g.fillStyle(outfit.primary);
    g.fillRect(sr(-13), sr(-3), sr(26), sr(13));
    g.fillRect(sr(-21), sr(-3 + rs), sr(9), sr(14));
    g.fillRect(sr(12),  sr(-3 + ls), sr(9), sr(14));
    g.fillStyle(0xf5c6a0);
    g.fillRect(sr(-21), sr(9 + rs), sr(9), sr(8));
    g.fillRect(sr(12),  sr(9 + ls), sr(9), sr(8));
    g.fillStyle(0xf5c6a0);
    g.fillCircle(0, sr(-15), sr(13));
    g.fillStyle(outfit.secondary);
    g.fillRect(sr(-14), sr(-27), sr(28), sr(12));
    g.fillRect(sr(2),   sr(-18), sr(13), sr(5));
    g.fillStyle(0x1a1a2e);
    g.fillCircle(sr(-5), sr(-14), sr(3));
    g.fillCircle(sr(5),  sr(-14), sr(3));
    g.fillStyle(0xffffff);
    g.fillCircle(sr(-4), sr(-15), 1.5);
    g.fillCircle(sr(6),  sr(-15), 1.5);
    if (!isBoy) {
      g.fillStyle(outfit.secondary);
      g.fillRect(sr(-20), sr(-14), sr(6), sr(18));
      g.fillRect(sr(14),  sr(-14), sr(6), sr(18));
    }
  }

  _pUp(g, sr, outfit, isBoy, f) {
    const ls = f === 0 ? 0 : -7;
    const rs = f === 0 ? 0 :  7;
    g.fillStyle(0x2c3e50);
    g.fillRect(sr(-13), sr(8 + ls), sr(10), sr(15));
    g.fillRect(sr(3),   sr(8 + rs), sr(10), sr(15));
    g.fillStyle(0x3d2b1f);
    g.fillRect(sr(-14), sr(21 + ls), sr(12), sr(8));
    g.fillRect(sr(2),   sr(21 + rs), sr(12), sr(8));
    g.fillStyle(outfit.primary);
    g.fillRect(sr(-13), sr(-3), sr(26), sr(13));
    g.fillRect(sr(-21), sr(-3 + rs), sr(9), sr(14));
    g.fillRect(sr(12),  sr(-3 + ls), sr(9), sr(14));
    g.fillStyle(0xf5c6a0);
    g.fillRect(sr(-21), sr(9 + rs), sr(9), sr(8));
    g.fillRect(sr(12),  sr(9 + ls), sr(9), sr(8));
    g.fillStyle(0xf5c6a0);
    g.fillCircle(0, sr(-15), sr(13));
    g.fillStyle(outfit.secondary);
    g.fillRect(sr(-14), sr(-27), sr(28), sr(22));
    if (!isBoy) {
      g.fillRect(sr(-20), sr(-14), sr(6), sr(20));
      g.fillRect(sr(14),  sr(-14), sr(6), sr(20));
    }
  }

  _pSide(g, sr, outfit, isBoy, f, flip) {
    const step = f === 0 ? 0 : 7;
    g.fillStyle(0x2c3e50);
    g.fillRect(flip * sr(-4), sr(8 - step), sr(9), sr(15));
    g.fillRect(flip * sr(-4), sr(8 + step), sr(9), sr(15));
    g.fillStyle(0x3d2b1f);
    g.fillRect(flip * sr(-5), sr(21 - step), sr(11), sr(8));
    g.fillRect(flip * sr(-5), sr(21 + step), sr(11), sr(8));
    g.fillStyle(outfit.primary);
    g.fillRect(flip * sr(-10), sr(-3), sr(18), sr(13));
    const ay = f === 0 ? 0 : -4;
    g.fillRect(flip * sr(-18), sr(-3 + ay), sr(9), sr(14));
    g.fillStyle(0xf5c6a0);
    g.fillRect(flip * sr(-18), sr(9 + ay), sr(9), sr(8));
    g.fillStyle(0xf5c6a0);
    g.fillCircle(flip * sr(2), sr(-15), sr(13));
    g.fillStyle(outfit.secondary);
    g.fillRect(flip * sr(-12), sr(-27), sr(26), sr(12));
    g.fillRect(flip * sr(2),   sr(-18), sr(13), sr(5));
    g.fillStyle(0x1a1a2e);
    g.fillCircle(flip * sr(9), sr(-14), sr(3));
    g.fillStyle(0xffffff);
    g.fillCircle(flip * sr(10), sr(-15), 1.5);
    if (!isBoy) {
      g.fillStyle(outfit.secondary);
      g.fillRect(flip * sr(-18), sr(-12), sr(6), sr(18));
    }
  }

  _spawnNPCs() {
    const TS = SETTINGS.TILE_SIZE;
    this.npcs = [];
    const defs = [
      {
        col: 7, row: 5, name: 'PROF. OAK', outfit: 2, gender: 'boy',
        dialogue: [
          'Ah, welcome to Pallet Town!',
          'I am Professor Oak. I study Pokémon for a living.',
          'My Lab is just to the north — follow the path.',
          "When you're ready, come visit. I have a starter Pokémon for you!",
        ],
      },
      {
        col: 16, row: 5, name: 'GARY', outfit: 1, gender: 'boy',
        dialogue: [
          "Out of my way! I'm in a hurry.",
          "I'm heading to Gramps' Lab to grab my starter first.",
          'I am going to be the greatest Champion of all time.',
          'Smell ya later!',
        ],
      },
    ];
    for (const def of defs) {
      const gfx = this.add.graphics();
      gfx.setPosition(def.col * TS + TS / 2, def.row * TS + TS / 2);
      gfx.setDepth(15);
      this._drawNPC(gfx, def);
      const label = this.add.text(def.col * TS + TS / 2, def.row * TS - 6, def.name, {
        fontSize: '9px', color: '#ffffff', fontFamily: 'monospace',
        stroke: '#000000', strokeThickness: 2,
      }).setDepth(16).setOrigin(0.5, 1);
      this.npcs.push({ ...def, gfx, label });
    }
  }

  _drawNPC(g, def) {
    const outfit = SETTINGS.OUTFIT_COLORS[def.outfit];
    const isBoy  = def.gender === 'boy';
    const s  = 0.65;
    const sr = v => Math.round(v * s);
    g.clear();
    g.fillStyle(0x000000, 0.14);
    g.fillEllipse(0, sr(28), sr(28), sr(9));
    g.fillStyle(0x3d2b1f);
    g.fillRect(sr(-11), sr(22), sr(10), sr(7));
    g.fillRect(sr(1),   sr(22), sr(10), sr(7));
    g.fillStyle(0x2c3e50);
    g.fillRect(sr(-11), sr(8), sr(9), sr(15));
    g.fillRect(sr(2),   sr(8), sr(9), sr(15));
    g.fillStyle(outfit.primary);
    g.fillRect(sr(-11), sr(-3), sr(22), sr(13));
    g.fillRect(sr(-18), sr(-3), sr(8),  sr(13));
    g.fillRect(sr(10),  sr(-3), sr(8),  sr(13));
    g.fillStyle(0xf5c6a0);
    g.fillRect(sr(-18), sr(9), sr(8), sr(7));
    g.fillRect(sr(10),  sr(9), sr(8), sr(7));
    if (def.name === 'PROF. OAK') {
      g.fillStyle(0xffffff, 0.7);
      g.fillRect(sr(-4), sr(-3), sr(8), sr(13));
    }
    g.fillStyle(0xf5c6a0);
    g.fillCircle(0, sr(-14), sr(12));
    g.fillStyle(outfit.secondary);
    g.fillRect(sr(-12), sr(-25), sr(24), sr(11));
    if (!def.name.includes('OAK')) {
      g.fillRect(sr(1), sr(-15), sr(11), sr(5));
    }
    g.fillStyle(0x1a1a2e);
    g.fillCircle(sr(-4), sr(-13), sr(2.5));
    g.fillCircle(sr(4),  sr(-13), sr(2.5));
    if (!isBoy) {
      g.fillStyle(outfit.secondary);
      g.fillRect(sr(-17), sr(-11), sr(5), sr(15));
      g.fillRect(sr(12),  sr(-11), sr(5), sr(15));
    }
  }

  _createHUD() {
    const W = SETTINGS.SCREEN_W, H = SETTINGS.SCREEN_H;
    this.add.rectangle(W/2, 22, W, 44, 0x000000, 0.75).setScrollFactor(0).setDepth(100);
    this.add.text(14, 22, `♦ ${this.profile.name}`, {
      fontSize: '14px', color: '#FFD700', fontFamily: 'monospace',
    }).setScrollFactor(0).setDepth(101).setOrigin(0, 0.5);
    this.add.text(W/2, 22, 'PALLET TOWN', {
      fontSize: '14px', color: '#ffffff', fontFamily: 'monospace',
    }).setScrollFactor(0).setDepth(101).setOrigin(0.5, 0.5);
    this.add.text(W - 14, 22, '📋 Pokédex: 0/386', {
      fontSize: '12px', color: '#aaaacc', fontFamily: 'monospace',
    }).setScrollFactor(0).setDepth(101).setOrigin(1, 0.5);
    this.add.rectangle(W/2, H - 18, W, 36, 0x000000, 0.75).setScrollFactor(0).setDepth(100);
    this.add.text(W/2, H - 18, 'Arrow Keys / WASD — Move   •   SPACE / Enter — Talk', {
      fontSize: '11px', color: '#445566', fontFamily: 'monospace',
    }).setScrollFactor(0).setDepth(101).setOrigin(0.5, 0.5);
  }

  _getTile(col, row) {
    if (row < 0 || row >= this.ROWS || col < 0 || col >= this.COLS) return '2';
    return this.mapData[row][col];
  }

  _canMoveTo(col, row) {
    return !this.collidable.has(this._getTile(col, row));
  }

  update() {
    if (Phaser.Input.Keyboard.JustDown(this.spaceKey) ||
        Phaser.Input.Keyboard.JustDown(this.enterKey)) {
      if (this.dialogue.active) { this.dialogue.advance(); return; }
      this._tryInteract();
      return;
    }
    if (this.isMoving || this.dialogue.active) return;

    let dx = 0, dy = 0;
    if      (this.cursors.left.isDown  || this.wasd.left.isDown)  dx = -1;
    else if (this.cursors.right.isDown || this.wasd.right.isDown) dx =  1;
    else if (this.cursors.up.isDown    || this.wasd.up.isDown)    dy = -1;
    else if (this.cursors.down.isDown  || this.wasd.down.isDown)  dy =  1;

    if (dx !== 0 || dy !== 0) {
      const nx = this.playerTileX + dx;
      const ny = this.playerTileY + dy;
      if      (dx === -1) this.facing = 'left';
      else if (dx ===  1) this.facing = 'right';
      else if (dy === -1) this.facing = 'up';
      else                this.facing = 'down';
      if (!this._canMoveTo(nx, ny)) { this._drawPlayer(); return; }
      this._movePlayer(nx, ny);
    }
  }

  _tryInteract() {
    const delta = { up:[0,-1], down:[0,1], left:[-1,0], right:[1,0] };
    const [fdx, fdy] = delta[this.facing];
    const tx = this.playerTileX + fdx;
    const ty = this.playerTileY + fdy;
    for (const npc of this.npcs) {
      if (npc.col === tx && npc.row === ty) {
        this.dialogue.show(npc.name, npc.dialogue);
        return;
      }
    }
    if (this._getTile(tx, ty) === '6') {
      this.dialogue.show('SIGN', ['The door is locked for now.', '(Building interiors coming in Phase 3!)']);
    }
  }

  _movePlayer(newCol, newRow) {
    const TS = SETTINGS.TILE_SIZE;
    this.isMoving    = true;
    this.playerTileX = newCol;
    this.playerTileY = newRow;
    this.walkFrame   = 1;
    this._drawPlayer();
    this.tweens.add({
      targets: this.playerGfx,
      x: newCol * TS + TS / 2,
      y: newRow * TS + TS / 2,
      duration: SETTINGS.PLAYER_SPEED,
      ease: 'Linear',
      onComplete: () => {
        this.isMoving  = false;
        this.walkFrame = 0;
        this._drawPlayer();
        this._onLand(newCol, newRow);
      },
    });
  }

  _onLand(col, row) {
    const tile = this._getTile(col, row);
    if (tile === '4' && Math.random() < 0.30) this._showEncounterFlash();
    if (tile === '6') this.dialogue.show('SIGN', ['The door is locked for now.', '(Building interiors coming in Phase 3!)']);
  }

  _showEncounterFlash() {
    const W = SETTINGS.SCREEN_W, H = SETTINGS.SCREEN_H;
    const flash = this.add.rectangle(W/2, H/2, W, H, 0xffffff, 0).setScrollFactor(0).setDepth(200);
    this.tweens.add({
      targets: flash, alpha: 0.85, duration: 80, yoyo: true, repeat: 2,
      onComplete: () => {
        flash.destroy();
        const msg = this.add.text(W/2, H/2, '⚡ A wild Pokémon appeared!', {
          fontSize: '20px', color: '#ffffff', fontFamily: 'monospace', fontStyle: 'bold',
          stroke: '#000000', strokeThickness: 4,
        }).setScrollFactor(0).setDepth(201).setOrigin(0.5);
        this.tweens.add({
          targets: msg, y: msg.y - 60, alpha: 0, duration: 1800, ease: 'Power2',
          onComplete: () => msg.destroy(),
        });
      },
    });
  }
}
