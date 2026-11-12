# AI augmentation log

This is the readable version. The machine-readable log is in `07-ai-log/`:

| File | What it is | How it's made |
|---|---|---|
| `07-ai-log/ai-augmentation-log.jsonl` | One record per interaction (16), in the required format plus `prompt`, `outcome` and `evidence` fields | Written by me, checked by `build_log.py` |
| `07-ai-log/auto/session-turns.jsonl` | One line per prompt I typed: time, models, tools, files written, sub-agents started | **Generated** from the Claude Code transcript by `extract_session_log.py` |
| `07-ai-log/auto/tool-calls.jsonl` | Every tool call: time, tool, target file or command, permission decision, error | **Generated** |
| `07-ai-log/auto/subagents.jsonl` | Every sub-agent: type, model, task, start/end, tools, status | **Generated** |
| `07-ai-log/summary.md` | Table of all records plus totals | **Generated** by `build_log.py` |
| `07-ai-log/evidence/` | Test, eval, baseline and git output with UTC timestamps | Re-run on 2026-11-03 08:03 UTC |

Regenerate (the transcript lives in `~/.claude/projects/<project>/<session-id>.jsonl`):
```bash
python submission/07-ai-log/extract_session_log.py <path-to-session.jsonl> --repo . --out submission/07-ai-log/auto
```
```bash
python submission/07-ai-log/build_log.py
```

## 1. AI tool and model

- Claude Code desktop app (Code tab), version 2.1.309. Session `747f733e-9abc-45f2-82e3-d06a4e8b5a7b`, 2026-11-02 to 2026-11-03.
- Main agent: `claude-opus-5-5`.
- Sub-agents: 48 × `claude-sonnet-5-5` (eval reviewers), 1 × `claude-opus-5-5` (ADR advisor).

## 2. Agent details

| Agent | Type | Mode | Used for |
|---|---|---|---|
| Claude Code main agent | built-in | agent (auto permission mode: edits and commands run, risky ones go through a classifier) | All five tasks, docs, scripts |
| ADR trade-off advisor | sub-agent (built-in general-purpose) | agent, background | Independent A/B/C trade-offs and 3 stress tests for Task 2 |
| Eval reviewer × 48 | sub-agent (built-in general-purpose) | agent, background, non-interactive | One fresh review per case per run for Task 4 |

## 3. Prompts and interactions

The six prompts I typed are in `auto/session-turns.jsonl` word for word. In short:

| Turn | Time (UTC) | Prompt |
|---|---|---|
| 1 | 11-02 11:36 | The PDF plus the repo link: plan and complete the assignment, with run/verify steps and a video script |
| 2 | 11-02 11:53 | Do the remaining parts yourself and tell me how to verify and what to show |
| 3 | 11-02 12:23 | The script sounds AI-generated: plain technical voice, no filler lines |
| 4 | 11-03 04:53 | A classmate's submission as a reference for structure; make our own version |
| 5 | 11-03 05:19 | Say which file to open at every step of the script |
| 6 | 11-03 08:00 | The required log format (this log) |

Sub-agent prompts:
- Eval: exactly the v1 or v2 text in `04-review-eval/prompts.md` followed by the diff. The 48 prompt files are in `04-review-eval/prompts/`.
- ADR advisor: Prompt 0 and three stress-test follow-ups, quoted in `02-decision-record/agent-transcript.md`.

## 4. Skills, custom instructions, sub-agents

- Skills: none invoked.
- Custom instructions: `CLAUDE.md` → `AGENTS.md`, loaded automatically. It also got loaded into the eval reviewers (24 of 48 outputs mention it), which I didn't intend. It was the same for every run, so the comparison still holds, and it's disclosed in `04-review-eval/README.md`.
- Sub-agents: 49, all completed (`auto/subagents.jsonl`).

## 5. Tools and integrations

