# How it works — the Ion bus, the control law, and this node

One document with everything this project has established about the
Carrier/ICP **Ion System Control** bus and about controlling the system
from an ESP node. Every load-bearing claim here was derived from primary
artifacts — live bus captures, the thermostat firmware image (v4.79,
decoded and analysed function by function), and the factory service
manuals — and then independently re-verified. Where something is still
unknown, it is listed as unknown in §12.

Reference installation: SYST0101CW wall control (firmware v4.79),
Heil G80CTL1352422A two-stage gas furnace (107K BTU/h; the bus
reports the model string as G80CTL1352422A2), Heil HVA960GKA
variable-speed outdoor unit (60K, 5 ton), EN(A,D)4X61 evaporator coil,
single zone.

## 1. The system at a glance

Three kinds of participants share one RS-485 bus:

| Address | Device | Role |
|---|---|---|
| `0x20` | Ion wall control | The thermostat. **The only initiator on the bus.** |
| `0x44` | Furnace control board | Executes heat/fan demands, reports status |
| `0x53` | Outdoor unit board | Executes compressor demands, reports status |
| `0x92` | SAM (System Access Module) | Accessory slot — this is where our ESP node sits |
| `0x1F` | The thermostat again, at boot | Temporary persona during commissioning |

The thermostat polls, computes and commands. The equipment boards never
initiate anything in steady state: they answer polls and run their own
protection logic (§8). There is **no indoor-temperature channel on the
bus** — the thermostat's room sensor is internal to the wall unit, which
is why any replacement needs a temperature sensor of its own.

## 2. The wire protocol

- Physical: RS-485, **38400 baud, 8N1**. Wall cable: DX+ green,
  DX− blue, C (common) white, D red (24 VAC).
- A frame is a small header (destination, source, length, function,
  table id) plus payload, closed by a 16-bit CRC: nibble-wise
  reflected CRC (polynomial A001, init 0), transmitted little-endian
  after a final byte swap. The exact builder routine was recovered
  from the firmware image; it is proven on the wire by the
  independent gofinity capture (1,532/1,532 frames) and
  self-consistent on this installation's reconstructed frame bodies
  — the local JSONL corpus stores no CRC bytes, so a wire-level
  check against it is impossible in principle.
- Function `0x0B` = read a table (the request), `0x06` = the read
  response, `0x0C` = write a table (full read-modify-write of the
  whole table image). This dialect has no write-acknowledgement
  function. Tables are addressed by a 16-bit id whose high byte
  names the owning device class (03xx/04xx furnace, 06xx outdoor
  unit, 3Bxx SAM, 40xx the shared comfort table).
- Frame payloads are built from per-class *staging blobs*: the
  thermostat keeps a RAM image per outgoing table and serialises it on
  schedule. An emulator therefore needs the same images, not ad-hoc
  frame assembly.

## 3. Steady state — who says what

The thermostat runs a fixed poll schedule in tiers (≈3/5/7/10/11/17/20/
29/31 s). The furnace and the outdoor unit are polled for identity,
status and operating data. The SAM slot is the mirror image: the
node at 0x92 polls the thermostat's 3B02/3B03 tables (median period
3.00 s, strictly alternating) and is served zeros (§6).

Every ≈10 s the thermostat emits the **command burst** — the frames
that actually run the house:

- `0305` — the demand frame (12 B): heat stage `[0]`, cool stage `[2]`,
  blower CFM `[4..5]`, and a state byte `0x78` at `[11]` that is
  constant once the system is commissioned.
- `0605` — compressor capacity command (7 B): a float on a **0–5
  scale** in `[0..3]`, a call-state byte at `[4]`, `[5]` always 0.
- `060D` — a one-byte call flag to the outdoor unit.
- `061E` — present in **every** burst (9 B): carries the evaporator
  coil parameter as a float (for the EN(A,D)4X61 coil, 1.69). It is
  built from the coil parameter stored at commissioning, not a
  universal constant.
- `0602` — outdoor-unit housekeeping, a read poll on the ~17 s tier
  (not a burst write).

Timing facts that matter for anyone sharing the bus: the longest
silence the thermostat ever leaves in steady state is **2.81 s**;
`060D` *leads* the demand change it announces (≈65 s before a cooling
demand appears, ≈135 s before a heating one — it is a wake-up, not an
acknowledgement).

## 4. Boot and commissioning

From power-up the thermostat takes ≈62 s to reach steady state:

1. The furnace speaks first (`44→45 030A`, six times) before the
   thermostat says anything.
2. At ≈+6 s the thermostat appears as persona `0x1F` and broadcasts its
   discovery triplet, then sweeps the address space (median step
   95 ms; most targets are probed twice, zone-damper-class targets
   four times).
