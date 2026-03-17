"""LunaClaw Brief — Scheduler

Cron-based scheduler that triggers report generation + delivery
based on schedule config in config.yaml.

Config format in config.yaml:
  schedule:
    - preset: stock_a_daily
      cron: "0 18 * * 1-5"     # weekdays 6pm
      delivery:
        - type: email
        - type: webhook
          url: https://hooks.slack.com/...
          webhook_type: slack
    - preset: ai_cv_weekly
      cron: "0 9 * * 1"        # Monday 9am
      delivery:
        - type: email

Usage:
  python -m brief.scheduler             # start scheduler
  python -m brief.scheduler --run-once  # trigger all due jobs once
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path

from brief.log import BriefLogger


def _match_cron(cron_expr: str, dt: datetime) -> bool:
    """Simple 5-field cron matcher (minute hour day month weekday).

    Supports: *, specific values, comma-separated values, ranges (N-M).
    """
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        return False

    fields = [dt.minute, dt.hour, dt.day, dt.month, dt.isoweekday() % 7]
    # isoweekday: Mon=1..Sun=7 → convert Sun=0 for cron compatibility
    fields[4] = dt.isoweekday() % 7  # Sun=0, Mon=1, ..., Sat=6

    for field_val, spec in zip(fields, parts):
        if spec == "*":
            continue
        allowed = set()
        for segment in spec.split(","):
            if "-" in segment:
                lo, hi = segment.split("-", 1)
                allowed.update(range(int(lo), int(hi) + 1))
            else:
                allowed.add(int(segment))
        if field_val not in allowed:
            return False
    return True


class BriefScheduler:
    """Schedule-driven report generator with multi-channel delivery."""

    def __init__(self, config: dict):
        self.config = config
        self.schedules = config.get("schedule", [])
        self.log = BriefLogger("scheduler")
        self._last_run: dict[str, str] = {}

    def check_and_run(self):
        """Check all schedules and run any that match the current time."""
        now = datetime.now()
        now_key = now.strftime("%Y-%m-%d %H:%M")

        for job in self.schedules:
            preset_name = job.get("preset", "")
            cron = job.get("cron", "")
            if not preset_name or not cron:
                continue

            job_key = f"{preset_name}:{cron}"
            if self._last_run.get(job_key) == now_key:
                continue

            if _match_cron(cron, now):
                self.log.info(f"Triggering: {preset_name}", cron=cron)
                self._last_run[job_key] = now_key
                self._execute_job(job)

    def _execute_job(self, job: dict):
        """Execute a single scheduled job: generate + deliver."""
        from brief.presets import get_preset
        from brief.pipeline import ReportPipeline
        from brief.sender import EmailSender, WebhookSender

        preset_name = job["preset"]
        try:
            preset = get_preset(preset_name)
            pipeline = ReportPipeline(preset, self.config)
            result = pipeline.run()

            if not result.get("success"):
                self.log.error(f"Job failed: {preset_name}", error=result.get("error"))
                return

            for delivery in job.get("delivery", []):
                d_type = delivery.get("type", "")
                if d_type == "email":
                    email_cfg = self.config.get("email", {})
                    if email_cfg:
                        sender = EmailSender(email_cfg)
                        html_path = result.get("html_path", "")
                        html_content = Path(html_path).read_text(encoding="utf-8") if html_path else ""
                        subject = f"🦞 {preset.display_name} — {result.get('issue_label', '?')}"
                        sender.send(
                            subject=subject,
                            html_content=html_content,
                            text_content=result.get("md_path", "")[:2000],
                            attachment_path=result.get("pdf_path"),
                        )
                elif d_type == "webhook":
                    wh_sender = WebhookSender(delivery)
                    md_path = result.get("md_path", "")
                    text = Path(md_path).read_text(encoding="utf-8")[:2000] if md_path else ""
                    subject = f"🦞 {preset.display_name} — {result.get('issue_label', '?')}"
                    wh_sender.send(subject, text, result.get("html_path", ""))

            self.log.info(f"Job complete: {preset_name}")

        except Exception as e:
            self.log.error(f"Job exception: {preset_name}", error=str(e)[:100])

    def run_loop(self, interval: int = 30):
        """Run the scheduler loop, checking every `interval` seconds."""
        self.log.info(f"Scheduler started with {len(self.schedules)} jobs")
        for job in self.schedules:
            self.log.info(f"  {job.get('preset')}: {job.get('cron')}")

        try:
            while True:
                self.check_and_run()
                time.sleep(interval)
        except KeyboardInterrupt:
            self.log.info("Scheduler stopped")

    def run_once(self):
        """Run all scheduled jobs once regardless of cron expression."""
        self.log.info(f"Running all {len(self.schedules)} jobs once")
        for job in self.schedules:
            self.log.info(f"Running: {job.get('preset')}")
            self._execute_job(job)


def main():
    parser = argparse.ArgumentParser(description="LunaClaw Brief Scheduler")
    parser.add_argument("--run-once", action="store_true", help="Run all jobs once and exit")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds")
    args = parser.parse_args()

    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from run import load_config

    config = load_config()
    scheduler = BriefScheduler(config)

    if args.run_once:
        scheduler.run_once()
    else:
        scheduler.run_loop(args.interval)


if __name__ == "__main__":
    main()
