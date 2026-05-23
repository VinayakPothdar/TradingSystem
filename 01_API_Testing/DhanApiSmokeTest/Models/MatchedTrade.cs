namespace DhanApiSmokeTest.Models;

public class MatchedTrade
{
    public string TradeId { get; set; } = string.Empty;

    public string Symbol { get; set; } = string.Empty;

    public decimal EntryPrice { get; set; }

    public decimal ExitPrice { get; set; }

    public int Quantity { get; set; }

    public decimal GrossPnL { get; set; }

    public decimal Charges { get; set; }

    public decimal NetPnL { get; set; }

    public DateTime BuyTime { get; set; }

    public DateTime SellTime { get; set; }

    public double HoldingDays { get; set; }
}