#!/usr/bin/env python3
"""
build_emerald_assets.py
Generates GBA-Emerald-palette tilesets and original Brendan/May-inspired
trainer sprite sheets for Pokemon World.

Tiles produced (48×48 each, 9 tiles wide):
  0 = short grass    1 = dirt path    2 = stone border   3 = tree
  4 = tall grass     5 = building wall  6 = door         7 = water
  8 = building roof

Trainer sprites: 192×192 (3×3 grid of 64×64 frames)
  Row 0 frames 0-2: walk_down (idle / left-step / right-step)
  Row 1 frames 3-5: walk_up
  Row 2 frames 6-8: walk_side (face left; engine flips for right)
"""

from PIL import Image, ImageDraw
import os, random, math

BASE   = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, 'assets')
TILE   = 48   # pixels per tile
FRAME  = 64   # pixels per trainer frame

# ─── GBA Emerald-palette ─────────────────────────────────────────────────────
P = {
    # terrain
    'grass':        (104, 192,  56),
    'grass_dk':     ( 48, 120,  12),
    'grass_lt':     (144, 220,  80),
    'path':         (208, 168,  80),
    'path_dk':      (160, 120,  48),
    'path_lt':      (240, 200, 112),
    'rock':         (120, 120, 120),
    'rock_dk':      ( 72,  72,  72),
    'rock_lt':      (172, 172, 172),
    # tree
    'tree_out':     ( 32,  72,  16),
    'tree_mid':     ( 64, 112,  32),
    'tree_hi':      (100, 168,  52),
    'tree_trunk':   (112,  72,  32),
    'tree_shadow':  ( 20,  48,   8),
    # tall grass
    'tg_base':      ( 64, 144,  28),
    'tg_blade':     (104, 200,  48),
    'tg_tip':       (152, 240,  72),
    # water
    'water':        ( 56, 144, 248),
    'water_lt':     (112, 196, 255),
    'water_dk':     ( 32, 100, 200),
    # building
    'bld':          (240, 224, 160),
    'bld_dk':       (176, 156, 100),
    'bld_rf':       (192,  88,  64),
    'bld_rf_dk':    (140,  52,  32),
    'win':          ( 88, 172, 240),
    # door
    'door':         (136,  72,  28),
    'door_dk':      ( 88,  40,  12),
    'door_frm':     ( 56,  28,   8),
    # trainer skin tones
    'skin':         (240, 196, 152),
    'skin_dk':      (200, 148, 100),
    'hair_br':      ( 80,  44,  16),
    'bandana_w':    (240, 240, 240),
    'bandana_r':    (216,  48,  48),
    'shoe_g':       (120, 120, 120),
    'shoe_w':       (230, 230, 230),
}

def c(name, a=255):
    r, g, b = P[name]
    return (r, g, b, a)

def rgb(r, g, b, a=255):
    return (r, g, b, a)

# ─── Tile generators ─────────────────────────────────────────────────────────

def tile_grass():
    img = Image.new('RGBA', (TILE, TILE), c('grass'))
    d   = ImageDraw.Draw(img)
    rng = random.Random(1001)
    for _ in range(24):
        x = rng.randint(2, TILE - 4)
        y = rng.randint(3, TILE - 5)
        # small V-tuft
        d.line([(x,   y + 3), (x,   y)], fill=c('grass_dk'), width=1)
        d.line([(x+2, y + 3), (x+2, y)], fill=c('grass_dk'), width=1)
        d.point((x - 1, y),     fill=c('grass_lt'))
        d.point((x + 3, y),     fill=c('grass_lt'))
    # light noise overlay
    for _ in range(10):
        x = rng.randint(0, TILE - 3)
        y = rng.randint(0, TILE - 3)
        d.ellipse([x, y, x + 3, y + 2], fill=(*P['grass_lt'], 90))
    return img


def tile_path():
    img = Image.new('RGBA', (TILE, TILE), c('path'))
    d   = ImageDraw.Draw(img)
    rng = random.Random(2002)
    for _ in range(20):
        x = rng.randint(2, TILE - 5)
        y = rng.randint(2, TILE - 5)
        r = rng.randint(2, 4)
        col = c('path_dk') if rng.random() < 0.55 else c('path_lt')
        d.ellipse([x, y, x + r, y + r], fill=(*col[:3], 160))
    # faint tracks
    for x in range(4, TILE - 4, 12):
        d.line([(x, 0), (x, TILE)], fill=(*P['path_dk'], 30), width=1)
    return img


