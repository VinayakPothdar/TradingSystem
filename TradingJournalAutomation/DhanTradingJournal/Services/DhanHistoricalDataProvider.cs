using DhanTradingJournal.Models;

namespace DhanTradingJournal.Services;

public class DhanHistoricalDataProvider : IHistoricalDataProvider
{
    private readonly IDhanClient _dhanClient;

    public DhanHistoricalDataProvider(IDhanClient dhanClient)
    {
        _dhanClient = dhanClient;
    }

    public Task<List<HistoricalCandle>> GetDailyCandles(
        ScreenerInstrument instrument,
        DateTime from,
        DateTime to) =>
        _dhanClient.GetDailyCandles(
            instrument.SecurityId,
            instrument.ExchangeSegment,
            from,
            to);
}
