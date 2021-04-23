import logging
import requests

from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
)

from .const import (
    CONF_RTSP_PORT,
    CONF_MQTT_PREFIX,
    CONF_TOPIC_STATUS,
    CONF_TOPIC_MOTION_DETECTION,
    CONF_TOPIC_AI_HUMAN_DETECTION,
    CONF_TOPIC_SOUND_DETECTION,
    CONF_TOPIC_BABY_CRYING,
    CONF_TOPIC_MOTION_DETECTION_IMAGE,
    CONF_DONE,
)

_LOGGER = logging.getLogger(__name__)

async def async_get_conf(hass, config):
    """Get configuration from camera."""
    host = config.data[CONF_HOST]
    port = config.data[CONF_PORT]
    user = config.data[CONF_USERNAME]
    password = config.data[CONF_PASSWORD]
    error = False

    auth = None
    if user or password:
        auth = HTTPBasicAuth(user, password)

    try:
        response = requests.get("http://" + host + ":" + port + "/cgi-bin/get_configs.sh?conf=system", timeout=5, auth=auth)
        if response.status_code >= 300:
            _LOGGER.error("Failed to get configuration from device %s", host)
            error = True
    except requests.exceptions.RequestException as error:
        _LOGGER.error("Failed to get configuration from device %s: error %s", host, error)
        error = True

    if not error and response is not None:
        conf = response.json()

        try:
            response = requests.get("http://" + host + ":" + port + "/cgi-bin/get_configs.sh?conf=mqtt", timeout=5, auth=auth)
            if response.status_code >= 300:
                _LOGGER.error("Failed to get mqtt configuration from device %s", host)
                error = True
        except requests.exceptions.RequestException as error:
            _LOGGER.error("Failed to get mqtt configuration from device %s: error %s", host, error)
            error = True

        if not error and response is not None:
            mqtt = response.json()

            hass.config_entries.async_update_entry(config, data={**config.data, CONF_RTSP_PORT: conf[CONF_RTSP_PORT]})
            hass.config_entries.async_update_entry(config, data={**config.data, CONF_MQTT_PREFIX: mqtt[CONF_MQTT_PREFIX]})
            hass.config_entries.async_update_entry(config, data={**config.data, CONF_TOPIC_STATUS: mqtt[CONF_TOPIC_STATUS]})
            hass.config_entries.async_update_entry(config, data={**config.data, CONF_TOPIC_MOTION_DETECTION: mqtt[CONF_TOPIC_MOTION_DETECTION]})
            hass.config_entries.async_update_entry(config, data={**config.data, CONF_TOPIC_AI_HUMAN_DETECTION: mqtt[CONF_TOPIC_AI_HUMAN_DETECTION]})
            hass.config_entries.async_update_entry(config, data={**config.data, CONF_TOPIC_SOUND_DETECTION: mqtt[CONF_TOPIC_SOUND_DETECTION]})
            hass.config_entries.async_update_entry(config, data={**config.data, CONF_TOPIC_BABY_CRYING: mqtt[CONF_TOPIC_BABY_CRYING]})
            hass.config_entries.async_update_entry(config, data={**config.data, CONF_TOPIC_MOTION_DETECTION_IMAGE: mqtt[CONF_TOPIC_MOTION_DETECTION_IMAGE]})
            hass.config_entries.async_update_entry(config, data={**config.data, CONF_DONE: True})
