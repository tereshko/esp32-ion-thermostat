# Project status, decisions and plan

Status as of **2026-11-26 (end of day)**. This page is the newcomer's
orientation: where the project has been, why it took the turns it took,
where it stands right now, and what happens next. Engineering detail
lives in the linked documents; this page carries no new claims of its
own.

System under work: ICP Ion SYST0101CW wall control (firmware v4.79)
on the proprietary RS-485 bus of a Heil G80CTL1352422A furnace
(0x44) and a Heil HVA960GKA inverter outdoor unit (0x53), with an
ESP32 node and Home Assistant alongside.

---

## 1. Timeline

### Phase 1 — passive mirror (2026-10-27 → 2026-10-29, closed)

- 2026-10-27: phase-1 kit assembled (stock InfinitESP on a classic
  ESP32 DevKit + MAX13487E RS-485 module on an HW-451 carrier) and
  the first BLE room sensor (LYWSD03MMC) reflashed to ATC firmware.
- 2026-10-28: first bus connection produced an `INDOOR UNIT
  COMMUNICATION FAULT` at the wall. Root cause found the same day:
  all ESP-side wires sat in the HW-451's black (G) pin row instead
  of the blue (S) signal row, so the module held the bus down.
  Lesson recorded: bench-check A–B ≈ 0 V at rest before any bus
  landing.
- 2026-10-29: wires reseated correctly, bus heard from the first
  attempt, live telemetry in Home Assistant. A full reference
  capture archive was recorded across all modes (~17,600 frames:
  cold start, idle, fan-only, cool, heat staircase) — the corpus
  every later stage works from (`docs/THERMOSTAT-PROTOCOL-MAP.md`,
  `docs/evidence/`).

### Phase 2 — SAM registration attempt (2026-10-29, closed as impossible)

- The node ran as a SAM at 0x92; the Ion answered its identity probe
  and exchanged tables with it, but the acceptance test failed: SAM
  setpoint writes reached the bus and were ignored, `3B02`/`3B03`
  reads were served all zeros, and the SAM never appeared in the
  Ion's equipment summary.
- Three registration triggers were tried and all failed: whole-system
  breaker restart, FULL INSTALLATION from the service menu, and a
  thermostat-only reseat.
- Same-day research (`SAM-REGISTRATION-RESEARCH`) closed the path:
  the ICP installation manual's commissioning sequence has no
  "Searching for SAM Module" step at all (the Carrier manual on the
  same platform has one), and no SAM handshake traffic ever appears
  in any capture. A later firmware-image check refined the verdict:
  the SAM code **is** present in the Ion's image (strings, step
  table) but is never launched — the gate is runtime device-resident
  data, not the image. A factory reset was considered and rejected:
  it would rerun the same search while wiping all control settings.

### Direct-write discovery — control via table 400A (2026-10-29 → 2026-10-30)

