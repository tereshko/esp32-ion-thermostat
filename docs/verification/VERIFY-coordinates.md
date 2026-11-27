# VERIFY — Coordinate conversion & session evaluator (stage Q, as corrected by audit-2)

Independent re-derivation from primary artifacts only: Ghidra listings
(`firmware-re/stageQ/out/listing_acc.txt`), decompiles (stageQ decompQ1–Q4,
stageG decomp1/decomp2, stageL decomp + pools), stageQ's pool resolution for
FUN_180c15d2, and the flat image `firmware-re/stageB/flat.bin` (base
0x18040000) read directly for every pool word and float constant cited.
Two spots were additionally checked in raw capstone disassembly
(stageB/dis_chunk.py). Report prose (stage Q, audit-2) was used only to know
what to test, never as evidence.

Corrected mode semantics applied throughout (stage S, adopted by audit-2):
**CD7D: 1 = HEAT, 2 = COOL, 3 = AUTO.** CCC4 = mode-2 (cool) table,
CCDC = heat table.

---

## Claim 1 — Accessor pairs, CD94/CD98 cells, CD90 staging, dispatcher routing

**CONFIRMED** (listing-level, `listing_acc.txt`).

- `FUN_181f77f4`: `fmov.s @r3,fr2` with r3 = *0x181F7854 → **0xFFF8CD94** —
  channel-1 getter reads CD94. `FUN_181f7822`: r3 = *0x181F7860 →
  **0xFFF8CD98** — channel-2 getter reads CD98.
- `FUN_181f77fc` (ch1 setter): writes the value to **CD94**, then to
  **CD90** (pool 0x181F7850 → 0xFFF8CD90), then calls **FUN_181f4d04**
  (pool 0x181F785C) with r4 = &CD90, r5 = *0x181F7858 → 0x3C12EC6C.
- `FUN_181f782a` (ch2 setter): calls FUN_181f4d04 **first**, with r4 = &CD90
  and r5 = a stack copy of the value; afterwards writes the (possibly
  clamped) copy to **CD98** and to **0x3C12EC6C**.
- Both setters call the clamp dispatcher exactly once; both pass &CD90 as
  the dispatcher's param_1 (the secondary value cell — in the heat chain
  FUN_181f48de can write through it, see claim 3). "CD90 as the staging cell
  both setters route through" is accurate, with the asymmetry noted: the
  ch1 setter pre-writes CD94 and CD90 before the call; the ch2 setter
  clamps its stack copy and only then commits CD98/EC6C.

## Claim 2 — Dispatcher merge, clamp maxima set, size bands

**CONFIRMED**, with the engagement gates spelled out.

Merge: in `FUN_180c15d2`'s sibling listing of FUN_181f4d04
(`listing_acc.txt` lines 181f4d0c–181f4d3a) and its pool, resolved from the
flat image:

- pool 0x181F4E3C → **0x1830B0A8** (flash template), copied 0x2E = 46 bytes
  to the stack record by FUN_1823C6E4;
- pool 0x181F4E4C → **0xFFF82CAC** (live record), merged over it, 46 bytes,
  by the distinct merge-copy FUN_1823D404 (the same routine used for record
  overlays in FUN_181f4308 and the publish step of FUN_181f7050);
- pool 0x181F4E58 → 0xFFF8CD7D (CD7D, read directly in the dispatcher).

Maxima — every constant read from the flat image:

| Constant | Value | Where used |
|---|---|---|
| 0x181F4CE4 | 1.3 | FUN_181f4b4a, band <31, record[0]==4 |
| 0x181F4CE8 | 1.4 | FUN_181f4b4a, band <31, record[0]!=4 |
| 0x181F4CEC | 1.0 | FUN_181f4b4a, band 31–60 |
| 0x181F4CF0 | 0.0 | FUN_181f4b4a, band ≥61 (forced) |
| 0x181F4AC8 | 1.3 | FUN_181f48de, band <31, record[0]==4 |
| 0x181F4ACC | 1.4 | FUN_181f48de, band <31, record[0]!=4 |
| 0x181F4AD0 | 1.0 | FUN_181f48de, band 31–60 |
| 0x181F4A90 | 0.0 | FUN_181f48de, band ≥61 (forced) |
| 0x181F4CE0 | 2.0 | FUN_181f4b32 (cool chain, bit-0x20 clear, record[0]==4, <31) |
| 0x181F4AD4 | 2.0 | FUN_181f4a74 (heat chain, bit-0x20 clear, record[0]==4, <31) |

