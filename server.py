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
    },
    "construction_repairs": {
        "label": "Construction & Repairs",
        "codes": ["236220", "238160", "238210", "238220", "238320", "238350", "238990"],
        "description": "Building construction, carpentry, doors, roofing, electrical, plumbing"
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

    bond_filter = request.args.get('bondFilter', 'all')
    print(f"\n{'='*60}")
    print(f"[SEARCH] NAICS: {ncode_list} | State: {state or 'Any'} | Bond: {bond_filter}")
    print(f"{'='*60}")

    def fetch_for_ncode(ncode_val):
        iter_params = params.copy()
        if ncode_val:
            iter_params["ncode"] = ncode_val
        
        # Build the actual URL so we can see exactly what's being called
        from urllib.parse import urlencode
        debug_params = {k: v for k, v in iter_params.items() if k != 'api_key'}
        print(f"  [>>] NAICS {ncode_val or 'ALL'} — Calling SAM.gov...")
        print(f"       URL: {SAM_API_BASE}?{urlencode(debug_params)}")
        
        import time as _time
        start = _time.time()
        try:
            resp = requests.get(SAM_API_BASE, params=iter_params, timeout=30)
            elapsed = round(_time.time() - start, 2)
            print(f"  [<<] NAICS {ncode_val or 'ALL'} — HTTP {resp.status_code} in {elapsed}s")
            
            if resp.status_code != 200:
                print(f"       RESPONSE BODY: {resp.text[:500]}")
                resp.raise_for_status()
            
            return resp.json()
        except requests.exceptions.Timeout:
            elapsed = round(_time.time() - start, 2)
            print(f"  [!!] NAICS {ncode_val or 'ALL'} — TIMEOUT after {elapsed}s (SAM.gov not responding)")
            raise
        except requests.exceptions.ConnectionError as e:
            elapsed = round(_time.time() - start, 2)
            print(f"  [!!] NAICS {ncode_val or 'ALL'} — CONNECTION ERROR after {elapsed}s: {e}")
            raise
        except Exception as e:
            elapsed = round(_time.time() - start, 2)
            print(f"  [!!] NAICS {ncode_val or 'ALL'} — ERROR after {elapsed}s: {type(e).__name__}: {e}")
            raise

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_ncode = {executor.submit(fetch_for_ncode, code): code for code in ncode_list}
        for future in concurrent.futures.as_completed(future_to_ncode):
            ncode_key = future_to_ncode[future]
            try:
                data = future.result()
                count = int(data.get("totalRecords", 0))
                opps = data.get("opportunitiesData", [])
                print(f"  [OK] NAICS {ncode_key or 'ALL'}: {count} total records, {len(opps)} returned this page")
                total_records += count
                for opp in opps:
                    if opp["noticeId"] not in seen_ids:
                        seen_ids.add(opp["noticeId"])
                        all_opps.append(opp)
            except Exception as e:
                print(f"  [FAIL] NAICS {ncode_key}: {type(e).__name__}: {e}")
                errors.append(str(e))
    
    print(f"[SEARCH DONE] {len(all_opps)} unique results collected, {len(errors)} errors")

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

    # ── Bond Filtering (for Construction contracts) ────────────────
    if bond_filter in ('required', 'none'):
        # Tag each opportunity with bond status by scanning description keywords
        BOND_KEYWORDS = [
            'payment bond', 'performance bond', 'payment and performance bond',
            'surety bond', 'bid bond', 'miller act', 'far 28.102',
            'far 52.228-15', 'far 52.228-1', 'bonding requirement',
            'bond is required', 'bonds are required', 'bonding is required',
            'must provide bond', 'shall furnish bond', 'shall provide bond',
            'contractor shall furnish', 'performance and payment bond'
        ]
        NO_BOND_KEYWORDS = [
            'no bond required', 'bond is not required', 'bonds not required',
            'bond waived', 'bond waiver', 'no bonding', 'waive bond',
            'bond not applicable'
        ]
        
        def detect_bond_status(opp):
            """Returns 'required', 'none', or 'unknown' based on title + description hints."""
            text = (opp.get('title', '') + ' ' + opp.get('description', '')).lower()
            
            # Check no-bond first (more specific)
            for kw in NO_BOND_KEYWORDS:
                if kw in text:
                    return 'none'
            
            # Check bond-required keywords
            for kw in BOND_KEYWORDS:
                if kw in text:
                    return 'required'
            
            # For construction over $150k, FAR 28.102 generally requires bonds
            # We can infer from award value if available
            return 'unknown'
        
        for opp in all_opps:
            opp['_bondStatus'] = detect_bond_status(opp)
        
        if bond_filter == 'required':
            all_opps = [o for o in all_opps if o.get('_bondStatus') in ('required', 'unknown')]
        elif bond_filter == 'none':
            all_opps = [o for o in all_opps if o.get('_bondStatus') in ('none', 'unknown')]
    else:
        # Tag them anyway for badge display but don't filter
        BOND_KEYWORDS = [
            'payment bond', 'performance bond', 'payment and performance bond',
            'surety bond', 'bid bond', 'miller act', 'far 28.102',
            'bonding requirement', 'bond is required'
        ]
        NO_BOND_KEYWORDS = [
            'no bond required', 'bond is not required', 'bond waived', 'no bonding'
        ]
        for opp in all_opps:
            text = (opp.get('title', '') + ' ' + opp.get('description', '')).lower()
            status = 'unknown'
            for kw in NO_BOND_KEYWORDS:
                if kw in text:
                    status = 'none'
                    break
            if status == 'unknown':
                for kw in BOND_KEYWORDS:
                    if kw in text:
                        status = 'required'
                        break
            opp['_bondStatus'] = status

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
        
    # 1.5. Fetch attached PDF documents (resourceLinks)
    pdf_text = ""
    pdfs_read_count = 0
    try:
        opp_url = f"https://api.sam.gov/opportunities/v2/search?api_key={API_KEY}&noticeId={notice_id}"
        opp_res = requests.get(opp_url, timeout=15)
        if opp_res.status_code == 200:
            opp_data = opp_res.json()
            if opp_data.get("opportunitiesData"):
                resource_links = opp_data["opportunitiesData"][0].get("resourceLinks", [])
                
                if resource_links:
                    import io
                    import PyPDF2
                    print(f"Found {len(resource_links)} attachments, attempting to read them...")
                    for link in resource_links[:3]: # Limit to first 3 attachments to avoid massive token counts
                        try:
                            # Attachments usually require API key
                            pdf_link = link if "api_key=" in link else f"{link}?api_key={API_KEY}"
                            
                            headers = {}
                            sam_cookie = os.getenv("SAM_COOKIE")
                            if sam_cookie:
                                headers["Cookie"] = sam_cookie
                                
                            pdf_res = requests.get(pdf_link, headers=headers, timeout=15)
                            if pdf_res.status_code == 200 and b"%PDF" in pdf_res.content[:10]:
                                pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_res.content))
                                for page in pdf_reader.pages:
                                    extracted = page.extract_text()
                                    if extracted:
                                        pdf_text += extracted + "\n"
                                pdfs_read_count += 1
                        except Exception as e:
                            print(f"Error reading attachment {link}: {e}")
    except Exception as e:
        print(f"Error fetching attachments: {e}")

    # 2. Call Gemini
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=gemini_key)
        
        prompt = f"""
        You are an expert Government Contracting Analyst and Proposal Writer.
        Analyze the following Active Contract Bid (Title: {contract_title}, Notice ID: {notice_id}).
        
        Textual Description:
        {desc_text[:15000]}
        
        Attached PDF Document Content (if any):
        {pdf_text[:15000]}
        
        
        Task 1: Difficulty Report. Cross-reference the requirements. Calculate how long it would take to acquire necessary certifications/vendor approvals. 
        Assign a 'difficulty_score' out of 100 based strictly on wait times and requirements. Explicitly mention if you cannot find enough info to give a solid number.
        
        Task 2: Draft a Proposal Template. Base your wording and style on winning templates from GAO protests or FOIA Reading Rooms for similar tech/supply contracts.
        Important Company Information to inject into the template:
        - Company Name: The Nomad Trader
        - Email: [User's Name]@thenomadtrader.net
        - Pricing Strategy: Add placeholders for sourced parts and explicitly apply a 60% markup baseline to the final cost.
        Make the template ready for submission, only leaving bracketed placeholders like [INSERT SOURCED PRICE HERE] where physical parts or API pricing is missing.
        
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
        result_json['pdfs_analyzed'] = pdfs_read_count
        
        # 3. Save locally as a readable .txt file
        os.makedirs("scraped_data", exist_ok=True)
        # Create a safe, human-readable filename from the contract title
        safe_title = "".join(c if c.isalnum() else "_" for c in contract_title)[:60].strip('_')
        prefix = f"AI_Report_{safe_title}" if safe_title else "AI_Report"
        local_filename = f"scraped_data/{prefix}_{notice_id}.txt"
        
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
            f.write(f"\n\n---------------------------------------\n")
            f.write(f"=== RAW EXTRACTED PDF TEXT (First 15000 chars) ===\n\n")
            f.write(pdf_text[:15000] if pdf_text else "No PDF text extracted.")
            
        return jsonify({"status": "success", "data": result_json, "file_saved": local_filename})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/bulk_scan', methods=['POST'])
def bulk_scan():
    API_KEY = os.getenv('SAM_API_KEY')
    gemini_key = os.getenv('GEMINI_API_KEY')
    
    if not gemini_key:
        return jsonify({"error": "Gemini API key is missing. Add GEMINI_API_KEY to .env"}), 400
        
    data = request.json
    opportunities = data.get('opportunities', [])
    
    if not opportunities:
        return jsonify({"error": "No opportunities provided."}), 400
        
    # Limit to 10 at a time to prevent timeout
    opportunities = opportunities[:10]
    
    # 1. Fetch descriptions
    context_blocks = []
    for opp in opportunities:
        nid = opp.get('noticeId')
        title = opp.get('title')
        desc_text = "No detailed description."
        try:
            desc_url = f"https://api.sam.gov/prod/opportunities/v1/noticedesc?noticeid={nid}&api_key={API_KEY}"
            desc_res = requests.get(desc_url, timeout=5)
            if desc_res.status_code == 200:
                desc_text = json.dumps(desc_res.json())
        except:
            pass
        
        context_blocks.append(f"--- Contract: {title} (ID: {nid}) ---\nDescription: {desc_text[:3000]}\n")
        
    all_context = "\n".join(context_blocks)
    
    # 2. Call Gemini
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=gemini_key)
        prompt = f"""
        You are an expert Government Contracting Analyst. 
        I am giving you a list of {len(opportunities)} active contracts.
        For each contract, determine if it is "Low Hanging Fruit" (easy to fulfill, no complex certifications, quick turnaround) or "Complex" (requires ISO, ITAR, specific facility clearances, or long lead times).
        Estimate the wait time for certifications if applicable.
        
        Contracts:
        {all_context}
        
        Return a JSON object with a single key 'results' which is an array of objects. 
        Each object MUST have:
        "noticeId": <string>,
        "difficulty": <"Easy", "Medium", "Hard">,
        "score": <number 1-100 (100 is hardest)>,
        "reason": <short 1-2 sentence explanation>
        """
        
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        result_json = json.loads(response.text)
        return jsonify({"status": "success", "data": result_json.get('results', [])})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/supplier_outreach', methods=['POST'])
def supplier_outreach():
    data = request.json
    supplier_email = data.get('supplier_email')
    part_name = data.get('part_name')
    send_auto = data.get('send_auto', False)
    
    # Generate the email content
    subject = f"Request for Quote (RFQ) - {part_name} - The Nomad Trader"
    body = f"""Hello,

