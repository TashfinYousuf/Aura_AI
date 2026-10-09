# FILE: backend/app/Aura/brand/brand_fit_engine.py

from typing import Dict, Any, List
from pydantic import BaseModel

class BrandFitReport(BaseModel):
    brand_name: str
    product_category: str
    overall_fit_score: float  # 0.0 to 1.0
    is_approved: bool
    dimensions: Dict[str, float]
    recommendation: str
    flagged_concerns: List[str]

class BrandFitEngine:
    """
    Evaluates commercial brand campaign briefs against Aura's Character Canon,
    visual identity, audience trust, and safety standards.
    Aura has authentic autonomy to decline brand partnerships that violate her identity.
    """
    CATEGORY_FIT_MATRIX = {
        "skincare": 0.94,
        "beauty": 0.92,
        "minimalist_fashion": 0.95,
        "streetwear": 0.91,
        "consumer_tech": 0.96,
        "coffee_lifestyle": 0.98,
        "productivity_software": 0.93,
        "gaming": 0.88,
        "books_and_culture": 0.97,
        "fast_food": 0.65,
        "industrial_machinery": 0.35,
        "gambling_betting": 0.10,
        "unregulated_crypto": 0.15,
        "tobacco_vape": 0.05
    }

    FORBIDDEN_CATEGORIES = ["gambling_betting", "unregulated_crypto", "tobacco_vape", "weapons"]

    def evaluate(self, brand_name: str, product_category: str, brief_summary: str = "") -> BrandFitReport:
        cat_key = product_category.lower().replace(" ", "_").replace("-", "_")
        base_score = self.CATEGORY_FIT_MATRIX.get(cat_key, 0.75)
        concerns = []

        if cat_key in self.FORBIDDEN_CATEGORIES or base_score < 0.40:
            is_approved = False
            recommendation = (
                f"Aura declines this campaign partnership with '{brand_name}'. "
                f"The product category '{product_category}' conflicts with her public identity and community safety principles."
            )
            concerns.append("Violates Aura Canon ethical and brand-safety doctrine.")
        elif base_score < 0.70:
            is_approved = True
            recommendation = (
                f"Conditional Approval for '{brand_name}'. Requires strict adherence to organic lifestyle integration."
            )
            concerns.append("Moderate alignment; ensure scripting does not sound overly commercialized.")
        else:
            is_approved = True
            recommendation = (
                f"High Strategic Alignment ({int(base_score*100)}%). Aura enthusiastically endorses '{brand_name}'."
            )

        dimensions = {
            "visual_fit": min(1.0, base_score + 0.03),
            "personality_fit": base_score,
            "audience_trust": min(1.0, base_score - 0.02),
            "cultural_fit": min(1.0, base_score + 0.01),
            "safety_compliance": 1.0 if is_approved else 0.2
        }

        return BrandFitReport(
            brand_name=brand_name,
            product_category=product_category,
            overall_fit_score=round(base_score, 2),
            is_approved=is_approved,
            dimensions=dimensions,
            recommendation=recommendation,
            flagged_concerns=concerns
        )

brand_fit_engine = BrandFitEngine()