- Built-in tools: Read, Write, Edit, Bash, Agent, SendMessage, ToolSearch.
- MCP: `Claude_Browser` (the app's built-in browser). I used it to render the `.mmd` files with Mermaid 11.4.1 and save the `.svg`.
- MCP: `ccd_turn` (the app's task list).
- `mermaid` (`mcp-mermaid@0.4.1`) is added to `.mcp.json`. The agent's attempt to start it was blocked by auto mode (downloaded code), so I run it live in the video.
- External CLIs: `pdftotext`, `git`, `dotnet`, `python`.

## 6. AI actions and outputs, per task

| Task | What the agent did | Output |
|---|---|---|
| Setup | Pulled the brief from the PDF, cloned the repo, read the code and `ops/` | Plan |
| 1 | Three Mermaid diagrams with citations, the inferred list, the corrections list. An architecture test using reflection | `01-architecture/`, `ArchitectureTests.cs` |
| 2 | ADR draft. A separate advisor did the trade-offs and stress tests | `02-decision-record/` |
| 3 | Autonomy levels, the task table, the day-one level | `03-autonomy-policy/` |
| 4 | Wrote case-11/12, the answer key, v1/v2 prompts, `eval.py`. Ran 48 reviewer sessions | `ops/evals/cases/`, `ops/evals/results.csv`, `04-review-eval/` |
| 5 | Trifecta audit, `capture_baseline.py`, measurement plan | `05-risk-and-measurement/` |
| Docs | README, video script, this log and its scripts | `README.md`, `06-video/`, `07-ai-log/` |

## 7. Human intervention

Decisions and corrections:
1. I asked for the first video script to be rewritten: it read as AI text (turn 3). Then I asked for exact file-open steps (turn 5).
2. I gave a classmate's submission as a reference for structure only. We kept our own answers: a different autonomy task, and a full 48-run eval where theirs has one case (turn 4).
3. ADR: I rejected the advisor's inline PayEx call, because it brings back the 30 s request problem, and kept option B. The advisor's five mistakes are listed in the ADR.
4. Eval: v2 is not adopted. It lost the true case-09 finding.
5. Mermaid MCP: I run it myself in the video instead of working around the block.

Places where the AI was wrong and had to be corrected:
1. It read `AGENTS.md` and `ci-pipeline.yml` as facts about the code. It said every controller inherits `ApiControllerBase`, and that `/health` and a Dockerfile exist. None of that is true; the six claims are in the Corrections table.
2. The case-09 answer key was wrong at first (marked clean). It changed after the reviews flagged the README line and the code confirmed it. This is disclosed in `answer-key.md`, with both scorings.
3. ADR advisor: it contradicted itself on effort (~150 lines vs 6–9 eng-weeks), invented a timeout rate, and missed the API key rotation in our own evidence.
4. The first two PDF reads failed (no renderer, no Python PDF library). `pdftotext` worked.

Validation: every output was checked against the code or the evidence before it went in. The checks are listed per record in `action_verification`. The tests and scripts are run again live in the video.

## 8. Execution evidence

- Timestamps: on every record, plus a `tool_call_window` that matches `auto/tool-calls.jsonl`.
- Tests: `dotnet test` gave 8/8 passed, and the architecture test 1/1 (`evidence/dotnet-test.txt`, `architecture-test.txt`). The deliberate-break run is at 2026-11-02 11:39:58 UTC in `auto/tool-calls.jsonl`.
- Eval: v1 9/9 caught and 0/3 false alarms in each of 3 runs; v2 8/9 (`evidence/eval-score.txt`).
- Baseline: CI median 31.3 min, p90 34.5 min, failure rate 10% (`evidence/baseline.txt`).
- Files touched per turn: `files_written` in `auto/session-turns.jsonl`.
- Commits: none yet. `evidence/git.txt` shows the new files as untracked. The commit SHA goes into `evidence.commit` after the push.

## 9. Outcome

From the 16 records: 12 successful, 2 partially completed (the Mermaid MCP couldn't run in the agent session; the ADR advisor's output was only partly usable), and 2 needed rework (the diagrams' doc-based claims; the first video script).
