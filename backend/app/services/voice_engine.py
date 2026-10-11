# FILE: backend/app/services/voice_engine.py

import os
import re
import httpx
import base64
import edge_tts
from typing import Tuple, Optional, Dict, Any

# Kokoro/Cartesia Voice IDs
KOKORO_VOICE_EN = "af_heart"  # Warm, intimate young female voice
EDGE_VOICE_BN = "bn-IN-TanishaaNeural"
EDGE_VOICE_EN = "en-US-EmmaNeural"

def generate_speech_performance_script(text: str, mood: str = "WARM", energy: float = 0.6) -> Dict[str, Any]:
    """
    Transforms plain text into a performance script with pauses, pacing, and breath marks.
    """
    # 1. Clean system tags and URLs
    clean = re.sub(r'\[SEND_PIC:.*?\]', '', text, flags=re.IGNORECASE)
    clean = re.sub(r'\[SEND_VID:.*?\]', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'http\S+', '', clean)
    clean = re.sub(r'[^\w\s,.\?!।\'"a-zA-Z0-9\u0980-\u09FF]', '', clean).strip()

    # 2. Performance Marks: Soft ellipses for natural trailing breaths
    clean = re.sub(r'([।\.])\s+', r'... ', clean)
    clean = re.sub(r',\s*', r', ', clean)

    # 3. Dynamic Prosody Mapping based on AuraState Energy & Mood
    if mood in ["SEDUCTIVE", "SAD"] or energy < 0.4:
        speed = 0.88  # Slower, whispery tempo
        rate_str = "-18%"
        pitch_str = "-3Hz"
    elif mood in ["PLAYFUL", "EXCITED"] or energy > 0.75:
        speed = 1.05  # Upbeat, dynamic pace
        rate_str = "-5%"
        pitch_str = "+4Hz"
    else:
        speed = 0.95
        rate_str = "-10%"
        pitch_str = "-1Hz"

    has_bangla = bool(re.search(r'[\u0980-\u09FF]', clean))

    return {
        "script": clean,
        "speed": speed,
        "rate_str": rate_str,
        "pitch_str": pitch_str,
        "is_bangla": has_bangla
    }


async def synthesize_kokoro_voice(script: str, voice: str = KOKORO_VOICE_EN, speed: float = 0.95) -> Optional[bytes]:
    """
    Tier 1: Synthesizes high-fidelity expressive voice via Cloud Kokoro-82M API.
    Provides natural human micro-pauses and vocal texture.
    """
    fal_key = os.getenv("FAL_API_KEY")
    if not fal_key:
        return None

    headers = {
        "Authorization": f"Key {fal_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "input": script,
        "voice": voice,
        "speed": speed
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post("https://fal.run/fal-ai/kokoro", headers=headers, json=payload, timeout=15.0)
            if res.status_code == 200:
                audio_url = res.json().get("audio", {}).get("url")
                if audio_url:
                    audio_res = await client.get(audio_url, timeout=10.0)
                    if audio_res.status_code == 200:
                        print("✨ [VOICE ENGINE] Kokoro-82M High-Fidelity Audio Generated.")
                        return audio_res.content
    except Exception as e:
        print(f"⚠️ [KOKORO ENGINE FALLBACK]: {e}")
    return None


async def synthesize_edge_voice(script: str, voice: str, rate: str, pitch: str) -> Optional[bytes]:
    """
    Tier 2: Ultra-reliable zero-cost Edge-TTS engine with tuned prosody parameters.
    """
    try:
        communicate = edge_tts.Communicate(text=script, voice=voice, rate=rate, pitch=pitch)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        return audio_bytes if audio_bytes else None
    except Exception as e:
        print(f"⚠️ [EDGE-TTS ERROR]: {e}")
        return None


async def synthesize_elevenlabs_voice(
    script: str,
    voice_id: Optional[str] = None,
    stability: float = 0.55,
    similarity_boost: float = 0.85
) -> Optional[bytes]:
    """
    Tier 0: Studio-Grade Emotion & Intimacy Voice via ElevenLabs Multilingual V2.
    Produces astonishingly lifelike human cadence, vocal fry, breathing, and sweetness.
    """
    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    if not eleven_key:
        return None

    vid = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Sarah default
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
    headers = {
        "xi-api-key": eleven_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": script,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": 0.2,
            "use_speaker_boost": True
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code == 200 and res.content:
                print(f"✨ [ELEVENLABS VOICE SUCCESS]: Synthesized studio voice for Aura (Voice ID: {vid})")
                return res.content
            else:
                print(f"ℹ️ [ELEVENLABS NOTICE]: Status {res.status_code}: {res.text[:120]}. Falling back to auxiliary engines.")
    except Exception as e:
        print(f"⚠️ [ELEVENLABS ERROR]: {e}. Falling back to auxiliary engines.")
    return None


async def render_aura_voice(text: str, mood: str = "WARM", energy: float = 0.6) -> Tuple[Optional[str], str]:
    """
    Master Voice Entrypoint:
    Orchestrates performance script -> Selects optimal engine -> Returns (audio_base64, clean_script).
    Hierarchy: ElevenLabs (Tier 0) -> Kokoro-82M (Tier 1) -> Tuned Edge-TTS (Tier 2).
    """
    perf = generate_speech_performance_script(text, mood, energy)
    script = perf["script"]

    if not script:
        return None, ""

    audio_bytes = None

    # Priority 1: Studio-grade ElevenLabs Multilingual V2 (if key configured)
    if os.getenv("ELEVENLABS_API_KEY"):
        audio_bytes = await synthesize_elevenlabs_voice(script)

    # Priority 2: For English conversations, use Kokoro-82M for human-level vocal fry & breathiness
    if not audio_bytes and not perf["is_bangla"]:
        audio_bytes = await synthesize_kokoro_voice(script, voice=KOKORO_VOICE_EN, speed=perf["speed"])

    # Priority 3: For Bengali or when auxiliary engines fail, use tuned Edge-TTS
    if not audio_bytes:
        target_voice = EDGE_VOICE_BN if perf["is_bangla"] else EDGE_VOICE_EN
        audio_bytes = await synthesize_edge_voice(
            script=script,
            voice=target_voice,
            rate=perf["rate_str"],
            pitch=perf["pitch_str"]
        )

    if audio_bytes:
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        return audio_base64, script

    return None, script