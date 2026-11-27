# VERIFY-builder — frame builder & serializer directories (stage AA as corrected by FIRMWARE-AUDIT-2)

Date: 2026-11-26. Independent re-derivation from primary artifacts only:
flat image `firmware-re/stageB/flat.bin` (base 0x18040000, parsed byte-by-byte
in python), Ghidra outputs `firmware-re/stageAA/out/dumpAB.txt` /
`dumpAC.txt` / `dumpAD.txt` (decompiles, pool dumps, island listings), and a
fresh capture census over `traces/*.jsonl` + `traces/segments/*.jsonl`
(101,352 frames, 19 files). Report prose (AA, audit-2) was used only to
locate artifacts, never as evidence.

## Verdict summary

| # | Claim | Verdict |
|---|---|---|
| 1 | Builder FUN_180a44ee: buffer 0xFFF8529C, 12 B records @0xFFF853AC, kind→func map, payload at +0xB via FUN_180a815c/FUN_180a7eb0, TX FUN_180a44b8 → FUN_1819b27c gated by *0xFFF85295==0 and FUN_180d1cd4(0xA00080) | **CONFIRMED** (every element) |
| 2 | DIR-B disputed lengths & staging addresses | **Audit-2 CONFIRMED; AA §7 values REFUTED as installation values** (they are the first, foreign-class records) |
| 3 | DIR-A served set {0104, 0302, 3B02–3B05, 400A, 4202}; 3B02 member → 0x3C0D8D7D len 29 | Membership **CONFIRMED**; set-as-exhaustive **REFUTED** (72 records); 3B02 member **CONFIRMED** |
| 4 | DIR-C entries; length-field discrepancy 0302/0304/0307 | Entries **CONFIRMED**; AA's gloss "every length matches captures" **REFUTED** for 0302/0304/0307; field meaning **DETERMINED** (thermostat-side image size) |
| 5 | Canned fallback @0x182AFC50 = 18 × 120 B | **CONFIRMED** |
| 6 | RX island: 15-state machine, trailer at 0xC/0xD, error counter @0x3C12A5EC, queue 0xFFF85080, descriptor header 0x006B0000 | **CONFIRMED** (every element) |

---

## 1. Builder FUN_180a44ee — CONFIRMED

Evidence: decompile in `dumpAB.txt`; pool resolutions in `dumpAC.txt`.

- **Frame buffer / records.** Builder writes through `DAT_180a48cc` →
  **0xFFF8529C** (pool 0x180a48cc). Record pointer =
  `DAT_180a45bc + idx * 0xC` with `DAT_180a45bc` → **0xFFF853AC** and idx
  byte `DAT_180a45c0` → 0xFFF853A9: 12-byte runtime device records, exactly
  as claimed. Header: [0..1] = rec[0..1], [2..3] = own-address bytes from
  0x3C12A5E9/0x3C12A5EA (pools 0x180a48d0/0x180a48d4), [5] = rec[2],
  [6] = rec[3] XOR 0xC0 when nonzero, [8..10] = 0x00‖table-hi‖table-lo
  prefix for kinds 1–3.
- **Kind → func map**, read directly off the decompile branches:
  kind 1 → [7] = **0x0B**, [4] = 3, total 0xB, no walker (header only);
  kind 2 → [7] = **0x0C**, walker called with `frame + 0xB`,
  [4] = walker_len + 3; kind 3 → [7] = **0x06**, walker at `frame + 0xB`;
  kind 4 → [7] = **0x06**, [8] = 0, total 9 (single 0x00 payload byte);
  kind 5 → [7] = **0x15**, [8] = low byte of rec u16@+8, total 9;
  kind 6 → frame[0] = 0, total 1, and the CRC block is skipped by the
  explicit `param_1 != 6` guard → **raw 0x00, no CRC**. Matches the claimed
  sequence 0x0B / 0x0C / 0x06 / 0x06 / 0x15 / raw exactly.
- **Walkers.** Pool 0x180a48dc → **FUN_180a815c** (kind 2), pool
  0x180a48e0 → **FUN_180a7eb0** (kind 3); both receive `DAT_180a48cc + 0xb`
  — payload appended at **+0xB**. ✓ FUN_180a815c's own decompile
  (dumpAC) shows the dst == 0x20 field-walk over DIR-A @0x182C1440
  (pool 0x180a826c; records ×8, flags byte +2 bit 1, first member @+4,
  count @+6; members ×0x10, length @+9, skip @+0xB&1, format @+0xC,
  memcpy FUN_1823d404 + formatter FUN_180a7500) and the remote blob path
  via FUN_180a6df2 over DIR-B @0x182BF1D0 (pool 0x180a8448; records ×0xC,
  length u16 @+4) with blob pointers from the parallel table (pool
  0x180a8450, idx ×4), copied only when length ≤ 0xFD (the builder passes
  max_len 0xFD). FUN_180a7eb0's decompile shows the DIR-C lookup
  (FUN_180a6c84, directory pool 0x180a825c → 0x182BBD58) and the canned
  fallback (§5 below).
