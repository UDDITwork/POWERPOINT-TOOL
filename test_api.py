import requests
import json

url = "https://powerpoint-tool-282996737766.asia-south1.run.app/api/diagram/create"

payload = {
    "prompt": "Create a simple flowchart with Start (100), Process (200), End (300). Connect with arrows.",
    "quality": "fast"
}

print("Testing API...")
try:
    response = requests.post(url, json=payload, timeout=120)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
