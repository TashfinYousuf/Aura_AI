# FILE: backend/app/Aura/tools/tool_executor.py
"""
Agentic Tool Execution Framework for Aura:
- Risk-tiered execution (LOW, MEDIUM, HIGH).
- Safe mathematical computation (no dangerous eval).
- Calendar / commitment integration.
- Extensible registry for cognitive pipeline actions.
"""

import math
import re
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from pydantic import BaseModel

from app.database.session import SessionLocal
from app.database.models import OpenLoop

class ToolRiskTier(str, Enum):
    LOW = "low"          # Read-only, deterministic calculations, time checks
    MEDIUM = "medium"    # State alterations (calendar events, goal additions)
    HIGH = "high"        # Irreversible (account deletion, memory purge)

class ToolResult(BaseModel):
    success: bool
    tool_name: str
    result: Any
    risk_tier: ToolRiskTier
    error: Optional[str] = None

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_default_tools()

    def register(self, name: str, description: str, risk_tier: ToolRiskTier, handler: Callable):
        self._tools[name] = {
            "name": name,
            "description": description,
            "risk_tier": risk_tier,
            "handler": handler
        }

    def _register_default_tools(self):
        # 1. Safe Mathematical Calculator (No arbitrary code execution)
        def safe_calculate(expression: str) -> str:
            # Clean and sanitize expression: allow only numbers and basic math operators
            clean_expr = re.sub(r'[^0-9\+\-\*\/\.\(\)\%\^\s]', '', expression)
            clean_expr = clean_expr.replace('^', '**')
            try:
                # Compile to bytecode with restricted names
                code = compile(clean_expr, "<string>", "eval")
                # Whitelist safe builtins
                allowed_names = {
                    "sin": math.sin, "cos": math.cos, "sqrt": math.sqrt,
                    "pi": math.pi, "e": math.e, "pow": pow, "round": round
                }
                res = eval(code, {"__builtins__": {}}, allowed_names)
                return str(res)
            except Exception as e:
                return f"Calculation error: {e}"

        self.register(
            name="calculator",
            description="Performs safe mathematical calculations and conversions",
            risk_tier=ToolRiskTier.LOW,
            handler=safe_calculate
        )

        # 2. Clock / Time Check
        def get_current_time(timezone_name: str = "Asia/Dhaka") -> str:
            now = datetime.now()
            return f"Current time is {now.strftime('%I:%M %p on %A, %B %d, %Y')} ({timezone_name})"

        self.register(
            name="get_time",
            description="Returns current date, day, and time",
            risk_tier=ToolRiskTier.LOW,
            handler=get_current_time
        )

        # 3. Calendar & Commitment Tracker
        def add_calendar_event(user_id: str, topic: str, context: str) -> str:
            with SessionLocal() as db:
                loop = OpenLoop(
                    user_id=user_id,
                    topic=topic,
                    context=context,
                    status="active"
                )
                db.add(loop)
                db.commit()
            return f"Added commitment: '{topic}' - {context}"

        self.register(
            name="add_commitment",
            description="Schedules a new calendar event or open commitment loop",
            risk_tier=ToolRiskTier.MEDIUM,
            handler=add_calendar_event
        )

    def execute(self, tool_name: str, params: Dict[str, Any], user_id: str = "") -> ToolResult:
        if tool_name not in self._tools:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                result=None,
                risk_tier=ToolRiskTier.LOW,
                error=f"Tool '{tool_name}' not found in registry"
            )

        tool_meta = self._tools[tool_name]
        handler = tool_meta["handler"]
        risk = tool_meta["risk_tier"]

        try:
            # Inject user_id if handler expects it
            if "user_id" in handler.__code__.co_varnames and "user_id" not in params:
                params["user_id"] = user_id

            res = handler(**params)
            return ToolResult(
                success=True,
                tool_name=tool_name,
                result=res,
                risk_tier=risk
            )
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                result=None,
                risk_tier=risk,
                error=str(e)
            )

tool_registry = ToolRegistry()

