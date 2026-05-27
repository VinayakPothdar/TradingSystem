namespace DhanTradingJournal.Models;

public class TradeExecution
{
    public string OrderId { get; set; } = string.Empty;
    public string Symbol { get; set; } = string.Empty;
    public string TransactionType { get; set; } = string.Empty; // BUY / SELL

    public decimal Price { get; set; }
    public int Quantity { get; set; }

    public decimal Stt { get; set; }
    public decimal Brokerage { get; set; }
    public decimal ExchangeCharges { get; set; }
    public decimal StampDuty { get; set; }
    public decimal ServiceTax { get; set; }

    public DateTime Time { get; set; }
}
