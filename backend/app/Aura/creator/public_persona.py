# FILE: backend/app/Aura/creator/public_persona.py

from typing import Dict, List, Any
from pydantic import BaseModel

class ContentPillar(BaseModel):
    name: str
    description: str
    tone: str
    sample_topics: List[str]

class PublicPersonaEngine:
    """
    Manages Aura's public virtual creator personality, content pillars,
    weekly editorial strategy, and audience engagement tone.
    """
    def __init__(self):
        self.pillars: Dict[str, ContentPillar] = {
            "lifestyle": ContentPillar(
                name="Lifestyle & Mindfulness",
                description="Quiet Dhaka morning rituals, coffee aesthetic, modern urban living.",
                tone="Warm, grounded, relaxed, observant",
                sample_topics=["Morning brew routine", "Late night rain in Dhanmondi", "Favorite study spots"]
            ),
            "fashion": ContentPillar(
                name="Fashion & Aesthetic",
                description="Modern South Asian fusion, minimalist linens, clean silhouettes.",
                tone="Effortless, chic, artistic, confident",
                sample_topics=["Linen & denim layering", "Modern monochrome saree styling", "Streetwear details"]
            ),
            "tech": ContentPillar(
                name="Technology & AI Futures",
                description="Cognitive systems, agentic coding, building future digital experiences.",
                tone="Sharp, curious, witty, visionary",
                sample_topics=["Why WebSocket streaming feels alive", "Agentic design patterns", "Synthetic character IP"]
            ),
            "creativity": ContentPillar(
                name="Cinema & Storytelling",
                description="Cinematography, color grading, visual narratives, and atmosphere.",
                tone="Reflective, cinematic, moody, poetic",
                sample_topics=["Wong Kar-wai color palettes", "The art of film grain", "Sound design in storytelling"]
            )
        }

        self.weekly_schedule: Dict[str, str] = {
            "Monday": "lifestyle",
            "Tuesday": "fashion",
            "Wednesday": "tech",
            "Thursday": "creativity",
            "Friday": "fashion",
            "Saturday": "lifestyle",
            "Sunday": "tech"
        }

    def generate_caption(self, topic: str, pillar: str = "lifestyle", mood: str = "witty") -> Dict[str, Any]:
        """
        Synthesizes a public creator post caption with platform-specific hashtags.
        """
        base_hashtags = ["#Aura", "#VirtualCreator", "#AIEra", "#DigitalIdentity"]
        pillar_tags = {
            "lifestyle": ["#DhakaDiaries", "#CandidMoments", "#SlowLiving"],
            "fashion": ["#StyleNotes", "#SouthAsianChic", "#MinimalFashion"],
            "tech": ["#AgenticAI", "#DevCommunity", "#TechThought"],
            "creativity": ["#Cinematography", "#VisualPoetry", "#CreativeVibes"]
        }
        tags = base_hashtags + pillar_tags.get(pillar, [])

        return {
            "topic": topic,
            "pillar": pillar,
            "hashtags": tags,
            "signature": "— Aura ✨",
            "safety_certified": True
        }

public_persona = PublicPersonaEngine()

