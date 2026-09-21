import argparse
import csv
import sys
import time
from pathlib import Path

try:
    import yfinance as yf
except ImportError:
    print("Missing dependency: yfinance")
    print("Install with: py -m pip install yfinance pandas")
    sys.exit(1)


def read_watchlist(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    instruments: list[dict[str, str]] = []

    for row in rows:
        symbol = (row.get("Symbol") or "").strip().upper()
        if not symbol:
            continue

        instruments.append(
            {
                "symbol": symbol,
                "yahoo_symbol": (row.get("YahooSymbol") or f"{symbol}.NS").strip().upper(),
                "name": (row.get("Company Name") or row.get("Name") or "").strip(),
            }
        )

    return instruments


def write_empty_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])


def download_symbol(yahoo_symbol: str, output_path: Path, start: str, end: str) -> bool:
    data = yf.download(
        yahoo_symbol,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=False,
        progress=False,
        threads=False,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if data.empty:
        write_empty_file(output_path)
        return False

    if isinstance(data.columns, type(data.index)):
        data.columns = [str(c) for c in data.columns]

    data = data.reset_index()

    columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
    data = data[columns]
    data["Date"] = data["Date"].dt.strftime("%Y-%m-%d")
    data.to_csv(output_path, index=False)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Download Yahoo Finance daily candles into local CSV cache.")
    parser.add_argument("--watchlist", default="Data/Watchlists/nifty500.csv")
    parser.add_argument("--output", default="Data/Historical/Yahoo")
    parser.add_argument("--start", default="2019-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--limit", type=int, default=0, help="Optional max symbols for a test run.")
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between symbols in seconds.")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parents[1]
    watchlist_path = project_dir / args.watchlist
    output_dir = project_dir / args.output

    if not watchlist_path.exists():
        print(f"Watchlist not found: {watchlist_path}")
        return 1

    instruments = read_watchlist(watchlist_path)
    if args.limit > 0:
        instruments = instruments[: args.limit]

    print(f"Downloading {len(instruments)} symbols from Yahoo Finance...")
    print(f"Output: {output_dir}")

    ok = 0
    failed = 0

    for index, instrument in enumerate(instruments, start=1):
        yahoo_symbol = instrument["yahoo_symbol"]
        output_path = output_dir / f"{yahoo_symbol}.csv"

        try:
            has_data = download_symbol(yahoo_symbol, output_path, args.start, args.end)
            if has_data:
                ok += 1
                print(f"[{index}/{len(instruments)}] OK     {yahoo_symbol}")
            else:
                failed += 1
                print(f"[{index}/{len(instruments)}] EMPTY  {yahoo_symbol}")
        except Exception as ex:
            failed += 1
            write_empty_file(output_path)
            print(f"[{index}/{len(instruments)}] FAILED {yahoo_symbol}: {ex}")

        if args.delay > 0:
            time.sleep(args.delay)

    print(f"Done. OK: {ok} | Empty/failed: {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
