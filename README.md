# sizarr

Simple automated transcoder for Sonarr/Radarr libraries. Converts h264 → h265 on a schedule using FFmpeg, reducing file sizes by ~40-50% without quality loss.

## How it works

1. Queries Sonarr and Radarr APIs for all media file paths
2. Checks each file's codec with ffprobe
3. Skips files already in h265, av1, or vp9
4. Transcodes the rest to h265 in a cache directory, then moves them back in place

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `SONARR_URL` | yes | — | e.g. `http://sonarr:8989` |
| `SONARR_API_KEY` | yes | — | Sonarr API key |
| `RADARR_URL` | yes | — | e.g. `http://radarr:7878` |
| `RADARR_API_KEY` | yes | — | Radarr API key |
| `CACHE_PATH` | no | `/cache` | Temp directory for in-progress transcodes |
| `SCHEDULE` | no | `0 2 * * *` | Cron expression (default: 2am daily) |
| `CPU_THREADS` | no | `2` | FFmpeg thread count |
| `CRF` | no | `20` | Quality level (18–24 recommended, lower = better) |
| `PRESET` | no | `slow` | FFmpeg preset (`slow` = better compression, `fast` = quicker) |

## Usage

```bash
# Build
docker build -t sizarr .

# Run
docker compose -f docker-compose.example.yml up -d
```

## Development

```bash
pip install -r requirements.txt
pytest tests/ -v
```
# sizarr
