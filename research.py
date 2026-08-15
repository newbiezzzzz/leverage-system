import os
import requests
from pathlib import Path
from datetime import datetime, timezone

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY was not provided")

url = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

headers = {
    "Content-Type": "application/json",
    "x-goog-api-key": api_key
}

payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": (
                        "You are the AI research worker for Project Leverage. "
                        "Reply with exactly: GEMINI WORKER ONLINE"
                    )
                }
            ]
        }
    ]
}

response = requests.post(
    url,
    headers=headers,
    json=payload,
    timeout=60
)

report = f"""# Leverage AI Worker Test

Time: {datetime.now(timezone.utc).isoformat()}

HTTP Status: {response.status_code}

"""

if response.status_code == 200:
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    report += f"""Gemini Response:

{text}

STATUS: GEMINI CONNECTION SUCCESSFUL
"""
else:
    report += f"""Gemini API Error:

{response.text}

STATUS: GEMINI CONNECTION FAILED
"""

Path("market_report.md").write_text(report)

print(report)

if response.status_code != 200:
    raise RuntimeError("Gemini request failed")
