import sys, json
sys.path.insert(0,'.')
from fz.runner import Runner
spec=json.load(open(sys.argv[1]))
r=Runner("http://localhost:8052","mongodb://127.0.0.1:27017","sipro_s2","runs",1,nudge=True)
r.baseline()
from fz.world import World
w=World(r.client,r.db,"insp"+str(__import__('time').time_ns()%10**6),n_units=max(30,r.n_units_needed(spec['steps']))).setup()
for st in spec['steps']:
    st=json.loads(json.dumps(st)); r.exec_step(w,st)
    x=st['par'] if 'par' in st else [st]
    for y in x: print(y['op'],y['res']['code'],y['res']['note'][:100])
r.drain(w)
import pprint
for lab,e in w.ent.items():
    if e['kind']=='deal':
        d=w.one('deals',{'id':e['id']}); u=w.one('units',{'id':d['unit_id']}) if d else None
        inv=w.one('ar_invoices',{'deal_id':e['id']})
        print(lab, 'deal', d and d['status'], 'unit', u and (u['status'],u.get('payment_status')), 'AR', inv and (inv['status'],inv['paid'],inv['total']))
        for rc in w.rows('receipts',{'deal_id':e['id']}): print('   rcpt',rc.get('receipt_no'),rc.get('kind'),rc['amount'],rc['applied'],rc.get('deposit_amount'),rc.get('funding'),rc.get('status'))
        dep=w.one('customer_deposits',{'deal_id':e['id']}); print('   dep',dep and (dep['balance'],[ (x['type'],x['amount']) for x in dep['entries']]))
        cl=w.one('contract_liabilities',{'deal_id':e['id']}); print('   cl',cl and (cl['balance'],cl.get('recognized')))
new,_=r.check(settled=True)
print('NEW:',[ (v.inv,v.msg[:150]) for v in new])
