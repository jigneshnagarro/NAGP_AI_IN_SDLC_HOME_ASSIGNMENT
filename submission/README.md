# AI in SDLC: Home Assignment 2

Video: <link>

| # | Deliverable | Where |
|---|---|---|
| 1 | As-built and target diagrams, citations, inferred list | `01-architecture/diagrams.md` (+ `.mmd`, `.svg`) |
| 2 | Architecture test | `backend/tests/InvoiceApp.Tests/ArchitectureTests.cs` |
| 3 | Exactly-once decision record | `02-decision-record/ADR-001-exactly-once-payex.md`, agent replies in `agent-transcript.md` |
| 4 | Autonomy policy (month-end log triage) | `03-autonomy-policy/autonomy-policy-month-end-log-triage.md` |
| 5 | Added eval cases + results | `ops/evals/cases/case-11.diff`, `case-12.diff`, `04-review-eval/README.md`, `ops/evals/results.csv` |
| 6 | Risk audit | `05-risk-and-measurement/risk-audit-lethal-trifecta.md` |
| 7 | Measurement plan + two numbers | `05-risk-and-measurement/measurement-plan.md` |
| 8 | AI augmentation log | `ai-augmentation-log.md` (readable), `07-ai-log/ai-augmentation-log.jsonl` (structured), `07-ai-log/auto/` (generated from the session transcript), `07-ai-log/evidence/` |

## Running things

Needs the .NET 8 SDK and Python 3. Run everything from the repo root.

Architecture test (expect 1 passed), then the full suite (expect 8 passed):
```bash
dotnet test backend/InvoiceApp.sln --filter "FullyQualifiedName~ArchitectureTests"
```
```bash
dotnet test backend/InvoiceApp.sln
```

Eval table from `ops/evals/results.csv`:
```bash
python submission/04-review-eval/eval.py score
```

Baseline numbers (expect median 31.3 min, failure rate 10%):
```bash
python submission/05-risk-and-measurement/capture_baseline.py
```

AI log: check the structured log and rebuild `07-ai-log/summary.md` (expect "16 records OK"):
```bash
python submission/07-ai-log/build_log.py
```

Diagrams: open `diagrams.md` with a Mermaid-capable preview, open the `.svg` files, or paste a `.mmd` into mermaid.live.
The Mermaid MCP is in `.mcp.json` (`mcp-mermaid@0.4.1`).
