# FIRMWARE AUDIT — cross-verification of the Ion RE corpus

**Date:** 2026-11-26. **Scope:** every report in this directory through
stage N + VERSIONS + all of `external-research/` + the thermostat
algorithms research (`~/workspace/research_notes/thermostat-algorithms-research-20261126-0748/`).
Stages O, P, Q, R, S, T, U, V, W, X, Y are **in flight in parallel**;
their topics are marked `PENDING-O..Y` wherever they would otherwise
appear as gaps, and are not audited here.

**Method.** (1) Full-corpus claim extraction. (2) Every known
inter-report contradiction re-checked from primary material by the
auditor, in `firmware-re/audit/` (`recheck_image.py`,
`recheck_image2.py`, `recheck_captures.py` — independent
re-implementations, no stage script reused): raw image scans over
`firmware-re/stageB/flat.bin` (base 0x18040000, MD5-verified copy of
the analysed image), and a full recount of all 83,752 frames in
`traces/*.jsonl`. (3) Rulings below cite the decisive evidence for
each side.

**Evidence classes used in the ledger:** `CAP` capture-proven ·
`DUAL` dual-verified static (two independent methods/stages) ·
`STATIC` single-method static · `EXT` external document ·
`INF` inference.

---

## 1. Rulings on the known contradiction seeds

### 1.1 Stage D's "90 zlib streams" — REFUTED as stated; H/K upheld

- D §3.1: "all 90 zlib streams in the resources filesystem region
  (0x18810100–0x18D40577) were decompressed and searched: 0 hits."
- H (clarinox-image.md §286) and K §5: the streams do not reproduce;
  the region holds 90 zlib-*header-shaped* offsets and **zero**
  streams that decompress.
- **Audit re-check:** whole-image scan finds 9,406 FCHECK-valid
  header candidates under a loose filter (K counted 811 under a
  stricter one; the candidate count is filter-dependent and not
  load-bearing). Decompression attempted at every candidate, zlib
  wrapper and raw deflate: **0 successful decompressions**.
- **Ruling:** H/K are right. There are no zlib streams in the image;
  D's sentence is false as written (most plausibly D counted
  header-shaped candidates as "streams"). D's substantive negative —
  no furnace/ODU model strings anywhere, including the resources
  region — is **unaffected**: the region is uncompressed BE16
  graphics/fonts and is covered byte-for-byte by the whole-image
  string scans (D §3.1 itself, K §4).

### 1.2 Binding directory: D's parse superseded by F — and the count is 386, tables 98

- D §2: directory @ `0x182B5E40–0x182B6A48`, 385 records of
  `[len][00][table BE16][field][flags][store_offset BE16]`.
- F §4.2: code reads the structure from base **`0x182B5E3A`** as
  8-byte group records
  `[tableHi][tableLo][sub/class][flags][member_start BE16][member_count][pad]`
  over a member registry @ `0x182B6AC8`; D's "store offset" is a
  **member index**. Decisive test (F §4.3): group (0x030D, sub 0x42)
  → member_start 324, and member[324].buf = `0x3C0D41D0` — exactly
  the buffer stage C recorded independently for that call.
- **Audit re-check:** parsed the structure from 0x182B5E3A in F's
  format. Group (030D, 0x42) → member_start **324**, count 1 ✓;
  member[324] = `{0x3C0D41D0, 0x3C0D41D8, 0x03070002, 0x01000000}` ✓
  verbatim. **386** non-terminator records (indices 0–385), then a
  zero-table terminator at index 386 (@0x182B6A4A). F's own dump
  (`stageF/out/group_table.txt`) contains **385** records — it stops
  one record early, omitting the final group (0x3E0E, sub 0x50,
  members [1316,1321)). VERSIONS §4 independently walks **386**.
  Distinct tables: **98** by audit parse and by F's own dump.
- **Rulings:**
  - F's reparse (base, format, member-index semantics) is **correct**
    — independently reproduced from raw bytes, decisive test passes.
  - Record count: **386** groups. D's 385 and F's 385 are the same
    off-by-one at the tail (both walks stop before the last group);
    VERSIONS' 386 is right.
  - F §4.1/§4.2 prose "**106 distinct tables**" is **wrong against
    F's own data file** (98) and against the audit parse (98).
    VERSIONS' "99 tables" for 4.79 is unexplained (+1 vs both
    parses) — a counting-method artefact, unresolved and immaterial.
  - The **set of tables is identical** under D-phase and F-phase
    parses (audit-verified: both give the same 98-table set) — so
    every *absence* conclusion drawn from the directory (no group for
    0305/060D; 0605 groups only for classes 0x56/0x57/0x5B) survives
    the reparse unchanged.
  - **Contamination check:** I §2 and J §1 built their store-span
    tables on D's parse ("store offsets"). Under F's reparse those
    columns are member indices into a RAM registry, **not** offsets
    in the flat field store @0x3C0E4A20 — and whether the two stores
    are one space is explicitly unproven (J §9). I/J's *accessor
    census* negatives (which constant offsets code actually passes
    to the getter/setter) are parse-independent and stand; their
    *directory→store-offset mapping* does not. The protocol map and
    PHASE5/PHASE6 docs never cite the directory — no contamination
    there.

### 1.3 Stage E mislabels, corrected by L — corrections hold; no downstream reuse

L §6 corrects E on five points: (1) `FUN_181f21d4` is the **producer**
of the threshold tables CCC4/CCDC/CD04, not a consumer; (2) CC52 is a
16-bit **equipment class word**, not a "mode nibble"; (3)
`FUN_1816deec` writes **C9CC** (not CABC), `FUN_1816e2dc` writes
**C9AC** (not CB60) — E's attributions were window-tracking
artefacts; (4) demand float CD44 has a **second writer**
(`FUN_180c4322`, dispatcher case 2); (5) accumulator C90C has two
writers whose execution order is statically unsettled.
**Audit check:** no post-L document reuses the superseded forms —
N cites CD49/CD4A provenance "(Stage L)", VERSIONS and PHASE6.md do
not cite E's zone labels at all (grep: C9CC/C9AC occur only in L).
F and G predate L and must be read subject to L §6. **Ruling:** the
corrections are consistently reflected; E remains authoritative for
the leaf functions (quantizer, staging machine, trim, averager,
arbitrator) that L did not touch.

