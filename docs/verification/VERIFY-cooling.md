# VERIFY — Cooling wire behaviour (stage T claims)

Independent re-derivation from the primary capture corpus. Method: own parser
over the 12 top-level files in `traces/*.jsonl` (JSONL records
`ts/src/dst/func/reg/data`); frames counted and payloads decoded directly
(floats = big-endian IEEE-754 float32). `traces/segments/*` are duplicate
slices of the coldstart session and were excluded from all censuses (used
once, for the fan-only check in claim 4). No report prose was trusted; stage
T's numbers were treated only as claims to test.

Corpus parsed: **83,755 lines, 83,752 frame records** across 12 files
(3 lines blank/unparseable).

---

## Claim 1 — 0605 burst census: 651 bursts; 0.0 ×616, 5.0 ×34, 3.0 ×1

**CONFIRMED — exact match.**

All writes `0x20 → 0x53`, reg `0605`, with payload (func 0C), counted per file
and summed: **651**. Float census of bytes [0..3]:

| Float | Count |
|---|---|
| 0.0 | 616 |
| 5.0 | 34 |
| 3.0 | 1 |

Full-payload census (4 distinct payloads, all 7 B):
`00000000000001` ×571, `00000000010001` ×45, `40A00000010001` ×34,
`40400000010001` ×1. (The 616 zeros split 571/45 by byte [4].)
The only other 0605 writes in the corpus are 22 all-zero broadcasts to 0xF1
(boot/identity transition), correctly outside the directed census.

## Claim 2 — the single 3.0 frame is at 2026-11-03T20:03:34Z and is transitional

**CONFIRMED.**

The unique 3.0 payload `40400000010001` sits in
`phase3-validation3-20261103-145755.jsonl` at **2026-11-03T20:03:34.122Z**.
Context: the preceding heat call's 0305 demand had already zeroed (last heat
0305 at 20:03:19; the 0305 write at 20:03:29 is all-zero demand, CFM bytes
only); 060D stayed `02`; the following 0605 bursts (20:03:44, 20:03:54,
20:04:04 — end of file) are back to float 0.0; no compressor start followed
(no 5.0, no RPM readback activity). One-burst transition transient, exactly
as claimed.

## Claim 3 — the one captured cool call

**CONFIRMED in substance; one sub-item REFUTED (EXV absolutism).**

Coldstart file, 2026-10-29. 0605 float: 0.0 until **17:07:31.090Z**, then
**5.0 in every one of the 34 bursts** through 17:13:03.511Z, then **0.0 at
17:13:13.330Z — a one-step drop, no ramp-down**. ✔

- **RPM ramp ✔:** 0604 readbacks: target 2180 first seen 17:07:39 (current 0),
  current chases 1170 → 1986, target steps 2850 (17:08:09), touches 4140 at
  17:09:24, dips to 3700, back to 4140 at 17:10:44; **current reaches 4140 at
  17:10:54 — ≈3.4 min after call start**, matching "~2180→4140 over ~3.5 min".
- **0608 requested CFM ✔:** 938 (17:07:34) → 1201 → ~1195 (slight sag) →
  1485 → **1600** (17:10:44). Endpoints 938→1600 as claimed.
- **0305 CFM independent ✔:** 0 → **1232** (17:09:27) → **1760** (17:10:57) →
  1710 → 1660 — first rise ~2 min after the call started, while 0608 was
  already at 938 from the first seconds; different steps at different times.
- **EXV "pinned at 100%" ✘ REFUTED as an absolute:** the first in-call 0608
  readback (17:07:34.546Z, ~3 s after the first 5.0 burst) reads **EXV = 45%**
  (CFM already 938). All remaining in-window readbacks are 100 (65 of 66
  samples inside the 5.0 window). Correct statement: EXV reaches 100% within
  ~8 s of call start and stays there; it is not 100% from the first sample.

## Claim 4 — 0605 bytes [6] and [4]

**[6]: CONFIRMED. [4]: tail CONFIRMED (~3 min, measured); heat/fan CONFIRMED;
"[4] = 0 at idle" REFUTED as an absolute.**

- Byte [6] = 0x01 in **651/651** directed writes. (Byte [5] = 0x00 in 651/651
  as well.)
- Byte [4] = 1 in all 34 bursts of the cool call. After the last 5.0 burst
  (17:13:03.511Z) it stays 1 for **18 further bursts** with float already 0.0,
  last at 17:16:05.612Z (**+182 s**), clearing at 17:16:15.368Z (+192 s).
  Tail ≈ 3 min — **CONFIRMED**.
- Heat calls: [4] = 0 in **54/54** 0605 bursts inside the three heat-demand
  windows found corpus-wide (coldstart 21/21, 400a-test-141705 18/18,
  validation3 15/15). **CONFIRMED.**
- Fan-only: [4] = 0 in 23/23 bursts of segment `02-fan-only.jsonl`.
  **CONFIRMED.**
