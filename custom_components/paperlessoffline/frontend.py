"""Register the sidebar panel and the Lovelace card."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_BASE = f"/{DOMAIN}_static"
FRONTEND_DIR = Path(__file__).parent / "frontend"
PANEL_FILE = "paperlessoffline-panel.js"
CARD_FILE = "paperlessoffline-card.js"
PANEL_URL_PATH = DOMAIN
PANEL_ELEMENT = "paperlessoffline-panel"


def _bundle_version() -> str | None:
    """Content hash of the built bundles (cache buster), or None if not built."""
    digest = hashlib.sha256()
    for name in (PANEL_FILE, CARD_FILE):
        path = FRONTEND_DIR / name
        if not path.is_file():
            return None
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the bundles, add the admin panel and auto-load the card."""
    if "frontend" not in hass.config.components:
        _LOGGER.debug("Frontend not loaded; skipping panel registration")
        return
    version = await hass.async_add_executor_job(_bundle_version)
    if version is None:
        _LOGGER.warning("Frontend bundles missing in %s; panel not registered", FRONTEND_DIR)
        return

    # Imported lazily: only available when the frontend is set up.
    from homeassistant.components import frontend, panel_custom  # noqa: PLC0415

    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(FRONTEND_DIR), cache_headers=True)]
    )
    if PANEL_URL_PATH not in hass.data.get(frontend.DATA_PANELS, {}):
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title="Photo frames",
            sidebar_icon="mdi:image-frame",
            module_url=f"{URL_BASE}/{PANEL_FILE}?v={version}",
            require_admin=True,
            config={},
        )
    frontend.add_extra_js_url(hass, f"{URL_BASE}/{CARD_FILE}?v={version}")
