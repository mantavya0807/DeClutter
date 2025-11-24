import requests
import json
import base64

# 1. Define the API Endpoint
url = "http://localhost:3003/api/listings/create"

# 2. Create a dummy 1x1 pixel red image (Base64 encoded)
# This avoids needing a real file on disk for the test
dummy_image_b64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAMCAgMCAgMDAwMEAwMEBQgFBQQEBQoHBwYIDAoMDAsKCwsNDhIQDQ4RDgsLEBYQERMUFRUVDA8XGBYUGBIUFRT/2wBDAQMEBAUEBQkFBQkUDQsNFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBT/wAARCAABAAEDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD9U6KKKAP/2Q=="

# 3. Construct the Payload
payload = {
    "product": {
        "name": "Logitech MX Master 3 Wireless Mouse",
        "condition": "used",
        "category": "Electronics",  # This will trigger the Gemini category search
        "description": "Great condition mouse, ergonomic design. Comes with USB receiver.",
        "price": 65.00
    },
    "pricing_data": {
        "comps": [
            {"price": 60.00, "condition": "used", "platform": "ebay"},
            {"price": 75.00, "condition": "like_new", "platform": "facebook"},
            {"price": 55.00, "condition": "fair", "platform": "ebay"}
        ]
    },
    "platforms": ["facebook"],  # Only testing Facebook for now
    "images": [dummy_image_b64]
}

print("🚀 Sending mock request to Marketplace API...")
print(f"Target: {url}")
print(f"Product: {payload['product']['name']}")

try:
    response = requests.post(url, json=payload)
    
    print(f"\nStatus Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2))

except requests.exceptions.ConnectionError:
    print("\n❌ Could not connect to the server.")
    print("Make sure 'python apps/api/listing.py' is running in another terminal!")
