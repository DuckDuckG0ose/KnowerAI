"""App settings: window, Gemini API, and the Win32 capture protection."""
import os

APP_TITLE = "Knower AI"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

WINDOW_WIDTH, WINDOW_HEIGHT = 1000, 100
WINDOW_MAX_HEIGHT = 500
# Window opacity (0-255). The whole bar - gray and text - is drawn at this
# level; 165 is roughly 65% opaque.
WINDOW_ALPHA = 165

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/"
GEMINI_KEY_FILE = "gemini_key.txt"

SYSTEM_PROMPT = "Keep your answers short and to the point."

# Gemini versions get retired all the time, so the real list is fetched at
# startup. This is only used until that request comes back.
GEMINI_FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

# Models that aren't plain text chat (image/video/audio/embeddings/etc).
GEMINI_EXCLUDE_TAGS = (
    "image", "veo", "audio", "embedding", "imagen", "nano",
    "lyria", "music", "tts", "search", "tuned", "robotics",
    "computer-use",
)

WDA_EXCLUDEFROMCAPTURE = 0x00000011
WS_EX_LAYERED = 0x00080000
GWL_EXSTYLE = -20
LWA_ALPHA = 0x00000002
HWND_TOPMOST = -1
SWP_SHOWWINDOW = 0x0040
