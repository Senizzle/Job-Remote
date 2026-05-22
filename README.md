# 🔍 Remote Analyst Job Search Bot

Automated daily job search for **Business Analyst, Data Analyst, and Systems Analyst** roles that are:
- ✅ **Fully Remote** only
- ✅ **Mid-to-Senior** level
- ✅ **$120,000+/yr** or **$60+/hr**
- ✅ Posted on **Dice, LinkedIn, or Indeed**

Runs every weekday at 8am ET via GitHub Actions. Sends you an email digest **only when there are new postings** you haven't seen before.

---

## ⚡ Quick Setup (5 steps, ~10 minutes)

### 1. Get a SerpAPI key
Sign up at [serpapi.com](https://serpapi.com) — the free trial gives you 100 searches.  
The Hobby plan ($50/mo) covers ~200 searches/month (9 searches/day × 22 weekdays).

> **Free alternative**: The bot automatically falls back to the Indeed RSS feed if SerpAPI fails or runs out of quota. Results are less reliable but cost nothing.

### 2. Get a Resend key
Sign up at [resend.com](https://resend.com) — free tier is 3,000 emails/month.  
Verify your sending domain (or use `onboarding@resend.dev` for testing).

### 3. Add GitHub Secrets
In this repo go to **Settings → Secrets and variables → Actions → New repository secret**:

| Secret Name | Where to get it |
|---|---|
| `SERP_API_KEY` | [serpapi.com](https://serpapi.com) dashboard |
| `RESEND_API_KEY` | [resend.com](https://resend.com) dashboard |
| `TO_EMAIL` | Your email address (where to receive digests) |
| `FROM_EMAIL` | Your verified sender in Resend (e.g. `jobs@yourdomain.com`) |

### 4. Enable Actions
Go to the **Actions** tab → click **"I understand my workflows, go ahead and enable them"**

### 5. Test it now
Actions → **Daily Remote Analyst Job Search** → **Run workflow** → check ✅ "Send email even if no new jobs" → **Run workflow**

---

## 📁 File Structure

```
.github/workflows/daily-job-search.yml  ← Scheduler & orchestration
scripts/
  search.py        ← Scrapes jobs, filters, deduplicates
  send_email.py    ← Builds and sends HTML email digest
  requirements.txt ← Python dependencies
data/              ← Auto-created at runtime (not committed)
  seen_jobs.json   ← Tracks all previously seen job IDs (cached between runs)
  new_jobs.json    ← Today's new jobs (uploaded as downloadable artifact)
```

---

## ⏰ Schedule

Runs **Monday–Friday at 8:00am ET** by default.

To change it, edit the cron line in `.github/workflows/daily-job-search.yml`:

```yaml
- cron: '0 13 * * 1-5'   # 8am ET (UTC−5 = 13:00 UTC), Mon–Fri
```

Use [crontab.guru](https://crontab.guru) to build a custom schedule.

---

## 🔧 Customization

**Add more job titles** — edit `SEARCH_TITLES` in `scripts/search.py`:
```python
SEARCH_TITLES = [
    "Business Analyst",
    "Data Analyst",
    "Systems Analyst",
    "Product Analyst",    # ← add more here
]
```

**Tighten salary filtering** — in `search.py`, change:
```python
if is_remote(j) and is_senior_level(j) and (has_target_salary(j) or not j["salary"])
```
to:
```python
if is_remote(j) and is_senior_level(j) and has_target_salary(j)
```

**Exclude companies** — add a check in the filter loop in `main()`:
```python
EXCLUDE_COMPANIES = ["Company A", "Company B"]
# then add: and job["company"] not in EXCLUDE_COMPANIES
```

---

## 📊 Monitoring

After each run, check the **Actions** tab:
- **Summary tab** — table of new jobs found today
- **Artifacts** — download `job-results-[run-id].zip` for raw JSON
- **Logs** — click any step for detailed output

---

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| No email received | Check spam; verify `FROM_EMAIL` is confirmed in Resend |
| 0 jobs every run | Broaden `SALARY_KEYWORDS` or switch to `fromage=3` (last 3 days) in the RSS URL |
| `SERP_API_KEY` error | Secret names are case-sensitive — check exact spelling |
| Too many irrelevant jobs | Add more terms to `EXCLUDE_LEVELS` in `search.py` |
| Seen jobs not persisting | Don't rename the `runs-on: ubuntu-latest` line — the cache key depends on it |
