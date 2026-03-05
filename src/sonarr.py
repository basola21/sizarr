import logging

import requests

import config

logger = logging.getLogger(__name__)


def get_episode_files() -> list[str]:
    try:
        resp = requests.get(
            f"{config.SONARR_URL}/api/v3/episodefile",
            headers={"X-Api-Key": config.SONARR_API_KEY},
            timeout=30,
        )
        resp.raise_for_status()
        return [f["path"] for f in resp.json()]
    except requests.RequestException as e:
        logger.error(f"Failed to fetch episode files from Sonarr: {e}")
        return []
