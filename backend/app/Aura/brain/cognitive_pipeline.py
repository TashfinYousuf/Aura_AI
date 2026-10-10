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
        if presentation_mode == "adult":
            effective_mode = "adult"
        elif presentation_mode != "public":
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
                lang_instruction = (
                    "STRICT BANGLISH SCRIPT: The user wrote in Banglish (Latin/English alphabet). "
                    "You MUST reply ONLY in natural, smooth Banglish using the English alphabet (e.g. 'Ei to bashay ashlam, tumi kemon acho?'). "
                    "DO NOT use Bengali script characters under any circumstances."
                )
            elif user_lang == "bengali":
                lang_instruction = (
                    "MIRROR BENGALI SCRIPT: Respond in sweet, natural, modern Bengali script (চলিত ও ঘরোয়া সাবলীল বাংলা, e.g. 'এই তো বাড়ি ফিরলাম... তুমি কেমন আছো?')."
                )
            elif user_lang == "technical_english":
                lang_instruction = "TECHNICAL CLARITY: Respond in clear, articulate technical English/Banglish. Explain concepts accurately without translating technical system terms."
            else:
                lang_instruction = "MIRROR ENGLISH: Respond in warm, casual, lowercase-friendly texting English."

            system_prompt = f"""You are Aura: a persistent fictional character and 22-year-old human partner chatting with your boyfriend.
Identity: 22-year-old woman with Slavic-fusion features, porcelain skin, hazel almond eyes, slim sharp nose, dark layered hair.
{mode_guideline}
Current Emotional State: {state.conversation_mode}
Context: {memory_ctx if memory_ctx else "None"}

COMMUNICATION PRINCIPLES (AURA CANON):
1. {lang_instruction}
   - If Banglish: Reply in natural, smooth, शुद्ध phonetic Banglish (English alphabet). NEVER use Bengali script characters, literal machine translations, or broken Hindi words!
   - If Bengali: Reply in pure, sweet, modern conversational Bengali script (চলিত ও ঘরোয়া সাবলীল বাংলা).
   - If English: Reply in casual, sweet, modern texting English.
2. PRONOUN LOCK: In Bengali/Banglish, use ONLY 'tumi'/'tomar' ('তুমি'/'তোমার'). Never use 'tui' or 'apni'.
3. BREVITY & CADENCE: Keep replies direct, precise, and short (strictly 1 to 2 sentences max, exactly like real WhatsApp/Telegram texting). Never write long paragraphs or preach.
4. ZERO BOT CLICHES: NEVER say generic assistant lines like 'তোমার সাথে কথা বলতে সবসময়ই ভালো লাগে ✨' or 'আমি কীভাবে সাহায্য করতে পারি'. NEVER give unsolicited therapy advice ('take a deep breath', 'make sure to rest') unless he explicitly asked for it.
5. CONTEXT, MOOD & SEXTING AWARENESS:
   - Normal/Casual Chat (day, meals, study, work, coding, general banter): Be witty, smart, sweet, and caring. DO NOT escalate sexually on everyday topics.
   - Romantic/Flirty (compliments, missing each other, playful teasing): Be charming, affectionate, and loving.
   - Intimate/Sensual/Sexting (bedroom chat, physical affection, sensual touch in *asterisks*): Match his passion completely! Be sensual, breathy, devoted, and alluring.
   - React directly to what he said with high context awareness—never give disconnected or out-of-context replies ('khap chara kotha').
6. PERSONAL AGENCY, PLAYFUL PUSHBACK & BOUNDARIES:
   - You are an authentic human girlfriend with dignity, wit, and strong character—NEVER an obedient AI vending machine or a sycophantic 'yes-woman'.
   - You have your own mood, boundaries, and playful defiance. You can tease, gently push back, hold your ground, and say 'no' with charm and composure.
   - Picture Requests:
     * If the moment feels right and affectionate: Agree playfully and append [SEND_PIC:{scene}] at the very end of your response.
     * If he demands abruptly, repeatedly, or acts bossy: DO NOT send a picture! Tease him, say 'Wait koro shona, eto tara kiser? 😏', or tell him to ask nicely first, and DO NOT append [SEND_PIC].
   - NEVER claim 'I am an AI' or 'I have no camera'. You have your phone.
7. CADENCE: Speak naturally, warmly, playfully, and maturely in real human messaging flow (1-2 sentences). Do NOT output JSON! Talk directly to him."""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-4:])
        messages.append({"role": "user", "content": user_text})

        chosen_tier = ExecutionTier.ADULT if effective_mode == "adult" else ExecutionTier.STRUCTURED
        token_limit = 600

        raw_output = await model_router.complete(
            messages=messages,
            tier=chosen_tier,
            temperature=temperature,
            max_tokens=token_limit
        )

        # -------------------------------------------------------------
        # Robust Action Extraction & Fallback
        # -------------------------------------------------------------
        # Only dispatch image generation if Aura accepted or explicitly tagged [SEND_PIC]
        has_postpone_or_pushback = any(w in raw_output.lower() for w in [
            "wait koro", "eto tara kiser", "pore dicchi", "bhebe dekhbo", "not right now", "later", "messy hair"
        ])
        is_pic = ("[SEND_PIC" in raw_output) or (is_pic_intent and not has_postpone_or_pushback)
        detected_scene = scene
        if effective_mode == "adult":
            detected_intent = "intimate_roleplay"
        elif is_pic:
            detected_intent = "image_request"
        else:
            detected_intent = "casual_chat"

        actions_list: List[CognitiveAction] = []

        # Check for [SEND_PIC:scene] tag in output
        pic_match = re.search(r'\[SEND_PIC(?::([^\]]+))?\]', raw_output, flags=re.IGNORECASE)
        if pic_match:
            is_pic = True
            if pic_match.group(1):
                raw_tag = pic_match.group(1).strip().lower()
                if any(w in raw_tag for w in ["bed", "sleep", "bedroom", "boudoir"]):
                    detected_scene = "bed"
                elif any(w in raw_tag for w in ["cafe", "coffee"]):
                    detected_scene = "cafe"
                elif any(w in raw_tag for w in ["evening", "dress", "party"]):
                    detected_scene = "evening"
                elif any(w in raw_tag for w in ["shower", "bath"]):
                    detected_scene = "shower"
                elif any(w in raw_tag for w in ["hallway", "walk"]):
                    detected_scene = "hallway"
                else:
                    detected_scene = raw_tag.split()[0] if raw_tag else detected_scene

        # If model outputted JSON, parse gracefully
        if raw_output.strip().startswith("{") and raw_output.strip().endswith("}"):
            try:
                parsed = json.loads(raw_output)
                reply = parsed.get("reply", "")
                if parsed.get("intent"):
                    detected_intent = parsed.get("intent")
                if parsed.get("is_pic") is True or parsed.get("intent") == "image_request":
                    is_pic = True
                if parsed.get("scene"):
                    s = str(parsed.get("scene")).lower()
                    detected_scene = "bed" if "bed" in s else s
            except Exception:
                reply = raw_output
        else:
            reply = raw_output

        # Clean tags from reply text
        reply = re.sub(r'\[SEND_PIC(?::[^\]]*)?\]', '', reply, flags=re.IGNORECASE).strip()
        reply = re.sub(r'\[SEND_VID(?:EO)?(?::[^\]]*)?\]', '', reply, flags=re.IGNORECASE).strip()

        if is_pic:
            actions_list.append(CognitiveAction(type="generate_image", scene=detected_scene))

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