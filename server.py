"""
ScrapperGov — SAM.gov Contract Opportunities Scraper
Flask backend that proxies requests to the SAM.gov public API
"""

import os
import sys
import csv
import json
import time
import requests
import threading
import subprocess
import concurrent.futures
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static")
CORS(app)

SAM_API_BASE = "https://api.sam.gov/opportunities/v2/search"
SAM_AWARDS_BASE = "https://api.sam.gov/contract-awards/v1/search"
SAM_API_KEY = os.getenv("SAM_API_KEY", "DEMO_KEY")
API_KEY = SAM_API_KEY

# ── NAICS codes relevant to deliveries & software licensing ─────────
NAICS_PRESETS = {
    "delivery_services": {
        "label": "Delivery & Courier Services",
        "codes": ["492110", "492210", "484110", "484121", "484122", "488510", "493110"],
        "description": "Couriers, express delivery, trucking, freight, warehousing"
    },
    "software_licensing": {
        "label": "Software & IT Licensing",
        "codes": ["511210", "511211", "511212", "518210", "541511", "541512", "541519", "334111"],
        "description": "Software publishing, SaaS, data processing, IT consulting, computer manufacturing"
    },
    "it_services": {
        "label": "IT Services & Consulting",
        "codes": ["541511", "541512", "541513", "541519", "518210", "541690"],
        "description": "Custom programming, systems design, computer facilities management"
    },
    "logistics": {
        "label": "Logistics & Supply Chain",
        "codes": ["493110", "493120", "488510", "488490", "541614"],
        "description": "Warehousing, storage, freight transport arrangement"
    },
    "office_supplies": {
        "label": "Office Supplies & Equipment",
        "codes": ["424120", "424130", "339940", "423420", "423430"],
        "description": "Stationery, office equipment, office furniture"
    },
    "maintenance": {
        "label": "Maintenance & Janitorial",
        "codes": ["561720", "561210", "561730", "561740", "238220"],
        "description": "Janitorial, facilities support, landscaping, pest control"
    }
}

# ── Set-Aside codes ──────────────────────────────────────────────────
SET_ASIDE_OPTIONS = {
    "SBA": "Total Small Business Set-Aside (FAR 19.5)",
    "SBP": "Partial Small Business Set-Aside (FAR 19.5)",
    "8A": "8(a) Set-Aside (FAR 19.8)",
    "8AN": "8(a) Sole Source (FAR 19.8)",
    "HZC": "HUBZone Set-Aside (FAR 19.13)",
    "HZS": "HUBZone Sole Source (FAR 19.13)",
    "SDVOSBC": "Service-Disabled Veteran-Owned SB Set-Aside (FAR 19.14)",
    "SDVOSBS": "Service-Disabled Veteran-Owned SB Sole Source (FAR 19.14)",
    "WOSB": "Women-Owned Small Business Program Set-Aside (FAR 19.15)",
    "WOSBSS": "Women-Owned Small Business Program Sole Source (FAR 19.15)",
    "EDWOSB": "Economically Disadvantaged WOSB Program Set-Aside (FAR 19.15)",
    "EDWOSBSS": "Economically Disadvantaged WOSB Program Sole Source (FAR 19.15)",
    "LAS": "Local Area Set-Aside (FAR 26.2)",
    "IEE": "Indian Economic Enterprise (HHSAR 326.603)",
    "ISBEE": "Indian Small Business Economic Enterprise (Dear 1426.7003)",
    "BICiv": "Buy Indian Set-Aside (HHSAR 326.603)",
    "VSA": "Veteran-Owned Small Business Set-Aside (FAR 19.14)",
    "VSS": "Veteran-Owned Small Business Sole Source (FAR 19.14)",
}

# ── Procurement types ────────────────────────────────────────────────
PROCUREMENT_TYPES = {
    "p": "Presolicitation",
    "o": "Solicitation",
    "k": "Combined Synopsis/Solicitation",
    "r": "Sources Sought",
    "s": "Special Notice",
    "g": "Sale of Surplus Property",
    "f": "Fair Opportunity / Limited Sources Justification",
    "a": "Award Notice",
    "u": "Justification and Approval (J&A)",
    "i": "Intent to Bundle Requirements",
}


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


