"""Config flow for the yi-hack integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.ffmpeg import CONF_EXTRA_ARGUMENTS
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
)
from homeassistant.helpers.device_registry import format_mac

try:
    from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
except ImportError:  # Home Assistant < 2025.2
    from homeassistant.components.zeroconf import ZeroconfServiceInfo

from .common import YiHackAuthenticationError, YiHackError, get_status
from .const import (
    ALLWINNER,
    ALLWINNER_R,
    ALLWINNERV2,
    ALLWINNERV2_R,
    CONF_BOOST_SPEAKER,
    CONF_HACK_NAME,
    CONF_MQTT_PREFIX,
    CONF_PTZ,
    CONF_RTSP_PORT,
    CONF_SERIAL,
    CONF_TOPIC_MOTION_DETECTION,
    CONF_TOPIC_MOTION_DETECTION_IMAGE,
    CONF_TOPIC_SOUND_DETECTION,
    CONF_TOPIC_STATUS,
    DEFAULT_BRAND,
    DEFAULT_BRAND_R,
    DEFAULT_EXTRA_ARGUMENTS,
    DEFAULT_HOST,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DEFAULT_USERNAME,
    DOMAIN,
    MSTAR,
    MSTAR_R,
    SONOFF,
    SONOFF_R,
    V5,
    V5_R,
)

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
    ): vol.In(["auto", "disabled", "x 2", "x 3", "x 4", "x 5"]),
}

DATA_SCHEMA_ZC = {
    vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
    vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
    vol.Optional(CONF_EXTRA_ARGUMENTS, default=DEFAULT_EXTRA_ARGUMENTS): str,
    vol.Required(
        CONF_BOOST_SPEAKER,
        default="auto",
    ): vol.In(["auto", "disabled", "x 2", "x 3", "x 4", "x 5"]),
}


class YiHackFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a yi-hack config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    def __init__(self) -> None:
        """Set up the instance."""
        self.connection_data: dict[str, Any] = {}

    def _async_entry_for_mac(self, mac: str) -> ConfigEntry | None:
        """Return an existing entry matching a normalized MAC address."""
        for entry in self._async_current_entries():
            entry_mac = entry.data.get(CONF_MAC)
            if isinstance(entry_mac, str) and format_mac(entry_mac) == mac:
                return entry

        return None

    def _async_entry_for_host(self, host: str) -> ConfigEntry | None:
        """Return an existing entry configured with a host address."""
        return next(
            (
                entry
                for entry in self._async_current_entries()
                if entry.data.get(CONF_HOST) == host
            ),
            None,
        )

    def _show_connection_form(
        self,
        step_id: str,
        user_input: dict[str, Any] | None = None,
        errors: dict[str, str] | None = None,
    ) -> ConfigFlowResult:
        """Show a connection form and preserve submitted values."""
        schema = DATA_SCHEMA_ZC if step_id == "zeroconf_confirm" else DATA_SCHEMA
        data_schema = vol.Schema(schema)
        if user_input:
            data_schema = self.add_suggested_values_to_schema(data_schema, user_input)

        return self.async_show_form(
            step_id=step_id,
            data_schema=data_schema,
            errors=errors or {},
        )

    async def _async_get_status(
        self, data: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Fetch status and map camera errors to config-flow errors."""
        try:
            return (
                await self.hass.async_add_executor_job(get_status, data),
                None,
            )
        except YiHackAuthenticationError:
            return None, "invalid_auth"
        except YiHackError:
            return None, "cannot_connect"

    async def _async_verify_entry_at_host(
        self,
        host: str,
        port: int,
    ) -> tuple[ConfigEntry, str] | None:
        """Verify a host match using the MAC returned by status.json."""
        entry = self._async_entry_for_host(host)
        if entry is None:
            return None

        response, error = await self._async_get_status(
            {
                **entry.data,
                CONF_HOST: host,
                CONF_PORT: port,
            }
        )
        if error is not None or response is None:
            return None

        status_mac = response.get("mac_addr")
        entry_mac = entry.data.get(CONF_MAC)
        if not isinstance(status_mac, str) or not isinstance(entry_mac, str):
            return None

        normalized_status_mac = format_mac(status_mac)
        if normalized_status_mac != format_mac(entry_mac):
            return None

        return entry, normalized_status_mac

    async def async_process_input(
        self,
        user_input: dict[str, Any],
        step_id: str,
    ) -> ConfigFlowResult:
        """Validate input and complete a flow."""
        response, error = await self._async_get_status(user_input)
        if error is not None:
            return self._show_connection_form(step_id, user_input, {"base": error})

        assert response is not None
        if "privacy" in response:
            _LOGGER.error("Unsupported hack version, please update your camera")
            return self.async_abort(reason="wrong_hack_version")

        serial_number = response.get("serial_number")
        mac = response.get("mac_addr")
        if not serial_number or not isinstance(mac, str) or not mac:
            _LOGGER.error(
                "Unable to get MAC address or serial number from device %s",
                user_input[CONF_HOST],
            )
            return self._show_connection_form(
                step_id,
                user_input,
                {"base": "cannot_get_mac_or_serial"},
            )

        normalized_mac = format_mac(mac)
        hack_name = response.get("name", DEFAULT_BRAND)
        name_prefixes = {
            MSTAR: MSTAR_R,
            ALLWINNER: ALLWINNER_R,
            ALLWINNERV2: ALLWINNERV2_R,
            V5: V5_R,
            SONOFF: SONOFF_R,
        }

        data = {
            **user_input,
            CONF_SERIAL: serial_number,
            CONF_MAC: normalized_mac,
            CONF_PTZ: response.get("ptz", "no"),
            CONF_HACK_NAME: hack_name,
            CONF_NAME: (
                f"{name_prefixes.get(hack_name, DEFAULT_BRAND_R)}_"
                f"{normalized_mac.replace(':', '')[6:]}"
            ),
            CONF_RTSP_PORT: None,
            CONF_MQTT_PREFIX: None,
            CONF_TOPIC_STATUS: None,
            CONF_TOPIC_MOTION_DETECTION: None,
            CONF_TOPIC_SOUND_DETECTION: None,
            CONF_TOPIC_MOTION_DETECTION_IMAGE: None,
        }

        await self.async_set_unique_id(normalized_mac)
        self._abort_if_unique_id_configured()

        # Migrate entries created before MAC-based unique IDs were introduced.
        if entry := self._async_entry_for_mac(normalized_mac):
            self.hass.config_entries.async_update_entry(
                entry,
                unique_id=normalized_mac,
            )
            self._abort_if_unique_id_configured()

        return self.async_create_entry(title=data[CONF_NAME], data=data)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""
        if user_input is not None:
            return await self.async_process_input(user_input, "user")

        return self._show_connection_form("user")

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Handle a flow initialized by zeroconf discovery."""
        host = discovery_info.host
        port = discovery_info.port or DEFAULT_PORT
        hostname = discovery_info.hostname
        name = discovery_info.name.split(".", 1)[0]
        discovered_mac = discovery_info.properties.get("mac")

        if hostname is None or not discovered_mac:
            return self.async_abort(reason="not_yi-hack_device")

        mac = format_mac(discovered_mac)

        _LOGGER.debug(
            "Discovered yi-hack camera at %s:%s with advertised MAC %s",
            host,
            port,
            mac,
        )

        await self.async_set_unique_id(mac)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host, CONF_PORT: port})

        # Also match entries with a stored MAC and a missing or legacy unique ID.
        if entry := self._async_entry_for_mac(mac):
            self.hass.config_entries.async_update_entry(entry, unique_id=mac)
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: host, CONF_PORT: port}
            )

        # Some camera/firmware combinations advertise a MAC from a different
        # network interface. If the host is already configured, verify its
        # identity against status.json before deciding it is a new camera.
        if verified := await self._async_verify_entry_at_host(host, port):
            entry, status_mac = verified
            _LOGGER.debug(
                "Matched advertised MAC %s to configured camera MAC %s at %s",
                mac,
                status_mac,
                host,
            )
            await self.async_set_unique_id(status_mac)
            self.hass.config_entries.async_update_entry(
                entry,
                unique_id=status_mac,
            )
            self._abort_if_unique_id_configured(
                updates={CONF_HOST: host, CONF_PORT: port}
            )

        self.context["title_placeholders"] = {"name": name}
        self.connection_data.update(
            {
                CONF_HOST: host,
                CONF_PORT: port,
                CONF_USERNAME: "",
                CONF_PASSWORD: "",
                CONF_EXTRA_ARGUMENTS: DEFAULT_EXTRA_ARGUMENTS,
                CONF_BOOST_SPEAKER: "auto",
            }
        )

        return await self.async_step_zeroconf_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a confirmation flow initiated by zeroconf."""
        if user_input is not None:
            data = {**self.connection_data, **user_input}
            return await self.async_process_input(data, "zeroconf_confirm")

        return self._show_connection_form("zeroconf_confirm")

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start reauthentication for an existing camera."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate replacement camera credentials."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            updated_data = {**entry.data, **user_input}
            _, error = await self._async_get_status(updated_data)
            if error is None:
                return self.async_update_reload_and_abort(
                    entry,
                    data=updated_data,
                )
            errors["base"] = error

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_USERNAME,
                    default=entry.data.get(CONF_USERNAME, DEFAULT_USERNAME),
                ): str,
                vol.Optional(
                    CONF_PASSWORD,
                    default=entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD),
                ): str,
            }
        )
        if user_input:
            schema = self.add_suggested_values_to_schema(schema, user_input)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
        )
