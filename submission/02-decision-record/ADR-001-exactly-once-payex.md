# ADR-001: Submitting approved invoices to PayEx exactly once

Status: accepted, pending the PayEx answers listed under open questions
Date: 2026-11-02

## Context

- Every approved invoice has to be submitted to PayEx. Volume is ~40k a month, 60% of it in the last three working days, peaking at about 80 approvals a minute.
- PayEx returns a reference on success. It times out at 30 s, and a timeout doesn't reliably mean the call failed.
- 3 App Service instances, Azure SQL, Service Bus provisioned but unused. The current code has no DB and no PayEx client, only `InMemoryInvoiceRepository`.
- SOC 2 Type II in six months. Approval actions must be auditable for 7 years.
- Team of 6, two new to the code, one-week on-call.

Because of the timeout behaviour, exactly-once can't be guaranteed from our side alone. What we can do is make sure an
approval never loses its submission (at-least-once), stop duplicates with a key, and have a defined way to resolve the
calls we're unsure about.

Open question that the design depends on: does PayEx accept an idempotency key or client reference, and can we look
a submission up by it? The brief doesn't say. This needs a written answer from PayEx before build starts, including how
long they keep keys.

## Options

**A. Idempotency key + dedupe table, called inline in the approve request**
- Simple, and approvers get immediate feedback.
- If the process dies after the DB commit and before the PayEx call, nothing ever retries it.
- Each approve request can now take up to 30 s. At 80/min that ties up a lot of requests at exactly the wrong time.
- You end up needing a sweeper for failed calls anyway, which is basically an outbox without the guarantees.

**B. Transactional outbox + worker**
- Approval, audit row and `PaymentOutbox` row are written in one SQL transaction. If it's approved, the outbox row exists.
- Approve stays fast. PayEx latency only affects a queue we control and can rate-limit.
- Outbox and audit tables give the SOC 2 trail for free.
- More to build: worker, row claiming, retries, monitoring for stuck rows.
- Still at-least-once, so duplicate protection depends on the PayEx key or a lookup before resend.

**C. Optimistic submit + nightly reconciliation**
- Cheapest.
- Duplicates are found up to a day later, after money has moved, and month-end is when that hurts most.
- Puts finance clean-up on whoever is on call.

## Decision

B, with the invoice ID as the idempotency key, plus a daily reconciliation job from C as a backstop.

- `PaymentOutbox` has `UNIQUE(InvoiceId)`, so a second approval can't create a second row.
- The worker claims rows with `UPDLOCK, READPAST` and a lease, and sends with `Idempotency-Key: <InvoiceId>`.
- A timeout sets status `Unknown`, not `Failed`. Before any retry the worker looks the invoice up in PayEx. If lookup isn't possible, the row waits for a person. No blind resends.
- Retries use exponential backoff with jitter. After N attempts the row goes to `NeedsAttention` and an alert fires.
- Concurrency starts at 4 in-flight calls.
- Reconciliation compares `Submitted` rows against the PayEx settlement report every day. Mismatches alert in working hours.
- Service Bus is not on the payment path, because that would be a dual write between SQL and the bus. It can carry the `invoice.approved` notification after PayEx confirms.

I didn't pick A because of the crash gap and the 30 s requests at peak. I didn't pick C alone because finding a double payment the next morning is too late.

## Stress tests

I ran these against a separate agent session that only had the scenario facts, not this ADR. The replies are in `agent-transcript.md`.

**1. "I prefer A."** It didn't change its recommendation, and the reasons were sound (the crash gap, timeout ambiguity, 30 s
requests at peak). It then proposed a "small-team" variant: outbox row in the transaction, plus calling PayEx inline right
after commit. I didn't take the inline call. It brings back the 30 s request problem it had just used against A.

**2. 3 a.m., last working day.**

| What breaks | Effect with B | What on-call does |
|---|---|---|
| PayEx slow (20–30 s) | Outbox backlog grows, approvals still work | Alert on backlog age > 15 min. Worker keeps draining at the capped rate |
| PayEx timeouts | Rows go `Unknown`, nothing resent blindly | Throttle the worker. Resolve by lookup when PayEx recovers. Don't bulk resend |
| Worker dies mid-call | Lease expires, row is reclaimed | Resent with the same key. Only safe if PayEx honours it |
| Two instances grab one row | Prevented by `UPDLOCK, READPAST` + lease | – |
| SQL failover | Approve fails cleanly, user retries | Normal 5xx alert |
| Wrong PayEx key after rotation | Every call 401, rows stay `Pending` | Alert on 401 rate. Nothing lost, resumes once fixed |
| Duplicate row bug | Blocked by the unique constraint | – |
| Poison row | Fails every attempt | Moved to `NeedsAttention` via an admin endpoint, not hand-written SQL |

The agent and I agreed on the weakest point: if PayEx is slow *and* lookup doesn't work, `Unknown` rows pile up with no
automatic way out. That's a business escalation, not something on-call should guess at. The agent also raised idempotency key
expiry: if PayEx forgets keys after 24 h, a late resend pays twice. I added that as a revisit trigger.
I added the 401 row myself, because a PayEx key rotation is in `INC-2047/recent-changes.md` and the agent didn't list it.

**3. Cost.** The agent's estimates:

| | A | B | C | B + C (chosen) |
|---|---|---|---|---|
| Build (eng-weeks) | 1.5–2.5 | 3–5 | 2–4 | 6–9 |
| Extra Azure / month | ~$0 | $0–20 | ~$5 | < $50 |
| Ops time | 4–8 h/month of manual resends | 1–2 h/month | 5–10 h/month + finance clean-up | 2–4 h/month |

On top of that, 4–6 eng-weeks of shared work for any option (SQL migration, PayEx client).

I agree with the shape but not the numbers. Azure cost is negligible for all of them at 40k rows a month, so cost doesn't
decide this. The build weeks are "heuristics from similar work", and the ops hours assume a 1–3% timeout rate that nobody
has measured. Next step is a one-week spike against the PayEx sandbox to get real timeout rates and confirm key behaviour,
then re-estimate.

## Consequences

- "Submitted to PayEx" becomes its own status in the UI, separate from "Approved".
- New work: outbox table and migration, worker, metrics (backlog size and age, Unknown count), runbook, admin re-drive endpoint, reconciliation job.

## Revisit if

1. PayEx doesn't support idempotency keys or lookup by reference.
2. Outbox backlog is older than 1 hour during a month-end close.
3. Reconciliation finds any duplicate payment.
4. Peak goes above ~160 approvals/min, or PayEx publishes a rate limit we'd exceed.
5. The platform team ships a supported outbox library.
6. PayEx keys expire (e.g. after 24 h). Then anything older than the window needs manual review before a resend.

## Where the agent was wrong or useless

1. It contradicted itself on effort. In stress test 1 the combined design was "~one extra table and ~150 lines of code".
   In stress test 3 the same design was 6–9 engineer-weeks.
2. Its simpler variant called PayEx inline after commit, which is the 30 s request it had just used as an argument against A.
3. The ops estimates rest on "an assumed 1–3% month-end timeout rate". There's no data for that anywhere. The build numbers
   come from "heuristics from similar integration work", which I can't check.
4. In the 3 a.m. answer it says an expired lease is fine because "the idempotency key saves you". In its first answer it said
   PayEx key support was unknown and needed confirming in writing.
5. It missed the credential failure case, even though the key rotation on 2026-01-23 is in our own evidence pack.

What was useful: it said up front that exactly-once isn't achievable over the network, it didn't fold when I pushed for A,
it put the PayEx key question first, and the key retention point was new to me.