- **CRC + transmit gate.** For kind ≠ 6 the builder appends
  `FUN_180a42dc(frame, len)` high byte then low byte (of the byte-swapped
  return), then:
  `if (*DAT_180a48e4 == 0 && FUN_via_0x180a48ec(DAT_180a48e8) == 1)
  FUN_180a44b8(len − 1)`, with pools 0x180a48e4 → **0xFFF85295**,
  0x180a48e8 → **0x00A00080**, 0x180a48ec → **FUN_180d1cd4**. The same
  predicate also gates the builder's entry (pools 0x180a45b4 → 0xA00080,
  0x180a45b8 → FUN_180d1cd4). FUN_180d1cd4's decompile: `param >> 16`
  selects the SH7269 GPIO port register (0xA0 → 0xFFFE38BA), returns
  `(param & 0xFFFF & reg) != 0` — i.e. bit 7 of 0xFFFE38BA for the
  builder's constant. ✓
- **Transmit step.** FUN_180a44b8 decompile (dumpAC): FUN_180a4088(),
  FUN_180a403c() (GPIO toggle), stores the length, increments the TX
  counter, calls through pool 0x180a45b0 → **FUN_1819b27c**(0, len,
  frame-buffer pointer). ✓

No element of claim (1) failed.

## 2. DIR-B @0x182BF1D0 — audit-2 CONFIRMED; AA §7 REFUTED as installation values

My own parse of the full directory from `flat.bin`: the span
0x182BF1D0–0x182BFA88 is exactly 186 records × 12 B ([0] = hi, [1] = lo,
[2] = canonical device class, [4..5] = BE u16 length), with the parallel
pointer table @0x182BFA88 (idx × 4). DIR-B is **per-(table, class)**:
every disputed table has one record per class. The relevant rows, parsed
byte-by-byte:

| Table | Class 0x3E / 0x51 (AA §7, first record) | Class 0x40 / 0x52 (audit-2) |
|---|---|---|
| 0305 | 0x3E: len 12, blob 0xFFF857F6 | **0x40: len 12, blob 0xFFF85802** |
| 0307 | 0x3E: len 3, blob 0xFFF8583E | **0x40: len 4, blob 0xFFF85841** |
| 0605 | 0x51: len 7, blob 0xFFF85C86 | **0x52: len 7, blob 0xFFF85C8D** |
| 060D | 0x51: len 13, blob 0xFFF85CC1 | **0x52: len 1, blob 0xFFF85CCE** |
| 061E | 0x51: len 9, blob 0xFFF85D3B | **0x52: len 9, blob 0xFFF85D44** |

Raw record bytes (examples): 0307/0x3E = `0307 3e 0000 03 …`,
0307/0x40 = `0307 40 0000 04 …`; 060D/0x51 = `060d 51 0000 0d …`,
060D/0x52 = `060d 52 0000 01 …`. AA §7 quoted the **first record in
directory order** for each table (class 0x3E for the furnace-side 03xx
tables, class 0x51 for the ODU-side 06xx tables); audit-2 quoted the
records for the classes this installation's devices canonicalize to
(furnace 0x44 → 0x40, ODU 0x53 → 0x52, via FUN_180c6ebe, which the write
walker passes to the lookup FUN_180a6df2).

**Why the staging addresses differ — sequential packing.** The pointer
table assigns each record its own staging buffer, and the buffers are
packed back-to-back in directory order: each record's blob address =
previous record's blob + previous record's length. Verified arithmetically
for all five tables (0xFFF857F6 + 12 = 0xFFF85802; 0xFFF8583E + 3 =
0xFFF85841; 0xFFF85C86 + 7 = 0xFFF85C8D; 0xFFF85CC1 + 13 = 0xFFF85CCE;
0xFFF85D3B + 9 = 0xFFF85D44). AA's and audit-2's addresses are both real —
they belong to different class records of the same table.

**Wire ruling** (my census, 101,352 frames): the only lengths ever
transmitted by 0x20 are the 0x40/0x52 ones — 0305 → 44: 12 B ×806;
0307 → 44: **4 B ×804**; 0605 → 53: 7 B ×806; 060D → 53: **1 B ×806**;
061E → 53: 9 B ×806. The class-0x3E/0x51 lengths (3 B, 13 B) never appear
on this installation's wire. Verdict: **audit-2 is right; AA §7's
0307 = 3 / 060D = 13 (and its 0x3E/0x51 staging addresses) are refuted as
values for this installation** — they are genuine records for other
equipment classes. (AA §12 itself flagged the 0307 uncertainty; the 060D
class dependence it did not flag.)

