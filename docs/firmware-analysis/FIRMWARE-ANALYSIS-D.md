# FIRMWARE-ANALYSIS-D — Stage D: equipment-control path, poll data plane, and the indoor-unit model database

Target: Carrier/ICP "Ion" wall control firmware **BINF0479, v4.79** (Renesas SH7269,
SuperH:BE:32:SH-2A, image base `0x18040000`). Source image
`ion-firmware/carrier/BINF0479_Carrier.hex` (binary Intel-HEX-record stream,
MD5 `e31903228bf39a4bc9c0a2a74192359e`, byte-identical ICP/Carrier — stage A).

**Scope of this stage.** Stages A–C covered the SAM-registration / binding
engine. Stage D targets what A–C did not: (1) the ABCD frame-construction /
transmit path toward the furnace (`0x44`) and outdoor unit (`0x53`); (2) the
cyclic poll schedule, if it exists as data; (3) control constants near the
equipment-command logic; (4) thermostat-side behaviour on equipment silence;
(5) the per-model equipment database the author's commissioning flow implies —
furnace `G80CTL1352422A2`, ODU `HVA960GKA201`, evaporator coil `EN(A,D)4X61`.

**Mandate (2026-11-26):** maximum effort; every extracted table / record /
constant / call-site claim dual-verified by a second independent method
before it is stated as [FACT]; exhaustive enumeration, no sampling; closing
porting section mapping findings to the gap list G1–G11 of
`THERMOSTAT-PROTOCOL-MAP.md`. A parallel stage E covers the control-decision
core; this stage stays on the transmit path, the poll data plane, and the
model database.

**Method.** All work on copies under `firmware-re/stageD/` (own copy of the
stage-C Ghidra project `proj/`, scripts, outputs). Ghidra 12.2 headless
(`firmware-re/stageB/ghidra/support/analyzeHeadless`, Temurin JDK 25),
`-noanalysis` on the stage-B-seeded project "Bing" (10,853 functions), plus
raw Python scans of `firmware-re/stageB/flat.bin` (15,728,640 B, base
`0x18040000`). New script this stage: `XrefDump.java` (reference enumeration
per target). **Toolchain verification: PASSED** — smoke run plus runs 1–9 all
`EXIT=0` (logs `stageD/run*.log`).

**Headline results.**

1. The ABCD **frame builder / UART transmit queue is NOT isolated** (§1).
   The one CRC-16 table in the image belongs to a fixed-length dictionary
   record path, not to the bus. The equipment data plane that *is* visible
   is a 385-record field-binding directory (§2). The wire engine sits
   behind the Clarinox object/registry layer (computed calls, runtime
   registration) and does not yield to the static anchors tried.
2. **No cyclic poll schedule exists as a data table** in any structure
   found (§2.3). The capture-observed tiers (3/5/7/10/11/17/20/29/31/60 s)
   are not stored as `{dest, table, period}` records anywhere identified.
3. **The model database exists — but only for the passive indoor units**
   (coils / fan coils), not for the furnace or ODU (§3). Four pattern lists,
   263 records total, fully extracted. **the author's coil record is verbatim:**
   `EN(A,D)4X61` → float `0x3FD851EC` = **1.69**, and those exact 4 bytes are
   bytes [1..4] of the `061E` write payload seen in every capture — the
   first G4 "constant" to gain a semantics.
4. The selection-commit path is identified: `FUN_18140C80` / `FUN_18140BEA`
   write the chosen model's parameters into the field store at offsets
   **`0x59F`** (float param), **`0x1C7C`**, **`0x1C7D`**, **`0x1C7E`** (§3.4).

---

## 1. Transmit path: hunt log and what was actually found

### 1.1 The only CRC-16 table, and why it is not the bus CRC

[FACT — dual: signature scan + recomputation] A reflected-0xA001 CRC table
signature scan over the whole image finds three candidate starts; only
**`0x182C4164`** verifies: all 256 entries equal the CRC-16/MODBUS-style
table (poly `0xA001`, reflected) stored as BE16 words, recomputed
independently in Python (256/256 match). The other two candidates
(`0x182B598C`, `0x182C2EEC`) match 16/256 — false positives.

[FACT — dual: pool-cell scan + Ghidra refs] Exactly one pool cell references
`0x182C4164`: **`0x180EAA1C`**, inside `FUN_180EA704`.

