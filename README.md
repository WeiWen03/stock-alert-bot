# Stock Alert Bot

Stock Alert Bot scans a configurable list of liquid U.S. stocks and ETFs for intraday and short-term options trading candidates, then sends a mobile-friendly watchlist to Discord.

It is designed to run every U.S. trading day at **6:30 AM Pacific Time** using GitHub Actions.

## Features

- Finds high-volatility U.S. stocks from a configurable ticker list
- Ranks each symbol as `A+`, `A`, `B`, `C`, or `D`
- Marks each symbol as `Call`, `Put`, or `Watch`
- Includes ticker, price, percent change, RVOL, catalyst/headline, and risk level
- Sends results to Discord through a `DISCORD_WEBHOOK_URL` secret
- Supports manual runs with `workflow_dispatch`

## Disclaimer

This project is for informational and educational purposes only. It is not financial advice, investment advice, or a recommendation to buy or sell any security, option, or financial instrument. Options trading is risky and can result in rapid losses.

## Files

```text
main.py
requirements.txt
README.md
.github/workflows/daily-options-watchlist.yml
```

## Discord Webhook Setup

1. Open Discord.
2. Go to the server and channel where you want alerts.
3. Open channel settings.
4. Go to `Integrations`.
5. Open `Webhooks`.
6. Create a new webhook.
7. Copy the webhook URL.

Keep the webhook private. Anyone with the webhook URL can post to that channel.

## GitHub Secret Setup

1. Open your GitHub repository.
2. Go to `Settings`.
3. Go to `Secrets and variables`.
4. Open `Actions`.
5. Click `New repository secret`.
6. Name the secret:

```text
DISCORD_WEBHOOK_URL
```

7. Paste your Discord webhook URL as the value.
8. Save the secret.

## Optional GitHub Variables

You can customize tickers and result count from:

`Settings` -> `Secrets and variables` -> `Actions` -> `Variables`

Optional variable:

```text
WATCHLIST_TICKERS
```

Example:

```text
SPY,QQQ,IWM,AAPL,MSFT,NVDA,AMD,TSLA,META,AMZN,GOOGL,NFLX,AVGO,COIN,MSTR,PLTR,SMCI
```

Optional variable:

```text
MAX_RESULTS
```

Example:

```text
8
```

## Manual Local Run

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Set your webhook:

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

Run:

```bash
python main.py
```

On Windows PowerShell:

```powershell
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python main.py
```

## Manual GitHub Actions Run

1. Open the repository on GitHub.
2. Go to `Actions`.
3. Choose `Daily Options Watchlist`.
4. Click `Run workflow`.

## Schedule

GitHub Actions uses UTC, while Pacific Time changes with daylight saving time.

The workflow runs at both:

- `13:30 UTC`
- `14:30 UTC`

The job checks the current time in `America/Los_Angeles` and only sends when the local Pacific hour is `6`, so the duplicate scheduled run is skipped automatically.

GitHub scheduled workflows can be delayed by a few minutes.

## Data Notes

This project uses `yfinance`, which is convenient but not professional real-time market data. For production trading workflows, consider a paid market data provider for more reliable premarket, options, and catalyst data.
