import requests
from datetime import datetime, timezone
from pathlib import Path

url = "https://api.coingecko.com/api/v3/simple/price"

params = {
    "ids": "bitcoin",
    "vs_currencies": "usd"
}

response = requests.get(url, params=params, timeout=30)
response.raise_for_status()

data = response.json()
price = data["bitcoin"]["usd"]

now = datetime.now(timezone.utc)

report = f"""# Leverage Market Report

Time: {now.isoformat()}

## Market

Bitcoin: ${price:,.2f}

## System

Worker: ONLINE
Data source: CoinGecko
Capital deployed: RM0

## Status

Market data retrieved successfully.
"""

Path("market_report.md").write_text(report)

print(report)
