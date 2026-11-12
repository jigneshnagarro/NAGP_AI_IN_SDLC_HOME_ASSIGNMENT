## Review of case-03

### Finding 1: Rounding mode change plus double rounding alters money amounts

- File: backend/src/InvoiceApp.Domain/DiscountCalculator.cs
- Line: the changed return statement, new lines 23-24 of the hunk (`@@ -12,9 +12,9 @@`, inside `Apply`)
- Quoted line: `return Math.Round(amount - Math.Round(discount, 2, MidpointRounding.ToZero),`
  `2, MidpointRounding.ToZero);`
- What goes wrong: The original code computed `amount - discount` and rounded once to 2 decimals with `MidpointRounding.AwayFromZero`. The new code does two things.
  1. It rounds the discount to 2 decimals first, then subtracts, so rounding now happens twice.
  2. It uses `MidpointRounding.ToZero`, which truncates and no longer rounds half away from zero.
  Truncating the discount rounds it down, so the customer gets a smaller discount and the discounted total comes out higher. Example: amount 10.00 at 12.5% gives discount 1.25, which is unchanged. Amount 19.99 at 15% gives discount 2.9985. The old code gave 19.99 - 2.9985 = 16.9915, which rounds to 16.99. The new code truncates the discount to 2.99, gives 17.00, and truncates that to 17.00. The result is 1 cent higher than before. Totals change on a large share of invoices, so this is a systematic billing shift on every discounted invoice. Nothing in the diff suggests a deliberate rounding-policy change.
  Because `ToZero` truncation also applies to the final result, the final amount is never rounded to the nearest cent. Any amount that is not an exact 2-decimal value is biased downward in magnitude.
- Confidence: high (about 90%) that behaviour changes and that totals differ from before. I cannot tell from the diff alone whether the change is intentional. If it is not, it is a defect. If it is intended, the diff has no tests or description that say so.

### Other checks from the list

I checked the diff for these categories and found nothing to report in the diff: authorisation, null or unvalidated input, injection, data races, swallowed exceptions or status codes, time-zone handling, and secrets or personal data in logs.

Not reported as defects, because the changed lines do not show them: there is no validation of `discountPercent` (for example negative values or values over 100), and the diff adds no tests. Both are unchanged context or absent files rather than changed lines, so they are noted here only for the author.
