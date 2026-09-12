"""Common helpers for yi-hack cameras."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

import requests
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from requests.auth import HTTPBasicAuth

from .const import (
    CONF_FIRMWARE_VERSION,
    CONF_HACK_NAME,
    CONF_HARDWARE_VERSION,
    CONF_MODEL,
    CONF_SERIAL,
    DEFAULT_BRAND,
    DOMAIN,
    HTTP_TIMEOUT,
)


class YiHackError(Exception):
    """Base exception for communication with a yi-hack camera."""


class YiHackAuthenticationError(YiHackError):
    """Raised when a camera rejects the configured credentials."""


class YiHackConnectionError(YiHackError):
    """Raised when a camera cannot be reached or returns an HTTP error."""


class YiHackInvalidResponseError(YiHackError):
    """Raised when a camera returns an invalid response."""


def build_camera_url(
    config: Mapping[str, Any],
    path: str,
    query: Mapping[str, str] | None = None,
) -> str:
    """Build a camera URL, including brackets around IPv6 literals."""
    host = str(config[CONF_HOST])
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    url = f"http://{host}:{config[CONF_PORT]}/{path.lstrip('/')}"
    if query:
        url = f"{url}?{urlencode(query)}"
    return url


def _auth(config: Mapping[str, Any]) -> HTTPBasicAuth | None:
    """Return basic authentication configured for a camera."""
    username = config.get(CONF_USERNAME, "")
    password = config.get(CONF_PASSWORD, "")
    if username or password:
        return HTTPBasicAuth(username, password)
    return None


def _get_json(config: Mapping[str, Any], path: str) -> dict[str, Any]:
    """Fetch and validate a JSON object from a camera."""
    host = config[CONF_HOST]

    try:
        response = requests.get(
            build_camera_url(config, path),
            timeout=HTTP_TIMEOUT,
            auth=_auth(config),
        )
    except requests.exceptions.RequestException as err:
        raise YiHackConnectionError(f"Unable to connect to camera {host}") from err

    if response.status_code in (401, 403):
        raise YiHackAuthenticationError(f"Authentication failed for camera {host}")
    if response.status_code >= 300:
        raise YiHackConnectionError(
            f"Camera {host} returned HTTP {response.status_code}"
        )

    try:
        payload = response.json()
    except ValueError as err:
        raise YiHackInvalidResponseError(
            f"Camera {host} returned invalid JSON"
        ) from err

    if not isinstance(payload, dict):
        raise YiHackInvalidResponseError(
            f"Camera {host} returned {type(payload).__name__} instead of an object"
        )

    return payload


def get_device_info(config_entry: ConfigEntry) -> DeviceInfo:
    """Build device registry information for a camera."""
    data = config_entry.data
    configuration_url = build_camera_url(data, "").rstrip("/")

    device_info = DeviceInfo(
        name=data[CONF_NAME],
        connections={(CONNECTION_NETWORK_MAC, data[CONF_MAC])},
        identifiers={(DOMAIN, data[CONF_MAC])},
        manufacturer=DEFAULT_BRAND,
        model=data.get(CONF_MODEL, data.get(CONF_HACK_NAME, DOMAIN)),
        configuration_url=configuration_url,
    )

    optional_fields = {
        "serial_number": data.get(CONF_SERIAL),
        "sw_version": data.get(CONF_FIRMWARE_VERSION),
        "hw_version": data.get(CONF_HARDWARE_VERSION),
    }
    for key, value in optional_fields.items():
        if value not in (None, "", "N/A"):
            device_info[key] = value

    return device_info


def get_status(config: Mapping[str, Any]) -> dict[str, Any]:
    """Get system status from a camera."""
    return _get_json(config, "cgi-bin/status.json")


def get_firmware_info(config: Mapping[str, Any]) -> dict[str, Any]:
    """Get installed and available firmware versions from a camera."""
    info = _get_json(config, "cgi-bin/fw_upgrade.sh?get=info")

    if info.get("error") in (True, "true"):
        raise YiHackInvalidResponseError(
            "Camera failed to check for firmware updates: "
            f"{info.get('description', 'unknown error')}"
        )

    return info


def get_system_conf(config: Mapping[str, Any]) -> dict[str, Any]:
    """Get system configuration from a camera."""
    return _get_json(config, "cgi-bin/get_configs.sh?conf=system")


def get_mqtt_conf(config: Mapping[str, Any]) -> dict[str, Any]:
    """Get MQTT configuration from a camera."""
    return _get_json(config, "cgi-bin/get_configs.sh?conf=mqtt")