- The InfinitESP author (upstream issue #61) pointed at the path he
  had used years earlier: direct writes into a 4xxx thermostat
  register. Analysis (`DIRECT-WRITE-RESEARCH`) identified the
  register as **400A**, the zone-1 comfort row: 35 bytes, five
  activities × 7 bytes; the manual activity's heat byte is 28, cool
  byte is 29, fan byte is 30.
- 2026-10-30: live test at the wall, **PASS** — the Ion stores
  foreign 400A writes from the unregistered SAM slot and consults
  the manual entry live (criteria 6a/6b pass, 6c partial). Control
  does not require SAM registration; it requires the wall to be
  sitting in its Touch-N-Go Manual entry (see the decisions log).

### Phase 3 — production control (2026-11-03 → 2026-11-24, in service)

- 2026-11-03: `phase3-control` flashed and validated the same day.
  Home Assistant owned the manual heat/cool pair through a guarded
  write-core (full-row read-modify-write, func 0x0C, up to 3
  transmissions 4 s apart). Final lived state: wall on Touch-N-Go
  Manual, mode Heat, pair 70/73 °F.
- The stock upstream climate component rode along in this build —
  unaudited. That mattered later (2026-11-24).

### Phase 4 — sensor steering + fan circulation (built 2026-11-03, never separately validated)

- Built the same day as phase 3: steering by the nursery BLE sensor
  (wall setpoint = room target + wall−room offset, clamp ±6 °F,
  anticipatory shutoff episodes) and hourly fan circulation via
  byte 30. Delivered as a kit; it received no separate live
  validation cycle, and its features were later rewritten onto
  audited inputs inside phase 5. Byte 30 (fan) has still never been
  live-tested as a write.

### Panel track (2026-11-17 → 2026-11-20, hardware complete)

- 2026-11-17: wall-panel design settled (ecobee-style UI, 480×320,
  LVGL on ESPHome): PIN lock — yes; temperature reference selectable
  (any of three sensors or their average); time-of-day profiles
  instead of Smart Home/Away; a furnace watchdog (call without
  temperature rise → alert, then full Off, manual reset only);
  eco+ — no; music — no; VOC sensor — not buying; the panel must
  work autonomously without Home Assistant.
- The panel parts set was ordered on the night of **2026-11-12**
  (3.5″ ST7796U+FT6336U display, TSL2591, SHT40, LD2410C, SPH0645
  microphone, MAX98357A, speakers, sockets/terminals/wire, second
  LYWSD03MMC); only the carrier bits and the S3 boards followed on
  2026-11-17/18.
- Platform decision: **ESP32-S3 N16R8** (the P4 option was closed);
  two GlobalGo ESP32-S3-DevKitC-1 N16R8 boards were ordered
  2026-11-18 and **delivered by 2026-11-26** (see §3).
- 2026-11-20: bench layout for the MB-102 breadboard and a bench-test
  firmware were delivered; bench assembly status is not confirmed
  in the project records.

### Incident and Phase 5 — the hardened build (2026-11-24)

- ~13:22 ET: setting a value from the HA climate card "House"
  produced `INDOOR UNIT COMMUNICATION FAULT` at the wall and the
  outdoor temperature went to "---". Full audit the same day found
  two independent causes:
  1. The stock climate component in phase 3 had **6+ live write
     paths** into the dead SAM mirror (frames 3B02/3B03/3B04),
     auto-spawned entities and unauthenticated console setters —
     and its card had never displayed live data at all (the 70 °F
     shown was a boot seed; the Ion serves an unregistered SAM
     zeros).
  2. During the power hookup, the white wire (C) had been taken off
     the RS-485 module and given only to the power converter,
     leaving the module without the bus common. Separately, the
     converter itself — an XWST XW-AC24-DC5-DC — proved to be a
     **non-isolated** buck: its output negative is tied to its
     input, which shorted C to D through the bridge and blew the
     furnace board fuse. The fuse was replaced and the furnace
     restarted; the node was disconnected from the furnace
     entirely and went back to USB power.
- **Phase 5** was built the same day as the answer: no climate
  component at all; ten template numbers (heat/cool × 5
  activities); one write-core for every write, behind a bus-health
  gate (a real thermostat reply within 60 s) and a global 10 s
  rate limit; steering rewritten in feedback form on the BLE
  sensor. Status: built, **not compiled, not flashed** — by the
  standing rule, power/wiring and a clean bus come first.

### Firmware reverse engineering (2026-10-30 → 2026-11-26)

- The Ion's update image (v4.79) was decoded in Ghidra (Renesas
  SH-2A / SH7269, big-endian, load base 0x18040000). Stage A
  (2026-10-30) established that the official Carrier image is
  **byte-identical** to the ICP image — one universal image, so
  "flash the Carrier firmware to get SAM" is moot.
- Stages B–Y, AA and the Series C analysis followed through
  November, closing among other things: the demand formula
  (verified against an emulator, 10/10), the staging hysteresis
  (stage 2 above ×1.25 of threshold, stage 1 at ×0.25, drop at
  ×0.01, no timers), the CFM law and its floor, the mode word
  (CD7D: 1 = HEAT, 2 = COOL, 3 = AUTO), the frame builder and CRC
  routine, the boot/commissioning script, the SAM surface, and the
  fact that **all compressor/furnace protections and timers live
  in the equipment boards, not in the thermostat** (furnace:
  15 s prepurge, 17 s igniter, up to 4 trials → 3 h lockout;
  outdoor unit: 3.5 min anti-short-cycle, ~2 min standby after the
  last valid message).
- Version diffing across all 16 official Series B images
  (2.40…4.79) showed the coil parameter for this installation's
  evaporator (EN(A,D)4X61 → 1.69) — and every other catalog
  parameter — never changed in any release.
- 2026-11-26: an independent 20-agent verification fleet
  re-derived the load-bearing claims from the primary artifacts.
  The corpus held; a register of corrections was folded back into
  the map and the emulator spec (all listed in
  `docs/THERMOSTAT-PROTOCOL-MAP.md`, verification corrections
  V-1…V-9, and `docs/EMULATOR-SPEC.md`).