[FACT — dual: decompiler + instruction listing
(`out/listing_crc.txt`)] `FUN_180EA704` computes this CRC over a **fixed
30 bytes** (`mov #0x1e, r7` loop bound at `0x180EA712`/`0x180EA74E`), init 0.
Callers (Ghidra `XrefDump`, `UNCONDITIONAL_CALL`): `FUN_180EA4EC`
(@`0x180EA544`) and `FUN_180EA5BC` (@`0x180EA5FE`). A raw BE32 word scan for
`0x180EA704` as data finds 0 occurrences — the calls are direct branches,
not table entries (consistent with the two methods agreeing on the call
edges, not on data refs).

### 1.2 The 0x180EAxxx cluster is a dictionary-record publisher, not the TX path

Cluster survey `0x180EA000–0x180EB000` (12 functions, `out_cluster_ea/`):

- `FUN_180EA4EC` builds a `0x32`-byte buffer (copies `0x32` B, fills via
  `FUN_180EA610`), stores the `FUN_180EA704` CRC at +0x1E/+0x1F, zeroes
  `0x12` B at +0x20, and publishes through a 5-argument API call
  `(0x4F, 3, 0x32, buf, 0xFE)` — the same `(id, 3, len, buf, flag)` shape as
  stage C's dictionary op `FUN_180A8DA2`. [FACT: decompiled call shape]
- `FUN_180EA610` is a change detector: writes record fields at offsets
  +2, +6, +0xB, +0x11, +0x12 only when changed.
- `FUN_180EA238` (626 B) reads field-store offsets `0x24, 0xBF, 0x28,
  0x1C3B, 0x1C3C` via the stage-C getter and assembles a 12-byte record,
  then calls `FUN_180EA4EC`.
- `FUN_180EA75A` compares a 2-byte field-store value (offset 1) against
  `0x8241`/`0x8141`. `FUN_180EAB02` (834 B) is float/setpoint-flavoured
  logic — control-core territory (stage E).

**Inference (strong):** a fixed-30-byte CRC'd record published through the
dictionary API is the Clarinox binding/dictionary layer's integrity-checked
record path. ABCD frames are variable-length; this is not the frame
builder. The cluster is reported so the next pass does not re-chase it.

### 1.3 Anchors that did not lead to the frame builder

Each of these was tried and produced the stated negative:

- **Payload constants in flash:** the full `061E` payload
  `0F3FD851EC06000000`, the `0612` payload `22B80000000000000000`, and the
  idle `0305` 12-byte payload occur **0 times** in the code regions
  (raw byte scan). The burst constants are computed/assembled at runtime,
  not stored verbatim. [FACT: scan of `flat.bin` code span]
- **Table-ID immediates in driver clusters:** cluster survey of the
  device region `0x18070000–0x18073000` (139 functions, `out_cluster_70/`)
  plus the binding neighbourhood `0x180A7000–0x180AB500` (26 functions,
  `out_cluster_a7/`): no decompiled reference to `0x305 / 0x306 / 0x604 /
  0x605 / 0x60D / 0x61E` as immediates, and no `0xA001`. Equipment tables
  are reached through the binding directory (§2), not through immediates.
- **Peripheral bases:** pool-word tally for `0xFFFE0000–0xFFFFFFFF` is
  dominated by masks/sign-extension constants; no SCIF base stands out.
  The BSP serial driver was not isolated this way.
