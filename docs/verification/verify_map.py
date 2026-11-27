#!/usr/bin/env python3
"""VERIFY-map: independent re-measurement of THERMOSTAT-PROTOCOL-MAP.md
against primary sources (traces/*.jsonl, traces/external/gofinity-bootup.bin,
firmware-re/stageB/flat.bin). Does not reuse audit scripts."""
import json, glob, collections, datetime, struct, os, statistics

BASE = '/home/hatch/workspace/diy-thermostat'
TR = BASE + '/traces'

def load(p):
    out, bad = [], 0
    for line in open(p):
        line = line.strip()
        if line:
            try: out.append(json.loads(line))
            except Exception: bad += 1
    return out, bad

def ts(f):
    return datetime.datetime.fromisoformat(f['ts'].replace('Z', '+00:00'))

def D(f):
    return bytes.fromhex(f['data']) if f.get('data') else b''

files = sorted(glob.glob(TR + '/*.jsonl'))
segfiles = sorted(glob.glob(TR + '/segments/*.jsonl'))
corpus = []          # (fname, frame) over the 12 top-level files
per_file = {}
for p in files:
    fr, bad = load(p)
    per_file[os.path.basename(p)] = (len(fr), bad)
    corpus += [(os.path.basename(p), f) for f in fr]
print("== S0 corpus ==")
for k, v in per_file.items(): print(f"  {k}: {v[0]} parsed, {v[1]} unparseable")
print(f"  TOTAL top-level: {len(corpus)} frames in {len(files)} files")
seg_total = 0
for p in segfiles:
    fr, _ = load(p); seg_total += len(fr)
print(f"  segments dir: {seg_total} frames in {len(segfiles)} files (copies of coldstart)")

print("\n== S1 func inventory (12 files) ==")
fc = collections.Counter(f['func'] for _, f in corpus)
print("  funcs:", dict(fc))
print("  func 15 frames:", sum(1 for _, f in corpus if f['func'] == '15'))
print("  reg 3B0E frames:", sum(1 for _, f in corpus if f['reg'] == '3B0E'))
print("  src set:", dict(collections.Counter(f['src'] for _, f in corpus)))

print("\n== S2 0305 census ==")
w = [(p, f) for p, f in corpus if f['reg'] == '0305' and f['func'] == '0C' and f.get('data')]
print(f"  0305 writes (func 0C, data) in 12 files: {len(w)}")
bysrc = collections.Counter()
b11 = collections.Counter()
for p, f in w:
    d = D(f)
    bysrc[f['src']] += 1
    if len(d) == 12: b11[(f['src'], d[11])] += 1
    else: b11[(f['src'], 'len%d' % len(d))] += 1
print("  by src:", dict(bysrc))
print("  (src,[11]):", dict(b11))
zero11 = [(p, f) for p, f in w if len(D(f)) == 12 and D(f)[11] == 0]
print(f"  frames with [11]==0x00: {len(zero11)}; by (file,src):",
      dict(collections.Counter((p, f['src']) for p, f in zero11)))
print("  all-zero payloads among [11]==0:", sum(1 for _, f in zero11 if set(D(f)) == {0}))
# with segments (raw) and unique-line dedup
raw_all = list(w)
for p in segfiles:
    fr, _ = load(p)
    raw_all += [(os.path.basename(p), f) for f in fr
                if f['reg'] == '0305' and f['func'] == '0C' and f.get('data')]
print(f"  0305 writes incl. segment copies (raw): {len(raw_all)}")
uniq = {(f['ts'], f['src'], f['dst'], f['func'], f['reg'], f['data']) for _, f in raw_all}
print(f"  unique (ts,src,dst,func,reg,data) incl. segments: {len(uniq)}")
# CFM / stages over src=20
cfm = collections.Counter(); heat = collections.Counter(); cool = collections.Counter()
coact = 0; n20 = 0
for p, f in w:
    if f['src'] != '20': continue
    d = D(f)
    if len(d) != 12: continue
    n20 += 1
    cfm[(d[4] << 8) | d[5]] += 1; heat[d[0]] += 1; cool[d[2]] += 1
    if d[0] != 0 and d[2] != 0: coact += 1
