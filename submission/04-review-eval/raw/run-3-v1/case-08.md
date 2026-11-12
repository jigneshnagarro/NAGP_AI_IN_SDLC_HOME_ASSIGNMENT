## Findings

### 1. Thread-unsafe shared state: ConcurrentDictionary replaced with Dictionary
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Line: 9 (field declaration `private readonly Dictionary<string, Invoice> _invoices = new();`)
- What goes wrong: In ASP.NET Core the repository is typically registered as a singleton and is shared across concurrent requests. A plain `Dictionary` is not safe for concurrent reads and writes. Simultaneous `Add`/`Update`/`GetById`/`GetAll` calls can corrupt the internal buckets, throw exceptions (for example "Operations that change non-concurrent collections must have exclusive access"), or loop forever on a corrupted bucket chain. Enumerating the dictionary (the `GetAll`-style method) while another request writes throws `InvalidOperationException`.
- Confidence: high (about 90%). It is lower only because the DI lifetime is not visible in this diff. It is a singleton in any in-memory repository design.

### 2. Check-then-act race in Add (lost uniqueness guarantee)
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Line: about 19-26 (`Add`)
- What goes wrong: The atomic `TryAdd` became `ContainsKey` followed by an indexer assignment. Two concurrent requests with the same invoice id can both pass the `ContainsKey` check. The second then silently overwrites the first instead of throwing "already exists", so the duplicate-detection behavior (which the service layer presumably maps to 409) is lost. Concurrent mutation can also corrupt the dictionary, as in finding 1.
- Confidence: high (about 90%).

### 3. Update writes are now unsynchronized
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Line: about 29 (`Update`, unchanged line but now operating on a non-thread-safe type)
- What goes wrong: `_invoices[invoice.Id] = invoice` was safe on a `ConcurrentDictionary`. On `Dictionary` it can corrupt state when it runs concurrently with `Add` or reads. This is a consequence of finding 1 rather than a separate edit.
- Confidence: medium-high (about 80%).

## Summary
The change has no benefit and introduces thread-safety regressions. Revert to `ConcurrentDictionary` and `TryAdd`. If a `Dictionary` is wanted, guard every access with a lock. The diff also contains no tests for the changed behavior.
