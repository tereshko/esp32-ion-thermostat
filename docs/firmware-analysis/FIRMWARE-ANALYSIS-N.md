# Firmware Analysis — Stage N: the 0305 construction path, bottom-up

**Target:** Ion (Infinity) control firmware `BINF0479`, image base
`0x18040000`, Renesas SH-2A (SuperH BE). Same image as stages A–M
(MD5 `e31903228bf39a4bc9c0a2a74192359e`).

**Task:** determine HOW the thermostat builds the `0305` demand frame,
given that stages D/K proved it is NOT built by the dictionary/binding
model. Route: bottom-up from the frame/TX layer — find the frame
builder, the table-id constants, the payload assembly, the burst
scheduler. A sibling stage (F) attacked the same writers top-down from
the descriptor tables; §11 records the convergence.

**Method:** all work on copies under `firmware-re/stageN/` (Ghidra
12.2 headless, project copy `stageN/proj` from stage B, no re-analysis
pass); custom census scripts (`stageN/scripts/`); independent
capstone disassembly of un-analysed code via the stage-N venv
(capstone 5.0.7); capture ground truth re-derived from `traces/`
directly. Every load-bearing fact is dual-verified (two independent
methods or two independent stages).

---

## 0. Headline results

1. **The frame builder / serializer is not in the analysed function
   set — proven by four independent exhaustive censuses** (§§2–5):
   no table-id immediates for the TX set *or* the serve set anywhere
   in 910,147 instructions; no bus-CRC implementation (both CRCs in
   the image are identified and both are non-bus, §3); no UART/SCIF
   register reference in the complete 115-function peripheral census
   (§4); no unclassified reader of the decision module's outputs
   (§5).
2. **The one new code object found bottom-up is a second CRC**: a
   complete CRC-16/BUYPASS (MSB-first, poly 0x8005) table
   @ `0x182AD53C` with its routine at `0x180524D8` in an un-analysed
   code island. It is **provably not the wire CRC** (numeric proof,
   §3.2) — a utility CRC whose consumer was not identified.
3. **`0305[11] = 0x78` verdict (dual-verified with stage F §6):**
   not a checksum; a constant configuration/capability byte of this
   installation, read at serialization time from a field that is
   zero until the system is commissioned/configured (§7).
4. **`0303`/`0307`:** neither has per-table construction code; `0307`
   differs from `0305` only in that the dictionary tracks a 1-byte
   object for it (stage F §5). The wire construction of all three is
   the same engine serializer — which is the unresolved boundary (§8).
5. **The burst scheduler is not isolated in code.** From captures
   (re-verified): tick ≈ 10 s, member order
   `0305 → 0403 → 0409 → 0307` at ~40 ms steps, with sub-schedules
   (`0307` lag, `0414` ≈ 20 s, `031D`) inside the tick (§9).
6. **Convergence with stage F: total.** F's top-down route and this
   bottom-up route terminate at the same boundary from opposite
   sides: the serializer is engine (Clarinox/Carrier-framework) code
   dispatched through runtime-registered pointers over RAM-resident
   device objects built at discovery; it exposes no per-table code,
   no payload data, and no statically resolvable pointer in flash
   (§§10–11).

---

## 1. Ground truth used (re-derived this stage)

**Frame format** (InfinitESP source, read as text; consistent with
all captures): 8-byte header
`[dst][dst_bus][src][src_bus][len][pid=0][ext=0][func]`, then payload,
then CRC-16 (init `0x0000`, reflected poly `0xA001`) little-endian.
For a register operation, payload[1..2] = table id BE16 and register
byte *i* sits at payload[i+3]; the capture files' `data` field holds
the register bytes directly.

**0305 census** (all `traces/*.jsonl`, this stage's own recount,
`reg == "0305"`):

| src | func | len | count | byte [11] |
|---|---|---|---|---|
| 0x20 | 0x0C | 12 | 652 | `0x78` |
| 0x20 | 0x0C | 12 | 22 | `0x00` (payload all-zero) |
| 0x1F | 0x0C | 12 | 3 | `0x00` (payload all-zero) |