print(f"  src=20 0305 frames: {n20}; [0]&[2] co-active: {coact}")
print("  CFM set (corpus, src20):", sorted(cfm))
print("  heat [0] values:", dict(heat), "| cool [2] values:", dict(cool))

print("\n== S3 0605 census ==")
w5 = [(p, f) for p, f in corpus if f['reg'] == '0605' and f['func'] == '0C' and f.get('data')]
print("  0605 writes total:", len(w5), "| lengths:", dict(collections.Counter(len(D(f)) for _, f in w5)))
dir5 = [(p, f) for p, f in w5 if f['dst'] == '53']
bcast5 = [(p, f) for p, f in w5 if f['dst'] == 'F1']
print(f"  directed (dst 53): {len(dir5)}; broadcast (dst F1): {len(bcast5)}",
      dict(collections.Counter(f['src'] for _, f in bcast5)))
print("  directed [4]:", dict(collections.Counter(D(f)[4] for _, f in dir5)))
print("  directed [5]:", dict(collections.Counter(D(f)[5] for _, f in dir5)))
print("  directed [6]:", dict(collections.Counter(D(f)[6] for _, f in dir5)))
print("  broadcast [6]:", dict(collections.Counter(D(f)[6] for _, f in bcast5)))
fl = collections.Counter()
for p, f in dir5:
    fl[struct.unpack('>f', D(f)[0:4])[0]] += 1
print("  directed float [0..3] values:", dict(fl))
for p, f in dir5:
    if struct.unpack('>f', D(f)[0:4])[0] == 3.0:
        print(f"  float==3.0 frame: file={p} ts={f['ts']} src={f['src']} data={f['data']}")

print("\n== S4a response spot rows (whole corpus) ==")
resp = collections.defaultdict(collections.Counter)
for p, f in corpus:
    if f['func'] == '06' and f.get('data'):
        resp[(f['dst'], f['reg'])][len(D(f))] += 1
for key in [('44','0104'),('44','0306'),('44','030A'),('53','0104'),('53','0302'),
            ('44','0307'),('53','061F'),('44','0316'),('53','0304'),('44','030D'),('53','0608'),('53','0604')]:
    print(f"  resp to {key[0]} reg {key[1]}: lengths {dict(resp[key])}")
# constancy of specific answers
def distinct_resp(dst, reg):
    return collections.Counter(f['data'] for _, f in corpus
                               if f['func'] == '06' and f['dst'] == dst and f['reg'] == reg and f.get('data'))
for dst, reg in [('44','030A'), ('44','0307'), ('44','0104'), ('53','0104')]:
    c = distinct_resp(dst, reg)
    print(f"  distinct answers {dst}/{reg}: {len(c)} distinct; top: {c.most_common(2)}")

print("\n== S4b constant-write spot rows (src=20, func 0C) ==")
for reg, dst in [('0403','44'),('0409','44'),('0307','44'),('0610','53'),('0612','53'),('061A','53'),('061E','53')]:
    c = collections.Counter(f['data'] for _, f in corpus
                            if f['src'] == '20' and f['dst'] == dst and f['reg'] == reg and f['func'] == '0C')
    print(f"  20->{dst} {reg}: {sum(c.values())} writes, {len(c)} distinct: {c.most_common(3)}")
c060d = collections.Counter(f['data'] for _, f in corpus
                            if f['src'] == '20' and f['reg'] == '060D' and f['func'] == '0C')
print("  060D write payloads:", dict(c060d))

print("\n== S4c 060B/0414 shared byte ==")
for reg, dst, ln in [('060B','53',7), ('0414','44',6)]:
    rows = [(p, f) for p, f in corpus if f['src'] == '20' and f['dst'] == dst and f['reg'] == reg and f['func'] == '0C']
    ok = sum(1 for _, f in rows if len(D(f)) == ln and D(f)[0] == 1 and D(f)[1] == 4)
    xs = [D(f)[2] for _, f in rows if len(D(f)) == ln]
    print(f"  {reg}: {len(rows)} writes; pattern-conforming {ok}; XX range {min(xs)}..{max(xs)}")
