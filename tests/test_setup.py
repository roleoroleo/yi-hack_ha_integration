"""Tests for yi-hack config entry setup."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from custom_components.yi_hack import async_setup_entry
from custom_components.yi_hack.common import YiHackAuthenticationError
from custom_components.yi_hack.const import CONF_HACK_NAME, DEFAULT_BRAND

from .conftest import add_config_entry


def _entry(hass):
    return add_config_entry(
        hass,
        title="camera",
        unique_id="b4:fb:e3:c0:1c:9f",
        data={
            CONF_HOST: "192.168.1.51",
            CONF_PORT: 80,
            CONF_USERNAME: "camera",
            CONF_PASSWORD: "secret",
            CONF_HACK_NAME: DEFAULT_BRAND,
        },
    )


def _coordinator() -> Mock:
    coordinator = Mock()
    coordinator.data = {"serial_number": "SN123"}
    coordinator.async_config_entry_first_refresh = AsyncMock()
    return coordinator


@pytest.mark.asyncio
async def test_setup_starts_reauth_for_rejected_credentials(hass) -> None:
    """HTTP authentication failures are not retried as an offline camera."""
    with (
        patch(
            "custom_components.yi_hack.YiHackDataUpdateCoordinator",
            return_value=_coordinator(),
        ),
        patch(
            "custom_components.yi_hack.get_system_conf",
            side_effect=YiHackAuthenticationError,
        ),
        patch("custom_components.yi_hack.get_mqtt_conf", return_value={}),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await async_setup_entry(hass, _entry(hass))


@pytest.mark.asyncio
async def test_setup_retries_incomplete_camera_configuration(hass) -> None:
    """Missing camera configuration keys trigger ConfigEntryNotReady."""
    with (
        patch(
            "custom_components.yi_hack.YiHackDataUpdateCoordinator",
            return_value=_coordinator(),
        ),
        patch("custom_components.yi_hack.get_system_conf", return_value={}),
        patch("custom_components.yi_hack.get_mqtt_conf", return_value={}),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, _entry(hass))
