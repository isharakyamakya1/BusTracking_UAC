import json, urllib.request, urllib.error

url = "http://192.168.105.23:5000/api/buses/locations"
req = urllib.request.Request(url, headers={"Accept": "application/json"})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('HTTP', r.status)
        print(r.read().decode())
except Exception as e:
    print('ERR', e)
