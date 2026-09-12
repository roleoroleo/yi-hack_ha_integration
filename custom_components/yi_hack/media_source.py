"""yi-hack media source implementation."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
from aiohttp import hdrs
from aiohttp.helpers import encode_basic_auth
from homeassistant.components.media_player import MediaClass, MediaType
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceError,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .common import build_camera_url
from .const import DEFAULT_BRAND, DOMAIN, HTTP_TIMEOUT

MIME_TYPE_MP4 = "video/mp4"
_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> YiHackMediaSource:
    """Set up the yi-hack media source."""
    return YiHackMediaSource(hass)


class YiHackMediaSource(MediaSource):
    """Provide yi-hack camera recordings as media sources."""

    name: str = DEFAULT_BRAND

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the yi-hack source."""
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve media to a Home Assistant proxy URL."""
        entry_id, event_dir, event_file = async_parse_identifier(item)
        if not entry_id or not event_dir or not event_file:
            raise Unresolvable(
                f"Incomplete yi-hack media identifier: {item.identifier}"
            )
        if self._entry_for_identifier(entry_id) is None:
            raise Unresolvable(f"Unknown yi-hack camera: {entry_id}")

        return PlayMedia(
            f"/api/yi-hack/{entry_id}/{event_dir}/{event_file}",
            MIME_TYPE_MP4,
        )

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Browse cameras and their recordings."""
        entry_id, event_dir, event_file = async_parse_identifier(item)
        if event_file is not None:
            raise MediaSourceError(f"Cannot browse a media file: {item.identifier}")

        if entry_id is None:
            return self._build_root()

        config_entry = self._entry_for_identifier(entry_id)
        if config_entry is None:
            raise MediaSourceError(f"Unknown yi-hack camera: {entry_id}")

        if event_dir is None:
            return await self._build_event_directories(config_entry)
        return await self._build_event_files(config_entry, event_dir)

    def _entry_for_identifier(self, identifier: str) -> ConfigEntry | None:
        """Resolve a current entry ID or a legacy camera-name identifier."""
        entry = self.hass.config_entries.async_get_entry(identifier)
        if entry is not None and entry.domain == DOMAIN:
            return entry

        for candidate in self.hass.config_entries.async_entries(DOMAIN):
            if candidate.data.get(CONF_NAME) == identifier:
                return candidate
        return None

    def _entry_title(self, entry: ConfigEntry) -> str:
        """Return the user-selected device name when available."""
        registry = dr.async_get(self.hass)
        devices = dr.async_entries_for_config_entry(registry, entry.entry_id)
        if devices:
            device = next(iter(devices))
            return device.name_by_user or device.name or entry.title
        return entry.title

    def _build_root(self) -> BrowseMediaSource:
        """Build the camera list."""
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier="",
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=DEFAULT_BRAND,
            can_play=False,
            can_expand=True,
            children=[
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=entry.entry_id,
                    media_class=MediaClass.APP,
                    media_content_type=MediaType.VIDEO,
                    title=self._entry_title(entry),
                    can_play=False,
                    can_expand=True,
                )
                for entry in self.hass.config_entries.async_entries(DOMAIN)
            ],
        )

    async def _async_get_records(
        self,
        config_entry: ConfigEntry,
        endpoint: str,
        query: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch and validate a recording list from a camera."""
        data = config_entry.data
        username = data.get(CONF_USERNAME, "")
        password = data.get(CONF_PASSWORD, "")
        headers = None
        if username or password:
            headers = {hdrs.AUTHORIZATION: encode_basic_auth(username, password)}
        session = async_get_clientsession(self.hass)

        try:
            async with session.post(
                build_camera_url(data, endpoint, query),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
            ) as response:
                if response.status in (401, 403):
                    raise MediaSourceError(
                        f"Authentication failed for camera {config_entry.title}"
                    )
                if response.status >= 300:
                    raise MediaSourceError(
                        f"Camera {config_entry.title} returned HTTP {response.status}"
                    )
                payload = await response.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, ValueError) as err:
            raise MediaSourceError(
                f"Unable to browse recordings from camera {config_entry.title}"
            ) from err

        if not isinstance(payload, dict) or not isinstance(
            records := payload.get("records"), list
        ):
            raise MediaSourceError(
                f"Camera {config_entry.title} returned an invalid recording list"
            )

        valid_records = [record for record in records if isinstance(record, dict)]
        if len(valid_records) != len(records):
            _LOGGER.debug(
                "Ignored malformed recording records from camera %s",
                config_entry.title,
            )
        return valid_records

    async def _build_event_directories(
        self, config_entry: ConfigEntry
    ) -> BrowseMediaSource:
        """Build the event-directory list for a camera."""
        media = BrowseMediaSource(
            domain=DOMAIN,
            identifier=config_entry.entry_id,
            media_class=MediaClass.DIRECTORY,
            media_content_type=MediaType.VIDEO,
            title=self._entry_title(config_entry),
            can_play=False,
            can_expand=True,
            children=[],
        )

        records = await self._async_get_records(
            config_entry,
            "cgi-bin/eventsdir.sh",
        )
        for record in records:
            dirname = record.get("dirname")
            if not isinstance(dirname, str) or not dirname:
                continue
            event_dir = dirname.replace("/", "-")
            title = str(record.get("datetime", dirname))
            title = title.replace("Date: ", "").replace("Time: ", "")
            media.children.append(
                BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=f"{config_entry.entry_id}/{event_dir}",
                    media_class=MediaClass.DIRECTORY,
                    media_content_type=MediaType.VIDEO,
                    title=title,
                    can_play=False,
                    can_expand=True,
                )
            )
        return media

    async def _build_event_files(
        self,
        config_entry: ConfigEntry,
        event_dir: str,
    ) -> BrowseMediaSource:
        """Build the recording-file list for an event directory."""
        media = BrowseMediaSource(
            domain=DOMAIN,
            identifier=f"{config_entry.entry_id}/{event_dir}",
            media_class=MediaClass.VIDEO,
            media_content_type=MediaType.VIDEO,
            title=event_dir,
            can_play=False,
            can_expand=True,
            children=[],
        )

        records = await self._async_get_records(
            config_entry,
            "cgi-bin/eventsfile.sh",
            {"dirname": event_dir.replace("-", "/")},
        )
        for record in records:
            filename = record.get("filename")
            if not isinstance(filename, str) or not filename:
                continue
            child = BrowseMediaSource(
                domain=DOMAIN,
                identifier=f"{config_entry.entry_id}/{event_dir}/{filename}",
                media_class=MediaClass.VIDEO,
                media_content_type=MediaType.VIDEO,
                title=str(record.get("time", filename)),
                can_play=True,
                can_expand=False,
            )
            thumbnail = record.get("thumbfilename")
            if isinstance(thumbnail, str) and thumbnail:
                child.thumbnail = (
                    f"/api/yi-hack/{config_entry.entry_id}/{event_dir}/{thumbnail}"
                )
            media.children.append(child)
        return media


@callback
def async_parse_identifier(
    item: MediaSourceItem,
) -> tuple[str | None, str | None, str | None]:
    """Parse a yi-hack media identifier."""
    if not item.identifier:
        return None, None, None

    parts = item.identifier.split("/", 2)
    parts.extend([None] * (3 - len(parts)))
    return parts[0], parts[1], parts[2]
