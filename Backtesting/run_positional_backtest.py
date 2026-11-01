import os
import glob
import pandas as pd
import numpy as np
from positional_backtest_engine import PositionalBacktestEngine

def run():
    config_path = os.path.join(os.path.dirname(__file__), 'positional_strategy_config.yaml')
    engine = PositionalBacktestEngine(config_path)
    
    csv_dir = engine.data_dir
    files = glob.glob(os.path.join(csv_dir, '*.csv'))
    
    stock_files = [f for f in files if not os.path.basename(f).startswith('^')]
    print(f"==================================================")
    print(f"POSITIONAL 200 WEMA STRATEGY BACKTEST ENGINE")
    print(f"Universe: {len(stock_files)} stocks in Nifty 500")
    print(f"Config:   {config_path}")
    print(f"==================================================\n")
    
    all_trades = []
    processed = 0
    
    for f in stock_files:
        sym = os.path.basename(f).replace('.csv', '')
        try:
            trades = engine.scan_and_backtest_symbol(sym, f)
            if trades:
                all_trades.extend(trades)
        except Exception as e:
            pass
        processed += 1
        if processed % 50 == 0:
            print(f"  Processed {processed}/{len(stock_files)} stocks... Found {len(all_trades)} trades so far.")
            
    print(f"\nScan complete! Total trades generated: {len(all_trades)}")
    
    if not all_trades:
        print("No trades found matching setup criteria.")
        return
        
    df = pd.DataFrame(all_trades)
    output_csv = os.path.join(os.path.dirname(__file__), 'positional_backtest_trades.csv')
    df.to_csv(output_csv, index=False)
    print(f"Detailed trade log saved to: {output_csv}\n")
    
    # --------------------------------------------------------------------------
    # METRICS & PERFORMANCE REPORTING
    # --------------------------------------------------------------------------
    total = len(df)
    wins = df[df['NetPnL'] > 0]
    losses = df[df['NetPnL'] < 0]
    bes = df[df['NetPnL'] == 0]
    
    win_rate = (len(wins) / total) * 100 if total > 0 else 0
    loss_rate = (len(losses) / total) * 100 if total > 0 else 0
    
    gross_win = wins['NetPnL'].sum() if len(wins) > 0 else 0
    gross_loss = abs(losses['NetPnL'].sum()) if len(losses) > 0 else 0
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else np.nan
    
    total_r = df['RealizedR'].sum()
    avg_r = df['RealizedR'].mean()
    avg_win_r = wins['RealizedR'].mean() if len(wins) > 0 else 0
    avg_loss_r = losses['RealizedR'].mean() if len(losses) > 0 else 0
    
    avg_days_win = wins['HoldingDays'].mean() if len(wins) > 0 else 0
    avg_days_loss = losses['HoldingDays'].mean() if len(losses) > 0 else 0
    
    round_trips = df[df['IsRoundTrip'] == True]
    
    print("==================================================")
    print("OVERALL BACKTEST PERFORMANCE (200 WEMA SYSTEM)")
    print("==================================================")
    print(f"Total Trades:           {total}")
    print(f"Winning Trades:         {len(wins)} ({win_rate:.1f}%)")
    print(f"Losing Trades:          {len(losses)} ({loss_rate:.1f}%)")
    print(f"Breakeven Trades:       {len(bes)}")
    print(f"Total Realized R:       {total_r:+.2f}R")
    print(f"Average R per Trade:    {avg_r:+.2f}R")
    print(f"Profit Factor:          {profit_factor:.2f}")
    print(f"Total Net P&L:          Rs. {df['NetPnL'].sum():+,.2f}")
    print(f"Average Winner:         {avg_win_r:+.2f}R (Rs. {wins['NetPnL'].mean():+,.2f}) | {avg_days_win:.1f} days")
    print(f"Average Loser:          {avg_loss_r:+.2f}R (Rs. {losses['NetPnL'].mean():+,.2f}) | {avg_days_loss:.1f} days")
    print(f"Round-Trip Failures:    {len(round_trips)} (Peaked >= +1.5R but exited negative)")
    print(f"Average Peak R:         +{df['PeakR'].mean():.2f}R")
    print(f"Average Heat R:         {df['HeatR'].mean():.2f}R")
    print("==================================================\n")
    
    # --------------------------------------------------------------------------
    # MARKET REGIME HYPOTHESIS TESTING
    # --------------------------------------------------------------------------
    print("==================================================")
    print("MARKET REGIME PERFORMANCE BREAKDOWN")
    print("==================================================")
    for regime, r_group in df.groupby('MarketRegime'):
        r_total = len(r_group)
        r_wins = len(r_group[r_group['NetPnL'] > 0])
        r_wr = (r_wins / r_total) * 100 if r_total > 0 else 0
        r_pnl = r_group['NetPnL'].sum()
        r_avgr = r_group['RealizedR'].mean()
        print(f"Regime: {regime:<28} | Trades: {r_total:3d} | WR: {r_wr:5.1f}% | Avg R: {r_avgr:+.2f}R | Net PnL: Rs. {r_pnl:+,.2f}")
    print("==================================================\n")
    
    # --------------------------------------------------------------------------
    # USER HYPOTHESIS: PRE-AUGUST 2026 VS POST-AUGUST 2026
    # --------------------------------------------------------------------------
    print("==================================================")
    print("2026 MARKET REGIME AUDIT: PRE-AUG VS POST-AUG")
    print("Testing User Hypothesis on Downtrend Reversals")
    print("==================================================")
    df_2026 = df[df['EntryDate'] >= '2026-01-01'].copy()
    if len(df_2026) > 0:
        pre_aug = df_2026[df_2026['EntryDate'] < '2026-08-01']
        post_aug = df_2026[df_2026['EntryDate'] >= '2026-08-01']
        
        for name, sub in [("Pre-August 2026 (Jan - Jul)", pre_aug), ("Post-August 2026 (Aug - Sep)", post_aug)]:
            sub_tot = len(sub)
            if sub_tot == 0:
                print(f"{name:<30} | No trades generated in period.")
                continue
            sub_w = len(sub[sub['NetPnL'] > 0])
            sub_l = len(sub[sub['NetPnL'] < 0])
            sub_wr = (sub_w / sub_tot) * 100
            sub_pnl = sub['NetPnL'].sum()
            sub_r = sub['RealizedR'].sum()
            sub_peak = sub['PeakR'].mean()
            print(f"{name:<30} | Trades: {sub_tot:3d} | Wins: {sub_w:2d} | Losses: {sub_l:2d} | WR: {sub_wr:5.1f}% | Total R: {sub_r:+.2f}R | Net PnL: Rs. {sub_pnl:+,.2f} | Avg Peak R: +{sub_peak:.2f}R")
    else:
        print("No 2026 trades found.")
    print("==================================================\n")

    # --------------------------------------------------------------------------
    # COMPARISON OF TRADE MANAGEMENT (NO BE VS +1.5R BE)
    # --------------------------------------------------------------------------
    print("==================================================")
    print("TRADE MANAGEMENT AUDIT: IMPACT OF +1.5R BREAKEVEN RULE")
    print("==================================================")
    # Without BE rule: any trade that was saved by BE would have hit full SL (-1R)
    saved_by_be = df[df['ExitReason'] == 'Breakeven / Trail Stop Hit']
    print(f"Trades Saved from Full Losses by +1.5R BE Rule: {len(saved_by_be)}")
    capital_saved = len(saved_by_be) * 1000.0 - saved_by_be['NetPnL'].sum()
    print(f"Capital Saved by Eliminating Round Trips:       Rs. {capital_saved:+,.2f} (~{len(saved_by_be)}R)")
    print("==================================================\n")

if __name__ == '__main__':
    run()
