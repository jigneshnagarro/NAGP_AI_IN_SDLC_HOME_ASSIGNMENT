"""Review-eval helper for ops/evals.

  python submission/04-review-eval/eval.py prepare            # write paste-ready prompt files + empty results.csv
  python submission/04-review-eval/eval.py run --model sonnet --prompt v1 --runs 1 2 3
  python submission/04-review-eval/eval.py run --model sonnet --prompt v2 --runs 4
  python submission/04-review-eval/eval.py score              # rates per run, written to results.md

`run` needs the Claude Code CLI (`claude`) on PATH. Each case runs in a fresh, empty temp
folder so no CLAUDE.md / AGENTS.md or earlier case leaks in. Without the CLI, use the
files from `prepare` and paste each one into a brand-new chat by hand.
Verdicts are scored by a human (you) in results.csv using answer-key.md.
"""
import argparse
import csv
import math
import pathlib
import re
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
CASES = sorted((REPO / "ops" / "evals" / "cases").glob("case-*.diff"))
RESULTS = REPO / "ops" / "evals" / "results.csv"
FIELDS = ["run", "case", "model", "prompt_version", "verdict", "finding_summary", "confidence_reported", "notes"]
VERDICTS = {"caught", "missed", "false_alarm", "clean_ok"}


def load_prompt(version):
    text = (HERE / "prompts.md").read_text(encoding="utf-8")
    match = re.search(rf"## {version} .*?\n\n(.*?)(?=\n## |\Z)", text, re.S)
    return match.group(1).strip()


def build_input(version, case_path):
    return f"{load_prompt(version)}\n\n```diff\n{case_path.read_text(encoding='utf-8')}\n```\n"


def prepare(_args):
    for version in ("v1", "v2"):
        out_dir = HERE / "prompts" / version
        out_dir.mkdir(parents=True, exist_ok=True)
        for case_path in CASES:
            (out_dir / f"{case_path.stem}.txt").write_text(build_input(version, case_path), encoding="utf-8")
    if not RESULTS.exists():
        with RESULTS.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for run, version in ((1, "v1"), (2, "v1"), (3, "v1"), (4, "v2")):
                for case_path in CASES:
                    writer.writerow({"run": run, "case": case_path.stem, "prompt_version": version})
    print(f"Prompt files in {HERE / 'prompts'}; results sheet at {RESULTS}")


def run(args):
    for run_number in args.runs:
        out_dir = HERE / "raw" / f"run-{run_number}-{args.prompt}"
        out_dir.mkdir(parents=True, exist_ok=True)
        for case_path in CASES:
            with tempfile.TemporaryDirectory() as empty_dir:
                completed = subprocess.run(
                    ["claude", "-p", "--model", args.model],
                    input=build_input(args.prompt, case_path),
                    capture_output=True, text=True, encoding="utf-8", cwd=empty_dir, shell=False,
                )
            (out_dir / f"{case_path.stem}.md").write_text(completed.stdout or completed.stderr, encoding="utf-8")
            print(f"run {run_number} {case_path.stem}: {len(completed.stdout)} chars")


def wilson(successes, total, z=1.96):
    if total == 0:
        return (0.0, 0.0)
    rate = successes / total
    centre = (rate + z * z / (2 * total)) / (1 + z * z / total)
    margin = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def score(_args):
    rows = list(csv.DictReader(RESULTS.open(encoding="utf-8")))
    bad = [r for r in rows if r["verdict"] not in VERDICTS]
    if bad:
        print(f"WARNING: {len(bad)} rows have no valid verdict (use {sorted(VERDICTS)}); they are skipped.")
    groups = {}
    for row in rows:
        if row["verdict"] in VERDICTS:
            groups.setdefault((row["run"], row["prompt_version"], row["model"]), []).append(row["verdict"])
    groups[("1-3 combined", "v1", "")] = [
        r["verdict"] for r in rows if r["prompt_version"] == "v1" and r["verdict"] in VERDICTS]

    lines = ["| Run | Prompt | Model | Caught | Missed | False alarm | Catch rate (95% CI) | False-alarm rate (95% CI) |",
             "|---|---|---|---|---|---|---|---|"]
    for (run_label, prompt, model), verdicts in groups.items():
        caught, missed = verdicts.count("caught"), verdicts.count("missed")
        false_alarm, clean_ok = verdicts.count("false_alarm"), verdicts.count("clean_ok")
        defects, cleans = caught + missed, false_alarm + clean_ok
        catch_low, catch_high = wilson(caught, defects)
        fa_low, fa_high = wilson(false_alarm, cleans)
        lines.append(
            f"| {run_label} | {prompt} | {model} | {caught}/{defects} | {missed}/{defects} | {false_alarm}/{cleans} | "
            f"{caught / defects if defects else 0:.0%} ({catch_low:.0%}-{catch_high:.0%}) | "
            f"{false_alarm / cleans if cleans else 0:.0%} ({fa_low:.0%}-{fa_high:.0%}) |")
    table = "\n".join(lines)
    (HERE / "results.md").write_text("# Eval results (generated by eval.py score)\n\n" + table + "\n", encoding="utf-8")
    print(table)


parser = argparse.ArgumentParser()
sub = parser.add_subparsers(required=True)
sub.add_parser("prepare").set_defaults(func=prepare)
run_parser = sub.add_parser("run")
run_parser.add_argument("--model", default="sonnet")
run_parser.add_argument("--prompt", default="v1", choices=["v1", "v2"])
run_parser.add_argument("--runs", nargs="+", type=int, default=[1, 2, 3])
run_parser.set_defaults(func=run)
sub.add_parser("score").set_defaults(func=score)
parsed = parser.parse_args()
parsed.func(parsed)
