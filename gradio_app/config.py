"""
Central configuration for the FounderOS Gradio frontend.

Nothing in this file talks to the network — it just defines constants
that api.py and ui.py read from, so the whole app is reconfigurable
from one place.
"""
import os

# ---------------------------------------------------------------------------
# Backend
# ---------------------------------------------------------------------------
# Can be overridden with an env var at deploy time (Render/HF Spaces/Railway)
# without touching code. Falls back to the deployed FounderOS API.
DEFAULT_BACKEND_URL = os.environ.get(
    "FOUNDEROS_BACKEND_URL", "https://founderos-3ps7.onrender.com"
)

# Existing FastAPI routes, reused exactly as defined in auth.py / ventures.py /
# history.py / chat.py. Nothing here changes the backend's contract.
ENDPOINTS = {
    "signup": "/user",
    "login": "/login",
    "generate": "/idea_analysis",
    "history_list": "/history",
    "history_detail": "/history/{id}",
    "delete_analysis": "/analysis/{id}",
    "chat": "/analysis/{id}/",
    "health": "/docs",
}

REQUEST_TIMEOUT = 30          # seconds, normal requests
GENERATE_TIMEOUT = 90         # seconds, idea analysis can be slow (LLM + cold start)
HEALTH_TIMEOUT = 8            # seconds, backend status ping

# ---------------------------------------------------------------------------
# Blueprint sections
# ---------------------------------------------------------------------------
# CONFIRMED from ai_service.py — these are the only fields the AI is ever
# asked to produce, read straight off the two prompts:
#
#   get_prompt1() asks for:  app_type (list), core_features (list),
#                             target_users (list), db_design (dict of
#                             table -> {field: datatype})
#   get_analysis() asks for: end_points (list of
#                             {method, path, description, tables_joined}),
#                             roadmap (list of {phase, days, tasks}),
#                             risk_areas (list of {area, description})
#
# `developer_idea` isn't produced by either prompt — it's added when the
# row is saved to the DB, so it may or may not be present on the response
# from POST /idea_analysis depending on what tasks/test.py does (that file
# wasn't available to inspect). The frontend falls back to the idea text
# the user typed when this key is missing, rather than guessing.
#
# The DB column seen in chat.py's fetch_conversations was named
# `risk_factors`, not `risk_areas` — since it's unclear whether
# POST /idea_analysis returns the raw AI keys or the saved-row keys, the
# frontend treats risk_areas/risk_factors as the same section (see
# helpers.normalize_blueprint).
#
# Sections the request brief asked for that AREN'T produced by either
# prompt — Problem Statement, User Flow, Backend Architecture, AI
# Workflow, Tech Stack, Redis Usage, Security, Scaling, Future
# Improvements — are intentionally not hardcoded here. Nothing fabricates
# content for a field the backend never sends.
BLUEPRINT_SECTIONS = [
    ("developer_idea", "🚀 Startup Summary"),
    ("app_type", "🏷️ App Type"),
    ("target_users", "🎯 Target Users"),
    ("core_features", "⭐ Core Features"),
    ("db_design", "🗄 Database Design"),
    ("end_points", "🔗 API Endpoints"),
    ("roadmap", "🛣 MVP Roadmap"),
    ("risk_areas", "⚠ Risk Analysis"),
]

# ---------------------------------------------------------------------------
# Copy
# ---------------------------------------------------------------------------
APP_TITLE = "FounderOS"
APP_SUBTITLE = "AI Startup Architect"
APP_TAGLINE = "Turn a startup idea into a structured technical blueprint."
HERO_TITLE = "Draft your startup's blueprint"
HERO_SUBTITLE = (
    "Describe the idea. Get core features, a database design, an API "
    "surface, an MVP roadmap, and the risks worth knowing about — "
    "generated from your own backend."
)
PLACEHOLDER_IDEA = "e.g. An AI assistant that helps doctors summarize patient visits"

LOADING_MESSAGES = [
    "Reading your idea…",
    "Sketching the data model…",
    "Wiring up the API surface…",
    "Mapping the MVP roadmap…",
    "Weighing the risks…",
    "Almost there…",
]