- [FACT] 21 distinct payloads from src 0x20. Invariants across all
  steady-state writes: [1] = [3] = [6..10] = 0; [0] = heat stage,
  [2] = cool stage, [4..5] = CFM BE vary; [11] = `0x78`.
- [FACT] All 22 all-zero frames from src 0x20 fall in two
  commissioning windows: 11 in
  `sam-commissioning-20261029-143248.jsonl`, 11 in
  `sam-reseat-20261029-151123.jsonl`. The 3 frames from src 0x1F
  (SystemInit) are likewise all-zero. Zero payloads are therefore an
  *initialization-state* emission, not a steady-state variant.

---

## 2. The table-id constant hunt — exhaustive negative

**Method** (`PoolHunt.java` / `PoolHunt2.java`, `out/poolhunt.txt`,
`out/poolhunt2.txt`): every instruction of the image (910,147)
scanned for each target id in four encodings — 16-bit scalar
immediate, 32-bit scalar, 16-bit literal-pool load (POOL16), 32-bit
literal-pool load (POOL32). This covers `mov #imm`, `movi20`, and
PC-relative pool loads of the value — every way SH-2A code materializes
a constant.

### 2.1 TX set: 0x0303, 0x0305, 0x0307, 0x0605, 0x060D, 0x061E, 0x0403, 0x0409

[FACT] Every hit in the image is classified; none is a bus table id:

- `0x0305` scalar in `FUN_182693dc`: an assertion code pair
  (`0xAF1`, `0x305`) in a UI method — not a table reference.
- `0x0605` / `0x060D` / `0x061E` scalars cluster in
  `FUN_180e3dda`, `FUN_180e4f60`, `FUN_180e54c8`, `FUN_180e5b5c`,
  `FUN_180e6414` (region 0x180E…): these are **Sparkplug dictionary
  property IDs** in the contiguous family 0x5FC–0x628 (energy/cost
  computed properties). `FUN_180e3dda` decompiled
  (`out/decomp1/`): property setters/getters for IDs 0x619–0x628
  with fixed-point division by 1000. No bus involvement.
- `0x0307` POOL16 hits resolve to the cell `0x182AEF4D`, whose bytes
  `03 07 0b 0f 16 1e 28 3c 50 62…` are the head of a **base64 decode
  table** (the alphabet and the 0x7F-filled reverse table follow
  immediately; neighbouring strings: `g-templates/`,
  `/provision/cbor`, `/accepted`, `/rejected`). The two readers,
  `FUN_18078984` / `FUN_18078a48`, are base64 helpers
  (`out/decomp4/`); callers `0x180679c8`, `0x181da6f2`.
- `0x0403` / `0x0409`: no code hits at all outside data regions.

### 2.2 Serve set: 0x3B02, 0x3B03, 0x3B04, 0x3B05, 0x400A, 0x4202, 0x3E02

[FACT] **Zero** SCALAR or POOL32 hits for any of these ids in the
whole image. The thermostat's own served tables (the ones our node
polls and writes) are likewise never materialized as constants. Both
directions of the wire protocol are therefore driven entirely by
data (object records), never by per-table code — the same conclusion
stage F reached from the group-table side (§11).

**Consequence:** there is no construction site of the form "load
0x0305 near a builder call" to find. Whoever emits 0305 learns the
table id from a runtime object, not from the instruction stream.

---

## 3. The CRC question — two CRCs in the image, neither is the bus CRC

The wire CRC is CRC-16/MODBUS-flavoured: reflected poly `0xA001`,
init `0x0000`, transmitted LE (§1). A frame builder must implement
it (table, nibble table, or bitwise). Census of all its possible
static forms:

### 3.1 The reflected-A001 table @ `0x182C4164`

