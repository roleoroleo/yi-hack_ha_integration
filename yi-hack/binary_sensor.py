"""Support for collecting data from the yi-hack cam."""
import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import callback
from homeassistant.const import (
    CONF_NAME,
)

from .const import (
    DOMAIN,
    DEFAULT_BRAND,
    MSTAR,
    ALLWINNER,
    ALLWINNERV2,
    CONF_HACK_NAME,
    CONF_SERIAL,
    CONF_MQTT_PREFIX,
    CONF_TOPIC_STATUS,
    CONF_TOPIC_MOTION_DETECTION,
    CONF_TOPIC_AI_HUMAN_DETECTION,
    CONF_TOPIC_SOUND_DETECTION,
    CONF_TOPIC_BABY_CRYING,
)

ICON = "mdi:update"

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config, async_add_entities):
    """Set up MQTT motion detection sensor."""
    if (config.data[CONF_HACK_NAME] == MSTAR):
        async_add_entities(
            [
                YiMQTTBinarySensor(hass, config, CONF_TOPIC_STATUS),
                YiMQTTBinarySensor(hass, config, CONF_TOPIC_MOTION_DETECTION),
                YiMQTTBinarySensor(hass, config, CONF_TOPIC_BABY_CRYING)
            ]
        )
    elif (config.data[CONF_HACK_NAME] == ALLWINNER) or (config.data[CONF_HACK_NAME] == ALLWINNERV2):
        async_add_entities(
            [
                YiMQTTBinarySensor(hass, config, CONF_TOPIC_STATUS),
                YiMQTTBinarySensor(hass, config, CONF_TOPIC_MOTION_DETECTION),
                YiMQTTBinarySensor(hass, config, CONF_TOPIC_AI_HUMAN_DETECTION),
                YiMQTTBinarySensor(hass, config, CONF_TOPIC_SOUND_DETECTION),
                YiMQTTBinarySensor(hass, config, CONF_TOPIC_BABY_CRYING)
            ]
        )

class YiMQTTBinarySensor(BinarySensorEntity):
    """Representation of a motion detection sensor that is updated via MQTT."""

    def __init__(self, hass, config, sensor_type):
        """Initialize the sensor."""
        self._state = False
        self._device_name = config.data[CONF_NAME]
        self._serial_number = config.data[CONF_SERIAL]
        self._updated = None
        if (sensor_type == CONF_TOPIC_STATUS):
            self._name = self._device_name + "_status"
            self._unique_id = self._device_name + "_bsst"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_STATUS]
        elif (sensor_type == CONF_TOPIC_MOTION_DETECTION):
            self._name = self._device_name + "_motion_detection"
            self._unique_id = self._device_name + "_bsmd"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_MOTION_DETECTION]
        elif (sensor_type == CONF_TOPIC_BABY_CRYING):
            self._name = self._device_name + "_baby_crying"
            self._unique_id = self._device_name + "_bsbc"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_BABY_CRYING]

    async def async_added_to_hass(self):
        """Subscribe to MQTT events."""

        @callback
        def message_received(msg):
            """Handle new MQTT messages."""
            data = msg.payload

            self._state = data
            self.async_write_ha_state()

        return await mqtt.async_subscribe(
            self.hass, self._state_topic, message_received, 1
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe from MQTT events."""

        return await mqtt.async_unsubscribe(
            self.hass, self._state_topic
        )

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return ICON

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "name": self._name,
            "identifiers": {(DOMAIN, self._serial_number)},
            "manufacturer": DEFAULT_BRAND,
            "model": DOMAIN,
        }

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "name": self._device_name,
            "identifiers": {(DOMAIN, self._serial_number)},
            "manufacturer": DEFAULT_BRAND,
            "model": DOMAIN,
        }
