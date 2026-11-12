## Findings

### 1. Catch-all returns HTTP 200 "completed" for any unexpected exception
- File: backend/src/InvoiceApp.Api/Controllers/ApiControllerBase.cs
- Line: the added `catch (Exception) { return Ok(new { status = "completed" }); }` (diff lines 25-28, just after the ArgumentException handler)
- What goes wrong: Any unhandled failure inside `action()` is now reported to the client as a success. That includes NullReferenceException, repository or storage errors, and any bug in a domain rule. For example, an approve, reject or delete call that throws unexpectedly tells the caller `{ "status": "completed" }` with a 200, although nothing happened or the state is only partly changed. The UI and API clients cannot tell success from failure, so a user may believe an invoice was approved or paid when it was not. This is a data-integrity and correctness bug in an approval workflow.
- Second problem: the exception is swallowed. It is not logged and the variable is not captured, so the failure leaves no trace and cannot be diagnosed. It also bypasses ASP.NET Core's default 500 handling and any exception middleware.
- Fix: remove the catch-all and let unexpected exceptions propagate to the framework (500 plus logging). If a handler is wanted, log the exception and return `StatusCode(500, ...)` or a ProblemDetails response, never 200.
- Confidence: high (about 95%).

### 2. Related: success response shape is inconsistent
- Same location. The fake body `{ status = "completed" }` has a different shape from the real `Ok(action())` result, so clients that parse the response may misbehave. Confidence: medium. This is secondary to finding 1.

### 3. No test accompanies the change
- The project convention requires tests for every new rule or endpoint. No test is included, and a test of this behaviour would have exposed the problem. Confidence: medium-high.

## Summary
The change should not be merged. The catch-all handler turns every unexpected server error into a false success.
