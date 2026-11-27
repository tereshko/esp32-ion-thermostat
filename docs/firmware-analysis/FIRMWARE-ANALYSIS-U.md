# FIRMWARE-ANALYSIS-U.md — Commissioning / Discovery specification for the emulator, and the 0x0E verdict

Stage U, 2026-11-26. Desk work on project files and captures only; nothing
was flashed or written to any device.

**Mission:** one ordered boot script an autonomous replacement thermostat
must execute on the ABCD bus to discover the furnace (0x44) and the ODU
(0x53), commission itself (including the coil-parameter commit into 061E),
and reach steady state exactly as Ion does — plus a verdict on address
0x0E, the commissioning-input/persistence inventory, and the known/unknown
failure behaviour at boot.

**Confidence labels:** **[OBS]** = observed in a capture (ours or
gofinity's). **[FACT]** = decompiled/measured in the firmware image by an
earlier stage. **[INF]** = inference, reasoning shown. **[LIT]** =
vendor/community literature. **[UNK]** = not established; needs a live
test.

**Sources:** `THERMOSTAT-PROTOCOL-MAP.md` (boot ritual, poll tiers);
our 19 capture files in `traces/` (101,352 frames total, re-censused this
stage); `traces/external/gofinity-bootup.bin` (1,532 frames, independently
re-parsed this stage: CRC-16 poly 0x8005 reflected, init 0, stored
little-endian; 0 skipped bytes, all CRCs valid) +
`external-research/gofinity-bootup.md`; `FIRMWARE-ANALYSIS-C.md` (field
store, commissioning latch); `-D.md` (coil commit); `-F.md` (binding
groups, canonicalizer); `-I.md`/`-L.md` (0316 store mirror, class word);
InfinitESP + infinitive local sources; Infinitude wiki "Infinity — known
devices" and "Infinity Framing Protocol" (fetched 2026-11-26).

---

## 1. The boot script

Times are from our coldstart capture (`coldstart-20261029-125733.jsonl`,
t=0 = 2026-10-29T16:57:50.999Z, a whole-system power restore) unless
marked [gofinity]. Frame indices for gofinity refer to
`gofinity-bootup.bin` (no timestamps exist in that file; ordering only).

### B0 — Power-up: the bus is not silent, and the thermostat is late

- The furnace boots faster than the thermostat. At t=0 the furnace is
  already transmitting its autonomous sub-unit poll: bursts of
  `44→45 READ 030A` (×6, ~45 ms apart), repeated at +62.3 / +124.1 /
  +185.0 / +247.5 s, then never again. This is the furnace↔sub-unit
  channel (cf. wiki: indoor unit reads 030A from its sub-unit), **not**
  a thermostat fault signal. **[OBS]**
- A diagnostic node (0x93) may poll `3B05` at the thermostat from
  +0.28 s; it gets no answer until the thermostat is up (first answer
  +196.6 s in coldstart). The emulator must eventually serve 3B05
  (11 zero bytes) — see B9. **[OBS]**
- Emulator requirement: listen-only until its own SystemInit moment;
  do not answer the furnace's 030A bursts (they are not addressed to
  the thermostat).

### B1 — SystemInit broadcast triplet (t ≈ +6.0 s)

The thermostat comes up under the temporary discovery persona **0x1F**
and emits exactly three broadcast writes to **0xF1**, in this order
**[OBS — byte-identical in our coldstart and in gofinity frames 0–2]**:

| # | Frame | Payload |
|---|---|---|
| 1 | `1F→F1 WRITE 0305` | 12 × 0x00 |
| 2 | `1F→F1 WRITE 3E02` | 1 × 0x00 |
| 3 | `1F→F1 WRITE 0605` | 7 × 0x00 |

Semantics: a zeroed demand (0305), a zeroed two-capacity stage byte
(3E02), a zeroed variable-speed stage float (0605) — "everything off,
identify yourselves". In sam-commissioning the same 1F phase began at
+82 s after the power event, preceded by 78.23 s of total 0x20 silence —
the 1F phase is a (re)discovery ritual, not only a cold-boot one.
**[OBS]**

### B2 — The 0x1F sweep (≈ +6.0 … +16.7 s)

