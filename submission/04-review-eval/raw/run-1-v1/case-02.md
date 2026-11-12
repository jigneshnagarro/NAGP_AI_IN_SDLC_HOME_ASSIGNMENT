## Findings

### 1. SQL injection via `customer` parameter
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: 16 (new `Search` method; `var sql = $"SELECT * FROM Invoices WHERE CustomerName LIKE '%{customer}%'";`)
- What goes wrong: The user-supplied query string value is interpolated directly into the SQL text. An input such as `' OR 1=1 --` or `'; DROP TABLE Invoices; --` changes the query's meaning, so a caller can read every invoice, read other tables via UNION, or modify or destroy data, depending on what `_queries.Run` allows. The value should be passed as a bound parameter instead.
- Confidence: High (about 95%).

### 2. SQL injection via `status` parameter
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: 20 (`sql += $" AND Status = '{status}'";`)
- What goes wrong: This has the same flaw as finding 1. `status` is concatenated into the query unescaped, so a value like `x' OR '1'='1` bypasses the filter or injects arbitrary SQL.
- Confidence: High (about 95%).

### 3. `_queries` is not declared or registered in the diff
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: 23 (`_queries.Run(sql)`)
- What goes wrong: The diff shows no `_queries` field, constructor injection or `Program.cs` registration, so the code may not compile. Nothing in the repo conventions describes a raw-SQL runner. Per the project conventions, the app uses an in-memory repository with no database, so this appears to introduce a raw SQL execution path that doesn't fit the architecture.
- Confidence: Medium (about 60%), because the field may exist outside the visible diff.

### 4. Business and query logic in the controller, with no tests or role restriction
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Lines: 13-24
- What goes wrong: The endpoint builds queries in the controller, which violates the rule that business rules belong in the Domain project behind a repository interface. The diff includes no tests, which the project requires for every new endpoint. It also shows no `[RequireRole]`. Sign-in is applied to every endpoint by convention, but combined with the injection this exposes all customer data to any signed-in user.
- Confidence: Medium (about 70%) for the convention violations. Whether missing roles matters depends on the base class.

### 5. `customer` is declared non-nullable but not validated
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: 14
- What goes wrong: A missing `customer` value yields an empty or "null" string. With `LIKE '%%'` this returns all invoices, and under nullable-reference-type settings, a missing value may cause a 400 or an unexpected result. Wildcard characters `%` and `_` in the input are also not escaped. This is minor next to the injection.
- Confidence: Low to medium (about 40%).

## Summary
The main defect is the SQL injection in both parameters, and it should block the merge. The fix is to use parameterized queries, or better, a repository method that filters invoices in the Domain/Api layers, together with tests.
