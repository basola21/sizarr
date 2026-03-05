import logging

import requests

import config

logger = logging.getLogger(__name__)


def get_movie_files() -> list[str]:
    try:
        resp = requests.get(
            f"{config.RADARR_URL}/api/v3/moviefile",
            headers={"X-Api-Key": config.RADARR_API_KEY},
            timeout=30,
        )
        resp.raise_for_status()
        return [f["path"] for f in resp.json()]
    except requests.RequestException as e:
        logger.error(f"Failed to fetch movie files from Radarr: {e}")
        return []
