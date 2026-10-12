import json
import re
from typing import List, Dict, Any, Optional
from config import load_settings
from virality_scorer import calculate_virality_score, generate_social_package

VIRAL_PROMPT_SYSTEM = """Anda adalah Senior Viral Video Editor & Algorithmic Growth Specialist untuk program monetisasi klip video (MotionKlip, KlipReward, TikTok Creator Rewards, YouTube Shorts, Reels).

Tugas Anda:
Analisis transkrip video berikut secara mendalam, lalu temukan 3 hingga 6 momen TERBAIK yang paling berpotensi VIRAL dan meledak di platform video pendek (Shorts/TikTok/Reels).

Kriteria Klip Viral Pemenang:
1. DURASI IDEAL: Antara 30 hingga 60 detik (sangat diutamakan 35-50 detik untuk retensi tontonan >80%).
2. HOOK MENOHOK: Kalimat pembuka dalam 3 detik pertama harus langsung memancing rasa penasaran ("Stop-the-scroll"), kontroversial, pertanyaan provokatif, atau rahasia yang terbongkar.
3. INTI PESAN LENGKAP: Momen tersebut harus memiliki konteks yang utuh (masalah -> penjelasan/punchline), sehingga penonton puas tanpa harus menonton video panjangnya.
4. HEADLINE HOOK (OVERLAY): Buat teks hook singkat (5-9 kata) dengan HURUF BESAR (CAPITAL) dan emoji relevan yang akan ditempelkan di bagian atas video (Contoh: "JANGAN INVESTASI SEBELUM TAHU RAHASIA INI! 💸", "FAKTA MENGERIKAN TENTANG GAJI DI INDONESIA 😱").

PENTING: Keluarkan HANYA array JSON murni tanpa markdown formatting atau pembuka/penutup penjelasan lain:
[
  {
    "title": "Judul klip menarik",
    "hook_text": "HEADLINE HOOK VIRAL HURUF BESAR 😱",
    "start_time": 12.0,
    "end_time": 54.0,
    "virality_reason": "Alasan mengapa klip ini memicu share dan komentar tinggi",
    "keywords": ["kata1", "kata2"]
  }
]
"""

