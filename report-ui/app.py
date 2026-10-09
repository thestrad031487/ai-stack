import os
import html
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

app = FastAPI()

REPORTS_DIR = "/app/reports"

def get_reports():
    try:
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".md")]
        files.sort(reverse=True)
        reports = []
        for f in files:
            path = os.path.join(REPORTS_DIR, f)
            topic = "Unknown"
            report_type = "standard"
            try:
                with open(path) as fh:
                    for line in fh:
                        if line.startswith("# Security Report:"):
                            topic = line.replace("# Security Report:", "").strip()
                            break
            except:
                pass
            if f.startswith("debate_"):
                report_type = "debate"
            try:
                parts = f.replace("report_", "").replace("debate_", "").replace(".md", "")
                dt = datetime.strptime(parts, "%Y%m%d_%H%M%S")
                date_str = dt.strftime("%b %d %Y %H:%M")
                sort_key = dt
            except:
                date_str = "Unknown"
                sort_key = datetime.min
            reports.append({
                "filename": f,
                "topic": topic,
                "date": date_str,
                "type": report_type,
                "sort_key": sort_key
            })
        reports.sort(key=lambda x: x["sort_key"], reverse=True)
        return reports
    except Exception as e:
        return []

@app.get("/", response_class=HTMLResponse)
def index():
    reports = get_reports()
    rows = ""
    for r in reports:
        badge_color = "#c8963e" if r["type"] == "debate" else "#2dd4aa"
        badge_label = "DEBATE" if r["type"] == "debate" else "STANDARD"
        rows += f"""
        <tr onclick="window.location='/report/{r['filename']}'" style="cursor:pointer;">
          <td style="padding:12px 16px;color:#dad8d2;">{r['date']}</td>
          <td style="padding:12px 16px;color:#dad8d2;font-weight:500;">{r['topic']}</td>
          <td style="padding:12px 16px;">
            <span style="font-size:9px;font-weight:700;letter-spacing:0.1em;padding:2px 8px;border-radius:3px;background:rgba(0,0,0,0.3);color:{badge_color};border:1px solid {badge_color}40;">{badge_label}</span>
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CyberGrind — Security Reports</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #1d1e20; color: #dad8d2; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 15px; line-height: 1.6; }}
  .wrap {{ max-width: 900px; margin: 0 auto; padding: 48px 24px; }}
  .eyebrow {{ font-size: 11px; letter-spacing: 0.15em; color: #c8963e; text-transform: uppercase; margin-bottom: 10px; }}
  h1 {{ font-size: 28px; font-weight: 700; color: #dad8d2; margin-bottom: 6px; }}
  .subtitle {{ font-size: 13px; color: #9b9c9d; margin-bottom: 36px; }}
  .card {{ background: #2e2e33; border: 1px solid #333; border-radius: 8px; overflow: hidden; }}
  table {{ width: 100%; border-collapse: collapse; }}
  thead tr {{ border-bottom: 1px solid #333; }}
  th {{ padding: 10px 16px; font-size: 10px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #9b9c9d; text-align: left; }}
  tbody tr {{ border-bottom: 1px solid #2a2a2f; transition: background 0.15s; }}
  tbody tr:last-child {{ border-bottom: none; }}
  tbody tr:hover {{ background: #35353b; }}
  .empty {{ padding: 48px; text-align: center; color: #9b9c9d; font-size: 14px; }}
  .count {{ font-size: 12px; color: #9b9c9d; margin-top: 12px; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">// CyberGrind SOC</div>
  <h1>Security Reports</h1>
  <p class="subtitle">AI-generated threat analysis reports from the CyberClaw pipeline.</p>
  <div class="card">
    {'<table><thead><tr><th>Date</th><th>Topic</th><th>Type</th></tr></thead><tbody>' + rows + '</tbody></table>' if reports else '<div class="empty">No reports found.</div>'}
  </div>
  <p class="count">{len(reports)} report{"s" if len(reports) != 1 else ""}</p>
</div>
</body>
</html>"""

@app.get("/report/{filename}", response_class=HTMLResponse)
def view_report(filename: str):
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        with open(path) as f:
            content = f.read()
    except:
        raise HTTPException(status_code=500, detail="Could not read report")

    safe_json = json.dumps(content).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Report — {html.escape(filename)}</title>
<script src="https://cdn.jsdelivr.net/npm/marked@18.0.14/lib/marked.umd.js" integrity="sha384-2vpGtuKqJvFlwJqYnf/wUMuzUfhUnYBt9oay0e2yaFcq0Dh6/aEbQ8YAOeKGzlYo" crossorigin="anonymous"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3.4.16/dist/purify.min.js" integrity="sha384-a7SzOxErzJ3ZpQz0zJ32d67dSitNzPcbfybc/ykU9KJhMgZkwqfSxlhhdJRS+XGL" crossorigin="anonymous"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: #1d1e20; color: #dad8d2; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 15px; line-height: 1.75; }}
  .wrap {{ max-width: 780px; margin: 0 auto; padding: 48px 24px 80px; }}
  .back {{ display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: #9b9c9d; text-decoration: none; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 32px; border-bottom: 1px solid transparent; transition: color 0.15s, border-color 0.15s; }}
  .back:hover {{ color: #c8963e; border-color: #c8963e; }}
  .report-body h1 {{ font-size: 26px; font-weight: 700; color: #dad8d2; margin: 0 0 8px; }}
  .report-body h2 {{ font-size: 12px; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; color: #c8963e; margin: 36px 0 14px; padding-bottom: 8px; border-bottom: 1px solid #333; }}
  .report-body h3 {{ font-size: 14px; font-weight: 600; color: #e8b86d; margin: 20px 0 8px; }}
  .report-body p {{ color: #c4c4c5; margin-bottom: 14px; }}
  .report-body ul, .report-body ol {{ padding-left: 20px; margin-bottom: 14px; color: #c4c4c5; }}
  .report-body li {{ margin-bottom: 6px; }}
  .report-body strong {{ color: #dad8d2; }}
  .report-body code {{ font-size: 12px; background: #2e2e33; padding: 1px 6px; border-radius: 3px; color: #2dd4aa; }}
  .report-body pre {{ background: #2e2e33; border: 1px solid #333; border-radius: 6px; padding: 16px; overflow-x: auto; margin-bottom: 16px; }}
  .report-body pre code {{ background: none; padding: 0; color: #c4c4c5; }}
  .report-body table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; font-size: 14px; }}
  .report-body th {{ background: #2e2e33; padding: 8px 12px; text-align: left; font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: #9b9c9d; border: 1px solid #333; }}
  .report-body td {{ padding: 8px 12px; border: 1px solid #333; color: #c4c4c5; }}
  .report-body hr {{ border: none; border-top: 1px solid #333; margin: 28px 0; }}
  .meta {{ font-size: 12px; color: #9b9c9d; margin-bottom: 32px; padding-bottom: 20px; border-bottom: 1px solid #333; }}
</style>
</head>
<body>
<div class="wrap">
  <a href="/" class="back">← All Reports</a>
  <div class="meta">{html.escape(filename)}</div>
  <div class="report-body" id="report"></div>
</div>
<script>
  const raw = {safe_json};
  document.getElementById('report').innerHTML = DOMPurify.sanitize(marked.parse(raw));
</script>
</body>
</html>"""
