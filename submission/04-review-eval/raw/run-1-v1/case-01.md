## Review of case-01 (BulkApprove endpoint)

File: backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs

**1. Line 21 (`foreach (var id in request.Ids)`): null Ids causes NullReferenceException (HTTP 500). Confidence: high (~95%).**
`BulkApproveRequest(List<string>? Ids)` is explicitly nullable. A body of `{}` or `{"ids": null}` leaves `Ids` null, and the loop throws. An empty or missing body can also give a null `request`. The result is a 500 instead of a 400. Add a null or empty check and return BadRequest.

**2. Lines 21-24: not atomic, so a failure partway leaves partial state. Confidence: high (~90%).**
`_approvals.Approve(id, ...)` is called in a loop with no try/catch and no pre-validation. The service throws on an unknown id (mapped to 404), an invalid state (409), or other rule violations. If the third id fails, invoices 1 and 2 are already approved and persisted (the repository is in-memory with no transaction). The client gets an error response and cannot tell which invoices were approved, and retrying will hit 409 on the ones already approved. Either validate all ids first and then apply, or return per-item results (success or error for each id).

**3. Line 23: calls `_approvals.Approve` directly, outside `Handle(...)`. Confidence: medium-high (~80%).**
AGENTS.md says controllers use `Handle(...)` so service errors map to 404, 409 and 400. The other actions go through `Handle`, but here the domain exceptions are not mapped. They will probably surface as 500 errors instead of 404 or 409. This compounds findings 1 and 2.

**4. Lines 21-24: no limit, no duplicate handling, no id validation. Confidence: medium (~60%).**
The list size is unbounded, which allows a large-request DoS or long lock time. Duplicate ids in the list make the second `Approve` fail with a state conflict, which then trips finding 2. Null or empty-string ids are not checked.

**5. Approval authorization and separation of duties. Confidence: low-medium (~40%).**
`[RequireRole("Approver")]` matches the single approve endpoint as seen in the neighbouring code. AGENTS.md says approvals are Approver or Admin, so check that Admin is also allowed (the attribute may accept only the one role). Also check that the single-approve path does not have extra rules, such as a self-approval check or an amount limit, that the bulk path would bypass. This cannot be confirmed from the diff alone.

**6. Missing tests. Confidence: high (~90%).**
AGENTS.md requires tests for every new endpoint. The diff adds none (null ids, empty list, partial failure, unknown id, role check).

**7. Response shape. Confidence: low (~30%).**
`results.Select(DecisionResponse.From)` is returned as a lazy enumerable. This is fine to serialize, but it is inconsistent with the single endpoint and gives the client no per-id status. The `results` list is also redundant, since the `Select` could be done inline. This is minor.

No other issues found in the diff.
