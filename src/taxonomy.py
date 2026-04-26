"""
UNMAPPED Portable Skills & Role Taxonomy
=========================================

This module defines the portable taxonomy that all messy informal
experience and localized labor data is normalized against. It is the
defensible data infrastructure layer.

Stable IDs (e.g. GR-REPAIR-001) are permanent. They are designed to
support cross-system interoperability the way ISCO-08 codes do — the
codes do not change as labels are translated or localized.

Each canonical role carries:
  - global_role_id: stable, opaque identifier
  - title: standardized human-readable label
  - level: career stage
  - isco_like_category: nearest ISCO-08 group (informational)
  - skill_signals: keywords/phrases that map raw text to this role
  - core_skills: canonical skills central to the role
  - bridge_skills: skills that bridge a profile from "almost matches"
    to "ready" — the explicit upskilling target
  - cross_market_examples: regional surface labels
  - opportunity_types: realistic pathways (employment, self-employment,
    gig, training)
  - automation_exposure_default: Frey-Osborne-style proxy (0–1)

The skill normalization map below covers both formal and INFORMAL
skill markers (phone repair, mobile money, WhatsApp Business, sari-
sari, etc.) — this is critical for surfacing invisible talent.
"""

# ---------------------------------------------------------------------------
# Global Role Taxonomy
# ---------------------------------------------------------------------------

