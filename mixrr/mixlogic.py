import re
from typing import List

from .models import Track


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


def build_mix_order(seed: Track, candidates: List[Track]) -> List[Track]:
    """
    Build an ordered list starting with the seed. We prefer Camelot-adjacent + BPM-close
    tracks; if none fit, we start a new trend (allow a jump) and continue the constraints
    from that new point.
    """
    order: List[Track] = [seed]
    seed.jump = False
    remaining: List[Track] = list(candidates)
    prev = order[0]

    while remaining:
        valid = [
            t
            for t in remaining
            if is_camelot_adjacent(prev.camelot, t.camelot) and bpm_matches(prev.bpm, t.bpm)
        ]

        if valid:
            valid.sort(key=lambda t: abs(t.bpm - prev.bpm))
            chosen = valid[0]
            chosen.jump = False
        else:
            # No smooth option; pick a new "mini-seed" that has the best chance to continue.
            def connectivity_score(track):
                return sum(
                    1
                    for other in remaining
                    if other is not track
                    and is_camelot_adjacent(track.camelot, other.camelot)
                    and bpm_matches(track.bpm, other.bpm)
                )

            best = None
            best_key = None
            for t in remaining:
                connect = connectivity_score(t)
                key = (-connect, abs(t.bpm - prev.bpm))  # prefer more neighbors, then closest BPM jump
                if best is None or key < best_key:
                    best = t
                    best_key = key

            chosen = best
            chosen.jump = True  # trend reset / BPM jump

        order.append(chosen)
        remaining.remove(chosen)
        prev = chosen

    return order


def filter_by_vibe(
    candidates: List[Track],
    seed: Track,
    tol_da: float = 0.2,
    tol_energy: float = 0.2,
) -> List[Track]:
    """
    Keep only tracks whose danceability/energy are close to the seed (if features exist).
    If seed features are missing, returns candidates unchanged.
    """
    if seed.danceability is None and seed.energy is None:
        return candidates

    filtered: List[Track] = []
    for t in candidates:
        ok = True
        if seed.danceability is not None and t.danceability is not None:
            if abs(t.danceability - seed.danceability) > tol_da:
                ok = False
        if seed.energy is not None and t.energy is not None:
            if abs(t.energy - seed.energy) > tol_energy:
                ok = False
        if ok:
            filtered.append(t)
    return filtered


def filter_trends(tracks: List[Track], min_len: int = 3) -> List[Track]:
    """
    Keep only trend segments of length >= min_len.
    A trend starts at index 0, and any track with jump=True starts a new trend.
    """
    if not tracks:
        return []

    segments: List[List[Track]] = []
    current: List[Track] = []
    for idx, t in enumerate(tracks):
        if idx == 0:
            current = [t]
            continue
        if t.jump:
            segments.append(current)
            current = [t]
        else:
            current.append(t)
    segments.append(current)

    filtered = [seg for seg in segments if len(seg) >= min_len]
    if not filtered:
        return []

    # Re-flag jumps after filtering.
    out: List[Track] = []
    for seg_idx, seg in enumerate(filtered):
        for i, t in enumerate(seg):
            t.jump = seg_idx > 0 and i == 0
            out.append(t)
    if out:
        out[0].jump = False
    return out
