# Strom Project

Energy price scraper for web.dynatarif.de (Flutter CanvasKit web app by EnergieDock GmbH).

## Key Architecture
- **No Playwright needed** — direct API calls via urllib (stdlib only)
- **API**: `api.dynatarif.de` — REST with JWT auth (OAuth2 password grant)
- **Auth**: POST `/tokens/` with form data `grant_type=password&username=...&password=...`
- **Prices**: GET `/tariffs/prognosis?timezone=Europe/Berlin&page_size=200&sort=valid_from:asc&filters=...&contract_id=...`
- **User data**: GET `/users/me/` returns contracts with contract_id
- **Contract ID**: `26010063`, email: `mail@joachim-breitner.de`
- **Price format**: 15-min intervals, `price_ct_kwh` field, timestamps in ISO format with tz offset

## How the API was discovered
Claude used Playwright to automate the Flutter CanvasKit UI and intercepted network responses
to discover the API. See initial commit `03e1c3b` for the Playwright-based version with
Flutter tab-order navigation and network interception details.

## Nix Setup
- `flake.nix` with just Python 3.12 (no extra packages needed)
- Run via: `nix develop --command python strom.py`
