import os
import sys


def _require(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        print(f"ERROR: required env var {name} is not set", file=sys.stderr)
        sys.exit(1)
    return value


SONARR_URL = _require("SONARR_URL")
SONARR_API_KEY = _require("SONARR_API_KEY")
RADARR_URL = _require("RADARR_URL")
RADARR_API_KEY = _require("RADARR_API_KEY")

CACHE_PATH = os.environ.get("CACHE_PATH", "/cache")
SCHEDULE = os.environ.get("SCHEDULE", "0 2 * * *")  # 2am daily by default
CPU_THREADS = int(os.environ.get("CPU_THREADS", "2"))
CRF = int(os.environ.get("CRF", "20"))
PRESET = os.environ.get("PRESET", "slow")
