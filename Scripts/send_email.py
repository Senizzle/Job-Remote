"""
send_email.py — Sends the daily job digest via Resend.
Reads data/new_jobs.json and emails a formatted HTML digest.
Requires env vars: RESEND_API_KEY, TO_EMAIL, FROM_EMAIL
Set FORCE_EMAIL=true to send a test email even when no jobs found.
"""

import os
import json
import datetime
import requests
from pathlib import Path

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
TO_EMAIL       = os.environ.get("TO_EMAIL", "")
FROM_EMAIL     = os.environ.get("FROM_EMAIL", "")
FORCE_EMAIL    = os.environ.get("FORCE_EMAIL", "false").lower() == "true"

NEW_JOBS_FILE  = Path("data/new_jobs.json")

SOURCE_COLORS = {
    "dice":     "#0073E6",
    "linkedin": "#0A66C2",
    "indeed":   "#2D2D87",
}

def badge(source: str) -> str:
    color = SOURCE_COLORS.get(source.lower(), "#555")
    label = source.title()
    return (
        f'<span style="background:{color};color:#fff;padding:2px 8px;'
        f'border-radius:4px;font-size:12px;font-weight:bold;">{label}</span>'
    )

def build_test_html(date: str) -> str:
    """Minimal test email when no jobs found but force_email=true."""
    return f"""
    <!DOCTYPE html><html><body style="font-family:-apple-system,sans-serif;background:#f9fafb;padding:24px;">
      <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e5e7eb;">
        <div style="background:linear-gradient(135deg,#1d4ed8,#7c3aed);padding:28px 32px;color:#fff;">
          <div style="font-size:20px;font-weight:700;">✅ Job Search Bot — Test Successful</div>
          <div style="font-size:14px;opacity:.85;margin-top:4px;">{date}</div>
        </div>
        <div style="padding:24px 32px;">
          <p style="color:#374151;font-size:15px;">Your daily remote analyst job search bot is working correctly!</p>
          <p style="color:#6b7280;font-size:13px;">No new jobs matched your criteria today, but the bot ran successfully. 
          You'll receive real job listings in future emails when new postings appear.</p>
          <hr style="border:none;border-top:1px solid #e5e7eb;margin:20px 0;">
          <p style="color:#9ca3af;font-size:12px;">
            Search criteria: Business / Data / Systems Analyst · Fully Remote · Mid–Senior · $120k+/yr or $60+/hr<br>
            Sources: Dice, LinkedIn, Indeed
          </p>
        </div>
      </div>
    </body></html>
    """

def build_html(jobs: list, date: str, total_scraped: int) -> str:
    rows = ""
    for i, j in enumerate(jobs, 1):
        salary_html = (
            f'<span style="color:#16a34a;font-weight:bold;">{j["salary"]}</span>'
            if j.get("salary") else
            '<span style="color:#999;">Salary not listed — check posting</span>'
        )
        rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb;">
          <td style="padding:16px 0;">
            <div style="font-size:11px;color:#6b7280;margin-bottom:4px;">
              #{i} &nbsp; {badge(j['source'])} &nbsp;
              <span style="color:#9ca3af;">{j.get('date_posted','')}</span>
            </div>
            <div style="font-size:17px;font-weight:600;">
              <a href="{j['url']}" style="color:#1d4ed8;text-decoration:none;">{j['title']}</a>
            </div>
            <div style="font-size:14px;color:#374151;margin-top:2px;">
              {j['company']} &nbsp;·&nbsp; 🌐 Fully Remote
            </div>
            <div style="margin-top:6px;">{salary_html}</div>
            <div style="margin-top:10px;">
              <a href="{j['url']}" style="background:#1d4ed8;color:#fff;padding:6px 14px;
                border-radius:6px;text-decoration:none;font-size:13px;font-weight:600;display:inline-block;">
                View &amp; Apply →
              </a>
            </div>
          </td>
        </tr>"""

    return f"""
    <!DOCTYPE html><html><body style="font-family:-apple-system,sans-serif;background:#f9fafb;padding:24px;">
      <div style="max-width:640px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);">
        <div style="background:linear-gradient(135deg,#1d4ed8,#7c3aed);padding:28px 32px;color:#fff;">
          <div style="font-size:22px;font-weight:700;">🆕 {len(jobs)} New Remote Analyst Job{'s' if len(jobs)!=1 else ''}</div>
          <div style="font-size:14px;opacity:.85;margin-top:4px;">{date}</div>
        </div>
        <div style="background:#eff6ff;padding:12px 32px;font-size:13px;color:#1e40af;border-bottom:1px solid #dbeafe;">
          🔍 &nbsp; BA / DA / Systems Analyst &nbsp;·&nbsp; Fully Remote &nbsp;·&nbsp; Mid–Senior &nbsp;·&nbsp; $120k+/yr or $60+/hr
        </div>
        <div style="padding:0 32px;">
          <table style="width:100%;border-collapse:collapse;">{rows}</table>
        </div>
        <div style="background:#f3f4f6;padding:20px 32px;font-size:12px;color:#6b7280;text-align:center;">
          {total_scraped} total postings scanned · {len(jobs)} new today<br>
          <span style="color:#d1d5db;">No new results = no email.</span>
        </div>
      </div>
    </body></html>
    """

def send(subject: str, html: str):
    if not all([RESEND_API_KEY, TO_EMAIL, FROM_EMAIL]):
        missing = [k for k, v in {"RESEND_API_KEY": RESEND_API_KEY, "TO_EMAIL": TO_EMAIL, "FROM_EMAIL": FROM_EMAIL}.items() if not v]
        print(f"❌ Missing required env vars: {', '.join(missing)}")
        raise SystemExit(1)

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        json={"from": FROM_EMAIL, "to": [TO_EMAIL], "subject": subject, "html": html},
        timeout=15,
    )
    if resp.status_code in (200, 201):
        print(f"✅ Email sent! ID: {resp.json().get('id','')}")
    else:
        print(f"❌ Email failed ({resp.status_code}): {resp.text}")
        raise SystemExit(1)

def main():
    data = json.loads(NEW_JOBS_FILE.read_text()) if NEW_JOBS_FILE.exists() else {"jobs": [], "new_count": 0, "total_scraped": 0}
    jobs = data.get("jobs", [])
    total_scraped = data.get("total_scraped", 0)
    today_fmt = datetime.date.today().strftime("%B %d, %Y")

    if not jobs and FORCE_EMAIL:
        print("No new jobs, but FORCE_EMAIL=true — sending test confirmation email.")
        send(f"✅ Job Search Bot Test — {today_fmt}", build_test_html(today_fmt))
    elif not jobs:
        print("No new jobs — skipping email.")
    else:
        subject = f"🆕 {len(jobs)} New Remote Analyst Job{'s' if len(jobs)!=1 else ''} — {today_fmt}"
        send(subject, build_html(jobs, today_fmt, total_scraped))

if __name__ == "__main__":
    main()
