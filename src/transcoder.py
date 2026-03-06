import json
import logging
import shutil
import subprocess
from pathlib import Path

import config

logger = logging.getLogger(__name__)

SKIP_CODECS = {"hevc", "x265", "av1", "vp9"}


def _probe_video(path: str) -> tuple[str, float | None]:
    """Return (codec_name, duration_seconds) for the first video stream."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(f"ffprobe failed for {path}: {result.stderr}")
        return "", None
    data = json.loads(result.stdout)
    codec = ""
    duration: float | None = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            codec = stream.get("codec_name", "")
            if "duration" in stream:
                duration = float(stream["duration"])
            break
    if duration is None:
        fmt_dur = data.get("format", {}).get("duration")
        if fmt_dur:
            duration = float(fmt_dur)
    return codec, duration


def get_video_codec(path: str) -> str:
    codec, _ = _probe_video(path)
    return codec


def transcode(path: str, codec: str = "") -> dict | None:
    duration_seconds: float | None = None

    if codec:
        resolved_codec = codec.lower()
    else:
        resolved_codec, duration_seconds = _probe_video(path)

    if not resolved_codec:
        return None

    if resolved_codec in SKIP_CODECS:
        logger.info(f"Skipping {path} (already {resolved_codec})")
        return None

    input_path = Path(path)
    size_before = input_path.stat().st_size
    cache_file = Path(config.CACHE_PATH) / input_path.name

    logger.info(f"Transcoding {path} ({resolved_codec} → h265)...")

    use_gpu = config.USE_GPU
    video_codec = "hevc_nvenc" if use_gpu else "libx265"
    extra_args = (
        ["-rc", "vbr", "-cq", str(config.GPU_CQ), "-preset", config.GPU_PRESET, "-rc-lookahead", "32", "-bf", "4"]
        if use_gpu
        else ["-crf", str(config.CRF), "-preset", config.PRESET, "-threads", str(config.CPU_THREADS)]
    )

    result = subprocess.run([
        "ffmpeg", "-i", str(input_path),
        "-map", "0:v:0",
        "-map", "0:a",
        "-map", "0:s",
        "-c:v", video_codec,
        *extra_args,
        "-c:a", "copy",
        "-c:s", "copy",
        "-y", str(cache_file),
    ])

    if result.returncode != 0:
        logger.error(f"FFmpeg failed for {path}")
        cache_file.unlink(missing_ok=True)
        return None

    shutil.move(str(cache_file), str(input_path))
    size_after = input_path.stat().st_size
    logger.info(f"Done: {path}")

    return {
        "size_before": size_before,
        "size_after": size_after,
        "codec_before": resolved_codec,
        "duration_seconds": duration_seconds,
    }
