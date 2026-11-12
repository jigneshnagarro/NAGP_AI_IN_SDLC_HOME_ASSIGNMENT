# Review prompts

## v1 (baseline, verbatim from ops/evals/README.md)

Review this diff for defects. For each finding give the file, the line, what
goes wrong, and how confident you are. If you find nothing, say so
explicitly rather than listing general observations.

## v2 (changed prompt, same model)

Review this diff for defects. For each finding give the file, the line, what
goes wrong, and how confident you are. If you find nothing, say so
explicitly rather than listing general observations.

Before answering, check the diff specifically for: missing or wrong
authorisation, unvalidated or null input, injection, data races on shared
state, swallowed exceptions or wrong status codes, money/rounding changes,
time-zone handling, and secrets or personal data written to logs.
Only report a defect if you can quote the exact changed line that causes it.
Style, naming and "could be improved" notes are not defects — leave them out.
