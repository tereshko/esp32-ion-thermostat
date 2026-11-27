# Firmware Analysis — Stage P: the threshold-table producer FUN_181f21d4, its twin FUN_181f07ec, and our installation's equipment class word

Stage P, 2026-11-26. Scope (the author's third wave): complete specification
of `FUN_181f21d4` (the producer of the staging threshold tables
`0xFFF8CCC4` / `0xFFF8CCDC` / `0xFFF8CD04`), of its twin `FUN_181f07ec`
(tables `0xFFF8CC04` / `0xFFF8CC1C` / `0xFFF8CC34`), of every input they
consume, of the equipment class-word encoding, and — the practical
question — what class word OUR installation (G80CTL1352422A2 2-stage
gas furnace + HVA960GKA201 variable-speed AC + EN(A,D)4X61 coil,
single zone) runs, with our threshold tables computed.

Method: fresh Ghidra decompilation of both producers, all four helper
functions, the post-processor `FUN_181f3f44`, the ingestion functions
`FUN_181f59e0` / `FUN_181f54e8` / `FUN_181f5e9a`, the tail functions
`FUN_1804e9ac` / `FUN_1804ed70`, and the category mappers
`FUN_180e2a80` / `180e2ae8` / `180e2afc` / `180e2b1a` / `180e2e34`;
instruction-level verification from listings for the prologue, the
fallback, the shared tail, the `0x92C2`/`0x85C2` selector switches, the
string-class zero/fill loops, the twin's head, and `FUN_181f159c`;
pool-cell resolution against the raw image (every `DAT_`/`PTR_`
constant resolved from `flat_trim.bin`, base `0x18040000`); dual
verification of cell censuses (Ghidra `UsersOf` vs independent raw
BE32 scan — counts agree exactly); dictionary cells resolved to
(table, device-class, member) triples through the stage-F group table
`firmware-re/stageF/out/group_table.txt`; store fields resolved
through the stage-F descriptor table (key = store offset).
Intermediates: `firmware-re/stageP/` (`out/decomp/`, `out/listing/`,
`out/pools_*.txt`, `out/usersof.txt`, `out/classhunt.txt`,
`out/pools_ingest.txt`, `cellmap.py`, `resolve.py`).

Labels: **[FACT]** = decompiled/listing-verified or dual-verified.
**[I]** = inference, marked as such. Signed decompiler renderings of
class words are converted to unsigned hex throughout
(e.g. `−0x7dbf` = `0x8241`); all class comparisons in the listing are
`extu.w` + `movi20` + `cmp/eq` — unsigned 16-bit equality [FACT,
listing `lst_epi.txt`/`lst_main.txt`].

---

## 0. Headline results

1. **Both producers are now specified completely** — every branch,
   every table entry, every input cell. §2 (FUN_181f21d4, 18 compared
   class words + fallback + unmatched default), §3 (twin, 11 class
   words + gate), §4 (the lookup helper FUN_181f159c and its 6×3
   table at `0x1830B094`).
2. **The "field store" is one flat byte array at `0x3C0E4A20`**
   (≤ 0x2000 B), accessed only through getter `FUN_1815927c` /
   setter `FUN_181592e4` with **byte offsets**. The class words are
   store bytes **[1..2]** (CC52) and **[3..4]** (CBF4); R's byte is
   store **[8]**; the twin's byte is store **[0x12]**. §1.
3. **Every dictionary input is resolved** to a (table, device-class,
   member) triple (§5.4). The producers do not read "properties" —
   they read per-device-class parameter sets of bus tables
   `0504` (classes 0x50/0x54), `0606`/`0607` (classes 0x51/0x56/0x57/
   0x5B), `030A` (classes 0x3E/0x40), `0402` (classes 0x3E/0x40/0x42),
   and one 125-byte parameter blob in the `060E` object of device
   class **0x52 — the canonicalized class of bus address 0x53, i.e.
   of OUR ODU** (§2.6).
4. **Class-word encoding** (§6): bit `0x8000` always set in compared
   values; bits `0x7C00` = family field (the shared tail tests
   `== 0x4000` for the parameterized classes); bit `0x0100` = "second
   table (CCDC) present" (proven by the tail's conditional processing,
   §2.7); low nibble = breakpoint count − 1 (`CC5A = (CC52 & 0xF)+1`).
   A separate mapper cluster (`FUN_180e2a80`…) collapses class words
   into a **category byte at dictionary cell `0x3C12A8D5`**: {0x92C1,
   0x91C1}→1, {0x92C2, 0x91C2}→2 or 3, {0x85C2}→4, {0xA2C2, 0xA1C2}→5,
   {0x8241, 0x8141}→7, {0x8242, 0x8142}→8. Equipment-type *names* for
   the families are **not in the image** (§6.3, §8).
5. **Our class word is NOT derivable from bus captures** (§7.2): the
   class words never appear on the wire — the 0104 payloads are pure
   ASCII identity, the binding chunks that cover store offsets 0–4
   carry internal device-object variables, not wire bytes, and no
   flash table maps model strings to class words for the furnace/ODU
   (stage D/K: no such database exists; only the coil has one).
   §7.4 gives the **exact snapshot targets** (RAM addresses) and the
   bounded candidate set.
6. **Our tables, bounded** (§7.5): under the stated hypotheses
   (X = 60.0, store[8] = 60 → R = 5.0), the plausible classes
   0x8141/0x91C1 give CCC4 = {0, 60000, 0, 0}, CCDC = {0, 59486.2, 0,
   0}, CD04 = {5.0, …}; the full sensitivity table over
   store[8] ∈ {24, 36, 48, 60, 72} is in §7.5. The near-equality
   CCC4[1] ≈ CCDC[1] ≈ 60000 for a matched 5-ton system is a
   consistency check, not a proof [I].

---

## 1. The field store and the accessor pair

