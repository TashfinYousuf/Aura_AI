# FILE: backend/app/services/episodic_service.py

import json
from datetime import datetime, timedelta
from groq import Groq
from sqlalchemy.orm import Session
from app.database.models import SharedEpisode

def extract_and_store_episode(db: Session, client: Groq, user_id: str, message: str, ai_reply: str, intensity: int):
    """
    Background worker: Extracts meaningful episodic life events from emotional interactions.
    """
    if intensity < 7:
        return

    prompt = f"""Analyze this conversation turn and determine if an episodic memory occurred.
An episode is a concrete life event, personal struggle, milestone, or deeply intimate shared moment.
Examples: 'Passed university midterms', 'Had a stressful workday', 'Stayed up late coding Aura'.

User: "{message}"
AI: "{ai_reply}"

Output strictly JSON:
{{
    "is_episode": <true/false>,
    "title": "Short title under 6 words, or null",
    "impact": "1 sentence describing relationship impact, or null"
}}"""

    try:
        res = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        data = json.loads(res.choices[0].message.content)
        
        if data.get("is_episode") and data.get("title"):
            # Check if this episode was already recorded recently to avoid duplication
            recent_cutoff = datetime.utcnow() - timedelta(days=2)
            existing = db.query(SharedEpisode).filter(
                SharedEpisode.user_id == user_id,
                SharedEpisode.title.ilike(f"%{data['title'][:15]}%"),
                SharedEpisode.created_at >= recent_cutoff
            ).first()

            if not existing:
                episode = SharedEpisode(
                    user_id=user_id,
                    title=data["title"],
                    impact_on_relationship=data.get("impact", "Deepened mutual trust and emotional connection"),
                    created_at=datetime.utcnow()
                )
                db.add(episode)
                db.commit()
                print(f"📖 [EPISODE RECORDED]: {data['title']}")
    except Exception as e:
        db.rollback()
        print(f"⚠️ [EPISODE LOG ERROR]: {e}")


def get_contextual_episodic_callback(db: Session, user_id: str, user_message: str) -> str:
    """
    Retrieves a relevant shared episode, filtering out memories referenced too recently.
    """
    # Exclude memories recorded in the last 6 hours so it doesn't repeat what just happened
    cooldown_cutoff = datetime.utcnow() - timedelta(hours=6)
    episodes = db.query(SharedEpisode).filter(
        SharedEpisode.user_id == user_id,
        SharedEpisode.created_at <= cooldown_cutoff
    ).order_by(SharedEpisode.created_at.desc()).limit(10).all()

    if not episodes:
        return ""

    message_words = set(user_message.lower().split())
    for ep in episodes:
        ep_words = set(ep.title.lower().split())
        # If there is semantic overlap in discussion topics
        if len(message_words.intersection(ep_words)) > 0:
            return (
                f"\n[SHARED MEMORY CALLBACK]: You and user experienced '{ep.title}'. "
                f"Impact: {ep.impact_on_relationship}. "
                "Casually acknowledge this shared history naturally if appropriate."
            )

    return ""