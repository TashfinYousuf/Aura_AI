# FILE: backend/app/services/voice_prosody.py

import re
import random
from typing import Tuple

FILLERS_BN = {
    "WARM": ["হুম...", "শোনো...", "আসলে..."],
    "PLAYFUL": ["আরে...", "wait...", "হাহা, শোনো,"],
    "SEDUCTIVE": ["উম্ম...", "জানো..."],
    "SAD": ["আসলে...", "হুম..."]
}

FILLERS_EN = {
    "WARM": ["Umm...", "You know...", "Honestly..."],
    "PLAYFUL": ["Wait...", "Haha,", "Hey,"],
    "SEDUCTIVE": ["Uff...", "Mmm..."],
    "SAD": ["Well...", "I mean..."]
}

def humanize_speech_markup(text: str, mood: str = "WARM", lang: str = "BN") -> Tuple[str, str, str]:
    """
    Transforms raw chat reply into expressive, prosody-driven speech markup.
    Returns: (prosody_ready_text, tts_rate, tts_pitch)
    """
    # 1. Clean system tags, emojis, and URLs
    clean = re.sub(r'\[SEND_PIC:.*?\]', '', text, flags=re.IGNORECASE)
    clean = re.sub(r'\[SEND_VID:.*?\]', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'http\S+', '', clean)
    clean = re.sub(r'[^\w\s,.\?!।\'"a-zA-Z0-9\u0980-\u09FF]', '', clean).strip()

    # 2. Insert Micro-Behaviors (Conversational Fillers) at the beginning (40% probability)
    fillers_dict = FILLERS_BN if lang == "BN" else FILLERS_EN
    available_fillers = fillers_dict.get(mood, ["হুম..." if lang == "BN" else "Well..."])
    
    if random.random() < 0.40 and not any(clean.startswith(f) for f in available_fillers):
        clean = f"{random.choice(available_fillers)} {clean}"

    # 3. Prosody Punctuation Tuning (Adds natural breathing pauses)
    # Replace single periods with ellipses (...) for soft trailing voice
    clean = re.sub(r'([।\.])\s+', r'... ', clean)
    # Ensure commas have breathing space
    clean = re.sub(r',\s*', r', ', clean)

    # 4. Dynamic Pitch & Rate Modulation based on Mood
    rate = "-10%"
    pitch = "-2Hz"

    if mood in ["SEDUCTIVE", "SAD"]:
        rate = "-20%"  # Slower, softer whisper-like delivery
        pitch = "-4Hz"
    elif mood in ["PLAYFUL", "HAPPY"]:
        rate = "-5%"   # Lively, quick banter
        pitch = "+4Hz" # Higher tone showing excitement
    elif mood == "CALM":
        rate = "-12%"
        pitch = "-1Hz"

    return clean, rate, pitch