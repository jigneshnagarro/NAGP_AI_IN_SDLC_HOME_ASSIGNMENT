## Findings

### 1. DiscountCalculator.cs, Apply (lines ~12-17): rounding changed from AwayFromZero to ToZero, and rounding is done twice. Confidence: high (about 90%) that behaviour changes; medium whether intended.

What goes wrong:
- The original code rounded the final price once, half away from zero.
- The new code truncates (`MidpointRounding.ToZero`) the discount to 2 decimals, subtracts it from the amount, then truncates the result again.
- Truncating the discount rounds it down, so the customer gets a slightly smaller discount and the discounted price comes out slightly higher.
- Example: amount 10.05, 10% discount. The discount is 1.005. The old code gives 9.045, which rounds to 9.05. The new code truncates the discount to 1.00 and gives 9.05, so this case matches.
- Example: amount 19.99, 15% discount. The discount is 2.9985. The old code gives 16.9915, which rounds to 16.99. The new code truncates the discount to 2.99 and gives 17.00. The price is 1 cent higher than before.
- Any invoice total computed through this method may now differ by a cent from the previous output and from any existing expected values.
- Existing tests that assert rounded results may fail. If they don't, the tests don't cover these cases.

Why it is a risk:
- A silent change in money rounding affects billing and reconciliation.
- Systematically favouring the seller (discount truncated) can also be a compliance or customer-fairness problem.
- The diff gives no rationale for the change.

Suggested fix:
- If the change is unintended, revert to a single `Math.Round(amount - discount, 2, MidpointRounding.AwayFromZero)`.
- If it is intended, document the rule and add tests for midpoint and fractional-cent cases.

### 2. DiscountCalculator.cs: no input validation, and no tests in the diff. Confidence: medium.

- The diff touches no tests, although the project convention requires tests for every rule change.
- `discountPercent` is not validated. A negative value or a value over 100 yields an increased price or a negative total.
- With a negative result, `ToZero` rounding behaves differently from AwayFromZero.
- This validation gap existed before the diff, but the diff is the place to add boundary tests.

### 3. Readability. Confidence: low.

- Nesting the two `Math.Round` calls in one expression is hard to read.
- Named intermediate variables, such as `roundedDiscount`, would make the intent clearer.
- The old `discounted` variable was removed.