- **Discovery-probe tables:** byte-pattern hunts for `(addr, table)` probe
  sequences and for ascending zone-address runs found only ambiguous data
  (e.g. `21 22 23 24 25 26 27 28` at `0x182AF000`/`0x182AF080`, adjacent to
  stage B's hash-prime table — suspect, not claimed). No probe table is
  claimed.
- **4-byte table-catalog blocks** at `0x18404EC0–0x1840575C` (551 records
  `{type ∈ {1,2}, 00, table BE16}`, ids `0x0194–0x03CF`) and
  `0x18405D40+` (06xx ids): a table *catalog* (dictionary/UI), no periods,
  no destinations, no pool pointers to their bases. Not a poll schedule.

**Conclusion for goals 1–2:** the frame-construction / transmit function
and its call sites toward `0x44`/`0x53` are **not isolated**. The evidence
says the thermostat's equipment traffic is driven by the Clarinox
dictionary/binding engine over the field store (stages B/C architecture):
drivers register field bindings (§2), the engine performs the wire work
behind computed calls. Any future isolation attempt should start from the
engine's descriptor table (stage C, `0x182B04D4`) provider pointers, or
from dynamic analysis, not from constant hunting.

---

## 2. The poll data plane: the field-binding directory

### 2.1 Structure and extent

[FACT — dual: two independent extent walks + hex-dump inspection] At
**`0x182B5E40–0x182B6A48`** lies a directory of 8-byte records:

```
[len][00][table_id BE16][field][flags][store_offset BE16]
```

- Walk 1 (validator `len ≤ 16`): 310 records, ends `0x182B67F0`.
- Walk 2 (validator `len ≤ 64`): **385 records**, ends `0x182B6A48`, where a
  different structure (repeated `0x015E` pairs) follows.
- The discrepancy is explained by inspection: records past `0x182B6800`
  legitimately carry `len` up to `0x19` (e.g. table `061F` field records at
  `0x182B6800`: `13 00 06 1F 56 01 03 FF`). Walk 2's extent is the correct
  one; walk 1's "absent" list was provisional and is superseded.
- Store offsets increment by field length within a table's field sequence
  (verified on samples, e.g. table `0302` fields at store `0xBE, 0xC0`;
  `0303` at `0xC2, 0xC4, 0xC6`).
- [FACT — raw scan] Zero BE32 pointers into `0x182B5E40–0x182B6A48` exist
  anywhere in the image: the directory is found by the engine at runtime
  (registration/scan), like every other Clarinox structure in this image.

Full verbatim dump: `out/binding_directory.txt` (385 records).

### 2.2 Which tables are bound — exhaustive

Present (record counts in the dump): `0104, 0302, 0303, 0304 (×9), 0306
(×3), 0307, 030A, 030D, 030E, 0310, 0311, 0316, 0317, 0319, 031B, 031C,
031E, 031F, 0320–0323, 0326, 0327, 0402–0438 (subset: 0402, 0403, 0404,
0405, 0407, 0409, 040A, 040B, 040C, 040D, 040F, 0410, 0411, 0413, 0414,
041B, 041C, 041E, 041F, 0424, 0428, 0429, 0434, 0438), 0502, 0504, 050E,
0602, 0604 (×5), 0605 (×3), 0606, 0607, 0608, 060A, 060E, 0612, 0613, 0615,
0616, 0618, 061F (×5), 0625 (×5), 0702, 0704–0708, 0715, 0716, 2403, 2406,
2415–241C, 3404, 3405, 3406, 3E01 (×2), 3E02 (×2), 3E03, 3E04, 3E07,
3E08 (×1), 3E09–3E0E`.

**Absent in both walks** [FACT]: `0305, 060B, 060D, 0610, 061A, 061E, 031D,
0202, 0203, 400A`, and `3B02/3B03`.

**Interpretation (inference):** the directory binds fields of tables the
thermostat *mirrors into its dictionary* — overwhelmingly tables it reads
(polls) plus a few it also writes (`0307, 0403, 0409, 0605, 0612` appear).
The pure command outputs of the 10 s burst — `0305` (demand), `060D`
(flag), `0610`, `061A`, `061E` (constants), `060B`, `031D` — have **no**
field bindings, and neither do the thermostat-owned tables `0202/0203`
(SYSTIME) and `400A` (comfort row, written by SAMs). This is consistent
with §1.3: the burst is built programmatically in the unisolated TX path,
not mirrored through the dictionary. Whether this directory's store is the
same field store as stage C's (base `0x3C0E4A20`) is **not established** —
offsets overlap in range (e.g. `0xC4`) but identity was not proven.

### 2.3 Poll schedule as data — not found

No `{dest, table, period}` (or equivalent) table was found: the binding
directory is a field map (no periods, no destinations); the catalog blocks
(§1.3) carry no timing; no period constants (`3000/5000/10000` ms or
3/5/7/10 s in any unit) cluster near the equipment logic in the surveyed
clusters. The schedule is therefore engine/driver timing, **not isolated**
— the capture-derived tier list in `THERMOSTAT-PROTOCOL-MAP.md` remains
the authoritative schedule for the emulator.

---

## 3. Model database (commissioning equipment profiles)

### 3.1 Furnace and ODU: no model-string database exists

[FACT — negative with searched space stated] The full 15 MB flat image
contains **no** occurrence — ASCII, UTF-16BE, or UTF-16LE — of
`G80CTL1352422A2`, `G80CTL`, `G80C`, `HVA960GKA201`, `HVA960`, `HVA9`,
`GKA`, `CTL1`, or `VARIABLE SPEED FURNACE`. Additionally, all 90 zlib
streams in the resources filesystem region (`0x18810100–0x18D40577`) were
decompressed and searched: 0 hits. The only bare `HVA` hits are "HVAC" in
legal/UI text. A "Model Number" UI label exists at `0x182AE56C`.

**Inference:** the furnace and ODU are bus devices that self-report their
identity and configuration (their `0104` identities; furnace config table
`0316` is bound in the directory, §2.2). The thermostat needs no model
table for them — it reads what it needs over the bus. The commissioning
questions the author remembers are the thermostat *displaying / confirming*
the bus-reported identities — and asking for the one component that
cannot report anything: the passive indoor coil / air handler. That
database does exist:

### 3.2 The indoor-unit pattern database — geometry

[FACT — dual: array tiling arithmetic + code constants in
`FUN_180FC082`] Four arrays of model-pattern records sit back to back,
followed by the pattern strings in fixed 12-byte slots:

| Array | Base | Stride | Count | Record shape |
|---|---|---|---|---|
| CAT0 stride-8 | `0x182C48E0` | 8 | 74 | `{u32 str_ptr, float32 param}` |
| CAT1 stride-8 | `0x182C4B30` | 8 | 72 | `{u32 str_ptr, float32 param}` |
| CAT0 stride-14 | `0x182C4D70` | 14 | 54 | `{u32 str_ptr, u8 b4, u8 b5, float32 f1, float32 f2}` |
| CAT1 stride-14 | `0x182C5064` | 14 | 63 | `{u32 str_ptr, u8 b4, u8 b5, float32 f1, float32 f2}` |
| Strings | `0x182C53D8–0x182C5EF4` | 12/slot | — | NUL-padded patterns |

Dual verification: (i) tiling — 74×8 + 72×8 + 54×14 + 63×14 lands exactly
on `0x182C53D8`, the first string slot; (ii) the count getter
`FUN_180FC082` returns exactly `0x4A=74 / 0x48=72 / 0x36=54 / 0x3F=63` for
the four (category × format) combinations. The stride-8 arrays end with
an `OTHER` record (param 0) at CAT0[73] / CAT1[71]; the CAT1 stride-14
array ends with `Other` at [62].

Selectors [FACT: decompiled]:
- `FUN_180FC0DE` — category: a field-store short maps `0,1 → CAT0`,
  `2 → CAT1`.
- A mode byte (getter behind pool cell `0x180FC2F0`): `== 2` selects the
  stride-14 lists; otherwise the stride-8 lists.
- Four pool-cell pairs reference the four bases: `0x180FC2F8/0x180FC530`
  (CAT0-14), `0x180FC2FC/0x180FC53C` (CAT0-8), `0x180FC300/0x180FC534`
  (CAT1-14), `0x180FC304/0x180FC540` (CAT1-8) — two pool blocks
  (`0x180FC2xx`, `0x180FC5xx`) serving two code clusters at `0x180FC110`
  and `0x180FC308/3B4`.

Pattern families by string group: CAT0 stride-8 = `CVPM*/CSPV*/CVPVA*` +
`CAP**/CNP**/CSPH*`; CAT1 stride-8 = `EVM**/ESD**/EVD**` fan coils +
`EA*4X../EN*4X../EHD4X..` coils; CAT0 stride-14 = `CVA**/CAA**/CSA**`;
CAT1 stride-14 = `EVD5*/EVM5*/EAM5*/EAA5*/ESH5*`. Patterns use `*`
wildcards and `(A,D)` variant groups — matched as patterns, not literals.
Full verbatim extraction of all 263 records: `out/model_arrays.txt`.

Field semantics within stride-14 records [FACT for the values, INFERENCE
for the labels]: `b5` equals the nominal size in the pattern (18/24/30/36/
48/60 — thousand-BTU class); `b4 ∈ {0,1}` (flag, meaning unknown); `f2`
takes the same values as the stride-8 `param` for the same size class
(e.g. 0.10 for 18/24, 0.21 for 30, 1.93 for 60/61-class in the `*5`
families); `f1` is a second, smaller float (0.0333 / 0.0356 / 0.0386 /
0.0564 / 0.1543 / 0.1697 / 0.1930 observed). The physical quantity of
`param`/`f2` (and `f1`) is **not** tied to a named engineering unit by any
code usage found in this stage; within each family it scales with nominal
coil size and differs by construction family. Do not port a unit label.

### 3.3 the author's coil record — verbatim

the author's evaporator coil `EN(A,D)4X61` (Ion equipment-summary screen,
2026-11-26) is **CAT1 stride-8 index 70**:

