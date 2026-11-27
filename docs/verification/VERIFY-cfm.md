# VERIFY-cfm — Independent re-derivation of stage R (CFM computation)

Method: primary artifacts only — decompiles in `firmware-re/stageR/decomp/`,
`stageN/out/decomp2/`, `stageJ/out/`, `stageI/out/`, `stageG/out/`, `stageQ/out/`;
literal pools resolved by the verifier directly from the flat image
`firmware-re/stageB/flat.bin` (base 0x18040000, big-endian); whole-image BSR census
by raw opcode scan; captures re-parsed from `traces/*.jsonl` by the verifier.
Report prose (stage R, audit-2) was not trusted for any verdict.

**Result: no claim REFUTED. All 9 claims CONFIRMED; claims 2, 5, 6 carry
precision refinements noted inline.**

---

## Claim 1 — CD88 is the commanded airflow; producer FUN_1804e4b6 from FUN_181f4308's tail; FUN_180c15d2 / FUN_181f7050 do not write it

**CONFIRMED.**

- Pool slot 0x1804E988 in FUN_1804e4b6 resolves to **0xFFF8CD88 (CD88)**; the
  floor/clamp block writes through it (`*DAT_1804e988 = fVar4`). A second slot,
  0x1804E6FC, also resolves to 0xFFF8CD88 (zeroing path, `*DAT = 0.0`).
- FUN_1804e4b6 calls FUN_1804fa1c(base) via pool 0x1804E6E8 = 0x1804FA1C.
  FUN_1804fa1c's first store is `*DAT_1804fbfc = param_1`, and pool 0x1804FBFC
  resolves to **0xFFF8CD88** — so the base value lands in CD88 through fa1c,
  then e4b6's own floor/clamp block adjusts CD88 directly.
- Call site: FUN_181f4308's tail (stageR decompile) ends
  `FUN_181f4e60(); (*(code *)PTR_FUN_181f4a98)();` and pool 0x181F4A98 resolves
  to **0x1804E4B6**. So FUN_1804e4b6 runs at the tail of every refresh. ✓
- Negative census (pool references resolved from flat.bin for every DAT_/PTR_
  name in each decompile; a 32-bit RAM address is only reachable via a literal
  pool in this codebase):
  - FUN_180c15d2: 191 pool refs (stageI decompile), **0** equal to 0xFFF8CD88;
    identical result on the stageG decompile; stageQ's independent pool dump
    `stageQ/out/pool_180c15d2.txt` also contains no CD88 (it does contain
    CD44/CD7C/CD7D/CCDC-adjacent cells).
  - FUN_181f7050: 39 pool refs (stageJ decompile), **0** to CD88; identical on
    the stageG decompile.

## Claim 2 — Demand floor: CD88 raised to max(FUN_1804fca0(), 325 × CD8C / 12000.0); FUN_1804fca0 = max(configured C750 or default 300, floor 175)

**CONFIRMED, with two precision refinements.**

From FUN_1804e4b6's floor block with pools resolved:

- Call target pool 0x1804E974 = **0x1804FCA0** → `fVar4 = FUN_1804fca0()`.
- Pool 0x1804E978 = **0x1830B112** (flash); `*(ushort *)` there = **325**.
- Pool 0x1804E97C = **0xFFF8CD8C (CD8C)**.
- Pool 0x1804E980 = the inline value **0x463B8000 = 12000.0f** (value, not a
  pointer — verified numerically).
- So the demand term is `(float)(325 × CD8C) / 12000.0`, exactly as claimed.

Refinements the claim omits (do not change its substance):

1. The demand term is applied only when byte **0xFFF8C9F0 ≠ 0**
   (`if (*DAT_1804e984 != '\0') && (fVar4 < term)`), i.e. the max() is
   `fVar4 = max(fca0_result, term)` under that gate, else just the fca0 result.
2. The term is truncated to a ushort (`(uint)(...) & 0xFFFF`) before the
   comparison, and CD88 is then raised to fVar4 only if `CD88 < fVar4`.

FUN_1804fca0 itself (decompile + pools):

- Flag pool 0x1804FEDC = 0xFFF8C74F. If flag == 0 → `uVar1 = *(ushort *)`
  pool 0x1804FEE4 = flash **0x1830B10A**, whose u16 = **300** (the default).
  If flag != 0 → `uVar1 = *` pool 0x1804FEE0 = **0xFFF8C750** (the configured
  ushort cell C750, address-verified).
- Result then raised to `*(ushort *)` pool 0x1804FEE8 = flash **0x1830B108**,
  u16 = **175** (absolute floor).
- Exactly `max(configured C750 | default 300, 175)`. ✓

## Claim 3 — Flash block @0x1830B108 = {175, 300, 200, 300, 350, 325, 325, 325, 350, 350, 400}; entry @0x1830B112 = 325

