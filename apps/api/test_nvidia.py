"""Direct test with lower max_tokens"""
import httpx
import json
import time

API_KEY = "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"
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "moonshotai/kimi-k2.5"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

# Test with moderate max_tokens and a real question
payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "You are a helpful UPSC study assistant. Be concise."},
        {"role": "user", "content": "What is Article 21 of Indian Constitution? Brief answer."},
    ],
    "max_tokens": 1024,
    "temperature": 0.7,
    "stream": False,
}

print("Test: max_tokens=1024, real question...")
start = time.time()
r = httpx.post(f"{BASE_URL}/chat/completions", headers=headers, json=payload, timeout=120)
elapsed = time.time() - start
print(f"Status: {r.status_code} ({elapsed:.1f}s)")

data = r.json()
choices = data.get("choices", [])
if choices:
    msg = choices[0].get("message", {})
    content = msg.get("content")
    reasoning = msg.get("reasoning_content", "")
    finish = choices[0].get("finish_reason")
    print(f"finish_reason: {finish}")
    print(f"content: {repr(content)}")
    print(f"reasoning_content ({len(reasoning)} chars): {reasoning[:300]}")
    
    # The actual answer
    answer = content if content else reasoning
    print(f"\nFinal answer: {answer[:500]}")
else:
    print(f"No choices. Full: {json.dumps(data, indent=2)[:1000]}")
