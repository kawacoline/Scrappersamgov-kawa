# 🏛️ ScrapperGov — SAM.gov Federal Contract Intelligence Platform & Scraper

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://python.org)
[![Backend Framework](https://img.shields.io/badge/Framework-Flask%20%2F%20REST%20API-red.svg)](https://flask.palletsprojects.com/)
[![Federal Source](https://img.shields.io/badge/Data%20Source-SAM.gov%20API%20v2-blue.svg)](https://sam.gov)
[![Frontend](https://img.shields.io/badge/Frontend-HTML5%20%2F%20CSS3%20%2F%20JS-orange.svg)](https://developer.mozilla.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**ScrapperGov** is an automated intelligence suite and search engine designed to discover, filter, and extract high-value **US Federal Government contracting opportunities** from the official **SAM.gov (System for Award Management)** API.

Featuring a robust Flask REST proxy backend and a clean, responsive single-page application (SPA), ScrapperGov eliminates the manual friction of navigating federal procurement portals by categorizing contracts by NAICS industry codes, tracking past awards, and extracting actionable solicitation data.

---

## 🏛️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        SAM.GOV FEDERAL APIS                            │
│  • Opportunities API v2 (Active RFPs, RFIs, Solicitations, Sources Sought)│
│  • Contract Awards API v1 (Historical pricing, incumbents, vendor data)│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ JSON Feeds
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      FLASK INTELLIGENCE BACKEND                        │
│  • Concurrent asynchronous request proxying & rate-limit handling      │
│  • Industry NAICS Code Presets (IT, Logistics, Software, Janitorial)   │
│  • Document & Attachment extraction engine                             │
│  • Supplier & Sourcing reconciliation pipeline                         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Cleaned & Structured Data
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                    RESPONSIVE WEB DASHBOARD (SPA)                      │
│  • Instant search by keyword, set-aside status, agency, and deadline   │
│  • Detailed modal breakdown for contract specifications & contacts     │
│  • One-click export to JSON and structured tabular datasets            │
└────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Core Capabilities

- **Pre-Configured NAICS Industry Taxonomy**: Instantly query high-demand federal sectors without manually looking up North American Industry Classification System codes:
  - **IT Services & Software Licensing** (`541511`, `541512`, `511210`, `518210`)
  - **Delivery & Courier Logistics** (`492110`, `492210`, `484110`)
  - **Maintenance & Facilities Support** (`561720`, `561210`, `238220`)
  - **Office Supplies & Equipment** (`424120`, `423420`)
- **Historical Contract Awards Analysis**: Query historical pricing, winning vendors, and award amounts to conduct competitive intelligence before bidding.
- **Attachment Extraction Pipeline**: Analyzes solicitation packets and attachment metadata to identify statements of work (SOW) and critical submission criteria.
- **Modern Interactive Dashboard**: Filter contracts by notice type (*Presolicitation*, *Combined Synopsis/Solicitation*, *Sources Sought*), set-aside program (*Small Business*, *8(a)*, *SDVOSB*), or department.

---

## 🛠️ Quickstart & Setup

### 1. Prerequisites
- **Python 3.10+**
- **SAM.gov API Key** (Obtain a free public API key at [sam.gov](https://sam.gov))

### 2. Clone & Install
```bash
git clone https://github.com/kawacoline/Scrappersamgov-kawa.git
cd Scrappersamgov-kawa
setup.bat
```

*(On Linux / macOS)*:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Credentials
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```

Add your SAM.gov key:
```ini
SAM_API_KEY=your_sam_api_key_here
PORT=5000
```

### 4. Run the Application
Launch via the batch script:
```bash
start.bat
```

Or directly:
```bash
python server.py
```

Open your browser at **`http://localhost:5000`** to access the dashboard.

---

## 📁 Repository Structure

```
├── server.py               # Flask backend API & procurement proxy engine
├── static/                 # Single-page web dashboard assets
│   ├── index.html          # Clean procurement dashboard interface
│   ├── app.js              # Real-time search, filtering, and modal controller
│   └── style.css           # Modern aesthetic design system
├── scraped_data/           # Cached sample payloads and export directory
├── requirements.txt        # Production dependencies
├── setup.bat / start.bat   # Windows setup and launch automation
└── .env.example            # Environment variable template
```

---

## 👨‍💻 Author

**Hazael**  
*Full Stack Software Engineer & Data Engineering Specialist*  
- **GitHub**: [@kawacoline](https://github.com/kawacoline)  
- **Email**: kawacoline@gmail.com  
- **Portfolio**: [hazael.dev](https://github.com/kawacoline)

---

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.
