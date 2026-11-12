## Findings

### 1. Sensitive data written to logs (invoice payload and full session object)
- File: backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs
- Line: the added line `invoice, CurrentUser);` in `Approve` (diff lines +23 to +25, about line 34 of the new file). The log call is `"Approval completed. Invoice payload: {@Invoice}. Session: {@Session}"`.
- What goes wrong: the `{@...}` operator tells Serilog or Microsoft.Extensions.Logging with a structured sink to destructure the whole object. Two things get logged on every approval:
  - `invoice`, the entire invoice. This likely includes supplier and customer details, amounts, bank or payment data and free-text notes. That is business data and possibly personal data.
  - `CurrentUser`, the whole authenticated user or session object. Depending on its definition this can include the name, email, roles, and a session token, claims or credential material. It is a likely path for authentication secrets and personal data to reach log storage.
- Impact: logs are usually retained longer and are more widely readable than the application database. Personal data and session secrets in them create a privacy and compliance problem (for example GDPR). A leaked session token could let someone hijack a session. The fields logged are unbounded: any property added to `Invoice` or the user type later is logged automatically.
- Fix: log only identifiers, for example `{InvoiceId}` and `{UserName}` (`invoice.Id`, `CurrentUser.Name`). Never destructure `CurrentUser`.
- Confidence: high that sensitive or personal data is logged, since the whole objects are destructured. Medium on exactly which fields are exposed, because the `Invoice` and `CurrentUser` definitions are not in the diff.

### 2. Possible missing `_logger` field (compile risk)
- File: backend/src/InvoiceApp.Api/Controllers/ApprovalsController.cs, the added `_logger.LogInformation(` line.
- The diff does not show that `_logger` is declared or injected in this controller. If it is not, the code will not compile.
- Confidence: low. The hunk shows only part of the file, so this may already exist.

## Checked, no defect found in the changed lines
- Authorisation: `[RequireRole("Approver")]` is unchanged.
- Injection: no query, command or string building is added. The message template is a constant.
- Null input: `invoice` comes from `_approvals.Approve` and is already used on the next line. `CurrentUser` is already dereferenced earlier.
- Swallowed exceptions or status codes: no change.
- Money, rounding, time zones, shared-state races: not touched.
