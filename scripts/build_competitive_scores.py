#!/usr/bin/env python3
"""
Build competitive POS intent scores from SFDC data.

Intent Score Formula (0-100):
  - Marketo Behavior Score (0-40 pts): engagement with Square content
  - Marketo Lead Score (0-20 pts): demographic/firmographic fit
  - DS Lead Score (0-15 pts): data science propensity model
  - Competitor POS Signal (0-15 pts): known competitor = higher switching likelihood
  - Lead Status Boost (0-10 pts): Qualified/Engaging = actively in pipeline

This creates a composite score that prioritizes:
1. Businesses actively engaging with Square (behavior)
2. On a known competitor POS (switching signal)
3. Already qualified or in pipeline (timing)
"""

import json
import os
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

# Competitor POS switching likelihood weights
# Higher = more likely to switch to Square
COMPETITOR_WEIGHTS = {
    'Toast': 12,       # Direct competitor, high switching signal
    'Clover': 13,      # Clover sellers often frustrated with hardware lock-in
    'Aloha': 15,       # Legacy system, very high switch likelihood
    'Heartland': 14,   # Legacy, often looking to modernize
    'Revel': 13,       # Mid-market, may be over-paying
    'SpotOn': 11,      # Newer competitor, moderate switch signal
    'Lightspeed': 10,  # E-comm focused, may want in-store
    'QuickBooks': 8,   # Accounting tool, not true POS — upgrade opportunity
    'Shopify': 7,      # E-comm → in-store expansion signal
    'New Business': 5, # No POS yet — greenfield
}

# Lead status weights
STATUS_WEIGHTS = {
    'Engaging': 10,
    'Qualified': 8,
    'Open': 6,
    'Converted': 4,  # Already converted — lower priority for outreach
    'Dripped': 3,
    'Auto Converted - LeanData': 2,
    'Rejected': 0,
}

# Lead source weights
SOURCE_WEIGHTS = {
    'Sales Sourced': 5,
    'Marketing Sourced': 4,
    'Lead Form': 4,
    'Lead Partner': 3,
    'Internally Sourced': 2,
    'Externally Sourced': 1,
}


def calculate_intent_score(record):
    """Calculate composite intent score (0-100) from SFDC fields."""
    score = 0
    breakdown = {}
    
    # 1. Marketo Behavior Score (0-40 pts)
    # Raw behavior scores range 0-100+, normalize to 0-40
    behavior = record.get('mkto_Behavior_Score__c') or 0
    behavior_pts = min(40, round(behavior * 0.67))  # 60 raw → 40 pts
    score += behavior_pts
    breakdown['behavior'] = behavior_pts
    
    # 2. Marketo Lead Score (0-20 pts)
    # Raw lead scores range 0-100+, normalize to 0-20
    lead_score = record.get('mkto2__Lead_Score__c') or 0
    lead_pts = min(20, round(lead_score * 0.32))  # 63 raw → 20 pts
    score += lead_pts
    breakdown['lead_score'] = lead_pts
    
    # 3. DS Lead Score (0-15 pts)
    # Raw DS scores range 0-100, normalize to 0-15
    ds = record.get('DS_Lead_Score__c') or 0
    ds_pts = min(15, round(ds * 0.2))  # 75 raw → 15 pts
    score += ds_pts
    breakdown['ds_score'] = ds_pts
    
    # 4. Competitor POS signal (0-15 pts)
    competitor = record.get('Competitor_POS__c') or ''
    comp_pts = COMPETITOR_WEIGHTS.get(competitor, 3)
    score += comp_pts
    breakdown['competitor'] = comp_pts
    
    # 5. Lead Status boost (0-10 pts)
    status = record.get('Status') or ''
    status_pts = STATUS_WEIGHTS.get(status, 2)
    score += status_pts
    breakdown['status'] = status_pts
    
    # 6. Lead Source bonus (0-5 pts)
    source = record.get('LeadSource') or ''
    source_pts = SOURCE_WEIGHTS.get(source, 1)
    score += source_pts
    breakdown['source'] = source_pts
    
    # Cap at 100
    final_score = min(100, score)
    
    return final_score, breakdown