The claimed union {0.0, 1.0, 1.3 (record[0]==4) / 1.4, 2.0} is exact.

Size bands: the size byte is the merged record's byte at offset 0x10
(dispatcher listing: `mov.b @(0x10,r15),r4` passed as first argument to
both mode handlers). Both band implementations use identical thresholds:
< 0x1F (31), 0x1F–0x3C (31–60), ≥ 0x3D (61) — FUN_181f4b4a decompile
(`param_1 < 0x1f`, `0x1e < param_1 && param_1 < 0x3d`, else forced) and
FUN_181f48de raw listing at 0x181F48EC–0x181F490C (`cmp/gt #30` /
`cmp/gt #60` building the two band flags).

Gates the claim omits (mechanics unaffected): the dispatcher acts only if
the record predicate FUN_181f4c9e passes (record[6]==4 &&
record[0]∈{3,4} && record[5]==2 — decompile, decompQ3) and a record byte
is 0; each mode chain then requires class-word bit 0x20 for the main clamp
(FUN_181f4ad8/FUN_181f4bca decompiles), else the record[0]==4 fallback
(2.0 clamp, band <31 only) applies.

## Claim 3 — Audit-2's correction: derate mode, latch side

**PARTIALLY REFUTED.** The primary attribution holds; the exclusivity
("not heat") does not.

- Dispatcher listing (`listing_acc.txt` 181f4d64–181f4dc6): CD7D is
  compared against **1** → calls FUN_181f4ad8; against **2** → calls
  FUN_181f4bca. FUN_181f4bca (decompile) with class bit 0x20 set calls
  FUN_181f4b4a, whose ≥61 branch is `*param_2 = DAT_181f4cf0` = **0.0,
  forced assignment**. So the FUN_181f4b4a derate Q's table described is
  indeed in the **CD7D==2 = COOL** chain. Audit-2's correction of Q is
  verified at the listing level.
- **But the heat chain derates too.** FUN_181f48de (CD7D==1 chain via
  FUN_181f4ad8, bit 0x20 set), raw listing 0x181F498A–0x181F4A6E: band
  flags select the ≥61 block at 0x181F4A60, which executes
  `mova 0x181F4A90,r0; fmov.s @r0,fr7` (fr7 := 0.0),
  `fmov.s fr7,@r14` (**\*param_3 := 0.0, unconditional**), and, when the
  bVar2 flag (class word bit 0x40 set, an auxiliary byte == 0,
  record[0] != 4) holds, `fmov.s fr7,@r13` (\*param_4 := 0.0). The
  decompile (decompQ4) renders the same branch. So "size ≥61 → 0.0
  applies in COOL mode (not heat)" is false as an exclusive statement:
  **both mode chains force the coordinate to 0.0 at size ≥ 61**; they
  differ in which cells they write (cool: the value cell; heat: both
  value cells, the second conditionally).
- Excess latch is heat-side: **CONFIRMED** — see claim 4 (latch block is
  gated CD7D==1 and works over CCDC).

## Claim 4 — Converter FUN_180c15d2

**MIXED: five of six sub-claims CONFIRMED; the cap attribution REFUTED.**

Pool resolutions are stageQ's `pool_180c15d2.txt`, cross-checked against
the stageG decompile of the function.

- **Zeroes both coordinates at entry — CONFIRMED.** Head of the function:
  pool 0x180C17B8 = literal 0.0; calls FUN_181f77fc(0.0) (pool 0x180C17D0)
  and FUN_181f782a(0.0) (pool 0x180C17BC) before anything else.
- **"Caps demand at the mode-2 table's last entry" — REFUTED as stated.**
  The head cap reads: `fStack_44 = CD44` (pool 0x180C17D4 → 0xFFF8CD44);
  `if (CD79 != 0 && *(CCDC + (CC5A−1)*4) < fStack_44 && CD7D == 1)
  fStack_44 = CCDC[CC5A−1]`, with pool 0x180C17DC → **0xFFF8CCDC (CCDC)**,
  0x180C17E0 → CC5A, 0x180C17E4 → CD7D. The cap is over the **heat
  table CCDC, gated to HEAT mode (CD7D==1)** — the same quantity the
  latch uses. No CCC4 cap exists at the head. (A second, distinct cap
  over the mode-selected table's last entry does occur later, inside the
  channel-2 interpolation, for whichever mode is active — see below.)
