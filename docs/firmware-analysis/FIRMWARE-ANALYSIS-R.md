# Firmware Analysis — Stage R: where the commanded airflow (CFM) is computed

**Question (parent task):** find the producer of the CFM value carried in
the 0305 demand frame at bytes [4..5]; recover the full formula (inputs,
clamps, per-mode behaviour), the v4.79 "compressor demand response
removed" change, and the provenance chain from the computation to the
0305 bytes; verify against the captures.

**Method:** Ghidra 12.2 decompilation in a stage-R project copy
(`firmware-re/stageR/proj`), cross-checked with capstone (SH-2A)
disassembly for every function whose Ghidra typing mangles the
float/variant returns (`firmware-re/stageR/out/dis_*.txt`), raw
pool-cell resolution (`scripts/pool.py`), and whole-image BE32 cell
censuses (`scripts/cell_scan.py`). Every load-bearing claim below was
verified by two independent methods (decompile + disassembly, or
census + pool resolution). Captures: `traces/coldstart-…`,
`full-install-…`, `400a-test-…`, `phase3-validation3-…`
(`scripts/captures0305.py`, `scripts/timeline.py`).

---

## 0. Verdict

- **[FACT] The commanded airflow is the float cell `0xFFF8CD88`
  (CD88) in the decision block.** It is the only CFM-scale cell in the
  block: it is written by the airflow computation cluster, clamped by
  CFM limit fields, distributed per-zone, and zeroed at idle together
  with the demand total CD8C (reset function @ `0x181F026E` stores 0.0
  to both). Captured 0305 CFM = 0 at idle in every trace — consistent.
- **[FACT] The producer is `FUN_1804e4b6`** (device-object layer,
  0x1804xxxx), called each refresh from `FUN_181f4308`'s tail and from
  a dispatcher @ `0x181F015A`. It computes a per-mode base airflow by
  table interpolation (`FUN_1804f2cc` for mode 1, `FUN_1804f6cc` for
  mode 2), applies a cap, a minimum-airflow raise, and writes the
  result into CD88 via `FUN_1804fa1c`; a second half of `FUN_1804e4b6`
  then raises CD88 to a demand-scaled floor and clamps it to
  per-mode limit fields read from the field store.
- **[FACT] An alternate producer, `FUN_180511da`** (zoning
  distribution), replaces the direct computation when a configuration
  predicate (`FUN_1805185c`) holds; it writes CD88 by one of five
  zone-distribution strategies and finishes with
  `CD88 = min(CD88, *(float*)0xFFF80F9C)` via `FUN_180868d2`.
