# FILE: backend/app/core/identity_pack.py

from typing import Dict, Any

AURA_MULTI_SCENE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "bedroom_desk": {
        "outfit": "casual black knit cardigan over fitted top",
        "pose": "leaning chin comfortably on right hand at wooden study desk",
        "environment": "cozy student room, laptop and notebook in background, warm desk lamp",
        "lighting": "intimate warm indoor ambient light",
        "shot_type": "medium close-up smartphone selfie"
    },
    "bedroom_bed": {
        "outfit": "oversized comfortable heather-gray fleece crewneck sweater",
        "pose": "lying down on bed with head resting sideways on soft pillow",
        "environment": "messy cozy bedsheets, morning sunlight streaming through window",
        "lighting": "bright natural daylight with realistic shadows",
        "shot_type": "intimate high-angle bed selfie"
    },
    "standing_casual": {
        "outfit": "white delicate floral lace-trim tank top with high-waisted denim jeans",
        "pose": "standing naturally in doorway/hallway holding small black shoulder bag",
        "environment": "apartment hallway, clean natural interior perspective",
        "lighting": "neutral ambient indoor corridor light",
        "shot_type": "mid-body candid portrait showing slim athletic silhouette"
    },
    "evening_cafe": {
        "outfit": "black ribbed top with delicate silver necklace",
        "pose": "sitting at an outdoor wooden cafe table holding iced coffee",
        "environment": "warmly lit evening terrace garden cafe",
        "lighting": "warm bokeh fairy lights and ambient evening street lighting",
        "shot_type": "candid personal smartphone shot taken across table"
    }
}