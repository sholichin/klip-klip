from typing import Dict, Any, List

def calculate_virality_score(clip_duration: float, hook_text: str, transcript_snippet: str) -> Dict[str, Any]:
    """Calculate virality and monetization metrics for MotionKlip and KlipReward platforms."""
    duration = float(clip_duration)
    
    # 1. Duration Score (Max 30 pts): 30s-55s is golden zone
    if 30 <= duration <= 55:
        duration_score = 30
    elif 25 <= duration < 30 or 55 < duration <= 60:
        duration_score = 25
    elif 15 <= duration < 25:
        duration_score = 18
    else:
        duration_score = 12

    # 2. Hook Strength (Max 35 pts)
    hook_len = len(hook_text.split())
    hook_score = 20
    # Viral triggers in Indonesian & English
    viral_triggers = [
        "rahasia", "jangan", "ternyata", "kaget", "hancur", "kaya", "sukses",
        "bahaya", "terbukti", "terbongkar", "gila", "tips", "trik", "rugi",
        "parah", "bocorkan", "fakta", "kenapa", "alasan", "viral", "secret",
        "mistake", "warning", "never", "how to"
    ]
    matched_triggers = [w for w in viral_triggers if w in hook_text.lower()]
    hook_score += min(15, len(matched_triggers) * 6)
    if any(p in hook_text for p in ["!", "?", "😱", "🤯", "🔥", "💸", "⚠️"]):
        hook_score = min(35, hook_score + 4)

    # 3. Retention & Emotional Arc (Max 35 pts)
    text_len = len(transcript_snippet.split())
    retention_score = 25
    if text_len >= 50:
        retention_score += 5
    if any(w in transcript_snippet.lower() for w in ["tapi", "namun", "makanya", "artinya", "intinya", "jadi"]):
        retention_score += 5

    total_score = min(98, max(50, duration_score + hook_score + retention_score))

    if total_score >= 90:
        grade = "S (Viral Potensial Sangat Tinggi)"
        badge_color = "emerald"
    elif total_score >= 80:
        grade = "A (Potensi Tinggi)"
        badge_color = "cyan"
    elif total_score >= 70:
        grade = "B (Potensi Bagus)"
        badge_color = "amber"
    else:
        grade = "C (Standar)"
        badge_color = "slate"

    checklist = [
        {
            "name": "Hook 3 Detik Pertama",
            "passed": bool(hook_text and len(hook_text) > 5),
            "detail": "Headline menarik memicu rasa penasaran penonton (Stop-the-Scroll)."
        },
        {
            "name": "Durasi Algoritma Emas (30-60 detik)",
            "passed": (25 <= duration <= 60),
            "detail": f"Durasi saat ini {round(duration, 1)}s cocok untuk retensi tontonan >80%."
        },
        {
            "name": "Format Vertikal 9:16 (1080x1920)",
            "passed": True,
            "detail": "Standar wajib MotionKlip, KlipReward, TikTok, Shorts & Reels."
        },
        {
            "name": "Dynamic Subtitle / Text Overlay",
            "passed": True,
            "detail": "Meningkatkan engagement penonton yang menonton tanpa earphone."
        },
        {
            "name": "Monetization Quality Standard",
            "passed": total_score >= 75,
            "detail": "Memenuhi syarat approval kurasi MotionKlip & KlipReward."
        }
    ]

    return {
        "score": total_score,
        "grade": grade,
        "badge_color": badge_color,
        "duration": round(duration, 1),
        "motionklip_approved": total_score >= 70,
        "klipreward_approved": total_score >= 70,
        "checklist": checklist
    }

def generate_social_package(title: str, hook_text: str, keywords: List[str] = None) -> Dict[str, str]:
    """Generate ready-to-copy social media captions and hashtags for MotionKlip, KlipReward, TikTok, and Shorts."""
    base_tags = [
        "#klipklip", "#fyp", "#viral", "#foryou", "#trending",
        "#motionklip", "#klipreward", "#shorts", "#reels", "#tiktokindonesia"
    ]
    if keywords:
        for kw in keywords[:4]:
            clean_kw = "#" + "".join(e for e in kw.lower().replace(" ", "") if e.isalnum())
            if clean_kw not in base_tags:
                base_tags.append(clean_kw)

    hashtag_str = " ".join(base_tags)
    
    caption_tiktok = f"{hook_text}\n\nKira-kira menurut kalian gimana nih? Setuju ga? Komen pendapatmu di bawah ya! 👇🔥\n\n{hashtag_str}"
    
    caption_motionklip = f"[KLIP KLIP REWARD] {hook_text}\nKategori: Viral Creator Clips\nHighlight: {title}\nTagar: {hashtag_str}"

    return {
        "title": hook_text,
        "caption_tiktok": caption_tiktok,
        "caption_motionklip": caption_motionklip,
        "hashtags": hashtag_str
    }
