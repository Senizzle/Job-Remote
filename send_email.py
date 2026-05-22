"""
send_email.py — Format and send the daily job digest via Resend.
Reads new_jobs.json and sends an HTML email only when jobs exist.
"""

import os
import json
import requests
from datetime import date

# ── Config ────────────────────────────────────────────────────────────────────

RESEND_API_KEY = os.environ["RESEND_API_KEY"]
TO_EMAIL       = os.environ["TO_EMAIL"]
FROM_EMAIL     = os.environ["FROM_EMAIL"]
NEW_JOBS_PATH  = "data/new_jobs.json"

# Source badge colors
SOURCE_COLORS = {
    "dice":     "#0073E6",
    "linkedin": "#0A66C2",
    "indeed":   "#2D2D87",
}

# ── Email builder ─────────────────────────────────────────────────────────────

def build_email(jobs: list[dict]) -> tuple[str, str]:
    """Return (subject, html_body)."""

    today = date.today().strftime("%B %d, %Y")
    count = len(jobs)
    subject = f"🆕 {count} New Remote Analyst Job{'s' if count != 1 else ''} — {today}"

    # Build job cards HTML
    cards_html = ""
    for i, job in enumerate(jobs, 1):
        title        = job.get("title", "Unknown Title")
        company      = job.get("company", "Unknown Company")
        source       = job.get("source", "other")
        source_label = job.get("source_label", source.capitalize())
        salary       = job.get("salary") or "Salary not listed"
        posted       = job.get("date_posted", str(date.today()))
        url          = job.get("url", "#")
        color        = SOURCE_COLORS.get(source, "#555555")

        cards_html += f"""
        <tr>
          <td style="padding: 20px 0; border-bottom: 1px solid #e5e7eb;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <span style="background:{color};color:#fff;font-size:11px;font-weight:600;
                               padding:3px 8px;border-radius:4px;text-transform:uppercase;
                               letter-spacing:0.5px;">{source_label}</span>
                  &nbsp;
                  <span style="background:#dcfce7;color:#166534;font-size:11px;font-weight:600;
                               padding:3px 8px;border-radius:4px;">🌐 Remote</span>
                </td>
              </tr>
              <tr>
                <td style="padding-top:8px;">
                  <a href="{url}" style="font-size:18px;font-weight:700;color:#111827;
                                         text-decoration:none;">{i}. {title}</a>
                </td>
              </tr>
              <tr>
                <td style="padding-top:4px;font-size:14px;color:#6b7280;">
                  {company} &nbsp;·&nbsp; {salary} &nbsp;·&nbsp; Posted: {posted}
                </td>
              </tr>
              <tr>
                <td style="padding-top:12px;">
                  <a href="{url}"
                     style="display:inline-block;background:#2563eb;color:#fff;
                            font-size:13px;font-weight:600;padding:8px 18px;
                            border-radius:6px;text-decoration:none;">
                    View &amp; Apply →
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <title>{subject}</title>
    </head>
    <body style="margin:0;padding:0;background:#f9fafb;font-family:-apple-system,BlinkMacSystemFont,
                 'Segoe UI',sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:32px 0;">
        <tr>
          <td align="center">
            <table width="600" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:12px;overflow:hidden;
                          box-shadow:0 1px 3px rgba(0,0,0,.1);">

              <!-- Header -->
              <tr>
                <td style="background:#1e40af;padding:28px 32px;">
                  <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;">
                    🔍 Remote Analyst Job Alert
                  </h1>
                  <p style="margin:6px 0 0;color:#bfdbfe;font-size:14px;">
                    {count} new posting{'s' if count != 1 else ''} found — {today}
                  </p>
                </td>
              </tr>

              <!-- Criteria bar -->
              <tr>
                <td style="background:#eff6ff;padding:12px 32px;font-size:12px;color:#3730a3;
                           border-bottom:1px solid #dbeafe;">
                  <strong>Search criteria:</strong>
                  Business / Data / Systems Analyst &nbsp;·&nbsp;
                  Fully Remote &nbsp;·&nbsp;
                  $120k+/yr or $60+/hr &nbsp;·&nbsp;
                  Mid–Senior Level &nbsp;·&nbsp;
                  Dice · LinkedIn · Indeed
                </td>
              </tr>

              <!-- Job cards -->
              <tr>
                <td style="padding:8px 32px 0;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    {cards_html}
                  </table>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="padding:24px 32px;border-top:1px solid #f3f4f6;
                           font-size:12px;color:#9ca3af;text-align:center;">
                  You're receiving this because you set up a daily remote analyst job search.<br>
                  Sent automatically via GitHub Actions · Powered by Claude
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    return subject, html

# ── Send via Resend ───────────────────────────────────────────────────────────

def send_email(subject: str, html: str) -> None:
    payload = {
        "from":    FROM_EMAIL,
        "to":      [TO_EMAIL],
        "subject": subject,
        "html":    html,
    }

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type":  "application/json",
        },
        json=payload,
        timeout=15,
    )

    if resp.status_code == 200:
        print(f"✓ Email sent to {TO_EMAIL}")
    else:
        print(f"✗ Email failed: {resp.status_code} — {resp.text}")
        raise SystemExit(1)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    try:
        with open(NEW_JOBS_PATH) as f:
            jobs = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("No new_jobs.json found or it is empty — nothing to send.")
        return

    if not jobs:
        print("0 new jobs — skipping email.")
        return

    print(f"Sending digest for {len(jobs)} new job(s)…")
    subject, html = build_email(jobs)
    send_email(subject, html)

if __name__ == "__main__":
    main()
