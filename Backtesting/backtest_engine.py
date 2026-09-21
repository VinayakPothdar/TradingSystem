import os
import glob
import yaml
import numpy as np
import pandas as pd
from datetime import datetime

class SwingBacktestEngine:
    def __init__(self, config_path, data_dir=None):
        with open(config_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
            
        if data_dir is None:
            self.data_dir = r'd:\TradingSystem\TradingJournalAutomation\DhanTradingJournal\Data\Historical\Yahoo'
        else:
            self.data_dir = data_dir
            
        self.nifty_df = self._load_nifty()
        
    def _load_clean_csv(self, file_path):
        try:
            df = pd.read_csv(file_path)
            if len(df) < 150:
                return None
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

    def _load_nifty(self):
        nifty_path = os.path.join(self.data_dir, '^NSEI.csv')
        if not os.path.exists(nifty_path):
            return None
        df = self._load_clean_csv(nifty_path)
        if df is None:
            return None
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        # RSI 5
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=5).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=5).mean()
        rs = gain / (loss + 1e-9)
        df['RSI5'] = 100 - (100 / (1 + rs))
        return df.set_index('Date')

    def is_nifty_valid(self, date):
        if not self.cfg.get('enable_nifty_filter', True) or self.nifty_df is None:
            return True
        cond = self.cfg.get('nifty_condition', 'pullback')
        if cond == 'all':
            return True
        if date not in self.nifty_df.index:
            # find closest previous date
            prev_dates = self.nifty_df.index[self.nifty_df.index <= date]
            if len(prev_dates) == 0:
                return True
            row = self.nifty_df.loc[prev_dates[-1]]
        else:
            row = self.nifty_df.loc[date]
            
        if cond == 'above_200':
            return row['Close'] >= row['EMA200']
        elif cond == 'pullback':
            # Nifty is below 20 EMA, or RSI5 < 50, or Close within 1% of EMA50
            return (row['Close'] <= row['EMA20'] * 1.01) or (row['RSI5'] < 50)
        return True

    def calculate_indicators(self, df):
        sup_span = self.cfg['support_ema']
        df['SupportEMA'] = df['Close'].ewm(span=sup_span, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        
        # ATR 14
        tr1 = df['High'] - df['Low']
        tr2 = (df['High'] - df['Close'].shift(1)).abs()
        tr3 = (df['Low'] - df['Close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['ATR'] = tr.rolling(window=14, min_periods=5).mean()
        
        # Rolling 250-day High (ATH proxy)
        df['ATH'] = df['High'].rolling(window=250, min_periods=60).max()
        
        # Days since last ATH
        is_ath = (df['High'] >= df['ATH'] * 0.998)
        days_since_ath = []
        last_idx = -9999
        for i in range(len(df)):
            if is_ath.iloc[i]:
                last_idx = i
            days_since_ath.append(i - last_idx)
        df['BarsSinceATH'] = days_since_ath
        return df

    def scan_and_backtest_symbol(self, symbol, csv_path):
        df = self._load_clean_csv(csv_path)
        if df is None or len(df) < 220:
            return []
            
        df = self.calculate_indicators(df)
        trades = []
        
        sup_upper = self.cfg['zone_tolerance_upper']
        sup_lower = self.cfg['zone_tolerance_lower']
        ath_max_lookback = self.cfg['ath_lookback_days']
        ath_min_age = self.cfg['ath_min_age_days']
        max_bounces = self.cfg['max_allowed_bounces']
        cluster_window = self.cfg['bounce_cluster_window']
        min_base = self.cfg['base_min_candles']
        max_base = self.cfg['base_max_candles']
        req_higher_low = self.cfg['require_higher_low']
        req_above_200 = self.cfg.get('require_primary_trend_above_200', True)
        
        # We search for base setups
        i = 200 # Start after enough history
        last_exit_idx = 0
        
        while i < len(df) - 10:
            if i <= last_exit_idx:
                i += 1
                continue
                
            row = df.iloc[i]
            bars_since_ath = row['BarsSinceATH']
            
            # 1. ATH Check
            if not (ath_min_age <= bars_since_ath <= ath_max_lookback):
                i += 1
                continue
                
            # 2. Primary Trend Filter (if 50 EMA, must still be above 200 EMA)
            if req_above_200 and (row['Close'] < row['EMA200'] * 0.97):
                i += 1
                continue
                
            # 3. Touch in Support EMA zone
            sup_val = row['SupportEMA']
            is_in_zone = (row['Low'] <= sup_val * (1 + sup_upper)) and (row['Close'] >= sup_val * (1 + sup_lower))
            if not is_in_zone:
                i += 1
                continue
                
            # 4. Approach direction check (must approach from above)
            if self.cfg.get('require_approach_from_above', True):
                # Prior 10 to 20 bars should have been above support EMA
                lookback_approach = df.iloc[max(0, i-20):i]
                if lookback_approach['Close'].mean() < sup_val * 0.98:
                    i += 1
                    continue
                    
            # 5. Count Bounces since ATH
            ath_idx = i - bars_since_ath
            prior_window = df.iloc[ath_idx:i]
            # Touches in zone
            touches = (prior_window['Low'] <= prior_window['SupportEMA'] * (1 + sup_upper)) & \
                      (prior_window['Close'] >= prior_window['SupportEMA'] * (1 + sup_lower))
            touch_indices = np.where(touches)[0]
            
            bounce_count = 1
            if len(touch_indices) > 1:
                # cluster touches
                diffs = np.diff(touch_indices)
                bounces = np.sum(diffs > cluster_window) + 1
                bounce_count = bounces
                
            if bounce_count > max_bounces:
                i += 1
                continue
                
            # 6. Base Formation Check
            # Check if there is a 4-12 candle consolidation base ending at or around bar i
            base_window = df.iloc[max(0, i - max_base): i + 1]
            if len(base_window) < min_base:
                i += 1
                continue
                
            base_high = base_window['High'].max()
            base_low = base_window['Low'].min()
            
            # Higher low / W-pattern check
            if req_higher_low and len(base_window) >= 4:
                first_half_low = base_window.iloc[:len(base_window)//2]['Low'].min()
                second_half_low = base_window.iloc[len(base_window)//2:]['Low'].min()
                if second_half_low < first_half_low * 0.99:
                    i += 1
                    continue
                    
            # 7. Entry Trigger (Breakout of Base High within next 3 bars)
            entry_triggered = False
            entry_idx = -1
            entry_price = 0
            
            for fwd in range(1, 4):
                if i + fwd >= len(df):
                    break
                fwd_row = df.iloc[i + fwd]
                if fwd_row['High'] >= base_high:
                    entry_triggered = True
                    entry_idx = i + fwd
                    entry_price = max(base_high, fwd_row['Open'])
                    break
                    
            if not entry_triggered:
                i += 1
                continue
                
            entry_date = df.iloc[entry_idx]['Date']
            
            # 8. Nifty Market Timing Filter
            if not self.is_nifty_valid(entry_date):
                i += 1
                continue
                
            # 9. Stop Loss & Risk Calculation
            atr_val = df.iloc[entry_idx]['ATR']
            sl_buffer = self.cfg.get('sl_atr_buffer', 0.3) * atr_val
            sl_price = base_low - sl_buffer
            risk_per_share = entry_price - sl_price
            
            if risk_per_share <= 0:
                i += 1
                continue
                
            risk_pct = risk_per_share / entry_price
            if risk_pct > self.cfg.get('max_initial_sl_pct', 0.07):
                i += 1
                continue
                
            risk_inr = self.cfg.get('risk_per_trade_inr', 1000.0)
            qty = int(risk_inr / risk_per_share)
            if qty <= 0:
                i += 1
                continue
                
            # 10. Bar-by-Bar Trade Lifecycle Simulation
            trade_result = self._simulate_trade(df, entry_idx, entry_price, sl_price, qty, risk_per_share, bounce_count)
            trades.append(trade_result)
            last_exit_idx = trade_result['ExitIdx']
            i = last_exit_idx + 1
            
        return trades

    def _simulate_trade(self, df, entry_idx, entry_price, initial_sl, qty, risk_per_share, bounce_count):
        symbol = df.iloc[0].get('Symbol', 'STOCK')
        entry_date = df.iloc[entry_idx]['Date']
        
        active_sl = initial_sl
        be_trigger_r = self.cfg.get('breakeven_trigger_r', 1.5)
        target_1_r = self.cfg.get('target_1_r', 2.0)
        target_1_pct = self.cfg.get('target_1_size_pct', 0.50)
        max_holding = self.cfg.get('max_holding_days', 60)
        
        target_1_price = entry_price + (target_1_r * risk_per_share)
        be_trigger_price = entry_price + (be_trigger_r * risk_per_share)
        
        qty_remaining = qty
        qty_booked_t1 = 0
        t1_exit_price = 0
        t1_booked = False
        be_activated = False
        
        exit_idx = entry_idx
        exit_date = entry_date
        exit_reason = 'Holding'
        final_exit_price = 0
        
        peak_price = entry_price
        trough_price = entry_price
        
        for cur_idx in range(entry_idx + 1, min(len(df), entry_idx + max_holding + 1)):
            cur_bar = df.iloc[cur_idx]
            cur_high = cur_bar['High']
            cur_low = cur_bar['Low']
            cur_close = cur_bar['Close']
            
            if cur_high > peak_price:
                peak_price = cur_high
            if cur_low < trough_price:
                trough_price = cur_low
                
            # Check Breakeven trigger
            if not be_activated and peak_price >= be_trigger_price:
                be_activated = True
                active_sl = max(active_sl, entry_price) # Breakeven
                
            # Check Target 1 (book partial or 100%)
            if not t1_booked and cur_high >= target_1_price:
                t1_booked = True
                qty_booked_t1 = int(qty * target_1_pct)
                qty_remaining -= qty_booked_t1
                t1_exit_price = target_1_price
                if qty_remaining == 0:
                    exit_idx = cur_idx
                    exit_date = cur_bar['Date']
                    final_exit_price = target_1_price
                    exit_reason = 'Target1_100pct'
                    break
                
            # Trail runner (remaining 50%)
            if t1_booked and be_activated:
                # Trail to 20 EMA or rising higher low
                trail_ema20 = cur_bar['EMA20']
                if trail_ema20 > active_sl:
                    active_sl = trail_ema20
                    
            # Check Stop Loss hit
            if cur_low <= active_sl:
                exit_idx = cur_idx
                exit_date = cur_bar['Date']
                final_exit_price = active_sl
                exit_reason = 'StopLoss' if not be_activated else ('Breakeven' if not t1_booked else 'TrailSL')
                break
                
            # Time exit
            if cur_idx == entry_idx + max_holding:
                exit_idx = cur_idx
                exit_date = cur_bar['Date']
                final_exit_price = cur_close
                exit_reason = 'TimeExit'
                break
                
        # If reached end of dataset without exiting
        if final_exit_price == 0:
            exit_idx = min(len(df) - 1, entry_idx + max_holding)
            exit_date = df.iloc[exit_idx]['Date']
            final_exit_price = df.iloc[exit_idx]['Close']
            exit_reason = 'OpenPosition'
            
        # PnL Calculation
        gross_pnl = (qty_booked_t1 * (t1_exit_price - entry_price)) + (qty_remaining * (final_exit_price - entry_price))
        # Realistic friction charges (~0.15% turnover)
        turnover = (entry_price * qty) + (t1_exit_price * qty_booked_t1) + (final_exit_price * qty_remaining)
        charges = turnover * 0.0015
        net_pnl = gross_pnl - charges
        realized_r = net_pnl / self.cfg.get('risk_per_trade_inr', 1000.0)
        peak_r = ((peak_price - entry_price) * qty) / self.cfg.get('risk_per_trade_inr', 1000.0)
        heat_r = ((trough_price - entry_price) * qty) / self.cfg.get('risk_per_trade_inr', 1000.0)
        
        return {
            'EntryIdx': entry_idx,
            'ExitIdx': exit_idx,
            'EntryDate': entry_date.strftime('%Y-%m-%d'),
            'ExitDate': exit_date.strftime('%Y-%m-%d'),
            'EntryPrice': round(entry_price, 2),
            'InitialSL': round(initial_sl, 2),
            'FinalExitPrice': round(final_exit_price, 2),
            'HoldingDays': (exit_date - entry_date).days,
            'Quantity': qty,
            'GrossPnL': round(gross_pnl, 2),
            'Charges': round(charges, 2),
            'NetPnL': round(net_pnl, 2),
            'RealizedR': round(realized_r, 2),
            'PeakR': round(peak_r, 2),
            'HeatR': round(heat_r, 2),
            'ExitReason': exit_reason,
            'BounceCount': bounce_count,
            'Target1Hit': t1_booked
        }

    def run_full_backtest(self, max_stocks=None):
        csv_files = glob.glob(os.path.join(self.data_dir, '*.csv'))
        all_trades = []
        
        # Exclude indices
        stock_files = [f for f in csv_files if not os.path.basename(f).startswith('^') and not 'NIFTY' in os.path.basename(f).upper()]
        
        if max_stocks:
            stock_files = stock_files[:max_stocks]
            
        print(f"Running backtest across {len(stock_files)} stocks...")
        for i, file_path in enumerate(stock_files):
            sym = os.path.basename(file_path).replace('.NS.csv', '').replace('.csv', '')
            sym_trades = self.scan_and_backtest_symbol(sym, file_path)
            for t in sym_trades:
                t['Symbol'] = sym
                all_trades.append(t)
                
            if (i + 1) % 50 == 0 or i == len(stock_files) - 1:
                print(f"Processed {i+1}/{len(stock_files)} stocks... Found {len(all_trades)} trades so far.")
                
        df_trades = pd.DataFrame(all_trades)
        return df_trades
