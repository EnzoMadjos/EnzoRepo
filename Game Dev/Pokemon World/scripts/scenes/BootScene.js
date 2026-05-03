/**
 * BootScene.js — Phase 3 Step 3
 * First scene to run. Loads pokemon.json + moves.json, seeds starter
 * party into localStorage if missing, then starts CharacterCreate.
 */

class BootScene extends Phaser.Scene {
  constructor() {
    super({ key: "Boot" });
  }

  preload() {
    const W = SETTINGS.SCREEN_W;
    const H = SETTINGS.SCREEN_H;

    // --- Loading bar background ---
    const barBg = this.add.graphics();
    barBg.fillStyle(0x222222, 1);
    barBg.fillRect(W / 2 - 200, H / 2 - 12, 400, 24);

    const barFill = this.add.graphics();

    const label = this.add
      .text(W / 2, H / 2 - 36, "Loading game data…", {
        fontFamily: "monospace",
        fontSize: "16px",
        color: "#ffffff",
      })
      .setOrigin(0.5);

    this.load.on("progress", (value) => {
      barFill.clear();
      barFill.fillStyle(0x4caf50, 1);
      barFill.fillRect(W / 2 - 200, H / 2 - 12, 400 * value, 24);
    });

    this.load.on("loaderror", (file) => {
      label.setText(
        `❌ Failed to load: ${file.key}\nRun  python generate_data.py  first.`
      );
      label.setColor("#ff4444");
    });

    // Load JSON data — served as static files by FastAPI /data mount
    this.load.json("pokemonData", "/data/pokemon.json");
    this.load.json("movesData",   "/data/moves.json");
  }

  create() {
    const pokemonList = this.cache.json.get("pokemonData");
    const movesDict   = this.cache.json.get("movesData");

    if (!pokemonList || !movesDict) {
      // loaderror handler already showed the message — stop here
      return;
    }

    // Build a fast lookup map: id → species entry
    const pokemonById = new Map();
    for (const p of pokemonList) {
      pokemonById.set(p.id, p);
    }

    // Expose globally for BattleEngine and BattleScene
    window.GAME_DATA = {
      pokemon:     pokemonList,
      moves:       movesDict,
      pokemonById,
    };

    // --- Seed starter party + bag into localStorage (version-gated) ---
    const PARTY_KEY   = "pw_party";
    const BAG_KEY     = "pw_bag";
    const SAVE_VER    = "v1.2";  // bump this to force reset on all clients
    const savedVer    = localStorage.getItem("pw_save_ver");

    if (savedVer !== SAVE_VER) {
      // Wipe old data so new starter + bag get seeded clean
      localStorage.removeItem(PARTY_KEY);
      localStorage.removeItem(BAG_KEY);
      localStorage.setItem("pw_save_ver", SAVE_VER);
    }

    // Starter party is seeded by StarterSelect scene — no auto-seed here.

    if (!localStorage.getItem(BAG_KEY)) {
      const startBag = [
        { id: 'potion',       name: 'Potion',       count: 3, hp: 20  },
        { id: 'super_potion', name: 'Super Potion',  count: 1, hp: 50  },
        { id: 'pokeball',     name: 'Poké Ball',     count: 5, ball: 1 },
        { id: 'great_ball',   name: 'Great Ball',    count: 1, ball: 1.5 },
      ];
      localStorage.setItem(BAG_KEY, JSON.stringify(startBag));
    }

    this.scene.start("CharacterCreate");
  }
}
