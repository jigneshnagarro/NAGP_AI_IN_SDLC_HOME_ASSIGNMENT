## Review of ApprovalsController.cs (BulkApprove)

1. **ApprovalsController.cs, line 21 (`foreach (var id in request.Ids)`)**: `Ids` is declared nullable (`List<string>?`) and is never checked. A body of `{}` or `{"ids": null}` gives a NullReferenceException and a 500 response. A null `request` is possible too. Confidence: high (about 95%). Fix: return 400 when `Ids` is null or empty.

2. **ApprovalsController.cs, lines 21-24 (loop calling `_approvals.Approve`)**: The batch is not atomic and has no error handling. Each `Approve` call persists its change. The conventions say to use `Handle(...)` so service errors map to 404, 409 and 400, but this loop bypasses it. If one id is missing, or is already approved or in the wrong state, the service throws partway through. Earlier invoices stay approved, the client gets an error, and the response lists none of the approvals that did succeed. The client cannot tell which ids were approved, and a retry will hit 409s on the ones already done. Confidence: high (about 85%) that this is a defect. How the service reports errors (exception or result) is not visible in the diff, but either way the partial-success behaviour is unhandled. Fix: validate all ids first, or return per-id results, and route errors through `Handle`.

3. **ApprovalsController.cs, lines 19-26 (loop in the controller)**: The project rule is to keep business rules out of controllers. Looping over many invoices and deciding how to handle a mix of successes and failures is orchestration that belongs in `ApprovalService` (for example `ApproveMany`). Confidence: medium (about 70%), a convention violation rather than a runtime bug.

4. **ApprovalsController.cs, line 21 (no input limits)**: There is no cap on the list size and no de-duplication. Duplicate ids make the second approval fail with a conflict after the first has already been committed. A very large list is an easy way to tie up the request. Confidence: medium (about 60%).

5. **ApprovalsController.cs, line 23 (self-approval and authorization)**: `Approve(id, CurrentUser.Name)` is called for every invoice. It is not visible whether `Approve` blocks an approver from approving their own invoice, or whether a limit applies per invoice. A bulk path multiplies any gap in that check. Confidence: low (about 30%), because it depends on code outside the diff.

6. **Missing tests**: The diff adds a new endpoint and no tests. The project rule is that every new rule or endpoint needs tests. Confidence: high (about 90%), though only the diff was available, so tests could exist in another change.

7. **ApprovalsController.cs, line 26 (response shape)**: `Ok(results.Select(DecisionResponse.From))` returns a lazy enumerable, which is fine with the JSON serializer. The response gives no indication of ids that were skipped or failed. This relates to finding 2. Confidence: low (about 40%).

The route `bulk-approve` does not clash with `{id}/reject`, and `[RequireRole("Approver")]` matches the existing endpoints.
