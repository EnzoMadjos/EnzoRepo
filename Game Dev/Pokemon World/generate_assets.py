#!/usr/bin/env python3
"""
Asset generator for Pokemon World.
Downloads LPC CC-BY-SA 3.0 sprites and generates:
  1. Overworld tileset PNG (48x48 tiles, Pokemon Emerald style)
  2. Trainer spritesheets for boy/girl x 3 outfits (red/blue/green)
     Walk cycle: 3 frames x 3 directions in a 3x3 grid (192x192px at 64px/frame)

Attribution (CC-BY-SA 3.0):
  - LPC Base Assets by Sharm, commissioned by OpenGameArt.org / Liberated Pixel Cup
  - Universal LPC Spritesheet Generator contributors:
    bluecarrot16, BenCreating, Evert, ElizaWy, TheraHedwig, MuffinElZangano,
    Johannes Sjölund (wulax), Stephen Challener (Redshrike), and many more
  - Full credits: https://github.com/sanderfrenken/Universal-LPC-Spritesheet-Character-Generator/blob/master/CREDITS.csv
"""

import urllib.request
import os
import sys
from pathlib import Path

try:
    from PIL import Image
    import numpy as np
except ImportError:
    print("Installing Pillow...")
    os.system(f"{sys.executable} -m pip install Pillow numpy -q")
    from PIL import Image
    import numpy as np

ASSETS = Path("/home/enzo/ai-lab/Game Dev/Pokemon World/assets")
TILESETS = ASSETS / "tilesets"
TRAINER_DIR = ASSETS / "sprites" / "trainer"
TILESETS.mkdir(parents=True, exist_ok=True)
TRAINER_DIR.mkdir(parents=True, exist_ok=True)

RAW = "https://raw.githubusercontent.com/sanderfrenken/Universal-LPC-Spritesheet-Character-Generator/master/spritesheets"

def dl(url, path):
    """Download file if not already cached."""
    if path.exists():
        return
    print(f"  DL {path.name}...")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as r, open(path, "wb") as f:
        f.write(r.read())

def composite(*layers) -> Image.Image:
    """Alpha-composite layers in order (bottom to top). Crops all to min height."""
    converted = [l.convert("RGBA") for l in layers]
    # Find minimum height (old LPC = 1344, new = 2944 — walk rows are in first 1344)
    min_h = min(l.height for l in converted)
    base = converted[0].crop((0, 0, converted[0].width, min_h)).copy()
    for layer in converted[1:]:
        lay = layer.crop((0, 0, layer.width, min_h))
        base = Image.alpha_composite(base, lay)
    return base

def crop_walk_frames(sheet: Image.Image, direction: int, frames: list) -> list:
    """
    LPC sheet layout (64px per frame/row):
      Row 8  (y=512): walk south (down)
      Row 9  (y=576): walk west  (left)
      Row 10 (y=640): walk east  (right)
      Row 11 (y=704): walk north (up)
    direction: 0=down, 1=left, 2=right, 3=up
    frames: list of column indices (0-8)
    """
    direction_row = {0: 8, 1: 9, 2: 10, 3: 11}
    y = direction_row[direction] * 64
    result = []
    for col in frames:
        x = col * 64
        frame = sheet.crop((x, y, x + 64, y + 64))
        result.append(frame)
    return result

def build_trainer_sheet(body_path, shirt_path, pants_path, hair_path, out_path):
    """
    Composite LPC layers and extract walk cycle.
    Output: 192x192px (3 cols x 3 rows at 64px)
      Row 0: down  (stand, step-left, step-right)
      Row 1: up    (stand, step-left, step-right)
      Row 2: side  (stand, step-left, step-right)  [use flipX for right direction in Phaser]
    Walk frame indices from LPC 9-frame cycle: 0=stand, 1=step1, 5=step2
    """
    if out_path.exists():
        print(f"  {out_path.name} already exists, skipping.")
        return

    body = Image.open(body_path).convert("RGBA")
    layers = [body]
    if hair_path and hair_path.exists():
        layers.append(Image.open(hair_path).convert("RGBA"))
    if pants_path and pants_path.exists():
        layers.append(Image.open(pants_path).convert("RGBA"))
    if shirt_path and shirt_path.exists():
        layers.append(Image.open(shirt_path).convert("RGBA"))

    composited = composite(*layers)

    # Walk frames: stand=0, step_a=1, step_b=5
    walk_frames = [0, 1, 5]
    sheet = Image.new("RGBA", (192, 192), (0, 0, 0, 0))

    dir_map = [(0, 0), (3, 1), (1, 2)]  # (LPC dir 0=down,3=up,1=left), sheet row
    for lpc_dir, row in dir_map:
        frames = crop_walk_frames(composited, lpc_dir, walk_frames)
        for col, frame in enumerate(frames):
            sheet.paste(frame, (col * 64, row * 64), frame)

    sheet.save(out_path)
    print(f"  Saved {out_path.name} ({out_path.stat().st_size // 1024}KB)")

