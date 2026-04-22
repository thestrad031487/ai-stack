import requests

CTI_API_URL = "https://api.cybergrind.org"

SKIP_KEYWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "are",
    "was", "has", "have", "been", "will", "not", "but", "can",
    "all", "any", "its", "our", "your", "their", "what", "how",
    "when", "where", "which", "security", "attack", "threat",
    "risk", "vulnerability", "exploit", "malware", "network"
}

def extract_keywords(topic: str) -> list:
    words = topic.lower().replace("-", " ").replace("_", " ").split()
    keywords = [w.strip(".,;:()[]") for w in words if len(w) > 3 and w not in SKIP_KEYWORDS]
    if len(topic.split()) <= 4:
        keywords.append(topic.strip())
    return list(dict.fromkeys(keywords))[:5]

def fetch_by_value(keyword: str, limit: int = 10) -> list:
    try:
        res = requests.get(
            f"{CTI_API_URL}/api/misp/search",
            params={"value": keyword, "limit": limit},
            timeout=10
        )
        res.raise_for_status()
        return res.json().get("matches", [])
    except Exception as e:
        print(f"[misp_context] Value search failed for '{keyword}': {e}")
        return []

def fetch_by_threat(keyword: str, limit: int = 10) -> list:
    try:
        res = requests.get(
            f"{CTI_API_URL}/api/misp/threat",
            params={"q": keyword, "limit": limit},
            timeout=10
        )
        if res.status_code == 404:
            return []
        res.raise_for_status()
        return res.json().get("results", [])
    except Exception as e:
        print(f"[misp_context] Threat search failed for '{keyword}': {e}")
        return []

def get_misp_context(topic: str) -> str:
    keywords = extract_keywords(topic)
    if not keywords:
        return ""

    print(f"[misp_context] Searching MISP for keywords: {keywords}")

    all_iocs = []
    seen_values = set()

    for kw in keywords:
        for ioc in fetch_by_value(kw):
            val = ioc.get("value", "")
            if val and val not in seen_values:
                seen_values.add(val)
                all_iocs.append(ioc)
        for ioc in fetch_by_threat(kw):
            val = ioc.get("value", "")
            if val and val not in seen_values:
                seen_values.add(val)
                all_iocs.append(ioc)

    if not all_iocs:
        print(f"[misp_context] No MISP IOCs found for topic: {topic}")
        return ""

    print(f"[misp_context] Found {len(all_iocs)} relevant IOCs from MISP")

    lines = [
        f"LIVE THREAT INTELLIGENCE FROM MISP ({len(all_iocs)} indicators related to this topic):",
        ""
    ]

    by_type = {}
    for ioc in all_iocs:
        t = ioc.get("ioc_type", "unknown")
        by_type.setdefault(t, []).append(ioc)

    for ioc_type, iocs in by_type.items():
        lines.append(f"[{ioc_type.upper()}]")
        for ioc in iocs[:8]:
            threat = ioc.get("threat", "")
            malware = ioc.get("malware", "")
            value = ioc.get("value", "")
            meta = f" | threat: {threat}" if threat else ""
            meta += f" | source: {malware}" if malware else ""
            lines.append(f"  - {value}{meta}")
        lines.append("")

    lines.append("Use these indicators to inform your risk analysis. Reference specific IOCs where relevant.")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    topic = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "docker container hardening"
    ctx = get_misp_context(topic)
    print(ctx if ctx else "No MISP context found.")
