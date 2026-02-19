# Strompreise

An alternative frontend for [web.dynatarif.de](https://web.dynatarif.de/), the dynamic electricity tariff portal by EnergieDock GmbH.

This is a single static HTML page that talks directly to the dynatarif API from your browser. Your email and password are sent only to `api.dynatarif.de` — never to any other server. The resulting access token is stored in your browser's local storage.

## Features

- Horizontal bar chart of 15-minute electricity prices
- Adjustable averaging window (15 min – 4 h)
- Local price minima highlighted
- Daily average displayed as reference line
- Hover/click for detailed price information
- Share access via link (embeds token in URL, no password shared)

## Usage

Open `index.html` in a browser and log in with your dynatarif credentials, or host it anywhere (e.g. GitHub Pages) — the API supports CORS from any origin.

## Disclaimer

This project is not affiliated with EnergieDock GmbH. No guarantees are made regarding correctness, availability, or continued functionality. Use at your own risk.
