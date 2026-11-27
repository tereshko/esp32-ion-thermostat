# VERIFY — Threshold-table producers & the class word (stage P / audit-2)

Independent re-derivation from primary artifacts only: listings and decompiles in
`firmware-re/stageP/out/`, getter/setter decompiles in `firmware-re/stageC/out/`,
descriptor dump in `firmware-re/stageF/out/descriptor_table.txt`, and raw reads of
`firmware-re/stageB/flat.bin` (base 0x18040000, big-endian). Report prose was not trusted;
every number below was re-extracted or recomputed.

## Claim 1 — FUN_181f21d4 branch census: **audit-2 CONFIRMED (21 + fallback); stage P's "18" REFUTED as a word count**

Definitive recount, done three independent ways — (a) every class test in
`decomp/decomp_181f21d4.c` (all pool slots 181f246c/27c4/2b4c/2ea0/31b0/3404/374c/3a50/3bc0/3f28
resolve in `pools_181f21d4.txt` to the single cell 0xFFF8CC52 = CC52), (b) `movi20` census of
`listing/lst_main.txt` FUN_181f21d4 section, (c) `classhunt.txt` func 181f21d4 section.
All three agree exactly. **21 distinct compared class words**, each appearing exactly once:

| # | word | movi20 site | branch body |
|---|------|-------------|-------------|
| 1 | 0x8241 | 0x181f2356 | A (shared with 0x92C1) |
| 2 | 0x92C1 | 0x181f2364 | A |
| 3 | 0x8141 | 0x181f23d0 | B (shared with 0x91C1) |
| 4 | 0x91C1 | 0x181f23de | B |
| 5 | 0x8242 | 0x181f24ce | C (shared with 0xA2C2) |
| 6 | 0xA2C2 | 0x181f24dc | C |
| 7 | 0x8142 | 0x181f2556 | D (shared with 0xA1C2) |
| 8 | 0xA1C2 | 0x181f2564 | D |
| 9 | 0x92C2 | 0x181f261e | E |
| 10 | 0x91C2 | 0x181f287a | F |
| 11 | 0x85C2 | 0x181f2bf8 | G (entered by != fall-through) |
| 12 | 0x8AA2 | 0x181f2ede | H |
| 13 | 0x89A2 | 0x181f3018 | I |
| 14 | 0x8EA2 | 0x181f3246 | J |
| 15 | 0x8DA2 | 0x181f3496 | K |
| 16 | 0xC295 | 0x181f3806 | L |
| 17 | 0xC195 | 0x181f3ab6 | M |
| 18 | 0xC6A2 | 0x181f3e76 | N (calls FUN_181f169c) |
| 19 | 0xC5A2 | 0x181f3e8c | O (calls FUN_181f18dc) |
| 20 | 0xCAA2 | 0x181f3ea2 | P (calls FUN_181f1c38) |
| 21 | 0xC9A2 | 0x181f3eb8 | Q (calls FUN_181f1e78) |

Plus the fallback test on **0x8000** (movi20 @0x181f225e) and the unmatched-class default
fall-through into the tail.