[FACT] Exactly one code consumer in the image: `FUN_180EA704`,
which CRCs a **fixed 30-byte** dictionary record inside the
dictionary publisher (stage D §3.2; re-confirmed this stage by xref,
`out/xref_crcuser.txt`). No variable-length consumer exists.
Nibble-table forms: none found. The scalar/pool value `0xA001`:
POOL16 hits are all artifacts of the jump-table cell `0x1823DC6C`;
stage F's independent pool-word scan (`0x0000A001`/`0xFFFFA001`)
found 5 hits, all in resource/string data ≥ `0x1831AE52`, zero in
code. Two methods, one negative.

### 3.2 NEW: a complete CRC-16/BUYPASS @ `0x182AD53C` — identified, and excluded

[FACT] A full 256-entry MSB-first CRC table exists @ `0x182AD53C`.
Dual verification: this stage regenerated the CRC-16/BUYPASS
(poly `0x8005`) table independently — **256/256 entries match**
(`out/crc_verify.txt`).

[FACT] Its only referencing pool cell is `0x1805252C`, loaded by the
instruction @ `0x18052500` inside an **un-analysed code island
`0x180524AC–0x180525DC`** (Ghidra created no function there;
XrefScript reports no references). Capstone disassembly of the
island (stage-N venv; `out/dis_crc_routine.txt`,
`out/list_crc_gap.txt`) shows the routine at `0x180524D8–0x1805252A`:
classic MSB-first loop `crc = (crc<<8) ^ table[((crc>>8) ^ byte)]`,
seed in r4 (0 → default `0xFFFF` via `movi20 #65535`), buffer r5,
length r6. Neighbours in the island are fixed-point helpers and
min-trackers — a utility library fragment.

[FACT — exclusion] This routine **cannot** be the wire CRC: on 200
random vectors its output differs from the wire CRC (reflected
`0xA001`, init 0) in **200/200** cases, for both seeds `0xFFFF` and
`0x0000` (`out/crc_verify.txt`). The two CRC families are different
algorithms; no seed choice reconciles them.

[NOT ISOLATED] The BUYPASS routine's consumer (a non-bus user —
plausibly a Clarinox utility for some other protocol/record) was not
identified; its callers were not exhaustively hunted because the
exclusion above makes it irrelevant to the frame path.

**Consequence:** the image's analysed code contains **no**
implementation of the wire CRC. The CRC step of frame construction
lives wherever the builder lives — outside static reach (§10).

---

## 4. The UART / peripheral census — no SCIF driver in analysed code

**Method** (`PeripheralHunt.java`, `PeripheralHunt2.java`):
for every analysed function, collect every peripheral-space value
(≥ `0xFFFE0000`) it references directly or through a literal pool.
Complete result: **115 functions** (`out/periph_all.txt`). Value
blocks present in the entire firmware's static references:

| block | refs | classification |
|---|---|---|
| 0xFFFE00xx–13xx | ~74 | INTC / CPG / MSTP / low system modules |
| 0xFFFE38xx–39xx | 236 | GPIO ports (panel hardware) |
| 0xFFFEC0xx | 11 | **CMT timer** (identified below) |
| 0xFFFEE0xx–ECxx | 19 ×4 | 4-channel byte-register module, 0x400 spacing (IIC-like; panel peripherals) |
| 0xFFFF74xx–7Axx | ~113 | display controller area |

[FACT] **No function references any address in
`0xFFFE8000–0xFFFEDFFF`** — the SCIF (serial) zone is statically
untouched. A polled or interrupt-driven UART driver in analysed code
would have to load its register base from a pool cell or immediate;
none does. (A driver addressed purely through a RAM-resident device
struct would leave no static reference — that possibility is exactly
the §10 boundary, not a gap in this census.)

**The 0xFFFEC000 module, identified register-by-register** (it was
the only unexplained peripheral cluster): it is the SH7269 **CMT
(compare-match timer)**, not a UART:

