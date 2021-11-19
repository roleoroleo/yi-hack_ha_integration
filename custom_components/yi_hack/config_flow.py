"""Config flow for yi_hack integration."""

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.ffmpeg import CONF_EXTRA_ARGUMENTS
from homeassistant.const import (CONF_HOST, CONF_MAC, CONF_NAME, CONF_PASSWORD,
                                 CONF_PORT, CONF_USERNAME)
from homeassistant.helpers.device_registry import format_mac

from .common import get_status
from .const import (ALLWINNER, ALLWINNER_R, ALLWINNERV2, ALLWINNERV2_R,
                    CONF_BOOST_SPEAKER, CONF_HACK_NAME, CONF_MQTT_PREFIX,
                    CONF_PTZ, CONF_RTSP_PORT, CONF_SERIAL,
                    CONF_TOPIC_BABY_CRYING, CONF_TOPIC_MOTION_DETECTION,
                    CONF_TOPIC_MOTION_DETECTION_IMAGE,
                    CONF_TOPIC_SOUND_DETECTION, CONF_TOPIC_STATUS,
                    DEFAULT_BRAND, DEFAULT_BRAND_R, DEFAULT_EXTRA_ARGUMENTS,
                    DEFAULT_HOST, DEFAULT_PASSWORD, DEFAULT_PORT,
                    DEFAULT_USERNAME, DOMAIN, MSTAR, MSTAR_R, SONOFF, SONOFF_R,
                    V5, V5_R)

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = {
    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
    vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
    vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    vol.Optional(CONF_EXTRA_ARGUMENTS, default=DEFAULT_EXTRA_ARGUMENTS): str,
    vol.Required(
        CONF_BOOST_SPEAKER,
        default="auto",
    ): vol.In(["auto", "disabled", "x 2", "x 3", "x 4", "x 5"])
}

class YiHackFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a yi-hack config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            user = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]
            extra_arguments = user_input[CONF_EXTRA_ARGUMENTS]
            boost_speaker = user_input[CONF_BOOST_SPEAKER]

            response = await self.hass.async_add_executor_job(get_status, user_input)
            if response is not None:
                try:
                    serial_number = response["serial_number"]
                except KeyError:
                    serial_number = None

                try:
                    mac = response["mac_addr"]
                except KeyError:
                    mac = None

                try:
                    ptz = response["ptz"]
                except KeyError:
                    ptz = "no"

                try:
                    hackname = response["name"]
                except KeyError:
                    hackname = DEFAULT_BRAND

                if serial_number is not None and mac is not None:
                    user_input[CONF_SERIAL] = serial_number
                    user_input[CONF_MAC] = format_mac(mac)
                    user_input[CONF_PTZ] = ptz
                    user_input[CONF_HACK_NAME] = hackname
                    if hackname == MSTAR:
                        user_input[CONF_NAME] = MSTAR_R + "_" + user_input[CONF_MAC].replace(':', '')[6:]
                    elif hackname == ALLWINNER:
                        user_input[CONF_NAME] = ALLWINNER_R + "_" + user_input[CONF_MAC].replace(':', '')[6:]
                    elif hackname == ALLWINNERV2:
                        user_input[CONF_NAME] = ALLWINNERV2_R + "_" + user_input[CONF_MAC].replace(':', '')[6:]
                    elif hackname == V5:
                        user_input[CONF_NAME] = V5_R + "_" + user_input[CONF_MAC].replace(':', '')[6:]
                    elif hackname == SONOFF:
                        user_input[CONF_NAME] = SONOFF_R + "_" + user_input[CONF_MAC].replace(':', '')[6:]
                    else:
                        user_input[CONF_NAME] = DEFAULT_BRAND_R + "_" + user_input[CONF_MAC].replace(':', '')[6:]
                else:
                    _LOGGER.error("Unable to get mac address or serial number from device %s", host)
                    errors["base"] = "cannot_get_mac_or_serial"

                if not errors:
                    await self.async_set_unique_id(user_input[CONF_MAC])
                    self._abort_if_unique_id_configured()

                    for entry in self._async_current_entries():
                        if entry.data[CONF_MAC] == user_input[CONF_MAC]:
                            _LOGGER.error("Device already configured: %s", host)
                            return self.async_abort(reason="already_configured")

                    user_input[CONF_RTSP_PORT] = None
                    user_input[CONF_MQTT_PREFIX] = None
                    user_input[CONF_TOPIC_STATUS] = None
                    user_input[CONF_TOPIC_MOTION_DETECTION] = None
                    user_input[CONF_TOPIC_SOUND_DETECTION] = None
                    user_input[CONF_TOPIC_BABY_CRYING] = None
                    user_input[CONF_TOPIC_MOTION_DETECTION_IMAGE] = None

                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data=user_input
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(DATA_SCHEMA),
            errors=errors,
        )
