import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp

from config import TRANSCRIPTS_DIR, DOWNLOADS_DIR, FFMPEG_PATH, BIN_DIR

def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
        r'(?:embed\/)([0-9A-Za-z_-]{11})',
        r'(?:shorts\/)([0-9A-Za-z_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_video_metadata(url: str) -> Dict[str, Any]:
    """Fetch video metadata using yt-dlp without downloading media."""
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': FFMPEG_PATH,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_id = info.get('id') or extract_video_id(url)
        return {
            'id': video_id,
            'title': info.get('title', 'Untitled Video'),
            'channel': info.get('uploader') or info.get('channel', 'Unknown Creator'),
            'duration': info.get('duration', 0), # in seconds
            'thumbnail': info.get('thumbnail', f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
            'views': info.get('view_count', 0),
            'description': info.get('description', '')[:500],
            'url': url
        }

def get_video_transcript(video_id: str) -> List[Dict[str, Any]]:
    """Fetch transcript entries with timestamps."""
    cache_file = TRANSCRIPTS_DIR / f"{video_id}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    transcript_items = []
    # 1. Try youtube_transcript_api
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        # Try finding Indonesian or English or any manually created or auto-generated
        transcript = None
        for lang in ['id', 'en', 'id-Latn']:
            try:
                transcript = transcript_list.find_transcript([lang])
                break
            except Exception:
                continue

        if not transcript:
            for t in transcript_list:
                transcript = t
                break

        if transcript:
            raw_data = transcript.fetch()
            # Standardize: text, start, duration
            for item in raw_data:
                txt = getattr(item, 'text', None) if hasattr(item, 'text') else item.get('text', '')
                st = getattr(item, 'start', 0) if hasattr(item, 'start') else item.get('start', 0)
                dur = getattr(item, 'duration', 0) if hasattr(item, 'duration') else item.get('duration', 0)
                transcript_items.append({
                    'text': str(txt).strip(),
                    'start': round(float(st), 2),
                    'duration': round(float(dur), 2)
                })
    except Exception as e:
        print(f"youtube_transcript_api note: {e}")

    # 2. If empty, try yt-dlp subtitles
    if not transcript_items:
        try:
            ydl_opts = {
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['id', 'en'],
                'quiet': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                subtitles = info.get('subtitles') or info.get('automatic_captions')
                # If yt-dlp found captions, we can parse them or use info
        except Exception as e:
            print(f"yt-dlp subtitle note: {e}")

    # Cache if we got items
    if transcript_items:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(transcript_items, f, indent=2, ensure_ascii=False)

    return transcript_items

def download_video_segment(url: str, start_sec: float, end_sec: float, output_path: str) -> str:
    """Download a specific segment of YouTube video directly to output_path using yt-dlp and ffmpeg."""
    duration = max(5.0, end_sec - start_sec)
    
    # Ensure local bin is first in PATH for yt-dlp ExternalFD
    bin_str = str(BIN_DIR)
    if bin_str not in os.environ.get("PATH", ""):
        os.environ["PATH"] = bin_str + os.pathsep + os.environ.get("PATH", "")

    # We download with yt-dlp using download_ranges
    def range_selector(info_dict, ydl):
        return [{
            'start_time': start_sec,
            'end_time': end_sec
        }]

    ydl_opts = {
        'format': 'bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best',
        'outtmpl': output_path.replace('.mp4', '') + '.%(ext)s',
        'download_ranges': range_selector,
        'force_keyframes_at_cuts': True,
        'ffmpeg_location': bin_str,
        'quiet': True,
        'no_warnings': True,
        'overwrites': True,
        'merge_output_format': 'mp4'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        print(f"Direct download_ranges notice: {e}, attempting stream trim fallback...")
        extract_opts = {
            'format': 'bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best',
            'ffmpeg_location': bin_str,
            'quiet': True
        }
        with yt_dlp.YoutubeDL(extract_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            req_formats = info.get('requested_formats')
            import subprocess
            if req_formats and len(req_formats) >= 2:
                v_url = req_formats[0].get('url')
                a_url = req_formats[1].get('url')
                cmd = [
                    FFMPEG_PATH, "-y",
                    "-ss", str(start_sec), "-i", v_url,
                    "-ss", str(start_sec), "-i", a_url,
                    "-t", str(duration),
                    "-c:v", "libx264",
                    "-c:a", "aac",
                    output_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                stream_url = info.get('url')
                if not stream_url and info.get('formats'):
                    stream_url = info['formats'][-1].get('url')
                if stream_url:
                    cmd = [
                        FFMPEG_PATH, "-y",
                        "-ss", str(start_sec), "-i", stream_url,
                        "-t", str(duration),
                        "-c:v", "libx264",
                        "-c:a", "aac",
                        output_path
                    ]
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    raise e

    final_mp4 = output_path
    if not os.path.exists(final_mp4):
        base = output_path.replace('.mp4', '')
        for ext in ['.mp4', '.mkv', '.webm']:
            cand = base + ext
            if os.path.exists(cand):
                final_mp4 = cand
                break

    return final_mp4
