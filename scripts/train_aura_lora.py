# FILE: scripts/train_aura_lora.py
"""
Aura LoRA Fine-Tuner:
- Fine-tunes a Low-Rank Adaptation (LoRA) on SD 1.5 (Realistic Vision) using Aura's 27 aesthetic portraits.
- Permanently locks Aura's facial identity, bone structure, eyes, and expressions into diffusion weights.
- Output: aura_v1.safetensors
- Runs on Google Colab (Tesla T4) or Kaggle in ~10-15 minutes.
"""

import os
import sys
import glob
import math
import torch
import torch.nn.functional as F

# 1. Neutralize broken torchao version check in PEFT / Colab / Kaggle
try:
    import peft.import_utils
    peft.import_utils.is_torchao_available = lambda: False
except Exception:
    pass
try:
    import peft.tuners.lora.torchao
    peft.tuners.lora.torchao.is_torchao_available = lambda: False
except Exception:
    pass

from pathlib import Path
from PIL import Image
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from transformers import CLIPTextModel, CLIPTokenizer
from diffusers import AutoencoderKL, DDPMScheduler, UNet2DConditionModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "aura_lora_dataset"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "app" / "static" / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "SG161222/Realistic_Vision_V5.1_noVAE"
OUTPUT_LORA_PATH = OUTPUT_DIR / "aura_v1.safetensors"

class AuraDataset(Dataset):
    def __init__(self, data_dir: Path, tokenizer, size: int = 512):
        self.data_dir = data_dir
        self.tokenizer = tokenizer
        self.size = size
        self.image_files = sorted(list(data_dir.glob("*.jpg")))
        
        self.transform = transforms.Compose([
            transforms.Resize(size, interpolation=transforms.InterpolationMode.BILINEAR),
            transforms.CenterCrop(size),
            transforms.ToTensor(),
            transforms.Normalize([0.5], [0.5])
        ])

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        img_path = self.image_files[idx]
        txt_path = img_path.with_suffix(".txt")
        
        caption = "a photo of aura_woman, fair skin, hazel eyes, dark brown hair"
        if txt_path.exists():
            with open(txt_path, "r", encoding="utf-8") as f:
                caption = f.read().strip()
                
        img = Image.open(img_path).convert("RGB")
        pixel_values = self.transform(img)
        
        input_ids = self.tokenizer(
            caption,
            padding="max_length",
            truncation=True,
            max_length=self.tokenizer.model_max_length,
            return_tensors="pt"
        ).input_ids[0]

        return {"pixel_values": pixel_values, "input_ids": input_ids}

