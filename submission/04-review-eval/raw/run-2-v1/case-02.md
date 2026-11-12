## Findings

### 1. SQL injection via `customer` and `status`
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Lines: 16 and 20 of the diff (the two interpolated `sql` strings in `Search`)
- What goes wrong: `customer` and `status` come straight from the query string and are interpolated into the SQL text. A caller can send `customer=' OR 1=1 --` to dump every invoice. Depending on what `_queries.Run` executes, they could also append statements, read other tables or modify data. `status` has the same problem, because `' OR '1'='1` closes the quote early. The fix is to use parameterized queries (`@customer`, `@status`, with the `%` wildcards added to the parameter value) or an ORM/LINQ filter. Allow-list `status` against the known enum values.
- Confidence: high (about 99%). This is the textbook pattern and needs no extra context.

### 2. Endpoint is missing the access check the repo requires
- File: InvoicesController.cs, line 13 of the diff (`[HttpGet("search")]`)
- What goes wrong: I can only see the diff, so I can't confirm that a class-level auth attribute is absent. The project convention is that every endpoint is behind sign-in and restricted with `[RequireRole]`. This action has no visible role restriction. If the controller has no class-level attribute, anyone can run the injectable query above.
- Confidence: medium (about 50%).

### 3. `customer` is non-nullable but has no validation
- File: InvoicesController.cs, line 14 of the diff
- What goes wrong: if `customer` is omitted, behaviour depends on how nullable reference types and `[ApiController]` are configured. It either returns a 400 or produces `LIKE '%%'`, which matches every row. `LIKE` wildcards (`%`, `_`) in user input are also not escaped.
- Confidence: low to medium (about 35%).

### 4. Design and convention problems
- File: InvoicesController.cs, lines 16-23 of the diff
- What goes wrong: the controller builds query text itself. `AGENTS.md` says business logic does not belong in controllers and that repositories are interfaces in Domain with an in-memory implementation. This code introduces a raw-SQL path (`_queries`) that bypasses the repository. The diff doesn't show where `_queries` is declared, injected or registered in `Program.cs`. If it isn't, the code won't compile or will fail at runtime. The in-memory app has no SQL database at all, so `Invoices` and `CustomerName` may not exist.
- Confidence: medium (about 60%) on the convention issue. The compile and runtime failure is unverifiable from the diff alone.

### 5. No tests
- The diff adds an endpoint but no tests. The repo requires them for every new endpoint.
- Confidence: high (about 90%), based only on what the diff shows.

## Verdict
Do not merge. Finding 1 is a blocking security defect.
