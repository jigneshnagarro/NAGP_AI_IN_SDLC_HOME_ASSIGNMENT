## Review of case-01 (BulkApprove endpoint)

**Finding 1: Null dereference on `request.Ids`**
- File: backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs, line 21 of the diff (`foreach (var id in request.Ids)`)
- What goes wrong: `Ids` is declared nullable (`List<string>?`), so a body such as `{}` or `{"Ids":null}` leaves it null. The `foreach` then throws NullReferenceException and the client gets a 500 instead of a 400. A null or missing body can also leave `request` itself null.
- Confidence: high

**Finding 2: Not atomic, partial approval on failure**
- File: same, lines 21-24 (loop calling `_approvals.Approve`)
- What goes wrong: Each invoice is approved one at a time. If a later id is unknown (404) or not in PendingApproval (409), the service error propagates and the request fails. The earlier invoices stay approved, but the client sees only an error and doesn't know which ones were approved. A retry then hits 409 on the ones already approved. There is no per-item result and no validation up front.
- Confidence: high

**Finding 3: Error handling bypasses the `Handle(...)` convention**
- File: same, line 23
- What goes wrong: Project convention is that controllers use `Handle(...)` so service errors map to 404, 409 and 400. Here the service is called directly, so domain exceptions are probably not mapped to those status codes and surface as 500s. This depends on how `Handle` works, which isn't visible in the diff.
- Confidence: medium

**Finding 4: Approval authorisation and rules not verified for the bulk path**
- File: same, line 23
- What goes wrong: The single approve action may enforce rules, such as no self-approval, that are not shown in the diff. This code relies on `Approve` to enforce them, so behaviour should match. Admin access is also unclear. `[RequireRole("Approver")]` may reject Admins, while the project convention says approvals are "Approver or Admin".
- Confidence: low to medium

**Finding 5: No limits or de-duplication on `Ids`**
- File: same, line 21
- What goes wrong: An empty list returns 200 with an empty array. A very large list is processed with no cap. Duplicate ids make the second approval fail with 409 after the first succeeded.
- Confidence: medium

**Finding 6: No tests**
- File: whole diff
- What goes wrong: The project requires tests for every new endpoint, and none are in the diff.
- Confidence: high

**Minor:** The response is a lazy `IEnumerable` from `Select`. It is fine here, but `results.Select(DecisionResponse.From)` is not materialised and the shape differs from the single-approve response.
