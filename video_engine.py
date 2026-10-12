import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Union
from PIL import Image, ImageDraw, ImageFont

from config import FFMPEG_PATH, CACHE_DIR, EXPORTS_DIR

def create_hook_banner_image(
    hook_text: str, 
    output_png_path: str, 
    style: str = "badge_yellow"
) -> str:
    """
    Render clean, high-contrast viral hook banner without any brand watermark/badge.
    Banner is 960px wide to fit nicely inside 1080x1920 canvas with padding.
    """
    width = 960
    
    # Color Themes
    if style == "badge_red":
        bg_color = (220, 38, 38, 245)      # Vibrant Red
        text_color = (255, 255, 255, 255)  # Crisp White
    elif style == "neon":
        bg_color = (15, 23, 42, 245)       # Dark Slate
        text_color = (56, 189, 248, 255)   # Neon Cyan
    else: # Default: badge_yellow (MrBeast & TikTok highest retention style)
        bg_color = (255, 214, 10, 245)     # Eye-popping Yellow
        text_color = (17, 17, 17, 255)     # Deep Bold Black

    # Word wrap text for banner width
    words = hook_text.strip().split()
    lines = []
    curr = []
    for w in words:
        curr.append(w)
        if len(" ".join(curr)) > 26:
            lines.append(" ".join(curr[:-1]))
            curr = [w]
    if curr:
        lines.append(" ".join(curr))
    if not lines:
        lines = [hook_text]

    line_height = 54
    text_block_height = len(lines) * line_height
    total_height = text_block_height + 46

    # Create RGBA canvas
    img = Image.new("RGBA", (width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Clean rounded rectangle background without brand badge
    radius = 24
    draw.rounded_rectangle([(0, 0), (width, total_height)], radius=radius, fill=bg_color)
    draw.rounded_rectangle([(0, 0), (width, total_height)], radius=radius, outline=(255, 255, 255, 120), width=3)

    # Font selection
    font_main = None
    for font_name in [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial.ttf"
    ]:
        if os.path.exists(font_name):
            try:
                font_main = ImageFont.truetype(font_name, 48)
                break
            except Exception:
                pass

    if not font_main:
        font_main = ImageFont.load_default()

    # Draw hook headline lines centered
    start_y = 23
    for i, line in enumerate(lines):
        y_pos = start_y + (i * line_height) + (line_height // 2)
        draw.text((width // 2, y_pos), line.upper(), fill=text_color, font=font_main, anchor="mm")

    Path(output_png_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_png_path, "PNG")
    return output_png_path

def render_vertical_clip(
    input_video: str,
    output_mp4: str,
    start_sec: float,
    end_sec: float,
    layout: str = "blurred_bg", # "blurred_bg" | "crop_center" | "split"
    speaker_focus: Union[str, float] = "center", # "center" | "left" | "right" | "split" | float 0.0-1.0
    show_hook: bool = True,
    hook_text: Optional[str] = None,
    hook_style: str = "badge_yellow",
    ass_subtitle_path: Optional[str] = None
) -> str:
    """
    Renders 1080x1920 vertical video with super-fast VideoToolbox hardware acceleration,
    intelligent speaker crop framing (left, center, right, split), and optional clean hook banner.
    """
    output_path = Path(output_mp4)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    duration = max(5.0, end_sec - start_sec)
    
    # 1. Generate hook banner PNG only if show_hook is True
    hook_banner_png = None
    if show_hook and hook_text and len(hook_text.strip()) > 3:
        hook_banner_png = str(CACHE_DIR / f"hook_{abs(hash(hook_text))}.png")
        create_hook_banner_image(hook_text, hook_banner_png, style=hook_style)

    # 2. Build FFmpeg Filter Graph
    filter_chains = []
    
    # Layout & Speaker Crop Selection
    if layout == "split" or speaker_focus == "split":
        # Split Screen (Stack: Left speaker on top, Right speaker on bottom)
        layout_filter = (
            "[0:v]split=2[raw_top][raw_bot];"
            "[raw_top]scale=-2:960:force_original_aspect_ratio=increase,crop=1080:960:(in_w-1080)*0.20:0[vtop];"
            "[raw_bot]scale=-2:960:force_original_aspect_ratio=increase,crop=1080:960:(in_w-1080)*0.80:0[vbot];"
            "[vtop][vbot]vstack[vbase]"
        )
    elif layout == "crop_center":
        # Speaker Framing calculation
        if str(speaker_focus).lower() == "left":
            crop_x_expr = "(in_w-1080)*0.18"
        elif str(speaker_focus).lower() == "right":
            crop_x_expr = "(in_w-1080)*0.82"
        elif str(speaker_focus).lower() == "center":
            crop_x_expr = "(in_w-1080)/2"
        else:
            try:
                frac = float(speaker_focus)
                frac = max(0.0, min(1.0, frac))
                crop_x_expr = f"(in_w-1080)*{frac}"
            except Exception:
                crop_x_expr = "(in_w-1080)/2"

        layout_filter = (
            f"[0:v]scale=-2:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920:{crop_x_expr}:0[vbase]"
        )
    else: # blurred_bg (Ultra-Fast Downscale-Blur-Upscale)
        layout_filter = (
            "[0:v]split=2[raw_bg][raw_fg];"
            "[raw_bg]scale=160:284:force_original_aspect_ratio=increase,crop=160:284,"
            "boxblur=3:1,scale=1080:1920[bg_blur];"
            "[raw_fg]scale=1080:-2:force_original_aspect_ratio=decrease[fg_scaled];"
            "[bg_blur][fg_scaled]overlay=(W-w)/2:(H-h)/2[vbase]"
        )
    
    filter_chains.append(layout_filter)
    current_stream = "[vbase]"

    # Overlay hook banner if show_hook is True
    inputs = [
        "-ss", str(start_sec),
        "-t", str(duration),
        "-i", input_video
    ]

    if hook_banner_png and os.path.exists(hook_banner_png):
        inputs.extend(["-i", hook_banner_png])
        banner_filter = (
            f"{current_stream}[1:v]overlay=x=(W-w)/2:y=130[vhook]"
        )
        filter_chains.append(banner_filter)
        current_stream = "[vhook]"

    # Burn-in subtitles if exists
    if ass_subtitle_path and os.path.exists(ass_subtitle_path):
        clean_ass = os.path.abspath(ass_subtitle_path).replace("\\", "/").replace(":", "\\:")
        sub_filter = f"{current_stream}ass='{clean_ass}'[vsub]"
        filter_chains.append(sub_filter)
        current_stream = "[vsub]"

    complex_filter = ";".join(filter_chains)

    # Fast Hardware Accelerated Encode Command
    is_darwin = sys.platform == "darwin"

    def build_cmd(use_videotoolbox: bool = False):
        vcodec_args = (
            ["-c:v", "h264_videotoolbox", "-b:v", "5500k"]
            if (use_videotoolbox and is_darwin) else
            ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "22"]
        )
        return [
            FFMPEG_PATH,
            "-y",
            *inputs,
            "-filter_complex", complex_filter,
            "-map", current_stream,
            "-map", "0:a?",
            *vcodec_args,
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path)
        ]

    # On macOS, try Apple Silicon VideoToolbox first, fallback to ultrafast libx264.
    # On Linux / Docker container, directly use ultrafast libx264.
    if is_darwin:
        cmd = build_cmd(use_videotoolbox=True)
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            print(f"VideoToolbox notice: {proc.stderr[:300]}, falling back to libx264 ultrafast...")
            cmd_fallback = build_cmd(use_videotoolbox=False)
            proc_fallback = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc_fallback.returncode != 0:
                raise RuntimeError(f"FFmpeg rendering failed: {proc_fallback.stderr[-400:]}")
    else:
        cmd = build_cmd(use_videotoolbox=False)
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg rendering failed: {proc.stderr[-400:]}")

    return str(output_path)