- `FUN_180bc6b6` (init ch0): ungates the module clock
  (`0xFFFE0418 &= 0xFB`, MSTP), sets IRQ priority nibble in
  `0xFFFE0C0C` (IPR), writes CMCOR0 = `0xEA6` (3750), CMCNT0 = 0,
  CMCSR0 bits (interrupt enable), sets CMSTR bit 0 (start ch0).
- `FUN_18127170` (init ch1): same clock/priority registers, CMCOR1 =
  `0x3A9` (937), CMSTR bit 1.
- `FUN_180bc748`: clears CMCSR0 bit 7 (the OVF flag).
- `FUN_1818e990`: computes `(overflow ? base+1 : base) × 0xEA6 +
  CMCNT0` — a **timestamp reader** built on ch0.
  (Decompiles: `out/decomp5/`; callers `out/callers4.txt`.)

A baud-rate register cannot take the value 0xEA6 (3750); a timer
period can. The module is a system timebase. Classified, excluded.

---

## 5. Readers of the decision module's outputs — all classified

Stage L mapped the producers: staging byte `0xFFF8CD49` ←
`FUN_180c54d8`; arbitration bytes CD4A/CD4C ← `FUN_180c5832`; demand
float CD44 ← `FUN_180c62fc` / `FUN_180c4322`. If a serializer in
analysed code consumed them, it would appear as a reader outside the
decision cluster. Census (`out/xref_ram.txt`):

- [FACT] **CD4C has zero xrefs in the entire image** — not even its
  own writer references it by absolute address; access is
  base+offset from the module's block base. An absolute-address
  consumer of CD4C does not exist.
- [FACT] CD44 readers outside the cluster: `FUN_180d4088`,
  `FUN_180d4114` (×4), `FUN_180d429c`, `FUN_180d4328` — all in the
  0x180D4xxx control-math region — plus the refresh itself.
- [FACT] C90C (the accumulator CD44 sums) readers: `FUN_181f4e60`,
  `FUN_180d208c`. `FUN_180d208c` / `FUN_180d2728` decompiled
  (`out/decomp2/`): 8-zone float demand distribution math — control
  side, not TX.
- [FACT] `FUN_181f4e60` decompiled (`out/decomp2/`): a **bulk
  mirror** — it copies dozens of values between the decision block
  (0xFFF8Cxxx) and a mirror region under lock/unlock
  (`PTR_FUN_181f50a8` / `PTR_FUN_181f50b4`), with memcpy moves of
  0x20/8/0x10 bytes (`PTR_FUN_181f5104`). Callers: `FUN_181f4308`,
  `FUN_181f8592`, `FUN_181f857c`, and sys_ctrl stubs. This is the
  Clarinox block-plumbing that keeps the engine's object view in
  sync with the control module — the values cross into engine space
  here, but no frame is assembled; serialization happens later,
  inside the engine, from the mirrored objects.
- [FACT] CD8C readers include `FUN_1804e4b6`, `FUN_1804fa1c`
  (setpoint max/select helpers; `FUN_18052354` decompiled — float
  select over a min-tracker `FUN_18052410` and `FUN_180d2728`) and
  `FUN_18226ab4` (UI). Region map: `out/funcmap_1804e_18053.txt`.

**Consequence:** every statically visible consumer of the decision
outputs is control math, UI, or the mirror plumbing. The hand-off to
the wire is the mirror/engine boundary — values leave static sight
inside `FUN_181f4e60`'s engine-side copies, and no analysed code
reads them back toward a UART.

---

## 6. Un-analysed code islands — census and pointer scan

The builder could in principle hide in code Ghidra never turned
into functions. Census (`GapHunt.java`, `out/gaphunt.txt`): **734
gaps ≥ 200 B** in `0x18040000–0x182C0000`. Controls:

- [FACT] The boot span `0x18040000–0x18048100` contains exactly 3
  Ghidra functions (stubs @ `0x180405FC`, `0x1804060C`;
  `FUN_1804807a`) over a 31 KB gap @ `0x18040620` that the vector
  table points into — the exception/stub + C-runtime area
  (`out/funcmap_boot.txt`).
