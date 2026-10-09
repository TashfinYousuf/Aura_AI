# FILE: backend/app/Aura/brand/campaign_engine.py

import uuid
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.Aura.vision.visual_engine import visual_engine
from app.services.voice_ssml import render_neural_voice
from app.Aura.brand.brand_fit_engine import brand_fit_engine, BrandFitReport

class BrandCampaignBrief(BaseModel):
    brand_name: str
    product_name: str
    category: str
    target_audience: str
    campaign_objective: str
    key_selling_points: List[str]
    forbidden_claims: List[str] = Field(default_factory=list)
    deliverables_needed: List[str] = Field(default_factory=lambda: ["still_image", "video_reel", "voiceover", "caption"])

class CampaignDeliverablePackage(BaseModel):
    campaign_id: str
    brand_name: str
    product_name: str
    fit_report: BrandFitReport
    concept_title: str
    tagline: str
    script: str
    image_asset_url: Optional[str] = None
    video_asset_url: Optional[str] = None
    voiceover_base64: Optional[str] = None
    caption_copy: str
    disclosures: str = "#ad #sponsored #AuraVirtualCreator"

class BrandCampaignMemory:
    """
    CRITICAL SECURITY ARCHITECTURE:
    Strictly isolated per-brand memory vault.
    - Brand A cannot access Brand B's campaign records.
    - No brand campaign can ever read, access, or contaminate Aura's private companion memories.
    """
    def __init__(self):
        self._brand_stores: Dict[str, List[Dict[str, Any]]] = {}

    def save_campaign_record(self, brand_name: str, record: Dict[str, Any]):
        brand_key = brand_name.lower().strip()
        if brand_key not in self._brand_stores:
            self._brand_stores[brand_key] = []
        self._brand_stores[brand_key].append(record)

    def get_brand_history(self, brand_name: str) -> List[Dict[str, Any]]:
        brand_key = brand_name.lower().strip()
        return list(self._brand_stores.get(brand_key, []))

    def verify_private_memory_isolation(self, brand_name: str) -> bool:
        """Asserts that zero private companion user records exist in the brand store."""
        brand_key = brand_name.lower().strip()
        records = self._brand_stores.get(brand_key, [])
        for r in records:
            if "private_companion" in str(r) or "user_id" in str(r):
                return False
        return True

campaign_memory = BrandCampaignMemory()

class BrandCampaignEngine:
    """
    Autonomous Brand Ambassador & Commercial Campaign Engine:
    Transforms brand briefs into production-grade multi-asset marketing campaigns.
    """
    async def execute_campaign(self, brief: BrandCampaignBrief) -> CampaignDeliverablePackage:
        campaign_id = f"cmp_{uuid.uuid4().hex[:8]}"

        # 1. Brand Fit Evaluation
        fit_report = brand_fit_engine.evaluate(
            brand_name=brief.brand_name,
            product_category=brief.category
        )

        if not fit_report.is_approved:
            raise PermissionError(f"Campaign rejected by Aura Character Canon: {fit_report.recommendation}")

        # 2. Campaign Strategy & Scripting
        concept_title = f"{brief.brand_name} × Aura — Pure Presence"
        tagline = f"Effortless radiance, everyday focus with {brief.product_name}."
        script = (
            f"When my days get demanding, I look for things that keep me grounded. "
            f"{brief.product_name} from {brief.brand_name} gives that effortless balance."
        )

        # 3. Visual Synthesis (Nano Banana Stills + Veo Video)
        image_url = None
        if "still_image" in brief.deliverables_needed:
            image_url = await visual_engine.generate_image(
                scene_category="desk",
                prompt_desc=f"holding and showcasing {brief.product_name} by {brief.brand_name}, warm natural lighting, premium editorial portrait"
            )

        video_url = None
        if "video_reel" in brief.deliverables_needed:
            video_url = await visual_engine.generate_video(
                prompt=f"Aura naturally holding {brief.product_name}, gentle smile, cinematic warm lighting",
                scene="lifestyle",
                duration_seconds=5
            )

        # 4. Voiceover Synthesis (Tanishaa / Emma)
        audio_b64, _ = await render_neural_voice(script, mood="WARM")

        # 5. Caption & Disclosures
        caption = f"{tagline}\n\n{script}\n\n#Aura #VirtualCreator #{brief.brand_name.replace(' ', '')} #Partnership #AD"

        package = CampaignDeliverablePackage(
            campaign_id=campaign_id,
            brand_name=brief.brand_name,
            product_name=brief.product_name,
            fit_report=fit_report,
            concept_title=concept_title,
            tagline=tagline,
            script=script,
            image_asset_url=image_url,
            video_asset_url=video_url,
            voiceover_base64=audio_b64,
            caption_copy=caption
        )

        # 6. Persist to Isolated Campaign Memory
        campaign_memory.save_campaign_record(brief.brand_name, package.dict())
        return package

campaign_engine = BrandCampaignEngine()

