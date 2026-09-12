"""Diagnostic sensors for yi-hack cameras."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .common import get_device_info
from .const import (
    ALLWINNER,
    ALLWINNERV2,
    CONF_HACK_NAME,
    DATA_COORDINATOR,
    DOMAIN,
    MSTAR,
    SONOFF,
)
from .coordinator import YiHackDataUpdateCoordinator

SENSOR_WIFI_QUALITY = "wifi_quality"
SENSOR_STORAGE_FREE = "storage_free"
SENSOR_UPTIME = "uptime"

RAW_WIFI_QUALITY_HACKS = {MSTAR, ALLWINNER, ALLWINNERV2, SONOFF}


def _number(value: Any) -> float | None:
    """Convert a camera status value to a number."""
    if value in (None, "", "N/A"):
        return None

    try:
        return float(str(value).strip().rstrip("%"))
    except (TypeError, ValueError):
        return None


def _percentage(value: Any) -> int | None:
    """Convert a camera percentage value to a bounded integer."""
    number = _number(value)
    if number is None:
        return None
    return round(max(0, min(100, number)))


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up yi-hack diagnostic sensors."""
    coordinator: YiHackDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        DATA_COORDINATOR
    ]
    async_add_entities(
        [
            YiHackStatusSensor(coordinator, config_entry, SENSOR_WIFI_QUALITY),
            YiHackStatusSensor(coordinator, config_entry, SENSOR_STORAGE_FREE),
            YiHackStatusSensor(coordinator, config_entry, SENSOR_UPTIME),
        ],
    )


class YiHackStatusSensor(CoordinatorEntity[YiHackDataUpdateCoordinator], SensorEntity):
    """Representation of a value returned by status.json."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: YiHackDataUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize a status sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._sensor_type = sensor_type
        self._attr_unique_id = f"{config_entry.data[CONF_MAC]}_{sensor_type}"
        self._attr_device_info = get_device_info(config_entry)
        self._attr_translation_key = sensor_type

        if sensor_type == SENSOR_WIFI_QUALITY:
            self._attr_icon = "mdi:wifi"
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif sensor_type == SENSOR_STORAGE_FREE:
            self._attr_icon = "mdi:micro-sd"
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif sensor_type == SENSOR_UPTIME:
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.SECONDS
        else:
            raise ValueError(f"Unsupported sensor type: {sensor_type}")

    @property
    def native_value(self) -> int | None:
        """Return the current diagnostic value."""
        status = self.coordinator.data

        if self._sensor_type == SENSOR_WIFI_QUALITY:
            quality = _number(status.get("wlan_strength"))
            if quality is None:
                return None
            if self._config_entry.data[CONF_HACK_NAME] in RAW_WIFI_QUALITY_HACKS:
                quality = quality * 100 / 70
            return round(max(0, min(100, quality)))

        if self._sensor_type == SENSOR_STORAGE_FREE:
            return _percentage(status.get("free_sd"))

        uptime = _number(status.get("uptime"))
        return round(uptime) if uptime is not None else None
