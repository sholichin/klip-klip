import os
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
BIN_DIR = BASE_DIR / "bin"
STORAGE_DIR = BASE_DIR / "storage"
DOWNLOADS_DIR = STORAGE_DIR / "downloads"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"
EXPORTS_DIR = STORAGE_DIR / "exports"
CACHE_DIR = STORAGE_DIR / "cache"
SETTINGS_FILE = STORAGE_DIR / "settings.json"

for d in [DOWNLOADS_DIR, TRANSCRIPTS_DIR, EXPORTS_DIR, CACHE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

import shutil

# FFmpeg binary resolution
def get_ffmpeg_path() -> str:
    local_ffmpeg = BIN_DIR / "ffmpeg"
    if local_ffmpeg.exists() and os.access(local_ffmpeg, os.X_OK):
        return str(local_ffmpeg)
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg
    for p in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"]:
        if os.path.exists(p):
            return p
    return "ffmpeg"

FFMPEG_PATH = get_ffmpeg_path()

# Prepend BIN_DIR to PATH so yt-dlp and ExternalFD find local ffmpeg
bin_str = str(BIN_DIR)
if bin_str not in os.environ.get("PATH", ""):
    os.environ["PATH"] = bin_str + os.pathsep + os.environ.get("PATH", "")

# Settings Manager
DEFAULT_SETTINGS = {
    "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
    "gemini_model": "gemini-1.5-flash",
    "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    "default_layout": "blurred_bg", # "blurred_bg" | "crop_center"
    "default_hook_style": "badge_yellow", # "badge_yellow" | "badge_red" | "neon" | "clean"
    "default_subtitle_style": "karaoke_yellow",
    "target_platform": "all", # "motionklip" | "klipreward" | "tiktok" | "all"
    "min_clip_duration": 30,
    "max_clip_duration": 60,
    "video_quality": "1080p",
}

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(new_settings: dict) -> dict:
    current = load_settings()
    current.update(new_settings)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving settings: {e}")
    return current
