"""The yi-hack component."""

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .config import get_mqtt_conf, get_system_conf
from .const import (
    ALLWINNER,
    ALLWINNERV2,
    CONF_AI_HUMAN_DETECTION_START_MSG,
    CONF_AI_HUMAN_DETECTION_STOP_MSG,
    CONF_BABY_CRYING_MSG,
    CONF_BIRTH_MSG,
    CONF_HACK_NAME,
    CONF_MOTION_START_MSG,
    CONF_MOTION_STOP_MSG,
    CONF_MQTT_PREFIX,
    CONF_RTSP_PORT,
    CONF_SERIAL,
    CONF_SOUND_DETECTION_MSG,
    CONF_TOPIC_AI_HUMAN_DETECTION,
    CONF_TOPIC_BABY_CRYING,
    CONF_TOPIC_MOTION_DETECTION,
    CONF_TOPIC_MOTION_DETECTION_IMAGE,
    CONF_TOPIC_SOUND_DETECTION,
    CONF_TOPIC_STATUS,
    CONF_WILL_MSG,
    DOMAIN,
)

PLATFORMS = ["camera", "binary_sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up yi-hack from a config entry."""

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data[CONF_SERIAL]

    conf = await hass.async_add_executor_job(get_system_conf, entry)
    mqtt = await hass.async_add_executor_job(get_mqtt_conf, entry)

    if conf is not None and mqtt is not None:
        updated_data = {
            **entry.data,
            CONF_RTSP_PORT: conf[CONF_RTSP_PORT],
            CONF_MQTT_PREFIX: mqtt[CONF_MQTT_PREFIX],
            CONF_TOPIC_STATUS: mqtt[CONF_TOPIC_STATUS],
            CONF_TOPIC_MOTION_DETECTION: mqtt[CONF_TOPIC_MOTION_DETECTION],
            CONF_TOPIC_BABY_CRYING: mqtt[CONF_TOPIC_BABY_CRYING],
            CONF_MOTION_START_MSG: mqtt[CONF_MOTION_START_MSG],
            CONF_MOTION_STOP_MSG: mqtt[CONF_MOTION_STOP_MSG],
            CONF_BABY_CRYING_MSG: mqtt[CONF_BABY_CRYING_MSG],
            CONF_BIRTH_MSG: mqtt[CONF_BIRTH_MSG],
            CONF_WILL_MSG: mqtt[CONF_WILL_MSG],
            CONF_TOPIC_MOTION_DETECTION_IMAGE: mqtt[CONF_TOPIC_MOTION_DETECTION_IMAGE],
        }
        if (entry.data[CONF_HACK_NAME] == ALLWINNER) or (entry.data[CONF_HACK_NAME] == ALLWINNERV2):
            updated_data.update(**{
                CONF_TOPIC_AI_HUMAN_DETECTION: mqtt[CONF_TOPIC_AI_HUMAN_DETECTION],
                CONF_TOPIC_SOUND_DETECTION: mqtt[CONF_TOPIC_SOUND_DETECTION],
                CONF_AI_HUMAN_DETECTION_START_MSG: mqtt[CONF_AI_HUMAN_DETECTION_START_MSG],
                CONF_AI_HUMAN_DETECTION_STOP_MSG: mqtt[CONF_AI_HUMAN_DETECTION_STOP_MSG],
                CONF_SOUND_DETECTION_MSG: mqtt[CONF_SOUND_DETECTION_MSG],
            })

        hass.config_entries.async_update_entry(entry, data=updated_data)

        for component in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, component)
            )

        return True
    else:
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
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
