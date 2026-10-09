# FILE: backend/app/Aura/brain/naturalness_critic.py

import os
import re
import random
from typing import Any
from groq import Groq

# Banned therapy / robotic triggers
BANNED_THERAPY_PATTERNS = [
    r"শ্বাস\s*নাও",
    r"গভীর\s*শ্বাস",
    r"চোখ\s*বন্ধ\s*করে",
    r"১০\s*মিনিট",
    r"মেডিটেশন",
    r"নিজের\s*প্রতি\s*দয়া",
    r"ক্লান্তি\s*স্বাভাবিক",
    r"আমি\s*এখানে\s*আছি",
    r"সব\s*ঠিক\s*হয়ে\s*যাবে",
    r"take\s*a\s*deep\s*breath",
    r"close\s*your\s*eyes",
    r"as\s*an\s*ai",
    r"feel\s*better"
]

# Real, playful girlfriend replacements when user is tired/annoyed
ORGANIC_REPLACEMENTS = [
    "কাজের প্যারা ভুলে গিয়ে আমার সাথে একটু গল্প করো, মেজাজ এমনিতেই ফ্রেশ হয়ে যাবে।",
    "চুপচাপ মাথার নিচে বালিশ দিয়ে শোও তো, এত কথা না বলে রেস্ট নাও।",
    "আমার সাথে একটু আড্ডা দাও, দেখবা সব ক্লান্তি গায়েব হয়ে গেছে।",
    "অতিরিক্ত ভেবে মাথা গরম কইরো না তো। শুয়ে পড়ো, আমি আছি পাশে।"
]

ORGANIC_EN_REPLACEMENTS = [
    "Forget about work for a minute and chat with me, you'll feel so much better ✨",
    "Put your phone down and get some rest! Don't overthink things.",
    "Come talk to me for a bit, let's take your mind off everything.",
    "Hey, take it easy tonight. I'm right here with you ✨"
]

async def sanitize_and_critic_pass(raw_draft: str, user_text: str, state: Any, **kwargs) -> str:
    """
    Hard-stops any robotic therapy language with zero silent failthrough.
    """
    has_bengali = any('\u0980' <= c <= '\u09FF' for c in user_text)
    
    # 1. Deterministic Interception (Zero dependency on secondary LLM failures)
    for pattern in BANNED_THERAPY_PATTERNS:
        if re.search(pattern, raw_draft, re.IGNORECASE):
            print(f"🛡️ [HARD-CRITIC BLOCKED]: '{raw_draft}' triggered '{pattern}'")
            return random.choice(ORGANIC_REPLACEMENTS if has_bengali else ORGANIC_EN_REPLACEMENTS)

    # 2. Prevent unfinished / cut-off sentences (e.g. "শ্বাস নিলেই")
    stripped = raw_draft.strip()
    if len(stripped.split()) <= 2 and not stripped.endswith(("?", "!", "।", ".")):
        print(f"🛡️ [HARD-CRITIC BLOCKED FRAGMENT]: '{stripped}'")
        return "উফ্, তুমি না একদম অবুঝের মতো করো! ফোন রেখে ঘুমাও এখন।" if has_bengali else "Hey, get some rest already and stop overthinking! ✨"

    # 3. LLM Critic Pass (Using working active Groq model)
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return raw_draft

    # If draft is too formal or generic, rewrite it
    if any(k in raw_draft.lower() for k in ["করুন", "বলুন", "ধন্যবাদ", "সহায়তা", "assist you"]):
        try:
            client = Groq(api_key=api_key)
            prompt = f"""You are the tone auditor for Aura, a 22yo lively companion texting her boyfriend.
The draft below is too formal or robotic. Rewrite it into 1 short, natural, slightly teasing spoken sentence matching the user's language.

User message: "{user_text}"
Bad draft: "{raw_draft}"

Output ONLY the rewritten sentence:"""
            
            from app.core.config import settings
            res = client.chat.completions.create(
                model=settings.PRIMARY_CHAT_MODEL,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.4,
                max_tokens=100
            )
            return res.choices[0].message.content.strip().replace('"', '').replace("'", "")
        except Exception:
            return raw_draft

    return raw_draft

# Compatibility alias
naturalize_and_audit = sanitize_and_critic_pass