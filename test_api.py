#!/usr/bin/env python3
"""Test script for Big Beautiful Screens API."""
import requests
import json

BASE_URL = "http://localhost:8000"

# Create a screen
print("Creating a new screen...")
response = requests.post(f"{BASE_URL}/api/screens")
screen = response.json()
print(f"Screen created: {json.dumps(screen, indent=2)}")

screen_id = screen["screen_id"]
api_key = screen["api_key"]

# Test 1: Single text message
print("\n--- Test 1: Single text message ---")
response = requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": api_key},
    json={"content": ["Hello, World!"]}
)
print(f"Response: {response.json()}")

# Test 2: Multiple text messages (should split screen)
print("\n--- Test 2: Two text messages ---")
response = requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": api_key},
    json={"content": ["Panel One", "Panel Two"]}
)
print(f"Response: {response.json()}")

# Test 3: Markdown content
print("\n--- Test 3: Markdown content ---")
response = requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": api_key},
    json={"content": ["# Big Heading\n\nSome **bold** text and *italic* text."]}
)
print(f"Response: {response.json()}")

# Test 4: Image
print("\n--- Test 4: Image URL ---")
response = requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": api_key},
    json={"content": ["https://picsum.photos/800/600.jpg"]}
)
print(f"Response: {response.json()}")

# Test 5: Mixed content
print("\n--- Test 5: Mixed content (text + markdown + image) ---")
response = requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": api_key},
    json={"content": [
        "Simple text",
        "# Markdown Title",
        "https://picsum.photos/400/300.jpg"
    ]}
)
print(f"Response: {response.json()}")

# Test 6: Wrong API key (should fail)
print("\n--- Test 6: Wrong API key (should fail) ---")
response = requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": "wrong_key"},
    json={"content": ["Should not work"]}
)
print(f"Response: {response.status_code} - {response.json()}")

print(f"\n\nScreen viewer URL: {BASE_URL}/screen/{screen_id}")
print(f"Open this URL in a browser to see the screen!")
