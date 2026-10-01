import os, sys, json, requests
from dotenv import load_dotenv
load_dotenv('/app/frontend/.env')
API = os.environ['REACT_APP_BACKEND_URL'].rstrip('/') + '/api'
PW = 'Sipro#2026'

def login(email):
    r = requests.post(f'{API}/auth/login', json={'email': email, 'password': PW}); r.raise_for_status()
    return {'Authorization': f"Bearer {r.json()['access_token']}"}

def ok(cond, msg):
    print(('PASS' if cond else 'FAIL'), msg)
    if not cond: sys.exit(1)

sales = login('sales@sipro.co.id'); mgr = login('manager@sipro.co.id'); owner = login('owner@sipro.co.id')
# 1. rules have approval_mode
rules = requests.get(f'{API}/pricing/discount-schemes', headers=mgr).json()['data']
mgr_rule = next(r for r in rules if r['code'] == 'DISC-MGR')
promos = requests.get(f'{API}/pricing/promos', headers=mgr).json()['data']
coupons = requests.get(f'{API}/pricing/coupons', headers=mgr).json()['data']
print('modes', {r['code']: r.get('approval_mode') for r in rules + promos + coupons})
# 2. set promo PROMO-LAUNCH approval_mode=always via PUT
pl = next(p for p in promos if p['code'] == 'PROMO-LAUNCH')
r = requests.put(f'{API}/pricing/promos/{pl["id"]}', headers=mgr, json={'approval_mode': 'always'})
ok(r.status_code == 200 and r.json()['data']['approval_mode'] == 'always' and r.json()['data']['requires_approval'] is True, 'promo approval_mode=always saved')
# 3. sales simulate with PROMO-LAUNCH → needs approval
opts = requests.get(f'{API}/quotations/options', headers=sales).json()['data']
unit = opts['units'][0]
leads = requests.get(f'{API}/leads', headers=sales, params={'limit': 50}).json()['data']
lead = next((l for l in leads if l.get('stage') not in ('booking', 'won', 'lost')), leads[0])
sim = requests.post(f'{API}/quotations/simulate', headers=sales, json={'unit_id': unit['id'], 'lead_id': lead['id'], 'promo_id': pl['id']}).json()['data']
ok(sim['needs_discount_approval'] and any(x['code'] == 'rule_always' for x in sim['approval_reasons']), f"simulate needs approval: {[x['label'] for x in sim['approval_reasons']]}")
# 4. reserve as sales without reason → 400; with reason → pending
r = requests.post(f'{API}/deals/reserve', headers=sales, json={'unit_id': unit['id'], 'lead_id': lead['id'], 'promo_id': pl['id'], 'booking_fee': 1000000})
ok(r.status_code == 400 and 'alasan' in r.text.lower(), f'reserve w/o reason rejected: {r.json()["detail"][:80]}')
r = requests.post(f'{API}/deals/reserve', headers=sales, json={'unit_id': unit['id'], 'lead_id': lead['id'], 'promo_id': pl['id'], 'booking_fee': 1000000, 'discount_reason': 'Pembeli pameran, minta promo launch'})
if r.status_code == 409:
    print('409', r.json()['detail']); sys.exit(1)
ok(r.status_code == 200, f'reserve created: {r.status_code} {r.text[:120]}')
deal = r.json()['data']
ok(deal['pricing_approval']['state'] == 'pending', 'deal pricing_approval pending')
# 5. booking blocked
r = requests.post(f'{API}/deals/{deal["id"]}/book', headers=sales, json={})
ok(r.status_code == 400 and 'persetujuan' in r.text.lower(), f'book blocked: {r.json()["detail"][:80]}')
# 6. sales cannot approve (403); manager approves
r = requests.post(f'{API}/deals/{deal["id"]}/pricing-approval', headers=sales, json={'approve': True, 'reason': 'coba sendiri'})
ok(r.status_code == 403, f'sales cannot approve ({r.status_code})')
r = requests.post(f'{API}/deals/{deal["id"]}/pricing-approval', headers=mgr, json={'approve': True, 'reason': 'Disetujui untuk pameran'})
ok(r.status_code == 200 and r.json()['data']['pricing_approval']['state'] == 'approved', 'manager approved')
r = requests.get(f'{API}/deals/{deal["id"]}', headers=sales).json()['data']
ok(r['pricing_approval']['decided_by'] == 'manager@sipro.co.id', 'decision recorded')
# 7. manager self-approve path: reserve directly by manager on another unit with DISC-MGR
unit2 = opts['units'][1]
lead2 = next((l for l in leads if l['id'] != lead['id']), lead)
r = requests.post(f'{API}/deals/reserve', headers=mgr, json={'unit_id': unit2['id'], 'lead_id': lead2['id'], 'discount_scheme_id': mgr_rule['id'], 'booking_fee': 1000000, 'discount_reason': 'Manager memberi diskon khusus'})
print('mgr reserve', r.status_code, r.text[:150])
if r.status_code == 200:
    ok(r.json()['data']['pricing_approval']['state'] == 'approved' and r.json()['data']['pricing_approval'].get('self_approved'), 'manager self-approved')
    deal2 = r.json()['data']
else:
    deal2 = None
# 8. global nominal threshold: set 1_000_000 and simulate with PROMO-DP (global) → over_amount
requests.put(f'{API}/settings/pricing.approval_min_amount', headers=owner, json={'value': 1000000})
pdp = next(p for p in promos if p['code'] == 'PROMO-DP')
sim = requests.post(f'{API}/quotations/simulate', headers=sales, json={'unit_id': opts['units'][2]['id'], 'promo_id': pdp['id']}).json()['data']
ok(any(x['code'] == 'over_amount' for x in sim['approval_reasons']), f"nominal threshold works: {[x['label'] for x in sim['approval_reasons']]}")
# never mode excludes
requests.put(f'{API}/pricing/promos/{pdp["id"]}', headers=mgr, json={'approval_mode': 'never'})
sim = requests.post(f'{API}/quotations/simulate', headers=sales, json={'unit_id': opts['units'][2]['id'], 'promo_id': pdp['id']}).json()['data']
ok(not sim['needs_discount_approval'], 'never mode excluded from threshold')
requests.put(f'{API}/pricing/promos/{pdp["id"]}', headers=mgr, json={'approval_mode': 'global'})
requests.put(f'{API}/settings/pricing.approval_min_amount', headers=owner, json={'value': 0})
requests.put(f'{API}/pricing/promos/{pl["id"]}', headers=mgr, json={'approval_mode': 'global'})
# 9. KPR config keys present
eff = requests.get(f'{API}/settings/effective', headers=owner, params={'keys': 'kpr.disbursement.require_scheme,kpr.disbursement.default_scheme_code'}).json()['data']
ok(eff.get('kpr.disbursement.require_scheme') is True and eff.get('kpr.disbursement.default_scheme_code') == 'BANK_STD', f'kpr cfg {eff}')
# cleanup: cancel deals
for d in [deal, deal2]:
    if d:
        r = requests.post(f'{API}/deals/{d["id"]}/cancel', headers=mgr, json={'reason': 'Uji otomatis selesai', 'refund_mode': 'forfeit'})
        print('cancel', d['id'], r.status_code)
print('ALL PASS')
