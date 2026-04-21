import requests
from bs4 import BeautifulSoup
import re
import time

def duckduckgo_scrape(query):
    print(f"Scraping DuckDuckGo for: {query}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # DuckDuckGo HTML version is easier to scrape than the JS version
    url = 'https://html.duckduckgo.com/html/'
    data = {'q': f"{query} price"}
    
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('div', class_='result__body')
        
        sources = []
        for result in results[:5]: # Get top 5 results
            title_el = result.find('a', class_='result__url')
            if not title_el:
                continue
                
            link = title_el.get('href')
            # Extract actual URL from DuckDuckGo redirect
            match = re.search(r'uddg=(.*?)(&|$)', link)
            if match:
                import urllib.parse
                link = urllib.parse.unquote(match.group(1))
            else:
                link = f"https://{title_el.text.strip()}"
                
            snippet_el = result.find('a', class_='result__snippet')
            snippet = snippet_el.text.strip() if snippet_el else ""
            
            # Very basic regex to find a price in the snippet (e.g., $125.00)
            price_match = re.search(r'\$\d+(?:,\d{3})*(?:\.\d{2})?', snippet)
            price = price_match.group(0) if price_match else "Unknown"
            
            # Simple domain extraction for 'supplier' name
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', link)
            supplier = domain_match.group(1) if domain_match else "Unknown"
            
            sources.append({
                "supplier": supplier,
                "price": price,
                "url": link,
                "snippet": snippet
            })
            
        return sources
            
    except Exception as e:
        print(f"Error scraping: {e}")
        return []

if __name__ == "__main__":
    results = duckduckgo_scrape("Dewalt 20V Max Cordless Drill DCD771C2")
    for r in results:
        print(f"Supplier: {r['supplier']} | Price: {r['price']}")
        print(f"URL: {r['url']}")
        print(f"Snippet: {r['snippet']}\n")
