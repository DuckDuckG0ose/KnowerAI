"""Loading and saving the Gemini API key."""
import os

from config import BASE_DIR, GEMINI_KEY_FILE


def get_gemini_key():
    """Env var wins, otherwise the local key file."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        path = os.path.join(BASE_DIR, GEMINI_KEY_FILE)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                key = f.read().strip()
    return key


def save_gemini_key(key):
    with open(os.path.join(BASE_DIR, GEMINI_KEY_FILE), "w", encoding="utf-8") as f:
        f.write(key.strip())
