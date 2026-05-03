import requests
import json
import os

SAM_API_KEY = os.getenv("SAM_API_KEY", "DEMO_KEY")

def test_sam_attachments(notice_id):
    # Try the v2 search api to get the full opportunity details
    url = f"https://api.sam.gov/opportunities/v2/search?api_key={SAM_API_KEY}&noticeId={notice_id}"
    print(f"Fetching {url}")
    
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sam_attachments("eb90da5ccb804bbdbfae7b998cfb46de")  # Random notice ID, replace if needed
