"""Button to skip to the next photo."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PaperlessConfigEntry
from .entity import PaperlessEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaperlessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up buttons."""
    async_add_entities([SkipButton(entry.runtime_data, "skip")])


class SkipButton(PaperlessEntity, ButtonEntity):
    """Skip the photo that is up next."""

    async def async_press(self) -> None:
        """Skip."""
        self.manager.async_skip()
