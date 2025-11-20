# Mixrr DJ Recommender

Interactive CLI to search Spotify, fetch song/rec data, and build a Camelot/BPM-friendly DJ mix. Outputs a single text file of Spotify track URLs when you end the session.

## Setup
- Python 3.13 recommended.
- Create a venv and install deps:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt` (or `pip install cloudscraper coolname requests` if no lockfile).
- Add `.env` with Spotify app creds (Client Credentials flow):
  ```
  SPOTIPY_CLIENT_ID=your_id
  SPOTIPY_CLIENT_SECRET=your_secret
  ```

## Usage
Run the CLI:
```
python reco.py
```
- Enter a song/artist to search Spotify.
- Pick a result (paged navigation: `n`/`p`, `q` to quit, Enter=1).
- The app fetches recommendation data, builds a mix using Camelot-adjacent keys and BPM within 6% (including half/double BPM), and prints the order with key/BPM deltas.
- After each mix segment you can continue (`y`) to seed from the last track and extend the set; only one playlist file is written when you stop.

## Output
- Console: aligned rows `Artist - Title - Camelot - BPM (Δ)` with `[jump to new trend]` markers when a smooth transition wasn’t possible.
- File: `<TwoWordTitle>_<timestamp>.txt` containing only the ordered Spotify track URLs for the full session.
- Trend filter: keeps only segments of length ≥3; one-off or 2-track “micro-trends” are dropped to avoid end-of-list noise.

## Project Structure
- `reco.py` — CLI entrypoint.
- `mixrr/` — modules:
  - `env.py` (load `.env`)
  - `spotify.py` (client creds, search, paginated selection)
  - `rec_api.py` (track + rec fetch with retry; uses the rec API endpoint)
  - `mixlogic.py` (Camelot/BPM rules, trend filtering, mix ordering)
  - `formatting.py` (titles, filenames, display grid)
  - `models.py` (`Track` dataclass)
