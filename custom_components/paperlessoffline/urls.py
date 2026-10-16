"""URLs the frame uses to reach Home Assistant."""

from __future__ import annotations

import ipaddress
import re

from homeassistant.core import HomeAssistant
from homeassistant.helpers.network import NoURLAvailableError, get_url
from yarl import URL

from .const import IMAGE_PATH, SETTINGS_PATH

URL_HOST_AUTO = "auto"
_HOST_RE = re.compile(r"^[A-Za-z0-9]([A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")


async def async_frame_base_url(hass: HomeAssistant, host: str | None = None) -> str | None:
    """HA's local URL as the frame can use it, or None if there is none.

    - With ``host`` (an IP or name chosen by the user), the URL points at HA's
      own web server at that address: HA's port, and https if HA serves https.
    - Otherwise HA's internal URL is used as configured (including its port),
      unless its host is unusable for the frame: loopback addresses (they point
      at the frame itself), ``localhost`` or ``*.local`` names (the ESP32
      firmware has no mDNS resolver). Those are replaced by this machine's LAN
      IP address, again with HA's own port and scheme.

    The port appears in the URL whenever it isn't the scheme's default (80 for
    http, 443 for https).
    """
    try:
        base = URL(get_url(hass, allow_external=False, allow_cloud=False, prefer_external=False))
    except NoURLAvailableError:
        return None
    if host and host != URL_HOST_AUTO:
        return _ha_server_url(hass, host, base)
    if base.host and not frame_can_use_host(base.host):
        # Imported lazily: the network integration is always loaded in a real
        # install, but keep this module importable without it.
        from homeassistant.components import network  # noqa: PLC0415

        try:
            ip = await network.async_get_source_ip(hass)
        except Exception:
            return str(base.origin())
        return _ha_server_url(hass, ip, base)
    return str(base.origin())


def _ha_server_url(hass: HomeAssistant, host: str, fallback: URL) -> str:
    """URL of HA's own web server at ``host`` (port and scheme from HA's HTTP config)."""
    api = hass.config.api
    if api is None:  # HTTP not set up (tests): keep the configured URL's scheme and port
        return str(fallback.with_host(host).origin())
    scheme = "https" if api.use_ssl else "http"
    return str(URL.build(scheme=scheme, host=host, port=api.port).origin())


def frame_urls(base_url: str, token: str) -> dict[str, str]:
    """Image and settings URLs for a token."""
    return {
        "image_url": base_url + IMAGE_PATH.format(token=token),
        "settings_url": base_url + SETTINGS_PATH.format(token=token),
    }


def frame_can_use_host(host: str) -> bool:
    """Whether a frame on the LAN can reach HA at ``host``."""
    host = host.strip("[]").lower()
    if host == "localhost" or host.endswith((".local", ".localhost")):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True  # a normal DNS name
    return not (address.is_loopback or address.is_unspecified or address.is_link_local)


def valid_host(host: str) -> bool:
    """Whether ``host`` is a plausible IP address or DNS name for the frame."""
    host = host.strip()
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return bool(_HOST_RE.match(host)) and ".." not in host
    return True


async def async_ha_addresses(hass: HomeAssistant) -> list[str]:
    """IPv4 addresses of this machine that a frame on the LAN could use."""
    # Imported lazily: always loaded in a real install.
    from homeassistant.components import network  # noqa: PLC0415

    try:
        adapters = await network.async_get_adapters(hass)
    except Exception:
        return []
    addresses: list[str] = []
    # Adapters HA itself uses for the network come first.
    for adapter in sorted(adapters, key=lambda a: (not a["enabled"], not a["default"])):
        for ipv4 in adapter["ipv4"]:
            address = ipv4["address"]
            if frame_can_use_host(address) and address not in addresses:
                addresses.append(address)
    return addresses
