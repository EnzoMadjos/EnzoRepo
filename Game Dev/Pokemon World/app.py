from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
SAVE_DIR = BASE_DIR / "save"
SAVE_DIR.mkdir(exist_ok=True)

# Ensure all static dirs exist
for d in ["scripts", "assets", "data", "templates"]:
    (BASE_DIR / d).mkdir(exist_ok=True)

app = FastAPI(title="Pokemon World")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/scripts", StaticFiles(directory=str(BASE_DIR / "scripts")), name="scripts")
app.mount("/assets", StaticFiles(directory=str(BASE_DIR / "assets")), name="assets")
app.mount("/data", StaticFiles(directory=str(BASE_DIR / "data")), name="data")


@app.get("/")
async def index():
    return FileResponse(str(BASE_DIR / "templates" / "index.html"))


@app.post("/api/save")
async def save_game(request: Request):
    try:
        body = await request.json()
        profile = body.get("profile", {})
        world = body.get("world", {})
        (SAVE_DIR / "profile.json").write_text(json.dumps(profile, indent=2))
        (SAVE_DIR / "world.json").write_text(json.dumps(world, indent=2))
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/load")
async def load_game():
    profile_path = SAVE_DIR / "profile.json"
    world_path = SAVE_DIR / "world.json"
    profile = json.loads(profile_path.read_text()) if profile_path.exists() else {}
    world = json.loads(world_path.read_text()) if world_path.exists() else {}
    return {"profile": profile, "world": world}


@app.get("/api/health")
async def health():
    return {"status": "ok", "game": "Pokemon World", "phase": 1}
