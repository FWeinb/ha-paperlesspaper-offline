"""Setup / unload tests."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant


async def test_setup_and_unload(hass: HomeAssistant, loaded_entry) -> None:
    assert loaded_entry.state is ConfigEntryState.LOADED
    assert hass.states.get("binary_sensor.kitchen_in_sync") is not None
    assert hass.states.get("select.kitchen_up_next") is not None
    assert await hass.config_entries.async_unload(loaded_entry.entry_id)
    await hass.async_block_till_done()
    assert loaded_entry.state is ConfigEntryState.NOT_LOADED