GLOBAL_TAXONOMY = {
    "GR-REPAIR-001": {
        "title": "Device Repair Technician",
        "level": "Entry",
        "isco_like_category": "ISCO-08 7421 — Electronics Mechanics & Servicers",
        "skill_signals": [
            "phone repair", "repair phones", "screen replacement",
            "soldering", "battery diagnostics", "circuit", "troubleshooting",
            "hardware troubleshooting", "device repair", "laptop repair",
            "electronics", "fixed phones",
        ],
        "core_skills": [
            "Repair Diagnostics", "Hardware Troubleshooting",
            "Customer Service", "Mobile Money",
        ],
        "bridge_skills": [
            "Formal certification (NVTI / TESDA NC II)",
            "Inventory tracking with Excel",
            "Basic digital marketing for repair shop",
        ],
        "cross_market_examples": {
            "Ghana": "Phone Repair Stall Operator (Accra, Kumasi)",
            "Nigeria": "Repair Technician (Computer Village, Lagos)",
            "Philippines": "Device Repair / IT Support (provincial)",
        },
        "opportunity_types": ["self-employment", "gig", "employment (small shop)", "training pathway"],
        "automation_exposure_default": 0.22,
    },

    "GR-DIGSUP-001": {
        "title": "Digital Support Assistant",
        "level": "Entry",
        "isco_like_category": "ISCO-08 4222 — Contact Centre Information Clerks (digital adjacent)",
        "skill_signals": [
            "whatsapp business", "customer chat", "online customer support",
            "virtual assistant", "va work", "remote support",
            "digital support", "online support", "social media support",
            "youtube coding", "self-taught", "html", "wordpress", "shopify",
        ],
        "core_skills": [
            "Customer Service", "Digital Literacy", "Written Communication",
            "Basic Web/HTML",
        ],
        "bridge_skills": [
            "English written communication upskilling",
            "Stable broadband / quiet workspace",
            "Platform onboarding (Upwork, Fiverr, Toptal, OnlineJobs.ph)",
        ],
        "cross_market_examples": {
            "Ghana": "Junior digital support / WhatsApp commerce",
            "Nigeria": "Remote customer support / WordPress freelancer",
            "Philippines": "Virtual assistant / Shopify VA",
        },
        "opportunity_types": ["gig", "employment (remote)", "self-employment", "training pathway"],
        "automation_exposure_default": 0.45,
    },

    "GR-DATA-001": {
        "title": "Data Analyst",
        "level": "Entry",
        "isco_like_category": "ISCO-08 2511 — Systems Analysts (junior data adjacent)",
        "skill_signals": [
            "data analyst", "mis executive", "mis specialist",
            "reporting analyst", "insights analyst", "insights associate",
            "bi analyst", "reports analyst", "analytics", "dashboard",
            "sql", "power bi", "tableau", "looker",
        ],
        "core_skills": ["SQL", "Excel", "Dashboarding", "Reporting"],
        "bridge_skills": [
            "Intermediate SQL (joins, window functions)",
            "Python pandas basics",
            "Portfolio of 2–3 dashboard projects",
        ],
        "cross_market_examples": {
            "Ghana": "MIS / Reporting Analyst (banking, telco)",
            "Nigeria": "Insights Analyst (fintech, NGO M&E)",
            "Philippines": "MIS Specialist / Reports Analyst (shared services)",
        },
        "opportunity_types": ["employment", "training pathway"],
        "automation_exposure_default": 0.55,
    },

    "GR-OPS-001": {
        "title": "Operations Data Coordinator",
        "level": "Entry",
        "isco_like_category": "ISCO-08 4131 — Typists & Data Entry Clerks",
        "skill_signals": [
            "data entry", "encoder", "computer operator", "bpo data agent",
            "wfm", "workforce mgmt", "reconciliation officer",
            "office admin", "ops coordinator", "operations data",
            "helpdesk", "encoding", "barangay encoder",
        ],
        "core_skills": [
            "Excel", "Data Entry", "Process Documentation", "Reporting",
        ],
        "bridge_skills": [
            "Excel intermediate (pivots, vlookup, basic VBA)",
            "Basic SQL queries",
            "Touch typing speed >40 wpm",
        ],
        "cross_market_examples": {
            "Ghana": "Operations clerk / NGO data entry",
            "Nigeria": "OND-track operations clerk / NGO M&E",
            "Philippines": "Encoder / barangay clerical / shared services",
        },
        "opportunity_types": ["employment", "gig (short-term contract)", "training pathway"],
        "automation_exposure_default": 0.55,
    },

    "GR-FIN-001": {
        "title": "Finance Operations Associate",
        "level": "Entry",
        "isco_like_category": "ISCO-08 3313 — Accounting Associate Professionals",
        "skill_signals": [
            "bookkeeper", "bookkeeping", "account officer", "junior accountant",
            "financial analyst", "fp&a", "accounts", "accountancy",
            "reconciliation", "ledger", "quickbooks", "xero", "tally", "sage",
            "cash counting", "daily reconciliation",
        ],
        "core_skills": [
            "Accounting Software", "Excel", "Reconciliation",
            "Financial Reporting",
        ],
        "bridge_skills": [
            "Formal credential (ICAG / ICAN partial / CPA review)",
            "Cloud accounting (QuickBooks Online, Xero)",
            "Excel modeling (variance, three-statement basics)",
        ],
        "cross_market_examples": {
            "Ghana": "Account Officer (Tally/Sage)",
            "Nigeria": "Account Officer / Banking ops",
            "Philippines": "Junior Accountant (QuickBooks/Xero)",
        },
        "opportunity_types": ["employment", "training pathway"],
        "automation_exposure_default": 0.50,
    },

    "GR-BPO-001": {
        "title": "Customer Support / BPO Agent",
        "level": "Entry",
        "isco_like_category": "ISCO-08 4222 — Contact Centre Information Clerks",
        "skill_signals": [
            "call center", "bpo", "customer service", "customer support",
            "customer chat", "voice account", "english communication",
            "customer dispute",
        ],
        "core_skills": [
            "Customer Service", "Spoken English", "Digital Literacy",
            "Conflict Resolution",
        ],
        "bridge_skills": [
            "Industry-specific certs (healthcare BPO, finance BPO)",
            "Stable internet and quiet workspace",
            "Typing speed and CRM tool fluency",
        ],
        "cross_market_examples": {
            "Ghana": "Outsourced customer support (emerging)",
            "Nigeria": "BPO entry agent (Lagos, Abuja)",
            "Philippines": "BPO / contact centre agent (large formal sector)",
        },
        "opportunity_types": ["employment", "training pathway"],
        "automation_exposure_default": 0.40,
    },

    "GR-MICRO-001": {
        "title": "Microenterprise Operator",
        "level": "Entry",
        "isco_like_category": "ISCO-08 5221 — Shopkeepers / 5223 — Shop Sales Assistants",
        "skill_signals": [
            "sells", "trading", "market trading", "buying/selling",
            "sari-sari", "stall", "kiosk", "online seller", "fabric",
            "tailoring", "hairdresser", "salon", "skincare",
            "whatsapp groups", "instagram", "shopee", "lazada",
            "mobile money", "momo",
        ],
        "core_skills": [
            "Sales", "Customer Relationship Management", "Mobile Money",
            "Inventory Tracking",
        ],
        "bridge_skills": [
            "Basic bookkeeping",
            "Digital marketing (Canva, social ads)",
            "Inventory tracking in Excel/Google Sheets",
        ],
        "cross_market_examples": {
            "Ghana": "WhatsApp/Instagram trader / market vendor",
            "Nigeria": "Market trader / Instagram vendor / tailor",
            "Philippines": "Sari-sari operator / Shopee/Lazada seller",
        },
        "opportunity_types": ["self-employment", "gig", "training pathway"],
        "automation_exposure_default": 0.10,
    },

    "GR-WEBNC-001": {
        "title": "Junior Web Support / No-Code Assistant",
        "level": "Entry",
        "isco_like_category": "ISCO-08 3514 — Web Technicians",
        "skill_signals": [
            "html", "css", "wordpress", "shopify", "no-code", "no code",
            "canva", "javascript", "youtube coding", "bootcamp",
            "fullstack", "full stack", "self-taught coder",
        ],
        "core_skills": [
            "HTML/CSS", "Basic JavaScript", "Web Tools",
            "Digital Literacy",
        ],
        "bridge_skills": [
            "Public portfolio (GitHub or live sites)",
            "Stable broadband",
            "One paid client engagement to break credentialing wall",
        ],
        "cross_market_examples": {
            "Ghana": "Self-taught web freelancer",
            "Nigeria": "WordPress freelancer / Andela bootcamp graduate",
            "Philippines": "Shopify VA / Webflow assistant",
        },
        "opportunity_types": ["gig", "self-employment", "employment (remote)", "training pathway"],
        "automation_exposure_default": 0.35,
    },
}


