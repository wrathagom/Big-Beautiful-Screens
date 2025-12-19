#!/usr/bin/env python3
"""Test script for color features."""
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

# Test 1: Default colors (no colors specified)
print("\n--- Test 1: Default (no colors) ---")
response = requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": api_key},
    json={"content": ["Hello, World!"]}
)
print(f"Response: {response.json()}")

# Test 2: Background and panel colors
print("\n--- Test 2: Background and panel colors ---")
response = requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": api_key},
    json={
        "content": ["Panel 1", "Panel 2"],
        "background_color": "#0d1b2a",
        "panel_color": "#1b263b"
    }
)
print(f"Response: {response.json()}")

# Test 3: Per-panel color override
print("\n--- Test 3: Per-panel color override ---")
response = requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": api_key},
    json={
        "content": [
            {"type": "text", "value": "Default color"},
            {"type": "text", "value": "Red panel", "color": "#c0392b"},
            {"type": "text", "value": "Green panel", "color": "#27ae60"}
        ],
        "background_color": "#1a1a2e",
        "panel_color": "#16213e"
    }
)
print(f"Response: {response.json()}")

# Test 4: Mixed content with colors
print("\n--- Test 4: Mixed content with colors ---")
response = requests.post(
    f"{BASE_URL}/api/screens/{screen_id}/message",
    headers={"X-API-Key": api_key},
    json={
        "content": [
            "Auto-detected text",
            {"type": "markdown", "value": "# Heading\nWith **bold**", "color": "#2980b9"},
            "https://picsum.photos/400/300.jpg"
        ],
        "background_color": "#2c3e50"
    }
)
print(f"Response: {response.json()}")

print(f"\n\nScreen viewer URL: {BASE_URL}/screen/{screen_id}")
print(f"Admin page: {BASE_URL}/admin/screens")
print(f"Open these URLs in a browser to see the results!")
