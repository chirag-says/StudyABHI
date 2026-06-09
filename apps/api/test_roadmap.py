import httpx, json, traceback

r = httpx.post('http://localhost:8000/api/v1/auth/login', json={'email':'abhitha@gmail.com','password':'Abhitha@123'})
token = r.json()['tokens']['access_token']
print('Auth OK')

# Use OPTIONS to check CORS preflight first
r_opt = httpx.options(
    'http://localhost:8000/api/v1/roadmap/onboarding/complete',
    headers={'Origin': 'http://localhost:3000', 'Access-Control-Request-Method': 'POST'}
)
print('OPTIONS status:', r_opt.status_code)

r2 = httpx.post(
    'http://localhost:8000/api/v1/roadmap/onboarding/complete',
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
    json={
        'target_exam_year': 2026,
        'preparation_level': 'beginner',
        'study_preference': 'moderate',
        'daily_study_hours': 6.0,
        'is_working': False,
        'preferred_study_time': 'morning',
        'medium': 'english',
        'optional_subject': None
    },
    timeout=30
)
print('Status:', r2.status_code)
try:
    body = r2.json()
    print('Response:', json.dumps(body, indent=2)[:2000])
except Exception as e:
    print('Raw:', r2.text[:500])
