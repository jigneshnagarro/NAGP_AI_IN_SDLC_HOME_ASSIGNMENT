using System.Reflection;
using InvoiceApp.Domain;
using Xunit;

namespace InvoiceApp.Tests;

/// <summary>
/// Structural rule from AGENTS.md: "Business rules go in the Domain project ... no web or storage code."
/// The Domain assembly may reference only the .NET base library, never ASP.NET Core, the Api project,
/// a database client or a messaging client. When SQL and Service Bus arrive, this keeps them out of Domain.
/// </summary>
public class ArchitectureTests
{
    private static readonly string[] ForbiddenPrefixes =
    {
        "InvoiceApp.Api",
        "Microsoft.AspNetCore",
        "Microsoft.EntityFrameworkCore",
        "Microsoft.Data.SqlClient",
        "System.Data.SqlClient",
        "Azure.Messaging.ServiceBus",
        "Dapper",
    };

    [Fact]
    public void Domain_DoesNotDependOnWebStorageOrMessaging()
    {
        var domainAssembly = typeof(ApprovalService).Assembly;

        var violations = domainAssembly
            .GetReferencedAssemblies()
            .Select(reference => reference.Name ?? string.Empty)
            .Where(name => ForbiddenPrefixes.Any(prefix => name.StartsWith(prefix, StringComparison.Ordinal)))
            .ToList();

        Assert.True(
            violations.Count == 0,
            $"InvoiceApp.Domain must not reference: {string.Join(", ", violations)}");
    }
}
