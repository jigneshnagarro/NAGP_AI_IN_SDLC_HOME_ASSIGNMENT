No defects found.

The diff is a pure rename of the `ApprovalService` field and constructor parameter from `_repository`/`repository` to `_invoices`/`invoices`. I checked each hunk:

- The field declaration, the constructor parameter and the constructor assignment are renamed together.
- All four usages are updated: `Update` in the submit, approve and reject methods, and `GetById` in `Find`.
- No reference to the old name `_repository` remains in the visible hunks.
- Behaviour is unchanged. The status transitions, `DecidedBy`/`DecidedAt` assignments and the `KeyNotFoundException` path are untouched.
- The constructor parameter name changes. That would only matter to a caller using named arguments (`repository: ...`) or to reflection or DI that binds by parameter name. Standard ASP.NET Core DI binds by type, so this is very unlikely to break anything. Confidence that this is harmless: high (about 90%). I could only see the diff, so I could not search for other callers.

Confidence that the diff contains no behavioural defect: high.
