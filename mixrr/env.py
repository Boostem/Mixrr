import os
from pathlib import Path


def load_env_from_file(env_path: str = ".env"):
    """Populate os.environ with keys from a simple KEY=VALUE .env file if not already set."""
    if os.getenv("SPOTIPY_CLIENT_ID") and os.getenv("SPOTIPY_CLIENT_SECRET"):
        return

    path = Path(env_path)
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())
