## Review of case-06 diff (ApprovalServiceTests.cs)

I found no defects that would make these tests fail or give false results. The diff adds three xUnit tests. Findings are limited to the points below, ordered by importance.

1. File: backend/tests/InvoiceApp.Tests/ApprovalServiceTests.cs, line 35 (`Assert.InRange(result.DecidedAt!.Value, before, DateTime.UtcNow)`).
   - What could go wrong: this only passes if the service stamps `DecidedAt` with `DateTime.UtcNow`. If it uses `DateTime.Now`, or sets `DateTimeKind` differently, the comparison can fail or pass for the wrong reason. `DateTime` comparison ignores `Kind`, so a local-time stamp would fail only in time zones ahead of UTC.
   - Why it is minor: the test is not flaky in the normal case, because `before` is captured before the call and the upper bound is evaluated after it. Clock resolution can make equal values compare as in range, and `InRange` is inclusive.
   - Confidence: low (about 20%). It is a robustness concern, not a bug.

2. File: same file, lines 13-21 (`Reject_WithWhitespaceReason_Throws`).
   - What could go wrong: the test asserts `ArgumentException`, and `Assert.Throws<T>` requires the exact type. If the service throws `ArgumentNullException` or a custom validation exception, the test fails. AGENTS.md says the controller maps service errors to 400, so `ArgumentException` is plausible, but I cannot see `ApprovalService` in this diff.
   - Gap: the test does not check that the invoice stayed Pending after the rejected call. It could pass even if the status changed before the throw.
   - Confidence: low (about 15%).

3. File: same file, lines 38-44 (`Approve_UnknownInvoice_Throws`).
   - What could go wrong: it asserts `KeyNotFoundException`. This depends on the service or repository throwing exactly that type, which I could not verify from the diff.
   - Confidence: low (about 15%).

Not defects, but checked:
- `Pending(...)` and `FakeInvoiceRepository` are used the same way as in the existing tests visible in the diff context.
- The new tests add no one-letter variables or flag parameters.
- The diff does not show whether `DecidedBy` and `DecidedAt` exist on the returned invoice type. Compilation depends on that, and I could not confirm it from this file alone.

Conclusion: no confirmed defects. The tests are reasonable additions, with only the low-confidence assumptions above.
