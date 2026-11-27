# Firmware Analysis — Stage F: the descriptor-provider route to the payload writers

**Target:** Ion (Infinity) control firmware `BINF0479`, image base
`0x18040000`, Renesas SH-2A (SuperH BE). Same image as stages A–E
(MD5 `e31903228bf39a4bc9c0a2a74192359e`).

**Task:** attack the outbound payload writers — furnace demand `0305`
(incl. the constant `0x78` byte at [11]), ODU stage `0605`, call flag
`060D` — starting from the stage-C descriptor tables and their provider
functions: follow descriptor registration into handler/dispatch tables,
enumerate the registered handlers, identify which handlers construct or
transmit the burst payloads.

**Method:** all work on copies under `firmware-re/stageF/` (Ghidra 12.2
headless, project copy `stageF/proj`, no analysis pass — functions
created on demand); raw-image scans in Python over
`firmware-re/stageB/flat.bin` (`scan1..scan5`); every load-bearing fact
below is dual-verified (decompiler + raw bytes, or data + an independent
earlier-stage observation). Handler functions in the descriptor cluster
did not exist in the stage-B function database; they were created at
their table-referenced addresses with `CreateAndDecompile.java` and
decompiled (`stageF/out/handlers/`).

---

## 0. Headline results

1. **The stage-C descriptor route is now fully mapped — and it is a
   dead end for the payload writers, provably.** The descriptor table
   @ `0x182B04D4` is the field store's *schema*: each entry carries a
   default-value pointer (+0x10) and a **validator** function pointer
   (+0x14). The table has exactly two code consumers:
   `FUN_181664da` (restore field from default) and `FUN_18166394`
   (validate a candidate value by calling the +0x14 validators through
   a computed call). **All 26 distinct validators were enumerated and
   decompiled (§3): every one is a typed range/step/character
   sanitizer. None builds, queues, or transmits a bus frame.**
2. **The dictionary binding layer (stage D's "field-binding
   directory") is decoded end-to-end, with a phase correction to
   stage D.** The directory @ `0x182B5E3A` is a *group* table
   (385 groups over 106 bus tables); each group owns a contiguous
   range of members in a unified object registry @ `0x182B6AC8`.
   Stage D's trailing "field-store offset" is in fact a **member
   index** — proven by a decisive test against stage C's independently
   recorded SAM buffer (§4.3). Stage C's "second descriptor table @
   0x182B70EC" is the same registry (the SAM device record is
   member 98).
3. **`0305` and `060D` have no binding groups at all; `0605` has
   groups only for device classes 0x56/0x57/0x5B — not for our ODU
   (0x53 → class 0x52).** A full call census of the binding op
   `FUN_180a8da2` (72 caller functions, 1,755 rendered call
   expressions) confirms: zero calls for (any class, 0x03, 0x05) or
   (any class, 0x06, 0x0D); the only `0605` calls are
   `(0x56,6,5)`, `(0x57,6,5)`, `(0x5B,6,5)` in `FUN_1808f578` (§5).
   The 10 s burst for our equipment is therefore **not driven through
   the dictionary binding layer**.
4. **The `0x78` byte verdict:** it is **not a checksum** — the idle
   `0305` payload is eleven zero bytes followed by `0x78`, and [11]
   stays `0x78` while [0]/[2]/[4..5] vary across all 1,811 captured
   writes. It is a constant configuration/capability byte whose
   producing code was not isolated (§6).
5. **The writers were NOT isolated. The stall boundary is exact
   (§7):** everything statically reachable from the descriptor tables
   and from the dictionary binding layer terminates in (a) field-store
   validation/restore, or (b) membership bookkeeping (two RAM bitmaps)
   over the object registry. The component that serializes
   device-object state into ABCD frames has **no per-table code and
   no payload data anywhere in the application image** (stage D §2/§7
   negatives re-confirmed and extended in §7.2). §8 lists the concrete
   watchpoints a dynamic pivot needs.

---

## 1. The descriptor table, code-verified

Table @ `0x182B04D4`, **860 entries × 0x18 B**, ending `0x182B5574`
(raw dump: `stageF/out/descriptor_table.txt`, `scan2_descfull.py`).
Entry layout, verified against both consumers' decompiles:

