import asyncio, httpx, json, time

async def test():
    r = httpx.post('http://localhost:8000/api/v1/auth/login', json={'email':'abhitha@gmail.com','password':'Abhitha@123'})
    token = r.json()['tokens']['access_token']
    print('Auth OK')

    print('Sending stream request...')
    t0 = time.time()
    count = 0
    async with httpx.AsyncClient(timeout=httpx.Timeout(60)) as client:
        async with client.stream('POST', 'http://localhost:8000/api/v1/chat/general/stream',
            headers={'Authorization': f'Bearer {token}'},
            json={'question': 'What is Article 14 in one line?', 'language': 'en'}
        ) as resp:
            print('HTTP Status:', resp.status_code)
            async for line in resp.aiter_lines():
                if not line.startswith('data: '):
                    continue
                data = line[6:]
                if data == '[DONE]':
                    print(f'DONE after {time.time()-t0:.1f}s, {count} chunks')
                    break
                try:
                    chunk = json.loads(data)
                    if chunk.get('content'):
                        count += 1
                        if count == 1:
                            print(f'First token in {time.time()-t0:.1f}s')
                        if count <= 5:
                            print(f'  chunk {count}:', repr(chunk['content'][:40]))
                    if chunk.get('error'):
                        print('ERROR:', chunk['error'])
                except Exception as e:
                    print('Parse error:', e, repr(data[:50]))

asyncio.run(test())
