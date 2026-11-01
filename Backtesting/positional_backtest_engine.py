import os
import glob
import yaml
import numpy as np
import pandas as pd
from datetime import datetime

class PositionalBacktestEngine:
    def __init__(self, config_path, data_dir=None):
        with open(config_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
            
        if data_dir is None:
            self.data_dir = r'd:\TradingSystem\TradingJournalAutomation\DhanTradingJournal\Data\Historical\Yahoo'
        else:
            self.data_dir = data_dir
            
        self.nifty_daily, self.nifty_weekly = self._load_nifty()
        
    def _load_clean_daily_csv(self, file_path):
        try:
            df = pd.read_csv(file_path)
            if len(df) < 200:
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

    def _resample_to_weekly(self, df_daily):
        df_d = df_daily.copy().set_index('Date')
        df_w = df_d.resample('W-FRI').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()
        return df_w.reset_index()

    def _load_nifty(self):
        nifty_path = os.path.join(self.data_dir, '^NSEI.csv')
        if not os.path.exists(nifty_path):
            return None, None
        df_d = self._load_clean_csv(nifty_path) if hasattr(self, '_load_clean_csv') else self._load_clean_daily_csv(nifty_path)
        if df_d is None:
            return None, None
            
        df_d['EMA200'] = df_d['Close'].ewm(span=200, adjust=False).mean()
        df_d['EMA50'] = df_d['Close'].ewm(span=50, adjust=False).mean()
        
        df_w = self._resample_to_weekly(df_d)
        df_w['EMA200W'] = df_w['Close'].ewm(span=200, adjust=False).mean()
        df_w['EMA50W'] = df_w['Close'].ewm(span=50, adjust=False).mean()
        df_w['EMA20W'] = df_w['Close'].ewm(span=20, adjust=False).mean()
        
        return df_d.set_index('Date'), df_w.set_index('Date')

    def get_market_regime(self, dt):
        """Returns market regime classification at a given date."""
        if self.nifty_daily is None or self.nifty_weekly is None:
            return "UNKNOWN", True
            
        # Daily Nifty
        prev_d = self.nifty_daily.index[self.nifty_daily.index <= dt]
        if len(prev_d) == 0:
            return "UNKNOWN", True
        last_d = self.nifty_daily.loc[prev_d[-1]]
        
        # Weekly Nifty
        prev_w = self.nifty_weekly.index[self.nifty_weekly.index <= dt]
        if len(prev_w) == 0:
            return "UNKNOWN", True
        last_w = self.nifty_weekly.loc[prev_w[-1]]
        
        is_above_200d = last_d['Close'] >= last_d['EMA200']
        is_above_50w = last_w['Close'] >= last_w['EMA50W']
        is_above_20w = last_w['Close'] >= last_w['EMA20W']
        
        cond = self.cfg.get('nifty_condition', 'above_50_wema')
        if cond == 'all':
            valid = True
        elif cond == 'above_50_wema':
            valid = is_above_50w
        elif cond == 'above_20_wema':
            valid = is_above_20w
        else:
            valid = is_above_200d
            
        if is_above_50w and is_above_200d:
            regime = "Bullish Uptrend"
        elif is_above_50w and not is_above_200d:
            regime = "Pullback in Secular Trend"
        else:
            regime = "Bearish Downtrend"
            
        return regime, valid

    def calculate_weekly_indicators(self, df_w):
        sup_span = self.cfg.get('support_ema', 200)
        df_w['SupportEMA'] = df_w['Close'].ewm(span=sup_span, adjust=False).mean()
        df_w['EMA50W'] = df_w['Close'].ewm(span=50, adjust=False).mean()
        df_w['EMA20W'] = df_w['Close'].ewm(span=20, adjust=False).mean()
        
        # Weekly ATR 14
        tr1 = df_w['High'] - df_w['Low']
        tr2 = (df_w['High'] - df_w['Close'].shift(1)).abs()
        tr3 = (df_w['Low'] - df_w['Close'].shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df_w['ATR'] = tr.rolling(window=14, min_periods=5).mean()
        
        # 52-week High (Rolling 52 weeks)
        df_w['ATH52'] = df_w['High'].rolling(window=52, min_periods=26).max()
        
        # Weeks since 52W High
        is_ath = (df_w['High'] >= df_w['ATH52'] * 0.995)
        weeks_since_ath = []
        last_idx = -9999
        for i in range(len(df_w)):
            if is_ath.iloc[i]:
                last_idx = i
            weeks_since_ath.append(i - last_idx)
        df_w['WeeksSinceATH'] = weeks_since_ath
        return df_w

    def scan_and_backtest_symbol(self, symbol, csv_path):
        df_daily = self._load_clean_daily_csv(csv_path)
        if df_daily is None or len(df_daily) < 400: # Need ~1.5 years daily at minimum
            return []
            
        df_weekly = self._resample_to_weekly(df_daily)
        if len(df_weekly) < 180: # Need sufficient weekly bars to seed 200 WEMA
            return []
            
        df_weekly = self.calculate_weekly_indicators(df_weekly)
        
        sup_upper = self.cfg.get('zone_tolerance_upper', 0.03)
        sup_lower = self.cfg.get('zone_tolerance_lower', -0.05)
        ath_max_weeks = self.cfg.get('ath_lookback_weeks', 52)
        ath_min_weeks = self.cfg.get('ath_min_age_weeks', 6)
        min_base = self.cfg.get('base_min_candles', 3)
        max_base = self.cfg.get('base_max_candles', 10)
        req_higher_low = self.cfg.get('require_higher_low', True)
        enable_nifty = self.cfg.get('enable_nifty_filter', True)
        
        trades = []
        
        # Start scanning from week 150 onwards
        w_idx = 150
        last_exit_date = pd.to_datetime('1900-01-01')
        
        while w_idx < len(df_weekly) - 4:
            w_row = df_weekly.iloc[w_idx]
            week_date = w_row['Date']
            
            if week_date <= last_exit_date:
                w_idx += 1
                continue
                
            weeks_since_ath = w_row['WeeksSinceATH']
            # 1. 52W High filter: Stock must have been near 52W High within lookback, but allowed to pull back
            if not (ath_min_weeks <= weeks_since_ath <= ath_max_weeks):
                w_idx += 1
                continue
                
            # 2. 200 WEMA Support Zone Touch
            sup_val = w_row['SupportEMA']
            is_in_zone = (w_row['Low'] <= sup_val * (1 + sup_upper)) and (w_row['Close'] >= sup_val * (1 + sup_lower))
            if not is_in_zone:
                w_idx += 1
                continue
                
            # 3. Approach direction (must approach from above)
            if self.cfg.get('require_approach_from_above', True):
                prior_weeks = df_weekly.iloc[max(0, w_idx - 12):w_idx]
                if prior_weeks['Close'].mean() < sup_val * 0.98:
                    w_idx += 1
                    continue
                    
            # 4. Weekly Base Consolidation Check
            base_window = df_weekly.iloc[max(0, w_idx - max_base + 1): w_idx + 1]
            if len(base_window) < min_base:
                w_idx += 1
                continue
                
            base_high = base_window['High'].max()
            base_low = base_window['Low'].min()
            
            # 5. Higher-Low / W-bottom check inside weekly base
            if req_higher_low and len(base_window) >= 4:
                first_half_low = base_window.iloc[:len(base_window)//2]['Low'].min()
                second_half_low = base_window.iloc[len(base_window)//2:]['Low'].min()
                if second_half_low < first_half_low * 0.985: # Allow small wick variance
                    w_idx += 1
                    continue
                    
            # 6. Look for Daily Breakout Trigger in the subsequent 2 to 4 weeks
            # Find daily bars corresponding to the next 20 trading days after base completion
            next_daily_bars = df_daily[df_daily['Date'] > week_date].head(25)
            if len(next_daily_bars) == 0:
                w_idx += 1
                continue
                
            breakout_daily_row = None
            entry_idx_in_daily = -1
            
            for d_i, d_row in next_daily_bars.iterrows():
                # Trigger when daily price crosses base high
                if d_row['High'] >= base_high:
                    breakout_daily_row = d_row
                    entry_idx_in_daily = d_i
                    break
                # If price breaks significantly below base low before breakout, cancel setup
                if d_row['Low'] < base_low * 0.96:
                    break
                    
            if breakout_daily_row is None:
                w_idx += 1
                continue
                
            entry_date = breakout_daily_row['Date']
            entry_price = max(base_high, breakout_daily_row['Open'])
            
            # Market Regime Filter check at Entry Date
            regime, is_market_valid = self.get_market_regime(entry_date)
            if enable_nifty and not is_market_valid:
                w_idx += 1
                continue
                
            # 7. Stop-Loss & Position Sizing (1R = Rs. 1,000)
            weekly_atr = w_row['ATR'] if not np.isnan(w_row['ATR']) else (base_high - base_low)
            sl_atr_buf = self.cfg.get('sl_atr_buffer', 0.3)
            initial_sl = base_low - (sl_atr_buf * weekly_atr)
            risk_per_share = entry_price - initial_sl
            
            if risk_per_share <= 0:
                w_idx += 1
                continue
                
            sl_pct = risk_per_share / entry_price
            max_sl_pct = self.cfg.get('max_initial_sl_pct', 0.12)
            if sl_pct > max_sl_pct or sl_pct < 0.02:
                w_idx += 1
                continue
                
            risk_capital = self.cfg.get('risk_per_trade_inr', 1000)
            quantity = int(risk_capital / risk_per_share)
            if quantity <= 0:
                quantity = 1
                
            capital_outlay = entry_price * quantity
            
            # 8. Simulate Daily Excursions & Exits
            holding_bars = df_daily[df_daily['Date'] >= entry_date].iloc[1:] # Bars after entry
            max_hold = self.cfg.get('max_holding_days', 180)
            
            be_trigger_r = self.cfg.get('breakeven_trigger_r', 1.5)
            t1_r = self.cfg.get('target_1_r', 2.5)
            t1_size_pct = self.cfg.get('target_1_size_pct', 0.50)
            
            cur_sl = initial_sl
            is_breakeven_active = False
            is_t1_booked = False
            t1_exit_date = None
            t1_pnl = 0.0
            
            peak_price = entry_price
            trough_price = entry_price
            exit_date = None
            exit_price = 0.0
            exit_reason = ""
            
            days_held = 0
            
            for b_i, b_row in holding_bars.iterrows():
                days_held += 1
                bar_high = b_row['High']
                bar_low = b_row['Low']
                bar_close = b_row['Close']
                bar_date = b_row['Date']
                
                if bar_high > peak_price:
                    peak_price = bar_high
                if bar_low < trough_price:
                    trough_price = bar_low
                    
                cur_peak_r = ((peak_price - entry_price) * quantity) / risk_capital
                
                # Check Breakeven Trigger
                if cur_peak_r >= be_trigger_r and not is_breakeven_active:
                    cur_sl = max(cur_sl, entry_price)
                    is_breakeven_active = True
                    
                # Check Target 1 Booking
                if cur_peak_r >= t1_r and not is_t1_booked:
                    is_t1_booked = True
                    t1_exit_date = bar_date
                    t1_qty = int(quantity * t1_size_pct)
                    t1_target_price = entry_price + (t1_r * (risk_capital / quantity))
                    t1_pnl = (t1_target_price - entry_price) * t1_qty
                    # Move stop for remainder to entry price or higher
                    cur_sl = max(cur_sl, entry_price)
                    
                # Check Stop Hit
                if bar_low <= cur_sl:
                    exit_date = bar_date
                    exit_price = min(cur_sl, b_row['Open'])
                    if is_breakeven_active:
                        exit_reason = "Breakeven / Trail Stop Hit"
                    else:
                        exit_reason = "Initial Stop Hit"
                    break
                    
                # Check Max Holding Time Stop
                if days_held >= max_hold:
                    exit_date = bar_date
                    exit_price = bar_close
                    exit_reason = "Time Stop (Max Holding Reached)"
                    break
                    
            if exit_date is None:
                # Open trade up to latest bar
                last_bar = holding_bars.iloc[-1] if len(holding_bars) > 0 else breakout_daily_row
                exit_date = last_bar['Date']
                exit_price = last_bar['Close']
                exit_reason = "Active / End of Data"
                
            last_exit_date = exit_date
            
            # P&L Calculation with partial booking
            if is_t1_booked:
                rem_qty = quantity - int(quantity * t1_size_pct)
                rem_pnl = (exit_price - entry_price) * rem_qty
                net_pnl = t1_pnl + rem_pnl
            else:
                net_pnl = (exit_price - entry_price) * quantity
                
            realized_r = net_pnl / risk_capital
            peak_r = ((peak_price - entry_price) * quantity) / risk_capital
            heat_r = ((trough_price - entry_price) * quantity) / risk_capital
            
            # Check Round-trip
            is_round_trip = (net_pnl < 0) and (peak_r >= 1.5)
            
            trades.append({
                'Symbol': symbol,
                'EntryDate': entry_date.strftime('%Y-%m-%d'),
                'ExitDate': exit_date.strftime('%Y-%m-%d'),
                'HoldingDays': days_held,
                'EntryPrice': round(entry_price, 2),
                'ExitPrice': round(exit_price, 2),
                'InitialSL': round(initial_sl, 2),
                'SL_Pct': round(sl_pct * 100, 1),
                'Quantity': quantity,
                'CapitalOutlay': round(capital_outlay, 2),
                'NetPnL': round(net_pnl, 2),
                'RealizedR': round(realized_r, 2),
                'PeakPrice': round(peak_price, 2),
                'PeakR': round(peak_r, 2),
                'TroughPrice': round(trough_price, 2),
                'HeatR': round(heat_r, 2),
                'IsRoundTrip': is_round_trip,
                'ExitReason': exit_reason,
                'T1_Booked': is_t1_booked,
                'MarketRegime': regime,
                'SupportEMA': round(sup_val, 2),
                'WeeksInBase': len(base_window)
            })
            
            w_idx += max(1, days_held // 5)
            
        return trades
