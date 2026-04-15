from app import app

print('Testing student dashboard...')
client = app.test_client()

# Test without login (should redirect)
rv = client.get('/student')
print('Status:', rv.status_code)
if rv.status_code == 302:
    print('Redirect to:', rv.headers.get('Location'))

# Test with student login
rv2 = client.post('/login', data={'email': 'student@example.com', 'password': 'uac2026'}, follow_redirects=True)
print('Login status:', rv2.status_code)
if b'student' in rv2.data.lower():
    print('Student dashboard loaded successfully')
else:
    print('Student dashboard failed to load')