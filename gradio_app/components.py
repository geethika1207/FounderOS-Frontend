"""
Reusable HTML/Markdown fragments. These return strings for gr.HTML /
gr.Markdown components — no state, no side effects, easy to reuse
across Home / History / Saved Ideas / Profile.
"""
from typing import Dict, List, Optional

import config
import helpers


def sidebar_brand_html() -> str:
    return f"""
    <div class="fos-brand">
        <div class="fos-brand-mark">F</div>
        <div class="fos-brand-text">
            <div class="fos-brand-title">{config.APP_TITLE}</div>
            <div class="fos-brand-sub">{config.APP_SUBTITLE}</div>
        </div>
    </div>
    """


def header_html(status_online: Optional[bool]) -> str:
    if status_online is None:
        status_class, label = "", "Checking backend…"
    elif status_online:
        status_class, label = "online", "Backend Connected"
    else:
        status_class, label = "offline", "Backend Offline"

    return f"""
    <div class="fos-header">
        <div>
            <p class="fos-header-title">{config.APP_TITLE}</p>
            <p class="fos-header-tag">{config.APP_TAGLINE}</p>
        </div>
        <div class="fos-status {status_class}">
            <span class="fos-status-dot"></span>{label}
        </div>
    </div>
    """


def hero_html() -> str:
    return f"""
    <div class="fos-hero">
        <span class="fos-hero-eyebrow">AI Startup Architect</span>
        <h1>{config.HERO_TITLE}</h1>
        <p>{config.HERO_SUBTITLE}</p>
    </div>
    """


def empty_state_html(title: str, subtitle: str) -> str:
    return f"""
    <div class="fos-empty">
        <div class="fos-empty-title">{title}</div>
        <div>{subtitle}</div>
    </div>
    """


def history_card_markdown(item: Dict) -> str:
    idea = helpers.truncate(item.get("developer_idea", "Untitled idea"), 90)
    app_type = item.get("app_type") or "—"
    created = helpers.format_datetime(item.get("created_at"))
    msg_count = item.get("message_count", 0)
    return (
        f"**{idea}**\n\n"
        f"`{app_type}` · {created} · {msg_count} follow-up message(s)"
    )


def stat_tiles_html(stats: List[Dict[str, str]]) -> str:
    tiles = "".join(
        f"""<div class="fos-stat">
                <div class="fos-stat-value">{s['value']}</div>
                <div class="fos-stat-label">{s['label']}</div>
            </div>"""
        for s in stats
    )
    return f'<div class="fos-stat-grid">{tiles}</div>'
