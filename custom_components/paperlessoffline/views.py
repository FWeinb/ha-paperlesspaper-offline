"""HTTP endpoints: polled by the frames, and used by the panel."""

from __future__ import annotations

import base64
import binascii
import hmac
import json
from pathlib import Path
from typing import TYPE_CHECKING

from aiohttp import BodyPartReader, hdrs, web
from homeassistant.components.http import KEY_HASS, KEY_HASS_USER, HomeAssistantView
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_AUTH_ENABLED,
    CONF_AUTH_PASSWORD,
    CONF_AUTH_USER,
    DOMAIN,
    MAX_UPLOAD_BYTES,
)
from .data import DATA_KEY
from .frame import IMAGE_PATH, http_date

if TYPE_CHECKING:
    from .frame import FrameManager


def _manager_for(request: web.Request, token: str) -> FrameManager | None:
    hass = request.app[KEY_HASS]
    if (data := hass.data.get(DATA_KEY)) is None:
        return None
    for known, manager in data.tokens.items():
        if hmac.compare_digest(known, token):
            return manager
    return None


def _auth_ok(request: web.Request, manager: FrameManager) -> bool:
    opts = manager.options
    if not opts.get(CONF_AUTH_ENABLED):
        return True
    header = request.headers.get(hdrs.AUTHORIZATION, "")
    if not header.lower().startswith("basic "):
        return False
    try:
        user, _, password = base64.b64decode(header[6:]).decode().partition(":")
    except (binascii.Error, UnicodeDecodeError):
        return False
    return hmac.compare_digest(user, opts.get(CONF_AUTH_USER, "")) and hmac.compare_digest(
        password, opts.get(CONF_AUTH_PASSWORD, "")
    )


class FrameImageView(HomeAssistantView):
    """Serve the current pre-dithered image for a frame."""

    url = IMAGE_PATH
    name = f"api:{DOMAIN}:image"
    requires_auth = False

    async def get(self, request: web.Request, token: str) -> web.StreamResponse:
        """Handle the frame's image download."""
        manager = _manager_for(request, token)
        if manager is None:
            return web.Response(status=404)
        if not _auth_ok(request, manager):
            return web.Response(
                status=401, headers={hdrs.WWW_AUTHENTICATE: 'Basic realm="paperlessoffline"'}
            )
        bmp, last_modified = await manager.async_handle_image_request(dict(request.query))
        return web.Response(
            body=bmp,
            content_type="image/bmp",
            headers={
                hdrs.LAST_MODIFIED: http_date(last_modified),
                hdrs.CACHE_CONTROL: "no-cache",
            },
        )


class FrameSettingsView(HomeAssistantView):
    """Serve the settings JSON for a frame.

    The firmware fetches this without credentials, so only the token protects it.
    """

    url = "/api/paperlessoffline/{token}/settings.json"
    name = f"api:{DOMAIN}:settings"
    requires_auth = False

    async def get(self, request: web.Request, token: str) -> web.StreamResponse:
        """Handle the frame's settings download."""
        manager = _manager_for(request, token)
        if manager is None:
            return web.Response(status=404)
        download_url = str(request.url.with_path(manager.image_path()).with_query(None))
        payload, last_modified = await manager.async_handle_settings_request(
            dict(request.query), download_url, request.headers.get(hdrs.IF_MODIFIED_SINCE)
        )
        headers = {hdrs.LAST_MODIFIED: http_date(last_modified), hdrs.CACHE_CONTROL: "no-cache"}
        if payload is None:
            return web.Response(status=304, headers=headers)
        return web.Response(
            text=json.dumps(payload), content_type="application/json", headers=headers
        )


class PhotoPreviewView(HomeAssistantView):
    """Serve dithered previews of library photos to authenticated users."""

    url = "/api/paperlessoffline/preview/{entry_id}/{photo_id}.png"
    name = f"api:{DOMAIN}:preview"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, photo_id: str) -> web.StreamResponse:
        """Return the preview PNG."""
        hass = request.app[KEY_HASS]
        data = hass.data.get(DATA_KEY)
        manager = data.entries.get(entry_id) if data else None
        if manager is None or manager.get_photo(photo_id) is None:
            return web.Response(status=404)
        png = await manager.async_photo_preview(photo_id)
        if png is None:
            return web.Response(status=404)
        return web.Response(body=png, content_type="image/png")


class PhotoThumbView(HomeAssistantView):
    """Serve small thumbnails of library originals to authenticated users."""

    url = "/api/paperlessoffline/thumb/{entry_id}/{photo_id}.jpg"
    name = f"api:{DOMAIN}:thumb"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, photo_id: str) -> web.StreamResponse:
        """Return the thumbnail JPEG."""
        hass = request.app[KEY_HASS]
        data = hass.data.get(DATA_KEY)
        manager = data.entries.get(entry_id) if data else None
        if manager is None or manager.get_photo(photo_id) is None:
            return web.Response(status=404)
        try:
            size = int(request.query.get("size", 320))
            rotation = int(request.query.get("rotation", 0))
        except ValueError:
            return web.Response(status=400)
        jpeg = await manager.async_thumbnail(photo_id, size, rotation)
        return web.Response(body=jpeg, content_type="image/jpeg")


class PhotoUploadView(HomeAssistantView):
    """Accept multipart photo uploads from the panel (admins only)."""

    url = "/api/paperlessoffline/upload/{entry_id}"
    name = f"api:{DOMAIN}:upload"
    requires_auth = True

    async def post(self, request: web.Request, entry_id: str) -> web.StreamResponse:
        """Store every uploaded file field as a photo."""
        hass = request.app[KEY_HASS]
        if not request[KEY_HASS_USER].is_admin:
            return web.Response(status=403)
        data = hass.data.get(DATA_KEY)
        manager = data.entries.get(entry_id) if data else None
        if manager is None:
            return web.Response(status=404)
        reader = await request.multipart()
        added: list[dict[str, str]] = []
        errors: list[dict[str, str]] = []
        while (part := await reader.next()) is not None:
            if not isinstance(part, BodyPartReader) or not part.filename:
                continue
            buf = bytearray()
            too_large = False
            while chunk := await part.read_chunk(65536):
                buf.extend(chunk)
                if len(buf) > MAX_UPLOAD_BYTES:
                    too_large = True
                    break
            if too_large:
                errors.append({"file": part.filename, "error": "larger than 50 MB"})
                continue
            try:
                photo = await manager.async_add_photo(bytes(buf), Path(part.filename).stem)
            except HomeAssistantError as err:
                errors.append({"file": part.filename, "error": str(err)})
                continue
            added.append({"photo_id": photo.id, "name": photo.name})
        return self.json({"added": added, "errors": errors})