cs = load(TR + '/coldstart-20261029-125733.jsonl')[0]
for reg, dst in [('060B','53'), ('0414','44')]:
    xs = [D(f)[2] for f in cs if f['src'] == '20' and f['dst'] == dst and f['reg'] == reg and f['func'] == '0C']
    print(f"  coldstart {reg}: n={len(xs)} XX range {min(xs)}..{max(xs)}")
# pairing within each file: nearest opposite-reg write within 1.5 s
pairs = 0; same = 0
for p in sorted(per_file):
    fr = load(TR + '/' + p)[0]
    a = [(ts(f), D(f)[2]) for f in fr if f['src'] == '20' and f['reg'] == '060B' and f['func'] == '0C']
    b = [(ts(f), D(f)[2]) for f in fr if f['src'] == '20' and f['reg'] == '0414' and f['func'] == '0C']
    for t, x in a:
        cand = [(abs((t2 - t).total_seconds()), x2) for t2, x2 in b if abs((t2 - t).total_seconds()) <= 1.5]
        if cand:
            cand.sort(); pairs += 1; same += (cand[0][1] == x)
print(f"  nearest-tick pairs: {pairs}, identical XX: {same}")

print("\n== S4d misc (a) rows ==")
c031d = [f for f in cs if f['src'] == '20' and f['reg'] == '031D' and f['func'] == '0C']
print(f"  coldstart 031D writes: {len(c031d)}, payloads {dict(collections.Counter(f['data'] for f in c031d))}")
c0418 = [f for f in cs if f['src'] == '20' and f['reg'] == '0418' and f['func'] == '0C']
t0 = ts(cs[0])
print(f"  coldstart 0418 writes: {len(c0418)}, payloads {[f['data'] for f in c0418]}, at +{[(ts(f)-t0).total_seconds() for f in c0418]} s")
for reg in ('0202', '0203'):
    tt = [ts(f) for f in cs if f['reg'] == reg and f['src'] == '20']
    ds = sorted((tt[i+1]-tt[i]).total_seconds() for i in range(len(tt)-1))
    print(f"  coldstart {reg}: n={len(tt)} dsts={dict(collections.Counter(f['dst'] for f in cs if f['reg']==reg))} lens={dict(collections.Counter(len(D(f)) for f in cs if f['reg']==reg))} interval min={ds[0]:.1f} med={ds[len(ds)//2]:.1f} max={ds[-1]:.1f}")
n0302 = sum(1 for f in cs if f['src'] == '20' and f['dst'] == '44' and f['reg'] == '0302' and f['func'] == '0B')
print(f"  coldstart 20->44 0302 reads: {n0302}; answer lengths: {dict(resp[('44','0302')])}")
init = collections.Counter((f['src'], f['dst']) for f in cs if f['func'] in ('0B', '0C'))
print("  coldstart initiator (src,dst) for 0B/0C:", dict(init))

print("\n== S5 (b) SAM surface ==")
mw = [(p, f) for p, f in corpus if f['src'] == '20' and f['func'] == '0C' and f['reg'] in ('3B02', '3B03')]
print(f"  writes FROM 0x20 to 3B02/3B03 (any dst): {len(mw)}; broadcast dst=F1: {sum(1 for _, f in mw if f['dst'] == 'F1')}")
for reg, ln in [('3B02', 29), ('3B03', 150)]:
    c = [(p, f) for p, f in corpus if f['src'] == '20' and f['dst'] == '92' and f['func'] == '06' and f['reg'] == reg]
    ok = sum(1 for _, f in c if len(D(f)) == ln and set(D(f)) == {0})
    print(f"  20->92 {reg} replies: {len(c)}, of which {ln}B all-zero: {ok}")
sc = load(TR + '/sam-commissioning-20261029-143248.jsonl')[0]
for reg in ('3B02', '3B03'):
    rd = [ts(f) for f in sc if f['src'] == '92' and f['dst'] == '20' and f['reg'] == reg and f['func'] == '0B']
    gaps = sorted((rd[i+1]-rd[i]).total_seconds() for i in range(len(rd)-1))
    print(f"  sam-commissioning 92->20 {reg} reads: {len(rd)}; median gap {gaps[len(gaps)//2]:.2f} s" if gaps else f"  {reg}: {len(rd)}")
