import argparse
import csv
import os
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("Missing dependency: yfinance")
    print("Install with: py -m pip install yfinance pandas")
    sys.exit(1)


def load_indices(indices_path: Path) -> dict[str, str]:
    """Dynamically load indices from CSV (Name -> Ticker)."""
    indices: dict[str, str] = {}
    if not indices_path.exists():
        print(f"Indices file not found: {indices_path}")
        return indices

    with indices_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Name") or row.get("Index Name") or "").strip()
            ticker = (row.get("Ticker") or row.get("Symbol") or "").strip()
            if name and ticker:
                indices[name] = ticker
    return indices


def load_aliases(aliases_path: Path) -> dict[str, str]:
    """Dynamically load symbol aliases from CSV (TradeSymbol -> YahooTicker)."""
    aliases: dict[str, str] = {}
    if not aliases_path.exists():
        return aliases

    with aliases_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            trade_sym = (row.get("TradeSymbol") or row.get("Symbol") or "").strip().lower()
            yahoo_tick = (row.get("YahooTicker") or row.get("Ticker") or "").strip().upper()
            if trade_sym and yahoo_tick:
                aliases[trade_sym] = yahoo_tick
    return aliases


def load_watchlist_lookup(watchlist_path: Path) -> tuple[dict[str, str], set[str]]:
    lookup: dict[str, str] = {}
    valid_symbols: set[str] = set()
    if not watchlist_path.exists():
        return lookup, valid_symbols

    with watchlist_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Company Name") or row.get("Name") or "").strip().lower()
            sym = (row.get("Symbol") or "").strip().upper()
            if sym:
                valid_symbols.add(sym)
            if name and sym:
                lookup[name] = sym
    return lookup, valid_symbols


def resolve_symbol(
    raw_name: str,
    watchlist_lookup: dict[str, str],
    valid_symbols: set[str],
    aliases: dict[str, str]
) -> str:
    """Resolves any raw trade name or symbol into a valid Yahoo Finance ticker."""
    raw_clean = raw_name.strip()
    norm = raw_clean.lower()
    upper = raw_clean.upper()

    # 1. Direct ticker match (e.g. 'BEL', 'TVSMOTOR', 'RELIANCE', '^NSEI')
    if upper in valid_symbols or upper.startswith("^") or upper.endswith(".NS"):
        ticker = upper
    # 2. Alias lookup (e.g. 'hero motocorp' -> 'HEROMOTOCO')
    elif norm in aliases:
        ticker = aliases[norm]
    # 3. Exact company name lookup
    elif norm in watchlist_lookup:
        ticker = watchlist_lookup[norm]
    # 4. Partial company name match
    else:
        ticker = None
        for k, v in watchlist_lookup.items():
            if norm in k:
                ticker = v
                break
        if not ticker:
            ticker = upper

    yahoo_symbol = f"{ticker}.NS" if not ticker.startswith("^") and not ticker.endswith(".NS") else ticker
    return yahoo_symbol