### 1.4 J's 0605 off-by-one against the protocol map — J upheld, with one refinement

- Map line 366: cool payload `40A00000010001`, "byte [5] also 00→01".
- J §6: the changing byte is **[4]**; [5] never changes; [6] = 0x01.
- **Audit recount** (all 676 0605 frames in the archive): [4] = 0 in
  596, 1 in 80 — and in the coldstart cool-call window [4]=1 in
  33/36 frames vs 0/23 at idle: **[4] is the call-state byte**. [5] =
  0 in **676/676**. [6] = 1 in exactly the 651 directed 0x20→0x53
  frames, 0 in the 25 broadcast frames (0x1F→F1 ×3, 0x20→F1 ×22).
- **Ruling:** J is right; the map's "[5]" is an off-by-one (errata
  E-1). One refinement to J: "[6] always 0x01" holds only for
  directed frames; broadcast 0605 frames carry [6]=0.

### 1.5 The retracted climate-card era claims — retraction verified, map is clean of them

PHASE5.md §1 retracted the phase-3-era readings of the HA climate
card (the card never showed live data: "70 °F" was a boot seed,
"Per Schedule" a fallback artefact; the stock component had 6+
live write paths into the dead SAM mirror). **Audit check:** the
protocol map contains no claim sourced from the climate card — its
setpoint/temperature statements are capture- and screen-sourced
(grep: no "Per Schedule" claim stands in the map; the map's own
§-statements about 3B02/3B03 zeros are capture-proven, §2.2 below).
**Ruling:** the retraction is complete and does not propagate into
the map. Any pre-PHASE5 chat-era statement about card behaviour is
superseded by PHASE5.md §1.

---

## 2. Rulings on NEW contradictions found by this audit

### 2.1 N §8 on 0303 — REFUTED in its second clause

- N §8: "[FACT] `0303`: absent from the unified catalog (stage K
  census) **and has no binding group (stage F group table, 385
  records, complete)**. Like 0305, it exists only as wire traffic."
- **Audit re-check:** F's own `group_table.txt` (records 39–43) and
  the audit's raw parse both show **five binding groups for 0303** —
  device classes 0x51, 0x52, 0x56, 0x57, 0x5B, member buffers at
  0x3C0D4018…. K §3.3 itself calls 0303 "**bound**-yet-uncatalogued",
  and J §1 lists five 0303 binding records under D's parse. N
  conflated catalog absence with group absence.
- **Ruling:** N §8's 0303 sentence is wrong. Correct statement: 0303
  is absent from the unified catalog (K, audit-verified §2.4) but
  **has** binding groups, including one for the ODU device class
  0x52 — the class our thermostat actually sends 0303 to. Whether
  the binding layer participates in constructing 0303's wire frames
  is the same open serializer question as for 0307 (F §4.4: the
  binding op is membership bookkeeping and never serializes). N's
  bottom-line inference (all three tables share the engine
  serializer) is unaffected, but its stated evidence for 0303 is.

### 2.2 I vs L on `FUN_181f21d4` — L supersedes I

- I §4: the control lineage "never calls the field-store accessor";
  `FUN_181f21d4` is "the single exception", and its reads of fields
  1, 8, 0x2F, 0x31 are "**housekeeping, not furnace data, not
  control**" (assembling a dictionary record). I §4.1 casts the RAM
  threshold tables as runtime-filled properties with "no identifiable
  'load furnace config' function".
- L §3.2/§4: the **same function, same fields** (field 1 → CC52
  class word; field 8 → R = byte/12.0; fields 0x2F/0x31 → CC56/CC58)
  is the **sole writer of the threshold tables CCC4/CCDC/CD04**,
  computing them by per-class formulas — i.e. the ingestion half of
  the control lineage proper, listing-verified from the function
  head.
- **Ruling:** L is right and supersedes I on the function's role.
  I's narrower, load-bearing negative survives intact: **no code
  consumes the furnace-reported spans** (0316, 0306/0307, table-04)
  — L does not touch it, and the fields `FUN_181f21d4` reads are the
  thermostat's own identity/config fields, not furnace data. But
  I §1's headline phrasing ("control never calls the accessor") is
  false as stated and must not be quoted without L's correction.

### 2.3 VERSIONS' constant-count claims — method-dependent, literally false as stated

- VERSIONS §0.3/§4: the {375.0, 400.0} pair occurs "**exactly
  once** in every version 2.40→4.79"; "0.01 literal count = **5**
  in every version"; 0.63 = 3 everywhere.
- **Audit recount** (whole-image BE f32 census): 4.79 — 375.0 ×1,
  **400.0 ×4** (three literal-pool copies at 0x1804B798, 0x1804BA70,
  0x182292D8 + the getter's constant array at 0x18051FF8, which
  holds {375.0, 325.0, 400.0, 351.0}); 2.40 — 400.0 ×3, **0.01 ×4**
  (not 5); 4.74 — 400.0 ×3, 0.01 ×5; 0.63 ×3 in all three.
- **Ruling:** the counts as printed are not reproducible by a
  whole-image census; VERSIONS evidently counted a restricted
  population (code-referenced literals in the decision module's
  neighbourhood) without saying so. The **substantive** claim —
  the decision core's constants are present and unchanged across
  all 16 versions — is supported: the getter's array {375, 325,
  400, 351} exists at the analogous address in 2.40 (0x18051888)
  and 4.79 (0x18051FF8), 375.0 is unique in every version checked,
  0.63 = 3 everywhere. Treat VERSIONS §4's exact counts as
  indicative, not as census data.

### 2.4 Minor numeric defects (recorded, immaterial)

- **VERSIONS §0.1** headline "8 referenced versions are not
  downloadable" — its own lists (§0.1 parenthetical, §11) enumerate
  **9** (1.30, 1.31, 1.32, Series B 2.00, 4.22, 4.38, 4.62, 4.64,
  4.72), and 16 obtained + 9 = 25 referenced. The headline number
  is wrong; 9 is correct.
