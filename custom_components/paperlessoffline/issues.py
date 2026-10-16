"""Repair issues: frames that stopped checking in or need new URLs."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.util import dt as dt_util
from yarl import URL

from .const import (
    CONF_PROVISIONED_BASE,
    CONF_PROVISIONED_TOKEN,
    DOMAIN,
    OFFLINE_GRACE_SECONDS,
    OFFLINE_MISSED_WAKES,
)
from .urls import frame_can_use_host

if TYPE_CHECKING:
    from .frame import FrameManager

ISSUE_OFFLINE = "offline"
ISSUE_REPROVISION = "reprovision"


def issue_id(kind: str, entry_id: str) -> str:
    """Issue id for a frame."""
    return f"{kind}_{entry_id}"


def overdue_since(manager: FrameManager) -> float | None:
    """Timestamp after which the frame counts as overdue, or None if never."""
    st = manager.state
    if st.last_request is None:
        reference = manager.entry.created_at.timestamp()
        first_sleep = manager.interval
    else:
        reference = st.last_request
        # The last settings fetch told the frame how long to sleep (incl. quiet hours).
        first_sleep = st.last_timeout or manager.interval
    return (
        reference
        + first_sleep
        + (OFFLINE_MISSED_WAKES - 1) * manager.interval
        + OFFLINE_GRACE_SECONDS
    )


def is_overdue(manager: FrameManager, now: float | None = None) -> bool:
    """Whether the frame has missed several expected wakes."""
    deadline = overdue_since(manager)
    return deadline is not None and (now or time.time()) > deadline


def reprovision_reason(manager: FrameManager, current_base: str | None) -> str | None:
    """Why the frame needs new URLs: "token", "url" or None."""
    data = manager.entry.data
    provisioned_token = data.get(CONF_PROVISIONED_TOKEN)
    if provisioned_token is not None and provisioned_token != manager.token:
        return "token"
    provisioned_base = data.get(CONF_PROVISIONED_BASE)
    if current_base and provisioned_base and provisioned_base != current_base:
        if manager.url_host is not None:
            # The user chose the address explicitly: apply it at the next chance.
            return "url"
        host = URL(provisioned_base).host
        if host and not frame_can_use_host(host):
            # e.g. a loopback URL written earlier: it can never work for the frame.
            return "url"
    if (
        current_base
        and provisioned_base
        and provisioned_base != current_base
        and is_overdue(manager)
    ):
        return "url"
    return None


@callback
def async_update_issues(
    hass: HomeAssistant, manager: FrameManager, current_base: str | None
) -> None:
    """Create or clear the frame's repair issues."""
    entry_id = manager.entry.entry_id
    reason = reprovision_reason(manager, current_base)
    last_seen = (
        dt_util.as_local(dt_util.utc_from_timestamp(manager.state.last_request)).strftime(
            "%Y-%m-%d %H:%M"
        )
        if manager.state.last_request
        else "-"
    )
    placeholders = {"name": manager.display_name, "last_seen": last_seen}
    if reason:
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id(ISSUE_REPROVISION, entry_id),
            is_fixable=True,
            is_persistent=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=f"reprovision_{reason}",
            translation_placeholders=placeholders,
            data={"entry_id": entry_id},
        )
        ir.async_delete_issue(hass, DOMAIN, issue_id(ISSUE_OFFLINE, entry_id))
        return
    ir.async_delete_issue(hass, DOMAIN, issue_id(ISSUE_REPROVISION, entry_id))
    if is_overdue(manager):
        ir.async_create_issue(
            hass,
            DOMAIN,
            issue_id(ISSUE_OFFLINE, entry_id),
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="offline",
            translation_placeholders=placeholders,
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, issue_id(ISSUE_OFFLINE, entry_id))


@callback
def async_delete_issues(hass: HomeAssistant, entry_id: str) -> None:
    """Remove all issues of a frame."""
    for kind in (ISSUE_OFFLINE, ISSUE_REPROVISION):
        ir.async_delete_issue(hass, DOMAIN, issue_id(kind, entry_id))
