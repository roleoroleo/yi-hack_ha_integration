"""Data update coordinator for yi-hack cameras."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .common import YiHackAuthenticationError, YiHackError, get_status
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=60)


class YiHackDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate status.json updates for one camera."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=UPDATE_INTERVAL,
            always_update=False,
        )
        self.config_entry = config_entry

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch camera status data."""
        try:
            status = await self.hass.async_add_executor_job(
                get_status, self.config_entry.data
            )
        except YiHackAuthenticationError as err:
            raise ConfigEntryAuthFailed from err
        except YiHackError as err:
            raise UpdateFailed(
                f"Unable to get status from {self.config_entry.data[CONF_HOST]}"
            ) from err

        return status