**CONFIRMED.** Raw bytes at 0x1830B108 read from flat.bin:
`00af 012c 00c8 012c 015e 0145 0145 0145 015e 015e 0190`
= u16 BE {175, 300, 200, 300, 350, 325, 325, 325, 350, 350, 400}. ✓
u16 @0x1830B112 (block index 5) = **325**. ✓ This is also the exact cell the
claim-2 multiplier dereferences.

## Claim 4 — 375/400 enter via FUN_18051898 → FUN_18051cec(CD4A), one BSR @0x180518B2, gate (CC52 & 0xF) == 1; selector CD4B, windows {375,325,400,350}@FF0 / {400,350,…}@FF8

**CONFIRMED.**

- FUN_18051898 decompile: `if ((*DAT_18051a74 & 0xf) == 1) uVar1 =
  FUN_18051cec(*DAT_18051a78);` Pools: 0x18051A74 = **0xFFF8CC52 (CC52)**,
  0x18051A78 = **0xFFF8CD4A (CD4A)**. Gate and argument exactly as claimed.
- Whole-image raw BSR census (opcode 0xB000, 12-bit PC-relative displacement,
  scanned over all 15,728,640 bytes): **exactly one** BSR in the image targets
  0x18051CEC, at **0x180518B2** (instruction word 0xB21B, target computed
  0x18051CEC). ✓ Separately, exactly one u32 pool reference to 0x18051CEC
  exists, at 0x180C5D88 — the pool-visible caller; it is not a BSR and does
  not contradict the "exactly one BSR" claim.
- FUN_18051cec: first-level selector pool 0x18051D54 = **0xFFF8CD4B (CD4B)**.
  Selector 1 → returns window @0x18051FF0 when param == 5; selector 2, 3 or 4 →
  window @0x18051FF8 when param == 5.
- Floats read raw at 0x18051FF0: **{375.0, 325.0, 400.0, 350.0}**; at
  0x18051FF8: **{400.0, 350.0, …}**. (The wider literal run starting at
  0x18051FE8 is {200, 275, 375, 325, 400, 350}.) ✓

## Claim 5 — Final per-mode clamps from field store: heat [197, 199], cool [4062, 4064], 0 = unset, defaults 0

**CONFIRMED** (indices and 0 = unset verified from code; on the descriptor
"defaults 0" sub-point see the note).

FUN_1804e4b6 calls the field-store getter (pool 0x1804E998 = **0x1815927C**)
four times with (index, buf, 2, 1): **199** → auStack_14, **197** (0xC5) →
auStack_18, **4062** (0xFDE) → auStack_c, **4064** (0xFE0) → auStack_10.
Mode byte pool 0x1804E99C = 0xFFF8CD7D (CD7D):

- CD7D == 1 (heat): clamp against auStack_14 (store **199**, max) and
  auStack_18 (store **197**, min) → range [197, 199]. ✓
- CD7D == 2 (cool): clamp against auStack_10 (store **4064**, max) and
  auStack_c (store **4062**, min) → range [4062, 4064]. ✓
- In both branches a bound of **0 disables that side** (`auStack == 0` checks
  in the comparisons) — 0 = unset is code-level fact. The four stack buffers
  are zero-initialised at function entry.

Note: the factory-default values behind the getter live in the descriptor
defaults (stage F mechanism); they are not independently re-parsed here. The
claim's operative content — indices, pairing, and 0 = unset — is fully
verified from FUN_1804e4b6's code and pools.

## Claim 6 — Alternate producer FUN_180511da under predicate FUN_1805185c (CA94==0 && CA80==1 && CBF4&0x20 && CC1C[1]==0); FUN_181f5e9a override not on this unit's path

**CONFIRMED, with the "class fields" identified.**

- FUN_1805185c decompile + pools: 0x18051A60 = **0xFFF8CA94 (CA94)** compared
  == 0; 0x18051A64 = **0xFFF8CA80 (CA80)** compared == 1; 0x18051A68 =
  **0xFFF8CBF4 (CBF4)** tested & 0x20; 0x18051A6C = **0xFFF8CC1C (CC1C)** with
  `*(float *)(CC1C + 4) == 0.0`, i.e. CC1C[1] == 0. Predicate exactly as
  claimed. ✓
- Wiring in FUN_1804e4b6: predicate via pool 0x1804E6D0 = **0x1805185C**;
  alternate producer via pool 0x1804E6D4 = **0x180511DA**, called when the
  predicate returns non-zero. FUN_180511da itself references CD88 (its pool
  0x180512A4 = 0xFFF8CD88), consistent with it being a real alternate producer
  of the same cell. ✓
- FUN_181f5e9a: both gate cells resolve to CC52 (pools 0x181F5F64 and
  0x181F6508 = **0xFFF8CC52**). The gates are full-16-bit compares:
  branch 1 requires CC52 ∈ {0x89A2, 0x8AA2}, branch 2 requires
  CC52 ∈ {0x8DA2, 0x8EA2}; otherwise the function falls through to a
  pass-through (`*out = param_1`). This unit's candidate class words
  {0x8141, 0x91C1} (stage P) match none of the four gate values, so the
  override branches cannot execute on this unit. ✓
