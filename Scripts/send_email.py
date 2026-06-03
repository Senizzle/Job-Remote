import os, json, datetime, requests
from pathlib import Path

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
TO_EMAIL       = os.environ.get("TO_EMAIL", "")
FROM_EMAIL     = os.environ.get("FROM_EMAIL", "")
FORCE_EMAIL    = os.environ.get("FORCE_EMAIL", "false").lower() == "true"
NEW_JOBS_FILE  = Path("data/new_jobs.json")

def send(subject, html):
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
        json={"from": FROM_EMAIL, "to": [TO_EMAIL], "subject": subject, "html": html},
        timeout=15,
    )
    if resp.status_code in (200, 201):
        print(f"Email sent! ID: {resp.json().get('id','')}")
    else:
        print(f"Email failed ({resp.status_code}): {resp.text}")
        raise SystemExit(1)

def main():
    data = json.loads(NEW_JOBS_FILE.read_text()) if NEW_JOBS_FILE.exists() else {"jobs": [], "total_scraped": 0}
    jobs = data.get("jobs", [])
    today = datetime.date.today().strftime("%B %d, %Y")
    if jobs:
        send(f"New Remote Analyst Jobs - {today}", "<h2>" + str(len(jobs)) + " new jobs</h2>" + "".join(f"<p><a href='{j['url']}'>{j['title']} @ {j['company']}</a></p>" for j in jobs))
    elif FORCE_EMAIL:
        send(f"Job Search Bot Test - {today}", "<h2>Test successful!</h2><p>Bot is running. No new jobs today.</p>")
    else:
        print("No new jobs - skipping email.")

if __name__ == "__main__":
    main()
