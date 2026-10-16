import os
import sys
import logging
import requests
import subprocess
from datetime import datetime
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

logging.basicConfig(level=logging.INFO)

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
AGENTS_DIR = os.environ.get("AGENTS_DIR", "/app/security-agents")
SHELTER_API = os.environ.get("SHELTER_API", "http://shelter-api:8000")
SHELTER_SCHEDULER = os.environ.get("SHELTER_SCHEDULER", "http://shelter-scheduler:8001")

print("Starting CyberClaw Slack bot...", flush=True)

app = App(token=SLACK_BOT_TOKEN)

def chat(message: str) -> str:
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": "gemma3:4b",
            "messages": [{"role": "system", "content": "Respond concisely in plain conversational text, no more than 2-4 sentences unless the user explicitly asks for a detailed breakdown. Avoid markdown headers and bullet lists for simple answers."}, {"role": "user", "content": message}],
            "stream": False
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()["message"]["content"]

def shelter_fetch(path):
    try:
        r = requests.get(f"{SHELTER_API}{path}", timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        return None

def shelter_query(query: str) -> str:
    q = query.lower()

    if any(w in q for w in ["summary", "insight", "today", "daily"]):
        data = shelter_fetch("/metrics/summary")
        if data and data.get("summary"):
            return f"*Daily insight:*\n{data['summary']}"
        return "No summary available yet."

    if any(w in q for w in ["metric", "stat", "rate", "overview"]):
        m = shelter_fetch("/metrics")
        if not m:
            return "Could not reach shelter API."
        return (
            f"*Shelter network overview:*\n"
            f"• Total animals: {m['total_animals']}\n"
            f"• Available: {m['available']}\n"
            f"• Adopted: {m['adopted']}\n"
            f"• Adoption rate: {m['adoption_rate']}%\n"
            f"• Pending: {m['pending']}"
        )

    species = None
    if "dog" in q:
        species = "dog"
    elif "cat" in q:
        species = "cat"

    status = "available"
    if "adopted" in q:
        status = "adopted"
    elif "pending" in q:
        status = "pending"
    elif "all" in q:
        status = None

    animals = shelter_fetch("/animals")
    if not animals:
        return "Could not reach shelter API."

    filtered = animals
    if species:
        filtered = [a for a in filtered if a["species"] == species]
    if status:
        filtered = [a for a in filtered if a["status"] == status]

    city_filter = None
    for word in q.split():
        if word.istitle() or word[0].isupper():
            city_filter = word
            break

    if city_filter:
        shelters = shelter_fetch("/shelters")
        if shelters:
            matched = [s["id"] for s in shelters if city_filter.lower() in s["city"].lower() or city_filter.lower() in s["name"].lower()]
            if matched:
                filtered = [a for a in filtered if a["shelter_id"] in matched]

    if not filtered:
        label = f"{species or 'animal'}s" if species else "animals"
        return f"No {label} found matching your query."

    label = f"{species or 'animal'}s" if species else "animals"
    lines = [f"*{len(filtered)} {label} found:*"]
    for a in filtered[:8]:
        days = None
        if a.get("intake_date"):
            try:
                intake = datetime.fromisoformat(a["intake_date"].replace("Z", ""))
                days = (datetime.utcnow() - intake).days
            except:
                pass
        day_str = f" — {days}d in shelter" if days is not None else ""
        lines.append(f"• *{a['name']}* ({a['breed']}, {a['age_years']}yr {a['sex']}){day_str}")
        if a.get("description"):
            lines.append(f"  _{a['description'][:120]}..._")

    if len(filtered) > 8:
        lines.append(f"_...and {len(filtered) - 8} more. Visit shelter.cybergrind.org for the full list._")

    return "\n".join(lines)

def shelter_update() -> str:
    try:
        r = requests.post(f"{SHELTER_SCHEDULER}/update", timeout=120)
        if r.status_code != 200:
            return f"Shelter scheduler returned error: {r.status_code} — {r.text[:200]}"
        result = r.json()
        if result.get("status") != "ok":
            return f"Update failed: {result.get('message', 'unknown error')}"
    except requests.exceptions.Timeout:
        return "Shelter update timed out (>120s). The update may still be running."
    except Exception as e:
        return f"Could not reach shelter scheduler: {e}"

    m = shelter_fetch("/metrics")
    summary_data = shelter_fetch("/metrics/summary")

    if not m:
        return "Update complete, but could not fetch metrics."

    lines = [
        "*✅ Shelter network updated.*",
        f"• Total animals: {m['total_animals']}",
        f"• Available: {m['available']}",
        f"• Adopted: {m['adopted']}",
        f"• Adoption rate: {m['adoption_rate']}%",
        f"• Pending: {m['pending']}",
    ]

    if summary_data and summary_data.get("summary"):
        lines.append(f"\n*Daily insight:*\n{summary_data['summary']}")

    return "\n".join(lines)

def is_shelter_query(text: str) -> bool:
    keywords = [
        "dog", "cat", "shelter", "animal", "adopt", "available",
        "intake", "pets", "rescue", "summary", "insight", "daily"
    ]
    return any(k in text.lower() for k in keywords)

def list_reports() -> str:
    reports_dir = os.path.join(AGENTS_DIR, "outputs/reports")
    try:
        files = [f for f in os.listdir(reports_dir) if f.endswith(".md")]
        if not files:
            return "No reports found."
        files.sort(reverse=True)
        lines = [f"*Last {min(len(files), 10)} security reports:*"]
        for f in files[:10]:
            try:
                parts = f.replace("report_", "").replace("debate_", "").replace(".md", "")
                dt = datetime.strptime(parts, "%Y%m%d_%H%M%S")
            except:
                dt = None
            try:
                with open(os.path.join(reports_dir, f)) as fh:
                    topic_line = fh.readline().strip().replace("# Security Report: ", "")
            except:
                topic_line = f
            label = dt.strftime("%b %d %H:%M") if dt else f
            prefix = "🗣️" if f.startswith("debate_") else "📄"
            lines.append(f"• {prefix} `{label}` — {topic_line}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error reading reports: {e}"

def debate_narrator(report_text: str) -> str:
    prompt = f"""You are a security narrator summarizing a debate-format threat analysis report for a Slack channel.
Read the report below and write a 3-4 sentence plain-English summary that covers:
- What the two analysts agreed on
- The key point where they diverged
- The most important takeaway for a security team

Be concise, direct, and avoid jargon. Do not use bullet points.

REPORT:
{report_text[-3000:]}

Write the narrator summary now:"""

    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "gemma3:4b",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["message"]["content"].strip()
    except Exception as e:
        return f"(Narrator unavailable: {e})"

def run_pipeline(topic: str, say, user: str, debate: bool = False):
    say(f"<@{user}> Starting {'debate' if debate else 'security'} analysis on: *{topic}*. This will take a few minutes...")
    try:
        result = subprocess.run(
            ["python3", "main.py"] + (["--debate"] if debate else []) + [topic],
            cwd=AGENTS_DIR,
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "OLLAMA_URL": OLLAMA_URL}
        )
        if result.returncode == 0:
            output = result.stdout
            if "FINAL REPORT" in output:
                report = output.split("="*60)[-1].strip()
                if len(report) > 3800:
                    say(f"<@{user}> Report generated (truncated):\n```{report[:3800]}```")
                    say(f"<@{user}> Full report saved to server at `security-agents/outputs/reports/`")
                else:
                    say(f"<@{user}> ```{report}```")

                if debate:
                    narrator_summary = debate_narrator(report)
                    say(f"<@{user}> *🎙️ Narrator Summary:*\n{narrator_summary}")
            else:
                say(f"<@{user}> Pipeline completed. Report saved to server.")
        else:
            say(f"<@{user}> Pipeline error: {result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        say(f"<@{user}> Pipeline timed out. Try a more specific topic.")
    except Exception as e:
        say(f"<@{user}> Error running pipeline: {e}")

@app.event("app_mention")
def handle_mention(event, say):
    user = event["user"]
    text = event["text"]
    clean_text = " ".join(text.split()[1:]).strip()

    if clean_text.lower().startswith("list reports"):
        say(f"<@{user}> {list_reports()}")
        return

    if clean_text.lower().startswith("run shelter update"):
        say(f"<@{user}> Running shelter update — this may take a minute...")
        reply = shelter_update()
        say(f"<@{user}> {reply}")
        return

    if clean_text.lower().startswith("run debate report"):
        topic = clean_text[len("run debate report"):].strip()
        if not topic:
            topic = "self-hosted AI platform security"
        run_pipeline(topic, say, user, debate=True)
        return

    if clean_text.lower().startswith("run security report"):
        topic = clean_text[len("run security report"):].strip()
        if not topic:
            topic = "self-hosted AI platform security"
        run_pipeline(topic, say, user)
    elif clean_text.lower().startswith("run report"):
        topic = clean_text[len("run report"):].strip()
        if not topic:
            topic = "self-hosted AI platform security"
        run_pipeline(topic, say, user)
    elif is_shelter_query(clean_text):
        try:
            reply = shelter_query(clean_text)
            say(f"<@{user}> {reply}")
        except Exception as e:
            say(f"<@{user}> Error querying shelter data: {e}")
    else:
        try:
            reply = chat(clean_text)
            say(f"<@{user}> {reply}")
        except Exception as e:
            say(f"<@{user}> Error: {e}")

if __name__ == "__main__":
    print("Initializing SocketModeHandler...", flush=True)
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
