namespace DhanTradingJournal.Models;

public class HistoricalCandle
{
    public DateTime Date { get; set; }
    public decimal Open { get; set; }
    public decimal High { get; set; }
    public decimal Low { get; set; }
    public decimal Close { get; set; }
    public long Volume { get; set; }
}

public class ScreenerInstrument
{
    public string SecurityId { get; set; } = string.Empty;
    public string Symbol { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string ExchangeSegment { get; set; } = "NSE_EQ";
}
