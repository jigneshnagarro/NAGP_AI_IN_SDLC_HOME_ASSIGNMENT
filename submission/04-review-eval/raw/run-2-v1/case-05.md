## Review of case-05 diff

### Finding 1: Delete endpoint has no role restriction
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: new `Delete` method, the `[HttpDelete("{id}")]` attribute (diff lines 13-14, around line 44 of the file)
- What goes wrong: `Delete` has no `[RequireRole("Admin")]`. The neighbouring `Update` action is guarded by it. Any signed-in user can permanently delete any invoice, including a user with only the Approver role or any other authenticated role. This is an authorization bypass on a destructive operation. The project convention says destructive actions are Admin only.
- Confidence: high (about 95%), assuming `RequireRole` is the only role check and that no controller-wide or global policy already restricts it. The diff shows nothing like that.
- Fix: add `[RequireRole("Admin")]`.

### Finding 2: No error handling or existence check, and no `Handle(...)` wrapper
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: body of `Delete`, `_repository.Delete(id);` (diff line 16)
- What goes wrong: other actions use `Handle(() => ...)` so that service errors map to 404, 409 and 400. Here the repository is called directly. If the invoice does not exist, the repository may throw, which gives a 500 instead of 404. If it does not throw, the endpoint returns 204 for a missing invoice and logs a deletion that did not happen. The log line is written even if the delete failed to find anything.
- Confidence: medium (about 65%). The repository's behaviour for an unknown id is not visible in the diff.

### Finding 3: No lifecycle or business-rule check, and the rule is outside the Domain project
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: `Delete` body (diff lines 15-18)
- What goes wrong: the controller deletes directly from the repository and skips `ApprovalService`. An Approved or PendingApproval invoice can be hard-deleted, which breaks the audit trail. It also goes against the convention that business rules live in Domain and not in controllers.
- Confidence: medium (about 55%). It depends on whether deletion should be limited by invoice state, which the diff does not say.

### Finding 4: Missing tests
- File: backend/tests/InvoiceApp.Tests (no change in the diff)
- What goes wrong: the diff adds a new destructive endpoint with no tests. The project requires tests for every new endpoint. A test that a non-admin gets 403 would have caught Finding 1.
- Confidence: high (about 90%) that no tests are included in this diff.

### Not a defect
The use of `_logger` and `CurrentUser.Name` cannot be checked from the diff. I assume they exist in the class and the base class, since `_repository` is already used the same way. I am not flagging this.
