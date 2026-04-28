from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

SECURE_FOLDER_CANDIDATES = [Path("/mnt/c/ATLAS"), Path("C:/ATLAS"), Path("/c/ATLAS")]
MONITORED_FILES = ["atlas.bin", "atlas.key", "atlas.py.bak"]
BASELINE_FILENAME = ".atlas_monitor_baseline.json"
LOG_FILENAME = ".atlas_monitor.log"


def get_secure_atlas_folder() -> Optional[Path]:
    for path in SECURE_FOLDER_CANDIDATES:
        if path.exists() and path.is_dir():
            return path
    return None


def sha256_of_file(path: Path) -> str:
    hash_obj = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def load_baseline(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_baseline(path: Path, baseline: Dict[str, str]) -> None:
    path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")


def append_log(path: Path, message: str) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    with path.open("a", encoding="utf-8") as stream:
        stream.write(f"[{timestamp}] {message}\n")


def current_file_hashes(folder: Path) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for filename in MONITORED_FILES:
        file_path = folder / filename
        if file_path.exists():
            hashes[filename] = sha256_of_file(file_path)
    return hashes


def get_windows_acl(folder: Path) -> Optional[str]:
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", f"icacls {str(folder).replace('/', '\\\\')}"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def report_changes(
    folder: Path, baseline: Dict[str, str], current: Dict[str, str], log_path: Path
) -> None:
    added = sorted([name for name in current if name not in baseline])
    removed = sorted([name for name in baseline if name not in current])
    modified = sorted(
        [
            name
            for name in current
            if name in baseline and baseline[name] != current[name]
        ]
    )

    if not added and not removed and not modified:
        append_log(log_path, "Integrity check passed; no changes detected.")
        print("Integrity check passed; no changes detected.")
        return

    if added:
        msg = f"ALERT: new monitored files detected: {added}"
        append_log(log_path, msg)
        print(msg)
    if removed:
        msg = f"ALERT: monitored files missing: {removed}"
        append_log(log_path, msg)
        print(msg)
    if modified:
        msg = f"ALERT: monitored files modified: {modified}"
        append_log(log_path, msg)
        print(msg)


def ensure_monitor_files(folder: Path) -> None:
    baseline_path = folder / BASELINE_FILENAME
    log_path = folder / LOG_FILENAME
    if not baseline_path.exists():
        hashes = current_file_hashes(folder)
        save_baseline(baseline_path, hashes)
        append_log(log_path, "Baseline created.")
        print("Baseline created. Run the monitor again later to verify integrity.")
        return

    baseline = load_baseline(baseline_path)
    current = current_file_hashes(folder)
    report_changes(folder, baseline, current, log_path)
    acl_output = get_windows_acl(folder)
    if acl_output:
        append_log(log_path, "Checked ACL settings.")
        print("Current ACL settings for the secure folder:")
        print(acl_output)
    else:
        append_log(log_path, "ACL check unavailable.")
        print("ACL check unavailable on this system.")


def main() -> int:
    secure_folder = get_secure_atlas_folder()
    if secure_folder is None:
        print("Secure ATLAS folder not found. Ensure C:\\ATLAS exists.")
        return 1

    if len(sys.argv) > 1 and sys.argv[1] in {"--init", "init"}:
        baseline_path = secure_folder / BASELINE_FILENAME
        save_baseline(baseline_path, current_file_hashes(secure_folder))
        log_path = secure_folder / LOG_FILENAME
        append_log(log_path, "Baseline recreated by user.")
        print("Baseline recreated.")
        return 0

    ensure_monitor_files(secure_folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
