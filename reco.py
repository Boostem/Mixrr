import os
import re
from datetime import datetime
from pathlib import Path

import cloudscraper
from coolname import generate_slug
import requests

# Initialize cloudscraper session
scraper = cloudscraper.create_scraper()

# Headers (keeping only the essential headers)
TUNEBAT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://tunebat.com",
    "Origin": "https://tunebat.com",
}


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


def get_spotify_token():
    """Fetch a Spotify client credentials token."""
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Missing SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_SECRET in environment/.env")
        return None

    resp = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(client_id, client_secret),
        timeout=20,
    )
    if resp.status_code != 200:
        print(f"Failed to fetch Spotify token (status {resp.status_code}): {resp.text}")
        return None
    return resp.json().get("access_token")


def search_spotify_tracks(query: str, token: str, limit: int = 5, offset: int = 0):
    """Return a list of Spotify tracks for the query plus total count."""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": query, "type": "track", "limit": limit, "offset": offset}
    resp = requests.get(
        "https://api.spotify.com/v1/search", headers=headers, params=params, timeout=20
    )
    if resp.status_code != 200:
        print(f"Failed to search Spotify (status {resp.status_code}): {resp.text}")
        return [], 0

    data = resp.json().get("tracks", {})
    items = data.get("items", [])
    total = data.get("total", 0)
    return items, total


def format_artists(track):
    return ", ".join(artist["name"] for artist in track.get("artists", []))


def choose_track_paginated(query: str, token: str, page_size: int = 5):
    """Interactive, paginated track picker."""
    offset = 0
    total = None

    while True:
        tracks, total = search_spotify_tracks(query, token, limit=page_size, offset=offset)
        if not tracks:
            if offset == 0:
                print("No tracks found on Spotify for that search.")
            else:
                print("No tracks on this page.")
            return None

        page_start = offset + 1
        page_end = offset + len(tracks)
        print(f"\nSelect a track (showing {page_start}-{page_end} of {total}):")
        for idx, track in enumerate(tracks, start=1):
            artist_names = format_artists(track)
            print(f"{idx}. {track.get('name')} — {artist_names}")

        print("Commands: number to select | n = next page | p = prev page | q = quit | Enter = select 1")
        choice = input("Your choice: ").strip().lower()

        if choice == "q":
            return None
        if choice == "n":
            if total is not None and offset + page_size >= total:
                print("Already at the last page.")
                continue
            offset += page_size
            continue
        if choice == "p":
            if offset == 0:
                print("Already at the first page.")
                continue
            offset = max(0, offset - page_size)
            continue

        if not choice:
            choice_idx = 0
        else:
            try:
                choice_idx = int(choice) - 1
            except ValueError:
                print("Invalid input, defaulting to 1.")
                choice_idx = 0

        if choice_idx < 0 or choice_idx >= len(tracks):
            print("Choice out of range, defaulting to 1.")
            choice_idx = 0

        return tracks[choice_idx]


def fetch_track_and_recommendations(track_id: str):
    """
    Fetch seed track details and recommendations (r) for the given track id.

    Returns a tuple of (seed_track_data, recommendations_list).
    """
    track_url = f"https://api.tunebat.com/api/tracks?trackId={track_id}"
    response = scraper.get(track_url, headers=TUNEBAT_HEADERS)
    if response.status_code != 200:
        print(f"Failed to fetch track details, status code: {response.status_code}")
        return {}, []

    track_data = response.json().get("data", {})
    return track_data, track_data.get("r", [])


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9 _.-]+", "", name).strip()
    return cleaned or "seed"


def ordinal_suffix(day: int) -> str:
    if 11 <= day % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def human_timestamp(ts: datetime) -> str:
    month = ts.strftime("%b")
    day = ts.day
    suffix = ordinal_suffix(day)
    hour_12 = ts.hour % 12 or 12
    minute = ts.minute
    ampm = "AM" if ts.hour < 12 else "PM"
    # Use a hyphen instead of colon to keep filenames portable.
    return f"{month} {day}{suffix} {hour_12}-{minute:02d}{ampm} {ts.year}"


def random_mix_title() -> str:
    words = generate_slug().split("-")
    return " ".join(word.capitalize() for word in words)


def write_playlist_file(base_name: str, random_title: str, lines: list[str]):
    timestamp_str = human_timestamp(datetime.now())
    filename = f"{base_name} {random_title}_{timestamp_str}.txt"
    filename = sanitize_filename(filename)
    Path(filename).write_text("\n".join(lines))
    print(f"\nSaved playlist to {filename}")


def build_grid_formatter(rows: list[dict]):
    """Return a formatter function that aligns Artist/Title/Key columns."""
    artist_width = max(len(r.get("artist", "")) for r in rows) if rows else 0
    title_width = max(len(r.get("title", "")) for r in rows) if rows else 0
    key_width = max(len(str(r.get("camelot", ""))) for r in rows) if rows else 0

    def _fmt(row: dict) -> str:
        artist = row.get("artist", "")
        title = row.get("title", "")
        camelot = row.get("camelot", "N/A")
        bpm = row.get("bpm")
        delta = row.get("delta")

        bpm_str = f"{bpm:.0f}" if isinstance(bpm, (int, float)) else "N/A"
        if isinstance(delta, (int, float)):
            delta_str = f"Δ {delta:+.0f}"
        else:
            delta_str = "Δ N/A"

        return (
            f"{artist:<{artist_width}} - "
            f"{title:<{title_width}} - "
            f"{camelot:<{key_width}} - "
            f"{bpm_str:>4} ({delta_str})"
        )

    return _fmt


