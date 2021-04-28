"""Support for collecting data from the yi-hack cam."""
import logging

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .const import (
    ALLWINNER,
    ALLWINNERV2,
    CONF_HACK_NAME,
    CONF_MQTT_PREFIX,
    CONF_SERIAL,
    CONF_TOPIC_AI_HUMAN_DETECTION,
    CONF_TOPIC_BABY_CRYING,
    CONF_TOPIC_MOTION_DETECTION,
    CONF_TOPIC_SOUND_DETECTION,
    CONF_TOPIC_STATUS,
    DEFAULT_BRAND,
    DOMAIN,
    MSTAR,
)

ICON = "mdi:update"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config, async_add_entities):
    """Set up MQTT motion detection sensor."""

    if (config.data[CONF_HACK_NAME] == DEFAULT_BRAND) or (config.data[CONF_HACK_NAME] == MSTAR):
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
        self._mac = config.data[CONF_MAC]
        self._updated = None
        self._mqtt_subscription = None

        if sensor_type == CONF_TOPIC_STATUS:
            self._name = self._device_name + "_status"
            self._unique_id = self._device_name + "_bsst"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_STATUS]
        elif sensor_type == CONF_TOPIC_MOTION_DETECTION:
            self._name = self._device_name + "_motion_detection"
            self._unique_id = self._device_name + "_bsmd"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_MOTION_DETECTION]
        elif sensor_type == CONF_TOPIC_AI_HUMAN_DETECTION:
            self._name = self._device_name + "_ai_human_detection"
            self._unique_id = self._device_name + "_bsah"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_AI_HUMAN_DETECTION]
        elif sensor_type == CONF_TOPIC_SOUND_DETECTION:
            self._name = self._device_name + "_sound_detection"
            self._unique_id = self._device_name + "_bssd"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_SOUND_DETECTION]
        elif sensor_type == CONF_TOPIC_BABY_CRYING:
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

        self._mqtt_subscription = await mqtt.async_subscribe(
            self.hass, self._state_topic, message_received, 1
        )

    async def async_will_remove_from_hass(self):
        """Unsubscribe from MQTT events."""
        if self._mqtt_subscription:
            self._mqtt_subscription()

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
            "connections": {(CONNECTION_NETWORK_MAC, self._mac)},
            "identifiers": {(DOMAIN, self._serial_number)},
            "manufacturer": DEFAULT_BRAND,
            "model": DOMAIN,
        }