def determine_status(score, lead_status):
    """Determine display status based on score and lead status."""
    if score >= 70 or lead_status in ('Engaging',):
        return 'hot'
    elif score >= 40 or lead_status in ('Qualified', 'Open'):
        return 'active'
    else:
        return 'new'


def generate_signals(record, breakdown):
    """Generate human-readable signal descriptions."""
    signals = []
    competitor = record.get('Competitor_POS__c') or ''
    
    if competitor:
        if competitor in ('Toast', 'Clover', 'Aloha', 'Revel', 'SpotOn'):
            signals.append(f'On {competitor} — Switch Target')
        elif competitor in ('Heartland', 'Lightspeed'):
            signals.append(f'Legacy POS ({competitor})')
        elif competitor == 'QuickBooks':
            signals.append('QuickBooks → POS Upgrade')
        elif competitor == 'Shopify':
            signals.append('Shopify → In-Store Expansion')
        elif competitor == 'New Business':
            signals.append('New Business — Greenfield')
    
    behavior = record.get('mkto_Behavior_Score__c') or 0
    if behavior >= 50:
        signals.append('High Engagement')
    elif behavior >= 20:
        signals.append('Active Engagement')
    
    lead_score = record.get('mkto2__Lead_Score__c') or 0
    if lead_score >= 50:
        signals.append('Strong Fit Score')
    elif lead_score >= 30:
        signals.append('Good Fit Score')
    
    ds = record.get('DS_Lead_Score__c') or 0
    if ds >= 50:
        signals.append('High DS Propensity')
    elif ds >= 25:
        signals.append('Moderate DS Propensity')
    
    status = record.get('Status') or ''
    if status == 'Engaging':
        signals.append('Actively Engaging')
    elif status == 'Qualified':
        signals.append('Qualified Lead')
    
    source = record.get('LeadSource') or ''
    if source == 'Sales Sourced':
        signals.append('Sales Sourced')
    elif source == 'Lead Form':
        signals.append('Inbound Lead Form')
    
    return signals[:5]  # Cap at 5 signals


def generate_notes(record, score, breakdown):
    """Generate actionable sales notes."""
    competitor = record.get('Competitor_POS__c') or 'Unknown'
    company = record.get('Company') or 'Unknown'
    
    notes = []
    
    if competitor == 'Toast':
        notes.append(f'{company} is currently on Toast. Lead with Square\'s lower processing fees (2.6%+10¢ vs Toast\'s 2.99%+15¢) and no long-term contract.')
    elif competitor == 'Clover':
        notes.append(f'{company} uses Clover. Highlight Square\'s free software tier, no hardware lock-in, and integrated ecosystem.')
    elif competitor == 'Aloha':
        notes.append(f'{company} is on Aloha (legacy NCR system). Position Square as modern cloud-based alternative with real-time reporting.')
    elif competitor == 'QuickBooks':
        notes.append(f'{company} uses QuickBooks for payments. Opportunity to upgrade to full POS with inventory, staff management, and analytics.')
    elif competitor == 'Shopify':
        notes.append(f'{company} is on Shopify. Pitch Square for in-store POS that syncs with their online presence.')
    elif competitor == 'Heartland':
        notes.append(f'{company} uses Heartland. Legacy processor — lead with modern hardware and transparent pricing.')
    else:
        notes.append(f'{company} is on {competitor}. Confirm pain points and position Square\'s all-in-one value.')
    
    if score >= 70:
        notes.append('HIGH PRIORITY: Multiple intent signals detected. Recommend immediate outreach.')
    elif score >= 50:
        notes.append('MEDIUM PRIORITY: Good engagement signals. Add to outreach sequence.')
    
    return ' '.join(notes)