- What the "class fields 0x0000/0x1000" are: they are the **family field
  (CC52 & 0x7C00)** of the two candidate words — 0x8141 & 0x7C00 = 0x0000 and
  0x91C1 & 0x7C00 = 0x1000 (arithmetic verified). The gated words' family
  fields are 0x0800 (0x89A2/0x8AA2) and 0x0C00 (0x8DA2/0x8EA2) — disjoint from
  both candidates, which is the precise sense in which the override is not on
  this unit's path. (The claim's shorthand "class-0x800" matches branch 1's
  family field 0x0800.)

## Claim 7 — Cap base = min(base, FUN_18052354()); per-zone split CD9C[i] = CD88 × CD1C[i] in FUN_1804fa1c

**CONFIRMED.**

- FUN_1804e4b6: pool 0x1804E6C0 = **0x18052354**, called before the mode
  branches (`fVar4 = FUN_18052354()`). In both branches:
  `local_2c = <mode base>; if (fVar4 < local_2c) local_2c = fVar4;` — i.e.
  base := min(base, FUN_18052354()). ✓
- FUN_1804fa1c: after storing CD88 = param_1, it loops i = 0..7 and computes
  `*(float *)(DAT_1804fc0c + i*4) = *CD88 * *(float *)(DAT_1804fc08 + i*4)`.
  Pools: 0x1804FC0C = **0xFFF8CD9C (CD9C)**, 0x1804FC08 = **0xFFF8CD1C
  (CD1C)**. So CD9C[i] = CD88 × CD1C[i]. ✓ (A second array at 0xFFF8CDBC
  receives the same split of the CD8C cell; not part of the claim.)

## Claim 8 — Capture signature

**CONFIRMED in full.** Verifier re-parsed all 12 files in `traces/*.jsonl`,
extracting every src=0x20 func 0x0C reg 0305 frame (12-byte payloads, CFM =
u16 BE at bytes [4..5]):

- **Full observed CFM set = {0, 378, 379, 382, 384, 1166, 1232, 1368, 1617,
  1660, 1710, 1750, 1760}** — exactly the claimed set, no missing values, no
  extras. **Maximum = 1760.** ✓
- CFM = 0 at idle: 0 appears in every file; purely-idle captures
  (phase3-validation, phase3-validation2, sam-control-test, sam-reseat) show
  only 0. ✓
- Cool stage-2 ramp: segment `traces/segments/04-cool-70F.jsonl` compressed
  CFM sequence = **[0, 1232, 1760, 1710, 1660]** — exactly the claimed
  0→1232→1760→1710→1660. ✓
- Heat: segment 06-heat-75-79F compressed sequence contains **1368 → 1617**;
  value 1617 occurs in two independent captures — coldstart-20261029 (8×) and
  phase3-validation3-20261103 (9×) — i.e. it repeats exactly across traces. ✓
- Fan-only: segment 02-fan-only compressed = [0, **1166, 379**, 0] — 1166
  settling into the claimed ~380 band; across the corpus the settle values
  are 378 (400a-test-145554), 379 (fan-only segment), 382
  (phase3-validation3), 384 (coldstart) — the full claimed wobble band
  378–384. ✓
- Commissioning traces show exactly **1750**: full-install-20261029 (3×) and
  sam-commissioning-20261029 (1×), and 1750 occurs nowhere else. ✓

## Claim 9 — Bulk mirror FUN_181f4e60 does NOT copy CD88

**CONFIRMED.** Pool census as in claim 1: FUN_181f4e60 has 136 pool references
in its decompile; resolving every one from flat.bin yields **0** equal to
0xFFF8CD88 — in both the stageN and the stageQ decompiles. The mirror cannot
address CD88, so CD88 does not cross through it. ✓

---

## Summary table

| # | Claim (short) | Verdict |
|---|---|---|
| 1 | CD88 producer = FUN_1804e4b6 from FUN_181f4308 tail; 15d2/7050 don't write it | CONFIRMED |
| 2 | Demand floor max(fca0, 325·CD8C/12000); fca0 = max(C750\|300, 175) | CONFIRMED (gate byte 0xFFF8C9F0 + ushort truncation omitted by the claim) |
| 3 | Flash family @0x1830B108; entry @…112 = 325 | CONFIRMED |
| 4 | 375/400 via 18051898→18051cec(CD4A), one BSR @0x180518B2, gate (CC52&0xF)==1; CD4B selector; windows | CONFIRMED |
| 5 | Store clamps heat [197,199], cool [4062,4064], 0 = unset | CONFIRMED (descriptor defaults not independently re-parsed) |
| 6 | FUN_180511da predicate; FUN_181f5e9a not on this unit's path | CONFIRMED (fields = (CC52 & 0x7C00) of candidates: 0x0000 / 0x1000) |
| 7 | Cap min(base, FUN_18052354()); split CD9C[i] = CD88 × CD1C[i] | CONFIRMED |
| 8 | Capture CFM signature incl. exact value set | CONFIRMED |
| 9 | FUN_181f4e60 does not copy CD88 | CONFIRMED |