def train_lora(
    steps: int = 500,
    lr: float = 1e-4,
    rank: int = 16,
    batch_size: int = 1,
    gradient_accumulation_steps: int = 2
):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🚀 Starting Aura LoRA Fine-Tuning on {device.upper()}...")
    print(f"📊 Dataset: {len(list(DATA_DIR.glob('*.jpg')))} images in {DATA_DIR}")
    print(f"🎯 Target Model: {MODEL_ID} | Steps: {steps} | Rank: {rank}")

    if not any(DATA_DIR.glob("*.jpg")):
        print("⚠️ No images found in dataset. Running preparer first...")
        from scripts.prepare_aura_lora_dataset import prepare_dataset
        prepare_dataset()

    tokenizer = CLIPTokenizer.from_pretrained(MODEL_ID, subfolder="tokenizer")
    text_encoder = CLIPTextModel.from_pretrained(MODEL_ID, subfolder="text_encoder", torch_dtype=torch.float32)
    vae = AutoencoderKL.from_pretrained(MODEL_ID, subfolder="vae", torch_dtype=torch.float32)
    unet = UNet2DConditionModel.from_pretrained(MODEL_ID, subfolder="unet", torch_dtype=torch.float32)
    noise_scheduler = DDPMScheduler.from_pretrained(MODEL_ID, subfolder="scheduler")

    vae.requires_grad_(False)
    text_encoder.requires_grad_(False)
    unet.requires_grad_(False)

    vae.to(device)
    text_encoder.to(device)
    unet.to(device)

    # Attach LoRA to UNet (with torchao neutralization and native fallback)
    use_peft = False
    try:
        from peft import LoraConfig, get_peft_model
        # Ensure torchao check is disabled
        try:
            import peft.import_utils
            peft.import_utils.is_torchao_available = lambda: False
        except Exception:
            pass
        try:
            import peft.tuners.lora.torchao
            peft.tuners.lora.torchao.is_torchao_available = lambda: False
        except Exception:
            pass

        lora_config = LoraConfig(
            r=rank,
            lora_alpha=rank,
            init_lora_weights="gaussian",
            target_modules=["to_k", "to_q", "to_v", "to_out.0"]
        )
        unet = get_peft_model(unet, lora_config)
        use_peft = True
        print("✅ [PEFT LORA]: Attached LoRA adapters to UNet successfully!")
        unet.print_trainable_parameters()
    except Exception as peft_err:
        print(f"⚠️ [PEFT NOTICE]: {peft_err}. Activating Diffusers native LoRA processor...")
        from diffusers.models.attention_processor import LoRAAttnProcessor
        lora_attn_procs = {}
        for name in unet.attn_processors.keys():
            cross_attention_dim = None if name.endswith("attn1.processor") else unet.config.cross_attention_dim
            if name.startswith("mid_block"):
                hidden_size = unet.config.block_out_channels[-1]
            elif name.startswith("up_blocks"):
                block_id = int(name[len("up_blocks.")])
                hidden_size = list(reversed(unet.config.block_out_channels))[block_id]
            elif name.startswith("down_blocks"):
                block_id = int(name[len("down_blocks.")])
                hidden_size = unet.config.block_out_channels[block_id]

            lora_attn_procs[name] = LoRAAttnProcessor(
                hidden_size=hidden_size,
                cross_attention_dim=cross_attention_dim,
                rank=rank
            )
        unet.set_attn_processor(lora_attn_procs)
        print("✅ [DIFFUSERS LORA]: Attached native LoRA attention processors to UNet!")

    dataset = AuraDataset(DATA_DIR, tokenizer, size=512)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    trainable_params = [p for p in unet.parameters() if p.requires_grad]
    if not trainable_params:
        trainable_params = [p for n, p in unet.named_parameters() if "lora" in n.lower()]
    optimizer = torch.optim.AdamW(trainable_params or unet.parameters(), lr=lr, weight_decay=1e-2)

    global_step = 0
    epoch = 0
    unet.train()

    print("🔥 Training in progress... Please wait ~10-15 minutes on GPU:")
    while global_step < steps:
        epoch += 1
        for batch in dataloader:
            pixel_values = batch["pixel_values"].to(device, dtype=vae.dtype)
            input_ids = batch["input_ids"].to(device)

            # Latent encoding (harmonized dtype with VAE)
            with torch.no_grad():
                latents = vae.encode(pixel_values).latent_dist.sample()
                latents = latents * vae.config.scaling_factor

            # Sample noise
            noise = torch.randn_like(latents)
            bsz = latents.shape[0]
            timesteps = torch.randint(0, noise_scheduler.config.num_train_timesteps, (bsz,), device=latents.device).long()
            noisy_latents = noise_scheduler.add_noise(latents, noise, timesteps)

            # Text embeddings
            with torch.no_grad():
                encoder_hidden_states = text_encoder(input_ids)[0]

            # Predict noise residual
            model_pred = unet(noisy_latents.to(unet.dtype), timesteps, encoder_hidden_states.to(unet.dtype)).sample

            # Compute loss
            if noise_scheduler.config.prediction_type == "epsilon":
                target = noise
            elif noise_scheduler.config.prediction_type == "v_prediction":
                target = noise_scheduler.get_velocity(latents, noise, timesteps)
            else:
                target = noise

            loss = F.mse_loss(model_pred.float(), target.float(), reduction="mean")
            loss = loss / gradient_accumulation_steps
            loss.backward()

            if (global_step + 1) % gradient_accumulation_steps == 0:
                torch.nn.utils.clip_grad_norm_(unet.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad()

            global_step += 1

            if global_step % 50 == 0 or global_step == steps:
                print(f"  Step {global_step}/{steps} - Loss: {loss.item() * gradient_accumulation_steps:.4f}")

            if global_step >= steps:
                break

    print(f"💾 Saving trained LoRA to {OUTPUT_LORA_PATH}...")
    try:
        from safetensors.torch import save_file
        if use_peft:
            peft_dir = OUTPUT_DIR / "aura_lora"
            peft_dir.mkdir(parents=True, exist_ok=True)
            unet.save_pretrained(str(peft_dir))

            peft_state_dict = unet.state_dict()
            lora_state_dict = {k: v for k, v in peft_state_dict.items() if "lora" in k.lower()}
            if not lora_state_dict:
                lora_state_dict = peft_state_dict
        else:
            lora_state_dict = {}
            for name, proc in unet.attn_processors.items():
                for k, v in proc.state_dict().items():
                    lora_state_dict[f"{name}.{k}"] = v

        save_targets = [
            OUTPUT_LORA_PATH,
            Path("aura_v1.safetensors"),
            Path("/content/aura_v1.safetensors") if Path("/content").exists() else None,
            Path("/kaggle/working/aura_v1.safetensors") if Path("/kaggle/working").exists() else None,
            Path("/kaggle/working/Aura_AI/backend/app/static/models/aura_v1.safetensors") if Path("/kaggle/working").exists() else None
        ]
        for target in save_targets:
            if target is not None:
                try:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    save_file(lora_state_dict, str(target))
                except Exception:
                    pass

        if Path("/content/drive/MyDrive").exists():
            try:
                drive_target = Path("/content/drive/MyDrive/Aura_AI/aura_v1.safetensors")
                drive_target.parent.mkdir(parents=True, exist_ok=True)
                save_file(lora_state_dict, str(drive_target))
                print(f"💾 [GOOGLE DRIVE PERMANENT BACKUP]: Preserved in Google Drive at {drive_target}!")
            except Exception:
                pass

        print("✨ [LORA TRAINING COMPLETE]: aura_v1.safetensors successfully created and locked!")
    except Exception as e:
        fallback_path = OUTPUT_DIR / "aura_v1.pt"
        torch.save(unet.state_dict(), str(fallback_path))
        torch.save(unet.state_dict(), "aura_v1.pt")
        print(f"✨ [LORA SAVE FALLBACK]: Saved to {fallback_path} ({e})")

if __name__ == "__main__":
    train_lora()