- **K §1.1 vs audit on 96000:** K claims zero hits for 96000 in
  evidence-grade encodings; the audit finds 2 raw unaligned i32-BE
  byte-pattern hits (@0x1841E029 inside resource data, @0x18862051
  in ROM-FS graphics). Neither is an aligned field. K's claim
  survives in substance ("no evidence-grade occurrence") but its
  wording should be read with K's own alignment/context method.
  Same pattern for 1760.0: I §6 "stored float in resources" vs
  K §1.4 "cross-boundary artifact inside pointer records" — K's
  context dump is the better evidence; there is no stored 1760.0.
- **I §6 on 60000.0** ("0 pointer-cell references… unlinked") is
  superseded by J §6: the sole consumer is `FUN_181f7050`, which
  uses it as an ms→minutes divisor in a timing-statistics
  aggregator. All stages agree it is not a capacity value.
- **Getter caller count:** I's 899 vs J's 903 — reconciled by J §2
  (899 decompiled accessor users ⊂ 903 distinct callers; the delta
  is 2 store-internal wrappers + 2 typed getters). Not a
  contradiction; cite J's figures.
- **Boot timing figures** (map vs gofinity-bootup.md vs audit):
  reconciled. Audit measurement on coldstart: power→first 0x1F
  frame ≈ 6.0 s; 0x1F phase 10.7 s; first 0x20 frame at **+16.7 s
  from power** (the gofinity report's "handoff ~16.7 s" — same
  milestone, origin = power-up); first 0x20 0305 at +65.6 s from
  0x1F start. The map's "steady ≈62 s" is the same neighbourhood
  under a different origin/definition. No factual conflict; origins
  must be stated when quoting.
- **Address 0x0E (gofinity):** the gofinity thermostat probes a
  device at 0x0E persistently. **Audit check: zero frames involving
  0x0E exist in any of our 12 captures**, including the full
  coldstart sweep. Ruling: 0x0E is an artefact of that older
  Bryant system's configuration, not a missing piece of ours; our
  emulator does not need to probe it. (The sweep address set is
  configuration-dependent — see gap B-6.)

### 2.5 Audit-verified confirmations (load-bearing, re-checked from primary material)

- **Coil commit:** record @0x182C4D60 = {ptr 0x182C59A8 →
  "EN(A,D)4X61", f32 **1.69**}; the 0x3FD851EC word occurs exactly
  twice in the image (our coil + CNPV*61 @0x182C4B24) — D §3/K §2
  upheld.
- **061E on the wire:** one distinct payload in the entire archive,
  `0F 3FD851EC 06 00000000`, 0x20→0x53 ×651 — the committed coil
  parameter is exactly what the thermostat sends. D §3 upheld CAP.
- **0305 census:** 677 frames total (0x20: 652 with [11]=0x78 + 22
  all-zero; 0x1F: 3 all-zero) — N's recount reproduced exactly;
  F's 1,811-write corpus is a superset from a different counting
  base (writes incl. other captures), no conflict. CFM values
  observed: {0, 378, 379, 382, 384, 1166, 1232, 1368, 1617, 1660,
  1710, 1750, 1760} — J §1.4's list was a subset, not wrong.
  Cool-stage byte [2] only ever takes {0, 2} in the archive.
- **SAM zeros:** 865 replies of 3B02 (29 B) and 868 of 3B03
  (150 B) to the SAM, **all zero bytes, 100%** — C's claim and the
  infinitive body lengths (29/150) are capture-proven at scale.
- **Unified catalog:** 5,417 records @0x18404928–0x18409DCC, ids
  strictly ascending 0x0002–0x2222, class histogram matches K
  (1:4271, 2:690, 3:132, 4:114…); 0303/0305/0307 absent, neighbours
  present; the anomalous record @0x18406D64 (class 0xD2, id 0x101B)
  confirmed byte-for-byte. K §3 upheld.
- **CRC tables:** the reflected-0xA001 table @0x182C4164 matches the
  generated table 256/256 (stored BE); it is the **only** full
  A001 table in the image (two further 16-byte signature matches
  do not extend to full tables). The BUYPASS table @0x182AD53C
  matches its generated table 256/256, and the audit's independent
  vector test diverges from the wire CRC on **200/200** vectors —
  D/F/N on CRCs upheld.
- **Burst structure:** coldstart steady state confirms N §9's
  furnace-burst order 0305 → 0403 → 0409 → 0307, 0305 period median
  **10.00 s** (n=153, 9.01–11.20), preceded each tick by the ODU
  block (0610, 0612, 0605, 061A, 060D, 061E; 060B/0414 every other
  tick); 0202/0203 broadcast interval median **60.3 s** (map/INDEX
  "~60 s" upheld).
- **Boot handoff:** coldstart frames 0–121 are 0x1F, frame 122 is
  the first 0x20 frame — a clean, frame-adjacent persona handoff,
  consistent with the gofinity capture's stronger version of the
  same fact.
- **400A:** SAM writes are 35-byte rows, func 0x0C, ×36 in the
  archive; thermostat reads ×22 — the phase-3 row geometry is
  capture-consistent.
- **Official 4.79 = our image:** the local file's MD5/SHA-256
  (e3190322…, 2d1a9ea3…c90c04) match VERSIONS §0.2 exactly.

---

---

## 4. Master gap list for the autonomous thermostat

Ranked by what it blocks. `PENDING-x` = a stage O–Y agent is on it
right now; do not re-open until that stage reports. Map gap numbers
(G1–G11) refer to THERMOSTAT-PROTOCOL-MAP.md's own list.

### 4.1 Blocks coding the emulator

