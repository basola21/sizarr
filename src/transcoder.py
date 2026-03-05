import json
import logging
import shutil
import subprocess
from pathlib import Path

import config

logger = logging.getLogger(__name__)

SKIP_CODECS = {"hevc", "x265", "av1", "vp9"}


def get_video_codec(path: str) -> str:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(f"ffprobe failed for {path}: {result.stderr}")
        return ""
    for stream in json.loads(result.stdout).get("streams", []):
        if stream.get("codec_type") == "video":
            return stream.get("codec_name", "")
    return ""


def transcode(path: str, codec: str = "") -> bool:
    resolved_codec = codec.lower() if codec else get_video_codec(path)
    if not resolved_codec:
        return False

    if resolved_codec in SKIP_CODECS:
        logger.info(f"Skipping {path} (already {resolved_codec})")
        return False

    input_path = Path(path)
    cache_file = Path(config.CACHE_PATH) / input_path.name

    logger.info(f"Transcoding {path} ({resolved_codec} → h265)...")

    use_gpu = config.USE_GPU
    video_codec = "hevc_nvenc" if use_gpu else "libx265"
    extra_args = ["-rc", "vbr", "-cq", str(config.CRF)] if use_gpu else ["-crf", str(config.CRF), "-preset", config.PRESET, "-threads", str(config.CPU_THREADS)]

    result = subprocess.run([
        "ffmpeg", "-i", str(input_path),
        "-c:v", video_codec,
        *extra_args,
        "-c:a", "copy",
        "-c:s", "copy",
        "-y", str(cache_file),
    ])

    if result.returncode != 0:
        logger.error(f"FFmpeg failed for {path}")
        cache_file.unlink(missing_ok=True)
        return False

    shutil.move(str(cache_file), str(input_path))
    logger.info(f"Done: {path}")
    return True
