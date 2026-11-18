"""Tests for the yi-hack media source."""

import asyncio
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from aiohttp import web
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


@asynccontextmanager
async def _camera_server(handler):
    """Serve the eventsdir.sh endpoint on localhost and yield its port."""
    app = web.Application()
    app.router.add_post("/cgi-bin/eventsdir.sh", handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    try:
        yield runner.addresses[0][1]
    finally:
        await runner.cleanup()


def _local_entry(hass, port: int):
    return add_config_entry(
        hass,
        title="Front door",
        unique_id="b4:fb:e3:c0:1c:9f",
        data={
            CONF_HOST: "127.0.0.1",
            CONF_PORT: port,
            CONF_USERNAME: "",
            CONF_PASSWORD: "",
            CONF_NAME: "yi_hack_a2_c01c9f",
        },
    )


@pytest.mark.asyncio
async def test_slow_recording_list_is_not_capped_by_total_time(hass) -> None:
    """A list that keeps streaming is read in full, however long it takes.

    The camera script prints one folder at a time and needs far longer than
    HTTP_TIMEOUT for a full SD card, but it never pauses that long.
    """
    records = 6

    async def handler(request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(headers={"Content-Type": "application/json"})
        await response.prepare(request)
        await response.write(b'{"records":[\n')
        for index in range(records):
            await asyncio.sleep(0.15)
            separator = b"," if index else b""
            await response.write(
                separator
                + json.dumps(
                    {"dirname": f"2026Y09M01D{index:02d}H", "datetime": "x"}
                ).encode()
            )
        await response.write(b"]}\n")
        return response

    async with _camera_server(handler) as port:
        entry = _local_entry(hass, port)
        source = YiHackMediaSource(hass)
        async with aiohttp.ClientSession() as session:
            with (
                patch("custom_components.yi_hack.media_source.HTTP_TIMEOUT", 0.5),
                patch(
                    "custom_components.yi_hack.media_source.async_get_clientsession",
                    return_value=session,
                ),
            ):
                result = await source._async_get_records(entry, "cgi-bin/eventsdir.sh")

    assert len(result) == records


@pytest.mark.asyncio
async def test_stalled_recording_list_still_times_out(hass) -> None:
    """A camera that goes silent for HTTP_TIMEOUT is still reported as an error."""
    release = asyncio.Event()

    async def handler(request: web.Request) -> web.StreamResponse:
        response = web.StreamResponse(headers={"Content-Type": "application/json"})
        await response.prepare(request)
        await response.write(b'{"records":[\n')
        await release.wait()
        return response

    async with _camera_server(handler) as port:
        entry = _local_entry(hass, port)
        source = YiHackMediaSource(hass)
        try:
            async with aiohttp.ClientSession() as session:
                with (
                    patch("custom_components.yi_hack.media_source.HTTP_TIMEOUT", 0.5),
                    patch(
                        "custom_components.yi_hack.media_source.async_get_clientsession",
                        return_value=session,
                    ),
                    pytest.raises(MediaSourceError, match="Unable to browse recordings"),
                ):
                    # Well below the overall limit: only the per-read limit can
                    # end the request in time.
                    async with asyncio.timeout(5):
                        await source._async_get_records(entry, "cgi-bin/eventsdir.sh")
        finally:
            release.set()
