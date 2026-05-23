using System.Text.Json;
using DhanApiSmokeTest.Models;
using DhanApiSmokeTest.Services;

Console.WriteLine("🚀 Dhan API Test Starting...");

var client = new HttpClient();

var token = "";
var clientId = "";

// Historical trades endpoint
var allExecutions = new List<TradeExecution>();

client.DefaultRequestHeaders.Clear();
client.DefaultRequestHeaders.Add("access-token", token);
client.DefaultRequestHeaders.Add("client-id", clientId);

try
{
    Console.WriteLine("📡 Calling Dhan API...\n");
    var fromDate = "2026-04-01";
    var toDate = DateTime.Today.ToString("yyyy-MM-dd");


    for (int page = 0; page < 10; page++)
    {
        var url = $"https://api.dhan.co/v2/trades/{fromDate}/{toDate}/{page}";

        Console.WriteLine($"Fetching Page: {page}");

        var response = await client.GetAsync(url);

        Console.WriteLine($"Status Code: {response.StatusCode}");

        if (!response.IsSuccessStatusCode)
        {
            Console.WriteLine("❌ API call failed");
            break;
        }

        var body = await response.Content.ReadAsStringAsync();

        if (string.IsNullOrWhiteSpace(body))
        {
            Console.WriteLine("⚠ Empty response body");
            break;
        }

        var executions = DeserializeTrades(body);

        if (executions == null || executions.Count == 0)
        {
            Console.WriteLine("✅ No more records found. Stopping pagination.");
            break;
        }

        Console.WriteLine($"Records Found: {executions.Count}");

        allExecutions.AddRange(executions);
    }

    Console.WriteLine($"\n✅ Total Executions Count: {allExecutions.Count}");

    // ===============================
    // Match Trades
    // ===============================

    var matcher = new FifoTradeMatcher();

    var matchedTrades = matcher.MatchTrades(allExecutions);

    // ===============================
    // Export
    // ===============================

    var excelExporter = new ExcelExportService();

    excelExporter.SyncTrades(allExecutions);
    excelExporter.ExportMatchedTrades(matchedTrades);

    Console.WriteLine("\n===== MATCHED TRADES =====\n");

    foreach (var t in matchedTrades)
    {
        Console.WriteLine("------ MATCHED TRADE ------");

        Console.WriteLine($"Symbol       : {t.Symbol}");
        Console.WriteLine($"Entry Price  : {t.EntryPrice}");
        Console.WriteLine($"Exit Price   : {t.ExitPrice}");
        Console.WriteLine($"Quantity     : {t.Quantity}");
        Console.WriteLine($"Gross PnL    : {t.GrossPnL}");
        Console.WriteLine($"Charges      : {t.Charges}");
        Console.WriteLine($"Net PnL      : {t.NetPnL}");
        Console.WriteLine();
    }
}
catch (Exception ex)
{
    Console.WriteLine("\n❌ ERROR OCCURRED");
    Console.WriteLine(ex.Message);
}

Console.WriteLine("\n✅ Done");


// ======================================================
// Deserialize Method
// ======================================================

static List<TradeExecution> DeserializeTrades(string jsonString)
{
    var executions = new List<TradeExecution>();

    if (string.IsNullOrWhiteSpace(jsonString))
        return executions;

    var json = JsonSerializer.Deserialize<JsonElement>(jsonString);

    if (json.ValueKind != JsonValueKind.Array)
        return executions;

    foreach (var item in json.EnumerateArray())
    {
        executions.Add(new TradeExecution
        {
            OrderId = GetString(item, "orderId"),

            Symbol = GetString(item, "customSymbol"),

            TransactionType = GetString(item, "transactionType"),

            Price = GetDecimal(item, "tradedPrice"),

            Quantity = GetInt(item, "tradedQuantity"),

            Stt = GetDecimal(item, "stt"),

            Brokerage = GetDecimal(item, "brokerageCharges"),

            ExchangeCharges = GetDecimal(item, "exchangeTransactionCharges"),

            StampDuty = GetDecimal(item, "stampDuty"),

            ServiceTax = GetDecimal(item, "serviceTax"),
            Time = GetDateTime(item, "exchangeTime"),
        });
    }
    executions = [.. executions.OrderByDescending(x=>x.Time)];
    return executions;
}


// ======================================================
// Safe JSON Helpers
// ======================================================

static string GetString(JsonElement item, string propertyName)
{
    if (item.TryGetProperty(propertyName, out var value))
    {
        return value.GetString() ?? string.Empty;
    }

    return string.Empty;
}

static decimal GetDecimal(JsonElement item, string propertyName)
{
    if (item.TryGetProperty(propertyName, out var value))
    {
        if (value.ValueKind == JsonValueKind.Number)
        {
            return value.GetDecimal();
        }
    }

    return 0;
}

static int GetInt(JsonElement item, string propertyName)
{
    if (item.TryGetProperty(propertyName, out var value))
    {
        if (value.ValueKind == JsonValueKind.Number)
        {
            return value.GetInt32();
        }
    }

    return 0;
}

static DateTime GetDateTime(JsonElement item, string propertyName)
{
    if (item.TryGetProperty(propertyName, out var value))
    {
        var str = value.GetString();

        if (!string.IsNullOrWhiteSpace(str))
        {
            if (DateTime.TryParse(str, out var result))
            {
                return result;
            }
        }
    }

    return DateTime.MinValue;
}