def tile_border():
    img = Image.new('RGBA', (TILE, TILE), c('rock'))
    d   = ImageDraw.Draw(img)
    # horizontal stone rows
    for y in range(0, TILE, 16):
        d.line([(0, y), (TILE, y)], fill=c('rock_dk'), width=2)
    # offset joints
    for row in range(3):
        y1, y2 = row * 16, row * 16 + 16
        offset = [0, 10, 5][row % 3]
        for x in range(offset, TILE, 24):
            d.line([(x, y1 + 2), (x, y2 - 2)], fill=c('rock_dk'), width=1)
    d.line([(0, 0), (TILE, 0)], fill=c('rock_lt'), width=1)
    d.line([(0, 0), (0, TILE)], fill=c('rock_lt'), width=1)
    return img


def tile_tree():
    img = Image.new('RGBA', (TILE, TILE), c('grass'))
    d   = ImageDraw.Draw(img)
    cx, cy = TILE // 2, TILE // 2 - 1
    R = 19
    # cast shadow
    d.ellipse([cx - R + 3, cy + R - 2, cx + R - 3, cy + R + 9],
              fill=(*P['tree_shadow'], 90))
    # canopy layers
    d.ellipse([cx - R,     cy - R + 2, cx + R,     cy + R - 2], fill=c('tree_out'))
    d.ellipse([cx - R + 4, cy - R + 6, cx + R - 4, cy + R - 5], fill=c('tree_mid'))
    # highlight blobs
    d.ellipse([cx - R + 5, cy - R + 5,  cx - R + 17, cy - R + 14], fill=c('tree_hi'))
    d.ellipse([cx - 3,     cy - R + 8,  cx + 8,      cy - R + 18], fill=c('tree_hi'))
    # trunk
    d.rectangle([cx - 4, cy + R - 6, cx + 4, cy + R + 5], fill=c('tree_trunk'))
    return img


def tile_tallgrass():
    img = Image.new('RGBA', (TILE, TILE), c('tg_base'))
    d   = ImageDraw.Draw(img)
    rng = random.Random(3003)
    for bx in range(4, TILE - 1, 5):
        h   = rng.randint(14, 22)
        ox  = rng.randint(-1, 1)
        bx2 = bx + ox
        # blade body
        d.line([(bx2 + 1, TILE - 1), (bx2 + 1, TILE - h)],
               fill=c('tg_blade'), width=2)
        # tip curl
        tip = bx2 + rng.randint(-4, 4)
        d.line([(bx2 + 1, TILE - h), (tip, TILE - h - 5)],
               fill=c('tg_tip'), width=1)
    # base shadow strip
    d.rectangle([0, TILE - 7, TILE, TILE], fill=(*P['tg_base'], 200))
    return img


def tile_water():
    img = Image.new('RGBA', (TILE, TILE), c('water'))
    d   = ImageDraw.Draw(img)
    rng = random.Random(4004)
    for y in range(5, TILE - 5, 8):
        for x in range(0, TILE - 10, 12):
            xo = rng.randint(0, 4)
            d.arc([x + xo, y, x + xo + 10, y + 5], 200, 340,
                  fill=c('water_lt'), width=1)
    # depth gradient at bottom
    for i in range(7):
        alpha = int(50 * i / 6)
        d.line([(0, TILE - 7 + i), (TILE, TILE - 7 + i)],
               fill=(*P['water_dk'], alpha))
    return img


def tile_buildwall():
    img = Image.new('RGBA', (TILE, TILE), c('bld'))
    d   = ImageDraw.Draw(img)
    # top overhang
    d.rectangle([0, 0, TILE, 7], fill=c('bld_rf'))
    d.line([(0, 7), (TILE, 7)], fill=c('bld_rf_dk'), width=2)
    # wall texture
    for y in range(11, TILE, 10):
        d.line([(0, y), (TILE, y)], fill=(*P['bld_dk'], 55), width=1)
    # window
    d.rectangle([8,  13, 24, 30], fill=c('win'))
    d.rectangle([8,  13, 24, 30], outline=c('bld_dk'), width=1)
    d.line([(8, 21),  (24, 21)], fill=c('bld_dk'), width=1)
    d.line([(16, 13), (16, 30)], fill=c('bld_dk'), width=1)
    # shadow under roof
    d.line([(0, 9), (TILE, 9)], fill=(*P['bld_dk'], 70), width=1)
    return img


