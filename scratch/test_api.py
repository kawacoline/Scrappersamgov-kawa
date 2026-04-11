import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("SAM_API_KEY")

base_url = "https://api.sam.gov/opportunities/v2/search"
from datetime import datetime, timedelta
today = datetime.now()
yesterday = today - timedelta(days=5)

params = {
    "api_key": API_KEY,
    "limit": "5",
    "ncode": "492110,492210",
    "postedFrom": yesterday.strftime("%m/%d/%Y"),
    "postedTo": today.strftime("%m/%d/%Y")
}

resp = requests.get(base_url, params=params)
print("Testing ncode with comma-separated values:")
print(f"Status Code: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    print(f"Total Records: {data.get('totalRecords')}")
else:
    print(resp.text)
