import cloudscraper

TUNEBAT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://tunebat.com",
    "Origin": "https://tunebat.com",
}

# Initialize cloudscraper session
scraper = cloudscraper.create_scraper()


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