- **[FACT] `FUN_180c15d2` is NOT the CFM producer.** It is the demand
  interpolator: it produces the demand total CD8C (scale ≈ 12000 ×
  equipment factor — demand units, not CFM) and publishes the
  *segment index* of the demand through setter B (`FUN_181f782a`),
  which is one of the inputs of the CFM computation. `FUN_181f7050`
  (stage J's timing aggregator) plays no role in CFM.
- **[FACT] The dictionary's CFM properties are mirrors, not
  producers.** Every `*cfm*` property's provider is a sync/publish
  handler (§5). The computation lives entirely in the control layer
  (CD88); the dictionary layer only republishes store/RAM values.
- **[FACT] Provenance to the wire closes to the same boundary stage N
  established for the whole 0305 frame:** CD88 is produced in the
  decision block; the float→ushort packing into the furnace device
  object happens inside the runtime-bound engine layer (the bulk
  mirror `FUN_181f4e60` does **not** copy CD88 — verified by full
  pool census — so CD88 crosses via the engine's runtime-bound
  object bindings, statically invisible, exactly like the heat/cool
  stage bytes whose provenance stage N also traced only to the
  mirror/engine boundary).

---

## 1. The computation — `FUN_1804e4b6` end to end

Notation: `CDxx` = byte/float cell at `0xFFF8CDxx`; `CAxx`/`CBxx`/
`CCxx` likewise in the decision block. Mode byte **CD7D**
(`0xFFF8CD7D`): **1 = heat, 2 = cool, 3 = auto** — [inference, strong:
stage L §3.6 — the CD44 aggregator's per-zone error term is
`setpoint − temp` for CD7D==1 and `temp − setpoint` for CD7D==2;
FUN_180c62fc has a separate ==3 branch]. CD7D itself is ingested by
`FUN_181f4308` from byte 0 of the 11-byte device-mirror record at
`0xFFF82E0D` (copied to `0xFFF8C5A0`).

### 1.1 First half — per-mode base airflow → CD88

Gate: if `CA80 == 0 && CA94 == 0` (both accessor indices zero — no
capacity request) and no mode matches, `FUN_180511da()` is invoked as
a reset path and CD88 is left at its reset value (0).

**Mode 1 (heat), predicate `FUN_1805185c() == 0`:**

```
base = FUN_1804f2cc(...)                       // §2.1, double precision
base = min(base, FUN_18052354())               // cap: max of the two
                                               // FUN_180d2728 zone-distribution
                                               // channels (0) and (1)
if (CA94 != 0):
    base = max(base, resolve(FUN_1805002a()))  // minimum-airflow raise, §2.3
    // (class-0x4000 equipment with flag byte 0xFFF806A4 == 0 → base = 0.0)
FUN_1804fa1c(base)                             // CD88 = base + zone split, §2.4
```

If `FUN_1805185c() != 0` the zoning producer `FUN_180511da` runs
instead (§3). The predicate is
`CA94 == 0 && CA80 == 1 && (CBF4 & 0x20) && CC1C[1] == 0.0`
[FACT, decompiled + pool-resolved].

**Mode 2 (cool)** is identical in shape with `FUN_1804f6cc` (§2.2) as
the base computation.

After the mode path: if `FUN_1805185c() != 0` and `CD87 == 0 &&
CB55 == 0 && CB56 == 0`, CD88 is forced to **0.0** and the second
half is skipped (no demand anywhere → no airflow). [FACT]

### 1.2 Second half — demand floor + store clamps (runs when any of CD86/CD87/CB55/CB56 ≠ 0)

```
floor = FUN_1804fca0()                    // = max(C74F ? C750 : 300, 175)
                                          // C750 = configured ushort cell;
                                          // 300 and 175 are flash constants
                                          // @0x1830B10A / @0x1830B108
demandFloor = (ushort @0x1830B112) × CD8C / 12000.0
                                          // = 325 × CD8C / 12000.0  [FACT:
                                          // pool 0x1804E978 → 0x1830B112,
                                          // ushort there = 325; divisor
                                          // 0x463B8000 = 12000.0f]
if (C9F0 != 0) floor = max(floor, demandFloor)
if (CD88 < floor) CD88 = floor            // ratchet up only
    // (equipment class field (CC52 & 0x7C00) == 0x4000 and
    //  0xFFF806A4 == 0 and CD87 == 0 → CD88 = 0.0 instead)
// final clamp, per mode, limits read via getter-B FUN_1815927c,
// 2 bytes each; a limit of 0 means "unset" and is skipped:
if (CD7D == 1)  CD88 = clamp(CD88, store[197], store[199])   // floor, cap
if (CD7D == 2)  CD88 = clamp(CD88, store[4062], store[4064]) // floor, cap
```

[FACT throughout: decompile `decomp/decomp_1804e4b6.c` (stage N copy)
+ full capstone disassembly `out/dis_1804e4b6.txt` — the store reads
are literal `getter(199, buf, 2, 1)`, `getter(197, …)`,
`getter(4062, …)`, `getter(4064, …)` at 0x1804E7BA–0x1804E7F8, and
the clamp branches at 0x1804E806 (mode 1) / 0x1804E872 (mode 2).]

The store fields: stage-F descriptor schema has keys `0xC5` (197),
`0xC7` (199), `0xFDE` (4062), `0xFE0` (4064), all len 2, range
0–65535, **default 0** (default bytes at `0x182F6D1A` = `00 00`),
each ×3 (three store instances). The adjacent bool key `0xFDD`
(4061, range 0–1) is written by the ingestion dispatcher
`FUN_181f5d08` (`setter(0xFDD, buf, 1, 1)`), so fields 4061–4064 form
one runtime-written parameter group. [FACT] Their dictionary names
were **not** recovered (no binding-directory record covers these
offsets — verified by grep over stage D's `binding_directory.txt`);
functionally they are the per-mode minimum/maximum airflow limits
written at install/commissioning time. [inference]

### 1.3 What the numbers mean

- The **325** in the demand floor is one entry of a flash constants
  block at `0x1830B108`: ushorts **{175, 300, 200, 300, 350, 325,
  325, 325, 350, 350, 400}** — the CFM/ton parameter family (350 =
  nominal, 400 = +15 % comfort, 325 = −7 % efficiency — the G80CTL /
  Infinity trim values). Different functions hold fixed pointers to
  individual entries (census: each entry is referenced by 1–4 pool
  cells, all inside the 0x1804Exxx–0x18051xxx airflow cluster).
  `FUN_1804e4b6`'s floor uses entry 325; `FUN_1804fca0` uses 300
  (default) and 175 (absolute floor). [FACT values + users;
  the per-slot semantic beyond the traced ones is inference.]
- **CD8C's scale:** the demand tables CCC4/CCDC are built by
  `FUN_181f21d4` with a full scale of `R × 12000` (stage L:
  `R = field8 / 12.0`; class 0x8141/0x91C1:
  `CCDC[1] = R × 34.286 × (137 + 3.5·X)`, `X = clamp(*(float*)
  0xFFF820F8, 12, 61)` — note 34.286 ≈ 12000/350, so both forms are
  ≈ 12000 × size factor). CD8C therefore lives in demand units where
  full scale ≈ 12000 × R, and `325 × CD8C / 12000` converts demand
  fraction × R × 325 — i.e. a CFM/ton-scaled demand airflow used as a
  floor. [FACT formulas from stage L + this stage's pool work;
  the physical reading is inference.]

---

## 2. The mode base computations

Both functions interpolate **float tables in the decision block**
over a continuous *capacity index*. The two index inputs are the
accessor pair values:

- **Accessor A**: getter `FUN_181f77f4` → cell **CD94**; setter
  `FUN_181f77fc(v)` writes CD94 and CD90 and notifies
  `FUN_181f4d04(CD90, dict 0x3C12EC6C)`.
- **Accessor B**: getter `FUN_181f7822` → cell **CD98**; setter
  `FUN_181f782a(v)` notifies and writes CD98 and the shared
  dictionary cell **`0x3C12EC6C`**.
- `FUN_181f77ec()` returns **CD90**; `FUN_181f7816()` returns
  **`*0x3C12EC6C`** (the last value published through either setter).

[FACT: the four accessors are 8–36-byte functions, decompiled in
`decomp/decomp_181f77f4/fc/7822/782a/77ec/7816.c`, pools resolved.]

The values are set from: (a) `FUN_181f4308`'s head — bytes 1 and 5 of
the device-mirror record `0xFFF82E0D` (the same record whose byte 0
is CD7D); (b) `FUN_180c15d2` and its sub-evaluators — setter B is
called with the **segment index of the demand CD44** in the
CCC4/CCDC tables, setter A in its branches; (c) the glue cluster at
0x181F0xxx. So the index is the equipment's current capacity/stage
position as tracked by the control module. Segment endpoint bytes
**CA59/CA5A** (for the CC34-family tables), **CA75/CA76** (for the
CCC4/CCDC-family tables), **CA80 = (int)CD94**, **CA94 = (int)CD98**
are recomputed each refresh by `FUN_181f4308` / `FUN_180c15d2`.
[FACT]

The generic interpolation used everywhere below, for input `v` and
segment `[lo, hi]` (byte cells) over table `T`:
`T[lo] + (v − lo) × (T[hi] − T[lo]) / (hi − lo)`, applied only when
`lo < v < hi` and `lo != hi`; outside the segment, a direct lookup
fallback (`T[CA80]`, `T[CA94]`, or `T[X]`, X = byte `0xFFF806A4` —
a cached copy of dictionary field `0x3C0D8272`, refreshed at
`FUN_1804e4b6`'s head) or 0.0 is used. [FACT: read from the capstone
disassemblies `out/dis_1804f2cc.txt`, `out/dis_1804f6cc.txt`.]

### 2.1 Mode 1 (heat) — `FUN_1804f2cc` (returns double; result = part 1 + part 2)

- **Part 1** (gate: `CBF4 & 4`): input `v1 = CD90` (`FUN_181f77ec`),
  segment [CA5A, CA59]; table **CC1C** (`0xFFF8CC1C`) if `CD3F != 0`,
  else **CC04** (`0xFFF8CC04`). Fallback: `T[CA80]`.
- **Part 2** (gate: `CC52 & 0x20`): input `v2 = *0x3C12EC6C`
  (`FUN_181f7816`), segment [CA75, CA76]; table **CCAC**
  (`0xFFF8CCAC`) if `CD43 != 0`, else **CC94** (`0xFFF8CC94`).
  Fallbacks: `T[CA94]`, or `T[X]` / 0.0 for class field 0x4000.
- Equipment class field `(CC52 & 0x7C00) == 0x800` replaces the
  result with `FUN_181f5e9a(...)` (§4).

### 2.2 Mode 2 (cool) — `FUN_1804f6cc`

- **Main** (gate: `CC52 & 0x20` and `CA75 < v < CA76`,
  `v = *0x3C12EC6C`):
  - `CD43 != 0`: if `C74D == 1 && CB4D == 0` → `FUN_18051898()`
    (below); else interpolate over **CC7C** (`0xFFF8CC7C`).
  - `CD43 == 0`: interpolate over **CC64** (`0xFFF8CC64`) — input
    `v`, or input **X** (`0xFFF806A4`) for class field 0x4000
    (0.0 if X == 0).
- **Fallbacks** (input outside the segment): direct lookups
  `CC7C[X]` / `CC7C[CA94]` (CD43 != 0) or `CC64[X]` / `CC64[CA94]`
  (CD43 == 0); the `FUN_18051898` detour applies in the CD43 != 0
  branch as above.
- Class field 0x800 → `FUN_181f5e9a` override, as in mode 1.

**`FUN_18051898`** (the detour): if `(CC52 & 0xF) == 1` →
`FUN_18051cec(CD4A)`; else `f = *0x3C12EC6C − 1.0` (class field
0x4000: `f = (X − 1) / 4.0`), `f = max(f, 0.0)`, result =
`FUN_18051908(f, CD4A)` — the two-point interpolation getter of
stage E §7, whose table indices come from the class-dependent
translator `FUN_18050c26(1)/(2)` and whose constant getter
`FUN_18051cec` returns pointers to **375.0 / 400.0** for argument 5
(stage E). [FACT: decompiles `decomp_18051898/18051908/18051cec/
18050c26.c` + pools.] This is the path where the CFM/ton-scale
constants 375/400 enter the cool computation.

### 2.3 The minimum-airflow raise — `FUN_1805002a` + `FUN_18086898`

`FUN_1805002a` (mode-dispatched) uses the class-dependent index
translators `FUN_1804fe5c` (mode 1) / `FUN_1804fce2` (mode 2):
per equipment class they yield the stage byte `X`, `X << 2`, the
constant 1, or a pointer to a float constant (**0.85** at
`0x180501CC` for the 0x400-field branch); the non-0x4000 path calls
the translators with stages 1 and 2 and returns a pointer to the
**1.0** constant cell (`0x180501F0`). The cluster's pools also
reference the flash parameter entries **200** (`0x1830B10C`),
**350** (`0x1830B110`), **325** (`0x1830B114`, `0x1830B116`).
The selected value is applied in `FUN_1804e4b6` through
`FUN_18086898(value, base)`:

```
FUN_18086898(p1, p2):  limit = *(float*)0xFFF80F9C   // engine-side cell
    if (p2 <= limit) { flag 0xFFF80F88 = 0; return min(p1, limit) }
    else             { flag 0xFFF80F88 = 1; return p2 }
```
and the caller then takes `base = max(base, FUN_18086898(...))`.
[FACT: decompile `decomp_18086898.c`, pools resolved. The exact
variant-return ABI of `FUN_1805002a` — pointer-to-constant vs index —
is **not fully resolved**; see §7. Functionally it is a
class-dependent minimum-airflow selection from the flash parameter
family {200, 325, 350, 0.85, 1.0}, applied as a raise.]

### 2.4 The write — `FUN_1804fa1c(value)`

```
CD88 = value
for i in 0..7:
    if zone i inactive (FUN_181f035c(i) == 0): CD9C[i] = 0; CDBC[i] = 0
    else:
        CD9C[i] = CD88 × CD1C[i]        // per-zone share of commanded CFM
        CDBC[i] = CD8C × CD1C[i]        // per-zone share of demand total
        // zones with CBA9[i] == 4 accumulate into CDDC[i] instead,
        // latched by bytes at 0xFFF8069C+i
```
[FACT: decompile (stage N copy) + pools: CD9C = `0xFFF8CD9C`,
CDBC = `0xFFF8CDBC`, weights CD1C = `0xFFF8CD1C`, CDDC =
`0xFFF8CDDC`.] CD1C is the per-zone weight array (also an input of
the CD44 aggregator, stage L).

---

## 3. Alternate producer — `FUN_180511da` (zoning distribution)

Dispatched on bytes CD87 / CB55 / CB56 / CBDC to five strategies,
all writing CD88 and the per-zone array CD9C, followed by
`CD88 = FUN_180868d2(CD88) = min(CD88, *(float*)0xFFF80F9C)`:
[FACT: decompiles `decomp_180511da/180512ac/180514f0/18051638/
1805173a/180517a2/180868d2.c` + pools.]

- `FUN_180512ac`: CD88 = 0, CD9C[i] = 0 (no airflow).
- `FUN_180514f0`: single-source passthrough — source selected by
  byte CB3E from engine cells `0xFFF8066C / 0xFFF80698 / 0xFFF80694`
  (or 0); zone 0 (if active) receives it in CD9C[0]; CD88 = sum.
- `FUN_1805173a`: like above with source `0xFFF80694` fixed.
- `FUN_180517a2`: per-zone distribution
  `CD9C[i] = S × (CBBC[i] + CBB8 / nActive)`, CD88 = Σ, with
  `S = *0xFFF80694`, nActive from `FUN_18052314`.
- `FUN_18051638`: same with `S = *0xFFF80690` and per-zone caps
  `CD9C[i] = min(CD9C[i], *(ushort*)(CAFE + 2i))`.

Whether our single-zone install ever takes this path depends on the
runtime predicate values (CA80/CA94/CBF4/CC1C[1]) — not recorded in
the traces; see §7.

---

## 4. The class-0x800 override — `FUN_181f5e9a`

A 2522-byte equipment-family evaluator (branches on class words
0x89A2/0x8AA2 and 0x8DA2/0x8EA2) that reads min/max ushorts from
device mirrors under lock, interpolates over the same CC64/CC94/
CC7C tables, and applies a float multiplier. It is invoked from
`FUN_1804f2cc` / `FUN_1804f6cc` / `FUN_18051908` only when the
equipment class field `(CC52 & 0x7C00) == 0x800`. The G80CTL class
words seen in stage L (0x8241/0x92C1 → field 0x0000/0x1000;
0x8141/0x91C1 → 0x0000/0x1000) never take this branch. [FACT:
decompile `decomp_181f5e9a.c`; class fields computed from stage L's
class words.] For the target system it is **not on the CFM path**.

---

## 5. Dictionary CFM properties — producers are sync/publish handlers

Registration records (stage K layout @ `0x181C511C–0x181CC26C`,
parsed in `out/name_id_map.txt`) and the provider table @
`0x1830xxxx` (parsed in `out/descriptor_table.txt`). Every CFM
property ID occurs **exactly once** in the image — in its own
registration record (`out/id_occurrences.txt`); no code addresses
properties by ID. Providers (all decompiled, `decomp/fx_*.c`):

| property | ID | provider | behaviour |
|---|---|---|---|
| mincfm | — (store-backed) | `FUN_181c582a` | sync: store → RAM cell, republish on change |
| maxcfm | — | `FUN_181c582a` | same handler |
| calcMinCFM | 0x3C126D54 | `FUN_181c582a` | same handler |
| blowerSpeed | 0x3C126D56 | `FUN_181c582a` | same handler |
| absmincfm | 0x3C126E60 | `FUN_181c5fde` | same sync pattern |
| absmaxcfm | 0x3C126E62 | `FUN_181c5fde` | same |
| mincfmenable | 0x3C126D1B | (sync family) | — |
| maxcfmenable | 0x3C126D1C | `FUN_181c4dea` | — |
| pwmblower | 0x3C126D28 | `FUN_181c51f2` | — |
| cfmlimitsvalid | 0x3C126E6B | `FUN_181c60a6` | computed: `(value != 0) && (paired cell != 0)` |
| iducfm | — | `FUN_181cec2a` | sync |
| cfmlimit | — | `FUN_181dd022` | indexed-array handler |
| systemCFM | 0x3C12CD6-slot | `FUN_181ddc94` | sync (store → object, with a 0x1B-byte record copy under lock) |
| blowerActualCFM | 0x3C129FC6 | `FUN_181ddafe` | sync |
| blowerCoolingCFM | 0x3C129FC8 | `FUN_181ddafe` | sync |
| blowerHeatingCFM | 0x3C129FCA | `FUN_181ddafe` | sync |
| blowerPower | 0x3C129FCC | `FUN_181ddafe` | sync |
| vcapfloorcfm | 0x3C129494 | `FUN_181d1120` | sync from store |
| vcapceilingcfm | 0x3C129496 | `FUN_181d1120` | sync from store |
| vcapcfmfloor | 0x3C12A070 | `FUN_181d11cc` | **publish from RAM mirror** `*(short*)0xFFF82F00` if `0xFFF8C030 & 0x20`, else 0 |
| vcapcfmceiling | 0x3C12A072 | `FUN_181d12fe` | publish from `*(short*)0xFFF82F0A`, same gate |
| vcapcfmuplimit | 0x3C12A074 | `FUN_181d13d0` | publish from `*(short*)0xFFF82F0C`, same gate |

No registration record exists for `systemCFM`, `cfmlimit`, `iducfm`,
`mincfm`, `maxcfm` in the 0x3C12 ID space — they are bound through
the descriptor/provider table only. [FACT]

**Consequence for the task's item (1):** there are no "setter calls
with those property IDs" to find — the CING engine reaches properties
through provider functions and binding records, never by ID. The
producers of the *values* are the control-layer computations of
§1–§3 (for the blower/system CFM family) and the device-mirror
ingestion (for the vcap family: mirror record at `0xFFF82F00`,
written by the engine from the variable-capacity device object;
its writers are runtime-bound — the cell occurs in code only in
the publisher functions and in binding-record tables at
0x18110ED8/0x18113C58/0x18116464/0x18117BD8 and a device-layer
function at 0x1806E4FC).

---

## 6. The v4.79 change — "Removed compressor demand response from CFM calculation"

Stage VERSIONS established the data-model side: the
`system/utilityEvent/demand*` group (`demandClAbs`, `demandHtAbs`,
`demandOffset`, `demandResp`, …) present in ≤ 4.74 is **entirely
absent from 4.79** (strings gone, "Demand Response Settings" UI
gone), replaced by a lone `totalDemandReductionPercent`.

In the 4.79 CFM computation recovered here, the input set is closed
(§1–§3: mode, capacity indices, equipment tables, class word, X
byte, flag bytes, store limits, CD8C) — **no demand-response input
exists anywhere in the airflow cluster**, and no consumer of
`totalDemandReductionPercent` appears in it. [FACT: full decompile
coverage of the cluster + cell censuses.] So in 4.79 the formula is
exactly §1 — driven by *load* demand (CD44/CD8C) only. The ≤4.74
formula presumably carried an additional DR offset/reduction term
fed by the `utilityEvent/demand*` properties; that term's exact
shape is **not recoverable from the 4.79 image** (the code is gone,
not vestigial — no dead DR branch was found in `FUN_1804e4b6`,
`FUN_1804f2cc`, or `FUN_1804f6cc`).

---

## 7. Provenance chain to 0305 [4..5]

```
zone temps/setpoints ──► CD44 (FUN_180c62fc, demand float)
                              │ interpolation over CCC4/CCDC/CC34
                              ▼
                     CD8C (demand total, FUN_180c15d2 / FUN_181f4308)
                              │ segment index published via setter B
device record 0xFFF82E0D ──► CD7D (mode), CD94/CD98 (capacity indices)
                              │
                              ▼
   FUN_1804e4b6 ──► per-mode interpolation (CC04/CC1C/CC7C/CC64/CC94/CCAC)
                 ──► cap FUN_18052354, min-raise FUN_1805002a/FUN_18086898
                 ──► FUN_1804fa1c writes CD88  (or FUN_180511da, §3)
                 ──► floor max(FUN_1804fca0(), 325·CD8C/12000)
                 ──► clamp to store[197/199] (heat) / store[4062/4064] (cool)
                              │
                              ▼
              CD88 = commanded CFM (float, decision block)
                              │
              engine object layer (runtime-bound bindings;
              FUN_181f4e60 mirror does NOT carry CD88 — §0)
                              │
                              ▼
              furnace device object ──► serializer ──► 0305 [4..5] (ushort BE)
```

Evaluation order per refresh [FACT]: `FUN_181efdfc` (refresh) →
… → `FUN_181f4308` (ingest + CD8C + mirror `FUN_181f4e60`) →
`FUN_1804e4b6` (called at `FUN_181f4308`'s tail via pool
`0x181F4A98`, and from the dispatcher @ `0x181F015A` together with
`FUN_180c08ec` / `FUN_181f04ec`). The glue cluster at 0x181F0xxx
also holds the idle reset (@ `0x181F026E`: CD88 = CD8C = 0, segment
bytes cleared, CD7E[i] = 0x0F) and the per-zone split @ `0x181F017E`
(mode-selected total from CA00 (mode 1) / C9FC (mode 2)).

The last hop (CD88 float → ushort in the serialized object) is
inside the engine's runtime-registered serializer — the same wall
stage N proved for the frame's other fields (no statically
reachable code reads the mirrored objects back toward a UART).
What is proven: CD88 is the only CFM-scale, CFM-clamped,
idle-zeroed float in the decision block, and every other 0305
field's provenance ends at this same boundary.

---

## 8. Capture verification

Method: census of all 0305 payloads per trace
(`scripts/captures0305.py`) + ordered change timeline for coldstart
(`scripts/timeline.py`). The traces record only wire values — the
demand index trajectory and the runtime table contents are not on
the wire, so exact numeric reproduction of the formula is
impossible from captures alone; what can be tested is the
formula's *behavioural signature*. Results:

| # | Prediction from §1–§3 | Capture evidence | Verdict |
|---|---|---|---|
| 1 | No call, fan auto → CFM = 0 | Dominant payload in every trace is `…0000…` CFM=0 (e.g. 136/149 frames in phase3-validation2) | ✓ |
| 2 | CFM is *modulated* by a continuous demand index within one stage (interpolation), not a fixed per-stage tap | Coldstart cool stage 2, single call: CFM 0 → **1232** (17:09:27Z) → **1760** (17:10:57) → **1710** → **1660** as load falls; call ends, CFM holds 1660 through the off-delay, then 0 | ✓ — a fixed-tap model predicts ≤1 value per stage |
| 3 | Heat airflow also demand-shaped, with a staging lag | Coldstart heat: stage 1 CFM **1368**; stage 2 starts at 1368, steps to **1617** after ~20 s; 1617 repeats exactly in phase3-validation3 (heat 2) — a stable table-derived value | ✓ |
| 4 | Fan-only airflow from the same computation (fan index), with a start/settle profile | Two fan-only episodes in coldstart: **1166** for ~70 s → **379/384** → 0; 1166 identical in all 5 appearances across traces (a table value); the low value wobbles 378–384 across traces (computed, not a constant) | ✓ |
| 5 | Cooling max ≈ capacity × CFM/ton within the trim envelope | Max observed CFM = **1760**; 5-ton unit → 352 CFM/ton, inside the {325, 350, 400} trim family and +0.6 % over nominal 5 × 350 = 1750 (interpolation/rounding; exact equality not claimed). The install traces show exactly **1750** with no call (commissioning blower run) | ✓ consistent |
| 6 | CFM not slaved to ODU 0608 requested CFM | Stage J: no consumer of the 0608 slot exists; §1's input set contains no 0608 term | ✓ (by stage J + §1) |

**Precise mismatch statement:** none of the captured values
contradicts the formula; equally, the captures cannot *prove* the
interior table values, because the runtime contents of
CC04/CC1C/CC7C/CC64/CC94/CCAC and the demand-index trajectory are
not observable on the wire. The stable repeats (1166, 1368, 1617)
are consistent with table entries at integer indices; the smooth
ramps (1232→1760→1660) are consistent with fractional-index
interpolation between them.

---

## 9. For the emulator (what to implement)

1. Keep a **capacity/demand index** per mode (the thermostat's load
   computation), map it through a per-equipment **airflow table**
   (index → CFM) with linear interpolation between integer steps
   and direct lookup outside the segment — tables are equipment
   data, not constants: for this G80CTL + 5-ton HVA9 the observed
   anchor points are heat ≈ {1368, 1617}, cool max ≈ 1750–1760,
   fan ≈ {~380 low, 1166 high}.
2. Apply, in order: cap by the zone-distribution maximum; minimum-
   airflow raise (equipment parameter); demand floor
   `max(300-ish configured minimum, 325 × demandFraction × R)`
   — for a fixed-speed emulator approximation the floor term is
   `325 × CD8C/12000` with CD8C on the 12000×R demand scale;
   final clamp to per-mode [min, max] CFM limits (0 = unset).
3. At idle (no call, no fan) command 0; on call end, hold the last
   CFM through the blower off-delay (captured: 1660 held ~60 s
   after the cool byte cleared).
4. No demand-response term (4.79 behaviour).

---

## 10. Explicit unknowns

1. **Runtime contents of the CFM tables** CC04/CC1C/CC7C/CC64/
   CC94/CCAC. Their builders are in the 0x181F0xxx and 0x181F3xxx
   clusters (cell census: CC04/CC1C referenced at
   0x181F0AC8–0x181F1678; CC7C/CC64/CC94/CCAC at
   0x181F3A70–0x181F3BEC) and were not fully decompiled in this
   stage; the pattern is the same as `FUN_181f21d4` (per equipment
   class, from capacity inputs). The interpolation mechanics,
   indexing, and consumers are fully proven; the per-entry
   formulas are not.
2. **Dictionary names of store fields 197/199/4062/4064** — no
   binding record covers them; functionally the per-mode CFM
   clamp pair (§1.2). Their runtime writers (install/commissioning
   path) were not traced.
3. **`FUN_1805002a`'s variant-return ABI** (pointer-to-float vs
   index) — the minimum-airflow selection is functionally
   identified (§2.3) but the exact dereference step is unresolved
   in the mangled decompile; the disassembly shows the result is
   consumed as a float through `FUN_18086898`.