- Idle absolutism **REFUTED**: 45 bursts carry float 0.0 with [4] = 1; only
  18 are the cool-call tail. The other **27** sit outside any call: 24 at the
  head of `400a-test-20261030-141705` (18:17:10–18:21:01, float 0.0, no heat
  demand yet — the run ends ~4 s before that file's heat window opens) and
  3 after the 3.0 frame in validation3 (to end of file). So [4] is not a
  clean "call + 3 min tail" flag; it also sets in non-call windows (stage T
  §2.3 in fact documents these windows — the claim as posed to this audit
  overstated the idle case).

## Claim 5 — 061E in every burst, identical; companions constant

**CONFIRMED.**

- 061E writes `0x20 → 0x53`: **651**, and the per-file counts equal the 0605
  counts in **all 12 files**. Pairing check: **651/651** 0605 bursts have a
  061E write within 2 s after them.
- Payload: a single distinct value in 651/651 — `0F3FD851EC06000000`
  (byte [0] 0x0F, float [1..4] = 1.69, byte [5] 0x06, zeros). Identical across
  the whole corpus, including the `sam-commissioning` file (which contains
  only 4 ODU bursts, all with this payload — the before/after re-commissioning
  identity holds there and, more strongly, corpus-wide).
- Companions, 651 writes each, one payload each:
  0610 = `00000000` (zeros ✔); 0612 = `22B80000000000000000` (starts 22B8 ✔);
  061A = `01` ✔.

## Claim 6 — 060D leads the demand bytes by up to ~2 bursts at call start

**REFUTED (the lead is real; the magnitude is ~3–7× larger).**

Measured 00→02 transitions of 060D against the first nonzero 0305 demand
byte:

| Call start | 060D → 02 | First 0305 demand | Lead |
|---|---|---|---|
| Cool, coldstart | 17:06:20.955Z | 17:07:26.118Z (cool [2]=02) | **65.2 s = 6 bursts** (6 0605 bursts and 6 0305 writes fall inside the window) |
| Heat, coldstart | 17:16:15.455Z | 17:18:30.272Z (heat [0]>0) | **134.8 s ≈ 13 bursts** |
| Heat, validation3 | 19:58:32.088Z | 20:00:48.779Z (heat [0]>0) | **136.7 s ≈ 14 bursts** |

060D does lead — it is set during the preceding pause while 0305 is still
all-zero — but by ~1–2.3 **minutes**, not ~2 bursts. (Stage T's own §1 table
already shows 060D set at 17:07:01 with 0305 still zero; the "~2 bursts"
figure in §4 does not survive a timestamp diff.)

## Claim 7 — 061F changing bytes and floats

**REFUTED as generalised; the cool-scoped parts CONFIRM.**

Corpus: 1,490 responses `0x53 → 0x20` reg 061F, all 81 B, 79 distinct
payloads. Byte-wise variance over the **whole corpus**: bytes
17, 18, 19, 20, 30, 31, 32, 33, 58, 59, 60, 61 change — **and byte 41 also
changes**, which the claim omits. Byte 41 is the last byte of the word at
[38..41]: `…1000` vs `…1002` (values {0: 554 responses, 2: 936}); it takes
both values *within* the coldstart file and within validation2, so this is
not merely a cross-file artefact. Within the cool-call-vs-idle diff that
stage T actually performed, the varying set {17–20, 30–33, 58–61} is
correct — the claim fails only in its "ever" (corpus-wide) form.

- Offset-17 float: **CONFIRMED.** Coldstart pre-call responses carry exactly
  one distinct value, **0.0** (idle); during the cool call (72 responses)
  it ranges **−66.5 … +25.22**; corpus-wide min/max identical (−66.5 /
  +25.22), i.e. it moves only in cooling.
- Offsets 1 / 5 / 9 / 13: **CONFIRMED** — exactly one distinct float each
  across all 1,490 responses (8.6, 16.3, 20.3, 18.3). They never move.

---

## Summary of verdicts

| # | Claim | Verdict |
|---|---|---|
| 1 | 651 bursts; 0.0 ×616 / 5.0 ×34 / 3.0 ×1 | CONFIRMED (exact) |
| 2 | 3.0 frame 2026-11-03T20:03:34Z, transitional | CONFIRMED |
| 3 | Cool call: 5.0 constant, RPM/CFM behaviour, one-step end | CONFIRMED, except EXV "pinned at 100%" REFUTED (one 45% sample at call start) |
| 4 | [6]=0x01 651/651; [4] call + ~3 min tail; 0 in heat/fan/idle | [6] CONFIRMED; tail CONFIRMED (18 bursts, +182 s); heat/fan CONFIRMED; idle absolutism REFUTED (27 extra [4]=1 bursts outside calls) |
| 5 | 061E 651/651 identical incl. re-commissioning; companions constant | CONFIRMED |
| 6 | 060D leads by up to ~2 bursts | REFUTED — lead is 65 s (cool) to ~137 s (heat), 6–14 bursts |
| 7 | 061F: only bytes 17–20/30–33/58–61 ever change; @17 idle 0.0, cool −66.5…+25.2; @1/5/9/13 frozen | REFUTED corpus-wide (byte 41 also changes); @17 and @1/5/9/13 parts CONFIRMED |
