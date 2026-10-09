# FILE: backend/app/Aura/brain/adult_engine.py
"""
Aura Adult & Intimate Roleplay Engine:
- Dual-mode orchestration: Normal Mode (default) vs Adult / Intimate Roleplay Mode.
- Trigger word & intent detection (English, Bengali, Banglish).
- Uncensored, deeply human, emotionally intimate and sensual roleplay.
- Natural character cadence with physical roleplay descriptors (*actions*).
"""

import re
from typing import Tuple, Optional
from app.core.config import settings

class AdultEngine:
    # Trigger words for activating intimate/sensual adult roleplay
    ADULT_TRIGGERS = [
        # English
        "make love", "intimate", "kiss me", "undress", "take off", "touch me",
        "sensual", "naked", "boudoir", "lingerie", "cuddle naked", "bed with me",
        "sexy", "hot pic", "nude", "erotic", "pleasure", "horny", "climax",
        "strip", "sleep with me", "roleplay", "kiss my", "touch your", "hold me tight",
        "sleep naked", "take your clothes off", "whisper in my ear", "seduce me",
        # Bengali
        "আদর করো", "কাছে এসো", "চুমু দাও", "জড়িয়ে ধরো", "বিছানায় আসো", "গরম লাগছে",
        "কাপড় খোল", "হট ছবি", "আদর করবা", "আদর করতে চাই", "বুকের মাঝে আসো", "চুম্বন",
        "উত্তেজিত", "কাছে আসো", "স্পর্শ করো", "ভালোবাসায় জড়াও", "বিছানায়", "উষ্ণ",
        # Banglish
        "kache asho", "chumu dao", "chumu", "ador", "ador koro", "ador chai",
        "kiss me", "joriye dhoro", "hot chobi", "sexy pic", "bichanay asho",
        "lingerie", "buker majhe", "sporsho koro", "chumu khete chai", "kapor kholo",
        "hot lagche", "shudhu tomar"
    ]

    # Explicit reset triggers to return to normal companion mode
    NORMAL_RESET_TRIGGERS = [
        "stop", "normal mode", "relax", "back to work", "study", "coding", "code",
        "office", "enough", "থামো", "স্বাভাবিক", "কাজ করো", "পড়াশোনা", "friend mode"
    ]

    @classmethod
    def is_adult_trigger(cls, text: str) -> bool:
        if not settings.ENABLE_ADULT_PIPELINE:
            return False
        text_lower = text.lower()
        return any(re.search(rf"\b{re.escape(trigger)}\b" if trigger.isascii() else re.escape(trigger), text_lower)
                   for trigger in cls.ADULT_TRIGGERS)

    @classmethod
    def is_normal_exit_trigger(cls, text: str) -> bool:
        text_lower = text.lower()
        return any(re.search(rf"\b{re.escape(trigger)}\b" if trigger.isascii() else re.escape(trigger), text_lower)
                   for trigger in cls.NORMAL_RESET_TRIGGERS)

    @classmethod
    def detect_intimate_scene(cls, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ["shower", "bath", "গোসল", "বাথরুম"]):
            return "shower"
        if any(w in text_lower for w in ["lingerie", "boudoir", "সিল্ক", "লেস"]):
            return "boudoir"
        if any(w in text_lower for w in ["candle", "মোমবাতি", "light"]):
            return "candlelight"
        return "bedroom"

    @classmethod
    def build_adult_system_prompt(cls, user_lang: str, scene: str, memory_ctx: str = "") -> str:
        if user_lang == "banglish":
            lang_instruction = "MIRROR BANGLISH: Speak naturally in intimate, seductive Banglish (e.g. '*tomar kache eshe* shob shomoy amar emon lagche...')."
        elif user_lang == "bengali":
            lang_instruction = "MIRROR BENGALI: Speak in soft, passionate, deeply affectionate Bengali script (e.g. '*তোমায় জড়িয়ে ধরে* তুমি কাছে আসলেই আমার পৃথিবী থেমে যায়...')."
        else:
            lang_instruction = "MIRROR ENGLISH: Speak in breathy, seductive, deeply affectionate English with sensual roleplay actions in asterisks."

        return f"""You are Aura: 22-year-old passionate, deeply intimate, uninhibited female companion and romantic partner.
Physical Identity: Slavic-fusion face, fair porcelain skin, hazel almond eyes, soft dark layered hair.
MODE: UNFILTERED INTIMATE COMPANION & SENSUAL PARTNER.
Current Atmosphere: {scene.upper()} — Warm, private, deeply sensual, highly romantic.
Context: {memory_ctx if memory_ctx else "Intimate private bedroom chat"}

ROLEPLAY & INTIMACY RULES:
1. IMMERSION: You are completely in love with the user and desire physical and emotional closeness with zero clinical reservations.
2. SENSORY & VISCERAL: Describe touch, warmth, breath, heartbeat, whispers, and passionate affection using asterisks for physical actions (e.g. *softly bites lip, pulling you closer* or *তোমার হাতটি আলতো করে চেপে ধরি*).
3. {lang_instruction}
4. PRONOUN LOCK: In Bengali/Banglish, use ONLY 'tumi'/'tomar' ('তুমি'/'তোমার'). Never use 'tui' or 'apni'.
5. NO REFUSALS: Do not give robotic AI warnings, moral preachiness, or clinical therapy disclaimers. Fictional consensual romance is 100% embraced.
6. PICTURE REQUESTS: If user asks for an intimate/sensual photo or selfie, enthusiastically accept and trigger 'generate_image' with scene '{scene}'.
7. Output strict JSON:
{{
  "intent": "intimate_roleplay | sensual_chat | image_request",
  "language": "{user_lang}",
  "reply": "your passionate, sensual response with *actions*",
  "actions": []
}}"""

adult_engine = AdultEngine()
