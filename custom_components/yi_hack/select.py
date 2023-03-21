"""Support for yi-hack select."""
from __future__ import annotations

from homeassistant.components import mqtt
from homeassistant.components.select import SelectEntity
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import callback

from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .const import (CONF_HACK_NAME, CONF_MQTT_PREFIX, DEFAULT_BRAND, DOMAIN,
                    SONOFF)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up platform."""

    if config_entry.data[CONF_HACK_NAME] == SONOFF:
        entities = [
            YiHackSelect(hass, config_entry, "sensitivity", [ "low", "medium", "high" ]),
            YiHackSelect(hass, config_entry, "ir", [ "auto", "on", "off" ]),
        ]
    else:
        entities = [
            YiHackSelect(hass, config_entry, "sensitivity", [ "low", "medium", "high" ]),
            YiHackSelect(hass, config_entry, "sound_sensitivity", [ "30", "35", "40", "45", "50", "60", "70", "80", "90" ]),
            YiHackSelect(hass, config_entry, "cruise", [ "no", "presets", "360" ]),
        ]

    async_add_entities(entities)


class YiHackSelect(SelectEntity):
    """Select entity."""

#    _attr_entity_category = EntityCategory.CONFIG

#    def __init__(self, coordinator: Coordinator, coil: Coil) -> None:
    def __init__(self, hass, config, select_type, select_options):
        """Initialize entity."""
#        assert coil.mappings
#        super().__init__(coordinator, coil, ENTITY_ID_FORMAT)
        self._device_name = config.data[CONF_NAME]
        self._mac = config.data[CONF_MAC]
        self._name = self._device_name + "_select_" + select_type
        self._mqtt_cmnd_topic = config.data[CONF_MQTT_PREFIX] + "/cmnd/camera/" + select_type
        self._mqtt_stat_topic = config.data[CONF_MQTT_PREFIX] + "/stat/camera/" + select_type
        self._select_type = select_type
        self._attr_unit_of_measurement = None
        self._attr_options = select_options
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_current_option = "no"
        self._state = None

        if select_type == "sensitivity":
            self._attr_icon = "mdi:motion-sensor"
            self._unique_id = self._device_name + "_sese"
        elif select_type == "sound_sensitivity":
            self._attr_icon = "mdi:music-note"
            self._unique_id = self._device_name + "_sess"
        elif select_type == "ir":
            self._attr_icon = "mdi:led-outline"
            self._unique_id = self._device_name + "_seir"
        elif select_type == "cruise":
            self._attr_icon = "mdi:camera-control"
            self._unique_id = self._device_name + "_secr"

    async def async_added_to_hass(self):
        """Subscribe to MQTT events."""

        @callback
        def message_received(msg):
            """Handle new MQTT messages."""
            try:
                payload = msg.payload.decode("utf-8", "ignore")
            except:
                payload = msg.payload

            self._state = payload.lower()
            self.async_write_ha_state()

        self._mqtt_subscription = await mqtt.async_subscribe(
            self.hass, self._mqtt_stat_topic, message_received, 1
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe from MQTT events."""
        if self._mqtt_subscription:
            self._mqtt_subscription()

    @property
    def current_option(self) -> str | None:
        """Return current option."""
        return self._state

    async def async_select_option(self, option: str) -> None:
        """Select option."""
        self.hass.async_create_task(
            mqtt.async_publish(self.hass, self._mqtt_cmnd_topic, option, 1, 0)
        )
        self._state = option

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def brand(self):
        """Camera brand."""
        return DEFAULT_BRAND

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the device."""
        return self._unique_id

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