Reconciliation of the two published numbers: the 21 words group into **17 branch bodies**
(4 pairs + 13 singles). 17 bodies + 1 fallback = **18** — that is what stage P's headline
counted. As a count of *compared class words* (audit-2's unit), 18 is wrong; audit-2's
**21 + fallback is correct**.

Two corrections to audit-2's own parentheticals, found in this pass:
- Audit-2 said "20 immediates in listings + 0x92C2 from classhunt @0x181f261e". The listing
  itself contains 0x92C2: `lst_main.txt` line 444 is `181f261e: movi20 #0x92c2,r1`. All 21
  are listing-visible; no classhunt-only value exists.
- (See claim 4 for the twin analogue.)

## Claim 2 — Fallback condition and effect: **CONFIRMED**

Decompile of FUN_181f21d4, pools-resolved:
`if (CC52 == -0x8000 /*0x8000*/ || CC54 == 4 || CC54 == 0)` where CC52 = *0xFFF8CC52
(pool 181f246c) and CC54 = *0xFFF8CC54 (pool 181f2478, loaded at entry from mirror
0xFFF830AD). Body: CC5A := 1, entry count := 1, index[0] := 0, CCC4[0] := 0.0,
CCDC[0] := 0.0, CD04[0] := 0.0 (cells 0xFFF8CC5A/CCF4/CC5B/CCC4/CCDC/CD04) — single-entry
zero tables — then `jmp @r3 -> 0x181f3ee4` (listing lst_main line 97), which is the
function epilogue (rts at 0x181f3eec), **skipping the shared tail at 0x181f3ec4**. ✓

## Claim 3 — Shared tail @0x181f3ec4: **CONFIRMED (listing-exact)**

`listing/lst_main.txt` lines 2999–3013:
```
181f3ec4: jsr FUN_1804e9ac        (unconditional)
181f3ec8: jsr FUN_1804ed70        (unconditional)
181f3ecc: r6 = CC52 (0xFFF8CC52); r2 = r6 & 0x7C00; cmp/eq 0x4000
181f3ede: bf 0x181f3ee4           (skip if not equal)
181f3ee0: bsr FUN_181f3f44
181f3ee4: epilogue / rts
```
Pool slots 0x181f3f3c -> 0x1804e9ac and 0x181f3f40 -> 0x1804ed70 (`pools_181f21d4.txt`).
Every non-fallback branch body reaches 0x181f3ec4 (22 jmp/bra sites in the listing,
including the 0x85C2 body's four selector sub-exits and the default fall-through). ✓

## Claim 4 — Twin FUN_181f07ec gate, 11 branches, 0x39 loop: **CONFIRMED; audit-2's "8/11" refined to 11/11**

Gate (decompile, pools-resolved: DAT_181f0ab0 -> 0xFFF8CBF4 = CBF4, DAT_181f0ab8 ->
0xFFF8CBF6 = CBF6): the body runs iff `CBF4 != 0 && CBF6 != 0 && CBF6 != 4`; equivalently
it is skipped iff **CBF4 == 0 or CBF6 in {0,4}**, exactly as claimed.

11 branch conditions, all testing the single cell CBF4 (pool slots 181f0ab0/0de0/1174/
13c0/1664 all -> 0xFFF8CBF4): 0x99, 0x199, 0x9A, 0x19A, 0x9B, 0x19B, 0x97, 0x197, 0x59,
0x5B, and the else-branch 0x39. **All 11 are listing-verifiable**: the twin section of
lst_main.txt carries 0x99/0x199/0x9A/0x19A/0x9B/0x19B/0x97/0x197 as `movi20` immediates and
0x59/0x5B/0x39 as `cmp/eq` immediates. Audit-2's note "8/11 immediates found, 3 rest on
P's decompile" understates the listing evidence — the 3 are present in the 8-bit compare
form. The branch count 11 itself is confirmed.

0x39 zone-minimum loop (decompile + `pools_181f07ec.txt`): getter reads store offset
0xCE (2 B) and 0xCEE (8 ushorts); threshold immediate 0x1C2 = 450. The loop writes the
running minimum of zone values **> 450** into *(0xFFF8CC04 + 4) = CC04[1] (pool 181f1674
-> 0xFFF8CC04). Then `if (*(float *)(0xFFF8CC1C + 4) == 450.0)` (pool 181f1678 ->
0xFFF8CC1C = CC1C; constant pool 181f1688 -> 0x43E10000 = 450.0) both CC04[1] and CC1C[1]
are set to 0.0 (pool 181f168c -> 0.0). And *(0xFFF8CC34 + 4) is set to 50000.0
(pool 181f1690 -> 0xFFF8CC34 = CC34; pool 181f1694 -> 0x47435000 = 50000.0) = CC34[1].
All three sub-claims confirmed verbatim. (Detail: the min-update is additionally gated
per zone by a byte test the decompiler renders as *0xFFF8CD7D == 1; this does not affect
the three numeric claims.)

## Claim 5 — Helper FUN_181f159c table @0x1830B094 is 6x3, keys 9/15/18/20/24/30: **CONFIRMED (raw bytes)**

`listing/lst_159c.txt`: loop bound 6 (`mov #0x6,r7`, cmp/ge), stride 3 (`mulr` by 3),
base pointer loaded from pool 0x181f1698 -> 0x1830B094 (pool file and raw image agree);
param_2 selects column +1 (==1), +2 (==2), +0 (==3); no match returns 0.0.
Raw bytes at file offset 0x2CB094 of flat.bin:
```
09 03 06 | 0F 05 0A | 12 06 0C | 14 05 0F | 18 08 10 | 1E 0A 14
```
Rows: (9,3,6) (15,5,10) (18,6,12) (20,5,15) (24,8,16) (30,10,20). Keys = **9, 15, 18,
20, 24, 30** exactly. ✓

## Claim 6 — Field store layout, offsets, defaults: **CONFIRMED (one addressing imprecision in the claim's phrasing)**

- Flat array base: getter FUN_1815927c and setter FUN_181592e4 (stageC decompiles) both
  memcpy at `DAT_181593f4 + offset` with a bounds check against a size word; raw pool read
  gives **DAT_181593f4 = 0x3C0E4A20** exactly. Both producers access fields only through
  the getter, with (offset, buf, len, 1) calls. (The stronger "accessed *only* via
  getter/setter image-wide" rests on the stage F/I caller censuses — `usersof.txt` is the
  setter's two-level census — and was not re-censused in this pass.)
- Offsets, proven by the producers' own getter calls: FUN_181f21d4 calls getter(1, ->CC52
  cell), getter(0x2F, ->CC56), getter(0x31, ->CC58), getter(8, buf, 1) for the R byte;
  FUN_181f07ec calls getter(3, ->CBF4 cell), getter(0x2D, ->CBF8). Hence **CC52 = store
  bytes [1..2], CBF4 = [3..4]** ✓. Independent corroboration: in stage F's descriptor
  dump the len-2 records for these fields carry key=0x0001 (CC52) and key=0x0003 (CBF4),
  and the R-byte record carries key=0x0008 — descriptor key == store byte offset.
- R = byte[8] / 12.0: producer computes `fStack_24 = (float)byte / DAT_181f248c`, pool
  181f248c = 0x41400000 = 12.0 (raw image verified). ✓
- Defaults: class-word descriptors (key 0x0001/0x0003, len 2) share default pointer
  **0x182F6D1A**, whose raw BE16 value is **0x0000** ✓. The R-byte descriptor
  (key 0x0008, len 1, **min 0.0 max 72.0** — the claimed range ✓) has default pointer
  **0x182F6D21**, whose raw byte is **24** ✓ (0x18 also visible at D1A+7 in a raw dump).
  Precision note: the two defaults live at *different* addresses in the same default
  cluster (words at …D1A, R byte at …D21); the claim's single-address phrasing
  "@0x182F6D1A give class words 0x0000 and R byte 24" is imprecise, the values are exact.

## Claim 7 — Class-word encoding: **CONFIRMED**

- 0x8000 always set: all 21 compared words of FUN_181f21d4 (claim 1 list) and all mapper
  inputs have bit 0x8000 set; 0x8000 itself is the bare fallback sentinel. ✓
- Bit 0x0100 = CCDC present: in tail helper FUN_1804e9ac (decompile, pool 1804ec80 ->
  0xFFF8CC52), the second array (0xFFF8CC94-side fill via FUN_1804fe5c, pool 1804ec58)
  is populated only under `(*CC52 & 0x100) != 0`, in both the per-entry loop and the
  final interpolation block. FUN_1804ed70 shows the same gate. ✓
- Bit 0x0020 gates tail interpolation: in FUN_1804e9ac the closing interpolation blocks
  for both arrays run only under `(*CC52 & 0x20) != 0`; when the bit is 0 the code instead
  does the (CC52 & 0x20)==0 bookkeeping path. Same pattern in FUN_1804ed70
  (`(*DAT_1804f2b8 & 0x20) != 0` around its interpolation block). ✓ (Audit-2's caution
  stands: the *zoning predicate* in stage R tests CBF4 bit 0x20 — a different word; the
  CC52 bit-0x20 role here is as claimed.)
- Low nibble = CC5A - 1: producer body: `*0xFFF8CC5A = ((byte)CC52 & 0xF) + 1`
  (decompile line, pool 181f2494 -> 0xFFF8CC5A). ✓

## Claim 8 — Category mapper: **CONFIRMED (decompiles + raw pool resolution)**

Target byte: pool cells DAT_180e2c4c and DAT_180e2f28 both resolve in the raw image to
**0x3C12A8D5**; the split byte DAT_180e2c50 resolves to **0xFFF8356D**. Decompiles:
- FUN_180e2a80: param in {0x92C1 (-0x6D3F), 0x91C1 (-0x6E3F)} -> byte = **1**;
  param in {0x92C2, 0x91C2} -> **2** if *0xFFF8356D == 0x17, **3** if == 0x18. ✓
- FUN_180e2ae8: param == 0x85C2 (-0x7A3E) -> **4**. ✓
- FUN_180e2afc: param in {0xA2C2 (-0x5D3E), 0xA1C2 (-0x5E3E)} -> **5**. ✓
- FUN_180e2e34: param in {0x8241 (-0x7DBF), 0x8141 (-0x7EBF)} -> **7**;
  param in {0x8242, 0x8142} -> **8**. ✓
All eight mappings exactly as claimed. (FUN_180e2b1a additionally maps 0xC295/0xC195 -> 6,
outside the claim's scope.)

## Claim 9 — Arithmetic K(60), R=5.0 tables for 0x8141/0x91C1: **CONFIRMED (recomputed from raw constants)**

Producer branch B (CC52 == 0x8141 or 0x91C1), decompile + raw-image constants:
CCC4[1] = R x 12000.0 (pool 181f24b4 = 0x463B8000);
CCDC[1] = R x 34.286 x (137.0 + 3.5 x X) (pools 181f24bc = 0x420924DD = 34.2859992980957,
181f24c0 = 137.0, 181f24c4 = 3.5 — all re-read from flat.bin, not from prose).
CD04[0] = R (set before the branch dispatch).
- K(60) = 34.2859992980957 x (137 + 3.5x60) = 34.286 x 347 = **11,897.242** (exact
  float32 recomputation: 11897.2418). ✓
- store[8] = 60 -> R = 60/12.0 = **5.0**; CCC4 = {0, **60000**, 0, 0} ✓;
  CCDC = {0, 5 x 11897.242 = **59486.21 ~= 59486.2**, 0, 0} ✓; CD04 = {5.0, ...} ✓.
Entries [0], [2], [3] are the pre-branch zero initialisation, as the claimed vectors show.

## Claim 10 — X clamp [12,61] / invalid -> 61; FUN_181f3f44 unclamped, invalid -> 65.0: **CONFIRMED**

FUN_181f21d4 prologue (decompile + pools): X = *0xFFF820F8 (pool 181f2480), validity
byte copied from 0xFFF820F5 (pool 181f2484);
`if (X < 12.0) X = 12.0;` (pool 181f248c = 0x41400000);
`if (61.0 < X || validity != 1) X = 61.0;` (pool 181f2490 = 0x42740000 = 61.0, raw-verified).
FUN_181f3f44 (decompile + pools_rest): X = *0xFFF820F8 (pool 181f4214), validity from
0xFFF820F5 (pool 181f4218); `if (validity != 1) X = 65.0` (pool 181f421c = 0x42820000 =
65.0, raw-verified); no clamp comparison is applied to X anywhere in the function. ✓

---

### Bottom line

No substantive claim of stage P / audit-2 on this topic is refuted. Audit-2's census
(21 + fallback) is confirmed by three independent extractions; stage P's headline "18"
is a body count (17 bodies + fallback), wrong only as a word count. Two audit-2
parentheticals are themselves corrected above (0x92C2 *is* in the listing at 0x181f261e;
the twin's 11 branches are *all* listing-verifiable, 3 of them in cmp/eq form), and
claim 6's default-address phrasing is imprecise (R default at 0x182F6D21, not …D1A)
while its values are exact.
