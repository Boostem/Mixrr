from mixrr.env import load_env_from_file
from mixrr.formatting import build_grid_formatter, random_mix_title, write_playlist_file
from mixrr.mixlogic import build_mix_order, parse_camelot
from mixrr.spotify import choose_track_paginated, format_artists, get_spotify_token
from mixrr.tunebat import fetch_track_and_recommendations


def build_candidates(related_tracks):
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
    return candidates


def build_seed(selected, seed_data):
    seed_track_id = selected.get("id")
    seed_name = selected.get("name", "Unknown")
    seed_artists = format_artists(selected)
    seed_bpm = seed_data.get("b")
    seed_cam = parse_camelot(seed_data.get("c"))
    seed_cam_str = seed_data.get("c") or seed_data.get("k", "N/A")

    return {
        "id": seed_track_id,
        "name": seed_name,
        "artists": seed_artists,
        "camelot": seed_cam,
        "camelot_str": seed_cam_str,
        "bpm": seed_bpm,
        "url": f"https://open.spotify.com/track/{seed_track_id}",
    }


def display_mix(mix_tracks):
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
    seed_info = build_seed(selected, seed_data)

    if seed_info["camelot"] is None or seed_info["bpm"] is None:
        print("Seed is missing Camelot key or BPM; cannot build DJ mix order.")
        return

    candidates = build_candidates(related_tracks)
    mix_tracks = build_mix_order(seed_info, candidates)

    mix_title = random_mix_title()
    display_mix(mix_tracks)

    url_lines = [t["url"] for t in mix_tracks]
    write_playlist_file(seed_info["name"], mix_title, url_lines)


if __name__ == "__main__":
    main()
