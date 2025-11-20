# Repository Guidelines

## Project Structure & Module Organization
- Root contains CLI entry `reco.py` plus sample payload `response_example.json`.
- Core code lives in `mixrr/` modules: `env.py` (env loader), `spotify.py` (search/auth/paging), `tunebat.py` (track + rec fetch with retry), `formatting.py` (titles, filenames, display grid), `mixlogic.py` (Camelot/BPM rules, trend filtering), `models.py` (`Track` dataclass).
- `.venv/` should stay uncommitted; `.env` supplies secrets (see `.env-example`).
- Generated playlist files: single file per session, named `<TwoWordTitle>_<timestamp>.txt`, containing only ordered Spotify URLs.

## Build, Test, and Development Commands
- Create venv + install: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` (or ad hoc: `pip install cloudscraper coolname requests`).
- Run interactive flow: `python reco.py` (choose seed, optionally continue to extend the set; writes one playlist file on exit).
- Update dependency lock (if added): `pip freeze > requirements.txt`.

## Coding Style & Naming Conventions
- Python 3.13; 4-space indent; prefer dataclasses (`Track`) for structured data.
- Favor f-strings; avoid hard-coded absolute paths; keep functions small/specific.
- Naming: descriptive verbs for helpers (e.g., `build_mix_order`, `filter_trends`), nouns for models.

## Testing Guidelines
- No test suite present. If adding tests, use `pytest` under `tests/`, named `test_<feature>.py`.
- Mock Spotify/Tunebat HTTP calls; avoid live network in unit tests.
- Add scenarios for Camelot adjacency, BPM tolerance, trend filtering (min 3).

## Commit & Pull Request Guidelines
- Commit messages: present-tense, descriptive (e.g., `Add paginated Spotify search`, `Fix camelot adjacency checks`).
- Keep commits focused and minimal; avoid bundling unrelated changes (e.g., do not mix formatting and feature work).
- Pull requests should include: brief summary of changes, testing performed (`python reco.py` run notes or `pytest`), and any screenshots/text-file samples if output formatting changed.

## Security & Configuration Tips
- Do not commit secrets; `.env` holds `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET`. Rotate if leaked.
- Network calls hit Spotify and Tunebat; avoid spamming APIs and handle failures gracefully.
- Generated playlist files may contain user queries—clean up before publishing or sharing the repo.
