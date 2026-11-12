# Scoring key

The repo doesn't say which cases have defects, so this is my own reading of each diff.

| Case | Defect? | What "caught" has to name | Confidence |
|---|---|---|---|
| 01 | Yes | `request.Ids` is nullable, so a null body gives a NullReferenceException/500. The loop isn't wrapped in `Handle`, so one bad id gives a 500 after earlier invoices were already approved (partial bulk). It also drops Admin from the roles. | High |
| 02 | Yes | SQL injection: `customer` and `status` interpolated into the query | High |
| 03 | Yes | Rounding switched to `MidpointRounding.ToZero` for both the discount and the total. The discount is truncated, so the customer can be overcharged by up to 1 cent, with no test. | Medium (could be intended) |
| 04 | No | Rename of `_repository` to `_invoices` | High |
| 05 | Yes | `Delete` has no `[RequireRole("Admin")]`, so any signed-in user can delete. It also returns 204 for an id that doesn't exist. | High |
| 06 | No | Tests only | High |
| 07 | Yes | Logs the whole invoice and the session object (`{@Session}`), so customer and session data ends up in the logs | High |
| 08 | Yes | `ConcurrentDictionary` → `Dictionary` in a singleton: data race, and check-then-add is no longer atomic | High |
| 09 | Yes, docs | README says signing out and back in resets the sample data. False: the repo is a singleton seeded once (`AddSingleton` in `Program.cs`), and `AuthController.Login` only creates a session. The config change itself is fine. | Medium |
| 10 | Yes | `catch (Exception)` returns 200 `{status: "completed"}`, so every failure looks like a success | High |
| 11 | Yes | `DateTime.Now` instead of `UtcNow` for `DecidedAt` and the cut-off: the audit timestamp depends on the server time zone | High |
| 12 | No | Constant extraction, same behaviour | High |

9 defect cases (01, 02, 03, 05, 07, 08, 09, 10, 11), 3 clean (04, 06, 12).

Note on 09: my first version of this key had 09 as clean. All the v1 reviews flagged the README line, so I went back to the
code before scoring, confirmed the line is wrong, and changed it. Changing a key after seeing results is a bias risk, so
the README for this task shows how the numbers come out under both versions.

## Rules I scored by

- caught: names the defect above, for the right reason. A vague "could be improved" near the line doesn't count.
- missed: a defect case where the defect isn't named.
- false_alarm: a clean case where the review claims a defect that isn't there. Style comments don't count.
- clean_ok: a clean case with nothing wrong reported, or only style.
- If a review finds the real defect plus an invented one, it's scored caught and the invented one goes in notes.
