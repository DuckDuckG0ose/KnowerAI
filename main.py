"""Entry point: create the bar window and keep it protected."""
import os
import threading

import webview

import bridge
import win
from config import APP_TITLE, BASE_DIR, WINDOW_HEIGHT, WINDOW_WIDTH


def main():
    # The window is created by the WebView2 control in our own process,
    # which is what lets SetWindowDisplayAffinity actually take effect.
    threading.Thread(target=win.run_guard, args=(WINDOW_WIDTH,), daemon=True).start()

    webview.create_window(
        APP_TITLE,
        os.path.join(BASE_DIR, "web", "index.html"),
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        frameless=True,
        transparent=True,
        background_color="#0b0b0d",
        js_api=bridge.Api(),
    )
    webview.start()


if __name__ == "__main__":
    main()
