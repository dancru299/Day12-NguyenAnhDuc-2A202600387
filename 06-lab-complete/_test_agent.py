"""Test TravelBuddy Agent — gọi thật qua API"""
import requests
import json

BASE = "http://localhost:8010"
API_KEY = "dev-key-change-me-in-production"
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# 1. Health
print("=" * 60)
print("HEALTH CHECK")
print("=" * 60)
r = requests.get(f"{BASE}/health")
print(json.dumps(r.json(), indent=2, ensure_ascii=False))

# 2. Auth test - no key
print("\n" + "=" * 60)
print("AUTH TEST - NO KEY (expect 401)")
print("=" * 60)
r = requests.post(f"{BASE}/ask", json={"question": "hello"})
print(f"Status: {r.status_code}")

# 3. Real question - TravelBuddy
print("\n" + "=" * 60)
print("REAL QUESTION — GPT-4o-mini + LangGraph Tools")
print("=" * 60)
r = requests.post(f"{BASE}/ask",
    headers=HEADERS,
    json={"question": "Tìm chuyến bay từ Hà Nội đến Đà Nẵng, ngân sách 5 triệu cho 2 đêm"})
print(f"Status: {r.status_code}")
data = r.json()
print(json.dumps(data, indent=2, ensure_ascii=False))

# 4. Another question
print("\n" + "=" * 60)
print("FOLLOW-UP QUESTION")
print("=" * 60)
r = requests.post(f"{BASE}/ask",
    headers=HEADERS,
    json={"question": "Tìm khách sạn ở Phú Quốc dưới 1 triệu/đêm"})
print(f"Status: {r.status_code}")
data = r.json()
print(json.dumps(data, indent=2, ensure_ascii=False))
