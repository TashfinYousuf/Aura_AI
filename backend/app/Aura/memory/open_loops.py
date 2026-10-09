# FILE: backend/app/Aura/memory/open_loops.py

import json
from groq import Groq
from app.core.config import settings
from app.database.session import SessionLocal
from app.database.models import OpenLoop

def scan_and_extract_open_loops(user_text: str, user_id: str):
    trigger_words = [
        "কাল", "আগামীকাল", "পরশু", "next week", "tomorrow", 
        "exam", "meeting", "interview", "presentation", "deadline", "project"
    ]
    if not any(w in user_text.lower() for w in trigger_words):
        return

    if not settings.GROQ_API_KEY:
        return

    prompt = f"""Analyze the user message for any unresolved upcoming life event, deadline, exam, or meeting.
User text: "{user_text}"

If found, return JSON:
{{"has_open_loop": true, "topic": "short topic (e.g. presentation)", "context": "1-sentence summary"}}
Else return:
{{"has_open_loop": false}}"""

    try:
        # Initialized safely inside try block
        client = Groq(api_key=settings.GROQ_API_KEY)
        res = client.chat.completions.create(
            model=settings.STRUCTURED_MODEL,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        data = json.loads(res.choices[0].message.content)
        if data.get("has_open_loop"):
            with SessionLocal() as db:
                loop = OpenLoop(
                    user_id=user_id,
                    topic=data["topic"],
                    context=data["context"],
                    status="active"
                )
                db.add(loop)
                db.commit()
                print(f"📌 [OPEN LOOP REGISTERED]: {data['topic']} for user {user_id}")
    except Exception as e:
        print(f"⚠️ [OPEN LOOP SCANNER BYPASS]: {e}")