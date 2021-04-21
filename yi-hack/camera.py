"""Support for Xiaomi Cameras: yi-hack-MStar, yi-hack-Allwinner and yi-hack-Allwinner-v2."""
import asyncio
import logging
import functools

from haffmpeg.camera import CameraMjpeg
from haffmpeg.tools import IMAGE_JPEG, ImageFrame
import requests
from requests.auth import HTTPBasicAuth

from homeassistant.components import mqtt
from homeassistant.components.camera import Camera
from homeassistant.components.ffmpeg import DATA_FFMPEG, CONF_EXTRA_ARGUMENTS
from homeassistant.const import HTTP_BASIC_AUTHENTICATION
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_PASSWORD,
    CONF_PATH,
    CONF_USERNAME,
    CONF_MAC,
)
from homeassistant.helpers.aiohttp_client import async_aiohttp_proxy_stream
from homeassistant.core import callback

from .const import (
    DOMAIN,
    DEFAULT_BRAND,
    CONF_SERIAL,
    CONF_RTSP_PORT,
    CONF_MQTT_PREFIX,
    CONF_TOPIC_MOTION_DETECTION_IMAGE
)

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:camera"

async def async_setup_entry(hass, config, async_add_entities):
    """Set up a Yi Camera."""
    async_add_entities(
        [
            YiCamera(hass, config),
            YiMqttCamera(hass, config)
        ],
        True
    )

class YiCamera(Camera):
    """Define an implementation of a Yi Camera."""

    def __init__(self, hass, config):
        """Initialize."""
        super().__init__()

        self._extra_arguments = config.data[CONF_EXTRA_ARGUMENTS]
        self._manager = hass.data[DATA_FFMPEG]
        self._device_name = config.data[CONF_NAME]
        self._name = self._device_name + "_cam"
        self._unique_id = self._device_name + "ca__"
        self._mac = config.data[CONF_MAC]
        self._serial_number = config.data[CONF_SERIAL]
        self._is_on = True
        self._host = config.data[CONF_HOST]
        self._port = config.data[CONF_PORT]
        self._rtsp_port = config.data[CONF_RTSP_PORT]
        if self._rtsp_port == 554:
            self._stream_source = "rtsp://" + self._host + "/ch0_0.h264"
        else:
            self._stream_source = "rtsp://" + self._host + ":" + self._rtsp_port + "/ch0_0.h264"
        if self._rtsp_port == 80:
            self._still_image_url = "http://" + self._host + "/cgi-bin/snapshot.sh?res=high&watermark=yes"
        else:
            self._still_image_url = "http://" + self._host + ":" + self._port + "/cgi-bin/snapshot.sh?res=high&watermark=yes"
        self._user = config.data[CONF_USERNAME]
        self._password = config.data[CONF_PASSWORD]

    async def stream_source(self):
        """Return the stream source."""
        return self._stream_source

    async def async_camera_image(self):
        """Return a still image response from the camera."""
        image = None

        if self._still_image_url:
            auth = None
            if self._user or self._password:
                auth = HTTPBasicAuth(self._user, self._password)

            def fetch():
                """Read image from a URL."""
                try:
                    response = requests.get(self._still_image_url, timeout=5, auth=auth)
                    if response.status_code < 300:
                        return response.content
                except requests.exceptions.RequestException as error:
                    _LOGGER.error(
                        "Fetch snapshot image failed from %s, falling back to FFmpeg; %s",
                        self._name,
                        error,
                    )

                return None

            image = await self.hass.async_add_executor_job(fetch)

        if image is None:
            ffmpeg = ImageFrame(self.hass.data[DATA_FFMPEG].binary)
            image = await asyncio.shield(
                ffmpeg.get_image(
                    self._stream_source,
                    output_format=IMAGE_JPEG,
                    extra_cmd=self._extra_arguments
                )
            )

        return image

    async def handle_async_mjpeg_stream(self, request):
        """Generate an HTTP MJPEG stream from the camera."""
        _LOGGER.debug("Handling mjpeg stream from camera '%s'", self._name)

        stream = CameraMjpeg(self._manager.binary)
        await stream.open_camera(
            self._stream_source,
            extra_cmd=self._extra_arguments
        )

        try:
            stream_reader = await stream.get_reader()
            return await async_aiohttp_proxy_stream(
                self.hass,
                request,
                stream_reader,
                self._manager.ffmpeg_stream_content_type,
            )
        finally:
            await stream.close()

    @property
    def brand(self):
        """Camera brand."""
        return DEFAULT_BRAND

    @property
    def name(self):
        """Return the name of the camera."""
        return self._name

    @property
    def is_on(self):
        """Determine whether the camera is on."""
        return self._is_on

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "name": self._device_name,
            "identifiers": {(DOMAIN, self._serial_number)},
            "manufacturer": DEFAULT_BRAND,
            "model": DOMAIN,
        }

class YiMqttCamera(Camera):
    """representation of a MQTT camera."""

    def __init__(self, hass, config):
        """Initialize the MQTT Camera."""
        super().__init__()

        self._hass = hass
        self._device_name = config.data[CONF_NAME]
        self._name = self._device_name  + "_motion_detection_cam"
        self._unique_id = self._device_name + "_camd"
        self._mac = config.data[CONF_MAC]
        self._serial_number = config.data[CONF_SERIAL]
        self._is_on = True
        self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_MOTION_DETECTION_IMAGE]
        self._last_image = None

    async def async_added_to_hass(self):
        """Subscribe to MQTT events."""

        @callback
        def message_received(msg):
            """Handle new MQTT messages."""
            data = msg.payload

            self._last_image = data

        return await mqtt.async_subscribe(
            self.hass, self._state_topic, message_received, 1, None
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe from MQTT events."""

        return await mqtt.async_unsubscribe(
            self.hass, self._state_topic
        )

    async def async_camera_image(self):
        """Return image response."""
        return self._last_image

    @property
    def brand(self):
        """Camera brand."""
        return DEFAULT_BRAND

    @property
    def name(self):
        """Return the name of the camera."""
        return self._name

    @property
    def is_on(self):
        """Determine whether the camera is on."""
        return self._is_on

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "name": self._device_name,
            "identifiers": {(DOMAIN, self._serial_number)},
            "manufacturer": DEFAULT_BRAND,
            "model": DOMAIN,
        }