[FACT] Getter `FUN_1815927c(offset, dest, len, flag)` (decompiled,
pools resolved): bounds-checks `offset+len` against the store size
`*(uint*)*0xFFF877DC`; locks mutex `0xFFF8AD40` (`FUN_180bc2d2`);
memcpy (`FUN_1823d404`) from **store base `0x3C0E4A20`**; if
`flag ≠ 0`, post-copy hook `FUN_18166394(offset, len, dest)` (stage
F's descriptor validator dispatcher — the producers always pass
flag = 1, so every read is sanitized against the field's descriptor);
unlock `FUN_180bc36a`. Returns 0 ok / 1 fail.

[FACT] Setter `FUN_181592e4(offset, src, len)` (stage I decompile,
re-verified): gated by byte `*0x3C12E168 == 0`; memcmp
(`FUN_1823d3d8`) — writes only on change; on write it bumps a
sequence cell (`FUN_181593d4`, pool `0x181593dc`) and marks dirty
pages in a bitmap at **`0x3C0E6A20`** = store base + 0x2000 (so the
store is ≤ 8192 B); page size from the same size struct.

[FACT] The store base `0x3C0E4A20` occurs in exactly 3 image cells
(raw BE32 scan = Ghidra refs, dual-verified): `0x181593f4` (getter),
`0x18159688`, `0x181598f0` (two further accessor-module functions;
one of them, at `FUN_181598c6`'s neighborhood, is a 34-byte
"write u16 field" wrapper around the setter — decompiled stage P).

[FACT] Consequence: every "field N" in earlier stages is a **byte
offset into this one array**. The producers' reads:

| reader | offset | len | destination |
|---|---|---|---|
| FUN_181f21d4 | 0x2F | 2 | CC56 (`0xFFF8CC56`) |
| FUN_181f21d4 | 0x31 | 2 | CC58 (`0xFFF8CC58`) |
| FUN_181f21d4 | 1 | 2 | **CC52 (`0xFFF8CC52`) — class word A** |
| FUN_181f21d4 | 8 | 1 | **R byte** → R = byte / 12.0 |
| FUN_181f07ec | 0x2D | 2 | CBF8 (`0xFFF8CBF8`) |
| FUN_181f07ec | 3 | 2 | **CBF4 (`0xFFF8CBF4`) — class word B** |
| FUN_181f07ec (0x59/0x5B branches) | 0x12 | 1 | size byte |
| FUN_181f07ec (0x39 branch) | 0xCE | 2 | base value (descriptor: 450–2000) |
| FUN_181f07ec (0x39 branch) | 0xCEE | 16 | 8 zone ushorts |
| FUN_181f3f44 | 0x118 | 6 | stage-count/limit bytes [0x118..0x11D] |

[FACT] Descriptor coverage (stage F descriptor table; key = store
offset): offset 1 (len 2, u16 validator `FUN_1816684c`, range
0–65535, **default bytes at `0x182F6D1A` = `00 00`**); offset 3 (same
descriptor shape, same default 0); offset 8 (len 1, range **0–72**,
default byte at `0x182F6D21` = **24**); offset 0x12 (len 1, 0–255,
default 0); offset 0x2D (len 2, signed validator, 0–200); offset
0x2F (len 2, signed, −21–8888); offset 0x31 (len 2, signed, 0–8888);
offset 0xCE (len 2, **450–2000**); offsets 0x118–0x11B (len 1,
**1–5** — stage counts); 0x11C/0x11D (len 1, 0–127). The factory
default of both class words is therefore **0x0000** — the running
values are written after commissioning (§7.2).

[FACT] Group-table coverage (stage F parse, phase-corrected in stage
P — see §8 note on stage D): the binding chunks tile the store head
contiguously: (table `0104`, class 0x21) covers store 0–4, class
0x22 covers 5–9 (so **R's byte at store[8] is byte 3 of the
(0104, 0x22) chunk**), class 0x24 covers 15–19 (twin byte at 0x12 =
chunk byte 3), class 0x40 covers 44–47 (CBF8 at 0x2D = chunk bytes
1–2), class 0x42 covers 48–51 (CC58 at 0x31 = chunk bytes 1–2; CC56
at 0x2F straddles the 0x40/0x42 boundary — readers treat the head as
a flat struct and the chunks tile contiguously, so the read is
coherent). The chunk contents are internal device-object variables
written by the binding engine, **not** wire payload bytes: the 0104
wire payload bytes 23–47 are zero for every device in our captures
while these fields are demonstrably nonzero in operation [FACT,
captures §7.1]. "Class" here is the binding's device-class byte
(stage F: canonicalizer `FUN_180c6ebe` maps bus addresses to
classes, e.g. 0x44→0x40, 0x53→0x52); it is **not** a payload offset.

---

## 2. FUN_181f21d4 — complete specification

Body 6390 B, entry `0x181f21d4`. Sole caller: ingestion dispatcher
`FUN_181f5d08` (call at `0x181f5d1c`, UsersOf) [FACT]. It writes:

- `CCC4[0..5]` @ `0xFFF8CCC4`, `CCDC[0..5]` @ `0xFFF8CCDC`,
  `CD04[0..5]` @ `0xFFF8CD04` — float breakpoint tables (only
  indices 0–3 are ever written by the analytic branches; the string
  branches address 0–5);
- `CC5A` @ `0xFFF8CC5A` (byte, active breakpoint count),
  `CCF4[0..3]` @ `0xFFF8CCF4` (per-index valid flags),
  `CC5B[0..3]` @ `0xFFF8CC5B` (per-index source ids);
- the scratch profile block `0xFFF8C75C`–`0xFFF8C7AC` (floats) for
  the parameterized classes, consumed downstream (§2.8);
- for the string classes additionally the auxiliary arrays
  `C7B0/C7C8/C7E0/C7F8/C810/C828/C840/C858` @ `0xFFF8C7B0`….

Notation below: **R** = store[8] / 12.0; **X** = the clamped float
of §2.1; **K** = 34.286 × (137.0 + 3.5·X) (constants `0x420924DD`,
`0x43090000`, `0x40600000` from pools `0x181f24bc`/`24c0`/`24c4`);
**U1** = `*(float*)0xFFF8C754`, **U2** = `*(float*)0xFFF8C758`;
"dict cell" = a `0x3C0Dxxxx` dictionary-object buffer, resolved in
§5.4. All float constants below are pool-verified.

### 2.1 Prologue (listing-verified)

1. getter(0x2F → CC56), getter(0x31 → CC58), getter(1 → CC52) —
   each (offset, dest, 2, flag=1). Lock `FUN_180bc05a`; **CC54 =
   mirror byte `0xFFF830AD`**; unlock `FUN_180bc06e`.
2. **X**: lock; validity byte copied from `0xFFF820F5` (1 B,
   memcpy); `X = *(float*)0xFFF820F8`; unlock. Clamp: if X < 12.0 →
   12.0; if X > 61.0 **or validity ≠ 1** → 61.0 (constants
   `0x181f248c` = 12.0, `0x181f2490` = 61.0; `fcmp/gt` verified in
   listing).
3. **Fallback test**: if CC52 == `0x8000` (unsigned) **or** CC54 == 0
   **or** CC54 == 4 → fallback (§2.2) and exit via `0x181f3ee4`
   (pure epilogue), **skipping the shared tail**.
4. General prologue: `CC5A = (CC52 & 0xF) + 1`; CCF4 = {1,0,0,0};
   CC5B = {0,1,2,3}; CCC4[0] = CCDC[0] = 0.0; **CD04[0] = R**
   (getter(8, buf, 1, 1); float conversion + `fdiv` by 12.0 verified
   in listing); CCC4[1..3] = CCDC[1..3] = 0.0 defaults. **CD04[1..5]
   are never written anywhere in this function** [FACT, decompile +
   listing].

### 2.2 Fallback (CC52 == 0x8000, or CC54 ∈ {0, 4})

CC5A = 1; CCF4[0] = 1, CC5B[0] = 0 (entries 1–3 are not written on
this path — they keep the general-prologue values only if reached;
on the fallback path the branch is taken before the general
prologue, and the listing shows only CCF4[0]/CC5B[0] written);
CCC4[0] = CCDC[0] = CD04[0] = 0.0; exit. No tail calls. [FACT,
listing `lst_epi.txt`: `movi20 #0x8000; cmp/eq` on `extu.w`, exit
pool `0x181f24b0` → `0x181f3ee4`.]

### 2.3 Analytic branches (R/K/U formulas)

All end by jumping to the shared tail `0x181f3ec4` (§2.7). Entries
not mentioned keep the §2.1 defaults (CCF4/CC5B entries [i] = 1/i
where the branch activates index i; CCC4[3] = CCDC[3] = 0.0 and
CCF4[3] = 0 in all analytic branches).

| class word(s) | CCC4 | CCDC |
|---|---|---|
| `0x8241`, `0x92C1` | [1] = R × 12000.0 | all 0 |
| `0x8141`, `0x91C1` | [1] = R × 12000.0 | [1] = R × K |
| `0x8242`, `0xA2C2` | [1] = R × 12000.0 × U1; [2] = R × 12000.0 × U2 | all 0 |
| `0x8142`, `0xA1C2` | as `0x8242` | [1] = R × K × U1; [2] = R × K × U2 |
| `0x92C2` | selector form (§2.4), scale 12000.0 | [1] = [2] = 0 |
| `0x91C2` | selector form (§2.4), scale 12000.0 | selector form (§2.4), scale K |
| `0x85C2` | selector form (§2.4), scale 12000.0, dict set B | selector form (§2.4), scale **12000.0**, dict set B |

12000.0 = pool `0x181f24b4` (`0x463B8000`) [FACT].

### 2.4 The selector form (classes 0x92C2 / 0x91C2 / 0x85C2)

Four dictionary ushorts are read (lock-bracketed) and scaled by
1/1000.0 (pool `0x181f2800` = 1000.0) into scratch cells:

- set A (0x92C2/0x91C2): `0x3C0D8060`→C774, `0x3C0D805C`→C76C,
  `0x3C0D805E`→C778, `0x3C0D805A`→C770 — table `0504`, class 0x50,
  members 727/725/726/724 (§5.4);
- set B (0x85C2): `0x3C0D8068`→C774, `0x3C0D8064`→C76C,
  `0x3C0D8066`→C778, `0x3C0D8062`→C770 — table `0504`, class 0x54,
  members 731/729/730/728.

Min-clamps (constant `0x181f2820` = 0.0001): if C76C < 0.0001 →
C76C = C774; if C770 < 0.0001 → C770 = C778.

Selection by a **selector byte**: for CCC4 the byte is
`0xFFF8C74D`; for CCDC (0x91C2/0x85C2) it is `0xFFF8C74E`. Mapping
(listing-verified switch): selector ∈ {4, 3, 2} **or any other
value** → use the (C774, C778) pair; selector ∈ {1, 0} → use the
(C76C, C770) pair. Then `table[1] = R × scale × first`,
`table[2] = R × scale × second`. CCF4[1] = CCF4[2] = 1. [FACT]

### 2.5 Parameterized branches (raw dictionary copies + scratch profile)

These branches copy **floats and ushorts verbatim** from the
per-class parameter sets of tables `0606` (floats) and `0607`
(ushorts) into CCC4/CCDC and the scratch block. Scratch target
layout (offsets from `0xFFF8C75C`): the block holds two groups —
group-2 cells C75C/C760/C77C/C780/C784/C788/C78C/C790 and group-1
cells C764/C768/C794/C798/C79C/C7A0/C7A4/C7A8. "u16→f" = ushort read
as float, no scaling. All cell→(table, class, member) resolutions
in §5.4.

**Class `0x8AA2`** (parameter set: `0606`/`0607` class 0x51):
CCDC[1] = CCDC[2] = 0; eight scratch cells zeroed (C764, C768,
C7A8, C7A0, C798, C7A4, C79C, C794); CCC4[1] = f32(dict `0x3C0D8110`),
CCC4[2] = f32(dict `0x3C0D8114`); with A = u16(dict `0x3C0D8192`),
B = u16(dict `0x3C0D8190`): C75C = A; C790 = A × 1.425; C788 =
A × 1.425; C780 = A × 1.25; C760 = B; C78C = B × 1.425; C784 =
B × 1.425; C77C = B × 1.25 (constants `0x3FB66666` = 1.425,
`0x3FA00000` = 1.25).

**Class `0x89A2`**: everything `0x8AA2` does (same CCC4 sources,
same group-2 scratch), **plus** CCDC[1] = f32(dict `0x3C0D8108`),
CCDC[2] = f32(dict `0x3C0D810C`), **plus** group-1 scratch with
multiplier 1.14 (`0x3F91EB85`): with A′ = u16(dict `0x3C0D8196`),
B′ = u16(dict `0x3C0D8194`): C764 = A′; C768 = B′; C7A8 = A′ × 1.14;
C7A0 = A′ × 1.14; C798 = A′; C7A4 = B′ × 1.14; C79C = B′ × 1.14;
C794 = B′.

**Class `0x8EA2`** (parameter set class 0x56): CCDC[1] = CCDC[2] =
0; eight scratch cells zeroed; CCC4[1] = f32(dict `0x3C0D8138`),
CCC4[2] = f32(dict `0x3C0D8128`); eight u16→f conversions, **no
multipliers**: C75C ← `0x3C0D819E`, C760 ← `0x3C0D81B4`, C788 ←
`0x3C0D819A`, C784 ← `0x3C0D81A8`, C780 ← `0x3C0D81AA`, C77C ←
`0x3C0D819C`, C790 ← `0x3C0D81A6`, C78C ← `0x3C0D8198`.

**Class `0x8DA2`** (parameter set class 0x56): CCC4[1] = f32(dict
`0x3C0D8138`), CCC4[2] = f32(dict `0x3C0D8128`); CCDC[1] = f32(dict
`0x3C0D813C`), CCDC[2] = f32(dict `0x3C0D812C`); group-1 scratch
(u16→f, no multipliers): C764 ← `0x3C0D81A4`, C768 ← `0x3C0D81B6`,
C7A0 ← `0x3C0D81AE`, C79C ← `0x3C0D81A2`, C798 ← `0x3C0D81B0`,
C794 ← `0x3C0D81B2`, C7A8 ← `0x3C0D81AC`, C7A4 ← `0x3C0D81A0`;
group-2 scratch identical to `0x8EA2`'s eight conversions.

**Helper-dispatched classes** (dispatch listing-verified at
`0x181f3e70`–`0x181f3ec2`; each helper call is followed by
`bra 0x181f3ec4`):

- `0xC6A2` → `FUN_181f169c` (parameter set class 0x57): CCDC[1] =
  CCDC[2] = 0; group-1 cells zeroed; CCC4[1] = f32(dict
  `0x3C0D8154`), CCC4[2] = f32(dict `0x3C0D8148`); group-2 u16→f:
  C75C ← `0x3C0D81BE`, C760 ← `0x3C0D81D4`, C788 ← `0x3C0D81BA`,
  C784 ← `0x3C0D81C8`, C780 ← `0x3C0D81CA`, C77C ← `0x3C0D81BC`,
  C790 ← `0x3C0D81C6`, C78C ← `0x3C0D81B8`.
- `0xC5A2` → `FUN_181f18dc` (set class 0x57): CCC4 as `0xC6A2`;
  CCDC[1] = f32(dict `0x3C0D8158`), CCDC[2] = f32(dict
  `0x3C0D814C`); group-2 as `0xC6A2`; group-1 u16→f: C764 ←
  `0x3C0D81C4`, C768 ← `0x3C0D81D6`, C7A0 ← `0x3C0D81CE`, C79C ←
  `0x3C0D81C2`, C798 ← `0x3C0D81D0`, C794 ← `0x3C0D81D2`, C7A8 ←
  `0x3C0D81CC`, C7A4 ← `0x3C0D81C0`.
- `0xCAA2` → `FUN_181f1c38` (set class 0x5B): CCDC[1] = CCDC[2] =
  0; group-1 cells zeroed; CCC4[1] = f32(dict `0x3C0D8174`),
  CCC4[2] = f32(dict `0x3C0D8170`); group-2 u16→f: C75C ←
  `0x3C0D81DE`, C760 ← `0x3C0D81F4`, C788 ← `0x3C0D81DA`, C784 ←
  `0x3C0D81E8`, C780 ← `0x3C0D81EA`, C77C ← `0x3C0D81DC`, C790 ←
  `0x3C0D81E6`, C78C ← `0x3C0D81D8`.
- `0xC9A2` → `FUN_181f1e78` (set class 0x5B): CCC4 as `0xCAA2`;
  CCDC[1] = f32(dict `0x3C0D816C`), CCDC[2] = f32(dict
  `0x3C0D8168`); group-2 as `0xCAA2`; group-1 u16→f: C764 ←
  `0x3C0D81E4`, C768 ← `0x3C0D81F6`, C7A0 ← `0x3C0D81EE`, C79C ←
  `0x3C0D81E2`, C798 ← `0x3C0D81F0`, C794 ← `0x3C0D81F2`, C7A8 ←
  `0x3C0D81EC`, C7A4 ← `0x3C0D81E0`.

All four helpers also set CCF4[1] = CCF4[2] = 1, CC5B[1..2] = 1, 2,
CCF4[3] = 0, CC5B[3] = 3, CCC4[3] = CCDC[3] = 0.0 [FACT,
decompilations + pools in `out/pools_rest.txt`, cells mapped by
`cellmap.py`].

Note: stage L §4's prose summary of the A2 classes differs from the
above; the stage-P reading is confirmed by **two independent
decompilations** (stage L's own and stage P's fresh one agree
instruction-for-instruction in structure) plus pool resolution —
the decompilations govern.

### 2.6 String classes `0xC295` / `0xC195` — the 125-byte blob

Both classes: memcpy 125 bytes from dictionary cell **`0x3C0D8273`**
(lock-bracketed, `FUN_1823d404`) to the stack. Resolution (§5.4):
`0x3C0D8273` is inside the object for **table `060E`, device class
0x52, member 893** — class 0x52 is the canonicalized class of bus
address `0x53` (stage F), i.e. **the blob lives in our ODU's 060E
object**; the copy starts one byte into member 893's buffer and
reads the contiguous object memory. The class words `0xC295`/
`0xC195` themselves have `(CC52 & 0x7C00) == 0x4000`, which arms the
post-processor `FUN_181f3f44` in the shared tail (§2.7).

Zero phase (listing-verified): 14 float arrays × 6 entries set to
0.0 — CCC4, CCDC, CC64 (`0xFFF8CC64`), CC94 (`0xFFF8CC94`), CC7C
(`0xFFF8CC7C`), CCAC (`0xFFF8CCAC`), C7B0, C7C8, C7E0, C7F8, C810,
C828, C840, C858.

Fill loop, i = 1..CC5A−1 (= 1..5, since the low nibble of
0xC295/0xC195 is 5): CCF4[i] = 1; CC5B[i] = i; and float
conversions from the blob (unsigned conversion — negative int32
values get +4294967296.0, constant `0x4F800000`):

**Blob layout — pinned and dual-verified** (decompiler frame
offsets + two listing data points: the BE u16 assembled from blob
bytes 105–106 → C7E0[1] at `0x181f3e00`–`0x181f3e20`, and from
115–116 → C7F8[1] at `0x181f3e22`–`0x181f3e52`; u16s are BE,
`shll8` + `or`):

| blob bytes | type | → array (0xC295) | → also (0xC195 only) |
|---|---|---|---|
| 0–2 | 3 header bytes | — (not read) | — |
| 3–22 | int32[5] BE | CCC4[1..5] | |
| 23–32 | u16[5] BE | C810[1..5] | |
| 33–42 | u16[5] BE | C828[1..5] | |
| 43–52 | u16[5] BE | C840[1..5] | |
| 53–62 | u16[5] BE | C858[1..5] | |
| 63–64 | 2 gap bytes | — | — |
| 65–84 | int32[5] BE | — | CCDC[1..5] |
| 85–94 | u16[5] BE | — | C7B0[1..5] |
| 95–104 | u16[5] BE | — | C7C8[1..5] |
| 105–114 | u16[5] BE | — | C7E0[1..5] |
| 115–124 | u16[5] BE | — | C7F8[1..5] |

Total 125 ✓. For `0xC295`, blob bytes 63–124 are copied but unused
by the fill loop. CD04 is **not** zeroed or filled by the string
branches — CD04[0] = R from the prologue stands.

### 2.7 Shared tail @ `0x181f3ec4` and `FUN_181f3f44`

[FACT, listing `lst_epi.txt` lines ~3005–3018] Every non-fallback
path reaches `0x181f3ec4`, which executes, in order:

```
jsr FUN_1804e9ac
jsr FUN_1804ed70
CC52 & 0x7C00 == 0x4000 ?  →  jsr FUN_181f3f44
fall through to epilogue 0x181f3ee4
```

- `FUN_1804e9ac` (862 B): rebuilds the working arrays **CC64**
  (from CCC4) and **CC94** (from CCDC) — zeroes 6 entries, refills
  [1..CC5A−1] through per-index accessor calls, invalidates entries
  whose adjusted demand test fails, and computes the fractional
  stage outputs `0xFFF8C8AC` / `0xFFF8C8B4` by linear interpolation.
  It processes the CCDC-derived array **only if CC52 bit `0x0100`
  is set**, and special-cases `(CC52 & 0x7C00) == 0x800` together
  with bit `0x0020` (pools: `0x1804ec68` → CC5A, `0x1804ec80` →
  CC52, `0x1804ec50` → CC64, `0x1804ec58` → CC94).
- `FUN_1804ed70` (1216 B): the same for **CC7C** (from CCC4) and
  **CCAC** (from CCDC), except the per-index source is chosen by
  the **selector bytes** — `0xFFF8C74D` selects among 5 accessor
  functions for CC7C entries, `0xFFF8C74E` likewise for CCAC
  (pools `0x1804f02c` → C74D, `0x1804f044` → C74E); fractional
  outputs `0xFFF8C8A8` / `0xFFF8C8B0` / `0xFFF8C8B8`. This is the
  downstream consumer of the selector bytes that §2.4 reads.
- `FUN_181f3f44` (only for `(CC52 & 0x7C00) == 0x4000` — among
  compared classes: only `0xC195`/`0xC295`): a min/max clamp
  post-processor for the string classes. It re-copies the same
  125-byte blob from `0x3C0D8273` (pool `0x181f4204`), reads store
  bytes [0x118..0x11D] via the getter, and reads X from
  `0xFFF820F8` with validity byte `0xFFF820F5` — **without the
  12/61 clamp; invalid → X := 65.0** (pool `0x181f421c`). It
  maintains two state bytes at dictionary `0x3C12EC65`/`0x3C12EC66`
  (adjacent to the sys_ctrl FSM state byte `0x3C12EC68`, stage G)
  by comparing X against store[0x11C] − EC65 and store[0x11D] +
  EC66, and computes stage-count bytes **CBB1–CBB4**
  (`0xFFF8CBB1`–`0xFFF8CBB4`) from store[0x118..0x11B] and blob
  bytes 1, 2, 63, 64 with float limits from `0xFFF8C8A8` (→ CD0C
  @ `0xFFF8CD0C`), `0xFFF8C8B0`, `0xFFF8C8B8`; results are
  published to mirror bytes `0xFFF83E80`–`0xFFF83E83`. (Stage L:
  `FUN_1814c9ba` sets CC5A = CBB1+1 / CBB3+1 / 2 — CBB1/CBB3 are
  alternate stage-count sources for these classes.)

**Unmatched class word** (none of the 18 compared values, not the
fallback): the §2.1 defaults stand (CCC4 = CCDC = {0,0,0,0},
CD04 = {R,0,0,0}, CC5A from the low nibble) and the tail still
runs. [FACT]

### 2.8 Who consumes the scratch block

[FACT] `FUN_181f5e9a` (2522 B, ingestion family) branches on CC52:
for `0x89A2`/`0x8AA2` and for `0x8DA2`/`0x8EA2` it piecewise-linearly
reshapes a demand float over the C810/C828/C840/C858 arrays,
selecting the source value by a mode byte and the selector bytes
(C74D appears in its pool list); other classes pass the value
through. The tail `FUN_1804ed70` consumes C74D/C74E + the base
tables (§2.7). A full consumer map of the scratch block is beyond
stage P's scope (§8).

---

## 3. Twin producer FUN_181f07ec — complete specification

Body 3204 B, entry `0x181f07ec`. Sole caller: the same ingestion
dispatcher `FUN_181f5d08` (UsersOf: call at `0x181f5d1c` region;
pool `0x181f5f58` in the dispatcher holds FUN_181f21d4's address —
both producers are invoked from the dispatcher's table-build step)
[FACT]. Writes `CC04[0..3]` @ `0xFFF8CC04`, `CC1C[0..3]` @
`0xFFF8CC1C`, `CC34[0..3]` @ `0xFFF8CC34`, flags `CC4C[0..3]` @
`0xFFF8CC4C`, indices `CBFB[0..3]` @ `0xFFF8CBFB`, count `CBFA` @
`0xFFF8CBFA`.

**Head** (listing-verified): memcpy 10 bytes from mirror record
`0xFFF83048`; **CD00 (`0xFFF8CD00`) = (float)(BE u16 at record
bytes [5..6])** — assembled `shll8`+`or` from stack offsets
dest+5/dest+6 at `0x181f0814`–`0x181f082e`, written **before** the
gate, on every call. Then getter(0x2D → CBF8, 2, 1), getter(3 →
CBF4, 2, 1); CBF6 = mirror byte `0xFFF830AE`.

**Gate**: if CBF4 == 0, or CBF6 == 0, or CBF6 == 4 → return,
writing no tables (CD00 above still updated). [FACT]

**Prologue** (gate passed, listing-verified at `0x181f0886`–
`0x181f08d0`): CBFA = (CBF4 & 3) + 1; CC4C = {1,0,0,0}; CBFB =
{0,1,2,3}; CC04[0] = CC1C[0] = CC34[0] = 0.0; entries [1..3] of all
three tables default 0.0, CC4C[1..3] = 0.

**Branches** (class word = CBF4, unsigned). "byteA" = the byte at
dict `0x3C0D40C8` (table `030A`, class 0x40, member 256); "byteB" =
dict `0x3C0D40B3` (table `030A`, class 0x3E, member 250). f = byte ×
1000.0. Ushort sources are table `0402` members (§5.4). Entries not
mentioned stay 0; CC4C[i] = 1 for every activated index i.

| CBF4 | CC04 / CC1C | CC34 |
|---|---|---|
| `0x99` | [1] = u16(dict `0x3C0D7AB6`) (both tables) | [1] = f(byteA) |
| `0x199` | [1] = u16(dict `0x3C0D7A8A`) (both) | [1] = f(byteB) |
| `0x9A` | [1] = u16(`0x3C0D7AB4`), [2] = u16(`0x3C0D7AB6`) (both) | [1] = f(byteA) × 0.6; [2] = f(byteA) |
| `0x19A` | [1] = u16(`0x3C0D7A88`), [2] = u16(`0x3C0D7A8A`) (both) | [1] = f(byteB) × 0.6; [2] = f(byteB) |
| `0x9B` | [1] = u16(`0x3C0D7AB4`), [2] = u16(`0x3C0D7ABA`), [3] = u16(`0x3C0D7AB6`) (both) | [1] = f(byteA) × 0.4; [2] = f(byteA) × 0.6; [3] = f(byteA) |
| `0x19B` | [1] = u16(`0x3C0D7A88`), [2] = u16(`0x3C0D7A98`), [3] = u16(`0x3C0D7A8A`) (both) | byteB × (0.4 / 0.6 / 1.0) |
| `0x97` | [1] = u16(`0x3C0D7AB4`), [2] = u16(`0x3C0D7ABA`), [3] = u16(`0x3C0D7AB6`) — **CC04 only** (CC1C[2..3] stay 0) | [1] = f(byteA) × 0.4; [2] = f(byteA) × 0.6; [3] = f(byteA) |
| `0x197` | [1] = u16(`0x3C0D7A88`), [2] = u16(`0x3C0D7A98`), [3] = u16(`0x3C0D7A8A`) — CC04 only | byteB × (0.4 / 0.6 / 1.0) |
| `0x59` | [1] = u16(dict `0x3C0D7AD0`) (both) | [1] = (store byte 0x12, read inside the branch) × **3414.0** |
| `0x5B` | [1] = u16(`0x3C0D7AD0`), [2] = u16(`0x3C0D7AD2`), [3] = u16(`0x3C0D7AD4`) — CC04 only | [1] = LUT(byte,1) × 3414.0; [2] = LUT(byte,2) × 3414.0; [3] = byte × 3414.0, byte = store[0x12], LUT = §4 |
| `0x39` | special, below | [1] = **50000.0** |

Multipliers 0.6 = `0x3F19999A`, 0.4 = `0x3ECCCCCD`, 3414.0 =
`0x45556000`, 50000.0 = `0x47435000` (pools `out/pools_181f07ec.txt`)
[FACT].

**Class `0x39`** (final else; tested as `(uint)CBF4 == 0x39`):
CC4C[1] = CBFB[1] = 1; v = u16 read via getter(store offset 0xCE,
2 B); CC04[1] = CC1C[1] = (float)v. If mirror byte **CBDC
(`0xFFF8CBDC`) ≠ 0**: read 8 ushorts via getter(store offset
0xCEE, 16 B); for i = 0..7, with the **loop-invariant** mode test
`*(byte*)0xFFF8CD7D == 1` (the stage-E mode byte): if mode == 1
and value > 450 (0x1C2): CB1E[i] (`0xFFF8CB1E`) = value, and
**CC04[1] tracks the minimum** of such values; if mode ≠ 1:
CB1E[i] = 450 for all i; if mode == 1 and value ≤ 450, CB1E[i] is
not written. After the loop: if **CC1C[1] == 450.0** (pool
`0x181f1688`) → CC04[1] = CC1C[1] = 0.0. CC34[1] = 50000.0.
Entries 2–3 of all tables 0; CC4C[2] = CC4C[3] = 0, CBFB[2] = 2,
CBFB[3] = 3. [FACT, decompile lines 346–392 + pools: DAT_181f1674
→ CC04, 1678 → CC1C, 1690 → CC34, 1684 → CB1E, 167c → CBDC,
1680 → CD7D.]

Unmatched CBF4 (gate passed): prologue defaults stand
(CC04 = CC1C = CC34 = {0,0,0,0}, CBFA = (CBF4 & 3) + 1). The
function's return value is a decompiler artifact of register
reuse. [FACT]

---

## 4. FUN_181f159c — the twin's lookup helper

Entry `0x181f159c`, 200 B. **Listing-verified semantics**
(`out/listing/lst_159c.txt`): args (key: byte, col: byte). Table
pointer pool `0x181f1698` → **`0x1830B094`**; rows i = 0..5,
row = 3 bytes at table + 3i: if row[0] == key → return
(float)row[col] for col ∈ {1, 2}, or (float)row[0] for col == 3;
no match (or col ∉ {1,2,3}) → return `*(float*)0x181f168c` =
**0.0**. Raw table bytes (18 B) [FACT, dual: raw read + listing
addressing]:

| key | col 1 | col 2 | col1/key | col2/key |
|---|---|---|---|---|
| 9 | 3 | 6 | 1/3 | 2/3 |
| 15 | 5 | 10 | 1/3 | 2/3 |
| 18 | 6 | 12 | 1/3 | 2/3 |
| 20 | 5 | 15 | 1/4 | 3/4 |
| 24 | 8 | 16 | 1/3 | 2/3 |
| 30 | 10 | 20 | 1/3 | 2/3 |

The key's equipment meaning is **not established** (§8); the twin
feeds it store[0x12] and multiplies results by 3414.0.

---

## 5. Inputs traced

### 5.1 R — store byte [8]

[FACT] R = store[8] / 12.0, descriptor range 0–72, factory default
24 (→ R = 2.0). The byte sits in the (0104, class 0x22) binding
chunk (chunk byte 3, §1). Which equipment datum the chunk carries
is **not established**: the chunk contents are engine-internal
device-object variables, and no consumer besides the /12.0 scaling
was isolated. Bounds: R ∈ [0, 6.0]; R × 12000 ∈ [0, 72000].

### 5.2 X — mirror float `0xFFF820F8`, validity byte `0xFFF820F5`

[FACT] Both producers and `FUN_181f3f44` read the pair from a
mirror record at ~`0xFFF820F0` (validity at +5, float at +8).
Census (dual-verified): 16 pool cells reference the float, 17 the
validity byte — **all reads**; no direct write reference exists in
either method, so the record is written through a computed address
by the binding engine's mirror ingest (the same pattern as CC54's
source `0xFFF830AD`: 11 cells, all reads). The feeding bus table is
**not isolated** (§8).

[FACT] In `FUN_181f21d4` X is clamped to [12.0, 61.0], invalid →
61.0; in `FUN_181f3f44` X is unclamped, invalid → 65.0.

[I] X behaves like a nominal capacity: the clamp range [12, 61],
the sentinel-like 61 on invalid data, and the identity
137.0 + 3.5 × 61.0 = 350.5 ≈ 350 with 34.286 ≈ 12000/350 make
K = 34.286 × (137 + 3.5X) a full-scale-350 normalization derated
linearly by X; at X = 60 (our ODU's nominal kBTU), K = 11897.242
and R × K ≈ R × 12000 × 0.9914. This is stage L's inference,
unchanged; stage P adds no proof.

### 5.3 U1/U2, selector bytes, CC54

[FACT] **U1 = `*(float*)0xFFF8C754`, U2 = `*(float*)0xFFF8C758`**
are written by the ingestion function **`FUN_181f59e0`** (stage-L
census WRITE instructions at `0x181f5ba6` → C758 and `0x181f5bae` →
C754, inside its body): U2 = `*(float*)0xFFF82210`, U1 =
`*(float*)0xFFF8220C` — a float pair at +0x0C/+0x10 of a mirror
record at ~`0xFFF82200`, copied under lock. Their bus source is
not isolated (§8); numerically they act as dimensionless stage
factors in §2.3.

[FACT] **Selector bytes C74D (`0xFFF8C74D`) / C74E
(`0xFFF8C74E`)**: readers are `FUN_181f21d4` (§2.4),
`FUN_1804ed70` (§2.7), `FUN_181f5e9a` (§2.8). Writer candidates by
census: `FUN_181f54e8` (pool cells `0x181f56d0`/`0x181f56d8` — the
ingestor that stage L showed copying CABC/CADC from mirror records
`0xFFF83C58`/`0xFFF83C38`) and `FUN_181f5e9a`; a direct WRITE
instruction was not isolated for either byte (§8). The bytes are
small enums (the §2.4 switch tests 0–4).

[FACT] **CC54** = mirror byte `0xFFF830AD`, read in the prologue;
values 0 and 4 force the fallback (§2.2). The same mirror record
supplies CBF6 at `0xFFF830AE` (twin gate) — record base
~`0xFFF83048` is also the twin's CD00 source (§3). No direct
writer (computed-address ingest, as §5.2).

### 5.4 Dictionary cells → (table, device class, member)

Resolution via the stage-F group table (member buffer addresses
are the `0x3C0Dxxxx` cells; size from buffer spacing). The
Sparkplug name inventory (stage H) does **not** name these member
buffers — names map to `0x3C12Exxx` property IDs, a different
space — so the (table, class, member) triple is the evidence-grade
resolution the task's "property name" resolves to. [FACT]

| cell(s) | table | class | members | used by |
|---|---|---|---|---|
| `0x3C0D805A/5C/5E/60` | 0504 | 0x50 | 724/725/726/727 (u16) | §2.4 set A |
| `0x3C0D8062/64/66/68` | 0504 | 0x54 | 728/729/730/731 (u16) | §2.4 set B |
| `0x3C0D8108/0C/10/14` | 0606 | 0x51 | 773/774/775/776 (f32) | 0x89A2/0x8AA2 |
| `0x3C0D8128/2C/38/3C` | 0606 | 0x56 | 781/782/785/786 (f32) | 0x8EA2/0x8DA2 |
| `0x3C0D8148/4C/54/58` | 0606 | 0x57 | 789/790/792/793 (f32) | 0xC6A2/0xC5A2 |
| `0x3C0D8168/6C/70/74` | 0606 | 0x5B | 797/798/800/801 (f32) | 0xC9A2/0xCAA2 |
| `0x3C0D8190…8196` | 0607 | 0x51 | 811–814 (u16) | 0x8AA2/0x89A2 |
| `0x3C0D8198…81B6` | 0607 | 0x56 | 815–830 (u16) | 0x8EA2/0x8DA2 |
| `0x3C0D81B8…81D6` | 0607 | 0x57 | 831–846 (u16) | 0xC6A2/0xC5A2 |
| `0x3C0D81D8…81F6` | 0607 | 0x5B | 847–862 (u16) | 0xC9A2/0xCAA2 |
| `0x3C0D8273` (+125 B) | 060E | **0x52** | 893 (+1 B offset) | §2.6 blob |
| `0x3C0D40B3` | 030A | 0x3E | 250 (u8) | twin byteB |
| `0x3C0D40C8` | 030A | 0x40 | 256 (u8) | twin byteA |
| `0x3C0D7A88/8A/98` | 0402 | 0x3E | 611/612/615 (u16) | twin 0x19x |
| `0x3C0D7AB4/B6/BA` | 0402 | 0x40 | 617/618/620 (u16) | twin 0x9x |
| `0x3C0D7AD0/D2/D4` | 0402 | 0x42 | 622/623/624 (u16) | twin 0x59/0x5B |

Pattern [FACT]: the parameter sets live on **device classes** —
0504 on classes 0x50/0x54; 0606/0607 on classes 0x51/0x56/0x57/0x5B;
the blob on class 0x52 (= address 0x53 canonicalized, our ODU);
the twin's sets on classes 0x3E/0x40/0x42 (030A/0402 are furnace
tables; class 0x40 = address 0x44 canonicalized, our furnace).
The class word in the store therefore selects, per branch, which
device class's parameter set parameterizes the tables — the
producers are equipment-class-driven in the literal sense.

---

## 6. The class-word encoding

### 6.1 Bit fields [FACT unless marked]

- **Bit `0x8000`**: set in all 18 compared CC52 values and all 11
  compared CBF4 values' high counterparts; the value `0x8000`
  itself is CC52's "unconfigured" fallback trigger (§2.2).
- **Bits `0x7C00`** (the stage-I mask): the shared tail tests
  `== 0x4000` (parameterized string classes) and `FUN_1804e9ac`
  special-cases `== 0x800`. Values taken by compared classes:
  0x0000 (0x81xx/0x82xx), 0x0400 (0x85C2), 0x0800 (0x89A2/0x8AA2),
  0x0C00 (0x8DA2/0x8EA2), 0x1000 (0x91xx/0x92xx), 0x2000
  (0xA1xx/0xA2xx), 0x4000 (0xC195/0xC295), 0x4400 (0xC5A2/0xC6A2),
  0x4800 (0xC9A2/0xCAA2).
- **Bit `0x0100`**: distinguishes CCDC-bearing variants (0x81xx,
  0x91xx, 0xA1xx) from CCC4-only variants (0x82xx, 0x92xx, 0xA2xx);
  proven functional by `FUN_1804e9ac`, which processes the
  CCDC-derived array only under this bit (§2.7).
- **Bit `0x0020`**: tested by both tail functions together with
  the interpolation path — an "interpolate" flag [I: name ours;
  the test itself is FACT].
- **Low nibble**: `CC5A = (CC52 & 0xF) + 1` (twin: `CBFA =
  (CBF4 & 3) + 1` — only the low **2 bits** for CBF4) [FACT].
  Compared CC52 nibbles: 1 (x141/x1C1 → CC5A 2), 2 (x142/x1C2/
  x5C2/x8A2/x9A2/xAA2 → CC5A 3), 5 (x195/x295 → CC5A 6, matching
  the 6-entry string arrays).
- **Paired variants** [FACT, branch structure]: 0x8241↔0x92C1,
  0x8141↔0x91C1, 0x8242↔0xA2C2, 0x8142↔0xA1C2 differ by bits
  0x1000/0x2000 **and** bit `0x0080` (low byte 0x41→0xC1,
  0x42→0xC2) with **identical formulas** — two equipment families
  sharing staging math. The twin shows the same pairing pattern:
  0x99↔0x199, 0x9A↔0x19A, 0x9B↔0x19B, 0x97↔0x197 differ by bit
  `0x0100` and switch the parameter source between device classes
  0x40 and 0x3E (030A byte + 0402 ushort sets).

### 6.2 The category byte `0x3C12A8D5`

[FACT] A mapper cluster in the dictionary region collapses CC52
into a small category enum at dictionary byte **`0x3C12A8D5`**:

| mapper | classes | category |
|---|---|---|
| FUN_180e2e34 | 0x8241, 0x8141 | 7 |
| FUN_180e2e34 | 0x8242, 0x8142 | 8 |
| FUN_180e2a80 | 0x92C1, 0x91C1 | 1 |
| FUN_180e2a80 | 0x92C2, 0x91C2 | 2 if mirror byte `0xFFF8356D` == 0x17; 3 if == 0x18; else 0 |
| FUN_180e2ae8 | 0x85C2 | 4 |
| FUN_180e2afc | 0xA2C2, 0xA1C2 | 5 |
| (default) | anything else | 0 |

`FUN_180e2b1a` handles 0xC295/0xC195 (string buffers in its frame;
its category output was not isolated). The A2 classes
(0x89A2…0xCAA2) are not covered by the mappers above — further
mapper functions exist in the `0x1814xxxx` cluster (ClassHunt:
`FUN_18144776` tests 0x8AA2/0x89A2, `FUN_18144ad4` tests
0xC295/0xC195, `FUN_1814b076` tests 0x8EA2/0x8DA2, `FUN_1814b5a4`/
`1814bb50` test 0xCAA2/0xC9A2, `FUN_1814c084`/`1814c4b4` test
0xC6A2/0xC5A2) but were not decompiled in stage P (§8).
Corroborating predicates [FACT, ClassHunt]: `FUN_1806f830`,
`FUN_180890a8`, `FUN_1811507e`, `FUN_181462c8`, `FUN_180ea75a`
test the {0x8141, 0x8241, 0x8142, 0x8242} family; `FUN_1806c64c`
tests {0x92C2, 0x91C2}; `FUN_181f5e9a` tests the A2 classes (§2.8).

### 6.3 What the families ARE — and are not

Established [FACT]: the families differ in (a) whether a second
(CCDC) table exists, (b) whether tables are computed analytically
from R/X/U (0x81xx/0x82xx/0x91xx/0x92xx/0xA1xx/0xA2xx/0x85C2),
copied from per-class parameter sets (0x89A2–0x8EA2, 0xC5A2–
0xCAA2), or parsed from a device-supplied blob (0xC195/0xC295);
(c) which device class's parameter set they consume (§5.4);
(d) the category byte (§6.2).

**Not established**: vendor equipment-type names for the families
(gas furnace vs heat pump vs fan coil vs geothermal…). No string
in the image names them: the dictionary name inventory (stage H)
contains no class-family names, the help texts (stage E §9) name
*settings*, not class words, and stage D/K proved there is no
furnace/ODU model database to key names off. Any assignment of
type names to the families in this report would be invention; the
emulator does not need them — it needs the formulas, which are
complete. [I, marked as ours alone: the analytic families with
the R×12000 heat table and the X-derated second table behave like
conventional staged fossil-fuel heat + separate cooling; the
blob classes behave like communicating inverter systems that
ship their own staging parameters — consistent with the blob
living in the ODU's 060E object.]

---

## 7. Our installation

### 7.1 What the captures establish [FACT]

0104 identity answers (120 B, all captures agree): furnace 0x44 —
"VARIABLE SPEED FURNACE", CESR******-**, model
**G80CTL1352422A2**, codes 2821/A213; ODU 0x53 — "VAR SPD COMP
VERSION", CESR******-**, model **HVA960GKA201**, codes 5422/3521;
payload bytes 23–47 are zero in every 0104 answer. The furnace's
0316 answers in our captures are dominated by live values (blower
CFM as BE u16 at payload [4..5]: 378…1750 across captures) with a
constant tail `… 78 01 00 03 6B`; **no class-word-shaped constant
appears in any equipment answer** (census over all traces in
stage P). Equipment summary (the author's photo, 2026-11-26): gas heat
2-stage 107K BTU/H output; AC 60K (5-ton) multi-stage.

### 7.2 Why the class word cannot be derived from the bus

[FACT] (i) The class words are thermostat-internal store fields
(§1) whose factory default is 0x0000; the running value is written
through the setter by a writer that stage P did **not** isolate
(§8) — the setter has ~700 call sites and the head-field writer is
not among the ones decompiled in any stage. (ii) No flash table
maps furnace/ODU identity → class word (stages D/K: the only
model-pattern database in the image is the coil's). (iii) The
binding chunks covering store 0–4 carry engine-internal variables,
not wire bytes (§1). (iv) The category byte `0x3C12A8D5` is
likewise internal. Conclusion: **derivation from captures is
impossible with the evidence available; the value must be read
from the unit or identified behaviorally.** This is a bounded
negative, with the exact read targets in §7.4.

### 7.3 Bounded candidate set [I]

Reasoning from the formula structure alone: our heat is 2-stage
gas; our cooling is a separate variable-speed AC. In
`FUN_181f21d4`'s terms that wants (a) a CCC4 table with one stored
breakpoint (stage 2 follows from stage E's ×1.25 rule) — low
nibble 1; (b) a CCDC table present — bit `0x0100` set. Candidates:
**0x8141 (category 7) or 0x91C1 (category 1)** — the two families
are formula-identical and differ only in bits 0x1000/0x0080 and
category, which no capture distinguishes. If the installation
instead stores two breakpoints per table, the candidates become
0x8142/0x91C1's siblings **0x8142/0x91C2** (the latter with the
selector form and 0504 parameter sets). The parameterized/blob
classes are less likely for this equipment generation [I]: their
parameter sets live on ODU device classes 0x51–0x5B, and our ODU
presents as class 0x52 — which carries the blob — so **0xC195
cannot be excluded** if the thermostat adopted the ODU-supplied
parameterization. Honest bound: {0x8141, 0x91C1} primary;
{0x8142, 0x91C2, 0xC195} not excluded.

### 7.4 Exact snapshot instructions

If a live read of the unit ever becomes possible (bench spare,
debug console, service tool), these are the values that close
every open parameter of §§2–3, in priority order [FACT addresses]:

| value | RAM address | notes |
|---|---|---|
| **CC52 (class word A)** | store bytes [1..2] = `0x3C0E4A21` (BE u16 at base+1); C-block mirror `0xFFF8CC52` | the answer to task (3) |
| CBF4 (class word B) | store [3..4] = `0x3C0E4A23`; mirror `0xFFF8CBF4` | twin's class |
| R byte | store [8] = `0x3C0E4A28` | R = byte/12 |
| twin byte | store [0x12] = `0x3C0E4A32` | §4 key |
| X (+ validity) | `0xFFF820F8` (byte `0xFFF820F5`) | §5.2 |
| U1 / U2 | mirrors `0xFFF8220C` / `0xFFF82210`; C-block copies `0xFFF8C754` / `0xFFF8C758` | §5.3 |
| selector bytes | `0xFFF8C74D` / `0xFFF8C74E` | §5.3 |
| category byte | `0x3C12A8D5` | §6.2 — cross-check for CC52 |
| finished tables | CCC4 `0xFFF8CCC4`, CCDC `0xFFF8CCDC`, CD04 `0xFFF8CD04`, CC04 `0xFFF8CC04`, CC1C `0xFFF8CC1C`, CC34 `0xFFF8CC34` (24 B each) | ground truth for §7.5 |

[FACT] No live channel to read these is currently known: no JTAG
evidence in the image (stage M), and the Clarinox socket debug
console (ports 4002/14321, stage M) appears flag-disabled. The
practical route for the emulator is therefore §7.5's bounded
tables + behavioral validation against captures (stage E §10's
method), not a snapshot.

### 7.5 Our threshold tables — bounded computation

Fixed inputs: K(X) = 34.286 × (137 + 3.5X): K(12) = 6137.194,
K(36) = 9017.218, K(48) = 10457.230, **K(60) = 11897.242**,
K(61) = 12017.243. R × 12000 and R × K(60) by store[8]:

| store[8] | R | R × 12000 | R × K(60) |
|---|---|---|---|
| 24 (factory default) | 2.0 | 24000 | 23794.5 |
| 36 | 3.0 | 36000 | 35691.7 |
| 48 | 4.0 | 48000 | 47589.0 |
| 60 | 5.0 | 60000 | 59486.2 |
| 72 (descriptor max) | 6.0 | 72000 | 71383.5 |

[I] Hypothesis set H: X = 60.0 (ODU nominal kBTU, §5.2) and
store[8] = 60 → R = 5.0 (the byte that makes R × 12000 = 60000 =
the system's nominal capacity — the same 60 the ODU reports;
flagged as a hypothesis, not a reading). Under H:

| candidate class | CCC4 | CCDC | CD04 |
|---|---|---|---|
| 0x8141 / 0x91C1 (CC5A = 2) | {0, **60000**, 0, 0} | {0, **59486.2**, 0, 0} | {5.0, –, –, –} |
| 0x8241 / 0x92C1 (CC5A = 2) | {0, 60000, 0, 0} | all 0 | {5.0, –, –, –} |
| 0x8142 (CC5A = 3; 0x91C2 instead uses the §2.4 selector form over the 0504/0x50 set) | {0, 60000·U1, 60000·U2, 0} | {0, 59486.2·U1, 59486.2·U2, 0} | {5.0, –, –, –} |
| fallback (CC52 = 0x8000 or CC54 ∈ {0,4}) | {0,0,0,0} | {0,0,0,0} | {0,–,–,–} |

(– = never written by the producer, §2.1.) With the factory-default
byte 24 instead of 60, the 0x8141/0x91C1 row reads CCC4[1] =
24000, CCDC[1] = 23794.5 — the sensitivity is linear in the byte,
so a single behavioral observation of a staging threshold from
captures (stage E §10 method) pins the byte to one row of the
table above.

The twin's tables (CC04/CC1C/CC34) **cannot be computed** from
available data: they need CBF4 plus runtime dictionary values
(030A bytes, 0402 ushorts) that are not in the captures in decoded
form. The 0x39 branch's constant CC34[1] = 50000.0 and the 0x59/
0x5B scale (byte × 3414.0; byte = 30 → 102420) bound their
magnitude family. [FACT bound]

---

## 8. Explicit unknowns / not isolated

1. **The writer of store bytes [1..2] / [3..4]** (the running class
   words). The defaults path writes 0x0000 (`FUN_181664da` →
   setter, descriptor default `0x182F6D1A`); the commissioning/
   discovery writer was not isolated among ~700 setter call sites.
   Untested candidates: `FUN_1818601e` and `FUN_180670d0` (~30
   setter calls each, unclassified), the third accessor-module
   function (pool cells `0x18159688`/`0x181598f0`).
2. **The bus tables feeding the mirror records** for X
   (~`0xFFF820F0`), U1/U2 (~`0xFFF82200`), CC54/CBF6/CD00
   (~`0xFFF83048`), and the category discriminator byte
   (`0xFFF8356D`). All are written via computed addresses by the
   binding engine; no direct writer exists in the image (dual
   census). Same wall as stages F/N, one level up.
3. **Equipment-type names** for the class families and for
   categories 0–8 (§6.3). Not in the image.
4. **R byte's equipment meaning** (§5.1) and **X's physical
   identity** (§5.2, capacity = inference). The §4 lookup key's
   meaning (store[0x12]) likewise.
5. **Selector-byte writers** (§5.3): direct WRITE instructions not
   isolated; `FUN_181f54e8`/`FUN_181f5e9a` are candidates by pool
   census.
6. **The `0x1814xxxx` mapper cluster** for the A2/string classes
   (category outputs) and `FUN_180e2b1a`'s category output —
   functions identified by ClassHunt, not decompiled.
7. **Full consumer map of the scratch block** `0xFFF8C75C`–
   `0xFFF8C7AC` and of CC64/CC94/CC7C/CCAC beyond the tail and
   `FUN_181f5e9a` (§2.8).
8. **CC56/CC58** (store 0x2F/0x31): read by `FUN_181f21d4`'s
   prologue and never used in its body [FACT] — their consumers
   are elsewhere (stage I noted CC56/CC58 ingestion); not pursued.
9. Note on sources: stage D's binding-directory dump is the same
   byte stream as stage F's group table read 6 bytes out of phase
   (stage P verified the raw bytes at `0x182B5E3A`); the two parses
   describe the same tiling with relabeled fields. Stage L §4's
   prose for the A2 classes is superseded by §2.5 (two agreeing
   decompilations govern).

---

## 9. Evidence index (stage P)

- `firmware-re/stageP/out/decomp/` — decompilations: 181f21d4,
  181f07ec, 181f169c, 181f18dc, 181f1c38, 181f1e78, 181f3f44,
  181f159c, 181f54e8, 181f59e0, 181f5d08, 181f5e9a, 1804e9ac,
  1804ed70, 181598c6, 180e2a80, 180e2ae8, 180e2afc, 180e2b1a,
  180e2e34, 1806f830.
- `firmware-re/stageP/out/listing/lst_main.txt` (181f21d4 +
  181f07ec), `lst_epi.txt` (tail/epilogue region), `lst_159c.txt`.
- `firmware-re/stageP/out/pools_181f21d4.txt`, `pools_181f07ec.txt`,
  `pools_rest.txt`, `pools_ingest.txt` — pool-cell resolutions.
- `firmware-re/stageP/out/usersof.txt` — Ghidra reference census;
  `out/classhunt.txt` — instruction-level scalar census of all
  class-word constants image-wide.
- `firmware-re/stageP/cellmap.py`, `resolve.py`, `run1–4.sh`,
  `scripts/` (Ghidra scripts incl. `ClassHunt.java`).
- Prior stages relied on: L §4 (partial formulas — completed
  here), E (staging machine, dictionary), F (group/descriptor
  tables), I/J (accessor census), D/K (coil DB, catalog), H
  (dictionary inventory), M (emulator — not needed for stage P's
  static results).
