# EMULATOR SPEC — replacing the Ion thermostat (0x20) on the Carrier/ICP bus

Implementation-ready specification for a from-scratch reimplementation of the
ICP Ion SYST0101CW wall control (firmware v4.79, CESR******-**.79) as bus
address **0x20**, for one specific installation:

- Furnace / air handler: Heil **G80CTL1352422A2**, 2-stage gas, 107K BTU/H
  (bus 0x44, canonical device class 0x40) [P §7.1]
- Outdoor unit: Heil **HVA960GKA201**, variable-speed AC, 60K (5-ton),
  cooling-only, no reversing valve (bus 0x53, canonical class 0x52) [P §7.1, T §0]
- Indoor coil: **EN(A,D)4X61** [P §7.1]
- **Single zone.** No heat pump, no aux/electric heat, no zoning. [Y §0]

An engineer (or ESPHome / custom-component author) can code from this
document alone. Every normative statement carries a provenance tag:
[Map] = THERMOSTAT-PROTOCOL-MAP.md (capture evidence), [O] [P] [Q] [R] [S]
[T] [U] [V] [Y] [AA] [B7] = the corresponding FIRMWARE-ANALYSIS stage,
[Audit-2] = FIRMWARE-AUDIT-2.md ruling. **[INF]** marks inference, with
strength where the source gives one. Two source corrections are applied
throughout and are part of this spec:

- **Stage Q's mode words are reversed in its prose** — mode 1 = HEAT,
  mode 2 = COOL everywhere. This spec uses the corrected labels only.
  [Audit-2 §2.3]
- **Stage AA §7's DIR-B lengths/staging addresses are first-record
  (class 0x3E/0x51) values.** For this installation the class-0x40/0x52
  records govern (§2.4). [Audit-2 §3.1]

Conventions: all temperatures °F unless noted; "burst" = the ~10 s command
burst of §1.3; table ids are 4-hex-digit register names (e.g. `0305`);
payload byte offsets are 0-based within the payload.

---

## 1. Role & bus behaviour

### 1.1 Role

- The emulator **is** the thermostat: bus address **0x20**, the sole
  initiator on the bus in steady state. The furnace and ODU never transmit
  unsolicited and never read the thermostat; they only answer. [Map (a)]
- Physical layer: RS-485, **38400 baud, 8N1** [project-established, phase-1
  captures]. Half-duplex: never transmit while receiving (§2.5). [AA §3]
- The poll schedule is also the emulator's **presence signal**: the ODU
  returns to standby ~2 min after the last valid communication (§8.3), so
  the cadence of §1.2–§1.3 is part of the protection envelope, not a
  cosmetic rhythm. [Y B-19, §9 rule 3]

### 1.2 Poll schedule (steady state)

All reads are func `0x0B` with empty payload; answers are func `0x06`.
Periods are medians and drift (the ~11 s tier ranges 9.9–12.7 s); treat
them as Ion-faithful targets, not exact clocks. [Map (a), U B8]

| Tier | Reads (→ answer summary) |
|---|---|
| ~3 s | `0104`→44 (120 B identity), `0306`→44 (10 B IDU status; blower RPM = BE16 [1..2]), `030A`→44 (14 B, constant `014F4F02001F006B000010100115`), `0104`→53 (120 B identity) |
| ~5 s | `0302`→53 (24 B TLV sensors, raw/16), `0303`→53 (TLV pressures), `0307`→44 (3 B, always `000000`), `0413`→44, `041B`→44, `0604`→53 (target RPM [0..1], current RPM [2..3]), `0608`→53 (EXV % [2], requested CFM BE16 [5..6]), `061F`→53 (81 B refrigeration block) |
| ~7 s | `0404`→44, `040D`→44 |
| ~10 s | **command burst (§1.3)** + reads `031F`/`0320`/`0321`→53, `060A`→53 |
| ~11 s | `030D`→44 (7 B zeros), `0316`→44 (IDU config), `0402`→44, `0409`→44 (read), `0304`→53 (16 B), `030D`→53, `060E`→53 (actual stage index [0]) |
| ~17 s | `0304`→44, `0602`→53 |
| ~17–20 s | `0310`/`0311`→53; writes `060B`→53 and `0414`→44 (§7) |
| ~29 s | `0625`→53 |
| ~31 s | `030E`→44, `0310`/`0311`→44, `030E`→53; write `031D`→44 (1 B `01`, every ~30 s) |
| ~60 s | broadcast writes to **F1**: `0202` (3 B) and `0203` (3 B) — SYSTIME (thermostat-owned time/date) |
| irregular | `0302`→44 (12 B, constant payload `041100000000000000000000`), gaps 0.4–28 s, median ~5.7 s |

### 1.3 The command burst (~10 s)

Every ~10 s (median 10.00 s, range 9.0–11.2) the thermostat refreshes
**all** of the following in one burst. Nothing is event-driven: mode and
setpoint changes take effect by the *next* burst carrying new values.
[Map (a), Y §7]

To furnace 0x44 (internal spacing ≈45 ms per member: `0305`, `0403`,
`0409`, `0307`) [U B7; N timeline]:

| Reg | Len | Idle payload | Content |
|---|---|---|---|
| `0305` | 12 | `000000000000000000000078` | **The demand write** (§5.6): [0] heat stage, [2] cool stage, [4..5] BE16 blower CFM, [11] = `0x78` state byte (§3.4) |
| `0403` | 4 | `00010100` | constant in every scenario; replay verbatim |
| `0409` | 4 | `00010000` | constant; replay verbatim |
| `0307` | 4 | `00000000` | constant write (distinct from the 3 B `0307` read answer) |

To ODU 0x53 (every burst, in **all** modes, heat and fan-only included;
wire order as written — this group follows the furnace group by
≈5.7 s): [T §4]

| Reg | Len | Idle payload | Content |
|---|---|---|---|
| `0610` | 4 | `00000000` | constant; replay verbatim |
| `0612` | 10 | `22B80000000000000000` | constant; replay verbatim |
| `0605` | 7 | `00000000000001` | compressor capacity command (§6.1) |
| `061A` | 1 | `01` | constant; replay verbatim |
| `060D` | 1 | `00` | call-armed flag: `02` during any heat or cool call, `00` idle/fan-only (§6.2) |
| `061E` | 9 | `0F3FD851EC06000000` | coil-parameter frame (§6.3) |

### 1.4 Timing tolerances

- Request→response latency on this bus: median 19 ms, p90 48 ms. Poll in
  bursts (~15–50 ms between requests); expect answers within ~50 ms.
  [Map (a)]
- ~0.1 % of steady-state reads go unanswered (1 of 879 in the reference
  sample); the loop simply moves on —
  no retry storm, no fault. Reproduce this tolerance. [Map (a), U §4]
- A healthy thermostat never goes > ~3 s without transmitting in steady
  state (measured max TX gap 2.81 s), > ~5 s even mid-wizard (4.90 s).
  [Map (d)]
- SAM-facing answers (§4) should complete within ~50 ms of the request.
  [V §3]

---

## 2. Frame layer

### 2.1 Wire frame layout

Derived from the firmware's frame builder `FUN_180a44ee` [AA §3] and
confirmed against captures [Map]:

| Bytes | Content |
|---|---|
| [0..1] | destination field — the destination address in both bytes for normal frames (broadcast = `F1 F1`) |
| [2..3] | source field — the sender's own address bytes (for the emulator: 0x20) |
| [4] | length = **3 + payload length** (the 3 counts the prefix: `0x00`, table-hi, table-lo) |
| [5] | device-record field rec[2] (0x00 in all observed thermostat traffic) |
| [6] | device-record field rec[3], **XORed with 0xC0 when rec[3] ≠ 0**; 0x00 in observed traffic |
| [7] | function code (§2.2) |
| [8] | `0x00` |
| [9..10] | table id, big-endian (hi, lo) |
| [11 .. 10+N] | payload (N bytes; omitted for read requests) |
| last 2 | CRC (§2.3), low byte first |

Total frame size = 11 + N + 2. The builder has two special single-byte
forms (kind 4: func `0x06` with one `0x00` byte; kind 5: func `0x15` with
one byte = low byte of the table id) and a kind 6 (single raw `0x00` byte,
**no CRC**) [AA §3]; none of these is needed by the emulator except
possibly the exception form, which §2.6 tells it not to send.

### 2.2 Function codes

| Func | Meaning | Use |
|---|---|---|
| `0x0B` | read request | emulator → equipment, empty payload [Map] |
| `0x06` | read response | equipment → emulator; also the emulator's serve function (§4) [AA §3] |
| `0x0C` | write | all command/served writes; **writes are never acknowledged** [Map, V §1.1] |
| `0x15` | exception | exists in the builder (kind 5) [AA §3]; never observed on this bus in either direction [Map, V §1.1] — see §2.6 |
| `0x0D` | — | **does not exist in this dialect.** Never emit an acknowledgement frame. [V §3 item 4] |

These are the only function codes that appear anywhere in the capture
archive: `0B`, `06`, `0C`. [Map]

### 2.3 CRC

The wire CRC is computed by `FUN_180a42dc` [AA §1]:

- Algorithm: CRC-16, reflected polynomial **0xA001** (0x8005 reflected),
  **init 0x0000**, no final XOR — the standard reflected-0xA001 CRC.
  Bit-wise form (exactly equivalent):

  ```
  crc = 0
  for each byte b of the frame (all bytes before the CRC):
      crc ^= b
      repeat 8 times:
          crc = (crc & 1) ? (crc >> 1) ^ 0xA001 : crc >> 1
  ```

- The firmware computes it nibble-wise: `crc = crc>>8 ^
  tableA[((crc ^ b) & 0xF)] ^ tableB[((crc ^ b) & 0xF0) >> 4]`, with
  tableA @0x182B598C and tableB @0x182B59AC in the image; the function's
  return value is byte-swapped and the builder writes it high-byte-first,
  so **the true CRC lands on the wire little-endian (low byte first)**.
  [AA §1, §3]
- The CRC covers the whole frame from byte [0] through the last payload
  byte (receiver validates over `buffer, count − 2`). [AA §5]
- Verification status: the routine equals the standard reflected-A001 CRC
  on 2000/2000 random buffers and 1532/1532 gofinity wire frames,
  and is self-consistent with the standard form on 101,352 frame
  bodies reconstructed from this installation's captures. Wire-level
  verification on the installation's own captures is impossible —
  the JSONL corpus stores no CRC bytes — and the verification corpus
  rules that half UNVERIFIABLE (verification/VERIFY-crc.md); the
  wire proof is the gofinity capture. [AA §1]

### 2.4 Frame construction — directories and staging buffers

The builder appends payloads by one of three directories [AA §4, §7]:

- **DIR-A @0x182C1440** — field-walk for writes addressed to the thermostat
  itself (dst == 0x20): the writable self-table set of §4.2.
- **DIR-B @0x182BF1D0** — blob copy for writes to equipment: the payload is
  memcpy'd verbatim from a RAM staging buffer; there is **no per-table
  construction code**. The emulator equivalent: maintain one staging
  buffer per demand table and copy it into the frame at burst time.
- **DIR-C @0x182BBD58** — descriptor-driven serialization for read
  responses (§4.1). If a DIR-C lookup fails and the request's record flag
  is set, the firmware copies a canned payload from a static table
  @0x182AFC50 (18 records × 120 B) [AA §4.2]; the emulator may omit this
  fallback (it exists for tables the emulator will serve explicitly).

