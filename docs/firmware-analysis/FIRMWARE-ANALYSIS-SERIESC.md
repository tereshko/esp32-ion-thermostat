# FIRMWARE-ANALYSIS-SERIESC — Series C (SYST0201CW) probe: what the next generation reveals about the bus serializer

Date: 2026-11-26. Scope: a **probe**, not a full RE, of the Series C image
(CINF0200.BEX, CESR131755) that the versions pass downloaded as a sibling
from the V0200 slot. Question: is Series C's bus frame construction
statically visible, and if so, what shape transfers back to the v4.79
problem (stages F+N: the 0305 builder is dispatched via runtime-registered
per-class method pointers over discovery-built RAM objects — invisible
statically)? Method: python raw census + targeted Capstone (Thumb-2)
disassembly of the functions the census surfaced. Work dir:
`firmware-re/stageSC/` (copies only; `firmware-re/versions/` originals
untouched).

## 0. Headlines

1. **Series C is a different SoC generation: ARM Cortex-M (Thumb-2,
   little-endian), almost certainly NXP i.MX RT (Cortex-M7)** — not
   SH-2A. [FACT for ARM/LE from the vector table and code; i.MX RT is
   inference from the memory map, §1.]
2. **Its bus serializer is fully statically visible** — but it is *not*
   immediate-driven. It is the same platform design as 4.79 (static
   descriptor tables + a generic walker + runtime-built device
   records), except that in Series C the walker/builder is ordinary
   statically-linked code reached by direct BL calls, so it can be
   read. [FACT, §3.]
3. **The visible Series C serializer serves the thermostat's own
   tables** (SAM 3B02–3B06, schedules 4002–4016, identity 0104, its
   sensor table 0302, …) via a 72-record table directory
   @0x608AFBD0 and ~243 field descriptors @0x608AFEC0 that bind table
   fields to live RAM variables. **The demand family (0305, 0307,
   0605, 060D, 061E, 0316) is absent from this directory in Series C
   too** — Series C hands us no direct shape for the 0305 builder.
   [FACT, §2–§3.]
4. **The wire CRC in Series C is computed nibble-wise** from two
   32-byte tables (A = tab[0..15], B = tab[j<<4]) by FUN_6012F160,
   init 0, returning the CRC byte-swapped; verified 1000/1000 against
   the standard reflected-A001 wire CRC. [FACT, §3.4.]
5. **Main transferable result — a new concrete lead in 4.79**: the
   same 64-byte nibble-pair signature exists in the 4.79 image at
   **0x182B598C / 0x182B59AC** (BE), immediately before a `"CCN"`
   string (0x182B59CC), and it has exactly one static code reference:
   pool words at **0x180A4560 / 0x180A4564**, in a function whose pool
   also references the Clarinox property-set function FUN_1809FDE2
   and the message-post pair FUN_180BC558 / FUN_180BC602 (stage G).
   4.79's nibble-CRC consumer therefore sits inside the engine/binding
   module — where stages F/G placed the runtime boundary. This refines
   stage N's census: 4.79 has no nibble tables *in code*, but it has
   the pair *as data* with one consumer site. [FACT, §5.]
6. **Coil DB is present in Series C** as the LE twin of the stage-D
   format ({LE32 string ptr, f32 LE param}); the author's EN(A,D)4X61 =
   **1.69** there too (@0x608B30D8). The versions probe missed it
   because it scanned the BE format. [FACT, §4.]

## 1. Platform identification

- **File**: `extract/0200/TSTAT/CINF0200.BEX`, 8,896,064 B,
  MD5 `7eb779687c9db1a500e79dc1ddb84c46`,
  SHA-256 `820df3f37fcc5eae55d9d203ba0f52d4851eb5a5e86c0a3709827d42a6f3ae3d`.
  Same Intel-HEX-style record container as Series B; decoded by the
  versions pass with 38,812 records, **0 bad checksums**.
- **Regions**: main span **0x60100000–0x60942F18** (8,662,808 B);
  trailer at 0x60CFFE00 (108 B: `!!START_OF_CODE!CESR******-**.00`
  followed by an address-range table); 4-byte trailer at 0x60CFFFFC
  (`0xE8A83674` — a checksum; algorithm not verified in this probe).
- **CPU/architecture** [FACT]: a Cortex-M vector table sits at the
  load base: word[0] = initial SP **0x80800000**, word[1] = reset
  **0x60100331** (odd = Thumb), followed by ~100 further odd handler
  addresses (a default-handler cluster at 0x602345xx). The reset code
  at 0x60100330 disassembles cleanly as Thumb-2. Panic-dump strings
  name Cortex-M fault registers (CFSR, HFSR, UFSR, IPSR).
