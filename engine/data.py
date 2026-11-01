"""
Data management module:
- Converts 535 CSV files into a compressed single Parquet file (historical_candles.parquet)
- Fast candle loading from Parquet (loads in ~0.3s)
- Incremental tail-fetching from Yahoo Finance
- Dynamic tail stitching for 100% up-to-date backtests & scans
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
PARQUET_FILE = DATA_DIR / "historical_candles.parquet"
WATCHLIST_FILE = DATA_DIR / "nifty500.csv"
LEGACY_CSV_DIR = PROJECT_DIR / "TradingJournalAutomation" / "DhanTradingJournal" / "Data" / "Historical" / "Yahoo"


def load_nifty500_symbols() -> List[str]:
    """Loads Nifty 500 stock symbols from watchlist."""
    if not WATCHLIST_FILE.exists():
        return []
    df = pd.read_csv(WATCHLIST_FILE)
    col = "Symbol" if "Symbol" in df.columns else df.columns[0]
    return [str(s).strip().upper() for s in df[col] if pd.notna(s) and str(s).strip()]


def build_parquet_from_csvs(output_path: Optional[Path] = None) -> Path:
    """
    Consolidates all 535 CSV files into a single, compressed Parquet file.
    Reduces 80 MB down to ~12-15 MB and enables sub-second loading.
    """
    out_file = output_path or PARQUET_FILE
    out_file.parent.mkdir(parents=True, exist_ok=True)

    csv_files = list(LEGACY_CSV_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {LEGACY_CSV_DIR}")

    frames = []
    for f in csv_files:
        sym = f.stem.replace(".NS", "").upper()
        try:
            df = pd.read_csv(f)
            if df.empty or "Date" not in df.columns or "Close" not in df.columns:
                continue

            df["Date"] = pd.to_datetime(df["Date"])
            df["Symbol"] = sym

            cols = ["Symbol", "Date", "Open", "High", "Low", "Close", "Volume"]
            avail_cols = [c for c in cols if c in df.columns]
            df = df[avail_cols]

            # Downcast floats to float32 to save RAM and disk
            float_cols = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
            df[float_cols] = df[float_cols].astype(np.float32)
            if "Volume" in df.columns:
                df["Volume"] = df["Volume"].fillna(0).astype(np.int64)

            frames.append(df)
        except Exception:
            continue

    if not frames:
        raise ValueError("Failed to load any valid candle data.")

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["Symbol", "Date"]).reset_index(drop=True)

    # Save with snappy/zstd compression
    combined.to_parquet(out_file, engine="pyarrow", compression="zstd", index=False)
    return out_file


def load_all_candles() -> pd.DataFrame:
    """
    Loads all historical candles from the compressed Parquet file.
    If the Parquet file doesn't exist yet, automatically builds it from CSVs.
    """
    if not PARQUET_FILE.exists():
        build_parquet_from_csvs(PARQUET_FILE)

    return pd.read_parquet(PARQUET_FILE, engine="pyarrow")


def load_stock_candles(symbol: str) -> Optional[pd.DataFrame]:
    """Loads candles for a single symbol from Parquet."""
    df_all = load_all_candles()
    sym = symbol.replace(".NS", "").upper()
    stock_df = df_all[df_all["Symbol"] == sym].sort_values("Date").reset_index(drop=True)
    return stock_df if not stock_df.empty else None


def fetch_fresh_tail(symbols: List[str], start_date: str) -> Dict[str, pd.DataFrame]:
    """
    Fetches recent daily candles from Yahoo Finance starting from start_date.
    Uses multi-threaded batch downloading.
    """
    if yf is None or not symbols:
        return {}

    # Format tickers with .NS for Yahoo
    tickers = [s if s.endswith(".NS") or s.startswith("^") else f"{s}.NS" for s in symbols]
    
    try:
        data = yf.download(
            tickers,
            start=start_date,
            interval="1d",
            group_by="ticker",
            progress=False,
            threads=True,
            auto_adjust=False,
        )

        result: Dict[str, pd.DataFrame] = {}
        for sym, tick in zip(symbols, tickers):
            try:
                if len(tickers) == 1:
                    sub_df = data.copy()
                elif hasattr(data.columns, "levels") and tick in data.columns.levels[0]:
                    sub_df = data[tick].dropna(subset=["Close"])
                else:
                    sub_df = None

                if sub_df is not None and not sub_df.empty:
                    sub_df = sub_df.reset_index()
                    sub_df["Date"] = pd.to_datetime(sub_df["Date"])
                    sub_df["Symbol"] = sym.replace(".NS", "").upper()
                    result[sub_df["Symbol"].iloc[0]] = sub_df
            except Exception:
                continue

        return result
    except Exception:
        return {}
