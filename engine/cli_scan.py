"""
CLI Entrypoint for GitHub Actions & Local Cron:
Runs daily scan at 6:00 PM IST:
1. Loads cached data & fetches latest EOD candles
2. Runs unified scan for 50 DEMA (@ ₹1k) & 200 EMA (@ ₹2k)
3. Evaluates Gatekeeper score
4. Saves data/latest_setups.json
5. Sends formatted Telegram alert to mobile phone
"""

import os
import sys
from pathlib import Path

# Force UTF-8 encoding for Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from engine.data import load_all_candles, PARQUET_FILE, DATA_DIR
from engine.gatekeeper import compute_gatekeeper_score
from engine.scanner import export_scan_to_json, run_full_scan
from engine.telegram import format_telegram_digest, send_telegram_message


def main():
    print("==================================================")
    print("RUNNING DAILY SWING SCANNER (50 DEMA & 200 EMA)")
    print("==================================================")

    # 1. Load historical candles
    df_all = load_all_candles()
    print(f"Loaded {len(df_all):,} historical candles from Parquet.")

    # 2. Gatekeeper regime
    indices_dict = {}
    for sym in ["^NSEI", "^NSMIDCP", "^NSEBANK"]:
        sub_df = df_all[df_all["Symbol"] == sym.replace("^", "")]
        if sub_df.empty:
            sub_df = df_all[df_all["Symbol"] == sym]
        if not sub_df.empty:
            indices_dict[sym] = sub_df.sort_values("Date").reset_index(drop=True)

    gatekeeper = compute_gatekeeper_score(indices_dict)
    print(f"Gatekeeper: {gatekeeper.status} ({gatekeeper.score}/10) - {gatekeeper.headline}")

    # 3. Run full scan across both 50 DEMA and 200 EMA
    results = run_full_scan(df_all)
    print(f"Discovered {len(results)} qualifying setups.")

    # 4. Export to data/latest_setups.json
    out_json = DATA_DIR / "latest_setups.json"
    export_scan_to_json(results, out_json)
    print(f"Exported setups to {out_json}")

    # 5. Format & Send Telegram notification
    msg = format_telegram_digest(results, gatekeeper)
    sent = send_telegram_message(msg)
    if sent:
        print("Telegram alert successfully delivered to phone!")
    else:
        print("Telegram alert skipped or token not set.")

    print("==================================================")
    print("DAILY SCAN COMPLETE!")
    print("==================================================")


if __name__ == "__main__":
    main()