both = sorted(ts(f) for f in sc if f['src'] == '92' and f['dst'] == '20' and f['reg'] in ('3B02', '3B03') and f['func'] == '0B')
g2 = sorted((both[i+1]-both[i]).total_seconds() for i in range(len(both)-1))
print(f"  combined 3B02+3B03 read stream: {len(both)} reads; median gap {g2[len(g2)//2]:.2f} s")
r3d = [(p, f) for p, f in corpus if f['reg'] == '3D02' and f['func'] == '0B']
a3d = [(p, f) for p, f in corpus if f['reg'] == '3D02' and f['func'] == '06']
print(f"  3D02 reads in corpus: {len(r3d)} by (file,src): {dict(collections.Counter((p, f['src']) for p, f in r3d))}")
print(f"  3D02 answers in corpus: {len(a3d)}")
samfiles = ['sam-commissioning-20261029-143248.jsonl', 'sam-control-test-20261029-145357.jsonl']
c400 = collections.Counter(f['data'] for p, f in corpus if p in samfiles and f['src'] == '20' and f['dst'] == '92' and f['reg'] == '400A' and f['func'] == '06')
print("  400A served in SAM captures:", {k: v for k, v in c400.items()})
c4012 = collections.Counter(f['data'] for p, f in corpus if p in samfiles and f['src'] == '20' and f['reg'] == '4012' and f['func'] == '06')
print("  4012 served in SAM captures:", dict(c4012))
c4202 = [(len(D(f)), f['data'][:24]) for p, f in corpus if p in samfiles and f['src'] == '20' and f['reg'] == '4202' and f['func'] == '06']
print(f"  4202 served in SAM captures: {len(c4202)} replies, (len, prefix): {collections.Counter(c4202)}")
id20 = [f['data'] for _, f in corpus if f['src'] == '20' and f['reg'] == '0104' and f['func'] == '06' and len(D(f)) == 120]
print(f"  0x20 0104 answers (120B): {len(id20)}, distinct: {len(set(id20))}")
if id20:
    raw = bytes.fromhex(id20[0])
    print("   name field:", raw[0:24])
    print("   sw field:", raw[56:72], "| model:", raw[72:82], "| serial area:", raw[88:120])
p93 = [f for f in cs if f['src'] == '93' and f['dst'] == '20' and f['reg'] == '3B05' and f['func'] == '0B']
gaps93 = [(ts(p93[i+1]) - ts(p93[i])).total_seconds() for i in range(len(p93)-1)]
a93 = [f for f in cs if f['src'] == '20' and f['dst'] == '93' and f['reg'] == '3B05' and f['func'] == '06']
print(f"  coldstart 93->20 3B05 reads: {len(p93)}, gaps: {[round(g, 2) for g in gaps93]}")
print(f"  coldstart 20->93 3B05 answers: {len(a93)}, all 11B zeros: {all(len(D(f)) == 11 and set(D(f)) == {0} for f in a93)}, first answer at +{(ts(a93[0]) - t0).total_seconds():.1f} s" if a93 else "  no answers")