- **Latches excess over CCDC maximum — CONFIRMED.** Under gates
  (CC52 & 0x100, CD7C != 0, CD7D == 1, CC54 != 3, CBF4 bit 0x40 or 0x20):
  `excess = CD44 − CCDC[CC5A−1]`; running maximum stored to pool
  0x180C17FC → **0x3C12A844** (A844); if the latched value < 1.0
  (pool 0x180C1800 = 1.0f) the latch-state flag A848 (0x3C12A848) is set
  and CD7B cleared.
- **Channel 1 inverse-interpolated over CC34 with the latched excess —
  CONFIRMED.** Segment machinery works on pool 0x180C1A94 / 0x180C1D00 →
  **0xFFF8CC34 (CC34)**; in the gated path the interpolated argument is
  the excess fStack_48 and the result is written through
  FUN_181f77fc (pool 0x180C1D20) and read back via FUN_181f77f4.
  Segment indices are mirrored to A838/A839 (pool 0x180C1AB8/0x180C1ABC →
  0x3C12A838/0x3C12A839).
- **Channel 2 over CCDC (heat) / CCC4 (cool) — CONFIRMED.** The table
  load is selected by CD7D itself: `if (CD7D == 1)` x-array from pool
  0x180C1D58 → **CCDC**, y-array from 0x180C1D5C → CC94; `else if
  (CD7D == 2)` x-array from pool 0x180C1EE8 → **0xFFF8CCC4 (CCC4)**,
  y-array from 0x180C1EEC → CC64. Writes go through FUN_181f782a
  (pools 0x180C24DC, 0x180C27B8), read-backs via FUN_181f7822.
- **Tail recomputes CD8C := forward-eval(ch1) + forward-eval(ch2) —
  CONFIRMED.** Final arithmetic: `*0xFFF8CD8C = *0xFFF874A8 +
  *0xFFF874AC` (pool 0x180C2B04 → CD8C), where 0xFFF874A8 is the
  channel-1 forward value produced by the CC34 interpolation paths and
  0xFFF874AC the channel-2 forward value. A84C (pool 0x180C2AD4 →
  0x3C12A84C) is written as a segment endpoint divided by 2.0
  (pool 0x180C2AF4), matching Q's structural identification.

## Claim 5 — FUN_181f4308 forward composition and zone split

**CONFIRMED** (stageL decompile + `pools_181f4308.txt`, all slots
resolved there and spot-checked against the image).

- Selector is CD7D itself (pool 0x181F480C → 0xFFF8CD7D); target is CD8C
  (pool 0x181F4834 → 0xFFF8CD8C).
- Term 1 (local_44): forward interpolation over pool 0x181F4818 →
  **0xFFF8CC34 (CC34)** at the coordinate returned by the channel-1
  getter FUN_181f77f4 (pool 0x181F4820) — CC34(P1).
- Term 2 (fStack_40): over pool 0x181F4828 → **0xFFF8CCC4 (CCC4)** at the
  channel-2 getter FUN_181f7822 (pool 0x181F482C) — CCC4(P2).
- Term 3 (fVar8): over pool 0x181F4830 → **0xFFF8CCDC (CCDC)**, same
  channel-2 getter — CCDC(P2).
- Combine: `CD7D == 2 → CD8C := fStack_40` (**cool = CCC4(P2) only**);
  `CD7D == 1 → CD8C := local_44 + fVar8` (**heat = CC34(P1) +
  CCDC(P2), both channels**); otherwise CD8C := 0.0 fallback. Exactly
  the audit-2-corrected composition.
- Equal split: zones are counted over 8 via predicate FUN_181f035c
  (pool 0x181F4840); for each active zone,
  `C8CC[i] = CD8C / count` (array pool 0x181F484C → 0xFFF8C8CC);
  inactive zones get 0.0 in both output arrays. **CONFIRMED.**

## Claim 6 — Table scale: R·12000 and the 34.286 factor

**CONFIRMED in substance; the "= 12000/350" identity is approximate,
not bit-exact.**

