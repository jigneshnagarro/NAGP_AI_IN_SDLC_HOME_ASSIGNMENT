"""Capture the two baseline numbers available today from the repo and its CI history.

  python submission/05-risk-and-measurement/capture_baseline.py

Source: ops/pipeline/run-timings.csv (last 20 runs of the production pipeline, one row per step)
        and `git log` of this repository.
"""
import csv
import pathlib
import statistics
import subprocess
from collections import OrderedDict
from datetime import datetime

REPO = pathlib.Path(__file__).resolve().parents[2]
TIMINGS = REPO / "ops" / "pipeline" / "run-timings.csv"


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


runs = OrderedDict()
for row in csv.DictReader(TIMINGS.open(encoding="utf-8")):
    run = runs.setdefault(row["run_number"], {
        "started": parse_time(row["started_at"]), "branch": row["branch"], "event": row["event"],
        "conclusion": row["conclusion"], "seconds": 0, "steps": 0})
    run["seconds"] += int(row["duration_seconds"])
    run["steps"] += 1

all_runs = list(runs.values())
minutes = sorted(run["seconds"] / 60 for run in all_runs)
failed = [run for run in all_runs if run["conclusion"] == "failure"]
pr_runs = [run for run in all_runs if run["event"] == "pull_request"]
main_runs = [run for run in all_runs if run["event"] == "push"]

print("== Number 1: CI pipeline duration (the build/test part of lead time for changes)")
print(f"runs: {len(all_runs)}  window: {all_runs[0]['started']:%Y-%m-%d} to {all_runs[-1]['started']:%Y-%m-%d}")
print(f"median: {statistics.median(minutes):.1f} min   p90: {minutes[int(0.9 * len(minutes)) - 1]:.1f} min   "
      f"min: {minutes[0]:.1f}   max: {minutes[-1]:.1f}")

print("\n== Number 2: CI run failure rate")
print(f"all runs: {len(failed)}/{len(all_runs)} = {len(failed) / len(all_runs):.0%}")
print(f"pull_request: {sum(r in failed for r in pr_runs)}/{len(pr_runs)}   "
      f"main push: {sum(r in failed for r in main_runs)}/{len(main_runs)}")
for run in failed:
    print(f"  failed: {run['started']:%Y-%m-%d %H:%M} {run['branch']} ({run['steps']} of 19 steps recorded)")

print("\n== Proxy: branch first-PR-run -> next main push (lead time, rough)")
for branch in OrderedDict.fromkeys(r["branch"] for r in pr_runs):
    branch_runs = [r for r in pr_runs if r["branch"] == branch]
    last_pr = branch_runs[-1]["started"]
    next_main = next((r["started"] for r in main_runs if r["started"] > last_pr), None)
    if next_main:
        hours = (next_main - branch_runs[0]["started"]).total_seconds() / 3600
        print(f"  {branch}: {hours:.1f} h  ({len(branch_runs)} PR runs)")
    else:
        print(f"  {branch}: no later main push in window")

print("\n== Git history of this repository")
log = subprocess.run(["git", "log", "--format=%ad|%an|%s", "--date=iso-strict"],
                     cwd=REPO, capture_output=True, text=True).stdout.strip().splitlines()
merges = subprocess.run(["git", "log", "--merges", "--oneline"], cwd=REPO, capture_output=True, text=True).stdout
print(f"commits on main: {len(log)}   merge commits (PRs): {len(merges.splitlines())}")
for line in log:
    print("  " + line)
