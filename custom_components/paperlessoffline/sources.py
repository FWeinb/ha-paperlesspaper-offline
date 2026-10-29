"""Fetch image bytes from the sources services accept."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from aiohttp import ClientError, ClientTimeout
from homeassistant.components import media_source
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url

from .const import DOMAIN, MAX_UPLOAD_BYTES

ATTR_FILE_PATH = "file_path"
ATTR_URL = "url"
ATTR_MEDIA = "media_content_id"
ATTR_ENTITY = "image_entity_id"
SOURCE_KEYS = (ATTR_FILE_PATH, ATTR_URL, ATTR_MEDIA, ATTR_ENTITY)


def _error(key: str, **placeholders: str) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders or None,
    )


async def async_fetch_source(hass: HomeAssistant, data: dict) -> tuple[bytes, str]:
    """Return (bytes, suggested name) for exactly one source in ``data``."""
    given = [key for key in SOURCE_KEYS if data.get(key)]
    if len(given) != 1:
        raise _error("exactly_one_source")
    key = given[0]
    value = data[key]
    if isinstance(value, dict):  # media selector value
        value = value.get("media_content_id", "")
    if key == ATTR_FILE_PATH:
        return await _async_read_path(hass, Path(value))
    if key == ATTR_URL:
        return await async_download(hass, value), _name_from_url(value)
    if key == ATTR_ENTITY:
        try:
            content = await async_entity_image(hass, value)
        except (HomeAssistantError, KeyError) as err:
            raise _error("source_failed", error=str(err)) from err
        state = hass.states.get(value)
        name = state.name if state else value
        return content, str(name)
    return await _async_media_source(hass, value)


async def async_entity_image(hass: HomeAssistant, entity_id: str) -> bytes:
    """The current picture of a camera or image entity."""
    # Imported lazily: these components (and their requirements) are only
    # loaded when the user has such entities.
    if entity_id.split(".", 1)[0] == "camera":
        from homeassistant.components import camera  # noqa: PLC0415

        return (await camera.async_get_image(hass, entity_id)).content
    from homeassistant.components import image  # noqa: PLC0415

    return (await image.async_get_image(hass, entity_id)).content


async def _async_read_path(hass: HomeAssistant, path: Path) -> tuple[bytes, str]:
    if not hass.config.is_allowed_path(str(path)):
        raise _error("path_not_allowed", path=str(path))

    def _read() -> bytes:
        if path.stat().st_size > MAX_UPLOAD_BYTES:
            raise _error("image_too_large")
        return path.read_bytes()

    try:
        data = await hass.async_add_executor_job(_read)
    except OSError as err:
        raise _error("source_failed", error=str(err)) from err
    return data, path.stem


async def async_download(hass: HomeAssistant, url: str) -> bytes:
    """Download an image, refusing more than MAX_UPLOAD_BYTES; a path is on HA itself."""
    if url.startswith("/"):
        url = get_url(hass, allow_external=False) + url
    session = async_get_clientsession(hass)
    try:
        async with session.get(url, timeout=ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            if (resp.content_length or 0) > MAX_UPLOAD_BYTES:
                raise _error("image_too_large")
            data = bytearray()
            async for chunk in resp.content.iter_chunked(65536):
                data.extend(chunk)
                if len(data) > MAX_UPLOAD_BYTES:
                    raise _error("image_too_large")
            return bytes(data)
    except (ClientError, TimeoutError) as err:
        raise _error("source_failed", error=str(err)) from err


async def _async_media_source(hass: HomeAssistant, media_id: str) -> tuple[bytes, str]:
    try:
        resolved = await media_source.async_resolve_media(hass, media_id, None)
    except HomeAssistantError as err:
        raise _error("source_failed", error=str(err)) from err
    name = media_id.rstrip("/").rsplit("/", 1)[-1]
    if resolved.path is not None:
        data, _ = await _async_read_path_unchecked(hass, resolved.path)
        return data, Path(name).stem
    return await async_download(hass, resolved.url), Path(name).stem


async def _async_read_path_unchecked(hass: HomeAssistant, path: Path) -> tuple[bytes, str]:
    def _read() -> bytes:
        if path.stat().st_size > MAX_UPLOAD_BYTES:
            raise _error("image_too_large")
        return path.read_bytes()

    try:
        return await hass.async_add_executor_job(_read), path.stem
    except OSError as err:
        raise _error("source_failed", error=str(err)) from err


def _name_from_url(url: str) -> str:
    tail = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    return Path(tail).stem or "image"
