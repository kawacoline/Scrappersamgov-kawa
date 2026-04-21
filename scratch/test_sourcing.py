import os
import re
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("Error: GEMINI_API_KEY not found in .env")
    exit(1)

client = genai.Client(api_key=API_KEY)

def test_sourcing(part_query):
    print(f"Sourcing Part: {part_query}...")
    
    prompt = f"""
    You are a professional industrial sourcing agent. I need you to find the current commercial price for the following part:
    "{part_query}"
    
    Please use your Google Search tool to find 3 real suppliers (like Grainger, Zoro, Uline, Amazon Business, or direct manufacturers) that sell this part.
    
    Return the output in STRICT JSON format like this:
    [
        {{"supplier": "Grainger", "price": "$125.00", "url": "https://www.grainger.com/..."}},
        {{"supplier": "Zoro", "price": "$122.50", "url": "https://www.zoro.com/..."}},
        {{"supplier": "Amazon", "price": "$119.99", "url": "https://www.amazon.com/..."}}
    ]
    
    Do not output any other text, just the JSON array.
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{'google_search': {}}],
                temperature=0.2
            )
        )
        print("Raw Response:")
        print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_sourcing("Dewalt 20V Max Cordless Drill DCD771C2")
