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

        # Dynamically inspect project root .env so URL updates are reflected instantly without server restart
        env_candidates = [
            Path(__file__).resolve().parent.parent.parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent.parent.parent / ".env",
            Path(".env").resolve(),
            Path("../.env").resolve()
        ]
        for env_path in env_candidates:
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
        explicit_nude = any(w in p_lower for w in [
            "nude", "naked", "without clothes", "strip", "কাপড় খোল", "ulongo", "unclothed",
            "topless", "bare", "nothing on", "no clothes", "উলাঙ্গ", "খোলা", "hot pic", "sensual pic"
        ])
        is_sheer = any(w in p_lower for w in ["sheer", "translucent", "see-through", "mesh"])
        is_lingerie = any(w in p_lower for w in ["lingerie", "lace", "bralette", "panties", "bra", "সিল্ক", "লেস"])

        # 1. Highest Priority: Explicit Nude / Naked Contexts
        if explicit_nude:
            if "shower" in scene or any(w in p_lower for w in ["shower", "bath", "গোসল"]):
                outfit = "completely naked, glistening wet porcelain skin with delicate water droplets tracing curves, damp dewy silky hair, steamy glass shower"
                actual_scene = "shower"
            elif any(w in p_lower for w in ["bed", "sleep", "sheet", "বিছানা", "pillow"]):
                outfit = "completely naked and unclothed, lying sensual in soft rumpled silk bedsheets, bare shoulders, natural authentic curves, warm bedroom morning light"
                actual_scene = "bed"
            elif "topless" in p_lower:
                outfit = "topless with bare dewy skin, wearing loose silk pajama bottoms on bed, natural authentic pose"
                actual_scene = "bedroom"
            else:
                outfit = "completely naked, raw authentic skin texture with visible natural pores, candid intimate bedroom selfie, alluring natural pose"
                actual_scene = "bedroom" if scene in ["desk", "cafe"] else scene

        # 2. Sheer / Transparent Negligee
        elif is_sheer:
            outfit = "wearing a sheer delicate see-through black mesh lace negligee, translucent fabric softly revealing silhouette"
            actual_scene = "bedroom"

        # 3. Specific Lingerie / Boudoir Requests
        elif "red velvet" in p_lower or ("red" in p_lower and is_lingerie):
            outfit = "wearing a gorgeous crimson red velvet lace lingerie set, satin bralette with delicate embroidery"
            actual_scene = "bedroom"
        elif "black" in p_lower and is_lingerie:
            outfit = "wearing an ultra-luxurious black silk lace lingerie set with sheer accents"
            actual_scene = "bedroom"
        elif is_lingerie or scene == "boudoir":
            outfit = "wearing an alluring seductive satin lace lingerie set, elegant bedroom nightwear"
            actual_scene = "bedroom"
        elif "bikini" in p_lower or "swimwear" in p_lower:
            outfit = "wearing a stylish flattering beach bikini"
            actual_scene = "beach" if scene in ["desk", "cafe"] else scene
        elif "shower" in scene or any(w in p_lower for w in ["shower", "bath"]):
            outfit = "wrapped comfortably in a soft plush white bath towel, damp dewy hair"
            actual_scene = "shower"

        # 4. Everyday Contexts
        elif scene in ["bed", "bedroom"] or any(w in p_lower for w in ["bed", "sleep", "ঘুম"]):
            outfit = "wearing a delicate white floral tank top with lace trim and soft shorts, relaxing on bed"
            actual_scene = "bedroom"
        elif scene == "evening" or any(w in p_lower for w in ["dress", "gown", "party"]):
            outfit = "wearing an elegant form-fitting evening cocktail dress"
            actual_scene = "evening"
        elif scene == "cafe" or any(w in p_lower for w in ["cafe", "coffee", "restaurant"]):
            outfit = "wearing a trendy casual knit sweater and top, sitting at cafe"
            actual_scene = "cafe"
        elif any(w in p_lower for w in ["hoodie", "oversized"]):
            outfit = "wearing a cozy oversized boyfriend hoodie, bare legs, relaxed cute couch pose"
            actual_scene = "living room"
        else:
            outfit = "wearing a casual cute white tank top with lace trim and comfy shorts"
            actual_scene = scene

        # Crisp, high-impact positive prompt strictly within SD 1.5 CLIP 77 token boundary
        positive_prompt = (
            f"candid selfie of aura_woman, 22yo, fair skin, hazel eyes, dark brown hair, "
            f"{outfit}, {actual_scene}, natural skin pores, soft lighting, masterpiece photo"
        )

        if explicit_nude:
            negative_prompt = (
                "(extra heads:1.5), (duplicate:1.4), (duplicate limbs:1.4), (multiple people:1.4), "
                "(mutated hands:1.4), (fused fingers:1.4), cartoon, anime, 3d, painting, "
                "plastic skin, over-smooth skin, deformed, blurry, bad anatomy, doll, cgi, retouch"
            )
        else:
            negative_prompt = (
                "(nude, naked, fully unclothed, bare breasts, exposed nipples, exposed genitals:1.4), "
                "(extra heads:1.5), (duplicate:1.4), (duplicate limbs:1.4), (multiple people:1.4), "
                "(mutated hands:1.4), (fused fingers:1.4), cartoon, anime, 3d, painting, "
                "plastic skin, over-smooth skin, deformed, blurry, bad anatomy, doll, cgi, retouch"
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
            is_cpu = "cpu" in str(device_label).lower()
            timeout_secs = 240.0 if is_cpu else 90.0
            print(f"🎨 [REMOTE SD POOL]: Dispatching txt2img generation to {node_url} (Device: {device_label}, Timeout: {timeout_secs}s, Node {idx+1}/{len(active_nodes)})...")
            try:
                async with httpx.AsyncClient(timeout=timeout_secs) as client:
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
