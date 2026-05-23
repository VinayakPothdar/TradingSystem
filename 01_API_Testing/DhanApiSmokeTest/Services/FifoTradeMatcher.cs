using DhanApiSmokeTest.Models;

namespace DhanApiSmokeTest.Services;

public class FifoTradeMatcher
{
    public List<MatchedTrade> MatchTrades(List<TradeExecution> executions)
    {
        var result = new List<MatchedTrade>();

        var symbolGroups = executions.GroupBy(x => x.Symbol);

        foreach (var group in symbolGroups)
        {
            var buyQueue = new Queue<TradeExecution>();

            var ordered = group
                .OrderBy(x => x.Time)
                .ToList();

            foreach (var e in ordered)
            {
                if (e.TransactionType == "BUY")
                {
                    buyQueue.Enqueue(Clone(e));
                }
                else if (e.TransactionType == "SELL")
                {
                    int remaining = e.Quantity;

                    while (remaining > 0 && buyQueue.Count > 0)
                    {
                        var buy = buyQueue.Peek();

                        var qty = Math.Min(remaining, buy.Quantity);

                        result.Add(new MatchedTrade
                        {
                            TradeId = $"{group.Key}_{buy.Time:O}_{e.Time:O}_{qty}",

                            Symbol = group.Key,
                            EntryPrice = buy.Price,
                            ExitPrice = e.Price,
                            Quantity = qty,

                            GrossPnL = (e.Price - buy.Price) * qty,

                            Charges =
                                buy.Stt + buy.Brokerage + buy.ExchangeCharges + buy.StampDuty + buy.ServiceTax +
                                e.Stt + e.Brokerage + e.ExchangeCharges + e.StampDuty + e.ServiceTax,

                            NetPnL = ((e.Price - buy.Price) * qty) - (
                                buy.Stt + buy.Brokerage + buy.ExchangeCharges + buy.StampDuty + buy.ServiceTax +
                                e.Stt + e.Brokerage + e.ExchangeCharges + e.StampDuty + e.ServiceTax
                            ),

                            BuyTime = buy.Time,
                            SellTime = e.Time,
                            HoldingDays = Math.Max(0, (e.Time - buy.Time).TotalDays)
                        });

                        remaining -= qty;
                        buy.Quantity -= qty;

                        if (buy.Quantity == 0)
                            buyQueue.Dequeue();
                    }
                }
            }
        }

        return result.OrderBy(x => x.BuyTime).ToList();
    }

    private static TradeExecution Clone(TradeExecution t)
    {
        return new TradeExecution
        {
            OrderId = t.OrderId,
            Symbol = t.Symbol,
            TransactionType = t.TransactionType,
            Price = t.Price,
            Quantity = t.Quantity,
            Time = t.Time,
            Stt = t.Stt,
            Brokerage = t.Brokerage,
            ExchangeCharges = t.ExchangeCharges,
            StampDuty = t.StampDuty,
            ServiceTax = t.ServiceTax
        };
    }

    private static TradeExecution CloneExecution(TradeExecution t)
    {
        return new TradeExecution
        {
            OrderId = t.OrderId,
            Symbol = t.Symbol,
            TransactionType = t.TransactionType,
            Price = t.Price,
            Quantity = t.Quantity,
            Time = t.Time,
            Stt = t.Stt,
            Brokerage = t.Brokerage,
            ExchangeCharges = t.ExchangeCharges,
            StampDuty = t.StampDuty,
            ServiceTax = t.ServiceTax
        };
    }

    private static string BuildMatchedTradeId(string symbol, DateTime buyTime, DateTime sellTime, int qty)
    {
        return $"{symbol}|{buyTime:O}|{sellTime:O}|{qty}";
    }
}