```
entry @0x182C4D60:  str_ptr = 0x182C59A8 -> "EN(A,D)4X61"
                    param   = 0x3FD851EC = 1.69 (float32)
```

Neighbours in the same sub-list (verbatim from `out/model_arrays.txt`):

```
[65] @0x182C4D38  EA*4X60     param 0x3FF70A3D = 1.93
[66] @0x182C4D40  EN*4X60     param 0x3FACCCCD = 1.35
[67] @0x182C4D48  EHD4X60     param 0x3FB33333 = 1.40
[68] @0x182C4D50  EA*4X61     param 0x3FF70A3D = 1.93
[69] @0x182C4D58  ENH4X61     param 0x400147AE = 2.02
[70] @0x182C4D60  EN(A,D)4X61 param 0x3FD851EC = 1.69
[71] @0x182C4D68  OTHER       param 0x00000000 = 0
```

**The `061E` tie** [FACT: byte equality across two independent sources]:
the live-capture `061E` write payload is `0F 3F D8 51 EC 06 00 00 00`
(`THERMOSTAT-PROTOCOL-MAP.md`, constant in every capture of the author's
system). Bytes [1..4] are exactly the `EN(A,D)4X61` param bits
`0x3FD851EC`. **Inference (strong):** `061E` is not an opaque constant —
it carries the commissioned indoor coil's parameter to the ODU, and would
differ on a system with a different coil. Bytes [0] `0x0F`, [5] `0x06`,
[6..8] `0` remain unexplained. The code path that copies the parameter
into the `061E` frame was not isolated (§1); the field-store route in
§3.4 is the identified intermediate.

