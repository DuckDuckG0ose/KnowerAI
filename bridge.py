"""pywebview js_api: everything the page can call."""
import json
import threading

import requests
import webview

import gemini
import keys
import win
from config import WINDOW_HEIGHT, WINDOW_MAX_HEIGHT, WINDOW_WIDTH

# Full conversation history; the whole thing is sent with every request.
history = []


def _call_js(name, payload=None):
    """Run a function in the page, e.g. on_token("hi")."""
    try:
        webview.windows[0].evaluate_js(f"{name}({json.dumps(payload)})")
    except Exception:
        pass


class Api:
    def get_status(self):
        key = keys.get_gemini_key()
        return {"models": gemini.get_models(key), "has_key": bool(key)}

    def save_api_key(self, key):
        keys.save_gemini_key(key)

    def resize_window(self, height):
        """Grow/shrink the bar to wrap the current message.

        Resizing goes through pywebview's own API: raw SetWindowPos calls
        confuse its JS bridge.
        """
        win.height[0] = max(WINDOW_HEIGHT, min(int(height), WINDOW_MAX_HEIGHT))
        try:
            webview.windows[0].resize(WINDOW_WIDTH, win.height[0])
        except Exception:
            pass

    def quit(self):
        try:
            webview.windows[0].destroy()
        except Exception:
            pass

    def send_message(self, message, model):
        # Runs on its own thread so streaming doesn't block the page.
        threading.Thread(
            target=self._send_in_background, args=(message, model), daemon=True
        ).start()

    def _send_in_background(self, message, model):
        history.append({"role": "user", "content": message})

        full_reply = []
        try:
            for token in gemini.stream(history, model, keys.get_gemini_key()):
                full_reply.append(token)
                _call_js("on_token", token)
        except requests.HTTPError as error:
            detail = error.response.text[:300]
            try:
                detail = (
                    error.response.json().get("error", {}).get("message", "")
                    or detail
                )
            except Exception:
                pass
            _call_js("on_error", f"Gemini returned {error.response.status_code}: {detail}")
        except requests.RequestException as error:
            _call_js("on_error", f"Could not reach Gemini: {error}")
        except Exception as error:
            _call_js("on_error", f"Something went wrong: {error}")
        finally:
            if full_reply:
                history.append({"role": "assistant", "content": "".join(full_reply)})
            _call_js("on_done")
