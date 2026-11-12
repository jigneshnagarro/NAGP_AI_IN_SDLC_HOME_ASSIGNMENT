## Review of case-05

Findings:

1. **File:** backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs, the new `Delete` action (added at about line 44, directly above `Update`)
   **What goes wrong:** The `Delete` endpoint has no `[RequireRole("Admin")]` attribute. The neighbouring `Update` action does have it. As far as the diff shows, any signed-in user, including an Approver, can delete any invoice. Deletion is destructive, and the project convention is that destructive actions are Admin only.
   **Confidence:** High (about 90%). The one caveat is that the diff does not show whether the controller or its base class applies a role requirement at class level. The diff context suggests it does not, because `Update` carries its own attribute.

2. **File:** same file, same `Delete` action
   **What goes wrong:** The action calls `_repository.Delete(id)` directly, without the `Handle(...)` wrapper used by `Add` and the other actions. A missing invoice therefore will not map to 404 as the convention expects. Depending on the repository, it either throws and returns a 500, or silently returns 204 for an id that does not exist. The code then logs "deleted" and returns `NoContent` even if nothing was deleted.
   **Confidence:** Medium-high (about 75%). I cannot see how the repository handles a missing id.

3. **File:** same file, same `Delete` action
   **What goes wrong:** There is no lifecycle check. An invoice that is Approved, or PendingApproval, can be deleted outright. This looks like a business rule that belongs in the Domain project, for example in `ApprovalService`. The convention says not to put business logic in controllers, and this action also skips the domain layer entirely. It could destroy approved financial records.
   **Confidence:** Medium (about 60%). The intended rules are not stated in the diff.

4. **File:** same file, same `Delete` action
   **What goes wrong:** The diff adds no tests. The project requires tests for every new endpoint. A test would also catch the missing role check and the missing-id behaviour.
   **Confidence:** High (about 90%) that the tests are missing. This is a process defect, not a runtime bug.

5. **File:** same file, same `Delete` action (minor)
   **What goes wrong:** The code uses `_logger` and `CurrentUser.Name`. I cannot confirm from the diff that `_logger` is injected into the controller or that `CurrentUser` exists on the base class. If either is missing, the code will not compile.
   **Confidence:** Low (about 25%).

Summary: the main defect is the missing `[RequireRole("Admin")]`, which is an authorization gap on a destructive endpoint. It should be fixed before merge. The missing-id handling and the lack of tests should be fixed as well.