# ── Download LPC Layers ────────────────────────────────────────────────
print("=== Downloading LPC sprite layers ===")
TMP = TRAINER_DIR / "_raw"
TMP.mkdir(exist_ok=True)

files = {
    "body_male_light": f"{RAW}/body/bodies/male/light.png",
    "body_female_light": f"{RAW}/body/bodies/female/light.png",
    "hair_boy": f"{RAW}/hair/buzzcut/adult/dark_brown.png",
    "hair_girl": f"{RAW}/hair/bangs/adult/dark_brown.png",
    "pants_male_black": f"{RAW}/legs/pants/male/black.png",
    "pants_female_black": f"{RAW}/legs/pants/female/black.png",
    "shirt_male_red": f"{RAW}/torso/clothes/shortsleeve/shortsleeve/male/maroon.png",
    "shirt_male_blue": f"{RAW}/torso/clothes/shortsleeve/shortsleeve/male/navy.png",
    "shirt_male_green": f"{RAW}/torso/clothes/shortsleeve/shortsleeve/male/forest.png",
    "shirt_female_red": f"{RAW}/torso/clothes/shortsleeve/shortsleeve/female/maroon.png",
    "shirt_female_blue": f"{RAW}/torso/clothes/shortsleeve/shortsleeve/female/navy.png",
    "shirt_female_green": f"{RAW}/torso/clothes/shortsleeve/shortsleeve/female/forest.png",
}

downloaded = {}
for key, url in files.items():
    path = TMP / f"{key}.png"
    try:
        dl(url, path)
        downloaded[key] = path
    except Exception as e:
        print(f"  WARN: {key} download failed ({e}), will skip.")
        downloaded[key] = None

# ── Build Trainer Sheets ───────────────────────────────────────────────
print("\n=== Building trainer spritesheets ===")
variants = [
    ("boy", "male", "boy", ["red", "blue", "green"]),
    ("girl", "female", "girl", ["red", "blue", "green"]),
]
shirt_key_map = {"red": "maroon", "blue": "navy", "green": "forest"}

for gender_key, gender, prefix, colors in variants:
    for color in colors:
        shirt_map_key = shirt_key_map[color]
        shirt_url = f"{RAW}/torso/clothes/shortsleeve/shortsleeve/{gender}/{shirt_map_key}.png"
        shirt_path = TMP / f"shirt_{gender}_{shirt_map_key}.png"
        try:
            dl(shirt_url, shirt_path)
        except Exception as e:
            print(f"  WARN: shirt {gender} {color} failed: {e}")
            shirt_path = None

        out = TRAINER_DIR / f"{prefix}_{color}.png"
        # gender_key is "boy"/"girl" but downloads used "male"/"female" keys
        body_key = f"body_{gender}_light"
        pants_key = f"pants_{gender}_black"
        hair_key = f"hair_{'boy' if gender == 'male' else 'girl'}"
        try:
            build_trainer_sheet(
                body_path=downloaded.get(body_key),
                shirt_path=shirt_path if shirt_path and shirt_path.exists() else None,
                pants_path=downloaded.get(pants_key),
                hair_path=downloaded.get(hair_key),
                out_path=out
            )
        except Exception as e:
            print(f"  ERROR building {prefix}_{color}: {e}")

# ── Generate Pokemon-Style Tileset ─────────────────────────────────────
print("\n=== Generating Pokemon-style overworld tileset ===")

TS = 48  # tile size

