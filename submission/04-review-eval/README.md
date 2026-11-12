# Task 4: Review eval

## Files

| File | |
|---|---|
| `ops/evals/cases/case-11.diff` | Added case, has a defect: `DecidedAt` and a month-end cut-off switched from `DateTime.UtcNow` to `DateTime.Now` |
| `ops/evals/cases/case-12.diff` | Added case, clean: `"Bearer "` pulled into a constant in `AuthController` |
| `prompts.md` | v1 (the prompt from `ops/evals/README.md`, unchanged) and v2 |
| `answer-key.md` | What counts as caught for each case |
| `raw/run-N-vX/case-NN.md` | All 48 reviewer outputs, unedited |
| `ops/evals/results.csv` | One row per case per run |
| `eval.py` | `prepare` builds the prompt files, `run` calls the `claude` CLI, `score` builds the table |

Why case 11: local time in an audit timestamp is a common real-world bug. It's easy to miss because cloud hosts run in UTC,
so it only shows up somewhere else (a dev machine, a different region, DST).

## Setup

- Model: Claude Sonnet (`claude-sonnet-5-5`), one new sub-agent session per case, 48 in total.
- Each session got one file: the prompt followed by the diff.
- Runs 1–3 used v1. Run 4 used v2. The model didn't change, so the prompt is the only variable.
- v2 = v1 + a checklist (authz, null input, injection, races, swallowed exceptions/status codes, money/rounding, time zones,
  secrets in logs) + "only report a defect if you can quote the changed line" + "style notes aren't defects".

## Results

| Run | Prompt | Caught | Missed | False alarm | Catch rate (95% CI) | False alarm rate (95% CI) |
|---|---|---|---|---|---|---|
| 1 | v1 | 9/9 | 0/9 | 0/3 | 100% (70–100) | 0% (0–56) |
| 2 | v1 | 9/9 | 0/9 | 0/3 | 100% (70–100) | 0% (0–56) |
| 3 | v1 | 9/9 | 0/9 | 0/3 | 100% (70–100) | 0% (0–56) |
| 1–3 | v1 | 27/27 | 0/27 | 0/9 | 100% (88–100) | 0% (0–30) |
| 4 | v2 | 8/9 | 1/9 | 0/3 | 89% (56–98) | 0% (0–56) |

Intervals are Wilson 95%. To regenerate: `python submission/04-review-eval/eval.py score`

## What I take from it

**v2 wasn't an improvement.** It found everything v1 found except case 09. That's the README change saying "sign out and
sign in again" resets the sample data, which is false: the repository is a singleton seeded once, and login only creates a
session. All three v1 runs flagged it. v2 went down its checklist, found that docs and config didn't match any item,
and said "no defects". My reading is that the checklist made the reviewer look only for the categories on the list.

**Confidence is low.** It's one case in one run. With 9 defect cases even a perfect score only puts the catch rate somewhere
between 70% and 100%, and 8/9 vs 9/9 overlap almost completely. I'd need a lot more cases, or several v2 runs, before
claiming anything either way.

**Case 09 decides the direction.** I first had case 09 as clean in my key. After seeing every v1 run flag the README line,
I checked the code, confirmed the line is wrong, and changed it to a doc defect (noted in `answer-key.md`). If you
score it as clean instead, v1 gets 1 false alarm out of 4 clean cases per run and v2 gets 0, and v2 looks better. So the
result depends on that one call.

Other things I noticed:
- The set is too easy. v1 scored 100% every run with no variation, so it can show a regression but not an improvement. It needs
  harder cases, e.g. authz bypass through indirection, or bugs that need repo context.
- 24 of the 48 answers mention `AGENTS.md` or "project conventions", even though the reviewer only read the diff. The agent
  harness loads the repo's `CLAUDE.md` → `AGENTS.md` automatically. That was the same for every run, so the v1/v2 comparison is still
  one variable, but it isn't "prompt and diff only" as `ops/evals/README.md` asks. Next time I'd run the reviewer outside the repo.
- No case changed verdict between runs 1–3.