def tile_door():
    img = Image.new('RGBA', (TILE, TILE), c('bld'))
    d   = ImageDraw.Draw(img)
    for y in range(10, TILE, 10):
        d.line([(0, y), (TILE, y)], fill=(*P['bld_dk'], 45), width=1)
    dx1, dx2 = TILE // 2 - 9, TILE // 2 + 9
    dy1 = 14
    # frame
    d.rectangle([dx1 - 2, dy1 - 2, dx2 + 2, TILE], fill=c('door_frm'))
    # door body
    d.rectangle([dx1, dy1, dx2, TILE], fill=c('door'))
    # panels
    d.rectangle([dx1 + 2, dy1 + 3,  dx1 + 8, dy1 + 12], fill=c('door_dk'))
    d.rectangle([dx1 + 2, dy1 + 15, dx1 + 8, dy1 + 24], fill=c('door_dk'))
    # handle
    d.ellipse([dx2 - 7, TILE // 2, dx2 - 3, TILE // 2 + 4],
              fill=rgb(210, 170, 0))
    # step
    d.rectangle([TILE // 2 - 13, TILE - 7, TILE // 2 + 13, TILE],
                fill=c('path'))
    return img


def tile_roof():
    img = Image.new('RGBA', (TILE, TILE), c('bld_rf'))
    d   = ImageDraw.Draw(img)
    for row in range(4):
        y1     = row * 12
        offset = 0 if row % 2 == 0 else 13
        for x in range(offset, TILE, 26):
            d.rectangle([x, y1, x + 23, y1 + 10], fill=c('bld_rf_dk'))
    # bottom lip
    d.line([(0, TILE - 1), (TILE, TILE - 1)], fill=c('bld_dk'), width=2)
    return img


# ─── Build + save tileset ────────────────────────────────────────────────────

def build_tileset():
    tiles = [
        tile_grass(),       # 0
        tile_path(),        # 1
        tile_border(),      # 2
        tile_tree(),        # 3
        tile_tallgrass(),   # 4
        tile_buildwall(),   # 5
        tile_door(),        # 6
        tile_water(),       # 7
        tile_roof(),        # 8
    ]
    sheet = Image.new('RGBA', (TILE * len(tiles), TILE))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * TILE, 0))
    out = os.path.join(ASSETS, 'tilesets', 'overworld.png')
    sheet.save(out)
    print(f'  tileset → {out}  ({sheet.width}×{sheet.height})')


# ─── Trainer sprites ─────────────────────────────────────────────────────────
# Original GBA-inspired characters.  NOT copied from any Nintendo asset.
#
# Boy  = Brendan-inspired: bandana, dark hair, coloured shirt, dark shorts
# Girl = May-inspired:     headband, brown hair, coloured top, shorts