DIR-B records **for this installation's device classes** (canonicalizer:
0x44→0x40, 0x53→0x52 [AA §7 as corrected by Audit-2 §3.1]):

| Table | Dst class | Len | Staging buffer (Ion RAM; emulator: own) |
|---|---|---|---|
| `0305` | 0x40 | 12 | 0xFFF85802 |
| `0307` | 0x40 | 4 | 0xFFF85841 |
| `0605` | 0x52 | 7 | 0xFFF85C8D |
| `060D` | 0x52 | 1 | 0xFFF85CCE |
| `061E` | 0x52 | 9 | 0xFFF85D44 |
| `3E02` | 0x0E | 1 | (boot broadcast only, §3.2) |

The demand tables (`0305`/`0605`/`060D`) are **write-only**: they are
absent from DIR-C and are never read back. [AA §7]

### 2.5 Transmit and receive rules

Transmit [AA §3]:

- The builder transmits only when its receiver is idle (received-byte
  counter == 0) and a bus-free GPIO predicate holds; an RS-485
  direction/enable line is toggled at transmit time [INF for the pin's
  physical meaning]. Emulator rule: **never transmit while a frame is
  being received; assert the RS-485 driver only for the frame's
  duration.**
- Frames are built from 12-byte runtime device records (dst, kind, table
  id); kinds map to funcs: 1→`0x0B`, 2→`0x0C`, 3→`0x06`, 4→`0x06`
  (single byte), 5→`0x15`, 6→raw byte, no CRC. [AA §3]

Receive [AA §5] — the firmware's receiver is a 15-state byte-at-a-time
state machine; the emulator's receiver must behave equivalently:

1. Assemble header bytes [0..4]; the length byte [4] > 0xF8 is rejected.
2. Collect payload per the length byte, then the 2 CRC bytes (assembled
   hi<<8, then +lo).
3. Validate: CRC over (frame, count − 2) must equal the received trailer.
   On mismatch: **drop the frame silently** (the firmware additionally
   bumps internal error statistics — not wire-visible; omit).
4. On match, classify: **src == own address** (own echo / link handling —
   ignore for control), **dst == own address** (process: serve reads per
   §4, accept writes per §4.3), **broadcast** (frame[0]==frame[1] and
   frame[0] > 0xF0, e.g. `F1 F1` — process as broadcast, e.g. SYSTIME).

### 2.6 Error and exception policy

- Reads of unserved registers get **no answer** — silence, matching every
  locally observed behaviour on this dialect. Do not emit `0x15`
  exceptions: the `0x15`/`0x04` style is attested only on another
  equipment generation. [V §3 item 10]
- Writes are never acknowledged, to anyone, ever. [Map, V §3 item 4]
- Reads of absent devices are simply never answered — by the equipment
  (§1.4) and by the emulator alike. [V §1.1]

---

## 3. Boot & commissioning sequence

Ordered script [U §1, §5]. Times are from a whole-system power restore
(t=0 = power on); the emulator runs this on its own power-up.

### B0 — Listen first

- The furnace boots faster than the thermostat and transmits autonomous
  bursts of `44→45 READ 030A` (×6, ~45 ms apart) at ≈ +0 / +62 / +124 /
  +185 / +248 s, then never again. This is the furnace↔sub-unit channel.
  **Do not answer it; it is not addressed to the thermostat.** [U B0]
- A diagnostic node at 0x93 may read `3B05` from as early as +0.28 s; it
  tolerates no answer until the thermostat is up (first answer at
  +196.6 s in the reference capture) and simply retries on its 300 s
  schedule. [U B0, Map (b)]

### B1 — SystemInit broadcast triplet (t ≈ +6 s)