- [FACT] Code-density scoring (capstone over each gap ≥ 1500 B:
  valid-instruction ratio, prologue count, call count) ranks many
  gaps as dense code. The densest, @ `0x18053ED4` (35 prologues /
  1 KB), was disassembled in full (`out/dis_18053ed4.txt`): it is
  assert-wrapped setpoint/control math (movi20 line numbers
  229/230/238/251…, constants 1400/2799/2801 = °C×100 bounds) —
  control side, no frame signatures (no header-shaped byte-store
  sequences, no CRC-table or peripheral pool loads).
- [FACT] **Pointer scan** (every BE32 word in the image whose value
  falls inside a gap ≥ 512 B; `out/gap_pointers.txt`): the
  heavily-pointed islands are all accounted for — descriptor-table
  → validator cluster @ `0x181666CC` (813 pointers; stage F §3),
  data region @ `0x182AB25A` (693; tables/strings of §2.1/§3.2),
  boot area @ `0x18040620` (333; vector table), and UI/dictionary
  code islands (pointed from 0x1830xxxx–0x1833xxxx name/pointer
  tables). **No static pointer from the descriptor table
  (`0x182B04D4`), the group table (`0x182B5E3A`), the member
  registry (`0x182B6AC8`), or any engine table targets an
  un-analysed island that could be a serializer.**

**Consequence:** if the serializer is compiled into this image at
all, it is reached only through pointers stored in RAM at runtime —
there is no flash-resident pointer to it. That is stage F's
registration boundary, reached independently from below.

---

## 7. The `0x78` byte — verdict

- [FACT] [11] = `0x78` in all 652 steady-state writes; [11] = 0 in
  exactly the 22 all-zero commissioning-window writes and the 3
  SystemInit writes (§1). [0]/[2]/[4..5] vary while [11] does not.
- [VERDICT] **[11] is not a checksum or CRC of the payload** — any
  function of [0..10] would differ between the all-zero payload and
  calling payloads; it does not. (Same verdict as stage F §6,
  reached from F's 1,811-write corpus and this stage's independent
  677-frame recount.)
- [VERDICT] [11] is a **constant configuration/capability byte of
  this installation** (`0x78` = 120), emitted by the serializer from
  a field that reads 0 before the responsible object is populated
  (commissioning windows, SystemInit) and `0x78` thereafter. The
  commissioning-window zeros are the discriminating evidence: the
  byte is *state*, not a code immediate — an immediate would be
  `0x78` in the SystemInit frames too.
- [INFERENCE, unproven] Semantics (blower/equipment size code, e.g.
  a CFM class, or a capability bitfield `0b01111000`) cannot be
  assigned without the producing code. For the 0x20 emulator this is
  moot: emitting `0x78` reproduces every observed steady-state
  frame exactly.

**Per-byte provenance of 0305, as far as static analysis reaches:**
[0] heat stage and [2] cool stage derive from the decision module's
staging/arbitration state (CD49/CD4A, stage L) via the mirror
plumbing (§5); [4..5] CFM is computed at runtime on the furnace side
of the model (stage J: no stored CFM value exists to copy); [11] is
the configuration byte above; [1], [3], [6..10] are structural
zeros. The exact instructions that place these values into the
frame buffer are inside the §10 boundary.

---

## 8. Do 0303 / 0307 share the path?

- [FACT] `0303`: absent from the unified catalog (stage K census)
  and has no binding group (stage F group table, 385 records,
  complete). Like 0305, it exists only as wire traffic.
- [FACT] `0307`: **has** binding groups — classes 0x3E/0x40/0x42,
  binding three **1-byte** objects @ `0x3C0D40B0/B1/B2` (stage F §5).
  But the binding op `FUN_180a8da2` is membership bookkeeping over
  RAM bitmaps; it never serializes (stage F §4.4). A group therefore
  means "the dictionary tracks a 1-byte object under this table",
  not "this layer builds the frame".
