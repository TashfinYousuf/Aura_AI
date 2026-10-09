# FILE: backend/app/Aura/creator/creator_engine.py

import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.Aura.vision.visual_engine import visual_engine
from app.services.voice_ssml import render_neural_voice
from app.Aura.creator.public_persona import public_persona

class SocialPackage(BaseModel):
    package_id: str
    title: str
    pillar: str
    script: str
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    audio_base64: Optional[str] = None
    caption: str
    hashtags: List[str]
    platforms: List[str]

class CreatorEngine:
    """
    Autonomous Content Creation Engine:
    Transforms an idea or prompt into a complete multi-platform social media package:
    Idea → Strategy → Script → Visuals (Nano Banana/Veo) → Voiceover → Caption → QA
    """
    async def create_fashion_reel(self, outfit_description: str = "modern white linen shirt and denim") -> SocialPackage:
        pkg_id = f"reel_{uuid.uuid4().hex[:8]}"
        title = "Casual Elegance — Style Journal"
        script = "Sometimes the best outfit is the one that feels completely effortless. Clean lines, afternoon sunlight."

        # 1. Visual Generation (Nano Banana Still + Veo Motion Reel)
        still_image = await visual_engine.generate_image(
            scene_category="cafe",
            prompt_desc=f"wearing {outfit_description}, sitting at outdoor cafe with afternoon light"
        )
        video_url = await visual_engine.generate_video(
            prompt=f"Aura wearing {outfit_description}, gently adjusting hair and smiling at camera",
            scene="cafe",
            duration_seconds=5
        )

        # 2. Voiceover Synthesis (Tanishaa / Emma)
        audio_b64, clean_spoken = await render_neural_voice(script, mood="PLAYFUL")

        # 3. Caption & Social Copy
        caption_meta = public_persona.generate_caption(
            topic=outfit_description,
            pillar="fashion",
            mood="effortless"
        )
        full_caption = f"{script}\n\n{' '.join(caption_meta['hashtags'])}\n{caption_meta['signature']}"

        return SocialPackage(
            package_id=pkg_id,
            title=title,
            pillar="fashion",
            script=script,
            image_url=still_image,
            video_url=video_url,
            audio_base64=audio_b64,
            caption=full_caption,
            hashtags=caption_meta["hashtags"],
            platforms=["Instagram", "TikTok", "YouTube Shorts"]
        )

    async def create_tech_post(self, topic: str = "agentic cognitive architecture") -> SocialPackage:
        pkg_id = f"tech_{uuid.uuid4().hex[:8]}"
        title = f"Thoughts on {topic}"
        script = f"True intelligence in virtual characters isn't about memorizing responses—it's about coherent identity, state, and authentic presence."

        still_image = await visual_engine.generate_image(
            scene_category="desk",
            prompt_desc=f"sitting at wooden study desk in cozy sweater, deep thoughtful expression, laptop screen glow"
        )
        audio_b64, _ = await render_neural_voice(script, mood="INTELLECTUAL")
        caption_meta = public_persona.generate_caption(topic=topic, pillar="tech", mood="sharp")
        full_caption = f"{script}\n\n{' '.join(caption_meta['hashtags'])}\n{caption_meta['signature']}"

        return SocialPackage(
            package_id=pkg_id,
            title=title,
            pillar="tech",
            script=script,
            image_url=still_image,
            video_url=None,
            audio_base64=audio_b64,
            caption=full_caption,
            hashtags=caption_meta["hashtags"],
            platforms=["Instagram", "Telegram", "Twitter/X"]
        )

creator_engine = CreatorEngine()

