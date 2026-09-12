"""Tests for yi-hack config and discovery flows."""

from ipaddress import ip_address
from unittest.mock import patch

import pytest
from homeassistant.components.ffmpeg import CONF_EXTRA_ARGUMENTS
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.data_entry_flow import AbortFlow, FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from custom_components.yi_hack.common import (
    YiHackAuthenticationError,
    YiHackConnectionError,
)
from custom_components.yi_hack.config_flow import YiHackFlowHandler
from custom_components.yi_hack.const import (
    CONF_BOOST_SPEAKER,
    DEFAULT_EXTRA_ARGUMENTS,
    DOMAIN,
)

from .conftest import add_config_entry


def _flow(hass, source: str = "zeroconf") -> YiHackFlowHandler:
    flow = YiHackFlowHandler()
    flow.hass = hass
    flow.handler = DOMAIN
    flow.context = {"source": source}
    return flow


def _discovery(host: str, mac: str, port: int = 80) -> ZeroconfServiceInfo:
    address = ip_address(host)
    return ZeroconfServiceInfo(
        ip_address=address,
        ip_addresses=[address],
        port=port,
        hostname="yi-camera.local.",
        type="_yi-hack._tcp.local.",
        name="yi-camera._yi-hack._tcp.local.",
        properties={"mac": mac},
    )


def _entry_data(host: str, mac: str) -> dict:
    return {
        CONF_HOST: host,
        CONF_PORT: 80,
        CONF_MAC: mac,
        CONF_USERNAME: "camera",
        CONF_PASSWORD: "secret",
    }


@pytest.mark.asyncio
async def test_zeroconf_aborts_for_all_configured_cameras(hass) -> None:
    """The exact entries reported by the user are not rediscovered."""
    cameras = (
        ("yi_hack_a2_c01c9f", "192.168.1.51", "b4:fb:e3:c0:1c:9f"),
        ("yi_hack_v5_a3028c", "192.168.1.54", "b0:d5:9d:a3:02:8c"),
        ("yi_hack_a2_c067f6", "192.168.1.52", "b4:fb:e3:c0:67:f6"),
    )
    for title, host, mac in cameras:
        add_config_entry(
            hass,
            title=title,
            unique_id=mac,
            data=_entry_data(host, mac),
        )

    for _, host, mac in cameras:
        with pytest.raises(AbortFlow, match="already_configured"):
            await _flow(hass).async_step_zeroconf(_discovery(host, mac))


@pytest.mark.asyncio
async def test_zeroconf_verifies_alternate_advertised_mac(hass) -> None:
    """A camera advertising another interface MAC is identified by status.json."""
    configured_mac = "b4:fb:e3:c0:1c:9f"
    add_config_entry(
        hass,
        title="yi_hack_a2_c01c9f",
        unique_id=configured_mac,
        data=_entry_data("192.168.1.51", configured_mac),
    )

    with (
        patch.object(hass.config_entries._store, "async_delay_save"),
        patch(
            "custom_components.yi_hack.config_flow.get_status",
            return_value={"mac_addr": configured_mac},
        ) as mock_status,
        pytest.raises(AbortFlow, match="already_configured"),
    ):
        await _flow(hass).async_step_zeroconf(
            _discovery("192.168.1.51", "00:11:22:33:44:55", 8080)
        )

    assert mock_status.call_args.args[0][CONF_PORT] == 8080


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception", "expected_error"),
    [
        (YiHackConnectionError(), "cannot_connect"),
        (YiHackAuthenticationError(), "invalid_auth"),
    ],
)
async def test_user_flow_returns_connection_errors(
    hass, exception: Exception, expected_error: str
) -> None:
    """Camera errors redisplay the form instead of returning None."""
    user_input = {
        CONF_HOST: "192.168.1.51",
        CONF_PORT: 80,
        CONF_USERNAME: "camera",
        CONF_PASSWORD: "secret",
        CONF_EXTRA_ARGUMENTS: DEFAULT_EXTRA_ARGUMENTS,
        CONF_BOOST_SPEAKER: "auto",
    }
    with patch(
        "custom_components.yi_hack.config_flow.get_status",
        side_effect=exception,
    ):
        result = await _flow(hass, "user").async_step_user(user_input)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}
