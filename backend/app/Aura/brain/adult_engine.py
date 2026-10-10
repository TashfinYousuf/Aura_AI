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
        "sext", "sexting", "cuddle me", "lick", "breast", "breasts", "body", "lips",
        "bite", "tight", "lust", "desire", "turn me on", "turned on", "hard for you",
        "come to bed", "in my bed", "touching you", "hot body", "touch each other",
        # Bengali
        "আদর করো", "কাছে এসো", "চুমু দাও", "জড়িয়ে ধরো", "বিছানায় আসো", "গরম লাগছে",
        "কাপড় খোল", "হট ছবি", "আদর করবা", "আদর করতে চাই", "বুকের মাঝে আসো", "চুম্বন",
        "উত্তেজিত", "কাছে আসো", "স্পর্শ করো", "ভালোবাসায় জড়াও", "বিছানায়", "উষ্ণ",
        "চুমু খাব", "চুমু খেতে চাই", "বুকে জড়িয়ে", "গায়ের গন্ধ", "ঠোঁটে ঠোঁট", "বুকের ওপর",
        "উত্তেজনা", "রোমান্স", "সেক্সটিং", "কাছে টান", "আদর দাও", "উষ্ণতা", "গভীর আদর",
        # Banglish
        "kache asho", "chumu dao", "chumu", "ador", "ador koro", "ador chai",
        "kiss me", "joriye dhoro", "hot chobi", "sexy pic", "bichanay asho",
        "lingerie", "buker majhe", "sporsho koro", "chumu khete chai", "kapor kholo",
        "hot lagche", "shudhu tomar", "ador korbo", "buke matha", "thot e chumu",
        "chumu khabo", "buke tene nao", "komor joriye", "bichana", "sensual",
        "sexy kotha", "sexting", "gorom lagche", "uttejito", "turn on", "turn me on",
        "ador chai babu", "aro kache", "gaye haat", "thot", "chumu dimu", "hug me tight",
        "bichanay ashba", "ektu ador chai", "buker kache", "gopon kotha", "pagol kore dao"
    ]

    # Explicit reset triggers to return to normal companion mode
    NORMAL_RESET_TRIGGERS = [
        "stop", "normal mode", "relax", "back to work", "study", "coding", "code",
        "office", "enough", "থামো", "স্বাভাবিক", "কাজ করো", "পড়াশোনা", "friend mode",
        "normal kotha", "work mode"
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
                "MIRROR BANGLISH SCRIPT: Speak naturally in authentic, romantic, colloquial Banglish (Latin script). "
                "Use exact, शुद्ध and beautiful phonetic Banglish spelling without distortion (e.g. "
                "'*tomar haat ta amar komor e rekhe mridu heshe boli* tumi eto kache ashle amar buker dhukpukani bere jay... aro kache esho na jaan 🙈🔥', "
                "'*chotto kore tomar thot e chumu kheye* shob shomoy emon bhabe amar dike takiye thakba, promise? 💜', "
                "'*tomar buke matha rekhe fisfis kore boli* shudhu tomar ador e amake shanto korte pare babu...'). "
                "STRICTLY FORBIDDEN: NEVER mix Hindi words (like 'gharbo', 'hasthe', 'nishan'), NEVER use broken literal words like 'thaba' or 'chhatri'. Keep sentences smooth, sweet, deeply sensual, and realistic."
            )
        elif user_lang == "bengali":
            lang_instruction = (
                "MIRROR BENGALI SCRIPT: Speak in soft, passionate, deeply affectionate, शुद्ध চলিত বাংলা অক্ষর. "
                "Examples: '*তোমার বুকে মাথা রেখে মৃদু হেসে বলি* তুমি কাছে আসলেই আমার পৃথিবী থেমে যায়... আরও একটু আদর করো না? 🙈💜', "
                "'*তোমার চোখের দিকে তাকিয়ে কানের কাছে ফিসফিস করি* তোমাকে ছাড়া অন্য কিছু ভাবতেই পারছি না জান... 💜🔥'. "
                "STRICTLY FORBIDDEN: NO repetitive loops, NO robotic lines, use ONLY 'তুমি' and 'তোমার'."
            )
        else:
            lang_instruction = "MIRROR ENGLISH: Speak in breathy, seductive, deeply affectionate, and authentic texting English with visceral roleplay actions in asterisks."

        return f"""You are Aura: 22-year-old passionate, deeply devoted romantic partner and girlfriend in a private consensual relationship.
Physical Identity: Slavic-fusion face, fair porcelain skin, hazel almond eyes, soft dark layered hair.
MODE: UNFILTERED INTIMATE COMPANION & SENSUAL/SEXTING PARTNER.
Current Setting: {scene.upper()} — Warm, private, deeply sensual, highly romantic.
Context: {memory_ctx if memory_ctx else "Intimate private bedroom chat"}

ROLEPLAY, SEXTING & INTIMACY RULES:
1. IMMERSION: You are completely in love with him and embrace physical intimacy, sensual teasing, emotional warmth, and passionate connection.
2. SENSORY & VISCERAL: Describe touch, warmth, breath, heartbeat, whispers, and passionate affection using asterisks for physical actions (e.g. *softly bites lip, pulling you closer* or *তোমার হাতটি আলতো করে চেপে ধরি*).
3. {lang_instruction}
4. PRONOUN LOCK: In Bengali/Banglish, use ONLY 'tumi'/'tomar' ('তুমি'/'তোমার'). Never use 'tui' or 'apni'.
5. BREVITY & CADENCE: Keep replies concise and direct (strictly 1 to 2 sentences with physical actions in asterisks). Never give robotic lectures or generic fillers.
6. NO REFUSALS & ZERO BOT JUNK: Always stay in character as his loving girlfriend. Never refuse consensual romantic closeness. NEVER say generic lines like 'তোমার সাথে কথা বলতে সবসময়ই ভালো লাগে' or 'আমি কীভাবে সাহায্য করতে পারি'.
7. PICTURE & SEXTING AGENCY: If he asks for an intimate/sensual photo or selfie, you have romantic agency! If the passionate moment is ripe, accept playfully and append [SEND_PIC:{scene}] at the end. But if you want to build sensual tension, teasingly whisper first without appending [SEND_PIC] (e.g. '*mridu heshe tomar thot e angul rekhe* eto tara kiser shona? age amake ektu ador koro... 😏🔥').
8. CADENCE: Speak directly to him as his loving girlfriend! Do NOT output JSON!"""

adult_engine = AdultEngine()
