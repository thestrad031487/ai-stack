from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from main import run_report
from datetime import datetime, timezone

scheduler = BlockingScheduler(timezone="UTC")

# Every 6 hours: 00:00, 06:00, 12:00, 18:00 UTC
scheduler.add_job(
    run_report,
    CronTrigger(hour="0,6,12,18", minute=0),
    id="server_health_report",
    name="Server Health Report",
)

print(f"[{datetime.now(timezone.utc)}] Server health scheduler started — runs at 00:00, 06:00, 12:00, 18:00 UTC")

try:
    scheduler.start()
except (KeyboardInterrupt, SystemExit):
    print("Scheduler stopped.")
