"""
Pure helper functions: turning backend JSON into Markdown/tables/cards,
building downloadable files, formatting dates. No network calls and no
Gradio component creation here — just data in, data out.

Field shapes are matched against ai_service.py's two prompts
(get_prompt1 / get_analysis) — the only place that defines what the AI
is asked to return:

    app_type       -> list[str]
    core_features  -> list[str]
    target_users   -> list[str]
    db_design      -> dict[str, dict[str, str]]  (table -> {field: type})
    end_points     -> list[{method, path, description, tables_joined}]
    roadmap        -> list[{phase, days, tasks: list[str]}]
    risk_areas     -> list[{area, description}]

`developer_idea` is NOT part of this payload — it only exists on
/history rows (from the DB). ui.py fills it in from the typed idea text
before storing the blueprint in state, so every function below can
assume it's present.

Every formatter still degrades gracefully if a value doesn't match the
confirmed shape (plain string, differently-keyed dict, etc.) rather
than crashing.
"""
import re
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import config


# ---------------------------------------------------------------------------
# Value -> Markdown (generic fallback for unrecognized fields)
# ---------------------------------------------------------------------------
def value_to_markdown(value: Any) -> str:
    """Render a field's value as Markdown regardless of whether the
    backend sent a string, a list, or a nested dict."""
    if value is None or value == "":
        return "_Not provided._"

    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                inner = ", ".join(f"**{k}**: {v}" for k, v in item.items())
                lines.append(f"- {inner}")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines) if lines else "_Not provided._"

    if isinstance(value, dict):
        lines = [f"- **{k}**: {v}" for k, v in value.items()]
        return "\n".join(lines) if lines else "_Not provided._"

    return str(value)


# ---------------------------------------------------------------------------
# app_type / target_users / core_features -> list[str]
# ---------------------------------------------------------------------------
def list_to_bullets(value) -> str:
    """Clean Markdown bullet list. Handles the confirmed shape (a JSON
    list of strings) and falls back to splitting a single string if the
    backend ever sends prose instead."""
    if value is None or value == "":
        return "_Not provided._"
    if isinstance(value, list):
        items = [str(v) for v in value if str(v).strip()]
    else:
        raw = str(value)
        parts = re.split(r"\n+|(?<=[.;])\s+(?=[A-Z])", raw)
        items = [p.strip(" -\u2022") for p in parts if p.strip(" -\u2022")]
    if not items:
        return "_Not provided._"
    return "\n".join(f"- {item}" for item in items)


def list_to_pills_html(value) -> str:
    """app_type reads better as compact pills than a bullet list since
    it's a short list of category tags."""
    if not value:
        return "<span style='color:var(--fos-ink-soft);'>Not provided.</span>"
    items = value if isinstance(value, list) else [value]
    pills = "".join(f'<span class="fos-pill">{str(v)}</span>' for v in items if str(v).strip())
    return pills or "<span style='color:var(--fos-ink-soft);'>Not provided.</span>"


# ---------------------------------------------------------------------------
# db_design -> dict[table, dict[field, type]]
# ---------------------------------------------------------------------------
def db_design_to_table(value) -> Tuple[List[str], List[List[str]]]:
    """Returns (headers, rows) for a gr.Dataframe: Table | Fields.
    Confirmed shape is a dict of {table_name: {field: datatype}}; a
    nested field dict is flattened into 'field (type), field (type)'."""
    headers = ["Table", "Fields"]
    if not value:
        return headers, [["\u2014", "Not provided."]]

    def _format_fields(fields) -> str:
        if isinstance(fields, dict):
            return ", ".join(f"{fname} ({ftype})" for fname, ftype in fields.items())
        if isinstance(fields, list):
            return ", ".join(str(f) for f in fields)
        return str(fields)

    if isinstance(value, dict):
        rows = [[str(table), _format_fields(fields)] for table, fields in value.items()]
        return headers, rows

    if isinstance(value, list):
        rows = []
        for item in value:
            if isinstance(item, dict):
                name = item.get("table") or item.get("name") or next(iter(item.values()), "")
                fields = item.get("fields") or item.get("columns") or item.get("description") or ""
                rows.append([str(name), _format_fields(fields)])
            else:
                rows.append([str(item), ""])
        return headers, rows or [["\u2014", "Not provided."]]

    return headers, [["Schema", str(value)]]


