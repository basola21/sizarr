import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import transcoder


FFPROBE_OUTPUT_H264 = json.dumps({
    "streams": [
        {"codec_type": "video", "codec_name": "h264", "duration": "3600.0"},
        {"codec_type": "audio", "codec_name": "aac"},
    ]
})

FFPROBE_OUTPUT_HEVC = json.dumps({
    "streams": [{"codec_type": "video", "codec_name": "hevc"}]
})

FFPROBE_OUTPUT_AV1 = json.dumps({
    "streams": [{"codec_type": "video", "codec_name": "av1"}]
})

FFPROBE_OUTPUT_NO_VIDEO = json.dumps({
    "streams": [{"codec_type": "audio", "codec_name": "aac"}]
})

_FAKE_STAT = MagicMock(st_size=1_000_000)


# ── get_video_codec ───────────────────────────────────────────────────────────

@patch("transcoder.subprocess.run")
def test_get_video_codec_returns_codec(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_H264)

    assert transcoder.get_video_codec("/data/movies/film.mkv") == "h264"


@patch("transcoder.subprocess.run")
def test_get_video_codec_returns_empty_on_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

    assert transcoder.get_video_codec("/data/movies/film.mkv") == ""


@patch("transcoder.subprocess.run")
def test_get_video_codec_returns_empty_when_no_video_stream(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_NO_VIDEO)

    assert transcoder.get_video_codec("/data/movies/film.mkv") == ""


# ── transcode: codec provided (no ffprobe) ───────────────────────────────────

@patch("transcoder.shutil.move")
@patch("transcoder.subprocess.run")
def test_transcode_skips_when_codec_provided_as_hevc(mock_run, mock_move):
    result = transcoder.transcode("/data/movies/film.mkv", codec="HEVC")

    assert result is None
    mock_run.assert_not_called()  # no ffprobe, no ffmpeg


@patch("transcoder.shutil.move")
@patch("transcoder.subprocess.run")
def test_transcode_skips_when_codec_provided_as_x265(mock_run, mock_move):
    result = transcoder.transcode("/data/movies/film.mkv", codec="x265")

    assert result is None
    mock_run.assert_not_called()


@patch("pathlib.Path.stat", return_value=_FAKE_STAT)
@patch("transcoder.shutil.move")
@patch("transcoder.subprocess.run")
def test_transcode_calls_ffmpeg_when_codec_provided_as_x264(mock_run, mock_move, mock_stat):
    mock_run.return_value = MagicMock(returncode=0)

    result = transcoder.transcode("/data/movies/film.mkv", codec="x264")

    assert result is not None
    assert result["codec_before"] == "x264"
    assert result["size_before"] == 1_000_000
    assert result["size_after"] == 1_000_000
    mock_run.assert_called_once()  # only ffmpeg, no ffprobe
    ffmpeg_call = mock_run.call_args[0][0]
    assert "ffmpeg" in ffmpeg_call
    assert "libx265" in ffmpeg_call


# ── transcode: no codec provided (falls back to ffprobe) ─────────────────────

@patch("transcoder.subprocess.run")
def test_transcode_skips_hevc_via_ffprobe(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_HEVC)

    result = transcoder.transcode("/data/movies/film.mkv")

    assert result is None
    mock_run.assert_called_once()  # only ffprobe


@patch("transcoder.subprocess.run")
def test_transcode_skips_av1_via_ffprobe(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_AV1)

    result = transcoder.transcode("/data/movies/film.mkv")

    assert result is None
    mock_run.assert_called_once()


@patch("pathlib.Path.stat", return_value=_FAKE_STAT)
@patch("transcoder.shutil.move")
@patch("transcoder.subprocess.run")
def test_transcode_h264_via_ffprobe_calls_ffmpeg(mock_run, mock_move, mock_stat):
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_H264),
        MagicMock(returncode=0),
    ]

    result = transcoder.transcode("/data/movies/film.mkv")

    assert result is not None
    assert result["codec_before"] == "h264"
    assert result["duration_seconds"] == 3600.0
    assert mock_run.call_count == 2


# ── transcode: error handling ─────────────────────────────────────────────────

@patch("pathlib.Path.stat", return_value=_FAKE_STAT)
@patch("transcoder.shutil.move")
@patch("transcoder.subprocess.run")
def test_transcode_moves_cache_file_to_original_path(mock_run, mock_move, mock_stat):
    mock_run.return_value = MagicMock(returncode=0)

    transcoder.transcode("/data/movies/film.mkv", codec="x264")

    _, dst = mock_move.call_args[0]
    assert dst == "/data/movies/film.mkv"


@patch("pathlib.Path.stat", return_value=_FAKE_STAT)
@patch("transcoder.Path.unlink")
@patch("transcoder.subprocess.run")
def test_transcode_cleans_up_cache_on_ffmpeg_failure(mock_run, mock_unlink, mock_stat):
    mock_run.return_value = MagicMock(returncode=1)

    result = transcoder.transcode("/data/movies/film.mkv", codec="x264")

    assert result is None
    mock_unlink.assert_called_once()


@patch("transcoder.subprocess.run")
def test_transcode_returns_false_when_codec_empty(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

    result = transcoder.transcode("/data/movies/film.mkv")

    assert result is None