4. **Which producer ran during the captures** — direct
   (`FUN_1804e4b6` mode path) vs zoning (`FUN_180511da`): decided
   by the `FUN_1805185c` predicate's runtime values, not on the
   wire. For a single-zone install both converge to "one zone gets
   the total".
5. **The final float→ushort packing** of CD88 into the furnace
   object (runtime-bound engine serializer; §7) — including any
   rounding (observed values are integers; CD88 is float).
6. **Byte `0xFFF806A4`** (cached dict field `0x3C0D8272`): used as
   boolean, table index, and `(X−1)/4.0` operand in class-0x4000
   branches — an equipment variant/stage index; exact identity
   not recovered. Not on this unit's path (our class fields are
   0x0000/0x1000).
7. **Mirror record `0xFFF82E0D`'s owning device**: bytes 0/1/5
   feed CD7D/CD94/CD98; the record is engine-maintained
   (occurrences: `FUN_181f4308`'s copy, `FUN_181f5d08`'s cluster,
   a device-layer function at 0x1806E4FC). Which device object it
   mirrors was not determined.

---

## 11. Evidence index (all under `firmware-re/stageR/`)

- `decomp/fx_*.c` — the 13 CFM dictionary providers (§5).
- `decomp/decomp_1804f2cc.c`, `decomp_1804f6cc.c` + `out/dis_1804f2cc.txt`,
  `out/dis_1804f6cc.txt` — mode base computations (decompile +
  disassembly dual verification).
