"""Export curated job data to web/data/jobs.json for the static frontend."""

from __future__ import annotations

import json
import os
from datetime import date

from jobs_data import JOBS
from jobs_remote_global import JOBS_REMOTE_GLOBAL
from profile import PROFILE


def main():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out_dir = os.path.join(repo_root, "web", "data")
    os.makedirs(out_dir, exist_ok=True)

    payload = {
        "generated_on": date.today().isoformat(),
        "profile": PROFILE,
        "india_jobs": [{**j, "scope": "India"} for j in JOBS],
        "remote_jobs": [{**j, "scope": "Worldwide Remote"} for j in JOBS_REMOTE_GLOBAL],
    }

    out_path = os.path.join(out_dir, "jobs.json")
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote {out_path}")
    print(f"  India:  {len(payload['india_jobs'])} roles")
    print(f"  Remote: {len(payload['remote_jobs'])} roles")


if __name__ == "__main__":
    main()
