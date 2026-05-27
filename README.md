# POS Intent Tracker

Dynamic sales intelligence tool for identifying businesses with POS buying intent, searchable by ZIP code.

## Data Sources

| Source | What It Pulls | SFDC Fields |
|--------|--------------|-------------|
| **Leads (Competitor POS)** | Businesses currently using competitor POS systems | `Competitor_POS__c`, `mkto2__Lead_Score__c`, `mkto_Behavior_Score__c`, `DS_Lead_Score__c` |
| **Accounts (6Sense/Engagio)** | Accounts with intent signals synced from 6Sense | `engagio__Status__c`, `engagio__qualification_score__c`, `engagio__IntentMinutesLast30Days__c` |
| **Lead Gen Dashboard** | MQLs from go/LeadgenDash (Marketo behavioral scoring) | `LeadSource`, `Status`, `mkto_Behavior_Score__c` |

## Quick Start

```bash
# 1. Refresh data from SFDC (requires WARP VPN + sq agent-tools)
./scripts/refresh.sh "94103,94107,94110"

# 2. Open the app
open index.html
```

## Refresh with custom ZIPs

```bash
# San Francisco
./scripts/refresh.sh "94103,94107,94110,94102,94105,94114,94117"

# Oakland
./scripts/refresh.sh "94601,94602,94603,94606,94607,94609,94610"

# All Bay Area (broader pull)
./scripts/refresh.sh "94103,94107,94110,94102,94105,94114,94117,94601,94602,94607"
```

## Project Structure

```
pos-intent-tracker/
├── index.html              ← Main app (open in browser)
├── data/
│   ├── accounts.json       ← Combined data (auto-generated)
│   ├── leads_raw.json      ← Raw SFDC lead query results
│   └── accounts_raw.json   ← Raw SFDC account query results
├── scripts/
│   ├── refresh.sh          ← Data pull script (run this to refresh)
│   └── build_data.py       ← Normalizes raw SFDC → accounts.json
└── README.md
```

## Connectors

The app has three tabbed connectors:

1. **Salesforce** — Direct SOQL queries against `squareinc.my.salesforce.com`
2. **6Sense** — Intent signals via `engagio__` fields (synced into SFDC)
3. **Lead Gen Dashboard** — MQL data from go/LeadgenDash (Looker)

## Deploying to URL

```bash
# Push to squareup GitHub org
git init
git remote add origin git@github.com:squareup/pos-intent-tracker.git
git add .
git commit -m "Initial commit — POS Intent Tracker"
git push -u origin main

# Enable GitHub Pages in repo settings → serves at:
# https://squareup.github.io/pos-intent-tracker
```

## Prerequisites

- WARP VPN connected (`warp-cli status`)
- `sq agent-tools` installed (`sq packs add agent-tools`)
- Salesforce-sq extension connected (visit go/agent-tools)
