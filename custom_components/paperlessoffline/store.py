"""Persistent storage for global defaults and per-frame libraries/state."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_VERSION

SAVE_DELAY = 2


KIND_PHOTO = "photo"
KIND_CARD = "card"


@dataclass
class LibraryItem:
    """One library item: a photo, or a card (no file; its overlays are its content)."""

    id: str
    filename: str
    name: str
    sha256: str
    added: str
    enabled: bool = True
    overrides: dict[str, Any] = field(default_factory=dict)
    hide_frame_overlays: bool = False
    overlays: list[OverlayDef] = field(default_factory=list)
    # Capture data from EXIF, read once when the photo is added (or by the migration).
    date: str | None = None  # ISO 8601 with offset
    location: dict[str, float] | None = None  # latitude, longitude, optionally altitude
    exif_read: bool = False
    kind: str = KIND_PHOTO
    # Cards only: "white", "black", a panel colour, or "photo" (background_photo_id).
    background: str = "white"
    background_photo_id: str | None = None

    @property
    def is_card(self) -> bool:
        """Whether this is a card rather than a photo with a file."""
        return self.kind == KIND_CARD

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LibraryItem:
        """Deserialise, ignoring unknown keys."""
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        known["overlays"] = [OverlayDef.from_dict(o) for o in known.get("overlays") or []]
        return cls(**known)

    def as_dict(self) -> dict[str, Any]:
        """Serialise."""
        return asdict(self)


@dataclass
class OverlayDef:
    """A markdown/template text box drawn over what a frame shows."""

    id: str
    name: str
    template: str
    enabled: bool = True
    show_if: str | None = None
    anchor: str = "bottom_right"
    margin: float = 0.03
    width: int | None = None
    align: str = "left"
    size: str = "m"
    text_color: str = "black"
    backing: str = "box"
    backing_color: str = "white"
    redraw: str = "change"  # "change": every wake it changed; "photo": with the photo

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OverlayDef:
        """Deserialise, ignoring unknown keys."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def as_dict(self) -> dict[str, Any]:
        """Serialise."""
        return asdict(self)


@dataclass
class Override:
    """A one-off image or text shown instead of the rotation.

    A one-off image has a file; a one-off text (``show_text``) has none, its
    ``text`` holds the template and how to draw it, and ``sha256`` hashes that.
    """

    filename: str
    name: str
    sha256: str
    overrides: dict[str, Any] = field(default_factory=dict)
    wakes_remaining: int | None = None
    shown: int = 0
    overlays: bool = True  # draw the frame's overlays on it
    # show_text: template, background, size, anchor, align.
    text: dict[str, Any] | None = None


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
    served_base_key: str | None = None
    # Overlay texts evaluated at the last wake (None = hidden) and what they were evaluated for.
    overlay_texts: dict[str, str | None] = field(default_factory=dict)
    overlay_eval_base: str | None = None
    overlay_errors: dict[str, str] = field(default_factory=dict)
    ble_status: dict[str, Any] = field(default_factory=dict)
    ble_read_at: float | None = None
    ble_error: str | None = None
    # Battery / power / orientation the frame sent with its image requests.
    wake_status: dict[str, Any] = field(default_factory=dict)
    wake_read_at: dict[str, float] = field(default_factory=dict)
    fw: str | None = None
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
        self.photos: list[LibraryItem] = []
        self.overlays: list[OverlayDef] = []
        self.state = FrameState()

    async def async_load(self) -> None:
        """Load from disk."""
        data = await self._store.async_load() or {}
        self.photos = [LibraryItem.from_dict(p) for p in data.get("photos", [])]
        self.overlays = [OverlayDef.from_dict(o) for o in data.get("overlays", [])]
        self.state = FrameState.from_dict(data.get("state", {}))

    def _data(self) -> dict[str, Any]:
        return {
            "photos": [p.as_dict() for p in self.photos],
            "overlays": [o.as_dict() for o in self.overlays],
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
