"""
chatbot_client.py

Wrapper for the Meridian banking app APIs.
  POST /api/chat      — send a chat message, get a bot reply
  GET  /api/state     — fetch current account state (balance, transactions, …)
  POST /api/ui-event  — record a UI action (e.g. card lock) for cross-surface tests
  POST /api/llm       — send an arbitrary prompt to the app's LLM endpoint
                        (used for LLM-as-judge scoring in tests)
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("APP_URL")
SESSION_TOKEN = os.getenv("SESSION_TOKEN")

if not BASE_URL or not SESSION_TOKEN:
    raise RuntimeError(
        "APP_URL and SESSION_TOKEN are required. "
        "Copy .env.example to .env and fill in your credentials."
    )


def send_message(message: str, session_id: str = "test-session") -> dict:
    """
    Send a message to the chatbot and return the parsed response.

    Returns a dict with:
      - 'reply': the chatbot's text response
      - 'status': HTTP status code
      - 'raw': full response JSON (if available)
    """
    payload = {
        "message": message,
        "sessionId": session_id,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/chat",
            json=payload,
            headers=_headers(),
            params=_params(),
            timeout=10,
        )
    except requests.exceptions.Timeout:
        return {"reply": "", "status": 408, "raw": {}, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        # Real transport failure (DNS, refused connection, etc.)
        return {"reply": "", "status": 0, "raw": {}, "error": str(e)}

    # We got an HTTP response -- preserve the real status code even if the
    # body isn't JSON (e.g. an HTML error page from a proxy).
    try:
        data = response.json()
    except ValueError:
        return {
            "reply": "",
            "status": response.status_code,
            "raw": {},
            "error": f"non-JSON response (content-type: {response.headers.get('content-type', 'unknown')})",
        }

    return {
        "reply": data.get("reply") or data.get("message") or "",
        "status": response.status_code,
        "raw": data,
    }


def _headers() -> dict:
    return {"Content-Type": "application/json"}


def _params() -> dict:
    # Token is passed as a URL query parameter: ?token=<value>
    return {"token": SESSION_TOKEN} if SESSION_TOKEN else {}


def get_state() -> dict:
    """
    Fetch current account state from GET /api/state.

    Returns a dict with at minimum:
      - 'status': HTTP status code
      - 'raw': full response JSON (if available)
    Commonly includes 'balance', 'transactions', 'account', etc.
    Returns status=0 on connection failure.
    """
    try:
        response = requests.get(
            f"{BASE_URL}/api/state",
            headers=_headers(),
            params=_params(),
            timeout=10,
        )
    except requests.exceptions.Timeout:
        return {"status": 408, "raw": {}, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        return {"status": 0, "raw": {}, "error": str(e)}

    try:
        data = response.json()
    except ValueError:
        return {
            "status": response.status_code,
            "raw": {},
            "error": f"non-JSON response (content-type: {response.headers.get('content-type', 'unknown')})",
        }

    return {"status": response.status_code, "raw": data, **data}


def send_ui_event(payload: dict) -> dict:
    """
    Record a UI action via POST /api/ui-event.

    Common payloads (schema is app-defined):
      {"type": "card_lock",   "locked": True}
      {"type": "card_unlock", "locked": False}

    Returns a dict with 'status' and 'raw'. Returns status=0 on failure.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/api/ui-event",
            json=payload,
            headers=_headers(),
            params=_params(),
            timeout=10,
        )
    except requests.exceptions.Timeout:
        return {"status": 408, "raw": {}, "error": "timeout"}
    except requests.exceptions.RequestException as e:
        return {"status": 0, "raw": {}, "error": str(e)}

    try:
        data = response.json()
    except ValueError:
        data = {}

    return {"status": response.status_code, "raw": data}


def llm_judge(prompt: str) -> str:
    """
    Send an evaluation prompt to the app's LLM endpoint (POST /api/llm)
    and return the response text.

    Returns an empty string on any failure so callers can degrade gracefully
    to keyword-based assertions rather than failing on infra issues.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/api/llm",
            json={"prompt": prompt},
            headers=_headers(),
            params=_params(),
            timeout=30,
        )
        data = response.json()
    except Exception:
        return ""

    # Try common field names the endpoint might use
    return (
        data.get("reply")
        or data.get("response")
        or data.get("text")
        or data.get("message")
        or ""
    )
