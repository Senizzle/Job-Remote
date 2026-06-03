import os, json, datetime, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

GMAIL_USER     = os.environ.get("GMAIL_USER", "")
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
TO_EMAIL       = os.environ.get("TO_EMAIL", "")
FORCE_EMAIL    = os.environ.get("FORCE_EMAIL", "false").lower() == "true"
NEW_JOBS_FILE  = Path("data/new_jobs.json")

def send(subject, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = TO_EMAIL
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_PASSWORD)
        s.sendmail(GMAIL_USER, TO_EMAIL, msg.as_string())
    print(f"Email sent to {TO_EMAIL}")

def main():
    data = json.loads(NEW_JOBS_FILE.read_text()) if NEW_JOBS_FILE.exists() else {"jobs": [], "total_scraped": 0}
    jobs = data.get("jobs", [])
    today = datetime.date.today().strftime("%B %d, %Y")
    if jobs:
        send(f"New Remote Analyst Jobs - {today}", f"<h2>{len(jobs)} new jobs found</h2>" + "".join(f"<p><a href='{j['url']}'>{j['title']} @ {j['company']}</a></p>" for j in jobs))
    elif FORCE_EMAIL:
        send(f"Job Search Bot Test - {today}", "<h2>Test successful!</h2><p>Bot is running. No new jobs today.</p>")
    else:
        print("No new jobs - skipping email.")

if __name__ == "__main__":
    main()