- The thermostat-algorithms research (what real thermostats do that
  this node doesn't) was compiled the same day; everything in it
  that works without room sensors became phase 6.

### Phase 6 — sensorless autonomy (built 2026-11-26, not flashed)

- On top of phase 5, unchanged write-core: an SNTP clock next to
  the HA clock; an HA heartbeat (epoch written every 5 min); a
  **dead-man return** — if the heartbeat is older than the limit
  (default 6 h) and the manual pair sits outside the safe band
  (heat 60–72, cool 74–85), write the baseline pair 68/78 once per
  outage; fan circulation with real-call minutes credited against
  the hourly budget.
- HA package: Day/Evening/Night profiles (starts 10:00 / 17:30 /
  00:00), hold modes (Schedule / Temporary / Permanent / Vacation,
  vacation pair 55/85), node-offline alert (> 1 h), filter reminder
  by real blower hours (default 1000 h).
- Deliberately excluded (they need room sensors): optimum start,
  occupancy setback, multi-sensor averaging, humidity overcool,
  freeze monitoring. Status: built, **not compiled, not flashed**.

### Publication (2026-11-26)

- The knowledge base and the firmware were published as a public
  GitHub repository (MIT): the distilled guide, the full protocol
  map and emulator spec, the firmware-analysis stages and both
  audits, the 20-report verification corpus, capture-derived
  evidence exhibits (raw captures are not published — they are a
  timeline of the house's life), and the unified node firmware.
  Published copies are scrubbed: home-network addresses, sensor
  MACs and equipment serial identifiers are placeholders/masked.

---

## 2. Decisions log

**D1. The Ion stays the master; the ESP is a smart layer, never a
direct actuator.** The ESP never touches gas or fan directly — it
only moves setpoints. All equipment protections live in the
furnace/ODU boards and keep working whatever the node does.
*(Architecture, from the start of the project.)*

**D2. The SAM path is closed.** Three registration triggers failed;
the ICP commissioning sequence contains no SAM search step; the
Ion serves an unregistered SAM all-zero 3B02/3B03 and silently
ignores its writes. The SAM code exists in the firmware image but
is gated by runtime data, so no bus-side action can enable it.
Factory reset rejected (same search, all settings wiped).
*(2026-10-29; `SAM-REGISTRATION-RESEARCH`.)*

**D3. Control goes through table 400A, not through the SAM
mirror.** A full-row write (func 0x0C) from the SAM slot is
honoured by the unregistered thermostat — proven live 2026-10-30.
The manual activity's bytes are 28 (heat) / 29 (cool) / 30 (fan).
*(2026-10-30; `400A-TEST-RESULT`.)*

**D4. Operating contract: the wall lives on Touch-N-Go Manual.**
The manual slot is re-seeded from the active profile whenever the
user enters manual mode or the profile changes, so HA's writes
only stick while Manual is active; while Manual *is* active it
survives mode switches (Off→Heat→Cool). HA owns the manual pair;
schedule profiles are never written by the node. A consequence:
there is still no remote Off — stopping heat remotely means
setting Manual Heat to 50 (cool symmetrically to 99) until the
mode byte is found (test T-4 below).
*(Decision 2026-10-30; validated 2026-11-03.)*

**D5. One write-core, no stock climate component.** After the
2026-11-24 audit showed 6+ unaudited write paths in the stock
component, phase 5 removed the climate component entirely. Every
write in the node funnels through a single guarded core:
bus-health gate, global rate limit, deadband (cool ≥ heat + 3 °F —
the Honeywell default; +5 would forbid the proven 70/73 pair),
range clamps, cache freshness.
*(2026-11-24; `PHASE5.md` §1–2.)*

**D6. Bus power only through verified isolation.** The node has no
outlet at the wall and must live off the C/D 24 VAC pair — but
only through a converter whose isolation is stated in its
datasheet **and** proven on the bench (input↔output open circuit;
clean 5.0 V out; first bus landing power-only for 10–15 min with
no fault before any data wires). The XWST non-isolated buck is
banned from the bus in any variant. The whole power chain is
connectorised — no soldering in the power path.
*(2026-11-24, after the fuse incident.)*

**D7. Panel/emulator platform: ESP32-S3 N16R8.** PSRAM for the
LVGL framebuffer and camera snapshots; the classic ESP32 stays as
the current bus node. Two boards are on hand with assigned roles
(§3). Panel functional decisions are in the timeline (2026-11-17).
*(2026-11-17/18.)*

**D8. The end goal is a full Ion replacement with failover, not a
permanent mirror.** The owner approved the replacement plan on
2026-11-26 (§4). The failover rules are normative
(`EMULATOR-SPEC` §10): **Ion always wins** — on hearing any genuine
0x20 (or boot-persona 0x1F) frame the emulator stops transmitting
immediately; takeover is additionally gated by an explicit enable
switch in Home Assistant, with alerts in both directions; the
takeover threshold must sit **between Ion's recovery time and the
furnace comm-fault timeout** — the two numbers are measured by
tests T-1 (comm-fault timeout) and T-2 (Ion recovery time),
with the window already bounded below (> ~36 s of tolerated
silence, from the reseat capture) and above (~2 min to ODU
standby).
*(2026-11-26.)*

**D9. No firmware ships ahead of power and a clean bus.** Every
build since phase 5 carries the same gate: power decision and
wiring first, 15 minutes of clean bus, then compile, then the
documented first-run checks. Rollback is always the previous
build.
*(Standing rule since 2026-11-24.)*

---

## 3. Current state — end of 2026-11-26

- **The house runs on the Ion alone.** The ESP node is fully
  disconnected from the furnace and powered by USB. Nothing about
  the node's absence affects heating: the Ion is autonomous (D1).
- **Phase 3** was the last firmware in service (until 2026-11-24).
  **Phase 5** and **phase 6** are built and documented but **not
  compiled and not flashed**; ESPHome compilation happens on the
  owner's machine and is the first gate for both. (Operating
  context: builds run **only** on the owner's Windows PC — the
  assistant's environment has no ESPHome installed and no network
  route to the home LAN, so every build's compile, flash and
  on-bus verification happen owner-side, guided step by step.)
- **Bus power is undecided.** Two verified-isolation options are
  on the table (decision pending since 2026-11-24):
  - a component chain — C/D → 1 A slow-blow fuse → bridge →
    470 µF/63 V → isolated **Mornsun URB4805** DC/DC (1500 VDC
    isolation per datasheet) → 5 V (~$12 in parts, assembled on a
    prototyping board with screw terminals);
  - a single ready unit — **PowerStream PST-ACDC2405-15**
    ($49), electrically suitable but 170×78 mm: it does not fit
    the panel enclosure and would live at the furnace.
  The owner's stated intent on 2026-11-26: decide and land power
  on 2026-11-27. The pre-flight procedure of D6 is mandatory
  either way.
- **Both ESP32-S3 boards have arrived.** Assigned roles:
  board №1 — mirror / shadow emulator: **RX-only** on the bus (no
  transmitter connected), runs the control law in parallel on the
  nursery BLE sensor's temperature (the bus provably carries no
  room-temperature channel) and logs divergences against the real
  Ion's bursts. Board №2 — the gradual assembly: sensors, then
  the panel / full thermostat.
  The shadow firmware itself is not yet written; its specification
  is `EMULATOR-SPEC` plus the divergence-logging requirement.
