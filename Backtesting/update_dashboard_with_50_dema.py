import csv
import json
import os
import re

def main():
    csv_path = r"d:\TradingSystem\Backtesting\backtest_50_dema_trades_log.csv"
    dash_path = r"d:\TradingSystem\ai-docs\Swing-Trade-Review-Dashboard.html"
    art_path = r"C:\Users\LENOVO\.gemini\antigravity\brain\62f0b1c3-2c14-4d7e-9a27-a1089182c2b6\swing_trade_review_dashboard.html"

    trades = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, 1):
            realized_r = round(float(row["RealizedR"]), 2)
            net_pnl = round(float(row["NetPnL"]), 2)
            peak_r = round(float(row["PeakR"]), 2)
            heat_r = round(float(row["HeatR"]), 2)
            exit_reason = row["ExitReason"]
            target1_hit = row["Target1Hit"].strip().lower() == "true"
            market_cap = row["MarketCap"].strip()
            symbol = row["Symbol"].strip()

            if realized_r > 0 and exit_reason != "Breakeven":
                category = "WIN"
            elif exit_reason == "Breakeven" or (-0.1 <= realized_r <= 0.05):
                category = "BREAKEVEN"
            else:
                category = "LOSS"

            trade = {
                "id": i,
                "symbol": symbol,
                "ticker": symbol,
                "marketCap": market_cap,
                "supportEMA": "50 EMA",
                "entryDate": row["EntryDate"],
                "exitDate": row["ExitDate"],
                "entryPrice": round(float(row["EntryPrice"]), 2),
                "exitPrice": round(float(row["FinalExitPrice"]), 2),
                "initialSl": round(float(row["InitialSL"]), 2),
                "quantity": int(float(row["Quantity"])),
                "netPnl": net_pnl,
                "realizedR": realized_r,
                "peakR": peak_r,
                "heatR": heat_r,
                "holdingDays": int(row["HoldingDays"]),
                "category": category,
                "exitReason": exit_reason,
                "bounceCount": int(row.get("BounceCount", 1)),
                "target1Hit": target1_hit,
                "note": f"Systematic 50 DEMA Backtest: Bounce #1. Target 1 Hit: {target1_hit}. Exit: {exit_reason}."
            }
            trades.append(trade)

    print(f"Loaded {len(trades)} trades from 50 DEMA backtest.")
    json_data = json.dumps(trades, indent=2)
    js_var_snippet = f"    const swing50BacktestTradesData = {json_data};\n"

    # HTML 50 DEMA table rows for View 2 Empirical Table
    rows_50_dema_html = '''              <!-- 50 DEMA ROWS -->
              <tr class="bg-indigo-950/20 border-t-2 border-indigo-700/40 font-sans">
                <td colspan="10" class="py-2.5 px-4 font-bold text-indigo-300 uppercase tracking-wider text-[11px] flex items-center gap-2">
                  <span>⚡</span> Swing 50 DEMA Systematic Suite (Nifty 500 &bull; 665 Trades &bull; 2018–2026)
                </td>
              </tr>
              <tr class="hover:bg-slate-900/50">
                <td class="py-3 px-4 font-bold text-slate-300">Swing 50 DEMA</td>
                <td class="py-3 px-4 text-blue-400">Large Cap (Top 100)</td>
                <td class="py-3 px-4">304 (45.7%)</td>
                <td class="py-3 px-4 text-white">38.8% (118W / 186L)</td>
                <td class="py-3 px-4 text-blue-400 font-bold">22 BE (0 Leak)</td>
                <td class="py-3 px-4 text-emerald-400 font-bold">+28.23 R</td>
                <td class="py-3 px-4">+0.09 R</td>
                <td class="py-3 px-4">1.30</td>
                <td class="py-3 px-4 text-emerald-400">+₹28,247</td>
                <td class="py-3 px-4"><span class="px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 font-sans font-bold">★★★★☆ HIGH TRADE FREQUENCY</span></td>
              </tr>
              <tr class="hover:bg-slate-900/50 bg-emerald-950/20">
                <td class="py-3 px-4 font-bold text-emerald-400">Swing 50 DEMA</td>
                <td class="py-3 px-4 font-bold text-emerald-400">Mid Cap (101-250)</td>
                <td class="py-3 px-4 font-bold">215 (32.3%)</td>
                <td class="py-3 px-4 text-emerald-400 font-bold">40.0% (86W / 129L)</td>
                <td class="py-3 px-4 text-blue-400 font-bold">24 BE (0 Leak)</td>
                <td class="py-3 px-4 text-emerald-400 font-black">+56.04 R</td>
                <td class="py-3 px-4 font-bold text-emerald-400">+0.26 R</td>
                <td class="py-3 px-4 font-bold text-emerald-400">1.67</td>
                <td class="py-3 px-4 font-black text-emerald-400">+₹56,008</td>
                <td class="py-3 px-4"><span class="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-sans font-bold">★★★★★ ALPHA DRIVER (61% TOTAL)</span></td>
              </tr>
              <tr class="hover:bg-slate-900/50">
                <td class="py-3 px-4 font-bold text-slate-300">Swing 50 DEMA</td>
                <td class="py-3 px-4 text-purple-400">Small Cap (251-500)</td>
                <td class="py-3 px-4">146 (22.0%)</td>
                <td class="py-3 px-4 text-slate-300">35.6% (52W / 94L)</td>
                <td class="py-3 px-4 text-blue-400 font-bold">13 BE (0 Leak)</td>
                <td class="py-3 px-4 text-emerald-400 font-bold">+7.65 R</td>
                <td class="py-3 px-4">+0.05 R</td>
                <td class="py-3 px-4">1.20</td>
                <td class="py-3 px-4 text-emerald-400">+₹7,641</td>
                <td class="py-3 px-4"><span class="px-2 py-0.5 rounded bg-purple-500/20 text-purple-400 font-sans font-bold">★★★☆☆ SPREAD SENSITIVE</span></td>
              </tr>
              <tr class="bg-slate-900/90 font-bold border-b-2 border-indigo-700/60">
                <td class="py-3 px-4 text-white">50 DEMA Composite</td>
                <td class="py-3 px-4 text-indigo-300">All Nifty 500 (Full)</td>
                <td class="py-3 px-4">665</td>
                <td class="py-3 px-4 text-emerald-400">38.5% (256W / 409L)</td>
                <td class="py-3 px-4 text-blue-400">59 BE</td>
                <td class="py-3 px-4 text-emerald-400 font-black">+91.92 R</td>
                <td class="py-3 px-4">+0.14 R</td>
                <td class="py-3 px-4">1.39</td>
                <td class="py-3 px-4 text-emerald-400 font-black">+₹91,895</td>
                <td class="py-3 px-4 text-indigo-300 text-xs font-sans">Full Universe High-Beta Engine</td>
              </tr>
'''

    for path in [dash_path, art_path]:
        if not os.path.exists(path):
            print(f"Skipping {path}, does not exist.")
            continue

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Insert swing50BacktestTradesData before swingBacktestTradesData if not already present
        if "const swing50BacktestTradesData =" not in content:
            target_str = "    const swingBacktestTradesData = ["
            if target_str in content:
                content = content.replace(target_str, js_var_snippet + target_str, 1)
                print(f"Inserted swing50BacktestTradesData into {path}")
            else:
                print(f"Warning: Could not find target_str in {path}")
        else:
            print(f"swing50BacktestTradesData already present in {path}")

        # 2. Add 50 DEMA rows to Empirical Breakdown Table if not present
        if "Swing 50 DEMA Systematic Suite" not in content:
            # We insert right before <!-- SECTION 3: 8.5-YEAR SYSTEMATIC NIFTY 500 BENCHMARK --> or after 200 EMA rows
            target_bench = "              <!-- SECTION 3: 8.5-YEAR SYSTEMATIC NIFTY 500 BENCHMARK -->"
            if target_bench in content:
                content = content.replace(target_bench, rows_50_dema_html + "\n" + target_bench, 1)
                print(f"Inserted 50 DEMA table rows into {path}")
            else:
                print(f"Warning: Could not find target_bench in {path}")

        # 3. Update renderMatrix logic and EMA support button logic
        old_switch_source = '''    function switchDataSource(src) {
      currentDataSource = src;
      const bAct = document.getElementById('btn-src-actual');
      const bBt = document.getElementById('btn-src-backtest');
      if (src === 'ACTUAL') {
        bAct.className = 'px-3.5 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 text-white transition shadow';
        bBt.className = 'px-3.5 py-1.5 text-xs font-bold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition';
      } else {
        bBt.className = 'px-3.5 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 text-white transition shadow';
        bAct.className = 'px-3.5 py-1.5 text-xs font-bold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition';
      }
      currentCategoryFilter = 'ALL';
      renderMatrix();
    }'''

        new_switch_source = '''    function switchDataSource(src) {
      currentDataSource = src;
      const bAct = document.getElementById('btn-src-actual');
      const bBt = document.getElementById('btn-src-backtest');
      if (src === 'ACTUAL') {
        bAct.className = 'px-3.5 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 text-white transition shadow';
        bBt.className = 'px-3.5 py-1.5 text-xs font-bold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition';
        document.getElementById('btn-ema-all').innerText = 'All (30)';
        document.getElementById('btn-ema-200').innerText = '200 EMA (29)';
        document.getElementById('btn-ema-50').innerText = '50 EMA (1)';
      } else {
        bBt.className = 'px-3.5 py-1.5 text-xs font-bold rounded-lg bg-indigo-600 text-white transition shadow';
        bAct.className = 'px-3.5 py-1.5 text-xs font-bold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition';
        document.getElementById('btn-ema-all').innerText = 'Combined (879)';
        document.getElementById('btn-ema-200').innerText = '200 EMA (214)';
        document.getElementById('btn-ema-50').innerText = '50 EMA (665)';
      }
      currentCategoryFilter = 'ALL';
      renderMatrix();
    }'''

        if old_switch_source in content:
            content = content.replace(old_switch_source, new_switch_source)
            print(f"Updated switchDataSource in {path}")

        # Update renderMatrix dataset selection for SWING BACKTEST
        old_render_swing = '''        } else {
          dataset = swingBacktestTradesData;
          heading.innerText = `Swing 200 EMA Systematic Backtest Overview (Nifty 500)`;
          subheading.innerText = `8.5-Year Aggregate Performance Breakdown across SEBI Market Cap Tiers`;
          filterBox.innerHTML = ``;
        }'''

        new_render_swing = '''        } else {
          if (currentSwingEmaFilter === '50') {
            dataset = swing50BacktestTradesData;
            heading.innerText = `Swing 50 DEMA Systematic Backtest Overview (Nifty 500)`;
            subheading.innerText = `8.5-Year Aggregate Performance Breakdown across SEBI Market Cap Tiers (665 Trades)`;
          } else if (currentSwingEmaFilter === '200') {
            dataset = swingBacktestTradesData;
            heading.innerText = `Swing 200 EMA Systematic Backtest Overview (Nifty 500)`;
            subheading.innerText = `8.5-Year Aggregate Performance Breakdown across SEBI Market Cap Tiers (214 Trades)`;
          } else {
            dataset = swing50BacktestTradesData.concat(swingBacktestTradesData);
            heading.innerText = `Swing 50 DEMA & 200 EMA Combined Backtest Overview (Nifty 500)`;
            subheading.innerText = `8.5-Year Composite Suite across SEBI Market Cap Tiers (879 Total Setups)`;
          }
          filterBox.innerHTML = ``;
        }'''

        if old_render_swing in content:
            content = content.replace(old_render_swing, new_render_swing)
            print(f"Updated renderMatrix in {path}")

        # Update stratTitle for BACKTEST
        old_strat_title = '''      if (currentDataSource === 'BACKTEST') {
        const stratTitle = currentStrategy === 'SWING' ? 'Swing 200 EMA' : 'Positional 200 WEMA';
        container.innerHTML = generateBacktestOverview(dataset, stratTitle);
        return;
      }'''

        new_strat_title = '''      if (currentDataSource === 'BACKTEST') {
        let stratTitle = 'Positional 200 WEMA';
        if (currentStrategy === 'SWING') {
          if (currentSwingEmaFilter === '50') stratTitle = 'Swing 50 DEMA (665 Trades)';
          else if (currentSwingEmaFilter === '200') stratTitle = 'Swing 200 EMA (214 Trades)';
          else stratTitle = 'Swing 50 DEMA + 200 EMA Combined (879 Trades)';
        }
        container.innerHTML = generateBacktestOverview(dataset, stratTitle);
        return;
      }'''

        if old_strat_title in content:
            content = content.replace(old_strat_title, new_strat_title)
            print(f"Updated stratTitle in {path}")

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Successfully wrote updated file {path}")

if __name__ == "__main__":
    main()