3. At ≈+16.7 s it hands over to its operational persona `0x20`.
4. The first addressed command leaves at ≈+62 s; the first `0305`
   demand frame at **+71.65 s**. A replacement must budget the same
   minute before it may command anything.
5. Table `031C` is exchanged only during the very first commissioning.

Address `0x0E` is a reserved discovery slot for a second outdoor-unit
family; this thermostat never probes it in normal operation.

## 5. The tables that matter

**400A — the comfort table (the control surface).** 35 bytes =
5 activities × 7 bytes, in the order *home, away, sleep, wake, manual*.
For activity *r*: heat setpoint = byte `r*7+0`, cool setpoint =
`r*7+1`, fan = `r*7+2` (0 auto, 1 low, 2 med, 3 high). The manual
activity is bytes **28 (heat), 29 (cool), 30 (fan)**. This table is
writable from the SAM slot and the thermostat honours the writes —
proven live (§6). Two behaviours define the contract:

- The manual slot is **re-seeded from the active profile** whenever the
  user enters manual mode or the profile changes. Writes only stick
  while Touch-N-Go Manual is active.
- While manual *is* active, it survives mode switches (Off→Heat→Cool)
  untouched.

**Served tables.** Anything that replaces the thermostat must also
*answer*: peers poll the thermostat's own tables. The served set and
its sizes are the DIR-C directory's (EMULATOR-SPEC §4.1) — e.g. the
thermostat's own served `0302` image is 32 B. Do not confuse these
with the equipment's answers to the thermostat's reads of the same
table ids (24 B from the outdoor unit, 12 B from the furnace for
`0302`): the two directions have different sizes. The SAM-facing
tables are the exception: see §6.

**The coil parameter.** The evaporator coil identifies itself at
commissioning; the thermostat stores one float per coil model (263
models in the built-in catalogue, identical values across all 16
official firmware versions). Our coil: **1.69**. There is no equipment
model database in the firmware — furnace and outdoor unit
self-identify over the bus (table 0104).

## 6. Controlling the system today — the SAM node

Our ESP node sits in the SAM slot (`0x92`) and does two things:
telemetry into Home Assistant, and setpoint control through 400A.

**SAM registration is a dead end — do not chase it.** This thermostat
never completes SAM registration: the gate is a runtime binding inside
the firmware, not a discoverable bus step, on both the Carrier and the
ICP personality. Consequences, all verified on the wire:

- To an unregistered SAM the thermostat serves **all-zero 3B02/3B03
  replies** — any "mirror the SAM tables" design is dead on arrival.
- SAM writes are accepted silently and ignored (no ACK, no error).
- The thermostat itself initiates almost nothing toward the SAM
  (ten 0104 probes in the entire capture corpus: six from the 0x20
  persona, four from the boot persona 0x1F).

**400A control works anyway.** Registration is not required for the
comfort table: a full-table write (`0x0C`) from `0x92` with the manual
activity bytes changed is honoured by the thermostat within one poll
cycle. The production rules the node firmware enforces:

- Write only while Touch-N-Go Manual is active; otherwise the write is
  silently re-seeded away. This is an operating contract, not a
  firmware guard: the wall's mode is not visible over the SAM
  interface, so the write-core cannot check it — the eight enforced
  guards are the complete set in firmware-history/PHASE5 §2.
- Always read-modify-write the full 35-byte image; never write a
  partial table.
- Guard the pair: cool ≥ heat + 3 °F; equal values are a no-op; the
  cached image must be ≤10 min old; a global 10 s write rate limit.
- All writes go through a single write-core, and only while the bus is
  demonstrably healthy (a real thermostat reply seen within 60 s).

**A hard-won lesson.** The stock upstream climate component exposes
six-plus live write paths into the dead SAM mirror, spawns entities the
user never asked for, and its setters accept unauthenticated commands
over a TCP console. In this installation a furnace communication
fault followed a setpoint change through that component — strong
circumstantial evidence, not proof (no capture exists for that
minute; the console is exposure, not a suspect — PHASE5 §1.4 keeps
the accounting). The firmware in this repository therefore
has **no climate component at all** — only the guarded write-core
above, driving plain number entities.

## 7. The control law (what the thermostat computes)

Recovered from the firmware image and verified by re-implementation —
the demand pipeline reproduces the original arithmetic exactly.

- **Demand** is computed per zone from the temperature error. Heating
  error = setpoint − room; cooling error = room − setpoint. The error
  passes a correction stage, is normalised by a size factor, and feeds
  a recursive (history-dependent) accumulator per channel, clamped to
  `[0, cap]`. Total demand is the sum over zones/channels.
