"""Win32 window handling: find, pin, protect, make translucent."""
import ctypes
import ctypes.wintypes
import os
import time

from config import (
    APP_TITLE,
    GWL_EXSTYLE,
    HWND_TOPMOST,
    LWA_ALPHA,
    SWP_SHOWWINDOW,
    WDA_EXCLUDEFROMCAPTURE,
    WINDOW_ALPHA,
    WINDOW_HEIGHT,
    WS_EX_LAYERED,
)

user32 = ctypes.windll.user32

# Current window height. resize requests from the page update it; the guard
# pins the window to this value.
height = [WINDOW_HEIGHT]

# Without explicit argtypes ctypes truncates HWND_TOPMOST (-1) to 32 bits
# and every SetWindowPos call fails with "invalid window handle".
user32.SetWindowPos.argtypes = [
    ctypes.c_void_p,   # hWnd
    ctypes.c_void_p,   # hWndInsertAfter
    ctypes.c_int,      # X
    ctypes.c_int,      # Y
    ctypes.c_int,      # cx
    ctypes.c_int,      # cy
    ctypes.c_uint,     # uFlags
]
user32.SetWindowPos.restype = ctypes.c_bool
user32.GetWindowRect.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(ctypes.wintypes.RECT),
]
user32.GetWindowRect.restype = ctypes.c_bool
user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetLayeredWindowAttributes.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint32,   # crKey
    ctypes.c_byte,     # bAlpha
    ctypes.c_uint32,   # dwFlags
]
user32.SetLayeredWindowAttributes.restype = ctypes.c_bool


def find_window():
    """Our bar window (own process only - a stale one from a crashed run
    could otherwise be mistaken for ours)."""
    own_pid = os.getpid()
    result = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_callback(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        if length:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            if buffer.value == APP_TITLE:
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                if pid.value == own_pid:
                    result.append(hwnd)
        return True

    user32.EnumWindows(enum_callback, 0)
    return result[0] if result else None


def hide_from_capture(hwnd):
    """Show up as a black box in screenshots and recordings."""
    user32.SetWindowDisplayAffinity.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    user32.SetWindowDisplayAffinity.restype = ctypes.c_bool
    if not user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
        raise ctypes.WinError()


def make_translucent(hwnd):
    """Layered window at WINDOW_ALPHA opacity.

    WebView2 never does real per-pixel transparency in this setup, so the
    whole window is made translucent instead and the page just draws an
    opaque gray bar.
    """
    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    if not ex_style & WS_EX_LAYERED:
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED)
    if not user32.SetLayeredWindowAttributes(hwnd, 0, WINDOW_ALPHA, LWA_ALPHA):
        raise ctypes.WinError()


def pin_to_top(hwnd, width):
    """Center the bar along the top edge; skip it if it's already there.

    Moving the window every pass makes pywebview's JS bridge misreport the
    move and spam the console, so the current rect is checked first.
    """
    screen_w = user32.GetSystemMetrics(0)
    x = (screen_w - width) // 2
    rect = ctypes.wintypes.RECT()
    if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        if (
            rect.left == x
            and rect.top == 0
            and rect.right - rect.left == width
            and rect.bottom - rect.top == height[0]
        ):
            return
    if not user32.SetWindowPos(
        hwnd, HWND_TOPMOST, x, 0, width, height[0], SWP_SHOWWINDOW
    ):
        raise ctypes.WinError()


def run_guard(width):
    """Pin, protect, and keep translucent, forever.

    Polls fast at first so the layered style lands before the WebView2
    compositor initializes (the reposition also forces the compositor to
    re-init against the new style); re-checks every 2s afterwards.
    """
    protected = False
    delay = 0.002
    try:
        while True:
            hwnd = find_window()
            if hwnd:
                try:
                    hide_from_capture(hwnd)
                    make_translucent(hwnd)
                    protected = True
                except Exception:
                    protected = False  # window not ready yet
                try:
                    pin_to_top(hwnd, width)
                except Exception:
                    pass
                if protected:
                    delay = 2.0
            time.sleep(delay)
    except Exception:
        pass