def parse_camelot(code: str | None):
    """Parse camelot like '4A' or '10B' -> (num, mode)."""
    if not code:
        return None
    m = re.match(r"^\s*(\d{1,2})([AaBb])\s*$", str(code))
    if not m:
        return None
    num = int(m.group(1))
    if not (1 <= num <= 12):
        return None
    mode = m.group(2).upper()
    return num, mode


def camelot_neighbors(cam: tuple[int, str]):
    """Return acceptable neighbor camelot keys (including self)."""
    num, mode = cam
    num_minus = 12 if num == 1 else num - 1
    num_plus = 1 if num == 12 else num + 1
    other_mode = "B" if mode == "A" else "A"
    return {
        (num, mode),  # same
        (num_minus, mode),
        (num_plus, mode),
        (num, other_mode),  # relative major/minor
    }


def is_camelot_adjacent(a: tuple[int, str] | None, b: tuple[int, str] | None) -> bool:
    if not a or not b:
        return False
    return b in camelot_neighbors(a)


def bpm_matches(prev_bpm: float | int | None, bpm: float | int | None, tolerance=0.06) -> bool:
    if prev_bpm is None or bpm is None or prev_bpm <= 0 or bpm <= 0:
        return False

    def within(target):
        return abs(bpm - target) / target <= tolerance

    return within(prev_bpm) or within(prev_bpm * 2) or within(prev_bpm * 0.5)


def build_mix_order(seed: dict, candidates: list[dict]):
    """
    Build an ordered list starting with the seed. We prefer Camelot-adjacent + BPM-close
    tracks; if none fit, we start a new trend (allow a jump) and continue the constraints
    from that new point.
    """
    order = [seed | {"jump": False}]
    remaining = [c.copy() for c in candidates]
    prev = order[0]

    while remaining:
        valid = [
            t
            for t in remaining
            if is_camelot_adjacent(prev["camelot"], t["camelot"]) and bpm_matches(prev["bpm"], t["bpm"])
        ]

        if valid:
            valid.sort(key=lambda t: abs(t["bpm"] - prev["bpm"]))
            chosen = valid[0]
            chosen["jump"] = False
        else:
            # No smooth option; pick a new "mini-seed" that has the best chance to continue.
            def connectivity_score(track):
                return sum(
                    1
                    for other in remaining
                    if other is not track
                    and is_camelot_adjacent(track["camelot"], other["camelot"])
                    and bpm_matches(track["bpm"], other["bpm"])
                )

            best = None
            best_key = None
            for t in remaining:
                connect = connectivity_score(t)
                key = (-connect, abs(t["bpm"] - prev["bpm"]))  # prefer more neighbors, then closest BPM jump
                if best is None or key < best_key:
                    best = t
                    best_key = key

            chosen = best
            chosen["jump"] = True  # trend reset / BPM jump

        order.append(chosen)
        remaining.remove(chosen)
        prev = chosen

    return order


def main():
    load_env_from_file()

    user_input = input("Enter a song/artist to search on Spotify: ").strip()
    if not user_input:
        print("No search term provided.")
        return

    token = get_spotify_token()
    if not token:
        return

    selected = choose_track_paginated(user_input, token, page_size=5)
    if not selected:
        return

    seed_track_id = selected.get("id")
    if not seed_track_id:
        print("Selected track is missing an id.")
        return

    seed_data, related_tracks = fetch_track_and_recommendations(seed_track_id)

    seed_name = selected.get("name", "Unknown")
    seed_artists = format_artists(selected)
    seed_bpm = seed_data.get("b")
    seed_cam = parse_camelot(seed_data.get("c"))
    seed_cam_str = seed_data.get("c") or seed_data.get("k", "N/A")

    if seed_cam is None or seed_bpm is None:
        print("Seed is missing Camelot key or BPM; cannot build DJ mix order.")
        return

    seed_info = {
        "id": seed_track_id,
        "name": seed_name,
        "artists": seed_artists,
        "camelot": seed_cam,
        "camelot_str": seed_cam_str,
        "bpm": seed_bpm,
        "url": f"https://open.spotify.com/track/{seed_track_id}",
    }

    # Prepare candidate pool with required fields
    candidates = []
    for track in related_tracks:
        tid = track.get("id")
        cam = parse_camelot(track.get("c"))
        bpm = track.get("b")
        if not tid or cam is None or bpm is None:
            continue
        candidates.append(
            {
                "id": tid,
                "name": track.get("n", "Unknown"),
                "artists": ", ".join(track.get("as", [])),
                "camelot": cam,
                "camelot_str": track.get("c") or track.get("k", "N/A"),
                "bpm": bpm,
                "url": f"https://open.spotify.com/track/{tid}",
            }
        )

    mix_tracks = build_mix_order(seed_info, candidates)

    mix_title = random_mix_title()

    # Console display with details
    display_rows = []
    prev_bpm_for_delta = None
    for track in mix_tracks:
        delta = None
        if prev_bpm_for_delta is not None and track["bpm"] is not None:
            delta = track["bpm"] - prev_bpm_for_delta
        display_rows.append(
            {
                "artist": track["artists"],
                "title": track["name"],
                "camelot": track["camelot_str"],
                "bpm": track["bpm"],
                "delta": delta if delta is not None else 0,
                "jump": track.get("jump", False),
            }
        )
        prev_bpm_for_delta = track["bpm"]

    fmt = build_grid_formatter(display_rows)

    print("\nDJ mix order (console):")
    for idx, row in enumerate(display_rows, start=1):
        line = f"{idx:02d}. {fmt(row)}"
        if row.get("jump"):
            line += "  [jump to new trend]"
        print(line)

    url_lines = [t["url"] for t in mix_tracks]

    write_playlist_file(seed_name, mix_title, url_lines)


if __name__ == "__main__":
    main()
