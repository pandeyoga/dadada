import json,sys
for fn in sys.argv[1:]:
    d=json.load(open(fn))
    print("==",fn.split('/')[-1],d['inv'],d['msg'][:200])
    for s in d['steps']:
        ss=s['par'] if 'par' in s else [s]
        pre="  PAR " if 'par' in s else "  "
        for x in ss:
            r=x.get('res') or {}
            print(pre,x['op'],json.dumps(x['args'],ensure_ascii=False),'->',r.get('code'),str(r.get('note'))[:90])
