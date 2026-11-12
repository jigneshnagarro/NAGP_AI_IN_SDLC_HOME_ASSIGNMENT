## Findings

### 1. Thread safety removed from a shared in-memory store
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Line: 9 (the `_invoices` field declaration; new-file line, hunk starting at line 6)
- What goes wrong: `ConcurrentDictionary<string, Invoice>` was replaced with a plain `Dictionary<string, Invoice>`. A repository like this is normally registered as a singleton in ASP.NET Core and is hit by concurrent requests on thread-pool threads. `Dictionary` is not safe for concurrent writes, or for reads that overlap a write. Under load this can cause lost updates, corrupted internal buckets, `GetById` returning wrong or missing entries, exceptions, or an infinite loop in a lookup (a known failure mode of concurrent `Dictionary` mutation). The diff gives no reason for the change and adds no locking.
- Confidence: high (about 85%) that this is a defect. The one assumption is that the repository is registered as a singleton, which is the usual pattern here but is not visible in this diff.

### 2. `Add` is now a non-atomic check-then-insert
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Lines: about 19-27 (`Add`)
- What goes wrong: `TryAdd` was atomic. The replacement is `ContainsKey` followed by `_invoices[invoice.Id] = invoice`. Two concurrent `Add` calls with the same id can both pass the check. The second then silently overwrites the first, and the "already exists" `InvalidOperationException` (which `Handle(...)` presumably maps to a 409) is never raised. So the duplicate-id guarantee breaks under concurrency. The two calls can also race inside `Dictionary` and corrupt it (see finding 1).
- Confidence: high (about 85%) on the logic. It only shows up under concurrent calls, so a single-threaded unit test will not catch it.

### 3. Other members may break on a plain `Dictionary` (not visible in the diff)
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Lines: about 16-18 (the unchanged members around `GetById` and the list method)
- What goes wrong: the diff does not show the list/`GetAll` method. If it enumerates `_invoices.Values`, a concurrent `Add` or `Update` can throw `InvalidOperationException` ("Collection was modified") during enumeration. `ConcurrentDictionary` allowed that safely. `Update` (`_invoices[invoice.Id] = invoice`) is also an unsynchronized write.
- Confidence: low to medium (about 40%), because that code is outside the diff.

### 4. Minor: probable leftover import
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Line: near the top of the file (outside the shown hunk)
- What goes wrong: `using System.Collections.Concurrent;` is likely now unused. It is harmless, only a warning or cleanup.
- Confidence: low.

## Suggested fix
Revert to `ConcurrentDictionary` and keep `TryAdd`. If a plain `Dictionary` is wanted, guard every read, write and enumeration with a single `lock`, and do the existence check and insert inside the same lock. Add a concurrency test, for example parallel `Add` calls with the same id that expect exactly one success.
