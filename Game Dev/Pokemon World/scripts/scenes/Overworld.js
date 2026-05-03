class Overworld extends Phaser.Scene {
  constructor() { super({ key: 'Overworld' }); }

  init(data) {
    this.profile = data.profile
      || JSON.parse(localStorage.getItem('pw_profile') || 'null')
      || { gender: 'boy', outfit: 0, name: 'TRAINER' };
    this._returnPos = data.returnPos || null;
  }

  preload() {
    this.load.image('overworld_ts', '/assets/tilesets/overworld.png');
    // Load all 6 trainer variants (gender × outfit)
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

    // ── Phaser Tilemap (replaces fillRect-based _drawMap) ─────────────
    const mapNums = this.mapData.map(row => [...row].map(Number));
    const map = this.make.tilemap({ data: mapNums, tileWidth: TS, tileHeight: TS });
    const tileset = map.addTilesetImage('overworld_ts', 'overworld_ts', TS, TS, 0, 0);
    this.mapLayer = map.createLayer(0, tileset, 0, 0);
    this.mapLayer.setDepth(0);

    // Building labels on top of tilemap
    this._addMapLabels(TS);

    // ── Player sprite (replaces playerGfx Graphics) ──────────────────
    this.playerTileX = this._returnPos ? this._returnPos.col : 5;
    this.playerTileY = this._returnPos ? this._returnPos.row : 10;
    this.facing    = 'down';
    this.isMoving  = false;

    const outfitNames = ['red', 'blue', 'green'];
    this._trainerKey = `trainer_${this.profile.gender}_${outfitNames[this.profile.outfit] || 'red'}`;
    this._setupAnimations();

    this.playerSprite = this.add.sprite(
      this.playerTileX * TS + TS / 2,
      this.playerTileY * TS + TS / 2,
      this._trainerKey, 0
    );
    this.playerSprite.setDepth(20);
    this.playerSprite.setScale(0.75);  // 64px → ~48px
    this.playerSprite.play(`${this._trainerKey}_idle_down`);

    this._spawnNPCs();

    this.cameras.main.setBounds(0, 0, this.mapWidth, this.mapHeight);
    this.cameras.main.startFollow(this.playerSprite, true, 0.12, 0.12);
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

  _setupAnimations() {
    const k = this._trainerKey;
    if (this.anims.exists(`${k}_walk_down`)) return;  // already created

    // Walk animations (3 frames per direction)
    this.anims.create({ key: `${k}_walk_down`, frames: this.anims.generateFrameNumbers(k, { start: 0, end: 2 }), frameRate: 8, repeat: -1 });
    this.anims.create({ key: `${k}_walk_up`,   frames: this.anims.generateFrameNumbers(k, { start: 3, end: 5 }), frameRate: 8, repeat: -1 });
    this.anims.create({ key: `${k}_walk_side`, frames: this.anims.generateFrameNumbers(k, { start: 6, end: 8 }), frameRate: 8, repeat: -1 });

    // Idle animations (single frame)
    this.anims.create({ key: `${k}_idle_down`, frames: [{ key: k, frame: 0 }], frameRate: 1 });
    this.anims.create({ key: `${k}_idle_up`,   frames: [{ key: k, frame: 3 }], frameRate: 1 });
    this.anims.create({ key: `${k}_idle_side`, frames: [{ key: k, frame: 6 }], frameRate: 1 });
  }

  _playAnim(isWalking) {
    const k = this._trainerKey;
    const type = isWalking ? 'walk' : 'idle';
    const dir = (this.facing === 'left' || this.facing === 'right') ? 'side' : this.facing;
    this.playerSprite.setFlipX(this.facing === 'right');
    this.playerSprite.play(`${k}_${type}_${dir}`, true);
  }

  _addMapLabels(TS) {
    this.add.text(13 * TS + TS, 4, "OAK'S LAB", {
      fontSize: '9px', color: '#ffffff', fontFamily: 'monospace', fontStyle: 'bold',
      stroke: '#000000', strokeThickness: 2,
    }).setDepth(50).setOrigin(0.5, 0);
    this.add.text(19 * TS + TS, 4, 'POKÉMON CENTER', {
      fontSize: '9px', color: '#ffaaaa', fontFamily: 'monospace', fontStyle: 'bold',
      stroke: '#000000', strokeThickness: 2,
    }).setDepth(50).setOrigin(0.5, 0);
  }

  _drawMap() {
    // Superseded by Phaser tilemap in create(). Kept for reference only.
  }

  _drawPlayer() {
    // Superseded by _playAnim(). Kept for backward compat.
    this._playAnim(false);
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
        if (!this._canMoveTo(nx, ny)) { this._playAnim(false); return; }
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
    this._playAnim(true);
    this.tweens.add({
      targets: this.playerSprite,
      x: newCol * TS + TS / 2,
      y: newRow * TS + TS / 2,
      duration: SETTINGS.PLAYER_SPEED,
      ease: 'Linear',
      onComplete: () => {
        this.isMoving = false;
        this._playAnim(false);
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
        this._startWildBattle();
      },
    });
  }

  _startWildBattle() {
    // Pick a random wild Pokémon from the spawn table
    const table = SETTINGS.SPAWN_TABLES['tall_grass'] || [16];
    const wildId = table[Math.floor(Math.random() * table.length)];
    const species = window.GAME_DATA?.pokemonById?.get(wildId);
    if (!species) return; // GAME_DATA not loaded yet (shouldn't happen)

    const wildLevel = SETTINGS.BATTLE.WILD_LEVEL_MIN
      + Math.floor(Math.random() * (SETTINGS.BATTLE.WILD_LEVEL_MAX - SETTINGS.BATTLE.WILD_LEVEL_MIN + 1));
    const enemyMon = BattleEngine.buildBattleMon(species, wildLevel);

    // Get player's lead Pokémon from localStorage
    let party;
    try { party = JSON.parse(localStorage.getItem('pw_party') || '[]'); } catch { party = []; }
    const playerMon = party[0] || null;
    if (!playerMon) return; // No party — skip battle

    this.cameras.main.fadeOut(200);
    this.cameras.main.once('camerafadeoutcomplete', () => {
      this.scene.start('Battle', {
        enemyPokemon:  enemyMon,
        playerPokemon: playerMon,
        zone:          'tall_grass',
        returnPos:     { col: this.playerTileX, row: this.playerTileY },
        profile:       this.profile,
      });
    });
  }
}
