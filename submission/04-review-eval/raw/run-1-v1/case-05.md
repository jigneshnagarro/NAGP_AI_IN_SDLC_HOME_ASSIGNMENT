## Findings

**1. Missing authorization on destructive endpoint**
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: new `Delete` method, lines 13-19 of the diff (the `[HttpDelete("{id}")]` action)
- What goes wrong: `Delete` has no `[RequireRole("Admin")]`, while the neighbouring `Update` action is protected with it. Any signed-in user, such as the Approver demo account, can permanently delete any invoice. Deletion is destructive, so it should be restricted to Admin.
- Confidence: high (about 90%). The only uncertainty is whether the controller or base class applies a class-level role requirement that is not visible in the diff. The `Update` method carries its own attribute, which suggests there is none.

**2. No handling for a missing invoice and no `Handle(...)` wrapper**
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: `_repository.Delete(id);` in the new `Delete` method
- What goes wrong: Other actions use `Handle(() => ...)`, which maps service errors to 404, 409 and 400. This action calls the repository directly. If the invoice does not exist, the repository will probably throw, which gives a 500 instead of 404. If it silently does nothing, the action still logs "deleted" and returns 204 for an invoice that never existed.
- Confidence: medium (about 65%). I can't see the repository implementation.

**3. Lifecycle rule bypassed and business logic placed in the controller**
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: new `Delete` method
- What goes wrong: Deletion goes straight to the repository and skips the domain service (`ApprovalService`). Invoices in PendingApproval or Approved state can therefore be deleted, which loses the approval audit trail. This breaks the project rule that business rules belong in the Domain project, not in controllers.
- Confidence: medium (about 60%). There may be no rule against deleting approved invoices, but that would need a product decision.

**4. No tests**
- File: the diff touches only the controller. No test file was added.
- What goes wrong: The project requires tests for every new endpoint. Neither the role restriction nor the 404 behaviour is covered, so the authorization gap in finding 1 would not be caught.
- Confidence: high (about 90%) that tests are missing from this diff.

**Minor: log injection**
- Line: the `LogInformation` call
- What goes wrong: `id` comes from the URL and is written to the log. Structured logging limits the risk, but the value is untrusted. The log also says "deleted" even if nothing was deleted (see finding 2).
- Confidence: low (about 25%).
