import json,sys,glob
fn=sorted(glob.glob('runs/run_*.json'))[-1] if len(sys.argv)<2 else sys.argv[1]
d=json.load(open(fn))
st=d['stats']
ops=st['ops']
print(fn)
print("op: total ok rej skip err500")
for k in sorted(ops):
    print(f"  {k:14} {ops[k]:4} ok={st['ok'].get(k,0):3} rej={st['rej'].get(k,0):3} skip={st['skip'].get(k,0):3} 500={st['err500'].get(k,0)}")
print("tool_errors",d['tool_errors'])

print("--- alasan penolakan/lewati (top)")
for k,v in sorted(st.get('why',{}).items(), key=lambda x:-x[1])[:int(sys.argv[2]) if len(sys.argv)>2 else 40]:
    print(f"  {v:3} {k}")