### 3.4 Lookup / selection code path

Accessors [FACT: decompiled; roles dual-pinned by pool-cell resolution +
caller data flow]:

- `FUN_180FC082` — entry count for the active (category × format) list.
- `FUN_180FC110(idx)` — pattern-string pointer for entry `idx` (handles
  both strides; element 0 in each format).
- `FUN_180FC3B4(idx)` — the entry's main float param (bits), via pool
  cell `0x18140E98` in the commit functions.
- `FUN_180FC308(idx)` — the entry's `f1` float (stride-14), via pool cell
  `0x18140EAC`.
- `FUN_180FC21C(idx)` / `FUN_180FC286(idx)` — bytes `b4` / `b5` (read from
  the stride-14 arrays unconditionally — see caveat below).
- `FUN_180FC4FE` — returns `0x29` (CAT0) / `0x27` (CAT1); semantics not
  established.
- (`FUN_180FC308`/`FUN_180FC3B4` decompiler output is partially mangled;
  their roles rest on the raw pool-cell values `0x18140E98 → 0x180FC3B4`,
  `0x18140EAC → 0x180FC308` and on caller usage. Instruction listing for
  `FUN_180FC3B4`: `out/listing_fc3b4.txt`.)

Commit [FACT — dual: decompiled + raw pool-cell resolution; cross-stage
corroboration: stage C's `out/setterB_calls.txt` line 475 independently
lists `FUN_18140BEA → field 0x59F`]:

- `FUN_18140BEA` writes the selected param (4 B) to field-store offset
  **`0x59F`** (setter `FUN_181592E4`, pool cell `0x18140EA0`). Index
  source: field `0x9A` (1 B, via getter `FUN_1815927c`) in the flagged
  path, else a lookup (`FUN_18140EF0`, mode-2 adjust `FUN_18140EB4`) into
  a caller-supplied table.
