from ddgs import DDGS

def get_web_context(topic: str, max_results: int = 5) -> str:
    """Search DuckDuckGo for recent threat intel and news related to the topic."""
    try:
        query = f"{topic} cybersecurity threat attack 2025 2026"
        results = []

        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                title = r.get("title", "").strip()
                body = r.get("body", "").strip()
                href = r.get("href", "").strip()
                if title and body:
                    results.append(f"- {title}: {body[:300]}")

        if not results:
            return ""

        return (
            "WEB RESEARCH CONTEXT (recent open-source intelligence):\n"
            + "\n".join(results)
        )

    except Exception as e:
        print(f"[web_search] error: {e}", flush=True)
        return ""
