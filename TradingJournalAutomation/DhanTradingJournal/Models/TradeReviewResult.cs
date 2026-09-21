namespace DhanTradingJournal.Models;

public class TradeReviewResult
{
    public string TradeId { get; set; } = string.Empty;
    public string Symbol { get; set; } = string.Empty;
    public string YahooTicker { get; set; } = string.Empty;
    public string TradeType { get; set; } = string.Empty;
    public DateTime BuyTime { get; set; }
    public DateTime SellTime { get; set; }
    public double HoldingDays { get; set; }

    public decimal EntryPrice { get; set; }
    public decimal ExitPrice { get; set; }
    public int Quantity { get; set; }
    public decimal NetPnL { get; set; }
    public decimal ReturnPct { get; set; }

    public decimal? StopLossPrice { get; set; }
    public decimal InitialRiskPerShare { get; set; }
    public decimal? RealizedR { get; set; }

    // In-Trade Excursions (MFE & MAE)
    public decimal PeakPriceDuringTrade { get; set; }
    public decimal MaxFavorableExcursionPct { get; set; }
    public decimal? MaxFavorableExcursionR { get; set; }

    public decimal TroughPriceDuringTrade { get; set; }
    public decimal MaxAdverseExcursionPct { get; set; }
    public decimal? MaxAdverseExcursionR { get; set; }

    public decimal? CaptureEfficiencyPct { get; set; }
    public bool IsRoundTripFailure { get; set; }

    // Technical Posture at Entry
    public decimal? PriceVs200EmaPct { get; set; }
    public bool Above200Ema { get; set; }
    public bool IsOverextended { get; set; }
    public decimal? BreakoutVolumeRatio { get; set; }
    public bool VolumeSurge { get; set; }

    // Market Regime at Entry
    public decimal? Nifty50Close { get; set; }
    public string MarketRegime { get; set; } = string.Empty;
    public bool HasMarketTailwind { get; set; }

    // Post-Exit Analysis (20 Trading Days)
    public decimal? MaxPostExitPrice { get; set; }
    public decimal? PostExitMaxReturnPct { get; set; }
    public decimal? PostExitMaxR { get; set; }
    public bool LeftMoneyOnTable { get; set; }
    public bool ExitSavedFromDrawdown { get; set; }

    // Diagnosis / Autopsy
    public string DiagnosisCategory { get; set; } = string.Empty;
    public string AutopsyNotes { get; set; } = string.Empty;
}

public class FailureModeCount
{
    public string Mode { get; set; } = string.Empty;
    public int Count { get; set; }
    public decimal TotalLostPnL { get; set; }
    public string Description { get; set; } = string.Empty;
}

public class WinnersLosersComparison
{
    public int TotalTrades { get; set; }
    public int WinnersCount { get; set; }
    public int LosersCount { get; set; }
    public decimal WinRatePct { get; set; }

    public decimal TotalPnL { get; set; }
    public decimal WinnersPnL { get; set; }
    public decimal LosersPnL { get; set; }
    public decimal ProfitFactor { get; set; }

    public decimal AvgReturnPctWinners { get; set; }
    public decimal AvgReturnPctLosers { get; set; }

    public decimal AvgRealizedRWinners { get; set; }
    public decimal AvgRealizedRLosers { get; set; }

    // MFE & MAE
    public decimal AvgPeakRWinners { get; set; }
    public decimal AvgPeakRLosers { get; set; }
    public decimal AvgPeakPctWinners { get; set; }
    public decimal AvgPeakPctLosers { get; set; }

    public decimal AvgHeatRWinners { get; set; }
    public decimal AvgHeatRLosers { get; set; }
    public decimal AvgHeatPctWinners { get; set; }
    public decimal AvgHeatPctLosers { get; set; }

    public int RoundTripFailuresCount { get; set; }
    public decimal RoundTripLostPnL { get; set; }

    // Capture Efficiency
    public decimal AvgCaptureEfficiencyPct { get; set; }

    // Technicals & Volume
    public decimal AvgVolumeRatioWinners { get; set; }
    public decimal AvgVolumeRatioLosers { get; set; }
    public decimal PctVolumeSurgeWinners { get; set; }
    public decimal PctVolumeSurgeLosers { get; set; }

    public decimal PctAbove200EmaWinners { get; set; }
    public decimal PctAbove200EmaLosers { get; set; }
    public decimal AvgDistanceTo200EmaWinners { get; set; }
    public decimal AvgDistanceTo200EmaLosers { get; set; }

    // Market Tailwind
    public decimal PctMarketTailwindWinners { get; set; }
    public decimal PctMarketTailwindLosers { get; set; }

    // Holding Period
    public double AvgHoldingDaysWinners { get; set; }
    public double AvgHoldingDaysLosers { get; set; }

    // Post-Exit
    public decimal AvgPostExitMaxRWinners { get; set; }
    public decimal AvgPostExitMaxRLosers { get; set; }
    public int LeftMoneyOnTableCount { get; set; }
    public int ExitSavedFromDrawdownCount { get; set; }

    public List<FailureModeCount> FailureModes { get; set; } = new();
}
