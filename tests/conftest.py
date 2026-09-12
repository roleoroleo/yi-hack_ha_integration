"""Shared test fixtures for yi-hack."""

from __future__ import annotations

from types import MappingProxyType
from typing import Any

import pytest_asyncio
from homeassistant.config_entries import ConfigEntries, ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.yi_hack.const import DOMAIN


@pytest_asyncio.fixture
async def hass(tmp_path) -> HomeAssistant:
    """Return a minimal Home Assistant instance."""
    instance = HomeAssistant(str(tmp_path))
    instance.config_entries = ConfigEntries(instance, {})
    yield instance
    await instance.async_stop()


def add_config_entry(
    hass: HomeAssistant,
    *,
    title: str,
    unique_id: str | None,
    data: dict[str, Any],
) -> ConfigEntry:
    """Add a config entry without starting its platforms."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=title,
        data=data,
        source="user",
        unique_id=unique_id,
        discovery_keys=MappingProxyType({}),
        subentries_data=None,
        options={},
        pref_disable_new_entities=None,
        pref_disable_polling=None,
    )
    hass.config_entries._entries[entry.entry_id] = entry
    return entry
