from unittest.mock import MagicMock, patch

import pytest
import requests

import radarr


@patch("radarr.requests.get")
def test_get_movie_files_returns_paths(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: [
            {"path": "/data/movies/Inception (2010)/Inception.mkv"},
            {"path": "/data/movies/Dune (2021)/Dune.mkv"},
        ],
    )

    result = radarr.get_movie_files()

    assert result == [
        "/data/movies/Inception (2010)/Inception.mkv",
        "/data/movies/Dune (2021)/Dune.mkv",
    ]


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
def test_get_movie_files_sends_api_key_header(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
    mock_get.return_value.raise_for_status = MagicMock()

    radarr.get_movie_files()

    _, kwargs = mock_get.call_args
    assert "X-Api-Key" in kwargs["headers"]
