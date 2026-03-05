#!/usr/bin/env python3
"""
Encoding benchmark — compares quality settings across available encoders.

Downloads a sample clip automatically, encodes it at various quality levels,
and outputs a chart showing file size vs quality setting.

Usage:
    python benchmark.py                        # auto-download sample + benchmark
    python benchmark.py --input my_clip.mkv    # use your own file
    python benchmark.py --duration 60          # clip length in seconds (default: 60)
    python benchmark.py --encoders libx265     # comma-separated list of encoders
    python benchmark.py --output results.png   # chart output path
"""

import argparse
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

SAMPLE_URL = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
SAMPLE_FILENAME = "bbb.mp4"

# quality values to test for each encoder
QUALITY_RANGE = [18, 20, 22, 24, 26, 28, 30, 32]

ENCODER_CONFIG = {
    "libx265": {
        "flag": "-crf",
        "extra": ["-preset", "fast"],
        "label": "libx265 (CPU)",
    },
    "hevc_nvenc": {
        "flag": "-cq",
        "extra": ["-rc", "vbr"],
        "label": "hevc_nvenc (NVIDIA GPU)",
    },
    "hevc_videotoolbox": {
        "flag": "-q:v",
        "extra": [],
        "label": "hevc_videotoolbox (Apple GPU)",
        # videotoolbox uses 1-100 scale where lower = better, map from CRF-like range
        "quality_map": {18: 20, 20: 30, 22: 40, 24: 50, 26: 60, 28: 70, 30: 80, 32: 90},
    },
}


def detect_encoders() -> list[str]:
    result = subprocess.run(
        ["ffmpeg", "-encoders"],
        capture_output=True,
        text=True,
    )
    available = []
    for name in ENCODER_CONFIG:
        if name in result.stdout:
            available.append(name)
    return available


def download_sample(dest: Path) -> None:
    print(f"Downloading sample clip from Blender...")
    print(f"  {SAMPLE_URL}")

    def progress(count, block_size, total):
        pct = min(count * block_size / total * 100, 100)
        mb = min(count * block_size / 1024 / 1024, total / 1024 / 1024)
        total_mb = total / 1024 / 1024
        print(f"\r  {pct:.0f}%  {mb:.0f}/{total_mb:.0f} MB", end="", flush=True)

    urllib.request.urlretrieve(SAMPLE_URL, dest, reporthook=progress)
    print()


def extract_clip(source: Path, dest: Path, duration: int, start: int = 120) -> None:
    print(f"Extracting {duration}s clip starting at {start}s...")
    # Use mkv container to avoid subtitle compatibility issues (PGS etc can't go in mp4)
    dest = dest.with_suffix(".mkv")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", str(source),
            "-t", str(duration),
            "-c:v", "copy",
            "-c:a", "copy",
            "-sn",          # drop subtitle tracks
            str(dest),
        ],
        capture_output=True,
        check=True,
    )
    return dest


def encode(clip: Path, encoder: str, quality: int, out: Path) -> dict | None:
    cfg = ENCODER_CONFIG[encoder]
    q = cfg.get("quality_map", {}).get(quality, quality)

    cmd = [
        "ffmpeg", "-y",
        "-i", str(clip),
        "-c:v", encoder,
        cfg["flag"], str(q),
        *cfg["extra"],
        "-an",  # skip audio — we're measuring video only
        str(out),
    ]

    start = time.monotonic()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.monotonic() - start

    if result.returncode != 0:
        print(f"    FAILED: {result.stderr[-200:]}")
        return None

    size_mb = out.stat().st_size / 1024 / 1024

    # parse fps from ffmpeg output
    fps = None
    for line in (result.stdout + result.stderr).splitlines():
        m = re.search(r"(\d+(?:\.\d+)?)\s+fps", line)
        if m:
            fps = float(m.group(1))

    return {"size_mb": round(size_mb, 2), "elapsed_s": round(elapsed, 1), "fps": fps}


def run_benchmark(clip: Path, encoders: list[str], workdir: Path) -> dict:
    results = {}

    for encoder in encoders:
        label = ENCODER_CONFIG[encoder]["label"]
        print(f"\n[{label}]")
        results[encoder] = {}

        for q in QUALITY_RANGE:
            out = workdir / f"{encoder}_q{q}.mkv"
            print(f"  quality={q} ...", end=" ", flush=True)
            r = encode(clip, encoder, q, out)
            if r:
                results[encoder][q] = r
                print(f"{r['size_mb']:.1f} MB  {r['elapsed_s']:.0f}s", end="")
                if r["fps"]:
                    print(f"  ({r['fps']:.0f} fps)", end="")
                print()
            else:
                print("skipped")

    return results