| # | Gap | State / cheapest closing route |
|---|---|---|
| B-1 | **Exact demand formula** — the helpers' arithmetic between zone error and CD44 (weights, clamps, gating), incl. the role of the second writer `FUN_180c4322` | PENDING-O (firmware statics + stage M harness vectors) |
| B-2 | **Threshold tables for OUR installation** — per-class formulas are known (L §4) but our equipment class word CC52 is a runtime value, statically indeterminable (L §3.4) | PENDING-P. Fallback if P cannot derive it from field-1 provenance: identify our table behaviourally from captured staging transitions, or accept the formula family and calibrate on the shadow emulator (todo step 6) |
| B-3 | **CFM computation** — no report isolates where 0305 [4..5] is computed; J's "computed on the IDU side of the model" is an inference from vocabulary + negatives (§2, ledger) | PENDING-R (with Q). Fallback: fit the function from captures (CFM vs stage/OAT/demand across 83k frames) + furnace Table 4 envelope (EXT) |
| B-4 | **Interpolation engine + 8-channel evaluator semantics** — `FUN_180c15d2`'s outputs and `FUN_181f7050`'s channels are unnamed; one of them may be the CFM/capacity path | PENDING-Q (property-ID → dictionary-name resolution) |
| B-5 | **Cooling-path behaviour at part load** — archive shows 0605 float only at 0.0 and 5.0, 0305 cool stage only {0,2}; partial-capacity commands (0605 ∈ 1.0–4.0) never observed (map G8) | PENDING-T for the spec; the *behavioural* residue closes only with a long mild-weather cool capture (summer season / opportunistic) |
| B-6 | **Commissioning/discovery spec for our configuration** — boot ritual and sweep are captured for our install, but the full wizard run was never captured start-to-finish in one file (map G11), and the sweep address set is configuration-dependent (the gofinity system probes 0x0E; ours never does — audit §2.4) | PENDING-U. Residue: one full installer-wizard capture if the Ion is ever recommissioned for other reasons |
| B-7 | **The 0414/060B shared byte** — one byte in two thermostat→equipment writes varies together over 72–153 (coldstart) and beyond in other captures; 63 distinct payloads each. Everything else in the burst is constant and replay-safe (audit recount: 0307, 0403, 0409, 031D, 0610, 0612 payloads are single-valued across the whole archive) | Offline capture analysis: correlate the byte against OAT/demand channels (0302/0306/0420) across all 12 captures. No live session needed. If it is OAT-derived, the emulator computes it from its own OAT reading |
| B-8 | **Serializer construction** — proven unreachable by statics (F, N, DUAL) and by the emulator harness (M: no entry point; inputs are discovery-built RAM objects) | **Accepted boundary — do not re-attack statically.** The emulator reproduces wire behaviour from captures + constants; that is sufficient for every observed scenario. The only remaining route is on-device debug (E10A-USB) on a *spare* unit — rejected for the live unit (M, N §10) |
| B-9 | **Mode semantics from the firmware side** — SYSCTRL-49 encoding (heat 0 / cool 1 / auto 2 / off 5) is still a hypothesis; CD7D's provenance is mapped (L) but its value set is not tied to UI modes | PENDING-S. For the emulator itself this is informational (it defines its own modes); it is load-bearing for the *current* SAM control project (mode-experiment session 1, live) |
| B-10 | **SAM-facing behaviour of the emulator** — if any SAM client remains after Ion removal | Largely closed during this audit by stage V (delivered, not audited here). If the design drops the SAM role entirely (ESP becomes the thermostat), this gap is moot |

### 4.2 Blocks live testing (needs the author at the equipment)

| # | Gap | Closing route |
|---|---|---|
| T-1 | **G1 — comm-fault timeout & mid-call death behaviour.** Nothing in firmware or captures gives it (it is a furnace/ODU-board parameter; I/K confirm it is not in the Ion image). Sizes the failover watchdog and the whole step-9/10 test design | Controlled reseat test under capture, escalating silences 30 s → 10 min, idle and mid-heat-call (map G1 protocol). **Do before any live emulator test** |
| T-2 | **G5 variants** — furnace-only power cycle while the thermostat stays up; thermostat reseat with verified capture flow | Two captures in one session with T-1 |
| T-3 | **G9 — exception behaviour** of 44/53 to unsupported-register reads (the only gap whose test transmits) | One probe session from the SAM node, **only with the author's explicit go-ahead** |
| T-4 | **Mode-experiment session 1** (Heat/Cool/Auto/Off register diffs) — for the current control project; kit ready since 2026-11-03 | One attended session |
| T-5 | **Seasonal behaviour captures** — long mild-weather cool run (B-5's residue); winter heat soak is partially in hand (staircase + stage 2 observed) | Opportunistic; summer for cool part-load |

### 4.3 Nice to have (nothing blocks on these)

| # | Gap | Note |
|---|---|---|
| N-1 | G2 — exact serial digits in our 0104 identity | Read off the Ion About screen / sticker; 1 minute, no test |
| N-2 | G10 — 0202/0203 clock field mapping | One capture with the Ion clock set to a known value; the emulator keeps its own time regardless |
| N-3 | G3 — real (registered-SAM) 3B02/3B03 contents | Unobtainable on this Ion (registration gate, C); infinitive's layouts (EXT, audit-verified body lengths) are the accepted reference. Only matters if B-10 stays in scope |
| N-4 | 0x78 semantics | Behaviourally closed: emit 0 until commissioned, 0x78 after (N §7, audit §2.5). The meaning (CFM class? bitfield?) is curiosity |
| N-5 | Remaining constant payloads' semantics (030A 14 B, 0625, 4202's 72-vs-70 B) | Replay-verbatim suffices (audit recount: constant across the archive) |
| N-6 | Catalog class-byte semantics; BUYPASS-CRC consumer; the 7 writer-less RAM cells (L §7); C90C writer ordering (L §6.5); field-store vs member-registry store identity (J §9) | Structural curiosities; none changes emulator behaviour. The store-identity question does affect how I/J's directory tables should be *cited* (audit §1.2) |
| N-7 | Humidity/dehumidification scope | Not an RE gap: the equipment summary lists furnace + AC + coil only. Whether the emulator implements overcool-dehumidification is a design decision for the author, informed by the algorithms research |
| N-8 | 4.74's Clarinox version; Series C architecture | VERSIONS §5 (undeterminable from strings); stage W (delivered during this audit, unaudited) reports the older data plane holds no serializer leak |

