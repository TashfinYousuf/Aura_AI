# FILE: backend/app/core/unified_state.py

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime

class UniversalMessage(BaseModel):
    """
    Platform-independent envelope for all incoming messages (Web, PWA, Telegram, WhatsApp).
    """
    platform: str = "web"  # "telegram" | "web" | "whatsapp"
    user_id: str
    message_type: str = "text"  # "text" | "voice" | "image"
    text: Optional[str] = None
    media_url: Optional[str] = None
    media_bytes_base64: Optional[str] = None
    reply_to_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuraState(BaseModel):
    """
    The Single Source of Truth for Aura's internal emotion and contextual state.
    Text, Voice, and Visuals MUST read from this exact state.
    """
    emotion: str = "warm_attuned"
    energy: float = Field(default=0.65, ge=0.0, le=1.0)
    affection: float = Field(default=0.75, ge=0.0, le=1.0)
    humor: float = Field(default=0.50, ge=0.0, le=1.0)
    seriousness: float = Field(default=0.30, ge=0.0, le=1.0)
    curiosity: float = Field(default=0.80, ge=0.0, le=1.0)
    user_emotion: str = "Neutral"
    user_emotion_intensity: float = 0.5
    conversation_mode: str = "comfort"  # "comfort" | "playful_tease" | "intellectual" | "deep_listen"
    relationship_context: str = "close"
    time_context: str = "evening"
    media_probability: float = 0.15


class ResponseDirectorPlan(BaseModel):
    """
    Execution blueprint generated before LLM/Media synthesis.
    """
    text_goal: str
    response_length: str  # "short" (1 line) | "medium" | "deep"
    should_challenge: bool = False
    voice_prosody: Dict[str, Any] = {
        "rate": "-10%",
        "pitch": "-2Hz",
        "style": "warm",
        "pause_weight": 0.5
    }
    visual_intent: Optional[Dict[str, Any]] = None  # None or {"scene": "...", "clothing": "...", "shot": "..."}