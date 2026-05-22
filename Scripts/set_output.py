import json, os

data = json.load(open("data/new_jobs.json"))
count = data["new_count"]

with open(os.environ["GITHUB_OUTPUT"], "a") as f:
    f.write(f"new_count={count}\n")

print(f"Found {count} new job(s)")
