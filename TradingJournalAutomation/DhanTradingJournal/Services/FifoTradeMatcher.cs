using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public class FifoTradeMatcher
{
    public List<MatchedTrade> MatchTrades(List<TradeExecution> executions)
    {
        var matchedTrades = new List<MatchedTrade>();

        foreach (var group in executions.GroupBy(x => x.Symbol))
        {
            var buyQueue = new Queue<TradeExecution>();

            foreach (var execution in group.OrderBy(x => x.Time))
            {
                if (execution.TransactionType == "BUY")
                {
                    buyQueue.Enqueue(Clone(execution));
                    continue;
                }

                if (execution.TransactionType != "SELL")
                    continue;

                MatchSellExecution(group.Key, execution, buyQueue, matchedTrades);
            }
        }

        return ConsolidateSplitExits(matchedTrades);
    }

    private static void MatchSellExecution(
        string symbol,
        TradeExecution sell,
        Queue<TradeExecution> buyQueue,
        List<MatchedTrade> matchedTrades)
    {
        var remaining = sell.Quantity;

        while (remaining > 0 && buyQueue.Count > 0)
        {
            var buy = buyQueue.Peek();
            var qty = Math.Min(remaining, buy.Quantity);
            var charges = CalculateCharges(buy) + CalculateCharges(sell);
            var grossPnL = (sell.Price - buy.Price) * qty;

            matchedTrades.Add(new MatchedTrade
            {
                TradeId = $"{symbol}_{buy.Time:O}_{sell.Time:O}_{qty}",
                Symbol = symbol,
                EntryPrice = buy.Price,
                ExitPrice = sell.Price,
                Quantity = qty,
                GrossPnL = grossPnL,
                Charges = charges,
                NetPnL = grossPnL - charges,
                BuyTime = buy.Time,
                SellTime = sell.Time,
                HoldingDays = Math.Max(0, (sell.Time - buy.Time).TotalDays)
            });

            remaining -= qty;
            buy.Quantity -= qty;

            if (buy.Quantity == 0)
                buyQueue.Dequeue();
        }
    }

    private static List<MatchedTrade> ConsolidateSplitExits(List<MatchedTrade> matchedTrades) =>
        [.. matchedTrades
            .GroupBy(t => new
            {
                t.Symbol,
                t.EntryPrice,
                BuyDate = t.BuyTime.Date
            })
            .Select(g =>
            {
                var totalQty = g.Sum(t => t.Quantity);
                var weightedExitPrice = g.Sum(t => t.ExitPrice * t.Quantity) / totalQty;
                var firstBuy = g.OrderBy(t => t.BuyTime).First();
                var lastSell = g.OrderByDescending(t => t.SellTime).First();
                var totalGross = g.Sum(t => t.GrossPnL);
                var totalCharges = g.Sum(t => t.Charges);

                return new MatchedTrade
                {
                    TradeId = $"{g.Key.Symbol}_{g.Key.EntryPrice}_{g.Key.BuyDate:yyyy-MM-dd}",
                    Symbol = g.Key.Symbol,
                    EntryPrice = g.Key.EntryPrice,
                    ExitPrice = Math.Round(weightedExitPrice, 2),
                    Quantity = totalQty,
                    GrossPnL = totalGross,
                    Charges = totalCharges,
                    NetPnL = totalGross - totalCharges,
                    BuyTime = firstBuy.BuyTime,
                    SellTime = lastSell.SellTime,
                    HoldingDays = Math.Max(0, (lastSell.SellTime - firstBuy.BuyTime).TotalDays)
                };
            })
            .OrderBy(t => t.BuyTime)];

    private static decimal CalculateCharges(TradeExecution trade) =>
        trade.Stt + trade.Brokerage + trade.ExchangeCharges + trade.StampDuty + trade.ServiceTax;

    private static TradeExecution Clone(TradeExecution trade) => new()
    {
        OrderId = trade.OrderId,
        Symbol = trade.Symbol,
        TransactionType = trade.TransactionType,
        Price = trade.Price,
        Quantity = trade.Quantity,
        Time = trade.Time,
        Stt = trade.Stt,
        Brokerage = trade.Brokerage,
        ExchangeCharges = trade.ExchangeCharges,
        StampDuty = trade.StampDuty,
        ServiceTax = trade.ServiceTax
    };
}
