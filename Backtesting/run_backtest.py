import os
import sys
import io
import yaml
import pandas as pd
import numpy as np

# Force UTF-8 on Windows consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

# Ensure Backtesting folder is in sys.path
backtest_dir = os.path.dirname(os.path.abspath(__file__))
if backtest_dir not in sys.path:
    sys.path.append(backtest_dir)

from backtest_engine import SwingBacktestEngine

def print_performance_report(df_trades, cfg):
    print("\n" + "="*80)
    print(f"       BACKTEST RESULTS: {cfg.get('strategy_name', 'SWING PULLBACK')}")
    print(f"       Support EMA: {cfg.get('support_ema')} | ATH Lookback: {cfg.get('ath_lookback_days')} days | Max Bounces: {cfg.get('max_allowed_bounces')}")
    print("="*80)
    
    if len(df_trades) == 0:
        print("No trades found matching the exact criteria.")
        return
        
    total_trades = len(df_trades)
    wins = df_trades[df_trades['NetPnL'] > 0]
    losses = df_trades[df_trades['NetPnL'] < 0]
    be_trades = df_trades[df_trades['ExitReason'] == 'Breakeven']
    t1_hits = df_trades[df_trades['Target1Hit'] == True]
    
    win_rate = (len(wins) / total_trades) * 100
    t1_hit_rate = (len(t1_hits) / total_trades) * 100
    total_pnl = df_trades['NetPnL'].sum()
    total_r = df_trades['RealizedR'].sum()
    avg_r = df_trades['RealizedR'].mean()
    
    gross_profit = wins['GrossPnL'].sum()
    gross_loss = abs(losses['GrossPnL'].sum()) if len(losses) > 0 else 1.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.nan
    
    avg_win_r = wins['RealizedR'].mean() if len(wins) > 0 else 0
    avg_loss_r = losses['RealizedR'].mean() if len(losses) > 0 else 0
    
    print(f"Total Completed Trades      : {total_trades}")
    print(f"Target 1 (+2.0R) Hit Rate   : {t1_hit_rate:.1f}% ({len(t1_hits)} trades)")
    print(f"Overall Win Rate (>0 PnL)   : {win_rate:.1f}% ({len(wins)} wins / {len(losses)} losses / {len(be_trades)} BE)")
    print(f"Total Net P&L (Rs. 1k Risk) : Rs. {total_pnl:,.2f}")
    print(f"Total Realized R-Multiple   : +{total_r:.2f} R")
    print(f"Expectancy per Trade        : +{avg_r:.2f} R")
    print(f"Profit Factor               : {profit_factor:.2f}")
    print(f"Average Winner / Loser      : +{avg_win_r:.2f} R / {avg_loss_r:.2f} R")
    print(f"Average Holding Period      : {df_trades['HoldingDays'].mean():.1f} calendar days")
    
    print("\n--- EXIT REASON BREAKDOWN ---")
    exit_counts = df_trades['ExitReason'].value_counts()
    for reason, count in exit_counts.items():
        sub = df_trades[df_trades['ExitReason'] == reason]
        print(f"  {reason:<15}: {count:3d} trades ({count/total_trades*100:5.1f}%) | Net PnL: Rs. {sub['NetPnL'].sum():>9.2f} | Net R: {sub['RealizedR'].sum():>6.2f}R")
        
    print("\n--- RUNNER EXCURSION DISTRIBUTION (PEAK R REACHED) ---")
    r_tiers = [1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0]
    for r_val in r_tiers:
        hit = df_trades[df_trades['PeakR'] >= r_val]
        print(f"  Peaked >= +{r_val:.1f} R : {len(hit):3d} trades ({len(hit)/total_trades*100:5.1f}%)")
        
    print("\n--- SAMPLE RECENT TRADES ---")
    cols = ['Symbol', 'EntryDate', 'ExitDate', 'EntryPrice', 'FinalExitPrice', 'RealizedR', 'PeakR', 'ExitReason']
    print(df_trades[cols].tail(10).to_string(index=False))
    print("="*80 + "\n")

if __name__ == '__main__':
    config_path = os.path.join(backtest_dir, 'strategy_config.yaml')
    engine = SwingBacktestEngine(config_path)
    
    # Run across universe
    df_results = engine.run_full_backtest()
    
    # Output reports
    out_csv = os.path.join(backtest_dir, 'backtest_trades_log.csv')
    df_results.to_csv(out_csv, index=False)
    print(f"Saved full trade log to: {out_csv}")
    
    with open(config_path, 'r') as f:
        cfg = yaml.safe_load(f)
    print_performance_report(df_results, cfg)