- **Knowledge base is complete and published** (§1, Publication):
  protocol map, emulator spec, firmware analysis, verification
  corpus, evidence exhibits. Offline, only *data* remains open —
  §5 below — not code.
- **Open small items:** the mode byte is still unidentified (no
  remote On/Off; kit for the mode-diff session is built and
  waiting, test T-4); byte 30 (fan) writes are untested live;
  four orphaned TEST entities from the phase-3 era remain to be
  deleted in Home Assistant.

---

## 4. The 10-step plan to replace the Ion

Approved 2026-11-26. Steps 1–4 are measurements and captures;
5–7 build the emulator in shadow; 8–10 take it live. The failover
design constraints of D8 apply to every step from 6 on. The owner's
sequencing across tracks: **power and a real bus on/off (the mode
byte) first, then voice, then the panel**.

| # | Step | Criterion / what it produces |
|---|---|---|
| 1 | **Measure the furnace comm-fault timeout**: Ion off the bus under capture, at idle and mid-call; also watch the ODU at its ~2 min standby mark (test T-1). | The exact timeout. Lower bound already known: > ~36 s with no equipment reaction. This number and step 2's bound the takeover threshold. |
| 2 | **Measure Ion's recovery time** after a power cycle (test T-2 covers the boot variants). | Boot-to-first-frame and boot-to-steady numbers for the threshold's other bound. |
| 3 | **Seasonal captures** of Ion's commands and the equipment's reactions: deep-winter gas heat / defrost now; summer cooling, part-load and changeover transients in season (test T-5). | Closes B-5; validates the CFM anchors at the extremes. |
| 4 | **Mode-experiment session 1** (test T-4): register diffs across Heat / Cool / Auto / Off at the wall; SYSCTRL byte 49 and 3B02[22] in all four states; a fan-only setting separates the mode word's R = 3 vs R = 4. | The mode byte identified → remote On/Off becomes possible; kit is built and waiting. |
| 5 | **Emulator specification** from the captures and the firmware analysis. | **Done** — `EMULATOR-SPEC` (frame layer, boot script, served tables, control law, failover constraints), corrected by the 2026-11-26 verification fleet. |
| 6 | **Shadow emulator** on S3 board №1: RX-only, computes the law in parallel, logs every divergence from the real Ion's bursts. | Weeks of running with **zero unexplained divergences**; simultaneously the calibration route for B-12 and the behavioural pinning of B-2. |
| 7 | **Its own room-temperature sensor** in the living zone as the control loop's input (board №2 track; the nursery BLE sensor serves the shadow phase). | A temperature channel the emulator owns — the bus has none. |
| 8 | **Control loop + failover watchdog**: continuous presence check on 0x20 frames (Ion is the bus's only initiator); takeover after the measured silence threshold; instant yield on any genuine 0x20/0x1F frame; HA enable switch and two-way alerts. | The D8 rules implemented and bench-proven against recorded captures before any live bus test. |
| 9 | **First live driving**: Ion physically off the bus, short attended sessions, emulator runs the house. | Sessions complete with the equipment behaving per spec; rollback is mechanical — put the Ion back. |
| 10 | **Combat failover for the winter season**: emulator resident as the hot spare (and eventual replacement), Ion retired or kept as the fallback. | A full heating season under failover coverage. |

---

## 5. Open questions — the remaining gaps are data, not code

From `EMULATOR-SPEC` §11 (verification state 2026-11-26). The
control law's code is fully recovered; what is missing is four
items of installation data, each with a named closing route:

- **B-2 — the equipment class word (CC52).** Primary candidates
  {0x8141, 0x91C1} are formula-identical, so coding proceeds on
  them; {0x8142, 0x91C2, 0xC195} are not excluded. *Closed by:*
  behavioural pinning during the shadow phase (step 6), or a
  runtime snapshot — for which no read channel is known.
- **B-5 — cool part-load behaviour.** The single captured cooling
  call ran at capacity 5.0 from its first burst to its end;
  whether `0605` ever takes values 1.0–4.0 in real weather, and
  the producer law if it does, is unknown. The v1 law ships with
  the proven "5.0 for the whole call" behaviour. *Closed by:*
  a long mild-weather cooling capture (step 3 / T-5).
- **B-11 — the heat staging producer** was not isolated in the
  firmware image (five candidate functions). Low rank: the
  hysteresis form is proven on the cooling machine, and the
  captured heat staircase suffices to implement against.
  *Closed by:* static isolation of one candidate, or a heat-call
  capture with demand logged against stage flips.
- **B-12 — the control law's configuration values** (gain and
  table parameters: G, the CA04/CA24/C880/CD1C set, the
  personality byte, store[8], the CFM table contents, selectors).
  The values live at known addresses but there is no channel to
  read the unit's RAM. *Closed by:* shadow-emulator calibration
  (step 6) — feed the emulator the same inputs as the Ion and fit
  the parameters until its outputs track the real bursts — or
  behavioural pinning per parameter.

Blocking live tests, for completeness: T-1 (comm-fault timeout,
= step 1), T-2 (boot variants, = step 2), T-3 (equipment exception
behaviour — the only test that transmits probes; requires an
explicit go-ahead), T-4 (mode experiment, = step 4), T-5 (seasonal
captures, = step 3).

---

*Sources: `docs/THERMOSTAT-PROTOCOL-MAP.md`,
`docs/EMULATOR-SPEC.md`, `SAM-REGISTRATION-RESEARCH`,
`DIRECT-WRITE-RESEARCH`, `400A-TEST-RESULT`, `PHASE3-CONTROL.md`,
`PHASE4-SENSOR.md`, `PHASE5.md`, `PHASE6.md`, the firmware-analysis
stages and audits, and the project log through 2026-11-26.*
