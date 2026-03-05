from unittest.mock import MagicMock, patch

import pytest
import requests

import sonarr


@patch("sonarr.requests.get")
def test_get_episode_files_returns_paths(mock_get):
    mock_get.return_value = MagicMock(
        status_code=200,
        json=lambda: [
            {"path": "/data/tv/Show/S01E01.mkv"},
            {"path": "/data/tv/Show/S01E02.mkv"},
        ],
    )

    result = sonarr.get_episode_files()

    assert result == ["/data/tv/Show/S01E01.mkv", "/data/tv/Show/S01E02.mkv"]


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
    mock_get.return_value = MagicMock(status_code=200, json=lambda: [])
    mock_get.return_value.raise_for_status = MagicMock()

    sonarr.get_episode_files()

    _, kwargs = mock_get.call_args
    assert "X-Api-Key" in kwargs["headers"]
