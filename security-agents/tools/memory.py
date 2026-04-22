import os
from datetime import datetime

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "../outputs/reports")

def get_recent_reports(n=3) -> str:
    """Read the n most recent reports and extract topic + executive summary."""
    try:
        files = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".md")]
        if not files:
            return ""
        files.sort(reverse=True)
        summaries = []
        for f in files[:n]:
            path = os.path.join(REPORTS_DIR, f)
            try:
                with open(path) as fh:
                    content = fh.read()

                # extract topic from first line
                topic = "Unknown"
                for line in content.splitlines():
                    if line.startswith("# Security Report:"):
                        topic = line.replace("# Security Report:", "").strip()
                        break

                # extract date from filename
                try:
                    parts = f.replace("report_", "").replace(".md", "")
                    dt = datetime.strptime(parts, "%Y%m%d_%H%M%S")
                    date_str = dt.strftime("%b %d %Y")
                except:
                    date_str = "Unknown date"

                # extract executive summary section
                summary = ""
                in_summary = False
                for line in content.splitlines():
                    if line.strip() == "## Executive Summary":
                        in_summary = True
                        continue
                    if in_summary:
                        if line.startswith("## "):
                            break
                        if line.strip():
                            summary += line.strip() + " "

                summary = summary.strip()
                if summary:
                    summaries.append(f"- [{date_str}] {topic}: {summary}")
            except Exception:
                continue

        if not summaries:
            return ""

        return "PAST REPORT SUMMARIES (for context — avoid repeating these analyses):\n" + "\n".join(summaries)

    except Exception as e:
        return ""
