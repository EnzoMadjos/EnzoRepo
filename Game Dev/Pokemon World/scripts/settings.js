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
    BATTLE_SPRITE: (id) => `/assets/sprites/battle/main-sprites/emerald/${id}.png`,
    ICON:          (id) => `/assets/sprites/icons/pokemon/icons/${id}.png`,
    CRY:           (id) => `/assets/sounds/cries/pokemon/cries/${id}.ogg`,
  },
};
