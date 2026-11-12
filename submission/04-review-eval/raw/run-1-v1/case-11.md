## Review of case-11 diff (ApprovalService.Approve)

### Finding 1: DecidedAt changed from UTC to server local time (high confidence)
File: backend/src/InvoiceApp.Domain/ApprovalService.cs, line 25 (`invoice.DecidedAt = now;`)

`now` is `DateTime.Now` (local, Kind=Local), but `DecidedAt` was previously `DateTime.UtcNow`. Stored timestamps now depend on the server's time zone and DST. That makes them inconsistent with older records and any other code that assumes UTC, such as Reject, sorting, audit or display. It will also serialize with an offset, or without one, differently than before. Around DST changes, ordering can go wrong or timestamps can repeat. Keep `DecidedAt` in UTC. If the cut-off needs local business time, compute it separately.

### Finding 2: Month-end cut-off is evaluated in server-local time, not a defined business time zone (medium-high confidence)
File: ApprovalService.cs, lines 16-17

`DateTime.Now` uses the host's zone. On a UTC cloud host, "18:00 on the last day" means 18:00 UTC, not the business's time zone. The result differs by deployment and is not unit-testable, because the clock is not injectable. Use an injected clock (`TimeProvider`/`IClock`) and an explicit time zone.

### Finding 3: The "roll to next period" rule only writes a note and has no real effect (medium-high confidence)
File: ApprovalService.cs, lines 18-20

The only effect is setting `DecisionNote = "Rolled to next period"`. Nothing records or uses a period, and `DecidedAt` is still the current time. The invoice is approved normally, so the intended rule is not implemented. This also overwrites any `DecisionNote` already set on the invoice, which loses data. `Approve(invoiceId, approver)` has no note parameter, but the note could be set earlier, and overwriting it is risky.

### Finding 4: Rule is untested and not deterministic (high confidence)
Project convention: every new rule needs tests, and none are in the diff. The rule depends on `DateTime.Now`, so tests cannot cover the boundary cases: 17:59 against 18:00, the last day against other days, and December to January. The `now.AddDays(1).Month != now.Month` check is correct for the last-day test. Without a clock abstraction, these cases cannot be tested reliably.

### Minor
The rule is business logic placed inline in `Approve`. The rule belongs in the Domain project (which is where this is), but it should be a named method or constant (`18` is a magic number). This is low severity.

No other defects found in the diff.