| off | field | evidence |
|---|---|---|
| +0x00 | key (u16, field-store offset) | binary search compares it (`FUN_181662fa`) |
| +0x02 | len (u16) | range check + loop bounds |
| +0x04 | min (f32 bits, used as int) | validators compare `(int)*(float*)(e+4)` |
| +0x08 | max (f32 bits, used as int) | validators |
| +0x0C | step/divisor (f32 bits, used as int) | validators: `(v-min) % step == 0` |
| +0x10 | default-value pointer | `FUN_181664da` copies `len` B from it via setter-B |
| +0x14 | **validator function pointer** | called by `FUN_18166394` (§2.2) |

Facts:

- [FACT] Only **two pool cells in the whole image** contain the table
  base `0x182B04D4`: `0x1816656C` and `0x18166768`, both inside
  `FUN_181664da` (raw BE32 scan, `scan1`; decompile agrees). Any other
  consumer must go through the search function `FUN_181662fa`, which
  itself has exactly **two callers** (XrefDump,
  `stageF/out/xref_desc_consumers.txt`): `FUN_181664da` and
  `FUN_18166394`. The descriptor system's consumer set is closed.
- [FACT] An entry covers the store range **[key, key+len)**:
  `FUN_18166372(entry, off)` returns 1 iff `key ≤ off < key+len`
  (34-byte function, decompiled `stageF/out/decomp2/`). This explains
  the 495 unique keys among 860 entries (duplicate keys = repeated
  structures, e.g. per-zone blocks; `FUN_18166394` walks *all* entries
  of a key, then continues across following keys until the requested
  length is covered).
- [FACT] +0x10 classification over all 860 entries (raw scan): 734
  pointers into a small flash defaults region around
  `0x182F6D10`–`0x182F70xx`, 126 = the sentinel `0x182F6D10` itself,
  **zero pointers into code**. Most-referenced defaults: `0x182F6D1C`
  ×177 (byte 0x00), sentinel ×126, `0x182F6D1A` ×47.

## 2. The two consumers

### 2.1 `FUN_181664da` — restore one field from its descriptor

Decompiled in stage C; re-read in stage F
(`stageF/out/decomp1/decomp_181664da.c`). Search → range check → if
+0x10 is NULL or the sentinel `0x182F6D10`, zero the field via
setter-A `FUN_18159220(key, 0, len)`; else copy via setter-B
`FUN_181592e4(key, default_ptr, len)`. Referenced by 30 distinct
functions / 750 references (XrefDump) — the big ones are defaults
loaders (`FUN_1809c378` 228 refs, `FUN_1820e9c0` 108).

**Four keys bypass the static default pointer** — `0x712`, `0x744`,
`0x758`, `0x800` call the tiny providers `FUN_18166624` / `FUN_1816664e`
/ `FUN_18166678` / `FUN_181666a2` (42 B each), which select a string by
the brand byte derived from field `0x7B4` via `FUN_181665f4`:
`FUN_18166624` returns "Carrier Customer Relations" / "Bryant Customer
Relations" / "Consumer Relations"; `FUN_1816664e` returns the matching
phone strings ("1-800-CARRIER" / "1-800-428-4326" / "1-877-591-8908").
[FACT, decompiled `stageF/out/decomp2/`] These are the only *computed*
providers in the descriptor system — dealer-info strings for the UI.
No bus relevance.

### 2.2 `FUN_18166394` — validate a value against its descriptors

Signature `(key, len, buf) → corrected?` (326 B, decompiled
`stageF/out/decomp4/decomp_18166394.c`). It walks every descriptor
covering `[key, key+len)` and invokes the entry's validator through
the computed call `(**(code**)(entry+0x14))(entry, buf, …)`; returns 1
if any validator corrected a byte. This is the "sanitize on set" path
of the field store — and the **only** call site of all 26 validators.

## 3. Handler census: the 26 registered validators

Every distinct +0x14 value in the table (counts = descriptor entries;
sum = 860 ✓). All were created as functions and decompiled
(`stageF/out/handlers/fx_*.c`); all share the signature
`(descriptor_entry, value_buf) → corrected?` and the same shape:
compare each element against (min, max, step) from the entry, and on
violation overwrite from the entry's default (+0x10) via
memcpy `FUN_1823d404` / memset `FUN_1823da24`.

