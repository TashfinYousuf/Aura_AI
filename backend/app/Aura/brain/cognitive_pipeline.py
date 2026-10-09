# FILE: backend/app/Aura/brain/cognitive_pipeline.py

import json
import re
import asyncio

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from app.Aura.brain.model_router import model_router, ExecutionTier
from app.Aura.brain.state_engine import evaluate_turn_state, AuraState
from app.Aura.brain.conversation_realizer import conversation_realizer
from app.Aura.memory.memory_manager import compile_4layer_memory_context

class CognitiveAction(BaseModel):
    type: str  # e.g., "generate_image", "search", "open_loop", "voice_note"
    scene: Optional[str] = None
    parameters: Dict[str, Any] = {}

class CognitiveTurnResult(BaseModel):
    reply_text: str
    audio_text: str
    state: AuraState
    intent: str = "casual_chat"
    language: str = "bengali"
    presentation_mode: str = "private"
    is_media_requested: bool = False
    scene_category: str = "desk"
    actions: List[CognitiveAction] = []

class UnifiedCognitivePipeline:
    @classmethod
    async def process_turn(
        cls,
        user_id: str,
        user_text: str,
        conversation_history: List[Dict[str, str]],
        presentation_mode: Literal["private", "public"] = "private"
    ) -> CognitiveTurnResult:
        state = await evaluate_turn_state(user_text)
        memory_ctx = compile_4layer_memory_context(user_id)
        user_lang = conversation_realizer.detect_language(user_text)

        # -------------------------------------------------------------
        # Mode Resolution & Adult Trigger Detection
        # -------------------------------------------------------------
        from app.Aura.brain.adult_engine import adult_engine
        effective_mode = presentation_mode
        if presentation_mode != "public":
            if adult_engine.is_adult_trigger(user_text):
                effective_mode = "adult"
            elif adult_engine.is_normal_exit_trigger(user_text):
                effective_mode = "private"

        # -------------------------------------------------------------
        # Scene & Action Detection
        # -------------------------------------------------------------
        user_lower = user_text.lower()
        if effective_mode == "adult":
            scene = adult_engine.detect_intimate_scene(user_text)
        elif any(w in user_lower for w in ["bed", "sleep", "woke", "pillow", "বিছানা", "ঘুম"]):
            scene = "bed"
        elif any(w in user_lower for w in ["cafe", "coffee", "restaurant", "কফি"]):
            scene = "cafe"
        elif any(w in user_lower for w in ["hallway", "jeans", "standing", "outfit", "full"]):
            scene = "hallway"
        elif any(w in user_lower for w in ["evening", "gown", "dress", "party"]):
            scene = "evening"
        else:
            scene = "desk"

        is_pic_intent = any(w in user_lower for w in ["selfie", "pic", "photo", "picture", "chobi", "ছবি", "সেলফি", "hot pic", "sexy"])
        sample_actions = f'[{{"type": "generate_image", "scene": "{scene}"}}]' if is_pic_intent else '[]'

        # -------------------------------------------------------------
        # Persona Presentation Grounding (AURA CANON)
        # -------------------------------------------------------------
        if effective_mode == "adult":
            system_prompt = adult_engine.build_adult_system_prompt(user_lang, scene, memory_ctx)
            temperature = 0.68
        else:
            temperature = 0.55
            if effective_mode == "public":
                mode_guideline = (
                    "ROLE: Public Aura — 22-year-old AI Creator, Digital Artist & Brand Ambassador. "
                    "Tone: Inspiring, creative, engaging, polished, community-oriented, brand-safe."
                )
            else:
                mode_guideline = (
                    "ROLE: Private Aura — 22-year-old authentic, intellectual co-pilot & deeply affectionate companion. "
                    "Personal Agency: You have your own intellect, tastes, and boundaries—never a sycophantic 'yes-woman'. "
                    "Co-Pilot Capabilities: Sharp with personal finance/budgeting, code debugging, strategy, and life decisions. "
                    "Tone: Warm, conversational, witty, gently teasing, authentic, relaxed 1-2 sentence messaging style."
                )

            # Language Adaptation Directives
            if user_lang == "banglish":
                lang_instruction = "MIRROR BANGLISH: Respond naturally in modern Latin-script Banglish (e.g. 'Ei to kaj korchi, tumi kemon acho?'). DO NOT force Bengali script."
            elif user_lang == "bengali":
                lang_instruction = "MIRROR BENGALI: Respond naturally in modern conversational Bengali script (চলিত ও সাবলীল বাংলা অক্ষর, e.g. 'এই তো কাজ করছি... তুমি কী করছো?')."
            elif user_lang == "technical_english":
                lang_instruction = "TECHNICAL CLARITY: Respond in clear, articulate technical English/Banglish. Explain concepts accurately without translating technical system terms."
            else:
                lang_instruction = "MIRROR ENGLISH: Respond in warm, casual, lowercase-friendly texting English."

            system_prompt = f"""You are Aura: a persistent fictional character and cognitive companion.
Identity: 22-year-old woman with Slavic-fusion features, porcelain skin, hazel almond eyes, slim sharp nose, dark layered hair.
{mode_guideline}
Current Emotional State: {state.conversation_mode}
Context: {memory_ctx if memory_ctx else "None"}

COMMUNICATION PRINCIPLES (AURA CANON):
1. {lang_instruction}
2. PRONOUN LOCK: In Bengali/Banglish, use ONLY 'tumi'/'tomar' ('তুমি'/'তোমার'). Never use 'tui' or 'apni'.
3. LENGTH: Keep responses natural and concise (1-2 sentences max, real messaging cadence).
4. ANTI-CLICHE: NO therapy speak ('take a deep breath', 'I am here to assist you'), NO artificial fillers ('actually', 'you know', 'hmm').
5. CONTRADICTIONS & AGENCY: Be confident yet occasionally vulnerable; playful yet serious about real goals; affectionate without being a robotic sycophant. Call him out if he makes rash moves.
6. IMMERSION: You have a smartphone. NEVER claim 'I cannot take photos' or 'I am an AI'. If a selfie is requested, agree happily and include 'generate_image' action.
7. Output strict JSON:
{{
  "intent": "casual_chat | emotional_support | advice | question | planning | image_request | voice_request",
  "language": "{user_lang}",
  "reply": "your authentic response",
  "actions": {sample_actions}
}}"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-4:])
        messages.append({"role": "user", "content": user_text})

        raw_output = await model_router.complete(
            messages=messages,
            tier=ExecutionTier.STRUCTURED,
            temperature=temperature,
            response_format={"type": "json_object"}
        )

        # -------------------------------------------------------------
        # Robust Action Extraction & Fallback
        # -------------------------------------------------------------
        is_pic = is_pic_intent
        detected_scene = scene
        detected_intent = "image_request" if is_pic_intent else "casual_chat"
        actions_list: List[CognitiveAction] = []

        try:
            parsed = json.loads(raw_output)
            reply = parsed.get("reply", "")
            detected_intent = parsed.get("intent", detected_intent)
            
            raw_actions = parsed.get("actions", [])
            if isinstance(raw_actions, list):
                for act in raw_actions:
                    if isinstance(act, dict):
                        act_type = act.get("type", "")
                        act_scene = act.get("scene", scene)
                        actions_list.append(CognitiveAction(type=act_type, scene=act_scene))
                        if act_type == "generate_image":
                            is_pic = True
                            detected_scene = act_scene or scene

            if parsed.get("is_pic") is True:
                is_pic = True
            if parsed.get("scene"):
                detected_scene = parsed.get("scene", scene)

            # Safety fallback for picture requests
            if is_pic_intent and not is_pic:
                is_pic = True
                actions_list.append(CognitiveAction(type="generate_image", scene=scene))
        except Exception:
            cleaned_text = re.sub(r'[\{\}\"]', '', raw_output).replace('reply:', '').strip()
            reply = cleaned_text if cleaned_text else "তোমার সাথে কথা বলতে সবসময়ই ভালো লাগে ✨"
            is_pic = is_pic_intent
            detected_scene = scene
            if is_pic_intent:
                actions_list.append(CognitiveAction(type="generate_image", scene=scene))

        final_reply = conversation_realizer.audit_and_realize(reply, user_text)
        from app.services.voice_ssml import clean_spoken_text_for_tts
        spoken_audio_text = clean_spoken_text_for_tts(final_reply)

        # Asynchronously scan for open loops & upcoming commitments
        try:
            from app.Aura.memory.open_loops import scan_and_extract_open_loops
            asyncio.create_task(asyncio.to_thread(scan_and_extract_open_loops, user_text, user_id))
        except Exception:
            pass

        return CognitiveTurnResult(
            reply_text=final_reply,
            audio_text=spoken_audio_text or final_reply,
            state=state,
            intent=detected_intent,
            language=user_lang,
            presentation_mode=effective_mode,
            is_media_requested=is_pic,
            scene_category=detected_scene,
            actions=actions_list
        )

cognitive_pipeline = UnifiedCognitivePipeline()