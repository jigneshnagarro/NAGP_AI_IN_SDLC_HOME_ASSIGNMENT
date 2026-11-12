## Review of case-10

### Finding 1: Catch-all returns 200 OK for any unexpected exception (critical)

- **File:** backend/src/InvoiceApp.Api/Controllers/ApiControllerBase.cs
- **Line:** the added `catch (Exception)` block, lines 25-28 of the diff (after the `ArgumentException` handler)
- **What goes wrong:** Any exception not already handled (NullReferenceException, a storage or repository failure, a bug in `ApprovalService`, and so on) is swallowed. The client gets `200 OK` with `{ "status": "completed" }`, so a failed operation is reported as a success. For example, an approve, reject or delete call that throws partway through reports "completed" even though nothing was done, or only part of it was. The exception is not logged and is not rethrown, so nothing in the logs or monitoring shows the failure. This also bypasses ASP.NET Core's default 500 handling and any exception middleware. It undermines the API contract that `Handle(...)` maps service errors to 404, 409 and 400. Clients, the web UI and the e2e tests can no longer tell success from failure. For an invoice approval system this can mean a user believes an invoice was approved or paid when it was not.
- **Suggested fix:** Remove the catch-all and let unexpected exceptions propagate to the framework (500 plus logging). If a catch-all is wanted, log the exception and return `StatusCode(500, ...)` or a ProblemDetails response. Add a test that an unexpected exception does not produce a 200.
- **Confidence:** Very high (about 98%). This is a definite defect, visible in the diff itself.

### Minor observations (lower confidence)

- The catch-all follows the more specific handlers, so it does not shadow them. Ordering is fine.
- No test was added for the new branch, which conflicts with the project convention that every new rule needs tests. Any test for this branch would only lock in the wrong behavior.

No other defects found in this diff.
