import httpx
import json
import time

BASE = "http://localhost:8000"

# Login
login_data = {"email": "abhitha@gmail.com", "password": "Abhitha@123"}
r = httpx.post(f"{BASE}/api/v1/auth/login", json=login_data)
print(f"Login: {r.status_code}")

if r.status_code == 200:
    token = r.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 1: AI Chat (non-streaming) with longer timeout
    chat_data = {
        "question": "What is Article 21 of Indian Constitution?",
        "language": "en",
        "stream": False
    }
    print("\n--- Test 1: AI Chat (non-streaming) ---")
    start = time.time()
    try:
        r2 = httpx.post(f"{BASE}/api/v1/chat/general", json=chat_data, headers=headers, timeout=180)
        elapsed = time.time() - start
        print(f"Status: {r2.status_code} (took {elapsed:.1f}s)")
        if r2.status_code == 200:
            resp = r2.json()
            print(f"Model: {resp.get('model', 'unknown')}")
            answer = resp.get("answer", "")
            print(f"Answer ({len(answer)} chars):")
            print(answer[:500])
            print("\n==> AI CHAT WORKING!")
        else:
            print(f"Error: {r2.text[:500]}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"Failed after {elapsed:.1f}s: {e}")
    
    # Test 2: AI Chat (streaming)
    print("\n--- Test 2: AI Chat (streaming) ---")
    start = time.time()
    try:
        with httpx.stream("POST", f"{BASE}/api/v1/chat/general/stream", json=chat_data, headers=headers, timeout=180) as r3:
            print(f"Stream Status: {r3.status_code}")
            full_text = ""
            for line in r3.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk.get("content", "")
                        full_text += content
                    except:
                        pass
            elapsed = time.time() - start
            print(f"Streamed {len(full_text)} chars in {elapsed:.1f}s")
            print(f"Preview: {full_text[:300]}")
            print("\n==> STREAMING WORKING!")
    except Exception as e:
        elapsed = time.time() - start
        print(f"Failed after {elapsed:.1f}s: {e}")
else:
    print(f"Auth failed: {r.text[:300]}")