- [VERDICT] All three tables' wire frames are produced by the same
  engine serializer class of path: none of them has per-table code,
  payload data, or a constant anywhere in flash (§2), and the one
  mechanism that emits every other burst member is the engine's.
  The difference between 0307 and 0305 is bookkeeping visibility,
  not construction. Strictly: the shared serializer is *inferred*
  from the total absence of any alternative, not observed.

---

## 9. The burst scheduler — capture-side facts, code-side boundary

[FACT, from captures, re-verified this stage on
`coldstart-20261029-125733.jsonl`] One tick, dst 0x44, func 0x0C:

```
16:59:02.649Z  0305
16:59:02.690Z  0403   (+41 ms)
16:59:02.735Z  0409   (+45 ms)
16:59:02.780Z  0307   (+45 ms)
next tick 16:59:12.000Z  (period ≈ 9.35–10 s)
```

- [FACT] Sub-schedules exist inside the nominal 10 s burst: in the
  second observed tick `0307` lagged ~0.9 s behind `0409`; `0414`
  runs on a ≈ 20 s cadence; `031D` appears singly
  (16:59:07.684Z). The "burst" is a set of per-object engine timers
  with a common ~10 s quantum, not one monolithic routine emitting
  four frames back-to-back.
- [NOT ISOLATED] The posting mechanism in code. Stage G's sys_ctrl
  supervision FSM and its class-6/class-7 handlers drive the
  decision refresh, but no analysed code posts a transmit. The
  scheduler is part of the same engine layer as the serializer
  (§10): per-object timers over the RAM device objects.

---

## 10. The exact unresolved boundary

The application image contains the *schema* (descriptor table), the
*bookkeeping* (binding groups/members/bitmaps), the *decisions*
(stage E/L module), and the *mirror plumbing* that copies decision
outputs into engine object space (`FUN_181f4e60`, §5). It does not
contain — anywhere statically reachable — the *serializer*: no
frame builder, no TX queue, no wire-CRC routine, no UART driver, no
burst scheduler, and no flash-resident pointer to any of them
(§§2–6). The serializer is engine code dispatched through
**per-class transmit method pointers registered at runtime into RAM
dispatch structures over device objects built at discovery (RAM
`0x3C0D…` space)** — structures that do not exist in the flash
image. The single unresolvable computed value is that registered
method pointer. (This is stage F §7.3's boundary, confirmed
independently by every bottom-up census in this stage.)

**Why the dynamic route (stage M harness) could not cross it:**
the PCode emulator needs a function entry point and its input
state. The serializer has no isolated entry point, and its inputs
are the discovery-built RAM objects (stage M's own blocker: runtime
state is built by discovery and must be seeded by hand; cold boot
is not a goal). Emulating the *decision* module was already done
(stage M, 23/23 vectors) — its outputs' only readers are internal
(§5), so emulation from that side also terminates at the mirror
boundary. The remaining pivot is on-device: stage F §8's watchpoints
(UART TX FIFO write breakpoint during a burst; watchpoints on
`0xFFF8CD49/CD4A/CD44` readers; dumps of the furnace class-0x40 /
ODU class-0x52 records in `0x3C0D…` space). Stage M already recorded
why on-device debug (E10A-USB) is rejected for the live unit: it is
the home's only heating control; a spare unit would be required.

---

## 11. Convergence with stage F (and a correction F makes to stage D)

**Convergences (independent routes, same facts):**

1. No per-table code or payload data for 0305 anywhere in flash
   (F §7.2.1 = N §2).
2. No locatable wire-CRC routine; the only A001 table serves the
   dictionary publisher (F §7.2.3 = N §3.1, two different scan
   methods).
3. `0305`/`060D` have no binding groups; `0605` groups exist only
   for classes 0x56/0x57/0x5B — not our ODU (class 0x52) (F §5;
   consistent with N §2's zero-immediate result and stage J's
   no-slot-writer result).
4. `0x78` is not a checksum; constant configuration byte (F §6 =
   N §7; N adds the commissioning-window evidence).
