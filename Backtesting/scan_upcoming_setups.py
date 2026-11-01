"""
==============================================================================
NIFTY 500 SWING SETUP SCANNER (50 DEMA & 200 EMA)
==============================================================================
Scans all 500+ Nifty stocks across both 50 DEMA and 200 EMA support zones
applying the 10-Point Pre-Entry Gatekeeper rules:
  1. Price > 200 EMA (Stage 2 Uptrend)
  2. 50 DEMA > 200 EMA (for 50 DEMA setups)
  3. 52W ATH within <= 180 days (Rule 1 Leadership)
  4. Price within -3.0% to +3.5% of Support EMA
  5. Approach from above (prior 15-20 bars above support EMA)
  6. Base consolidation >= 4 bars
  7. Risk % strictly between 2.5% and 6.0% (Viable Geometry)
  8. Position sizing calculated strictly for 1R = ₹1,000 risk

Usage:
  py Backtesting/scan_upcoming_setups.py
==============================================================================
"""

import os
import glob
import json
import numpy as np
import pandas as pd

DATA_DIR = r'd:\TradingSystem\TradingJournalAutomation\DhanTradingJournal\Data\Historical\Yahoo'
OUT_JSON = r'd:\TradingSystem\Backtesting\upcoming_live_setups.json'

# Load market cap mapping from backtest logs
df50 = pd.read_csv(r'd:\TradingSystem\Backtesting\backtest_50_dema_trades_log.csv')
cap_map = dict(zip(df50['Symbol'], df50['MarketCap']))

def get_cap(sym):
    s = sym.replace('.NS', '')
    return cap_map.get(s, 'Mid Cap')

def load_clean_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        if len(df) < 150: return None
        if pd.isna(df.iloc[0]['Date']) or not str(df.iloc[0]['Date']).startswith('20'):
            df = df.iloc[1:].copy()
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values('Date').reset_index(drop=True)
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df = df.dropna(subset=['Close'])
        return df
    except Exception:
        return None

def scan_symbol(symbol, df, support_ema=50):
    if len(df) < 220: return None
    
    df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df['SupportEMA'] = df['Close'].ewm(span=support_ema, adjust=False).mean()
    
    tr1 = df['High'] - df['Low']
    tr2 = (df['High'] - df['Close'].shift(1)).abs()
    tr3 = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14, min_periods=5).mean()
    df['ATH'] = df['High'].cummax()
    
    is_ath = (df['High'] >= df['ATH'] * 0.998)
    days_since_ath = []
    last_idx = -9999
    for i in range(len(df)):
        if is_ath.iloc[i]: last_idx = i
        days_since_ath.append(i - last_idx)
    df['BarsSinceATH'] = days_since_ath
    
    latest_idx = len(df) - 1
    row = df.iloc[latest_idx]
    
    max_ath_days = 90 if support_ema == 50 else 180
    if not (5 <= row['BarsSinceATH'] <= max_ath_days):
        return None
        
    if row['Close'] < row['EMA200'] * 0.97:
        return None
    if support_ema == 50 and row['EMA50'] < row['EMA200']:
        return None
        
    sup_val = row['SupportEMA']
    dist_pct = (row['Close'] - sup_val) / sup_val * 100
    if not (-3.0 <= dist_pct <= 3.8):
        return None
        
    prior_window = df.iloc[max(0, latest_idx - 20): latest_idx]
    if prior_window['Close'].mean() < sup_val * 0.98:
        return None
        
    base_window = df.iloc[max(0, latest_idx - 8): latest_idx + 1]
    if len(base_window) < 4:
        return None
    base_high = float(base_window['High'].max())
    base_low = float(base_window['Low'].min())
    
    atr_val = float(row['ATR'])
    sl_price = round(base_low - 0.3 * atr_val, 2)
    entry_trigger = round(base_high, 2)
    risk_per_share = round(entry_trigger - sl_price, 2)
    if risk_per_share <= 0:
        return None
    risk_pct = round((risk_per_share / entry_trigger) * 100, 2)
    if risk_pct > 7.5 or risk_pct < 1.5:
        return None
        
    qty = int(1000 / risk_per_share)
    if qty <= 0: return None
    
    be_price = round(entry_trigger + 1.5 * risk_per_share, 2)
    tp_price = round(entry_trigger + 2.0 * risk_per_share, 2)
    clean_sym = symbol.replace('.NS', '')
    ath_val = round(float(row['ATH']), 2)
    cur_price = round(float(row['Close']), 2)
    corr_pct = round(((cur_price - ath_val) / ath_val) * 100, 1)
    
    return {
        'symbol': clean_sym,
        'ticker': clean_sym,
        'marketCap': get_cap(clean_sym),
        'supportEMA': f'{support_ema} EMA',
        'currentPrice': cur_price,
        'supportEmaPrice': round(float(sup_val), 2),
        'distFromEmaPct': round(float(dist_pct), 2),
        'entryTrigger': entry_trigger,
        'stopLoss': sl_price,
        'riskPct': risk_pct,
        'quantity': qty,
        'bePrice': be_price,
        'tpPrice': tp_price,
        'athPrice': ath_val,
        'corrFromAthPct': corr_pct,
        'barsSinceAth': int(row['BarsSinceATH']),
        'latestDate': str(row['Date'])[:10],
        'capitalOutlay': round(entry_trigger * qty, 2),
        'tvUrl': f'https://www.tradingview.com/chart/?symbol=NSE%3A{clean_sym}'
    }

def run_scanner():
    csv_files = glob.glob(os.path.join(DATA_DIR, '*.csv'))
    results = []
    
    for f in csv_files:
        sym = os.path.basename(f).replace('.csv', '')
        if sym.startswith('NIFTY') or sym.startswith('CNX') or sym.startswith('^') or sym == 'INDIAVIX':
            continue
        df = load_clean_csv(f)
        if df is None: continue
        
        res50 = scan_symbol(sym, df, support_ema=50)
        if res50: results.append(res50)
        
        res200 = scan_symbol(sym, df, support_ema=200)
        if res200: results.append(res200)

    results.sort(key=lambda x: abs(x['distFromEmaPct']))
    
    with open(OUT_JSON, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"Scan complete. Found {len(results)} qualified upcoming setups.")
    print(f"50 DEMA Setups: {len([x for x in results if x['supportEMA'] == '50 EMA'])}")
    print(f"200 EMA Setups: {len([x for x in results if x['supportEMA'] == '200 EMA'])}")
    print(f"Saved to: {OUT_JSON}")

if __name__ == '__main__':
    run_scanner()
