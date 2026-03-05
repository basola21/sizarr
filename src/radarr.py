import logging

import requests

import config

logger = logging.getLogger(__name__)


def _get_movie_ids() -> list[int]:
    resp = requests.get(
        f"{config.RADARR_URL}/api/v3/movie",
        headers={"X-Api-Key": config.RADARR_API_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    return [m["id"] for m in resp.json() if m.get("hasFile")]


def get_movie_files() -> list[tuple[str, str]]:
    """Returns list of (path, codec) tuples."""
    try:
        movie_ids = _get_movie_ids()
        files = []
        for movie_id in movie_ids:
            resp = requests.get(
                f"{config.RADARR_URL}/api/v3/moviefile",
                headers={"X-Api-Key": config.RADARR_API_KEY},
                params={"movieId": movie_id},
                timeout=30,
            )
            resp.raise_for_status()
            for f in resp.json():
                path = f["path"]
                codec = f.get("mediaInfo", {}).get("videoCodec", "")
                files.append((path, codec))
        return files
    except requests.RequestException as e:
        logger.error(f"Failed to fetch movie files from Radarr: {e}")
        return []