## 3. DIR-A @0x182C1440 — membership CONFIRMED, exhaustiveness REFUTED; 3B02 member CONFIRMED

My parse: DIR-A holds **72 valid 8-byte records** (indices 0–71, flags
byte 0x02/0x03); the bytes after index 71 are the u16 index table the
lookup FUN_180a6d42 uses, not directory records. All eight claimed tables
are present: 0104 (idx 1), 0302 (idx 8), 3B02 (idx 22), 3B03 (23),
3B04 (24), 3B05 (25), 400A (idx 35), 4202 (idx 48). But the directory
also contains 0102, 0202, 0203, 0205, 0207, 0209, 020A, 0404, 2F02–2F11,
3105, 3117, 3131, 3B06, 4002–4016, 4602, 4605–4615, 4702, 4703, 4802,
4908, 4909, 4A02–4A04, 4E02, 5104, 5702, 5703. So the claimed set is a
**subset** (it is the subset AA §7 chose to name, with an ellipsis in AA
itself); as a statement of DIR-A's content it is incomplete — REFUTED as
an exhaustive set, CONFIRMED as membership.

**3B02 member — CONFIRMED exactly.** DIR-A record idx 22 gives
first member 65, count 1. Member 65 @0x182C1730 + 65×16 raw bytes:
`3c0d8d7d 3c0d8d9c 03 1d 00 02 6d 000000` → bound address
**0x3C0D8D7D**, length byte @+9 = 0x1D = **29**. (Neighbours check out
too: member 66 = 3B03 → 0x3C0D8DA0 len 150; 67 = 3B04 → 0x3C0D8E3C
len 11; 68 = 3B05 → 0x3C0D8E4C len 11.)

## 4. DIR-C @0x182BBD58 — entries CONFIRMED; discrepancy RESOLVED (field = thermostat-side image size); AA's "matches captures" gloss REFUTED for 0302/0304/0307

My parse of the 10-byte records ([4..5] = first descriptor, [6] =
descriptor count, [8..9] = BE u16 total length; descriptors @0x182BC5D8,
16 B) reproduces AA's census exactly: 0104 = 120, 0302 = 32, 0303 = 24,
0304 = 24, 0307 = 24, 061E = 9, 3B02 = 29, 3B03 = 150, 3B04 = 11,
3B05 = 11, 400A = 35, 4202 = 72; **0305/0605/060D have no DIR-C record**
(write-only, never read back). ✓

**What the length field counts — determined from the walker + the wire.**
In FUN_180a7eb0 (dumpAC decompile) the walker first memsets the payload
area to the record's [8..9] total, writes each descriptor's field at
frame offset desc[+8] − 3, and reports `*out_len = max(out_len, total)`:
the field is the payload size of the frame **the thermostat itself
builds when it serves that table** — the size of the thermostat's own
serialized image of the table (the span of its descriptor layout in its
mirror store). Wire proof: every table the thermostat actually serves in
the corpus is served at exactly its DIR-C length — all src 0x20, func
0x06: 0104 → 92: 120 B ×19; 3B02 → 92: 29 B ×865; 3B03 → 92: 150 B ×868;
3B04 → 92: 11 B ×19; 3B05 → 92/93: 11 B ×32; 400A → 92: 35 B ×21;
4202 → 92: 72 B ×21. Seven for seven.

For 0302/0304/0307 the thermostat never serves in the corpus; the
equipment answers are **per-device and all smaller**, and there is no
single "wire size" per table:

| Table | DIR-C field | ODU (0x53) answer | Furnace (0x44) answer |
|---|---|---|---|
| 0302 | 32 | 24 B ×1628 | 12 B ×1532 |
| 0304 | 24 | 16 B ×917 | 8 B ×480 |
| 0307 | 24 | — | 3 B ×1819 |

The thermostat-side images bind its own RAM mirrors: 0302 = 9
descriptors spanning 32 B over 0xFFF82106–0xFFF8221A plus one field-store
field (offset 0x5A3); 0304 = one 24 B descriptor @0xFFF82148;
0307 = one 24 B descriptor @0xFFF82130. So the field counts **the
thermostat's internal table-image size** (the full record it maintains
and would serialize), not any device's wire answer. Two corrections
follow: (a) AA §7's sentence "every length matches the table sizes
established from captures" is **REFUTED** for 0302/0304/0307 — no
captured answer has size 32/24/24 for these tables; (b) the discrepancy
as posed ("wire-observed answers 24/16/3") is itself incomplete — those
are the ODU's 0302, the ODU's 0304 and the furnace's 0307; the furnace's
own 0302/0304 answers (12 B / 8 B) were missed by both AA and the audit
premise. With the field read as thermostat-side image size, code and
wire are fully consistent and the open item is closed.

## 5. Canned fallback @0x182AFC50 — CONFIRMED

