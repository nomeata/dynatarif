#!/usr/bin/env python3
"""Fetch dynamic electricity prices from api.dynatarif.de."""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

EMAIL = "mail@joachim-breitner.de"
PASSWORD_FILE = Path(__file__).parent / "password"

API = "https://api.dynatarif.de"
CET = timezone(timedelta(hours=1))


def api_request(path, token=None, form_data=None):
    """Make an API request and return parsed JSON."""
    url = f"{API}{path}"
    data = urllib.parse.urlencode(form_data).encode() if form_data else None
    req = urllib.request.Request(url, data=data)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def login():
    """Authenticate and return (access_token, contract_id)."""
    password = PASSWORD_FILE.read_text().strip()
    body = api_request("/tokens/", form_data={
        "grant_type": "password",
        "username": EMAIL,
        "password": password,
    })
    token = body["access_token"]

    user = api_request("/users/me/", token=token)
    contract_id = user["contracts"][0]["contract_id"]

    return token, contract_id


def fetch_prices(token, contract_id):
    """Fetch today's + tomorrow's price data."""
    now = datetime.now(CET)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = today_start + timedelta(days=2)

    params = urllib.parse.urlencode([
        ("timezone", "Europe/Berlin"),
        ("page_size", "200"),
        ("pages_list", "false"),
        ("sort", "valid_from:asc"),
        ("filters", f"valid_from:gte:{today_start.isoformat()}"),
        ("filters", f"valid_from:lte:{tomorrow_end.isoformat()}"),
        ("contract_id", contract_id),
    ])

    body = api_request(f"/tariffs/prognosis?{params}", token=token)
    return body.get("data", [])


def parse_time(iso_str):
    return datetime.fromisoformat(iso_str)


def format_time(dt):
    return dt.strftime("%Y-%m-%d %H:%M")


def cheapest_non_overlapping(prices, window_hours):
    """Find cheapest non-overlapping windows greedily."""
    window_size = window_hours * 4  # 15-minute intervals
    if len(prices) < window_size:
        return []

    # Build all possible windows with their average price
    windows = []
    for i in range(len(prices) - window_size + 1):
        w = prices[i:i + window_size]
        avg = sum(p["price_ct_kwh"] for p in w) / len(w)
        windows.append({
            "index": i,
            "start": parse_time(w[0]["start"]),
            "end": parse_time(w[-1]["end"]),
            "avg_price_ct_kwh": round(avg, 4),
        })

    # Greedily pick cheapest non-overlapping windows
    sorted_windows = sorted(windows, key=lambda x: x["avg_price_ct_kwh"])
    selected = []
    used = set()

    for w in sorted_windows:
        indices = set(range(w["index"], w["index"] + window_size))
        if not indices & used:
            selected.append(w)
            used |= indices

    selected.sort(key=lambda x: x["start"])
    return selected


def main():
    parser = argparse.ArgumentParser(description="Fetch dynamic electricity prices")
    parser.add_argument("--window", type=int, default=3, help="Moving average window in hours (default: 3)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    print("Logging in...", file=sys.stderr)
    token, contract_id = login()

    print("Fetching prices...", file=sys.stderr)
    prices = fetch_prices(token, contract_id)

    if not prices:
        print("ERROR: No price data received", file=sys.stderr)
        sys.exit(1)

    print(f"Fetched {len(prices)} price periods", file=sys.stderr)

    if args.json:
        print(json.dumps(prices, indent=2))
        return

    # 24h average
    day_avg = sum(p["price_ct_kwh"] for p in prices) / len(prices)

    # Find current price
    now = datetime.now(CET)
    current = None
    for entry in prices:
        if parse_time(entry["start"]) <= now < parse_time(entry["end"]):
            current = entry
            break

    # Print price table
    print(f"\n{'Time':>16s}  {'ct/kWh':>8s}  {'vs avg':>7s}")
    print("-" * 36)
    for entry in prices:
        start = parse_time(entry["start"])
        price = entry["price_ct_kwh"]
        diff = price - day_avg
        marker = " <--" if entry is current else ""
        print(f"{format_time(start)}  {price:8.2f}  {diff:+7.2f}{marker}")

    print(f"\nDay average: {day_avg:.2f} ct/kWh")

    # Cheapest non-overlapping windows
    windows = cheapest_non_overlapping(prices, args.window)
    if windows:
        print(f"\n{args.window}h cheapest non-overlapping windows:")
        print(f"{'Start':>16s} — {'End':>5s}  {'avg ct/kWh':>10s}  {'vs day avg':>10s}")
        print("-" * 50)
        for w in windows:
            s = format_time(w["start"])
            e = w["end"].strftime("%H:%M")
            diff = w["avg_price_ct_kwh"] - day_avg
            print(f"{s} — {e}  {w['avg_price_ct_kwh']:10.2f}  {diff:+10.2f}")

    if current:
        diff = current["price_ct_kwh"] - day_avg
        print(f"\nNow ({now.strftime('%H:%M')}): {current['price_ct_kwh']:.2f} ct/kWh ({diff:+.2f} vs avg)")


if __name__ == "__main__":
    main()
