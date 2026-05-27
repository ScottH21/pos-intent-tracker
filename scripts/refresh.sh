#!/bin/bash
# POS Intent Tracker — Full Data Refresh
# Pulls enriched SFDC data for Austin & San Antonio field sales
# Usage: ./scripts/refresh.sh [ZIP_PREFIXES]
# Example: ./scripts/refresh.sh "787,782,781"

set -e
cd "$(dirname "$0")/.."

ZIP_PREFIXES="${1:-787,782,781}"
TIMEOUT=45
DATA_DIR="data"
RAW_DIR="$DATA_DIR/raw"
mkdir -p "$RAW_DIR"

echo "═══════════════════════════════════════════════════════════"
echo "  POS Intent Tracker — Full Data Refresh"
echo "  Territory: ZIP prefixes $ZIP_PREFIXES"
echo "═══════════════════════════════════════════════════════════"

# Check prerequisites
if ! command -v sq &>/dev/null; then echo "❌ sq CLI not found"; exit 1; fi
if ! warp-cli status 2>/dev/null | grep -q "Connected"; then echo "⚠️  WARP may not be connected"; fi

# ─── QUERY 1: Leads with Competitor POS (San Antonio) ─────────────────────
echo ""
echo "📡 [1/5] Leads with Competitor POS (SA area)..."
sq agent-tools salesforce-sq query --soql \
  "SELECT Id, Company, FirstName, LastName, Title, Phone, Email, Website, \
   Street, City, State, PostalCode, Industry, \
   Competitor_POS__c, mkto2__Lead_Score__c, mkto_Behavior_Score__c, DS_Lead_Score__c, \
   LeadSource, Status, NumberOfEmployees, AnnualRevenue, \
   Owner.Name, LastActivityDate, CreatedDate \
   FROM Lead \
   WHERE State = 'TX' AND PostalCode LIKE '782%' \
   AND Competitor_POS__c != null \
   ORDER BY mkto_Behavior_Score__c DESC NULLS LAST \
   LIMIT 200" --timeout $TIMEOUT 2>/dev/null > "$RAW_DIR/leads_sa_competitive.json" && \
  echo "  ✓ SA competitive leads saved" || echo "  ⚠️  SA competitive query failed"

# ─── QUERY 2: Leads with Competitor POS (Austin) ──────────────────────────
echo "📡 [2/5] Leads with Competitor POS (Austin area)..."
sq agent-tools salesforce-sq query --soql \
  "SELECT Id, Company, FirstName, LastName, Title, Phone, Email, Website, \
   Street, City, State, PostalCode, Industry, \
   Competitor_POS__c, mkto2__Lead_Score__c, mkto_Behavior_Score__c, DS_Lead_Score__c, \
   LeadSource, Status, NumberOfEmployees, AnnualRevenue, \
   Owner.Name, LastActivityDate, CreatedDate \
   FROM Lead \
   WHERE State = 'TX' AND PostalCode LIKE '787%' \
   AND Competitor_POS__c != null \
   ORDER BY mkto_Behavior_Score__c DESC NULLS LAST \
   LIMIT 200" --timeout $TIMEOUT 2>/dev/null > "$RAW_DIR/leads_atx_competitive.json" && \
  echo "  ✓ Austin competitive leads saved" || echo "  ⚠️  Austin competitive query failed"

# ─── QUERY 3: High-engagement leads (Marketo 20+) ─────────────────────────
echo "📡 [3/5] High-engagement leads (Marketo behavior 20+)..."
sq agent-tools salesforce-sq query --soql \
  "SELECT Id, Company, FirstName, LastName, Title, Phone, Email, Website, \
   Street, City, State, PostalCode, Industry, \
   Competitor_POS__c, mkto2__Lead_Score__c, mkto_Behavior_Score__c, DS_Lead_Score__c, \
   LeadSource, Status, NumberOfEmployees, AnnualRevenue, \
   Owner.Name, LastActivityDate, CreatedDate \
   FROM Lead \
   WHERE State = 'TX' AND PostalCode LIKE '78%' \
   AND mkto_Behavior_Score__c >= 20 \
   ORDER BY mkto_Behavior_Score__c DESC \
   LIMIT 200" --timeout $TIMEOUT 2>/dev/null > "$RAW_DIR/leads_high_engagement.json" && \
  echo "  ✓ High-engagement leads saved" || echo "  ⚠️  High-engagement query failed"

# ─── QUERY 4: Accounts with Revenue & Employees ───────────────────────────
echo "📡 [4/5] Accounts with revenue data..."
sq agent-tools salesforce-sq query --soql \
  "SELECT Id, Name, BillingStreet, BillingCity, BillingState, BillingPostalCode, \
   Industry, AnnualRevenue, NumberOfEmployees, Website, Phone, \
   Owner.Name, LastActivityDate \
   FROM Account \
   WHERE BillingState = 'TX' AND BillingPostalCode LIKE '78%' \
   AND AnnualRevenue > 0 \
   ORDER BY AnnualRevenue DESC \
   LIMIT 200" --timeout $TIMEOUT 2>/dev/null > "$RAW_DIR/accounts_revenue.json" && \
  echo "  ✓ Revenue accounts saved" || echo "  ⚠️  Revenue accounts query failed"

# ─── QUERY 5: Campaign engagement (recent marketing touches) ──────────────
echo "📡 [5/5] Recent campaign engagement..."
sq agent-tools salesforce-sq query --soql \
  "SELECT LeadId, Lead.Company, Lead.PostalCode, Campaign.Name, Status, CreatedDate \
   FROM CampaignMember \
   WHERE Lead.State = 'TX' AND Lead.PostalCode LIKE '78%' \
   ORDER BY CreatedDate DESC \
   LIMIT 200" --timeout $TIMEOUT 2>/dev/null > "$RAW_DIR/campaign_members.json" && \
  echo "  ✓ Campaign data saved" || echo "  ⚠️  Campaign query failed"

# ─── BUILD COMBINED JSON ──────────────────────────────────────────────────
echo ""
echo "🔧 Building combined accounts.json with intent scoring..."
python3 scripts/build_data.py

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Refresh complete!"
echo "  📁 Output: $DATA_DIR/accounts.json"
echo "  🌐 Serve: python3 -m http.server 8080"
echo "═══════════════════════════════════════════════════════════"
