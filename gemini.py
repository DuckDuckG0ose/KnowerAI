"""Gemini API client: live model list and streaming chat."""
import json

import requests

from config import (
    GEMINI_EXCLUDE_TAGS,
    GEMINI_FALLBACK_MODELS,
    GEMINI_URL,
    SYSTEM_PROMPT,
)

_models = None


def get_models(key):
    """Chat models currently served for this key, flash family first.

    Cached per run; falls back to hardcoded names if the request fails.
    """
    global _models
    if _models:
        return _models

    try:
        response = requests.get(GEMINI_URL, params={"key": key}, timeout=15)
        response.raise_for_status()
        models = response.json().get("models", [])
    except Exception:
        return GEMINI_FALLBACK_MODELS

    chat_models = [
        model["name"].removeprefix("models/")
        for model in models
        if model.get("name", "").startswith("models/gemini-")
        and "generateContent" in model.get("supportedGenerationMethods", [])
        and not any(tag in model["name"].lower() for tag in GEMINI_EXCLUDE_TAGS)
    ]

    chat_models.sort(reverse=True)

    def group_key(name):
        # Stable models before previews; flash family first (lite last).
        lower = name.lower()
        preview = "preview" in lower
        if "flash" in lower:
            return (0, preview, "lite" in lower)
        return (1, preview, False)

    chat_models.sort(key=group_key)
    _models = chat_models or GEMINI_FALLBACK_MODELS
    return _models


def stream(messages, model, key):
    """Ask Gemini for a reply, yielding text chunks as they arrive."""
    url = GEMINI_URL + f"{model}:streamGenerateContent?alt=sse&key={key}"

    # Gemini alternates user/model roles, so consecutive same-role messages
    # get merged.
    contents = []
    for message in messages:
        role = "model" if message["role"] == "assistant" else "user"
        text = message["content"]
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"][0]["text"] += f"\n\n{text}"
        else:
            contents.append({"role": role, "parts": [{"text": text}]})

    payload = {
        "contents": contents,
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
    }

    with requests.post(url, json=payload, stream=True, timeout=120) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8", errors="ignore").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data:
                continue
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            if "error" in chunk:
                raise RuntimeError(chunk["error"].get("message", "Gemini error"))
            candidates = chunk.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts") or []
                for part in parts:
                    token = part.get("text") or ""
                    if token:
                        yield token
