from mixrr.env import load_env_from_file
from mixrr.formatting import build_grid_formatter, random_mix_title, write_playlist_file
from mixrr.mixlogic import build_mix_order, filter_trends, parse_camelot
from mixrr.models import Track
from mixrr.spotify import choose_track_paginated, format_artists, get_spotify_token
from mixrr.rec_api import fetch_track_and_recommendations


def build_candidates(related_tracks):
    candidates: list[Track] = []
    for track in related_tracks:
        tid = track.get("id")
        cam = parse_camelot(track.get("c"))
        bpm = track.get("b")
        if not tid or cam is None or bpm is None:
            continue
        candidates.append(
            Track(
                id=tid,
                name=track.get("n", "Unknown"),
                artists=", ".join(track.get("as", [])),
                camelot=cam,
                camelot_str=track.get("c") or track.get("k", "N/A"),
                bpm=bpm,
                url=f"https://open.spotify.com/track/{tid}",
            )
        )
    return candidates


def build_seed(selected, seed_data):
    seed_track_id = selected.get("id")
    seed_name = selected.get("name", "Unknown")
    seed_artists = format_artists(selected)
    seed_bpm = seed_data.get("b")
    seed_cam = parse_camelot(seed_data.get("c"))
    seed_cam_str = seed_data.get("c") or seed_data.get("k", "N/A")

    return Track(
        id=seed_track_id,
        name=seed_name,
        artists=seed_artists,
        camelot=seed_cam,
        camelot_str=seed_cam_str,
        bpm=seed_bpm,
        url=f"https://open.spotify.com/track/{seed_track_id}",
    )


def build_seed_from_data(track_id: str, seed_data, fallback: Track | None = None):
    name = seed_data.get("n") or (fallback.name if fallback else "Unknown")
    artists = ", ".join(seed_data.get("as", [])) or (fallback.artists if fallback else "Unknown")
    camelot = parse_camelot(seed_data.get("c")) or (fallback.camelot if fallback else None)
    camelot_str = seed_data.get("c") or seed_data.get("k", "N/A") or (fallback.camelot_str if fallback else "N/A")
    bpm = seed_data.get("b") or (fallback.bpm if fallback else None)

    return Track(
        id=track_id,
        name=name,
        artists=artists,
        camelot=camelot,
        camelot_str=camelot_str,
        bpm=bpm,
        url=f"https://open.spotify.com/track/{track_id}",
    )


def display_mix(mix_tracks: list[Track]):
    display_rows = []
    prev_bpm_for_delta = None
    for track in mix_tracks:
        delta = None
        if prev_bpm_for_delta is not None and track.bpm is not None:
            delta = track.bpm - prev_bpm_for_delta
        display_rows.append(
            {
                "artist": track.artists,
                "title": track.name,
                "camelot": track.camelot_str,
                "bpm": track.bpm,
                "delta": delta if delta is not None else 0,
                "jump": track.jump,
            }
        )
        prev_bpm_for_delta = track.bpm

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

    current_seed_id = seed_track_id
    fallback_track = None
    master_urls: list[str] = []
    mix_title = random_mix_title(2)

    while True:
        seed_data, related_tracks = fetch_track_and_recommendations(current_seed_id)
        if not seed_data or related_tracks is None:
            print("Unable to fetch track data or recommendations; stopping.")
            break
        seed_info = (
            build_seed_from_data(current_seed_id, seed_data, fallback=fallback_track)
            if fallback_track
            else build_seed(selected, seed_data)
        )

        if seed_info.camelot is None or seed_info.bpm is None:
            print("Seed is missing Camelot key or BPM; cannot build DJ mix order.")
            break

        candidates = build_candidates(related_tracks)
        if not candidates:
            print("No recommendations returned; stopping.")
            break
        mix_tracks = build_mix_order(seed_info, candidates)
        mix_tracks = filter_trends(mix_tracks, min_len=3)
        if not mix_tracks:
            print("No trend segment found with 3+ tracks; stopping.")
            break

        display_mix(mix_tracks)

        url_lines = [t.url for t in mix_tracks]
        if master_urls:
            master_urls.extend(url_lines[1:])  # avoid duplicating the previous last track
        else:
            master_urls.extend(url_lines)

        cont = input("Continue from last track? (y/N): ").strip().lower()
        if cont not in {"y", "yes"}:
            break

        fallback_track = mix_tracks[-1]
        current_seed_id = fallback_track.id

    if master_urls:
        write_playlist_file(mix_title, master_urls)


if __name__ == "__main__":
    main()
