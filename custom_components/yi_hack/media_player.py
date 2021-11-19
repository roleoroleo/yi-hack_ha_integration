"""Support for output tts to the yi-hack cam."""

import asyncio
import logging
import subprocess

import requests
from requests.auth import HTTPBasicAuth

from homeassistant.components.media_player import (DEVICE_CLASS_SPEAKER,
                                                   MediaPlayerEntity)
from homeassistant.components.media_player.const import (MEDIA_TYPE_MUSIC,
                                                         SUPPORT_PLAY_MEDIA,
                                                         SUPPORT_TURN_OFF,
                                                         SUPPORT_TURN_ON)
from homeassistant.const import (CONF_HOST, CONF_MAC, CONF_NAME, CONF_PASSWORD,
                                 CONF_PORT, CONF_USERNAME, STATE_IDLE,
                                 STATE_OFF, STATE_ON, STATE_PLAYING)
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .common import (get_privacy, set_power_off_in_progress,
                     set_power_on_in_progress, set_privacy)
from .const import (ALLWINNER, ALLWINNERV2, CONF_BOOST_SPEAKER, CONF_HACK_NAME,
                    DEFAULT_BRAND, DOMAIN, HTTP_TIMEOUT, MSTAR)

SUPPORT_YIHACK_MEDIA = (
    SUPPORT_PLAY_MEDIA
    | SUPPORT_TURN_OFF
    | SUPPORT_TURN_ON
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Yi Camera media player from a config entry."""
    if (config_entry.data[CONF_HACK_NAME] == MSTAR) or (config_entry.data[CONF_HACK_NAME] == ALLWINNER) or (config_entry.data[CONF_HACK_NAME] == ALLWINNERV2):
        async_add_entities([YiHackMediaPlayer(config_entry)], True)


class YiHackMediaPlayer(MediaPlayerEntity):
    """Define an implementation of a Yi Camera media player."""

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
        self._playing = False
        try:
            self._boost_speaker = config.data[CONF_BOOST_SPEAKER]
        except KeyError:
            self._boost_speaker = "auto"

    def update(self):
        """Return the state of the media player (privacy off = state on)."""
        self._state = not get_privacy(self.hass, self._device_name)

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
            if self._playing:
                return STATE_PLAYING
            else:
                return STATE_IDLE

        return STATE_OFF

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

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_YIHACK_MEDIA

    @property
    def device_class(self):
        """Set the device class to SPEAKER."""
        return DEVICE_CLASS_SPEAKER

    def turn_off(self):
        """Turn off camera (set privacy on)."""
        conf = dict([
            (CONF_HOST, self._host),
            (CONF_PORT, self._port),
            (CONF_USERNAME, self._user),
            (CONF_PASSWORD, self._password),
        ])
        if not get_privacy(self.hass, self._device_name):
            _LOGGER.debug("Turn off camera %s", self._name)
            set_power_on_in_progress(self.hass, self._device_name)
            set_privacy(self.hass, self._device_name, True, conf)

    def turn_on(self):
        """Turn on camera (set privacy off)."""
        conf = dict([
            (CONF_HOST, self._host),
            (CONF_PORT, self._port),
            (CONF_USERNAME, self._user),
            (CONF_PASSWORD, self._password),
        ])
        if get_privacy(self.hass, self._device_name):
            _LOGGER.debug("Turn on Camera %s", self._name)
            set_power_off_in_progress(self.hass)
            set_privacy(self.hass, self._device_name, False, conf)

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Send the play_media command to the media player."""

        def _perform_speaker(data):
            auth = None
            if self._user or self._password:
                auth = HTTPBasicAuth(self._user, self._password)

            self._playing = True

            try:
                response = requests.post("http://" + self._host + ":" + str(self._port) + "/cgi-bin/speaker.sh", data=data, timeout=HTTP_TIMEOUT, headers={'Content-Type': 'application/octet-stream'}, auth=auth)
                if response.status_code >= 300:
                    _LOGGER.error("Failed to send speaker command to device %s", self._host)
            except requests.exceptions.RequestException as error:
                _LOGGER.error("Failed to send speaker command to device %s: error %s", self._host, error)

            if response is None:
                _LOGGER.error("Failed to send speak command to device %s: error unknown", self._host)

            self._playing = False

        def _perform_cmd(p_cmd):
            return subprocess.run(p_cmd, check=False, shell=False, stdout=subprocess.PIPE).stdout

        if media_type != MEDIA_TYPE_MUSIC:
            _LOGGER.error(
                "Invalid media type %s. Only %s is supported",
                media_type,
                MEDIA_TYPE_MUSIC,
            )
            return

        if self._playing:
            _LOGGER.error("Failed to send speaker command, device %s is busy", self._host)
            return

        cmd = ["ffmpeg", "-i", media_id, "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-"]
        if self._boost_speaker == "auto":
            if self._hack_name == MSTAR:
                cmd = ["ffmpeg", "-i", media_id, "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-filter:a", "volume=4", "-"]
            elif self._hack_name == ALLWINNERV2:
                cmd = ["ffmpeg", "-i", media_id, "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-filter:a", "volume=3", "-"]
        elif self._boost_speaker != "disabled":
            cmd = ["ffmpeg", "-i", media_id, "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-filter:a", "volume=" + str(self._boost_speaker[-1]), "-"]
        data = await self.hass.async_add_executor_job(_perform_cmd, cmd)

        if data is not None and len(data) > 0:
            await self.hass.async_add_executor_job(_perform_speaker, data)
        else:
            _LOGGER.error("Failed to send data to speaker %s, no data available", self._host)