- **Mode** is a small state machine: CD7D 1 = heat, 2 = cool, 3 = auto,
  with a configurable changeover delay (minutes) in auto. The requested
  mode and the effective mode are separate bytes; two request values
  (3, 4) park the machine.
- **Staging (cooling, fully isolated):** pure hysteresis on demand
  relative to a per-unit threshold table — stage 2 above ×1.25,
  stage 1 above ×0.25, drop-out at ×0.01, 2→1 fallback at ×1.00.
  **There are no staging timers in the thermostat.** The heating
  staging producer has the same shape (a demand staircase is visible
  in captures) but was not isolated to the same standard — see §12.
- **Compressor capacity:** in the only cooling call ever captured, the
  `0605` float went to **5.0 in the first burst and stayed there** for
  the whole call; the outdoor unit ramps the compressor itself
  (2 180 → 4 140 RPM over ≈3.5 min). Thermostat CFM moved independently
  (1232 → 1760 → 1710 → 1660). Sustained part-load behaviour has never
  been observed — §12.
- **Blower CFM** is a computed float: `CFM ≥ max(base, 325 × demand /
  12000)` with the demand term applied only in demand-driven modes.
  (Simplified form — the full floor, the gating byte and the
  per-mode clamps are EMULATOR-SPEC §5.6.)
  The per-ton family in firmware is {175…400}; observed on the wire:
  {0, 378, 379, 382, 384, 1166, 1232, 1368, 1617, 1660, 1710, 1750,
  1760}.
- **Setpoint coordinates** convert through a size/temperature table
  pair with hard clamps; an oversize derate (≥61) forces demand to 0
  in both heating and cooling chains.
- **Smart Recovery** is a fixed 90 minutes. The thermostat's clock,
  once wrong, stays wrong — nothing in the observed system corrects
  it (on this unit the measured offset is ≈13 h 19 min, the rate
  correct; whether the node's own SYSTIME broadcast should
  discipline it is an open question).

## 8. Protections live in the equipment, not the thermostat

Verified against the factory service literature. The thermostat has
**no** compressor minimum-run/minimum-off timers and no ignition
safety logic — all of it sits in the boards:

- **Furnace (G80CTL):** prepurge 15 s, hot-surface igniter warm-up
  17 s, proving 2 s, up to 4 ignition trials, then a **3-hour
  lockout**. Factory blower-off delay 120 s.
- **Outdoor unit (HVA9):** anti-short-cycle **3.5 min**, pressure and
  brownout protections (HPS trip → 6 min, LPS trip → 15 min, three
  trips → 4-hour lockout), and it drops to **standby ≈2 min after the
  last valid bus message**.
- A thermostat (stock or replacement) that simply goes silent leaves
  the equipment in a safe state: the call ends, boards protect
  themselves. What a replacement must never do is emit *wrong*
  demands — hence the guards in §6 and the failover discipline in §9.
- The thermostat itself offers no proven freeze protection for the
  house; a replacement must implement its own (≈40 °F floor).

## 9. Failover and the road to replacement

The end goal is a node that can take over completely. The design that
the evidence supports:

1. **Mirror first.** The node listens receive-only, parses every
   frame, tracks the full equipment state, and runs the §7 control
   law in parallel on its own temperature input (a BLE room sensor —
   the bus has no room-temperature channel). It logs *its* computed
   burst next to the thermostat's actual burst. Weeks of zero
   unexplained divergences is the acceptance criterion.
2. **Takeover on silence.** The thermostat's death is unmistakable:
   it is the only initiator, and its longest steady-state silence is
   2.81 s. The takeover delay is bounded by measurement on both
   sides — equipment tolerates **more than 36 s** of thermostat
   silence without a fault (proven by a reseat capture), and the
   outdoor unit drops the call at ≈2 min. The takeover threshold
   therefore has to sit above the proven 36 s and below ≈2 min, and
   the design additionally listens silently for ≥2 min after its own
   boot before assuming any active role (EMULATOR-SPEC §10). The
   exact takeover value stays a calibration item until the
   thermostat's own recovery time is measured.
3. **The stock control always wins.** The instant a genuine `0x20`
   (or boot persona `0x1F`) frame is heard, the node stops
   transmitting and falls back to mirror mode. No bus fight, ever.
   Takeover is additionally gated by an explicit enable switch in
   Home Assistant, with alerts in both directions.
4. **Then replacement.** With the mirror calibrated (§12), the same
   firmware runs the bus full-time: boot script of §4, served tables
   of §5, bursts of §3, law of §7.

## 10. Hardware, wiring and power

