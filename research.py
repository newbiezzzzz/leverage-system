import requests
from datetime import datetime, timezone

print("=" * 60)
print("LEVERAGE MARKET DATA WORKER")
print("=" * 60)

url = "https://api.coingecko.com/api/v3/simple/price"

params = {
    "ids": "bitcoin",
    "vs_currencies": "usd"
}

response = requests.get(url, params=params, timeout=30)

if response.status_code != 200:
    raise RuntimeError(
        f"Market data request failed: {response.status_code}"
    )

data = response.json()
price = data["bitcoin"]["usd"]

print("Worker status: ONLINE")
print("Time:", datetime.now(timezone.utc).isoformat())
print("BTC price:", f"${price:,.2f}")
print("Data source: CoinGecko")
print("Capital deployed: RM0")

print("=" * 60)
print("Market data retrieved successfully.")
print("=" * 60)
