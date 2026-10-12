import os
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    BASE_DIR, EXPORTS_DIR, DOWNLOADS_DIR, TRANSCRIPTS_DIR, CACHE_DIR,
    load_settings, save_settings, FFMPEG_PATH
)
from youtube import extract_video_id, get_video_metadata, get_video_transcript, download_video_segment
from ai_analyzer import analyze_video_for_viral_clips
from subtitle import generate_ass_subtitles, generate_srt_subtitles
from video_engine import render_vertical_clip

app = FastAPI(title="KLIP KLIP API", description="AI YouTube Viral Clipping & Monetization Studio")

def cleanup_old_files(max_age_seconds: int = 7200):
    """Clean up temporary video files older than 2 hours to prevent disk saturation."""
    now = time.time()
    for folder in [EXPORTS_DIR, DOWNLOADS_DIR, CACHE_DIR]:
        if folder.exists():
            for f in folder.glob("*"):
                if f.is_file() and not f.name.startswith("."):
                    try:
                        if now - f.stat().st_mtime > max_age_seconds:
                            f.unlink(missing_ok=True)
                    except Exception:
                        pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class AnalyzeRequest(BaseModel):
    url: str
    gemini_api_key: Optional[str] = None

class RenderRequest(BaseModel):
    url: str
    clip_id: str
    start_time: float
    end_time: float
    hook_text: str
    hook_style: str = "badge_yellow"
    layout: str = "blurred_bg" # "blurred_bg" | "crop_center" | "split"
    speaker_focus: str = "center" # "center" | "left" | "right" | "split" | float
    show_hook: bool = True
    subtitle_style: str = "karaoke_yellow"
    font_size: int = 58

class SettingsRequest(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    default_layout: Optional[str] = None
    default_hook_style: Optional[str] = None
    default_subtitle_style: Optional[str] = None

# Static Files & Assets Serving (Flat Mode)
@app.get('/favicon.ico', include_in_schema=False)
@app.get('/favicon.svg', include_in_schema=False)
async def favicon():
    if os.path.exists('favicon.svg'):
        return FileResponse(path='favicon.svg', media_type='image/svg+xml')
    return JSONResponse(status_code=204, content={})

@app.get('/static/css/style.css')
@app.get('/style.css')
async def serve_css():
    return FileResponse('style.css', media_type='text/css')

@app.get('/static/js/preview.js')
@app.get('/preview.js')
async def serve_preview_js():
    return FileResponse('preview.js', media_type='application/javascript')

@app.get('/static/js/app.js')
@app.get('/app.js')
async def serve_app_js():
    return FileResponse('app.js', media_type='application/javascript')

@app.get('/', response_class=HTMLResponse)
async def serve_index():
    if os.path.exists('index.html'):
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    return '<h1>KLIP KLIP Studio is running.</h1>'

@app.get("/api/health")
async def health_check():
    settings = load_settings()
    has_gemini = bool(settings.get("gemini_api_key"))
    return {
        "status": "online",
        "app_name": "KLIP KLIP",
        "ffmpeg_path": FFMPEG_PATH,
        "ffmpeg_available": os.path.exists(FFMPEG_PATH),
        "gemini_configured": has_gemini,
        "storage": {
            "exports": len(list(EXPORTS_DIR.glob("*.mp4"))),
            "transcripts": len(list(TRANSCRIPTS_DIR.glob("*.json")))
        }
    }

@app.get("/api/settings")
async def get_settings():
    s = load_settings()
    masked_key = ""
    if s.get("gemini_api_key"):
        k = s["gemini_api_key"]
        masked_key = k[:4] + "••••••••" + k[-4:] if len(k) > 8 else "••••••••"
    return {
        "gemini_api_key_masked": masked_key,
        "has_gemini_key": bool(s.get("gemini_api_key")),
        "gemini_model": s.get("gemini_model", "gemini-1.5-flash"),
        "default_layout": s.get("default_layout", "blurred_bg"),
        "default_hook_style": s.get("default_hook_style", "badge_yellow"),
        "default_subtitle_style": s.get("default_subtitle_style", "karaoke_yellow")
    }

@app.post("/api/settings")
async def update_settings(req: SettingsRequest):
    data = req.model_dump(exclude_unset=True)
    updated = save_settings(data)
    return {"status": "success", "message": "Pengaturan berhasil disimpan."}

@app.post("/api/analyze")
async def analyze_video(req: AnalyzeRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL YouTube tidak boleh kosong.")
    
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="URL YouTube tidak valid.")

    try:
        # 1. Fetch metadata
        metadata = get_video_metadata(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengambil info video: {str(e)}")

    try:
        # 2. Fetch transcript
        transcript_items = get_video_transcript(video_id)
    except Exception as e:
        transcript_items = []
        print(f"Transcript warning: {e}")

    # 3. Analyze for viral clips
    try:
        clips = analyze_video_for_viral_clips(
            transcript_items=transcript_items,
            video_metadata=metadata,
            custom_gemini_key=req.gemini_api_key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menganalisis klip: {str(e)}")

    return {
        "status": "success",
        "video_id": video_id,
        "metadata": metadata,
        "transcript_available": len(transcript_items) > 0,
        "transcript_count": len(transcript_items),
        "clips": clips
    }

@app.post("/api/render")
async def render_clip(req: RenderRequest):
    cleanup_old_files()
    url = req.url.strip()
    video_id = extract_video_id(url) or "custom_clip"
    timestamp = int(time.time())
    clip_filename = f"klipklip_{video_id}_{req.clip_id}_{timestamp}.mp4"
    output_mp4 = str(EXPORTS_DIR / clip_filename)

    # 1. Download video segment
    raw_segment_path = str(DOWNLOADS_DIR / f"segment_{video_id}_{int(req.start_time)}_{int(req.end_time)}.mp4")
    
    try:
        download_video_segment(
            url=url,
            start_sec=req.start_time,
            end_sec=req.end_time,
            output_path=raw_segment_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mengunduh segmen video: {str(e)}")

    # 2. Generate subtitles
    transcript_items = get_video_transcript(video_id)
    ass_path = None
    if transcript_items:
        ass_path = str(CACHE_DIR / f"sub_{video_id}_{req.clip_id}_{timestamp}.ass")
        generate_ass_subtitles(
            transcript_items=transcript_items,
            clip_start=req.start_time,
            clip_end=req.end_time,
            output_ass_path=ass_path,
            style_name=req.subtitle_style,
            font_size=req.font_size
        )

    # 3. Render 9:16 vertical video with Hook & Subtitle
    try:
        rendered_file = render_vertical_clip(
            input_video=raw_segment_path,
            output_mp4=output_mp4,
            start_sec=0.0, # Segment is already trimmed from start_sec
            end_sec=max(5.0, req.end_time - req.start_time),
            layout=req.layout,
            speaker_focus=req.speaker_focus,
            show_hook=req.show_hook,
            hook_text=req.hook_text,
            hook_style=req.hook_style,
            ass_subtitle_path=ass_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal me-render video FFmpeg: {str(e)}")

    return {
        "status": "success",
        "filename": clip_filename,
        "download_url": f"/api/download/{clip_filename}",
        "message": "Klip video berhasil dirender!"
    }

@app.get("/api/download/{filename}")
async def download_rendered_video(filename: str):
    file_path = EXPORTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File video tidak ditemukan.")
    return FileResponse(
        path=str(file_path),
        media_type="video/mp4",
        filename=filename
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
