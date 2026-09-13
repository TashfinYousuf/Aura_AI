import random
from typing import Dict, Any

class AuraPromptComposer:
    """
    Constructs high-fidelity, identity-locked generation prompts
    using Aura's Master Character Bible.
    """

    def __init__(self):
        # 1. Fixed Identity Anchors (Never changes across generations)
        self.face_anchor = (
            "stunning 22-year-old fair skin European-Slavic toned woman, "
            "sharp straight nose, thin attractive defined lips, captivating almond eyes, "
            "medium-length layered dark brown hair with natural stray strands"
        )
        self.body_anchor = (
            "tall slim athletic build, flat toned abdomen, medium chest, fitted hips"
        )
        self.skin_realism = (
            "natural skin pores, authentic skin texture, subtle blush, soft subsurface scattering, "
            "no plastic smoothing, unedited natural aesthetic"
        )

        # 2. Dynamic Environments (Private/Bedroom Focused)
        self.environments = {
            "bedroom_bed": "lying on a cozy white bed, messy soft sheets, warm bedside lamp glow",
            "bedroom_mirror": "standing in front of a bedroom full-length mirror, soft ambient room lighting",
            "bedroom_window": "sitting by the bedroom window, soft natural morning sunlight casting realistic shadows",
            "cozy_desk": "sitting at a wooden work desk, warm indoor background blur"
        }

        # 3. Dynamic Wardrobe Presets
        self.wardrobe = {
            "saree": "wearing a modern elegant monochrome chiffon saree with a minimalist sleeveless blouse",
            "bedroom_casual": "wearing a fitted ribbed tank top and casual lounge shorts",
            "nightwear": "wearing a soft silk pajama set, casual straps",
            "gown": "wearing a sleek fitted evening gown with elegant neckline",
            "oversized_hoodie": "wearing an oversized comfortable fleece hoodie draped casually"
        }

        # 4. Camera Styles (Raw Phone Aesthetic)
        self.camera_styles = [
            "candid smartphone front camera selfie, slight arm perspective, natural wide angle",
            "intimate mirror selfie holding modern phone, soft indoor lighting",
            "casual handheld snapshot taken by herself, authentic camera grain, shallow depth of field"
        ]

    def build_prompt(self, scene_intent: Dict[str, Any]) -> str:
        """
        Combines fixed DNA with dynamic context.
        scene_intent example: {'setting': 'bedroom_bed', 'outfit': 'saree', 'expression': 'gentle smirk'}
        """
        setting_key = scene_intent.get("setting", "bedroom_bed")
        outfit_key = scene_intent.get("outfit", "bedroom_casual")
        expression = scene_intent.get("expression", "subtle playful smile, direct eye contact")

        selected_setting = self.environments.get(setting_key, self.environments["bedroom_bed"])
        selected_outfit = self.wardrobe.get(outfit_key, self.wardrobe["bedroom_casual"])
        selected_camera = random.choice(self.camera_styles)

        # Assembling the final structured prompt
        final_prompt = (
            f"{selected_camera}, {self.face_anchor}, {self.body_anchor}, {expression}, "
            f"{selected_outfit}, {selected_setting}, {self.skin_realism}, "
            f"authentic room perspective, natural indoor shadows, 35mm lens effect"
        )

        return final_prompt

    def build_negative_prompt(self) -> str:
        """
        Negative prompts targeting common AI artifacts and plastic looks.
        """
        return (
            "plastic skin, cartoon, 3d render, anime, smooth airbrushed face, heavy makeup, "
            "doll-like features, deformed fingers, extra limbs, asymmetrical eyes, blurry, low resolution"
        )

# Example execution test
if __name__ == "__main__":
    composer = AuraPromptComposer()
    sample_intent = {
        "setting": "bedroom_bed",
        "outfit": "saree",
        "expression": "soft intimate gaze, subtle smile"
    }
    generated_prompt = composer.build_prompt(sample_intent)
    print("--- GENERATED MASTER PROMPT ---")
    print(generated_prompt)
    print("\n--- NEGATIVE PROMPT ---")
    print(composer.build_negative_prompt())