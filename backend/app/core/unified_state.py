# FILE: backend/app/core/unified_state.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.Aura.brain.state_engine import AuraState

class UniversalMessage(BaseModel):
    platform: str = "web"
    user_id: str
    text: Optional[str] = ""
    message_type: str = "text"
    image_base64: Optional[str] = None
    audio_base64: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None

    # Safe Dynamic Getters (Never throws AttributeError)
    def __getattr__(self, name: str) -> Any:
        if name in ["mode", "mood"]:
            return self.conversation_mode
        if name == "energy_level":
            return self.energy
        return "casual_banter"

# Full compatibility alias
AuraCognitiveState = AuraState
AuraInternalState = AuraState

class ResponseDirectorPlan(BaseModel):
    text_goal: str = "Engage with warmth and curiosity."
    response_length: str = "short"
    should_challenge: bool = False
    voice_prosody: Dict[str, str] = Field(default_factory=lambda: {"rate": "-8%", "pitch": "-2Hz", "style": "natural"})