"""Template evaluation for overlays, with the helpers templates can call."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

# HA weather conditions to MDI icons (as the frontend shows them).
WEATHER_ICONS = {
    "clear-night": "weather-night",
    "cloudy": "weather-cloudy",
    "exceptional": "alert-circle-outline",
    "fog": "weather-fog",
    "hail": "weather-hail",
    "lightning": "weather-lightning",
    "lightning-rainy": "weather-lightning-rainy",
    "partlycloudy": "weather-partly-cloudy",
    "pouring": "weather-pouring",
    "rainy": "weather-rainy",
    "snowy": "weather-snowy",
    "snowy-rainy": "weather-snowy-rainy",
    "sunny": "weather-sunny",
    "windy": "weather-windy",
    "windy-variant": "weather-windy-variant",
}

MONTHS = {
    "en": [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ],
    "de": [
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ],
}  # fmt: skip
WEEKDAYS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "de": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
}
DATE_PRESETS = ("short", "long", "month_year", "weekday", "time")
FALSY = {"", "false", "0", "no", "off", "none", "unknown", "unavailable"}


class FrameVars:
    """``frame`` as seen by templates."""

    def __init__(self, name: str) -> None:
        """Initialise."""
        self.name = name

    def __str__(self) -> str:
        """Render as the frame's name."""
        return self.name


class PhotoVars:
    """``photo`` as seen by templates (``None`` where no photo is shown)."""

    def __init__(self, name: str) -> None:
        """Initialise."""
        self.name = name

    def __str__(self) -> str:
        """Render as the photo's name."""
        return self.name


def _language(hass: HomeAssistant) -> str:
    return "de" if (hass.config.language or "").startswith("de") else "en"


def weather_icon(state: Any) -> str:
    """Inline icon markup for an HA weather condition (or "")."""
    icon = WEATHER_ICONS.get(str(state or "").strip().lower())
    return f":mdi:{icon}:" if icon else ""


def make_entity_icon(hass: HomeAssistant) -> Callable[[str], str]:
    """``entity_icon(entity_id)``: an icon explicitly set on the entity."""

    def entity_icon(entity_id: str) -> str:
        icon = None
        if (state := hass.states.get(str(entity_id))) is not None:
            icon = state.attributes.get("icon")
        if not icon and (entry := er.async_get(hass).async_get(str(entity_id))):
            icon = entry.icon or entry.original_icon
        if isinstance(icon, str) and icon.startswith("mdi:"):
            return f":{icon}:"
        return ""

    return entity_icon


def _to_datetime(value: Any) -> datetime | date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return dt_util.as_local(value) if value.tzinfo else value
    if isinstance(value, date):
        return value
    if isinstance(value, int | float):
        return dt_util.as_local(dt_util.utc_from_timestamp(value))
    text = str(value)
    if (parsed := dt_util.parse_datetime(text)) is not None:
        return dt_util.as_local(parsed) if parsed.tzinfo else parsed
    if (parsed_date := dt_util.parse_date(text)) is not None:
        return parsed_date
    return None


def make_date_local(hass: HomeAssistant) -> Callable[..., str]:
    """``date_local(value, preset)``: dates with names in HA's language."""

    def date_local(value: Any = None, preset: str = "long") -> str:
        moment = _to_datetime(dt_util.now() if value is None else value)
        if moment is None:
            return ""
        lang = _language(hass)
        month = MONTHS[lang][moment.month - 1]
        weekday = WEEKDAYS[lang][moment.weekday()]
        if preset == "time":
            return moment.strftime("%H:%M") if isinstance(moment, datetime) else ""
        if preset == "weekday":
            return weekday
        if preset == "month_year":
            return f"{month} {moment.year}"
        if preset == "short":
            if lang == "de":
                return f"{moment.day:02d}.{moment.month:02d}.{moment.year}"
            return f"{month[:3]} {moment.day}, {moment.year}"
        if lang == "de":
            return f"{weekday}, {moment.day}. {month} {moment.year}"
        return f"{weekday}, {month} {moment.day}, {moment.year}"

    return date_local


def template_variables(
    hass: HomeAssistant, frame_name: str, photo_name: str | None = None
) -> dict[str, Any]:
    """Variables and helper functions available to overlay templates.

    ``photo_name`` is None where no photo is shown (one-off images, the placeholder).
    """
    return {
        "frame": FrameVars(frame_name),
        "photo": PhotoVars(photo_name) if photo_name is not None else None,
        "weather_icon": weather_icon,
        "entity_icon": make_entity_icon(hass),
        "date_local": make_date_local(hass),
    }


def render_text(hass: HomeAssistant, source: str, variables: dict[str, Any]) -> str:
    """Render a template to text. Raises ``TemplateError`` on failure."""
    try:
        return str(Template(source, hass).async_render(variables, parse_result=False))
    except TemplateError:
        raise
    except Exception as err:
        raise TemplateError(err) from err


def is_truthy(text: str) -> bool:
    """How a "show if" result is interpreted."""
    return text.strip().lower() not in FALSY
