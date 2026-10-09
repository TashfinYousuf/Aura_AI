import os
import re
import base64
import edge_tts
import tempfile
import asyncio

from openai import OpenAI
from fastapi import UploadFile

from typing import Optional
from fastapi import UploadFile
from groq import Groq
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY) if settings.GROQ_API_KEY else None

async def transcribe_audio_file(audio_file: UploadFile) -> Optional[str]:
    """
    Bug F13 Fixed:
    Asynchronously reads uploaded audio payload without blocking FastAPI's main event loop.
    Routes STT strictly through Whisper Large v3 Turbo.
    """
    if not settings.GROQ_API_KEY:
        print("⚠️ [VOICE SERVICE] GROQ_API_KEY not configured!")
        return None

    try:
        # ✅ FIX F13: Non-blocking async file read (replaces blocking audio_file.file.read())
        audio_bytes = await audio_file.read()
        
        if not audio_bytes:
            return None

        # Determine safe suffix
        filename = audio_file.filename or "audio.webm"
        suffix = os.path.splitext(filename)[1] or ".webm"

        # Create temporary file for Groq Whisper
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        def _transcribe_sync(filepath: str) -> str:
            with open(filepath, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    model="whisper-large-v3-turbo",
                    file=f
                )
                return transcription.text.strip()

        # Run transcription in a non-blocking background thread pool
        transcription_text = await asyncio.to_thread(_transcribe_sync, temp_path)

        # Cleanup temp file from disk
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return transcription_text

    except Exception as e:
        print(f"⚠️ [VOICE TRANSCRIPTION ERROR]: {e}")
        return None


def clean_text_for_tts(text: str) -> str:
    """
    Strips system tags, markdown links, URLs, and emojis for smooth prosody.
    """
    text = re.sub(r'\[SEND_PIC:.*?\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[SEND_VID:.*?\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'http\S+', '', text)
    cleaned = re.sub(r'[^\w\s,.\?!।\'"a-zA-Z0-9\u0980-\u09FF]', '', text).strip()
    return cleaned

async def generate_speech_base64(text: str, lang: str = "BN", mood: str = "NEUTRAL") -> str:
    """
    Generates human-like TTS audio using edge-tts with prosody control.
    """
    cleaned = clean_text_for_tts(text)
    if not cleaned:
        return ""

    voice = "en-US-EmmaNeural" if lang == "EN" else "bn-IN-TanishaaNeural"
    rate = "-15%"
    pitch = "-2Hz"

    if "SEDUCTIVE" in mood or "SAD" in mood:
        rate, pitch = "-20%", "+0Hz"
    elif "PLAYFUL" in mood:
        rate, pitch = "-5%", "+5Hz"

    communicate = edge_tts.Communicate(text=cleaned, voice=voice, rate=rate, pitch=pitch)
    
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]

    return base64.b64encode(audio_data).decode("utf-8")