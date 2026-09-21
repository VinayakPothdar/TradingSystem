import os, sys, yaml, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.append(r'd:\TradingSystem\Backtesting')

from backtest_engine import SwingBacktestEngine
import pandas as pd
import numpy as np

cfg_path = r'd:\TradingSystem\Backtesting\strategy_config.yaml'

# 1. Run 200 EMA
with open(cfg_path) as f: cfg200 = yaml.safe_load(f)
cfg200['support_ema'] = 200
cfg200['ath_lookback_days'] = 180
cfg200['max_allowed_bounces'] = 1

tfile200 = r'd:\TradingSystem\Backtesting\temp200.yaml'
with open(tfile200, 'w') as f: yaml.dump(cfg200, f)
eng200 = SwingBacktestEngine(tfile200)
df200 = eng200.run_full_backtest()
if os.path.exists(tfile200): os.remove(tfile200)

# 2. Run 50 EMA
cfg50 = cfg200.copy()
cfg50['support_ema'] = 50
cfg50['ath_lookback_days'] = 90
cfg50['max_allowed_bounces'] = 1
tfile50 = r'd:\TradingSystem\Backtesting\temp50.yaml'
with open(tfile50, 'w') as f: yaml.dump(cfg50, f)
eng50 = SwingBacktestEngine(tfile50)
df50 = eng50.run_full_backtest()
if os.path.exists(tfile50): os.remove(tfile50)

print("\n" + "="*80)
print("PEAK ANALYSIS COMPARISON: 200 EMA vs. 50 EMA")
print("="*80)

def analyze_peaks(df, name):
    print(f"\n--- {name} (Total Trades: {len(df)}) ---")
    print(f"Average Peak R (All Trades) : +{df['PeakR'].mean():.2f} R")
    print(f"Median Peak R               : +{df['PeakR'].median():.2f} R")
    print(f"Max Peak R Recorded         : +{df['PeakR'].max():.2f} R")
    
    wins = df[df['NetPnL'] > 0]
    print(f"Average Peak R of WINNERS   : +{wins['PeakR'].mean():.2f} R")
    print(f"Average Realized R (Winners): +{wins['RealizedR'].mean():.2f} R")
    print(f"Capture Efficiency (Realized / Peak): {wins['RealizedR'].sum() / wins['PeakR'].sum() * 100:.1f}%")
    
    print("\nExcursion Distribution:")
    tiers = [1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]
    for t in tiers:
        hit = df[df['PeakR'] >= t]
        pct = len(hit) / len(df) * 100
        print(f"  Peaked >= +{t:4.1f} R : {len(hit):3d} trades ({pct:5.1f}%)")
        
    print("\nTop 5 Monster Runner Peaks:")
    top5 = df.sort_values('PeakR', ascending=False)[['Symbol', 'EntryDate', 'ExitDate', 'PeakR', 'RealizedR', 'ExitReason']].head(5)
    print(top5.to_string(index=False))

analyze_peaks(df200, "200 EMA SUPPORT")
analyze_peaks(df50, "50 EMA SUPPORT")
