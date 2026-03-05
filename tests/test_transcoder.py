import json
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

import transcoder


FFPROBE_OUTPUT_H264 = json.dumps({
    "streams": [
        {"codec_type": "video", "codec_name": "h264"},
        {"codec_type": "audio", "codec_name": "aac"},
    ]
})

FFPROBE_OUTPUT_HEVC = json.dumps({
    "streams": [
        {"codec_type": "video", "codec_name": "hevc"},
    ]
})

FFPROBE_OUTPUT_AV1 = json.dumps({
    "streams": [
        {"codec_type": "video", "codec_name": "av1"},
    ]
})

FFPROBE_OUTPUT_NO_VIDEO = json.dumps({
    "streams": [
        {"codec_type": "audio", "codec_name": "aac"},
    ]
})


@patch("transcoder.subprocess.run")
def test_get_video_codec_returns_codec(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_H264)

    result = transcoder.get_video_codec("/data/movies/film.mkv")

    assert result == "h264"


@patch("transcoder.subprocess.run")
def test_get_video_codec_returns_empty_on_failure(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

    result = transcoder.get_video_codec("/data/movies/film.mkv")

    assert result == ""


@patch("transcoder.subprocess.run")
def test_get_video_codec_returns_empty_when_no_video_stream(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_NO_VIDEO)

    result = transcoder.get_video_codec("/data/movies/film.mkv")

    assert result == ""


@patch("transcoder.subprocess.run")
def test_transcode_skips_hevc(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_HEVC)

    result = transcoder.transcode("/data/movies/film.mkv")

    assert result is False
    mock_run.assert_called_once()  # only ffprobe, no ffmpeg


@patch("transcoder.subprocess.run")
def test_transcode_skips_av1(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_AV1)

    result = transcoder.transcode("/data/movies/film.mkv")

    assert result is False
    mock_run.assert_called_once()


@patch("transcoder.shutil.move")
@patch("transcoder.subprocess.run")
def test_transcode_h264_calls_ffmpeg(mock_run, mock_move):
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_H264),  # ffprobe
        MagicMock(returncode=0),                              # ffmpeg
    ]

    result = transcoder.transcode("/data/movies/film.mkv")

    assert result is True
    assert mock_run.call_count == 2
    ffmpeg_call = mock_run.call_args_list[1][0][0]
    assert "ffmpeg" in ffmpeg_call
    assert "libx265" in ffmpeg_call


@patch("transcoder.shutil.move")
@patch("transcoder.subprocess.run")
def test_transcode_moves_cache_file_to_original_path(mock_run, mock_move):
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_H264),
        MagicMock(returncode=0),
    ]

    transcoder.transcode("/data/movies/film.mkv")

    src, dst = mock_move.call_args[0]
    assert dst == "/data/movies/film.mkv"


@patch("transcoder.Path.unlink")
@patch("transcoder.subprocess.run")
def test_transcode_cleans_up_cache_on_ffmpeg_failure(mock_run, mock_unlink):
    mock_run.side_effect = [
        MagicMock(returncode=0, stdout=FFPROBE_OUTPUT_H264),
        MagicMock(returncode=1),
    ]

    result = transcoder.transcode("/data/movies/film.mkv")

    assert result is False
    mock_unlink.assert_called_once()


@patch("transcoder.subprocess.run")
def test_transcode_returns_false_when_codec_empty(mock_run):
    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")

    result = transcoder.transcode("/data/movies/film.mkv")

    assert result is False
