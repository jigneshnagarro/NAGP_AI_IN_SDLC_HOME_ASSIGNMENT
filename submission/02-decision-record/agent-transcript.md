# ADR-001 — agent transcript (trade-offs + three stress tests)

Agent: a fresh Claude subagent (general-purpose, no tools used), given only the scenario facts —
not my draft ADR. Date: 2026-11-02. Replies are copied verbatim.

## Prompt 0 — lay out the trade-offs

> How do we guarantee an approved invoice reaches PayEx exactly once? Lay out the trade-offs of at least
> (A) idempotency key + dedupe table, (B) transactional outbox + worker, (C) optimistic submission + nightly
> reconciliation, and give a recommendation. *(full scenario facts were included)*

### Reply

**Short answer:** You cannot *guarantee* "exactly once" across a network boundary — you can only build **effectively-once**: at-least-once delivery from your side + idempotent acceptance on PayEx's side. That makes the single most important question one about PayEx, not your code: **does PayEx accept an idempotency key (or let you look up a submission by your own reference)?** Get that answered in writing before designing further.

**(A) Idempotency key + dedupe table**
- ✅ Simple; a deterministic key (InvoiceId) prevents *your own* retries/double-clicks from producing two sends.
- ❌ A local dedupe table cannot resolve a timeout — you don't know whether PayEx processed it, so you either risk a double (retry) or a miss (don't). Only works end-to-end if PayEx honours the key. Doesn't protect against crash between "approved" commit and send.

**(B) Transactional outbox + worker**
- ✅ Approval, audit record and "submit to PayEx" intent are committed in **one Azure SQL transaction** — nothing is lost if an instance dies. Durable retries, a status state machine, and natural evidence for SOC 2 (every attempt recorded). 80/min is trivial load.
- ❌ More moving parts (background worker, 3-instance coordination via row leasing / `UPDLOCK, READPAST`). On its own it is at-least-once — still produces duplicates on timeout retries.

**(C) Optimistic submission + nightly reconciliation**
- ✅ Cheapest to build.
- ❌ Detects duplicates/misses up to a day later — *after* money moved, and during month-end when 60% of volume lands in 3 days, that means manual clean-up at the worst time. Auditors see a correction, not a control. Fine as a **detective** layer, not as the guarantee.

