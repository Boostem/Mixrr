import re
from datetime import datetime
from pathlib import Path

from coolname import generate


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


def random_mix_title(words: int = 2) -> str:
    """Generate a short 1-2 word title (adjective + noun)."""
    parts = generate(words)
    parts = parts[:words]
    return " ".join(word.capitalize() for word in parts)


def write_playlist_file(random_title: str, lines: list[str]):
    timestamp_str = human_timestamp(datetime.now())
    filename = f"{random_title}_{timestamp_str}.txt"
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
