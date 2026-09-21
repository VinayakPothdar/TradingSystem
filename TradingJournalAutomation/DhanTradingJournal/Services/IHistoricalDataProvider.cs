using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public interface IHistoricalDataProvider
{
    Task<List<HistoricalCandle>> GetDailyCandles(
        ScreenerInstrument instrument,
        DateTime from,
        DateTime to);
}
