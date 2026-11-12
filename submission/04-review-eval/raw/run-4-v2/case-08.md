## Findings

### 1. Data race on shared state: ConcurrentDictionary replaced with plain Dictionary
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Lines: 9 (field declaration), 18-22 (Add), 25 (Update), plus GetById and the list method (not shown in the diff)
- Changed line: `private readonly Dictionary<string, Invoice> _invoices = new();`
- What goes wrong: An ASP.NET Core repository registered as a singleton is called from concurrent requests. A plain `Dictionary` is not safe for concurrent writes, or for reads concurrent with writes. Concurrent `Add` or `Update` calls can corrupt the internal buckets, which can cause lost invoices, an infinite loop in `FindValue`, `InvalidOperationException` during enumeration, or wrong results. No lock was added anywhere in the diff.
- Confidence: high (about 90%). This assumes the repository is registered as a singleton, which is the normal arrangement for an in-memory store. If it is scoped, there is no per-request sharing and no bug.

### 2. Check-then-act race in Add breaks the duplicate-id guard
- File: backend/src/InvoiceApp.Api/InMemoryInvoiceRepository.cs
- Lines: 18-22
- Changed lines: `if (_invoices.ContainsKey(invoice.Id))` followed by `_invoices[invoice.Id] = invoice;`
- What goes wrong: The old `TryAdd` was an atomic add-if-absent. The new code does a separate existence check and then an indexer write. Two concurrent `Add` calls with the same id can both pass the `ContainsKey` check. The second write then silently overwrites the first, and no `InvalidOperationException` is thrown. The caller gets no 409 and the first invoice is lost. This is both a data race and a swallowed-error case, because the duplicate is no longer detected.
- Confidence: high (about 85%). It follows directly from the code, but it only occurs under concurrent requests.

## Nothing found in the other checked categories
There are no authorisation, injection, null-input, money, time-zone or logging changes in this diff.
