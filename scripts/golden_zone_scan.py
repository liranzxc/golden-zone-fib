#!/usr/bin/env python3
"""
golden_zone_scan.py — one file, one download, both anchorings, one CSV.

Fetches the S&P 500 constituent list, pulls daily bars once, and finds names in
an established uptrend that have pulled back into the golden Fibonacci zone.

    pip install yfinance pandas numpy lxml requests
    python golden_zone_scan.py                           # both anchors -> golden_zone.csv
    python golden_zone_scan.py --out gz.csv              # same, different path
    python golden_zone_scan.py --zone 0.618 0.786        # golden pocket only
    python golden_zone_scan.py --anchor pine             # one anchoring only
    python golden_zone_scan.py --no-confirm --all        # loosen, keep near-misses
    python golden_zone_scan.py --out ''                  # print only, write nothing

Anchoring (--anchor)
--------------------
fixed
    100% = highest high of the last --lookback bars.
      0% = lowest low before it.
    The leg stays put while price retraces into it.

pine
    100% = highest high since the last confirmed pivot low.
      0% = that pivot low.
    This is what the Pine script does, and it breaks exactly when you need it:
    a deep pullback prints a new pivot low, the anchor jumps forward to it, the
    leg you cared about disappears and the retrace resets toward 0%.

both (default)
    Runs each anchoring on the same downloaded bars — one fetch, not two — and
    tags every row with an `anchor` column, so the merged CSV holds both views
    of every name and the two can be diffed directly.

Convention
----------
`retrace` is measured DOWN from the high: 61.8 means price gave back 61.8% of
the leg. On the chart that is the line the Pine script labels "38.2%", because
the script measures UP from the low.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

USER_AGENT = os.environ.get(
    "SCAN_USER_AGENT",
    "nautilus-x-scanner/1.0 (personal research script; contact: local user)",
)
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
DATAHUB = ("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
           "main/data/constituents.csv")

TF_RULES = {"1D": None, "2D": "2D", "1W": "W-FRI", "2W": "2W-FRI", "1M": "ME"}

# columns as they exist in the local `setups` df -> column name in Supabase
SB_RENAME = {"e21>e50": "e21_gt_e50", ">e200": "gt_e200",
             "b_1D": "b_1d", "b_2D": "b_2d", "b_1W": "b_1w", "b_1M": "b_1m"}


# ══════════════════════════ supabase ══════════════════════════

def push_supabase(df: "pd.DataFrame", bars: dict, bars_keep: int = 180,
                  timeframe: str = "1d") -> None:
    """Upsert the setup rows + a trailing window of OHLCV bars for every
    ticker that appears in `df`. Needs SUPABASE_URL and SUPABASE_SECRET_KEY
    (the service-role key — RLS blocks the anon key from writing)."""
    import os
    from supabase import create_client
    from dotenv import load_dotenv

    load_dotenv()  # reads variables from a .env file and sets them in os.environ

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SECRET_KEY"]
    sb = create_client(url, key)

    # Prune setups older than 7 days
    from datetime import date, timedelta
    cutoff = str(date.today() - timedelta(days=7))
    sb.table("setups").delete().lt("date", cutoff).execute()
    print(f"  supabase: deleted setups before {cutoff}", file=sys.stderr)

    setups = df.drop(columns=[c for c in df.columns if c.startswith("_")])
    setups = setups.rename(columns=SB_RENAME)
    setups["date"] = setups["date"].astype(str)
    setups["timeframe"] = timeframe
    rows = setups.to_dict(orient="records")
    for k in range(0, len(rows), 500):
        sb.table("setups").upsert(rows[k:k + 500],
                                   on_conflict="ticker,anchor,date,timeframe").execute()
    print(f"  supabase: upserted {len(rows)} setup rows [{timeframe}]", file=sys.stderr)

    tickers = sorted(setups["ticker"].unique())
    bar_rows = []
    for t in tickers:
        d = bars.get(t)
        if d is None:
            continue
        tail = d.tail(bars_keep)
        for idx, r in tail.iterrows():
            date_str = (idx.strftime("%Y-%m-%dT%H:%M")
                        if timeframe != "1d" else str(idx.date()))
            bar_rows.append({
                "ticker": t,
                "date": date_str,
                "timeframe": timeframe,
                "open": round(float(r["Open"]), 4),
                "high": round(float(r["High"]), 4),
                "low": round(float(r["Low"]), 4),
                "close": round(float(r["Close"]), 4),
                "volume": int(r["Volume"]) if "Volume" in r and pd.notna(r["Volume"]) else None,
            })
    for k in range(0, len(bar_rows), 1000):
        sb.table("bars").upsert(bar_rows[k:k + 1000],
                                 on_conflict="ticker,date,timeframe").execute()
    print(f"  supabase: upserted {len(bar_rows)} bar rows "
          f"({len(tickers)} tickers) [{timeframe}]", file=sys.stderr)


# ══════════════════════════ tickers ══════════════════════════

def http_get(url: str, timeout: int = 20) -> str:
    try:
        import requests
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except ImportError:
        from urllib.request import Request, urlopen
        with urlopen(Request(url, headers=HEADERS), timeout=timeout) as resp:
            return resp.read().decode("utf-8", "replace")


def clean_symbols(syms) -> list[str]:
    out = {str(s).strip().upper().replace(".", "-") for s in syms}
    return sorted(s for s in out if s and s != "NAN")


def sp500_tickers() -> list[str]:
    """Wikipedia first, datahub CSV as fallback. Nothing cached."""
    for name, url, parse in (
            ("wikipedia", WIKI,
             lambda t: pd.read_html(io.StringIO(t), match="Symbol")[0]["Symbol"]),
            ("datahub", DATAHUB,
             lambda t: pd.read_csv(io.StringIO(t))["Symbol"]),
    ):
        try:
            syms = clean_symbols(parse(http_get(url)))
            if syms:
                print(f"  {len(syms)} tickers from {name}", file=sys.stderr)
                return syms
        except Exception as e:                              # noqa: BLE001
            print(f"  {name} failed: {type(e).__name__}: {e}", file=sys.stderr)
    raise RuntimeError("could not fetch the S&P 500 constituent list")


def download(tickers: list[str], period: str, chunk: int = 100
             ) -> dict[str, pd.DataFrame]:
    import yfinance as yf
    out: dict[str, pd.DataFrame] = {}
    for k in range(0, len(tickers), chunk):
        batch = tickers[k:k + chunk]
        print(f"  bars {k + 1}-{k + len(batch)} of {len(tickers)}", file=sys.stderr)
        data = yf.download(batch, period=period, interval="1d", auto_adjust=False,
                           group_by="ticker", progress=False, threads=True)
        for t in batch:
            try:
                d = data[t] if isinstance(data.columns, pd.MultiIndex) else data
            except KeyError:
                continue
            d = d.dropna(subset=["Close"])
            if len(d) >= 260:
                d = d.copy()
                d.index = pd.to_datetime(d.index)
                if getattr(d.index, "tz", None) is not None:
                    d.index = d.index.tz_localize(None)
                out[t] = d
        time.sleep(0.5)
    return out


def download_4h(tickers: list[str], chunk: int = 50) -> dict[str, pd.DataFrame]:
    """Download 1h bars (2y lookback) and resample to 4h OHLCV."""
    import yfinance as yf
    out: dict[str, pd.DataFrame] = {}
    for k in range(0, len(tickers), chunk):
        batch = tickers[k:k + chunk]
        print(f"  4h bars {k + 1}-{k + len(batch)} of {len(tickers)}", file=sys.stderr)
        data = yf.download(batch, period="2y", interval="1h", auto_adjust=False,
                           group_by="ticker", progress=False, threads=True)
        for t in batch:
            try:
                d = data[t] if isinstance(data.columns, pd.MultiIndex) else data
            except KeyError:
                continue
            d = d.dropna(subset=["Close"]).copy()
            d.index = pd.to_datetime(d.index)
            if getattr(d.index, "tz", None) is not None:
                d.index = d.index.tz_localize(None)
            d4 = d.resample("4h", offset="30min").agg(
                {"Open": "first", "High": "max", "Low": "min",
                 "Close": "last", "Volume": "sum"}
            ).dropna(subset=["Close"])
            if len(d4) >= 260:
                out[t] = d4
        time.sleep(0.5)
    return out


# ══════════════════════════ indicators ══════════════════════════

def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int) -> pd.Series:
    pc = df["Close"].shift()
    hl = df["High"] - df["Low"]
    tr = pd.concat([hl, (df["High"] - pc).abs(), (df["Low"] - pc).abs()], axis=1).max(axis=1)
    tr.iloc[0] = hl.iloc[0]
    return tr.ewm(alpha=1.0 / n, adjust=False).mean()        # Wilder RMA


def last_pivot_low(low: np.ndarray, left: int, right: int):
    """ta.pivotlow: strict local min, only known `right` bars after it printed."""
    for j in range(len(low) - right - 1, left - 1, -1):
        if low[j] < low[j - left:j].min() and low[j] < low[j + 1:j + right + 1].min():
            return j
    return None


def tf_bias(daily: pd.DataFrame, tf: str, fast: int, slow: int) -> int:
    rule = TF_RULES.get(tf, tf)
    d = daily if rule is None else daily.resample(rule).agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last"}
    ).dropna(subset=["Close"])
    if len(d) < slow + 1:
        return 0
    f, s = ema(d["Close"], fast).iloc[-1], ema(d["Close"], slow).iloc[-1]
    return 1 if f > s else (-1 if f < s else 0)


# ══════════════════════════ setup ══════════════════════════

def setup(df: pd.DataFrame, a, anchor: str) -> dict | None:
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    n = len(df)
    if n < max(260, a.lookback + 2 * a.piv_len + 10):
        return None

    high, low = df["High"].to_numpy(float), df["Low"].to_numpy(float)
    close = df["Close"]
    i = n - 1
    price = float(close.iloc[-1])
    av = float(atr(df, a.atr_len).iloc[-1])
    if av <= 0:
        return None

    # --- fib anchors ---------------------------------------------------
    if anchor == "pine":
        pl = last_pivot_low(low, a.piv_len, a.piv_len)
        if pl is None or i - pl < 5:
            return None
        a0_bar, a0 = pl, float(low[pl])
        a1_bar = pl + int(np.argmax(high[pl:i + 1]))
        a1 = float(high[a1_bar])
    else:
        lb = a.lookback
        a1_bar = i - lb + 1 + int(np.argmax(high[i - lb + 1:i + 1]))
        lo_start = max(0, a1_bar - lb)
        if a1_bar - lo_start < 5:
            return None
        a0_bar = lo_start + int(np.argmin(low[lo_start:a1_bar]))
        a0 = float(low[a0_bar])
        a1 = float(high[a1_bar])

    leg = a1 - a0
    if leg <= 0:
        return None
    lvl = lambda r: a1 - leg * r                                  # noqa: E731
    bars_since_high = i - a1_bar
    retrace = (a1 - price) / leg
    deepest = (a1 - float(low[a1_bar:].min())) / leg

    # --- trend context --------------------------------------------------
    e21, e50 = ema(close, a.ema_fast), ema(close, a.ema_slow)
    e200 = ema(close, 200)
    slope_back = min(n - 1, bars_since_high + a.slope_bars)
    biases = {tf: tf_bias(df, tf, a.ema_fast, a.ema_slow) for tf in a.tfs}
    align = sum(1 for b in biases.values() if b == 1)
    score = {4: 100, 3: 65, 2: 40}.get(align, 0)
    grade = "A" if score >= 100 else "B" if score >= 65 else "C" if score >= 40 else "F"

    # --- risk -----------------------------------------------------------
    stop = (lvl(a.invalidate) - 0.25 * av) if a.stop == "struct" else price - 1.5 * av
    risk_ps = price - stop
    qty = int(np.floor(a.risk / risk_ps)) if risk_ps > 0 else 0

    up = bool(close.iloc[-1] > df["Open"].iloc[-1] and close.iloc[-1] > close.iloc[-2])
    off_low = bool(low[-1] > low[-2] and close.iloc[-1] > close.iloc[-2])
    zlo, zhi = a.zone

    return {
        "ticker": None,
        "anchor": anchor,
        "date": df.index[-1].date(),
        "price": round(price, 2),
        "leg_low": round(a0, 2),
        "leg_high": round(a1, 2),
        "leg_pct": round(leg / a0 * 100, 1),
        "leg_atr": round(leg / av, 1),
        "bars_off_high": bars_since_high,
        "retrace": round(retrace * 100, 1),
        "deepest": round(deepest * 100, 1),
        "lvl_382": round(lvl(0.382), 2),
        "lvl_500": round(lvl(0.5), 2),
        "lvl_618": round(lvl(0.618), 2),
        "lvl_786": round(lvl(0.786), 2),
        "grade": grade,
        "score": score,
        "align": f"{align}/{len(biases)}",
        **{f"b_{k}": v for k, v in biases.items()},
        "trend_ok": all(biases.get(tf, 0) == 1 for tf in a.trend_tfs),
        "e21>e50": bool(e21.iloc[-1] > e50.iloc[-1]),
        ">e200": bool(price > e200.iloc[-1]),
        "e50_up": bool(e50.iloc[-1] > e50.iloc[-slope_back]),
        "turning": up or off_low,
        "atr_pct": round(av / price * 100, 2),
        "stop": round(stop, 2),
        "stop_atr": round(risk_ps / av, 1),
        "t1": round(price + 1.382 * av, 2),
        "t2": round(price + 2.382 * av, 2),
        "qty": qty,
        "rr_to_high": round((a1 - price) / risk_ps, 2) if risk_ps > 0 else np.nan,
        "_in_zone": zlo <= retrace <= zhi,
        "_dist": abs(retrace - (zlo + zhi) / 2),
    }


def passes(r: dict, a) -> bool:
    return (
            r["_in_zone"]
            and r["trend_ok"]
            and r["e50_up"]
            and r["deepest"] <= a.max_depth * 100
            and a.min_bars <= r["bars_off_high"] <= a.max_bars
            and r["leg_atr"] >= a.min_leg_atr
            and r["leg_pct"] >= a.min_leg_pct * 100
            and r["stop_atr"] <= a.max_stop_atr
            and r["qty"] >= 1
            and r["rr_to_high"] >= a.min_rr
            and r["score"] >= a.min_score
            and (r[">e200"] or not a.require_200)
            and (r["e21>e50"] or not a.require_stack)
            and (r["turning"] or not a.confirm)
    )


# ══════════════════════════ main ══════════════════════════

def main() -> int:
    p = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="S&P 500 golden-zone pullback scanner (in-memory).")
    p.add_argument("--anchor", choices=["fixed", "pine", "both"], default="both")
    p.add_argument("--zone", nargs=2, type=float, default=[0.382, 0.618],
                   metavar=("LO", "HI"), help="retrace window, measured down from the high")
    p.add_argument("--lookback", type=int, default=120, help="bars searched for the leg")
    p.add_argument("--piv-len", type=int, default=8)
    p.add_argument("--atr-len", type=int, default=14)
    p.add_argument("--ema-fast", type=int, default=21)
    p.add_argument("--ema-slow", type=int, default=50)
    p.add_argument("--tfs", nargs="+", default=["1D", "2D", "1W", "1M"])
    p.add_argument("--trend-tfs", nargs="+", default=["1W", "1M"],
                   help="must all be bullish; the daily is red by construction here")
    p.add_argument("--min-leg-atr", type=float, default=4.0)
    p.add_argument("--min-leg-pct", type=float, default=0.10)
    p.add_argument("--min-bars", type=int, default=3)
    p.add_argument("--max-bars", type=int, default=45)
    p.add_argument("--max-depth", type=float, default=0.786)
    p.add_argument("--invalidate", type=float, default=0.786)
    p.add_argument("--stop", choices=["struct", "atr"], default="struct")
    p.add_argument("--max-stop-atr", type=float, default=4.0)
    p.add_argument("--min-rr", type=float, default=1.0, help="reward:risk back to the high")
    p.add_argument("--min-score", type=int, default=0)
    p.add_argument("--slope-bars", type=int, default=40)
    p.add_argument("--require-200", action="store_true", default=True)
    p.add_argument("--no-require-200", dest="require_200", action="store_false")
    p.add_argument("--require-stack", action="store_true", default=False)
    p.add_argument("--confirm", action="store_true", default=True)
    p.add_argument("--no-confirm", dest="confirm", action="store_false")
    p.add_argument("--risk", type=float, default=100.0)
    p.add_argument("--period", default="15y")
    p.add_argument("--min-price", type=float, default=5.0)
    p.add_argument("--min-dollar-vol", type=float, default=5e6)
    p.add_argument("--limit", type=int, default=0, help="debug: first N tickers")
    p.add_argument("--all", action="store_true", help="also show in-zone near-misses")
    p.add_argument("--out", default="golden_zone.csv",
                   help="merged CSV path; written even when empty, and includes "
                        "every in-zone row (with a pass column) when --all is set. "
                        "Pass --out '' to skip writing")
    p.add_argument("--supabase", action="store_true",
                   help="also upsert setups + trailing bars into Supabase "
                        "(needs SUPABASE_URL / SUPABASE_SECRET_KEY env vars, "
                        "pip install supabase)")
    p.add_argument("--bars-keep", type=int, default=180,
                   help="trailing daily bars to upsert per ticker, for charting")
    p.add_argument("--timeframe", choices=["1d", "4h", "both"], default="1d",
                   help="which timeframe(s) to scan and push")
    a = p.parse_args()

    anchors = ["fixed", "pine"] if a.anchor == "both" else [a.anchor]
    timeframes = ["1d", "4h"] if a.timeframe == "both" else [a.timeframe]

    tickers = sp500_tickers()
    if a.limit:
        tickers = tickers[:a.limit]
    print(f"anchor={'+'.join(anchors)} zone={a.zone[0]:.3f}-{a.zone[1]:.3f} "
          f"tfs={a.tfs} timeframe={a.timeframe}", file=sys.stderr)

    for tf in timeframes:
        print(f"\n{'═'*20} timeframe={tf} {'═'*20}", file=sys.stderr)

        if tf == "1d":
            bars = download(tickers, a.period)
        else:
            bars = download_4h(tickers)

        rows = []
        for t, d in bars.items():
            if float(d["Close"].iloc[-1]) < a.min_price:
                continue
            if "Volume" in d and float((d["Close"] * d["Volume"]).tail(20).mean()) < a.min_dollar_vol:
                continue
            for anc in anchors:
                try:
                    r = setup(d, a, anc)
                except Exception as e:                              # noqa: BLE001
                    print(f"  {t} [{anc}]: {type(e).__name__}: {e}", file=sys.stderr)
                    continue
                if r:
                    r["ticker"] = t
                    r["_pass"] = passes(r, a)
                    rows.append(r)

        if not rows:
            print(f"no usable data [{tf}]", file=sys.stderr)
            continue

        df = pd.DataFrame(rows)
        cols = ["ticker"] + [c for c in df.columns if c != "ticker" and not c.startswith("_")]

        with pd.option_context("display.width", 260, "display.max_columns", 60):
            for anc in anchors:
                sub = df[df["anchor"] == anc]
                hits = sub[sub["_pass"]].sort_values(["score", "_dist", "rr_to_high"],
                                                     ascending=[False, True, False])
                print(f"\n═══ anchor={anc} [{tf}] ═══", file=sys.stderr)
                if len(hits):
                    print(hits[cols].to_string(index=False))
                    print(f"{len(hits)} setups", file=sys.stderr)
                else:
                    print(f"no setups in the zone today [{anc}] [{tf}]", file=sys.stderr)
                if a.all:
                    near = sub[~sub["_pass"] & sub["_in_zone"]].sort_values("_dist")
                    if len(near):
                        print(f"\n--- in zone, filtered out [{anc}] [{tf}] ---")
                        print(near[cols].head(25).to_string(index=False))

            if len(anchors) > 1:
                wide = df.pivot_table(index="ticker", columns="anchor",
                                      values=["retrace", "leg_high", "leg_low"],
                                      aggfunc="first")
                disagree = df.pivot_table(index="ticker", columns="anchor",
                                          values="_pass", aggfunc="first")
                disagree = disagree[disagree["fixed"] != disagree["pine"]]
                if len(disagree):
                    print("\n--- anchors disagree on the pass ---")
                    print(wide.loc[disagree.index].to_string())

        out = df[df["_in_zone"]] if a.all else df[df["_pass"]]
        out = out.copy()
        out["pass"] = out["_pass"]
        out = out.sort_values(["anchor", "score", "_dist"], ascending=[True, False, True])

        if a.out:
            path = a.out.replace(".csv", f"_{tf}.csv") if a.timeframe == "both" else a.out
            out[cols + ["pass"]].to_csv(path, index=False)
            print(f"wrote {path} ({len(out)} rows)", file=sys.stderr)

        if a.supabase:
            push_supabase(out[cols + ["pass"]], bars, bars_keep=a.bars_keep, timeframe=tf)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())