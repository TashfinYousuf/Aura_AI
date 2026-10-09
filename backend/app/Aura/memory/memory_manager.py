# FILE: backend/app/Aura/memory/memory_manager.py

import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.database.models import SemanticMemory, OpenLoop, SharedEpisode, UserPreference

class MemoryGovernanceEngine:
    """
    4-Layer Memory OS & Governance:
    - Layer 1 (Working Memory): Sliding active context in session.
    - Layer 2 (Episodic Memory): Shared personal milestones, life struggles, bonding stories.
    - Layer 3 (Semantic Memory): Stable user profile facts (goals, career, identity).
    - Layer 4 (Procedural Memory): Interaction style, rhythm, and anti-cliche preferences.
    """

    @staticmethod
    def get_procedural_preferences(user_id: Optional[str] = None) -> str:
        custom_prefs = []
        if user_id:
            try:
                with SessionLocal() as db:
                    prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).limit(3).all()
                    for p in prefs:
                        custom_prefs.append(f"- {p.preference_key}: {p.preference_val}")
            except Exception:
                pass

        default_rules = (
            "- Short, natural, conversational texting sentences (1-2 sentences max).\n"
            "- Dislikes robotic therapy cliches, over-validation, and unnatural romance.\n"
            "- Appreciates witty, grounded, teasing yet caring companionship."
        )
        if custom_prefs:
            return default_rules + "\n" + "\n".join(custom_prefs)
        return default_rules

    @classmethod
    def record_semantic_fact(cls, user_id: str, content: str, importance_score: int = 4):
        """
        Records a persistent user fact (importance 1 to 10).
        """
        score = max(1, min(10, importance_score))
        with SessionLocal() as db:
            mem = SemanticMemory(
                user_id=user_id,
                content=content,
                memory_type="core_memory",
                importance_score=score
            )
            db.add(mem)
            db.commit()

    @classmethod
    def record_shared_episode(cls, user_id: str, title: str, impact: str, emotional_theme: str = ""):
        """
        Records an episodic milestone into SharedEpisode table.
        """
        with SessionLocal() as db:
            ep = SharedEpisode(
                user_id=user_id,
                title=title,
                impact_on_relationship=impact,
                emotional_theme=emotional_theme or "Bonding",
                created_at=datetime.utcnow()
            )
            db.add(ep)
            db.commit()

    @classmethod
    def apply_memory_decay(cls, user_id: str, ttl_days: int = 14, min_retention_score: int = 3) -> int:
        """
        Memory Decay Governance:
        Prunes old trivial conversation messages (importance < min_retention_score)
        older than `ttl_days` while strictly keeping core memories and milestones.
        """
        cutoff = datetime.utcnow() - timedelta(days=ttl_days)
        with SessionLocal() as db:
            stale_query = db.query(SemanticMemory).filter(
                SemanticMemory.user_id == user_id,
                SemanticMemory.memory_type == "conversation",
                SemanticMemory.importance_score < min_retention_score,
                SemanticMemory.created_at <= cutoff
            )
            count = stale_query.count()
            stale_query.delete(synchronize_session=False)
            db.commit()
            return count

    @classmethod
    def compile_4layer_memory_context(cls, user_id: str) -> str:
        semantic_facts: List[str] = []
        episodic_events: List[str] = []

        with SessionLocal() as db:
            # Layer 2: Shared Episodes (Milestones)
            episodes = db.query(SharedEpisode).filter(
                SharedEpisode.user_id == user_id
            ).order_by(SharedEpisode.created_at.desc()).limit(2).all()

            for ep in episodes:
                episodic_events.append(f"- Shared Milestone: '{ep.title}' ({ep.impact_on_relationship})")

            # Layer 2: Active Open Loops (Upcoming events/deadlines)
            loops = db.query(OpenLoop).filter(
                OpenLoop.user_id == user_id,
                OpenLoop.status == "active"
            ).order_by(OpenLoop.created_at.desc()).limit(2).all()

            for loop in loops:
                episodic_events.append(f"- Active Commitment: {loop.topic} ({loop.context})")

            # Layer 3: Semantic User Facts
            facts = db.query(SemanticMemory).filter(
                SemanticMemory.user_id == user_id,
                SemanticMemory.memory_type == "core_memory"
            ).order_by(SemanticMemory.importance_score.desc(), SemanticMemory.created_at.desc()).limit(4).all()

            for f in facts:
                semantic_facts.append(f"- {str(f.content)[:100]}")

        parts = []
        if semantic_facts:
            parts.append("[User Facts]:\n" + "\n".join(semantic_facts))
        if episodic_events:
            parts.append("[Ongoing Context & Shared Milestones]:\n" + "\n".join(episodic_events))
        parts.append("[Interaction Style & Rhythms]:\n" + cls.get_procedural_preferences(user_id))

        return "\n\n".join(parts)

compile_4layer_memory_context = MemoryGovernanceEngine.compile_4layer_memory_context