print("\n== S6 coldstart boot timeline ==")
first1F = next(f for f in cs if f['src'] == '1F')
last1F = [f for f in cs if f['src'] == '1F'][-1]
first20 = next(f for f in cs if f['src'] == '20')
first20w = next(f for f in cs if f['src'] == '20' and f['func'] == '0C')
first0305 = next(f for f in cs if f['src'] == '20' and f['reg'] == '0305' and f['func'] == '0C')
firstSYST = next((f for f in cs if f['src'] == '20' and f['reg'] in ('0202', '0203')), None)
first0104r = next(f for f in cs if f['src'] == '20' and f['dst'] == '44' and f['reg'] == '0104' and f['func'] == '0B')
print(f"  t0 (first frame): {cs[0]['ts']}")
print(f"  first 1F frame: +{(ts(first1F)-t0).total_seconds():.3f} s reg={first1F['reg']}")
print(f"  last 1F frame: +{(ts(last1F)-t0).total_seconds():.3f} s")
print(f"  first 0x20 frame: +{(ts(first20)-t0).total_seconds():.3f} s reg={first20['reg']} func={first20['func']}; gap after last 1F: {(ts(first20)-ts(last1F)).total_seconds():.3f} s")
print(f"  first 0x20 WRITE (func 0C): +{(ts(first20w)-t0).total_seconds():.3f} s reg={first20w['reg']} dst={first20w['dst']} data={first20w['data']}")
print(f"  first 0x20 0305 write: +{(ts(first0305)-t0).total_seconds():.3f} s from t0; +{(ts(first0305)-ts(first1F)).total_seconds():.3f} s from 1F start; data={first0305['data']}")
print(f"  first 0x20 SYSTIME (0202/0203): +{(ts(firstSYST)-t0).total_seconds():.3f} s reg={firstSYST['reg']}" if firstSYST else "  none")
print(f"  first 20->44 0104 read: +{(ts(first0104r)-t0).total_seconds():.3f} s")
print("  frames with t in [+37, +42] s (src/reg/func):")
for f in cs:
    dt = (ts(f) - t0).total_seconds()
    if 37 <= dt <= 42:
        print(f"    +{dt:.3f} src={f['src']} dst={f['dst']} func={f['func']} reg={f['reg']} data={f['data'][:20]}")
sweepdst = {'21','22','23','24','25','26','27','28','3F','46','55','58','5A','5C','5F','60','61','69','80','92','94'}
sweep = [f for f in cs if f['src'] == '20' and f['dst'] in sweepdst]
print(f"  last 0x20 sweep-dst frame: +{(ts(sweep[-1])-t0).total_seconds():.3f} s dst={sweep[-1]['dst']} reg={sweep[-1]['reg']}")
b45 = [ts(f) for f in cs if f['src'] == '44' and f['dst'] == '45']
bursts = []
for t in b45:
    if not bursts or (t - bursts[-1][-1]).total_seconds() > 5: bursts.append([t])
    else: bursts[-1].append(t)
print(f"  44->45 bursts: {len(bursts)}; starts at +{[(b[0]-t0).total_seconds() for b in bursts]}; sizes {[len(b) for b in bursts]}")

print("\n== S7 segment scenario checks ==")
def loadseg(n): return load(TR + '/segments/' + n)[0]
seg02 = loadseg('02-fan-only.jsonl'); seg04 = loadseg('04-cool-70F.jsonl'); seg06 = loadseg('06-heat-75-79F.jsonl')
def cfm_seq(fr):
    out = []
    for f in fr:
        if f['src'] == '20' and f['reg'] == '0305' and f['func'] == '0C':
            d = D(f); v = (d[4] << 8) | d[5]
            if not out or out[-1] != v: out.append(v)
    return out
print("  seg02 fan-only CFM transitions:", cfm_seq(seg02))
print("  seg04 cool CFM transitions:", cfm_seq(seg04))
print("  seg06 heat 0305 payloads distinct:", dict(collections.Counter(f['data'] for f in seg06 if f['src'] == '20' and f['reg'] == '0305' and f['func'] == '0C')))
print("  seg02 060D payloads:", dict(collections.Counter(f['data'] for f in seg02 if f['src'] == '20' and f['reg'] == '060D' and f['func'] == '0C')))
print("  seg06 060D payloads:", dict(collections.Counter(f['data'] for f in seg06 if f['src'] == '20' and f['reg'] == '060D' and f['func'] == '0C')))
for probe in ('010000000000C808CA00', '010452048E00C808CA08', '010511065102A808CA18'):
    n = sum(1 for f in cs if f['data'] == probe)
    print(f"  coldstart frames with data {probe}: {n}")
