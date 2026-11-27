# FIRMWARE-ANALYSIS-AA — The frame-construction path, found: the CCN bus module (builder, walkers, RX validator)

Date: 2026-11-26. Scope: finish the chase of the frame-construction path in
v4.79 (BINF0479, SH-2A, base 0x18040000), building on the first AA pass
(wire CRC isolated and verified) and using the Series C organization
(FIRMWARE-ANALYSIS-SERIESC.md) as the template. This report **overturns
two stage F/N conclusions**: the wire-CRC routine *is* in the image, and
the frame serializer *is* statically linked ordinary code — it was
missed because it lives in a module whose receive half Ghidra never
turned into functions. Method: Ghidra headless on the stageAA project
copy (scripts DumpAB/DumpAC/DumpAD), raw censuses in python
(scripts/raw2.py + inline scans), all inside `firmware-re/stageAA/`.

## 0. Headlines

1. **The wire CRC is `FUN_180a42dc`** (0x180a42dc–0x180a4371), a
   nibble-wise CRC over the 4.79 tables @0x182B598C/0x182B59AC. Verified
   (first AA pass, `out/crc_test.txt`, not redone): == standard
   reflected A001 on 2000/2000 random buffers, on 1532/1532 gofinity
   wire frames, and nibble==std on 101352/101352 reconstructed bodies
   from our own captures. Stage N's "no nibble tables / wire-CRC
   routine not isolated" is **overturned** — the tables exist *as
   data*; stage N's census looked for them *in code*.
2. **Caller census of the CRC is complete and tiny** (dual-verified,
   §2): exactly two call sites — a direct BSR inside the frame builder
   (TX) and a computed call through a module descriptor slot inside the
   receive handler (RX). **The CRC serves both directions.**
3. **The frame builder is `FUN_180a44ee`** — the 4.79 twin of Series
   C's FUN_6012B7FC. It assembles frames field-by-field in the RAM
   frame buffer @0xFFF8529C from a runtime device record (12-byte
   records @0xFFF853AC), appends the payload via one of two walker
   functions, appends the CRC, and hands the frame to a Clarinox
   channel send. Frame kinds 1–6 map to wire funcs
   0x0B / 0x0C / 0x06 / 0x06 / 0x15 / (raw byte). §3.
4. **The demand family IS built by this path** (§7): the write
   walker's remote directory @0x182BF1D0 contains records for **0305
   (12 B), 0307, 0605 (7 B), 060D (13 B), 061E (9 B)** — lengths match
   the wire exactly. Demand payloads are not field-walked; they are
   blob-copied from statically addressed RAM staging buffers
   (0305 → 0xFFF857F6, 0605 → 0xFFF85C86, …). What stages F/N could
   not see was never the construction — it is only the *content
   production* of those staging buffers, which is the decision-side
   mirror already traced by stages L/N.
5. **The receiver is a byte-at-a-time state machine** in the
   un-functioned code island 0x180a53c0–0x180a5aa2 (§5): 15 states,
   jump-table dispatched, assembles the frame in a double-buffered RX
   buffer, assembles the received CRC trailer (hi<<8, then +lo) in
   0xFFF84FBC, validates it with the descriptor's CRC pointer,
   classifies by dst/src address match, maintains dictionary error
   statistics, and posts valid frames to the module queue
   @0xFFF85080.
6. **New boundary** (§9): the construction/validation *mechanism* is
   fully static now. What remains runtime-mediated is only the
   module's *activation*: the invoker that feeds bytes to the RX
   handler, the cadence source that ticks the link state machines,
   and the content writers of the demand staging buffers.

## 1. The CRC — FUN_180a42dc (completed first-pass result, cited)

Decompile: `out/fun_180a42dc.txt`. Signature `(byte *buf, u8 len)`,
init 0, per byte:
`crc = crc>>8 ^ tableA[((crc ^ b) & 0xF)] ^ tableB[((crc ^ b) & 0xF0) >> 4]`,
tables via pool cells 0x180A4560 → 0x182B598C and 0x180A4564 →
0x182B59AC; the return value is byte-swapped (CONCAT11) — callers
write it high-byte-first, which puts the true CRC on the wire
little-endian, exactly as observed in captures. Verification:
`out/crc_test.txt` (see headline 1). [FACT]

