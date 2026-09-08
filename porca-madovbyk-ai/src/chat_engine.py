import os
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
LOCAL_KEY_PATH = ROOT / ".streamlit" / "gemini_api_key.txt"
INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

# Prefer the newest Flash model, then fall back to other current Flash models.
MODEL_CANDIDATES = (
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
)


def load_api_key():
    env_key = str(os.environ.get("GEMINI_API_KEY", "")).strip()
    if env_key:
        return env_key, "environment"

    if LOCAL_KEY_PATH.exists():
        try:
            key = LOCAL_KEY_PATH.read_text(encoding="utf-8").strip()
            if key:
                return key, "local"
        except Exception:
            pass

    return "", None


def save_api_key(api_key):
    key = str(api_key or "").strip()
    if not key:
        raise ValueError("Chiave API vuota.")

    LOCAL_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_KEY_PATH.write_text(key, encoding="utf-8")
    return LOCAL_KEY_PATH


def delete_local_api_key():
    try:
        if LOCAL_KEY_PATH.exists():
            LOCAL_KEY_PATH.unlink()
    except Exception:
        return False
    return True


def _error_message(response):
    try:
        payload = response.json()
        message = payload.get("error", {}).get("message")
        if message:
            return str(message)
    except Exception:
        pass

    text = str(response.text or "").strip()
    return text[:500] if text else f"HTTP {response.status_code}"


def _extract_output_text(payload):
    parts = []

    # Current Interactions API schema: timeline steps -> model_output -> content.
    for step in payload.get("steps", []) or []:
        if step.get("type") != "model_output":
            continue
        for item in step.get("content", []) or []:
            if item.get("type") == "text" and item.get("text"):
                parts.append(str(item["text"]))

    # Compatibility with older/alternate response shapes.
    if not parts:
        for item in payload.get("outputs", []) or []:
            if item.get("type") == "text" and item.get("text"):
                parts.append(str(item["text"]))

    if not parts and payload.get("output_text"):
        parts.append(str(payload.get("output_text")))

    return "\n".join(part.strip() for part in parts if part.strip()).strip()


def create_interaction(
    api_key,
    prompt,
    previous_interaction_id=None,
    preferred_model=None,
    timeout=90,
):
    """Send one conversational turn through Gemini Interactions API.

    Returns a dict with response text, interaction id and model used.
    The server-side previous_interaction_id keeps the conversation contextual
    without resending the whole history from the browser.
    """

    key = str(api_key or "").strip()
    user_prompt = str(prompt or "").strip()

    if not key:
        raise ValueError("Manca la chiave Gemini API.")
    if not user_prompt:
        raise ValueError("Scrivi una domanda prima di inviare.")

    candidates = []
    if preferred_model:
        candidates.append(str(preferred_model).strip())
    for model in MODEL_CANDIDATES:
        if model not in candidates:
            candidates.append(model)

    headers = {
        "x-goog-api-key": key,
        "Content-Type": "application/json",
    }

    errors = []

    for model in candidates:
        body = {
            "model": model,
            "input": user_prompt,
        }
        if previous_interaction_id:
            body["previous_interaction_id"] = previous_interaction_id

        try:
            response = requests.post(
                INTERACTIONS_URL,
                headers=headers,
                json=body,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Connessione alla chat non riuscita: {exc}") from exc

        if response.ok:
            payload = response.json()
            text = _extract_output_text(payload)
            if not text:
                raise RuntimeError("Gemini ha risposto senza testo utilizzabile.")

            return {
                "text": text,
                "interaction_id": payload.get("id"),
                "model": model,
            }

        message = _error_message(response)
        errors.append(f"{model}: {message}")

        # Authentication/rate-limit errors will not improve by changing model.
        if response.status_code in {401, 403, 429}:
            break

    raise RuntimeError("Chat Gemini non disponibile. " + " | ".join(errors))
