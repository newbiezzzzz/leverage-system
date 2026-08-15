import os
import requests

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

print("HTTP status:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise RuntimeError("Gemini request failed")

data = response.json()

text = data["candidates"][0]["content"]["parts"][0]["text"]

print("Gemini response:")
print(text)
