# FILE: backend/app/Aura/brain/model_router.py

import os
from enum import Enum
from typing import List, Dict, Any, Optional
from groq import Groq
from app.core.config import settings, models

class ExecutionTier(str, Enum):
    FAST = "FAST"
    REASONING = "REASONING"
    STRUCTURED = "STRUCTURED"
    ADULT = "ADULT"

class ModelRouter:
    @property
    def api_key(self) -> str:
        return (settings.GROQ_API_KEY or "").strip()

    def select_model(self, tier: ExecutionTier) -> str:
        if tier == ExecutionTier.ADULT:
            return models.SPECIALIZED_MODEL  # openai/gpt-oss-120b (passionate intimate roleplay)
        elif tier == ExecutionTier.REASONING:
            return models.SMART_MODEL
        elif tier == ExecutionTier.STRUCTURED:
            return models.STRUCTURED_MODEL
        return models.FAST_MODEL

    async def complete(
        self,
        messages: List[Dict[str, str]],
        tier: ExecutionTier = ExecutionTier.FAST,
        temperature: float = 0.55,
        max_tokens: int = 400,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY missing in runtime environment.")

        client = Groq(api_key=self.api_key)
        target_model = self.select_model(tier)

        sanitized_messages = []
        for msg in messages:
            raw_role = str(msg.get("role", "user")).lower()
            role = "assistant" if raw_role in ["ai", "bot", "assistant"] else raw_role
            if role not in ["system", "user", "assistant"]:
                role = "user"
            sanitized_messages.append({"role": role, "content": str(msg.get("content", ""))})

        # Try with response_format first if provided
        try:
            kwargs = {
                "model": target_model,
                "messages": sanitized_messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            if response_format:
                kwargs["response_format"] = response_format

            res = client.chat.completions.create(**kwargs)
            content = res.choices[0].message.content.strip()
            if content:
                return content
        except Exception as e:
            err_str = str(e).lower()
            # If Groq fails specifically with JSON format issue, retry without JSON constraint
            if "json" in err_str or "format" in err_str or "schema" in err_str:
                print(f"⚠️ [JSON FORMAT REJECTED BY GROQ]: Bypassing strict JSON format and retrying...")
                try:
                    res = client.chat.completions.create(
                        model=target_model,
                        messages=sanitized_messages,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                    return res.choices[0].message.content.strip()
                except Exception as inner_e:
                    print(f"⚠️ [RETRY FAILED]: {inner_e}")
            else:
                print(f"⚠️ [MODEL COMPLETION ERROR on {target_model}]: {e}")

        # Cascade fallback across configured Groq models
        for fallback_model in settings.FALLBACK_CHAT_MODELS:
            if fallback_model == target_model:
                continue
            try:
                res = client.chat.completions.create(
                    model=fallback_model,
                    messages=sanitized_messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return res.choices[0].message.content.strip()
            except Exception:
                continue

        # Secondary Sovereign Fallback: Google Gemini
        gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
        if gemini_key:
            try:
                from google import genai
                clean_key = gemini_key.split()[0].replace("export", "").strip()
                g_client = genai.Client(api_key=clean_key)
                prompt_lines = [f"{m['role'].upper()}: {m['content']}" for m in sanitized_messages]
                g_res = g_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents="\n".join(prompt_lines)
                )
                if g_res and g_res.text:
                    print("✨ [GEMINI FALLBACK SUCCESS]: Generated turn via Gemini 2.5 Flash.")
                    return g_res.text.strip()
            except Exception as g_err:
                print(f"⚠️ [GEMINI SECONDARY FALLBACK ERROR]: {g_err}")

        return "হেই, শুনতে পাচ্ছো? নেটের গ্লিচে মেসেজটা মিস হয়ে গেছে... আবার বলো তো?"

model_router = ModelRouter()