## 2. Caller census of FUN_180a42dc — complete

Ghidra references to the entry (out/fun_180a42dc.txt, out/dumpAB.txt):

| From | Type | Site |
|---|---|---|
| 0x180a484a | UNCONDITIONAL_CALL | BSR inside FUN_180a44ee (the builder) |
| 0x180a5878 | COMPUTED_CALL | `jsr @r3`, r3 loaded from descriptor slot 0x180a5ac8 (the RX handler) |
| 0x180a5ac8 | DATA | the descriptor slot itself, containing 0x180A42DC |

Raw cross-check (scripts/raw2.py over the full 15 MB image):
- BE32 word `0x180A42DC` occurs **exactly once** in the image — at
  0x180a5ac8. There is no other literal pool holding the address.
- BSR/BRA 12-bit-displacement targets equal to 0x180a42dc: **exactly
  one** — the BSR at 0x180a484a. (SH-2A has no other direct-call
  encoding; a far call must go through a literal, covered by the BE32
  census.)
- References TO the slot 0x180a5ac8: exactly one, a READ at 0x180a5876
  (the RX handler loading the pointer). No BE32 occurrence of
  0x180a5ac8 or of the descriptor base 0x180a5ab0 exists anywhere —
  the runtime reaches the descriptor without a static pointer to it.

**Census verdict [FACT]: two call sites, one per direction.** No
third consumer exists in the image.

## 3. TX path — the builder FUN_180a44ee

Module map: the bus ("CCN") module occupies ≈0x180A3F5A–0x180A65xx
(41 functions in 0x180a3e00–0x180a6400, out/dumpAB.txt). Key resolved
addresses (pool dumps, out/dumpAC.txt):

- Device records: base **0xFFF853AC** (RAM), stride **0xC** (12 B),
  current-index byte @0xFFF853A9, second index @0xFFF853AA, ≤0x20
  records (FUN_180a5b30 wraps the scan index at 0x1F). Runtime-built
  (discovery), as in Series C — but 12-byte records, not 10.
  Record layout as used by the builder: [0] = dst address byte,
  [1] = dst field byte 2, [2]/[3] → frame[5]/[6], u32 @+4 = build
  kind (the state machines pass `*(u32*)(rec+4)` as the builder's
  argument), [9] = table id high byte (the u16 @+8 reads 0x00‖hi),
  [10] = table id low byte.
- Frame buffer: **0xFFF8529C** (RAM). Frame layout written by the
  builder matches the known wire format: [0..1] dst field from the
  record, [2..3] own-address bytes from dictionary cells
  **0x3C12A5E9 / 0x3C12A5EA**, [4] payload length, [5] = rec[2],
  [6] = rec[3] (XORed with 0xC0 when nonzero — cf. Series C's
  conditional XOR ~0x3F), [7] func, [8..10] = payload prefix
  (0x00, table hi, table lo), payload appended at +0xB by the
  walkers, CRC appended after the payload.

Builder behaviour by kind (argument = device-record type), all
[FACT] from the decompile in out/dumpAB.txt:

| Kind | Func | Payload | Notes |
|---|---|---|---|
| 1 | 0x0B | header only: [8..10] = rec u16@[8] BE + rec[10] (the 0x00‖table prefix); no payload appended | [4] = 3; pre-CRC length 0x0B; no walker |
| 2 | 0x0C | reg prefix + walker FUN_180a815c | [4] = walker_len + 3 |
| 3 | 0x06 | reg prefix + walker FUN_180a7eb0 at +0xB | [4] = walker_len + 3 |
| 4 | 0x06 | single 0x00 byte | [4] = 1, pre-CRC length 9 |
| 5 | 0x15 | single byte = low byte of rec u16@[8] | [4] = 1, [7] = 0x15, pre-CRC length 9 |
| 6 | — | frame = single byte 0x00 | **no CRC**; transmitted with length−1 = 0 |

For kinds 1/2 the builder first runs FUN_180a41bc(frame) — true when
frame[0]==frame[1] and frame[0] > 0xF0 (a broadcast/escape header,
e.g. 0xF1F1) — and if so sets module byte 0xFFF853A8 = 0x15.