| handler | × | class |
|---|---|---|
| `0x181666CC` | 510 | u8 range+step, fix from default |
| `0x1816684C` | 143 | u16 BE range+step |
| `0x18166E42` | 49 | no-op stub (`return 0`) |
| `0x18166CD4` | 27 | char sanitizer (invalid → `0x3F` '?') |
| `0x181667B0` | 15 | u8 variant |
| `0x1809E2BC` | 14 | 7-byte record validator |
| `0x18166A60` | 12 | float range+step |
| `0x18166AF6` | 12 | single-value (bool/enum) check |
| `0x181A2C92` | 8 | schedule validator (reads field 0x0D, table-driven) |
| `0x181A28EE` | 8 | schedule validator, 7-byte records |
| `0x18166E46` | 8 | copy-default-if-invalid |
| `0x18166F84` | 8 | u8 variant |
| `0x181668EA` | 6 | u16 signed variant |
| `0x18166DB8` | 6 | char sanitizer variant |
| `0x1820E8A6` | 5 | string validator (15-byte window) |
| `0x18166998` | 5 | u32 range+step |
| `0x181A2CF2` | 4 | schedule validator variant |
| `0x18166D44` | 3 | char sanitizer variant |
| `0x18148DAC` | 3 | 6-byte record validator |
| `0x18166B8E` | 3 | u16 variant |
| `0x18166C44` | 3 | float variant |
| `0x18184D8A` | 2 | u8, default taken from a RAM cell (computed default) |
| `0x1820E79A` | 2 | table-lookup validator (0x10-stride records) |
| `0x18166EF0` | 2 | u8 variant |
| `0x180D1AB6` | 1 | 7-byte record validator variant |
| `0x181A2ADE` | 1 | schedule validator variant |

[FACT] Before stage F, **none of these addresses was inside any
function** in the stage-B database ("NO FUNCTION CONTAINS" for every
sampled target) — they are reachable *only* through the descriptor
table's computed dispatch, the same registration-boundary pattern as
stages B–E. [FACT] None of the 26 references the field-store setters,
the dictionary op, any UART/comm symbol, or any payload constant; the
out-of-cluster members are still validators (schedule/date/string
domains — e.g. the `0x181A28EE` family consults field 0x0D and
7-byte-stride tables, i.e. weekly-schedule records).

**Conclusion of the descriptor route:** the "providers" of stage C are
a value-domain enforcement layer for the settings store. The route
terminates here; there is no registration step beyond `FUN_18166394`'s
computed call, and no handler in the set touches the bus.

## 4. The dictionary binding layer, decoded

### 4.1 Address canonicalizer `FUN_180c6ebe`

First step of the binding op; a pure map (106 B, decompiled):

`0x44→0x40, 0x3F→0x3E, 0x46→0x42, 0x58→0x50, 0x55→0x54, 0x53→0x52,
0x5A→0x57, 0x5C→0x5B`; all other bytes pass through. It maps a physical
bus address to its device-class base (idempotent: source and target
sets are disjoint). Our devices: furnace `0x44` → class **0x40**;
ODU `0x53` → class **0x52**.

### 4.2 Group table @ `0x182B5E3A` — phase correction to stage D

[FACT] The table stage D parsed from `0x182B5E40` is read by code from
base **`0x182B5E3A`** (pool cells `0x180A8F24` and `0x180A6EA0` both
hold `0x182B5E3A`, raw-verified). Records are 8 B:
`[tableHi][tableLo][sub/class][flags][member_start BE16][member_count][pad]`.
The indexer `FUN_180a6bb0(cls_byte, tableHi, tableLo)` — called as
`FUN_180a6bb0(p2, p3, canon(p1))` — finds a record by its first three
bytes, using a bucket index @ `0x182B6A4A` (u16[0x40], buckets by
tableHi; `scan3_groups.py`). **385 groups over 106 distinct tables**
(full dump: `stageF/out/group_table.txt`, `scan5_final.py`).

Consequence: stage D's per-record "field" byte is this record's
sub/class byte (that part survives), but stage D's "field-store
offset" (e.g. `0605` → 0x301/0x302/0x303) is the **member-start index**
(769/770/771) into the registry of §4.3 — not a field-store offset.
The two readings share the same bytes; the code reading wins because
§4.3's test is decisive.

