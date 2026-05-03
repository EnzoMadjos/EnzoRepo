const SETTINGS = {
  SCREEN_W: 960,
  SCREEN_H: 640,
  TILE_SIZE: 48,
  FPS: 60,
  PLAYER_SPEED: 180, // ms per tile move

  TILE: { GRASS: 0, PATH: 1, TREE: 2, WATER: 3, TALL_GRASS: 4 },

  TILE_COLORS: {
    0: 0x3a7d44,  // grass
    1: 0xc8a96e,  // path
    2: 0x1e5128,  // tree
    3: 0x1565c0,  // water
    4: 0x4caf50,  // tall grass
    5: 0xd4a96a,  // building wall
    6: 0xd4a96a,  // building door (door graphic drawn on top)
  },

  OUTFIT_COLORS: [
    { name: 'Red',   primary: 0xe74c3c, secondary: 0x2c3e50 },
    { name: 'Blue',  primary: 0x2980b9, secondary: 0xecf0f1 },
    { name: 'Green', primary: 0x27ae60, secondary: 0xf39c12 },
  ],

  PATHS: {
    BATTLE_SPRITE:      (id) => `/assets/sprites/battle/main-sprites/emerald/${id}.png`,
    BATTLE_SPRITE_BACK: (id) => `/assets/sprites/battle/main-sprites/ruby-sapphire/back/${id}.png`,
    ICON:               (id) => `/assets/sprites/icons/icons/${id}.png`,
    CRY:                (id) => `/assets/sounds/cries/pokemon/cries/${id}.ogg`,
    // Trainer back sprite in battle (brendan = male, may = female)
    TRAINER_BACK: (gender) => `/assets/sprites/trainer/back_${gender}.png`,
  },

  BATTLE: {
    ENCOUNTER_RATE: 0.30,     // 30% chance per tall-grass step
    WILD_LEVEL_MIN: 3,
    WILD_LEVEL_MAX: 7,
    STARTER_POKEMON_ID: 1,    // Bulbasaur — seeded in localStorage by BootScene
    STARTER_LEVEL: 10,
  },

  // Spawn tables — map zone key → array of Pokémon IDs
  // Zone 'tall_grass' = default overworld tall grass
  SPAWN_TABLES: {
    tall_grass: [16, 19, 21, 43, 69, 74, 111, 23, 27, 29, 32],
    // 16=Pidgey, 19=Rattata, 21=Spearow, 43=Oddish, 69=Bellsprout,
    // 74=Geodude, 111=Rhyhorn, 23=Ekans, 27=Sandshrew, 29=Nidoran♀, 32=Nidoran♂
    water:      [54, 55, 60, 61, 118, 119, 129],
    cave:       [41, 42, 66, 74, 95],
  },
};
