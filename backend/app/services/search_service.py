import os
import asyncio
import httpx
from duckduckgo_search import DDGS

async def execute_web_search(query: str) -> str:
    """
    Two-tier web search engine: DuckDuckGo HTML with Tavily fallback.
    """
    search_keywords = ["search", "latest", "news", "today", "update", "price", "bitcoin", "btc", "live"]
    if not any(k in query.lower() for k in search_keywords):
        return ""

    print(f"🌍 [SEARCH SERVICE] Executing live search for: {query}")
    
    # Tier 1: DuckDuckGo
    try:
        def _ddg():
            with DDGS(timeout=6) as ddgs:
                return list(ddgs.text(query, max_results=2, backend="html"))
        
        results = await asyncio.to_thread(_ddg)
        if results:
            formatted = "\n".join([f"- {r.get('title')}: {r.get('body')}" for r in results])
            return f"\n[REAL-TIME DATA]:\n{formatted}\n"
    except Exception as e:
        print(f"⚠️ [SEARCH SERVICE] DDG failed: {e}")

    # Tier 2: Tavily
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    "https://api.tavily.com/search",
                    json={"api_key": tavily_key, "query": query, "max_results": 2},
                    timeout=6.0
                )
                if res.status_code == 200:
                    items = res.json().get("results", [])
                    formatted = "\n".join([f"- {i.get('title')}: {i.get('content')}" for i in items])
                    return f"\n[REAL-TIME DATA]:\n{formatted}\n"
        except Exception as e:
            print(f"⚠️ [SEARCH SERVICE] Tavily failed: {e}")

    return ""