def build_data():
    """Load raw SFDC data and build scored accounts.json."""
    
    # Load competitive leads
    raw_path = os.path.join(DATA_DIR, 'raw_competitive_leads.json')
    if not os.path.exists(raw_path):
        print(f'ERROR: {raw_path} not found. Run refresh.sh first.')
        return
    
    with open(raw_path) as f:
        raw = json.load(f)
    
    records = raw.get('results', raw.get('result', {}).get('records', []))
    print(f'Loaded {len(records)} competitive leads from SFDC')
    
    # Also load the general leads/accounts if available
    general_leads_path = os.path.join(DATA_DIR, 'raw_leads.json')
    general_accounts_path = os.path.join(DATA_DIR, 'raw_accounts.json')
    
    all_records = list(records)  # Start with competitive leads
    
    if os.path.exists(general_leads_path):
        with open(general_leads_path) as f:
            gen = json.load(f)
        gen_records = gen.get('results', gen.get('result', {}).get('records', []))
        # Only add records not already in competitive set (by Company + PostalCode)
        existing = {(r.get('Company',''), r.get('PostalCode','')) for r in all_records}
        new_gen = [r for r in gen_records if (r.get('Company',''), r.get('PostalCode','')) not in existing]
        all_records.extend(new_gen)
        print(f'Added {len(new_gen)} general leads (deduped)')
    
    if os.path.exists(general_accounts_path):
        with open(general_accounts_path) as f:
            gen = json.load(f)
        gen_records = gen.get('results', gen.get('result', {}).get('records', []))
        all_records.extend(gen_records)
        print(f'Added {len(gen_records)} accounts')
    
    # Build scored records
    scored = []
    for i, r in enumerate(all_records):
        score, breakdown = calculate_intent_score(r)
        lead_status = r.get('Status') or ''
        status = determine_status(score, lead_status)
        signals = generate_signals(r, breakdown)
        notes = generate_notes(r, score, breakdown)
        
        # Normalize ZIP (strip extended codes)
        zip_code = (r.get('PostalCode') or r.get('BillingPostalCode') or '')
        if '-' in zip_code:
            zip_code = zip_code.split('-')[0]
        
        scored.append({
            'id': i + 1,
            'sfdcId': r.get('attributes', {}).get('url', '').split('/')[-1] if r.get('attributes') else '',
            'companyName': r.get('Company') or r.get('Name') or 'Unknown',
            'contactName': '',  # Would need Contact lookup
            'zip': zip_code,
            'city': '',  # Not in Lead object directly
            'state': 'TX',
            'industry': r.get('Industry') or '',
            'intentScore': score,
            'scoreBreakdown': breakdown,
            'competitorPOS': r.get('Competitor_POS__c') or '',
            'employees': str(r.get('NumberOfEmployees') or ''),
            'leadSource': r.get('LeadSource') or '',
            'leadStatus': lead_status,
            'marketoBehaviorScore': r.get('mkto_Behavior_Score__c') or 0,
            'marketoLeadScore': r.get('mkto2__Lead_Score__c') or 0,
            'dsLeadScore': r.get('DS_Lead_Score__c') or 0,
            'signals': signals,
            'notes': notes,
            'status': status,
            'type': 'lead',
            'trending': score >= 75,
        })
    
    # Sort by intent score descending
    scored.sort(key=lambda x: -x['intentScore'])
    
    # Build output
    output = {
        'meta': {
            'refreshed_at': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
            'total_records': len(scored),
            'competitive_leads': len(records),
            'sources': ['SFDC Leads (Competitor_POS__c)', 'Marketo Behavior Score', 'DS Lead Score'],
            'scoring_model': 'v2_competitive',
            'scoring_weights': {
                'marketo_behavior': '0-40 pts',
                'marketo_lead_score': '0-20 pts',
                'ds_lead_score': '0-15 pts',
                'competitor_pos': '0-15 pts',
                'lead_status': '0-10 pts',
                'lead_source': '0-5 pts',
            },
            'zip_prefix': '78',
            'territory': 'Texas (Austin / San Antonio metro)',
        },
        'records': scored,
    }
    
    out_path = os.path.join(DATA_DIR, 'accounts.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f'\n✅ Wrote {len(scored)} scored records to {out_path}')
    print(f'\nScore distribution:')
    hot = len([r for r in scored if r['status'] == 'hot'])
    active = len([r for r in scored if r['status'] == 'active'])
    new = len([r for r in scored if r['status'] == 'new'])
    print(f'  🔥 Hot (70+):    {hot}')
    print(f'  ⚡ Active (40+): {active}')
    print(f'  🆕 New (<40):    {new}')
    
    print(f'\nTop 10 highest intent:')
    for r in scored[:10]:
        print(f"  {r['intentScore']:3d} | {r['companyName']:35s} | {r['competitorPOS']:12s} | {r['leadStatus']}")


if __name__ == '__main__':
    build_data()
