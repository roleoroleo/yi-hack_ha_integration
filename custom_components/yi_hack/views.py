"""yi-hack HTTP views."""

from __future__ import annotations

import logging
from http import HTTPStatus
from ipaddress import ip_address
from typing import Any

import aiohttp
from aiohttp import hdrs, web
from aiohttp.helpers import encode_basic_auth
from aiohttp.web_exceptions import HTTPBadGateway
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from multidict import CIMultiDict

from .common import build_camera_url
from .const import (
    CONF_HACK_NAME,
    DOMAIN,
    SONOFF,
)

_LOGGER = logging.getLogger(__name__)


class VideoProxyView(HomeAssistantView):
    """View to handle Video requests."""

    requires_auth = True
    url = "/api/yi-hack/{entry_id}/{dir_path}/{file_path}"
    name = "api:yi-hack:video"

    def __init__(self, hass: HomeAssistant, websession: aiohttp.ClientSession) -> None:
        """Initialize the video proxy view."""
        self.hass = hass
        self._websession = websession

    def _entry_for_identifier(self, identifier: str) -> ConfigEntry | None:
        """Resolve a current entry ID or a legacy camera-name identifier."""
        entry = self.hass.config_entries.async_get_entry(identifier)
        if entry is not None and entry.domain == DOMAIN:
            return entry

        for candidate in self.hass.config_entries.async_entries(DOMAIN):
            if candidate.data.get(CONF_NAME) == identifier:
                return candidate
        return None

    @staticmethod
    def _create_path(config_entry: ConfigEntry, **kwargs: Any) -> str | None:
        """Create and validate a camera recording path."""
        dir_path = str(kwargs["dir_path"])
        file_path = str(kwargs["file_path"])
        if (
            not dir_path
            or not file_path
            or "/" in dir_path
            or "/" in file_path
            or "\\" in dir_path
            or "\\" in file_path
            or dir_path in (".", "..")
            or file_path in (".", "..")
        ):
            return None

        hack_name = config_entry.data.get(CONF_HACK_NAME)
        if hack_name == SONOFF:
            dir_path = dir_path.replace("-", "/")
            if any(part in ("", ".", "..") for part in dir_path.split("/")):
                return None
            return f"alarm_record/{dir_path}/{file_path}"

        return f"record/{dir_path}/{file_path}"

    async def get(
        self,
        request: web.Request,
        **kwargs: Any,
    ) -> web.Response | web.StreamResponse | web.WebSocketResponse:
        """Route data to service."""
        try:
            return await self._handle_request(request, **kwargs)

        except aiohttp.ClientError as err:
            _LOGGER.debug("Reverse proxy error for %s: %s", request.rel_url, err)

        raise HTTPBadGateway() from None

    async def _handle_request(
        self,
        request: web.Request,
        **kwargs: Any,
    ) -> web.Response | web.StreamResponse:
        """Handle route for request."""

        config_entry = self._entry_for_identifier(str(kwargs["entry_id"]))
        if config_entry is None:
            return web.Response(status=HTTPStatus.BAD_REQUEST)

        full_path = self._create_path(config_entry, **kwargs)
        if not full_path:
            return web.Response(status=HTTPStatus.NOT_FOUND)

        user = config_entry.data.get(CONF_USERNAME, "")
        password = config_entry.data.get(CONF_PASSWORD, "")
        url = build_camera_url(config_entry.data, full_path)
        data = await request.read()
        source_header = _init_header(request)

        if user or password:
            source_header[hdrs.AUTHORIZATION] = encode_basic_auth(user, password)

        async with self._websession.request(
            request.method,
            url,
            headers=source_header,
            params=request.query,
            allow_redirects=False,
            data=data,
        ) as result:
            headers = _response_header(result)

            # Stream response
            response = web.StreamResponse(status=result.status, headers=headers)
            response.content_type = result.content_type

            try:
                await response.prepare(request)
                async for chunk in result.content.iter_chunked(4096):
                    await response.write(chunk)

            except (aiohttp.ClientError, aiohttp.ClientPayloadError) as err:
                _LOGGER.debug("Stream error for %s: %s", request.rel_url, err)
            except ConnectionResetError:
                # Connection is reset/closed by peer.
                pass

            return response


def _init_header(request: web.Request) -> CIMultiDict | dict[str, str]:
    """Create initial header."""
    headers = {}

    # Filter flags
    for name, value in request.headers.items():
        if name in (
            hdrs.CONTENT_LENGTH,
            hdrs.CONTENT_ENCODING,
            hdrs.SEC_WEBSOCKET_EXTENSIONS,
            hdrs.SEC_WEBSOCKET_PROTOCOL,
            hdrs.SEC_WEBSOCKET_VERSION,
            hdrs.SEC_WEBSOCKET_KEY,
            hdrs.HOST,
        ):
            continue
        headers[name] = value

    # Set X-Forwarded-For
    forward_for = request.headers.get(hdrs.X_FORWARDED_FOR)
    assert request.transport
    connected_ip = ip_address(request.transport.get_extra_info("peername")[0])
    if forward_for:
        forward_for = f"{forward_for}, {connected_ip!s}"
    else:
        forward_for = f"{connected_ip!s}"
    headers[hdrs.X_FORWARDED_FOR] = forward_for

    # Set X-Forwarded-Host
    forward_host = request.headers.get(hdrs.X_FORWARDED_HOST)
    if not forward_host:
        forward_host = request.host
    headers[hdrs.X_FORWARDED_HOST] = forward_host

    # Set X-Forwarded-Proto
    forward_proto = request.headers.get(hdrs.X_FORWARDED_PROTO)
    if not forward_proto:
        forward_proto = request.url.scheme
    headers[hdrs.X_FORWARDED_PROTO] = forward_proto

    return headers


def _response_header(response: aiohttp.ClientResponse) -> dict[str, str]:
    """Create response header."""
    headers = {}

    for name, value in response.headers.items():
        if name in (
            hdrs.TRANSFER_ENCODING,
            # Removing Content-Length header for streaming responses
            #   prevents seeking from working for mp4 files
            # hdrs.CONTENT_LENGTH,
            hdrs.CONTENT_TYPE,
            hdrs.CONTENT_ENCODING,
        ):
            continue
        headers[name] = value

    return headers
