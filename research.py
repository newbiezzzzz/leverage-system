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

print("LEVERAGE RESEARCH WORKER")
print("=" * 60)

# ============================================================
# 1. GET BTC MARKET DATA
# ============================================================

url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"

params = {
    "vs_currency": "usd",
    "days": "30",
    "interval": "hourly"
}

response = requests.get(
    url,
    params=params,
    timeout=60
)

response.raise_for_status()

market = response.json()

prices = market["prices"]
volumes = market["total_volumes"]

print(f"Market observations: {len(prices)}")

# ============================================================
# 2. PREPARE PRICE DATA
# ============================================================

price_values = [item[1] for item in prices]
volume_values = [item[1] for item in volumes]

returns = []

for i in range(1, len(price_values)):
    previous_price = price_values[i - 1]
    current_price = price_values[i]

    hourly_return = (current_price / previous_price) - 1

    returns.append(hourly_return)

# ============================================================
# 3. BASIC STATISTICS
# ============================================================

average_return = statistics.mean(returns)

volatility = (
    statistics.stdev(returns)
    if len(returns) > 1
    else 0
)

positive_hours = sum(
    1 for r in returns
    if r > 0
)

negative_hours = sum(
    1 for r in returns
    if r < 0
)

largest_gain = max(returns)
largest_loss = min(returns)

# ============================================================
# 4. LARGE PRICE MOVEMENTS
# ============================================================

large_events = []

for i, hourly_return in enumerate(returns):

    if abs(hourly_return) >= 0.005:

        large_events.append({
            "hour_index": i + 1,
            "return": hourly_return,
            "price": price_values[i + 1]
        })

# ============================================================
# 5. CREATE RESEARCH DATA
# ============================================================

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
{positive_hours}

NEGATIVE HOURS:
{negative_hours}

LARGEST HOURLY GAIN:
{largest_gain:.4%}

LARGEST HOURLY LOSS:
{largest_loss:.4%}

LARGE MOVEMENT EVENTS (>= 0.5% hourly):
{len(large_events)}

RECENT LARGE EVENTS:
{large_events[-15:]}
"""

print()
print("STATISTICS")
print("=" * 60)
print(research_data)

# ============================================================
# 6. SEND RESEARCH TO GEMINI
# ============================================================

prompt = f"""
You are the AI research analyst for Project Leverage.

Your job is NOT to blindly recommend trades.

Analyze the evidence objectively.

IMPORTANT RULES:

1. Do not claim a profitable strategy exists unless the data
   actually demonstrates it.
2. Do not invent statistics or missing information.
3. Clearly separate FACTS from HYPOTHESES.
4. Identify weaknesses and possible biases.
5. Do not recommend risking real money.
6. Suggest the next experiment that would produce stronger evidence.
7. Look for useful patterns that could potentially be automated.
8. Remember that trading is a vehicle, not the final destination.
9. Consider whether the technology could be reused for other
   income-generating opportunities.

MARKET RESEARCH DATA:

{research_data}

Produce a concise research report using exactly these sections:

1. EXECUTIVE SUMMARY

2. WHAT THE DATA SHOWS

3. INTERESTING PATTERNS

4. WHAT WE CANNOT CONCLUDE

5. POSSIBLE RESEARCH HYPOTHESES

6. NEXT EXPERIMENT

7. NON-TRADING OPPORTUNITIES

8. RESEARCHER CONFIDENCE

For the confidence section, explain whether the current evidence
is weak, moderate, or strong and why.
"""

gemini_url = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-3.6-flash:generateContent"
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

print()
print("GEMINI HTTP STATUS:", gemini_response.status_code)

if gemini_response.status_code != 200:

    print("GEMINI API ERROR:")
    print(gemini_response.text)

    raise RuntimeError(
        "Gemini API request failed"
    )

result = gemini_response.json()

# ============================================================
# 7. EXTRACT AI RESPONSE
# ============================================================

try:

    analysis = (
        result["candidates"][0]
        ["content"]
        ["parts"][0]
        ["text"]
    )

except (KeyError, IndexError, TypeError):

    print("Unexpected Gemini response:")
    print(result)

    raise RuntimeError(
        "Could not extract Gemini response"
    )

# ============================================================
# 8. CREATE FINAL REPORT
# ============================================================

timestamp = datetime.now(
    timezone.utc
).isoformat()

report = f"""# LEVERAGE RESEARCH REPORT

Generated:
{timestamp}

---

## MARKET RESEARCH

{research_data}

---

# AI ANALYSIS

{analysis}

---

# SYSTEM STATUS

Market data: SUCCESS
Statistics: SUCCESS
AI analysis: SUCCESS

Capital deployed: RM0

---

Generated automatically by the
Leverage Research Worker.
"""

with open(
    "market_report.md",
    "w",
    encoding="utf-8"
) as report_file:

    report_file.write(report)

# ============================================================
# 9. PRINT RESULT
# ============================================================

print()
print("=" * 60)
print("RESEARCH COMPLETE")
print("=" * 60)

print("AI analysis generated successfully.")

print()
print("Report saved as:")
print("market_report.md")

print()
print("LEVERAGE WORKER STATUS: ONLINE")
