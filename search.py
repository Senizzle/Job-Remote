"""
search.py — Daily remote analyst job search
Searches Dice, LinkedIn, and Indeed via SerpAPI.
Deduplicates against seen_jobs.json and writes new_jobs.json.
"""

import os
import json
import hashlib
import requests
from datetime import date

# ── Configuration ─────────────────────────────────────────────────────────────

SERP_API_KEY = os.environ["SERP_API_KEY"]

SEARCH_TITLES = [
    "Business Analyst",
    "Data Analyst",
    "Systems Analyst",
]

# Sites to filter results to (matched against job listing URLs)
TARGET_SITES = ["dice.com", "linkedin.com", "indeed.com"]

# Salary keywords to look for in listings (case-insensitive)
SALARY_KEYWORDS = [
    "$120", "$125", "$130", "$135", "$140", "$145", "$150",
    "$155", "$160", "$165", "$170", "$175", "$180", "$185",
    "$190", "$195", "$200",
    "120,000", "130,000", "140,000", "150,000", "160,000",
    "170,000", "180,000", "190,000", "200,000",
    "$60/hr", "$65/hr", "$70/hr", "$75/hr", "$80/hr",
    "$85/hr", "$90/hr", "$95/hr", "$100/hr",
    "60 per hour", "65 per hour", "70 per hour",
]

# Terms that indicate entry-level (skip these)
EXCLUDE_LEVELS = [
    "entry level", "entry-level", "junior", "jr.", "jr ",
    "associate analyst", "intern", "internship", "co-op",
]