- `FUN_18140C80` writes the full selection: **`0x59F`** ← param (4 B);
  **`0x1C7C`** ← `b4` (1 B); **`0x1C7D`** ← `b5` (1 B); **`0x1C7E`** ←
  `(u16)(f1 × 65535.0)` (2 B). The scale constant `DAT_18140EB0 =
  0x477FFF00 = 65535.0` [FACT: raw read]. Its non-flagged path reads a
  stride-10 record `{u8 b4, u8 b5, float f1, u32 param}` — exactly a
  stride-14 record minus its string pointer, i.e. the same database in
  pointer-free form.

Caveat (honest): `FUN_180FC21C/286` read the stride-14 arrays regardless
of the mode byte, while counts/strides elsewhere are mode-dependent; how
byte fields are sourced for stride-8 (the author-class) selections is not
fully resolved statically. The wildcard **matcher loop** itself (the code
that compares a candidate model string against patterns) is **not
isolated**; the pattern getter's callers are the setup-wizard functions
`FUN_181EBA74` and `FUN_181ECF6A` (region `0x181Exxxx`, computed calls)
and the dictionary-commit function `FUN_180AAF64` (writes identity fields
`0x768, 0x766, 0x11B6, 0x14D5`). All FC-cluster references:
`out/xref_fc_callers.txt`.

---

## 4. Control constants near equipment-command logic (goal 4)

**Not isolated in this slice.** No staging timers, min on/off times, or
changeover/defrost parameters were tied to equipment-command code usage —
that logic lives in the control-decision core (stage E) and/or behind the
unisolated TX path. The only equipment-adjacent constants established
here are:

- `DAT_18140EB0 = 65535.0` (`0x477FFF00`) — fixed-point scale for the
  committed `f1` field `0x1C7E` (§3.4). [FACT: raw read + decompiled use]
