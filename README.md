# sizarr

Simple automated transcoder for Sonarr/Radarr libraries. Converts h264 → h265 on a schedule using FFmpeg, reducing file sizes by ~40-50% without quality loss.

## How it works

1. Queries Sonarr and Radarr APIs for all media file paths
2. Checks each file's codec with ffprobe
3. Skips files already in h265, av1, or vp9
4. Transcodes the rest to h265 in a cache directory, then moves them back in place
5. Tracks transcoded files in a SQLite database to avoid re-encoding on the next run

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `SONARR_URL` | yes | — | e.g. `http://sonarr:8989` |
| `SONARR_API_KEY` | yes | — | Sonarr API key |
| `RADARR_URL` | yes | — | e.g. `http://radarr:7878` |
| `RADARR_API_KEY` | yes | — | Radarr API key |
| `CACHE_PATH` | no | `/cache` | Temp directory for in-progress transcodes |
| `SCHEDULE` | no | `0 2 * * *` | Cron expression (default: 2am daily) |
| `USE_GPU` | no | `false` | Use NVIDIA GPU (hevc_nvenc) instead of CPU (libx265) |
| `CRF` | no | `20` | Quality level — see quality guide below |
| `PRESET` | no | `slow` | CPU preset (`slow` = better compression, `fast` = quicker) |
| `CPU_THREADS` | no | `2` | FFmpeg thread count (CPU mode only) |

## Usage

```bash
# Build
docker build -t sizarr .

# Run
docker compose -f docker-compose.example.yml up -d
```

## Tips

### Set the correct user (PUID/PGID)

sizarr moves transcoded files back in place, so it must run as the same user that owns your media files. Without this, you'll get permission errors.

Find your user/group IDs:
```bash
id $USER
# uid=1000(youruser) gid=1000(yourgroup)
```

Then set them in docker-compose:
```yaml
sizarr:
  image: basola21/sizarr:latest
  user: "1000:1000"  # match the owner of your /data files
```

Or use variables from your `.env`:
```yaml
sizarr:
  image: basola21/sizarr:latest
  user: "${PUID}:${PGID}"
```

### Transcoding quality

**GPU (NVIDIA hevc_nvenc)**

nvenc uses a CQ (Constant Quality) scale where higher = smaller files (opposite of CRF for x265):
- `CQ=20` — very high quality, minimal size reduction
- `CQ=28` — good balance of quality and compression (recommended)
- `CQ=35` — aggressive compression, visible quality loss on some content

```yaml
environment:
  - USE_GPU=true
  - CRF=28  # nvenc CQ value
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

**CPU (libx265)**

x265 CRF scale where lower = better quality:
- `CRF=18` — near-lossless, large files
- `CRF=22` — good quality, ~40% size reduction (recommended)
- `CRF=28` — noticeable quality loss, very small files

```yaml
environment:
  - USE_GPU=false
  - CRF=22
  - PRESET=slow       # slow preset = better compression at same CRF
  - CPU_THREADS=4     # increase if your CPU has spare cores
```

### GPU prerequisites

To use `USE_GPU=true`, the host must have:
1. NVIDIA drivers installed
2. [nvidia-container-toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed and Docker runtime configured

Verify GPU access before enabling:
```bash
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
```

### Cache volume

Use a separate volume for `CACHE_PATH` (default `/cache`) to avoid filling your media disk with in-progress transcodes. The SQLite tracking database is also stored here.

```yaml
volumes:
  - /data:/data
  - /transcode_cache:/cache
```

## Development

```bash
pip install -r requirements.txt
pytest tests/ -v
```
