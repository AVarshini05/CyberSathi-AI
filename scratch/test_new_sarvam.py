import httpx
import sys

api_key = "sk_b2r56ako_FxUTdxeYm8Sod172sd0ZWE8e"

payload = {
    "text": "Hello, this is a test of the new Sarvam key.",
    "target_language_code": "en-IN",
    "speaker": "ritu",
    "model": "bulbul:v3",
    "sample_rate": 24000,
    "output_audio_format": "wav",
}

headers = {
    "api-subscription-key": api_key,
    "Content-Type": "application/json"
}

url = "https://api.sarvam.ai/text-to-speech"

try:
    print("Testing new Sarvam key...")
    res = httpx.post(url, headers=headers, json=payload, timeout=15.0)
    print("Status Code:", res.status_code)
    print("Response text:", res.text)
except Exception as e:
    print("Error calling Sarvam:", e)
