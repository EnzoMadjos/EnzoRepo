"""
generate_data.py — Phase 3 Step 0
Fetches all Gen 1-3 Pokémon (ids 1-386) and their moves from PokeAPI.
Outputs:
  data/pokemon.json — [{id, name, types[], baseStats:{hp,atk,def,spa,spd,spe}, catchRate, baseExpYield, moves:[{name,level}]}]
  data/moves.json   — {name: {id, name, type, power, accuracy, pp, damageClass}}

Run once before starting the server:
  python generate_data.py
"""

import asyncio
import json
import os
import sys

import aiohttp

POKEAPI = "https://pokeapi.co/api/v2"
GEN3_MAX = 386
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CONCURRENCY = 20  # parallel requests — polite for PokeAPI


async def fetch_json(session: aiohttp.ClientSession, url: str) -> dict:
    async with session.get(url) as resp:
        if resp.status == 404:
            return {}
        resp.raise_for_status()
        return await resp.json()


async def fetch_pokemon(session: aiohttp.ClientSession, poke_id: int) -> dict | None:
    data = await fetch_json(session, f"{POKEAPI}/pokemon/{poke_id}")
    if not data:
        return None

    species_url = data.get("species", {}).get("url", "")
    species = await fetch_json(session, species_url) if species_url else {}

    # Base stats
    stats_raw = {s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])}
    base_stats = {
        "hp":  stats_raw.get("hp", 45),
        "atk": stats_raw.get("attack", 45),
        "def": stats_raw.get("defense", 45),
        "spa": stats_raw.get("special-attack", 45),
        "spd": stats_raw.get("special-defense", 45),
        "spe": stats_raw.get("speed", 45),
    }

    # Types
    types = [t["type"]["name"] for t in data.get("types", [])]

    # Learnset — level-up moves only, Gen 3 (version group 7 = firered-leafgreen or fallback)
    raw_moves = data.get("moves", [])
    level_moves = []
    for m in raw_moves:
        for vgd in m.get("version_group_details", []):
            if (vgd["move_learn_method"]["name"] == "level-up"
                    and vgd["version_group"]["name"] in ("firered-leafgreen", "emerald", "ruby-sapphire")):
                level_moves.append({
                    "name": m["move"]["name"],
                    "level": vgd["level_learned_at"],
                })
                break  # take first matching version group

    level_moves.sort(key=lambda x: x["level"])

    return {
        "id": poke_id,
        "name": data["name"],
        "types": types,
        "baseStats": base_stats,
        "catchRate": species.get("capture_rate", 45),
        "baseExpYield": species.get("base_happiness", 70),  # fallback; real field below
        "baseExpYieldReal": data.get("base_experience", 64),
        "moves": level_moves,
    }


async def fetch_move(session: aiohttp.ClientSession, name: str) -> dict | None:
    data = await fetch_json(session, f"{POKEAPI}/move/{name}")
    if not data:
        return None

    damage_class = data.get("damage_class", {}).get("name", "physical")
    return {
        "id": data["id"],
        "name": name,
        "type": data.get("type", {}).get("name", "normal"),
        "power": data.get("power") or 0,
        "accuracy": data.get("accuracy") or 100,
        "pp": data.get("pp", 10),
        "damageClass": damage_class,  # "physical" | "special" | "status"
    }


async def run():
    os.makedirs(DATA_DIR, exist_ok=True)

    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=120)

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # --- Fetch all Pokémon ---
        print(f"Fetching {GEN3_MAX} Pokémon from PokeAPI…", flush=True)
        sem = asyncio.Semaphore(CONCURRENCY)

        async def fetch_limited_pokemon(pid):
            async with sem:
                result = await fetch_pokemon(session, pid)
                if result:
                    sys.stdout.write(f"\r  {pid}/{GEN3_MAX} — {result['name']:<20}")
                    sys.stdout.flush()
                return result

        tasks = [fetch_limited_pokemon(i) for i in range(1, GEN3_MAX + 1)]
        raw_pokemon = await asyncio.gather(*tasks)

        pokemon_list = [p for p in raw_pokemon if p is not None]
        # Use real base exp yield
        for p in pokemon_list:
            p["baseExpYield"] = p.pop("baseExpYieldReal", p["baseExpYield"])

        print(f"\n  ✓ Got {len(pokemon_list)} Pokémon")

        # --- Collect unique move names ---
        all_move_names: set[str] = set()
        for p in pokemon_list:
            for m in p["moves"]:
                all_move_names.add(m["name"])

        print(f"Fetching {len(all_move_names)} unique moves…", flush=True)
        move_count = [0]

        async def fetch_limited_move(name):
            async with sem:
                result = await fetch_move(session, name)
                move_count[0] += 1
                sys.stdout.write(f"\r  {move_count[0]}/{len(all_move_names)} — {name:<30}")
                sys.stdout.flush()
                return result

        move_tasks = [fetch_limited_move(name) for name in all_move_names]
        raw_moves = await asyncio.gather(*move_tasks)

        moves_dict = {}
        for m in raw_moves:
            if m:
                moves_dict[m["name"]] = m

        print(f"\n  ✓ Got {len(moves_dict)} moves")

    # --- Write outputs ---
    pokemon_path = os.path.join(DATA_DIR, "pokemon.json")
    moves_path = os.path.join(DATA_DIR, "moves.json")

    with open(pokemon_path, "w", encoding="utf-8") as f:
        json.dump(pokemon_list, f, separators=(",", ":"))

    with open(moves_path, "w", encoding="utf-8") as f:
        json.dump(moves_dict, f, separators=(",", ":"))

    # Verify sizes
    pk_kb = os.path.getsize(pokemon_path) // 1024
    mv_kb = os.path.getsize(moves_path) // 1024
    print(f"\n✅ data/pokemon.json  — {len(pokemon_list)} entries ({pk_kb} KB)")
    print(f"✅ data/moves.json    — {len(moves_dict)} entries ({mv_kb} KB)")

    # Write ready flag for app.py startup check
    flag_path = os.path.join(DATA_DIR, "gen3_data_ready.flag")
    with open(flag_path, "w") as f:
        f.write("ok")
    print("✅ data/gen3_data_ready.flag written")


if __name__ == "__main__":
    asyncio.run(run())
