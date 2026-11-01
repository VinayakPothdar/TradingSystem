# Watchlists

Place downloaded watchlist CSV files here.

Recommended file for the current Nifty 500 constituents:

```text
nifty500.csv
```

Expected source:

```text
NSE Nifty 500 Index -> Download List of Nifty 500 Stocks (.csv)
```

The next step is to wire `WatchlistProvider` to read this CSV instead of using the hardcoded sample list.