- `out/dis_1804e4b6.txt` — master function disassembly (stage N
  decompile copy used as the second source).
- `decomp/decomp_181f4308.c`, `decomp_181f5d08.c`,
  `decomp_181f21d4.c`, `decomp_181f07ec.c`, `decomp_180c62fc.c` —
  refresh-side producers.
- `decomp/decomp_180511da/180512ac/180514f0/18051638/1805173a/
  180517a2/1805185c/18051898/18051908/18051cec/18051e4e/18052354/
  1805002a/1804fe5c/1804fce2/18050c26/1804fca0/18086898/180868d2/
  181f77f4/181f77fc/181f7822/181f782a/181f77ec/181f7816/181f035c/
  181f5e9a/181f4d04/181f5cec/18052314.c` — the cluster.
- `out/dis_181f0000.txt`, `out/dis_wrapper.txt` — glue cluster
  (dispatcher @0x181F015A, split @0x181F017E, reset @0x181F026E).
- `out/name_id_map.txt`, `out/descriptor_table.txt`,
  `out/id_occurrences.txt` — dictionary registration/provider
  parses; `scripts/cell_scan.py` censuses (CD88/CD8C/CD90/CD94/
  CD98/store-table entry users) in the session log.
- `out/pool_181f21d4.txt` — FUN_181f21d4 pool (CCC4/CCDC/CD04 only).
- `scripts/captures0305.py`, `scripts/timeline.py` — capture
  verification (§8).
