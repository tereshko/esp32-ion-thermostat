#!/usr/bin/env python3
"""VERIFY-map part 2: fixes and follow-ups."""
import json, glob, collections, datetime, struct, os

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
corpus = []
for p in files:
    fr, _ = load(p)
    corpus += [(os.path.basename(p), f) for f in fr]
cs = load(TR + '/coldstart-20261029-125733.jsonl')[0]

print("== F1 response lengths (src=device, func 06) ==")
resp = collections.defaultdict(collections.Counter)
for p, f in corpus:
    if f['func'] == '06' and f.get('data'):
        resp[(f['src'], f['reg'])][len(D(f))] += 1
for key in [('44','0104'),('44','0306'),('44','030A'),('53','0104'),('53','0302'),('44','0307'),
            ('53','061F'),('44','0316'),('53','0304'),('44','030D'),('53','0608'),('53','0604'),
            ('44','0302'),('53','0303'),('44','0402'),('53','060E')]:
    print(f"  {key[0]}->{20} reg {key[1]}: lengths {dict(resp[key])}")
for src, reg in [('44','030A'), ('44','0307'), ('44','0104'), ('53','0104'), ('44','030D')]:
    c = collections.Counter(f['data'] for _, f in corpus if f['func'] == '06' and f['src'] == src and f['reg'] == reg and f.get('data'))
    print(f"  distinct answers {src}/{reg}: {len(c)} distinct; top2: {c.most_common(2)}")

print("\n== F2 identity 0x20 exact offsets ==")
id20 = [f['data'] for _, f in corpus if f['src'] == '20' and f['reg'] == '0104' and f['func'] == '06' and len(D(f)) == 120][0]
raw = bytes.fromhex(id20)
for needle in (b'INFINITY', b'CESR******-**.79', b'SYST0101CW', b'3320'):
    idxs = []
    start = 0
    while True:
        i = raw.find(needle, start)
        if i < 0: break
        idxs.append(i); start = i + 1
    print(f"  {needle}: at offsets {idxs}")
print("  full payload hex:")
for i in range(0, 120, 20):
    print("   ", raw[i:i+20].hex(), repr(raw[i:i+20]))

print("\n== F3 payload example existence ==")
for probe, where in [('01000000048E', 'coldstart'), ('020000000651', 'seg07 rundown')]:
    ncs = sum(1 for f in cs if f['data'].startswith(probe))
    nall = sum(1 for _, f in corpus if f.get('data', '').startswith(probe))
    print(f"  prefix {probe}: coldstart {ncs}, corpus {nall}")
seg07 = load(TR + '/segments/07-heat-rundown.jsonl')[0]
c07 = collections.Counter(f['data'] for f in seg07 if f['src'] == '20' and f['reg'] == '0305' and f['func'] == '0C')
print("  seg07 0305 payloads:", dict(c07))
# 061F reads (0B) in segs 01/02/06 and non-modal answers
for n in ('01-coldstart-idle.jsonl', '02-fan-only.jsonl', '06-heat-75-79F.jsonl'):
    fr = load(TR + '/segments/' + n)[0]
    rd = sum(1 for f in fr if f['src'] == '20' and f['dst'] == '53' and f['reg'] == '061F' and f['func'] == '0B')
    an = [f['data'] for f in fr if f['src'] == '53' and f['reg'] == '061F' and f['func'] == '06']
    modal = collections.Counter(an).most_common(1)[0][1] if an else 0
    print(f"  {n}: 061F reads {rd}, answers {len(an)}, non-modal answers {len(an) - modal}")

print("\n== F4 seg05 unanswered variants ==")
seg05 = load(TR + '/segments/05-off-pause.jsonl')[0]
reads = [(i, f) for i, f in enumerate(seg05) if f['src'] == '20' and f['func'] == '0B']
def answered(i, f, rule):
    for j in range(i + 1, len(seg05)):
        g = seg05[j]
        if rule == 'nextread' and g['src'] == '20' and g['func'] == '0B' and g['dst'] == f['dst'] and g['reg'] == f['reg']:
            return False
        if (ts(g) - ts(f)).total_seconds() > 5.0: return False
        if g['func'] == '06' and g['src'] == f['dst'] and g['reg'] == f['reg']: return True
    return False
