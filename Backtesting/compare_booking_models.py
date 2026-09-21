import os, sys, yaml, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.append(r'd:\TradingSystem\Backtesting')

from backtest_engine import SwingBacktestEngine
import pandas as pd
import numpy as np

cfg_path = r'd:\TradingSystem\Backtesting\strategy_config.yaml'
with open(cfg_path) as f: base_cfg = yaml.safe_load(f)

def run_variation(sup_ema, ath_days, target_pct, name):
    cfg = base_cfg.copy()
    cfg['support_ema'] = sup_ema
    cfg['ath_lookback_days'] = ath_days
    cfg['target_1_r'] = 2.0
    cfg['target_1_size_pct'] = target_pct
    cfg['breakeven_trigger_r'] = 1.5
    
    temp_file = f"d:\\TradingSystem\\Backtesting\\temp_{name}.yaml"
    with open(temp_file, 'w') as f: yaml.dump(cfg, f)
    
    eng = SwingBacktestEngine(temp_file)
    df = eng.run_full_backtest()
    if os.path.exists(temp_file): os.remove(temp_file)
    return df

print("Starting Comparative Run for Booking Strategies across 504 stocks...")

# 1. 200 EMA - 100% Booked at 2R
print("\n[1/4] Running 200 EMA with 100% Exit at 2R...")
df_200_100pct = run_variation(200, 180, 1.0, "200_100pct")

# 2. 200 EMA - 50% Booked at 2R + 50% Trail
print("\n[2/4] Running 200 EMA with 50% Book at 2R + 50% Trail...")
df_200_50pct = run_variation(200, 180, 0.50, "200_50pct")

# 3. 50 EMA - 100% Booked at 2R
print("\n[3/4] Running 50 EMA with 100% Exit at 2R...")
df_50_100pct = run_variation(50, 90, 1.0, "50_100pct")

# 4. 50 EMA - 50% Booked at 2R + 50% Trail
print("\n[4/4] Running 50 EMA with 50% Book at 2R + 50% Trail...")
df_50_50pct = run_variation(50, 90, 0.50, "50_50pct")

def summarize_df(df, label):
    total = len(df)
    wins = df[df.NetPnL > 0]
    losses = df[df.NetPnL < 0]
    be = df[df.ExitReason == 'Breakeven']
    
    win_rate = len(wins) / total * 100 if total > 0 else 0
    total_pnl = df['NetPnL'].sum()
    total_r = df['RealizedR'].sum()
    expectancy = df['RealizedR'].mean()
    
    gross_win = wins['GrossPnL'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['GrossPnL'].sum()) if len(losses) > 0 else 1
    pf = gross_win / gross_loss if gross_loss > 0 else 0
    
    avg_win_r = wins['RealizedR'].mean() if len(wins) > 0 else 0
    avg_loss_r = losses['RealizedR'].mean() if len(losses) > 0 else 0
    max_win_r = df['RealizedR'].max() if total > 0 else 0
    avg_days = df['HoldingDays'].mean() if total > 0 else 0
    
    return {
        'Strategy Model': label,
        'Trades': total,
        'Win Rate (%)': f"{win_rate:.1f}%",
        'Net PnL (₹)': f"₹{total_pnl:,.2f}",
        'Total R': f"+{total_r:.2f}R",
        'Expectancy': f"+{expectancy:.2f}R",
        'Profit Factor': f"{pf:.2f}",
        'Avg Win': f"+{avg_win_r:.2f}R",
        'Avg Loss': f"{avg_loss_r:.2f}R",
        'Max Win': f"+{max_win_r:.2f}R",
        'Avg Days': f"{avg_days:.1f}d"
    }

results = [
    summarize_df(df_200_100pct, "200 EMA (Clean 100% @ 2R)"),
    summarize_df(df_200_50pct,   "200 EMA (50% @ 2R + 50% Trail)"),
    summarize_df(df_50_100pct,  "50 EMA (Clean 100% @ 2R)"),
    summarize_df(df_50_50pct,   "50 EMA (50% @ 2R + 50% Trail)")
]

df_report = pd.DataFrame(results)
print("\n" + "="*95)
print("HEAD-TO-HEAD COMPARISON: 100% BOOKING AT 2R vs. 50% AT 2R + 50% TRAIL")
print("="*95)
print(df_report.to_string(index=False))
print("="*95 + "\n")