Cadence ~95 ms per probe. Retry rule **[OBS, both systems]**:

- probe **unanswered → sent twice** (×2);
- probe **answered → sent once** (×1) and the device is registered.

Probe programme (our Ion, order as captured; gofinity's is the same
programme in a slightly different order) **[OBS]**:

- `030A → 20` ×2 (self/persona check)
- `030D, 031B → 46`; `0326, 0327 → 5A, 5C`
- `0404 → 46, 5F, 69`
- `0104 → 21, 22, …, 28` (secondary thermostats), `→ 5F, 69, 92, 94`
- `0302 → 60, 61` (zone controllers)
- `0307 → 3F, 44 (ANSWER), 46`; `0402 → 3F`; `041C → 44 (ANSWER)`;
  `041F → 3F, 44`; `0438 → 3F`
- `061F → 53 (ANSWER)` — the ODU is first touched here
- `3405 → 80` (NIM)
- Second pass: `0104 → 3F, 44 (ANSWER, 120 B), 46, 58, 53 (ANSWER,
  120 B), 55, 5A, 5C, 60, 61, 80`; `0306 → 3F, 44 (ANSWER)`;
  `030A → 3F, 44 (ANSWER), 46`
- 3E-family hunt: `20→58 READ 3E01` ×8 and `3E0A` ×8 during this window
  (canonical class 0x50 slot via bus 0x58) — all unanswered on our
  install (our ODU is variable-speed and refuses the 3E family).
  **[OBS]** Gofinity's thermostat additionally runs the 0x0E hunt
  (§2) — ours never does.

Discovery results are classified by the identification handlers on the
device-type word (field-store offset 1, mask 0x7C00 routing) **[FACT,
stage C §4.1]** and bound into RAM device objects (0x3C0Dxxxx) by the
binding engine **[FACT, stages C/F]**. The emulator equivalent: build
its device registry from the 0104 answers received in this sweep —
identity strings, CESR numbers, device class per address.

### B3 — Persona handoff 1F → 20 (t ≈ +16.7 s)

Last 0x1F frame at +16.67 s; first 0x20 frame at +16.69 s. The handoff
is seamless mid-programme: in gofinity, frame 106 is
`1F→0E READ 3E0A` and frame 107 is `20→0E READ 3E0A` — the 0x20 persona
continues the very probe the 1F persona was running. **[OBS]**
No announcement frame marks the transition; the emulator simply starts
sourcing frames from 0x20.

### B4 — The 0x20 second sweep + wizard scans (≈ +16.7 … +61.8 s)

- The 0x20 persona re-runs the discovery programme interleaved with the
  first steady-state polls. First steady read at +23.95 s
  (`20→44 READ 0104`). Retries escalate ×2 / ×4 / ×8 per
  (address, register) for unanswered probes. Last sweep probe at
  +61.76 s; **boot-to-steady ≈ 62 s**. **[OBS]**
- Wizard/equipment-ID scans ride along: deep table reads at candidate
  addresses (`46: 0403/0404/0407/040B/040C/040F`; `60/61: 3405`;
  `5F/69: 0404`; SAM hunt `0104 + 030D → 92` repeated). Max thermostat
  TX gap in this phase: 4.90 s. **[OBS]**
- Boot-only write: `20→44 WRITE 0418` payload `000000`, ×2, at ≈ +62 s
  (coldstart and sam-commissioning; in full-install a later non-zero
  `5A030F` pair also occurs during install activity). 16 frames total
  across all captures, all in boot/install windows, never in steady
  state. **[OBS]**

### B5 — Per-device configuration writes

**Furnace (0x44) — our install, reboot of a commissioned unit [OBS]:**
no configuration writes at boot beyond B4's `0418`. The furnace is
configured by being *read*: identity `0104`, config `0316` (mirrored
into field store offsets 0x1BC–0x1C3 **[FACT, stage I]**), status
`0306/030A/0307/041C/041F…` per the poll tiers (§1 B8).

**ODU, variable-speed (our 0x53) [OBS]:** no boot-time config writes
either; the ODU receives its orders through the steady command burst
(B7), which carries the coil parameter in 061E from the very first
burst.

