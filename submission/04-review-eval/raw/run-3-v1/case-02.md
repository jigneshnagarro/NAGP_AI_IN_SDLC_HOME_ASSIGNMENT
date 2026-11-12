## Review of case-02 diff

### Finding 1: SQL injection via `customer` parameter
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: 16 (new `Search` method, `var sql = $"SELECT * FROM Invoices WHERE CustomerName LIKE '%{customer}%'";`)
- What goes wrong: The user-supplied `customer` query string value is interpolated directly into the SQL text. An input such as `' OR 1=1 --` or `'; DROP TABLE Invoices; --` changes the query. The result is data disclosure, modification or deletion, depending on what `_queries.Run` allows. Fix: use parameterized queries (e.g. `WHERE CustomerName LIKE @customer` with the value passed as a parameter), or use the repository with in-memory filtering.
- Confidence: high (about 99%).

### Finding 2: SQL injection via `status` parameter
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: 20 (`sql += $" AND Status = '{status}'";`)
- What goes wrong: Same problem as above. `status` is concatenated into the SQL unescaped. Because it is appended after the first clause, an attacker can use either parameter independently. Fix: bind it as a parameter, or validate it against the allowed status enum values (Draft, PendingApproval, Approved, Rejected).
- Confidence: high (about 99%).

### Finding 3: `_queries` is not defined or registered in this diff
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: 23 (`return Ok(_queries.Run(sql));`)
- What goes wrong: The diff shows no `_queries` field, constructor injection, or `Program.cs` registration. Unless it already exists in the controller outside the shown hunk, the code will not compile. It also appears to introduce a raw-SQL execution abstraction into an app that otherwise uses an in-memory repository, and the project conventions say there is no database. This looks like an invented or unsupported dependency.
- Confidence: medium (about 60%). The surrounding file is not visible, so the field may already exist.

### Finding 4: No authorization restriction on the endpoint
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: 13-14 (`[HttpGet("search")]`)
- What goes wrong: The endpoint has no `[RequireRole(...)]` attribute. If the controller or base class does not enforce sign-in, this exposes the data. Combined with the injection, any signed-in user can read arbitrary tables. Even if class-level sign-in applies, a raw-SQL endpoint should be restricted.
- Confidence: low to medium (about 35%). It depends on class-level attributes not shown in the diff.

### Finding 5: `customer` is a non-nullable `string` with no validation, and the search logic is in a controller
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: 14
- What goes wrong: A missing `customer` is bound as null (or rejected as a 400 under the nullable-aware model validation default). If it reaches the query as null, the interpolation produces `LIKE '%%'`, matching everything. Search and filtering logic and query building also belong in the Domain project (a stated convention), not in the controller.
- Confidence: medium (about 50%) for the null-handling behavior, high that it violates the convention.

### Finding 6: No tests
- File: backend/tests (none added)
- What goes wrong: The diff adds a new endpoint with no accompanying tests, which the project requires for every new endpoint. The absence of tests means the injection and filtering behavior is unverified.
- Confidence: high (about 90%).

### Summary
Do not merge as is. The two SQL injection findings (lines 16 and 20) are blocking issues.