### 4.3 Member registry @ `0x182B6AC8` — and the decisive test

Records of 0x10 B: `{buf_ptr, aux_ptr, type_word, flag_word}`
(e.g. member 0: `{0x3C0D37A0, 0, 0x03180000, 0x01000000}`). Group
`(table, sub)` owns members `[start, start+count)`. Highest referenced
index: 896 (table `0612`); the registry's exact end was not determined
(flag word varies).

[FACT — decisive] Stage C recorded the SAM manager calling
`FUN_180a8da2(0x42, 3, 0x0D, buf = 0x3C0D41D0)`. The group
`(0x030D, sub 0x42)` is record 79: `member_start = 324, count = 1`,
and **member[324] = `{0x3C0D41D0, 0x3C0D41D8, 0x03070002, 0x01000000}`**
— its buf is exactly stage C's buffer. The group/member model is
therefore proven end-to-end by code + data + an independent earlier
observation.

[FACT] Stage C's "second static descriptor table @ `0x182B70EC`" is
this same registry read at a 4-byte phase shift: **member[98] =
`{0x3C0D3ED4, 0x3C0D3EE4, 0x43100002, 0x01000000}`** — buf = SAM device
record base, aux = SAM record handle word (raw-verified,
`scan5_final.py`).

### 4.4 The binding op `FUN_180a8da2` — membership bookkeeping only

