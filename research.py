import os

key = os.environ.get("GEMINI_API_KEY")

if not key:
    raise RuntimeError("GEMINI_API_KEY was not provided")

print("Gemini API secret is available to the worker.")
print("Key length:", len(key))
print("Key itself is NOT displayed.")
