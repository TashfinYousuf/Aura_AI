# FILE: backend/app/Aura/brain/presence_engine.py
"""
Aura Human Presence & Activity Lifecycle Engine:
- Simulates realistic human circadian rhythms and activity cycles.
- Replaces rigid 24/7 robotic 'Active now' with organic presence:
  * Daytime (9 AM - 6 PM): Active / Busy studying / Having coffee.
  * Evening (6 PM - 12 AM): High engagement Active now.
  * Late Night (12 AM - 2 AM): Intimate late night / sleepy chat.
  * Deep Night (2 AM - 7:30 AM): Sleeping / Away with realistic late-reply cadence.
"""

from datetime import datetime
from typing import Dict, Any

class PresenceEngine:
    @staticmethod
    def get_current_presence() -> Dict[str, Any]:
        now = datetime.now()
        hour = now.hour
        minute = now.minute

        # 2:30 AM to 7:30 AM -> Sleeping
        if 2 <= hour < 7 or (hour == 7 and minute < 30):
            return {
                "status": "sleeping",
                "status_label": "Sleeping 🌙",
                "indicator_color": "slate",
                "is_online": False,
                "natural_reply_delay": 3.0,
                "context_hint": "Late night, was asleep. Acknowledge being sleepy or woken up softly."
            }
        # 7:30 AM to 9:30 AM -> Waking up / Morning routine
        elif (hour == 7 and minute >= 30) or hour < 10:
            return {
                "status": "away",
                "status_label": "Morning coffee ☕",
                "indicator_color": "amber",
                "is_online": True,
                "natural_reply_delay": 1.8,
                "context_hint": "Morning routine, soft energetic mood."
            }
        # 10 AM to 5 PM -> Daily activities / study / reading
        elif 10 <= hour < 17:
            # Subtle variation based on hour
            if hour in (13, 14):
                return {
                    "status": "away",
                    "status_label": "Lunch break 🥗",
                    "indicator_color": "amber",
                    "is_online": True,
                    "natural_reply_delay": 1.5,
                    "context_hint": "Casual lunch/afternoon break."
                }
            return {
                "status": "active",
                "status_label": "Active now",
                "indicator_color": "emerald",
                "is_online": True,
                "natural_reply_delay": 1.0,
                "context_hint": "Active daytime companion."
            }
        # 5 PM to 12 AM -> Peak engagement
        elif 17 <= hour < 24:
            return {
                "status": "active",
                "status_label": "Active now",
                "indicator_color": "emerald",
                "is_online": True,
                "natural_reply_delay": 0.8,
                "context_hint": "Relaxed evening, highly attentive and affectionate."
            }
        # 12 AM to 2:30 AM -> Late night pillow talk
        else:
            return {
                "status": "active",
                "status_label": "Active now • Bed",
                "indicator_color": "emerald",
                "is_online": True,
                "natural_reply_delay": 1.5,
                "context_hint": "Late night in bed, cozy, quiet whispers, dewy relaxed mood."
            }

presence_engine = PresenceEngine()

