# FILE: backend/app/services/voice_ssml.py

import re
import html
import base64
import edge_tts
from typing import Optional, Tuple, Dict

# ==============================================================================
# CANONICAL NEURAL VOICES CONFIGURATION (ONE VOICE)
# ==============================================================================

VOICE_CONFIG = {
    "BN": {
        "voice": "bn-IN-TanishaaNeural",  # Canonical Tanishaa: Native, authentic Bengali pronunciation
        "base_rate": "-6%",
        "base_pitch": "-2Hz"
    },
    "EN": {
        "voice": "en-US-EmmaNeural",     # Canonical English: Warm, conversational young female
        "base_rate": "-5%",
        "base_pitch": "+0Hz"
    }
}

# Common Banglish phonetic transliteration map for natural voice pronunciation
BANGLISH_TO_BANGLA_MAP: Dict[str, str] = {
    "ki": "কী",
    "kemon": "কেমন",
    "acho": "আছো",
    "achi": "আছি",
    "korcho": "করছো",
    "korbo": "করবো",
    "koro": "করো",
    "amr": "আমার",
    "amar": "আমার",
    "tmr": "তোমার",
    "tomar": "তোমার",
    "tumi": "তুমি",
    "ami": "আমি",
    "valo": "ভালো",
    "bhalo": "ভালো",
    "hobe": "হবে",
    "mon": "মন",
    "kharap": "খারাপ",
    "onek": "অনেক",
    "khub": "খুব",
    "kotha": "কথা",
    "bolo": "বলো",
    "bol": "বলো",
    "shona": "সোনা",
    "babu": "বাবু",
    "ghum": "ঘুম",
    "kaj": "কাজ",
    "kalke": "কালকে",
    "ajke": "আজকে",
    "ekhon": "এখন",
    "pore": "পরে",
    "dekha": "দেখা",
    "chobi": "ছবি",
    "pic": "ছবি",
    "selfie": "সেলফি",
    "shuncho": "শুনছো",
    "shuno": "শোনো",
    "jani": "জানি",
    "ha": "হ্যাঁ",
    "na": "না",
    "tai": "তাই",
    "kintu": "কিন্তু",
    "keno": "কেন",
    "kotodin": "কতদিন",
    "sathe": "সাথে",
    "miss": "মিস",
    "korchi": "করছি"
}