@app.route("/api/config")
def get_config():
    """Return available filter options to the frontend."""
    return jsonify({
        "naics_presets": NAICS_PRESETS,
        "set_aside_options": SET_ASIDE_OPTIONS,
        "procurement_types": PROCUREMENT_TYPES,
        "has_api_key": SAM_API_KEY != "DEMO_KEY" and bool(SAM_API_KEY),
    })


@app.route("/api/search")
def search_opportunities():
    """Proxy search requests to SAM.gov API with filters."""
    # Date range — default to last 90 days
    posted_from = request.args.get("postedFrom")
    posted_to = request.args.get("postedTo")
    if not posted_from:
        posted_from = (datetime.now() - timedelta(days=90)).strftime("%m/%d/%Y")
    if not posted_to:
        posted_to = datetime.now().strftime("%m/%d/%Y")

    # Pagination
    limit = request.args.get("limit", "25")
    offset = request.args.get("offset", "0")

    # Build params
    params = {
        "api_key": SAM_API_KEY,
        "postedFrom": posted_from,
        "postedTo": posted_to,
        "limit": limit,
        "offset": offset,
    }

    # Optional filters
    ptype = request.args.get("ptype")
    if ptype:
        params["ptype"] = ptype

    title = request.args.get("title")
    if title:
        params["title"] = title

    naics = request.args.get("ncode")
    if naics:
        params["ncode"] = naics

    # Remove individual ncode string since we handle it dynamically
    ncodes = request.args.get("ncode", "")
    ncode_list = [n.strip() for n in ncodes.split(",")] if ncodes else [None]

    ccode = request.args.get("ccode")
    if ccode:
        params["ccode"] = ccode

    set_aside = request.args.get("typeOfSetAside")
    if set_aside:
        params["typeOfSetAside"] = set_aside

    state = request.args.get("state")
    if state:
        params["state"] = state

    zip_code = request.args.get("zip")
    if zip_code:
        params["zip"] = zip_code

    sol_num = request.args.get("solnum")
    if sol_num:
        params["solnum"] = sol_num

    rdl_from = request.args.get("rdlfrom")
    if rdl_from:
        params["rdlfrom"] = rdl_from

    rdl_to = request.args.get("rdlto")
    if rdl_to:
        params["rdlto"] = rdl_to

    # We will aggregate results using multi-threading
    all_opps = []
    total_records = 0
    seen_ids = set()
    errors = []

    def fetch_for_ncode(ncode_val):
        iter_params = params.copy()
        if ncode_val:
            iter_params["ncode"] = ncode_val
        resp = requests.get(SAM_API_BASE, params=iter_params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ncode = {executor.submit(fetch_for_ncode, code): code for code in ncode_list}
        for future in concurrent.futures.as_completed(future_to_ncode):
            try:
                data = future.result()
                try:
                    total_records += int(data.get("totalRecords", 0))
                except:
                    pass
                for opp in data.get("opportunitiesData", []):
                    if opp["noticeId"] not in seen_ids:
                        seen_ids.add(opp["noticeId"])
                        all_opps.append(opp)
            except Exception as e:
                # Store the error mapping
                errors.append(str(e))

    if not all_opps and errors:
        return jsonify({
            "error": "API Error", 
            "message": "SAM.gov API request failed. " + errors[0]
        }), 502

    # Enforce limit back on the aggregated dataset to avoid exploding results per page
    limit_int = 25
    try: limit_int = int(limit) 
    except: pass
    
    # Sort backwards by Date to maintain recency across combined results
    try:
        all_opps.sort(key=lambda x: x.get('postedDate', ''), reverse=True)
    except:
        pass
        
    all_opps = all_opps[:limit_int]

    return jsonify({
        "totalRecords": total_records,
        "opportunitiesData": all_opps,
        "appliedFilters": {k: v for k, v in params.items() if k != "api_key"}
    })

@app.route("/api/awards", methods=["GET"])
def search_awards():
    """Proxy the request to SAM.gov Contract Awards API and return JSON data."""
    if not API_KEY or API_KEY == "your_api_key_here":
        return jsonify({"error": "Configuration Error", "message": "API key missing in .env"}), 500

    limit = request.args.get("limit", "25")
    offset = request.args.get("offset", "0")
    
    params = {
        "api_key": API_KEY,
        "limit": limit,
        "offset": offset
    }

    keyword = request.args.get("ptq")
    if keyword:
        params["q"] = keyword
        
    ncodes = request.args.get("ncode", "")
    ncode_list = [n.strip() for n in ncodes.split(",")] if ncodes else [None]

    all_awards = []
    total_records = 0
    seen_ids = set()
    errors = []

    def fetch_for_ncode(ncode_val):
        iter_params = params.copy()
        if ncode_val:
            iter_params["naicsCode"] = ncode_val
        resp = requests.get(SAM_AWARDS_BASE, params=iter_params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ncode = {executor.submit(fetch_for_ncode, code): code for code in ncode_list}
        for future in concurrent.futures.as_completed(future_to_ncode):
            try:
                data = future.result()
                try:
                    total_records += int(data.get("totalRecords", 0))
                except:
                    pass
                for award in data.get("awardSummary", []):
                    piid = award.get("contractId", {}).get("piid")
                    if piid and piid not in seen_ids:
                        seen_ids.add(piid)
                        all_awards.append(award)
                    elif not piid:
                        all_awards.append(award)
            except Exception as e:
                errors.append(str(e))

    if not all_awards and errors:
        return jsonify({
            "error": "API Error", 
            "message": "SAM.gov Awards API failed. " + errors[0]
        }), 502

    limit_int = 25
    try: limit_int = int(limit) 
    except: pass
    
    all_awards = all_awards[:limit_int]

    return jsonify({
        "totalRecords": total_records,
        "awardSummary": all_awards,
        "appliedFilters": {k: v for k, v in params.items() if k != "api_key"}
    })

@app.route("/api/intelligence", methods=["POST"])
def get_intelligence():
    """Gemini AI Route: Generates Proposal Template and Difficulty Report"""
    data = request.json
    notice_id = data.get("noticeId")
    contract_title = data.get("title", "")
    
    if not notice_id:
        return jsonify({"error": "No noticeId provided"}), 400

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key or "AIza" not in gemini_key:
        return jsonify({"error": "Missing or invalid GEMINI_API_KEY in .env"}), 500

    # 1. Fetch the description text from SAM.gov
    desc_text = "No detailed description provided by SAM.gov API."
    try:
        desc_url = f"https://api.sam.gov/prod/opportunities/v1/noticedesc?noticeid={notice_id}&api_key={API_KEY}"
        desc_res = requests.get(desc_url, timeout=15)
        if desc_res.status_code == 200:
            desc_text = json.dumps(desc_res.json())
    except Exception as e:
        print(f"Error fetching desc: {e}")

    # 2. Call Gemini
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=gemini_key)
        
        prompt = f"""
        You are an expert Government Contracting Analyst and Proposal Writer.
        Analyze the following Active Contract Bid (Title: {contract_title}, Notice ID: {notice_id}) and its textual description:
        {desc_text[:20000]}
        
        Task 1: Difficulty Report. Cross-reference the requirements. Calculate how long it would take to acquire necessary certifications/vendor approvals. 
        Assign a 'difficulty_score' out of 100 based strictly on wait times and requirements. Explicitly mention if you cannot find enough info to give a solid number.
        Task 2: Draft a Proposal Template. Base your wording and style on winning templates from GAO protests or FOIA Reading Rooms for similar tech contracts.
        
        Return pure JSON with EXACTLY this structure (no markdown formatting):
        {{
            "difficulty_score": <number 1-100>,
            "eta_weeks": "<string, e.g. '3-6 weeks'>",
            "missing_requirements": ["list", "of", "missing", "certifications", "or", "requirements"],
            "notes": "<string explaining where info is missing or solid>",
            "proposal_template": "<markdown formatted string of a proposal draft>"
        }}
        """
        
        # Using gemini-3-flash-preview as requested
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        result_json = json.loads(response.text)
        
        # 3. Save locally as a readable .txt file
        os.makedirs("scraped_data", exist_ok=True)
        local_filename = f"scraped_data/AI_Report_{notice_id}.txt"
        
        with open(local_filename, "w", encoding="utf-8") as f:
            f.write(f"=== CONTRACT AI INTELLIGENCE REPORT ===\n")
            f.write(f"Notice ID: {notice_id}\n")
            f.write(f"Title: {contract_title}\n")
            f.write(f"---------------------------------------\n")
            f.write(f"DIFFICULTY SCORE: {result_json.get('difficulty_score', 'N/A')}/100\n")
            f.write(f"ETA WEEKS: {result_json.get('eta_weeks', 'N/A')}\n")
            
            reqs = result_json.get('missing_requirements', [])
            req_str = ', '.join(reqs) if isinstance(reqs, list) else reqs
            f.write(f"MISSING REQUIREMENTS: {req_str}\n")
            
            f.write(f"NOTES: {result_json.get('notes', 'N/A')}\n")
            f.write(f"---------------------------------------\n\n")
            f.write(f"=== PROPOSAL TEMPLATE ===\n\n")
            f.write(result_json.get('proposal_template', 'Error generating template.'))
            
        return jsonify({"status": "success", "data": result_json, "file_saved": local_filename})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/api/export', methods=['POST'])
def export_data():
    try:
        data = request.json.get('results', [])
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        import csv
        from datetime import datetime
        
        os.makedirs('scraped_data', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Determine if these are awards or opportunities based on data shape
        if len(data) > 0 and 'awardeeData' in data[0] or 'awardDetails' in data[0]:
            filename = f'scraped_data/contract_awards_{timestamp}.csv'
            # Flatten award data
            flat_data = []
            for d in data:
                aw_data = d.get('awardDetails', {}).get('awardeeData', {})
                flat_data.append({
                    'PIID': d.get('contractId', {}).get('piid', 'N/A'),
                    'Awardee': aw_data.get('awardeeHeader', {}).get('awardeeName') or aw_data.get('awardeeHeader', {}).get('legalBusinessName', 'UNKNOWN'),
                    'ObligatedAmount': float(d.get('awardDetails', {}).get('dollars', {}).get('actionObligation', 0) or 0),
                    'DateSigned': d.get('awardDetails', {}).get('dates', {}).get('dateSigned', 'N/A'),
                    'CageCode': aw_data.get('awardeeUEIInformation', {}).get('cageCode', 'N/A'),
                    'SAM_URL': f"https://sam.gov/search/?index=cdo&keywords={d.get('contractId', {}).get('piid', '')}",
                })
            if flat_data:
                keys = flat_data[0].keys()
                with open(filename, 'w', newline='', encoding='utf-8') as output_file:
                    dict_writer = csv.DictWriter(output_file, keys)
                    dict_writer.writeheader()
                    dict_writer.writerows(flat_data)
            
        else:
            filename = f'scraped_data/bids_opportunities_{timestamp}.csv'
            # Opportunities are already flat
            if data:
                # opportunities logic
                keys = data[0].keys()
                with open(filename, 'w', newline='', encoding='utf-8') as output_file:
                    dict_writer = csv.DictWriter(output_file, keys)
                    dict_writer.writeheader()
                    dict_writer.writerows(data)
            
        return jsonify({'message': 'Success', 'filename': filename}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
def check_for_updates():
    """Background loop that polls Git for updates."""
    while True:
        try:
            # Fetch latest from origin
            subprocess.run(["git", "fetch"], check=True, capture_output=True)
            
            # Check if main is behind origin/main
            result = subprocess.run(
                ["git", "status", "-uno"], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            # If "Your branch is behind" is in the output, we need to update
            if "Your branch is behind" in result.stdout:
                print("\n[UPDATER] 🚀 New update found on GitHub!")
                print("[UPDATER] Gracefully shutting down the server to restart...")
                # Exit with code 42 so the start.bat script knows to pull and restart
                os._exit(42)
                
        except Exception as e:
            # If git fails (e.g. no internet), just suppress and try again later
            pass
            
        # Check every 60 seconds
        time.sleep(60)

if __name__ == "__main__":
    print("\n[+] ScrapperGov - SAM.gov Contract Scraper")
    print(f"   API Key: {'[Loaded]' if SAM_API_KEY != 'DEMO_KEY' else '[DEMO_KEY limited] '}")
    print(f"   Server:  http://localhost:5000\n")
    
    # Start the auto-updater in a background thread
    updater_thread = threading.Thread(target=check_for_updates, daemon=True)
    updater_thread.start()
    
    app.run(debug=False, port=5000)
