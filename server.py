"""
ScrapperGov — SAM.gov Contract Opportunities Scraper
Flask backend that proxies requests to the SAM.gov public API
"""

import os
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static")
CORS(app)

SAM_API_BASE = "https://api.sam.gov/opportunities/v2/search"
SAM_API_KEY = os.getenv("SAM_API_KEY", "DEMO_KEY")

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

    try:
        resp = requests.get(SAM_API_BASE, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Enrich response with metadata
        data["appliedFilters"] = {
            k: v for k, v in params.items() if k != "api_key"
        }

        return jsonify(data)

    except requests.exceptions.HTTPError as e:
        return jsonify({
            "error": f"SAM.gov API Error: {e.response.status_code}",
            "message": e.response.text if e.response else str(e),
        }), e.response.status_code if e.response else 500

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "Connection Error",
            "message": str(e),
        }), 502


if __name__ == "__main__":
    print("\n🏛️  ScrapperGov — SAM.gov Contract Scraper")
    print(f"   API Key: {'✅ Loaded' if SAM_API_KEY != 'DEMO_KEY' else '⚠️  Using DEMO_KEY (limited)'}")
    print(f"   Server:  http://localhost:5000\n")
    app.run(debug=True, port=5000)