Come up under the temporary discovery persona **0x1F** and emit exactly
three broadcast writes to **F1**, in this order (byte-identical in two
independent systems' captures) [U B1]:

| # | Frame | Payload |
|---|---|---|
| 1 | `1F→F1 WRITE 0305` | 12 × 0x00 |
| 2 | `1F→F1 WRITE 3E02` | 1 × 0x00 |
| 3 | `1F→F1 WRITE 0605` | 7 × 0x00 |

Meaning: "everything off, identify yourselves". The 0x1F phase is a
(re)discovery ritual, not only a cold-boot one: in the re-commissioning
capture it began after 78.23 s of total 0x20 silence. [U B1]

### B2 — The 0x1F sweep (≈ +6 … +16.7 s)

Cadence ~95 ms per probe. Retry rule: **unanswered → sent twice**
(the dominant pattern — 34 of 43 unanswered targets; the
zone/damper-class addresses 46/5A/5C receive a second double-pass,
×4, and two targets were sent once; VERIFY-boot refuted "exactly
twice" as a universal rule); **answered → sent once** and the device
is registered. [U B2, Map (c)]

Probe programme (order as captured; the emulator needs the same coverage
for its device registry — the registry is RAM-only and rebuilt every
boot [U §3.2]):

- `030A`→20 ×2 (self/persona check; no answer expected — prober and
  thermostat are the same device)
- `030D`, `031B`→46; `0326`, `0327`→5A, 5C
- `0404`→46, 5F, 69
- `0104`→21…28 (secondary thermostats), →5F, 69, **92, 94** (SAM slots)
- `0302`→60, 61 (zone controllers)
- `0307`→3F, **44 (answers)**, 46; `0402`→3F; `041C`→**44 (answers)**;
  `041F`→3F, 44; `0438`→3F
- `061F`→**53 (answers)** — the ODU is first touched here
- `3405`→80 (NIM)
- Second pass: `0104`→3F, **44 (answers, 120 B)**, 46, 58, **53 (answers,
  120 B)**, 55, 5A, 5C, 60, 61, 80; `0306`→3F, **44 (answers)**;
  `030A`→3F, **44 (answers)**, 46
- 3E-family hunt: `READ 3E01` ×8 and `3E0A` ×8 toward the class-0x50 slot
  via bus 0x58 — all unanswered on this installation (our ODU refuses the
  3E family). [U B2]

Build the device registry from the `0104` answers received: identity
strings, CESR numbers, device class per address. Discovery results are
classified by the device-type word (field-store offset 1, mask 0x7C00
routing). [U B2, §3.1]

**Do not probe 0x0E.** This Ion never touches 0x0E in 101,352 captured
frames; 0x0E is a reserved discovery slot for a 3E-family two-capacity
ODU on other systems. Omit the 0x0E hunt entirely (the 0x58
3E-family hunt in the B2 programme above is this unit's own and
stays). [U §2]

### B3 — Persona handoff 1F → 20 (t ≈ +16.7 s)

Last 0x1F frame at +16.67 s; first 0x20 frame at +16.69 s. The handoff is
seamless, mid-programme; **no announcement frame marks it** — simply start
sourcing frames from 0x20. [U B3]

### B4 — The 0x20 second sweep + wizard scans (≈ +16.7 … +61.8 s)

- Re-run the discovery programme as 0x20, interleaved with the first
  steady-state polls. First steady read at +23.95 s (`20→44 READ 0104`).
  Retries escalate **×2 / ×4 / ×8** per (address, register) for unanswered
  probes. Last sweep probe at +61.76 s; **boot-to-steady ≈ 62 s**. [U B4]
- Wizard/equipment-ID scans ride along (deep table reads at candidate
  addresses: 46: `0403/0404/0407/040B/040C/040F`; 60/61: `3405`; 5F/69:
  `0404`; SAM hunt `0104` + `030D`→92 repeated). Max thermostat TX gap in
  this phase: 4.90 s. [U B4]
- Boot-only write: `20→44 WRITE 0418`, payload `000000`, ×2, at ≈ +62 s —
  in boot/install windows only, never in steady state. [U B4]

### B5 — Per-device configuration writes

- **Commissioned reboot (the normal case): no configuration writes at
  boot** beyond B4's `0418`. The furnace is configured by being *read*:
  identity `0104`, config `0316`, status per the poll tiers. The ODU
  likewise receives no boot-time config writes; its orders arrive via
  the steady burst, which carries the coil parameter in `061E` from the
  very first burst. [U B5]
- **`031C` writes are first-commissioning only.** On a foreign system's
  first commissioning the thermostat writes `031C` to furnace and ODU
  (byte 0 = a per-device incrementing counter; exact value semantics
  unresolved [UNK]). Our Ion has never written `031C` in 101,352 frames:
  a reboot of an already-commissioned unit skips the deep commissioning
  sequence entirely, gated by the commissioning-complete latch
  (field-store offset 5 = 'Z'). **Emulator rule: emit `031C` only inside
  a first-commissioning flow; a commissioned reboot must not emit it.**
  [U B5, B10]

### B6 — The coil commit

The indoor coil is **not learned from the bus**. It is selected at
commissioning (dealer/wizard "Indoor Evaporator Selection") and resolved
against the firmware's built-in coil catalogue: EN(A,D)4X61 → parameter
**1.69** (float32 0x3FD851EC), committed into the field store (fields
0x59F / 0x1C7C / 0x1C7D / 0x1C7E; catalogue index in field 0x9A).
Thereafter every `061E` write carries it (§6.3). **Emulator rule: persist
the coil selection (§3.5); derive the `061E` payload from it; never
re-derive it from bus traffic.** [U B6, D via U]

### B7 — First demand

- First func-0C write of any kind at **+39.10 s** in the reference
  capture — but it is only the SYSTIME broadcast. The first
  device-directed command write is `0418`→44 at +62.0 s; the first
  `0305` at +71.65 s. (Verification addendum 2026-11-26: U B7's
  "first command burst +39.1 s" label is refuted by the capture.)
- `0305` byte [11] is the thermostat object's **state byte: 0x00 before
  commissioning completes, 0x78 after**; it is not a checksum. All-zero
  `0305` payloads occur only in commissioning windows. [U B7]

### B8 — Steady state (reached ≈ +62 s)

Enter the §1.2 poll tiers and the §1.3 burst. Link behaviour to match:
~0.1 % of reads unanswered is normal; max steady TX gap 2.81 s. [U B8]

### B9 — Obligations toward other bus citizens

- **Diagnostic node 0x93:** reads `3B05` every ~300 s; answer 11 zero
  bytes (§4.1). [U B9]
- **SAM slot (0x92/0x94):** discovery probes both (`0104`, `030D`);
  presence is an internal binding outcome, not a bus handshake. See §4.4
  for the full SAM-facing contract. A separate SAM-persona device must
  observe a 180 s transmit holdoff after the last 0x1F frame — that
  constrains a co-resident SAM node, not the emulator itself. [U B9, V §4]

### B10 — Persistence

Persist across power cycles (the field store is a flat NVRAM byte array,
base 0x3C0E4A20 in Ion; the emulator needs equivalent non-volatile
storage) [U §3.2, P §1]:

- offset 1 — equipment class word (§9)
- offset 5 — commissioning-complete latch ('Z')
- offsets 0x23 / 0xC4 — accessory (B36/SAM) presence bytes
- offset 0x9A — coil catalogue index; offsets 0x59F / 0x1C7C–0x1C7E —
  committed coil parameter set
- offsets 0x1BC–0x1C3 — furnace config mirror (from `0316`; refreshed
  from the bus, but stored) (firmware-side claim: captures show the `0316` read, not where the values land — UNVERIFIABLE from captures, VERIFY-boot claim 8)
- all user/dealer settings: profiles and setpoints (the `400A` rows),
  dictionary settings (lockouts, latch, staging limits…), dealer info
- descriptor defaults for any field never set (factory defaults;
  e.g. both class words default 0x0000, R byte defaults 24) [P §1]

**RAM-only, rebuilt every boot (do NOT persist):** device objects and
their binding state, the active-address bitmap, demand/staging runtime
state, the `0305` state byte 0x78 (derived: 0 until commissioned, 0x78
after). [U §3.2]

### Failure behaviour at boot (what is established)

- Unanswered discovery probes never block boot (×2/×1 in the 1F sweep,
  ×2/×4/×8 in the 0x20 phase, then move on). An entirely absent expected
  device is retried cyclically with no fault and no effect on steady
  state. [U §4]
- At *first* commissioning, a missing indoor or outdoor unit blocks the
  wizard with a named screen ("OUTDOOR UNIT NOT IDENTIFIED" + a manual
  identification procedure). [U §4, LIT]
- Whether a *commissioned* unit that boots with the furnace or ODU
  absent re-enters any wizard step is **[UNK]** — live-test item (§11).
  [U §4]

---

## 4. Served tables — what the emulator answers

In steady state the furnace and ODU ask 0x20 **nothing — zero frames**.
The serve obligations come from three other actors: the diagnostic node
0x93, a SAM at 0x92, and (during boot) the discovery process itself.
[Map (b)]

### 4.1 Read surface (func `0x06` responses)

Serve the following tables to any reader, at bus rhythm (answer within
~50 ms; Ion's median request→response is 19 ms) [V §3 item 1]:

| Table | Len (wire) | Content policy |
|---|---|---|
| `0104` | 120 | **Real identity, verbatim** (§4.5) [Map (b)] |
| `0302` | 32 | own sensor block (DIR-C serve size — see note below) |
| `3B02` | 29 | **29 B, all zeros** (Ion-faithful default, §4.4) [V §1.1] |
| `3B03` | 150 | **150 B, all zeros** (same policy) [V §1.1] |
| `3B04` | 11 | 11 B, all zeros (no vacation state) [V §1.1] |
| `3B05` | 11 | 11 B, all zeros (no accessories configured) [V §1.1] |
| `400A` | 35 | **Real data** — zone-1 comfort profiles, 5 activities × 7 B (§5.7) [Map (b)] |
| `4012` | 7 | Real vacation settings [V §1.1] |
| `4202` | 72 | Real fault log (72 B observed; nominal layout 10×7 B) [Map (b)] |

The code-derived serve directory (DIR-C @0x182BBD58) lists: `0104` (120),
`0302` (32), `0303` (24), `0304` (24), `0307` (24), `061E` (9), `3B02`
(29), `3B03` (150), `3B04` (11), `3B05` (11), `400A` (35), `4202` (72)
[AA §7]. **Resolved (verification addendum 2026-11-26):** the DIR-C
length field is the payload size of the frame **the thermostat itself
builds when serving the table** (its own serialized image size, bound
to its RAM mirrors 0xFFF821xx). Every table the thermostat actually
serves on the wire matches DIR-C exactly (3B02 29, 3B03 150, 0104 120,
3B04 11, 3B05 11, 400A 35, 4202 72). The smaller sizes in Map (a)
(0302 = 24, 0304 = 16, 0307 = 3) are the *equipment's* answers to the
thermostat's reads and are per-device (0302: ODU 24 B / furnace 12 B;
0304: ODU 16 B / furnace 8 B; 0307: furnace 3 B) — they do not govern
what 0x20 serves. For serving, the **DIR-C sizes govern**; `3B02`'s
DIR-C/DIR-A member binds store buffer 0x3C0D8D7D with
length 29, matching the wire exactly [AA §7, Audit-2 E-18].
Serve-set policy: the table above is the wire-attested serve set plus `0302` (DIR-C). The remaining DIR-C entries (`0303`, `0304`, `0307`, `061E`) are code-derived serve images with no observed external reader; an emulator serves them at DIR-C sizes if read.

Not every read is answered even by Ion: in the SAM captures ≈4 % of
`3B02`/`3B03` polls were silently dropped (79/1,811 corpus-wide;
≈2.8 % in clean steady state — verification addendum 2026-11-26,
contra V's ≈8 %) and the reader simply continued
its schedule. The emulator need not reproduce the drops, but readers
tolerate them. [V §1.1]

### 4.2 Writable self-tables (DIR-A set)

Writes addressed to 0x20 are field-walked into the thermostat's own
tables. DIR-A holds **72 valid records** in total (verification
addendum 2026-11-26 — also `0102`, `0202`–`020A`, `2F02`–`2F11`,
`4002`–`4016`, `4602`–`4615`, `5702`/`5703`, …); the identity/config
core is: `0104`, `0302`, `3B02`, `3B03`, `3B04`,
`3B05`, `400A`, `4202`. [AA §4.1, §7] Of these, only `3B02`/`3B03` writes
occur in practice (from a SAM, §4.3); the rest are engine-internal.

### 4.3 Writes addressed to 0x20 — accept policy

- **Default policy = accept silently and ignore entirely** (Ion-faithful).
  Never emit an acknowledgement — func `0x0D` does not exist. [V §3
  items 4–5]
- The captured SAM writes were `3B03` ×6 (150 B) and `3B02` ×1 (29 B) in
  the InfinitESP dialect (change-flag words `0x000C` = heat+cool
  setpoints, `0x0010` = mode); the Ion reacted in no way. [V §1.1]
- OPTIONAL control acceptance — a deliberate, documented deviation from
  Ion, only if SAM control is ever wanted: parse the change-flag dialect
  (`3B03`: fan `0x01`, hold `0x02`, heat SP `0x04`, cool SP `0x08`,
  override `0x80`; `3B02`: mode `0x10`, weekday `0x80`, minutes `0x100`,
  displayed zone `0x200`), apply the two-step prime-then-data model, land
  setpoint changes as **MANUAL activity + hold** (hold-until with a
  duration, hold-permanent without), then write `3B0E` (activity flag
  `0x01`) to the SAM as registering controls do. Budget the side effect:
  each `3B02` global write may roll the clock back ≤1 min — re-sync time
  after global writes. [V §3 item 6, §1.2]

### 4.4 SAM-facing contract (complete)

This Ion **does not register a SAM**: it has no "Searching for SAM
Module" commissioning step, and across cold start, full installation and
reseat it emitted zero `040E`/`3F02` probes, zero `031C` writes to a SAM,
and zero steady-state polls to 0x92. The emulator must reproduce exactly
this relationship [V §1.1, §2, §3]:

**Serve:** the §4.1 read surface, to any reader. (In the corpus
0x93 only ever read `3B05`; whether it would be served the rest is
unobserved — VERIFY-sam marks that half UNVERIFIABLE. The zero
content of `3B02`/`3B03` is the tables' content on this unit, not
SAM-specific addressing.) [V §1.1]

**Never do:**

1. **Do not poll the SAM.** No `040E`/`030D` supervision, no `0104` SAM
   polls in steady state. Silence toward an absent SAM must be total and
   indefinite. [V §3 item 7]
2. Do not write `031C`, `3B06`, or `3B0E` to a SAM (outside the optional
   item in §4.3). [V §3 item 8]
3. Do not add a SAM search to commissioning. Run the standard 0x1F sweep
   (which includes single `0104` probes to 0x92/0x94) and let silence be
   silence. [V §3 item 9]
4. Exception policy = silence (§2.6). [V §3 item 10]

**Absence requirement (explicit):** with no SAM on the bus, the whole
SAM contract reduces to: serve `3B05` to 0x93, broadcast SYSTIME, and
nothing else. No timeouts, no retries, no fault state may be keyed to
SAM presence. [V §3]

**SYSTIME:** keep broadcasting `0202`/`0203` to **F1** every ~60 s — a
SAM takes time from the broadcast; never address it to 0x92. [V §3
item 11]

### 4.5 The 0104 identity of this Ion (serve verbatim)

Answer to any `0104` read, 120 B, constant [Map (b)]:

```
"INFINITY NEXT GEN UI   " + zero pad
"CESR******-**.79"        (software)
"SYST0101CW"              (model)
"3320********3320********…"  (serial field, asterisks to 120 B)
```

Decoded: device name **INFINITY NEXT GEN UI**, software
**CESR******-**.79**, model **SYST0101CW**. The asterisks are literal in
the cleaned captures — the capture pipeline masked the middle serial
digits (gap G2). The emulator should serve the real serial read off the
unit's About screen or sticker; no bus test is needed. [Map (b), G2]

For reference, the peers' identities (which the emulator reads on the
~3 s tier): furnace `VARIABLE SPEED FURNACE` / `CESR******-**` /
`G80CTL1352422A2`; ODU `VAR SPD COMP VERSION` / `CESR******-**` /
`HVA960GKA201`. [Map (b), P §7.1]

---

## 5. Control law

The law runs inside the decision-module refresh (`FUN_181efdfc`), which
the supervision layer re-runs on a 15 + 45 (≈60 s) supercycle and on
input changes [Y §3.3]; bus output keeps its own ~10 s rhythm (§1.3)
regardless. Temperatures below: `T` = measured zone temperature
(`CB60`), `HSP` = heating target (`CADC`), `CSP` = cooling target
(`CABC`) — per-zone arrays of 8 in the firmware; this installation has
exactly one zone. Setpoints themselves **never appear in
thermostat→device traffic**; devices see only demand. [Map (e)]

### 5.1 Mode machine [S — the reference for mode semantics]

Three encodings exist and must not be conflated [S §6]:

| Encoding | Values | Where |
|---|---|---|
| `CD7D` (internal coarse mode / active direction) | **1 = HEAT, 2 = COOL, 3 = AUTO / no direction** | decision block, byte 0xFFF8CD7D |
| `R` (requested mode, byte AE47) | **0 = auto, 1 = heat, 2 = cool, 3 = fan-only [INF strong], 4 = off [INF strong]** | mode machine input |
| SYSCTRL byte 49 / `3B02[22]` stagmode (SAM-side) | 0 heat, 1 cool, 2 auto, 3 electric, 4 heatpump, 5 off | external (infinitive); **not** an internal encoding — §11 T-4 |

The authority is the changeover state machine `FUN_1815d67e`, which
maintains a coarse byte `AE44` (this is what becomes `CD7D`) and a
detailed state `AE45` ∈ {1..5}:

- AE45: **1** = AUTO/no-direction [coarse 3]; **2, 3** = direction-1
  (HEAT) states [coarse 1], toggled by the heat call flag AE49 (2: flag
  clear → 3; 3: flag set → 2); **4, 5** = direction-2 (COOL) states
  [coarse 2], toggled by the cool call flag AE48 (4: flag clear → 5;
  5: flag set → 4). [S §2]
- Power-on default and any out-of-range state: park at (AE44, AE45) =
  (3, 1). [S §1a]
- `R` effect: 0 → demand decides (arbiter + changeover tests below);
  1 → force HEAT states; 2 → force COOL states; 3 or 4 → park at (3,1),
  no direction. Crossing to the opposite direction passes through (3,1)
  when the equipment word has bit 0x20 set and family ≠ 0x800. [S §2, §4]
- **Changeover delay:** on several transitions the machine arms a timer
  of `field 0x1B` minutes × 60 s (field 0x1B is a field-store byte).
  [S §1a, §2]
- **Auto arbiter** (`FUN_1815e01c`): sums over active zones heat-demand
  Σ(HSP − T) vs cool-demand Σ(T − CSP); the larger sum wins (heat-sum <
  cool-sum → direction 2, else direction 1). [S §3]
- **Changeover tests** (in AUTO, R = 0): in a HEAT state, if
  **T − CSP ≥ 0.5 °F** → switch to COOL state; in a COOL state, if
  **HSP − T ≥ 0.5 °F** → switch to HEAT state. [S §3]
- Call flags (`FUN_1815daaa`): with demand float > 0, AE44 == 1 sets
  AE49, AE44 == 2 sets AE48. [S §3]

Implementable summary [S §9]:

```
User mode   R   CD7D   AE45        Notes
AUTO        0   3      1 ⇄ 3/5     arbiter + 0.5 °F changeover tests; delay = field 0x1B min
HEAT        1   1      2 ⇄ 3       demand: max(HSP) + 0.75 − T
COOL        2   2      4 ⇄ 5       demand: T − (min(CSP) − 0.75); staging §5.4; arbitration §5.5
FAN ONLY    3   3      1 (parked)  no direction, no demand   [INF: R=3 identity]
OFF         4   3      1 (parked)  no direction, no demand   [INF: R=4 identity]
```

(The ±0.75 demand forms are `FUN_1816deec`'s per-mode demand: mode 1 →
`max(CADC) + 0.75 − T` with tracked max; mode 2 → `T − (min(CABC) −
0.75)` with tracked min; otherwise 0. [S §5]) No consumer anywhere tests
`CD7D` outside {1, 2, 3}; the emulator needs exactly three values. [S §5]

Mode changes take effect at the next burst; there are no changeover
frames and no bus-visible changeover delay beyond §5.1's timer. [T §6]

### 5.2 Demand formula [O]

Total demand `CD44` (float, dimensionless; full scale ≈ 12000 × R, §5.3)
is produced each refresh by `FUN_180c62fc`. **Verified end-to-end in a
PCode emulator against an independent closed-form oracle: 10/10 vectors
match** on all outputs. [O §0, §8]

#### Per-zone law (general form)

For each zone i (zones with `CBA0[i] ≠ 1`, or zone state `CBA9[i] ∈
{0, 5}`, or `CD7D == 3`, are zeroed and contribute nothing):

```
e_i = HSP[i] − T[i]        if CD7D == 1   (heating)
      T[i] − CSP[i]        if CD7D == 2   (cooling)
      0                    otherwise
h_i = min(0, C880[i] − C8EC_prev[i])
      + ( (gate && CBDC ≠ 0) ? CD8C·CD1C[i] − C8CC_prev[i] : 0 )
      where gate = (C870 ≤ acc0), acc0 = CD8C as ingested (normally)
d_i = (e_i < 0) ? K9F4 : 1.0
q_i = CA24[i] / d_i ;  s_i = 0.9 · CA24[i] / d_i
P_i = recursive contribution (below)
t_i = CA04[i] · e_i · (FS_1FDF ≠ 0 ? 15.0 : 1.0)
C8EC[i] = t_i + P_i
C8CC[i] = multi ? clamp(C8EC[i], 0, C880[i]) : max(C8EC[i], 0)
CD44 = Σ C8CC[i]        over computed zones
```

`multi = (n > 1) && (CBDC ≠ 0)`, n = #{i : CBA9[i] ∉ {0,5}}. The
`C880[i]` ceiling applies **only** in multi-zone operation. [O §2]

Recursive contribution `P_i` (dictionary array 0x3C12A864; skipped —
previous value kept — if `CD73 ≠ 0`). The field-store byte **FS_1FDF**
(field 0x1FDF) selects the personality, for both the contribution path
and the ×15 multiplier in `t_i` [O §2.2d/e]:

- **Path A** (`FS_1FDF == 0`), `FUN_180c5e3c`:
  if the one-shot latch `C950[i] ≠ 0`: consume it, `P_i := C958[i]`
  (**unclamped**); else
  `P_i := clamp(P_i + G·(CA04[i]·e_i / q_i) + G·(h_i / s_i), 0, C870)`
  (proportional term first, then the `h_i` term — order matters for
  bit-exactness). Edge: `CA24[i] == 0` ⇒ `s_i == 0` ⇒ `1/s_i = +Inf`;
  the code has no guard.
- **Path B** (`FS_1FDF ≠ 0`), `FUN_180c5ebc` — a pure integrator with a
  deadband window:
  `P_i := clamp(P_i + Δ, 0, C870)`,
  `Δ = G·(CA04[i]·e_i / q_i)` if `1e-5 ≤ |e_i| ≤ 2.0` (double-precision
  band constants, edges inclusive), else `Δ = 0`.

The clamp in both paths is **two-sided** `clamp(v, 0, C870)` — a negative
intermediate returns exactly 0.0. [O §2.2, §7]

Side state maintained by the same pass (does **not** feed `CD44`; listed
for completeness — a replacement thermostat does not need it to compute
demand): `CE00[i] := 0.95·CE00[i] + 0.05·|e_i|` (the 0.05 is a **double**
constant — earlier "1.325" readings were a misread of its high word);
`CE64 += |e_i|`; `CE60 := max(CE60 − Σ_active C8CC[i], 0)`. [O §4, §7]

A second writer (`FUN_180c4322`, `CD44 := param` verbatim) exists but is
a binding-property pass-through selected only for a normalised argument
in (0.1, 1.0] with `CD4A ∉ {1,2,3}`; it is **not** part of the
refresh-cycle law. The emulator implements writer 1 only. [O §5]

#### The ceiling C870 [O §3]

`C870` (demand full-scale / contribution ceiling) is produced by
`FUN_1809f4a4` per refresh (branch predicates decompiler-transcribed,
outputs and constants pool-verified [O §3, Audit-2 §2.1]):

- **Cooling (CD7D == 2): `C870 := CCC4[CC5A−1]`** — the ceiling *is* the
  staging threshold selected by CC5A.
- **Heating (CD7D == 1):** with `f8 = CC34[CBFA−1]`, `f9 =
  CCDC[CC5A−1]`, one of four branches selected by class-word bits
  (CC52 & 0x100), mirror bytes CC54/CBF4/CBF6 and flags CD71/CD7A/CD48:
  A: `C870 := f8 + f9`; B: `C870 := max(f8, f9)`; C: `C870 := f8`;
  D: `C870 := f9` (or all outputs 0). Constants 51210.0 / 100000.0 /
  4.0 appear only in the sibling scaling output C87C, which does not
  feed `CD44`.
- **CD7D other:** `C870 := 0`.

#### Single-zone reduction (THIS installation — implement this) [O §9]

One present/active zone k; all others absent (zeroed, contribute 0):

- `multi = false` regardless of CBDC ⇒ the `C880` ceiling drops out of
  the final clamp: `C8CC[k] = max(C8EC[k], 0)`.
- Ingestion's equal split gives the single zone the whole scale:
  `C8CC_prev[k] = CD8C`, so `gate = (C870 ≤ CD8C)`.
- The whole law:

```
e   = (mode 1) HSP[k] − T[k]  |  (mode 2) T[k] − CSP[k]
h   = min(0, C880[k] − C8EC_prev[k])
      + ( (C870 ≤ CD8C && CBDC ≠ 0) ? CD8C·(CD1C[k] − 1) : 0 )
d   = e < 0 ? K9F4 : 1 ;  q = CA24[k]/d ;  s = 0.9·CA24[k]/d
P  := (CD73 ≠ 0) ? P
    : (FS_1FDF == 0) ? (latch ? C958[k]
                        : clamp(P + G·CA04[k]·e/q + G·h/s, 0, C870))
    :                  clamp(P + (|e| ∈ [1e-5, 2] ? G·CA04[k]·e/q : 0), 0, C870)
CD44 = max( CA04[k]·e·(FS_1FDF ≠ 0 ? 15 : 1) + P , 0 )
```

- In cooling, `C870 = CCC4[CC5A−1]` exactly — the contribution ceiling
  is the staging threshold itself.
- [INF, unproven] If the single zone's weight `CD1C[k] = 1` (the natural
  normalisation), the share term of `h` vanishes and `h = min(0,
  C880[k] − C8EC_prev[k])` — a pure overshoot penalty.

**State the implementation must carry across cycles (per zone):**
`P[i]`, `C8EC[i]`, `C8CC[i]`, and the latch pair `C950[i]`/`C958[i]` if
path-A latch behaviour is replicated. Everything else is a per-cycle
input. [O §6]

Input semantics [O §6]: `CA04[i]` per-zone proportional gain;
`CA24[i]` per-zone normalisation scale; `C880[i]` per-zone cap;
`CD1C[i]` per-zone distribution weight [INF]; `CBDC` multi-zone /
demand-response enable byte; `K9F4` scalar divisor applied to negative
errors only (asymmetric gain for "zone satisfied" [INF]); `G` global
gain of the recursive contribution; `CD73` contribution-freeze byte.
Configuration values for all of these are **data, not code** — §9.

### 5.3 Threshold tables [P]

The demand law consumes breakpoint tables built at ingestion by two
producers. Table axes are demanded capacity on a nominal-capacity scale:
12000.0 = BTU/h per ton; 34.286 = 12000/350 (the nominal 350 CFM/ton air
volume). For this ODU, R = 5 ↔ 60K BTU/h. [Q §4, INF strong]

**Producer 1 — `FUN_181f21d4`** builds `CCC4` (mode-2/cool table),
`CCDC` (mode-1/heat table), `CD04`, count `CC5A = (CC52 & 0xF) + 1`,
from the equipment class word **CC52** (field-store bytes [1..2]),
**R = store[8] / 12.0**, and **X** = a mirror float clamped to [12, 61]
(invalid → 61). With **K = 34.286 × (137.0 + 3.5·X)**: [P §2]

- Fallback (CC52 == 0x8000, or mirror byte CC54 ∈ {0, 4}): single-entry
  zero tables (CC5A = 1, CCC4[0] = CCDC[0] = CD04[0] = 0), no tail
  processing.
- General prologue: CCC4[0] = CCDC[0] = 0; **CD04[0] = R**; entries
  [1..3] default 0 (CD04[1..5] are never written by this producer).
- Analytic branches (the families relevant here):

  | Class word(s) | CCC4 | CCDC |
  |---|---|---|
  | 0x8241, 0x92C1 | [1] = R × 12000 | all 0 |
  | **0x8141, 0x91C1** | [1] = R × 12000 | [1] = R × K |
  | 0x8242, 0xA2C2 | [1] = R×12000×U1; [2] = R×12000×U2 | all 0 |
  | 0x8142, 0xA1C2 | as 0x8242 | [1] = R×K×U1; [2] = R×K×U2 |
  | 0x92C2 / 0x91C2 / 0x85C2 | selector form (below) | selector form (0x91C2/0x85C2) |

  (U1/U2 are dimensionless stage factors from a device mirror record,
  §9.) Parameterized classes (0x89A2…0xCAA2) copy per-device-class
  parameter sets from bus tables `0606`/`0607` verbatim; string classes
  (0xC195/0xC295) parse a 125-byte blob from the ODU's own `060E` object
  (device class 0x52). Full branch tables: [P §2.3–§2.6].
- Selector form: four dictionary ushorts (table `0504`, class 0x50 or
  0x54) scaled by 1/1000, min-clamped at 0.0001; a selector byte
  (0xFFF8C74D for CCC4, 0xFFF8C74E for CCDC) picks the (first, second)
  pair — selector ∈ {1, 0} → pair 2, any other value → pair 1;
  `table[1] = R × scale × first`, `table[2] = R × scale × second`
  (scale 12000, or K for 0x91C2's CCDC). [P §2.4]
- Shared tail: rebuilds the derived arrays CC64 (from CCC4) and CC94
  (from CCDC) — the CCDC-derived array is processed **only if CC52 bit
  0x0100 is set** — and CC7C/CCAC (selector-byte-chosen sources), with
  fractional stage outputs. For family field `(CC52 & 0x7C00) ==
  0x4000` an additional min/max post-processor runs. [P §2.7]

**Class-word encoding** [P §6]: bit 0x8000 always set in compared
values (0x8000 itself = unconfigured/fallback); bits 0x7C00 = family
field; **bit 0x0100 = "second table (CCDC) present"**; bit 0x0020 gates
second-channel / derived-table processing in all consumers [Audit-2
§1(f)]; low nibble = breakpoint count − 1. A mapper cluster collapses
CC52 into a category byte (0x3C12A8D5): {0x92C1, 0x91C1}→1,
{0x92C2, 0x91C2}→2/3, {0x85C2}→4, {0xA2C2, 0xA1C2}→5, {0x8241,
0x8141}→7, {0x8242, 0x8142}→8. Equipment-type *names* for the families
are not in the image and are not needed. [P §6.2, §6.3]

**Producer 2 (twin) — `FUN_181f07ec`** builds `CC04` / `CC1C` / `CC34`
(the channel-1 and CFM-side tables of §5.4/§5.6) from class word **CBF4**
(field-store bytes [3..4]); count `CBFA = (CBF4 & 3) + 1`. Gate: CBF4 ==
0 or mirror byte CBF6 ∈ {0, 4} → no tables written. Branches copy
ushort parameters from table `0402` (classes 0x3E/0x40/0x42) into
CC04/CC1C identically, and build CC34 from a byte of table `030A` ×
1000.0 with 0.4/0.6/1.0 tapering; special classes: 0x59/0x5B use
store[0x12] × 3414.0 (with the 6×3 lookup table @0x1830B094: keys
9/15/18/20/24/30 → fractions 1/3, 2/3 or 1/4, 3/4); 0x39 is a
zone-minimum form with CC34[1] = 50000.0. Full branch table: [P §3, §4].

**Our installation's tables (bounded computation)** [P §7.5]: under the
flagged hypothesis set H — X = 60.0 (ODU nominal kBTU [INF]) and
store[8] = 60 → R = 5.0 — the primary candidate classes give:

| Candidate | CCC4 | CCDC | CD04 |
|---|---|---|---|
| 0x8141 / 0x91C1 (CC5A = 2) | {0, **60000**, 0, 0} | {0, **59486.2**, 0, 0} | {5.0, –, –, –} |

K(60) = 11897.242. Sensitivity is linear in store[8]: byte 24 (factory
default) → R = 2.0 → CCC4[1] = 24000, CCDC[1] = 23794.5; byte 72 (max)
→ R = 6.0 → 72000 / 71383.5. One behavioural observation of a staging
threshold pins the byte (§9). The twin's tables cannot be computed from
available data (they need CBF4 plus runtime dictionary values). [P §7.5]

### 5.4 Coordinate conversion [Q, labels corrected per Audit-2 §2.3]

Downstream of `CD44`, the module works with two continuous **stage
coordinates** P1/P2 — fractional indices into the capacity tables —
accessed through pairs `FUN_181f77f4/fc` (channel 1, cell CD94) and
`FUN_181f7822/782a` (channel 2, cell CD98), with CD90 as a staging cell.
The channels have no dictionary names (proven: they are runtime
object-instance fields, not registration records) [Q §2].

**Inverse direction — `FUN_180c15d2`** (demand → coordinates), run from
the refresh [Q §3]:

1. Zero both coordinates; recompute from scratch every evaluation.
2. **Channel 2 (primary):** segment-search CD44 over the mode-selected
   table — **heat (CD7D == 1): CCDC; cool (CD7D == 2): CCC4** (count
   CC5A) — and inverse-interpolate:
   `P = lo + (x − T[lo]) · (hi − lo) / (T[hi] − T[lo])`.
3. **Channel 1 (spillover):** in **heat**, CD44 is first capped at
   CCDC's last entry, and the **excess over the heat table's maximum**
   is latched: `0x3C12A844 := max(0x3C12A844, max(0, CD44 −
   CCDC[CC5A−1]))` (gated on class bits CC52 & 0x100, family == 0x400,
   and flag bytes); channel 1's input is that excess (without the gate,
   CD44 itself). Channel 1 inverse-interpolates its input over **CC34**
   (count CBFA). The latch resets when CD44 falls below a half-segment
   threshold (0x3C12A84C = active segment endpoint / 2).
4. Tail: `CD8C := forward(CC34, P1) + forward(mode table, P2)` — total
   demand recomputed as the sum of the two channels' forward-evaluated
   values.

**Forward direction — `FUN_181f4308`** (coordinates → CD8C), the refresh
ingestion path [Q §3]:

- Seeds P1/P2 from the device-mirror record (bytes 1 and 5); stage bytes
  CA80 := (int)P1, CA94 := (int)(P2 + 0.0001) (epsilon-truncation).
- Combine by mode: **heat (==1): CD8C := interp(CC34, P1) +
  interp(CCDC, P2)** — heat demand is the sum of **both** channels;
  **cool (==2): CD8C := interp(CCC4, P2)** — channel 2 alone; else 0.
- Split: each active zone gets `C8CC[i] := CD8C / count` (equal split —
  the pre-refresh value the demand law's share term reads).

**Coordinate clamping:** every write through either setter passes the
equipment-dependent clamp dispatcher `FUN_181f4d04`, which merges the
flash equipment-record template @0x1830B0A8 with the live record and
dispatches on mode, class-word bit 0x20, and the equipment size byte
(record[0x10], bands <31 / 31–60 / ≥61) [Q §1, labels corrected]:

| Mode | bit 0x20 | Clamp applied |
|---|---|---|
| heat (==1) | set | two-value clamp into the band set {0.0, 1.0, 1.3 if record[0]==4 else 1.4}; **≥61 → v := 0.0** (the heat chain `FUN_181f48de` forces 0.0 at size ≥61 independently — verification addendum 2026-11-26) |
| heat (==1) | clear | if size <31 and v ≥ 2.0 → v := 2.0 |
| cool (==2) | set | size <31 → v := min(v, 1.3/1.4); 31–60 → v := min(v, 1.0); **≥61 → v := 0.0** (the size derate applies in **both** mode chains, contra the cool-only reading) |
| cool (==2) | clear | if size <31 and v ≥ 2.0 → v := 2.0 |

[INF] The size byte is the nominal equipment size code (bands align with
the clamp X ∈ [12, 61] and size-class strings like the "61" of
EN(A,D)4X61); the caps read as maximum demand coordinate by equipment
size. Which physical equipment bit 0x20 encodes is not statically
resolvable. [Q §1]

**Physical meaning** [Q §4, INF strong]: the coordinate is a continuous
stage coordinate along the capacity curve — 15d2 inverts the curve
(capacity → coordinate), 4308 evaluates it (coordinate → capacity), and
the integer truncations CA80/CA94 are the stage bytes the staging
machine consumes. [INF] The two channels are two capacity sources staged
in sequence — channel 2 primary, channel 1 spillover; heat sums both,
cool uses channel 2 alone (per the 4308 combine).

(Not needed for control: `FUN_181f7050`, the per-zone call-session
evaluator — it times each zone's call, accumulates CD8C × CD1C[i] per
hub cycle, and at call end publishes session minutes, mean demand,
demand share, and a ±10 score from the end-of-call temperature deviation
(|diff| ≥ 1.875 → −10, in the mode's error sign convention). Telemetry/
attribution only; its consumers were not traced. [Q §6])

### 5.5 Staging and source arbitration

**Demand quantizer → CD4B** [S §7]: `FUN_180c576c` is a 4-level Schmitt
quantizer of the demand differential: bands at **+5 / 0 / −5**, ±1
deadband; CD4B ∈ {1, 2, 3, 4}; preset to 4 by ingestion.

**Cool-side staging machine → CD49** [E via S §3, §7; Y §4.3]:
`FUN_180c54d8`, gated on **CD7D == 2 (COOL)**, output CD49 ∈ {0, 1, 2}.
The threshold bases differ by transition (VERIFY-staging): stage-2
engage and fallback read `CCC4[CC5A−1]`, stage-1 engage and drop read
`CCC4[1]` (for this installation CC5A = 2, so both bases are the same
cell, `CCC4[1]`):

- stage 2 when demand > **×1.25** of `CCC4[CC5A−1]`;
- stage 1 engages at **×0.25** of `CCC4[1]`, held until demand <
  **×0.01** of `CCC4[1]`;
- stage 2 falls back at **×1.00** of `CCC4[CC5A−1]`.
- **No timers** — pure demand hysteresis. The hysteresis form is proven
  and was emulator-verified 12/12 by stage M (on this machine).
  [Audit-2 §1(b)]

**Heat-side staging — GAP B-11.** The producer of the heat staircase is
**not isolated**: `FUN_180c54d8` is the cool machine, and stage E's
attribution of it to the 0305[0] heat staircase is refuted as a producer
claim [Audit-2 §1(b)]. Candidates: `FUN_180c3012 / 180c3418 / 180c3814 /
180c3bee / 180c46b8` [S §3]. What is capture-proven and sufficient to
implement: 0305[0] ∈ {0, 1, 2}; stage 1 at moderate demand, stage 2 at
the top of the staircase (79 °F setpoint vs 72 °F room in the reference
capture); [0] and [2] are **never simultaneously nonzero** (674-frame
census) [Audit-2 §1(b)]; after a call ends there is exactly one residual
stage-2 demand write, then idle — a demand-domain rundown (the ×0.01
hold shape), not a timed one [Y §7]. An emulator may stage heat from
this captured behaviour, applying the same hysteresis ratios as the
cool machine [INF: same form, unverified producer].

**Source arbitration → CD4A / CD4C** [S §7]: `FUN_180c5832` runs **only
when CD7D == 2 and byte 0xFFF8CB5C == 1**; otherwise it forces CD4A =
CD4C = 0. **In heat, CD4A ≡ 0** — the arbitration is cool-side only
(heat-pump/reheat equipment variants). Transition table (gate passed;
inputs CD49 stage, CD4B band; CD4A is sticky — the previous value
selects the branch family):

- CD49 == 2 → CD4A = 5 (all branches)
- CD49 == 1 → CD4A = 3 if CD4B ∈ {1,2}; 4 if CD4B ∈ {3,4}
- CD49 == 0 → CD4A ∈ {0,1,2} by two predicates if CD4B ∈ {1,2};
  ∈ {0,4} if CD4B ∈ {3,4}

CD4C ∈ {0,1} is an arbitration-internal latch (1 when CD4A-in ∈ {1,2,3},
0 when ∈ {0,4,5} or the gate fails); no external consumer. The
dictionary enum `cooling, hpheat, eheat, gas, reheat, fangas` exists but
its **index↔name binding is UNPROVEN** — implement the transitions, not
the names. For this installation only the plain cooling path is
reachable in cool, and CD4A ≡ 0 in heat. [S §7, T §6]

**Other isolated control behaviours** [Y §4.3]: satisfaction hysteresis
— a zone-satisfaction average sets a flag at > 2.5, clears at < 1.5
(`FUN_18183d34`); demand-response trim — flagged zones give up half of a
system offset D = clamp(x, 0…6 °F), adjusted setpoint capped at 70.0 °F
(`FUN_180c55f2`; optional layer, DR events only).

### 5.6 CFM computation [R]

The commanded airflow is the float cell **CD88**, produced each refresh
by `FUN_1804e4b6` (called from `FUN_181f4308`'s tail). `FUN_180c15d2` is
**not** the CFM producer — it produces CD8C and publishes the demand's
segment index, one of the CFM computation's inputs. [R §0]

**Step 1 — per-mode base** by table interpolation over the continuous
capacity coordinate (generic interpolation over segment [lo, hi]:
`T[lo] + (v − lo)·(T[hi] − T[lo])/(hi − lo)`, applied only when `lo < v
< hi`; outside the segment, a direct lookup fallback or 0.0) [R §2]:

- **Heat** (`FUN_1804f2cc`, double precision): part 1 (gate CBF4 & 4) =
  interp over **CC1C** (if CD3F ≠ 0) else **CC04**, segment [CA5A, CA59],
  input = coordinate cell CD90; part 2 (gate CC52 & 0x20) = interp over
  **CCAC** (if CD43 ≠ 0) else **CC94**, segment [CA75, CA76], input =
  the shared coordinate cell 0x3C12EC6C. Base = part 1 + part 2.
- **Cool** (`FUN_1804f6cc`): main (gate CC52 & 0x20, input inside
  [CA75, CA76]) = interp over **CC7C** (CD43 ≠ 0) else **CC64**. Detour:
  in the CD43 ≠ 0 branch with selector byte C74D == 1, `FUN_18051898`
  runs — if `(CC52 & 0xF) == 1` it calls `FUN_18051cec(CD4A)`, the getter
  whose constant run is {200, 275, 375, 325, 400, 350} with first-level
  selection by CD4B (windows {375, 325, 400, 350} / {400, 350, …}) —
  **375/400 are live CFM/ton constants on this path, not dead code**
  [Audit-2 §1(e)]; else it interpolates `max(0x3C12EC6C − 1.0, 0)`
  through the two-point getter `FUN_18051908`. Both primary candidate
  class words (0x8141/0x91C1, low nibble 1) satisfy the `(CC52 & 0xF)
  == 1` gate. [R §2.2, Audit-2 §1(e)]
- Equipment family field `(CC52 & 0x7C00) == 0x800` replaces the result
  with the `FUN_181f5e9a` evaluator — **not on this unit's path** (our
  candidate family fields are 0x0000/0x1000). [R §4, Audit-2 §1(g)]

**Step 2 — cap:** `base = min(base, FUN_18052354())` = the maximum of
the two zone-distribution channels. [R §1.1]

**Step 3 — minimum-airflow raise** (only if CA94 ≠ 0):
`base = max(base, FUN_18086898(selected, base))`, where the selection
(`FUN_1805002a` via class-dependent index translators) comes from the
flash parameter family {200, 325, 350, 0.85, 1.0} and `FUN_18086898`
clamps against the engine limit cell 0xFFF80F9C. (The exact
variant-return ABI of `FUN_1805002a` is unresolved; functionally it is a
class-dependent minimum-airflow selection applied as a raise.) [R §2.3]
Class-0x4000 equipment with a zero flag byte forces base = 0.0 instead —
not our family. [R §1.1]

**Step 4 — write:** `FUN_1804fa1c`: CD88 := base, plus the per-zone
split `CD9C[i] = CD88 × CD1C[i]` (and `CDBC[i] = CD8C × CD1C[i]`).
[R §2.4]

**Step 5 — demand floor + store clamps** (second half; runs when any of
CD86/CD87/CB55/CB56 ≠ 0) [R §1.2]:

```
floor = FUN_1804fca0() = max( C74F ? C750 : 300 , 175 )
        ; C74F = selector byte; C750 = configured ushort; 300 and 175 are flash constants
demandFloor = 325 × CD8C / 12000.0
if (C9F0 ≠ 0) floor = max(floor, demandFloor)
if (CD88 < floor) CD88 = floor          ; ratchet up only
if (CD7D == 1) CD88 = clamp(CD88, store[197], store[199])    ; heat floor, cap
if (CD7D == 2) CD88 = clamp(CD88, store[4062], store[4064])  ; cool floor, cap
```

Store limits are read via the field-store getter, 2 bytes each; **a
limit of 0 means "unset" and is skipped**; descriptor defaults are 0.
[R §1.2] The 325 is one entry of the flash CFM/ton constants block
@0x1830B108: ushorts **{175, 300, 200, 300, 350, 325, 325, 325, 350,
350, 400}** (350 = nominal, 400 = +15 % comfort, 325 = −7 % efficiency
[INF for the per-slot semantics beyond the traced entries]). [R §1.3]

**Idle / no-demand:** if the zoning predicate holds and CD87 == CB55 ==
CB56 == 0, CD88 is forced to 0.0 and step 5 is skipped; at idle CD88 =
CD8C = 0 (reset function @0x181F026E). [R §1.1, §7]

**Alternate producer:** `FUN_180511da` (five zone-distribution
strategies, finishing with `CD88 = min(CD88, *0xFFF80F9C)`) replaces the
direct path when predicate `FUN_1805185c` holds (`CA94 == 0 && CA80 ==
1 && (CBF4 & 0x20) && CC1C[1] == 0.0`). Which producer ran during the
captures is not recorded; for a single-zone install both converge to
"one zone gets the total". [R §3, §10]

**No demand-response term:** the 4.79 CFM input set is closed — mode,
capacity indices, equipment tables, class word, flag bytes, store
limits, CD8C. The ≤4.74 `utilityEvent/demand*` group was deleted, not
left vestigial. [R §6]

**Capture anchors** (for calibration, §9): CFM = 0 at idle everywhere;
cool stage-2 call ramps 0 → 1232 → 1760 → 1710 → 1660 within one call
(modulation — not a fixed per-stage tap); heat 1368 → 1617, with 1617
repeating exactly across traces; fan-only 1166 (exact repeat, a table
value) settling to ~380 (378–384 wobble, computed); max 1760 ≈ 5 t ×
352 CFM/ton; commissioning traces show exactly 1750. On call end, the
last CFM is **held through the blower off-delay** (1660 held ~60 s after
the cool byte cleared) — the off-delay itself is the furnace board's
(§8.2). [R §8, §9]

### 5.7 Assembling the 0305 demand write

Per burst, from the control law's outputs [Map (e), R §7]:

- [0] = heat stage ∈ {0, 1, 2} (§5.5; heat producer = gap B-11, wire
  behaviour specified there)
- [2] = cool stage: `02` from the first demand burst of a cool call
  [T §11 item 5]; ∈ {0, 2} in all captured cooling (the CD49 staging
  output's wire mapping beyond this is part of B-11's family of
  unknowns — never co-active with [0])
- [4..5] = BE16 of CD88 (the float→ushort packing happens inside the
  engine layer in Ion; the emulator writes the integer CFM directly —
  observed values are integers) [R §7, §10]
- [11] = 0x78 once commissioned (§3 B7)
- all other bytes 0

Setpoints travel only inside the thermostat (profiles in `400A`: 5
activities × 7 B — heat setpoint, cool setpoint, fan byte per activity;
the captured constant is in [Map (b)]); devices see only the demand
above. [Map (b), (e)]

---

## 6. Cooling specifics [T]

### 6.1 The burst to 0x53 (normative, every burst, all modes)

Write, in this order (wire-measured in two captures, no exceptions;
the group is the burst's second sub-burst, ≈5.7 s after the furnace
group): `0610`, `0612`, `0605`, `061A`, `060D`, `061E`.
Idle values (the constants the thermostat sends when nothing calls):
`0605 = 00000000000001`, `060D = 00`, `0610 = 00000000`,
`0612 = 22B80000000000000000`, `061A = 01`, `061E = 0F3FD851EC06000000`.
Only `0605` bytes [0..4] and `060D` [0] ever change. [T §11 item 1]

### 6.2 The 0605 capacity command

- Payload 7 B: **[0..3] = float32 big-endian capacity command on a 0–5
  scale** (this ODU class exposes a 5-stage capacity model; compressor
  speed 25–100 %); **0.0 = no command**. [4] = call flag (below);
  [5] = 0 always; [6] = 1 in every ODU-addressed write (0 only in the
  B1 boot broadcasts). [T §2.1, §11 items 2–4]
- Observed values: 571 bursts carry the idle payload form (float 0.0
  with [4]=0); the float value 0.0 occurs in 616 bursts total (45 of
  them with [4]=1, only 18 of those being the cool-call tail); 34 bursts at **5.0** (the one
  captured call — setpoint 70 °F, OAT ≈ 65 °F, ≈6 min, ended by wall OFF,
  never satisfied); exactly **one** frame at 3.0 (2026-11-03, transition
  transient, ~10 s after heat ended).
- **v1 law (implement this):** during a cool call write **5.0** for the
  whole call, from the first demand burst; at call end drop to **0.0**
  in one step. Do **not** emit intermediate values (1.0–4.0) until
  summer evidence exists (§11 B-5): the thermostat-side producer of the
  part-load values is not identified in code, and nothing in the
  archive proves they occur. [T §11 item 5]
- Byte [4] (call flag): 1 while a cool call is commanded **and for ≈3
  min (18 bursts) after the call ends**; also observed 1 in unexplained
  windows (27 bursts outside any call: the first 24 of one capture,
  before its heat window opens, and 3 after a 3.0 transient in
  another — VERIFY-cooling claim 4) — its writer was not isolated;
  the rule above is the
  implementable form. [T §2.1, §5.3]

### 6.3 The 061E coil payload (literal construction)

9 B: `0F | <float32 BE of the committed coil parameter> | 06 | 00 00 00`.
For coil EN(A,D)4X61 the parameter is **1.69** = 0x3FD851EC, giving the
constant `0F3FD851EC06000000`. [0] = 0x0F and [5] = 0x06 are unknown
constants. The value is written **every burst** (651/651), is
commissioning-derived (§3 B6) and never changes afterwards. The
emulator must construct it from its persisted coil parameter — never
hard-code a different coil's bytes. [T §2.2, §11 item 6]

### 6.4 060D and the remaining burst members

- `060D` [0] = **0x02 when a heat or cool call is active or pending**
  (it *leads* the demand bytes substantially at call start: measured
  ≈65 s ≈ 6 bursts before the cool call's first `0305`, ≈135 s ≈
  13–14 bursts at heat call starts — verification addendum 2026-11-26,
  contra T's "~2 bursts"); **0x00
  in fan-only and in satisfied idle**. Write `00`/`02` exactly so.
  [T §11 item 7]
- `0610`, `0612`, `061A`: constant payloads (§6.1) in every mode.
  [T §11 item 8]

### 6.5 ODU self-behaviour (context, not thermostat control)

Under a constant 5.0 the ODU ramps itself (target RPM 2180 → 2850 →
3700 → 4140, current chasing); the EXV read 45 % in the first in-call
`0608` sample and 100 % in the other 65 of 66 in-window samples; its `0608` requested CFM (938 → 1600) is **not**
followed by the thermostat's `0305` CFM (no consumer of 0608 exists in
the image). The thermostat's cooling control surface is exactly §6.1–
§6.4; everything else is the ODU board's own inverter control. [T §3]

### 6.6 Readbacks (poll and republish only)

- `0604`: target RPM [0..1] BE16, current RPM [2..3] BE16.
- `0608`: [2] EXV %; [5..6] requested CFM BE16.
- `060E` [0]: actual compressor stage (0 at rest/spin-up, 5 once
  RPM ≳ 2850).
- `061F` (81 B status frame): only bytes 17–20 (float at offset 17 —
  signed control delta, 0.0 at idle, −66.5…+25.2 during the cool call),
  30–33 (unresolved integer region), byte 41 (low byte of the word at
  [38..41], toggles 0↔2 corpus-wide — verification addendum 2026-11-26),
  and 58–61 (float at 58: −13.18 at
  idle → +5.38 by call end) ever change; the floats at offsets 1/5/9/13
  **never move** on this unit (InfinitESP's superheat/subcooling names
  do not fit). The thermostat has **no code consumer** for `061F` — the
  ~5 s poll is pure telemetry. Republish to HA; do not feed into
  control. [T §4, Map (a)]
- `0302` TLV stream (type BE16, value BE16 ÷ 16): 0x111 = outdoor air
  temp [INF], 0x112 = coil temp [INF], 0x130 = suction temp, 0x145 =
  discharge temp, 0x14A = superheat channel, 0x14B = unidentified;
  `0303` pressures 0x100 / 0x148 ÷ 16. [T §5]

### 6.7 Not applicable to this installation

Heat-pump defrost logic, aux/electric heat staging, HP balance-point
lockouts, the Bristol ×0.63 ODU multiplier, the 3E-family ODU tables
(`0602`, `0606`/`0607`/`0609`, `061B`, `061C`, `061D`), zoning and
simultaneous heat+cool: all are code for other equipment classes; this
ODU is a cooling-only variable-speed unit and this furnace is the sole
heat source. [T §8, §9] (Note on `0602`: the thermostat does read it
on the ~17 s tier, §1.2 — it is listed here because its semantics are
3E-family and unused by the control law, not because the read does
not happen; an emulator issues the read like any other tier member.)

### 6.8 Dehumidification (optional, default OFF)

Class behaviour only, **provisional**: dehumidification target NONE or
55–65 % RH, overcool ≤ 3 °F below the cool setpoint, reduced CFM.
Defaults are not extractable; do not enable by default. [T §7]

---

## 7. The 0414 / 060B byte — synthesize it [B7]

Every ~20 s tick the thermostat writes `0414` (6 B: `01 04 XX 01 03 20`)
to the furnace and `060B` (7 B: `01 04 XX 00 00 00 00`) to the ODU. **XX
is identical in both frames** (153/153 pairs); 63 distinct values over
the corpus, range 70–194. [B7 §1]

What XX is **not** (each excluded with evidence): not outdoor air
temperature (r = −0.23; at fixed OAT 65.0–66.5 °F, XX spans 72–194);
not any polled channel (every |r| ≤ 0.36; a brute-force scan of all
integer fields in all tables found nothing above 0.6); not setpoints,
not a counter/checksum/bitfield, not time-of-day, not the 0x93-derived
temperature. [B7 §2] Verdict: a **thermostat-internal modelled
temperature state** — never validated against a physical sensor, with a
clear thermal fingerprint [B7 §3]:

- initialises at 70–72 at every boot (≈ room temperature; a cold-start
  capture has the room at 72 °F);
- boot ramp is exponential, τ ≈ 2–3 min, 72 → ~146 with all equipment
  channels flat;
- steady-state steps are small: |Δ| ≤ 3 per 20 s tick;
- per-tick drift by mode: heat **−0.76** (never rises during a heat
  call), fan **−0.47**, cool **−0.24** (mixed), idle **+0.32** net.

**Emulator recipe (implement this):** synthesize XX — initialise at the
measured room temperature; per 20 s tick add +0.3 idle, −0.8 heat,
−0.5 fan; clamp to ≈ 70–195. Even a constant would be indistinguishable
in the archive: equipment behaviour is identical at XX = 70 and
XX = 194. The exact internal name of the state remains open (B-7 closed
in practice; §11). [B7 §4]

---

## 8. Protections & timers [Y]

### 8.1 What the emulator itself implements

| # | Protection / behaviour | Spec |
|---|---|---|
| T-1 | Demand hysteresis | §5.5 thresholds (×1.25 / ×0.25 / ×0.01 cool-side; same form for heat per §5.5 B-11 note). Pure hysteresis — **no timers**. [Y §4.3] |
| T-2 | Quantizer deadband | CD4B ±1 deadband on the 5/0/−5 bands; satisfaction flag 2.5/1.5. [Y §4.3] |
| T-3 | Burst cadence | ~10 s; a call takes effect within one burst. [Y §4.3] |
| T-4 | Supervision supercycle | control-law refresh ≈ 60 s (15 + 45). **All** sys_ctrl timers (CF44–CF4A, the 120/180/300 s fields) are supervision/housekeeping — **none is an equipment timer or a comm watchdog**. There is no thermostat-side comm watchdog to implement. [Y §3.8] |
| T-5 | Smart Recovery | fixed **90 min** early start before a scheduled setpoint change (help-text attested). [Y §4.3] |
| T-6 | Heat/cool deadband | a setting exists; its **default is unproven** — expose it, do not assume a value. [Y §4.3] |
| T-7 | Setpoint limits | settings exist (heat/cool min/max); **defaults unproven** — expose, do not assume. [Y §4.3] |
| T-8 | Staging mode selection | setting {System / Furnace / Low / High}; select **"System"** explicitly for thermostat-side staging. [Y §4.3] |
| T-9 | Heat blower-off delay | a wall setting (`heatoffdelay`); the **communicating-mode default is unproven** — do not assume the board's conventional factory 120 s applies. The board executes it (§8.2). [Y §4.3] |
| T-10 | CFM limits | the §5.6 store-limit model (names exist; values are equipment-derived at commissioning, defaults 0 = unset). [Y §4.3] |
| T-11 | DR trim | optional; §5.5. [Y §4.3] |
| T-12 | **Freeze protection — emulator's own decision** | **No evidence Ion has a house freeze safety temperature** (the firmware's `freezelimit` is a GeoHP loop parameter, not a house protection). If the emulator implements one, the industry norm is a heat call at ≈ **40 °F** room temperature even in Off mode — an emulator policy choice, **not** inherited Ion behaviour; document it as such. [Y §4.3 T-14] |
| T-13 | Comm-fault surfacing | when an expected device stops answering, surface the fault to the user (Ion shows "INDOOR UNIT COMMUNICATION FAULT" and OAT "---", observed 2026-11-24). Detection is by poll silence; there is no bus watchdog timer behind it. [Y §4.3 T-15, project record] |
| T-14 | Lockout gating | thermostat lockouts (if configured) gate on **valid OAT only**; with OAT invalid/absent they must not engage. [Y §4.3 T-16] |
| T-15 | **No compressor min-off / min-run, no furnace upstage timer** | none exists in the isolated thermostat code. If the emulator adds its own min-off, that is **new policy**, and it must be **≥ the equipment boards' own enforcement** (§8.2) — never shorter. [Y §4.3 T-21] |

### 8.2 What lives in the equipment — respect, never replicate or fight

**Furnace control board** (service-manual values; conventional-doc
items marked †): prepurge 15 s; HSI warm-up 17 s; flame proving 2 s
beginning 5 s after the gas valve opens; ≤4 ignition trials → **3 h
ignition lockout** (auto-reset after 3 h or on power interrupt);
flame-present-at-start → gas lockout + inducer high; main limit trip →
combustion off + blower on (auto-reset); draft safeguard open > 3 min →
3 h lockout (reset: remove call + cycle 115 V); LPS/HPS proving; HPS
failure → low-heat ≤ 2 min; **blower-ON delay 45 s low-heat / 25 s
high-heat**; inducer post-purge 5 s; **blower-OFF delay heat 90/120/
150/180 s (factory 120)**, cooling 5/30/90 s (factory 90)†; power
restore mid-call → 90 s blower-only; fault memory 7 codes / 72 h; 24 V
circuit fused 3 A. The board's own adaptive staging applies to
**conventional mode only** — in communicating mode the emulator
commands stages explicitly. [Y §6]

**ODU board:** **anti-short-cycle 3.5 min** (after the last cycle, at
power-up, and on brownout return); PEV equalisation 150 s open + 15 s
off before the next start (non-bypassable); sump warm-up 10 min per HV
power-up; intelligent crankcase heater; brownout < 187 V for ≥ 4 s →
stop, inhibited until ≥ 190 V, then the 3.5 min delay; HPS opens
600 ± 5 psig / closes 470 ± 10 psig → 6 min delay + PEV, restart one
stage lower per trip, lockout at the lowest stage, clears after 2 h
clean; LPS stop < 15 psi anytime or < 33 psi for 5 min → resume after
15 min if > 43 psi; 3 consecutive < 15 psi trips → 4 h lockout (counter
resets after 15 min of good run); stage ramps gated on suction ≥ 45 psi
per step; inverter overtemperature → derate, fan 500 rpm until cool, no
restart while active; **standby ≈ 2 min after the last valid
communication (COMM LED off at 2 min)**; internal AOC↔MOC loss fault
after 2 min. Defrost values are heat-pump-only — N/A here. [Y §6]

### 8.3 Interaction rules (normative for the emulator) [Y §9]

1. **Demand ≠ motion.** A healthy system may take ~35 s (ignition
   sequence) to 10 min (sump warm-up) to answer a demand, and hours
   under a lockout. Fault logic must key on the boards' own fault
   reporting (`4202`, status tables), never on "demand sent, nothing
   moved".
2. **Never out-shout a protection.** On a board-reported fault or
   lockout, hold or drop demand and surface the fault; do not cycle
   demand to "retry" the equipment.
3. **Bus cadence is a safety input.** A > 2 min gap stands the ODU down
   mid-call (§10). The existing DIY-node guards (no writes if the wall
   is silent > 60 s; at most 1 write per 10 s — two of the node's
   eight write-core guards; the complete enforced set is listed in
   firmware-history/PHASE5 §2) are compatible with, and stricter
   than, this constraint.

---

## 9. Configuration parameters — data, not code (gap B-12)

The control law (§5) is exact; every quantity below is **installation
data** that the law consumes. None of them may be hard-coded from this
spec's examples: each must be pinned by one of the three routes in
§9.3 before the emulator's numbers are trusted. [O §10.1, P §7]

### 9.1 The parameter list

| Parameter | Role in the law | Known bounds / defaults |
|---|---|---|
| **G** (dict 0x3C12A85C) | global gain of the recursive contribution `P` | **No writer found** in any census — value unknown; likely a compile-time constant or a value set by an untraced path [O §10.1] |
| **K9F4** (`*0xFFF8C9F4`) | divisor applied to **negative** errors only (asymmetric gain) | writer `FUN_181f5d08`, configuration-dependent; value unknown [O §10.1] |
| **CA04[i]** | per-zone proportional gain | producer `FUN_181f017e`; values unknown [O §10.1] |
| **CA24[i]** | per-zone normalisation scale (divisor in q/s) | same producer; unknown [O §10.1] |
| **C880[i]** | per-zone cap (multi-zone ceiling; single-zone: overshoot-penalty reference in `h`) | producer `FUN_18226ab4`; unknown [O §10.1] |
| **CD1C[i]** | per-zone distribution weight (share term, CFM split) | producer `FUN_180d208c`; Σ = 1 normalisation **unproven** [O §10.1] |
| **FS_1FDF** (field-store byte 0x1FDF) | personality byte: selects path A vs B **and** the ×1 vs ×15 multiplier in `t_i` | binary; our unit's value unknown — determines which integrator the emulator runs [O §2.2] |
| **CD73** | contribution-freeze byte (nonzero ⇒ `P` held) | setting logic; runtime value normally 0 [INF] |
| **store[8] → R** | nominal capacity in tons: R = byte / 12.0 | descriptor range 0–72; **factory default 24 → R = 2.0**; hypothesis for this install: 60 → R = 5.0 [P §5.1, §7.5] |
| **X** (mirror float 0xFFF820F8, validity 0xFFF820F5) | nominal-size input to K = 34.286 × (137 + 3.5X) | producer clamps [12, 61], invalid → 61 (a second reader uses unclamped, invalid → 65.0); [INF] hypothesis X = 60 = ODU kBTU [P §2, §7.5] |
| **CC52** (field-store bytes [1..2]) | equipment class word — selects the table branches, counts, CFM detour | factory default 0x0000 (unconfigured). **Primary candidates {0x8141, 0x91C1}** — formula-identical (category 7 vs 1; both arm the `(CC52 & 0xF) == 1` CFM detour); {0x8142, 0x91C2, 0xC195} not excluded [P §7.2, Audit-2 §1(e)] |
| **CBF4** (field-store bytes [3..4]) | twin class word — builds CC04/CC1C/CC34 | unknown; default 0x0000 [P §7.2] |
| **U1 / U2** (mirror floats 0xFFF8220C / 0xFFF82210) | dimensionless stage factors (only for 0x8142-type classes) | via `FUN_181f59e0`; irrelevant if CC52 ∈ {0x8141, 0x91C1} [P §2.3] |
| **C74D / C74E** (bytes 0xFFF8C74D/E) | selector bytes for the dictionary-selector table forms and the CFM detour gate | unknown [P §2.4, R §2.2] |
| **CFM store limits** 197/199 (heat), 4062/4064 (cool) | final CFM floor/cap (§5.6 step 5) | **defaults 0 = unset/skipped** [R §1.2] |
| **CFM table contents** CC04/CC1C/CC7C/CC64/CC94/CCAC | interpolation tables of §5.6 step 1 | builders exist (0x181F0xxx/0x181F3xxx clusters) but were not decompiled — **calibration data**; capture anchors in §5.6 bound them [R §10] |
| **field 0x1B** | changeover delay, minutes (§5.1) | field-store byte; value unknown [S §2] |

### 9.2 What the sensitivity analysis already fixes [P §7.5]

Under hypothesis H (X = 60, store[8] = 60, CC52 ∈ {0x8141, 0x91C1}) the
threshold tables are fully determined (§5.3): CCC4 = {0, 60000, 0, 0},
CCDC = {0, 59486.2, 0, 0}, CD04[0] = 5.0, CC5A = 2. The tables scale
**linearly** in store[8] (R ∈ {2, 3, 4, 5, 6} for byte ∈ {24, 36, 48,
60, 72}), so a single behavioural observation of a staging threshold
(one demand value at which the stage flips, compared against the
formula) pins store[8] — and with it R — exactly. X enters only through
K, and only into CCDC; a heat-side threshold observation separates X
from R. [P §7.5]

### 9.3 Pinning routes (in order of preference)

1. **Runtime snapshot (definitive, no known channel).** The values live
   at known addresses — field store: CC52 @0x3C0E4A21, CBF4 @0x3C0E4A23,
   R byte @0x3C0E4A28, twin byte @0x3C0E4A32; mirrors: X @0xFFF820F8
   (+validity @0xFFF820F5), U1/U2 @0xFFF8220C/10, selectors
   @0xFFF8C74D/E, category byte @0x3C12A8D5; finished tables: CCC4
   @0xFFF8CCC4, CCDC @0xFFF8CCDC, CD04 @0xFFF8CD04, CC04 @0xFFF8CC04,
   CC1C @0xFFF8CC1C, CC34 @0xFFF8CC34 (24 B each). **No live read
   channel is known**: no JTAG evidence exists, and the Clarinox debug
   ports (4002/14321) appear flag-disabled. Treat this route as
   opportunistic only. [P §7.4]
2. **Behavioural pinning (practical).** Observe staging thresholds and
   CFM values on the live bus against the formulas of §5: one staging
   observation pins store[8] (§9.2); the CFM anchors of §5.6 (1368 /
   1617 heat, 1232–1760 cool, 1166 fan-only, 1750 commissioning) bound
   the CFM tables; the path A/B personality (FS_1FDF) is separable by
   the demand response shape to a known setpoint step (deadband-window
   integrator vs proportional+share law). [P §7.5, O §2]
3. **Shadow-emulator calibration (the planned route).** Run the
   emulator passively alongside Ion: feed it the same inputs (zone
   temperature, setpoints, mode), compute its `CD44`/stage/CFM outputs,
   and diff against Ion's actual `0305` writes cycle by cycle; fit the
   §9.1 parameters until the outputs track. This closes B-12 without
   any privileged access, and simultaneously validates §5 end-to-end
   before any takeover. [Audit-2 B-12]

---

## 10. Failover design constraints

The emulator's reason to exist is taking over when Ion dies. The
constraints below are normative; of the two numbers that would make the
design exact, the furnace comm-fault timeout is now **bounded below at
> ~36 s** (thermostat-reseat capture `sam-reseat-20261029-151123.jsonl`,
1,611 frames, ~36 s thermostat-only outage, no equipment reaction
[Map (d), V-2, verification 2026-11-26]); its exact value and Ion's
recovery time are still unmeasured (§11 T-1).

1. **Ion always wins.** 0x20 is the bus's sole initiator; two initiators
   corrupt the bus. On hearing **any** frame sourced from a real 0x20,
   the emulator must stop transmitting immediately and return to silent
   listening — no graceful handover, no final burst. [Map (d), project
   design]
2. **Takeover delay — lower bound.** Ion's maximum steady-state TX gap
   is 2.81 s (4.90 s in wizard phases). The silence threshold for
   declaring Ion dead must exceed this by a wide margin; the parent
   design listens silently for ≥ 2 min after its own boot before
   assuming any active role. (That ≥2 min is the startup rule, not
   the takeover threshold — the threshold is rule 3 below.)
   [Map (d), U §4]
3. **Takeover delay — upper bound.** The ODU enters standby ≈ **2 min**
   after its last valid message (COMM LED off at 2 min) [Y §6]. Standby
   is recoverable — the next valid frame re-lights COMM — but a
   takeover that lands well inside ~2 min of Ion's death avoids a
   mid-call ODU stand-down entirely. The design target is therefore:
   **threshold between Ion's recovery time and the furnace comm-fault
   timeout** — the timeout is bounded below at > ~36 s but its exact
   value is unmeasured, and Ion's recovery time is unmeasured, until
   T-1 is measured; until then, prefer the shortest silence threshold
   that cannot false-trigger on Ion's known gaps and boot behaviour
   (note the 78 s silence in the captures was a whole-system power
   cycle and proves nothing about live-bus thermostat death [Map (d)]).
4. **On takeover**, run §3 from B1 (the 0x1F ritual included — it is
   also the re-discovery ritual after silence [U B1]) and resume the
   last known mode/setpoints from persisted state (§3 B10). Surface
   the takeover to Home Assistant; likewise surface any yield (rule 1)
   immediately.
5. **A co-resident SAM-persona node** (the existing DIY node, if it
   keeps its SAM role) must observe its own 180 s TX holdoff after the
   last 0x1F frame before transmitting as 0x92 [V §4] — coordinate the
   two nodes' state machines so the emulator's boot ritual does not
   collide with the SAM node's transmissions.

---

## 11. Open gaps checklist

### Blocks coding / calibration

| Gap | What is open | What closes it |
|---|---|---|
| **B-2** | Our unit's exact **CC52** class word. Candidates {0x8141, 0x91C1} primary (formula-identical); {0x8142, 0x91C2, 0xC195} not excluded. | A §9.3-route-1 snapshot (no channel known), or behavioural pinning (§9.3 route 2/3). Coding may proceed on the primary candidates — the demand tables are identical for both. [Audit-2 §5.1] |
| **B-5** | **Cool part-load behaviour**: whether `0605` ever takes values 1.0–4.0 in real weather, and the producer law if it does. v1 law (§6.2) ships without them. | A long mild-weather cool capture (sustained part-load, hot full-load, restart cadence, changeover transients, humid/dehum cases) per [T §10]. |
| **B-11** | **Heat staging producer** unisolated (candidates `FUN_180c3012/3418/3814/3bee/46b8`). Low rank: the hysteresis form is proven on the cool machine and the captured staircase (§5.5) suffices to implement. | Static isolation of one candidate, or a heat-call capture with demand logged against stage flips. [Audit-2 §5.1] |
| **B-12** | **Configuration values** (§9.1): G, K9F4, CA04/CA24/C880/CD1C, FS_1FDF, store[8], X, CBF4, selectors, CFM tables. | §9.3: snapshot (no channel), behavioural pinning, or shadow-emulator calibration (planned). [Audit-2 §5.1] |
| B-7 (residual) | The exact internal **name** of the §7 byte's state. Behaviour fully specified; closed in practice. | A capture with the thermostat's own indoor T+RH logged, a constant-OAT humidity swing, a multi-hour idle soak, or a firmware stage naming the staging-buffer source cell. [B7 §4] |
| B-8′ (residual) | Frame-layer internals: RX invoker/cadence source, descriptor registration, `FUN_180a49a8` internals, `FUN_180a7500` format codes. **Non-blocking** — §2 specifies wire behaviour completely. | Further static work only if bit-exact engine emulation is ever wanted. [Audit-2 §5.1] |
| DIR-C lengths | **RESOLVED** (verification 2026-11-26): the field is the thermostat's own serve-image size; all 7 wire-served tables match DIR-C exactly. Equipment answer sizes (0302 24/12, 0304 16/8, 0307 3) are per-device and do not govern serving. §4.1 updated. | Closed. |

### Blocks live testing

| Test | What it measures | Protocol sketch |
|---|---|---|
| **T-1** (= G1) | **Furnace comm-fault timeout** and mid-call thermostat-death behaviour — the gating measurement for §10. Also watch the ODU at its ~2 min standby mark. Lower bound already > ~36 s from the reseat capture (Map (d), V-2); the live test extends the outage past 36 s to find the exact value. | ESP capturing; Ion mid-heat-call in mild weather; pull Ion only; watch the 30 s / 2 min / 5 min / 10 min marks (furnace LED + bus traffic); repeat at idle. [Audit-2 §5.2] |
| **T-2** (= G5) | Boot variants: furnace-only power cycle; thermostat reseat with verified capture running. | Power-cycle one device at a time with the capture live; diff against §3. [Audit-2 §5.2] |
| **T-3** (= G9) | Exception behaviour of 0x44/0x53 (does equipment ever emit func `0x15`?). **Only with the author's explicit go-ahead** — the only test that transmits probes. | Crafted bad-CRC / unknown-table frames toward each device; record any response. [Audit-2 §5.2] |
| **T-4** | Mode-experiment session 1, narrowed: SYSCTRL byte 49 and `3B02[22]` in Heat/Cool/Auto/Off, plus the fan-only user setting — separates R = 3 vs R = 4 (§5.1). | Read-only session: set each mode at the wall, capture `400A`/SYSCTRL-side state per mode. [Audit-2 §5.2, S §6] |
| **T-5** | Seasonal captures (summer cooling at load; deep-winter heating). | Long captures in real weather; closes B-5 and validates §5.6 CFM anchors at the extremes. [Audit-2 §5.2] |

### Closed by the source reports (for the record)

B-1 demand formula [O]; B-3 CFM as formula [R] (residue = table
contents, in B-12); B-4 coordinate conversion [Q as corrected by
Audit-2]; B-6 boot/commissioning for this configuration [U — marked
unaudited by Audit-2, used here as the best available source]; B-8
frame layer [AA]; B-9 mode semantics (internal side) [S]; B-10 SAM
surface [V]. [Audit-2 §5.1]
