"""Audit salinan denormalisasi pada DATA NYATA (bukan hanya DENORM_MAP).

Pemakaian (dari akar repo, dengan venv backend):  python scripts/denorm_audit.py <nama_db>
Mendeteksi pasangan "FK + salinan nama/kode" yang ada di data, lalu melaporkan (a) yang tidak terdaftar di
`denorm.DENORM_MAP` dan (b) jumlah salinan yang sudah basi. Hanya MEMBACA. Lihat docs/audit/11_POLA_BUG_DAN_SAPUAN.md (PL-04).
"""
import collections
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))
os.environ.setdefault("DB_NAME", "unused")
os.environ.setdefault("MONGO_URL", os.environ.get("MONGO_URL", "mongodb://127.0.0.1:27017"))
from pymongo import MongoClient  # noqa: E402
from denorm import DENORM_MAP  # noqa: E402
c = MongoClient(os.environ["MONGO_URL"])[sys.argv[1]]
covered={(ch,fk,cf) for m,ps in DENORM_MAP.items() for ch,fk,cf,sf in ps}
colls=[x for x in c.list_collection_names() if not x.startswith('system.')]
# peta id -> (koleksi, dokumen) untuk koleksi master kecil-menengah
idmap={}
for coll in colls:
    n=c[coll].estimated_document_count()
    if n>20000: continue
    for d in c[coll].find({}, {'_id':0,'id':1,'name':1,'code':1,'title':1,'number':1,'full_name':1,'unit_code':1,'spk_number':1,'po_number':1}):
        if d.get('id'): idmap.setdefault(d['id'],(coll,d))
res=collections.defaultdict(lambda: [0,0,None])  # (child,fk,copy)->[docs,mismatch,example]
for coll in colls:
    if coll in ('journal_entries','events','audit_logs','idempotency_keys'): continue
    cur=c[coll].find({}).limit(3000)
    for d in cur:
        for k,v in list(d.items()):
            if not k.endswith('_id') or not isinstance(v,str) or v not in idmap: continue
            mcoll,md=idmap[v]
            if mcoll==coll: continue
            p=k[:-3]
            for suf,srcs in (('_name',('name','full_name','title')),('_code',('code',)),('_number',('number',f'{p}_number','spk_number','po_number')),('_title',('title',))):
                cf=p+suf
                if cf in d and isinstance(d[cf],str):
                    srcv=None
                    for s in srcs:
                        if s in md: srcv=md[s]; break
                    if srcv is None: continue
                    e=res[(coll,k,cf,mcoll)]
                    e[0]+=1
                    if srcv!=d[cf]:
                        e[1]+=1; e[2]=e[2] or (d.get('id'),d[cf],srcv)
print(f'{"anak.fk -> salinan":58s} {"master":18s} dok  basi  terdaftar?')
rows=sorted(res.items(),key=lambda x:(-(x[0][0:3] in covered), -x[1][1]))
unc=0;stale=0
for (coll,k,cf,mcoll),(n,bad,ex) in sorted(res.items(), key=lambda x:(-x[1][1],-x[1][0])):
    reg=(coll,k,cf) in covered
    if not reg: unc+=1
    if bad: stale+=bad
    if (not reg) or bad:
        print(f'{coll+"."+k+" -> "+cf:58s} {mcoll:18s} {n:4d} {bad:4d}  {"YA" if reg else "TIDAK"}  {ex if bad else ""}')
print('\nPasangan terdeteksi:',len(res),'| tidak terdaftar di DENORM_MAP:',unc,'| total salinan basi:',stale)
