import logging

import requests

import config

logger = logging.getLogger(__name__)


def _get_series_ids() -> list[int]:
    resp = requests.get(
        f"{config.SONARR_URL}/api/v3/series",
        headers={"X-Api-Key": config.SONARR_API_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    return [s["id"] for s in resp.json()]


def get_episode_files() -> list[tuple[str, str]]:
    """Returns list of (path, codec) tuples."""
    try:
        series_ids = _get_series_ids()
        files = []
        for series_id in series_ids:
            resp = requests.get(
                f"{config.SONARR_URL}/api/v3/episodefile",
                headers={"X-Api-Key": config.SONARR_API_KEY},
                params={"seriesId": series_id},
                timeout=30,
            )
            resp.raise_for_status()
            for f in resp.json():
                path = f["path"]
                codec = f.get("mediaInfo", {}).get("videoCodec", "")
                files.append((path, codec))
        return files
    except requests.RequestException as e:
        logger.error(f"Failed to fetch episode files from Sonarr: {e}")
        return []
