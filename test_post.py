import json, urllib.request, urllib.error

url = "http://192.168.105.23:5000/api/update-location"
payload = {
    "plaque": "UAC-001",
    "latitude": -0.1234,
    "longitude": 29.1234,
    "dernier_arret": "Takenga"
}
req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('HTTP', r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print('HTTP ERR', e.code)
    try:
        print(e.read().decode())
    except Exception:
        pass
except Exception as e:
    print('ERR', e)
