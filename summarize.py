"""
summarize.py — Prints a Markdown summary table for GitHub Actions Step Summary.
Appended to $GITHUB_STEP_SUMMARY after each run.
"""

import json
import datetime
from pathlib import Path

NEW_JOBS_FILE = Path("data/new_jobs.json")

def main():
    if not NEW_JOBS_FILE.exists():
        print("## ❌ Job Search — No output file found")
        return

    data = json.loads(NEW_JOBS_FILE.read_text())
    jobs  = data.get("jobs", [])
    date  = data.get("date", str(datetime.date.today()))
    total = data.get("total_scraped", "?")
    rel   = data.get("total_relevant", "?")
    new_n = len(jobs)

    print(f"## {'✅' if new_n > 0 else '💤'} Remote Analyst Job Search — {date}\n")
    print(f"| Metric | Count |")
    print(f"|---|---|")
    print(f"| Total scraped | {total} |")
    print(f"| After relevance filter | {rel} |")
    print(f"| **New (not seen before)** | **{new_n}** |")
    print(f"| Email sent | {'Yes' if new_n > 0 else 'No (nothing new)'} |")

    if jobs:
        print(f"\n### New Jobs Found\n")
        print(f"| # | Title | Company | Source | Salary |")
        print(f"|---|---|---|---|---|")
        for i, j in enumerate(jobs, 1):
            salary = j.get("salary") or "—"
            print(f"| {i} | {j['title']} | {j['company']} | {j['source_label']} | {salary} |")
    else:
        print(f"\n> No new jobs found today. Seen-jobs cache updated. No email sent.")

if __name__ == "__main__":
    main()
