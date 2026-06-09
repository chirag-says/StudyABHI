import httpx, json

r = httpx.post('http://localhost:8000/api/v1/auth/login', json={'email':'abhitha@gmail.com','password':'Abhitha@123'})
token = r.json()['tokens']['access_token']
print('Auth OK')

# Get documents list
r2 = httpx.get('http://localhost:8000/api/v1/documents/', headers={'Authorization': f'Bearer {token}'}, timeout=10)
print('Docs status:', r2.status_code)
print('Docs raw:', r2.text[:1000])
