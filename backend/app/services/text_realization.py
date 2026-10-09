# FILE: backend/app/services/text_realization.py

import re
from typing import Dict, Any
from groq import Groq
import os

# Specific cringe patterns to instantly nuke
CRINGE_PATTERNS = [
    r"নিজের প্রতি.*দয়া",
    r"ক্লান্তি স্বাভাবিক",
    r"দারুণ কাজ করেছ",
    r"কী মজা করব",
    r"তুমিই ফিরে এলে",
    r"শ্বাস নাও",
    r"গভীর শ্বাস",
    r"আমি এখানে আছি",
    r"সব ঠিক হয়ে যাবে",
    r"কঠিন দিন",
    r"মনে রেখো তুমি একা নও",
    r"😜", r"😉", r"🥳", r"🤩"
]

def analyze_draft_naturalness(draft_text: str) -> Dict[str, bool]:
    has_cringe = any(re.search(p, draft_text) for p in CRINGE_PATTERNS)
    is_verbose = len(draft_text.split()) > 25
    has_bad_exclamations = draft_text.count("!") > 1

    return {
        "has_cringe": has_cringe,
        "too_verbose": is_verbose,
        "has_bad_exclamations": has_bad_exclamations,
        "needs_refinement": (has_cringe or is_verbose or has_bad_exclamations)
    }

async def realize_conversational_response(draft_text: str, user_text: str) -> str:
    analysis = analyze_draft_naturalness(draft_text)
    
    if not analysis["needs_refinement"]:
        return draft_text

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    from app.core.config import settings
    is_bn = any('\u0980' <= c <= '\u09FF' for c in user_text)
    lang_rule = "colloquial Bengali script" if is_bn else "casual texting English"
    
    correction_prompt = f"""You are a dialogue quality controller for Aura, a 22yo modern, witty partner.
The raw draft below sounds like awful literal Google Translate AI, robotic corporate therapy, or childish cartoon nonsense.

User message: "{user_text}"
Awful raw draft: "{draft_text}"

TASK: Rewrite the response into 1-2 totally authentic, natural sentences in {lang_rule}.
RULES:
- NO corporate therapy or AI disclaimers ("take a breath", "as an ai", "caring for yourself").
- NO childish cartoon emojis (No 😜, 😉, 🥳).
- Sound like a real young adult girlfriend texting on phone: calm, affectionate, natural.
- Output ONLY the rewritten sentence, nothing else."""

    try:
        res = client.chat.completions.create(
            model=settings.PRIMARY_CHAT_MODEL,
            messages=[{"role": "system", "content": correction_prompt}],
            temperature=0.5,
            max_tokens=150
        )
        refined = res.choices[0].message.content.strip()
        refined = refined.replace('"', '').replace("'", "")
        print(f"✨ [REALIZATION PURGE] Nuked cringe draft: '{draft_text}' -> '{refined}'")
        return refined
    except Exception as e:
        print(f"⚠️ [REALIZATION FAILED]: {e}")
        return draft_text