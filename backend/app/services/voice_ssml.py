# FILE: backend/app/services/voice_ssml.py

import re
import base64
import edge_tts
from typing import Optional, Tuple

VOICE_CONFIG = {
    "EN": {
        "voice": "en-US-AvaNeural",
        "rate": "-8%",
        "pitch": "+0Hz"
    },
    "BN": {
        "voice": "bn-IN-TanishaaNeural",
        "rate": "-10%",
        "pitch": "-2Hz"
    }
}

async def render_neural_voice(text: str, mood: str = "WARM") -> Tuple[Optional[str], str]:
    """
    Renders expressive audio using Edge-TTS with clean text, proper rate/pitch,
    and completely stripping markdown, links, and symbols to prevent the tag-reading bug.
    """
    if not text:
        return None, ""

    # 1. Aggressively strip system tags, markdown links, URLs, and symbols
    clean = re.sub(r'\[SEND_PIC:.*?\]', '', text, flags=re.IGNORECASE)
    clean = re.sub(r'\[SEND_VID:.*?\]', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'https?://\S+|www\.\S+', '', clean)  # Remove all URLs
    clean = re.sub(r'[*_#`~\[\]()<>{}]+', '', clean)    # Remove markdown/symbol clutter
    clean = re.sub(r'\s+', ' ', clean).strip()           # Normalize whitespace

    if not clean:
        return None, ""

    # 2. Detect language
    is_bangla = bool(re.search(r'[\u0980-\u09FF]', clean))
    lang_key = "BN" if is_bangla else "EN"
    cfg = VOICE_CONFIG[lang_key]

    # 3. Dynamic Mood Modulation
    rate = cfg["rate"]
    pitch = cfg["pitch"]
    if mood in ["SEDUCTIVE", "SAD"]:
        rate = "-18%"
        pitch = "-4Hz"
    elif mood in ["PLAYFUL", "HAPPY"]:
        rate = "-4%"
        pitch = "+3Hz"

    try:
        # Pass pure sanitized text directly to Edge-TTS (No raw XML/SSML markup)
        communicate = edge_tts.Communicate(text=clean, voice=cfg["voice"], rate=rate, pitch=pitch)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]

        if audio_bytes:
            return base64.b64encode(audio_bytes).decode("utf-8"), clean
    except Exception as e:
        print(f"⚠️ [VOICE RENDER ERROR]: {e}")

    return None, clean