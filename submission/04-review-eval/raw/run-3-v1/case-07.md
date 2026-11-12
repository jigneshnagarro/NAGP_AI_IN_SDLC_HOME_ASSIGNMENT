## Findings

### 1. Sensitive data logged: full invoice payload and the whole user session object
- File: backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs
- Line: the added `_logger.LogInformation(...)` call in `Approve`, diff lines 16-18 (new lines about 34-36).
- What goes wrong: The `{@Invoice}` and `{@Session}` placeholders use Serilog/Message Templates destructuring (`@`), so the entire `invoice` and `CurrentUser` objects are serialized into the log. That writes invoice contents (amounts, vendor and customer details, any other business data) and whatever `CurrentUser` holds into logs. A session object commonly carries identifiers, email, roles and possibly tokens or claims. Logs usually have wider access, longer retention and fewer controls than the application database. This is a sensitive-data exposure and a compliance risk (PII, financial data). It also breaks the project rule "Never commit ... customer data". It would let anyone with log access read session details and possibly hijack or impersonate a user if tokens are present.
- Fix: Log only identifiers, for example `invoice.Id`, the new status and `CurrentUser.Name` (or a user id). Do not destructure whole objects.
- Confidence: high (about 90%) that this is a defect. The exact fields exposed depend on the `Invoice` and `CurrentUser` types, which are not in the diff. Even in the best case, the log entry carries far more than needed.

### 2. Minor: no `_logger` shown in the diff
- File: ApprovalsController.cs, same line.
- What goes wrong: The diff does not show a `_logger` field or an `ILogger` constructor injection. If the controller does not already have one, this will not compile.
- Confidence: low (about 25%). It may already exist in the unchanged part of the file.

### 3. Minor: no test added
- The change adds behaviour in a controller with no test. The project convention requires tests for new rules or endpoints, but this is only a log line, so the impact is low.
- Confidence: low.