- Producer FUN_181f21d4 (stageL decompile + `pools_181f21d4.txt`):
  pool 0x181F24A0 → CCC4 base, and the code writes
  `CCC4[1] = fStack_24 * DAT_181f24b4` with pool 0x181F24B4 = **12000.0**
  (0x463B8000); pool 0x181F24A8 → CCDC base, and
  `CCDC[1] = fStack_24 * DAT_181f24bc * (...)` with pool 0x181F24BC =
  **34.286**. The pair (12000.0, 34.286) recurs at pools
  0x181F27D0/0x181F27E8 and 0x181F2B2C/0x181F2B80/0x181F2E74/0x181F2ED0 —
  the scale is systematic in the producer, applied to the quantity
  fStack_24 (the R-derived input).
- Precision: the stored literal is **0x420924DD = 34.28599929…**, i.e.
  the decimal constant 34.286. 12000/350 = 34.285714… would be
  0x42092492. Relative difference ≈ 8.3e-6. The claim's arithmetic gloss
  "34.286 = 12000/350" (and "12000 = BTU/h per ton, 350 = CFM/ton") is a
  sound interpretation of the design intent, but the firmware constant
  is the rounded 34.286, not the quotient.

## Claim 7 — Session evaluator FUN_181f7050

**CONFIRMED in every particular.** All pool slots below were resolved by
my own dump of the flat image (stageG's decompile carries no pool file).

- Loop runs over **8 zones** (`while ((uVar4 & 0xff) < 8)`).
- Zone state array: pool 0x181F72DC → **0xFFF8CBA9 (CBA9)**. When a
  zone's session flag (0xFFF8C618) is 0 and CBA9[i] becomes **4**, the
  tick getter FUN_180BC636 (pool 0x181F72E0) is stored into the start
  array 0xFFF8C5B8 and the flag set — timestamping **CONFIRMED**.
- While active: accumulator 0xFFF8C5F8[i] += *pool 0x181F7300
  (**0xFFF8CD8C = CD8C**) × *(pool 0x181F7304 → **0xFFF8CD1C = CD1C**)[i]
  — **CD8C × CD1C[i] accumulation CONFIRMED**. Sole caller is
  FUN_181f8592 (COMPUTED_CALL at 0x181F85A6, stageG `usersG2.txt`), the
  class-6 hub function — "per hub cycle" stands.
- Session end: Δt = end − start with wrap correction **+4294967296.0**
  (2^32; pool 0x181F730C) when the unsigned difference underflows, then
  minutes = Δt / **60000.0** (pool 0x181F7310 = 0x476A6000), with a
  second correction subtracting 2×2147483648.0 (pool 0x181F7314 = 2^31)
  when minutes ≥ 2^31 — the signed-32 ms-counter wrap. Minutes stored
  to 0xFFF8C620. **CONFIRMED.**
- Score: mode from CD7D (pool 0x181F731C); ==1 → CADC[i] (0xFFF8CADC) −
  CB60[i] (0xFFF8CB60); ==2 → CB60[i] − CABC[i] (0xFFF8CABC). Threshold
  pool 0x181F732C = **1.875**. |deviation| ≥ 1.875 writes byte **0xF6
  (−10)**; otherwise byte **10**. Both writes land in the same score
  array **0xFFF8C640** (pools 0x181F74B8 and 0x181F72F4 resolve to the
  same address). **±10 score CONFIRMED.** (Mode-1 deviation is the heat
  deviation, per the corrected labels — consistent with stage O's
  mode-1 error CADC−CB60.)
- Mean and share guards: mean[i] (0xFFF8C648) = accumulator[i] /
  minutes[i], but **:= 0.0 when (float)minutes ≤ 1.875** (the threshold
  constant is reloaded into fVar6 from pool 0x181F732C before the
  guards); share[i] (0xFFF8C668) = mean[i] / *pool 0x181F74D8
  (**0xFFF8CE60 = CE60**), **:= 0.0 when CE60 ≤ 1.875**. **"Guarded at
  1.875" CONFIRMED** for both.
- Publish destinations: the closing merge-copies (FUN_1823D404 under the
  180BC05A/180BC06E brackets) target pool 0x181F74E8 → **0xFFF8418C**
  (minutes, 0x20 B, from 0xFFF8C620), pool 0x181F74F4 → **0xFFF841AC**
  (score, 8 B, from 0xFFF8C640), pool 0x181F74F8 → **0xFFF841B4**
  (mean, 0x20 B, from 0xFFF8C648), pool 0x181F74FC → **0xFFF841D4**
  (share, 0x20 B, from 0xFFF8C668). **Exactly the claimed addresses.**

## Claim 8 — Mirror publisher FUN_181f4e60

**CONFIRMED in role and target object; the "~40" count is corrected
upward.**

My recount over the decompile (decompQ4), resolving every destination
pool word from the flat image: **47 scalar bracketed copies + 16 bulk
copies (mostly 0x20 B) = 63 copy operations**, each bracketed by the
FUN_180BC05A / FUN_180BC06E lock pair, into **63 distinct destinations
spanning 0xFFF83E29–0xFFF8423A** (bulk extents reach 0xFFF84230). Bulk
sources include the evaluator's own arrays (0xFFF8C8CC → object
+0xFFF83EB0, 0xFFF8C910 → +0xFFF83ED0, etc.), consistent with a
decision-block mirror. The claimed object span 0xFFF83E28–0xFFF84238
matches within two bytes at both ends (first scalar destination is the
byte field at +1; the last two scalar destinations are byte fields at
0xFFF84239/0xFFF8423A). Substance stands; the count is **63 operations,
not ~40**.

