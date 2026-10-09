# FILE: backend/app/services/response_planner.py

import json
from groq import Groq
from pydantic import BaseModel
from typing import Optional, Dict, Any

class ExecutionPlan(BaseModel):
    intent: str
    detected_emotion: str
    intensity_score: int
    target_tone: str
    should_challenge: bool
    response_length: str
    trigger_visual: bool
    suggested_scene: Optional[str] = None
    state_shift_empathy: int = 0
    state_shift_energy: int = 0
    new_goal_detected: Optional[str] = None

def plan_aura_response(client: Groq, message: str, past_context: str, memory_context: str) -> ExecutionPlan:
    """
    Subconscious orchestrator that creates a behavioral response contract before LLM generation.
    """
    planner_prompt = f"""You are Aura's internal subconscious and behavioral state planner.
Analyze the user's message and contextual memories to form an execution blueprint.

User Message: "{message}"
Past Memory Notes:
{memory_context}
Recent Context:
{past_context}

CRITICAL RULES:
1. Anti-Yes-Man: If user expresses flawed assumptions, extreme views, or asks for honest feedback, set "should_challenge": true.
2. Visual Intent: If user asks for a picture, selfie, outfit check, or says they miss her face, set "trigger_visual": true and pick one from: "bedroom_desk", "bedroom_bed", "standing_casual", "evening_cafe".
3. Response Length: Set to "short" (1-2 sentences) for casual chat, "medium" for standard banter, "deep" for serious discussions.

Output strictly valid JSON matching this schema:
{{
    "intent": "casual_chat | seeking_comfort | playful_tease | intellectual | visual_request",
    "detected_emotion": "Neutral | Happy | Frustrated | Tired | Playful | Sad",
    "intensity_score": <1-10>,
    "target_tone": "Warm | Sarcastic | Empathetic | Playful | Firm",
    "should_challenge": <true/false>,
    "response_length": "short | medium | deep",
    "trigger_visual": <true/false>,
    "suggested_scene": "bedroom_desk | bedroom_bed | standing_casual | evening_cafe | null",
    "state_shift_empathy": <-5 to +5>,
    "state_shift_energy": <-5 to +5>,
    "new_goal_detected": "string goal or null"
}}"""

    try:
        from app.core.config import settings
        res = client.chat.completions.create(
            model=settings.STRUCTURED_MODEL,
            messages=[{"role": "system", "content": planner_prompt}],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        data = json.loads(res.choices[0].message.content)
        return ExecutionPlan(**data)
    except Exception as e:
        print(f"⚠️ [PLANNER FALLBACK]: {e}")
        return ExecutionPlan(
            intent="casual_chat",
            detected_emotion="Neutral",
            intensity_score=5,
            target_tone="Warm",
            should_challenge=False,
            response_length="medium",
            trigger_visual=False,
            suggested_scene=None
        )