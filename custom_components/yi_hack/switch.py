"""Support for yi-hack privacy switch."""

import asyncio
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (CONF_HOST, CONF_MAC, CONF_NAME,
                                 CONF_PASSWORD, CONF_PORT, CONF_USERNAME)
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .common import (get_camera_conf, get_privacy, set_camera_conf,
                     set_power_off_in_progress,set_power_on_in_progress,
                     set_privacy)
from .const import (ALLWINNER, ALLWINNERV2, CONF_HACK_NAME, DEFAULT_BRAND,
                    DOMAIN, MSTAR, SONOFF, V5)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Yi Camera media player from a config entry."""
    if (config_entry.data[CONF_HACK_NAME] == DEFAULT_BRAND) or (config_entry.data[CONF_HACK_NAME] == MSTAR):
        entities = [
            YiHackSwitch(hass, config_entry, "privacy"),
            YiHackSwitch(hass, config_entry, "switch_on"),
            YiHackSwitch(hass, config_entry, "save_video_on_motion"),
            YiHackSwitch(hass, config_entry, "baby_crying_detect"),
            YiHackSwitch(hass, config_entry, "led"),
            YiHackSwitch(hass, config_entry, "ir"),
            YiHackSwitch(hass, config_entry, "rotate"),
        ]
    elif (config_entry.data[CONF_HACK_NAME] == ALLWINNER) or (config_entry.data[CONF_HACK_NAME] == V5):
        entities = [
            YiHackSwitch(hass, config_entry, "privacy"),
            YiHackSwitch(hass, config_entry, "switch_on"),
            YiHackSwitch(hass, config_entry, "save_video_on_motion"),
            YiHackSwitch(hass, config_entry, "ai_human_detection"),
            YiHackSwitch(hass, config_entry, "sound_detection"),
            YiHackSwitch(hass, config_entry, "led"),
            YiHackSwitch(hass, config_entry, "ir"),
            YiHackSwitch(hass, config_entry, "rotate"),
        ]
    elif (config_entry.data[CONF_HACK_NAME] == ALLWINNERV2):
        entities = [
            YiHackSwitch(hass, config_entry, "privacy"),
            YiHackSwitch(hass, config_entry, "switch_on"),
            YiHackSwitch(hass, config_entry, "save_video_on_motion"),
            YiHackSwitch(hass, config_entry, "ai_human_detection"),
            YiHackSwitch(hass, config_entry, "face_detection"),
            YiHackSwitch(hass, config_entry, "motion_tracking"),
            YiHackSwitch(hass, config_entry, "sound_detection"),
            YiHackSwitch(hass, config_entry, "led"),
            YiHackSwitch(hass, config_entry, "ir"),
            YiHackSwitch(hass, config_entry, "rotate"),
        ]
    elif config_entry.data[CONF_HACK_NAME] == SONOFF:
        entities = [
            YiHackSwitch(hass, config_entry, "privacy"),
        ]

    async_add_entities(entities)

class YiHackSwitch(SwitchEntity):
    """Representation of a Yi Camera Switch."""

    def __init__(self, hass, config, switch_type):
        """Initialize the device."""
        self._device_name = config.data[CONF_NAME]
        self._mac = config.data[CONF_MAC]
        self._host = config.data[CONF_HOST]
        self._port = config.data[CONF_PORT]
        self._user = config.data[CONF_USERNAME]
        self._password = config.data[CONF_PASSWORD]
        self._switch_type = switch_type
        self._state = False

        if switch_type == "privacy":
            self._name = self._device_name + "_switch_privacy"
            self._unique_id = self._device_name + "_swpr"
        elif switch_type == "switch_on":
            self._name = self._device_name + "_switch_switch_on"
            self._unique_id = self._device_name + "_swso"
        elif switch_type == "save_video_on_motion":
            self._name = self._device_name + "_switch_save_video_on_motion"
            self._unique_id = self._device_name + "_swsv"
        elif switch_type == "baby_crying_detect":
            self._name = self._device_name + "_switch_baby_crying_detect"
            self._unique_id = self._device_name + "_swbc"
        elif switch_type == "led":
            self._name = self._device_name + "_switch_led"
            self._unique_id = self._device_name + "_swle"
        elif switch_type == "ir":
            self._name = self._device_name + "_switch_ir"
            self._unique_id = self._device_name + "_swir"
        elif switch_type == "rotate":
            self._name = self._device_name + "_switch_rotate"
            self._unique_id = self._device_name + "_swro"
        elif switch_type == "ai_human_detection":
            self._name = self._device_name + "_switch_ai_human_detection"
            self._unique_id = self._device_name + "_swhd"
        elif switch_type == "face_detection":
            self._name = self._device_name + "_switch_face_detection"
            self._unique_id = self._device_name + "_swfd"
        elif switch_type == "motion_tracking":
            self._name = self._device_name + "_switch_motion_tracking"
            self._unique_id = self._device_name + "_swmt"
        elif switch_type == "sound_detection":
            self._name = self._device_name + "_switch_sound_detection"
            self._unique_id = self._device_name + "_swsd"

    def update(self):
        """Return the state of the switch."""
        conf = dict([
            (CONF_HOST, self._host),
            (CONF_PORT, self._port),
            (CONF_USERNAME, self._user),
            (CONF_PASSWORD, self._password),
        ])
        if self._switch_type == "privacy":
            self._state = get_privacy(self.hass, self._device_name, conf)
        else:
            self._state = get_camera_conf(self.hass, self._device_name, self._switch_type, conf)

    def turn_off(self):
        """Turn off switch"""
        conf = dict([
            (CONF_HOST, self._host),
            (CONF_PORT, self._port),
            (CONF_USERNAME, self._user),
            (CONF_PASSWORD, self._password),
        ])
        if self._switch_type == "privacy":
            if get_privacy(self.hass, self._device_name):
                _LOGGER.debug("Turn off privacy, camera %s", self._name)
                # Turn off the privacy switch:
                # power on the cam and set privacy false
                set_power_on_in_progress(self.hass, self._device_name)
                set_privacy(self.hass, self._device_name, False, conf)
                self._state = False
                self.schedule_update_ha_state(force_refresh=True)
        else:
            _LOGGER.debug("Turn off switch %s, camera %s", self._switch_type, self._name)
            set_camera_conf(self.hass, self._device_name, self._switch_type, False, conf)
            self._state = False
            self.schedule_update_ha_state(force_refresh=True)

    def turn_on(self):
        """Turn on privacy (set camera off)."""
        conf = dict([
            (CONF_HOST, self._host),
            (CONF_PORT, self._port),
            (CONF_USERNAME, self._user),
            (CONF_PASSWORD, self._password),
        ])
        if self._switch_type == "privacy":
            if not get_privacy(self.hass, self._device_name):
                _LOGGER.debug("Turn on privacy, camera %s", self._name)
                # Turn on the privacy switch:
                # power off the cam and set privacy true
                set_power_off_in_progress(self.hass, self._device_name)
                set_privacy(self.hass, self._device_name, True, conf)
                self._state = True
                self.schedule_update_ha_state(force_refresh=True)
        else:
            _LOGGER.debug("Turn on switch %s, camera %s", self._switch_type, self._name)
            set_camera_conf(self.hass, self._device_name, self._switch_type, True, conf)
            self._state = True
            self.schedule_update_ha_state(force_refresh=True)

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
