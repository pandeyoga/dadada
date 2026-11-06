"""Ringkas temuan dari beberapa berkas run_*.json: kelompok per invarian + pesan ternormalisasi; cetak contoh + jendela operasi."""
import json, sys, glob, re
from collections import defaultdict, Counter
files = sys.argv[1:] or sorted(glob.glob('runs/run_*.json'))
groups = defaultdict(list)
tot_ops = Counter(); ok_ops = Counter()
nops = 0; nchecks = 0
inv_runs = Counter(); inv_viol = Counter(); inv_skip = Counter()
for fn in files:
    d = json.load(open(fn))
    nops += sum(d['stats']['ops'].values()); nchecks += d['stats']['checks']
    for k, v in d['stats']['ops'].items(): tot_ops[k] += v
    for k, v in d['stats']['ok'].items(): ok_ops[k] += v
    for i, s in d['inv_stats'].items():
        inv_runs[i] += s['runs']; inv_viol[i] += s['viol']; inv_skip[i] += s['skipped']
    for f in d['findings']:
        f['_file'] = fn
        groups[(f['inv'], re.sub(r'\d[\d,.]*', 'N', f['msg'])[:90])].append(f)
print(f"berkas={len(files)} ops={nops} cek={nchecks}")
for (inv, m), fs in sorted(groups.items(), key=lambda x: (x[0][0], -len(x[1]))):
    f = fs[0]
    print(f"\n[{inv}] x{len(fs)} {'(soft)' if f['level']=='soft' else ''} known={f['known']} :: {f['msg'][:200]}")
    if '-v' in sys.argv or True:
        for s in f['window'][-5:]:
            ss = s['par'] if 'par' in s else [s]
            for x in ss:
                print('     ', ('PAR ' if 'par' in s else '') + x['op'], json.dumps(x['args'], ensure_ascii=False)[:110], '->', x['res'][:70])
