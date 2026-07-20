"""
Visual identity for FounderOS.

Design direction: "blueprint" — FounderOS turns a loose idea into a
structured technical document, so the UI borrows from architectural
blueprints: a cool ink-blue ground, a fine grid, and a warm amber pin
used only for the one action that matters (Generate). Everything else
stays quiet: off-white cards, generous whitespace, restrained motion.

Type: "Space Grotesk" for display (geometric, drafting-table feel),
"Inter" for body copy, "JetBrains Mono" for anything code/schema-shaped
(API endpoints, DB design) — reinforcing that this a technical, not a
marketing, tool.
"""
import gradio as gr

# Palette -----------------------------------------------------------------
INK = "#15233B"          # primary text / deep blueprint navy
INK_SOFT = "#4A5A78"      # secondary text
PAPER = "#F6F7FA"         # app background — cool, not cream
CARD = "#FFFFFF"
LINE = "#E2E6EE"          # hairline borders
BLUEPRINT = "#2A4E8C"     # primary brand blue
BLUEPRINT_DARK = "#1B3A6B"
MINT = "#16A788"          # success / positive accent
AMBER = "#F0A63A"         # single CTA accent — used sparingly
DANGER = "#D64545"


founderos_theme = gr.themes.Base(
    primary_hue=gr.themes.colors.blue,
    secondary_hue=gr.themes.colors.amber,
    neutral_hue=gr.themes.colors.slate,
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
).set(
    body_background_fill=PAPER,
    body_background_fill_dark="#0D1524",
    background_fill_primary=CARD,
    background_fill_primary_dark="#131E33",
    background_fill_secondary=PAPER,
    background_fill_secondary_dark="#0D1524",
    border_color_primary=LINE,
    border_color_primary_dark="#243654",
    block_background_fill=CARD,
    block_background_fill_dark="#131E33",
    block_border_color=LINE,
    block_border_color_dark="#243654",
    block_radius="16px",
    block_shadow="0 1px 2px rgba(21, 35, 59, 0.04), 0 8px 24px rgba(21, 35, 59, 0.04)",
    block_label_text_color=INK_SOFT,
    block_title_text_color=INK,
    button_primary_background_fill=BLUEPRINT,
    button_primary_background_fill_hover=BLUEPRINT_DARK,
    button_primary_text_color="#FFFFFF",
    button_primary_border_color=BLUEPRINT,
    button_secondary_background_fill=CARD,
    button_secondary_background_fill_hover=PAPER,
    button_secondary_text_color=INK,
    button_secondary_border_color=LINE,
    button_large_radius="12px",
    button_small_radius="10px",
    input_background_fill=CARD,
    input_background_fill_dark="#0D1524",
    input_border_color=LINE,
    input_radius="12px",
    body_text_color=INK,
    body_text_color_subdued=INK_SOFT,
    link_text_color=BLUEPRINT,
    shadow_spread="2px",
)


def load_css() -> str:
    """Reads styles.css next to this file. Kept as a function (rather than
    a module-level constant) so app.py always gets the current contents
    even if styles.css is edited without restarting from a fresh import
    cache."""
    import os
    css_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "styles.css")
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""
