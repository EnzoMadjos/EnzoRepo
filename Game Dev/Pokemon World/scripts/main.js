const config = {
  type: Phaser.AUTO,
  width: SETTINGS.SCREEN_W,
  height: SETTINGS.SCREEN_H,
  parent: 'game-container',
  backgroundColor: '#000000',
  pixelArt: true,
  scene: [BootScene, CharacterCreate, StarterSelect, Overworld, BattleScene],
};

const game = new Phaser.Game(config);
