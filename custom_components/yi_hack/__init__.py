"""The yi_hack component."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .common import get_mqtt_conf, get_status, get_system_conf
from .const import (ALLWINNER, ALLWINNERV2, CONF_ANIMAL_DETECTION_MSG,
                    CONF_BABY_CRYING_MSG, CONF_BIRTH_MSG, CONF_HACK_NAME,
                    CONF_HUMAN_DETECTION_MSG, CONF_MOTION_START_MSG,
                    CONF_MOTION_STOP_MSG, CONF_MQTT_PREFIX, CONF_RTSP_PORT,
                    CONF_SOUND_DETECTION_MSG, CONF_TOPIC_MOTION_DETECTION,
                    CONF_TOPIC_MOTION_DETECTION_IMAGE,
                    CONF_TOPIC_SOUND_DETECTION, CONF_TOPIC_STATUS,
                    CONF_VEHICLE_DETECTION_MSG, CONF_WILL_MSG, DEFAULT_BRAND,
                    DOMAIN, MSTAR, SONOFF, V5)

from .views import VideoProxyView

PLATFORMS = ["camera", "binary_sensor", "media_player", "select", "switch"]
PLATFORMS_SO = ["camera", "binary_sensor", "select", "switch"]
PLATFORMS_V5 = ["camera", "binary_sensor", "switch"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up yi-hack from a config entry."""

    device_name=entry.data[CONF_NAME]

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][device_name] = {}

    stat = await hass.async_add_executor_job(get_status, entry.data)

    if stat is not None:
        try:
            privacy = stat["privacy"]
            _LOGGER.error("Unsupported hack version (" + entry.data[CONF_HOST] + "), please update your cam")
            return False
        except KeyError:
            privacy = None

    conf = await hass.async_add_executor_job(get_system_conf, entry.data)
    mqtt = await hass.async_add_executor_job(get_mqtt_conf, entry.data)

    if conf is not None and mqtt is not None:
        updated_data = {
            **entry.data,
            CONF_MQTT_PREFIX: mqtt[CONF_MQTT_PREFIX],
            CONF_TOPIC_STATUS: mqtt[CONF_TOPIC_STATUS],
            CONF_TOPIC_MOTION_DETECTION: mqtt[CONF_TOPIC_MOTION_DETECTION],
            CONF_MOTION_START_MSG: mqtt[CONF_MOTION_START_MSG],
            CONF_MOTION_STOP_MSG: mqtt[CONF_MOTION_STOP_MSG],
            CONF_BIRTH_MSG: mqtt[CONF_BIRTH_MSG],
            CONF_WILL_MSG: mqtt[CONF_WILL_MSG],
            CONF_TOPIC_MOTION_DETECTION_IMAGE: mqtt[CONF_TOPIC_MOTION_DETECTION_IMAGE],
        }
        if (entry.data[CONF_HACK_NAME] == DEFAULT_BRAND) or (entry.data[CONF_HACK_NAME] == MSTAR):
            updated_data.update(**{
                CONF_RTSP_PORT: conf[CONF_RTSP_PORT],
                CONF_BABY_CRYING_MSG: mqtt[CONF_BABY_CRYING_MSG],
            })
        elif (entry.data[CONF_HACK_NAME] == ALLWINNER) or (entry.data[CONF_HACK_NAME] == V5):
            updated_data.update(**{
                CONF_RTSP_PORT: conf[CONF_RTSP_PORT],
                CONF_TOPIC_SOUND_DETECTION: mqtt[CONF_TOPIC_SOUND_DETECTION],
                CONF_HUMAN_DETECTION_MSG: mqtt[CONF_HUMAN_DETECTION_MSG],
                CONF_VEHICLE_DETECTION_MSG: mqtt[CONF_VEHICLE_DETECTION_MSG],
                CONF_ANIMAL_DETECTION_MSG: mqtt[CONF_ANIMAL_DETECTION_MSG],
                CONF_SOUND_DETECTION_MSG: mqtt[CONF_SOUND_DETECTION_MSG],
            })
        elif (entry.data[CONF_HACK_NAME] == ALLWINNERV2):
            updated_data.update(**{
                CONF_RTSP_PORT: conf[CONF_RTSP_PORT],
                CONF_TOPIC_SOUND_DETECTION: mqtt[CONF_TOPIC_SOUND_DETECTION],
                CONF_HUMAN_DETECTION_MSG: mqtt[CONF_HUMAN_DETECTION_MSG],
                CONF_VEHICLE_DETECTION_MSG: mqtt[CONF_VEHICLE_DETECTION_MSG],
                CONF_ANIMAL_DETECTION_MSG: mqtt[CONF_ANIMAL_DETECTION_MSG],
                CONF_SOUND_DETECTION_MSG: mqtt[CONF_SOUND_DETECTION_MSG],
            })
        elif entry.data[CONF_HACK_NAME] == SONOFF:
            updated_data.update(**{
                CONF_RTSP_PORT: conf[CONF_RTSP_PORT],
            })

        hass.config_entries.async_update_entry(entry, data=updated_data)

        if (entry.data[CONF_HACK_NAME] == V5):
            for component in PLATFORMS_V5:
                hass.async_create_task(
                    hass.config_entries.async_forward_entry_setup(entry, component)
                )
        elif (entry.data[CONF_HACK_NAME] == SONOFF):
            for component in PLATFORMS_SO:
                hass.async_create_task(
                    hass.config_entries.async_forward_entry_setup(entry, component)
                )
        else:
            for component in PLATFORMS:
                hass.async_create_task(
                    hass.config_entries.async_forward_entry_setup(entry, component)
                )

        session = async_get_clientsession(hass)
        hass.http.register_view(VideoProxyView(hass, session))

        return True
    else:
        _LOGGER.error("Unable to get configuration from the cam")
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    if (entry.data[CONF_HACK_NAME] == V5):
        unload_ok = all(
            await asyncio.gather(
                *[
                    hass.config_entries.async_forward_entry_unload(entry, component)
                    for component in PLATFORMS_V5
                ]
            )
        )
    elif (entry.data[CONF_HACK_NAME] == SONOFF):
        unload_ok = all(
            await asyncio.gather(
                *[
                    hass.config_entries.async_forward_entry_unload(entry, component)
                    for component in PLATFORMS_SONOFF
                ]
            )
        )
    else:
        unload_ok = all(
            await asyncio.gather(
                *[
                    hass.config_entries.async_forward_entry_unload(entry, component)
                    for component in PLATFORMS
                ]
            )
        )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
