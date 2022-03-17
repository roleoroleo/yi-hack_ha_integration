"""yi-hack Media Source Implementation."""
from __future__ import annotations

import datetime as dt
import logging
import requests
from requests.auth import HTTPBasicAuth

from homeassistant.components.media_player.const import (
    MEDIA_CLASS_APP,
    MEDIA_CLASS_DIRECTORY,
    MEDIA_CLASS_VIDEO,
    MEDIA_TYPE_VIDEO,
)
from homeassistant.components.media_player.errors import BrowseError
from homeassistant.components.media_source.error import MediaSourceError, Unresolvable
from homeassistant.components.media_source.models import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant, callback

from .const import DEFAULT_BRAND, DOMAIN, HTTP_TIMEOUT

MIME_TYPE_MP4 = "video/mp4"
_LOGGER = logging.getLogger(__name__)


async def async_get_media_source(hass: HomeAssistant) -> YiHackMediaSource:
    """Set up yi-hack media source."""
    return YiHackMediaSource(hass)


class YiHackMediaSource(MediaSource):
    """Provide yi-hack camera recordings as media sources."""

    name: str = DEFAULT_BRAND

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize yi-hack source."""
        super().__init__(DOMAIN)
        self.hass = hass
        self._devices = []

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Resolve media to a url."""
        entry_id, event_dir, event_file = async_parse_identifier(item)
        if entry_id is None:
            return None
        if event_dir is None:
            return None
        if event_file is None:
            return None

        url = "/api/yi-hack/" + entry_id + "/" + event_dir + "/" + event_file

        return PlayMedia(url, MIME_TYPE_MP4)

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Return media."""
        entry_id, event_dir, event_file = async_parse_identifier(item)

        if len(self._devices) == 0:
            device_registry = await self.hass.helpers.device_registry.async_get_registry()
            for device in device_registry.devices.values():
                if device.identifiers is not None:
                    try:
                        domain = list(list(device.identifiers)[0])[0]
                        if domain == DOMAIN:
                            self._devices.append(device)
                    except IndexError:
                        _LOGGER.warning("Index error about identifier")


        return await self.hass.async_add_executor_job(self._browse_media, entry_id, event_dir)

    def _browse_media(self, entry_id:str, event_dir:str) -> BrowseMediaSource:
        error = False
        host = ""
        port = ""
        user = ""
        password = ""

        if entry_id is None:
            media_class = MEDIA_CLASS_DIRECTORY
            media = BrowseMediaSource(
                domain=DOMAIN,
                identifier="root",
                media_class=media_class,
                media_content_type=MEDIA_TYPE_VIDEO,
                title=DOMAIN,
                can_play=False,
                can_expand=True,
#                thumbnail=thumbnail,
            )
            media.children = []
            for config_entry in self.hass.config_entries.async_entries(DOMAIN):
                title = config_entry.data[CONF_NAME]
                for device in self._devices:
                    if config_entry.data[CONF_NAME] == device.name:
                        title = device.name_by_user if device.name_by_user is not None else device.name

                media_class = MEDIA_CLASS_APP
                child_dev = BrowseMediaSource(
                    domain=DOMAIN,
                    identifier=config_entry.data[CONF_NAME],
                    media_class=media_class,
                    media_content_type=MEDIA_TYPE_VIDEO,
                    title=title,
                    can_play=False,
                    can_expand=True,
#                    thumbnail=thumbnail,
                )
                media.children.append(child_dev)

        elif event_dir is None:
            for config_entry in self.hass.config_entries.async_entries(DOMAIN):
                if config_entry.data[CONF_NAME] == entry_id:
                    host = config_entry.data[CONF_HOST]
                    port = config_entry.data[CONF_PORT]
                    user = config_entry.data[CONF_USERNAME]
                    password = config_entry.data[CONF_PASSWORD]
            if host == "":
                return None

            media_class = MEDIA_CLASS_DIRECTORY
            media = BrowseMediaSource(
                domain=DOMAIN,
                identifier=entry_id,
                media_class=media_class,
                media_content_type=MEDIA_TYPE_VIDEO,
                title=entry_id,
                can_play=False,
                can_expand=True,
#                thumbnail=thumbnail,
            )
            try:
                auth = None
                if user or password:
                    auth = HTTPBasicAuth(user, password)

                eventsdir_url = "http://" + host + ":" + str(port) + "/cgi-bin/eventsdir.sh"
                response = requests.post(eventsdir_url, timeout=HTTP_TIMEOUT, auth=auth)
                if response.status_code >= 300:
                    _LOGGER.error("Failed to send eventsdir command to device %s", host)
                    error = True
            except requests.exceptions.RequestException as error:
                _LOGGER.error("Failed to send eventsdir command to device %s: error %s", host, error)
                error = True

            if response is None:
                _LOGGER.error("Failed to send eventsdir command to device %s: error unknown", host)
                error = True

            if error:
                return None

            records_dir = response.json()["records"]
            if len(records_dir) > 0:
                media.children = []
                for record_dir in records_dir:
                    dir_path = record_dir["dirname"].replace("/", "-")
                    title = record_dir["datetime"].replace("Date: ", "").replace("Time: ", "")
                    media_class = MEDIA_CLASS_DIRECTORY

                    child_dir = BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=entry_id + "/" + dir_path,
                        media_class=media_class,
                        media_content_type=MEDIA_TYPE_VIDEO,
                        title=title,
                        can_play=False,
                        can_expand=True,
#                        thumbnail=thumbnail,
                    )

                    media.children.append(child_dir)

        else:
            for config_entry in self.hass.config_entries.async_entries(DOMAIN):
                if config_entry.data[CONF_NAME] == entry_id:
                    host = config_entry.data[CONF_HOST]
                    port = config_entry.data[CONF_PORT]
                    user = config_entry.data[CONF_USERNAME]
                    password = config_entry.data[CONF_PASSWORD]
            if host == "":
                return None

            title = event_dir
            media_class = MEDIA_CLASS_VIDEO

            media = BrowseMediaSource(
                domain=DOMAIN,
                identifier=entry_id + "/" + event_dir,
                media_class=media_class,
                media_content_type=MEDIA_TYPE_VIDEO,
                title=title,
                can_play=False,
                can_expand=True,
#                thumbnail=thumbnail,
            )

            try:
                auth = None
                if user or password:
                    auth = HTTPBasicAuth(user, password)

                eventsfile_url = "http://" + host + ":" + str(port) + "/cgi-bin/eventsfile.sh?dirname=" + event_dir.replace("-", "/")
                response = requests.post(eventsfile_url, timeout=HTTP_TIMEOUT, auth=auth)
                if response.status_code >= 300:
                    _LOGGER.error("Failed to send eventsfile command to device %s", host)
                    error = True
            except requests.exceptions.RequestException as error:
                _LOGGER.error("Failed to send eventsfile command to device %s: error %s", host, error)
                error = True

            if response is None:
                _LOGGER.error("Failed to send eventsfile command to device %s: error unknown", host)
                error = True

            if error:
                return None

            records_file = response.json()["records"]
            if len(records_file) > 0:
                media.children = []
                for record_file in records_file:
                    file_path = record_file["filename"]
                    try:
                        thumb_path = record_file["thumbfilename"]
                    except KeyError:
                        thumb_path = ""

                    title = record_file["time"]
                    media_class = MEDIA_CLASS_VIDEO

                    child_file = BrowseMediaSource(
                        domain=DOMAIN,
                        identifier=entry_id + "/" + event_dir + "/" + file_path,
                        media_class=media_class,
                        media_content_type=MEDIA_TYPE_VIDEO,
                        title=title,
                        can_play=True,
                        can_expand=False,
                    )
                    if (thumb_path != ""):
                        child_file.thumbnail="/api/yi-hack/" + entry_id + "/" + event_dir + "/" + thumb_path
                    media.children.append(child_file)

        return media


@callback
def async_parse_identifier(
    item: MediaSourceItem,
) -> tuple[str, str, str]:
    """Parse identifier."""
    if not item.identifier:
        return None, None, None
    if "/" not in item.identifier:
        return item.identifier, None, None
    entry, other = item.identifier.split("/", 1)

    if "/" not in other:
        return entry, other, None

    source, path = other.split("/")

    return entry, source, path
