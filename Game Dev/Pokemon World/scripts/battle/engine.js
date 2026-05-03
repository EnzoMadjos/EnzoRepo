/**
 * engine.js — Phase 3 Step 1
 * Pure battle math — zero Phaser dependency.
 * Exposes window.BattleEngine.
 *
 * Gen 3 mechanics sourced from pret/pokeemerald (battle_util.c, pokemon.c).
 */

(function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Type chart — 18 types, Gen 3
  // Row = attacking type, Col = defending type
  // Values: 0 = immune, 0.5 = not very effective, 1 = normal, 2 = super effective
  // ---------------------------------------------------------------------------
  const TYPES = [
    "normal","fire","water","electric","grass","ice",
    "fighting","poison","ground","flying","psychic","bug",
    "rock","ghost","dragon","dark","steel","fairy",
  ];

  // Indexed [atk][def] → effectiveness multiplier
  // prettier-ignore
  const RAW_CHART = [
    //nor  fir  wat  ele  gra  ice  fig  poi  gro  fly  psy  bug  roc  gho  dra  dar  ste  fai
    [  1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1, 0.5,  0,   1,   1, 0.5,  1 ], // normal
    [  1, 0.5, 0.5,  1,   2,   2,   1,   1,   1,   1,   1,   2, 0.5,  1,  0.5,  1,   2,   1 ], // fire
    [  1,   2, 0.5,  1,  0.5,  1,   1,   1,   2,   1,   1,   1,  2,   1,  0.5,  1,   1,   1 ], // water
    [  1,   1,   2, 0.5, 0.5,  1,   1,   1,   0,   2,   1,   1,  1,   1,  0.5,  1,   1,   1 ], // electric
    [  1, 0.5,   2,  1,  0.5,  1,   1, 0.5,   2, 0.5,   1, 0.5, 0.5,  1,  0.5,  1, 0.5,   1 ], // grass
    [  1, 0.5, 0.5,  1,   2, 0.5,   1,   1,   2,   2,   1,   1,  1,   1,   2,   1, 0.5,   1 ], // ice
    [  2,   1,   1,   1,   1,   2,   1, 0.5,   1, 0.5, 0.5, 0.5, 2,   0,   1,   2,   2, 0.5 ], // fighting
    [  1,   1,   1,   1,   2,   1,   1, 0.5, 0.5,  1,   1,   1,  1, 0.5,   1,   1,  0,   2 ], // poison
    [  1,   2,   1,   2, 0.5,   1,   1,   2,   1,   0,   1, 0.5, 2,   1,   1,   1,   2,   1 ], // ground
    [  1,   1,   1, 0.5,  2,   1,   2,   1,   1,   1,   1,   2, 0.5,  1,   1,   1, 0.5,   1 ], // flying
    [  1,   1,   1,   1,   1,   1,   2,   2,   1,   1, 0.5,  1,   1,   1,   1,   0, 0.5,   1 ], // psychic
    [  1, 0.5,   1,   1,   2,   1, 0.5, 0.5,  1, 0.5,  2,   1,   1, 0.5,   1,   2, 0.5, 0.5 ], // bug
    [  1,   2,   1,   1,   1,   2, 0.5,  1, 0.5,   2,   1,   2,   1,   1,   1,   1, 0.5,   1 ], // rock
    [  0,   1,   1,   1,   1,   1,   1,   1,   1,   1,   2,   1,   1,   2,   1, 0.5,  1,   1 ], // ghost
    [  1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   1,   2,   1, 0.5,   0 ], // dragon
    [  1,   1,   1,   1,   1,   1, 0.5,  1,   1,   1,   2,   1,   1,   2,   1, 0.5,  1, 0.5 ], // dark
    [  1, 0.5,  0.5, 0.5,  1,   2,   1,   1,   1,   1,   1,   1,   2,   1,   1,   1, 0.5,   2 ], // steel
    [  1, 0.5,  1,   1,   1,   1,   2, 0.5,   1,   1,   1,   1,   1,   1,   2,   2, 0.5,   1 ], // fairy
  ];

  const TYPE_INDEX = {};
  TYPES.forEach((t, i) => { TYPE_INDEX[t] = i; });

  /**
   * Returns type effectiveness multiplier (0 | 0.5 | 1 | 2 | 4).
   * defTypes is an array of 1 or 2 type strings.
   */
  function getTypeEffectiveness(atkType, defTypes) {
    const atkIdx = TYPE_INDEX[atkType] ?? TYPE_INDEX.normal;
    let mult = 1;
    for (const dt of defTypes) {
      const defIdx = TYPE_INDEX[dt] ?? TYPE_INDEX.normal;
      mult *= RAW_CHART[atkIdx][defIdx];
    }
    return mult;
  }

  // ---------------------------------------------------------------------------
  // Physical / Special split — Gen 3 is TYPE-based (not move-based)
  // ---------------------------------------------------------------------------
  const PHYSICAL_TYPES = new Set([
    "normal","fighting","flying","poison","ground","rock","bug","ghost","steel",
  ]);

  function isPhysical(type) {
    return PHYSICAL_TYPES.has(type);
  }

  // ---------------------------------------------------------------------------
  // Stat formulas — Gen 3 (IV=15, EV=0, nature=1.0 for wild mons)
  // ---------------------------------------------------------------------------

  /**
   * Calculate HP stat.
   * formula: floor((2*base + iv + floor(ev/4)) * level/100) + level + 10
   */
  function calcHP(base, level, iv = 15, ev = 0) {
    return Math.floor((2 * base + iv + Math.floor(ev / 4)) * level / 100) + level + 10;
  }

  /**
   * Calculate non-HP stat.
   * formula: floor((floor((2*base + iv + floor(ev/4)) * level/100) + 5) * nature)
   */
  function calcStat(base, level, iv = 15, ev = 0, nature = 1.0) {
    return Math.floor((Math.floor((2 * base + iv + Math.floor(ev / 4)) * level / 100) + 5) * nature);
  }

  // ---------------------------------------------------------------------------
  // Damage formula — Gen 3 (battle_util.c)
  // ---------------------------------------------------------------------------

  /**
   * Calculate raw damage.
   * @param {number} level    Attacker level
   * @param {number} power    Move base power
   * @param {number} atk      Effective attack stat (atk or spa)
   * @param {number} def      Effective defense stat (def or spd)
   * @param {number} typeEff  Type effectiveness multiplier (0|0.5|1|2|4)
   * @param {boolean} stab    Same-type attack bonus
   * @param {boolean} crit    Critical hit
   * @param {number} [rand]   Random factor 85–100; pass undefined for average (92)
   * @returns {number} Final damage (minimum 1 if move hits and power > 0)
   */
  function calcDamage(level, power, atk, def, typeEff, stab, crit, rand) {
    if (!power || typeEff === 0) return 0;

    const randPct = rand !== undefined ? rand : 92;
    let dmg = Math.floor(
      (Math.floor(2 * level / 5 + 2) * power * atk / def) / 50
    ) + 2;

    if (stab) dmg = Math.floor(dmg * 15 / 10);
    if (typeEff !== 1) dmg = Math.floor(dmg * typeEff);
    if (crit) dmg = Math.floor(dmg * 2);
    dmg = Math.floor(dmg * randPct / 100);

    return Math.max(1, dmg);
  }

  // ---------------------------------------------------------------------------
  // Build a battle-ready Pokémon object from data
  // ---------------------------------------------------------------------------

  /**
   * Build a combat mon from a species entry.
   * @param {object} species  Entry from window.GAME_DATA.pokemonById
   * @param {number} level
   * @param {string[]} [moveNames]  Up to 4 move names; defaults to first 4 learnable
   * @returns {object} battleMon
   */
  function buildBattleMon(species, level, moveNames) {
    const bs = species.baseStats;

    // Pick moves: use provided list or take last 4 level-up moves learnable at this level
    const learnable = (species.moves || []).filter(m => m.level <= level);
    const defaultMoves = learnable.slice(-4).map(m => m.name);
    const chosenMoveNames = (moveNames || defaultMoves).slice(0, 4);

    const moves = chosenMoveNames.map(name => {
      const md = window.GAME_DATA?.moves[name] || {};
      return {
        name,
        type:        md.type        || "normal",
        power:       md.power       || 0,
        accuracy:    md.accuracy    || 100,
        pp:          md.pp          || 10,
        maxPP:       md.pp          || 10,
        damageClass: md.damageClass || "physical",
      };
    });

    const maxHp = calcHP(bs.hp, level);
    return {
      id:         species.id,
      name:       species.name,
      types:      species.types,
      level,
      moves,
      stats: {
        hp:  maxHp,
        atk: calcStat(bs.atk, level),
        def: calcStat(bs.def, level),
        spa: calcStat(bs.spa, level),
        spd: calcStat(bs.spd, level),
        spe: calcStat(bs.spe, level),
      },
      currentHp: maxHp,
      maxHp,
      status: null,       // null | "psn" | "brn" | "par" | "slp" | "frz"
      catchRate: species.catchRate,
      baseExpYield: species.baseExpYield,
    };
  }

  // ---------------------------------------------------------------------------
  // EXP gain
  // ---------------------------------------------------------------------------

  /** floor(baseExpYield * wildLevel / 7) */
  function calcExpGain(baseExpYield, wildLevel) {
    return Math.floor(baseExpYield * wildLevel / 7);
  }

  /** EXP needed to reach a level: n³ (medium-fast group, used as default) */
  function expForLevel(level) {
    return level * level * level;
  }

  // ---------------------------------------------------------------------------
  // Catch formula — Gen 3 (pokemon.c)
  // ---------------------------------------------------------------------------

  /**
   * Simulate a catch attempt. Returns true if caught.
   * @param {number} maxHp
   * @param {number} currentHp
   * @param {number} catchRate   0–255 from species data
   * @param {number} [ballMult]  1 = Poké Ball, 1.5 = Great Ball, 2 = Ultra Ball, 255 = Master Ball
   * @param {number} [statusMult] 1 normal, 1.5 sleep/freeze, 1.2 burn/para/poison
   * @returns {{ caught: boolean, shakes: number }}
   */
  function calcCatch(maxHp, currentHp, catchRate, ballMult = 1, statusMult = 1) {
    if (ballMult >= 255) return { caught: true, shakes: 4 };

    const a = Math.floor(
      (3 * maxHp - 2 * currentHp) * catchRate * ballMult * statusMult / (3 * maxHp)
    );

    if (a >= 255) return { caught: true, shakes: 4 };

    const b = Math.floor(1048560 / Math.sqrt(Math.sqrt(16711680 / (a + 1))));

    let shakes = 0;
    for (let i = 0; i < 4; i++) {
      if (Math.floor(Math.random() * 65536) < b) {
        shakes++;
      } else {
        break;
      }
    }

    return { caught: shakes === 4, shakes };
  }

  // ---------------------------------------------------------------------------
  // AI — picks best move (highest expected damage)
  // ---------------------------------------------------------------------------

  /**
   * Simple AI: pick the move that deals the most expected damage.
   * Ignores status moves (power = 0), falls back to first valid move.
   * @param {object} attacker  battleMon
   * @param {object} defender  battleMon
   * @returns {object|null} move object or null if no valid moves
   */
  function aiPickMove(attacker, defender) {
    let best = null;
    let bestDmg = -1;

    for (const move of attacker.moves) {
      if (move.pp <= 0 || !move.power) continue;

      const physical = isPhysical(move.type);
      const atkStat = physical ? attacker.stats.atk : attacker.stats.spa;
      const defStat = physical ? defender.stats.def : defender.stats.spd;
      const typeEff = getTypeEffectiveness(move.type, defender.types);
      const stab    = attacker.types.includes(move.type);

      const dmg = calcDamage(attacker.level, move.power, atkStat, defStat, typeEff, stab, false, 92);

      if (dmg > bestDmg) {
        bestDmg = dmg;
        best = move;
      }
    }

    // Fallback: first move with PP (even if status)
    if (!best) {
      best = attacker.moves.find(m => m.pp > 0) || attacker.moves[0];
    }

    return best;
  }

  // ---------------------------------------------------------------------------
  // Hit accuracy check
  // ---------------------------------------------------------------------------

  /**
   * Returns true if the move hits.
   * @param {number} accuracy  Move accuracy (0–100); 0 means always hits
   * @param {number} [atkAccStage] Accuracy stage modifier (default 0)
   * @param {number} [defEvaStage] Evasion stage modifier (default 0)
   */
  function checkAccuracy(accuracy, atkAccStage = 0, defEvaStage = 0) {
    if (!accuracy) return true; // always-hit moves
    const stageMultipliers = [1/3, 3/8, 1/2, 2/3, 3/4, 1, 4/3, 3/2, 2, 8/3, 3];
    const stage = Math.max(-5, Math.min(5, atkAccStage - defEvaStage));
    const mult = stageMultipliers[stage + 5];
    return Math.random() < (accuracy / 100) * mult;
  }

  // ---------------------------------------------------------------------------
  // Export
  // ---------------------------------------------------------------------------

  window.BattleEngine = {
    TYPES,
    PHYSICAL_TYPES,
    getTypeEffectiveness,
    isPhysical,
    calcHP,
    calcStat,
    calcDamage,
    buildBattleMon,
    calcExpGain,
    expForLevel,
    calcCatch,
    aiPickMove,
    checkAccuracy,
  };

})();
