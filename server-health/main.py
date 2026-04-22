import os
import subprocess
import requests
import psutil
from datetime import datetime, timezone

# --- Config ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#serverhealth")
MODEL = os.getenv("HEALTH_MODEL", "mistral")
DOCKER_SOCKET = "/var/run/docker.sock"

# --- Helpers ---

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True).strip()
    except subprocess.CalledProcessError as e:
        return e.output.strip() or "error"


def collect_system():
    cpu = psutil.cpu_percent(interval=2)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    uptime_seconds = (datetime.now(timezone.utc).timestamp() - psutil.boot_time())
    uptime_hours = int(uptime_seconds // 3600)
    uptime_days = uptime_hours // 24
    uptime_hrs_rem = uptime_hours % 24
    return {
        "cpu_pct": cpu,
        "ram_used_gb": round(ram.used / 1e9, 1),
        "ram_total_gb": round(ram.total / 1e9, 1),
        "ram_pct": ram.percent,
        "disk_used_gb": round(disk.used / 1e9, 1),
        "disk_total_gb": round(disk.total / 1e9, 1),
        "disk_pct": disk.percent,
        "uptime": f"{uptime_days}d {uptime_hrs_rem}h",
    }


def collect_docker():
    raw = run("docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Image}}'")
    containers = []
    for line in raw.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            name, status, image = parts
            state = "✅" if status.lower().startswith("up") else "❌"
            containers.append({"name": name, "status": status, "image": image, "state": state})
    return containers


def collect_gpu():
    raw = run(
        "nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu "
        "--format=csv,noheader,nounits"
    )
    if "error" in raw.lower() or not raw:
        return None
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) < 5:
        return None
    return {
        "name": parts[0],
        "util_pct": parts[1],
        "vram_used_mb": parts[2],
        "vram_total_mb": parts[3],
        "temp_c": parts[4],
    }


def collect_ollama_models():
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = r.json().get("models", [])
        return [m["name"] for m in models]
    except Exception:
        return ["unreachable"]


def collect_security_events():
    events = []

    # Auth log — failed SSH logins
    auth_raw = run("grep -i 'failed password\\|invalid user\\|authentication failure' /host/var/log/auth.log 2>/dev/null | tail -20")
    if auth_raw and "error" not in auth_raw.lower():
        failed_count = len(auth_raw.splitlines())
        events.append(f"SSH: {failed_count} failed login attempt(s) in auth.log (last 20 lines)")
    else:
        events.append("SSH: auth.log not accessible or no recent failures")

    # Sudo usage
    sudo_raw = run("grep 'sudo' /host/var/log/auth.log 2>/dev/null | grep -i 'command\\|session opened' | tail -10")
    if sudo_raw and "error" not in sudo_raw.lower():
        sudo_count = len(sudo_raw.splitlines())
        events.append(f"Sudo: {sudo_count} sudo event(s) in auth.log")
    else:
        events.append("Sudo: no recent sudo events")

    # Docker container logs — error/warn scan (last 100 lines per container)
    containers = collect_docker()
    flagged = []
    for c in containers:
        if not c["status"].lower().startswith("up"):
            flagged.append(f"{c['name']} is {c['status']}")
            continue
        log_raw = run(f"docker logs --tail 100 {c['name']} 2>&1 | grep -iE 'error|fatal|exception|panic|oom' | tail -5")
        if log_raw and "error" not in log_raw.lower()[:10]:
            flagged.append(f"{c['name']}: {len(log_raw.splitlines())} error-level log line(s)")

    if flagged:
        events.append("Docker log anomalies: " + "; ".join(flagged))
    else:
        events.append("Docker logs: no error/fatal/panic lines detected")

    return events


def build_raw_block(sys, containers, gpu, models, security):
    lines = [
        f"🖥️  *thestrad-ubuntu-server — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*",
        "",
        "*System*",
        f"  CPU:    {sys['cpu_pct']}%",
        f"  RAM:    {sys['ram_used_gb']} / {sys['ram_total_gb']} GB ({sys['ram_pct']}%)",
        f"  Disk:   {sys['disk_used_gb']} / {sys['disk_total_gb']} GB ({sys['disk_pct']}%)",
        f"  Uptime: {sys['uptime']}",
        "",
        "*GPU*",
    ]
    if gpu:
        lines += [
            f"  {gpu['name']}",
            f"  Util:  {gpu['util_pct']}%  |  VRAM: {gpu['vram_used_mb']} / {gpu['vram_total_mb']} MB  |  Temp: {gpu['temp_c']}°C",
        ]
    else:
        lines.append("  nvidia-smi unavailable")

    lines += ["", "*Ollama Models*"]
    for m in models:
        lines.append(f"  • {m}")

    lines += ["", "*Docker Containers*"]
    for c in containers:
        lines.append(f"  {c['state']} {c['name']}  —  {c['status']}")

    lines += ["", "*Security Events*"]
    for e in security:
        lines.append(f"  • {e}")

    return "\n".join(lines)


def narrate(raw_block):
    prompt = f"""You are a server monitoring assistant for a self-hosted homelab running Docker, Ollama, and GPU workloads.

Below is a system health snapshot. Write a concise 4-6 sentence plain English summary. Call out anything unusual — high CPU/RAM/disk, GPU temperature concerns, stopped containers, failed SSH attempts, or Docker log errors. If everything looks healthy, say so clearly. Do not repeat every number — synthesize and highlight what matters.

{raw_block}"""

    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        return r.json().get("response", "Narrative generation failed.").strip()
    except Exception as e:
        return f"Narrative generation failed: {e}"


def post_to_slack(raw_block, narrative):
    if not SLACK_BOT_TOKEN:
        print("ERROR: SLACK_BOT_TOKEN not set")
        return

    text = f"{raw_block}\n\n*🤖 CyberClaw Analysis*\n{narrative}"

    r = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
        json={"channel": SLACK_CHANNEL, "text": text, "mrkdwn": True},
        timeout=15,
    )
    result = r.json()
    if result.get("ok"):
        print(f"[{datetime.now(timezone.utc)}] Report posted to {SLACK_CHANNEL}")
    else:
        print(f"[{datetime.now(timezone.utc)}] Slack error: {result.get('error')}")


def run_report():
    print(f"[{datetime.now(timezone.utc)}] Collecting metrics...")
    sys_data = collect_system()
    containers = collect_docker()
    gpu = collect_gpu()
    models = collect_ollama_models()
    security = collect_security_events()

    raw = build_raw_block(sys_data, containers, gpu, models, security)
    print(raw)

    print("Generating narrative...")
    narrative = narrate(raw)
    print(narrative)

    post_to_slack(raw, narrative)


if __name__ == "__main__":
    run_report()
