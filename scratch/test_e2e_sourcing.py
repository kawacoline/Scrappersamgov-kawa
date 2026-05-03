import requests
import json

def test_workflow():
    print("Testing End-to-End Sourcing Workflow...")
    
    # Mock data from a real SAM.gov Low Hanging Fruit contract we found earlier
    payload = {
        "title": "MJU-76B Pre-solicitation Synopsis",
        "description": "This is a pre-solicitation for the procurement of MJU-76B infrared decoy flares. The government intends to purchase 500 units of part number MJU-76B manufactured by unknown or equivalent. Deliveries required to Hill AFB."
    }
    
    url = "http://127.0.0.1:5000/api/source_parts"
    
    try:
        print(f"Sending contract '{payload['title']}' to the backend API...")
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("\n--- API Success! ---")
            
            part_details = data.get("part_details", {})
            print("\n--- AI Part Extraction ---")
            print(json.dumps(part_details, indent=2))
            
            sources = data.get("sources", [])
            print(f"\n--- Scraper Found {len(sources)} Sources ---")
            for i, src in enumerate(sources):
                print(f"[{i+1}] {src['supplier']} | {src['price']}")
                print(f"    URL: {src['url']}")
                print(f"    Snippet: {src['snippet'][:100]}...\n")
        else:
            print(f"API Failed with status {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Error testing API: {e}")
        print("Make sure your Flask server is running (python server.py) before running this test.")

if __name__ == "__main__":
    test_workflow()
