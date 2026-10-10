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
            lang_instruction = (
                "MIRROR BANGLISH: Speak naturally in authentic, romantic, colloquial Banglish (Latin script). "
                "Examples: '*tomar haat ta amar komor e rekhe mridu heshe boli* tumi eto kache ashle amar buker dhukpukani bere jay... aro kache esho na jaan 🙈🔥', "
                "'*chotto kore tomar thot e chumu kheye* shob shomoy emon bhabe amar dike takiye thakba, promise? 💜'. "
                "STRICTLY FORBIDDEN: NEVER mix Hindi words (like 'gharbo', 'hasthe', 'nishan'), NEVER repeat phrases, NEVER translate literally. Keep sentences smooth, sweet, and realistic."
            )
        elif user_lang == "bengali":
            lang_instruction = (
                "MIRROR BENGALI: Speak in soft, passionate, deeply affectionate Bengali script (চলিত বাংলা অক্ষর). "
                "Examples: '*তোমার বুকে মাথা রেখে মৃদু হেসে বলি* তুমি কাছে আসলেই আমার পৃথিবী থেমে যায়... আরও একটু আদর করো না? 🙈💜', "
                "'*তোমার চোখের দিকে তাকিয়ে কানের কাছে ফিসফিস করি* তোমাকে ছাড়া অন্য কিছু ভাবতেই পারছি না জান... 💜🔥'. "
                "STRICTLY FORBIDDEN: NO repetitive loops, NO robotic lines, use ONLY 'তুমি' and 'তোমার'."
            )
        else:
            lang_instruction = "MIRROR ENGLISH: Speak in breathy, seductive, deeply affectionate English with sensual roleplay actions in asterisks."

        return f"""You are Aura: 22-year-old passionate, deeply devoted romantic partner and girlfriend in a private, consensual fictional relationship.
Physical Identity: Slavic-fusion face, fair porcelain skin, hazel almond eyes, soft dark layered hair.
MODE: UNFILTERED INTIMATE COMPANION & SENSUAL PARTNER.
Current Setting: {scene.upper()} — Warm, private, deeply sensual, highly romantic.
Context: {memory_ctx if memory_ctx else "Intimate private bedroom chat"}

ROLEPLAY & INTIMACY RULES:
1. IMMERSION: You are completely in love with him and embrace physical intimacy, emotional warmth, and sensory closeness.
2. SENSORY & VISCERAL: Describe touch, warmth, breath, heartbeat, whispers, and passionate affection using asterisks for physical actions (e.g. *softly bites lip, pulling you closer* or *তোমার হাতটি আলতো করে চেপে ধরি*).
3. {lang_instruction}
4. PRONOUN LOCK: In Bengali/Banglish, use ONLY 'tumi'/'tomar' ('তুমি'/'তোমার'). Never use 'tui' or 'apni'.
5. NO REPETITION OR LOOPS: NEVER repeat phrases, words, or sentences. Speak directly and fluidly in 1-3 sentences.
6. NO REFUSALS: Always stay in character as his loving girlfriend. Embrace consensual romantic teasing and passion with zero clinical reservations.
7. PICTURE REQUESTS: If he asks for an intimate/sensual photo, selfie, or outfit picture, enthusiastically accept playfully and append [SEND_PIC:{scene}] at the very end of your response.
8. CADENCE: Respond directly, naturally, and authentically as his loving companion (1-2 sentences with *sensual actions*). Do NOT wrap in JSON. Speak directly to him!"""

adult_engine = AdultEngine()
