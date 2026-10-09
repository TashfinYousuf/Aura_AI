# FILE: backend/app/core/security.py

import os
from typing import Optional
from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import firebase_admin
from firebase_admin import auth, credentials
from app.core.config import settings

# Initialize Firebase Admin SDK safely
if not firebase_admin._apps:
    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    else:
        # Fallback to default project credentials
        try:
            firebase_admin.initialize_app(options={"projectId": settings.FIREBASE_PROJECT_ID})
        except Exception as e:
            print(f"⚠️ [FIREBASE ADMIN INIT WARNING]: {e}")

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user_id(cred: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> str:
    """
    Validates Firebase Bearer Token on HTTP requests.
    Returns the authentic verified UID.
    """
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Bearer Header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = cred.credentials
    try:
        decoded = auth.verify_id_token(token)
        return decoded["uid"]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or Expired Firebase Token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

def verify_ws_token(token: Optional[str]) -> Optional[str]:
    """
    Validates token during WebSocket handshake.
    """
    if not token:
        return None
    try:
        decoded = auth.verify_id_token(token)
        return decoded.get("uid")
    except Exception:
        return None