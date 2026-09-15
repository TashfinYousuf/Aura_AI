# FILE: backend/app/services/state_engine.py

import json
from datetime import datetime
from groq import Groq
import os
from typing import Dict, Any
from app.core.unified_state import AuraState, ResponseDirectorPlan

def determine_time_context() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 22:
        return "evening"
    else:
        return "late_night"


async def evaluate_interaction_state(user_text: str, past_mood: str = "WARM") -> AuraState:
    """
    Analyzes the incoming message and generates a unified AuraState.
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    time_ctx = determine_time_context()

    prompt = f"""Analyze the user's message and determine the optimal emotional state for Aura (a 22yo loving, playful companion).
User message: "{user_text}"
Current time: {time_ctx}
Past state: {past_mood}

Output ONLY valid JSON matching this schema:
{{
  "emotion": "warm_playful" | "comforting_soft" | "intellectual_sharp" | "intimate_seductive",
  "energy": 0.1 to 1.0,
  "affection": 0.1 to 1.0,
  "humor": 0.1 to 1.0,
  "conversation_mode": "comfort" | "playful_tease" | "intellectual" | "casual_banter",
  "user_emotion": "stressed" | "happy" | "tired" | "curious" | "neutral",
  "media_probability": 0.1 to 0.9
}}"""

    try:
        res = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content)
        return AuraState(
            emotion=data.get("emotion", "warm_playful"),
            energy=float(data.get("energy", 0.65)),
            affection=float(data.get("affection", 0.75)),
            humor=float(data.get("humor", 0.50)),
            conversation_mode=data.get("conversation_mode", "casual_banter"),
            user_emotion=data.get("user_emotion", "neutral"),
            time_context=time_ctx,
            media_probability=float(data.get("media_probability", 0.15))
        )
    except Exception as e:
        print(f"⚠️ [STATE ENGINE FALLBACK]: {e}")
        return AuraState(time_context=time_ctx)


def create_response_director_plan(state: AuraState, user_text: str) -> ResponseDirectorPlan:
    """
    Translates the unified AuraState into concrete directives for Text, Voice, and Visuals.
    """
    # 1. Voice Directives based on State
    if state.energy < 0.4 or state.emotion == "comforting_soft":
        voice_prosody = {"rate": "-15%", "pitch": "-3Hz", "style": "whisper"}
    elif state.energy > 0.75 or state.emotion == "warm_playful":
        voice_prosody = {"rate": "-5%", "pitch": "+3Hz", "style": "cheerful"}
    else:
        voice_prosody = {"rate": "-10%", "pitch": "-1Hz", "style": "natural"}

    # 2. Text Directives based on State
    if state.user_emotion in ["stressed", "tired"]:
        text_goal = "Be brief, deeply comforting, zero lectures or generic advice. Offer soothing presence."
        length = "short"
    elif state.conversation_mode == "playful_tease":
        text_goal = "Tease affectionately, bantering like a close girlfriend."
        length = "short"
    else:
        text_goal = "Engage with curiosity and warmth."
        length = "medium"

    return ResponseDirectorPlan(
        text_goal=text_goal,
        response_length=length,
        should_challenge=(state.humor > 0.6),
        voice_prosody=voice_prosody
    )