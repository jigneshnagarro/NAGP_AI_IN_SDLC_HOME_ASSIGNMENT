## Findings

### 1. DiscountCalculator.cs, lines 12-17 (Apply): rounding mode changed from AwayFromZero to ToZero, double rounding. Confidence: high (about 90%) that this is a defect.

What goes wrong: the old code computed `amount - discount` and rounded once, half away from zero. The new code rounds the discount to 2 decimals with `MidpointRounding.ToZero` (truncation), subtracts it, then truncates again. Two effects:

- The discount is truncated, so it is always rounded down. The customer gets a slightly smaller discount than the exact amount, and the final price is slightly higher.
  - Example: amount 10.05 at 15% gives a discount of 1.5075. Old result: 10.05 - 1.5075 = 8.5425, rounded to 8.54. New result: discount 1.50, 10.05 - 1.50 = 8.55. The result differs by one cent.
- Rounding twice means errors can compound, and the result no longer equals the exact discounted price rounded to the nearest cent.

Any existing tests that expect half-away-from-zero results (for example a .5 midpoint case) will likely fail or silently change the amounts billed. The diff contains no tests and no explanation of why the rounding policy changed. If the change was intentional (a business decision to round in the company's favour), it needs a test and a note. If it was not intentional, revert to a single `Math.Round(amount - discount, 2, MidpointRounding.AwayFromZero)`.

### 2. DiscountCalculator.cs, line 16 (secondary): `MidpointRounding.ToZero` is not a midpoint-rounding mode in the usual sense. Confidence: medium.

`ToZero` is a directed (truncating) mode and acts on every value, not only exact midpoints. This is why a value like 8.5499 becomes 8.54 instead of 8.55. This is probably not the intended behaviour for a price calculation, and it could produce negative or off-by-one-cent results for negative amounts or refunds.

### 3. No test changes. Confidence: high.

The project convention is that every new rule needs tests. This diff changes the monetary rounding behaviour and adds no tests.

No other defects found in the diff.