def heuristic_analyze_transcript(transcript_items: List[Dict[str, Any]], video_duration: float) -> List[Dict[str, Any]]:
    """Smart fallback parser when no AI API key is configured or offline."""
    if not transcript_items:
        # Generate 3-4 golden segments across video duration
        dur_segment = 42.0
        total_d = max(45.0, float(video_duration))
        clips_no_sub = []
        
        sample_moments = [
            (0.0, "Momen Pembuka Berenergi Tinggi", "TONTON SAMPAI HABIS BIAR GA SALAH PAHAM! 🔥"),
            (min(total_d * 0.3, total_d - 45.0), "Puncak Diskusi Menarik", "FAKTA INI BIKIN BANYAK ORANG KAGET! 😱"),
            (min(total_d * 0.6, total_d - 45.0), "Insight & Momen Paling Seru", "JANGAN PERNAH LEWATKAN BAGIAN INI! ⚠️"),
            (max(0.0, total_d - 50.0), "Pesan Penutup & Kesimpulan Penting", "KESIMPULAN INI JARANG DIBAHAS ORANG! 💡")
        ]
        
        # Deduplicate and sort
        seen_starts = set()
        for idx, (st, title, hook) in enumerate(sample_moments):
            st_clean = round(max(0.0, st), 1)
            if st_clean in seen_starts:
                continue
            seen_starts.add(st_clean)
            en_clean = round(min(total_d, st_clean + dur_segment), 1)
            clips_no_sub.append({
                "clip_id": f"clip_{len(clips_no_sub)+1}",
                "title": title,
                "hook_text": hook,
                "start_time": st_clean,
                "end_time": en_clean,
                "duration": round(en_clean - st_clean, 1),
                "virality_reason": "Segmen ini memiliki dinamika ritme tinggi yang cocok untuk retensi Shorts.",
                "keywords": ["viral", "klip", "trending", "shorts"]
            })
            if len(clips_no_sub) >= 4:
                break
        return clips_no_sub

    # Scan for emotional & controversial keywords
    curiosity_words = [
        "rahasia", "sebenarnya", "karena", "faktanya", "masalahnya", "ternyata",
        "kenapa", "alasan", "jangan", "jangan pernah", "hati-hati", "bahaya",
        "uang", "kaya", "rugi", "sukses", "gila", "parah", "aneh", "trik",
        "cara", "tips", "bocoran", "terbongkar", "sadar"
    ]

    clips = []
    total_items = len(transcript_items)
    step = max(1, total_items // 6)
    
    for idx in range(0, total_items - 5, step):
        chunk_start = transcript_items[idx]['start']
        # Find 35-50 second window
        target_end = chunk_start + 45.0
        end_idx = idx
        snippet_text = []
        for j in range(idx, min(total_items, idx + 40)):
            item = transcript_items[j]
            snippet_text.append(item['text'])
            end_idx = j
            if item['start'] + item.get('duration', 2) >= target_end:
                break
        
        chunk_end = transcript_items[end_idx]['start'] + transcript_items[end_idx].get('duration', 2)
        dur = round(chunk_end - chunk_start, 1)
        if dur < 20 or dur > 70:
            dur = 45.0
            chunk_end = chunk_start + dur

        full_chunk_text = " ".join(snippet_text)
        
        # Determine Hook Text based on text content
        hook = "FAKTA PENTING INI WAJIB KALIAN TAHU! 😱"
        for word in curiosity_words:
            if word in full_chunk_text.lower():
                if word in ["rahasia", "terbongkar", "bocoran"]:
                    hook = "RAHASIA INI AKHIRNYA TERBONGKAR! 🤫🔥"
                elif word in ["jangan", "hati-hati", "bahaya"]:
                    hook = "JANGAN PERNAH LAKUKAN INI SEBELUM MENYESAL! ⚠️"
                elif word in ["uang", "kaya", "sukses"]:
                    hook = "TRIK CUAN INI JARANG DIBONGKAR ORANG! 💸"
                elif word in ["ternyata", "faktanya", "sebenarnya"]:
                    hook = "TERNYATA INI FAKTA ASLINYA, BIKIN KAGET! 🤯"
                break

        title = full_chunk_text[:50].strip() + "..." if len(full_chunk_text) > 50 else "Highlight Momen Penting"
        clips.append({
            "clip_id": f"clip_{len(clips)+1}",
            "title": title,
            "hook_text": hook,
            "start_time": round(chunk_start, 1),
            "end_time": round(chunk_end, 1),
            "duration": dur,
            "virality_reason": "Bagian ini memiliki kepadatan informasi tinggi dan cocok untuk video pendek retensi tinggi.",
            "keywords": ["viral", "klipklip", "fakta"]
        })
        if len(clips) >= 5:
            break

    return clips

def analyze_video_for_viral_clips(
    transcript_items: List[Dict[str, Any]], 
    video_metadata: Dict[str, Any],
    custom_gemini_key: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Analyze transcript with Google Gemini API, with automatic heuristic fallback."""
    settings = load_settings()
    api_key = custom_gemini_key or settings.get("gemini_api_key")
    
    # Format transcript with timestamps
    transcript_lines = []
    for item in transcript_items[:600]: # Limit tokens to prevent context overload
        start_min = int(item['start'] // 60)
        start_sec = int(item['start'] % 60)
        transcript_lines.append(f"[{start_min:02d}:{start_sec:02d}] {item['text']}")
    
    transcript_text = "\n".join(transcript_lines)
    
    raw_clips = []
    
    # Try Google Gemini if API Key provided
    if api_key and transcript_text.strip():
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            
            prompt_content = f"{VIRAL_PROMPT_SYSTEM}\n\nJUDUL VIDEO: {video_metadata.get('title', '')}\nDURASI TOTAL: {video_metadata.get('duration', 0)} detik\n\nTRANSKRIP:\n{transcript_text}"
            
            # Model options: gemini-2.0-flash, gemini-1.5-flash
            model_name = settings.get("gemini_model", "gemini-1.5-flash")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_content,
            )
            
            resp_text = response.text or ""
            # Extract JSON block
            json_match = re.search(r'\[\s*\{.*\}\s*\]', resp_text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, list) and len(parsed) > 0:
                    raw_clips = parsed
        except Exception as e:
            print(f"Gemini API analysis notice: {e}, using heuristic engine.")

    # Fallback if Gemini not configured or failed
    if not raw_clips:
        raw_clips = heuristic_analyze_transcript(transcript_items, video_metadata.get('duration', 300))

    # Process and enrich each clip with virality scoring & social media packages
    enriched_clips = []
    for i, clip in enumerate(raw_clips):
        clip_id = f"clip_{i+1}"
        start_time = float(clip.get("start_time", 0))
        end_time = float(clip.get("end_time", start_time + 40))
        dur = round(max(15.0, end_time - start_time), 1)
        hook_text = clip.get("hook_text", "JANGAN LEWATKAN INI! 🔥").upper().strip()
        title = clip.get("title", f"Klip Viral #{i+1}")
        reason = clip.get("virality_reason", "Potensi retensi tinggi.")
        keywords = clip.get("keywords", ["viral", "shorts", "reels"])
        
        # Get snippet text for this timeframe
        snippet_words = [it['text'] for it in transcript_items if start_time <= it['start'] <= end_time]
        snippet_str = " ".join(snippet_words)
        
        virality_data = calculate_virality_score(dur, hook_text, snippet_str)
        social_pkg = generate_social_package(title, hook_text, keywords)
        
        enriched_clips.append({
            "clip_id": clip_id,
            "title": title,
            "hook_text": hook_text,
            "start_time": start_time,
            "end_time": end_time,
            "duration": dur,
            "virality_reason": reason,
            "keywords": keywords,
            "transcript_snippet": snippet_str[:250] + ("..." if len(snippet_str) > 250 else ""),
            "virality": virality_data,
            "social": social_pkg
        })

    return enriched_clips