My parse: 18 records × 0x78 (120) B. FUN_180a7eb0's fallback loop iterates
`local_30 < 0x12` (= 18), matches `(byte)table[rec × 0x78] == table_id`
(the record's [0] is the table **high** byte), requires
`length @+2 ≤ max_len`, and copies the payload from +3. Record high
bytes: 01, 02, 03, 04, 06, 2F, 31, 3B, 40, 41, 42, 46, 47, 48, 49, 4A,
4C, 4E; payloads begin `00 20` + an ASCII name — DEVCONF, SYSTIME,
INGUI, SSBCAST, LINESET, STARTUP, INGDATA, SAMINFO, SCHEDULE, TEMP,
LASTTEN, MISC1, RESTMR, HEALTH, SYSCTRL, MISC2, SYSMETRC, CHARGING —
i.e. canned self-table bodies, as claimed (18 × 120 B, [0] = hi,
[2] = length, [3..] = payload).

## 6. RX island 0x180a53c0–0x180a5aa2 — CONFIRMED

Evidence: raw listings in `dumpAD.txt` (0x180a53c0–0x180a5814) and
`dumpAC.txt` (0x180a5800–0x180a5ab2), descriptor pool dump in `dumpAC.txt`,
plus my own raw reads of `flat.bin`.

- **Un-functioned island.** dumpAB: sites 0x180a5878 and 0x180a5ac8 have
  containing function **NONE** — Ghidra never made functions here. ✓
- **15 states, jump-table dispatch.** The handler loads the state cell,
  guards `cmp/hi 0xE` at 0x180a5466 (states 0..0xE = 15; above → exit),
  and dispatches through `braf r0` at 0x180a547a. State cell via
  descriptor slot 0x180a5ac4 → **0xFFF85298** (pool dump). ✓
- **Trailer assembly.** State 0xC handler @0x180a57c4: stores the received
  byte into the RX buffer (pointer cell slot → 0xFFF8528C), then
  `shll8 r2` and stores the u16 into the received-CRC cell (slot →
  **0xFFF84FBC**), then sets state := 0xD. State 0xD handler @0x180a5814:
  adds the low byte into 0xFFF84FBC, then `mov.l @(0x180a5ac8,pc),r3;
  jsr @r3` at 0x180a5876/0x180a5878 calls the CRC over
  (rx_buffer, count − 2) and compares against the assembled trailer;
  mismatch → `bra 0x180a59d8`. ✓
- **Error path @0x180a59d8** (raw listing): state cell := 0xE;
  property-set FUN_1809fde2 (slot 0x180a5af0) with the byte @0xFFF85535;
  u16 counter at slot 0x180a5b08 → **0x3C12A5EC** incremented with
  saturation at 0xFFFF (`cmp/ge` guard); flag word at slot 0x180a5b0c →
  **0x3C12A5F0** OR-ed with **0x20**. ✓
- **Classification + queue post.** On CRC match: FUN_180a41e4 called via
  slot 0x180a5acc (src == own address test), FUN_180a4210 via 0x180a5b00
  (dst == us), FUN_180a41bc broadcast test via 0x180a5ae8; the valid frame
  is posted at 0x180a590e–0x180a5916 with r4 = *(slot 0x180a5af8 →
  **0xFFF85080**) through slot 0x180a5afc → **FUN_180bc5b8** (a second
  post site exists at 0x180a59cc), with the FUN_180a51ce recovery helper
  on the failure path; RX double buffers swap via the alternate pointer
  cell 0xFFF85290 (slot 0x180a5b10). ✓
- **Descriptor record @0x180a5ab0.** Raw u32 in `flat.bin` at 0x180a5ab0
  = **0x006B0000** ✓ (read directly, not via the pool dump). Slot +0x18
  @0x180a5ac8 = 0x180A42DC (raw read ✓); my own BE32 census: the word
  0x180A42DC occurs **exactly once** in the whole image (the slot), and
  0x180A5AC8 occurs zero times as a BE32 literal (the island reaches the
  slot PC-relative) — AA's caller census (one direct BSR in the builder
  at 0x180a484a, visible in the builder decompile; one computed call
  here) stands.

---

## Method notes / limits

- DIR-B/DIR-A/DIR-C/canned parses are my own from `flat.bin` bytes;
  record layouts were taken from the walker decompiles (which fields the
  code actually reads), not from the reports.
- DIR-C record region: the directory span up to the descriptor array
  (0x182BC5D8) is not a whole number of 10 B records; all records cited
  sit in the clean low region (indices ≤ 75) and are corroborated by the
  lookup function's behaviour — the tail bytes belong to adjacent data.
- The capture census counts payload bytes of the `data` field as logged
  by the ESP capture (post-CRC bodies); counts differ from audit-2's
  (652/650/651…) because this census also includes `traces/segments/`;
  the length values agree exactly.
