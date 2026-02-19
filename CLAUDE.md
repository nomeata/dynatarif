# Strom Project

Static HTML web app for viewing dynamic electricity prices from web.dynatarif.de (EnergieDock GmbH).

## Key Architecture
- **Single-file app** — `index.html` with inline CSS and JS, no build step, no dependencies
- **API**: `api.dynatarif.de` — REST with JWT auth (OAuth2 password grant), CORS fully open
- **Auth**: POST `/tokens/` with form data `grant_type=password&username=...&password=...`
- **Prices**: GET `/tariffs/prognosis?timezone=Europe/Berlin&page_size=200&sort=valid_from:asc&filters=...&contract_id=...`
- **User data**: GET `/users/me/` returns contracts with contract_id
- **Price format**: 15-min intervals, `price_ct_kwh` field, timestamps in ISO format with tz offset
- **Token storage**: JWT token + contract ID in localStorage
- **Sharing**: Token embedded in URL hash (`#token=...&contract=...`), imported on load and stripped from URL

## Features
- Login form (credentials not stored, only the JWT token)
- Horizontal bar chart with time axis (vertical), cost axis (horizontal)
- Sliding averaging window (15min–4h) via range slider
- Local minima highlighted in green
- Daily average shown as dotted vertical line
- Hover shows details, click locks selection
- Share button generates URL with embedded token

## How the API was discovered
Claude used Playwright to automate the Flutter CanvasKit UI and intercepted network responses
to discover the API. See initial commit `03e1c3b` for the Playwright-based version.

## Running locally
```
nix run nixpkgs#python3 -- -m http.server 8000
```
