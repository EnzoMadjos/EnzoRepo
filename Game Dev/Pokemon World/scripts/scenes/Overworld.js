class Overworld extends Phaser.Scene {
  constructor() {
    super({ key: 'Overworld' });
  }

  init(data) {
    this.profile = data.profile
      || JSON.parse(localStorage.getItem('pw_profile') || null)
      || { gender: 'boy', outfit: 0, name: 'TRAINER' };
  }

  create() {
    const TS = SETTINGS.TILE_SIZE;

    // Map: 30 cols × 20 rows  (0=grass 1=path 2=tree 3=water 4=tall_grass)
    this.mapData = [
      '222222222222222222222222222222',
      '200000004440000000000000000002',
      '200044004440000022200000000002',
      '200011100011100020200044000002',
      '200011100011100020200044000002',
      '200011122211100020000000000002',
      '200011100011100000000000000002',
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

    this.collidable = new Set(['2', '3']);

    // Draw tiles
    this.tileGfx = this.add.graphics();
    this._drawMap();

    // Player (tile 5, 10)
    this.playerTileX = 5;
    this.playerTileY = 10;
    this.playerGfx = this.add.graphics();
    this.playerGfx.setPosition(this.playerTileX * TS + TS / 2, this.playerTileY * TS + TS / 2);
    this.playerGfx.setDepth(20);
    this._drawPlayer();

    // Camera
    this.cameras.main.setBounds(0, 0, this.mapWidth, this.mapHeight);
    this.cameras.main.startFollow(this.playerGfx, true, 0.12, 0.12);
    this.cameras.main.fadeIn(400);

    // Input
    this.cursors = this.input.keyboard.createCursorKeys();
    this.wasd = this.input.keyboard.addKeys({
      up:    Phaser.Input.Keyboard.KeyCodes.W,
      down:  Phaser.Input.Keyboard.KeyCodes.S,
      left:  Phaser.Input.Keyboard.KeyCodes.A,
      right: Phaser.Input.Keyboard.KeyCodes.D,
    });

    this.isMoving = false;

    // HUD
    this._createHUD();
  }

  // ─── Map drawing ──────────────────────────────────────────────────
  _drawMap() {
    const TS = SETTINGS.TILE_SIZE;
    const g = this.tileGfx;
    g.clear();

    for (let row = 0; row < this.ROWS; row++) {
      for (let col = 0; col < this.COLS; col++) {
        const tile = this.mapData[row][col];
        const base = SETTINGS.TILE_COLORS[parseInt(tile)];

        // Base fill
        g.fillStyle(base);
        g.fillRect(col * TS, row * TS, TS, TS);

        // Tile details
        if (tile === '2') {
          // Tree canopy
          g.fillStyle(0x145214);
          g.fillCircle(col * TS + TS / 2, row * TS + TS / 2 - 4, 17);
          // Trunk
          g.fillStyle(0x6b3a2a);
          g.fillRect(col * TS + TS / 2 - 4, row * TS + TS / 2 + 8, 8, 14);
        } else if (tile === '4') {
          // Tall grass blades (deterministic placement)
          g.fillStyle(0x2e7d32);
          const seed = (col * 7 + row * 3) % 4;
          for (let b = 0; b < 4; b++) {
            const bx = col * TS + 6 + ((b + seed) % 4) * 11;
            g.fillRect(bx, row * TS + 8, 3, 22);
            g.fillRect(bx + 4, row * TS + 16, 3, 16);
          }
        } else if (tile === '3') {
          // Water shimmer strips
          g.fillStyle(0x5ba3e0, 0.45);
          g.fillRect(col * TS + 4, row * TS + TS / 3, TS - 8, 4);
          g.fillRect(col * TS + 10, row * TS + TS / 2 + 4, TS - 20, 4);
        } else if (tile === '1') {
          // Path pebble hint
          const px = col * TS + 4 + ((col * 13 + row * 5) % 30);
          const py = row * TS + 4 + ((col * 9 + row * 11) % 30);
          g.fillStyle(0xb8945e, 0.5);
          g.fillCircle(px, py, 2);
        }

        // Subtle grid
        g.lineStyle(1, 0x000000, 0.06);
        g.strokeRect(col * TS, row * TS, TS, TS);
      }
    }
  }

  // ─── Player drawing ───────────────────────────────────────────────
  _drawPlayer() {
    const g = this.playerGfx;
    g.clear();
    const outfit = SETTINGS.OUTFIT_COLORS[this.profile.outfit];
    const isBoy = this.profile.gender === 'boy';
    const s = 0.75; // scale factor (48px tile → ~36px tall sprite)

    const sr = (v) => Math.round(v * s); // scaled round

    // Shadow
    g.fillStyle(0x000000, 0.2);
    g.fillEllipse(0, sr(28), sr(30), sr(10));

    // Shoes
    g.fillStyle(0x3d2b1f);
    g.fillRect(sr(-14), sr(22), sr(12), sr(8));
    g.fillRect(sr(2),   sr(22), sr(12), sr(8));

    // Legs
    g.fillStyle(0x2c3e50);
    g.fillRect(sr(-14), sr(8), sr(10), sr(16));
    g.fillRect(sr(4),   sr(8), sr(10), sr(16));

    // Body
    g.fillStyle(outfit.primary);
    g.fillRect(sr(-14), sr(-4), sr(28), sr(14));

    // Arms
    g.fillStyle(outfit.primary);
    g.fillRect(sr(-22), sr(-4), sr(10), sr(16));
    g.fillRect(sr(12),  sr(-4), sr(10), sr(16));

    // Hands
    g.fillStyle(0xf5c6a0);
    g.fillRect(sr(-22), sr(10), sr(10), sr(8));
    g.fillRect(sr(12),  sr(10), sr(10), sr(8));

    // Head
    g.fillStyle(0xf5c6a0);
    g.fillCircle(0, sr(-16), sr(13));

    // Hat
    g.fillStyle(outfit.secondary);
    g.fillRect(sr(-14), sr(-28), sr(28), sr(12));
    g.fillRect(sr(2),   sr(-18), sr(14), sr(6));

    // Eyes
    g.fillStyle(0x1a1a2e);
    g.fillCircle(sr(-5), sr(-15), sr(3));
    g.fillCircle(sr(5),  sr(-15), sr(3));

    // Eye shine
    g.fillStyle(0xffffff);
    g.fillCircle(sr(-4), sr(-16), 1.5);
    g.fillCircle(sr(6),  sr(-16), 1.5);

    // Girl hair
    if (!isBoy) {
      g.fillStyle(outfit.secondary);
      g.fillRect(sr(-20), sr(-14), sr(6), sr(18));
      g.fillRect(sr(14),  sr(-14), sr(6), sr(18));
    }
  }

  // ─── HUD ──────────────────────────────────────────────────────────
  _createHUD() {
    const W = SETTINGS.SCREEN_W;
    const H = SETTINGS.SCREEN_H;

    // Top bar
    this.add.rectangle(W / 2, 22, W, 44, 0x000000, 0.75).setScrollFactor(0).setDepth(100);
    this.add.text(14, 22, `♦ ${this.profile.name}`, {
      fontSize: '14px', color: '#FFD700', fontFamily: 'monospace',
    }).setScrollFactor(0).setDepth(101).setOrigin(0, 0.5);
    this.add.text(W / 2, 22, 'PALLET TOWN', {
      fontSize: '14px', color: '#ffffff', fontFamily: 'monospace',
    }).setScrollFactor(0).setDepth(101).setOrigin(0.5, 0.5);
    this.add.text(W - 14, 22, '📋 Pokédex: 0/386', {
      fontSize: '12px', color: '#aaaacc', fontFamily: 'monospace',
    }).setScrollFactor(0).setDepth(101).setOrigin(1, 0.5);

    // Bottom bar
    this.add.rectangle(W / 2, H - 18, W, 36, 0x000000, 0.75).setScrollFactor(0).setDepth(100);
    this.add.text(W / 2, H - 18, 'Arrow Keys / WASD  —  Move  •  Walk into tall grass to encounter Pokémon', {
      fontSize: '11px', color: '#445566', fontFamily: 'monospace',
    }).setScrollFactor(0).setDepth(101).setOrigin(0.5, 0.5);
  }

  // ─── Tile helpers ─────────────────────────────────────────────────
  _getTile(col, row) {
    if (row < 0 || row >= this.ROWS || col < 0 || col >= this.COLS) return '2';
    return this.mapData[row][col];
  }

  _canMoveTo(col, row) {
    return !this.collidable.has(this._getTile(col, row));
  }

  // ─── Update loop ──────────────────────────────────────────────────
  update() {
    if (this.isMoving) return;

    let dx = 0, dy = 0;
    if      (this.cursors.left.isDown  || this.wasd.left.isDown)  dx = -1;
    else if (this.cursors.right.isDown || this.wasd.right.isDown) dx =  1;
    else if (this.cursors.up.isDown    || this.wasd.up.isDown)    dy = -1;
    else if (this.cursors.down.isDown  || this.wasd.down.isDown)  dy =  1;

    if (dx !== 0 || dy !== 0) {
      const nx = this.playerTileX + dx;
      const ny = this.playerTileY + dy;
      if (this._canMoveTo(nx, ny)) this._movePlayer(nx, ny);
    }
  }

  // ─── Movement ─────────────────────────────────────────────────────
  _movePlayer(newCol, newRow) {
    const TS = SETTINGS.TILE_SIZE;
    this.isMoving = true;
    this.playerTileX = newCol;
    this.playerTileY = newRow;

    this.tweens.add({
      targets:  this.playerGfx,
      x:        newCol * TS + TS / 2,
      y:        newRow * TS + TS / 2,
      duration: SETTINGS.PLAYER_SPEED,
      ease:     'Linear',
      onComplete: () => {
        this.isMoving = false;
        this._onLand(newCol, newRow);
      },
    });
  }

  _onLand(col, row) {
    const tile = this._getTile(col, row);
    if (tile === '4') {
      // 30% encounter chance (Phase 3 will start actual battle here)
      if (Math.random() < 0.30) {
        this._showEncounterFlash();
      }
    }
  }

  _showEncounterFlash() {
    const W = SETTINGS.SCREEN_W;
    const H = SETTINGS.SCREEN_H;

    // White flash
    const flash = this.add.rectangle(W / 2, H / 2, W, H, 0xffffff, 0)
      .setScrollFactor(0).setDepth(200);

    this.tweens.add({
      targets: flash, alpha: 0.8, duration: 80, yoyo: true, repeat: 2,
      onComplete: () => {
        flash.destroy();
        // Show floating text
        const msg = this.add.text(W / 2, H / 2, '⚡ A wild Pokémon appeared!', {
          fontSize: '20px', color: '#ffffff', fontFamily: 'monospace', fontStyle: 'bold',
          stroke: '#000000', strokeThickness: 4,
        }).setScrollFactor(0).setDepth(201).setOrigin(0.5);

        this.tweens.add({
          targets: msg, y: msg.y - 60, alpha: 0,
          duration: 1800, ease: 'Power2',
          onComplete: () => msg.destroy(),
        });
      },
    });
  }
}
