# Review of case-02

## Finding 1: SQL injection via `customer` (confidence: very high)

File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs, line 23 of the diff (new `Search` method)

Changed line:
`var sql = $"SELECT * FROM Invoices WHERE CustomerName LIKE '%{customer}%'";`

The unvalidated query-string value `customer` is interpolated straight into the SQL text and then passed to `_queries.Run(sql)`. A caller can send `customer=' OR 1=1 --` to return every invoice. They can also use UNION or stacked statements to read other tables or modify data, depending on what the backing store allows.

## Finding 2: SQL injection via `status` (confidence: very high)

File: same file, line 27 of the diff

Changed line:
`sql += $" AND Status = '{status}'";`

This has the same flaw as finding 1. The `status` value comes from the request and is concatenated into the query unescaped, for example `status=x' OR '1'='1`. Parameterised queries are required here, not input trimming.

## Finding 3: Missing null validation on `customer` (confidence: medium)

File: same file, line 21 of the diff

Changed line:
`public IActionResult Search([FromQuery] string customer, [FromQuery] string? status)`

`customer` is declared non-nullable but is never checked. If it is missing or empty, the query becomes `LIKE '%%'`, which matches every invoice. If nullable-reference validation is not enforced, the string interpolation silently treats null as empty. In both cases a request that should be rejected with 400 returns the full invoice table. This is lower severity than the injection findings, which already allow the same result.

## Finding 4: Result set exposed without any role restriction (confidence: low to medium)

File: same file, line 20 of the diff

Changed line:
`[HttpGet("search")]`

The endpoint has no `[RequireRole(...)]`. The project convention (AGENTS.md) says every endpoint is behind sign-in and actions are restricted by role. The diff does not show whether the controller or its base class already applies sign-in, so I cannot confirm the endpoint is unauthenticated. If there is no controller-level restriction, this endpoint is an unauthenticated route to arbitrary SQL. Combined with findings 1 and 2, that would make it an exposure of all invoice data.

## Other notes (not findings)

`_queries` is not declared in this diff, and `SELECT *` returns every column. I could not verify either from the diff, so I am not reporting a defect for them.

No defects found for the rest of the checklist (data races, swallowed exceptions, money/rounding, time zones, logging of secrets). The diff contains no code touching them.
