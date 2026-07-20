"""
All communication with the FounderOS FastAPI backend lives here.

Nothing in ui.py should ever call `requests` directly — every backend
call is one of the functions below, so the REST contract stays in one
auditable place. Endpoints, payload shapes, and auth are reused exactly
as the backend already defines them; nothing here re-implements
backend logic.
"""
from typing import Any, Dict, List, Optional

import requests

import config


class ApiError(Exception):
    """Raised for any failure talking to the backend — network, timeout,
    or an HTTP error response. `status_code` is None for pure network
    failures (offline / DNS / connection refused)."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def _headers(token: Optional[str]) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _handle_response(resp: requests.Response) -> Any:
    if resp.status_code == 401:
        raise ApiError("Your session has expired. Please log in again.", 401)
    if resp.status_code == 403:
        raise ApiError("You don't have access to that resource.", 403)
    if resp.status_code == 404:
        raise ApiError("That wasn't found. It may have been deleted.", 404)
    if resp.status_code >= 500:
        raise ApiError(
            "The backend hit an internal error. Please try again in a moment.",
            resp.status_code,
        )
    if resp.status_code >= 400:
        detail = "Request failed."
        try:
            body = resp.json()
            detail = body.get("detail", detail)
        except Exception:
            pass
        raise ApiError(str(detail), resp.status_code)

    if resp.status_code == 204 or not resp.content:
        return None
    try:
        return resp.json()
    except ValueError:
        raise ApiError("The backend returned a response we couldn't parse.", resp.status_code)


def _request(method: str, base_url: str, path: str, token: Optional[str] = None,
             timeout: Optional[int] = None, **kwargs) -> Any:
    try:
        resp = requests.request(
            method,
            _url(base_url, path),
            headers=_headers(token),
            timeout=timeout or config.REQUEST_TIMEOUT,
            **kwargs,
        )
    except requests.exceptions.ConnectTimeout:
        raise ApiError("Connecting to the backend timed out.")
    except requests.exceptions.ConnectionError:
        raise ApiError(
            "Couldn't reach the backend. It may be offline, or waking up from "
            "a cold start (this can take ~30s on Render's free tier)."
        )
    except requests.exceptions.Timeout:
        raise ApiError("The request timed out. Please try again.")
    except requests.exceptions.RequestException as exc:
        raise ApiError(f"Network error: {exc}")
    return _handle_response(resp)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
def check_health(base_url: str) -> bool:
    """Lightweight reachability check — hits the auto-generated /docs page
    rather than a dedicated health endpoint, since the backend doesn't
    expose one."""
    try:
        requests.get(_url(base_url, config.ENDPOINTS["health"]), timeout=config.HEALTH_TIMEOUT)
        return True
    except requests.exceptions.RequestException:
        return False


# ---------------------------------------------------------------------------
# Auth  — POST /user, POST /login
# ---------------------------------------------------------------------------
def signup(base_url: str, email: str, password: str) -> Dict:
    """POST /user — matches auth.py's UserRequest, which is built from
    email + password. If your UserRequest schema has additional required
    fields, add them to this payload."""
    payload = {"email": email, "password": password}
    return _request("POST", base_url, config.ENDPOINTS["signup"], json=payload)


def login(base_url: str, email: str, password: str) -> Dict:
    """POST /login — this endpoint takes OAuth2PasswordRequestForm, i.e.
    form-encoded data, not JSON. `username` is the email."""
    data = {"username": email, "password": password}
    return _request("POST", base_url, config.ENDPOINTS["login"], data=data)


# ---------------------------------------------------------------------------
# Ventures — POST /idea_analysis
# ---------------------------------------------------------------------------
def generate_idea_analysis(base_url: str, token: str, idea: str) -> Dict:
    """POST /idea_analysis — body matches ventures.UserIdea (field: idea).
    Returns {status, result, db_id} or {status, result: None, error}."""
    payload = {"idea": idea}
    return _request(
        "POST", base_url, config.ENDPOINTS["generate"],
        token=token, json=payload, timeout=config.GENERATE_TIMEOUT,
    )


# ---------------------------------------------------------------------------
# History — GET /history, GET /history/{id}, DELETE /analysis/{id}
# ---------------------------------------------------------------------------
def get_history(base_url: str, token: str, limit: int = 100) -> List[Dict]:
    return _request(
        "GET", base_url, config.ENDPOINTS["history_list"],
        token=token, params={"limit": limit},
    ) or []


def get_history_detail(base_url: str, token: str, analysis_id: int) -> Dict:
    path = config.ENDPOINTS["history_detail"].format(id=analysis_id)
    return _request("GET", base_url, path, token=token)


def delete_analysis(base_url: str, token: str, analysis_id: int) -> None:
    path = config.ENDPOINTS["delete_analysis"].format(id=analysis_id)
    return _request("DELETE", base_url, path, token=token)


# ---------------------------------------------------------------------------
# Chat — POST /analysis/{id}/
# ---------------------------------------------------------------------------
def send_chat_message(base_url: str, token: str, analysis_id: int, question: str) -> Dict:
    path = config.ENDPOINTS["chat"].format(id=analysis_id)
    payload = {"question": question}
    return _request("POST", base_url, path, token=token, json=payload)
