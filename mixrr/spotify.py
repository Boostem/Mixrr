import requests


def get_spotify_token():
    """Fetch a Spotify client credentials token from env vars."""
    import os

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
