# FILE: tests/test_open_loops_and_memory.py

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Resolve backend directory
current = Path(__file__).resolve()
backend_dir = current.parent if current.parent.name == "backend" else current.parent.parent
if (backend_dir / "backend").exists():
    backend_dir = backend_dir / "backend"
sys.path.insert(0, str(backend_dir))

from app.database.session import SessionLocal
from app.database.models import SemanticMemory, OpenLoop, SharedEpisode, UserPreference
from app.Aura.memory.memory_manager import MemoryGovernanceEngine
from app.Aura.memory.open_loops_scheduler import OpenLoopsScheduler, OpenLoopCandidate

class TestOpenLoopsAndMemoryGovernance(unittest.TestCase):
    def setUp(self):
        self.user_id = f"test_mem_user_{int(datetime.utcnow().timestamp())}"

    def tearDown(self):
        # Cleanup test records
        with SessionLocal() as db:
            db.query(SemanticMemory).filter(SemanticMemory.user_id == self.user_id).delete()
            db.query(OpenLoop).filter(OpenLoop.user_id == self.user_id).delete()
            db.query(SharedEpisode).filter(SharedEpisode.user_id == self.user_id).delete()
            db.query(UserPreference).filter(UserPreference.user_id == self.user_id).delete()
            db.commit()

    def test_semantic_fact_recording_and_capping(self):
        MemoryGovernanceEngine.record_semantic_fact(self.user_id, "User is studying Computer Science", importance_score=5)
        with SessionLocal() as db:
            mem = db.query(SemanticMemory).filter(
                SemanticMemory.user_id == self.user_id,
                SemanticMemory.memory_type == "core_memory"
            ).first()
            self.assertIsNotNone(mem)
            self.assertEqual(mem.importance_score, 5)
            self.assertIn("Computer Science", mem.content)

    def test_shared_episode_recording(self):
        MemoryGovernanceEngine.record_shared_episode(
            self.user_id,
            title="The late night hackathon session",
            impact="Built deep trust and creative alignment",
            emotional_theme="Shared Triumph"
        )
        with SessionLocal() as db:
            ep = db.query(SharedEpisode).filter(SharedEpisode.user_id == self.user_id).first()
            self.assertIsNotNone(ep)
            self.assertEqual(ep.title, "The late night hackathon session")
            self.assertEqual(ep.emotional_theme, "Shared Triumph")

    def test_memory_decay_prunes_stale_conversations_only(self):
        with SessionLocal() as db:
            # 1. Old conversation memory (15 days old, importance 1) -> Should be pruned
            old_conv = SemanticMemory(
                user_id=self.user_id,
                content="Hey there",
                memory_type="conversation",
                importance_score=1,
                created_at=datetime.utcnow() - timedelta(days=15)
            )
            # 2. Fresh conversation memory (2 days old, importance 1) -> Should be KEPT
            fresh_conv = SemanticMemory(
                user_id=self.user_id,
                content="Good morning",
                memory_type="conversation",
                importance_score=1,
                created_at=datetime.utcnow() - timedelta(days=2)
            )
            # 3. Old CORE memory (15 days old, importance 5) -> Should be KEPT
            core_mem = SemanticMemory(
                user_id=self.user_id,
                content="User lives in Dhaka",
                memory_type="core_memory",
                importance_score=5,
                created_at=datetime.utcnow() - timedelta(days=15)
            )
            db.add_all([old_conv, fresh_conv, core_mem])
            db.commit()

        pruned_count = MemoryGovernanceEngine.apply_memory_decay(self.user_id, ttl_days=10)
        self.assertEqual(pruned_count, 1)

        with SessionLocal() as db:
            remaining = db.query(SemanticMemory).filter(SemanticMemory.user_id == self.user_id).all()
            self.assertEqual(len(remaining), 2)
            types = [m.memory_type for m in remaining]
            self.assertIn("core_memory", types)
            self.assertIn("conversation", types)

    def test_compile_4layer_memory_context(self):
        MemoryGovernanceEngine.record_semantic_fact(self.user_id, "User works as a software engineer", importance_score=5)
        MemoryGovernanceEngine.record_shared_episode(self.user_id, "Exam Victory", "Celebrated together")

        with SessionLocal() as db:
            loop = OpenLoop(
                user_id=self.user_id,
                topic="Client Presentation",
                context="Important demo scheduled for tomorrow morning",
                status="active"
            )
            db.add(loop)
            db.commit()

        ctx = MemoryGovernanceEngine.compile_4layer_memory_context(self.user_id)
        self.assertIn("[User Facts]:", ctx)
        self.assertIn("software engineer", ctx)
        self.assertIn("Client Presentation", ctx)
        self.assertIn("[Interaction Style & Rhythms]:", ctx)

    def test_open_loops_scheduler_cooldown_and_discovery(self):
        scheduler = OpenLoopsScheduler(min_cooldown_hours=6)
        with SessionLocal() as db:
            # Active loop created 16 hours ago
            past_time = datetime.utcnow() - timedelta(hours=16)
            loop = OpenLoop(
                user_id=self.user_id,
                topic="Final Thesis Review",
                context="Needs to submit thesis chapter 4",
                status="active",
                created_at=past_time
            )
            db.add(loop)
            db.commit()

            # Test discovery
            candidates = scheduler.find_actionable_loops(db, self.user_id)
            self.assertTrue(len(candidates) >= 1)
            self.assertEqual(candidates[0].topic, "Final Thesis Review")
            self.assertTrue(candidates[0].urgency_score >= 0.8)

            # Test cooldown gate when no recent messages exist
            allowed, reason = scheduler.check_cooldown(db, self.user_id)
            self.assertTrue(allowed)

            # Add recent conversation message -> Cooldown should block
            recent_msg = SemanticMemory(
                user_id=self.user_id,
                content="Recent chat",
                memory_type="conversation",
                importance_score=1,
                created_at=datetime.utcnow() - timedelta(hours=1)
            )
            db.add(recent_msg)
            db.commit()

            allowed, reason = scheduler.check_cooldown(db, self.user_id)
            self.assertFalse(allowed)
            self.assertIn("cooldown", reason.lower())

if __name__ == "__main__":
    unittest.main()

