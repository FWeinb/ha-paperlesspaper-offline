"""Selects: photo up next and slideshow order."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import PaperlessConfigEntry
from .const import CONF_ORDER, ORDERS
from .entity import PaperlessEntity
from .frame import FrameManager

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaperlessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up selects."""
    manager = entry.runtime_data
    async_add_entities([UpNextSelect(manager), OrderSelect(manager)])


def photo_labels(manager: FrameManager) -> dict[str, str]:
    """Unique display label -> photo id for enabled photos."""
    labels: dict[str, str] = {}
    for photo in manager.photos:
        if not photo.enabled:
            continue
        label = photo.name
        suffix = 2
        while label in labels:
            label = f"{photo.name} ({suffix})"
            suffix += 1
        labels[label] = photo.id
    return labels


class UpNextSelect(PaperlessEntity, SelectEntity):
    """The photo the frame will show on its next wake."""

    def __init__(self, manager: FrameManager) -> None:
        """Initialise."""
        self._labels: dict[str, str] = {}
        super().__init__(manager, "up_next")

    @callback
    def _update_from_manager(self) -> None:
        self._labels = photo_labels(self.manager)
        self._attr_options = list(self._labels)
        kind, photo_id = self.manager.up_next()
        self._attr_current_option = next(
            (label for label, pid in self._labels.items() if pid == photo_id and kind == "photo"),
            None,
        )
        self._attr_extra_state_attributes = {"kind": kind, "photo_id": photo_id}

    async def async_select_option(self, option: str) -> None:
        """Queue the chosen photo."""
        self.manager.async_queue_photo(self._labels[option])


class OrderSelect(PaperlessEntity, SelectEntity):
    """Sequential or shuffled slideshow."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, manager: FrameManager) -> None:
        """Initialise."""
        self._attr_options = list(ORDERS)
        super().__init__(manager, "order")

    @callback
    def _update_from_manager(self) -> None:
        self._attr_current_option = self.manager.order

    async def async_select_option(self, option: str) -> None:
        """Change the order."""
        await self._async_set_option(CONF_ORDER, option)
