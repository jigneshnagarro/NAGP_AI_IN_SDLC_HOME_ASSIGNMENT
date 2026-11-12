Review of case-11 diff (ApprovalService.Approve)

Finding 1: DecidedAt switched from UTC to local time
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs, line 25 (`invoice.DecidedAt = now;`, where `now = DateTime.Now`)
- What goes wrong: `DecidedAt` was `DateTime.UtcNow` and is now server-local time (`DateTimeKind.Local`). Stored and serialized timestamps change meaning silently. Other code and consumers (JSON output, UI, comparisons with other UTC timestamps) will see inconsistent values and offsets. It also differs between hosts and time zones, and ambiguous or non-existent local times around DST changes can occur. Existing data holds UTC, so new records are mixed with old.
- Confidence: high (about 90%).

Finding 2: Month-end cut-off uses server-local time and is machine-dependent
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs, lines 16-17
- What goes wrong: `DateTime.Now.Hour >= 18` depends on the server's time zone. A container or cloud host usually runs in UTC, so "18:00" means 18:00 UTC rather than the business's time zone. The rule fires at the wrong moment for the intended users. It is also untestable, because there is no injectable clock, so tests would depend on the real current time. Business-rule time should come from an injected clock or `TimeProvider` with an explicit business time zone.
- Confidence: high (about 85%).

Finding 3: "Roll into next period" is only a note, and it overwrites DecisionNote
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs, lines 18-20
- What goes wrong: The only effect is setting `invoice.DecisionNote = "Rolled to next period"`. Nothing moves the invoice to a period, and `DecidedAt` is not adjusted. If the approver or the caller already set a decision note, this code overwrites it. It also writes a magic string with no constant. Whether this is the intended behavior is unclear. The comment promises a rollover that the code does not perform.
- Confidence: medium (about 60%).

Finding 4: Month-end check logic is brittle, and there are no tests
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs, line 17
- What goes wrong: `now.AddDays(1).Month != now.Month` does detect the last day of the month. It would throw at DateTime.MaxValue, which is not realistic. The larger problem is that the project requires tests for every new rule. The diff contains none. Untested boundaries include 17:59 versus 18:00, and the last day versus other days, with a Dec 31 year rollover and a leap-year Feb 28 or 29. The rule is also not reachable deterministically without a clock abstraction.
- Confidence: high (about 80%) for the missing tests, per the repo convention that every new rule needs tests.

No other defects found. The status, DecidedBy and Update flow is unchanged.
