"""Market data fetching via yfinance."""
from __future__ import annotations

import logging
from typing import Any

import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_market_data(config: dict[str, Any]) -> dict[str, Any]:
    """
    Fetch market data for indices, watchlist tickers, and sector ETFs.

    Uses yfinance bulk download with fallback to individual Ticker queries.

    Returns:
        Dict with 'indices', 'watchlist', 'sectors' keys containing price data.
    """
    watchlist_cfg = config.get("watchlist", {})

    # Collect all symbols
    all_symbols: list[str] = []
    symbol_names: dict[str, str] = {}

    # Indices (nested by region)
    indices_cfg = watchlist_cfg.get("indices", {})
    for region, items in indices_cfg.items():
        for item in items:
            sym = item.get("symbol", "")
            if sym:
                all_symbols.append(sym)
                symbol_names[sym] = item.get("name", sym)

    # Watchlist tickers
    for item in watchlist_cfg.get("tickers", []):
        sym = item.get("symbol", "")
        if sym:
            all_symbols.append(sym)
            symbol_names[sym] = item.get("name", sym)

    # Sector ETFs
    for item in watchlist_cfg.get("sector_etfs", []):
        sym = item.get("symbol", "")
        if sym:
            all_symbols.append(sym)
            symbol_names[sym] = item.get("name", sym)

    if not all_symbols:
        logger.warning("No symbols configured in watchlist")
        return {"indices": {}, "watchlist": [], "sectors": []}

    # Fetch data via bulk download
    prices = _fetch_bulk(all_symbols)

    # Fallback for failed symbols
    failed = [s for s in all_symbols if s not in prices]
    if failed:
        logger.info(f"Retrying {len(failed)} failed symbols individually")
        for sym in failed:
            result = _fetch_single(sym)
            if result:
                prices[sym] = result

    # Build response structures
    result: dict[str, Any] = {
        "indices": {},
        "watchlist": [],
        "sectors": [],
    }

    # Indices grouped by region
    for region, items in indices_cfg.items():
        result["indices"][region] = []
        for item in items:
            sym = item.get("symbol", "")
            if sym in prices:
                result["indices"][region].append({
                    "symbol": sym,
                    "name": symbol_names.get(sym, sym),
                    **prices[sym],
                })

    # Watchlist
    for item in watchlist_cfg.get("tickers", []):
        sym = item.get("symbol", "")
        if sym in prices:
            result["watchlist"].append({
                "symbol": sym,
                "name": symbol_names.get(sym, sym),
                **prices[sym],
            })

    # Sectors
    for item in watchlist_cfg.get("sector_etfs", []):
        sym = item.get("symbol", "")
        if sym in prices:
            result["sectors"].append({
                "symbol": sym,
                "name": symbol_names.get(sym, sym),
                **prices[sym],
            })

    logger.info(
        f"Fetched market data: {sum(len(v) for v in result['indices'].values())} indices, "
        f"{len(result['watchlist'])} watchlist, {len(result['sectors'])} sectors"
    )

    return result


def _fetch_bulk(symbols: list[str]) -> dict[str, dict[str, Any]]:
    """
    Fetch price data for multiple symbols using yf.download.

    Returns dict mapping symbol to {price, change_pct}.
    """
    prices: dict[str, dict[str, Any]] = {}

    try:
        # Download 5 days of daily data
        data = yf.download(
            symbols,
            period="5d",
            interval="1d",
            progress=False,
            threads=True,
            group_by="ticker",
        )

        if data.empty:
            logger.warning("Bulk download returned empty data")
            return prices

        # Handle single vs multiple symbols (yfinance returns different structures)
        if len(symbols) == 1:
            sym = symbols[0]
            close_col = data.get("Close")
            if close_col is not None and len(close_col.dropna()) >= 2:
                closes = close_col.dropna()
                last_price = float(closes.iloc[-1])
                prev_price = float(closes.iloc[-2])
                change_pct = ((last_price - prev_price) / prev_price) * 100
                prices[sym] = {
                    "price": last_price,
                    "change_pct": round(change_pct, 2),
                }
        else:
            for sym in symbols:
                try:
                    if sym not in data.columns.get_level_values(0):
                        continue
                    close_col = data[sym].get("Close")
                    if close_col is None:
                        continue
                    closes = close_col.dropna()
                    if len(closes) < 2:
                        continue
                    last_price = float(closes.iloc[-1])
                    prev_price = float(closes.iloc[-2])
                    change_pct = ((last_price - prev_price) / prev_price) * 100
                    prices[sym] = {
                        "price": last_price,
                        "change_pct": round(change_pct, 2),
                    }
                except Exception as e:
                    logger.warning(f"Failed to parse bulk data for {sym}: {e}")
                    continue

    except Exception as e:
        logger.warning(f"Bulk download failed: {e}")

    return prices


def _fetch_single(symbol: str) -> dict[str, Any] | None:
    """
    Fetch price data for a single symbol using yf.Ticker.

    Returns {price, change_pct} or None on failure.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d", interval="1d")

        if hist.empty or len(hist) < 2:
            logger.warning(f"Insufficient data for {symbol}")
            return None

        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return None

        last_price = float(closes.iloc[-1])
        prev_price = float(closes.iloc[-2])
        change_pct = ((last_price - prev_price) / prev_price) * 100

        return {
            "price": last_price,
            "change_pct": round(change_pct, 2),
        }

    except Exception as e:
        logger.warning(f"Failed to fetch {symbol}: {e}")
        return None


def get_best_worst_sectors(sectors: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """
    Find the best and worst performing sectors.

    Returns (best, worst) tuple, either can be None if no data.
    """
    valid = [s for s in sectors if "change_pct" in s]
    if not valid:
        return None, None

    sorted_sectors = sorted(valid, key=lambda x: x["change_pct"], reverse=True)
    best = sorted_sectors[0] if sorted_sectors else None
    worst = sorted_sectors[-1] if sorted_sectors else None

    return best, worst