def _draw_boy(canvas, ox, oy, direction, leg_phase, shirt_col, bandana_col):
    """Draw a single boy frame into `canvas` at (ox,oy)."""
    d  = ImageDraw.Draw(canvas)
    f  = FRAME
    cx = ox + f // 2
    cy = oy + f // 2 + 2   # slightly below center

    skin  = P['skin']
    skin_dk = P['skin_dk']
    hair  = P['hair_br']
    dark  = (16, 16, 16, 255)
    eye   = (32, 20, 10, 255)
    short = (28, 28, 28, 255)

    s_c   = (*shirt_col, 255)
    b_c   = (*bandana_col, 255)
    sk_c  = (*skin, 255)
    sk_dk = (*skin_dk, 255)
    hr_c  = (*hair, 255)
    sh_c  = (100, 96, 90, 255)   # shoe

    if direction == 'down':
        # legs
        lo = 4 * leg_phase   # leg offset
        d.rectangle([cx - 9, cy + 8,  cx - 2, cy + 20],    fill=short)
        d.rectangle([cx + 2, cy + 8,  cx + 9, cy + 20],    fill=short)
        d.rectangle([cx - 10, cy + 14 - lo, cx - 2, cy + 22 - lo], fill=sh_c)
        d.rectangle([cx + 2,  cy + 14 + lo, cx + 9, cy + 22 + lo], fill=sh_c)
        # body
        d.rectangle([cx - 10, cy - 4, cx + 10, cy + 10], fill=s_c)
        # collar
        d.rectangle([cx - 3, cy - 4, cx + 3, cy - 1], fill=(*[max(0,v-30) for v in shirt_col], 255))
        # arms (swing opposite to legs)
        arm_y = cy - 2 + 3 * leg_phase
        d.rectangle([cx - 15, arm_y,      cx - 9,  arm_y + 10], fill=sk_c)
        d.rectangle([cx + 9,  cy - 2 - 3 * leg_phase, cx + 15, cy - 2 - 3 * leg_phase + 10], fill=sk_c)
        # head
        hy = cy - 22
        d.ellipse([cx - 9, hy, cx + 9, hy + 17], fill=sk_c)
        # eyes
        d.ellipse([cx - 5, hy + 7, cx - 2, hy + 10], fill=eye)
        d.ellipse([cx + 2, hy + 7, cx + 5, hy + 10], fill=eye)
        # hair / bandana
        d.rectangle([cx - 9, hy,      cx + 9, hy + 5],  fill=hr_c)
        d.rectangle([cx - 11, hy + 4, cx + 11, hy + 8], fill=b_c)
        d.rectangle([cx - 9,  hy + 8, cx + 9,  hy + 12], fill=hr_c)

    elif direction == 'up':
        lo = 4 * leg_phase
        d.rectangle([cx - 9, cy + 8,  cx - 2, cy + 20], fill=short)
        d.rectangle([cx + 2, cy + 8,  cx + 9, cy + 20], fill=short)
        d.rectangle([cx - 10, cy + 14 - lo, cx - 2, cy + 22 - lo], fill=sh_c)
        d.rectangle([cx + 2,  cy + 14 + lo, cx + 9, cy + 22 + lo], fill=sh_c)
        d.rectangle([cx - 10, cy - 4, cx + 10, cy + 10], fill=s_c)
        arm_y = cy - 2 - 3 * leg_phase
        d.rectangle([cx - 15, arm_y,      cx - 9, arm_y + 10], fill=sk_c)
        d.rectangle([cx + 9,  cy - 2 + 3*leg_phase, cx + 15, cy - 2 + 3*leg_phase + 10], fill=sk_c)
        # back of head
        hy = cy - 22
        d.ellipse([cx - 9, hy, cx + 9, hy + 17], fill=hr_c)
        d.rectangle([cx - 9,  hy,     cx + 9, hy + 5],  fill=hr_c)
        d.rectangle([cx - 11, hy + 4, cx + 11, hy + 8], fill=b_c)

    elif direction == 'side':
        lo = 4 * leg_phase
        # legs (side view)
        d.rectangle([cx - 6, cy + 8,  cx + 2, cy + 20], fill=short)
        d.rectangle([cx - 2, cy + 8,  cx + 6, cy + 20], fill=short)
        d.rectangle([cx - 8, cy + 14 - lo, cx + 2, cy + 22 - lo], fill=sh_c)
        d.rectangle([cx,     cy + 14 + lo, cx + 8, cy + 22 + lo], fill=sh_c)
        # body
        d.rectangle([cx - 8, cy - 4, cx + 8, cy + 10], fill=s_c)
        # front arm
        ay = cy - 1 + 3 * leg_phase
        d.rectangle([cx + 6, ay, cx + 12, ay + 9], fill=sk_c)
        # back arm (slightly dimmer)
        bay = cy - 1 - 3 * leg_phase
        d.rectangle([cx - 12, bay, cx - 6, bay + 9], fill=sk_dk)
        # head (side profile)
        hy = cy - 22
        d.ellipse([cx - 6, hy, cx + 8, hy + 17], fill=sk_c)
        # eye
        d.ellipse([cx + 2, hy + 7, cx + 6, hy + 10], fill=eye)
        # nose hint
        d.point((cx + 8, hy + 11), fill=sk_dk)
        # hair / bandana
        d.ellipse([cx - 6, hy, cx + 8, hy + 9], fill=hr_c)
        d.rectangle([cx - 8, hy + 4, cx + 8, hy + 8], fill=b_c)