CRC + transmit sequence [FACT]: if kind != 6,
`crc = FUN_180a42dc(frame, len)`; frame[len] = crc>>8,
frame[len+1] = crc&0xFF (the CRC function already byte-swaps, so the
wire order is true-CRC low, high — matching captures). Then, gated by
`*0xFFF85295 == 0` (receiver-idle byte) **and** the GPIO predicate
FUN_180d1cd4(0x00A00080) == 1, it calls the transmit step
**FUN_180a44b8(len−1)**.

FUN_180d1cd4 is a GPIO pin test: param>>16 selects an SH7269 GPIO
port register in 0xFFFE38xx, param&0xFFFF is the bit mask; the
builder's constant 0x00A00080 tests bit 7 of the port at 0xFFFE38BA.
The same predicate gates the builder's entry. [FACT for the register
read; the pin's physical meaning — bus-free / enable — is inference.]

Transmit step FUN_180a44b8(len) [FACT, out/dumpAC.txt]: calls
FUN_180a4088() (module buffer/state reset helper) and FUN_180a403c()
— which sets bit 3 of GPIO data register 0xFFFE38B6 (an RS-485
direction/enable line toggle at transmit time [inference]); stores
the length at 0xFFF853A0; increments a TX counter at 0xFFF8539C;
hands (channel 0, length, frame buffer 0xFFF8529C) to
**FUN_1819b27c**, a Clarinox channel-send wrapper (channel < 8 path
posts the buffer with flag 0x80000); finally property-sets
FUN_1809fde2(*0xFFF85534, 6, 0).

Who calls the builder [FACT]: the link state machines
**FUN_180a5c40** and **FUN_180a5d28**, via pool-held pointers
(pool cells 0x180a5db8 / 0x180a6070 / 0x180a636c all contain
0x180A44EE), passing the device record's type u32. FUN_180a5d28
dispatches on the link-state cell **0xFFF853A4** (states 0–6+, retry
counters at 0xFFF853A8 with thresholds 2/3/10/0x15 that change when
the current frame's dst byte == 0x0E — the frame buffer doubles as
the "current target" record); it is itself called from seven static
thunk sites at 0x180a657e–0x180a65fa. FUN_180a5b30 is the shared
"is there a pending device record" scanner (walks the records under
the FUN_180bc2d2/FUN_180bc36a lock pair on 0xFFF8552C). One level
further out, the control cluster (0x180C99EC / 0x180CA384 /
0x180CA1BA) enters the module through **FUN_180a490e →
FUN_180a49a8**, a 7-argument request API (partially read; the
'i' (0x69) request class is special-cased). [FACT for the call
graph; FUN_180a49a8's internals not fully decoded — explicit
unknown.]

## 4. The payload walkers

### 4.1 FUN_180a815c — write walker (builder kind 2, func 0x0C)

Arguments: (frame+0xB, table id, rec[10], dst byte = rec[0],
max_len = 0xFD, &out_len). Two payload sources, chosen by
destination [FACT, out/dumpAC.txt]:

- **dst == 0x20 (self): field-walk.** Lookup FUN_180a6d42(table)
  over an index table (u16 offsets per table-high byte, hi < 0x58)
  into directory **DIR-A @0x182C1440** (8-byte records:
  [0]=hi, [1]=lo, [2]=flags — bit 1 must be set, [4..5]=first
  member, [6]=member count). Members @**0x182C1730** (16-byte
  records: [0..3] bound RAM/store address, [+9] byte length,
  [+0xB]&1 skip flag, [+0xC] format code). Each member's bytes are
  memcpy'd (FUN_1823d404) into the frame and post-processed by
  FUN_180a7500(ptr, len, format) [inference: byte-order/format
  conversion], under the FUN_180bc22a/FUN_180bc234 lock pair.
- **dst != 0x20 (remote): blob copy.** Lookup FUN_180a6df2(hi, lo,
  FUN_180c6ebe(dst)) — the destination is canonicalized by stage
  F's canonicalizer FUN_180c6ebe — over directory **DIR-B
  @0x182BF1D0** (12-byte records: [0]=hi, [1]=lo, [2]=canonical
  device class, [4..5]=payload length; ≤186 records). If the
  record's length ≤ 0xFD, the payload is memcpy'd from the blob
  pointer in the parallel pointer table **@0x182BFA88**
  (idx × 4). The blob pointers are static (flash) addresses of
  RAM staging buffers (§7).

