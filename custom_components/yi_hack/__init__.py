"""The yi_hack component."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant

from .common import get_mqtt_conf, get_system_conf
from .const import (ALLWINNER, ALLWINNERV2, CONF_BABY_CRYING_MSG,
                    CONF_BIRTH_MSG, CONF_HACK_NAME, CONF_MOTION_START_MSG,
                    CONF_MOTION_STOP_MSG, CONF_MQTT_PREFIX, CONF_RTSP_PORT,
                    CONF_SOUND_DETECTION_MSG, CONF_TOPIC_BABY_CRYING,
                    CONF_TOPIC_MOTION_DETECTION,
                    CONF_TOPIC_MOTION_DETECTION_IMAGE,
                    CONF_TOPIC_SOUND_DETECTION, CONF_TOPIC_STATUS,
                    CONF_WILL_MSG, DEFAULT_BRAND, DOMAIN, END_OF_POWER_OFF,
                    END_OF_POWER_ON, MSTAR, SONOFF, V5)

PLATFORMS = ["camera", "binary_sensor", "media_player", "switch"]
PLATFORMS_NOMEDIA = ["camera", "binary_sensor", "switch"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up yi-hack from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data[CONF_MAC]
    hass.data[DOMAIN][entry.data[CONF_NAME]] = None
    hass.data[DOMAIN][entry.data[CONF_NAME] + END_OF_POWER_OFF] = None
    hass.data[DOMAIN][entry.data[CONF_NAME] + END_OF_POWER_ON] = None

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
                CONF_TOPIC_BABY_CRYING: mqtt[CONF_TOPIC_BABY_CRYING],
                CONF_BABY_CRYING_MSG: mqtt[CONF_BABY_CRYING_MSG],
            })
        elif (entry.data[CONF_HACK_NAME] == ALLWINNER) or (entry.data[CONF_HACK_NAME] == ALLWINNERV2) or (entry.data[CONF_HACK_NAME] == V5):
            updated_data.update(**{
                CONF_RTSP_PORT: conf[CONF_RTSP_PORT],
                CONF_TOPIC_BABY_CRYING: mqtt[CONF_TOPIC_BABY_CRYING],
                CONF_TOPIC_SOUND_DETECTION: mqtt[CONF_TOPIC_SOUND_DETECTION],
                CONF_BABY_CRYING_MSG: mqtt[CONF_BABY_CRYING_MSG],
                CONF_SOUND_DETECTION_MSG: mqtt[CONF_SOUND_DETECTION_MSG],
            })
        elif entry.data[CONF_HACK_NAME] == SONOFF:
            updated_data.update(**{
                CONF_RTSP_PORT: conf[CONF_RTSP_PORT],
            })

        hass.config_entries.async_update_entry(entry, data=updated_data)

        if (entry.data[CONF_HACK_NAME] == SONOFF) or (entry.data[CONF_HACK_NAME] == V5):
            for component in PLATFORMS_NOMEDIA:
                hass.async_create_task(
                    hass.config_entries.async_forward_entry_setup(entry, component)
                )
        else:
            for component in PLATFORMS:
                hass.async_create_task(
                    hass.config_entries.async_forward_entry_setup(entry, component)
                )

        return True
    else:
        _LOGGER.error("Unable to get configuration from the cam")
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    if (entry.data[CONF_HACK_NAME] == SONOFF) or (entry.data[CONF_HACK_NAME] == V5):
        unload_ok = all(
            await asyncio.gather(
                *[
                    hass.config_entries.async_forward_entry_unload(entry, component)
                    for component in PLATFORMS_NOMEDIA
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