def _draw_girl(canvas, ox, oy, direction, leg_phase, shirt_col, bandana_col):
    """Draw a single girl frame into `canvas` at (ox,oy)."""
    d  = ImageDraw.Draw(canvas)
    f  = FRAME
    cx = ox + f // 2
    cy = oy + f // 2 + 2

    skin   = P['skin']
    skin_dk= P['skin_dk']
    hair   = P['hair_br']
    eye    = (32, 20, 10, 255)
    short  = (*shirt_col, 255)    # skirt/shorts match shirt tint
    white  = (240, 240, 240, 255)
    sh_c   = (220, 210, 200, 255)

    s_c  = (*shirt_col, 255)
    b_c  = (*bandana_col, 255)
    sk_c = (*skin, 255)
    sk_dk= (*skin_dk, 255)
    hr_c = (*hair, 255)

    if direction == 'down':
        lo = 4 * leg_phase
        # skirt
        d.polygon([
            (cx - 11, cy + 7), (cx + 11, cy + 7),
            (cx + 13, cy + 18), (cx - 13, cy + 18),
        ], fill=s_c)
        # legs below skirt
        d.rectangle([cx - 8,  cy + 16 - lo, cx - 2, cy + 24 - lo], fill=sk_c)
        d.rectangle([cx + 2,  cy + 16 + lo, cx + 8, cy + 24 + lo], fill=sk_c)
        d.rectangle([cx - 9,  cy + 22 - lo, cx - 1, cy + 27 - lo], fill=sh_c)
        d.rectangle([cx + 1,  cy + 22 + lo, cx + 9, cy + 27 + lo], fill=sh_c)
        # body
        d.rectangle([cx - 9, cy - 4, cx + 9, cy + 9], fill=white)
        # arms
        ay = cy - 1 + 3 * leg_phase
        d.rectangle([cx - 13, ay, cx - 8, ay + 9], fill=sk_c)
        d.rectangle([cx + 8, cy - 1 - 3*leg_phase, cx + 13, cy - 1 - 3*leg_phase + 9], fill=sk_c)
        # head
        hy = cy - 22
        d.ellipse([cx - 9, hy, cx + 9, hy + 17], fill=sk_c)
        d.ellipse([cx - 5, hy + 7, cx - 2, hy + 10], fill=eye)
        d.ellipse([cx + 2, hy + 7, cx + 5, hy + 10], fill=eye)
        # hair
        d.ellipse([cx - 10, hy - 2, cx + 10, hy + 9], fill=hr_c)
        # headband
        d.rectangle([cx - 11, hy + 4, cx + 11, hy + 8], fill=b_c)
        # side ponytail hints
        d.rectangle([cx - 12, hy + 8, cx - 8, hy + 18], fill=hr_c)
        d.rectangle([cx + 8,  hy + 8, cx + 12, hy + 18], fill=hr_c)

    elif direction == 'up':
        lo = 4 * leg_phase
        d.polygon([
            (cx - 11, cy + 7), (cx + 11, cy + 7),
            (cx + 13, cy + 18), (cx - 13, cy + 18),
        ], fill=s_c)
        d.rectangle([cx - 8, cy + 16 - lo, cx - 2, cy + 24 - lo], fill=sk_c)
        d.rectangle([cx + 2, cy + 16 + lo, cx + 8, cy + 24 + lo], fill=sk_c)
        d.rectangle([cx - 9, cy + 22 - lo, cx - 1, cy + 27 - lo], fill=sh_c)
        d.rectangle([cx + 1, cy + 22 + lo, cx + 9, cy + 27 + lo], fill=sh_c)
        d.rectangle([cx - 9, cy - 4, cx + 9, cy + 9], fill=white)
        # back of head
        hy = cy - 22
        d.ellipse([cx - 9, hy, cx + 9, hy + 17], fill=hr_c)
        d.rectangle([cx - 11, hy + 4, cx + 11, hy + 8], fill=b_c)
        d.rectangle([cx - 12, hy + 8, cx - 8,  hy + 18], fill=hr_c)
        d.rectangle([cx + 8,  hy + 8, cx + 12, hy + 18], fill=hr_c)

    elif direction == 'side':
        lo = 4 * leg_phase
        d.polygon([
            (cx - 9, cy + 7), (cx + 9, cy + 7),
            (cx + 11, cy + 18), (cx - 11, cy + 18),
        ], fill=s_c)
        d.rectangle([cx - 6, cy + 16 - lo, cx + 2, cy + 24 - lo], fill=sk_c)
        d.rectangle([cx - 2, cy + 16 + lo, cx + 6, cy + 24 + lo], fill=sk_c)
        d.rectangle([cx - 8, cy + 22 - lo, cx + 2, cy + 27 - lo], fill=sh_c)
        d.rectangle([cx,     cy + 22 + lo, cx + 8, cy + 27 + lo], fill=sh_c)
        d.rectangle([cx - 8, cy - 4, cx + 8, cy + 9], fill=white)
        ay = cy - 1 + 3 * leg_phase
        d.rectangle([cx + 6, ay, cx + 12, ay + 8], fill=sk_c)
        bay = cy - 1 - 3 * leg_phase
        d.rectangle([cx - 12, bay, cx - 6, bay + 8], fill=sk_dk)
        hy = cy - 22
        d.ellipse([cx - 6, hy, cx + 8, hy + 17], fill=sk_c)
        d.ellipse([cx + 2, hy + 7, cx + 6, hy + 10], fill=eye)
        d.point((cx + 8, hy + 11), fill=sk_dk)
        d.ellipse([cx - 8, hy - 2, cx + 9, hy + 9], fill=hr_c)
        d.rectangle([cx - 9, hy + 4, cx + 9, hy + 8], fill=b_c)
        d.rectangle([cx + 8, hy + 8, cx + 14, hy + 18], fill=hr_c)