Semantics (decompiled `stageF/out/decomp1/`, helpers in `decomp2/`):
canonicalize the address (§4.1) → find the group (§4.2) → walk its
member range: if a member's buf equals the caller's buffer, clear that
member's bit in bitmap A (`FUN_180a6eb8`, base `0xFFF855D6`); bits are
tested with `FUN_180a6f74` (same bitmap); if no member of the group is
bit-set, clear the group's bit in bitmap B (`FUN_180a6f16`, base
`0xFFF855A5`). Returns "buffer is a member of the group". It is a
**bind/unbind bookkeeping** primitive — it never reads payload data
and never serializes anything. Its 5-argument sibling
`FUN_180a898c` (pool-resolved from `FUN_180ea4ec`'s call
`(0x4F, 3, 0x32, buf, 0xFE)`) is the engine's object-publish API used
by the dictionary publisher cluster of stage D §3.2 — also not a bus
path (the published record is a fixed 0x32-byte dictionary object,
CRC'd over 30 bytes by `FUN_180ea704`).

## 5. Burst coverage: what the binding layer does and does not drive

Groups present for burst tables (full list in
`stageF/out/group_table.txt`):

| table | groups (sub/class) | member bufs |
|---|---|---|
| `0307` | 0x3E, 0x40, 0x42 | `0x3C0D40B0/B1/B2` (1-byte objects) |
| `0403` | 0x40, 0x42 | `0x3C0D7AD6…` |
| `0409` | 0x40 | `0x3C0D7B4D…` |
| `0414` | 0x42 | 7 members from `0x3C0D7DE0` |
| `0605` | **0x56, 0x57, 0x5B** | `0x3C0D8100/101/102` (1-byte objects, type `0x09010000`) |
| `0612` | 0x57, 0x5B | `0x3C0D82F0/F1` |
| `0305`, `060D`, `0610`, `061A`, `061E`, `060B`, `0202`, `0203`, `400A` | **none** | — |

Call census (`CallArgs2.java` over all 72 functions referencing
`FUN_180a8da2` through its 81 pool cells; 1,755 call expressions in
`stageF/out/callargs2_a8da2.txt`):

- [FACT] **Zero** call expressions with `(·, 3, 5, ·)` — table `0305`
  is never binding-queried, for any class.
- [FACT] **Zero** with `(·, 6, 0x0D, ·)` — table `060D` likewise.
- [FACT] Table `0605` is queried exactly three times, all in
  `FUN_1808f578`: `(0x56,6,5)`, `(0x57,6,5)`, `(0x5B,6,5)` — matching
  the three groups. Never `(0x52,6,5)` or `(0x53,6,5)`.
- Sanity: the census does recover known traffic — `(·, 3, 0x0D, ·)`
  ×28 (table `030D`), and our classes are queried for other tables
  (0x52: `061F` ×16, `0302`, `0625`, `0310/0311`, …; 0x40: `0413`,
  `030A`, `0409`, `0403`, …). The negative is specific to the three
  target tables, not an artifact of the method.
- Caveat: the census covers call sites whose arguments the decompiler
  rendered as constants; a caller passing fully computed arguments
  would not appear. The group-table absence (§5, data-complete over
  all 385 records) is independent of this caveat: with no group, the
  op returns "not a member" regardless of who asks.

Note also what the `0605` groups bind: three **1-byte** dictionary
objects at consecutive addresses — a per-class status/stage byte
object, not the 7-byte float payload layout. Even for classes
0x56/0x57/0x5B, the binding layer does not describe the wire payload.

## 6. The `0x78` byte of `0305` — verdict

- [FACT] Idle `0305` payload (protocol map §a):
  `00 00 00 00 00 00 00 00 00 00 00 78`. During calls, [0] (heat
  stage), [2] (cool stage) and [4..5] (CFM) vary; **[11] is `0x78` in
  all 1,811 observed writes** (protocol map §a/§e).
- [VERDICT] **[11] is not a checksum or CRC of the payload**: any
  function of [0..10] would change value between the all-zero idle
  payload and calling payloads; it does not. It is a **constant
  configuration/capability byte** of this installation
  (`0x78` = 120 decimal).
- [INFERENCE, unproven] Plausible semantics: a blower/equipment size
  code (e.g. a CFM class ×10) or a fixed capability bitfield
  (`0b01111000`). The producing code was not isolated (§7), so no
  semantic assignment is claimed. For the emulator this is moot:
  `0x78` is constant across every observed state, so emitting `0x78`
  reproduces the observed wire behaviour exactly.

## 7. The stall — exact boundary

### 7.1 Where each route ends

- **Descriptor route** (§§1–3): terminates at `FUN_18166394`'s computed
  call into the 26 validators and at `FUN_181664da`'s restore. Closed
  consumer set (two callers of the search function; two pool cells
  with the table base). No continuation toward the bus exists.
- **Dictionary route** (§§4–5): terminates at membership bookkeeping
  over the group/member tables. The target tables are absent from
  that system for our equipment classes. No serializer is reachable
  from it: `FUN_180a8da2` and its helpers touch only the two RAM
  bitmaps and the registry's buf fields.

### 7.2 What would have to exist, and does not

For a per-table writer to be statically findable, at least one of the
following would have to appear in the image. All were searched:

1. Payload bytes or templates as data — absent (stage D §2.3: the
   full `061E`/`0612` constant payloads and the idle `0305` payload
   occur 0 times in flash and in all 90 zlib streams; re-confirmed
   for stage F's targets by the group-table completeness in §5).
2. A binding group for the table — absent for `0305`/`060D` entirely,
   and for `0605` at class 0x52 (§5).
3. A CRC-16/MODBUS implementation for the frame tail — the bus CRC is
   CRC-16/MODBUS (init 0x0000, poly 0xA001; our own InfinitESP
   implementation, `infinitesp.cpp` `compute_crc_`). The image's only
   CRC table @ `0x182C4164` has exactly one code consumer,
   `FUN_180ea704`, inside the dictionary publisher (fixed 30-byte
   records). A stage-F scan for the polynomial as a pool word
   (`0x0000A001` / `0xFFFFA001`) finds **5 hits, all inside
   resource/string data at odd addresses ≥ `0x1831AE52`, zero in
   code** (`scan3_groups.py`). So the frame CRC is either computed by
   code outside this image region's static reach (engine library
   reached through registered pointers) or not present as a locatable
   routine.
4. A call path from any demand-side producer (stage E's module over
   `0xFFF8C8xx–0xFFF8CDxx`, refresh `FUN_181efdfc`) to any
   transmit-side consumer — stage E already established that the
   module's outputs (`0xFFF8CD49` staging byte, `0xFFF8CD4A`
   arbitration state, `0xFFF8CD4B` quantizer state) have **no static
   readers**; stage F adds that the binding layer never references
   them either (they appear in no group/member record and in no
   census call).

### 7.3 The boundary, in one sentence