def make_tileset():
    # 8 tiles: grass(0) path(1) tree(2) water(3) tall_grass(4) wall(5) door(6) fence(7)
    n_tiles = 8
    out = Image.new("RGBA", (TS * n_tiles, TS), (0, 0, 0, 0))
    arr = np.zeros((TS, TS * n_tiles, 4), dtype=np.uint8)
    arr[:, :, 3] = 255  # fully opaque

    def tile(idx):
        """Return view into array for tile at index."""
        return arr[:, idx * TS:(idx + 1) * TS, :]

    # Utility
    rng = np.random.default_rng(1337)  # deterministic

    def fill(t, rgb):
        t[:, :, :3] = rgb
        t[:, :, 3] = 255

    def add_noise(t, strength=10):
        n = (rng.random(t.shape[:2]) * strength - strength // 2).astype(np.int16)
        for c in range(3):
            chan = t[:, :, c].astype(np.int16) + n
            t[:, :, c] = np.clip(chan, 0, 255).astype(np.uint8)

    def draw_line_h(t, y, rgb, width=1):
        for dy in range(width):
            if 0 <= y + dy < TS:
                t[y + dy, :, :3] = rgb

    def draw_line_v(t, x, rgb, width=1):
        for dx in range(width):
            if 0 <= x + dx < TS:
                t[:, x + dx, :3] = rgb

    def draw_rect(t, x, y, w, h, rgb, filled=True):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(TS, x + w), min(TS, y + h)
        if filled:
            t[y0:y1, x0:x1, :3] = rgb
        else:
            t[y0:y1, x0, :3] = rgb
            t[y0:y1, x1 - 1, :3] = rgb
            t[y0, x0:x1, :3] = rgb
            t[y1 - 1, x0:x1, :3] = rgb

    def draw_circle(t, cx, cy, r, rgb):
        for y in range(TS):
            for x in range(TS):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r ** 2:
                    t[y, x, :3] = rgb

    # ── Tile 0: Grass ──────────────────────────────────────────────────
    t = tile(0)
    fill(t, (56, 152, 56))
    add_noise(t, 14)
    # Sparse lighter/darker grass tufts
    for _ in range(30):
        gx, gy = rng.integers(0, TS, 2)
        t[gy, gx, :3] = (80, 180, 68)
    for _ in range(15):
        gx, gy = rng.integers(0, TS, 2)
        t[gy, gx, :3] = (36, 116, 36)

    # ── Tile 1: Path / Dirt ────────────────────────────────────────────
    t = tile(1)
    fill(t, (192, 152, 100))
    add_noise(t, 16)
    # Subtle pebble marks
    for _ in range(18):
        gx, gy = rng.integers(2, TS - 2, 2)
        pebble_size = rng.integers(1, 3)
        for dy in range(-pebble_size, pebble_size + 1):
            for dx in range(-pebble_size, pebble_size + 1):
                if dx * dx + dy * dy <= pebble_size * pebble_size:
                    py, px = gy + dy, gx + dx
                    if 0 <= py < TS and 0 <= px < TS:
                        t[py, px, :3] = (168, 132, 80)

    # ── Tile 2: Tree (top view — full canopy) ──────────────────────────
    t = tile(2)
    # Base grass underneath
    fill(t, (44, 120, 44))
    # Canopy - dark green circle
    draw_circle(t, TS // 2, TS // 2, TS // 2 - 2, (32, 88, 32))
    # Inner highlight rings
    draw_circle(t, TS // 2 - 3, TS // 2 - 3, TS // 4, (52, 116, 52))
    draw_circle(t, TS // 2 - 4, TS // 2 - 4, TS // 8, (68, 140, 60))
    # Shadow at bottom of canopy
    for y in range(TS * 3 // 4, TS - 2):
        for x in range(0, TS):
            if (x - TS // 2) ** 2 + (y - TS // 2) ** 2 <= (TS // 2 - 2) ** 2:
                t[y, x, :3] = (24, 64, 24)
    # Trunk (small center)
    draw_rect(t, TS // 2 - 2, TS // 2 - 2, 4, 4, (100, 64, 28))

    # ── Tile 3: Water ──────────────────────────────────────────────────
    t = tile(3)
    fill(t, (52, 120, 200))
    # Wave lines (horizontal lighter stripes)
    for y in range(0, TS, 6):
        for x in range(0, TS):
            wave_val = int(20 * np.sin((x + y * 0.5) * 0.4))
            t[y, x, :3] = np.clip(
                np.array([52, 140, 216], dtype=np.int16) + wave_val - 10, 30, 255
            ).astype(np.uint8)
    # Shimmer spots
    for _ in range(8):
        wx, wy = rng.integers(2, TS - 2, 2)
        t[wy, wx, :3] = (160, 210, 255)
        t[wy, wx, 3] = 255
    add_noise(t, 8)

    # ── Tile 4: Tall Grass ─────────────────────────────────────────────
    t = tile(4)
    fill(t, (56, 152, 56))
    # Grass blades (lighter vertical strokes)
    for x in range(0, TS, 3):
        blade_h = 4 + rng.integers(0, 8)
        y0 = TS - blade_h - rng.integers(0, 8)
        for y in range(y0, y0 + blade_h):
            if 0 <= y < TS:
                blade_color = (100, 190, 68) if (x // 3) % 2 == 0 else (72, 170, 56)
                t[y, x, :3] = blade_color
                if x + 1 < TS:
                    t[y, x + 1, :3] = blade_color
    # Darker base
    for y in range(TS - 6, TS):
        t[y, :, :3] = np.clip(
            t[y, :, :3].astype(np.int16) - 20, 0, 255
        ).astype(np.uint8)
    add_noise(t, 10)

    # ── Tile 5: Building Wall ──────────────────────────────────────────
    t = tile(5)
    fill(t, (212, 196, 164))
    # Horizontal brick lines every 8px
    for y in range(7, TS, 8):
        t[y, :, :3] = (164, 152, 124)
    # Vertical brick joints (staggered)
    for row in range(TS // 8 + 1):
        offset = 12 if row % 2 == 0 else 0
        for x in range(offset, TS, 24):
            if 0 <= x < TS:
                for dy in range(7):
                    y = row * 8 + dy
                    if 0 <= y < TS:
                        t[y, x, :3] = (164, 152, 124)
    add_noise(t, 8)

    # ── Tile 6: Door ───────────────────────────────────────────────────
    t = tile(6)
    fill(t, (212, 196, 164))  # Wall around door
    # Brick pattern (same as wall)
    for y in range(7, TS, 8):
        t[y, :, :3] = (164, 152, 124)
    for row in range(TS // 8 + 1):
        offset = 12 if row % 2 == 0 else 0
        for x in range(offset, TS, 24):
            if 0 <= x < TS:
                for dy in range(7):
                    y = row * 8 + dy
                    if 0 <= y < TS:
                        t[y, x, :3] = (164, 152, 124)
    # Door body (centered, brown)
    door_x, door_w, door_h = TS // 2 - 10, 20, 36
    door_y = TS - door_h
    draw_rect(t, door_x, door_y, door_w, door_h, (136, 80, 36))
    # Door frame (darker brown outline)
    draw_rect(t, door_x - 1, door_y - 1, door_w + 2, door_h + 1, (88, 52, 20), filled=False)
    # Door panel lines
    draw_line_v(t, door_x + door_w // 2, (88, 52, 20), 1)
    draw_line_h(t, door_y + door_h // 2, (88, 52, 20), 1)
    # Door knob
    t[door_y + door_h * 3 // 4, door_x + door_w - 5, :3] = (220, 180, 80)

    # ── Tile 7: Fence / Border ────────────────────────────────────────
    t = tile(7)
    fill(t, (56, 152, 56))  # Grass base
    add_noise(t, 10)
    # Fence posts (vertical brown bars)
    for x in [4, 20, 36]:
        draw_rect(t, x, 4, 4, TS - 8, (148, 100, 52))
        draw_rect(t, x, 4, 4, TS - 8, (120, 80, 40), filled=False)
    # Horizontal fence rails
    draw_rect(t, 4, 12, TS - 8, 3, (168, 116, 60))
    draw_rect(t, 4, TS - 16, TS - 8, 3, (168, 116, 60))

    return Image.fromarray(arr, "RGBA")

tileset = make_tileset()
out_path = TILESETS / "overworld.png"
tileset.save(out_path)
print(f"Tileset saved: {out_path} ({out_path.stat().st_size // 1024}KB)")
print(f"Dimensions: {tileset.size} ({tileset.width // TS} tiles x {tileset.height // TS} rows)")

print("\n=== Done! ===")
print("\nTile indices:")
tile_names = ["0:grass", "1:path", "2:tree", "3:water", "4:tall_grass", "5:wall", "6:door", "7:fence"]
for t in tile_names:
    print(f"  {t}")
print("\nTrainer sheets (192x192, 64px frames, 3cols x 3rows):")
print("  Row 0: facing down  (frames 0,1,2 = stand,step1,step2)")
print("  Row 1: facing up    (frames 3,4,5 = stand,step1,step2)")
print("  Row 2: facing side  (frames 6,7,8 = stand,step1,step2 — flipX for right)")