def plot(results: dict, original_mb: float, output: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        print("\nmatplotlib not installed — skipping chart. Run: pip install matplotlib")
        print_table(results, original_mb)
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Encoding Benchmark — Quality vs File Size & Speed", fontsize=14, fontweight="bold")

    markers = ["o", "s", "^", "D"]
    colors = ["#2196F3", "#FF5722", "#4CAF50", "#9C27B0"]

    for i, (encoder, data) in enumerate(results.items()):
        if not data:
            continue
        label = ENCODER_CONFIG[encoder]["label"]
        qs = sorted(data.keys())
        sizes = [data[q]["size_mb"] for q in qs]
        speed_qs = [q for q in qs if data[q].get("fps") is not None]
        speeds = [data[q]["fps"] for q in speed_qs]

        ax1.plot(qs, sizes, marker=markers[i], color=colors[i], label=label, linewidth=2)
        if speeds:
            ax2.plot(speed_qs, speeds, marker=markers[i], color=colors[i], label=label, linewidth=2)

    # original size reference line
    ax1.axhline(original_mb, color="gray", linestyle="--", alpha=0.6, label=f"Original ({original_mb:.1f} MB)")

    ax1.set_xlabel("Quality Setting (CRF / CQ)")
    ax1.set_ylabel("Output File Size (MB)")
    ax1.set_title("File Size vs Quality")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax1.invert_xaxis()  # lower CRF = better quality, so invert so left = better

    ax2.set_xlabel("Quality Setting (CRF / CQ)")
    ax2.set_ylabel("Encoding Speed (fps)")
    ax2.set_title("Encoding Speed vs Quality")
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_locator(ticker.MultipleLocator(2))
    ax2.invert_xaxis()

    # add quality direction labels
    for ax in (ax1, ax2):
        ax.annotate("← better quality", xy=(0.02, 0.97), xycoords="axes fraction",
                    fontsize=8, color="gray", va="top")
        ax.annotate("more compressed →", xy=(0.98, 0.97), xycoords="axes fraction",
                    fontsize=8, color="gray", va="top", ha="right")

    plt.tight_layout()
    plt.savefig(output, dpi=150, bbox_inches="tight")
    print(f"\nChart saved to: {output}")

    print_table(results, original_mb)


def print_table(results: dict, original_mb: float) -> None:
    print(f"\n{'Encoder':<30} {'Quality':>8} {'Size MB':>9} {'Reduction':>11} {'Speed fps':>10}")
    print("-" * 72)
    for encoder, data in results.items():
        label = ENCODER_CONFIG[encoder]["label"]
        for q in sorted(data.keys()):
            r = data[q]
            reduction = (1 - r["size_mb"] / original_mb) * 100
            fps = f"{r['fps']:.0f}" if r["fps"] else "—"
            print(f"{label:<30} {q:>8} {r['size_mb']:>9.1f} {reduction:>10.0f}% {fps:>10}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Encoding benchmark")
    parser.add_argument("--input", help="Input video file (downloads sample if omitted)")
    parser.add_argument("--duration", type=int, default=60, help="Clip length in seconds (default: 60)")
    parser.add_argument("--encoders", help="Comma-separated encoders (default: auto-detect)")
    parser.add_argument("--output", default="benchmark.png", help="Chart output path (default: benchmark.png)")
    args = parser.parse_args()

    encoders = args.encoders.split(",") if args.encoders else detect_encoders()
    if not encoders:
        print("No supported encoders found. Install ffmpeg with hevc support.")
        sys.exit(1)

    print(f"Encoders to test: {', '.join(encoders)}")

    with tempfile.TemporaryDirectory(prefix="sizarr_bench_") as tmp:
        workdir = Path(tmp)

        if args.input:
            source = Path(args.input)
        else:
            source = workdir / SAMPLE_FILENAME
            download_sample(source)

        clip = extract_clip(source, workdir / "clip", args.duration)

        original_mb = clip.stat().st_size / 1024 / 1024
        print(f"Clip size: {original_mb:.1f} MB  ({args.duration}s)")

        results = run_benchmark(clip, encoders, workdir)
        plot(results, original_mb, Path(args.output))


if __name__ == "__main__":
    main()
