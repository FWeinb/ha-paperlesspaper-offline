"""Integration-wide runtime data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.hass_dict import HassKey

from .const import DOMAIN

if TYPE_CHECKING:
    from .frame import FrameManager
    from .store import GlobalStore


@dataclass
class DomainData:
    """Shared state: global defaults and loaded frames."""

    global_store: GlobalStore
    entries: dict[str, FrameManager] = field(default_factory=dict)
    tokens: dict[str, FrameManager] = field(default_factory=dict)


DATA_KEY: HassKey[DomainData] = HassKey(DOMAIN)


def get_manager(hass: HomeAssistant, entry_id: str) -> FrameManager:
    """Return the manager of a loaded frame or raise a validation error."""
    if (data := hass.data.get(DATA_KEY)) is None or entry_id not in data.entries:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="frame_not_loaded",
            translation_placeholders={"entry_id": entry_id},
        )
    return data.entries[entry_id]
