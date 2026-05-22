"""
search.py — Daily remote analyst job search
Searches Dice, LinkedIn, and Indeed via SerpAPI (Google Jobs engine).
Falls back to Indeed RSS if SERP_API_KEY is not set.
Deduplicates against data/seen_jobs.json and writes data/new_jobs.json.
"""

import os
import json
import hashlib
import datetime
import requests
import feedparser
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────

SEARCH_TITLES = [
    "Business Analyst",
    "Data Analyst",
    "Systems Analyst",
]

SALARY_KEYWORDS = [
    "$120", "$125", "$130", "$135", "$140", "$145", "$150",
    "$155", "$160", "$165", "$170", "$175", "$180",
    "$60/hr", "$65/hr", "$70/hr", "$75/hr", "$80/hr",
    "$85/hr", "$90/hr", "$95/hr", "$100/hr",
    "120,000", "130,000", "140,000", "150,000", "160,000",
]

EXCLUDE_LEVELS = [
    "entry level", "entry-level", "junior", "associate",
    "intern", "internship", "co-op", "graduate", "0-2 years",
]

REMOTE_KEYWORDS = [
    "remote", "work from home", "wfh", "fully remote", "100% remote",
]

TARGET_SITES = ["dice.com", "linkedin.com", "indeed.com"]

DATA_DIR = Path("data")
SEEN_JOBS_FILE = DATA_DIR / "seen_jobs.json"
NEW_JOBS_FILE = DATA_DIR / "new_jobs.json"

SERP_API_KEY = os.environ.get("SERP_API_KEY", "")

# ── Helpers ────────────────────────────────────────────────────────────────

def make_id(url: str) -> str:
    """Stable hash of the job URL used as dedup key."""
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]

def load_seen() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    if SEEN_JOBS_FILE.exists():
        return json.loads(SEEN_JOBS_FILE.read_text())
    return {}

def save_seen(seen: dict):
    SEEN_JOBS_FILE.write_text(json.dumps(seen, indent=2))

def is_relevant(job: dict) -> bool:
    """Return True if job passes all quality filters."""
    text = f"{job.get('title','')} {job.get('description','')}".lower()

    # Must mention remote work
    if not any(kw in text for kw in REMOTE_KEYWORDS):
        return False

    # Must not be entry-level
    if any(kw in text for kw in EXCLUDE_LEVELS):
        return False

    # Must mention salary in range (or no salary info — keep and let user decide)
    has_salary_info = any(kw.lower() in text for kw in SALARY_KEYWORDS)
    explicit_low_salary = any(
        f"${n}," in text or f"${n}k" in text
        for n in ["40", "45", "50", "55", "60", "65", "70", "75", "80", "85", "90", "95"]
    )
    if explicit_low_salary and not has_salary_info:
        return False

    return True

# ── SerpAPI search ─────────────────────────────────────────────────────────

def search_serpapi(title: str, site: str) -> list[dict]:
    """Query Google Jobs via SerpAPI for a specific title + site."""
    params = {
        "engine": "google_jobs",
        "q": f'"{title}" remote site:{site}',
        "chips": "date_posted:today,work_from_home:1",
        "api_key": SERP_API_KEY,
        "num": 10,
    }
    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = []
        for item in data.get("jobs_results", []):
            salary_raw = ""
            for ext in item.get("detected_extensions", {}).get("salary", []):
                salary_raw = ext
                break
            results.append({
                "id": make_id(item.get("share_link", item.get("title", ""))),
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "url": item.get("share_link", ""),
                "description": item.get("description", ""),
                "salary": salary_raw,
                "date_posted": item.get("detected_extensions", {}).get("posted_at", ""),
                "source": site.replace(".com", ""),
                "source_label": site.split(".")[0].title(),
            })
        return results
    except Exception as e:
        print(f"  ⚠ SerpAPI error for {title} @ {site}: {e}")
        return []

# ── Indeed RSS fallback ────────────────────────────────────────────────────

def search_indeed_rss(title: str) -> list[dict]:
    """Free fallback using Indeed's RSS feed (no API key needed)."""
    url = (
        f"https://www.indeed.com/rss"
        f"?q={title.replace(' ', '+')}&l=remote&sort=date&fromage=1&jt=fulltime"
    )
    try:
        feed = feedparser.parse(url)
        results = []
        for entry in feed.entries:
            results.append({
                "id": make_id(entry.get("link", entry.get("title", ""))),
                "title": entry.get("title", ""),
                "company": entry.get("author", ""),
                "url": entry.get("link", ""),
                "description": entry.get("summary", ""),
                "salary": "",
                "date_posted": entry.get("published", ""),
                "source": "indeed",
                "source_label": "Indeed",
            })
        return results
    except Exception as e:
        print(f"  ⚠ Indeed RSS error for {title}: {e}")
        return []

# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print(f"\n🔍 Job search starting — {datetime.date.today()}")
    seen = load_seen()
    all_scraped = []

    for title in SEARCH_TITLES:
        print(f"\n  Searching: {title}")
        if SERP_API_KEY:
            for site in TARGET_SITES:
                print(f"    → {site} (SerpAPI)")
                jobs = search_serpapi(title, site)
                all_scraped.extend(jobs)
                print(f"       {len(jobs)} results")
        else:
            print(f"    → Indeed RSS (no SERP_API_KEY set)")
            jobs = search_indeed_rss(title)
            all_scraped.extend(jobs)
            print(f"       {len(jobs)} results")

    print(f"\n  Total scraped: {len(all_scraped)}")

    # Filter for relevance
    relevant = [j for j in all_scraped if is_relevant(j)]
    print(f"  After relevance filter: {len(relevant)}")

    # Deduplicate
    new_jobs = []
    for job in relevant:
        jid = job["id"]
        if jid not in seen:
            new_jobs.append(job)
            seen[jid] = {
                "title": job["title"],
                "company": job["company"],
                "source": job["source"],
                "date_seen": str(datetime.date.today()),
                "url": job["url"],
            }

    print(f"  New (not seen before): {len(new_jobs)}")

    # Save
    save_seen(seen)
    output = {
        "date": str(datetime.date.today()),
        "total_scraped": len(all_scraped),
        "total_relevant": len(relevant),
        "new_count": len(new_jobs),
        "jobs": new_jobs,
    }
    NEW_JOBS_FILE.write_text(json.dumps(output, indent=2))
    print(f"\n✅ Done — {len(new_jobs)} new job(s) written to {NEW_JOBS_FILE}\n")

if __name__ == "__main__":
    main()