def clean_spoken_text_for_tts(text: str) -> str:
    """
    Cleans raw conversational reply into pure, natural spoken text for TTS:
    1. Completely strips all emojis and pictographs (prevents TTS reading 'sparkles', 'monkey').
    2. Replaces Bengali dari (।) with a clean period (.) so TTS pauses naturally without pronouncing 'dari'.
    3. Eliminates multiple periods (...) and (..) which make TTS say 'dot dot dot'.
    4. Strips markdown asterisks (*giggles*, *smiles*), brackets, quotes, and control tags.
    5. Converts Banglish phonetic words to Bengali script when needed so Tanishaa pronounces natively.
    """
    if not text:
        return ""

    # 1. Remove control tags and URLs
    clean = re.sub(r'\[SEND_PIC(?::.*?)?\]', '', text, flags=re.IGNORECASE)
    clean = re.sub(r'\[SEND_VID(?::.*?)?\]', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\[Photo Sent(?::.*?)?\]', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'\[Voice Message\]', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'https?://\S+|www\.\S+', '', clean)
    clean = re.sub(r'```.*?```', '', clean, flags=re.DOTALL)
    clean = re.sub(r'`[^`]*`', '', clean)

    # 2. Strip asterisks, roleplay actions (*smiles*, *sighs*) and markdown symbols
    clean = re.sub(r'\*[^*]+\*', '', clean)
    clean = re.sub(r'[*_#~\[\]()<>{}|\\]+', '', clean)

    # 3. Strip ALL Unicode Emojis & Pictographs
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U00002600-\U000026FF"  # Misc symbols (sun, coffee, etc.)
        "\U0000200D"              # Zero width joiner
        "\U0000FE0F"              # Variation Selector-16
        "\U000020E3"              # Keycap
        "]+", flags=re.UNICODE
    )
    clean = emoji_pattern.sub('', clean)

    # 4. Handle Bengali Dari (।) and punctuation without literal reading
    # Replace Bengali dari (।) with standard period (.) so EdgeTTS pauses naturally
    clean = clean.replace('।', '. ')

    # Remove repeated periods / ellipses (..., ..) that make TTS say 'dot dot dot'
    clean = re.sub(r'\.{2,}', '. ', clean)

    # Remove duplicated commas, question marks, exclamation marks
    clean = re.sub(r',+', ',', clean)
    clean = re.sub(r'\?+', '?', clean)
    clean = re.sub(r'!+', '!', clean)

    # Remove quotes and ticks
    clean = re.sub(r'[\'\"`^~]', '', clean)

    # 5. Banglish to Bengali Script Conversion for Audio Synthesis
    # If text is primarily Latin characters but contains Banglish words, convert to Bengali script
    has_bengali_chars = bool(re.search(r'[\u0980-\u09FF]', clean))
    if not has_bengali_chars:
        words = clean.split()
        converted_words = []
        banglish_count = 0
        for w in words:
            clean_word = re.sub(r'[^\w]', '', w.lower())
            if clean_word in BANGLISH_TO_BANGLA_MAP:
                banglish_count += 1
                # Preserve trailing punctuation
                punct = "".join([c for c in w if c in ".,!?"])
                converted_words.append(BANGLISH_TO_BANGLA_MAP[clean_word] + punct)
            else:
                converted_words.append(w)
        
        # If at least 2 Banglish markers were found, use the converted text for audio
        if banglish_count >= 1:
            clean = " ".join(converted_words)

    # 6. Normalize whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def detect_voice_parameters(spoken_text: str, mood: str = "WARM") -> Tuple[str, str, str]:
    """
    Selects the canonical neural voice and sets prosody:
    - Bengali text (or converted Banglish): bn-IN-TanishaaNeural (Tanisha bn)
    - English text: en-US-EmmaNeural
    """
    has_bangla = bool(re.search(r'[\u0980-\u09FF]', spoken_text))
    cfg = VOICE_CONFIG["BN"] if has_bangla else VOICE_CONFIG["EN"]

    rate = cfg["base_rate"]
    pitch = cfg["base_pitch"]

    mood_upper = mood.upper()
    if "COMFORT" in mood_upper or "LISTENING" in mood_upper:
        rate = "-12%"
        pitch = "-3Hz"
    elif "PLAYFUL" in mood_upper or "TEASE" in mood_upper:
        rate = "-4%"
        pitch = "+1Hz"
    elif "INTELLECTUAL" in mood_upper:
        rate = "-6%"
        pitch = "+0Hz"

    return cfg["voice"], rate, pitch


async def render_neural_voice(text: str, mood: str = "WARM") -> Tuple[Optional[str], str]:
    """
    Master Performance Voice Synthesizer:
    1. Cleans input text completely (strips emojis, dari/comma artifacts, 'dot dot dot').
    2. Routes Bengali & Banglish to Tanishaa (bn-IN-TanishaaNeural).
    3. Routes English to Emma (en-US-EmmaNeural).
    4. Generates streaming Edge-TTS audio and returns Base64 audio + clean spoken text.
    """
    if not text:
        return None, ""

    spoken_clean = clean_spoken_text_for_tts(text)
    if not spoken_clean:
        return None, ""

    voice, rate, pitch = detect_voice_parameters(spoken_clean, mood)

    try:
        communicate = edge_tts.Communicate(
            text=spoken_clean,
            voice=voice,
            rate=rate,
            pitch=pitch
        )
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]

        if audio_bytes:
            return base64.b64encode(audio_bytes).decode("utf-8"), spoken_clean
    except Exception as e:
        print(f"⚠️ [PERFORMANCE VOICE ERROR]: {e}")

    return None, spoken_clean