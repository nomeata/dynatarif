#!/usr/bin/env python3
"""Scrape dynamic electricity prices from web.dynatarif.de."""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

EMAIL = "mail@joachim-breitner.de"
PASSWORD_FILE = Path(__file__).parent / "password"

CET = timezone(timedelta(hours=1))


def login_and_fetch(page):
    """Log in via the Flutter UI and capture API responses."""
    captured = []

    def handle_response(response):
        url = response.url
        content_type = response.headers.get("content-type", "")
        if "json" in content_type and "api.dynatarif.de" in url:
            try:
                body = response.json()
                captured.append({"url": url, "body": body})
            except Exception:
                pass

    page.on("response", handle_response)

    password = PASSWORD_FILE.read_text().strip()

    print("Navigating to web.dynatarif.de...", file=sys.stderr)
    page.goto("https://web.dynatarif.de/", wait_until="networkidle")
    page.wait_for_timeout(3000)

    # Tab to focus email field (Flutter creates <input> on focus)
    print("Logging in...", file=sys.stderr)
    page.keyboard.press("Tab")
    page.wait_for_timeout(500)
    page.keyboard.type(EMAIL, delay=50)
    page.wait_for_timeout(300)

    # Tab to password field
    page.keyboard.press("Tab")
    page.wait_for_timeout(500)
    page.keyboard.type(password, delay=50)
    page.wait_for_timeout(300)

    # Tab from password field to LOGIN button, then press Enter
    page.keyboard.press("Tab")
    page.wait_for_timeout(300)
    page.keyboard.press("Enter")

    # Wait for price data to load
    print("Waiting for data...", file=sys.stderr)
    page.wait_for_timeout(10000)

    return captured


def fetch_all_prices(page, captured):
    """Use the captured auth token to fetch the full day's price data via the API."""
    token = None
    contract_id = None
    for resp in captured:
        if "/tokens/" in resp["url"]:
            token = resp["body"].get("access_token")
        if "/users/me/" in resp["url"]:
            contracts = resp["body"].get("contracts", [])
            if contracts:
                contract_id = contracts[0].get("contract_id")

    if not token or not contract_id:
        print("ERROR: Could not extract token or contract_id", file=sys.stderr)
        return []

    now = datetime.now(CET)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = today_start + timedelta(days=2)

    url = (
        f"https://api.dynatarif.de/tariffs/prognosis"
        f"?timezone=Europe%2FBerlin"
        f"&page_size=200"
        f"&pages_list=false"
        f"&sort=valid_from%3Aasc"
        f"&filters=valid_from%3Agte%3A{today_start.isoformat()}"
        f"&filters=valid_from%3Alte%3A{tomorrow_end.isoformat()}"
        f"&contract_id={contract_id}"
    )

    response = page.evaluate("""async (args) => {
        const resp = await fetch(args.url, {
            headers: { 'Authorization': 'Bearer ' + args.token }
        });
        return await resp.json();
    }""", {"url": url, "token": token})

    return response.get("data", [])


def parse_time(iso_str):
    """Parse an ISO timestamp string to a datetime object."""
    return datetime.fromisoformat(iso_str)


def format_time(dt):
    """Format datetime as 'YYYY-MM-DD HH:MM'."""
    return dt.strftime("%Y-%m-%d %H:%M")


def compute_moving_average(prices, window_hours):
    """Compute moving average over a window of hours."""
    window_size = window_hours * 4  # 15-minute intervals
    results = []

    for i in range(len(prices) - window_size + 1):
        window = prices[i:i + window_size]
        avg = sum(p["price_ct_kwh"] for p in window) / len(window)
        results.append({
            "start": parse_time(window[0]["start"]),
            "end": parse_time(window[-1]["end"]),
            "avg_price_ct_kwh": round(avg, 4),
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="Fetch dynamic electricity prices")
    parser.add_argument("--window", type=int, default=3, help="Moving average window in hours (default: 3)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted table")
    args = parser.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        captured = login_and_fetch(page)
        prices = fetch_all_prices(page, captured)

        browser.close()

    if not prices:
        print("ERROR: No price data received", file=sys.stderr)
        sys.exit(1)

    print(f"Fetched {len(prices)} price periods", file=sys.stderr)

    if args.json:
        print(json.dumps(prices, indent=2))
        return

    # Find current price
    now = datetime.now(CET)
    current = None
    for entry in prices:
        start = parse_time(entry["start"])
        end = parse_time(entry["end"])
        if start <= now < end:
            current = entry
            break

    # Print price table
    print(f"\n{'Time':>16s}  {'ct/kWh':>8s}")
    print("-" * 27)
    for entry in prices:
        start = parse_time(entry["start"])
        price = entry["price_ct_kwh"]
        marker = " <--" if entry is current else ""
        print(f"{format_time(start)}  {price:8.4f}{marker}")

    # Moving averages — cheapest windows
    averages = compute_moving_average(prices, args.window)
    if averages:
        sorted_avgs = sorted(averages, key=lambda x: x["avg_price_ct_kwh"])

        print(f"\n{args.window}h cheapest windows:")
        print(f"{'Start':>16s}  {'End':>5s}  {'avg ct/kWh':>10s}")
        print("-" * 36)
        for entry in sorted_avgs[:5]:
            s = format_time(entry["start"])
            e = entry["end"].strftime("%H:%M")
            print(f"{s}  {e:>5s}  {entry['avg_price_ct_kwh']:10.4f}")

    if current:
        print(f"\nNow ({now.strftime('%H:%M')}): {current['price_ct_kwh']:.2f} ct/kWh")


if __name__ == "__main__":
    main()
