# FILE: backend/app/Aura/generation/identity_qa.py

import io
import base64
from typing import Tuple, Optional
from PIL import Image

class IdentityQAEngine:
    """
    In-memory Quality Assurance & Structural Consistency Validator.
    Zero disk touching; audits raw bytes directly in RAM.
    """

    @staticmethod
    def audit_image_buffer(image_bytes: bytes) -> Tuple[bool, str]:
        if not image_bytes or len(image_bytes) < 18000:
            return False, "REJECTED_CORRUPTED_OR_EMPTY_BUFFER"

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                width, height = img.size
                
                # Minimum resolution barrier for high-fidelity rendering
                if width < 512 or height < 512:
                    return False, f"REJECTED_LOW_RESOLUTION_{width}x{height}"

                if img.format not in ["JPEG", "PNG", "WEBP"]:
                    return False, f"REJECTED_UNSUPPORTED_FORMAT_{img.format}"

                # Vertical or balanced portrait ratio mandatory for smartphone selfies
                aspect_ratio = height / width
                if aspect_ratio < 0.75:
                    return False, f"REJECTED_UNNATURAL_HORIZONTAL_ASPECT_RATIO_{aspect_ratio:.2f}"

            return True, "PASSED_QA"
        except Exception as e:
            return False, f"REJECTED_DECODE_EXCEPTION_{str(e)}"

    @staticmethod
    def verify_data_uri_payload(data_uri: str) -> bool:
        if not data_uri.startswith("data:image/"):
            return False
        try:
            raw_bytes = base64.b64decode(data_uri.split(",")[1])
            passed, _ = IdentityQAEngine.audit_image_buffer(raw_bytes)
            return passed
        except Exception:
            return False