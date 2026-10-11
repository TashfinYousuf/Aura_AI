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
        sanitized_messages = []
        for msg in messages:
            raw_role = str(msg.get("role", "user")).lower()
            role = "assistant" if raw_role in ["ai", "bot", "assistant"] else raw_role
            if role not in ["system", "user", "assistant"]:
                role = "user"
            sanitized_messages.append({"role": role, "content": str(msg.get("content", ""))})

        # -------------------------------------------------------------
        # 1. PRIMARY SOVEREIGN ENGINE: GOOGLE GEMINI (ChatGPT/Gemini Grade)
        # Bypassed for Adult/Intimate tier to avoid Google cloud moralizing disclaimers
        # -------------------------------------------------------------
        gemini_key = (settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")).strip()
        if gemini_key and tier != ExecutionTier.ADULT:
            clean_key = gemini_key.split()[0].replace("export", "").strip()
            if len(clean_key) >= 15:
                try:
                    from google import genai
                    from google.genai import types

                    g_client = genai.Client(api_key=clean_key)

                    # Extract system instruction & construct chat turns
                    system_content = ""
                    chat_turns = []
                    for m in sanitized_messages:
                        if m["role"] == "system":
                            system_content = m["content"]
                        else:
                            role_tag = "user" if m["role"] == "user" else "model"
                            chat_turns.append(types.Content(
                                role=role_tag,
                                parts=[types.Part.from_text(text=m["content"])]
                            ))

                    if not chat_turns:
                        chat_turns = [types.Content(role="user", parts=[types.Part.from_text(text="Hi")])]

                    # Allocate sufficient token budget so Gemini's internal thinking doesn't truncate text
                    gemini_token_limit = max(max_tokens, 1000)

                    config = types.GenerateContentConfig(
                        system_instruction=system_content if system_content else None,
                        temperature=temperature,
                        max_output_tokens=gemini_token_limit,
                        safety_settings=[
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HARASSMENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                            types.SafetySetting(category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=types.HarmBlockThreshold.BLOCK_NONE),
                        ]
                    )

                    # Cascade across supported Gemini models
                    gemini_candidates = [
                        "gemini-2.5-flash",
                        "gemini-3.5-flash",
                        "gemini-2.5-flash-lite",
                        "gemini-3.8-flash",
                        "gemini-flash-lite-latest"
                    ]

                    for g_candidate in gemini_candidates:
                        try:
                            g_res = g_client.models.generate_content(
                                model=g_candidate,
                                contents=chat_turns,
                                config=config
                            )
                            if g_res and g_res.text:
                                content = g_res.text.strip()
                                if content:
                                    print(f"✨ [GEMINI SOVEREIGN SUCCESS]: Generated turn via {g_candidate}.")
                                    return content
                        except Exception as g_err:
                            err_txt = str(g_err).lower()
                            if "nodename nor servname" in err_txt or "gaierror" in err_txt or "no route to host" in err_txt:
                                break
                            if any(code in err_txt for code in ["429", "503", "404", "unavailable", "quota", "resource_exhausted"]):
                                continue
                            print(f"⚠️ [GEMINI ATTEMPT FAILED on {g_candidate}]: {g_err}")
                except Exception as g_init_err:
                    print(f"⚠️ [GEMINI ENGINE INITIALIZATION ERROR]: {g_init_err}")

        # -------------------------------------------------------------
        # 2. SECONDARY FALLBACK ENGINE: GROQ
        # -------------------------------------------------------------
        if self.api_key:
            try:
                client = Groq(api_key=self.api_key)
                target_model = self.select_model(tier)

                kwargs = {
                    "model": target_model,
                    "messages": sanitized_messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                if response_format:
                    kwargs["response_format"] = response_format

                try:
                    res = client.chat.completions.create(**kwargs)
                    choice = res.choices[0]
                    content = (choice.message.content or "").strip()
                    if not content and hasattr(choice.message, "reasoning") and choice.message.reasoning:
                        content = choice.message.reasoning.strip()
                    if content:
                        print(f"✨ [GROQ FALLBACK SUCCESS]: Generated turn via {target_model}.")
                        return content
                except Exception as e:
                    err_str = str(e).lower()
                    if "json" in err_str or "format" in err_str or "schema" in err_str:
                        res = client.chat.completions.create(
                            model=target_model,
                            messages=sanitized_messages,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                        choice = res.choices[0]
                        content = (choice.message.content or "").strip()
                        if content:
                            return content
                    else:
                        print(f"⚠️ [GROQ ERROR on {target_model}]: {e}")

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
                        choice = res.choices[0]
                        content = (choice.message.content or "").strip()
                        if not content and hasattr(choice.message, "reasoning") and choice.message.reasoning:
                            content = choice.message.reasoning.strip()
                        if content:
                            print(f"✨ [GROQ FALLBACK SUCCESS]: Generated turn via {fallback_model}.")
                            return content
                    except Exception:
                        continue
            except Exception as groq_err:
                print(f"⚠️ [GROQ ENGINE ERROR]: {groq_err}")

        return "হেই, শুনতে পাচ্ছো? নেটের গ্লিচে মেসেজটা মিস হয়ে গেছে... আবার বলো তো?"

model_router = ModelRouter()