- **SoC family** [inference, strong]: **NXP i.MX RT (Cortex-M7)**.
  Evidence: image in FlexSPI NOR space at 0x60100000 (0x60000000
  base + 1 MB); DTCM pointers 0x20000000 / 0x2000FAE0 stored at
  0x60100310; OCRAM (0x20200000) holds the comm module's frame buffer
  (0x20202678), device records (0x20202778) and state bytes
  (0x2024AA19–0x2024AA24); SEMC SDRAM at 0x80000000 (initial SP
  0x80800000 = top of 8 MB; variables at 0x8007BE0F/10); the panic
  dump prints **SRSR** — the i.MX SRC status register's name.
- **RTOS** [inference, strong]: FreeRTOS. No `FreeRTOS` string
  exists, but the timer task/queue names `Tmr Svc` / `TmrQ` are
  FreeRTOS's own, and the image carries a full task-name table
  (@0x6089E354–0x6089E47C): *Configuration Task, ESPUART Message /
  Receive / Transmit Tasks, DataToCloud Task, Sparkplug Task, Data
  Transfer Task, OTA Task, Touch Task, CAT Task, **CCN Task**, NVM
  Task, System Control Task, WiFi Task*. The equipment-bus stack is
  the **CCN Task** (CCN = Carrier Comfort Network).
