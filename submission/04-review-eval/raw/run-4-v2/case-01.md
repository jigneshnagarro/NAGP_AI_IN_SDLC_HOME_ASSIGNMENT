## Review of case-01 (BulkApprove endpoint)

File: backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs

### Findings

1. Null input causes an unhandled NullReferenceException (HTTP 500). Confidence: high.
   - Line: `foreach (var id in request.Ids)`, in `BulkApprove`.
   - The request type declares `Ids` as nullable (`List<string>? Ids`). A body such as `{}` or `{"Ids": null}` leaves `request.Ids` null, and the foreach throws. An empty or missing body can also leave `request` itself null. The client gets a 500 instead of a 400.
   - Individual null or empty entries in the list are also passed straight to `Approve` with no validation.

2. Approvals are not atomic, so a failure part-way through leaves a partial result. Confidence: high.
   - Line: `results.Add(_approvals.Approve(id, CurrentUser.Name));` inside the loop.
   - Each call commits its own approval. If the Nth id is unknown or not in PendingApproval, `Approve` throws (the codebase maps these to 404 or 409). The invoices before it stay approved, and the caller gets only an error with no list of which ones succeeded. Retrying then fails again on the already-approved ids. There is no per-item result, no validation pass before the first write, and no rollback.

3. Service errors are not routed through `Handle(...)`, so expected 404 and 409 conditions become 500s. Confidence: medium.
   - Line: `results.Add(_approvals.Approve(id, CurrentUser.Name));`
   - The project convention is that controllers use `Handle(...)` so service errors map to 404, 409 and 400. This action calls the service directly and does not do that. I can't see `Approve` or `Handle` in the diff, so this depends on how those are implemented. If `Approve` throws domain exceptions, a missing or already-decided invoice produces an unhandled exception and a 500.

4. Duplicate ids in the request. Confidence: medium.
   - Line: `foreach (var id in request.Ids)`
   - The list is not de-duplicated. If the same id appears twice, the second `Approve` hits an already-approved invoice. That likely throws a conflict, which combined with finding 2 aborts the batch after earlier approvals have been committed.

5. No upper bound on the list size. Confidence: low.
   - Line: `public record BulkApproveRequest(List<string>? Ids);`
   - An Approver can submit an arbitrarily large list in one synchronous request. This is a minor resource-use concern.

### Checked, no defect found
- Authorisation: the endpoint has `[RequireRole("Approver")]`. I can't confirm from the diff whether Admin is also permitted, as the project conventions say ("approvals are Approver or Admin"). I'm not reporting this as a defect.
- Injection, money or rounding, time zones, and logging of secrets or personal data: nothing in the diff touches these.
- Tests: the diff includes no tests for the new endpoint. The project requires tests for every new endpoint. This is a process gap rather than a code defect, so it is not counted above.
