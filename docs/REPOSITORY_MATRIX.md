# 📊 Aura Codebase Inventory & Classification Matrix

> **Source**: Forensic Audit of 50+ Backend & Frontend Files  
> **Classification Framework**: KEEP / MERGE / REWRITE / DELETE

---

## 1. Core & Architecture

| File Path | Classification | Responsibility | Target State / Action |
|---|---|---|---|
| `backend/app/main.py` | **KEEP / REWRITE** | FastAPI App, Lifespan, Static Mounts, Persistence Routes | Keep clean; ensure static files are anchored via `Path(__file__)`; CORS allowlist strict. |
| `backend/app/core/config.py` | **KEEP** | Central Settings & ModelRegistry | Single source of truth for Groq models (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `qwen/qwen3.8-27b`). |
| `backend/app/core/prompts.py` | **KEEP** | Core Few-Shot Personas & Scenarios | Preserved with positive communication principles. |
| `backend/app/core/security.py` | **REWRITE** | Firebase Token Verification | Implement `verify_firebase_token` dependency for user scoping. |
| `backend/app/core/unified_state.py` | **MERGE** | Compatibility State Adapters | Re-export from `Aura/brain/state_engine.py`. |
| `backend/app/core/character_dna.py` | **KEEP** | Character specifications | Preserved as canon configuration. |
| `backend/app/core/identity_pack.py` | **KEEP** | Reference image packaging | Used by visual engine. |

---

## 2. Aura Brain (`Aura/brain/`)

| File Path | Classification | Responsibility | Target State / Action |
|---|---|---|---|
| `Aura/brain/cognitive_pipeline.py` | **KEEP / CANONICAL** | Central Cognitive Turn Orchestrator | Canonical turn processor; dispatches intent, actions (`generate_image`), language, and replies. |
| `Aura/brain/model_router.py` | **KEEP / CANONICAL** | 3-Tier Dynamic Model Dispatcher | Fast/Structured/Reasoning tier dispatcher; handles JSON retries. |
| `Aura/brain/state_engine.py` | **KEEP / CANONICAL** | Cognitive State (`AuraState`) | Evaluates mood, warmth, energy context dynamically. |
| `Aura/brain/conversation_realizer.py`| **KEEP / CANONICAL** | Anti-Cringe & Refusal Sanitizer | Intercepts AI refusal markers, strips tags, mirrors Bengali/English. |
| `Aura/brain/frontier_router.py` | **MERGE / COMPAT** | Legacy Fallback Chat Handler | Bridges old calls to `conversation_realizer` with positive framing. |
| `Aura/brain/naturalness_critic.py` | **KEEP** | Tone Auditor & Therapy Interceptor | Blocks clinical therapy language; provides bilingual organic fallbacks. |

---

## 3. Visual & Media Services

| File Path | Classification | Responsibility | Target State / Action |
|---|---|---|---|
| `services/visual_engine.py` | **KEEP / CANONICAL** | Master Image Generation Engine | Realistic unedited smartphone camera prompt formula (768×1024, `enhance=false`, local caching). |
| `Aura/vision/visual_engine.py` | **MERGE** | Secondary visual engine stub | Re-exports canonical `services/visual_engine.py`. |
| `services/image_service.py` | **DELETE / DEPRECATE**| Old Doll-Face Generator | Truncated prompts and lacked `enhance=false`; safely delegated to `services/visual_engine.py`. |
| `services/prompt_composer.py` | **MERGE** | DNA Prompt Builder | Prompt logic unified into `services/visual_engine.py`. |
| `Aura/generation/identity_qa.py` | **KEEP** | Visual QA Gate | Audits generated image buffer for quality. |
| `services/avatar_service.py` | **KEEP** | Animated Talking Avatar Video | SadTalker/Wav2Lip video synthesis service. |

---

## 4. Voice Engine

| File Path | Classification | Responsibility | Target State / Action |
|---|---|---|---|
| `services/voice_ssml.py` | **KEEP / CANONICAL** | Expressive Edge-TTS Synthesizer | Generates expressive Bengali/English audio with mood prosody. |
| `services/voice_engine.py` | **MERGE** | Duplicate Voice Engine | Bridge to `voice_ssml.py`. |
| `services/voice_prosody.py` | **KEEP** | Prosody Planner | Calculates rate, pitch, and emotion tags for speech synthesis. |
| `services/voice_service.py` | **MERGE** | Voice Utility Service | Maintain for compatibility. |

---

## 5. Memory & Persistence

| File Path | Classification | Responsibility | Target State / Action |
|---|---|---|---|
| `Aura/memory/memory_manager.py` | **KEEP / CANONICAL** | 4-Layer Memory Context Compiler | Ingests working, episodic, semantic, and procedural layers. |
| `Aura/memory/open_loops.py` | **KEEP / CANONICAL** | Unresolved Event / Deadline Scanner | Extracts open loops with `settings.STRUCTURED_MODEL`. |
| `services/episodic_service.py` | **KEEP** | Milestone & Shared Episode Logger | Logs meaningful relationship memories with 4h cooldown. |
| `services/memory_service.py` | **KEEP** | Memory CRUD Operations | Handles recall and persistence in database. |
| `database/models.py` | **KEEP** | SQLAlchemy Data Models | Core schema (`SemanticMemory`, `SharedEpisode`, `OpenLoop`, `EmotionLog`, `UserProfile`). |
| `database/session.py` | **KEEP** | SQLite / Postgres Session Factory| Single database session factory. |
| `database/vector_db.py` | **KEEP** | Vector Memory (Chroma / Pinecone)| Vector embeddings and semantic search. |

---

## 6. Routers & Channels

| File Path | Classification | Responsibility | Target State / Action |
|---|---|---|---|
| `routers/voice.py` | **KEEP / CANONICAL** | Master WebSocket Gateway | Handles audio transcription, cognitive turn, streaming tokens, image delivery. |
| `routers/chat.py` | **KEEP** | REST Chat API | Secondary REST endpoint; handles history and proactive triggers. |
| `routers/analytics.py` | **KEEP** | Companion Dashboard Metrics | Returns mood logs, goal progress, and interaction counts. |
| `integrations/telegram_adapter.py`| **KEEP** | Telegram Bot Channel | Ingests user messages, executes cognitive pipeline, delivers voice/photos. |
| `services/proactive_worker.py` | **KEEP** | Background Proactive Daemon | Scheduled daemon evaluating open loops and relationship pings. |

