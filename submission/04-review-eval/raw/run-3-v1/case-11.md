## Review of case-11 diff

### Finding 1: DecidedAt changed from UTC to local time
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs
- Line: `invoice.DecidedAt = now;` (the line replacing `DateTime.UtcNow`)
- What goes wrong: `now` is `DateTime.Now`, which is server-local time with `Kind=Local`. `DecidedAt` was previously stored as UTC. Stored timestamps are now in the server's time zone. That makes them inconsistent with older records and with any code or UI that assumes UTC. JSON serialization will include a local offset. Comparisons, ordering and audit trails break across time zones and DST changes. Local time can also repeat or skip an hour at DST changes.
- Confidence: high (about 90%).

### Finding 2: The month-end cut-off uses server-local time and gives wrong results
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs
- Line: `if (now.Hour >= 18 && now.AddDays(1).Month != now.Month)`
- What goes wrong: The rule depends on the host's time zone, not on a business time zone. An approver in another zone, or a server running in UTC (common for containers), will get the cut-off at the wrong moment. The result also varies between environments and cannot be tested reliably. The `DateTime.Now` call is not injected or abstracted, so tests cannot control the clock. Per AGENTS.md, every new rule needs tests, and none are in the diff.
- Confidence: high (about 80%).

### Finding 3: The "roll to next period" rule has no effect other than a note, and it overwrites DecisionNote
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs
- Line: `invoice.DecisionNote = "Rolled to next period";`
- What goes wrong: The only effect of the cut-off is a free-text string. No period or booking date field changes, so the invoice is not actually rolled to the next period. The comment says it is. The assignment also unconditionally overwrites any `DecisionNote` already on the invoice. Nothing clears the note when the cut-off does not apply. Downstream consumers may also have to parse the magic string.
- Confidence: medium (about 60%). It depends on whether `DecisionNote` is used elsewhere and on what "roll" is meant to do.

### Finding 4: No tests added
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs (the whole new block)
- What goes wrong: This is a new business rule with a time-dependent branch and no accompanying tests. It breaks the project convention that every new rule needs tests. Without a clock abstraction it also cannot be tested deterministically.
- Confidence: high (about 85%).

### Not a defect
- `now.AddDays(1).Month != now.Month` correctly detects the last day of the month, including December to January and leap years.