---

---

## 2b. Additional rulings from the full-corpus sweep

### 2b.1 Message-class count: E's "12 classes" vs G's 20 — G wins

E §0.5/§8 speaks of "12 message classes" for `sys_ctrl_task`. G §3
enumerates **20 post-side stub classes (0–19)**; the dispatcher's
*statistics* cover only classes 0–11, and the dispatcher itself has
no bounds check (G §1, listing-verified). E conflated the stats
range with the class space; G corrects it without flagging the
correction. **Ruling:** 20 classes; quote G. (G also upgrades E §8's
other dispatcher claims — 1000 ms timeout, stats layout — from
single-method to dual-verified; values unchanged.)

### 2b.2 The {375.0, 400.0} getter may be unreachable from its only described caller

E §7: `FUN_18051cec` returns 375.0/400.0 only when its selector
argument == 5. E §6 / G §4: the helper `FUN_180c5c7c` calls it with
`u ∈ {1, 2}` by construction — a call that can never take the
375/400 branch on E's own rule. Neither report notices. Either the
selector is a different parameter than `u`, or the branch is dead
on this path, or another caller exists. **Ruling:** unresolved
tension inside E; the constants' *existence* and cross-version
stability (audit §2.3) are solid, but their **live role is
doubtful** — do not cite {375, 400} as "the CFM limits" anywhere.
Referred to PENDING-R/Q.

### 2b.3 CCC4's role: E (threshold values) vs G (breakpoints) — apparent, dual use

E §3 reads `0xFFF8CCC4` as the staging threshold table; G §6 reads
it as a breakpoint array whose values live in the parallel array
`0xFFF8CC64`. L §4 (later) has `FUN_181f21d4` computing CCC4/CCDC/
CD04 as one table family, consumed both by the staging machine
(demand-domain thresholds) and by the interpolation engine
(breakpoints over the same demand domain). **Ruling:** no factual
contradiction — the array serves both consumers; E and G each saw
one. Definitive per-consumer assignment is PENDING-Q.

### 2b.4 0x78 semantics: F's "installation capability byte" superseded by N's state byte

F §6 read 0x78 as a constant configuration/capability byte *of
this installation*; G §8 notes the same value 120 is used inside
sys_ctrl as a supervision-timer property (and disclaims any link).
N §7's commissioning evidence (audit §2.5: [11]=0 in all 22
commissioning + 3 SystemInit frames, 0x78 in all 652 steady-state
writes) supports the cleaner account: **a state byte — 0 until the
device object is initialised, 0x78 after**. **Ruling:** cite N;
F's wording is superseded, G's timer parallel is a coincidence of
value (as G itself says).

### 2b.5 The "1,811 writes" corpus figure — not reproducible

Map line 115 and F §6 (citing the map) state [11]=0x78 "in all
1,811 writes observed". **Audit recount:** the current archive
contains **677** deduplicated 0305 write frames (832 counting the
duplicate segment copies of coldstart; 832 is also the total of
0305 frames of *any* kind). No counting of the present archive
reaches 1,811. **Ruling:** the figure is an unreproducible corpus
number (presumably from an earlier, larger working set); the
qualitative claim is verified on 100% of the reproducible corpus.
Errata E-3.

### 2b.6 031C vs 031D — resolved for our installation: follow our captures

Gofinity's thermostat writes `031C`→furnace once at boot (frame
534, before its first demand); SAM-RESEARCH records 031C writes to
SAMs and IDU/ODU on other controls. **Audit check: zero 031C
frames exist anywhere under `traces/`** (all files, incl.
segments). Our Ion's repertoire has `031D`→44 = constant `01`
(audit recount: 209 writes, single distinct payload) and no 031C.
**Ruling:** a cross-generation difference, not a gap in our data;
the emulator follows our captures. Whether some untested Ion
sequence (full recommissioning) emits 031C is part of gap B-6.

### 2b.7 Stage A's check-word negative — superseded by B (as B documents)

A §3 left the image check word UNDETERMINED after testing sums,
yet B §1 solves it as a plain 32-bit byte sum over
0x18040000–0x18F3FEF8 with **0xFF gap fill** — the discriminating
detail A's ranges did not use (B documents the failing
perturbations). **Ruling:** B is correct and complete; A's
negative is a method artefact. No downstream claim depends on A.

### 2b.8 External-doc seams (recorded, not load-bearing for our stack)

- **Wiki triplet cadence:** SAM-RESEARCH's wiki source claims the
  0x1F broadcast triplet repeats every ~1.3 s; both real captures
  (ours, gofinity's) show it **once**, opening the sweep. Captures
  win.
- **Header endianness as written:** infinitive describes dst/src
  as u16 BE, gofinity's Frame.go as LE — the two external docs
  disagree on paper. Our pipeline (InfinitESP + capture.py) is the
  operative definition for our frames; do not port constants
  across notations without the width/endianness reconciliation
  infinitive-registers itself flags.
- **0420's two roles:** thermostat broadcast table (infinitive)
  vs SAM-served config register (SAM-RESEARCH, from a physical-SAM
  scan). Register numbers are per-device, so both can be real;
  neither doc acknowledges the other. Unresolved on paper,
  harmless in practice: our SAM node is our own code.
- **Stage C's pool-cell arithmetic:** C reports 279 Ghidra pool
  cells for setter-B but its own raw scan found 257 BE-word
  occurrences — a 22-cell discrepancy C records without explaining
  (presumably non-word-aligned references). Immaterial to C's
  conclusions (the 894-call-expression census is the load-bearing
  figure, corroborated by I/J).
- **D §3.2 tiling arithmetic** lands at 0x182C53D6, not the stated
  string base 0x182C53D8 — a 2-byte slip in D's prose (a pad, or a
  count off by a fraction of a record). the author's coil record address
  is unaffected (audit-verified byte-for-byte, §2.5).
