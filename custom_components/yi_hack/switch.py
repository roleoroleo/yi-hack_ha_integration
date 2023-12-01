"""Support for yi-hack switches."""

import asyncio
import logging

from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (CONF_HOST, CONF_MAC, CONF_NAME,
                                 CONF_PASSWORD, CONF_PORT, CONF_USERNAME)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .const import (ALLWINNER, ALLWINNERV2, CONF_HACK_NAME, DEFAULT_BRAND,
                    CONF_MQTT_PREFIX, DOMAIN, MSTAR, SONOFF, V5)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Yi Camera switches from a config entry."""
    if (config_entry.data[CONF_HACK_NAME] == DEFAULT_BRAND) or (config_entry.data[CONF_HACK_NAME] == MSTAR):
        entities = [
            YiHackSwitch(hass, config_entry, "switch_on", "Switch On"),
            YiHackSwitch(hass, config_entry, "save_video_on_motion", "Save Video on Motion"),
            YiHackSwitch(hass, config_entry, "baby_crying_detect", "Baby Crying Detect"),
            YiHackSwitch(hass, config_entry, "led", "LED"),
            YiHackSwitch(hass, config_entry, "ir", "IR"),
            YiHackSwitch(hass, config_entry, "rotate", "Rotate"),
        ]
    elif (config_entry.data[CONF_HACK_NAME] == V5):
        entities = [
            YiHackSwitch(hass, config_entry, "switch_on", "Switch On"),
#            YiHackSwitch(hass, config_entry, "motion_detection", "Motion Detection"),
            YiHackSwitch(hass, config_entry, "save_video_on_motion", "Save Video on Motion"),
            YiHackSwitch(hass, config_entry, "sound_detection", "Sound Detection"),
            YiHackSwitch(hass, config_entry, "baby_crying_detect", "Baby Crying Detect"),
            YiHackSwitch(hass, config_entry, "led", "LED"),
            YiHackSwitch(hass, config_entry, "ir", "IR"),
            YiHackSwitch(hass, config_entry, "rotate", "Rotate"),
        ]
    elif (config_entry.data[CONF_HACK_NAME] == ALLWINNER):
        entities = [
            YiHackSwitch(hass, config_entry, "switch_on", "Switch On"),
            YiHackSwitch(hass, config_entry, "motion_detection", "Motion Detection"),
            YiHackSwitch(hass, config_entry, "save_video_on_motion", "Save Video on Motion"),
            YiHackSwitch(hass, config_entry, "ai_human_detection", "AI Human Detection"),
            YiHackSwitch(hass, config_entry, "ai_vehicle_detection", "AI Vehicle Detection"),
            YiHackSwitch(hass, config_entry, "ai_animal_detection", "AI Animal Detection"),
            YiHackSwitch(hass, config_entry, "sound_detection", "Sound Detection"),
            YiHackSwitch(hass, config_entry, "led", "LED"),
            YiHackSwitch(hass, config_entry, "ir", "IR"),
            YiHackSwitch(hass, config_entry, "rotate", "Rotate"),
        ]
    elif (config_entry.data[CONF_HACK_NAME] == ALLWINNERV2):
        entities = [
            YiHackSwitch(hass, config_entry, "switch_on", "Switch On"),
            YiHackSwitch(hass, config_entry, "motion_detection", "Motion Detection"),
            YiHackSwitch(hass, config_entry, "save_video_on_motion", "Save Video on Motion"),
            YiHackSwitch(hass, config_entry, "ai_human_detection", "AI Human Detection"),
            YiHackSwitch(hass, config_entry, "ai_vehicle_detection", "AI Vehicle Detection"),
            YiHackSwitch(hass, config_entry, "ai_animal_detection", "AI Animal Detection"),
            YiHackSwitch(hass, config_entry, "face_detection", "Face Detection"),
            YiHackSwitch(hass, config_entry, "motion_tracking", "Motion Tracking"),
            YiHackSwitch(hass, config_entry, "sound_detection", "Sound Detection"),
            YiHackSwitch(hass, config_entry, "led", "LED"),
            YiHackSwitch(hass, config_entry, "ir", "IR"),
            YiHackSwitch(hass, config_entry, "rotate", "Rotate"),
        ]
    elif config_entry.data[CONF_HACK_NAME] == SONOFF:
        entities = [
            YiHackSwitch(hass, config_entry, "switch_on", "Switch On"),
            YiHackSwitch(hass, config_entry, "motion_detection", "Motion Detection"),
            YiHackSwitch(hass, config_entry, "local_record", "Local Record"),
            YiHackSwitch(hass, config_entry, "rotate", "Rotate"),
        ]

    async_add_entities(entities)

class YiHackSwitch(SwitchEntity):
    """Representation of a Yi Camera Switch."""

    def __init__(self, hass, config, switch_type, name):
        """Initialize the device."""
        self._device_name = config.data[CONF_NAME]
        self._mac = config.data[CONF_MAC]
        self._host = config.data[CONF_HOST]
        self._port = config.data[CONF_PORT]
        self._user = config.data[CONF_USERNAME]
        self._password = config.data[CONF_PASSWORD]
        self._switch_type = switch_type
        self._name = self._device_name + " " + name
        self._mqtt_subscription = None
        self._mqtt_cmnd_topic = config.data[CONF_MQTT_PREFIX] + "/cmnd/camera/" + switch_type
        self._mqtt_stat_topic = config.data[CONF_MQTT_PREFIX] + "/stat/camera/" + switch_type
        self._state = False

        if switch_type == "switch_on":
            self._attr_unique_id = self._device_name + "_swso"
            self._attr_icon = "mdi:video"
        elif switch_type == "save_video_on_motion":
            self._attr_unique_id = self._device_name + "_swsv"
            self._attr_icon = "mdi:content-save"
        elif switch_type == "local_record":
            self._attr_unique_id = self._device_name + "_swlr"
            self._attr_icon = "mdi:content-save"
        elif switch_type == "motion_detection":
            self._attr_unique_id = self._device_name + "_swmd"
            self._attr_icon = "mdi:motion-sensor"
        elif switch_type == "ai_human_detection":
            self._attr_unique_id = self._device_name + "_swhd"
            self._attr_icon = "mdi:human-greeting-variant"
        elif switch_type == "ai_vehicle_detection":
            self._attr_unique_id = self._device_name + "_swvd"
            self._attr_icon = "mdi:car"
        elif switch_type == "ai_animal_detection":
            self._attr_unique_id = self._device_name + "_swad"
            self._attr_icon = "mdi:dog-side"
        elif switch_type == "face_detection":
            self._attr_unique_id = self._device_name + "_swfd"
            self._attr_icon = "mdi:face-recognition"
        elif switch_type == "motion_tracking":
            self._attr_unique_id = self._device_name + "_swmt"
            self._attr_icon = "mdi:motion"
        elif switch_type == "sound_detection":
            self._attr_unique_id = self._device_name + "_swsd"
            self._attr_icon = "mdi:music-note"
        elif switch_type == "baby_crying_detect":
            self._attr_unique_id = self._device_name + "_swbc"
            self._attr_icon = "mdi:account-voice"
        elif switch_type == "led":
            self._attr_unique_id = self._device_name + "_swle"
            self._attr_icon = "mdi:led-on"
        elif switch_type == "ir":
            self._attr_unique_id = self._device_name + "_swir"
            self._attr_icon = "mdi:led-outline"
        elif switch_type == "rotate":
            self._attr_unique_id = self._device_name + "_swro"
            self._attr_icon = "mdi:rotate-right"

    async def async_added_to_hass(self):
        """Subscribe to MQTT events."""

        @callback
        def message_received(msg):
            """Handle new MQTT messages."""
            try:
                payload = msg.payload.decode("utf-8", "ignore")
            except:
                payload = msg.payload

            if payload.lower() in ["yes", "on"]:
                self._state = True
            elif payload.lower() in ["no", "off"]:
                self._state = False
            else:  # Payload is not correct for this entity
                _LOGGER.info(
                    "No matching payload found for entity %s with topic: %s. Payload: '%s'",
                    self._name,
                    self._mqtt_stat_topic,
                    payload,
                )
                return

            self.async_write_ha_state()

        self._mqtt_subscription = await mqtt.async_subscribe(
            self.hass, self._mqtt_stat_topic, message_received, 1
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe from MQTT events."""
        if self._mqtt_subscription:
            self._mqtt_subscription()

    def turn_off(self):
        """Turn off switch"""
        self.hass.async_create_task(
            mqtt.async_publish(self.hass, self._mqtt_cmnd_topic, "off", 1, 0)
        )
        self._state = False

    def turn_on(self):
        """Turn on switch"""
        self.hass.async_create_task(
            mqtt.async_publish(self.hass, self._mqtt_cmnd_topic, "on", 1, 0)
        )
        self._state = True

    @property
    def is_on(self):
        """Return true if the switch is on."""
        return self._state

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def brand(self):
        """Camera brand."""
        return DEFAULT_BRAND

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