5. The boundary is the runtime-registered engine transmit method
   (F §7.3 = N §10), and the dynamic pivot is on-device watchpoints
   (F §8 = N §10).

**No contradictions** between the two routes were found. Stage I's
headline on the writers ("programmatic, per stages D–F") is
consistent as well.

**Correction F establishes to stage D (flagged for the record):**
the table stage D parsed from `0x182B5E40` as a 7-byte-record
"binding directory" is read by code from base **`0x182B5E3A`** as
8-byte **group** records
`[tableHi][tableLo][sub/class][flags][member_start BE16][member_count][pad]`
over a member registry @ `0x182B6AC8`. Stage D's "field-store
offset" in those records is a **member index**, proven decisively
by F §4.3 (member[324].buf = `0x3C0D41D0`, exactly stage C's
independently recorded SAM buffer for the (0x030D, 0x42) call).
This corrects the directory *parse*; stage D's code-based findings
(the coil commit functions, the catalogue of burst tables' absence)
are unaffected — indeed the absence conclusion is strengthened,
since the group table is now fully decoded and 0305 is absent from
it as a group, not merely as a directory row.

---

## 12. Not isolated (explicit list)

- The frame builder / serializer function — **not isolated** (does
  not exist in statically reachable code; §10).
- The TX queue and the UART (SCIF) driver — **not isolated** (no
  static register reference exists; §4).
- The wire-CRC routine — **not isolated** (both in-image CRCs
  identified and excluded; §3).
- The burst scheduler / per-object transmit timers in code —
  **not isolated** (capture-side behaviour fully characterized;
  §9).
- The per-byte assembly instructions for 0305 (which mirror/object
  fields land in [0], [2], [4..5]) — **not isolated**; provenance
  is established to the mirror boundary only (§§5, 7).
- The semantics of `0305[11] = 0x78` — **not isolated** (excluded:
  checksum; established: configuration state byte, §7).
- The consumer of the CRC-16/BUYPASS routine @ `0x180524D8` —
  **not isolated** (excluded from the bus path by proof; §3.2).
- The 0307 lag mechanism (~0.9 s in one observed tick) — observed,
  mechanism **not isolated** (§9).
- Whether the serializer is compiled into this image at all
  (reached via RAM-registered pointers) or lives in a separately
  loaded engine component — **not determinable from the image**;
  either way it is outside static reach (§§6, 10).

## 13. Artifacts (all under `firmware-re/stageN/`)

- `scripts/`: `PoolHunt.java`, `PoolHunt2.java` (constant censuses),
  `PeripheralHunt.java`, `PeripheralHunt2.java` (peripheral census),
  `GapHunt.java` (un-analysed island census), `FuncMap.java`,
  `ListRange.java`; runners `runN.sh`–`runN11.sh` + logs; `disx.py`
  (capstone disassembler with pool annotation); `venv/` (capstone
  5.0.7); `proj/` (Ghidra project copy).
- `out/poolhunt.txt`, `out/poolhunt2.txt` — constant censuses (§2).
- `out/crc_verify.txt` — BUYPASS table verification (256/256) and
  the wire-CRC exclusion test (200/200) (§3.2).
- `out/dis_crc_routine.txt`, `out/list_crc_gap.txt` — the CRC
  island disassembly (§3.2).
- `out/periph_all.txt`, `out/peripheralhunt.txt` — the 115-function
  peripheral census (§4).
- `out/xref_ram.txt` — decision-output reader census (§5);
  `out/decomp1/`…`out/decomp5/` — decompiles cited (property
  cluster, mirror `FUN_181f4e60`, zone math, base64 helpers, CMT
  inits/timestamp); `out/callers1.txt`…`out/callers4.txt`.
- `out/gaphunt.txt` — 734-gap census; `out/gap_pointers.txt` —
  pointer-scan summary (§6); `out/dis_18053ed4.txt` — densest-gap
  disassembly; `out/funcmap_1804e_18053.txt`,
  `out/funcmap_boot.txt` — region function maps.
