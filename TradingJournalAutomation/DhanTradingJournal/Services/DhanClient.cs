using System.Net.Http.Json;
using System.Text.Json;
using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public class DhanClient : IDhanClient
{
    private const string TradesBaseUrl = "https://api.dhan.co/v2/trades";
    private const string HistoricalBaseUrl = "https://api.dhan.co/v2/charts/historical";

    private readonly HttpClient _client;
    private readonly string _token;
    private readonly string _clientId;

    public DhanClient(HttpClient client, string token, string clientId)
    {
        _client = client;
        _token = token;
        _clientId = clientId;
    }

    public async Task<List<TradeExecution>> GetTrades(DateOnly fromDate, DateOnly toDate, int maxPages = 10)
    {
        var executions = new List<TradeExecution>();

        for (var page = 0; page < maxPages; page++)
        {
            var url = $"{TradesBaseUrl}/{fromDate:yyyy-MM-dd}/{toDate:yyyy-MM-dd}/{page}";
            Console.WriteLine($"  Fetching page {page}...");

            using var request = CreateRequest(HttpMethod.Get, url);
            using var response = await _client.SendAsync(request);

            if (!response.IsSuccessStatusCode)
            {
                Console.WriteLine($"  API failed: {response.StatusCode}");
                break;
            }

            var body = await response.Content.ReadAsStringAsync();

            if (string.IsNullOrWhiteSpace(body))
            {
                Console.WriteLine("  No more records.");
                break;
            }

            var pageExecutions = ParseTrades(body);

            if (pageExecutions.Count == 0)
            {
                Console.WriteLine("  No more records.");
                break;
            }

            Console.WriteLine($"  Records: {pageExecutions.Count}");
            executions.AddRange(pageExecutions);
        }

        return [.. executions.OrderByDescending(x => x.Time)];
    }

    public async Task<List<HistoricalCandle>> GetDailyCandles(
        string securityId,
        string exchangeSegment,
        DateTime from,
        DateTime to)
    {
        var payload = new
        {
            securityId,
            exchangeSegment,
            instrument = "EQUITY",
            expiryCode = 0,
            oi = false,
            fromDate = from.ToString("yyyy-MM-dd"),
            toDate = to.ToString("yyyy-MM-dd")
        };

        using var request = CreateRequest(HttpMethod.Post, HistoricalBaseUrl, payload);
        using var response = await _client.SendAsync(request);

        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadAsStringAsync();
            Console.WriteLine($"Historical fetch failed for {securityId}: {response.StatusCode} | {error}");
            return [];
        }

        var body = await response.Content.ReadAsStringAsync();
        return ParseCandles(body);
    }

    private HttpRequestMessage CreateRequest(HttpMethod method, string url, object? payload = null)
    {
        var request = new HttpRequestMessage(method, url);
        request.Headers.Add("access-token", _token);
        request.Headers.Add("client-id", _clientId);

        if (payload != null)
            request.Content = JsonContent.Create(payload);

        return request;
    }

    private static List<TradeExecution> ParseTrades(string jsonString)
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

        return executions;
    }

    private static List<HistoricalCandle> ParseCandles(string jsonString)
    {
        var candles = new List<HistoricalCandle>();

        if (string.IsNullOrWhiteSpace(jsonString))
            return candles;

        var doc = JsonSerializer.Deserialize<JsonElement>(jsonString);

        if (!doc.TryGetProperty("open", out var opens)) return candles;
        if (!doc.TryGetProperty("high", out var highs)) return candles;
        if (!doc.TryGetProperty("low", out var lows)) return candles;
        if (!doc.TryGetProperty("close", out var closes)) return candles;
        if (!doc.TryGetProperty("volume", out var volumes)) return candles;
        if (!doc.TryGetProperty("timestamp", out var timestamps)) return candles;

        var openArr = opens.EnumerateArray().ToArray();
        var highArr = highs.EnumerateArray().ToArray();
        var lowArr = lows.EnumerateArray().ToArray();
        var closeArr = closes.EnumerateArray().ToArray();
        var volArr = volumes.EnumerateArray().ToArray();
        var tsArr = timestamps.EnumerateArray().ToArray();

        var count = Math.Min(openArr.Length, tsArr.Length);

        for (var i = 0; i < count; i++)
        {
            candles.Add(new HistoricalCandle
            {
                Date = DateTimeOffset.FromUnixTimeSeconds(tsArr[i].GetInt64()).LocalDateTime,
                Open = openArr[i].GetDecimal(),
                High = highArr[i].GetDecimal(),
                Low = lowArr[i].GetDecimal(),
                Close = closeArr[i].GetDecimal(),
                Volume = volArr[i].GetInt64()
            });
        }

        return candles.OrderBy(c => c.Date).ToList();
    }

    private static string GetString(JsonElement item, string prop) =>
        item.TryGetProperty(prop, out var v) ? v.GetString() ?? string.Empty : string.Empty;

    private static decimal GetDecimal(JsonElement item, string prop) =>
        item.TryGetProperty(prop, out var v) && v.ValueKind == JsonValueKind.Number ? v.GetDecimal() : 0;

    private static int GetInt(JsonElement item, string prop) =>
        item.TryGetProperty(prop, out var v) && v.ValueKind == JsonValueKind.Number ? v.GetInt32() : 0;

    private static DateTime GetDateTime(JsonElement item, string prop)
    {
        if (item.TryGetProperty(prop, out var v))
        {
            var str = v.GetString();
            if (!string.IsNullOrWhiteSpace(str) && DateTime.TryParse(str, out var result))
                return result;
        }

        return DateTime.MinValue;
    }
}

