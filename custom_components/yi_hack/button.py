"""Support for yi-hack camera buttons."""

from __future__ import annotations

import logging

import requests
from homeassistant.components.button import ButtonDeviceClass, ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from requests.auth import HTTPBasicAuth

from .common import get_device_info
from .const import HTTP_TIMEOUT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the yi-hack camera buttons."""
    async_add_entities([YiHackRestartButton(config_entry)])


class YiHackRestartButton(ButtonEntity):
    """Button that restarts a yi-hack camera."""

    _attr_device_class = ButtonDeviceClass.RESTART
    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_translation_key = "restart"

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the restart button."""
        self._host = config_entry.data[CONF_HOST]
        self._port = config_entry.data[CONF_PORT]
        self._username = config_entry.data[CONF_USERNAME]
        self._password = config_entry.data[CONF_PASSWORD]

        self._attr_unique_id = f"{config_entry.data[CONF_MAC]}_restart"
        self._attr_device_info = get_device_info(config_entry)

    def press(self) -> None:
        """Restart the camera."""
        auth = None
        if self._username or self._password:
            auth = HTTPBasicAuth(self._username, self._password)

        try:
            response = requests.get(
                f"http://{self._host}:{self._port}/cgi-bin/reboot.sh",
                timeout=HTTP_TIMEOUT,
                auth=auth,
            )
            if response.status_code >= 300:
                _LOGGER.error("Failed to send restart command to device %s", self._host)
        except requests.exceptions.RequestException as error:
            _LOGGER.error(
                "Failed to send restart command to device %s: %s",
                self._host,
                error,
            )
