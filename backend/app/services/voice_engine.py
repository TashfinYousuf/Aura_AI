# FILE: backend/app/services/voice_engine.py

import os
import re
import httpx
import base64
import edge_tts
from typing import Tuple, Optional, Dict, Any

import hashlib
from collections import OrderedDict

# Kokoro/Cartesia Voice IDs
KOKORO_VOICE_EN = "af_heart"  # Warm, intimate young female voice
EDGE_VOICE_BN = "bn-IN-TanishaaNeural"
EDGE_VOICE_EN = "en-US-EmmaNeural"

# High-Performance In-Memory Audio Cache (prevents duplicate API queries & saves credits)
_AUDIO_CACHE: OrderedDict[str, bytes] = OrderedDict()
_CACHE_MAX_SIZE = 128

def _get_cached_audio(cache_key: str) -> Optional[bytes]:
    if cache_key in _AUDIO_CACHE:
        _AUDIO_CACHE.move_to_end(cache_key)
        return _AUDIO_CACHE[cache_key]
    return None

def _put_cached_audio(cache_key: str, data: bytes):
    if len(_AUDIO_CACHE) >= _CACHE_MAX_SIZE:
        _AUDIO_CACHE.popitem(last=False)
    _AUDIO_CACHE[cache_key] = data

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
        el_stability = 0.52
        el_style = 0.18
        el_speed = 0.92
    elif mood in ["PLAYFUL", "EXCITED"] or energy > 0.75:
        speed = 1.05  # Upbeat, dynamic pace
        rate_str = "-5%"
        pitch_str = "+4Hz"
        el_stability = 0.44
        el_style = 0.12
        el_speed = 1.00
    else:
        # Blueprint Default: Sweet, calm, natural conversational warmth
        speed = 0.95
        rate_str = "-10%"
        pitch_str = "-1Hz"
        el_stability = 0.48
        el_style = 0.15
        el_speed = 0.96

    has_bangla = bool(re.search(r'[\u0980-\u09FF]', clean))

    return {
        "script": clean,
        "speed": speed,
        "rate_str": rate_str,
        "pitch_str": pitch_str,
        "el_stability": el_stability,
        "el_style": el_style,
        "el_speed": el_speed,
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

    cache_key = hashlib.sha256(f"kokoro_{script}_{voice}_{speed}".encode()).hexdigest()
    cached = _get_cached_audio(cache_key)
    if cached:
        return cached

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
                        _put_cached_audio(cache_key, audio_res.content)
                        return audio_res.content
    except Exception as e:
        print(f"⚠️ [KOKORO ENGINE FALLBACK]: {e}")
    return None


async def synthesize_edge_voice(script: str, voice: str, rate: str, pitch: str) -> Optional[bytes]:
    """
    Tier 2: Ultra-reliable zero-cost Edge-TTS engine with tuned prosody parameters.
    """
    cache_key = hashlib.sha256(f"edge_{script}_{voice}_{rate}_{pitch}".encode()).hexdigest()
    cached = _get_cached_audio(cache_key)
    if cached:
        return cached

    try:
        communicate = edge_tts.Communicate(text=script, voice=voice, rate=rate, pitch=pitch)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        if audio_bytes:
            _put_cached_audio(cache_key, audio_bytes)
            return audio_bytes
    except Exception as e:
        print(f"⚠️ [EDGE-TTS ERROR]: {e}")
    return None


async def synthesize_elevenlabs_voice(
    script: str,
    voice_id: Optional[str] = None,
    stability: float = 0.48,
    similarity_boost: float = 0.75,
    style: float = 0.15,
    speed: float = 0.96
) -> Optional[bytes]:
    """
    Tier 0: Studio-Grade Emotion & Intimacy Voice via ElevenLabs Multilingual V2.
    Produces astonishingly lifelike human cadence, vocal fry, breathing, and sweetness.
    Tuned with exact parameters: stability=0.48, similarity_boost=0.75, style=0.15, speed=0.96.
    """
    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    if not eleven_key:
        return None

    vid = voice_id or os.getenv("ELEVENLABS_VOICE_ID", "gJU2icYQsdEmbGJ65Z8W")  # Aura's custom sweet voice
    cache_key = hashlib.sha256(f"eleven_{script}_{vid}_{stability}_{similarity_boost}_{style}_{speed}".encode()).hexdigest()
    cached = _get_cached_audio(cache_key)
    if cached:
        print(f"⚡ [ELEVENLABS CACHE HIT]: Serving instant cached audio for '{script[:30]}...'")
        return cached

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
            "style": style,
            "speed": speed,
            "use_speaker_boost": True
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code == 200 and res.content:
                print(f"✨ [ELEVENLABS VOICE SUCCESS]: Synthesized studio voice for Aura (Voice ID: {vid})")
                _put_cached_audio(cache_key, res.content)
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
        audio_bytes = await synthesize_elevenlabs_voice(
            script=script,
            stability=perf.get("el_stability", 0.48),
            similarity_boost=0.75,
            style=perf.get("el_style", 0.15),
            speed=perf.get("el_speed", 0.96)
        )

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