- **F's geometry has a ±2-byte seam:** F's bucket index
  @0x182B6A4A × 0x40 u16 ends at 0x182B6ACA, overlapping F's member
  registry base 0x182B6AC8 by 2 bytes; one of the three numbers is
  off by 2. The audit's parse (386 groups ending 0x182B6A49,
  bucket-shaped data from 0x182B6A4A) is consistent with F's bucket
  base; the registry base is the likely slip. Immaterial — the
  decisive member[324] test passes under the audit parse.
- **G §2 item 4** repeats D's superseded directory reading
  (base 0x182B5E40, "field-store offsets") although F's reparse
  predates it. G's own results do not depend on the directory;
  recorded as a citation-hygiene defect only.
- **Evidence-class note:** G §6's interp-2 segment adjustment
  leans on E §6's arbitration outputs, which E §11 itself marks
  "one-and-a-half method" (no listing pass). Values are consistent;
  the class is weaker than G's presentation suggests.

### 2b.9 File defect found: `external-research/sam-spec-notes.md` is truncated on disk

The file literally ends mid-sentence in §8.2 item 5 with an
embedded "...[truncated 8182 chars]" marker; §8.2 items 5+ and the
referenced §8.3 **do not exist on disk**. The SAM01-01XA PDF in the
same folder is intact (14 pp, audit-checked header). Any claim
attributed to sam-spec-notes beyond §8.2 item 4 is unsupported by
the file as saved. **Recommendation:** re-extract the tail from
the PDF before the SAM spec is used for stage V/T work. (Stage V
delivered during this audit; whether it relied on the missing
tail is for its own review.)

---

## 3. Claim ledger (summary)

Load-bearing claims for the emulator, with evidence class and
source. Everything marked CAP was additionally re-verified by this
audit's recounts where noted (§2.5).

### 3.1 Bus and protocol (from the map, capture-proven)

| Claim | Class | Source |
|---|---|---|
| 0x20 is the sole steady-state initiator; 44/53 only answer; funcs 0B/06/0C only; no 0x15, no write-ACKs in the archive | CAP | Map §(a) |
| Poll tiers 3/5/7/10/11/17/20/29/31 s; no schedule exists as firmware data (D §2.3, N) | CAP + DUAL | Map §(a); D-15 |
| Command burst every ~10 s (median 10.00 s, audit recount): 0305/0403/0409/0307 →44; 0605/060D/0610/0612/061A/061E →53; 060B/0414 every ~20 s; 031D ~30 s | CAP | Map §(a)/(e); N §9; audit §2.5 |
| Burst payloads other than 0305/0605/060D and the 0414/060B shared byte are **constant across the entire archive** (audit recount: single distinct payload each for 0307, 0403, 0409, 031D, 0610, 0612) | CAP | Audit §4.1 B-7 |
| 0305 layout: [0] heat stage {0,1,2}, [2] cool stage {0,2} observed, [4..5] CFM BE16, [11] state byte (0 pre-init, 0x78 steady) | CAP | Map §(e); N §7; audit §2.5 |
| 0605 layout: float32 BE stage [0..3] (only 0.0/5.0 observed), [4] call-state, [5] = 0, [6] = 1 on directed frames | CAP | Map §(e) as corrected by J §6; audit §1.4 |
| 060D = 02 during any call (heat or cool), 00 idle | CAP | Map §(e) |
| 061E = `0F` + coil param f32 BE + `06` + zeros; the param is the commissioned coil's, committed at commissioning | CAP + DUAL | D §3; audit §2.5 |
| Boot: ~6 s to 0x1F triplet (0305/3E02/0605 zero broadcasts), ~95 ms probe sweep (unanswered ×2, answered ×1), frame-adjacent 0x1F→0x20 handoff at +16.7 s from power, first burst +39 s, steady ≈62 s | CAP | Map §(c); gofinity-bootup (EXT, second system); audit §2.4 |
| Serve obligations: 0x93's 3B05 poll every 300 s → 11 zero bytes; SAM reads 3B02 (29 B) / 3B03 (150 B) — all zeros from this unregistered Ion, 100% of 865/868 replies | CAP | Map §(b); audit §2.5 |
| Thermostat never accepts control from equipment; setpoint values never appear in thermostat→device traffic — devices see demand only | CAP | Map §(a)/(e) |
| Silence discipline: healthy 0x20 never silent >~3 s steady-state, >~5 s mid-wizard | CAP | Map §(d) |

### 3.2 Control law (firmware statics)