- The burst payload constants (`0305` byte [11] `0x78`, `0612`'s
  `22B8…`, `061E`'s frame bytes) are **not** stored verbatim in flash
  (§1.3) — they are assembled at runtime. [FACT: byte scans]

## 5. Thermostat-side behaviour on equipment silence (goal 5)

**Not isolated.** No retry counter / timeout constant tied to equipment
RX was found in the surveyed clusters or the data structures above. The
capture-side observation stands (protocol map: the thermostat carries on
polling through ~0.6 % unanswered reads); the firmware-side mechanism is
unresolved. The equipment-side comm-fault timeout is out of scope for
this image by construction (it lives in the furnace/ODU firmware).

## 6. Not-isolated list (explicit)

1. ABCD frame-construction / transmit-queue function; its call sites
   toward `0x44`/`0x53`; the UART (SCIF) driver.
2. The cyclic poll schedule as data (concluded: not present as a table
   in any structure found; engine timing not isolated).
3. The wildcard matcher loop over the model patterns (getters and commit
   identified; the compare loop is not).
4. The consumer of field `0x59F` — i.e. the code that copies the coil
   param into the `061E` frame (byte-identity evidence only).
5. Physical semantics (engineering units) of the model-DB floats
   `param`/`f2` and `f1`, and of stride-14 byte `b4`.
6. Staging / min-on-off / changeover / defrost constants on the
   thermostat side (stage E slice).
7. Thermostat-side silence handling (retries/timeouts) in firmware.
8. Byte-field sourcing for stride-8 model selections (§3.4 caveat).
9. Whether the binding directory's store is stage C's field store
   (offset-space overlap noted, identity unproven).
10. `FUN_180FC4FE` return values (41/39 per category) — meaning unknown.

## 7. Porting section — findings mapped to protocol-map gaps G1–G11

- **G1 (comm-fault timeout): STAYS OPEN.** Confirmed equipment-side;
  nothing in the thermostat image can close it. The controlled reseat
  test remains the only route.
- **G2 (exact serial digits): cannot close.** Serials are runtime data;
  this stage confirms the firmware carries no per-unit identity strings
  at all (§3.1) — read the serial off the About screen / sticker as
  planned.
- **G3 (real 3B02/3B03 contents): cannot close.** The binding directory
  contains no `3B02/3B03` records (§2.2) — the thermostat's own
  dictionary does not model a SAM's zone tables.
- **G4 (constant payload semantics): PARTIALLY CLOSED — `061E` only.**
  `061E` bytes [1..4] = the commissioned indoor coil's float param from
  the model database (`0x182C48E0` region; the author: `EN(A,D)4X61` @
  `0x182C4D60` → `0x3FD851EC` = 1.69), committed to field `0x59F` by
  `FUN_18140BEA`/`FUN_18140C80`. For the emulator: `061E` must be
  built from the commissioned coil, not replayed as a universal
  constant; on the author's system the replay value stands. All other G4
  items (`030A`, `0403/0409`, `0610/0612`, `0305[11]=0x78`, `060B/0414`
  byte, `4202` length) remain open; note `0610/0612/061A/0305` have no
  binding records and no verbatim payloads in flash (§1.3, §2.2) —
  they are assembled in the unisolated TX path.
- **G5 (who runs SystemInit, when): cannot close from this slice.**
  The SystemInit initiator is part of the unisolated bus engine (§1).
- **G6 (real SAM01 write dialect): cannot close.** That dialect lives
  in the SAM's firmware, not this image; nothing here contradicts
  stage C.
- **G7 (identity of node 0x93): cannot close.** No reference to a
  third bus peer's identity exists in the structures found.
- **G8 (part-load behaviour): cannot close from this slice.** Demand
  shaping is control-core (stage E). This stage adds one boundary
  fact: the demand table `0305` is not dictionary-mirrored (§2.2), so
  part-load values are computed in code, not table-driven.
- **G9 (exception behaviour): cannot close.** Equipment-side responses;
  the thermostat image cannot answer it. The planned probe session
  remains the route.
- **G10 (clock contents of 0202/0203): cannot close from this slice.**
  `0202/0203` have no binding records (§2.2) — thermostat-owned,
  assembled in the unisolated TX path; no field layout was found in
  data. The known-clock capture remains the route.
- **G11 (wizard/commissioning variants): PARTIALLY CLOSED.** The
  commissioning equipment-identification internals are now known:
  furnace/ODU are identified over the bus (`0104`; no firmware model
  DB — §3.1), while the indoor coil/air handler is selected by
  wildcard-pattern match against the four lists at
  `0x182C48E0/0x182C4B30/0x182C4D70/0x182C5064` (263 records, verbatim
  in `out/model_arrays.txt`), and the selection is committed to field
  store `0x59F / 0x1C7C / 0x1C7D / 0x1C7E` by `FUN_18140BEA` /
  `FUN_18140C80` (§3.4). For the emulator: a recommissioning that
  changes the coil changes `061E` (see G4) — the rest of the wizard's
  bus-scan sequence (46/5F/69/60/61 sweeps) was not isolated in code
  and still needs the full installer-run capture if it ever matters.

## Appendix — stage D artifacts (`firmware-re/stageD/`)

- `proj/` — stage D's own copy of the Ghidra project (stage B/C untouched).
- `scripts/` — stage C scripts + new `XrefDump.java`.
- `run_smoke.sh`, `run1.sh`…`run9.sh` + `run*.log` — all runs `EXIT=0`.
- `out/model_arrays.txt` — all 263 model-DB records, verbatim.
- `out/binding_directory.txt` — all 385 binding records, verbatim.
- `out/xref_fc_callers.txt` — reference enumeration for the model-DB
  accessor cluster.
- `out/cellusers_model.txt` — functions using the four array-base pool
  cells (`FUN_180FC110/21C/286/308/3B4`).
- `out/listing_crc.txt` — instruction listing of `FUN_180EA704`
  (dual verification of the fixed-30-byte CRC).
- `out/listing_fc3b4.txt` — instruction listing of `FUN_180FC3B4`.
- `out/decomp_*.c` — decompiles incl. `FUN_18140C80`, `FUN_18140BEA`,
  `FUN_180AAF64`, `FUN_181EBA74`, `FUN_181ECF6A`.
- `out_cluster_ea/`, `out_cluster_a7/`, `out_cluster_fc/`,
  `out_cluster_70/` — cluster surveys (12 / 26 / 10 / 139 functions).
- `scan1.py` — signature/pool scan script used for §1–§3 raw checks.
