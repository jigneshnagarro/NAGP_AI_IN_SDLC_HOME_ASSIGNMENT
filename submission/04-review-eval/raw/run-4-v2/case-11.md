## Review of ApprovalService.Approve diff

### Finding 1: DecidedAt changed from UTC to server-local time (confidence: high)
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs
- Line: the changed line `invoice.DecidedAt = now;` (replacing `invoice.DecidedAt = DateTime.UtcNow;`), with `var now = DateTime.Now;` at the diff's line 23.
- What goes wrong: `DateTime.Now` is server-local time with Kind=Local. It is now stored in `DecidedAt`, which was UTC before. Existing records hold UTC and new ones hold local time, so the timestamps are inconsistent. Any code that treats `DecidedAt` as UTC will be off by the server's UTC offset. The offset also changes at DST transitions, so ordering can break. Serialisation (JSON offset, later persistence) will carry the local offset or none, depending on the serialiser.

### Finding 2: Month-end cut-off uses server-local time, not a defined business time zone (confidence: high)
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs
- Line: `if (now.Hour >= 18 && now.AddDays(1).Month != now.Month)`
- What goes wrong: "18:00 on the last day" depends on the time zone of the host machine. A server running in UTC (typical for containers) and users in another zone will disagree about which period an approval belongs to. The same approval can roll or not roll depending on where the app is deployed. The rule is also not testable deterministically because it reads the clock directly (`DateTime.Now`) with no injected time source.

### Finding 3: Rule is only half implemented, so approvals are not actually rolled (confidence: medium-high)
- File: backend/src/InvoiceApp.Domain/ApprovalService.cs
- Line: `invoice.DecisionNote = "Rolled to next period";`
- What goes wrong: The comment says approvals roll into the next period, but the only effect is a free-text note. `DecidedAt` is still set to the actual time, and no period field changes. Anything that reports by period from `DecidedAt` will count the invoice in the old month. The note is also overwritten or ignored by any later decision-note handling. The behaviour does not match the stated intent.

### Not reported
- No authorisation, injection, logging or money/rounding issues are visible in this diff. The diff does not show the controller, so I cannot say whether the Approve endpoint is role-restricted.
- There are no tests in the diff for the new rule. The project convention requires tests for every new rule, but I am not counting this as a defect.
