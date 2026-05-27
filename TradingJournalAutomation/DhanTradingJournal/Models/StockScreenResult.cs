namespace DhanTradingJournal.Models;

public static class StockScreenResultGrades
{
    public const string Fail = "FAIL";
    public const string A = "A";
    public const string B = "B";
    public const string Wait = "WAIT";
}

public class StockScreenResult
{
    public string Symbol { get; set; } = string.Empty;
    public string SecurityId { get; set; } = string.Empty;

    public decimal CurrentPrice { get; set; }
    public decimal Ema200 { get; set; }
    public decimal PriceVsEma200Pct { get; set; }

    public bool AthWithin63Days { get; set; }
    public bool AboveEma200 { get; set; }
    public bool Ema200Rising { get; set; }
    public bool WithinEmaZone { get; set; }

    public bool BaseTightRange { get; set; }
    public bool BaseVolumeDryUp { get; set; }
    public bool BaseHigherLows { get; set; }
    public bool BaseSupportConfluence { get; set; }
    public bool BaseCalmCandles { get; set; }
    public bool BaseMultipleTouches { get; set; }

    public int BaseScore => Convert.ToInt32(BaseTightRange)
                          + Convert.ToInt32(BaseVolumeDryUp)
                          + Convert.ToInt32(BaseHigherLows)
                          + Convert.ToInt32(BaseSupportConfluence)
                          + Convert.ToInt32(BaseCalmCandles)
                          + Convert.ToInt32(BaseMultipleTouches);

    public bool PassesMandatoryRules =>
        AthWithin63Days && AboveEma200 && Ema200Rising && WithinEmaZone;

    public string Grade => (PassesMandatoryRules, BaseScore) switch
    {
        (false, _) => StockScreenResultGrades.Fail,
        (true, >= 6) => StockScreenResultGrades.A,
        (true, >= 4) => StockScreenResultGrades.B,
        _ => StockScreenResultGrades.Wait
    };

    public DateTime ScannedAt { get; set; } = DateTime.Now;
}
