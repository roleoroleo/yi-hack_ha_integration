"""Support for output tts to the yi-hack cam."""
from __future__ import annotations

import asyncio
import logging
import subprocess
import threading

import requests
from requests.auth import HTTPBasicAuth
from typing import Any

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    BrowseMedia,
    MediaType,
    MediaPlayerDeviceClass,
    MediaPlayerEnqueue,
    MediaPlayerEntity,
    MediaPlayerEntityFeature
)
from homeassistant.components.media_player.browse_media import (
    async_process_play_media_url
)
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    STATE_IDLE,
    STATE_ON,
    STATE_PLAYING
)
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .const import (
    ALLWINNER,
    ALLWINNERV2,
    CONF_BOOST_SPEAKER,
    CONF_HACK_NAME,
    DEFAULT_BRAND,
    DOMAIN,
    HTTP_TIMEOUT,
    MSTAR
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Yi Camera media player from a config entry."""
    if (config_entry.data[CONF_HACK_NAME] == MSTAR) or (config_entry.data[CONF_HACK_NAME] == ALLWINNER) or (config_entry.data[CONF_HACK_NAME] == ALLWINNERV2):
        async_add_entities([YiHackMediaPlayer(config_entry)], True)


class YiHackMediaPlayer(MediaPlayerEntity):
    """Define an implementation of a Yi Camera media player."""

    _attr_device_class = MediaPlayerDeviceClass.SPEAKER
    _attr_supported_features = (
        MediaPlayerEntityFeature.BROWSE_MEDIA
        | MediaPlayerEntityFeature.PLAY_MEDIA
    )

    def __init__(self, config):
        """Initialize the device."""
        self._device_name = config.data[CONF_NAME]
        self._name = self._device_name + "_media_player"
        self._unique_id = self._device_name + "_mpca"
        self._mac = config.data[CONF_MAC]
        self._host = config.data[CONF_HOST]
        self._port = config.data[CONF_PORT]
        self._user = config.data[CONF_USERNAME]
        self._password = config.data[CONF_PASSWORD]
        self._hack_name = config.data[CONF_HACK_NAME]
        # Assume that the media player is not in Play mode
        self._state = None
        self._playing = threading.Lock()
        try:
            self._boost_speaker = config.data[CONF_BOOST_SPEAKER]
        except KeyError:
            self._boost_speaker = "auto"

    @property
    def brand(self):
        """Camera brand."""
        return DEFAULT_BRAND

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the device."""
        return self._unique_id

    @property
    def state(self):
        """Return the state of the device."""
        if self._state:
            if self._playing.locked():
                return STATE_PLAYING
            else:
                return STATE_IDLE

        return STATE_ON

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "name": self._device_name,
            "connections": {(CONNECTION_NETWORK_MAC, self._mac)},
            "identifiers": {(DOMAIN, self._mac)},
            "manufacturer": DEFAULT_BRAND,
            "model": DOMAIN,
        }

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return False

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        enqueue: MediaPlayerEnqueue | None = None,
        announce: bool | None = None, **kwargs: Any
    ) -> None:
        """Send the play_media command to the media player."""

        def _perform_speaker(data):
            auth = None
            if self._user or self._password:
                auth = HTTPBasicAuth(self._user, self._password)

            self._playing.acquire()

            response = None

            try:
                url_speaker = "http://" + self._host + ":" + str(self._port) + "/cgi-bin/speaker.sh"
                if self._boost_speaker == "auto":
                    if self._hack_name == MSTAR:
                        url_speaker = "http://" + self._host + ":" + str(self._port) + "/cgi-bin/speaker.sh?vol=4";
                    elif self._hack_name == ALLWINNERV2:
                        url_speaker = "http://" + self._host + ":" + str(self._port) + "/cgi-bin/speaker.sh?vol=3";
                elif self._boost_speaker != "disabled":
                    url_speaker = "http://" + self._host + ":" + str(self._port) + "/cgi-bin/speaker.sh?vol=" + str(self._boost_speaker[-1]);

                response = requests.post(url_speaker, data=data, timeout=HTTP_TIMEOUT, headers={'Content-Type': 'application/octet-stream'}, auth=auth)
                if response.status_code >= 300:
                    _LOGGER.error("Failed to send speaker command to device %s", self._host)
            except requests.exceptions.RequestException as error:
                _LOGGER.error("Failed to send speaker command to device %s: error %s", self._host, error)

            if response is None:
                _LOGGER.error("Failed to send speak command to device %s: error unknown", self._host)

            self._playing.release()

        def _perform_cmd(p_cmd):
            return subprocess.run(p_cmd, check=False, shell=False, stdout=subprocess.PIPE).stdout

        if media_source.is_media_source_id(media_id):
            media_type = MediaType.MUSIC
            play_item = await media_source.async_resolve_media(self.hass, media_id)
            media_id = async_process_play_media_url(self.hass, play_item.url)

        if media_type != MediaType.MUSIC:
            _LOGGER.error(
                "Invalid media type %s. Only %s is supported",
                media_type,
                MediaType.MUSIC,
            )
            return

        if self._playing.locked():
            _LOGGER.error("Failed to send speaker command, device %s is busy", self._host)
            return

        cmd = ["ffmpeg", "-i", media_id, "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-"]
        data = await self.hass.async_add_executor_job(_perform_cmd, cmd)

        if data is not None and len(data) > 0:
            await self.hass.async_add_executor_job(_perform_speaker, data)
        else:
            _LOGGER.error("Failed to send data to speaker %s, no data available", self._host)

    async def async_browse_media(
        self,
        media_content_type: str | None = None,
        media_content_id: str | None = None
    ) -> BrowseMedia:
        """Implement the websocket media browsing helper."""
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/"),
        )
