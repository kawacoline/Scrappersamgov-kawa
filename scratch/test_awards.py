import requests

try:
    resp = requests.get('http://127.0.0.1:5000/api/awards', params={'limit': 5, 'ncode': '511210'})
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"Total: {data.get('totalRecords')}")
    print(f"Items: {len(data.get('awardSummary', []))}\n")
    
    print("--- SAMPLE SCRAPED AWARDS ---")
    for i, item in enumerate(data.get('awardSummary', [])[:3]):
        awardee = item.get('awardeeData', {}).get('awardeeHeader', {}).get('awardeeName', 'Unknown')
        dollars = item.get('awardDetails', {}).get('dollars', {}).get('totalContractDollars', '0')
        piid = item.get('contractId', {}).get('piid', 'N/A')
        print(f"Contract {i+1}:")
        print(f"  Awardee : {awardee}")
        print(f"  Value   : ${float(dollars):,.2f}" if dollars else "  Value   : N/A")
        print(f"  PIID    : {piid}\n")
except Exception as e:
    print('Error:', e)
