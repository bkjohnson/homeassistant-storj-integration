"""Test Storj setup process."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from collections.abc import Awaitable, Callable, Coroutine
from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.storj.const import DOMAIN

type ComponentSetup = Callable[[], Awaitable[None]]


@pytest.fixture(name="setup_integration")
async def mock_setup_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> Callable[[], Coroutine[Any, Any, None]]:
    """Fixture for setting up the component."""
    mock_config_entry.add_to_hass(hass)

    async def func() -> None:
        await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    return func


async def test_setup_success(
    hass: HomeAssistant,
    setup_integration: ComponentSetup,
) -> None:
    """Test successful setup and unload."""

    await setup_integration()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(entries[0].entry_id)
    await hass.async_block_till_done()

    assert entries[0].state is ConfigEntryState.NOT_LOADED