My name is Thomas, and I am a purchasing agent representing The Nomad Trader. 
We are currently sourcing components for an upcoming Federal Government contract.

We would like to request a formal quote for the following part/product:
Product: {part_name}
Quantity: Please provide price breaks for 10, 50, and 100 units (if applicable).

We are operating on a strict timeline, so your prompt response is highly appreciated. If you have an expedited shipping option or a dedicated B2B portal, please let us know.

Thank you,
Thomas Nosser
The Nomad Trader
thomas@thenomadtrader.net
"""
    
    # If not sending automatically, just return the draft so the user can open it in their client
    if not send_auto:
        return jsonify({"status": "draft", "subject": subject, "body": body})
        
    # Optional: Actual SMTP sending logic (requires credentials in .env)
    # GoDaddy SMTP settings: smtpout.secureserver.net : 465 (SSL)
    import smtplib
    from email.mime.text import MIMEText
    
    smtp_user = os.getenv('SMTP_USER') # e.g. thomas@thenomadtrader.net
    smtp_pass = os.getenv('SMTP_PASS')
    
    if not smtp_user or not smtp_pass:
        return jsonify({"error": "SMTP credentials missing from .env. Could not send email automatically."}), 400
        
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = smtp_user
        msg['To'] = supplier_email
        
        server = smtplib.SMTP_SSL('smtpout.secureserver.net', 465)
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return jsonify({"status": "success", "message": "Email sent successfully to supplier."})
    except Exception as e:
        return jsonify({"error": f"Failed to send email: {str(e)}"}), 500

def duckduckgo_scrape(query):
    import requests
    from bs4 import BeautifulSoup
    import re
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = 'https://html.duckduckgo.com/html/'
    data = {'q': f"{query} price"}
    
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('div', class_='result__body')
        
        sources = []
        for result in results[:5]: 
            title_el = result.find('a', class_='result__url')
            if not title_el:
                continue
                
            link = title_el.get('href')
            match = re.search(r'uddg=(.*?)(&|$)', link)
            if match:
                import urllib.parse
                link = urllib.parse.unquote(match.group(1))
            else:
                link = f"https://{title_el.text.strip()}"
                
            snippet_el = result.find('a', class_='result__snippet')
            snippet = snippet_el.text.strip() if snippet_el else ""
            
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', link)
            supplier = domain_match.group(1) if domain_match else "Unknown"
            
            sources.append({
                "supplier": supplier,
                "price": "Check Link",
                "url": link,
                "snippet": snippet
            })
            
        return sources
    except Exception as e:
        print(f"Scraper error: {e}")
        return []

@app.route('/api/source_parts', methods=['POST'])
def source_parts():
    try:
        from google import genai
        from google.genai import types
        gemini_key = os.getenv("GEMINI_API_KEY")
        if not gemini_key:
            return jsonify({"error": "GEMINI_API_KEY not configured"}), 500
            
        client = genai.Client(api_key=gemini_key)
        
        data = request.json
        contract_title = data.get('title', '')
        desc_text = data.get('description', '')
        
        if not desc_text:
            return jsonify({"error": "No description provided to extract part."}), 400
            
        prompt = f"""
        You are an expert Government Parts Sourcing Agent.
        Analyze this contract title and description:
        Title: {contract_title}
        Description: {desc_text[:10000]}
        
        Identify if there is a SPECIFIC physical part, tool, or product being requested that we can buy from a commercial supplier (e.g. Dewalt Drill, MJU-76B flare, specific medical device).
        Do NOT guess if it's a general service. If it is a service, set has_specific_part to false.
        
        Return pure JSON with EXACTLY this structure:
        {{
            "has_specific_part": true or false,
            "part_number": "<the exact part number, NSN, or precise name to search>",
            "manufacturer": "<brand name if known, else Unknown>"
        }}
        """
        
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        result_json = json.loads(response.text)
        
        if not result_json.get("has_specific_part"):
            return jsonify({
                "status": "success", 
                "message": "No specific physical part found to source.", 
                "part_details": result_json,
                "sources": []
            })
            
        query = f"{result_json.get('manufacturer', '')} {result_json.get('part_number', '')}".strip()
        sources = duckduckgo_scrape(query)
        
        return jsonify({
            "status": "success",
            "part_details": result_json,
            "sources": sources
        })
        
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


@app.route('/api/find_vendors', methods=['POST'])
def find_vendors():
    """Find qualified vendors in a specific state using SAM.gov Entity API + web search."""
    data = request.json
    state = data.get('state', '')
    naics_code = data.get('naicsCode', '')
    title = data.get('title', '')
    notice_id = data.get('noticeId', '')
    
    vendors = []
    seen_names = set()
    
    # ── Method 1: SAM.gov Entity API ──────────────────────────────
    SAM_ENTITY_API = "https://api.sam.gov/entity-information/v3/entities"
    try:
        entity_params = {
            "api_key": SAM_API_KEY,
            "registrationStatus": "A",  # Active registrations only
            "includeSections": "entityRegistration,coreData,assertions,certifications",
            "page": 0,
            "size": 15,
        }
        
        if state:
            entity_params["physicalAddressStateCode"] = state
        if naics_code:
            entity_params["naicsCode"] = naics_code
            
        entity_res = requests.get(SAM_ENTITY_API, params=entity_params, timeout=15)
        if entity_res.status_code == 200:
            entity_data = entity_res.json()
            entities = entity_data.get('entityData', [])
            
            for ent in entities:
                reg = ent.get('entityRegistration', {})
                core = ent.get('coreData', {})
                assertions = ent.get('assertions', {})
                
                name = reg.get('legalBusinessName', 'Unknown Business')
                if name.lower() in seen_names:
                    continue
                seen_names.add(name.lower())
                
                addr = core.get('physicalAddress', {})
                uei = reg.get('ueiSAM', '')
                cage = reg.get('cageCode', '')
                
                # Extract certifications
                certs = []
                goods_and_services = assertions.get('goodsAndServices', {})
                if goods_and_services:
                    naics_list = goods_and_services.get('naicsList', [])
                    for n in naics_list[:5]:
                        code = n.get('naicsCode', '')
                        desc = n.get('naicsDescription', '')
                        if code:
                            certs.append(f"NAICS {code}")
                
                # Check for small biz certs
                sb_types = reg.get('businessTypes', [])
                if isinstance(sb_types, list):
                    for bt in sb_types[:5]:
                        if isinstance(bt, str):
                            certs.append(bt)
                        elif isinstance(bt, dict):
                            certs.append(bt.get('shortDescription', bt.get('businessTypeCode', '')))
                
                vendors.append({
                    'name': name,
                    'city': addr.get('city', ''),
                    'state': addr.get('stateOrProvinceCode', state),
                    'zip': addr.get('zipCode', ''),
                    'uei': uei,
                    'cage': cage,
                    'certs': certs[:8],  # Limit to 8 cert tags
                    'email': core.get('electronicBusinessPointOfContact', {}).get('email', ''),
                    'sam_url': f"https://sam.gov/entity/{uei}/coreData" if uei else '',
                    'source': 'SAM.gov'
                })
    except Exception as e:
        print(f"[Vendor Finder] SAM Entity API error: {e}")
    
    # ── Method 2: DuckDuckGo web search fallback ──────────────────
    if len(vendors) < 5 and (state or naics_code):
        try:
            search_terms = []
            if naics_code:
                search_terms.append(naics_code)
            if title:
                # Extract key service terms from the title
                for word in title.split()[:4]:
                    if len(word) > 3 and word.lower() not in ('the', 'and', 'for', 'with'):
                        search_terms.append(word)
            
            query = f"government contractor {' '.join(search_terms)} {state} certified"
            web_results = duckduckgo_scrape(query.replace(' price', ''))
            
            for r in web_results[:5]:
                name = r.get('supplier', 'Unknown')
                if name.lower() in seen_names:
                    continue
                seen_names.add(name.lower())
                
                vendors.append({
                    'name': name,
                    'city': '',
                    'state': state,
                    'zip': '',
                    'uei': '',
                    'cage': '',
                    'certs': ['Web Result'],
                    'email': '',
                    'sam_url': r.get('url', ''),
                    'source': 'Web Search'
                })
        except Exception as e:
            print(f"[Vendor Finder] Web search error: {e}")
    
    return jsonify({
        'status': 'success',
        'vendors': vendors[:15],  # Cap at 15 results
        'state': state,
        'naicsCode': naics_code
    })

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
    
    app.run(debug=False, port=5000, use_reloader=False)