| Claim | Class | Source |
|---|---|---|
| Staging machine FUN_180c54d8: pure demand hysteresis — stage 2 at demand > T×1.25, stage 1 at > T[1]×0.25, drop at ×0.01, 2→1 at ×1.00; gated on mode byte CD7D == 2; **no timers** | DUAL | E §3 (D+L+R verified; emulated 12/12 by M) |
| Demand quantizer FUN_180c576c: Schmitt thresholds 5/0/−5, deadband ±1, state byte CD4B | DUAL | E §2; emulated 11/11 by M |
| Setpoint trim FUN_180c55f2: D = clamp(x, 0, 6); flagged zones −D/2; cap 70.0 | DUAL | E §4 |
| Satisfaction averager FUN_18183d34: hysteresis 1.5/2.5 on mean zone satisfaction | DUAL | E §5 |
| Source arbitrator FUN_180c5832: state 0–5; dictionary enum `cooling, hpheat, eheat, gas, reheat, fangas` is name-only (mapping INF) | STATIC (one-and-a-half method) | E §6 |
| Demand CD44 = Σ zone contributions via FUN_180c62fc + 5 helpers (formula PENDING-O); second writer FUN_180c4322 (dispatcher case 2) | DUAL (writers) | L §3.1 |
| Threshold tables CCC4/CCDC/CD04 are **computed** by FUN_181f21d4 from equipment class word CC52 (field-store field 1) + R = field-8 byte/12.0 + X = clamp(float, 12, 61); full per-class formulas in L §4; **our CC52 value unknown statically** | DUAL | L §3.2–3.4, §4 |
| Interpolation engine FUN_180c15d2 consumes CD44 over the tables; it is a consumer, not a producer (E's suspicion resolved negatively by G) | DUAL | G §6 |
| Equipment-reported values (0316, 0306/0307, table-04, all 06xx slots) have **no code consumer** in the control lineage — the law is dimensionless and equipment-independent given the RAM tables | DUAL | I §4–5; J §3 (subject to audit §1.2's mapping caveat) |
| CFM is computed at runtime; no stored CFM value or capacity constant exists in the image (107000/60000 BTU absent in all encodings) | DUAL | I §6; J §5–6; K §1 (audit §2.4 on wording) |
| Sys_ctrl supervision: 20 message classes → one 10-state FSM (FUN_181f86cc); handler table @0x3C12EC70 is never populated in the image; supervision property values 10/15/30→45/80/120/300 are timer-*like* (units unproven) | DUAL | G §1–5 (correcting E §8's framing, §2b.1) |

### 3.3 Equipment parameterization

| Claim | Class | Source |
|---|---|---|
| The coil is the **only** component with a stored model→parameter table (263 records, 4 arrays); our coil EN(A,D)4X61 → **1.69**, committed to field 0x59F (+0x1C7C/0x1C7D/0x1C7E) at commissioning | DUAL | D §3; K §2; audit §2.5 |
| 1.69 is a size-class parameter (also serves CNPV*61) and is **1.69 in all 16 firmware versions**; no coil parameter ever changed in any version | STATIC | K §2; VERSIONS §4 |
| Furnace/ODU self-report via 0104 (model + CESR) and config tables; the thermostat holds no model DB for them | DUAL | D §3.1 (as corrected on zlib, §1.1); I §1 |
| Decision-core constants {375, 400} and ratios ×1.25/×0.25/×0.01 are present in every version 2.40→4.79 (exact literal counts method-dependent, §2.3); the staging core did not change in 6 years of releases | STATIC | VERSIONS §4; E §3/§7 |
| Official ICP 4.79 image is byte-identical to our unit's (MD5 e3190322…, SHA-256 2d1a9ea3…c90c04); the image is brand-universal (Carrier = ICP) | DUAL | VERSIONS §0.2; A §5; audit §2.5 |

### 3.4 SAM relationship

| Claim | Class | Source |
|---|---|---|
| SAM registration is gated on an internal Clarinox binding (device-record dword at object+0x38 ≠ 0), checked at 0x18147C6C; field 0xC4 ('Z' = SAM present) is an **output** of that check, written only by FUN_18147c58 from state 0x17 of a running SAM/B36 manager FSM | DUAL | C §5–7; B (presence model) |
| No bus-reachable flag flips the gate; the only external lever is what answers at 0x92 during discovery and how the ID handlers classify it | STATIC + INF | C §7 |
| On controls where registration works: gate reads are 040E + 3F02 at 0x92 during INSTALL; post-registration supervision reads 040E ~10 s, 030D ~23 s; control writes 031C to the SAM and pushes 3B06, acks changes with 3B0E | EXT | SAM-REGISTRATION-RESEARCH (issues #41/#42, wiki) |
| Our Ion: never read 040E/3F02, never wrote 031C, never polls 0x92 in steady state, in any capture | CAP | SAM-REGISTRATION-RESEARCH; audit §2b.6 (031C) |
| SAM ASCII face: setpoint write = MANUAL activity + hold (with duration = hold-until, without = permanent); HOLD!ON = permanent hold on current activity; Touch clamps out-of-range setpoints and shifts the pair for deadband | EXT | SAM01-01XA via sam-spec-notes §§1–8.2(4) (file truncated after that, §2b.9) |
| 3B02/3B03/3B04 field layouts and the change-flag write dialect (flags at body [1..2]; 0x000C = heat+cool SP, 0x0010 = mode) — infinitive ≡ InfinitESP with a +3 offset shift; body sizes 29/150/11 match our captures exactly | EXT + CAP | infinitive-registers; audit §2.5 |
| Writing 3B02 global parameters rolls the thermostat clock back up to 1 min per write (infinitive's +30 s / flags 0x180 compensation) | EXT | infinitive-registers |
| The phase-3 HA climate card **never** showed live wall data: 70 °F was the hub's boot seed, "Per Schedule" a default-branch artefact of the preset matcher; the wall serves neither room temperature nor mode over the SAM interface | CAP (negative, ~75k frames) | PHASE5.md §1.3 |

### 3.5 Platform / engine

| Claim | Class | Source |
|---|---|---|
| CPU Renesas SH-2A (SH7269) BE; Clarinox suite 9.0.0 family (Blue b11452, SoftFrame b16695, WiFi 9.0.0.p3 b2097) = network/BT/OS layer only; the binding/dictionary engine is Carrier's own CING code on top | DUAL | H (clarinox-image); clarinox-web (EXT) |
| Frame serializer + bus CRC routine + TX queue are **absent from statically reachable code** — four independent exhaustive censuses (constants, CRC, peripherals, output readers); dispatch is via runtime-registered per-class transmit pointers over discovery-built RAM objects | DUAL | F §7; N §§2–6 |
| The only CRC tables in the image: reflected-0xA001 @0x182C4164 (sole consumer: the 30-byte dictionary publisher FUN_180EA704) and CRC-16/BUYPASS @0x182AD53C (proven NOT the bus CRC, 200/200 vectors) | DUAL | D §1; N §3; audit §2.5 |
| Image integrity: additive 32-bit byte sum over 0x18040000–0x18F3FEF8 with 0xFF gap fill = stored word 0x92B6CC87; no cryptographic signature | DUAL | B §1 (superseding A, §2b.7) |
| Unified catalog: 5,417 records {class, 00, id BE16} @0x18404928–0x18409DCC; 0303/0305/0307 absent in 4.79 (present in 4.47–4.74 catalogs — a 4.79 data-model removal); class-byte semantics not established | DUAL | K §3; VERSIONS §6; audit §2.5 |
| Dynamic route: Ghidra PCode emulation of decision leaves works (23/23 vectors, M); it cannot cross the serializer boundary (no entry point; inputs are discovery-built RAM) | DUAL | M (dynamic-route); N §10 |
| Protections/staging/defrost mostly live in the equipment boards and Ion's own layer, not in anything the SAM-side emulator must replicate; our control layer is UL 60730 Class A (non-safety) | EXT | Algorithms research report |

---

---

## 5. Protocol-map errata checklist (for the parent agent to apply)

Line numbers are the map's current ones (486 lines). The map itself
was **not** modified by this audit.

- [ ] **E-1 (factual error) — line 366:** 0605 cool payload
  `40A00000010001`, "byte [5] also 00→01" → the changing byte is
  **[4]** (call-state). Fix line 123's layout sentence too: cover
  all 7 bytes — [0..3] float32 stage, [4] call-state 0/1, [5] = 0
  always, [6] = 1 on directed frames / 0 on broadcast frames.
  (J §6; audit §1.4.)
- [ ] **E-2 (precision) — line 349 and §(e):** "`[11]` = `78`
  always" → "0x78 in all steady-state writes; 0x00 in the
  SystemInit frames and the two commissioning windows (25 frames
  in the archive)". (N §7; audit §2.5.)
- [ ] **E-3 (unreproducible figure) — line 115:** "constant in all
  1,811 writes observed" → the current archive holds 677
  deduplicated 0305 writes; the qualitative claim is verified on
  all of them. Replace or annotate the count. (Audit §2b.5.)
- [ ] **E-4 (terminology) — lines 203–205:** "`00000C`/`000010`
  mode words" → these are the **change-flag words** at body
  [1..2]: 0x000C = heat-SP + cool-SP flags; 0x0010 = mode flag.
  (infinitive-registers.)
- [ ] **E-5 (stale gap status) — G3/G6:** annotate as partially
  closed by infinitive-registers: full 3B02/3B03/3B04 layouts, the
  flag dialect, and the Touch two-write model (notification write
  primes, direct write delivers) are now documented from external
  sources. What remains unknowable is only the registered-on-this-
  Ion contents (registration is gated, stage C).
- [ ] **E-6 (scope) — lines 38–39:** "reads of absent devices are
  simply never answered" holds for 44/53 in this archive, but the
  dialect has a real exception function 0x15 (code 0x04) —
  exercised by SAM-side devices for absent tables. Qualify the
  sentence's scope; G9 remains open for 44/53 specifically.
- [ ] **E-7 (missing quantification) — §(b) serve table:** add:
  no 3B02/3B03 broadcast (mirror) write from the thermostat exists
  in ~75,000 captured frames — the passive-mirror path never fires
  on this Ion; wall room temperature and system mode are **not**
  obtainable over the SAM interface (3D02 slow-poll reads were
  never answered). (PHASE5.md §1.3.) This is the fact whose absence
  enabled the phase-3/4 fossil misreading.
- [ ] **E-8 (uncorroborated field) — line ~82 (0608):** "requested
  IDU CFM BE16 [5..6]" is [SRC]-only and no captured value is
  quoted anywhere; add the firmware-side fact that the slot has
  **no consumer** — 0305 CFM does not follow it. (J §5.)
- [ ] **E-9 (range wording) — §(e) CFM statements:** the archive's
  observed 0305 CFM set is {0, 378, 379, 382, 384, 1166, 1232,
  1368, 1617, 1660, 1710, 1750, 1760} (audit recount) — present it
  as observed values, not a 379–1760 range; another system's
  capture shows 360 (gofinity), so the floor is not a clamp.
- [ ] **E-10 (thin claim) — line 69 (0303):** mark the one-line
  [SRC] claim as unverified beyond InfinitESP docs (no payload
  example exists in the map). Add the firmware-side correction:
  0303 **has** binding groups (device classes 0x51/0x52/0x56/0x57/
  0x5B) although it is absent from the unified catalog — this
  corrects stage N §8, which states the opposite.
- [ ] **E-11 (timing origins) — §(c):** state the origin for every
  boot figure (t=0 = power/capture start; 0x1F opens +6.0 s;
  handoff +16.7 s from power; first 0x20 0305 +65.6 s from 0x1F
  start; steady ≈62 s). Cross-doc confusion on these numbers is
  documented in audit §2.4.
- [ ] **E-12 (client cadence) — §(b):** annotate that the ~3 s
  3B02/3B03 alternation is InfinitESP's polling, not a protocol
  constant: a real SAM polls the thermostat at ~65 ms, and
  infinitive's client uses 500 ms timeout × 5 retries. An emulator
  serving a SAM must not assume a 3 s client.
- [ ] **E-13 (missing identification) — §(c) sweep list:** the
  probed address 0x94 is the **B36** slot (stage C §8, strong
  inference from the bitmap-clear pair 0x92/0x94); the map lists
  the probes without the identification.
- [ ] **E-14 (no change — verified open):** 4202's 72 B observed
  vs 70 B nominal (line 192, G4) remains unresolved in every
  later doc; keep the flag.

---

## 6. Audit trail and scope notes

- Re-check artifacts: `firmware-re/audit/recheck_image.py`,
  `recheck_image2.py`, `recheck_captures.py` (+ `.out` files) —
  independent implementations; no stage script was reused, no
  stage file or the protocol map was modified.
- Corpora used: `firmware-re/stageB/flat.bin` (15,728,640 B, the
  analysed 4.79 image; identical copy in stageH), all 12
  top-level `traces/*.jsonl` (83,752 frames) plus `traces/segments/`
  for the corpus-count ruling, decoded version images 0240/0474
  for the cross-version constant recount.
- Not audited (in flight or just delivered, per the parent fleet):
  stages O, P, Q, R, S, T, U, X, Y (running) and V, W (delivered
  during this audit — their headline results are noted in the gap
  list where relevant, but their claims have not been through this
  process). A follow-up audit pass over O–Y + V + W is recommended
  once they land, with particular attention to: the FUN_18051cec
  reachability tension (§2b.2), the CCC4 role assignment (§2b.3),
  and whether stage V relied on the truncated tail of
  sam-spec-notes.md (§2b.9).