def build_trainer_sheet(gender, shirt_col, bandana_col, filename):
    """
    Produce a 192×192 sprite sheet (3×3 grid, each frame 64×64).
    Layout mirrors what Overworld.js expects:
      frame 0-2: walk_down   row 0
      frame 3-5: walk_up     row 1
      frame 6-8: walk_side   row 2
    leg_phase sequence per row: 0, 1, -1
    """
    sheet  = Image.new('RGBA', (FRAME * 3, FRAME * 3), (0, 0, 0, 0))
    fn     = _draw_boy if gender == 'boy' else _draw_girl
    phases = [0, 1, -1]

    dirs = ['down', 'up', 'side']
    for row, dirn in enumerate(dirs):
        for col, lp in enumerate(phases):
            ox = col * FRAME
            oy = row * FRAME
            fn(sheet, ox, oy, dirn, lp, shirt_col, bandana_col)

    out = os.path.join(ASSETS, 'sprites', 'trainer', filename)
    sheet.save(out)
    print(f'  trainer  → {out}')


# ─── Outfit color definitions ─────────────────────────────────────────────────
# Boys  shirt : [ red,           blue,           green         ]
# Girls shirt : same tint used for skirt/shorts
BOY_OUTFITS = [
    ((216,  80,  40), P['bandana_w']),   # red shirt, white bandana
    (( 48, 100, 200), P['bandana_w']),   # blue shirt
    (( 48, 160,  72), P['bandana_w']),   # green shirt
]
GIRL_OUTFITS = [
    ((200,  48,  48), P['bandana_r']),   # red skirt, red headband
    (( 48, 100, 200), P['bandana_r']),   # blue skirt
    (( 48, 160,  72), P['bandana_r']),   # green skirt
]
OUTFIT_NAMES = ['red', 'blue', 'green']


def build_all_trainers():
    for i, (shirt, band) in enumerate(BOY_OUTFITS):
        build_trainer_sheet('boy', shirt, band, f'boy_{OUTFIT_NAMES[i]}.png')
    for i, (shirt, band) in enumerate(GIRL_OUTFITS):
        build_trainer_sheet('girl', shirt, band, f'girl_{OUTFIT_NAMES[i]}.png')


# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print('Building Emerald-style assets …')
    print('[1/2] Tileset …')
    build_tileset()
    print('[2/2] Trainer sprites …')
    build_all_trainers()
    print('Done.')
