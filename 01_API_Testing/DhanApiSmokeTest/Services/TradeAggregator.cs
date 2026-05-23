using DhanApiSmokeTest.Models;

namespace DhanApiSmokeTest.Services;

public class TradeAggregator
{
    public class TradeSummary
    {
        public string Symbol { get; set; }
        public decimal BuyAvg { get; set; }
        public decimal SellAvg { get; set; }
        public int Quantity { get; set; }

        public decimal TotalCharges { get; set; }
        public decimal PnL { get; set; }
    }

    public List<TradeSummary> BuildTrades(List<TradeExecution> executions)
    {
        var grouped = executions
            .GroupBy(x => x.Symbol);

        var result = new List<TradeSummary>();

        foreach (var group in grouped)
        {
            var buys = group.Where(x => x.TransactionType == "BUY").ToList();
            var sells = group.Where(x => x.TransactionType == "SELL").ToList();

            var buyAvg = buys.Any()
                ? buys.Sum(x => x.Price * x.Quantity) / buys.Sum(x => x.Quantity)
                : 0;

            var sellAvg = sells.Any()
                ? sells.Sum(x => x.Price * x.Quantity) / sells.Sum(x => x.Quantity)
                : 0;

            var qty = buys.Sum(x => x.Quantity);

            var charges = group.Sum(x =>
                x.Stt + x.Brokerage + x.ExchangeCharges + x.StampDuty + x.ServiceTax);

            var pnl = (sellAvg - buyAvg) * qty - charges;

            result.Add(new TradeSummary
            {
                Symbol = group.Key,
                BuyAvg = buyAvg,
                SellAvg = sellAvg,
                Quantity = qty,
                TotalCharges = charges,
                PnL = pnl
            });
        }

        return result;
    }
}