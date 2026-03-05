from unittest.mock import MagicMock, patch

import requests

import sonarr


def _make_response(json_data):
    m = MagicMock()
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    return m


@patch("sonarr.requests.get")
def test_get_episode_files_returns_paths_and_codecs(mock_get):
    mock_get.side_effect = [
        _make_response([{"id": 1}, {"id": 2}]),
        _make_response([{"path": "/data/tv/Show/S01E01.mkv", "mediaInfo": {"videoCodec": "x264"}}]),
        _make_response([{"path": "/data/tv/Show/S01E02.mkv", "mediaInfo": {"videoCodec": "HEVC"}}]),
    ]

    result = sonarr.get_episode_files()

    assert result == [
        ("/data/tv/Show/S01E01.mkv", "x264"),
        ("/data/tv/Show/S01E02.mkv", "HEVC"),
    ]


@patch("sonarr.requests.get")
def test_get_episode_files_handles_missing_media_info(mock_get):
    mock_get.side_effect = [
        _make_response([{"id": 1}]),
        _make_response([{"path": "/data/tv/Show/S01E01.mkv"}]),  # no mediaInfo
    ]

    result = sonarr.get_episode_files()

    assert result == [("/data/tv/Show/S01E01.mkv", "")]


@patch("sonarr.requests.get")
def test_get_episode_files_returns_empty_on_http_error(mock_get):
    mock_get.side_effect = requests.RequestException("connection refused")

    result = sonarr.get_episode_files()

    assert result == []


@patch("sonarr.requests.get")
def test_get_episode_files_returns_empty_on_non_200(mock_get):
    mock_get.return_value = MagicMock(
        raise_for_status=MagicMock(side_effect=requests.HTTPError("403"))
    )

    result = sonarr.get_episode_files()

    assert result == []


@patch("sonarr.requests.get")
def test_get_episode_files_sends_api_key_header(mock_get):
    mock_get.side_effect = [
        _make_response([{"id": 1}]),
        _make_response([]),
    ]

    sonarr.get_episode_files()

    for c in mock_get.call_args_list:
        _, kwargs = c
        assert "X-Api-Key" in kwargs["headers"]


@patch("sonarr.requests.get")
def test_get_episode_files_queries_each_series(mock_get):
    mock_get.side_effect = [
        _make_response([{"id": 10}, {"id": 20}]),
        _make_response([]),
        _make_response([]),
    ]

    sonarr.get_episode_files()

    assert mock_get.call_count == 3
