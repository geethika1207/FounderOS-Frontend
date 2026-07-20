"""
Layout and event wiring for the FounderOS Gradio frontend.

Structure:
  - An auth screen (Log in / Sign up) shown until a token is obtained.
  - An app shell (sidebar + header + pages) shown once authenticated.
  - Pages are gr.Column groups whose visibility is toggled by the sidebar
    nav — no page reload, no routing library needed.
  - Anything data-dependent (results, history list, saved grid, profile
    stats) is built with @gr.render so it reacts to state changes
    instead of being wired one field at a time.

No business logic lives here — every backend call goes through api.py,
every payload/response shape is exactly what the existing FastAPI routes
already define. The blueprint fields rendered below (app_type,
core_features, target_users, db_design, end_points, roadmap, risk_areas)
are the confirmed shape from ai_service.py's two Groq prompts.
"""
import threading
import time

import gradio as gr

import api
import components
import config
import helpers
import theme

PAGE_NAMES = ["home", "history", "saved", "profile", "settings", "about"]
HISTORY_PAGE_SIZE = 6


def build_app() -> gr.Blocks:
    with gr.Blocks(
        theme=theme.founderos_theme,
        css=theme.load_css(),
        title=f"{config.APP_TITLE} — {config.APP_SUBTITLE}",
        fill_width=True,
    ) as demo:

        # ------------------------------------------------------------------
        # Global state (per-browser-session)
        # ------------------------------------------------------------------
        token_state = gr.State(None)
        email_state = gr.State(None)
        base_url_state = gr.State(config.DEFAULT_BACKEND_URL)
        status_state = gr.State(None)
        history_state = gr.State([])
        current_blueprint_state = gr.State(None)
        chat_state = gr.State([])
        history_search_state = gr.State("")
        history_page_state = gr.State(0)

        # ==================================================================
        # AUTH SCREEN
        # ==================================================================
        with gr.Column(visible=True, elem_id="fos-auth") as auth_col:
            gr.HTML(f"""
                <div style="text-align:center; padding: 48px 0 8px 0;">
                    <div class="fos-brand-mark" style="margin:0 auto 14px auto;">F</div>
                    <h1 class="fos-display" style="font-size:26px; margin-bottom:6px;">{config.APP_TITLE}</h1>
                    <p style="color:var(--fos-ink-soft);">{config.APP_TAGLINE}</p>
                </div>
            """)
            with gr.Column(elem_classes=["fos-card"], scale=1, min_width=380):
                with gr.Tabs():
                    with gr.Tab("Log in"):
                        login_email = gr.Textbox(label="Email", placeholder="you@startup.com")
                        login_password = gr.Textbox(label="Password", type="password")
                        login_btn = gr.Button("Log in", variant="primary", size="lg")
                    with gr.Tab("Sign up"):
                        signup_email = gr.Textbox(label="Email", placeholder="you@startup.com")
                        signup_password = gr.Textbox(label="Password", type="password")
                        signup_confirm = gr.Textbox(label="Confirm password", type="password")
                        signup_btn = gr.Button("Create account", variant="primary", size="lg")
                gr.Markdown(
                    "<div style='text-align:center; color:var(--fos-ink-soft); font-size:12.5px; "
                    "margin-top:6px;'>Connects to your FounderOS backend — configurable later under Settings.</div>"
                )

        # ==================================================================
        # APP SHELL
        # ==================================================================
        with gr.Column(visible=False, elem_id="fos-app") as app_col:
            with gr.Row(equal_height=False):

                # ---------------- Sidebar ----------------
                with gr.Column(scale=0, min_width=230, elem_classes=["fos-sidebar"]):
                    gr.HTML(components.sidebar_brand_html())
                    nav_home = gr.Button("🏠  Home", elem_classes=["fos-nav-btn"])
                    nav_generate = gr.Button("✨  Generate Startup", elem_classes=["fos-nav-btn"])
                    nav_history = gr.Button("🕘  History", elem_classes=["fos-nav-btn"])
                    nav_saved = gr.Button("⭐  Saved Ideas", elem_classes=["fos-nav-btn"])
                    nav_profile = gr.Button("👤  Profile", elem_classes=["fos-nav-btn"])
                    nav_settings = gr.Button("⚙️  Settings", elem_classes=["fos-nav-btn"])
                    nav_about = gr.Button("ℹ️  About", elem_classes=["fos-nav-btn"])
                    gr.Markdown("&nbsp;")
                    logout_btn = gr.Button("↩ Log out", size="sm")

                # ---------------- Main column ----------------
                with gr.Column(scale=1):
                    header_html_comp = gr.HTML(components.header_html(None))
                    page_cols = []

                    # ---------- HOME ----------
                    with gr.Column(visible=True) as home_col:
                        gr.HTML(components.hero_html())

                        idea_box = gr.Textbox(
                            label="Describe your startup idea",
                            placeholder=config.PLACEHOLDER_IDEA,
                            lines=3,
                        )
                        with gr.Row():
                            industry_dd = gr.Dropdown(
                                ["AI", "Healthcare", "Finance", "Education", "Agriculture",
                                 "SaaS", "E-commerce", "Cybersecurity", "Other"],
                                label="Industry", value="AI",
                            )
                            stage_dd = gr.Dropdown(
                                ["Idea", "Prototype", "MVP", "Scaling"],
                                label="Startup stage", value="Idea",
                            )
                            market_dd = gr.Dropdown(
                                ["Global", "India", "USA", "Japan", "Europe"],
                                label="Target market", value="Global",
                            )
                        with gr.Row():
                            generate_btn = gr.Button("✨ Generate Blueprint", variant="primary", size="lg")
                            clear_btn = gr.Button("Clear", size="lg")

                        loading_md = gr.Markdown(visible=False)

                        with gr.Column(visible=True) as results_wrap:
                            @gr.render(inputs=[current_blueprint_state, chat_state])
                            def _render_results(blueprint, chat_msgs):
                                if not blueprint:
                                    return

                                title = blueprint.get("developer_idea") or "Untitled idea"
                                app_types = blueprint.get("app_type")
                                type_display = ", ".join(app_types) if isinstance(app_types, list) else (app_types or "App")

                                md_text = helpers.blueprint_to_full_markdown(blueprint, title=title)
                                md_path = helpers.markdown_to_file(md_text, title)
                                pdf_path = helpers.markdown_to_pdf(md_text, title)

                                gr.HTML(f"""
                                    <div style="margin: 26px 0 4px 0;">
                                        <h1 class="fos-display" style="font-size:24px; margin:0;">Startup Blueprint</h1>
                                        <div style="color:var(--fos-ink-soft); font-size:12.5px; margin-top:2px;">
                                            #{blueprint.get('id', '—')} · {type_display}
                                        </div>
                                    </div>
                                """)

                                # ---- Startup Summary ----
                                with gr.Group(elem_classes=["fos-card"]):
                                    gr.Markdown("#### 🚀 Startup Summary")
                                    gr.Markdown(title)
                                    if blueprint.get("app_type"):
                                        gr.HTML(helpers.list_to_pills_html(blueprint["app_type"]))

                                # ---- Target Users ----
                                if blueprint.get("target_users"):
                                    with gr.Accordion("🎯 Target Users", open=True, elem_classes=["fos-result-accordion"]):
                                        gr.Markdown(helpers.list_to_bullets(blueprint["target_users"]))

                                # ---- Core Features ----
                                if blueprint.get("core_features"):
                                    with gr.Accordion("⭐ Core Features", open=True, elem_classes=["fos-result-accordion"]):
                                        gr.Markdown(helpers.list_to_bullets(blueprint["core_features"]))

                                # ---- Database Design (table) ----
                                if blueprint.get("db_design"):
                                    with gr.Accordion("🗄 Database Design", open=False, elem_classes=["fos-result-accordion"]):
                                        headers, rows = helpers.db_design_to_table(blueprint["db_design"])
                                        gr.Dataframe(
                                            value=rows, headers=headers, interactive=False,
                                            wrap=True, show_row_numbers=False,
                                        )

                                # ---- API Endpoints (table) ----
                                if blueprint.get("end_points"):
                                    with gr.Accordion("🔗 API Endpoints", open=False, elem_classes=["fos-result-accordion"]):
                                        headers, rows = helpers.endpoints_to_table(blueprint["end_points"])
                                        gr.Dataframe(
                                            value=rows, headers=headers, interactive=False,
                                            wrap=True, show_row_numbers=False,
                                        )

                                # ---- MVP Roadmap (numbered phases) ----
                                if blueprint.get("roadmap"):
                                    with gr.Accordion("🛣 MVP Roadmap", open=False, elem_classes=["fos-result-accordion"]):
                                        gr.Markdown(helpers.roadmap_to_markdown(blueprint["roadmap"]))

                                # ---- Risk Analysis (cards) ----
                                if blueprint.get("risk_areas"):
                                    with gr.Accordion("⚠ Risk Analysis", open=False, elem_classes=["fos-result-accordion"]):
                                        for area, desc in helpers.risk_items(blueprint["risk_areas"]):
                                            with gr.Group(elem_classes=["fos-card"]):
                                                gr.Markdown(f"**{area}**\n\n{desc}")

                                # ---- Anything else the backend sent that isn't one of the
                                # known fields above still renders, so new backend fields
                                # show up instead of silently disappearing.
                                known_keys = {
                                    "id", "analysis_id", "user_id", "created_at", "messages",
                                    "developer_idea", "app_type", "target_users", "core_features",
                                    "db_design", "end_points", "roadmap", "risk_areas",
                                }
                                for key, value in blueprint.items():
                                    if key in known_keys or not value:
                                        continue
                                    label = "🗂️ " + key.replace("_", " ").title()
                                    with gr.Accordion(label, open=False, elem_classes=["fos-result-accordion"]):
                                        gr.Markdown(helpers.value_to_markdown(value))

                                hidden_md = gr.Textbox(value=md_text, visible=False)
                                share_text = gr.Textbox(
                                    value=f"Check out my startup blueprint from FounderOS: {title}",
                                    visible=False,
                                )

                                with gr.Row():
                                    copy_btn = gr.Button("📋 Copy", size="sm")
                                    dl_md_btn = gr.DownloadButton("⬇️ Markdown", value=md_path, size="sm")
                                    dl_pdf_btn = gr.DownloadButton("⬇️ PDF", value=pdf_path, size="sm")
                                    save_btn = gr.Button("💾 Save", size="sm")
                                    share_btn = gr.Button("🔗 Share", size="sm")
                                    again_btn = gr.Button("↻ Generate Again", size="sm")
                                    clear_again_btn = gr.Button("✕ Clear", size="sm")

                                copy_btn.click(
                                    fn=None, inputs=[hidden_md], outputs=[],
                                    js="(md) => { navigator.clipboard.writeText(md); }",
                                )
                                share_btn.click(
                                    fn=None, inputs=[share_text], outputs=[],
                                    js="(t) => { navigator.clipboard.writeText(t); }",
                                )
                                save_btn.click(
                                    fn=lambda: gr.Info(
                                        "Already saved — FounderOS stores every generated blueprint automatically."
                                    ),
                                    outputs=[],
                                )
                                again_btn.click(
                                    fn=lambda: (None, []),
                                    outputs=[current_blueprint_state, chat_state],
                                )
                                clear_again_btn.click(
                                    fn=lambda: (None, [], ""),
                                    outputs=[current_blueprint_state, chat_state, idea_box],
                                )

                                # ---- Follow-up chat (POST /analysis/{id}/) ----
                                gr.HTML('<div class="fos-section-label">Ask a follow-up</div>')
                                chat_display = gr.Chatbot(
                                    value=_flatten_chat(chat_msgs),
                                    height=260,
                                    show_label=False,
                                )
                                with gr.Row():
                                    question_box = gr.Textbox(
                                        placeholder="Ask about pricing, scaling, tech choices…",
                                        show_label=False, scale=4,
                                    )
                                    send_btn = gr.Button("Send", variant="primary", scale=1)

                                def _ask(question, bp, msgs, token, base_url):
                                    if not question or not question.strip():
                                        raise gr.Error("Type a question first.")
                                    if not bp or not bp.get("id"):
                                        raise gr.Error("Generate a blueprint first.")
                                    try:
                                        resp = api.send_chat_message(base_url, token, bp["id"], question.strip())
                                    except api.ApiError as e:
                                        raise gr.Error(e.message)
                                    answer = resp.get("answer", "") if isinstance(resp, dict) else str(resp)
                                    new_msgs = msgs + [{"question": question.strip(), "answer": answer}]
                                    return new_msgs, ""

                                send_btn.click(
                                    _ask,
                                    inputs=[question_box, current_blueprint_state, chat_state,
                                            token_state, base_url_state],
                                    outputs=[chat_state, question_box],
                                )
                                question_box.submit(
                                    _ask,
                                    inputs=[question_box, current_blueprint_state, chat_state,
                                            token_state, base_url_state],
                                    outputs=[chat_state, question_box],
                                )

                    page_cols.append(home_col)

                    # ---------- HISTORY ----------
                    with gr.Column(visible=False) as history_col:
                        gr.Markdown("### History")
                        with gr.Row():
                            history_search_box = gr.Textbox(
                                placeholder="Search your past ideas…", show_label=False, scale=4,
                            )
                            history_refresh_btn = gr.Button("↻ Refresh", scale=1)

                        history_search_box.change(
                            lambda q: (q, 0), inputs=[history_search_box],
                            outputs=[history_search_state, history_page_state],
                        )

                        with gr.Column():
                            @gr.render(inputs=[history_state, history_search_state, history_page_state])
                            def _render_history(items, search, page):
                                filtered = _filter_history(items, search)
                                if not filtered:
                                    gr.HTML(components.empty_state_html(
                                        "No blueprints yet",
                                        "Generate your first one from Home, or try a different search.",
                                    ))
                                    return

                                total_pages = max(1, (len(filtered) - 1) // HISTORY_PAGE_SIZE + 1)
                                page = max(0, min(page, total_pages - 1))
                                start = page * HISTORY_PAGE_SIZE
                                page_items = filtered[start:start + HISTORY_PAGE_SIZE]

                                for item in page_items:
                                    with gr.Group(elem_classes=["fos-history-card"]):
                                        gr.Markdown(components.history_card_markdown(item))
                                        with gr.Row():
                                            open_btn = gr.Button("Open", size="sm")
                                            del_btn = gr.Button("Delete", size="sm", variant="stop")
                                        open_btn.click(
                                            _make_open_handler(item["id"]),
                                            inputs=[token_state, base_url_state],
                                            outputs=[current_blueprint_state, chat_state],
                                        ).then(lambda: _switch_page("home"), outputs=page_cols)
                                        del_btn.click(
                                            _make_delete_handler(item["id"]),
                                            inputs=[token_state, base_url_state],
                                            outputs=[history_state],
                                        )

                                if total_pages > 1:
                                    with gr.Row():
                                        prev_btn = gr.Button("← Prev", size="sm", interactive=(page > 0))
                                        gr.Markdown(
                                            f"<div style='text-align:center; padding-top:6px; color:var(--fos-ink-soft); font-size:12.5px;'>"
                                            f"Page {page + 1} of {total_pages}</div>"
                                        )
                                        next_btn = gr.Button("Next →", size="sm", interactive=(page < total_pages - 1))
                                        prev_btn.click(lambda p=page: max(0, p - 1), outputs=[history_page_state])
                                        next_btn.click(lambda p=page: p + 1, outputs=[history_page_state])

                    page_cols.append(history_col)

                    # ---------- SAVED IDEAS ----------
                    with gr.Column(visible=False) as saved_col:
                        gr.Markdown(
                            "### Saved Ideas\n"
                            "<span style='color:var(--fos-ink-soft); font-size:13px;'>"
                            "Every generated blueprint is saved automatically — this is your full library.</span>"
                        )

                        @gr.render(inputs=[history_state])
                        def _render_saved(items):
                            if not items:
                                gr.HTML(components.empty_state_html(
                                    "Nothing saved yet", "Generated blueprints will show up here as cards.",
                                ))
                                return
                            for row_start in range(0, len(items), 3):
                                row_items = items[row_start:row_start + 3]
                                with gr.Row():
                                    for item in row_items:
                                        with gr.Column(elem_classes=["fos-history-card"], min_width=220):
                                            gr.Markdown(components.history_card_markdown(item))
                                            open_btn = gr.Button("Open full report", size="sm")
                                            open_btn.click(
                                                _make_open_handler(item["id"]),
                                                inputs=[token_state, base_url_state],
                                                outputs=[current_blueprint_state, chat_state],
                                            ).then(lambda: _switch_page("home"), outputs=page_cols)

                    page_cols.append(saved_col)

                    # ---------- PROFILE ----------
                    with gr.Column(visible=False) as profile_col:
                        gr.Markdown("### Profile")

                        @gr.render(inputs=[history_state, email_state])
                        def _render_profile(items, email):
                            total_ideas = len(items)
                            total_followups = sum(i.get("message_count", 0) for i in items)
                            gr.HTML(f"""
                                <div class="fos-card" style="margin-bottom:16px;">
                                    <div style="font-weight:600; color:var(--fos-ink);">{email or 'Signed in'}</div>
                                    <div style="font-size:12.5px; color:var(--fos-ink-soft);">FounderOS account</div>
                                </div>
                            """)
                            gr.HTML(components.stat_tiles_html([
                                {"value": str(total_ideas), "label": "Ideas generated"},
                                {"value": str(total_followups), "label": "Follow-up questions asked"},
                                {"value": "—", "label": "Last login (not tracked by backend)"},
                            ]))
                            if items:
                                gr.Markdown("<div class='fos-section-label'>Recent</div>")
                                for item in items[:5]:
                                    gr.Markdown(components.history_card_markdown(item))

                    page_cols.append(profile_col)

                    # ---------- SETTINGS ----------
                    with gr.Column(visible=False) as settings_col:
                        gr.Markdown("### Settings")
                        with gr.Column(elem_classes=["fos-card"]):
                            backend_url_box = gr.Textbox(
                                label="Backend URL", value=config.DEFAULT_BACKEND_URL,
                            )
                            with gr.Row():
                                test_conn_btn = gr.Button("Save & test connection", variant="primary", size="sm")
                            settings_status_md = gr.Markdown()

                        with gr.Column(elem_classes=["fos-card"]):
                            theme_radio = gr.Radio(
                                ["System", "Light", "Dark"], value="System", label="Theme",
                            )
                            theme_radio.change(
                                fn=None, inputs=[theme_radio], outputs=[],
                                js="""(t) => {
                                    const url = new URL(window.location);
                                    if (t === 'System') { url.searchParams.delete('__theme'); }
                                    else { url.searchParams.set('__theme', t.toLowerCase()); }
                                    window.location.href = url.toString();
                                }""",
                            )

                        with gr.Column(elem_classes=["fos-card"]):
                            gr.Markdown("Ending your session clears your token from this browser tab.")
                            reset_btn = gr.Button("Reset session", variant="stop", size="sm")

                    page_cols.append(settings_col)

                    # ---------- ABOUT ----------
                    with gr.Column(visible=False) as about_col:
                        gr.Markdown(f"""
### About {config.APP_TITLE}

**{config.APP_SUBTITLE}** — turns a one-line startup idea into a structured
technical blueprint: app type, target users, core features, a database
design, an API surface, an MVP roadmap, and the risks worth flagging early.

This interface is a pure frontend: every action here calls the existing
FastAPI backend (`/user`, `/login`, `/idea_analysis`, `/history`,
`/history/{{id}}`, `/analysis/{{id}}`, `/analysis/{{id}}/`) exactly as it's
already defined, over REST. No business logic lives in this UI.

**Stack:** Gradio (frontend) · FastAPI · PostgreSQL · Groq / LLaMA (analysis generation)
                        """)

                    page_cols.append(about_col)

        # ==============================================================
        # Wiring
        # ==============================================================
        def _do_login(base_url, email, password):
            if not email or not password:
                raise gr.Error("Enter both email and password.")
            try:
                resp = api.login(base_url, email, password)
            except api.ApiError as e:
                raise gr.Error(e.message)
            token = (resp or {}).get("access_token")
            if not token:
                raise gr.Error("Login succeeded but the backend didn't return a token.")
            gr.Info("Logged in.")
            return token, email, gr.update(visible=False), gr.update(visible=True)

        def _do_signup(base_url, email, password, confirm):
            if not email or not password:
                raise gr.Error("Enter an email and a password.")
            if password != confirm:
                raise gr.Error("Passwords don't match.")
            try:
                api.signup(base_url, email, password)
            except api.ApiError as e:
                raise gr.Error(e.message)
            try:
                resp = api.login(base_url, email, password)
            except api.ApiError as e:
                raise gr.Error(f"Account created, but automatic log in failed: {e.message}")
            token = (resp or {}).get("access_token")
            gr.Info("Account created.")
            return token, email, gr.update(visible=False), gr.update(visible=True)

        def _do_logout():
            gr.Info("Logged out.")
            return (None, None, [], None, [], gr.update(visible=True), gr.update(visible=False))

        def _refresh_history(token, base_url):
            if not token:
                return []
            try:
                return api.get_history(base_url, token, limit=100)
            except api.ApiError as e:
                gr.Warning(e.message)
                return []

        def _refresh_status(base_url):
            online = api.check_health(base_url)
            return online, components.header_html(online)

        login_btn.click(
            _do_login, inputs=[base_url_state, login_email, login_password],
            outputs=[token_state, email_state, auth_col, app_col],
        ).then(_refresh_history, inputs=[token_state, base_url_state], outputs=[history_state])

        signup_btn.click(
            _do_signup, inputs=[base_url_state, signup_email, signup_password, signup_confirm],
            outputs=[token_state, email_state, auth_col, app_col],
        ).then(_refresh_history, inputs=[token_state, base_url_state], outputs=[history_state])

        logout_btn.click(
            _do_logout,
            outputs=[token_state, email_state, history_state, current_blueprint_state,
                     chat_state, auth_col, app_col],
        )

        nav_home.click(lambda: _switch_page("home"), outputs=page_cols)
        nav_generate.click(lambda: _switch_page("home"), outputs=page_cols)
        nav_history.click(
            lambda: _switch_page("history"), outputs=page_cols,
        ).then(_refresh_history, inputs=[token_state, base_url_state], outputs=[history_state]
        ).then(lambda: 0, outputs=[history_page_state])
        nav_saved.click(
            lambda: _switch_page("saved"), outputs=page_cols,
        ).then(_refresh_history, inputs=[token_state, base_url_state], outputs=[history_state])
        nav_profile.click(
            lambda: _switch_page("profile"), outputs=page_cols,
        ).then(_refresh_history, inputs=[token_state, base_url_state], outputs=[history_state])
        nav_settings.click(lambda: _switch_page("settings"), outputs=page_cols)
        nav_about.click(lambda: _switch_page("about"), outputs=page_cols)

        def _save_backend_url(url):
            return url or config.DEFAULT_BACKEND_URL

        test_conn_btn.click(
            _save_backend_url, inputs=[backend_url_box], outputs=[base_url_state],
        ).then(
            _refresh_status, inputs=[base_url_state], outputs=[status_state, header_html_comp],
        ).then(
            lambda online: "🟢 Connected" if online else "🔴 Couldn't reach that URL — check it and try again.",
            inputs=[status_state], outputs=[settings_status_md],
        )

        reset_btn.click(
            _do_logout,
            outputs=[token_state, email_state, history_state, current_blueprint_state,
                     chat_state, auth_col, app_col],
        )

        def _do_generate(base_url, token, idea, industry, stage, market):
            if not token:
                raise gr.Error("Please log in first.")
            if not idea or not idea.strip():
                raise gr.Error("Please describe your startup idea first.")

            # The backend's /idea_analysis endpoint (ventures.UserIdea) only
            # accepts a single `idea` string — there's no separate
            # industry/stage/market field in its schema. The extra context
            # picked in the UI is folded into that same idea string rather
            # than sent as backend parameters that don't exist.
            context_bits = [b for b in [
                f"Industry: {industry}" if industry else "",
                f"Stage: {stage}" if stage else "",
                f"Target market: {market}" if market else "",
            ] if b]
            full_idea = idea.strip()
            if context_bits:
                full_idea += " (" + ", ".join(context_bits) + ")"

            box = {}

            def worker():
                try:
                    box["data"] = api.generate_idea_analysis(base_url, token, full_idea)
                except api.ApiError as e:
                    box["error"] = e

            t = threading.Thread(target=worker, daemon=True)
            t.start()

            i = 0
            while t.is_alive():
                msg = config.LOADING_MESSAGES[i % len(config.LOADING_MESSAGES)]
                yield (
                    gr.update(value=f"⏳ {msg}", visible=True),
                    gr.update(interactive=False),
                    gr.update(visible=False),
                    gr.update(),
                    gr.update(),
                )
                i += 1
                time.sleep(1.4)
            t.join()

            if "error" in box:
                yield (
                    gr.update(value="", visible=False),
                    gr.update(interactive=True),
                    gr.update(visible=True),
                    gr.update(),
                    gr.update(),
                )
                raise gr.Error(box["error"].message)

            resp = box.get("data") or {}
            if resp.get("error"):
                yield (
                    gr.update(value="", visible=False),
                    gr.update(interactive=True),
                    gr.update(visible=True),
                    gr.update(),
                    gr.update(),
                )
                raise gr.Error(str(resp["error"]))

            # Confirmed shape: {"status": "completed", "result": {...}, "db_id": <int>}
            # `result` has no `developer_idea` key (ai_service.py's prompts
            # never produce one) — it's filled in here from the typed idea
            # so every downstream renderer can rely on it being present.
            result = resp.get("result") or {}
            blueprint = dict(result)
            blueprint["id"] = resp.get("db_id")
            if not blueprint.get("developer_idea"):
                blueprint["developer_idea"] = idea.strip()

            yield (
                gr.update(value="", visible=False),
                gr.update(interactive=True),
                gr.update(visible=True),
                blueprint,
                [],
            )

        generate_btn.click(
            _do_generate,
            inputs=[base_url_state, token_state, idea_box, industry_dd, stage_dd, market_dd],
            outputs=[loading_md, generate_btn, results_wrap, current_blueprint_state, chat_state],
        )

        clear_btn.click(
            lambda: ("", gr.update(visible=False), None, [], gr.update(visible=True)),
            outputs=[idea_box, loading_md, current_blueprint_state, chat_state, results_wrap],
        )

        demo.load(_refresh_status, inputs=[base_url_state], outputs=[status_state, header_html_comp])

    return demo


# ---------------------------------------------------------------------------
# Module-level helpers used inside closures above
# ---------------------------------------------------------------------------
def _switch_page(name):
    return [gr.update(visible=(name == p)) for p in PAGE_NAMES]


def _filter_history(items, search):
    if not search:
        return items
    q = search.lower()
    return [i for i in items if q in (i.get("developer_idea") or "").lower()]


def _flatten_chat(chat_msgs):
    flat = []
    for m in chat_msgs:
        flat.append({"role": "user", "content": m.get("question", "")})
        flat.append({"role": "assistant", "content": m.get("answer", "")})
    return flat


def _make_open_handler(item_id):
    def handler(token, base_url):
        try:
            detail = api.get_history_detail(base_url, token, item_id)
        except api.ApiError as e:
            raise gr.Error(e.message)
        blueprint = dict(detail)
        blueprint["id"] = detail.get("id") or detail.get("analysis_id") or item_id
        # The backend's AnalysisResponse doesn't expose the prior follow-up
        # Q&A thread on this endpoint, so re-opening a saved blueprint
        # starts a fresh chat panel rather than guessing at a `messages`
        # shape the API doesn't document.
        chat_msgs = detail.get("messages") or []
        return blueprint, chat_msgs
    return handler


def _make_delete_handler(item_id):
    def handler(token, base_url):
        try:
            api.delete_analysis(base_url, token, item_id)
            gr.Info("Deleted.")
        except api.ApiError as e:
            gr.Warning(e.message)
        try:
            return api.get_history(base_url, token, limit=100)
        except api.ApiError:
            return []
    return handler