### 4.2 FUN_180a7eb0 — read/serve walker (builder kind 3, func 0x06)

Lookup FUN_180a6c84 over directory **DIR-C @0x182BBD58** (10-byte
records: [4..5]=first descriptor, [6]=descriptor count, [8..9]=
total payload length; ≤200 records). Descriptors @**0x182BC5D8**
(16-byte records). Each field is serialized by **FUN_180a7e20**
(out, bound_ptr, len, convert_flag = desc[+0xB]&1, format =
desc[+0xC]) writing at frame offset desc[+8]−3: raw copy +
FUN_180a7500 formatting when convert_flag == 0; a field-store read
through the stage I/J getter FUN_1815927c when convert_flag == 1.
Fallback [FACT]: if the lookup fails and rec[10] == 1, a canned
payload is copied from a static table @**0x182AFC50** (18 records ×
0x78 bytes: [0]=table hi, [2]=length, [3..]=payload bytes).

This is the same generic descriptor-driven design as Series C's
walker FUN_6012E4F4 (SERIESC §3.2) — no per-table code anywhere.
[FACT]

## 5. RX path — the island state machine

The code at **0x180a53c0–0x180a5aa2** has no Ghidra functions (an
analysis gap, not a runtime registration). It is one byte-at-a-time
receive handler, entered per received byte (the byte arrives in a
message, read at @(0xF,R15)), dispatched by a jump table on the
receiver state **0xFFF85298** (guard: state ≤ 0xE). Working cells:
RX buffer pointer cell **0xFFF8528C** (double-buffered; the
alternate pointer is held in 0xFFF85290 and swapped on one accept
path), byte counter **0xFFF85295**, remaining-payload counter
**0xFFF85296**, received-CRC cell **0xFFF84FBC**. Listing:
out/dumpAD.txt (0x180a53c0–0x180a5814) and out/dumpAC.txt
(0x180a5800–0x180a5ab2).

State walk [FACT from the listing]: states 1–4 store header bytes
0–3; state 5 stores frame[4] (the length byte) and loads the
remaining counter from it (a byte > 0xF8 is rejected through
FUN_180a415a with error 0x40); states 6–7 store bytes 5–6; states
8–11 store payload bytes while decrementing the remaining counter;
state 0xC stores the CRC **high** byte and writes it <<8 into
0xFFF84FBC; state 0xD stores the CRC **low** byte and completes the
frame:

- received_crc = 0xFFF84FBC + low byte (the cell held hi<<8);
- computed = **FUN_180a42dc(rx_buffer, count − 2)**, called through
  the descriptor slot (`mov.l @(0x180a5ac8,pc),r3; jsr @r3`);
- **mismatch** → error path 0x180a59d8: receiver state cell set to
  0xE, property-set FUN_1809fde2(*0xFFF85535, 1, 0), dictionary
  error counter @0x3C12A5EC incremented (saturating), dictionary
  flag word @0x3C12A5F0 |= 0x20;
- **match** → classification, using two descriptor methods:
  FUN_180a41e4(buf) = "frame[2..3] == own address bytes
  (0x3C12A5E9/EA)" and FUN_180a4210(buf) = "frame[0..1] == own
  address bytes", plus the broadcast check FUN_180a41bc. On the
  dst==us path: dictionary flag byte 0x3C12A605 |= 2, dictionary
  statistics at 0x3C12A5E8/0x3C12A5EC/0x3C12A5F0 updated (flag
  0x400), RX double buffers swapped, and the received message is
  posted to the module queue **0xFFF85080** via FUN_180bc5b8 (the
  queue the stage G message-post family serves; FUN_180a4372 /
  FUN_180a445c post type-4 / type-7 notifications to the same
  queue). On the src==us path with link state 0xFFF853A4 == 3, the
  state advances to 4 and a type-7 notification is posted. A
  post failure invokes the recovery helper FUN_180a51ce.

**Role verdict [FACT]: FUN_180a42dc is used on both paths** — TX
append by the builder (§3), RX validation by this handler.

