## Findings

### 1. Rounding mode changed from AwayFromZero to ToZero, silently changing invoice totals
- File: backend/src/InvoiceApp.Domain/DiscountCalculator.cs
- Line: the new return statement in `Apply` (about lines 15-16 of the diff, the `Math.Round(... MidpointRounding.ToZero ...)` calls)
- What goes wrong: The original rounded the final amount to 2 decimals with `MidpointRounding.AwayFromZero`. The new code uses `MidpointRounding.ToZero`, which truncates rather than rounds. `ToZero` is not a half-up rounding mode: it drops every digit beyond the second decimal, not only exact midpoints. Examples:
  - amount 10.00, 12.5% discount: discount = 1.25, result 8.75. No change.
  - amount 19.99, 15% discount: discount = 2.9985. It is truncated to 2.99, so the result is 17.00. The original gave 19.99 - 2.9985 = 16.9915, which rounds to 16.99. The customer is now charged 1 cent more.
  - amount 33.33, 33.33%: discount = 11.108889, truncated to 11.10, so the result is 22.23. The original gave 22.221111, which rounds to 22.22.
  - Truncating the discount rounds the discount down, so the discounted price rounds up. The customer systematically gets a smaller discount than they are entitled to, by up to 1 cent per call. This is a monetary behaviour change that favours the seller.
- Confidence: high (about 95%) that results differ from the previous behaviour. Whether the change is intended is unknown, because the diff has no description or tests.

### 2. Double rounding
- File: backend/src/InvoiceApp.Domain/DiscountCalculator.cs, same lines
- What goes wrong: The discount is rounded to 2 decimals first, then `amount - discount` is rounded again. The inner rounding introduces the error described above. If `amount` has more than 2 decimals, the outer truncation can add a further 1-cent error. The result can differ from the mathematically correct discounted price by more than one rounding step.
- Confidence: medium-high (about 80%).

### 3. Negative or out-of-range inputs
- File: same
- What goes wrong: `ToZero` behaves differently for negative values. For a negative amount (credit note) or a discount percent over 100, truncation pushes the result toward zero instead of away from it. The old code rounded the same way in both directions. No validation exists for these inputs, and the change makes them behave inconsistently.
- Confidence: low-medium (about 50%). Depends on whether such inputs reach this method.

### 4. No tests and no stated reason
- The diff touches money-handling business logic with no test changes. AGENTS.md says every new rule needs tests. Existing tests that assert AwayFromZero results (for example a midpoint like 0.005) may fail or may now be untested.
- Confidence: medium (about 70%). The diff shows no test files, but the tests may be elsewhere.

## Summary
The main defect is the unexplained switch from `AwayFromZero` to `ToZero` combined with rounding the discount before subtracting. Together these change invoice totals by up to 1 cent in the seller's favour. If a different rounding policy was intended, it should be stated and covered by tests. Otherwise, revert to a single `Math.Round(amount - discount, 2, MidpointRounding.AwayFromZero)`.
