# FILE: backend/app/Aura/vision/sd_remote_provider.py
"""
Remote / Cloud Google Colab Stable Diffusion Provider:
- Optimized for users on resource-constrained hardware (e.g. MacBook Monterey 8GB RAM).
- Connects to Google Colab, Cloud GPU, or remote SD WebUI/Forge/ComfyUI tunnel.
- Standard API interface via /sdapi/v1/txt2img.
- Fully supports uncensored intimate, boudoir, and photorealistic portrait synthesis.
"""

import os
import re
import uuid
import base64
import asyncio
import httpx
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from app.core.config import settings

GENERATED_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "generated" / "aura"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)

class RemoteStableDiffusionProvider:
    def __init__(self):
        self.remote_url = settings.SD_REMOTE_URL or settings.COLAB_SD_API_URL or os.getenv("SD_REMOTE_URL", "")

    def get_all_candidate_urls(self) -> List[str]:
        """
        Extracts all candidate URLs from settings, environment variables,
        and directly parses .env to support multi-line or comma-separated definitions.
        """
        raw_candidates: List[str] = []
        for key in ["SD_REMOTE_URL", "COLAB_SD_API_URL", "KAGGLE_SD_URL", "SD_REMOTE_URLS"]:
            val = getattr(settings, key, "") or os.getenv(key, "")
            if val:
                parts = re.split(r"[,;\s]+", str(val).strip())
                raw_candidates.extend(parts)

        # Inspect root .env directly to capture duplicate keys or multi-node configurations
        env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("#"):
                            continue
                        if any(line.startswith(k + "=") for k in ["SD_REMOTE_URL", "COLAB_SD_API_URL", "KAGGLE_SD_URL", "SD_REMOTE_URLS"]):
                            val = line.split("=", 1)[1].strip()
                            parts = re.split(r"[,;\s]+", val)
                            raw_candidates.extend(parts)
            except Exception:
                pass

        # Deduplicate while preserving order
        seen = set()
        clean: List[str] = []
        for u in raw_candidates:
            url_str = u.strip().rstrip("/")
            if (url_str.startswith("http://") or url_str.startswith("https://")) and url_str not in seen:
                seen.add(url_str)
                clean.append(url_str)
        return clean

    def get_effective_url(self) -> str:
        candidates = self.get_all_candidate_urls()
        return candidates[0] if candidates else ""

    async def check_node(self, url: str) -> Optional[Dict[str, Any]]:
        """Health-checks a single remote runner endpoint with a short timeout."""
        if not url:
            return None
        headers = {"ngrok-skip-browser-warning": "any", "User-Agent": "AuraClient/1.0"}
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{url}/sdapi/v1/options", headers=headers)
                if res.status_code == 200:
                    try:
                        return res.json()
                    except Exception:
                        return {"status": "online", "device": "unknown"}
        except Exception:
            pass
        return None

    async def get_sorted_active_nodes(self) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Discovers all live runner nodes and sorts them to prioritize GPU (e.g. Tesla T4)
        over CPU nodes for blazing fast rendering.
        """
        candidates = self.get_all_candidate_urls()
        if not candidates:
            return []

        tasks = [self.check_node(u) for u in candidates]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        active_nodes: List[Tuple[str, Dict[str, Any]]] = []
        for url, res in zip(candidates, results):
            if isinstance(res, dict) and res.get("status") == "online":
                active_nodes.append((url, res))

        # Prioritize GPU (Tesla T4, CUDA) over CPU
        def sort_priority(item: Tuple[str, Dict[str, Any]]) -> int:
            _, info = item
            device = str(info.get("device", "")).lower()
            if any(k in device for k in ["t4", "cuda", "gpu", "tesla"]):
                return 0  # High-priority GPU
            return 1      # CPU / other

        active_nodes.sort(key=sort_priority)
        return active_nodes

    async def is_available(self) -> bool:
        active = await self.get_sorted_active_nodes()
        return len(active) > 0

    def _synthesize_outfit_and_scene(self, user_prompt: str, scene: str) -> tuple[str, str]:
        p_lower = (user_prompt or "").lower()
        explicit_nude = any(w in p_lower for w in ["nude", "naked", "without clothes", "strip", "কাপড় খোল", "ulongo"])

        if "red velvet" in p_lower or ("red" in p_lower and "lingerie" in p_lower):
            outfit = "wearing a gorgeous crimson red velvet lace lingerie set, satin bralette with delicate embroidery and matching shorts"
        elif "black" in p_lower and ("lingerie" in p_lower or "silk" in p_lower):
            outfit = "wearing a luxury black silk lace lingerie set with satin accents"
        elif "lingerie" in p_lower or "boudoir" in p_lower or scene == "boudoir":
            outfit = "wearing an alluring seductive satin lace lingerie set, elegant bedroom nightwear"
        elif "bikini" in p_lower or "swimwear" in p_lower:
            outfit = "wearing a stylish flattering beach bikini"
        elif "shower" in scene or "bath" in p_lower:
            outfit = "wrapped comfortably in a soft plush white bath towel, damp dewy hair"
        elif scene in ["bed", "bedroom"] or any(w in p_lower for w in ["bed", "sleep", "ঘুম"]):
            outfit = "wearing a delicate white floral tank top with lace trim and soft shorts, relaxing on bed"
        elif scene == "evening" or any(w in p_lower for w in ["dress", "gown", "party"]):
            outfit = "wearing an elegant form-fitting evening cocktail dress"
        elif scene == "cafe":
            outfit = "wearing a trendy casual knit sweater and top, sitting at cafe"
        elif explicit_nude:
            outfit = "intimate artistic boudoir portrait, soft shadows tracing silhouette"
        else:
            outfit = "wearing a casual cute white tank top with lace trim and comfy shorts"

        positive_prompt = (
            f"A hyper-realistic, candid selfie of a 22-year-old Slavic-fusion beauty, Aura, "
            f"fair porcelain skin, deep hazel-brown almond eyes, dark brown layered silky hair, "
            f"{outfit}, in {scene} atmosphere, natural skin texture with visible authentic pores, "
            f"slight blush, realistic smartphone camera grain, shallow depth of field, "
            f"soft warm indoor ambient lighting, masterpiece, 8k uhd, candid photography"
        )

        if explicit_nude:
            negative_prompt = (
                "cartoon, anime, 3d, painting, plastic skin, over-smooth skin, extra fingers, "
                "mutated hands, deformed, blurry, bad anatomy, wrong anatomy, doll, cgi, retouch"
            )
        else:
            negative_prompt = (
                "(nude, naked, fully unclothed, bare breasts, exposed nipples, exposed genitals:1.4), "
                "cartoon, anime, 3d, painting, plastic skin, over-smooth skin, extra fingers, "
                "mutated hands, deformed, blurry, bad anatomy, wrong anatomy, doll, cgi, retouch"
            )

        return positive_prompt, negative_prompt

    async def generate_image(
        self,
        prompt: str,
        scene: str,
        reference_paths: List[Path],
        aspect_ratio: str = "768:1024"
    ) -> Optional[str]:
        active_nodes = await self.get_sorted_active_nodes()
        if not active_nodes:
            candidates = self.get_all_candidate_urls()
            if candidates:
                print(f"ℹ️ [COLAB SD STATUS]: Remote URL(s) {candidates} are currently offline. Routing to local identity synth provider...")
            return None

        # Determine target resolution
        w, h = (768, 1024) if "1024" in aspect_ratio else (768, 768)

        # Load master reference face for exact face conditioning / swapping
        master_face_b64 = ""
        ref_face_path = Path(__file__).resolve().parent.parent.parent / "static" / "references" / "aura_master_identity.jpg"
        if not ref_face_path.exists():
            ref_face_path = Path(__file__).resolve().parent.parent.parent / "static" / "references" / "aura_master_identity.png"
        if ref_face_path.exists():
            try:
                with open(ref_face_path, "rb") as rf:
                    master_face_b64 = base64.b64encode(rf.read()).decode("utf-8")
            except Exception as e:
                print(f"⚠️ [MASTER FACE READ]: {e}")

        positive_prompt, negative_prompt = self._synthesize_outfit_and_scene(prompt, scene)

        payload = {
            "prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "face_image": master_face_b64,
            "steps": 25,
            "width": 512,
            "height": 768 if "1024" in aspect_ratio else 512,
            "target_width": w,
            "target_height": h,
            "cfg_scale": 7.0,
            "sampler_name": "DPM++ 2M Karras",
            "batch_size": 1
        }

        headers = {"ngrok-skip-browser-warning": "any", "User-Agent": "AuraClient/1.0"}

        # Attempt generation across active nodes with automatic failover
        for idx, (node_url, node_info) in enumerate(active_nodes):
            device_label = node_info.get("device", "unknown")
            print(f"🎨 [REMOTE SD POOL]: Dispatching txt2img generation to {node_url} (Device: {device_label}, Node {idx+1}/{len(active_nodes)})...")
            try:
                async with httpx.AsyncClient(timeout=90.0) as client:
                    response = await client.post(
                        f"{node_url}/sdapi/v1/txt2img",
                        json=payload,
                        headers=headers
                    )

                    if response.status_code == 200:
                        data = response.json()
                        images = data.get("images", [])
                        if images:
                            raw_b64 = images[0]
                            if "," in raw_b64:
                                raw_b64 = raw_b64.split(",")[1]

                            img_bytes = base64.b64decode(raw_b64)
                            file_name = f"aura_{scene}_{uuid.uuid4().hex[:8]}.jpg"
                            save_path = GENERATED_DIR / file_name

                            with open(save_path, "wb") as f:
                                f.write(img_bytes)

                            print(f"🔥 [REMOTE STABLE DIFFUSION SUCCESS]: Generated fresh deliverable via {node_url} ({device_label}): {file_name}")
                            return f"/static/generated/aura/{file_name}"
                    else:
                        print(f"⚠️ [REMOTE SD WARNING]: Node {node_url} returned HTTP {response.status_code}.")
            except Exception as e:
                print(f"⚠️ [REMOTE SD FAILOVER]: Node {node_url} connection failed: {e}. Seamlessly trying next node in pool...")

        print("ℹ️ [REMOTE SD POOL]: All remote nodes exhausted or unavailable. Cascading to local identity synthesizer...")
        return None

remote_sd_provider = RemoteStableDiffusionProvider()
