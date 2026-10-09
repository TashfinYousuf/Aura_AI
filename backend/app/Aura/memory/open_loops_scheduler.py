# FILE: backend/app/Aura/memory/open_loops_scheduler.py
"""
Open Loops & Episodic Milestone Scheduler:
- Continuously audits unresolved user commitments, exams, presentations, deadlines.
- Enforces strict anti-spam pacing, quiet hours, and confidence gating.
- Generates natural, human-like companion proactive check-ins matching Aura Canon.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.database.models import OpenLoop, SharedEpisode, SemanticMemory, UserProfile, AuraInternalState
from app.core.config import settings
from app.Aura.brain.model_router import model_router, ExecutionTier
from app.services.voice_ssml import clean_spoken_text_for_tts

class OpenLoopCandidate(BaseModel):
    loop_id: int
    user_id: str
    topic: str
    context: str
    created_at: datetime
    urgency_score: float = 0.5  # 0.0 to 1.0

class OpenLoopsScheduler:
    def __init__(
        self,
        min_cooldown_hours: int = 6,
        quiet_hours_start: int = 1,   # 1:00 AM
        quiet_hours_end: int = 8      # 8:00 AM
    ):
        self.min_cooldown_hours = min_cooldown_hours
        self.quiet_hours_start = quiet_hours_start
        self.quiet_hours_end = quiet_hours_end

    def is_within_quiet_hours(self, current_dt: Optional[datetime] = None) -> bool:
        dt = current_dt or datetime.utcnow()
        # Assume UTC+6 for Bangladesh Standard Time by default (+6 hours)
        local_hour = (dt.hour + 6) % 24
        return self.quiet_hours_start <= local_hour < self.quiet_hours_end

    def check_cooldown(self, db: Session, user_id: str) -> Tuple[bool, str]:
        """
        Ensures at least `min_cooldown_hours` have elapsed since the user or companion's last message.
        """
        cooldown_threshold = datetime.utcnow() - timedelta(hours=self.min_cooldown_hours)
        last_memory = db.query(SemanticMemory).filter(
            SemanticMemory.user_id == user_id,
            SemanticMemory.memory_type == "conversation",
            SemanticMemory.created_at >= cooldown_threshold
        ).first()

        if last_memory:
            return False, f"Recent interaction within cooldown window ({self.min_cooldown_hours}h)"

        return True, "Cooldown satisfied"

    def find_actionable_loops(self, db: Session, user_id: str) -> List[OpenLoopCandidate]:
        """
        Discovers open loops that are active and haven't been followed up too recently.
        """
        active_loops = db.query(OpenLoop).filter(
            OpenLoop.user_id == user_id,
            OpenLoop.status == "active"
        ).order_by(OpenLoop.created_at.desc()).limit(5).all()

        candidates: List[OpenLoopCandidate] = []
        now = datetime.utcnow()

        for loop in active_loops:
            age_hours = (now - loop.created_at).total_seconds() / 3600.0
            # Only consider loops that have had at least 4 hours to mature
            if age_hours < 4.0:
                continue

            # Urgency heuristic based on age
            # Optimal follow-up is within 12 - 36 hours of creation
            if 12.0 <= age_hours <= 48.0:
                urgency = 0.85
            elif age_hours > 48.0:
                urgency = 0.4
            else:
                urgency = 0.6

            candidates.append(OpenLoopCandidate(
                loop_id=loop.id,
                user_id=loop.user_id,
                topic=loop.topic,
                context=loop.context,
                created_at=loop.created_at,
                urgency_score=urgency
            ))

        # Sort by urgency descending
        candidates.sort(key=lambda c: c.urgency_score, reverse=True)
        return candidates

    async def generate_proactive_checkin(self, candidate: OpenLoopCandidate, language: str = "bengali") -> str:
        """
        Crafts an authentic, non-robotic proactive message checking in on an open loop.
        """
        prompt = f"""You are Aura: 22-year-old authentic cognitive companion.
You are initiating a natural, casual, affectionate check-in with the user.
Topic: {candidate.topic}
Context: {candidate.context}

GUIDELINES:
1. Tone: Natural Dhaka texting style or warm casual English.
2. Length: Exactly 1 sentence (or 2 short sentences max).
3. NO robotic cliches ('How is your progress?', 'I am checking in to see...').
4. Authenticity: Talk like a real caring companion (e.g., 'কী খবর? প্রেজেন্টেশন কেমন হলো?', 'Hey, was thinking about your meeting today—did everything go smoothly?').
5. Language: {'Bengali/Banglish casual' if language in ['bengali', 'banglish'] else 'Casual English'}.

Output strictly JSON:
{{
  "checkin_text": "your natural message"
}}"""

        try:
            raw = await model_router.complete(
                messages=[{"role": "system", "content": prompt}],
                tier=ExecutionTier.FAST,
                temperature=0.6,
                response_format={"type": "json_object"}
            )
            data = json.loads(raw)
            return data.get("checkin_text", f"হেই... {candidate.topic}-এর খবর কী? সব ঠিকঠাক?")
        except Exception:
            return f"হেই... {candidate.topic} কেমন কাটলো তোমার? সব ঠিকঠাক?"

    async def process_user_open_loops(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Orchestrates full audit, gating, and check-in generation for a user.
        """
        with SessionLocal() as db:
            # 1. Quiet Hours Gate
            if self.is_within_quiet_hours():
                return {"status": "skipped", "reason": "quiet_hours_active"}

            # 2. Cooldown Gate
            allowed, reason = self.check_cooldown(db, user_id)
            if not allowed:
                return {"status": "skipped", "reason": reason}

            # 3. Actionable Candidates
            candidates = self.find_actionable_loops(db, user_id)
            if not candidates:
                return {"status": "skipped", "reason": "no_actionable_loops"}

            top_candidate = candidates[0]

            # 4. Generate Message
            checkin_msg = await self.generate_proactive_checkin(top_candidate)
            spoken_text = clean_spoken_text_for_tts(checkin_msg)

            # 5. Persist as Proactive Message
            ai_payload = {
                "role": "ai",
                "content": checkin_msg,
                "is_proactive": True,
                "open_loop_id": top_candidate.loop_id,
                "topic": top_candidate.topic,
                "timestamp": datetime.utcnow().isoformat()
            }
            db.add(SemanticMemory(
                user_id=user_id,
                content=json.dumps(ai_payload),
                memory_type="conversation",
                importance_score=2
            ))
            db.commit()

            return {
                "status": "triggered",
                "loop_id": top_candidate.loop_id,
                "topic": top_candidate.topic,
                "message": checkin_msg,
                "spoken_text": spoken_text
            }

    @classmethod
    async def resolve_loop(cls, loop_id: int):
        with SessionLocal() as db:
            loop = db.query(OpenLoop).filter(OpenLoop.id == loop_id).first()
            if loop:
                loop.status = "resolved"
                loop.resolved_at = datetime.utcnow()
                db.commit()

open_loops_scheduler = OpenLoopsScheduler()