## Claim 9 — Negative: no dictionary names for 0x3C12EC6C / 0x3C12A838–A84C

**CONFIRMED by independent re-run** (my own scanner, not stageQ's
`parse_reg.py`; run against `firmware-re/stageB/flat.bin`).

Method: whole-image scan at stride 4 for candidate registration records
in **both** field orders — (name_ptr, id) and (id, name_ptr) — where
id ∈ [0x3C120000, 0x3C130000) and name_ptr points inside the image to a
printable ASCII string of ≥ 2 chars. Result: 232 records in (name,id)
order and 266 in (id,name) order; **zero** records carry any target id
in {0x3C12EC6C} ∪ [0x3C12A838, 0x3C12A84C]. Sanity check: the target
values occur image-wide only as code literal-pool cells — 0x3C12EC6C
exactly once (0x181F7858, the channel-2 setter's pool) and 0x3C12A844
twice (0x180C17FC, 0x180C2AD8, both in FUN_180c15d2's pool) — i.e. they
are referenced as runtime cell addresses, never registered with a name.
The addresses are runtime object-instance fields, as Q concluded.

---

## Verdict summary

| # | Claim | Verdict |
|---|---|---|
| 1 | Accessors CD94/CD98, CD90 staging, dispatcher routing | CONFIRMED |
| 2 | Dispatcher merge, maxima {0.0, 1.0, 1.3/1.4, 2.0}, bands from record[0x10] | CONFIRMED |
| 3 | Audit-2 correction: derate is COOL-side, latch is HEAT-side | PARTIALLY REFUTED — 4b4a derate is cool-side and the latch is heat-side, but the heat chain FUN_181f48de also forces 0.0 at size ≥61; "not heat" is false |
| 4 | Converter FUN_180c15d2 | MIXED — entry zeroing, latch, CC34/CCDC/CCC4 routing and the CD8C tail CONFIRMED; "caps demand at the mode-2 table's last entry" REFUTED (head cap is over CCDC, gated CD7D==1) |
| 5 | FUN_181f4308: heat = CC34(P1)+CCDC(P2), cool = CCC4(P2); equal split into C8CC | CONFIRMED |
| 6 | Scale R·12000, CCDC factor 34.286 = 12000/350 | CONFIRMED with precision caveat (stored literal is decimal 34.286, 0x420924DD; the quotient would be 0x42092492) |
| 7 | Evaluator FUN_181f7050 (8 zones, timestamps, CD8C×CD1C, /60000.0, 1.875 guards, ±10 score, publish addresses) | CONFIRMED |
| 8 | Mirror publisher FUN_181f4e60, ~40 copies into 0xFFF83E28–0xFFF84238 | CONFIRMED in role/range; count corrected to 63 copy operations |
| 9 | No dictionary names for 0x3C12EC6C / 0x3C12A838–A84C | CONFIRMED (independent re-run, both record orders) |
