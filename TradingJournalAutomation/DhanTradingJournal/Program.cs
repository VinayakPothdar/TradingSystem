using DhanTradingJournal.Security;
using DhanTradingJournal.Services;

Console.WriteLine("Dhan Trading Journal");
Console.WriteLine("====================\n");

var credentials = DhanCredentialProvider.GetCredentials();

if (string.IsNullOrWhiteSpace(credentials.ClientId) ||
    string.IsNullOrWhiteSpace(credentials.AccessToken))
{
    return;
}

using var httpClient = new HttpClient();
IDhanClient dhanClient = new DhanClient(httpClient, credentials.AccessToken, credentials.ClientId);

var excelExportService = new ExcelExportService();
var journalSyncService = new JournalSyncService(
    dhanClient,
    new FifoTradeMatcher(),
    excelExportService);
var screenerWorkflow = new ScreenerWorkflow(
    new StockScreener(dhanClient),
    excelExportService);

Console.WriteLine("What would you like to do?");
Console.WriteLine("  1 - Sync journal");
Console.WriteLine("  2 - Run stock screener");
Console.WriteLine("  3 - Both");
Console.Write("\nEnter choice (1/2/3): ");

var choice = Console.ReadLine()?.Trim() ?? "1";
Console.WriteLine();

try
{
    if (choice is "1" or "3")
    {
        var fromDate = new DateOnly(2026, 4, 1);
        var toDate = DateOnly.FromDateTime(DateTime.Today);
        await journalSyncService.Run(fromDate, toDate);
    }

    if (choice is "2" or "3")
        await screenerWorkflow.Run();
}
catch (Exception ex)
{
    Console.WriteLine($"\nRun failed: {ex.Message}");
}

Console.WriteLine("\n====================");
Console.WriteLine("Done - check D:\\TradingJournal\\MasterJournal.xlsx");
