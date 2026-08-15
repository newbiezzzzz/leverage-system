import os
import requests

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing")

url = "https://generativelanguage.googleapis.com/v1beta/models"

response = requests.get(
    url,
    headers={
        "x-goog-api-key": api_key
    },
    timeout=60
)

print("HTTP STATUS:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise RuntimeError("Could not retrieve Gemini models")

data = response.json()

print("\nAVAILABLE GEMINI MODELS")
print("=" * 60)

for model in data.get("models", []):
    name = model.get("name", "")
    methods = model.get("supportedGenerationMethods", [])

    if "generateContent" in methods:
        print(name)
