## Findings

### 1. Missing authorisation on destructive endpoint
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: the new `Delete` action (diff lines 20-21, new-file lines ~44-45)
- Quoted line: `[HttpDelete("{id}")]` followed by `public IActionResult Delete(string id)`. There is no `[RequireRole("Admin")]` attribute.
- What goes wrong: the neighbouring `Update` action carries `[RequireRole("Admin")]`, but the new `Delete` does not. Any signed-in user, including a user with a non-Admin role, can permanently delete any invoice by id. Destructive actions are supposed to be Admin only.
- Confidence: high (about 90%). The only caveat is that I cannot see the controller class header, so a class-level `[RequireRole]` could exist. The `Update` method has its own attribute, which suggests the roles are applied per action.

### 2. No existence check, and the result is always 204
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: `_repository.Delete(id);` and `return NoContent();`
- What goes wrong: the call is not wrapped in `Handle(...)`, which the sibling `Add` action uses. A missing id is therefore not mapped to 404. Depending on the repository, it either throws an unhandled exception (a 500 error) or silently returns 204 for an id that does not exist. The action also does not check the invoice's state, so Approved invoices can be deleted without any domain rule being applied.
- Confidence: medium (about 60%). I cannot see the repository's behaviour.

### 3. User name written to the log
- File: backend/src/InvoiceApp.Api/Controllers/InvoicesController.cs
- Line: `_logger.LogInformation("Invoice {InvoiceId} deleted by {User}", id, CurrentUser.Name);`
- What goes wrong: this writes the user's name to the logs on every delete. It is low severity, since it is an audit trail, and it only matters if the name counts as personal data under the project's logging policy. The same line also logs "deleted" after `Delete` runs without any failure handling, so a failed delete would not be reflected in the log.
- Confidence: low (about 25%).

## Not found
I found no issues with injection, null input beyond the above, data races, money/rounding or time-zone handling in this diff.
