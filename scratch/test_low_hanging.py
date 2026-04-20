import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load env variables
load_dotenv()
API_KEY = os.getenv('SAM_API_KEY')
if not API_KEY or API_KEY == 'DEMO_KEY':
    print("Warning: Missing real SAM_API_KEY. Results might be heavily restricted or fail.")

today = datetime.now()
past_180 = today - timedelta(days=180)
past_30 = today - timedelta(days=30)

rdl_from = past_180.strftime("%m/%d/%Y")
rdl_to = past_30.strftime("%m/%d/%Y")

past_350 = today - timedelta(days=350)
posted_from = past_350.strftime("%m/%d/%Y")
posted_to = today.strftime("%m/%d/%Y")

print(f"Testing Low Hanging Fruit Logic...")
print(f"Posted Between: {posted_from} and {posted_to}")
print(f"Deadline Passed Between: {rdl_from} and {rdl_to}")

# SAM API URL (Opportunities endpoint is only for active notices by default)
SAM_API_BASE = "https://api.sam.gov/opportunities/v2/search"

params = {
    "api_key": API_KEY,
    "limit": 10,
    "rdlfrom": rdl_from,
    "rdlto": rdl_to,
    "postedFrom": posted_from,
    "postedTo": posted_to
}

try:
    print("Sending request to SAM.gov API...")
    resp = requests.get(SAM_API_BASE, params=params, timeout=30)
    
    if resp.status_code != 200:
        print(f"Request failed with status code {resp.status_code}")
        print(resp.text)
    else:
        data = resp.json()
        total = data.get("totalRecords", 0)
        print(f"\nSUCCESS! Found {total} total unawarded 'Low Hanging Fruit' contracts.")
        
        opps = data.get("opportunitiesData", [])
        print(f"\nDisplaying Top {len(opps)} immediate matches:")
        print("-" * 50)
        
        for idx, opp in enumerate(opps):
            title = opp.get("title", "No Title")
            dead = opp.get("responseDeadLine", "No Date")
            sol_num = opp.get("solicitationNumber", "No Sol Num")
            dept = opp.get("department", "Unknown Dept")
            
            # Format the output so we can verify the deadline is indeed in the past
            print(f"[{idx+1}] {title}")
            print(f"    Agency: {dept}")
            print(f"    Solicitation Number: {sol_num}")
            print(f"    ⭐ DEADLINE EXPIRED ON: {dead}")
            print("-" * 50)

except Exception as e:
    print(f"An error occurred during testing: {str(e)}")
