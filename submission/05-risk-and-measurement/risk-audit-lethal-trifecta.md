# Risk audit: agent setup vs. the lethal trifecta

The brief says the agent setup is described at the end of `ops/README.md`, but in this repo (commit `0616158`) that file
stops at "No answers here". There's no agent description in it. So I audited the setup the repo actually configures,
and I'd re-run this checklist if the missing section turns up.

## What I audited

| Part | Where |
|---|---|
| Coding agent with file read/write and a shell in the repo | `AGENTS.md`, `CLAUDE.md` |
| Playwright MCP, started as `npx @playwright/mcp@latest`. A real browser that can open any URL | `.mcp.json` |
| The agent reading incident logs, Service Bus output and review diffs | `ops/incidents/*`, `ops/evals/cases/*` |
| Planned: the agent helping on-call at month-end with read access to prod logs | autonomy policy |

## The three legs

| Leg | Present | Evidence |
|---|---|---|
| Private data | Yes | Source code; prod logs with customer names and amounts (`INC-2041/app-logs.txt`, `INC-2047/*-logs.txt`); demo credentials in `appsettings.json`; the developer's GitHub/Azure CLI session in the shell; the PayEx API key in prod config (rotated 2026-01-23, `INC-2047/recent-changes.md`) |
| Untrusted content | Yes | Log lines carry user-entered fields: customer name, and the supplier contact fields added in 2.15.0. Anyone who can create an invoice can get text in front of the agent. Also PRs from others, any page Playwright opens, and `@latest` pulling whatever npm has that day |
| External communication | Yes | Playwright can navigate anywhere (data in a query string is enough to leak it); the shell can `curl`, `git push`, `npm install`; the agent can post PR comments |

All three are present. A prompt injection in a log line or a diff could get the agent to read a secret and send it out.

## Decision: redesign, remove external communication

The private data is the point of triage, and logs are always going to contain attacker-influenced text. Outbound access
is the one leg the job doesn't need, so that's the one to cut.

- Pin the MCP version and limit it to the local app: `"args": ["@playwright/mcp@<version>", "--allowed-origins", "http://localhost:5000"]`. Check the flag against that version's `--help`.
- In triage/review sessions, deny `curl`, `wget`, `Invoke-WebRequest`, `git push`, `npm install` and web fetch in the agent's permission settings.
- Run the triage agent under its own read-only Azure identity (Log Analytics Reader), with no GitHub write token.
- Run triage in a container or devbox whose egress allowlist is Azure Monitor plus the model API.
- The agent drafts messages and a person sends them (L1 in the autonomy policy).

What's left, and I'm accepting it: the model API is still an outbound channel. That's covered by the enterprise agreement
(no training on our data), and by dropping personal fields from the logs before the agent sees them.

## Revisit when

- Someone wants to give the triage agent a write or messaging tool (e.g. posting in the incident channel)
- An injection-looking string turns up in prod logs or a PR
- A triage task moves to L3 or above
- The SOC 2 auditor raises agent access

Owner: service owner. Review before the rotation starts, then quarterly.