for rule in ('1s-window', 'nextread'):
    if rule == '1s-window':
        un = 0
        for i, f in reads:
            hit = any(g['func'] == '06' and g['src'] == f['dst'] and g['reg'] == f['reg']
                      for g in seg05[i+1:] if (ts(g) - ts(f)).total_seconds() <= 1.0)
            un += (not hit)
    else:
        un = sum(1 for i, f in reads if not answered(i, f, rule))
    print(f"  rule {rule}: unanswered {un} of {len(reads)}")

print("\n== F5 SAM writes to 0x20 (control test) & served 3B04/3B05 ==")
ct = load(TR + '/sam-control-test-20261029-145357.jsonl')[0]
cw = collections.Counter((f['reg'], len(D(f))) for f in ct if f['src'] == '92' and f['dst'] == '20' and f['func'] == '0C')
print("  sam-control-test 92->20 writes:", dict(cw))
samfiles = ['sam-commissioning-20261029-143248.jsonl', 'sam-control-test-20261029-145357.jsonl']
for reg in ('3B04', '3B05', '0104'):
    c = collections.Counter((len(D(f)), set(D(f)) == {0}) for p, f in corpus
                            if p in samfiles and f['src'] == '20' and f['dst'] == '92' and f['reg'] == reg and f['func'] == '06')
    print(f"  served {reg} in SAM captures (len, allzero)->count: {dict(c)}")

print("\n== F6 sam-commissioning 0x20 silence ==")
scf = load(TR + '/sam-commissioning-20261029-143248.jsonl')[0]
tx = [ts(f) for f in scf if f['src'] == '20']
best = (0, None, None)
for i in range(len(tx) - 1):
    g = (tx[i+1] - tx[i]).total_seconds()
    if g > best[0]: best = (g, tx[i], tx[i+1])
print(f"  max 0x20 tx gap in sam-commissioning: {best[0]:.3f} s, {best[1]} -> {best[2]}")

print("\n== F7 CRC table variants vs gofinity wire ==")
def crc_ref(buf):
    crc = 0
    for b in buf:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc
data = open(TR + '/external/gofinity-bootup.bin', 'rb').read()
img = open(BASE + '/firmware-re/stageB/flat.bin', 'rb').read()
B0 = 0x18040000
tabA = img[0x182B598C - B0: 0x182B598C - B0 + 32]
tabB = img[0x182B59AC - B0: 0x182B59AC - B0 + 32]
A16 = [struct.unpack_from('>H', tabA, i)[0] for i in range(0, 32, 2)]
B16 = [struct.unpack_from('>H', tabB, i)[0] for i in range(0, 32, 2)]
# generated reference nibble tables for reflected A001
def gen_tables():
    A = []; B = []
    for n in range(16):
        c = n
        for _ in range(4): c = (c >> 1) ^ (0xA001 if c & 1 else 0)
        # full 8-step for low-nibble table used in (crc>>8)^A^B form:
        c8 = n
        for _ in range(8): c8 = (c8 >> 1) ^ (0xA001 if c8 & 1 else 0)
        A.append(c8)
        c8 = n << 4
        for _ in range(8): c8 = (c8 >> 1) ^ (0xA001 if c8 & 1 else 0)
        B.append(c8)
    return A, B
gA, gB = gen_tables()
print("  image A == generated A:", A16 == gA, "| image B == generated B:", B16 == gB)
def crc_tab(buf, A, B, swap):
    crc = 0
    for b in buf:
        x = crc ^ b
        crc = (crc >> 8) ^ A[x & 0xF] ^ B[(x >> 4) & 0xF]
    return (((crc & 0xFF) << 8) | (crc >> 8)) if swap else crc
frames = []; pos = 0
while pos + 10 <= len(data):
    ln = data[pos+4]; total = ln + 10
    if pos + total > len(data): break
    fr = data[pos:pos+total]
    if crc_ref(fr[:-2]) == (fr[-2] | (fr[-1] << 8)):
        frames.append(fr); pos += total
    else: pos += 1
for swap in (False, True):
    ok = sum(1 for fr in frames if crc_tab(fr[:-2], A16, B16, swap) == (fr[-2] | (fr[-1] << 8)))
    print(f"  image-table CRC (final swap={swap}): {ok}/{len(frames)}")