- Node: ESP32 (DevKit, CP2102) on a perfboard carrier; MAX13487E
  auto-direction RS-485 module (A → DX+, B → DX−, module GND = the
  white C wire — the module must share the bus common or the bus
  faults). UART ↔ module: TXD → GPIO16, RXD → GPIO17, 38400 8N1.
- Mirror/replacement target: ESP32-S3 (N16R8).
- Room sensors: LYWSD03MMC with ATC firmware (ATC1441 advertising,
  values in °C), read passively over BLE.
- **Power — the expensive lesson.** There is no outlet at the wall;
  the node must live off the C/D 24 VAC pair. A non-isolated buck
  converter ties its output negative to its input, which shorts C to
  D through the bridge and blows the furnace fuse. Power design that
  is safe here: C/D → 1 A slow-blow fuse → bridge → 470 µF/63 V →
  **isolated** DC/DC (datasheet-rated isolation, e.g. 1500 VDC class)
  → 5 V. Bench-verify before the bus: input↔output must be open
  circuit, output a clean 5.0 V, and the first bus connection is
  power-only for 10–15 min (no fault, outdoor temperature present)
  before any data wires land.

## 11. The firmware in this repository

**Status (2026-11-26):** this build is written but has **not been
compiled or flashed yet**; the node is off the bus (see
`docs/STATUS-AND-PLAN.md`). The last build to run live was
phase3-control (2026-11-03 → 2026-11-24). What follows describes the
build's design and its intended behaviour.

`firmware/thermostat.yaml` (+ `firmware/components/`) is the unified
node build; `firmware/home-assistant.yaml` is its HA package.

- Telemetry: full bus state into Home Assistant (demands, stages,
  blower RPM, compressor state, outdoor temperature, bus health).
- Control: ten setpoint numbers (heat/cool × 5 activities) through the
  single guarded write-core of §6 — no climate component.
- Sensor steering: optional BLE room sensor feedback — the stored
  manual bytes are nudged toward the room target (error = target −
  sensor, step clamped to ±6 °F per 30 s tick, whole-degree steps of
  round(error) — the loop settles within ±0.5 °F),
  inert when the sensor is stale (>15 min) — no writes without fresh
  data. (The phase-4 gradient form, which steered by the wall
  reading, is superseded: this thermostat serves no wall temperature
  to a SAM. See firmware-history/PHASE5 §3.)
- Fan circulation with call credit: real heating/cooling fan minutes
  count toward the hourly circulation target; the node only tops up
  the remainder, and only under its ownership rules.
- Autonomy: SNTP clock next to the HA clock; a **dead-man return** —
  if the Home Assistant heartbeat is older than the configured limit
  (default 6 h) *and* the manual pair sits outside the safe band
  (heat 60–72 °F, cool 74–85 °F), the node writes the safe pair
  68/78 °F once and waits. Never fires before the first heartbeat.
- HA side: Day/Evening/Night profiles (10:00 / 17:30 / 00:00), hold
  modes (Schedule / Temporary / Permanent / Vacation with a 55/85 °F
  vacation pair), a 5-minute heartbeat, node-offline alert, and a
  filter reminder driven by real blower hours.

File-level facts (core blocks, helper entity ids, scripts and
automations, sensor platforms): `docs/ENTITY-INDEX.md`. The build
history starts at `docs/firmware-history/PHASE1-2.md`.

## 12. What is still unknown (data, not code)

- **Class word (B-2).** The equipment class word that selects several
  control-law tables cannot be read off the unit. Two candidates
  ({0x8141, 0x91C1}) are formula-identical; one behavioural observation
  in mirror mode pins the related size factor. Calibration item.
- **Configuration values (B-12).** The demand gain and a handful of
  per-zone constants live only in the thermostat's RAM; there is no
  read channel. The formula is exact — the constants get calibrated
  against mirror divergences.
- **Part-load cooling (B-5).** Every captured cooling call ran at
  capacity 5.0 end-to-end. Whether the thermostat ever commands
  sustained intermediate values needs a long summer capture.
- **Heating staging producer (B-11).** Isolated by shape and by wire
  observation, not to the cooling machine's standard. Low risk.
- **Exact comm-fault timeout.** Bounded (>36 s, <2 min for call
  retention) but never measured to the second; one attended test
  with the thermostat unplugged under capture closes it.

---

*Method note: the protocol facts come from 83,752 captured bus frames
in the main corpus (101,352 counting the cold-start segments)
and a second, independent 1 532-frame capture from a Bryant Evolution
system (gofinity project), which the frame layer, boot sequence and
commissioning behaviour match. The firmware facts come from the
official v4.79 image — byte-identical to the unit under test — decoded
in Ghidra (Renesas SH-2A). The same analysis was run over all 16
official Series B images (2.40–4.79): the coil catalogue values never
changed, and the staging constants are six years stable.*
