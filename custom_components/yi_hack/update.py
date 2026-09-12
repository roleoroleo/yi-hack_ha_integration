"""Support for yi-hack firmware update information."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .common import (
    YiHackAuthenticationError,
    YiHackError,
    get_device_info,
    get_firmware_info,
)
from .const import CONF_FIRMWARE_VERSION

SCAN_INTERVAL = timedelta(hours=6)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the yi-hack firmware update entity."""
    async_add_entities([YiHackFirmwareUpdate(config_entry)], True)


class YiHackFirmwareUpdate(UpdateEntity):
    """Report installed and available yi-hack firmware versions."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_has_entity_name = True
    _attr_translation_key = "firmware"

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the firmware update entity."""
        self._config_entry = config_entry
        self._attr_unique_id = f"{config_entry.data[CONF_MAC]}_firmware"
        self._attr_device_info = get_device_info(config_entry)
        self._attr_installed_version = config_entry.data.get(CONF_FIRMWARE_VERSION)
        self._attr_latest_version = self._attr_installed_version

    async def async_update(self) -> None:
        """Fetch firmware update information from the camera."""
        try:
            info = await self.hass.async_add_executor_job(
                get_firmware_info, self._config_entry.data
            )
        except YiHackAuthenticationError:
            self._config_entry.async_start_reauth(self.hass)
            self._attr_available = False
            return
        except YiHackError:
            self._attr_available = False
            return

        installed_version = info.get("fw_version") or self._attr_installed_version
        latest_version = info.get("latest_fw") or installed_version

        self._attr_installed_version = installed_version
        self._attr_latest_version = latest_version
        self._attr_available = installed_version is not None