The application image contains the *schema* (descriptors), the
*bookkeeping* (binding groups/members/bitmaps), and the *decisions*
(stage E) — but the *serializer* that turns a device object's state
into an ABCD frame is Clarinox engine code dispatched through
runtime-registered pointers over RAM-resident device objects, and it
exposes no per-table code, no payload data, and no statically
resolvable computed value (the device objects themselves are built at
discovery time in RAM `0x3C…` space) that static analysis of this
image can follow. **The unresolvable computed value is the engine's
per-class transmit method pointer, registered at runtime into RAM
dispatch structures that do not exist in the flash image.**

## 8. Input for a dynamic-analysis pivot

Concrete watchpoints, in the order a runtime session should arm them:

1. **UART TX path**: break on writes to the SCIF TX FIFO / TX DMA
   buffer during a 10 s burst; the return address chain at the first
   `0305` frame byte identifies the serializer directly. Frame format
   for matching: `[dst][src][func=0x0C][table BE16][len][payload][CRC16
   LE]` (InfinitESP `build_frame_`).
2. **RAM bitmaps** `0xFFF855D6` (member bits) and `0xFFF855A5` (group
   bits): watch who reads them outside `FUN_180a6f74`'s callers — a
   reader in a transmit loop would be the engine's scheduler.
3. **Device objects**: furnace (class 0x40) and ODU (class 0x52)
   records in `0x3C0D…` dictionary space, discovered at runtime;
   member[98] (`0x3C0D3ED4`, SAM) shows the record shape
   (`{record…, handle @ +0x10}`). Dump the furnace/ODU records in
   steady state and during a call; the fields that track
   stage/CFM are the serializer's inputs.
4. **Stage-E outputs** `0xFFF8CD49` (staging), `0xFFF8CD4A`
   (arbitration), `0xFFF8CD4B` (quantizer), demand float
   `0xFFF8CD44`: a data-watch on readers (any read not from
   `FUN_181efdfc`'s own module) crosses the boundary from the other
   side.
5. **Publish API** `FUN_180a898c` and op `FUN_180a8da2`: log callers
   during the burst window; if the burst is engine-scheduled, its
   scheduler will be active in the same window even if it never calls
   these two.

## 9. Not isolated (explicit list)

- The `0305` writer function — **not isolated** (no per-table writer
  exists in statically reachable code; §7).
- The `0605` writer for class 0x52 (our ODU) — **not isolated**; the
  same boundary. (`0605` binding groups exist only for classes
  0x56/0x57/0x5B and bind 1-byte objects, not the wire payload.)
- The `060D` writer — **not isolated**; same boundary.
- The frame builder / TX queue / bus CRC routine — **not isolated**
  (unchanged from stage D §7; stage F adds the negative polynomial
  scan of §7.2.3).
- The semantics of `0305[11] = 0x78` — **not isolated** (excluded:
  checksum; §6).
- The engine's per-class transmit method registration — **not in the
  image** (RAM-only; §7.3).
- The member registry's exact extent and the `type_word` encoding —
  partially decoded (record shape and membership semantics proven;
  type-word bit fields not decoded).
- Callers of `FUN_18166394` (the set-with-validation entry) — not
  enumerated; not needed for the TX question once §3 closed the
  handler set.

## 10. Artifacts (all under `firmware-re/stageF/`)

- `scan1_descriptors.py`, `scan2_descfull.py` → `out/descriptor_table.txt`
  (all 860 entries decoded).
- `scan3_groups.py` (bucket index, group/member resolution, CRC
  polynomial scan), `scan4_groups2.py` (decisive member test, burst
  coverage), `scan5_final.py` → `out/group_table.txt` (all 385 groups
  with member bufs).
- `scripts/CreateAndDecompile.java`, `scripts/CallArgs.java`,
  `scripts/CallArgs2.java` (new); reused stage-C/D/E scripts.
- `run1.sh`–`run5.sh` + logs.
- `out/decomp1/` (dispatcher + binding op), `out/decomp2/` (search,
  range check, providers, indexer, canonicalizer, bitmap ops),
  `out/decomp3/` (dictionary publisher cluster), `out/decomp4/`
  (validator dispatcher `FUN_18166394`), `out/handlers/` (all 26
  validators), `out/cluster_166/` (descriptor cluster survey),
  `out/xref_a8da2.txt`, `out/xref_desc_consumers.txt`,
  `out/callargs_a8da2.txt` (superseded), `out/callargs2_a8da2.txt`
  (full binding-op call census).
