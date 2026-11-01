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

backtest_dir = os.path.dirname(os.path.abspath(__file__))
if backtest_dir not in sys.path:
    sys.path.append(backtest_dir)

from backtest_engine import SwingBacktestEngine

def run_50_dema_backtest(ath_lookback=90):
    config_path = os.path.join(backtest_dir, 'strategy_config.yaml')
    with open(config_path, 'r') as f:
        cfg = yaml.safe_load(f)
        
    cfg['support_ema'] = 50
    cfg['strategy_name'] = 'Swing_50_DEMA_Pullback'
    cfg['description'] = 'Swing Pullback to 50 Daily EMA in Stage 2 Uptrend (Stock > 200 EMA)'
    cfg['ath_lookback_days'] = ath_lookback
    cfg['require_primary_trend_above_200'] = True
    cfg['zone_tolerance_upper'] = 0.02
    cfg['zone_tolerance_lower'] = -0.03
    
    # Save a dedicated config file for reproducibility
    cfg_50_path = os.path.join(backtest_dir, 'strategy_config_50_dema.yaml')
    with open(cfg_50_path, 'w') as f:
        yaml.dump(cfg, f, default_flow_style=False)
        
    print(f"Configured 50 DEMA backtest (ATH lookback: {ath_lookback}d, Trend Filter: > 200 EMA)")
    engine = SwingBacktestEngine(cfg_50_path)
    
    df_trades = engine.run_full_backtest()
    print(f"\nTotal completed 50 DEMA trades: {len(df_trades)}")
    
    if len(df_trades) == 0:
        return df_trades, cfg
        
    # Map Market Cap Tier
    market_caps_csv = os.path.join(backtest_dir, '..', 'TradingJournalAutomation', 'DhanTradingJournal', 'Data', 'Watchlists', 'nifty500_market_caps.csv')
    if os.path.exists(market_caps_csv):
        mc_df = pd.read_csv(market_caps_csv)
        sym_to_cap = dict(zip(mc_df['Symbol'], mc_df['MarketCapTier']))
        df_trades['MarketCap'] = df_trades['Symbol'].map(sym_to_cap).fillna('Mid Cap')
    else:
        df_trades['MarketCap'] = 'Mid Cap'
        
    out_csv = os.path.join(backtest_dir, 'backtest_50_dema_trades_log.csv')
    df_trades.to_csv(out_csv, index=False)
    print(f"Saved 50 DEMA trade log to: {out_csv}")
    
    # Print Performance Breakdown
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
    
    print("\n" + "="*80)
    print(f"       BACKTEST RESULTS: SWING 50 DEMA PULLBACK (STAGE 2 > 200 EMA)")
    print("="*80)
    print(f"Total Completed Trades      : {total_trades}")
    print(f"Target 1 (+2.0R) Hit Rate   : {t1_hit_rate:.1f}% ({len(t1_hits)} trades)")
    print(f"Overall Win Rate (>0 PnL)   : {win_rate:.1f}% ({len(wins)} wins / {len(losses)} losses / {len(be_trades)} BE)")
    print(f"Total Net P&L (Rs. 1k Risk) : Rs. {total_pnl:,.2f}")
    print(f"Total Realized R-Multiple   : +{total_r:.2f} R")
    print(f"Expectancy per Trade        : +{avg_r:.2f} R")
    print(f"Profit Factor               : {profit_factor:.2f}")
    print(f"Average Holding Period      : {df_trades['HoldingDays'].mean():.1f} calendar days")
    
    print("\n--- MARKET CAP PERFORMANCE MATRIX ---")
    for cap in ['Large Cap', 'Mid Cap', 'Small Cap']:
        sub = df_trades[df_trades['MarketCap'] == cap]
        if len(sub) > 0:
            swins = sub[sub['NetPnL'] > 0]
            sloss = sub[sub['NetPnL'] < 0]
            sbes = sub[sub['ExitReason'] == 'Breakeven']
            sgross_p = swins['GrossPnL'].sum()
            sgross_l = abs(sloss['GrossPnL'].sum()) if len(sloss) > 0 else 1.0
            spf = sgross_p / sgross_l if sgross_l > 0 else 99.9
            s_r = sub['RealizedR'].sum()
            s_pnl = sub['NetPnL'].sum()
            print(f"  {cap:<10}: {len(sub):3d} trades | WR: {len(swins)/len(sub)*100:5.1f}% ({len(swins)}W/{len(sloss)}L/{len(sbes)}BE) | R: {s_r:+7.2f}R | PF: {spf:4.2f} | PnL: Rs. {s_pnl:+10,.2f}")
            
    return df_trades, cfg

if __name__ == '__main__':
    run_50_dema_backtest(ath_lookback=90)