**First-ever commissioning only — the 031C writes [OBS gofinity;
absent in ALL our captures]:** on gofinity's (2014 Bryant) boot the
thermostat writes `031C` to the furnace (first at frame 534, 41-byte
payload, byte 0 = 0x22) and to the ODU (first at frame 584, byte 0 =
0x10), then repeats the ODU write many times with byte 0 incrementing
(0x10 → 0x19 → 0x1F → 0x20 → 0x2D → 0x2E → 0x2F → 0x35 across the
capture). The Infinitude wiki calls 031C the *setup-complete marker*
written to IDU and ODU in commissioning phases 4/5 **[LIT]**. Our Ion
has **never** written 031C in 101,352 captured frames — coldstart,
sam-commissioning, full-install included. Explanation **[INF, strong]**:
stage C proved the supervisor stops driving the commissioning state
machine once the completion latch (field-store offset 5) reads 'Z'
**[FACT, stage C §4.2]** — a reboot of an already-commissioned unit
skips the deep commissioning sequence, 031C writes included. Emulator
rule: write 031C (byte 0 = per-device counter, semantics of the exact
value unresolved) **only** as part of a first-commissioning flow; a
commissioned reboot must not emit it. Byte-0 semantics: **[UNK]** (not
needed beyond "increments per write to the same device").

