## Review of case-10

### Finding 1: Catch-all returns 200 OK on any unexpected exception (critical defect)

- File: backend/src/InvoiceApp.Api/Controllers/ApiControllerBase.cs
- Line: the new `catch (Exception)` block, diff lines +25 to +28 (around line 29 of the file)
- Confidence: high (about 95%)

What goes wrong: The new `catch (Exception) { return Ok(new { status = "completed" }); }` swallows every error that is not a KeyNotFoundException, InvalidOperationException or ArgumentException. Examples are NullReferenceException, repository or storage failures, and unexpected domain bugs. The client then receives HTTP 200 with `{ "status": "completed" }`, so a failed operation is reported as a success.

Concrete impact for this app:
- An approve, reject or delete action that actually failed (or only partly completed) is shown to the user as completed. This corrupts the invoice approval workflow, because users and the UI believe an invoice was approved or rejected when it was not.
- The exception is not logged and not rethrown. Any ASP.NET Core exception handling or error middleware, 500 responses, monitoring and alerting never see it. Failures become invisible and hard to debug.
- It is a fail-open pattern. If an authorization or validation step throws something unexpected, the caller still gets a success response.
- It masks existing bugs and any test that expects a 500 or an error. It also fakes a "completed" status for actions that return no such field.

Suggested fix: Remove the catch-all. Let unexpected exceptions propagate so the framework returns a 500 and logs it. If a catch-all is needed, log the exception and return `StatusCode(500, new { error = "Unexpected error" })`, never 200. Add a test that an unexpected exception from the action does not produce a 2xx response.

### Finding 2: Missing tests (low severity)

- File: backend/src/InvoiceApp.Api/Controllers/ApiControllerBase.cs
- Confidence: medium (about 70%)

The change adds new error-handling behavior with no accompanying test. The project convention requires tests for every new rule or endpoint.

### Summary

The diff should not be merged as is. The catch-all returning 200 is a serious correctness and observability bug.
