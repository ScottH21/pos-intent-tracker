#!/usr/bin/env python3
"""
Combines raw SFDC Lead + Account data into a single accounts.json
for the POS Intent Tracker frontend.
"""
import json
import sys
from datetime import datetime

DATA_DIR = sys.argv[1] if len(sys.argv) > 1 else "data"
OUTPUT = f"{DATA_DIR}/accounts.json"

def load(path):
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        if isinstance(data, list):
            return data
        return []
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"  ⚠ Could not load {path}: {e}")
        return []

# Load raw files
leads = load(f"{DATA_DIR}/leads_raw.json")
accounts = load(f"{DATA_DIR}/accounts_raw.json")

print(f"  Loaded {len(leads)} leads, {len(accounts)} accounts")

# Normalize leads
records = []
for i, l in enumerate(leads):
    behavior_score = l.get("mkto_Behavior_Score__c") or 0
    lead_score = l.get("mkto2__Lead_Score__c") or 0
    ds_score = l.get("DS_Lead_Score__c") or 0
    
    # Intent score: weighted combo of available scores
    # If we have behavior score, weight it heavily; otherwise use lead score
    if behavior_score > 0:
        intent = min(100, int(behavior_score * 0.6 + lead_score * 0.3 + ds_score * 0.1))
    elif lead_score > 0:
        intent = min(100, int(lead_score * 1.5))
    else:
        # Has competitor POS data = some intent signal
        intent = 45  # baseline for having competitor data

    # Build signals list
    signals = []
    competitor = l.get("Competitor_POS__c", "")
    if competitor and competitor not in ("Unknown", "New Business", "Other"):
        signals.append(f"Currently on {competitor}")
    elif competitor == "New Business":
        signals.append("New business — no POS yet")
    
    lead_source = l.get("LeadSource", "")
    if lead_source:
        signals.append(f"Source: {lead_source}")
    
    # Status mapping
    sfdc_status = l.get("Status", "")
    if sfdc_status in ("Qualified", "Working - Contacted"):
        status = "hot"
    elif sfdc_status in ("Open", "Open - Not Contacted"):
        status = "new"
    elif sfdc_status == "Dripped":
        status = "active"
    else:
        status = "active"

    # Employee range
    emp = l.get("NumberOfEmployees") or 0
    if emp == 0:
        emp_range = "Unknown"
    elif emp <= 5:
        emp_range = "1-5"
    elif emp <= 12:
        emp_range = "5-12"
    elif emp <= 50:
        emp_range = "12-50"
    elif emp <= 200:
        emp_range = "50-200"
    else:
        emp_range = "200+"

    records.append({
        "id": i + 1,
        "sfdcId": l.get("Id", ""),
        "companyName": l.get("Company", l.get("Name", "Unknown")),
        "contactName": l.get("Name", ""),
        "domain": "",
        "zip": l.get("PostalCode", ""),
        "city": l.get("City", ""),
        "state": l.get("State", ""),
        "industry": l.get("Industry") or "Unknown",
        "intentScore": intent,
        "employees": emp_range,
        "annualRevenue": "",
        "signals": signals,
        "status": status,
        "lastActivity": sfdc_status,
        "lastActivityDate": "",
        "contacts": 1,
        "notes": f"Competitor POS: {competitor}" if competitor else "",
        "trending": intent >= 75,
        "type": "lead",
        "competitorPOS": competitor,
        "marketoBehaviorScore": behavior_score,
        "marketoLeadScore": lead_score,
        "dsLeadScore": ds_score,
        "leadSource": lead_source,
        "leadStatus": sfdc_status
    })

# Normalize accounts (enrichment layer)
offset = len(records)
for i, a in enumerate(accounts):
    records.append({
        "id": offset + i + 1,
        "sfdcId": a.get("Id", ""),
        "companyName": a.get("Name", "Unknown"),
        "contactName": "",
        "domain": "",
        "zip": a.get("BillingPostalCode", ""),
        "city": a.get("BillingCity", ""),
        "state": a.get("BillingState", ""),
        "industry": a.get("Industry") or "Unknown",
        "intentScore": 40,  # baseline — no intent fields available due to timeout
        "employees": str(a.get("NumberOfEmployees") or "Unknown"),
        "annualRevenue": "",
        "signals": [f"Industry: {a.get('Industry', 'Unknown')}"],
        "status": "active",
        "lastActivity": "",
        "lastActivityDate": "",
        "contacts": 1,
        "notes": f"SFDC Account — {a.get('Industry', '')}",
        "trending": False,
        "type": "account",
        "sixsenseBuyingStage": a.get("engagio__Status__c", ""),
        "qualificationScore": a.get("engagio__qualification_score__c", 0),
    })

# Sort by intent score descending
records.sort(key=lambda x: x.get("intentScore", 0), reverse=True)

# Build output
output = {
    "meta": {
        "refreshed_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_records": len(records),
        "leads_count": len(leads),
        "accounts_count": len(accounts),
        "sources": ["sfdc_leads_competitor_pos", "sfdc_accounts"],
        "zips_queried": list(set(r["zip"] for r in records if r["zip"]))
    },
    "records": records
}

with open(OUTPUT, "w") as f:
    json.dump(output, f, indent=2)

print(f"  ✓ Wrote {len(records)} records to {OUTPUT}")
print(f"    - {len(leads)} leads (Competitor_POS__c)")
print(f"    - {len(accounts)} accounts")
print(f"    - ZIPs: {', '.join(output['meta']['zips_queried'][:10])}")
