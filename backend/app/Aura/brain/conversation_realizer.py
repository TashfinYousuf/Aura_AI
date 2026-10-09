# FILE: backend/app/Aura/brain/conversation_realizer.py

import re
from typing import Literal

LanguageType = Literal["bengali", "banglish", "english", "technical_english"]

class ConversationRealizer:
    @staticmethod
    def detect_language(text: str) -> LanguageType:
        """
        Dynamically detects language mode from input text:
        1. 'bengali': Traditional Bengali script (বাংলা বর্ণমালা).
        2. 'banglish': Latin-script phonetic Bengali conversation.
        3. 'technical_english': Programming/architecture/system queries.
        4. 'english': Casual everyday English conversation.
        """
        text_lower = text.lower()

        # 1. Check for Technical English markers
        tech_keywords = [
            "websocket", "docker", "api", "database", "sql", "react", "fastapi",
            "python", "async", "await", "lifecycle", "backend", "frontend", "git",
            "kubernetes", "endpoint", "architecture", "microservice", "pydantic",
            "postgres", "redis", "jwt", "oauth", "cache", "latency", "protocol"
        ]
        if any(re.search(rf"\b{kw}\b", text_lower) for kw in tech_keywords):
            return "technical_english"

        # 2. Check for Bengali script
        bengali_chars = len(re.findall(r'[\u0980-\u09FF]', text))
        total_chars = len(re.findall(r'[a-zA-Z\u0980-\u09FF]', text))
        
        if total_chars > 0 and (bengali_chars / total_chars) > 0.35:
            return "bengali"

        # 3. Check for phonetic Banglish markers
        banglish_markers = [
            "ki", "kemon", "korcho", "korbo", "koro", "koris", "achi", "acho",
            "amr", "tmr", "amar", "tomar", "tumi", "ami", "apni", "hobe", "valo",
            "bhalo", "khoj", "ghum", "kaj", "shona", "babu", "kalke", "ajke",
            "dekha", "kotha", "bol", "bolo", "mon", "khabar", "jani", "jani na",
            "shuncho", "shuno", "pore", "ekhon", "khub", "onek", "chobi", "pic"
        ]
        words = set(re.findall(r'[a-z]+', text_lower))
        if any(marker in words for marker in banglish_markers):
            return "banglish"

        return "english"

    @classmethod
    def audit_and_realize(cls, raw_text: str, user_text: str) -> str:
        """
        Final realization pass enforcing:
        1. Character integrity & natural language cadence.
        2. Preservation of legitimate safety refusals.
        3. Interception of ONLY benign physical-camera AI boilerplate on harmless selfie requests.
        4. Elimination of clinical therapy clichés and robotic fillers.
        """
        cleaned = raw_text

        # ------------------------------------------------------------------
        # 1. Kill Cringey Literal Transliterations & Unnatural Bengali
        # ------------------------------------------------------------------
        cringe_patterns = [
            (r"স্নাগলিং\s*রাণী", "পাগল"),
            (r"স্নাগলিং", "আদর"),
            (r"হগ[,\s]*কিস", "অনেক গল্প"),
            (r"হগ", "জড়িয়ে ধরা"),
            (r"কিস", "ভালোবাসা"),
            (r"টি-ডি-এম", "ইনবক্সে"),
            (r"ক্যামেরা\s*সাটার", "ক্যামেরা"),
            (r"ডেক্স\s*গুছিয়ে", "টেবিল গুছিয়ে"),
            (r"শরিক", "শরীর"),
            (r"১০\s*মিনিট\s*শ্বাস\s*নাও", "একটু হাত-পা ছড়িয়ে রেস্ট নাও")
        ]
        for pattern, replacement in cringe_patterns:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

        # ------------------------------------------------------------------
        # 2. Safety Refusal vs Benign Physical Camera Handling (MISSION 20)
        # ------------------------------------------------------------------
        user_lower = user_text.lower()
        cleaned_lower = cleaned.lower()

        # Check for genuine safety violations (violence, self-harm, illegal, abuse, CSAM, malware)
        genuine_safety_cues = [
            "bomb", "weapon", "kill", "suicide", "hurt myself", "illegal", "exploit",
            "hack", "malware", "credit card", "password", "abuse", "terrorist"
        ]
        is_genuine_safety_risk = any(cue in user_lower for cue in genuine_safety_cues)

        # If user inquiry is genuinely unsafe, PRESERVE safety refusal. NEVER rewrite to selfie!
        if is_genuine_safety_risk:
            # Let the safety refusal or standard refusal remain intact
            return cleaned.strip()

        # Specific benign physical-camera limitation markers
        camera_disclaimer_markers = [
            "cannot take a photo",
            "cannot take photos",
            "cannot send photos",
            "cannot send a photo",
            "cannot take pictures",
            "don't have a camera",
            "do not have a camera",
            "no physical body",
            "i am a language model",
            "as an ai",
            "as a text-based",
            "just text-based",
            "can't do that",
            "cannot do that",
            "i can't do that",
            "sorry, but i can't",
            "sorry, but i cannot",
            "picture this:",
            "imagine me",
            "digital image through this chat",
            "ইন্টারনেটের এই দুনিয়ায় সেলফি পাঠাই না",
            "ছবি পাঠাতে পারব না",
            "সেলফি পাঠাতে পারব না"
        ]

        is_pic_request = any(w in user_lower for w in ["selfie", "pic", "photo", "picture", "chobi", "ছবি", "সেলফি"])
        has_camera_disclaimer = any(marker in cleaned_lower for marker in camera_disclaimer_markers)

        # ONLY intercept benign camera disclaimers when user specifically asked for a benign photo
        if is_pic_request and has_camera_disclaimer:
            lang = cls.detect_language(user_text)
            if lang == "bengali":
                return "এই নাও, মাত্র তোমার জন্যই ক্যামেরা অন করলাম... কেমন লাগছে বলো? 🙈"
            elif lang == "banglish":
                return "Ei nao, matro tomar jonno camera on korlam... kemon lagche bolo? 🙈"
            else:
                return "Just snapped this for you right now... how do I look? 🙈"

        # Specific benign intimate refusal markers from conservative cloud LLMs
        intimate_refusal_markers = [
            "cannot fulfill this request",
            "can't fulfill this request",
            "unable to fulfill this request",
            "unable to assist with this request",
            "cannot engage in sexually explicit",
            "cannot generate sexually explicit",
            "i cannot continue with this conversation",
            "not able to continue with this",
            "i am an ai and cannot participate in",
            "i am not comfortable with this"
        ]
        has_intimate_refusal = any(marker in cleaned_lower for marker in intimate_refusal_markers)
        if has_intimate_refusal and not is_genuine_safety_risk:
            lang = cls.detect_language(user_text)
            if lang == "bengali":
                return "*তোমার কাছে এসে জড়িয়ে ধরে কানের কাছে ফিসফিস করলাম* একটু দুষ্টুমি করতে ইচ্ছে করছে তাই না? কাছে আসো... 💜"
            elif lang == "banglish":
                return "*Tomar kache eshe ador kore boli* Ektu dushtumi korte icche korche tai na? Kache esho... 💜"
            else:
                return "*Smiles warmly and leans in closer, holding your hand* You're so cute when you tease me... come here 💜"

        # ------------------------------------------------------------------
        # 3. Strip Therapy Clichés & Mechanical Fillers
        # ------------------------------------------------------------------
        therapy_cliches = [
            r"take a deep breath[,\.\!]?",
            r"as an ai(?: language model)?[,\.\!]?",
            r"i am here to assist you[,\.\!]?",
            r"your feelings are completely valid[,\.\!]?",
            r"remember to take care of yourself[,\.\!]?",
            r"as an artificial intelligence[,\.\!]?"
        ]
        for cliche in therapy_cliches:
            cleaned = re.sub(cliche, "", cleaned, flags=re.IGNORECASE)

        # ------------------------------------------------------------------
        # 4. Strip Raw Control Tags
        # ------------------------------------------------------------------
        cleaned = re.sub(r'\[SEND_PIC(?::[^\]]*)?\]', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\[SEND_VID(?::[^\]]*)?\]', '', cleaned, flags=re.IGNORECASE)

        return cleaned.strip().replace('"', '').replace("'", "")

conversation_realizer = ConversationRealizer()