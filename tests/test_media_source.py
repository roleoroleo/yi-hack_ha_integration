"""Tests for the yi-hack media source."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.components.media_source import MediaSourceError, MediaSourceItem
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)

from custom_components.yi_hack.media_source import YiHackMediaSource

from .conftest import add_config_entry


def _entry(hass):
    return add_config_entry(
        hass,
        title="Front door",
        unique_id="b4:fb:e3:c0:1c:9f",
        data={
            CONF_HOST: "192.168.1.51",
            CONF_PORT: 80,
            CONF_USERNAME: "camera",
            CONF_PASSWORD: "secret",
            CONF_NAME: "yi_hack_a2_c01c9f",
        },
    )


@pytest.mark.asyncio
async def test_browse_media_stays_on_event_loop(hass) -> None:
    """Home Assistant registries are not accessed from an executor thread."""
    entry = _entry(hass)
    source = YiHackMediaSource(hass)
    item = MediaSourceItem(hass, "yi_hack", entry.entry_id, None)

    with (
        patch.object(source, "_entry_title", return_value="Front door"),
        patch.object(
            source,
            "_async_get_records",
            AsyncMock(
                return_value=[
                    {
                        "dirname": "2026/09/01",
                        "datetime": "Date: 2026/09/01 Time: 12:00",
                    }
                ]
            ),
        ),
        patch.object(
            hass,
            "async_add_executor_job",
            side_effect=AssertionError("unexpected executor call"),
        ),
    ):
        result = await source.async_browse_media(item)

    assert result.children[0].identifier == f"{entry.entry_id}/2026-09-01"


class _Response:
    status = 200

    async def json(self, *, content_type=None):
        return {"records": "not-a-list"}


class _RequestContext:
    async def __aenter__(self):
        return _Response()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Session:
    def post(self, *args, **kwargs):
        return _RequestContext()


@pytest.mark.asyncio
async def test_browse_media_rejects_invalid_record_list(hass) -> None:
    """Malformed camera JSON is exposed as a media-source error."""
    entry = _entry(hass)
    source = YiHackMediaSource(hass)

    with (
        patch(
            "custom_components.yi_hack.media_source.async_get_clientsession",
            return_value=_Session(),
        ),
        pytest.raises(MediaSourceError, match="invalid recording list"),
    ):
        await source._async_get_records(entry, "cgi-bin/eventsdir.sh")
