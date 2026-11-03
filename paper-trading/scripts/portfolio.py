#!/usr/bin/env python3

import argparse
import csv
import json
import uuid
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PORTFOLIO_FILE = BASE_DIR / "portfolio.json"
TRADES_FILE = BASE_DIR / "trades.csv"


def load_portfolio():
    with PORTFOLIO_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_portfolio(portfolio):
    with PORTFOLIO_FILE.open("w", encoding="utf-8") as file:
        json.dump(portfolio, file, indent=2)


def append_trade(row):
    with TRADES_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(row)


def portfolio_cost(portfolio):
    return sum(
        position["quantity"] * position["average_cost"]
        for position in portfolio["positions"].values()
    )


def show_portfolio(portfolio):
    invested = portfolio_cost(portfolio)
    total_at_cost = portfolio["cash"] + invested

    print("\nPAPER PORTFOLIO")
    print("=" * 68)
    print(f"Starting cash:     ${portfolio['starting_cash']:,.2f}")
    print(f"Available cash:    ${portfolio['cash']:,.2f}")
    print(f"Invested at cost:  ${invested:,.2f}")
    print(f"Total at cost:     ${total_at_cost:,.2f}")
    print(f"Open positions:    {len(portfolio['positions'])}")
    print()

    if not portfolio["positions"]:
        print("No simulated positions yet.")
        return

    print(
        f"{'Ticker':<10}"
        f"{'Quantity':>12}"
        f"{'Avg cost':>14}"
        f"{'Cost basis':>16}"
    )
    print("-" * 68)

    for ticker, position in portfolio["positions"].items():
        cost_basis = position["quantity"] * position["average_cost"]
        print(
            f"{ticker:<10}"
            f"{position['quantity']:>12.4f}"
            f"${position['average_cost']:>13,.2f}"
            f"${cost_basis:>15,.2f}"
        )


def buy(portfolio, ticker, dollars, price, date, rating, notes):
    ticker = ticker.upper()

    if dollars <= 0 or price <= 0:
        raise ValueError("Dollars and price must both be greater than zero.")

    if ticker not in portfolio["watchlist"]:
        raise ValueError(f"{ticker} is not in the configured watchlist.")

    if dollars > portfolio["cash"]:
        raise ValueError(
            f"Insufficient simulated cash. Available: ${portfolio['cash']:,.2f}"
        )

    max_initial = (
        portfolio["starting_cash"]
        * portfolio["rules"]["maximum_initial_position_percent"]
        / 100
    )

    existing = portfolio["positions"].get(ticker)

    if existing is None and dollars > max_initial:
        raise ValueError(
            f"Initial position cannot exceed ${max_initial:,.2f}."
        )

    max_total = (
        portfolio["starting_cash"]
        * portfolio["rules"]["maximum_total_position_percent"]
        / 100
    )

    existing_value = 0.0
    if existing:
        existing_value = existing["quantity"] * existing["average_cost"]

    if existing_value + dollars > max_total:
        raise ValueError(
            f"Total cost allocation for {ticker} cannot exceed "
            f"${max_total:,.2f}."
        )

    quantity = dollars / price

    if existing:
        old_quantity = existing["quantity"]
        old_cost = old_quantity * existing["average_cost"]
        new_quantity = old_quantity + quantity
        new_average = (old_cost + dollars) / new_quantity

        existing["quantity"] = round(new_quantity, 8)
        existing["average_cost"] = round(new_average, 4)
        existing["last_action_date"] = date
    else:
        portfolio["positions"][ticker] = {
            "quantity": round(quantity, 8),
            "average_cost": round(price, 4),
            "opened_date": date,
            "last_action_date": date
        }

    portfolio["cash"] = round(portfolio["cash"] - dollars, 2)
    trade_id = str(uuid.uuid4())[:8]

    append_trade([
        trade_id,
        date,
        ticker,
        "BUY",
        f"{quantity:.8f}",
        f"{price:.4f}",
        f"{dollars:.2f}",
        f"{portfolio['cash']:.2f}",
        "TradingAgents",
        rating,
        notes
    ])

    save_portfolio(portfolio)

    print("\nSIMULATED TRADE RECORDED")
    print("=" * 68)
    print(f"Trade ID:    {trade_id}")
    print(f"Ticker:      {ticker}")
    print(f"Action:      BUY")
    print(f"Quantity:    {quantity:.8f}")
    print(f"Price:       ${price:,.2f}")
    print(f"Trade value: ${dollars:,.2f}")
    print(f"Cash left:   ${portfolio['cash']:,.2f}")
    print("No broker and no real money were used.")


