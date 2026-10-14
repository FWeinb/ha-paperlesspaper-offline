"""Persistent storage for global defaults and per-frame libraries/state."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION

SAVE_DELAY = 2


@dataclass
class Photo:
    """One photo in a frame's library."""

    id: str
    filename: str
    name: str
    sha256: str
    added: str
    enabled: bool = True
    overrides: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        """Serialise."""
        return asdict(self)


@dataclass
class Override:
    """A one-off image shown instead of the rotation."""

    filename: str
    name: str
    sha256: str
    overrides: dict[str, Any] = field(default_factory=dict)
    wakes_remaining: int | None = None
    shown: int = 0


@dataclass
class FrameState:
    """Runtime state of a frame that survives restarts."""

    current_id: str | None = None
    current_kind: str | None = None  # "photo" | "override" | "placeholder"
    queued_id: str | None = None
    bag: list[str] = field(default_factory=list)
    override: Override | None = None
    last_request: float | None = None
    last_wake: float | None = None
    wake_count: int = 0
    served_key: str | None = None
    served_lm: int = 0
    served_name: str | None = None
    settings_hash: str | None = None
    settings_lm: int = 0
    fetched_device_hash: str | None = None
    last_settings_fetch: float | None = None
    last_timeout: int | None = None
    ble_status: dict[str, Any] = field(default_factory=dict)
    ble_read_at: float | None = None
    ble_error: str | None = None
    telemetry: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FrameState:
        """Deserialise, ignoring unknown keys."""
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        if isinstance(known.get("override"), dict):
            known["override"] = Override(**known["override"])
        return cls(**known)


class GlobalStore:
    """Global render defaults, shared by all frames."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialise."""
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.global")
        self.defaults: dict[str, Any] = {}

    async def async_load(self) -> None:
        """Load from disk."""
        data = await self._store.async_load() or {}
        self.defaults = data.get("defaults", {})

    async def async_set_defaults(self, defaults: dict[str, Any]) -> None:
        """Replace the global defaults."""
        self.defaults = defaults
        await self._store.async_save({"defaults": self.defaults})


class FrameStore:
    """Library and state of one frame."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialise."""
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}")
        self.photos: list[Photo] = []
        self.state = FrameState()

    async def async_load(self) -> None:
        """Load from disk."""
        data = await self._store.async_load() or {}
        self.photos = [Photo(**p) for p in data.get("photos", [])]
        self.state = FrameState.from_dict(data.get("state", {}))

    def _data(self) -> dict[str, Any]:
        return {
            "photos": [p.as_dict() for p in self.photos],
            "state": asdict(self.state),
        }

    def schedule_save(self) -> None:
        """Save soon."""
        self._store.async_delay_save(self._data, SAVE_DELAY)

    async def async_save(self) -> None:
        """Save now."""
        await self._store.async_save(self._data())

    async def async_remove(self) -> None:
        """Delete the stored data."""
        await self._store.async_remove()
