"""Support for collecting data from the yi-hack cam."""
import logging

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_MOTION,
    DEVICE_CLASS_SOUND,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MAC, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import event
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

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
    CONF_SERIAL,
    CONF_SOUND_DETECTION_MSG,
    CONF_TOPIC_AI_HUMAN_DETECTION,
    CONF_TOPIC_BABY_CRYING,
    CONF_TOPIC_MOTION_DETECTION,
    CONF_TOPIC_SOUND_DETECTION,
    CONF_TOPIC_STATUS,
    CONF_WILL_MSG,
    DEFAULT_BRAND,
    DOMAIN,
    MSTAR,
)

ICON = "mdi:update"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(_hass: HomeAssistant, config: ConfigEntry, async_add_entities):
    """Set up MQTT motion detection sensor."""
    if (config.data[CONF_HACK_NAME] == DEFAULT_BRAND) or (config.data[CONF_HACK_NAME] == MSTAR):
        entities = [
            YiMQTTBinarySensor(config, CONF_TOPIC_STATUS),
            YiMQTTBinarySensor(config, CONF_TOPIC_MOTION_DETECTION),
            YiMQTTBinarySensor(config, CONF_TOPIC_BABY_CRYING),
        ]
    elif (config.data[CONF_HACK_NAME] == ALLWINNER) or (config.data[CONF_HACK_NAME] == ALLWINNERV2):
        entities = [
            YiMQTTBinarySensor(config, CONF_TOPIC_STATUS),
            YiMQTTBinarySensor(config, CONF_TOPIC_MOTION_DETECTION),
            YiMQTTBinarySensor(config, CONF_TOPIC_BABY_CRYING),
            YiMQTTBinarySensor(config, CONF_TOPIC_AI_HUMAN_DETECTION),
            YiMQTTBinarySensor(config, CONF_TOPIC_SOUND_DETECTION),
        ]

    async_add_entities(entities)


class YiMQTTBinarySensor(BinarySensorEntity):
    """Representation of a motion detection sensor that is updated via MQTT."""

    def __init__(self, config: ConfigEntry, sensor_type):
        """Initialize the sensor."""
        self._state = False
        self._device_name = config.data[CONF_NAME]
        self._serial_number = config.data[CONF_SERIAL]
        self._mac = config.data[CONF_MAC]
        self._mqtt_subscription = None
        self._delay_listener = None
        self._payload_off = None
        self._off_delay = None
        self._ignore_first_event = False

        if sensor_type == CONF_TOPIC_STATUS:
            self._name = self._device_name + "_status"
            self._unique_id = self._device_name + "_bsst"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_STATUS]
            self._payload_on = config.data[CONF_BIRTH_MSG]
            self._payload_off = config.data[CONF_WILL_MSG]
            self._device_class = DEVICE_CLASS_CONNECTIVITY
        elif sensor_type == CONF_TOPIC_MOTION_DETECTION:
            self._name = self._device_name + "_motion_detection"
            self._unique_id = self._device_name + "_bsmd"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_MOTION_DETECTION]
            self._payload_on = config.data[CONF_MOTION_START_MSG]
            self._payload_off = config.data[CONF_MOTION_STOP_MSG]
            self._device_class = DEVICE_CLASS_MOTION
        elif sensor_type == CONF_TOPIC_AI_HUMAN_DETECTION:
            self._name = self._device_name + "_ai_human_detection"
            self._unique_id = self._device_name + "_bsah"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_AI_HUMAN_DETECTION]
            self._payload_on = config.data[CONF_AI_HUMAN_DETECTION_START_MSG]
            self._payload_off = config.data[CONF_AI_HUMAN_DETECTION_STOP_MSG]
            self._device_class = DEVICE_CLASS_MOTION
        elif sensor_type == CONF_TOPIC_SOUND_DETECTION:
            self._name = self._device_name + "_sound_detection"
            self._unique_id = self._device_name + "_bssd"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_SOUND_DETECTION]
            self._payload_on = config.data[CONF_SOUND_DETECTION_MSG]
            self._off_delay = 60
            self._device_class = DEVICE_CLASS_SOUND
        elif sensor_type == CONF_TOPIC_BABY_CRYING:
            self._name = self._device_name + "_baby_crying"
            self._unique_id = self._device_name + "_bsbc"
            self._state_topic = config.data[CONF_MQTT_PREFIX] + "/" + config.data[CONF_TOPIC_BABY_CRYING]
            self._payload_on = config.data[CONF_BABY_CRYING_MSG]
            self._off_delay = 60
            self._device_class = DEVICE_CLASS_SOUND
            self._ignore_first_event = True
        else:
            raise RuntimeError("Unknown sensor type")

    async def async_added_to_hass(self):
        """Subscribe to MQTT events."""

        @callback
        def off_delay_listener(now):
            """Switch device off after a delay."""
            self._delay_listener = None
            self._state = False
            self.async_write_ha_state()

        @callback
        def message_received(msg):
            """Handle new MQTT messages."""
            payload = msg.payload

            if self._ignore_first_event:
                # for baby crying event
                # the first subscribed value is always 'crying'
                # we should consider the next event instead
                self._state = False
            elif payload == self._payload_on:
                self._state = True
            elif payload == self._payload_off:
                self._state = False
            else:  # Payload is not for this entity
                _LOGGER.info(
                    "No matching payload found for entity: %s with state topic: %s. Payload: '%s'",
                    self._name,
                    self._state_topic,
                    payload,
                )
                return

            if self._delay_listener is not None:
                self._delay_listener()
                self._delay_listener = None

            if self._state and self._off_delay is not None:
                self._delay_listener = event.async_call_later(
                    self.hass, self._off_delay, off_delay_listener
                )

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
    def is_on(self):
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
    def device_class(self):
        """Return the icon to use in the frontend."""
        return self._device_class

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
