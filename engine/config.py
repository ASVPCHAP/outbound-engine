"""Loads .env (stdlib only) and the client file for this install."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env(path=ROOT / ".env"):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_env()


def get(name, default=None):
    return os.environ.get(name) or default


def require(*names):
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise SystemExit(f"Missing in .env: {', '.join(missing)}")
    return [os.environ[n] for n in names]


def client():
    cid = get("CLIENT_ID", "example")
    return json.loads((ROOT / "clients" / f"{cid}.json").read_text(encoding="utf-8"))
