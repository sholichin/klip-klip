import os
from pathlib import Path
from typing import List, Dict, Any

def format_timestamp_ass(seconds: float) -> str:
    """Format seconds into ASS timestamp: H:MM:SS.cs (centiseconds)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def format_timestamp_srt(seconds: float) -> str:
    """Format seconds into SRT timestamp: HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        ms = 999
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def generate_ass_subtitles(
    transcript_items: List[Dict[str, Any]], 
    clip_start: float, 
    clip_end: float, 
    output_ass_path: str,
    style_name: str = "karaoke_yellow",
    font_size: int = 58,
    vertical_margin: int = 380 # Position above bottom (1080x1920 canvas)
) -> str:
    """
    Generate Advanced SubStation Alpha (.ass) subtitles with bold outlines
    and animated short word chunks (Hormozi / TikTok style).
    """
    # Color palette (ASS uses &HAABBGGRR format)
    # White: &H00FFFFFF&, Yellow: &H0000E5FF&, Neon Green: &H0000FF7F&, Cyan: &H00FFFF00&, Black Outline: &H00000000&
    highlight_color = "&H0000E5FF&" # Vibrant Yellow
    if style_name == "karaoke_green":
        highlight_color = "&H002BF771&" # Neon Green
    elif style_name == "karaoke_cyan":
        highlight_color = "&H00FFF000&" # Cyan Blue
    elif style_name == "clean_white":
        highlight_color = "&H00FFFFFF&" # Pure White

    ass_content = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,Arial,{font_size},&H00FFFFFF&,{highlight_color},&H00000000&,&H80000000&,-1,0,0,0,100,100,1,0,1,6,3,2,60,60,{vertical_margin},1",
        f"Style: Highlight,Arial,{font_size},{highlight_color},&H00FFFFFF&,&H00000000&,&H80000000&,-1,0,0,0,105,105,1,0,1,6,3,2,60,60,{vertical_margin},1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]

    # Filter items within clip timeframe
    relevant_items = []
    for item in transcript_items:
        item_start = item['start']
        item_end = item_start + item.get('duration', 2.0)
        if item_end >= clip_start and item_start <= clip_end:
            relevant_items.append(item)

    # Break long items into short 3-5 word chunks for high visual engagement
    dialogue_chunks = []
    for item in relevant_items:
        words = item['text'].split()
        if not words:
            continue
        
        item_start = max(clip_start, item['start'])
        item_end = min(clip_end, item['start'] + item.get('duration', 2.5))
        total_time = max(0.5, item_end - item_start)
        
        chunk_size = 4 # words per subtitle flash
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i + chunk_size]
            c_start = item_start + (i / len(words)) * total_time
            c_end = item_start + ((i + len(chunk_words)) / len(words)) * total_time
            
            # Relative to clip start
            rel_start = max(0.0, c_start - clip_start)
            rel_end = max(rel_start + 0.3, c_end - clip_start)
            
            # Format text: uppercase bold with highlighted last or middle word
            if len(chunk_words) > 1 and style_name != "clean_white":
                # Highlight last word in yellow
                main_part = " ".join(chunk_words[:-1]).upper()
                accent_part = chunk_words[-1].upper()
                styled_text = f"{main_part} {{\\c{highlight_color}}}{accent_part}{{\\r}}"
            else:
                styled_text = " ".join(chunk_words).upper()
            
            dialogue_chunks.append((rel_start, rel_end, styled_text))

    # Append events
    for rel_start, rel_end, text in dialogue_chunks:
        start_str = format_timestamp_ass(rel_start)
        end_str = format_timestamp_ass(rel_end)
        ass_content.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}")

    output_path = Path(output_ass_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(ass_content))

    return str(output_path)

def generate_srt_subtitles(
    transcript_items: List[Dict[str, Any]], 
    clip_start: float, 
    clip_end: float, 
    output_srt_path: str
) -> str:
    """Generate standard SRT subtitles file."""
    srt_entries = []
    index = 1
    for item in transcript_items:
        i_start = item['start']
        i_end = i_start + item.get('duration', 2.5)
        if i_end >= clip_start and i_start <= clip_end:
            rel_start = max(0.0, i_start - clip_start)
            rel_end = max(rel_start + 0.5, i_end - clip_start)
            srt_entries.append(f"{index}\n{format_timestamp_srt(rel_start)} --> {format_timestamp_srt(rel_end)}\n{item['text'].strip()}\n")
            index += 1

    with open(output_srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_entries))
    return output_srt_path
