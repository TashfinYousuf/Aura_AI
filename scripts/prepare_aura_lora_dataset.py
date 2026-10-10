# FILE: scripts/prepare_aura_lora_dataset.py
"""
Aura LoRA Dataset Preparer:
- Gathers Aura's curated aesthetic reference portraits from references and selfies folders.
- Filters out collages.
- Normalizes resolution to 512x512 (with smart face/aspect cropping).
- Automatically writes trigger-word captions (.txt) for each image:
  'a portrait of aura_woman, fair porcelain skin, deep hazel almond eyes, dark brown hair...'
- Outputs clean dataset ready for LoRA fine-tuning.
"""

import os
import shutil
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REF_DIR = PROJECT_ROOT / "backend" / "app" / "static" / "references"
SELFIES_DIR = PROJECT_ROOT / "backend" / "app" / "static" / "selfies"
OUTPUT_DIR = PROJECT_ROOT / "data" / "aura_lora_dataset"

TRIGGER_TAG = "aura_woman"

CAPTION_TEMPLATES = {
    "white": f"a candid photo of {TRIGGER_TAG}, fair porcelain skin, hazel almond eyes, wearing confident white top, natural lighting",
    "flower": f"a close-up portrait of {TRIGGER_TAG}, hazel almond eyes, gentle smile, holding flower, soft sunlight",
    "flying_kiss": f"a candid selfie of {TRIGGER_TAG} blowing a kiss, dark layered hair, hazel eyes, playful sweet expression",
    "front": f"a candid front-facing selfie of {TRIGGER_TAG}, flawless porcelain skin, deep hazel eyes, silky dark brown hair",
    "glamourous": f"a glamorous portrait of {TRIGGER_TAG}, elegant makeup, hazel almond eyes, dark silky hair, studio lighting",
    "silver": f"a photo of {TRIGGER_TAG} wearing a gorgeous silver outfit, fair skin, hazel eyes, elegant pose",
    "green": f"a modeling photo of {TRIGGER_TAG} in a stylish green outfit, hazel almond eyes, soft blush",
    "kiss": f"a sweet close-up selfie of {TRIGGER_TAG} sending a kiss, hazel eyes, natural skin texture",
    "off_shoulder": f"a portrait of {TRIGGER_TAG} wearing an off-shoulder top, dewy porcelain skin, hazel almond eyes",
    "red_velvet": f"a modeling portrait of {TRIGGER_TAG} in a red velvet outfit, deep hazel eyes, dark layered hair",
    "seducer": f"an alluring intimate portrait of {TRIGGER_TAG}, hazel almond eyes, soft lips, gentle blush, warm lighting",
    "seducing": f"an intimate bedroom selfie of {TRIGGER_TAG}, bare shoulders, hazel eyes, romantic lighting",
    "seductive": f"a sensual candid portrait of {TRIGGER_TAG}, soft alluring smile, deep hazel eyes, silky dark hair",
    "selfie": f"a candid smartphone selfie of {TRIGGER_TAG}, natural skin texture, hazel eyes, casual sweet expression",
    "sheer": f"an intimate sensual portrait of {TRIGGER_TAG} in sheer black lace negligee, hazel almond eyes",
    "side": f"a side profile portrait of {TRIGGER_TAG}, slim sharp nose, hazel eyes, dark layered hair",
    "bed": f"a cozy intimate selfie of {TRIGGER_TAG} relaxing in bed, bare shoulders, soft rumpled bedsheets, hazel eyes",
    "master": f"a master identity portrait of {TRIGGER_TAG}, fair porcelain skin, deep hazel almond eyes, slim sharp nose, dark hair"
}

def get_caption_for_filename(name: str) -> str:
    lower = name.lower()
    for key, cap in CAPTION_TEMPLATES.items():
        if key in lower:
            return cap
    return f"a candid portrait of {TRIGGER_TAG}, 22-year-old Slavic-fusion woman, fair porcelain skin, hazel almond eyes, dark brown layered silky hair"

def prepare_dataset():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Collect candidate files
    candidates = {}
    for d in [REF_DIR, SELFIES_DIR]:
        if d.exists():
            for f in d.glob("*.*"):
                if f.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    # Skip collages and multi-character sheets
                    if any(bad in f.name.lower() for bad in ["collage", "character_sheet"]):
                        continue
                    if f.name not in candidates:
                        candidates[f.name] = f

    print(f"📁 Found {len(candidates)} unique candidate portraits for Aura LoRA dataset.")

    count = 0
    for name, path in candidates.items():
        try:
            with Image.open(path) as img:
                rgb = img.convert("RGB")
                
                # Center crop to square and resize to 512x512
                w, h = rgb.size
                min_dim = min(w, h)
                left = (w - min_dim) // 2
                top = (h - min_dim) // 4  # bias slightly towards top for face framing
                right = left + min_dim
                bottom = top + min_dim
                
                # Boundary safety
                if bottom > h:
                    bottom = h
                    top = h - min_dim

                cropped = rgb.crop((left, top, right, bottom))
                resized = cropped.resize((512, 512), Image.Resampling.LANCZOS)
                
                out_img_name = f"aura_{count:03d}.jpg"
                out_txt_name = f"aura_{count:03d}.txt"
                
                resized.save(OUTPUT_DIR / out_img_name, "JPEG", quality=95)
                
                caption = get_caption_for_filename(name)
                with open(OUTPUT_DIR / out_txt_name, "w", encoding="utf-8") as f:
                    f.write(caption)
                
                count += 1
                print(f"  ✅ [{count:02d}] {name} -> {out_img_name} ({caption[:45]}...)")
        except Exception as e:
            print(f"  ⚠️ Error processing {name}: {e}")

    print(f"✨ Successfully generated {count} training pairs in {OUTPUT_DIR}")

if __name__ == "__main__":
    prepare_dataset()