- **Middleware names are stripped**: zero hits for `Clarinox`,
  `SoftFrame`, `FreeRTOS`, `lwIP`, `mbedTLS` in ASCII or UTF-16
  (contrast 4.79's full Clarinox 9.0.0 fingerprint, stage H). The
  Carrier project codename survives: `{"product":"Bing","fw_ver":…}`
  @0x608B10DC (Series B's build tree was `C:\BingClarinox\…`). No
  source paths or assert file names were found (Series B had CING
  paths; Series C has none).
- **Cloud/dictionary**: Sparkplug B is present (`spBv1.0`
  @0x608B0EF0, `Sparkplug Task`, `sparkplugmsg:`, broker
  `mqtt.res.carrier.io`). The windowed dictionary path set (~130)
  covers `idu/*`, `odu/*`, `system/*` — including the
  `system/utilityEvent/demand*` group that 4.79 *removed* (Series C
  2.00's data model matches Series B ≤4.74 here).
- **WiFi**: a separate module on a UART — the *ESPUART* tasks —
  replacing Series B's TI WL18XX (no WL18xx strings in Series C).
- **ROM FS**: `\images`, `\fonts` in UTF-16LE — the same convention
  as Series B gen 2. Brand strings for the ICP family (AIRQUEST,
  Arcoaire, Comfortmaker, Day & Night, HEIL, KeepRite, Kenmore,
  TEMPSTAR) @0x6089D808.

## 2. Bus-layer census

- **Table-id constants in code**: a MOVW/MOVT immediate scan of the
  whole code span (0x60100000–0x60280000) for the known ID set found
  essentially nothing: 0x0306 ×1, 0x0316 ×3, 0x0604 ×1 (all outside
  the bus module), and **zero** for 0x0305, 0x0307, 0x0605, 0x060D,
  0x061E, 0x3B02, 0x400A. Raw byte-pattern counts are noise (both
  endians, ~8.6 MB image). Series C is **not** immediate-driven —
  same negative as 4.79, by a different census method.
- **Table directory** @**0x608AFBD0** [FACT]: 72 records × 8 B,
  ascending by ID, terminated by a zero record @0x608AFE10:
  `{table_id: byte0=hi, byte1=lo; type/flags: u16 LE; first_field:
  u16 LE; field_count: u16 LE}`. Contents (full list in
  `stageSC/out/facts.txt`): 0102, 0104, 0202, 0203, 0205, 0207,
  0209, 020A, 0302, 0404, 2F02–2F11, 3105, 3117, 3131, **3B02–3B06**,
  **4002–4016**, 4202, 4602–4615, 4702, 4703, 4802, 4908, 4909,
  4A02–4A04, 4E02, 5104, 5702, 5703.
  **Absent** [FACT]: 0305, 0307, 0605, 060D, 061E, 0316, 0604 — the
  whole equipment-demand and ODU families. The directory therefore
  describes the tables the wall control **owns and serves** (its own
  data model), not the tables it writes to equipment [inference from
  the membership: SAM tables, schedules, its own sensor table 0302,
  identity 0104].
- **Field descriptors** @**0x608AFEC0** [FACT]: ~243 records × 16 B
  (the directory's first_field/field_count space runs to index 242):
  `{u32 RAM variable address (OCRAM 0x2022xxxx / 0x2024xxxx, byte-
  granular); u32 second address (peer/shadow, often 0); u16
  size/offset code; u16 type/flags; u32 aux}`. The flag byte at
  +0xB distinguishes live-pointer fields from immediate/constant
  fields (one record's first word is the constant 0x000005A3, not an
  address). Each descriptor binds one bus-table field to one live
  application variable — the Series C analogue of 4.79's binding
  directory + registry, with the same semantics but static ROM
  geometry.
- **CRC tables**: two forms exist. (a) The **nibble pair** used by
  the bus module: A @0x6084F2E0 (= byte-table entries 0..15),
  B @0x6084F300 (= entries tab[j<<4]) — 32 B each, at the head of a
  larger data blob (bytes after +0x40 are unrelated data; the pair
  is *not* a 512-byte table — an early misread, corrected by direct
  comparison: only entries 0..31 of the "table" match A001-derived
  values, and they match A and B exactly). (b) A full **byte-wise**
  A001 table @0x608B1F1C with exactly one code reference (pool word
  @0x601DAF18) — a separate consumer outside the bus module, not
  followed in this probe.

## 3. The serializer, as actually organized (Series C)

All in one module (code ≈0x6012A000–0x6012F600; state bytes at
0x2024AA19–0x2024AA24; frame buffer at **0x20202678**; a runtime-built
table of **10-byte device records at 0x20202778**, indexed by a device
byte at 0x2024AA21 — the discovery-built device objects, as in 4.79).

### 3.1 Frame builder — FUN_6012B7FC
Argument = frame kind 0..6, dispatched by a jump table. It assembles
a frame in the fixed buffer field-by-field from the current device
record and two SDRAM-resident bytes (0x8007BE0F/10):
record[0], record[1] → frame[0..1]; SDRAM bytes → frame[2..3];
frame[4] ∈ {1, 3}; record[2], record[3] → frame[5..6] (frame[6]
conditionally XORed with ~0x3F); record u16@[6] → frame[8..9]
big-endian; record[8] → frame[10]; a length byte is maintained at
frame[7]. Payload is appended at frame+0xB by the descriptor walker
(§3.2). It then computes the CRC over the assembled frame (§3.4),
appends it (return value's high byte, then low byte — the CRC
function already byte-swaps, so the wire order is CRC low, high),
and, when the state byte at 0x2024AA19 is 0, calls **FUN_6012B7BC**
with the final length — the transmit/queue step [inference: TX].

### 3.2 Payload walker — FUN_6012E4F4 / FUN_6012E308
Given the target buffer and device-record fields, the walker looks
up the table's directory record (FUN_6012D7CC, or FUN_6012D734 on
the record[0]==0x20 path), checks the record's validity flag
(byte @+2 & 2), then iterates the table's field descriptors and
copies each bound RAM variable's bytes into the frame (memcpy-like
FUN_60263930; memset-like FUN_60235FDE for constant fields),
advancing a length accumulator through a caller-supplied pointer.
This is a **generic descriptor-driven serializer**: no per-table
code exists; the table's shape lives entirely in the §2 ROM tables.

### 3.3 Second CRC consumer — FUN_6012C2B8
The only other caller of the CRC thunk; a same-module state machine
(writes status 0x0E, consults the device lookup FUN_6012C198 before
its CRC call). Partially read; its exact role (receive/response or
poll path) was not determined in probe scope.

### 3.4 CRC — FUN_6012F160 (via thunk FUN_602369B4)
Signature (buffer, u8 length) — the thunk truncates the length to a
byte; the CRC function copies the two 32-byte nibble tables to its
stack and runs, per byte:
`crc = (crc >> 8) ^ A[(crc^b) & 0xF] ^ B[((crc^b) >> 4) & 0xF]`,
init **0x0000**, returning the result **byte-swapped**. Verified
against the standard reflected-A001 (init 0) wire CRC on 1000 random
buffers: **1000/1000** (with the return swap accounted). It has
exactly one direct caller (the thunk) and no function-pointer
registrations anywhere in the image.

## 4. Coil DB

Present [FACT], in the LE twin of the stage-D record format:
`{LE32 pattern-string ptr, f32 LE param}` × 8 B, in at least three
arrays — @0x608B2D98 (16 records), @0x608B2E28 (15), @0x608B2FE0 (32);
63 records extracted with a conservative filter (pattern strings
@0x608B2338–0x608B27xx in 12-byte slots). A fourth family of 28-byte
records @0x608B33A4+ carries a pattern pointer plus several f32
values (two-parameter records; exact field layout not decoded in
probe scope). **EN(A,D)4X61 → 1.69 @0x608B30D8** — the author's coil
parameter is identical in Series C. (The versions report's "no
stage-D-format coil pairs in Series C" was a format assumption —
BE pointers/floats; the DB is there, byte-swapped.)

## 5. Transfer verdict for 4.79

1. **The architecture is a platform invariant.** Both generations
   build the bus data plane as *static descriptor tables + generic
   walker code + runtime-built device records*. Series C contains no
   immediate-driven builder and no per-table construction code — the
   organization the 4.79 search kept not finding does not exist in
   either generation. What differs is **linkage**: Series C's walker
   is reached by direct BL calls from statically-linked code;
   4.79's is dispatched through runtime-registered pointers (stages
   F/N). The 4.79 dead end is structural, not a search failure —
   confirmed from the other side.
2. **No new handle on 0305 payload construction.** Series C's
   directory/walker covers thermostat-served tables only; the demand
   tables are absent from its directory just as 0305 has no binding
   group in 4.79 (stages D/F). In both generations the demand path is
   built by a different mechanism than the served-table walker (in
   4.79 the burst is programmatic, stage F). Series C cannot supply
   the missing 0305 field map.
3. **One sharp new lead in 4.79 (follow-up, not followed here).**
   Searching the 4.79 image for the Series C CRC signature — the
   64-byte nibble pair A||B — finds it (BE) at **0x182B598C**
   (A) / **0x182B59AC** (B), followed by the string `"CCN"` at
   0x182B59CC, in the data region between the descriptor table
   (0x182B04D4) and the binding directory (0x182B5E3A); the
   neighbourhood is a string/data block (JSON-style literals
   `null/true/false/invalid` immediately precede it). Exactly one
   static code reference exists: pool words at **0x180A4560** (→A)
   and **0x180A4564** (→B). That pool also references
   FUN_1809FDE2 (Clarinox property set, stage G), FUN_180BC558 /
   FUN_180BC602 (message post / occupancy, stages G/H), and RAM in
   the 0xFFF85xxx membership-bitmap page (stage F). So 4.79's
   nibble-CRC consumer is a function in the engine/binding module —
   the same runtime boundary, now with a concrete address to start
   from. Stage N's "no nibble tables" should be read as *none in
   code*; the pair exists as data with this single consumer site.
4. **Signatures that transfer**: (a) the 64-byte A||B nibble pair
   (used in item 3); (b) the directory geometry
   `{id_hi, id_lo, u16 flags, u16 first_field, u16 field_count}` —
   4.79's binding directory/registry (stages D/F) is the same concept
   with BE geometry; Series C confirms the field-descriptor →
   RAM-variable binding semantics those 4.79 structures imply;
   (c) `CCN` names the bus stack in both generations.
5. **What does not transfer**: addresses, layout, endianness (new
   SoC); instruction-level patterns (ARM vs SH-2A); and the Series C
   directory itself, which lacks the demand tables the emulator spec
   still needs from captures.

## 6. Explicit negatives / not done

- No Clarinox, SoftFrame, FreeRTOS, lwIP or mbedTLS name strings in
  Series C (FreeRTOS inferred from task names only).
- No source paths / assert strings in Series C.
- No table-id immediates for the demand set anywhere in Series C
  code (MOVW/MOVT census).
- The 0305/demand construction path was **not** isolated in Series C
  either; only the served-table serializer was.
- FUN_6012C2B8's exact role, the 28-byte coil records' field layout,
  and the trailer checksum algorithm (0x60CFFFFC) were left
  undecoded — probe scope.
- Long ascending-run scan hits (e.g. @0x602A7474) are large sorted
  data tables unrelated to the bus directory geometry; not pursued.
- Ghidra was not used: the arch is Ghidra-supported (ARM:LE:32:Cortex)
  if a fuller Series C RE is ever wanted, but targeted Capstone
  disassembly answered the probe's questions.

## 7. Artifacts (firmware-re/stageSC/)

- `seriesC_flat.bin`, `region0_60100000.bin` — working copies.
- `scripts/` — census1.py (table-id/CRC census), runs.py (ascending
  runs), coil.py (coil extraction), crcfunc.py / crcfull.py (CRC
  function), crccallers.py (BL caller scan + first equivalence test),
  verify2.py (table-layout correction), caller.py / thunk.py /
  tail.py (builder, walker, MOVW scan).
- `out/census1.json`, `out/facts.txt` (directory + key addresses).
- `venv/` — python venv with capstone 5.0.7 (system pip is PEP-668
  blocked).
