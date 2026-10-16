"""Diagnostics."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import REDACTED, async_redact_data
from homeassistant.core import HomeAssistant

from . import PaperlessConfigEntry
from .const import CONF_AUTH_PASSWORD, CONF_AUTH_USER, CONF_PROVISIONED_TOKEN, CONF_TOKEN

TO_REDACT = {CONF_TOKEN, CONF_PROVISIONED_TOKEN, CONF_AUTH_PASSWORD, CONF_AUTH_USER}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: PaperlessConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a frame."""
    manager = entry.runtime_data
    return {
        "data": async_redact_data(dict(entry.data), TO_REDACT),
        "options": async_redact_data(dict(entry.options), TO_REDACT),
        "global_defaults": manager.global_store.defaults,
        "panel": asdict(manager.panel),
        "canvas": asdict(manager.canvas),
        "photos": [
            {
                "id": p.id,
                "kind": p.kind,
                "enabled": p.enabled,
                "overrides": p.overrides,
                "file": p.filename,
                "date": p.date,
                "location": REDACTED if p.location else None,
                **({"background": p.background} if p.is_card else {}),
            }
            for p in manager.photos
        ],
        "state": asdict(manager.state),
        "pending": manager.pending_changes(),
        "up_next": manager.up_next(),
        "storage": await hass.async_add_executor_job(manager.storage_usage),
    }