def get_traded_symbols_from_excel(
    workbook_path: Path,
    watchlist_lookup: dict[str, str],
    valid_symbols: set[str],
    aliases: dict[str, str]
) -> set[str]:
    tickers: set[str] = set()
    if not workbook_path.exists():
        print(f"Workbook not found: {workbook_path}")
        return tickers

    try:
        z = zipfile.ZipFile(workbook_path)
    except PermissionError:
        print("[NOTICE] MasterJournal.xlsx is locked by Excel. Closing Excel to obtain access...")
        os.system("taskkill /F /IM excel.exe >nul 2>&1")
        time.sleep(0.8)
        z = zipfile.ZipFile(workbook_path)

    with z:
        # Load shared strings
        sst_xml = z.read("xl/sharedStrings.xml")
        sst_tree = ET.fromstring(sst_xml)
        strings = []
        for si in sst_tree:
            t_node = si.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
            if t_node is not None and t_node.text:
                strings.append(t_node.text)
            else:
                r_texts = [r.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t").text
                           for r in si.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}r")
                           if r.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") is not None]
                strings.append("".join(r_texts))

        wb_xml = ET.fromstring(z.read("xl/workbook.xml"))
        rels_xml = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels_xml}

        matched_sheet_file = None
        for s in wb_xml.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"):
            if s.attrib.get("name") == "MatchedTrades":
                r_id = s.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
                if r_id in rel_map:
                    matched_sheet_file = "xl/" + rel_map[r_id].lstrip("/")
                    break

        if not matched_sheet_file:
            print("MatchedTrades sheet not found in workbook.")
            return tickers

        sheet_tree = ET.fromstring(z.read(matched_sheet_file))
        rows = list(sheet_tree.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"))
        if not rows:
            return tickers

        sym_col_prefix = "B"
        for c in rows[0].iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
            v_node = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
            if v_node is not None and v_node.text:
                t_attr = c.attrib.get("t")
                val = strings[int(v_node.text)] if t_attr == "s" else v_node.text
                if val.strip().lower() == "symbol":
                    r_ref = c.attrib.get("r", "")
                    sym_col_prefix = "".join([ch for ch in r_ref if ch.isalpha()])
                    break

        for row in rows[1:]:
            cells = list(row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"))
            sym_cell = [c for c in cells if "".join([ch for ch in c.attrib.get("r", "") if ch.isalpha()]) == sym_col_prefix]
            if not sym_cell:
                continue
            v_node = sym_cell[0].find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
            if v_node is None or not v_node.text:
                continue

            t_attr = sym_cell[0].attrib.get("t")
            raw_name = strings[int(v_node.text)] if t_attr == "s" else v_node.text
            yahoo_symbol = resolve_symbol(raw_name, watchlist_lookup, valid_symbols, aliases)
            tickers.add(yahoo_symbol)

    return tickers


def download_symbol(
    symbol: str,
    output_path: Path,
    secondary_output_path: Path | None,
    start: str,
    end: str | None = None
) -> bool:
    try:
        data = yf.download(
            symbol,
            start=start,
            end=end,
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=False,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if data.empty:
            return False

        # Flatten MultiIndex columns if present
        if hasattr(data.columns, "levels") and len(data.columns.levels) > 1:
            data.columns = [col[0] for col in data.columns]

        # Select standard columns
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]
        data = data[cols]
        data.index.name = "Date"

        data.to_csv(output_path, date_format="%Y-%m-%d")
        if secondary_output_path:
            secondary_output_path.parent.mkdir(parents=True, exist_ok=True)
            data.to_csv(secondary_output_path, date_format="%Y-%m-%d")
        return True
    except Exception as ex:
        print(f"    Error downloading {symbol}: {ex}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Download fresh candles for traded stocks, all indices, or custom symbols.")
    parser.add_argument("--mode", choices=["both", "matched", "indices", "custom", "all"], default="both",
                        help="Sync mode: 'matched' (trades only), 'indices' (indices only), 'custom' (comma-separated symbols), 'all' (Nifty 500 universe), or 'both' (default).")
    parser.add_argument("--symbols", default="", help="Comma-separated stock symbols for 'custom' mode (e.g. 'BEL, TVSMOTOR, RELIANCE').")
    parser.add_argument("--journal", default=r"D:\TradingJournal\MasterJournal.xlsx")
    parser.add_argument("--indices", default="Data/Watchlists/indices.csv")
    parser.add_argument("--aliases", default="Data/Watchlists/symbol_aliases.csv")
    parser.add_argument("--watchlist", default="Data/Watchlists/nifty500.csv")
    parser.add_argument("--output", default="Data/Historical/Yahoo")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--delay", type=float, default=0.1)
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parents[1]
    output_dir = project_dir / args.output
    bin_output_dir = project_dir / "bin" / "Debug" / "net8.0" / "Data" / "Historical" / "Yahoo"

    indices_path = project_dir / args.indices
    aliases_path = project_dir / args.aliases
    watchlist_path = project_dir / args.watchlist
    journal_path = Path(args.journal)

    print("==================================================")
    print(f"HISTORICAL CANDLE SYNC — MODE: {args.mode.upper()}")
    print("==================================================")
    print(f"Primary output:   {output_dir}")
    if bin_output_dir.parent.exists():
        print(f"Secondary output: {bin_output_dir}")
    print(f"Start date:       {args.start}\n")

    watchlist_lookup, valid_symbols = load_watchlist_lookup(watchlist_path)
    aliases = load_aliases(aliases_path)

    # 1. INDICES SYNC
    if args.mode in ("indices", "both"):
        print("--- Downloading Market Indices ---")
        market_indices = load_indices(indices_path)
        print(f"  Loaded {len(market_indices)} indices from {indices_path.name}.")

        idx_success = 0
        idx_fail = 0
        for idx_num, (name, ticker) in enumerate(market_indices.items(), 1):
            out_file = output_dir / f"{ticker}.csv"
            sec_file = bin_output_dir / f"{ticker}.csv" if bin_output_dir.parent.exists() else None
            print(f"  [{idx_num:2d}/{len(market_indices):2d}] {name:<26} ({ticker:<20})...", end=" ", flush=True)
            ok = download_symbol(ticker, out_file, sec_file, args.start, args.end)
            if ok:
                print("OK")
                idx_success += 1
            else:
                print("EMPTY/FAILED")
                idx_fail += 1
            time.sleep(args.delay)
        print(f"  Indices updated: {idx_success} / {len(market_indices)} (failed: {idx_fail})\n")

    # 2. MATCHED TRADES SYNC
    if args.mode in ("matched", "both"):
        print("--- Downloading Traded Stocks from MatchedTrades ---")
        traded_symbols = get_traded_symbols_from_excel(journal_path, watchlist_lookup, valid_symbols, aliases)
        print(f"  Found {len(traded_symbols)} unique traded symbols.\n")

        success_count = 0
        fail_count = 0
        for idx, symbol in enumerate(sorted(traded_symbols), 1):
            out_file = output_dir / f"{symbol}.csv"
            sec_file = bin_output_dir / f"{symbol}.csv" if bin_output_dir.parent.exists() else None
            print(f"  [{idx:2d}/{len(traded_symbols):2d}] {symbol:<20} ...", end=" ", flush=True)
            ok = download_symbol(symbol, out_file, sec_file, args.start, args.end)
            if ok:
                print("OK")
                success_count += 1
            else:
                print("EMPTY/FAILED")
                fail_count += 1
            time.sleep(args.delay)
        print(f"  Traded stocks updated: {success_count} / {len(traded_symbols)} (failed: {fail_count})\n")

    # 3. CUSTOM SYMBOLS SYNC
    if args.mode == "custom":
        if not args.symbols.strip():
            print("Error: No symbols provided for custom mode. Use --symbols 'SYM1, SYM2'.")
            return 1

        raw_list = [s.strip() for s in args.symbols.split(",") if s.strip()]
        resolved_symbols = [resolve_symbol(s, watchlist_lookup, valid_symbols, aliases) for s in raw_list]
        print(f"--- Downloading {len(resolved_symbols)} Custom Stocks ---")

        success_count = 0
        fail_count = 0
        for idx, symbol in enumerate(resolved_symbols, 1):
            out_file = output_dir / f"{symbol}.csv"
            sec_file = bin_output_dir / f"{symbol}.csv" if bin_output_dir.parent.exists() else None
            print(f"  [{idx:2d}/{len(resolved_symbols):2d}] {symbol:<20} ...", end=" ", flush=True)
            ok = download_symbol(symbol, out_file, sec_file, args.start, args.end)
            if ok:
                print("OK")
                success_count += 1
            else:
                print("EMPTY/FAILED")
                fail_count += 1
            time.sleep(args.delay)
        print(f"  Custom stocks updated: {success_count} / {len(resolved_symbols)} (failed: {fail_count})\n")

    # 4. ALL STOCKS (NIFTY 500 UNIVERSE) SYNC
    if args.mode == "all":
        print(f"--- Downloading All Stocks from {watchlist_path.name} ---")
        with watchlist_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            universe = []
            for row in reader:
                sym = (row.get("Symbol") or "").strip().upper()
                if sym:
                    universe.append(f"{sym}.NS")

        print(f"  Found {len(universe)} universe symbols.\n")
        success_count = 0
        fail_count = 0
        for idx, symbol in enumerate(universe, 1):
            out_file = output_dir / f"{symbol}.csv"
            sec_file = bin_output_dir / f"{symbol}.csv" if bin_output_dir.parent.exists() else None
            print(f"  [{idx:3d}/{len(universe):3d}] {symbol:<20} ...", end=" ", flush=True)
            ok = download_symbol(symbol, out_file, sec_file, args.start, args.end)
            if ok:
                print("OK")
                success_count += 1
            else:
                print("EMPTY/FAILED")
                fail_count += 1
            time.sleep(args.delay)
        print(f"  Universe stocks updated: {success_count} / {len(universe)} (failed: {fail_count})\n")

    print("==================================================")
    print("SYNC COMPLETE!")
    print("==================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
