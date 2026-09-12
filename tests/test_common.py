"""Tests for camera HTTP helpers."""

from unittest.mock import Mock, patch

import pytest
import requests
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from custom_components.yi_hack.common import (
    YiHackAuthenticationError,
    YiHackConnectionError,
    YiHackInvalidResponseError,
    build_camera_url,
    get_status,
)

CAMERA_CONFIG = {
    CONF_HOST: "192.168.1.51",
    CONF_PORT: 80,
    CONF_USERNAME: "camera",
    CONF_PASSWORD: "secret",
}


def test_build_camera_url_supports_ipv6() -> None:
    """IPv6 literals are enclosed in brackets."""
    config = {**CAMERA_CONFIG, CONF_HOST: "2001:db8::51", CONF_PORT: 8080}

    assert build_camera_url(config, "cgi-bin/status.json") == (
        "http://[2001:db8::51]:8080/cgi-bin/status.json"
    )


@patch("custom_components.yi_hack.common.requests.get")
def test_get_status_returns_json_object(mock_get: Mock) -> None:
    """A valid JSON object is returned to callers."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {"mac_addr": "b4:fb:e3:c0:1c:9f"}

    assert get_status(CAMERA_CONFIG)["mac_addr"] == "b4:fb:e3:c0:1c:9f"


@pytest.mark.parametrize("status", [401, 403])
@patch("custom_components.yi_hack.common.requests.get")
def test_get_status_detects_authentication_errors(mock_get: Mock, status: int) -> None:
    """Authentication failures are distinct from connectivity errors."""
    mock_get.return_value.status_code = status

    with pytest.raises(YiHackAuthenticationError):
        get_status(CAMERA_CONFIG)


@patch("custom_components.yi_hack.common.requests.get")
def test_get_status_rejects_invalid_json(mock_get: Mock) -> None:
    """Malformed camera JSON is reported explicitly."""
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.side_effect = ValueError

    with pytest.raises(YiHackInvalidResponseError):
        get_status(CAMERA_CONFIG)


@patch("custom_components.yi_hack.common.requests.get")
def test_get_status_maps_request_errors(mock_get: Mock) -> None:
    """Requests failures become camera connection errors."""
    mock_get.side_effect = requests.ConnectionError

    with pytest.raises(YiHackConnectionError):
        get_status(CAMERA_CONFIG)