def mark_to_market(portfolio, prices):
    cash = portfolio["cash"]
    market_value = 0.0

    print("\nMARK-TO-MARKET VALUATION")
    print("=" * 82)
    print(
        f"{'Ticker':<9}"
        f"{'Quantity':>12}"
        f"{'Avg cost':>13}"
        f"{'Price':>13}"
        f"{'Value':>14}"
        f"{'P/L':>14}"
    )
    print("-" * 82)

    for ticker, position in portfolio["positions"].items():
        if ticker not in prices:
            print(f"{ticker:<9} No current price supplied")
            continue

        quantity = position["quantity"]
        average_cost = position["average_cost"]
        price = prices[ticker]
        value = quantity * price
        cost = quantity * average_cost
        profit_loss = value - cost
        market_value += value

        print(
            f"{ticker:<9}"
            f"{quantity:>12.4f}"
            f"${average_cost:>12,.2f}"
            f"${price:>12,.2f}"
            f"${value:>13,.2f}"
            f"${profit_loss:>13,.2f}"
        )

    total = cash + market_value
    return_amount = total - portfolio["starting_cash"]
    return_percent = (
        return_amount / portfolio["starting_cash"] * 100
        if portfolio["starting_cash"]
        else 0
    )

    print("-" * 82)
    print(f"Cash:                 ${cash:,.2f}")
    print(f"Position market value:${market_value:,.2f}")
    print(f"Portfolio value:      ${total:,.2f}")
    print(f"Profit/loss:          ${return_amount:,.2f}")
    print(f"Return:                {return_percent:.2f}%")


def parse_prices(items):
    prices = {}

    for item in items:
        if "=" not in item:
            raise ValueError(
                f"Invalid price '{item}'. Use the format TICKER=PRICE."
            )

        ticker, price = item.split("=", 1)
        numeric_price = float(price)

        if numeric_price <= 0:
            raise ValueError("Prices must be greater than zero.")

        prices[ticker.upper()] = numeric_price

    return prices


def main():
    parser = argparse.ArgumentParser(
        description="TradingAgents paper portfolio simulator"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("show")

    buy_parser = subparsers.add_parser("buy")
    buy_parser.add_argument("ticker")
    buy_parser.add_argument("--dollars", type=float, required=True)
    buy_parser.add_argument("--price", type=float, required=True)
    buy_parser.add_argument(
        "--date",
        default=datetime.now().date().isoformat()
    )
    buy_parser.add_argument("--rating", default="UNSPECIFIED")
    buy_parser.add_argument("--notes", default="")

    mark_parser = subparsers.add_parser("mark")
    mark_parser.add_argument(
        "prices",
        nargs="+",
        help="Prices in TICKER=PRICE format"
    )

    args = parser.parse_args()
    portfolio = load_portfolio()

    if args.command == "show":
        show_portfolio(portfolio)

    elif args.command == "buy":
        buy(
            portfolio=portfolio,
            ticker=args.ticker,
            dollars=args.dollars,
            price=args.price,
            date=args.date,
            rating=args.rating,
            notes=args.notes
        )

    elif args.command == "mark":
        prices = parse_prices(args.prices)
        mark_to_market(portfolio, prices)


if __name__ == "__main__":
    main()