## 6. The module descriptor @0x180a5ab0

Immediately after the RX handler sits a descriptor record (the
handler uses it as its literal pool — every method call loads the
pointer from a slot). Layout [FACT, out/dumpAC.txt pool dump]:
header word 0x006B0000, then interleaved field pointers (RAM
0xFFF84FBC–0xFFF85538; dictionary 0x3C12A5E8–0x3C12A606) and method
pointers: FUN_180a42dc (CRC) @+0x18, FUN_180a41e4, FUN_180a445c,
FUN_1809fd98, FUN_180a41bc, FUN_1809fec0, FUN_1809fde2,
FUN_180a4372, FUN_180bc5b8, FUN_180a4210, FUN_1809fd7e,
FUN_180a4046, FUN_1819b1e6. This is the module's exported object —
the 4.79 analogue of the runtime-built device records in Series C,
except that here the record itself is static ROM data. No static
pointer to its base exists (§2); a sibling registration stub
FUN_180a5aa2 is referenced from a registration table at
0x182FAC24 [FACT], which is presumably how the runtime learns the
module [inference].

## 7. Which tables the path handles — directory census

Raw census of the three directories against the known table set
(this pass; lengths are the directories' own fields):

**DIR-A @0x182C1440** (self field-walk, func 0x0C to dst 0x20):
0104, 0302, 3B02, 3B03, 3B04, 3B05, 400A, 4202, … — served/self
tables only. (Sanity: 3B02's member 65 @0x182C1730 binds store
buffer 0x3C0D8D7D with length byte 0x1D = 29 — the exact 3B02 body
size.)

**DIR-B @0x182BF1D0** (remote blob copy, func 0x0C to equipment):
**0305 (class 0x3E, len 12, blob @0xFFF857F6), 0307 (class 0x3E,
len 3, blob @0xFFF8583E), 0605 (class 0x51, len 7, blob
@0xFFF85C86), 060D (class 0x51, len 13, blob @0xFFF85CC1), 061E
(class 0x51, len 9, blob @0xFFF85D3B), 3E02 (class 0x0E, len 1,
blob @0xFFF868C9)**; 79 of 186 records have table-high 0x03/0x06.
Lengths 12 / 7 / 9 match the observed 0305 / 0605 / 061E payloads
exactly.

**DIR-C @0x182BBD58** (read/serve, func 0x06): 0104 (len 120),
0302 (32), 0303 (24), 0304 (24), 0307 (24), 061E (9), 3B02 (29),
3B03 (150), 3B04 (11), 3B05 (11), 400A (35), 4202 (72), … — every
length matches the table sizes established from captures and the
infinitive layouts. 0305/0605/060D are absent from DIR-C —
write-only tables are never read back. [All FACT.]

**Demand verdict:** the burst frames are constructed by
FUN_180a44ee + FUN_180a815c's blob path, from staging buffers in
the module's RAM page (0xFFF857F6…). Stage F's observation that
0305 has no group in the binding directory @0x182B5E3A stands —
that directory serves a different mechanism (membership
bookkeeping); the serializer's own directories are DIR-A/B/C
above, and in them the demand tables are first-class records.
Stage N's inference "one engine serializer behind runtime
pointers" is refined: the serializer is this module, in ordinary
statically linked code.

## 8. Comparison with Series C (template check)

| Series C (SERIESC §3) | v4.79 (this report) |
|---|---|
| Builder FUN_6012B7FC, kinds 0..6, fixed frame buffer 0x20202678 | FUN_180a44ee, kinds 1..6, frame buffer 0xFFF8529C |
| Device records 10 B @0x20202778, runtime-built | Device records 12 B @0xFFF853AC, runtime-built |
| frame[6] conditionally XOR ~0x3F | frame[6] XOR 0xC0 when rec[3] != 0 (same constant) |
| Walker FUN_6012E4F4, directory @0x608AFBD0, descriptors @0x608AFEC0 | Walkers FUN_180a815c / FUN_180a7eb0, DIR-A/B/C + member/descriptor arrays |
| CRC FUN_6012F160, nibble pair, init 0, byte-swapped return | FUN_180a42dc, nibble pair @0x182B598C/AC, init 0, byte-swapped return |
| Builder calls FUN_6012B7BC to transmit when state byte == 0 | Builder calls FUN_180a44b8 → FUN_1819b27c when *0xFFF85295 == 0 and GPIO predicate holds |
| Second CRC consumer FUN_6012C2B8, role undetermined | Second CRC consumer = the RX state machine (§5) — role determined |

The organization is identical, as SERIESC predicted. The one
linkage difference SERIESC inferred ("4.79's walker is dispatched
through runtime-registered pointers") is **narrower than the
truth**: in 4.79 the builder and walkers are called through
ordinary pool-held pointers from statically visible state
machines; only the RX handler calls methods through the
descriptor record (and it sits in code Ghidra had not
function-analyzed, which is why the path looked invisible).

## 9. The new boundary — precise

Statically resolved by this stage: frame construction (all
kinds/funcs), both payload walkers and their three directories,
the CRC (both uses), the transmit step and its GPIO handshake,
the complete receive state machine, address classification, and
the link state machines that drive the builder.

Still runtime-mediated (the exact residue):
1. **Activation**: who posts the per-byte messages the RX handler
   consumes (UART ISR / driver task), and what ticks
   FUN_180a5d28/FUN_180a5c40 — the cadence source of the ~10 s
   burst is a timer/message registration, not code in this module.
2. **Descriptor registration**: no static pointer to @0x180a5ab0
   exists; the runtime learns the module through registration
   (stub FUN_180a5aa2, table @0x182FAC24).
3. **Demand content**: the staging buffers (0xFFF857F6…) are
   written by the decision side — the mirror/engine writes traced
   by stages L/N (FUN_181f4e60 bulk mirror et al.). Their producer
   semantics are the control-law stages' subject, not this one's.
4. **FUN_180a49a8** (the request API body, 0x180a49a8–0x180a4c99):
   entered from the control cluster via FUN_180a490e; only its
   entry wrapper was read.

## 10. What this gives the emulator

A complete code-derived template for the bus data plane in both
directions: frame formats per func, the CRC, the served tables'
field layouts (DIR-A members / DIR-C descriptors bind every field
to a live variable — a code-derived field map for 3B02/3B03/3B04/
3B05/400A/4202/0104/0302, complementing the infinitive layouts),
the demand tables' lengths and staging-buffer model, and the
receiver's validation/classification behaviour (including the
dictionary statistics bytes a real Ion maintains). The emulator
does not need the runtime-registered residue in §9 items 1–2 (its
own scheduler replaces it); item 3 is the control law itself.

## 11. Artifacts (firmware-re/stageAA/)

- scripts/DumpAB.java, DumpAC.java, DumpAD.java — census +
  decompile dumps; scripts/raw2.py — raw caller census;
  scripts/crc_test.py + out/crc_test.txt — CRC verification
  (first pass).
- out/dumpAB.txt — module map, FUN_180a44ee + FUN_180a5c40 +
  FUN_180a5d28 decompiles.
- out/dumpAC.txt — pool resolutions, both walkers, TX step,
  predicates, island listing 0x180a5800–0x180a5ab2.
- out/dumpAD.txt — directory bases, TX channel send, field
  formatter FUN_180a7e20, lookup functions, island listing
  0x180a53c0–0x180a5814.
- runAA3.sh / runAA4.sh / runAA5.sh + logs (all EXIT=0).

## 12. Explicit unknowns

- FUN_180a49a8's internals (request construction toward the
  builder's device records).
- The RX handler's invoker and the burst cadence source (§9.1).
- The physical meaning of the GPIO bits (FUN_180d1cd4's
  0xFFFE38BA bit 7 gate; FUN_180a403c's 0xFFFE38B6 bit 3 toggle) —
  register-level facts, roles inferred.
- FUN_180a7500's exact format conversion per format code
  (member/descriptor [+0xC]); it post-processes every walked
  field.
- DIR-B's 0307 length (3) is the directory's field for the
  class-0x3E record; whether other 0307 records/classes differ
  was not enumerated (first-match census).
- The relationship between the serializer's DIR-A (@0x182C1440)
  and stage F's binding group table (@0x182B5E3A) — same record
  geometry, different tables; why both exist was not determined.
