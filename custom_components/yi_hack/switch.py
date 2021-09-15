"""Support for yi-hack privacy switch."""

import asyncio
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import (CONF_HOST, CONF_MAC, CONF_NAME,
                                 CONF_PASSWORD, CONF_PORT, CONF_USERNAME)
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC

from .common import (get_privacy, set_power_off_in_progress,
                     set_power_on_in_progress, set_privacy)
from .const import DEFAULT_BRAND, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the Yi Camera media player from a config entry."""
    async_add_entities([YiHackSwitch(hass, config_entry)], True)

class YiHackSwitch(SwitchEntity):
    """Representation of a Yi Camera Switch."""

    def __init__(self, hass, config):
        """Initialize the device."""
        self._device_name = config.data[CONF_NAME]
        self._name = self._device_name + "_privacy"
        self._unique_id = self._device_name + "_swpr"
        self._mac = config.data[CONF_MAC]
        self._host = config.data[CONF_HOST]
        self._port = config.data[CONF_PORT]
        self._user = config.data[CONF_USERNAME]
        self._password = config.data[CONF_PASSWORD]
        self._state = None

    def update(self):
        """Return the state of the switch."""
        conf = dict([
            (CONF_HOST, self._host),
            (CONF_PORT, self._port),
            (CONF_USERNAME, self._user),
            (CONF_PASSWORD, self._password),
        ])
        #self._state = self.hass.async_add_executor_job(get_privacy, self.hass, conf)
        #self.hass.async_add_executor_job(set_privacy, self.hass, self._state)
        self._state = get_privacy(self.hass, self._device_name, conf)
        set_privacy(self.hass, self._device_name, self._state)

    def turn_off(self):
        """Turn off privacy (set camera on)."""
        conf = dict([
            (CONF_HOST, self._host),
            (CONF_PORT, self._port),
            (CONF_USERNAME, self._user),
            (CONF_PASSWORD, self._password),
        ])
        #privacy = self.hass.async_add_executor_job(get_privacy, self.hass)
        if get_privacy(self.hass, self._device_name):
            _LOGGER.debug("Turn off privacy, camera %s", self._name)
            set_power_off_in_progress(self.hass, self._device_name)
            #self.hass.async_add_executor_job(set_privacy, self.hass, False, conf)
            set_privacy(self.hass, self._device_name, False, conf)
            self._state = False

    def turn_on(self):
        """Turn on privacy (set camera off)."""
        conf = dict([
            (CONF_HOST, self._host),
            (CONF_PORT, self._port),
            (CONF_USERNAME, self._user),
            (CONF_PASSWORD, self._password),
        ])
        #privacy = self.hass.async_add_executor_job(get_privacy, self.hass)
        if not get_privacy(self.hass, self._device_name):
            _LOGGER.debug("Turn on privacy, camera %s", self._name)
            set_power_on_in_progress(self.hass, self._device_name)
            #self.hass.async_add_executor_job(set_privacy, self.hass, True, conf)
            set_privacy(self.hass, self._device_name, True, conf)
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
