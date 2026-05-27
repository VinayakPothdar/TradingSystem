namespace DhanTradingJournal.Models;

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

    public decimal? StopLossPrice { get; set; }
    public decimal? RiskAmount { get; set; }
    public decimal? RMultiple { get; set; }
    public string? TradeGrade { get; set; }

    public decimal? MaxPriceAfterExit { get; set; }
    public decimal? ObservedTrailR { get; set; }
    public string? Notes { get; set; }
}
