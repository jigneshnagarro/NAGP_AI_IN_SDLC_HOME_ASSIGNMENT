## Findings

### 1. Thread-safety regression: ConcurrentDictionary replaced with Dictionary
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Line: 9 (the `_invoices` field declaration, changed from `ConcurrentDictionary` to `Dictionary`)
- Confidence: high (about 90%), assuming the repository is registered as a singleton, which is the usual pattern for an in-memory repository in ASP.NET Core. I could not confirm the registration from this diff.

What goes wrong: ASP.NET Core handles requests concurrently. A plain `Dictionary<string, Invoice>` is not safe for concurrent writes, or for reads that overlap a write. Simultaneous `Add`/`Update` calls can corrupt the internal buckets and entries. That can cause lost invoices, an infinite loop in `TryGetValue` or the indexer, `InvalidOperationException`, or `NullReferenceException`. Any enumeration (for example a list-all method elsewhere in the file) can also throw "Collection was modified".

### 2. Check-then-act race in `Add` (line 19-27)
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Line: about 19-27 (`ContainsKey` followed by `_invoices[invoice.Id] = invoice`)
- Confidence: high (about 90%)

What goes wrong: `TryAdd` was atomic. The replacement is not. Two concurrent `Add` calls with the same id can both pass `ContainsKey`, and then the second silently overwrites the first. The duplicate-id guard ("already exists", which the API presumably maps to 409) no longer works under concurrency, and data is lost without any error. Even with a lock this would need to be a single critical section.

### Suggested fix
Revert to `ConcurrentDictionary` and `TryAdd`. If a plain `Dictionary` is wanted for some reason, guard every read and write with one `lock`.

### Other notes
- The diff gives no reason for the change, and it removes the atomic guarantee that `Add` relied on.
- `Update` (`_invoices[invoice.Id] = invoice`) is syntactically unchanged but is now unsafe, for the same reason as finding 1.
- The diff does not show any tests covering concurrency, and none were added.
