import os
import json
from server import app

def run_tests():
    app.config['TESTING'] = True
    client = app.test_client()

    print("--- 1. Testing Supplier Outreach Endpoint ---")
    outreach_payload = {
        "supplier_email": "test@supplier.com",
        "part_name": "Test Military Compass",
        "send_auto": False
    }
    res1 = client.post('/api/supplier_outreach', json=outreach_payload)
    if res1.status_code == 200:
        print("SUCCESS: Supplier Outreach returned 200 OK")
        data1 = json.loads(res1.data)
        print("Subject:", data1.get("subject"))
        print("Body snippet:", data1.get("body")[:100] + "...")
    else:
        print("ERROR: Supplier Outreach failed:", res1.status_code, res1.data)

    print("\n--- 2. Testing Bulk Scan Endpoint ---")
    bulk_payload = {
        "opportunities": [
            {"noticeId": "9e1c18002efc4013ad9ccad80f8dbd80", "title": "Custodial Services"},
            {"noticeId": "1b016b8022d4493eb1281ffec975cb45", "title": "IT Software License Renewal"}
        ]
    }
    res2 = client.post('/api/bulk_scan', json=bulk_payload)
    if res2.status_code == 200:
        print("SUCCESS: Bulk Scan returned 200 OK")
        data2 = json.loads(res2.data)
        print(json.dumps(data2.get('data', []), indent=2))
    else:
        print("ERROR: Bulk Scan failed:", res2.status_code, res2.data)

if __name__ == "__main__":
    run_tests()
