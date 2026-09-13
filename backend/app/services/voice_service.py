import os
import re
import base64
import edge_tts

from openai import OpenAI
from fastapi import UploadFile

def transcribe_audio(audio_file: UploadFile) -> str:
    """অডিও ফাইল রিসিভ করে টেক্সটে কনভার্ট করবে"""
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    
    # অডিও ফাইলটি সাময়িকভাবে সেভ করার জন্য
    temp_file_path = f"temp_{audio_file.filename}"
    
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(audio_file.file.read())
            
        with open(temp_file_path, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio
            )
        return transcript.text
    
    finally:
        # কাজ শেষ হলে টেম্পোরারি ফাইলটি ডিলিট করে দেওয়া (স্টোরেজ বাঁচানোর জন্য)
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


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