# ---------------------------------------------------------------------------
# end_points -> list[{method, path, description, tables_joined}]
# ---------------------------------------------------------------------------
def endpoints_to_table(value) -> Tuple[List[str], List[List[str]]]:
    """Returns (headers, rows) for a gr.Dataframe: Method | Endpoint |
    Description | Tables Joined — matching get_analysis()'s confirmed
    end_points shape exactly."""
    headers = ["Method", "Endpoint", "Description", "Tables Joined"]
    if not value:
        return headers, [["\u2014", "Not provided.", "", ""]]

    items = value if isinstance(value, list) else [value]
    rows = []
    for item in items:
        if isinstance(item, dict):
            method = item.get("method", "")
            endpoint = item.get("path") or item.get("endpoint") or ""
            desc = item.get("description", "")
            tables = item.get("tables_joined", [])
            tables_str = ", ".join(tables) if isinstance(tables, list) else str(tables or "")
            rows.append([str(method).upper(), str(endpoint), str(desc), tables_str])
        else:
            text = str(item).strip()
            match = re.match(r"^(GET|POST|PUT|PATCH|DELETE)\s+(.*)$", text, re.IGNORECASE)
            if match:
                rows.append([match.group(1).upper(), match.group(2), "", ""])
            else:
                rows.append(["", text, "", ""])
    return headers, rows or [["\u2014", "Not provided.", "", ""]]


# ---------------------------------------------------------------------------
# roadmap -> list[{phase, days, tasks: list[str]}]
# ---------------------------------------------------------------------------
def roadmap_to_markdown(value) -> str:
    """Numbered phase blocks with day range and task bullets, matching
    get_analysis()'s confirmed roadmap shape."""
    if not value:
        return "_Not provided._"

    if isinstance(value, list) and value and isinstance(value[0], dict):
        parts = []
        for i, phase in enumerate(value, start=1):
            title = phase.get("phase") or f"Phase {i}"
            days = phase.get("days")
            header = f"**{i}. {title}**" + (f" \u2014 {days}" if days else "")
            parts.append(header)
            tasks = phase.get("tasks") or []
            if isinstance(tasks, list):
                for task in tasks:
                    parts.append(f"   - {task}")
            elif tasks:
                parts.append(f"   - {tasks}")
            parts.append("")
        return "\n".join(parts).strip()

    steps = value if isinstance(value, list) else _split_sentences(str(value))
    return "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps)) or "_Not provided._"


# ---------------------------------------------------------------------------
# risk_areas -> list[{area, description}]
# ---------------------------------------------------------------------------
def risk_items(value) -> List[Tuple[str, str]]:
    """Returns a list of (area, description) tuples, matching
    get_analysis()'s confirmed risk_areas shape, for one card per risk."""
    if not value:
        return []
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                area = item.get("area") or item.get("name") or "Risk"
                desc = item.get("description") or ""
                out.append((str(area), str(desc)))
            else:
                out.append(("Risk", str(item)))
        return out
    return [("Risk", str(value))]


def _split_sentences(raw: str) -> List[str]:
    parts = re.split(r"\n+|(?<=[.;])\s+(?=[A-Z])", raw)
    return [p.strip(" -\u2022") for p in parts if p.strip(" -\u2022")]