r061f04 = [f['data'] for f in seg04 if f['src'] == '53' and f['reg'] == '061F' and f['func'] == '06']
print(f"  seg04 061F answers: {len(r061f04)}, distinct payloads: {len(set(r061f04))}")
idle061f = []
for n in ('01-coldstart-idle.jsonl', '02-fan-only.jsonl', '06-heat-75-79F.jsonl'):
    idle061f += [f['data'] for f in loadseg(n) if f['src'] == '53' and f['reg'] == '061F' and f['func'] == '06']
print(f"  segs 01/02/06 061F answers: {len(idle061f)}, distinct payloads: {len(set(idle061f))}")
# which byte offsets vary in seg04 vs the idle constant
if idle061f and r061f04:
    base = bytes.fromhex(collections.Counter(idle061f).most_common(1)[0][0])
    vary = set()
    for p in r061f04:
        d = bytes.fromhex(p)
        for i in range(min(len(d), len(base))):
            if d[i] != base[i]: vary.add(i)
    print(f"  seg04 061F varying byte offsets vs idle constant: {sorted(vary)}")

print("\n== S8 sam-reseat file ==")
rs, rsbad = load(TR + '/sam-reseat-20261029-151123.jsonl')
print(f"  frames: {len(rs)} (+{rsbad} unparseable); window {rs[0]['ts']} .. {rs[-1]['ts']}")
print("  funcs:", dict(collections.Counter(f['func'] for f in rs)))
polls = [f for f in rs if f['src'] == '92' and f['dst'] == '20' and f['func'] == '0B']
answers = [f for f in rs if f['src'] == '20' and f['dst'] == '92' and f['func'] == '06']
print(f"  92->20 reads: {len(polls)}; 20->92 answers: {len(answers)}")
unans = []
for i, f in enumerate(rs):
    if f['src'] == '92' and f['dst'] == '20' and f['func'] == '0B':
        nxt = [g for g in rs[i+1:i+8] if g['src'] == '20' and g['dst'] == '92' and g['reg'] == f['reg']]
        if not nxt: unans.append(f)
print(f"  unanswered 92 polls: {len(unans)}; window: {unans[0]['ts'] if unans else '-'} .. {unans[-1]['ts'] if unans else '-'}")
f1f = [f for f in rs if f['src'] == '1F']
print(f"  first 1F frame after silence: {f1f[0]['ts'] if f1f else 'none'}")
during = [f for f in rs if unans and unans[0]['ts'] <= f['ts'] <= (f1f[0]['ts'] if f1f else unans[-1]['ts'])]
print(f"  frames during silence (unans start .. 1F): {len(during)}; srcs: {dict(collections.Counter(f['src'] for f in during))}")
print(f"  any frame from 44/53 during silence: {[ (f['src'], f['reg'], f['func']) for f in during if f['src'] in ('44','53')][:10]}")

print("\n== S9 segment 05 latency / gaps ==")
seg05 = loadseg('05-off-pause.jsonl')
reads = [(i, f) for i, f in enumerate(seg05) if f['src'] == '20' and f['func'] == '0B']
lat = []; unans5 = 0
for i, f in reads:
    hit = None
    for g in seg05[i+1:]:
        if (ts(g) - ts(f)).total_seconds() > 1.0: break
        if g['func'] == '06' and g['src'] == f['dst'] and g['reg'] == f['reg']: hit = g; break
    if hit: lat.append((ts(hit) - ts(f)).total_seconds() * 1000)
    else: unans5 += 1
lat.sort()
print(f"  seg05 reads: {len(reads)}; answered: {len(lat)}; unanswered: {unans5}")
print(f"  latency ms: median {lat[len(lat)//2]:.0f}, p90 {lat[int(len(lat)*0.9)]:.0f}, max {lat[-1]:.0f}")
tx20 = [ts(f) for f in seg05 if f['src'] == '20']
gaps = sorted((tx20[i+1]-tx20[i]).total_seconds() for i in range(len(tx20)-1))
print(f"  seg05 0x20 tx gaps: median {gaps[len(gaps)//2]:.2f}, p90 {gaps[int(len(gaps)*0.9)]:.2f}, p99 {gaps[int(len(gaps)*0.99)]:.2f}, max {gaps[-1]:.2f}")

