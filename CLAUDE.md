# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app (local, Python 3.11)
streamlit run app.py

# Install dependencies
pip install -r requirements.txt

# Codespaces/devcontainer runs it with CORS/XSRF disabled:
streamlit run app.py --server.enableCORS false --server.enableXsrfProtection false
```

There is no test suite, linter, or build step configured.

## What this is

A single-page Streamlit tool that (1) calls an external API to mint unique exam-portal login links for a list of students, then (2) sends personalized HTML emails via **AWS SES**. It also supports a "General Email Mode" that skips link generation for plain announcements.

## Architecture

`app.py` is the entire UI — a long, top-to-bottom script (~2000 lines) organized as a set of `st.tabs(...)`. All state lives in `st.session_state`, initialized once in `init_session_state()` near the top; that defaults dict is the canonical list of app state. Business logic is delegated to `modules/`:

- **`modules/api_client.py`** — `APIClient.generate_links()` POSTs `{program_id, round_id, session_time, emails}` to the API (auth via `x-api-key` header) and returns `(success, data, error)`. Merges returned link data back onto student dicts.
- **`modules/email_sender.py`** — `EmailSender` wraps a boto3 SES client. `send_bulk_emails()` is the core loop: per-email try/except, placeholder substitution, optional `.ics` calendar attachment, **disk checkpointing** every N emails, and crash-report CSV generation. See checkpoint/resume system below.
- **`modules/file_handler.py`** — `FileHandler.process_file()` reads CSV/Excel (column names normalized to lowercase), validates emails, optionally maps login-id/password columns. Returns `(students, errors)`.
- **`modules/template_manager.py`** — Lists/loads/saves HTML templates from `templates/`. Built-in defaults are returned by `get_default_template()` / `get_general_email_template()`. Per-template subject lines are persisted in `config/user_preferences.json` (NOT in the HTML file).
- **`modules/calendar_event.py`** — Generates `.ics` invites (Google Meet / Outlook) from loosely-formatted date/time strings.
- **`modules/email_tracking.py`** — `EmailTracker` queries CloudWatch `AWS/SES` metrics (Send/Delivery/Bounce/Open/Click…) scoped to the SES **configuration set** for the Reports/Tracking tab.
- **`modules/visual_editor.py`** + **`components/visual_editor/index.html`** — a custom Streamlit `contenteditable` WYSIWYG component. It splits a template into styles/body/prefix/suffix, scopes `body{}` CSS to `#editable-content`, and wraps `{placeholder}` tokens in non-editable spans so they survive editing.

### Tab indices shift with mode
The tab variables are deliberately named `tab1, tab2, tab3, ...` but General Email Mode (`skip_link_generation`) omits the "Generate Links" tab, so `tab3 = None` and the same variable names map to different UI positions. When editing tab logic, key off the variable name and the `skip_link_generation` flag, not the displayed number.

### Checkpoint / crash-resume system
`send_bulk_emails()` writes `reports/checkpoint_<session_id>.json` periodically. On crash it emits a `crash_*` report CSV. `get_resumable_session()` finds an unfinished checkpoint so the UI can offer to resume (`resume_from_checkpoint=True`); `clear_checkpoint()` removes it on success. The `reports/` directory accumulates these JSON checkpoints and CSV reports — it is gitignored.

## Configuration

`config/settings.py` (`Config` class) resolves each setting via `_get_config()`, which prefers **Streamlit secrets** (`.streamlit/secrets.toml`, for Streamlit Cloud) and falls back to **environment variables** / `.env` (local). Copy `.env.example` → `.env` for local dev. UI fields in Tab 1 override these per-session.

> Note: `config/settings.py` currently contains hardcoded fallback credentials (AWS access key, API key) as defaults. Treat these as secrets; prefer `.env`/secrets and avoid committing real values.

## Data conventions

- Student records are plain dicts flowing through the pipeline; expected keys include `name`, `email`, and (after link generation) `login_link`, `candidate_id`, `expires_at`, etc.
- Template placeholders use single-brace syntax (`{name}`, `{login_link}`, `{program_name}`, …) — see the README table for the full set. They are filled by `_replace_placeholders()`.
- Uploaded source files can be dropped in `user-data/` to appear in the Tab 2 "search user data" file picker.
