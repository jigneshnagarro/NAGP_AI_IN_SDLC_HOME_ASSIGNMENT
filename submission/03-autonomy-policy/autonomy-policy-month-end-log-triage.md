# Autonomy policy: month-end log triage

Scope: during the last three working days of the month, an agent helps the on-call engineer read the approval service's logs,
metrics and Service Bus status to work out what's wrong. INC-2041 (slow and failing approvals) and INC-2047 (missed
notifications) are the kind of incidents this covers.

I picked log triage over the other two options because it's where the on-call load actually is at month-end, and because
INC-2047 already states the rule I want: the agent investigates and lays out options, a person decides.

## Levels

| Level | Meaning |
|---|---|
| L0 | Agent not used |
| L1 | Suggest: works only on what a person pastes in, proposes hypotheses |
| L2 | Read-only: runs log/metric/queue queries itself, drafts a summary |
| L3 | Prepares a change; a named person approves it before it runs |
| L4 | Runs a pre-approved reversible action alone, reports afterwards |

## Tasks

| Task | Level | Reason |
|---|---|---|
| Group/count errors, build the timeline | L2 | Read-only, easy to check against raw lines |
| Rank hypotheses, citing the supporting and contradicting lines | L2 | The citations are what a person verifies |
| Correlate with recent deploys and config changes | L2 | Read-only |
| Draft the incident channel update | L1 | Goes to finance; a person sends it |
| Propose mitigations (rollback, scale, fix a subscription rule) | L1 | INC-2047: the decision isn't the agent's |
| Scale out an instance | L3 | Reversible, but it's a prod change and costs money |
| Replay dead letters / resubmit to PayEx | L3 max, never higher | Double-payment risk (ADR-001) |
| Roll back a release | L3 max, never higher | At month-end it affects everything else in the release |
| Anything at L4 | none at launch | No task has the evidence yet |

## Controls

- L1/L2: the agent's identity only has Log Analytics Reader, Monitoring Reader and Service Bus peek. There are no write credentials in the session, so the control is the missing permission, not "please be careful".
- Every claim has to cite a log line or metric row. An uncited claim gets treated as a guess.
- Logs contain user-entered text (customer names, supplier contact fields), so the triage session has no outbound network or messaging tools. See the risk audit.
- L3: the change is written as a script or PR, with the undo step written first. The named approver (the incident commander out of hours) approves it in the incident channel.
- Agent sessions are attached to the incident ticket for SOC 2.

## Moving a task up a level

All of these must hold:
1. At least 10 real incidents or month-end drills at the current level, scored afterwards.
2. The right cause was in the agent's top 3 in ≥ 80% of them, and it never cited a log line that doesn't exist.
3. For L3/L4: the action can be undone in under 5 minutes and the rollback has been tested.
4. No open finding from the risk audit against this setup.

Who approves:
- L1 to L2: service owner.
- L2 to L3: service owner + engineering manager, recorded in the change log below.
- L3 to L4: the above + the SOC 2 control owner, reviewed quarterly.
- If the agent causes or worsens an incident, that task drops a level immediately. Any engineer can make that call.

## Day one

**L2 for the read-only investigation tasks, L1 for everything else, nothing at L3.**

Two of the six engineers are new to the codebase. On their on-call week they can't yet tell when a confident hypothesis is
wrong, so the agent shouldn't be able to change anything. It should only show its working with citations. I'd still give it L2
rather than L1, because querying logs at 80 approvals a minute is exactly the work that's worth taking off people, and
read-only access can't make an incident worse. New engineers pair with someone experienced on any L3 action for their
first two rotations.

## Change log

| Date | Change | Approved by |
|---|---|---|
| 2026-11-02 | Created, day-one levels set | service owner |