# ---------------------------------------------------------------------------
# Full blueprint -> Markdown (for Copy / Download)
# ---------------------------------------------------------------------------
def blueprint_to_sections(data: Dict) -> List[Dict[str, str]]:
    """Turn a blueprint dict into an ordered list of {key, label,
    markdown} for known fields, using the shape-specific formatter for
    each, then appends anything extra the backend sent that isn't
    recognized — so unexpected backend fields show up instead of
    silently disappearing."""
    sections = []
    seen = set()

    formatters = {
        "app_type": list_to_bullets,
        "target_users": list_to_bullets,
        "core_features": list_to_bullets,
        "db_design": lambda v: _table_to_markdown(*db_design_to_table(v)),
        "end_points": lambda v: _table_to_markdown(*endpoints_to_table(v)),
        "roadmap": roadmap_to_markdown,
        "risk_areas": lambda v: "\n\n".join(f"**{a}**\n{d}" for a, d in risk_items(v)) or "_Not provided._",
    }

    for key, label in config.BLUEPRINT_SECTIONS:
        if key in data:
            fmt = formatters.get(key, value_to_markdown)
            sections.append({"key": key, "label": label, "markdown": fmt(data[key])})
            seen.add(key)

    skip_keys = {"id", "analysis_id", "user_id", "created_at", "messages"}
    for key, value in data.items():
        if key in seen or key in skip_keys or not value:
            continue
        label = "🗂️ " + key.replace("_", " ").title()
        sections.append({"key": key, "label": label, "markdown": value_to_markdown(value)})
    return sections


def _table_to_markdown(headers: List[str], rows: List[List[str]]) -> str:
    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + " | ".join("---" for _ in headers) + " |"
    body_rows = ["| " + " | ".join(str(c).replace("\n", " ") for c in row) + " |" for row in rows]
    return "\n".join([header_row, sep_row] + body_rows)


def blueprint_to_full_markdown(data: Dict, title: Optional[str] = None) -> str:
    sections = blueprint_to_sections(data)
    parts = [f"# {title or 'FounderOS Blueprint'}", ""]
    created_at = data.get("created_at")
    if created_at:
        parts.append(f"_Generated {format_datetime(created_at)}_\n")
    for s in sections:
        parts.append(f"## {s['label']}")
        parts.append(s["markdown"])
        parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
def markdown_to_file(markdown_text: str, filename_hint: str = "founderos-blueprint") -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", filename_hint).strip("-").lower() or "founderos-blueprint"
    path = tempfile.NamedTemporaryFile(
        delete=False, suffix=".md", prefix=f"{safe}-"
    ).name
    with open(path, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    return path


def markdown_to_pdf(markdown_text: str, filename_hint: str = "founderos-blueprint") -> str:
    """Small, dependency-light Markdown -> PDF renderer built on fpdf2.
    Doesn't draw real tables — markdown table rows ('| a | b |') are
    flattened to 'a — b' so they're still readable on the page."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    safe = re.sub(r"[^a-zA-Z0-9_-]+", "-", filename_hint).strip("-").lower() or "founderos-blueprint"

    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    pdf.set_margins(18, 18, 18)

    def cell(text: str, height: float):
        pdf.multi_cell(0, height, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    for raw_line in markdown_text.split("\n"):
        line = raw_line.rstrip()

        if line.startswith("|"):
            stripped = line.replace("|", "").replace(" ", "")
            if set(stripped) <= {"-", ":"} and stripped:
                continue  # markdown table separator row
            cells = [c.strip() for c in line.strip("|").split("|")]
            line = " \u2014 ".join(cells)

        clean = re.sub(r"\*\*(.*?)\*\*", r"\1", line).replace("_", "").replace("`", "")
        clean = clean.encode("latin-1", "replace").decode("latin-1")

        if clean.startswith("# "):
            pdf.set_font("Helvetica", "B", 18)
            pdf.ln(4)
            cell(clean[2:], 9)
            pdf.ln(2)
        elif clean.startswith("## "):
            pdf.set_font("Helvetica", "B", 13)
            pdf.ln(3)
            cell(clean[3:], 7)
        elif clean.startswith("- "):
            pdf.set_font("Helvetica", "", 11)
            cell(f"  - {clean[2:]}", 6)
        elif clean == "":
            pdf.ln(2)
        else:
            pdf.set_font("Helvetica", "", 11)
            cell(clean, 6)

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix=f"{safe}-").name
    pdf.output(path)
    return path


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def format_datetime(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    try:
        return value.strftime("%b %d, %Y \u00b7 %I:%M %p")
    except Exception:
        return str(value)


def truncate(text: str, length: int = 90) -> str:
    text = (text or "").strip()
    return text if len(text) <= length else text[: length - 1].rstrip() + "\u2026"