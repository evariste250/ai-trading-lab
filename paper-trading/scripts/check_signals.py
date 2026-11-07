#!/usr/bin/env python3

import json
from pathlib import Path
import pandas as pd

HOME = Path.home()
BASE = Path(__file__).resolve().parent.parent
SIGNALS = BASE / "signals"

for signal_file in sorted(SIGNALS.glob("*.json")):
    signal = json.loads(signal_file.read_text())
    ticker = signal["ticker"]

    price_file = HOME / f".tradingagents/cache/{ticker}-YFin-data.csv"

    if not price_file.exists():
        print(f"{ticker}: no market data available")
        continue

    df = pd.read_csv(price_file)
    df = df.dropna(subset=["Close"])

    if df.empty:
        print(f"{ticker}: no valid closing price")
        continue

    row = df.iloc[-1]
    price = float(row["Close"])
    date = str(row["Date"])[:10]

    trigger = signal.get("entry_trigger")
    stop = signal.get("stop_level")

    print(f"\n{ticker}")
    print("=" * 45)
    print(f"Market date:   {date}")
    print(f"Close:         ${price:.2f}")
    print(f"AI rating:     {signal['rating']}")

    if signal["status"] == "WAITING_FOR_ENTRY":

        if trigger is not None and price > trigger:
            print(f"Entry trigger: ${trigger:.2f} PASSED")
            print("Paper action:  BUY SIGNAL")
        else:
            print(f"Entry trigger: ${trigger:.2f} NOT PASSED")
            print("Paper action:  WAIT")

    elif stop is not None and price <= stop:
        print(f"Stop level:    ${stop:.2f} BREACHED")
        print("Paper action:  EXIT SIGNAL")

    else:
        print("Paper action:  HOLD")
