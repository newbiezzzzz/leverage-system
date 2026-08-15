import os
import requests

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY missing")

url = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-2.5-flash:generateContent"
)

payload = {
    "contents": [
        {
            "parts": [
                {
                    "text": "Reply with exactly: GEMINI WORKER ONLINE"
                }
            ]
        }
    ]
}

response = requests.post(
    url,
    headers={
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    },
    json=payload,
    timeout=60
)

if response.status_code != 200:
    print("GEMINI CONNECTION FAILED")
    print("HTTP STATUS:", response.status_code)
    print(response.text)
    raise SystemExit(1)

data = response.json()

answer = data["candidates"][0]["content"]["parts"][0]["text"].strip()

if "GEMINI WORKER ONLINE" not in answer:
    print("GEMINI RESPONDED, BUT TEST FAILED")
    print(answer)
    raise SystemExit(1)

print("================================")
print("GEMINI WORKER ONLINE")
print("================================")
print("Cloud AI connection successful.")
