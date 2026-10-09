# FILE: backend/app/Aura/brain/state_engine.py

import os
import json
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from groq import Groq
from app.core.config import settings

def get_active_groq_model(client: Optional[Groq] = None) -> str:
    return settings.PRIMARY_CHAT_MODEL

def determine_time_context() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 22:
        return "evening"
    return "late_night"

class AuraState(BaseModel):
    emotion: str = "warm_playful"
    energy: float = 0.65
    affection: float = 0.75
    humor: float = 0.50
    conversation_mode: str = "casual_banter"
    user_emotion: str = "neutral"
    time_context: str = "daytime"
    media_probability: float = 0.15

    # Safe attribute access - fixes F9 infinite recursion bug permanently
    def __getattr__(self, name: str) -> Any:
        if name in ("mode", "mood"):
            return self.__dict__.get("conversation_mode", "casual_banter")
        if name == "energy_level":
            return self.__dict__.get("energy", 0.65)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

AuraCognitiveState = AuraState
AuraInternalState = AuraState

class ResponseDirectorPlan(BaseModel):
    text_goal: str = "Engage with warmth, wit, and authentic presence."
    response_length: str = "short"
    should_challenge: bool = False
    voice_prosody: Dict[str, str] = Field(default_factory=lambda: {"rate": "-8%", "pitch": "-2Hz", "style": "natural"})

async def evaluate_turn_state(user_text: str, past_mood: str = "WARM", **kwargs) -> AuraState:
    time_ctx = determine_time_context()
    if not settings.GROQ_API_KEY:
        return AuraState(time_context=time_ctx)

    client = Groq(api_key=settings.GROQ_API_KEY)
    prompt = f"""Analyze the user's message for Aura (22yo authentic female partner).
User text: "{user_text}"
Time: {time_ctx}

Output ONLY valid JSON:
{{
  "emotion": "warm_playful" | "comforting_soft" | "intellectual_sharp" | "intimate_seductive",
  "energy": 0.65,
  "affection": 0.75,
  "humor": 0.50,
  "conversation_mode": "comfort" | "playful_tease" | "intellectual" | "casual_banter",
  "user_emotion": "stressed" | "happy" | "tired" | "curious" | "neutral",
  "media_probability": 0.15
}}"""

    for model_name in [settings.STRUCTURED_MODEL] + settings.FALLBACK_CHAT_MODELS:
        try:
            res = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.2,
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
        except Exception:
            continue

    return AuraState(time_context=time_ctx)

def create_response_director_plan(state: AuraState, user_text: str = "") -> ResponseDirectorPlan:
    energy = getattr(state, "energy", 0.65)
    emotion = getattr(state, "emotion", "warm_playful")
    c_mode = getattr(state, "conversation_mode", "casual_banter")
    u_emotion = getattr(state, "user_emotion", "neutral")
    humor = getattr(state, "humor", 0.5)

    if energy < 0.4 or emotion == "comforting_soft":
        voice_prosody = {"rate": "-15%", "pitch": "-3Hz", "style": "whisper"}
    elif energy > 0.75 or emotion == "warm_playful":
        voice_prosody = {"rate": "-5%", "pitch": "+3Hz", "style": "cheerful"}
    else:
        voice_prosody = {"rate": "-8%", "pitch": "-1Hz", "style": "natural"}

    if u_emotion in ["stressed", "tired"]:
        text_goal = "Be calm, supportive, and grounded. Zero lectures."
        length = "short"
    elif c_mode == "playful_tease":
        text_goal = "Tease affectionately like a real partner."
        length = "short"
    else:
        text_goal = "Engage with curiosity and warmth."
        length = "medium"

    return ResponseDirectorPlan(
        text_goal=text_goal,
        response_length=length,
        should_challenge=(humor > 0.6),
        voice_prosody=voice_prosody
    )

evaluate_interaction_state = evaluate_turn_state
evaluate_cognitive_state = evaluate_turn_state