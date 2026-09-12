"""The yi-hack integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .common import (
    YiHackAuthenticationError,
    YiHackError,
    get_mqtt_conf,
    get_system_conf,
)
from .const import (
    ALLWINNER,
    ALLWINNERV2,
    CONF_ANIMAL_DETECTION_MSG,
    CONF_BABY_CRYING_MSG,
    CONF_BIRTH_MSG,
    CONF_FIRMWARE_VERSION,
    CONF_HACK_NAME,
    CONF_HARDWARE_VERSION,
    CONF_HUMAN_DETECTION_MSG,
    CONF_MODEL,
    CONF_MOTION_START_MSG,
    CONF_MOTION_STOP_MSG,
    CONF_MQTT_PREFIX,
    CONF_RTSP_PORT,
    CONF_SERIAL,
    CONF_SOUND_DETECTION_MSG,
    CONF_TOPIC_MOTION_DETECTION,
    CONF_TOPIC_MOTION_DETECTION_IMAGE,
    CONF_TOPIC_SOUND_DETECTION,
    CONF_TOPIC_STATUS,
    CONF_VEHICLE_DETECTION_MSG,
    CONF_WILL_MSG,
    DATA_COORDINATOR,
    DEFAULT_BRAND,
    DOMAIN,
    MSTAR,
    SONOFF,
    V5,
)
from .coordinator import YiHackDataUpdateCoordinator
from .views import VideoProxyView

PLATFORMS = [
    "button",
    "camera",
    "binary_sensor",
    "media_player",
    "select",
    "sensor",
    "switch",
    "update",
]
PLATFORMS_SONOFF = [
    "button",
    "camera",
    "binary_sensor",
    "select",
    "sensor",
    "switch",
    "update",
]
PLATFORMS_V5 = [
    "button",
    "camera",
    "binary_sensor",
    "select",
    "sensor",
    "switch",
    "update",
]

DATA_VIDEO_PROXY = "video_proxy_registered"
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up integration-wide resources."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get(DATA_VIDEO_PROXY):
        hass.http.register_view(VideoProxyView(hass, async_get_clientsession(hass)))
        domain_data[DATA_VIDEO_PROXY] = True
    return True


def _updated_entry_data(
    entry: ConfigEntry,
    status: dict[str, Any],
    system_conf: dict[str, Any],
    mqtt_conf: dict[str, Any],
) -> dict[str, Any]:
    """Build entry data and validate values required by the camera variant."""
    hack_name = entry.data.get(CONF_HACK_NAME, DEFAULT_BRAND)
    updated_data = {
        **entry.data,
        CONF_MQTT_PREFIX: mqtt_conf[CONF_MQTT_PREFIX],
        CONF_TOPIC_STATUS: mqtt_conf[CONF_TOPIC_STATUS],
        CONF_TOPIC_MOTION_DETECTION: mqtt_conf[CONF_TOPIC_MOTION_DETECTION],
        CONF_MOTION_START_MSG: mqtt_conf[CONF_MOTION_START_MSG],
        CONF_MOTION_STOP_MSG: mqtt_conf[CONF_MOTION_STOP_MSG],
        CONF_BIRTH_MSG: mqtt_conf[CONF_BIRTH_MSG],
        CONF_WILL_MSG: mqtt_conf[CONF_WILL_MSG],
        CONF_TOPIC_MOTION_DETECTION_IMAGE: mqtt_conf[CONF_TOPIC_MOTION_DETECTION_IMAGE],
        CONF_RTSP_PORT: system_conf[CONF_RTSP_PORT],
    }

    status_metadata = {
        CONF_FIRMWARE_VERSION: status.get("fw_version"),
        CONF_HARDWARE_VERSION: status.get("hardware_id"),
        CONF_MODEL: status.get("model_suffix") or status.get("model"),
        CONF_SERIAL: status.get("serial_number"),
    }
    updated_data.update(
        {
            key: value
            for key, value in status_metadata.items()
            if value not in (None, "", "N/A")
        }
    )

    if hack_name == DEFAULT_BRAND:
        updated_data[CONF_BABY_CRYING_MSG] = mqtt_conf[CONF_BABY_CRYING_MSG]
    elif hack_name in (V5, MSTAR):
        updated_data.update(
            {
                CONF_TOPIC_SOUND_DETECTION: mqtt_conf[CONF_TOPIC_SOUND_DETECTION],
                CONF_BABY_CRYING_MSG: mqtt_conf[CONF_BABY_CRYING_MSG],
                CONF_SOUND_DETECTION_MSG: mqtt_conf[CONF_SOUND_DETECTION_MSG],
            }
        )
    elif hack_name in (ALLWINNER, ALLWINNERV2):
        updated_data.update(
            {
                CONF_TOPIC_SOUND_DETECTION: mqtt_conf[CONF_TOPIC_SOUND_DETECTION],
                CONF_HUMAN_DETECTION_MSG: mqtt_conf[CONF_HUMAN_DETECTION_MSG],
                CONF_VEHICLE_DETECTION_MSG: mqtt_conf[CONF_VEHICLE_DETECTION_MSG],
                CONF_ANIMAL_DETECTION_MSG: mqtt_conf[CONF_ANIMAL_DETECTION_MSG],
                CONF_SOUND_DETECTION_MSG: mqtt_conf[CONF_SOUND_DETECTION_MSG],
            }
        )

    return updated_data


def _platforms_for_entry(entry: ConfigEntry) -> list[str]:
    """Return platforms supported by the configured camera variant."""
    hack_name = entry.data.get(CONF_HACK_NAME, DEFAULT_BRAND)
    if hack_name == V5:
        return PLATFORMS_V5
    if hack_name == SONOFF:
        return PLATFORMS_SONOFF
    return PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up yi-hack from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    coordinator = YiHackDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    status = coordinator.data

    if "privacy" in status:
        raise ConfigEntryError(
            f"Unsupported hack version on camera {entry.data[CONF_HOST]}"
        )

    try:
        system_conf, mqtt_conf = await asyncio.gather(
            hass.async_add_executor_job(get_system_conf, entry.data),
            hass.async_add_executor_job(get_mqtt_conf, entry.data),
        )
        updated_data = _updated_entry_data(
            entry,
            status,
            system_conf,
            mqtt_conf,
        )
    except YiHackAuthenticationError as err:
        raise ConfigEntryAuthFailed from err
    except (KeyError, TypeError, YiHackError) as err:
        raise ConfigEntryNotReady(
            f"Unable to get configuration from camera at {entry.data[CONF_HOST]}"
        ) from err

    hass.config_entries.async_update_entry(entry, data=updated_data)
    hass.data[DOMAIN][entry.entry_id] = {DATA_COORDINATOR: coordinator}

    await hass.config_entries.async_forward_entry_setups(
        entry,
        _platforms_for_entry(entry),
    )

    async def async_request_initial_status() -> None:
        """Ask the camera to publish its state once MQTT is ready."""
        await asyncio.sleep(10)
        await mqtt.async_publish(
            hass,
            f"{mqtt_conf[CONF_MQTT_PREFIX]}/cmnd/camera",
            "",
            1,
            0,
        )

    entry.async_create_background_task(
        hass,
        async_request_initial_status(),
        f"{DOMAIN} initial MQTT status",
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        _platforms_for_entry(entry),
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok
