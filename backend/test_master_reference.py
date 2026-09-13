import os
import sys
import urllib.parse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.append(os.getcwd())

STATIC_DIR = os.path.join(os.getcwd(), "app", "static", "references")
os.makedirs(STATIC_DIR, exist_ok=True)

def create_robust_session():
    """
    Creates a requests session with automatic retries and higher timeout config
    to prevent ReadTimeout errors on cloud rendering servers.
    """
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session

def generate_true_reference(prompt_context: str, filename: str):
    """
    Generates Aura's consistent reference using strict prompt tuning and robust session management.
    """
    session = create_robust_session()
    
    # Strict Identity-Locked Master Prompt maintaining Slavic-fusion features
    master_prompt = (
        f"candid smartphone front-camera selfie of the exact same 22yo Slavic-fusion woman, "
        f"fair porcelain skin, deep hazel-brown almond eyes, slim straight sharp nose, "
        f"thin attractive lips, dark layered hair, {prompt_context}, "
        f"natural bedroom background, phone camera grain, unedited real human photo"
    )
    
    negative_prompt = (
        "cartoon, anime, 3d render, painting, different person, altered face structure, "
        "plastic skin, blurry, low quality, watermark"
    )

    print(f"🚀 [AURA IDENTITY ENGINE] Generating: {filename}...")
    encoded_prompt = urllib.parse.quote(master_prompt)
    encoded_negative = urllib.parse.quote(negative_prompt)
    
    # Cloud FLUX endpoint with extended timeout (60 seconds)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=768&height=1024&model=flux&nologo=true&seed=1337&negative={encoded_negative}"
    
    try:
        response = session.get(image_url, timeout=60)
        if response.status_code == 200:
            file_path = os.path.join(STATIC_DIR, filename)
            with open(file_path, "wb") as f:
                f.write(response.content)
            print(f"✅ [SUCCESS] Master Reference Saved: {file_path}")
            return file_path
        else:
            print(f"❌ [FAILED] HTTP Status: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ [CONNECTION ERROR]: {e}")
        return None

if __name__ == "__main__":
    # Test 1: Tank Top (Matching Reference Identity)
    generate_true_reference(
        prompt_context="wearing a white ribbed tank top with lace trim, sitting on bed",
        filename="aura_master_tanktop.png"
    )

    # Test 2: Modern Saree Look (Keeping the exact same face)
    generate_true_reference(
        prompt_context="wearing an elegant modern chiffon saree with a minimalist sleeveless blouse",
        filename="aura_master_saree.png"
    )