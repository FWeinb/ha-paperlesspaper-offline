"""Rendered previews of what a frame shows."""

from __future__ import annotations

from homeassistant.components.image import ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import PaperlessConfigEntry
from .entity import PaperlessEntity
from .frame import FrameManager

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PaperlessConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up preview images."""
    manager = entry.runtime_data
    async_add_entities(
        [FramePreview(hass, manager, "showing"), FramePreview(hass, manager, "up_next")]
    )


class FramePreview(PaperlessEntity, ImageEntity):
    """Dithered preview as it looks on the panel."""

    _attr_content_type = "image/png"

    def __init__(self, hass: HomeAssistant, manager: FrameManager, which: str) -> None:
        """Initialise."""
        self._which = which
        self._content_key: str | None = None
        ImageEntity.__init__(self, hass)
        PaperlessEntity.__init__(self, manager, f"preview_{which}")

    def _current_key(self) -> str | None:
        manager = self.manager
        if self._which == "showing":
            return manager.state.served_key
        kind, photo_id = manager.up_next()
        if kind == "photo" and (photo := manager.get_photo(photo_id)):
            return manager.photo_key(photo)
        if kind == "override" and manager.state.override:
            return f"override:{manager.state.override.sha256}:{manager.state.override.overrides}"
        return manager.placeholder_key()

    @callback
    def _update_from_manager(self) -> None:
        key = self._current_key()
        if key != self._content_key:
            self._content_key = key
            self._attr_image_last_updated = dt_util.utcnow()

    async def async_image(self) -> bytes | None:
        """Return the preview PNG."""
        return await self.manager.async_preview(self._which)