**Recommendation: B + A, with C as safety net.**
1. **Approve transactionally:** invoice state change + append-only audit row + outbox row in one transaction. (Temporal tables or append-only audit table; archive to immutable Blob storage for 7-year retention.)
2. **Single SQL-polling outbox worker** (don't need Service Bus yet — fewer new concepts for the two new engineers; can move later). Send with `Idempotency-Key = InvoiceId`.
3. **Status state machine:** Pending → InFlight → Submitted (store PayEx reference) | Unknown | Failed.
4. **On timeout → mark Unknown, never blind-resend.** Query PayEx by your reference (or rely on its key) to resolve; bounded retries with backoff; unresolved go to a manual queue.
5. **Nightly reconciliation** against PayEx's settlement report, alert on mismatch — this is the control auditors will ask for.
6. **On-call:** dashboards for outbox age, Unknown count, reconciliation drift; runbook for clearing Unknown. One-week rotation means it must not rely on tribal knowledge.

**Fallback:** if PayEx supports neither idempotency key nor lookup, effectively-once is impossible — treat every timeout as Unknown and resolve manually/via reconciliation before any retry. Escalate this to the business now as a risk to the January date.

**Sequencing:** the in-memory store must be replaced with Azure SQL first — nothing here works without durable state. That migration plus PayEx sandbox testing (simulate timeouts) is your critical path to January.

## Stress test 1 — state a preference for a different option

> I actually prefer option A, the idempotency key with a dedupe table, done synchronously inside the approve request. It is simpler and my team is small. Do you change your recommendation?

### Reply

**No — the recommendation stands, but I can make it almost as simple as what you want.**

A alone, synchronous in the approve request, has three gaps a dedupe table can't close:

1. **Dual-write gap.** If you commit "Approved" then crash before calling PayEx, the payment is silently lost. If you call PayEx first and the commit fails, PayEx pays an invoice your system says isn't approved. Neither leaves anything to retry from.
2. **Timeout ambiguity.** A 30 s timeout still leaves you not knowing. Inside a web request your only choices are fail the approval or blindly retry — and blind retry risks a double payment.
3. **Month-end fragility.** At ~80 approvals/min, PayEx slowness ties up web requests for up to 30 s each, and PayEx outages become user-facing approval failures.

The simplicity is also illusory: you'll still need somewhere to retry failed sends from — which becomes an ad-hoc, untested outbox.

**Small-team version of my recommendation:**
- Keep A's idempotency key (InvoiceId).
- In the approve transaction, write approval + audit + one outbox row.
- After commit, **try the PayEx call immediately in the same request** — most invoices submit instantly, users get immediate feedback.
- A small in-process `BackgroundService` sweeps anything still Pending/Unknown. No Service Bus, no separate deployment — one table, one loop, a lease column.

That's ~one extra table and ~150 lines of code, and it closes the crash and timeout gaps while giving SOC 2 an attempt log.

**A alone is acceptable only if** PayEx guarantees idempotency-key semantics *and* offers status lookup, *and* the business accepts manual re-sends for lost submissions.

## Stress test 2 — how does it fail at 3 a.m. on the last day of the month?

> It is 3 a.m. on the last working day of the month and your recommended design is in production. Walk me through concretely how it fails: which failure modes happen, what the on-call engineer sees, and what they do. Be specific about where your design is weakest.

### Reply

**3 a.m., month-end — realistic failure modes, weakest first.**

**1. PayEx degraded → Unknown queue explodes (the weakest point).** PayEx slows, calls hit the 30 s timeout. Each one moves to Unknown, and the design *depends* on a status lookup before retry. If PayEx's lookup endpoint is also down (or lagging), Unknown grows with no automatic exit.
- *On-call sees:* alert "Unknown count > threshold", outbox age rising, App Insights timeouts.
- *Does:* runbook — throttle the worker (stop making it worse), do **not** bulk re-send. Check PayEx status, open a ticket with them, batch-resolve Unknowns once lookup recovers. Escalate to finance if month-end deadlines are at risk instead of guessing. This is where the design hurts most: it is safe but cannot make progress without PayEx.

**2. Idempotency key not honoured as assumed** (e.g. PayEx only keeps keys 24 h, or treats a changed payload as new). A re-drive creates a duplicate payment.
- *On-call sees:* nothing at 3 a.m. — nightly reconciliation catches it hours later.
- *Mitigation:* confirm key semantics before go-live; never re-send a modified payload.

**3. Worker issues.** Lease expiry: a slow call outlives its lease and a second instance picks up the same row — the idempotency key saves you, but the logs get noisy. A poison row (bad data) fails forever. App Service recycle kills the loop and the worker stalls.
- *Sees:* outbox age climbing while PayEx is healthy, or one row with a high attempt count.
- *Does:* restart the instance; move the poison row to Failed — needs runbook + admin endpoint, not ad-hoc SQL.

**4. Azure SQL throttling at peak** — outbox polling competes with approval writes; approvals slow.
- *Does:* back off polling frequency, scale DB tier.

**What on-call can't fix alone:** PayEx outage, ambiguous key semantics, money already paid twice — each needs a named escalation contact at PayEx and finance.

**Before go-live:** load test month-end volume against PayEx sandbox with injected timeouts.

## Stress test 3 — what does it cost to build and to run?

> What does each option (A, B, C, and your recommended combination) cost to build and to run? Give engineer-weeks to build, monthly Azure/run cost, and the ongoing on-call/operational cost. State what your numbers are based on.

### Reply

**Caveat up front: these are planning estimates, not quotes — none of the inputs are measured yet.**

**Shared cost (not counted below):** in-memory → Azure SQL migration + PayEx client (auth, error mapping, sandbox tests) ≈ **4–6 eng-weeks**. That's most of the January risk.

| Option | Build (eng-weeks) | Extra Azure/month | Ongoing on-call/ops |
|---|---|---|---|
| **A** sync key + dedupe | 1.5–2.5 | ~$0 | **High at month-end**: lost/timed-out payments found and re-sent by hand; ~4–8 h/month plus incident risk |
| **B** outbox + worker | 3–5 | $0–20 (slight extra SQL load; Service Bus Standard ~$10 if used) | Low: ~1–2 h/month (queue checks, occasional poison row) |
| **C** optimistic + nightly recon | 2–4 (parsing PayEx's report is the unknown) | ~$5 (scheduled WebJob/Function) | **High**: daily triage, 5–10 h/month at month-end, plus finance recovering duplicate payments |
| **B + A + C (recommended)** | 6–9 (incl. dashboards, runbook, admin re-drive endpoint) | < $50 | Low–moderate: ~2–4 h/month; PayEx outages still need escalation |

**Basis:**
- **Volume:** 40k rows/month is negligible for Azure SQL; the 3 App Service instances and the DB are already paid for, so infra cost hardly differs between options.
- **Build:** heuristics from similar integration work, +~30% for two engineers new to the codebase; includes tests and runbooks.
- **Ops hours:** an assumed 1–3% month-end timeout rate (≈200–700 invoices at peak to handle).

**The cost that matters most isn't Azure.** One month-end duplicate-payment incident (finance time, recovery, audit finding) likely outweighs the 4–6 eng-week build difference.

**To firm these up:** a one-week spike against the PayEx sandbox to confirm idempotency behaviour and real timeout rates, then re-estimate.
