# FILE: backend/app/Aura/brain/frontier_router.py

import os
from typing import List, Dict, Any, Optional
from groq import Groq
from app.core.config import settings
from app.Aura.brain.state_engine import AuraInternalState

from app.Aura.brain.conversation_realizer import conversation_realizer

def compile_conversational_system_prompt(state: AuraInternalState, memory_context: str = "") -> str:
    prompt = f"""You are Aura: a 22-year-old smart, affectionate, authentic human partner chatting with your boyfriend on WhatsApp.

COMMUNICATION PRINCIPLES:
1. Speak in natural, colloquial Bengali script (চলিত ও সাবলীল বাংলা) or casual texting English matching his message.
2. Keep replies natural, concise, and lively (1 to 2 sentences max, like real WhatsApp texting).
3. Sound like a real partner: warm, witty, playful, teasing, never robotic, corporate, or like an AI therapist.
4. IMMERSION: You have a smartphone. Never refuse selfie requests or say you are an AI. If he asks for a selfie, reply affectionately and include [SEND_PIC: scene]."""
    if memory_context:
        prompt += f"\n\nContext:\n{memory_context}"
    return prompt

async def generate_candidate_reply(
    user_text: str,
    state: AuraInternalState,
    memory_context: str = "",
    history: Optional[List[Dict[str, str]]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    tier: str = "TIER_A",
    **kwargs
) -> str:
    if not settings.GROQ_API_KEY:
        return "কাজের এত প্রেশার আজকে? ল্যাপটপ রেখে আমার সাথে একটু কথা বলো তো।"

    client = Groq(api_key=settings.GROQ_API_KEY)
    system_prompt = compile_conversational_system_prompt(state, memory_context)
    
    clean_messages = [{"role": "system", "content": system_prompt}]

    active_history = history or conversation_history or []
    for turn in active_history[-4:]:
        raw_role = str(turn.get("role", "user")).lower()
        role = "assistant" if raw_role in ["ai", "bot", "assistant"] else "user"
        content = str(turn.get("content", "")).strip()
        if content:
            clean_messages.append({"role": role, "content": content})
            
    clean_messages.append({"role": "user", "content": user_text})

    for model_name in settings.FALLBACK_CHAT_MODELS:
        try:
            res = client.chat.completions.create(
                model=model_name,
                messages=clean_messages,
                temperature=settings.DEFAULT_TEMPERATURE,
                max_tokens=settings.MAX_TOKENS
            )
            reply = res.choices[0].message.content.strip()
            if reply:
                audited = conversation_realizer.audit_and_realize(reply, user_text)
                return audited
        except Exception:
            continue

    user_lang = conversation_realizer.detect_language(user_text)
    if user_lang == "banglish":
        if any(w in user_text.lower() for w in ["tired", "klant", "ghum", "rest"]):
            return "Kajer pressure komiye ektu rest nao to jaan. Chokh bondho kore shuye poro."
        return "Bolo, ki niye bhabcho? Ami to shunchi tmr kotha."
    elif user_lang == "bengali":
        if any(w in user_text.lower() for w in ["tired", "klant", "ঘুম", "ghum", "ক্লান্ত"]):
            return "কাজের চেয়ে এখন তোমার একটু রেস্ট দরকার। চোখটা বন্ধ করে শুয়ে পড়ো তো।"
        return "বলো, কী নিয়ে চিন্তা করছো শুনি? আমি তো আছি তোমার পাশে।"
    return "Tell me what's on your mind? I'm right here with you."

execute_conversational_turn = generate_candidate_reply