**ODU, two-capacity (gofinity's 0x50) config-write set [OBS]:** once
the ODU is identified, the thermostat writes, as a repeating set:
`WRITE 3E0A` = `0022B8`, `WRITE 3E02` = `00`, `WRITE 3E03` = `02`,
`WRITE 050F` = `FF000000`, `WRITE 0510` = `00000000`, plus the 031C
writes above. Not applicable to our variable-speed ODU (it refuses
3E writes with exception 0x15/0x04 — InfinitESP live evidence), but
part of the platform's commissioning repertoire.

### B6 — The coil commit (our install's critical commissioning act)

The indoor coil is **not learned from the bus**. It is selected at
commissioning (dealer/wizard "Indoor Evaporator Selection" **[LIT]**)
and resolved against the firmware's built-in coil catalogue: our coil
EN(A,D)4X61 → parameter **1.69** (float32 0x3FD851EC) **[FACT, stage
D]**. The commit path **[FACT, stage D]**: FUN_18140BEA/FUN_18140C80
write the field store — `0x59F ← param`, `0x1C7C ← b4`, `0x1C7D ← b5`,
`0x1C7E ← (u16)(f1 × 65535)`; the catalogue index comes from field
0x9A. Thereafter **every** 061E write to the ODU carries it:
`061E = 0F 3F D8 51 EC 06 00 00 00` (bytes [1..4] = the float,
big-endian) **[OBS + FACT]**. Emulator rule: persist the coil
selection (§3); derive the 061E payload from it; never re-derive it
from bus traffic.

### B7 — First demand

- Our coldstart: first command burst at **+39.10 s** (inside the B4
  window — control starts before discovery fully closes). **[OBS]**
- Gofinity: first demand at frame 646: `20→40 WRITE 0305`, payload
  11 × 0x00 + **0x78**. Byte [11] = 0x78 is the thermostat object's
  state byte — 0x00 before commissioning completes, 0x78 after; it is
  not a checksum (stage N: identical in all 1,811 captured 0305
  writes; all-zero-payload frames occur only in commissioning
  windows). **[FACT/OBS, stage N]**
- The steady command burst (≈ every 10 s) **[OBS, protocol map]**:
  →44: `0305` (demand), `0403` = `00010100`, `0409` = `00010000`,
  `0307` = `00000000`; →53: `0605` (stage float), `060D` (call flag),
  `0610`, `0612` = `22B8…`, `061A` = `01`, `061E` (coil, B6).
  Burst internal spacing: 0305 → +41 ms 0403 → +45 ms 0409 → +45 ms
  0307 **[FACT, stage N]**.

### B8 — Steady state (reached ≈ +62 s)

Poll tiers **[OBS, protocol map §a]** (periods drift; treat as
Ion-faithful targets, not exact clocks):

| Tier | Tables |
|---|---|
| ~3 s | `0104→44`, `0104→53`, `0306`, `030A` |
| ~5 s | `0302/0303→53`, `0307`, `0413`, `041B`, `0604`, `0608`, `061F` |
| ~7 s | `0404`, `040D` |
| ~10 s | command burst (B7) + `031F/0320/0321`, `060A` |
| ~11 s | `030D`, `0316`, `0402`, `0409`, `0304→53`, `060E` |
| ~17–20 s | `0310/0311`; writes `060B`, `0414` |
| ~29–31 s | `0625`; `030E`; write `031D` |
| ~60 s | broadcast `0202/0203` SYSTIME → F1 |

Link behaviour: answer latency median 19 ms / p90 48 ms; ~0.6 % of
steady reads go unanswered and the loop simply moves on; a healthy
thermostat's max TX gap is 2.81 s in steady state. **[OBS]**

### B9 — Obligations toward other bus citizens

- **SAM slot (0x92/0x94):** discovery probes both (`0104`, `030D`);
  presence is an internal binding outcome, not a bus handshake
  **[FACT, stage C]**. An emulator replacing Ion inherits Ion's side
  of this; a separate SAM-persona device (our ESP) must observe the
  180 s transmit holdoff after the last 0x1F frame **[LIT/OBS,
  InfinitESP]**.
- **Diagnostic node 0x93:** reads `3B05` every 300 s; answer with
  11 zero bytes. **[OBS]**
- **Furnace sub-unit channel 44→45:** leave alone (B0).

### B10 — What a commissioned reboot skips (summary)

Skipped when the field-5 latch is set: the commissioning state machine
entirely — no 031C writes, no wizard blocking, no evaporator
selection. Still executed every boot: B1 triplet, B2/B4 sweeps (the
device registry is RAM and is rebuilt), B4's 0418 pair, B6's 061E
(from persisted coil fields), B7/B8. **[FACT stage C + OBS]**

---

## 2. The 0x0E mystery — verdict

### Evidence

1. **Gofinity's thermostat hunts 0x0E relentlessly.** Re-parsed census:
   110 frames to 0x0E — `3E08` ×50, `3E01` ×30, `3E0A` ×30; from 0x1F
   ×24, from 0x20 ×86. Pattern: bursts of exactly ×10 identical reads
   (frames 61–70: 3E08; 93–102: 3E01), the handoff mid-burst (frame
   106 1F→0E 3E0A, frame 107 20→0E 3E0A), then repeating burst cycles
   for the whole capture. **Zero frames ever originate from 0x0E.**
   **[OBS]**
2. **Correction to `external-research/gofinity-bootup.md`:** register
   **3E10 does not occur anywhere in the capture** (0 frames). The
   note's "READ 3E10" claims and its "handoff = READ 3E10→0E" are
   wrong; the real handoff probe is 3E0A. The note's other spot claim
   **is** verified: the ODU at 0x50 answers `3E01` with 13 bytes
   `03b9039903ff03ff000000013c`. **[OBS, this stage]**
3. **Our Ion never touches 0x0E.** 0 frames with src or dst 0x0E in
   101,352 frames across all 19 captures. Our Ion's complete dst set:
   1F, 20, 21–28, 3F, 44, 45, 46, 53, 55, 58, 5A, 5C, 5F, 60, 61, 69,
   80, 92, 93, 94, F1. Its two-capacity hunt goes to the class-0x50
   slot via bus 0x58 (B2). It never reads 3E08 at all (the single 3E08
   frame in our archive is our own SAM node polling the ODU).
   **[OBS, this stage]**
4. **The firmware carries a real 0x0E device slot.** In the binding
   group table (stage F dump, confirmed identical in v4.74 by stage
   W), the 3E family is bound for exactly two slots: **0x0E and
   0x50**. The identity tables **3E07, 3E08, 3E09, 3E0B, 3E0E exist
   ONLY for slot 0x0E**; 3E01/3E02/3E03/3E04/3E0A/3E0C/3E0D exist for
   both. Slot 0x0E has **no 0104 group** — a device there has no
   standard identity table; its identity is 3E08 (model string) /
   3E09 (serial string), exactly the tables InfinitESP/infinitive
   document for two-capacity ODUs, and exactly the order gofinity's
   thermostat probes them (identity 3E08 first). Generic per-device
   tables 031F/0320/0321 also carry a 0x0E group. The address
   canonicalizer (FUN_180c6ebe) passes 0x0E through unchanged — it is
   not an alias of any equipment class. **[FACT]**
5. **Community knowledge:** the Infinitude wiki known-devices list
   carries one row for it — "Device Interfaces? | 0E | NIM?" — flagged
   as a guess, no verified model, ever. InfinitESP and infinitive
   know no device at 0x0E; their 3E knowledge is entirely class-5
   (ODU). No Carrier/ICP literature found in stages H/K or this
   stage's search names a product at 0x0E. **[LIT]**

### Verdict

**0x0E is a reserved discovery slot in the thermostat firmware for a
two-capacity ("Everest"-family) outdoor device that identifies itself
through the 3E register family — 3E08 model / 3E09 serial — instead of
the standard 0104 identity table.** The firmware models it completely
(binding groups, identity tables bound nowhere else), and at least the
2014 Bryant Evolution firmware generation actively hunts it at every
boot in ×10 bursts, forever, without it ever answering in any recorded
system. The leading interpretation **[INF]**: the slot belongs to the
*original/legacy addressing of the two-capacity ODU or of an interface
module presenting one* (the wiki's "NIM?" guess points the same way —
an interface-presented outdoor unit would naturally speak the oldest
ODU register family and identify via 3E08/3E09). Which physical
product, if any, ever occupied 0x0E cannot be determined from any
available source: **no answering device at 0x0E has ever been
recorded.** The slot semantics (3E-family device, identity via
3E08/3E09, no 0104) are **[FACT]**; the product identity is
**[UNK]**.

**Emulator guidance:** 0x0E is **not** part of our install's boot
contract — our Ion (v4.79) never probes it in 101k frames. The
emulator may omit the 0x0E hunt entirely. If platform fidelity is
ever wanted, the hunt is: bursts of ×10 `READ 3E08`, then ×10
`READ 3E01`, then `READ 3E0A`, repeated cyclically, with no
consequence when unanswered.

---

## 3. Commissioning inputs and persistence

### 3.1 What the thermostat must learn from the bus at boot

| Value | Source frame(s) | Then lives in |
|---|---|---|
| Furnace identity (CESR******-**, model G80CTL1352422A2) | `0104` ACK from 0x44 (120 B), B2 sweep | RAM device object; re-read on ~3 s tier |
| Furnace config (stages, blower, limits) | `0316` ACK from 0x44 | field store 0x1BC–0x1C3 **[FACT stage I]** |
| ODU identity (CESR******-**, model HVA960GKA201) | `0104` ACK from 0x53 (120 B), B2 sweep | RAM device object |
| Equipment class word | derived during discovery from the identification results (handlers route on it, mask 0x7C00) | **field store offset 1**; read by FUN_181f21d4 → CC52 **[FACT stages C/L]** |
| ODU operating tables (0302/0303/0304, 0604/0608/061F…) | steady poll tiers | RAM only |
| SAM/B36 presence | internal binding outcome of discovery | field store 0xC4 / 0x23 (outputs, refreshed by the manager machine) **[FACT stage C]** |

**Not from the bus:** the coil (B6 — catalogue + stored selection);
user schedules/setpoints (400A content mirrors stored profiles).

Open items handed to stage P (bus side cannot close them): the exact
bit encoding of the class word for *our* equipment combination; the
bus provenance of **field 8** (stage L: R = (field-8 byte)/12.0 — no
stage has isolated which frame, if any, writes field 8); the writer
of the **X float** at RAM 0xFFF820F8 (a binding-engine-maintained
variable, clamped [12, 61] by FUN_181f21d4).

### 3.2 What must persist across power cycles (NVRAM field store)

The field store is a flat byte array (base 0x3C0E4A20) backed by
NVRAM with a page engine — background flush of dirty pages
(FUN_1815941c) and verify/repair (FUN_18159540); fields load from
NVRAM at boot, and a field discovery never sets keeps its stored or
descriptor-default value **[FACT, stage C §1]**. The emulator's
persistence list:

- **offset 1** — equipment class word (§3.1).
- **offset 5** — commissioning-complete latch ('Z'); gates the whole
  commissioning machine (B10).
- **offsets 0x23 / 0xC4** — accessory (B36/SAM) presence bytes.
- **offset 0x9A** — coil catalogue index; **0x59F / 0x1C7C / 0x1C7D /
  0x1C7E** — the committed coil parameter set (B6).
- **0x1BC–0x1C3** — furnace config mirror (from 0316; refreshed from
  the bus, but stored).
- All user/dealer settings: profiles and setpoints (the 400A rows),
  dictionary settings (lockouts, latch, staging limits…), dealer
  information.
- Descriptor defaults (table @0x182B04D4) restore any field whose
  provider is NULL — the emulator needs equivalent factory defaults
  for first boot.

**RAM-only, rebuilt every boot (do NOT persist):** device objects
0x3C0Dxxxx and their binding state (including the SAM object's
+0x38 bound dword — the stage-C gate operand), the active-address
bitmap, demand/staging runtime state, the 0305 state byte 0x78
(derived: 0 until commissioned, 0x78 after).

---

## 4. Failure behaviour at boot

**Established:**

- Unanswered discovery probes never block boot. The 1F sweep uses
  ×2/×1 (B2); the 0x20 phase escalates ×2/×4/×8 and moves on; an
  entirely absent expected device (gofinity's 0x0E) is retried in
  ×10 bursts cyclically, forever, with no fault and no effect on
  steady state. **[OBS]**
- Steady state tolerates silence: ~0.6 % of reads unanswered, loop
  continues; no re-discovery storm follows isolated misses. **[OBS]**
- At *first* commissioning, a missing unit blocks the wizard with a
  named screen: "If indoor unit is found, but the outdoor unit is
  not found, 'OUTDOOR UNIT NOT IDENTIFIED' will appear", followed by
  a manual Outdoor Unit Identification procedure **[LIT, SYSTXCCUID01
  installation instructions]**; the ITC01 commissioning sequence is
  likewise a gated step list (Searching for Indoor Unit → Searching
  for Outdoor Unit → Indoor Evaporator Selection → …) **[LIT]**.
- Loss of comms in operation surfaces as a thermostat fault: our own
  2026-11-24 incident — furnace stopped answering (bus fault) → Ion
  displayed **INDOOR UNIT COMMUNICATION FAULT** and outdoor
  temperature went "---". **[OBS]** Device-side, the ODU control
  flashes its own fault code on loss of UI communication **[LIT,
  25HNH5/25VNA4 manuals]**.

**Unknown — for the live tests (do not guess):**

1. **Comm-fault timeout (test G1):** how long the furnace/ODU must be
   silent before the thermostat raises the comm fault. Not derivable
   from the archive: the one long silence in our captures (78 s) was
   a whole-system power cycle — the equipment watchdogs were reset
   by the same outage, so it proves nothing about a live-bus
   thermostat death.
2. Whether a *commissioned* unit that boots with the furnace or ODU
   absent re-enters any wizard step, and what it displays before the
   comm-fault timeout fires.
3. The thermostat's recovery cadence once a faulted device starts
   answering again mid-operation (poll-tier absorption vs a fresh
   sweep).
4. 031C byte-0 semantics (§1 B5) — cosmetic for the emulator, listed
   for completeness.

---

## 5. Emulator checklist (one-screen summary)

1. Listen; ignore 44→45 030A bursts. **(B0)**
2. At +~6 s, as 0x1F: broadcast triplet 0305/3E02/0605 zeroed → F1. **(B1)**
3. 1F sweep, ~95 ms cadence, ×2 unanswered / ×1 answered; build the
   device registry from 0104 answers. **(B2)**
4. Hand off to 0x20 mid-programme; second sweep + wizard scans with
   ×2/×4/×8 retries; 0418 `000000` ×2 → 44. **(B3–B4)**
5. First-commissioning only: evaporator selection → coil commit;
   031C writes. Commissioned reboot: skip both. **(B5–B6, B10)**
6. First command burst by ~+39 s; 0305 state byte 0x78 once
   commissioned. **(B7)**
7. Steady poll tiers by ~+62 s; SYSTIME broadcast ~60 s; serve 3B05
   to 0x93. **(B8–B9)**
8. Never probe 0x0E (our platform behaviour); never write 031C on a
   commissioned reboot; persist exactly the §3.2 list.
