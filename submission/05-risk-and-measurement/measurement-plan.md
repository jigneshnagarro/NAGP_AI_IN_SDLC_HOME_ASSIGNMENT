# Measurement plan: baseline before the rotation starts

Capture these before the rotation starts, then once a month. Always compare a month-end window with another month-end window.

## Metrics and sources

| Metric | Definition | Source / query | Captured now? |
|---|---|---|---|
| Lead time for changes | First commit on a branch → running in prod | Commit→merge: `gh pr list --state merged --limit 200 --json number,createdAt,mergedAt,commits`. Merge→prod: `gh run list --workflow deploy --json headSha,createdAt,conclusion`, or App Service deployment history (`az webapp log deployment list`). Report median and p90. | Partly. CI duration (the build/test part) below, plus a rough branch proxy. There are no merged PRs or deploy workflow here |
| Change failure rate | % of prod deploys that lead to an incident, rollback or hotfix | Deploys: `az webapp deployment list` or the GitHub deployments API. Failures: incidents tagged with a release (INC-2041 → 2.14.0), plus `git log main --since=90.days -i --grep="revert\|hotfix" --oneline`. Rate = failed ÷ total | No. Needs deploy and incident records. CI failure rate below is a stand-in, not the same thing |
| Review turnaround | PR ready for review → first review | `gh pr view N --json createdAt,reviews`, or GraphQL `pullRequests { createdAt reviews(first:1){nodes{submittedAt}} }`. Median and p90, split by AI-assisted vs not | No. The repo has no PRs (`git log --merges` returns nothing) |

## The two numbers captured

```bash
python submission/05-risk-and-measurement/capture_baseline.py
```

Source: `ops/pipeline/run-timings.csv` (20 runs, 2026-01-19 to 2026-02-02) and `git log`.

| | Value |
|---|---|
| CI pipeline duration | median 31.3 min, p90 34.5 min (min 28.4, max 35.1), n = 20 |
| CI run failure rate | 10% (2/20). PR runs 2/12, main pushes 0/8 |

Rough proxy, not something I'd rely on: branch first PR run to the next main push is between 26 h and 291 h, median about 67 h.
`fix/notification-filter` took 291 h over 6 PR runs.

## Caveats

- 20 runs over two weeks, including one month-end. That's a starting point, not a trend.
- A red PR build is a problem caught before prod, so CI failure rate isn't change failure rate.
- `run-timings.csv` doesn't say which step failed. Run 6 only has 17 of 19 steps, so it probably stopped early.
- The repo history is 6 direct commits with no PRs, so review turnaround can't be measured from it at all.
- The install steps (restore, `npm ci`, Playwright browsers) take a big share of every run. That's the first place I'd look to cut lead time.

## Needed before day one

1. Branch protection, so every change goes through a PR. Otherwise review turnaround can't be measured.
2. A deploy workflow that records `headSha` and time, so lead time and CFR can be joined to commits.
3. Incidents tagged with the release that caused them.