print("\n== S10 gofinity bootup.bin (own parser, CRC A001 reflected init 0) ==")
def crc_ref(buf):
    crc = 0
    for b in buf:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc
data = open(TR + '/external/gofinity-bootup.bin', 'rb').read()
frames = []; pos = 0; skipped = 0
while pos + 10 <= len(data):
    dst, src = struct.unpack_from('<HH', data, pos)
    ln = data[pos+4]; op = data[pos+7]; total = ln + 10
    if pos + total > len(data): break
    fr = data[pos:pos+total]
    stored = fr[-2] | (fr[-1] << 8)
    if crc_ref(fr[:-2]) == stored and op in (0x06, 0x0B, 0x0C, 0x15):
        frames.append((dst, src, op, fr[8:-2])); pos += total
    else:
        skipped += 1; pos += 1
print(f"  parsed frames: {len(frames)}, bytes skipped: {skipped}")
gcfm = collections.Counter(); gw = 0
for dst, src, op, payload in frames:
    if op == 0x0C and src == 0x0120 and len(payload) >= 3:
        reg = (payload[1] << 8) | payload[2]; body = payload[3:]
        if reg == 0x0305 and len(body) == 12:
            gw += 1; gcfm[(body[4] << 8) | body[5]] += 1
        if reg in (0x0414, 0x060B): pass
print(f"  gofinity 0305 writes: {gw}; CFM values: {sorted(gcfm)}; 360 present: {360 in gcfm}")
g1460 = sum(1 for dst, src, op, payload in frames if op == 0x0C and src == 0x0120 and len(payload) >= 3
            and ((payload[1] << 8) | payload[2]) in (0x0414, 0x060B))
print(f"  gofinity 0414/060B writes from thermostat: {g1460}")

print("\n== S11 flat image: CRC nibble tables @0x182B598C / 0x182B59AC (AA) ==")
img = open(BASE + '/firmware-re/stageB/flat.bin', 'rb').read()
IMG_BASE = 0x18040000
tabA = img[0x182B598C - IMG_BASE: 0x182B598C - IMG_BASE + 32]
tabB = img[0x182B59AC - IMG_BASE: 0x182B59AC - IMG_BASE + 32]
def words(b): return [struct.unpack_from('>I', b, i)[0] for i in range(0, 32, 4)]
print("  tableA (8 u32 BE):", [hex(x) for x in words(tabA)])
print("  tableB (8 u32 BE):", [hex(x) for x in words(tabB)])
# AA formula uses 16-entry tables; the stored block is 32 bytes = 8 u32.
# Interpret each table as 16 u16 BE entries instead and test both readings
# against the gofinity wire CRCs.
def crc_tab(buf, A, B):
    crc = 0
    for b in buf:
        crc = (crc >> 8) ^ A[(crc ^ b) & 0xF] ^ B[((crc ^ b) & 0xF0) >> 4]
    return ((crc & 0xFF) << 8) | (crc >> 8)  # CONCAT11 byte-swap per AA
A16 = [struct.unpack_from('>H', tabA, i)[0] for i in range(0, 32, 2)]
B16 = [struct.unpack_from('>H', tabB, i)[0] for i in range(0, 32, 2)]
print("  as u16[16] A:", [hex(x) for x in A16])
print("  as u16[16] B:", [hex(x) for x in B16])
# re-walk the .bin with table CRC: stored wire CRC is LE at frame end
ok = 0; tot = 0; pos = 0
while pos + 10 <= len(data):
    ln = data[pos+4]; total = ln + 10
    if pos + total > len(data): break
    fr = data[pos:pos+total]
    stored = fr[-2] | (fr[-1] << 8)
    if crc_ref(fr[:-2]) == stored:  # frame boundary valid under reference CRC
        tot += 1
        if crc_tab(fr[:-2], A16, B16) == stored: ok += 1
        pos += total
    else:
        pos += 1
print(f"  image-table CRC vs gofinity wire CRC: {ok}/{tot} frames match")
print("  'CCN' string after tables at 0x182B59CC:", img[0x182B59CC - IMG_BASE: 0x182B59CC - IMG_BASE + 8])