# Paths
SEEN_JOBS_PATH  = "data/seen_jobs.json"
NEW_JOBS_PATH   = "data/new_jobs.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_seen_jobs() -> dict:
    """Load the dict of previously seen job IDs."""
    try:
        with open(SEEN_JOBS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_seen_jobs(seen: dict) -> None:
    with open(SEEN_JOBS_PATH, "w") as f:
        json.dump(seen, f, indent=2)

def job_id(job: dict) -> str:
    """Stable hash from URL (or title+company as fallback)."""
    key = job.get("url") or f"{job.get('title','')}-{job.get('company','')}"
    return hashlib.md5(key.encode()).hexdigest()

def is_remote(job: dict) -> bool:
    text = " ".join([
        job.get("title", ""),
        job.get("location", ""),
        job.get("description", ""),
    ]).lower()
    return any(kw in text for kw in ["remote", "work from home", "wfh", "anywhere"])

def has_target_salary(job: dict) -> bool:
    text = " ".join([
        job.get("salary", ""),
        job.get("description", ""),
        job.get("snippet", ""),
    ]).lower()
    return any(kw.lower() in text for kw in SALARY_KEYWORDS)

def is_senior_level(job: dict) -> bool:
    text = " ".join([
        job.get("title", ""),
        job.get("description", ""),
        job.get("snippet", ""),
    ]).lower()
    return not any(kw in text for kw in EXCLUDE_LEVELS)

def source_label(url: str) -> tuple[str, str]:
    """Return (source_key, display_label) based on URL."""
    if "dice.com"     in url: return "dice",     "Dice"
    if "linkedin.com" in url: return "linkedin", "LinkedIn"
    if "indeed.com"   in url: return "indeed",   "Indeed"
    return "other", "Other"

# ── SerpAPI search ────────────────────────────────────────────────────────────

def search_google_jobs(title: str) -> list[dict]:
    """
    Use SerpAPI's Google Jobs engine to find postings for a given job title.
    Returns a list of normalized job dicts.
    """
    params = {
        "engine":        "google_jobs",
        "q":             f"{title} remote",
        "location":      "United States",
        "hl":            "en",
        "chips":         "date_posted:today",   # last 24h; change to 'week' if too few results
        "api_key":       SERP_API_KEY,
    }

    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [WARN] SerpAPI request failed for '{title}': {e}")
        return []

    jobs = []
    for item in data.get("jobs_results", []):
        # Try to find a Dice/LinkedIn/Indeed URL in the apply links
        apply_links = item.get("apply_options", [])
        url = ""
        for link in apply_links:
            href = link.get("link", "")
            if any(site in href for site in TARGET_SITES):
                url = href
                break
        # Fall back to the first apply link if no target site found
        if not url and apply_links:
            url = apply_links[0].get("link", "")

        # Skip if none of the apply links point to our target sites
        if not any(site in url for site in TARGET_SITES):
            continue

        source_key, source_display = source_label(url)

        salary = ""
        salary_info = item.get("detected_extensions", {})
        if "salary" in salary_info:
            salary = salary_info["salary"]

        jobs.append({
            "title":        item.get("title", ""),
            "company":      item.get("company_name", ""),
            "location":     item.get("location", "Remote"),
            "description":  item.get("description", ""),
            "salary":       salary,
            "url":          url,
            "source":       source_key,
            "source_label": source_display,
            "date_posted":  item.get("detected_extensions", {}).get("posted_at", str(date.today())),
        })

    return jobs

# ── Indeed RSS fallback (no API key needed) ───────────────────────────────────

def search_indeed_rss(title: str) -> list[dict]:
    """
    Free fallback using Indeed's RSS feed.
    Less reliable than SerpAPI but costs nothing.
    """
    import feedparser
    query = title.replace(" ", "+")
    url = (
        f"https://www.indeed.com/rss?q={query}"
        f"&l=remote&sort=date&fromage=1&jt=fulltime"
    )
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"  [WARN] Indeed RSS failed for '{title}': {e}")
        return []

    jobs = []
    for entry in feed.entries:
        jobs.append({
            "title":        entry.get("title", ""),
            "company":      entry.get("author", ""),
            "location":     "Remote",
            "description":  entry.get("summary", ""),
            "salary":       "",   # RSS rarely includes salary
            "url":          entry.get("link", ""),
            "source":       "indeed",
            "source_label": "Indeed",
            "date_posted":  str(date.today()),
        })
    return jobs

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.makedirs("data", exist_ok=True)

    seen = load_seen_jobs()
    all_jobs: list[dict] = []

    for title in SEARCH_TITLES:
        print(f"\n→ Searching: {title}")
        results = search_google_jobs(title)

        # If SerpAPI returns nothing (quota hit etc.), fall back to Indeed RSS
        if not results:
            print(f"  SerpAPI returned 0 results — trying Indeed RSS fallback")
            results = search_indeed_rss(title)

        print(f"  {len(results)} raw results")
        all_jobs.extend(results)

    # Deduplicate within this run
    unique: dict[str, dict] = {}
    for job in all_jobs:
        jid = job_id(job)
        if jid not in unique:
            unique[jid] = job

    # Filter: remote + salary + not entry-level
    filtered = [
        j for j in unique.values()
        if is_remote(j) and is_senior_level(j) and (has_target_salary(j) or not j["salary"])
        # Note: if salary field is empty we include it and let the email recipient judge.
        # Set `and has_target_salary(j)` if you want strict salary filtering.
    ]

    print(f"\n✓ {len(filtered)} jobs after filtering")

    # Find truly NEW jobs (not in seen_jobs)
    new_jobs = []
    for job in filtered:
        jid = job_id(job)
        if jid not in seen:
            new_jobs.append(job)
            seen[jid] = {
                "title":     job["title"],
                "company":   job["company"],
                "source":    job["source"],
                "date_seen": str(date.today()),
                "url":       job["url"],
            }

    print(f"★ {len(new_jobs)} NEW jobs (not previously seen)")

    # Save outputs
    save_seen_jobs(seen)
    with open(NEW_JOBS_PATH, "w") as f:
        json.dump(new_jobs, f, indent=2)

    print(f"\nWrote {NEW_JOBS_PATH}")

if __name__ == "__main__":
    main()
