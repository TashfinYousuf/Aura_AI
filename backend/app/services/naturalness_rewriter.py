# FILE: backend/app/services/naturalness_rewriter.py

import re
import random

REPETITIVE_CLICHES = [
    r"প্যারা নাই",
    r"চিল করো",
    r"আমি সবসময় তোমার পাশে আছি",
    r"don't worry cutie",
    r"as you know, i",
]

CONVERSATIONAL_FILLERS_BN = ["হুম...", "আসলে...", "শোনো,", "আচ্ছা...", "wait,"]
CONVERSATIONAL_FILLERS_EN = ["Umm...", "Honestly...", "Wait,", "Well..."]

def sanitize_and_rhythmize(text: str, lang: str = "bn", energy_level: int = 50) -> str:
    """
    Strips robotic clichés, injects natural fillers based on energy,
    and formats conversational pacing.
    """
    cleaned_text = text

    # 1. Strip repetitive AI cliches
    for pattern in REPETITIVE_CLICHES:
        cleaned_text = re.sub(pattern, "", cleaned_text, flags=re.IGNORECASE)

    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    # 2. Add organic hesitation / fillers if energy is reflective
    if energy_level < 40 and not any(cleaned_text.startswith(f) for f in CONVERSATIONAL_FILLERS_BN + CONVERSATIONAL_FILLERS_EN):
        if lang == "bn" and random.random() < 0.35:
            cleaned_text = f"{random.choice(CONVERSATIONAL_FILLERS_BN)} {cleaned_text}"
        elif lang == "en" and random.random() < 0.35:
            cleaned_text = f"{random.choice(CONVERSATIONAL_FILLERS_EN)} {cleaned_text}"

    # 3. Prevent excessive sentence stacking in casual chat
    sentences = re.split(r'([.?!।])', cleaned_text)
    if len(sentences) > 6 and energy_level > 60:
        # Keep response punchy and natural
        cleaned_text = "".join(sentences[:6]).strip()

    return cleaned_text