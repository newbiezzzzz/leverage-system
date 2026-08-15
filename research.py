import os
import requests
import statistics
from datetime import datetime, timezone

# ============================================================
# LEVERAGE RESEARCH WORKER
# ============================================================

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY is missing")

# ------------------------------------------------------------
# 1. GET MARKET DATA
# ------------------------------------------------------------

print("LEVERAGE RESEARCH WORKER")
print("=" * 60)

url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"

params = {
    "vs_currency": "usd",
    "days": "30",
    "interval": "hourly"
}

response = requests.get(url, params=params, timeout=60)
response.raise_for_status()

market = response.json()

prices = market["prices"]
volumes = market["total_volumes"]

print(f"Market observations: {len(prices)}")

# ------------------------------------------------------------
# 2. PREPARE DATA
# ------------------------------------------------------------

price_values = [x[1] for x in prices]
volume_values = [x[1] for x in volumes]

returns = []

for i in range(1, len(price_values)):
    previous = price_values[i - 1]
    current = price_values[i]

    r = (current / previous) - 1
    returns.append(r)

# ------------------------------------------------------------
# 3. BASIC STATISTICS
# ------------------------------------------------------------

average_return = statistics.mean(returns)

volatility = statistics.stdev(returns) if len(returns) > 1 else 0

positive = sum(1 for r in returns if r > 0)
negative = sum(1 for r in returns if r < 0)

largest_gain = max(returns)
largest_loss = min(returns)

# ------------------------------------------------------------
# 4. IDENTIFY LARGE MOVEMENTS
# ------------------------------------------------------------

large_events = []

for i, r in enumerate(returns):

    if abs(r) >= 0.005:

        large_events.append({
            "hour_index": i + 1,
            "return": r,
            "price": price_values[i + 1]
        })

# ------------------------------------------------------------
# 5. BUILD EVIDENCE FOR AI
# ------------------------------------------------------------

research_data = f"""
PROJECT: LEVERAGE

ASSET:
Bitcoin (BTC)

DATA PERIOD:
30 days

OBSERVATIONS:
{len(price_values)}

AVERAGE HOURLY RETURN:
{average_return:.6f}

HOURLY VOLATILITY:
{volatility:.6f}

POSITIVE HOURS:
{positive}

NEGATIVE HOURS:
{negative}

LARGEST HOURLY GAIN:
{largest_gain:.4%}

LARGEST HOURLY LOSS:
{largest_loss:.4%}

LARGE MOVEMENT EVENTS (>= 0.5% hourly):
{len(large_events)}

RECENT LARGE EVENTS:
{large_events[-15:]}
"""

print("\nSTATISTICS")
print("=" * 60)
print(research_data)

# ------------------------------------------------------------
# 6. ASK GEMINI TO ANALYZE THE EVIDENCE
# ------------------------------------------------------------

prompt = f"""
You are the research analyst for Project Leverage.

IMPORTANT RULES:

1. Do NOT claim that a profitable trading strategy exists.
2. Do NOT invent data.
3. Distinguish facts from hypotheses.
4. Identify weaknesses in the evidence.
5. Suggest the NEXT experiment we should run.
6. Remember that trading is only one possible vehicle.
7. The ultimate objective is to discover technology-assisted
   opportunities that could potentially create income.

Analyze this market research:

{research_data}

Produce a concise report with these sections:

1. EXECUTIVE SUMMARY
2. WHAT THE DATA SHOWS
3. INTERESTING PATTERNS
4. WHAT WE CANNOT CONCLUDE
5. POSSIBLE RESEARCH HYPOTHESES
6. NEXT EXPERIMENT
7. NON-TRADING OPPORTUNITIES SUGGESTED BY THIS RESEARCH
"""

gemini_url = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": prompt
                }
            ]
        }
    ]
}

gemini_response = requests.post(
    gemini_url,
    headers={
        "Content-Type": "application/json",
        "x-goog-api-key": API_KEY
    },
    json=payload,
    timeout=120
)

gemini_response.raise_for_status()

result = gemini_response.json()

analysis = result["candidates"][0]["content"]["parts"][0]["text"]

# ------------------------------------------------------------
# 7. CREATE FINAL REPORT
# ------------------------------------------------------------

timestamp = datetime.now(timezone.utc).isoformat()

report = f"""
# LEVERAGE RESEARCH REPORT

Generated:
{timestamp}

---

## RAW RESEARCH DATA

{research_data}

---

## AI ANALYSIS

{analysis}

---

## SYSTEM STATUS

Market data: SUCCESS
Statistics: SUCCESS
AI analysis: SUCCESS

Capital deployed: RM0

---

Generated automatically by the Leverage Research Worker.
"""

with open("market_report.md", "w", encoding="utf-8") as f:
    f.write(report)

print("\n" + "=" * 60)
print("RESEARCH COMPLETE")
print("=" * 60)
print("AI analysis generated successfully.")
print("Report saved as market_report.md")
