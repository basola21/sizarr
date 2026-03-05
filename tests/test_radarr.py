from unittest.mock import MagicMock, patch

import requests

import radarr


def _make_response(json_data):
    m = MagicMock()
    m.json.return_value = json_data
    m.raise_for_status = MagicMock()
    return m


@patch("radarr.requests.get")
def test_get_movie_files_returns_paths_and_codecs(mock_get):
    mock_get.side_effect = [
        _make_response([{"id": 1, "hasFile": True}, {"id": 2, "hasFile": True}]),
        _make_response([{"path": "/data/movies/Inception.mkv", "mediaInfo": {"videoCodec": "x264"}}]),
        _make_response([{"path": "/data/movies/Dune.mkv", "mediaInfo": {"videoCodec": "HEVC"}}]),
    ]

    result = radarr.get_movie_files()

    assert result == [
        ("/data/movies/Inception.mkv", "x264"),
        ("/data/movies/Dune.mkv", "HEVC"),
    ]


@patch("radarr.requests.get")
def test_get_movie_files_skips_movies_without_file(mock_get):
    mock_get.side_effect = [
        _make_response([{"id": 1, "hasFile": True}, {"id": 2, "hasFile": False}]),
        _make_response([{"path": "/data/movies/Inception.mkv", "mediaInfo": {"videoCodec": "x264"}}]),
    ]

    result = radarr.get_movie_files()

    assert len(result) == 1
    assert mock_get.call_count == 2  # 1 movie call + 1 moviefile call (not 2)


@patch("radarr.requests.get")
def test_get_movie_files_returns_empty_on_http_error(mock_get):
    mock_get.side_effect = requests.RequestException("timeout")

    result = radarr.get_movie_files()

    assert result == []


@patch("radarr.requests.get")
def test_get_movie_files_returns_empty_on_non_200(mock_get):
    mock_get.return_value = MagicMock(
        raise_for_status=MagicMock(side_effect=requests.HTTPError("401"))
    )

    result = radarr.get_movie_files()

    assert result == []


@patch("radarr.requests.get")
def test_get_movie_files_handles_missing_media_info(mock_get):
    mock_get.side_effect = [
        _make_response([{"id": 1, "hasFile": True}]),
        _make_response([{"path": "/data/movies/Inception.mkv"}]),  # no mediaInfo
    ]

    result = radarr.get_movie_files()

    assert result == [("/data/movies/Inception.mkv", "")]


@patch("radarr.requests.get")
def test_get_movie_files_sends_api_key_header(mock_get):
    mock_get.side_effect = [
        _make_response([{"id": 1, "hasFile": True}]),
        _make_response([]),
    ]

    radarr.get_movie_files()

    for c in mock_get.call_args_list:
        _, kwargs = c
        assert "X-Api-Key" in kwargs["headers"]
