import requests

try:
    resp = requests.get('http://127.0.0.1:5000/api/awards', params={'limit': 5, 'ncode': '511210'})
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Total: {data.get('totalRecords')}")
    print(f"Items: {len(data.get('awardSummary', []))}")
except Exception as e:
    print('Error:', e)
