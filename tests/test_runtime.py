"""Tests for integration-wide runtime resources."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from custom_components.yi_hack import DATA_VIDEO_PROXY, async_setup
from custom_components.yi_hack.const import CONF_HACK_NAME, DOMAIN, SONOFF
from custom_components.yi_hack.views import VideoProxyView

from .conftest import add_config_entry


@pytest.mark.asyncio
async def test_video_proxy_is_registered_once() -> None:
    """Reloading integration-wide setup does not duplicate the global route."""
    hass = SimpleNamespace(data={}, http=SimpleNamespace(register_view=Mock()))
    session = Mock()

    with patch(
        "custom_components.yi_hack.async_get_clientsession",
        return_value=session,
    ):
        assert await async_setup(hass, {})
        assert await async_setup(hass, {})

    hass.http.register_view.assert_called_once()
    assert hass.data[DOMAIN][DATA_VIDEO_PROXY] is True


def test_video_proxy_rejects_parent_paths(hass) -> None:
    """Proxy paths cannot escape a camera's recording directory."""
    entry = add_config_entry(
        hass,
        title="camera",
        unique_id="b4:fb:e3:c0:1c:9f",
        data={
            CONF_HOST: "192.168.1.51",
            CONF_PORT: 80,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
            CONF_HACK_NAME: SONOFF,
        },
    )

    assert VideoProxyView._create_path(entry, dir_path="..", file_path="a.mp4") is None
    assert (
        VideoProxyView._create_path(entry, dir_path="2026-09-01", file_path="..")
        is None
    )
    assert (
        VideoProxyView._create_path(
            entry,
            dir_path="2026-09-01",
            file_path="event.mp4",
        )
        == "alarm_record/2026/09/01/event.mp4"
    )