# ---------------------------------------------------------------------------
# Skill normalization map (formal + informal markers)
# ---------------------------------------------------------------------------

SKILL_NORMALIZATION_MAP = {
    # === Informal / repair / hands-on ===
    "phone repair": "Repair Diagnostics",
    "repair phones": "Repair Diagnostics",
    "screen replacement": "Repair Diagnostics",
    "battery diagnostics": "Repair Diagnostics",
    "soldering": "Hardware Troubleshooting",
    "circuit": "Hardware Troubleshooting",
    "troubleshooting": "Hardware Troubleshooting",
    "hardware troubleshooting": "Hardware Troubleshooting",
    "os reinstall": "Hardware Troubleshooting",
    "networking": "Hardware Troubleshooting",
    "repair diagnostics": "Repair Diagnostics",

    # === Microenterprise / sales ===
    "sells": "Sales",
    "selling": "Sales",
    "trading": "Sales",
    "negotiation": "Sales",
    "buying/selling": "Sales",
    "customer follow-up": "Customer Relationship Management",
    "customer relationship": "Customer Relationship Management",
    "client scheduling": "Customer Relationship Management",
    "inventory tracking": "Inventory Tracking",
    "inventory": "Inventory Tracking",
    "product listing": "E-commerce Operations",

    # === Mobile money / payments ===
    "mobile money": "Mobile Money",
    "momo": "Mobile Money",
    "mtn momo": "Mobile Money",
    "vodafone cash": "Mobile Money",
    "opay": "Mobile Money",
    "paga": "Mobile Money",
    "moniepoint": "Mobile Money",
    "gcash": "Mobile Money",
    "maya": "Mobile Money",
    "interswitch": "Payments Systems",
    "paystack": "Payments Systems",
    "flutterwave": "Payments Systems",
    "pos": "POS / Payments",
    "pos reconciliation": "POS / Payments",

    # === Customer service / comms ===
    "customer service": "Customer Service",
    "customer support": "Customer Service",
    "customer chat": "Customer Service",
    "customer payments": "Customer Service",
    "took orders": "Customer Service",
    "order taking": "Customer Service",
    "orders": "Customer Service",
    "handled complaints": "Conflict Resolution",
    "food service": "Customer Service",
    "restaurant customer service": "Customer Service",
    "restaurant": "Customer Service",
    "waiter": "Customer Service",
    "waitress": "Customer Service",
    "server": "Customer Service",
    "customer care": "Customer Service",
    "front desk": "Customer Service",
    "whatsapp business": "Digital Communication",
    "whatsapp": "Digital Communication",
    "chat": "Digital Communication",
    "email handling": "Written Communication",
    "english communication": "Spoken English",
    "english customer support": "Spoken English",

    # === Digital literacy / web ===
    "html": "Basic Web/HTML",
    "html/css": "Basic Web/HTML",
    "css": "Basic Web/HTML",
    "javascript": "Basic JavaScript",
    "wordpress": "Web Tools",
    "wordpress page": "Web Tools",
    "shopify": "Web Tools",
    "github": "Web Tools",
    "portfolio": "Web Tools",
    "landing page": "Basic Web/HTML",
    "canva": "Digital Design (Canva)",
    "social media": "Digital Marketing",
    "digital marketing": "Digital Marketing",
    "content creation": "Digital Marketing",
    "no-code": "No-Code Tools",
    "no code": "No-Code Tools",
    "youtube coding": "Self-Taught Coding",
    "youtube videos": "Self-Taught Coding",
    "youtube tutorials": "Self-Taught Coding",
    "freecodecamp": "Self-Taught Coding",
    "learned how to code": "Self-Taught Coding",
    "self-taught": "Self-Taught Coding",
    "self taught": "Self-Taught Coding",

    # === E-commerce platforms ===
    "shopee": "E-commerce Platform",
    "lazada": "E-commerce Platform",
    "instagram": "E-commerce Platform",
    "facebook marketplace": "E-commerce Platform",
    "online seller": "E-commerce Operations",
    "online selling": "E-commerce Operations",

    # === Spreadsheets ===
    "excel": "Excel",
    "vlookup": "Excel",
    "pivot": "Excel",
    "spreadsheet": "Excel",
    "googlesheets": "Excel",
    "google sheets": "Excel",
    "vba": "Excel",
    "power query": "Excel",

    # === SQL ===
    "sql": "SQL",
    "postgres": "SQL",
    "mysql": "SQL",
    "snowflake": "SQL",
    "bigquery": "SQL",
    "redshift": "SQL",
    "sql server": "SQL",

    # === Programming / data ===
    "python": "Python",
    "pandas": "Python",
    "numpy": "Python",
    "jupyter": "Python",
    "r": "R",

    # === BI / Dashboards ===
    "tableau": "Dashboarding",
    "power bi": "Dashboarding",
    "powerbi": "Dashboarding",
    "looker": "Dashboarding",
    "dashboard": "Dashboarding",
    "ssrs": "Dashboarding",

    # === ETL / Data Eng ===
    "airflow": "ETL/Pipelines",
    "dbt": "ETL/Pipelines",
    "etl": "ETL/Pipelines",
    "alteryx": "ETL/Pipelines",

    # === Accounting / Finance ===
    "quickbooks": "Accounting Software",
    "xero": "Accounting Software",
    "tally": "Accounting Software",
    "sage": "Accounting Software",
    "netsuite": "Accounting Software",
    "sap": "Accounting Software",
    "anaplan": "Financial Modeling",
    "reconciliation": "Reconciliation",
    "recon": "Reconciliation",
    "fp&a": "Financial Modeling",
    "modeling": "Financial Modeling",
    "variance": "Financial Modeling",
    "bookkeeping": "Bookkeeping",
    "cash counting": "Bookkeeping",
    "daily reconciliation": "Reconciliation",

    # === Survey / M&E ===
    "kobotoolbox": "Survey/M&E Tools",
    "kobo": "Survey/M&E Tools",
    "data collection": "Survey/M&E Tools",

    # === Banking / Fintech regional ===
    "flexcube": "Core Banking Systems",
    "finacle": "Core Banking Systems",

    # === CRM / Sales ===
    "salesforce": "CRM",
    "hubspot": "CRM",

    # === Analytics platforms ===
    "ga4": "Product Analytics",
    "mixpanel": "Product Analytics",
    "amplitude": "Product Analytics",
    "segment": "Product Analytics",

    # === Statistics / ML ===
    "statistical": "Statistical Modeling",
    "backtest": "Statistical Modeling",
    "a/b test": "Statistical Modeling",

    # === Ops / data entry ===
    "data entry": "Data Entry",
    "encoding": "Data Entry",
    "encoder": "Data Entry",
    "typing": "Data Entry",
    "order logs": "Process Documentation",
    "order tracking": "Process Documentation",
    "booking": "Customer Relationship Management",
    "bookings": "Customer Relationship Management",
    "appointment booking": "Customer Relationship Management",
    "appointment scheduling": "Customer Relationship Management",
    "call center training": "Spoken English",
    "call center course": "Spoken English",
    "crm": "CRM",
    "pos system": "POS / Payments",
    "cashier": "POS / Payments",

    # === Languages & soft skills (informal evidence) ===
    "tutoring": "Teaching/Tutoring",
    "translation": "Translation",
    "community mobilization": "Community Engagement",

    # === Tailoring / craft (informal) ===
    "sewing": "Tailoring/Craft",
    "tailoring": "Tailoring/Craft",
    "hairdresser": "Personal Services",
    "salon": "Personal Services",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_role_by_id(role_id: str) -> dict:
    return GLOBAL_TAXONOMY.get(role_id, {})


def all_roles() -> list:
    return list(GLOBAL_TAXONOMY.items())
