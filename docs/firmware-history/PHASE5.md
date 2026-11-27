# PHASE 5 — HARDENED BUILD: full audit of phase-3 production + the fix

Built 2026-11-24 after the incident at ~13:22 ET: the author changed
setpoint/mode/preset on the HA climate card "House" of the running
phase3-control build; the Ion wall unit immediately showed
**INDOOR UNIT COMMUNICATION FAULT** and outdoor temperature "---"
(the whole bus down from the Ion's point of view). A furnace
power-cycle cleared the indoor fault. Precedent 2026-10-28: our
RS-485 module disturbing/driving the bus produced the identical
fault (the Ion lost the indoor unit).

**Status: BUILT, NOT COMPILED, NOT FLASHED.** ESPHome is not
installed in the preparation environment (same as every prior
kit) — the first gate is your local `esphome run phase5.yaml`
compile, §7. Nothing in this kit touches the production files:
`phase3-control.yaml` and `control-components/` are untouched;
rollback is reflashing phase3-control.yaml.

---

# 1. AUDIT — every bus-write/transmit path in the phase3-control build

## 1.0 How writes actually leave this node (mechanics)

All hub writes go through `send_write_frame_()`, which only
**queues**. `loop()` drains **one** due queued frame per iteration,
behind a bus-idle gate (>50 ms since the last heard byte, and a
200 ms post-own-transmit busy window). Each queued write is
transmitted up to **WRITE_ATTEMPTS = 3** times, 4 s apart
(RETRANSMIT_DELAY_MS), until a bare `[00]` REPLY from the
destination cancels the remaining attempts. Per
THERMOSTAT-PROTOCOL-MAP.md, this Ion never ACKs SAM writes — so
plan on **3 transmissions of every queued write**. A 3B03 payload
is 153 bytes ≈ **42 ms of wire time** at 38400 8N1; a 400A payload
is 38 bytes ≈ 10 ms. The thermostat's own traffic runs ~21
frames/s (captures); the hub's own comments record that replies
arrive 11–110 ms after a poll and that SAM-mode operation shows
~0.75 % CRC-failed frames vs ~0.01 % listen-only — the idle gate
reduces collisions, it cannot eliminate them.

Verdicts use: **safe** = audited + proven or read-only by
construction; **unproven** = never audited/tested, bounded blast
radius; **dangerous** = unaudited AND (built on garbage data, or
bursty, or able to fire without a deliberate per-action intent).

## 1.1 The write paths

| # | Path (HA surface → hub method) | Frames per action | Verdict |
|---|---|---|---|
| W1 | Climate card setpoint → `set_zone_setpoint()` | 1 queued 3B03 (153 B) ×3 TX | **dangerous** |
| W2 | Climate card mode → `set_system_mode()` | 2 queued (3B03 notify + 3B02) ×3 TX | **dangerous** |
| W3 | Climate card fan → `set_zone_fan()` | 1 queued 3B03 ×3 TX | **dangerous** |
| W4 | Climate presets Home/Away/Sleep/Wake → `apply_activity()` | 1 queued 3B03 (FAN\|HEAT\|COOL\|hold flags, permanent hold) ×3 TX | **dangerous** |
| W5 | Climate preset "Per Schedule" → `set_zone_hold(0)` | 1 queued 3B03 (cancel hold) ×3 TX | **dangerous** |
| W6 | Climate any-preset vacation clear → `set_vacation_hours(0)` | 1 queued 3B04 ×3 TX | unproven |
| W7 | Auto-spawned select **System Mode** → `set_system_mode()` | same as W2 | **dangerous** |
| W8 | Auto-spawned number **Vacation Hours** → `set_vacation_hours()` | 1 queued 3B04 ×3 TX | unproven |
| W9 | Auto-spawned button **Sync Thermostat Clock** → `sync_clock_from_source()` → `set_displayed_clock()` | 1 queued 3B02 (clock flags) ×3 TX | unproven |
| W10 | Auto-spawned per-zone: select **Fan Mode** → `set_zone_fan()`; number **Hold Minutes** / datetime **Hold Until** → `queue_hold_set()` → `set_zone_hold()` | 1 queued 3B03 each ×3 TX | **dangerous** |
| W11 | sam_ascii console (TCP 23, no auth) write verbs → the same setters | 1–2 queued per verb ×3 TX | **dangerous** (surface) |
| W12 | Template numbers Manual Heat/Cool → `write_manual_heat/cool()` → `write_manual_entry_()` | 1 queued 400A RMW (38 B) ×3 TX | **safe** |
| W13 | `command_setpoint_half()` + deferred row write | 400A row write, °C-bus only | unproven, unreachable in this build |

Details that matter:

- **W1–W5 are one `control()` call chain.** A single HA
  ClimateCall can carry mode + setpoint + preset together; the
  stock `InfinitESPClimate::control()` executes all of them
  sequentially. Worst case one card interaction queues **~5
  writes ≈ 15 long-frame transmissions over ~8–12 s**, on top of
  the node's own polling. The phase-3 design intent ("control
  ONLY via the two template numbers") was never enforced — the
  climate entity was kept "for display/telemetry parity" with
  its entire stock control surface live.
- **W1's frame is worse than unaudited — it is built on garbage.**
  `set_zone_setpoint()` copies the SAM-mirror 3B03, sets the two
  setpoint bytes from the climate's `heat_sp_`/`cool_sp_` members,
  and flags **both** CHANGE_HEAT|CHANGE_COOL whenever both members
  are > 0 (they always are: defaults 68/76, and the read-side
  that would refresh them is dead on this Ion, §1.9). So a
  one-bound drag emits the other bound at a stale/default value,
  in a 150-byte body that is otherwise **zeros** (the zeroed
  mirror, §1.9). W2's 3B02 body is likewise zeros except the
  stagmode byte. W4's `apply_activity()` at least reads its
  setpoints from the real 400A row — but still writes them via
  the 3B03 dialect with a permanent hold.
- **W7–W10 were never in any yaml.** The hub's `to_code` calls
  `auto_entities.spawn_system_entities()` and the climate's
  `to_code` calls `spawn_zone_entities()`: the "House" device in
  HA silently carried a writable System Mode select, a Vacation
  Hours number, a clock-sync button, a per-zone Fan Mode select,
  Hold Minutes and Hold Until — all wired to the same setters.
  Nobody audited them because nobody declared them.
- **W9 was live**: phase3-control.yaml declares a `time:`
  source, which is exactly what the clock sync needs.
- **W11**: the control tree's sam_ascii has **no** REG!/SCAN
  verbs (those exist only in scan-components, gated by
  `raw_writes`), but it has the full setter vocabulary —
  `MODE!`, `ZONE!`, `Z#HTSP!`, `Z#CLSP!`, `Z#FAN!`, `Z#HOLD!`,
  `VACDAYS!`, `VACHOURS!`, `VACMINT!`, `VACMAXT!`, `VACMINH!`,
  `VACMAXH!`, `VACFAN!`, `TIME!`, `DAY!`, `CFG*!`, `DEALER*!` —
  callable by anything that can open TCP 23 on the LAN. No
  evidence it was used in the incident; it is exposure, not a
  suspect.
- **W12 is the only audited write path**: full-row func-0x0C RMW
  of 400A from the poll cache, guards (SAM on; 40–99 °F; row
  cached; cache ≤ 10 min; equality no-op; deadband cool ≥
  heat + 3 vs the stored pair; write-through cache). Proven at
  the wall 2026-10-30, in production since 2026-11-03; the
  2026-11-03 validation session's deliberate sets produced 17
  write frames in total and no bus upset.
- **W13**: `command_setpoint_half()` returns false immediately
  when the bus is not in °C mode (this install is °F), so in
  phase 3 it never fired; its only caller is the climate.

The damper **cover** (auto-spawned per-zone) does **not** write
the bus — its control fires a local ESPHome trigger only, and no
automations are wired to it in the yaml. Inert.

## 1.2 Non-write transmissions (for completeness)

| # | Path | Verdict |
|---|---|---|
| T1 | Fast poll: READ 3B02/3B03 to 0x20, alternating, every 3 s, idle-gated, suppressed during retransmit iterations and discovery holdoff | safe (reads) |
| T2 | Slow poll: every 31 s, rotation over 400A + {0104, 3B04, 4012, 4202, 3B05, 3D02, 4608, 4609, 460A} | safe (reads) |
| T3 | ODU slow poll: every 31 s {0304, 3E01, 3E02, 3E08} | safe (reads) |
| T4 | Discovery probes from 0x93 every 3.5 s (READ tabledef 0xNN01 of observed devices) | safe (reads) |
| T5 | SAM emulation replies/exceptions to thermostat requests addressed to 0x92; store + ACK-echo for writes addressed to 0x92 | safe by design (reactive; this is what a real SAM does; on this Ion the thermostat essentially only answers our polls) |
| T6 | Metric-units probe poll — only when SAM is disabled | n/a (not this build) |
| T7 | bus_jsonl TCP 2373 stream | safe (output-only; client input is consumed and discarded in code) |

Polling is not free — T1–T4 are the node's constant bus presence
and the reason its SAM-mode CRC-fail rate is nonzero — but reads
were the designed, tested posture of phases 1–3, and the
2026-10-28 precedent fault came from a module *driving* the bus
wrongly, not from polling.

## 1.3 Why HA showed 70 °F, "Heat", "Idle", "Per Schedule" — the fossil decode

The climate's read path is: thermostat serves 3B02/3B03 to the
SAM → hub mirrors them under 0x92 → climate publishes. On **this**
Ion that path is dead, proven from our own captures:

- Every 3B02/3B03 read reply from 0x20 to 0x92 is **all zeros**:
  58/58 in the 2026-11-03 production validation capture, 16/16 in
  the 2026-10-29 control test. (THERMOSTAT-PROTOCOL-MAP.md: the
  Ion serves an *unregistered* SAM zeros.)
- In ~75 000 captured frames across all project traces
  (including a full cold start) there is **not one** 3B02/3B03
  broadcast write from the thermostat — the passive-mirror path
  in `handle_passive_frame_()` never fires here.
- The hub seeds the SAM registers at boot
  (`initialize_defaults_()`): 3B02 zone temps **70** (all zones),
  humidity 50, outdoor 70, stagmode 0x05 (stage 0, mode OFF);
  3B03 heat 68 / cool 76, fan auto, hold 0. `setup()` notifies
  entities from the seeds; the first poll replies then mirror
  **zeros** over them, and the climate's update branches
  early-return on the zeroed active-zones byte — so the
  published state freezes at the seed-derived values forever.

The incident screenshot decodes exactly:

- **Current temperature 70 °F** = the 3B02 **seed**. Not a stale
  measurement — a constant the firmware invented at build time.
  (Humidity on the card would read 50 %, also the seed.)
- **Idle** = seed stage nibble 0.
- **Mode Heat** = **not from the bus** (the seed is OFF). It is
  the local echo of the author's own card action: `control()` assigns
  `this->mode` from the call before invoking the hub.
- **Target 73 °F** = likewise the local echo of his setpoint
  drag (`control()` assigns `target_temperature_low/high` from
  the call). Not a value read back from the wall (the wall
  showed 73° *room* temperature at that moment — coincidence of
  digits, different quantity).
- **Preset "Per Schedule"** = the custom preset
  `PRESET_SCHEDULE`. Read-side, the climate infers a preset by
  matching the 3B03 setpoints+fan against the zone's 400A row
  when no hold and no vacation are active: home/away/sleep map
  to the standard presets, wake → custom "Wake", **manual →
  the default branch → "Per Schedule"**, and **no match at all
  → also "Per Schedule"**. At boot-notify, the 400A row was not
  cached yet, so the matcher found nothing and published
  "Per Schedule"; the mirror zeroing then froze it. "Per
  Schedule" therefore means *"no hold, and setpoints match the
  manual entry or match nothing"* — it is **not** evidence the
  wall was following its schedule program.

Corollaries:

1. The phase-3 "House" climate card **never displayed live wall
   data on this Ion** — not on the incident day, not ever. The
   two template numbers (400A, served for real) were the only
   truthful part of the control surface.
2. Phase 4 (never flashed) steered using this fossil's
   `current_temperature` / `mode` / `action`: mode reads OFF
   (seed) → its steering lambda returns immediately and would
   **never have steered**; its fan circulation gated on the
   fossil action (permanently "idle") and would have run its
   windows blind to real calls. The phase-5 merge (§3) therefore
   re-sources every input from live data.
3. The wall's measured room temperature and the system mode are
   **not obtainable** from this Ion over the SAM interface with
   current knowledge (the slow poll's 3D02 zone-temperature
   reads were never once answered in any capture — one read,
   zero replies). Phase 5 does not fake
   them (§5).

## 1.4 What the code does NOT explain about the incident

Honestly, and without forcing a theory:

- **No capture was running at 13:22.** We cannot prove which
  frame — if any single frame — collided with the thermostat's
  traffic, nor reconstruct the exact call sequence the author made
  (one combined ClimateCall vs several; HA's own logs would
  tell). The correlation (card actions → immediate fault) plus
  the 2026-10-28 precedent (bus disturbance → identical fault)
  is strong circumstantial evidence, not proof.
- The Ion **never adopted** SAM writes in any test (never ACKed,
  never reacted — SAM-REGISTRATION-RESEARCH.md). So the fault
  was almost certainly about our node *transmitting* (volume,
  timing, collisions), not about the *content* of the 3B02/3B03
  frames. But an Ion-side wedge triggered by accumulated bus
  errors from ordinary polling, coincidentally surfacing then,
  cannot be excluded from the code alone.
- Why the outdoor temperature was still "---" minutes after the
  indoor fault cleared is Ion-internal (ODU re-discovery
  timing); nothing in this codebase speaks to it.
- The remediation does not depend on the unproven link: the
  climate/auto-spawn/console write paths were unaudited, one of
  them demonstrably built frames on zeroed data, and none of
  them were needed. Removing them is correct regardless of
  which exact frame hurt.

---

# 2. THE PHASE-5 PACKAGE

| Piece | What it is |
|---|---|
| `phase5.yaml` | The build. Same device name `diy-thermostat`, same SAM 0x92, same BLE sensor, same phase-3 manual number names/ids. **No `climate:` block.** |
| `phase5-components/` | Copy of `sensor-components/` with changes confined to 4 files (verified by diff): `infinitesp/infinitesp.h`, `infinitesp/infinitesp.cpp`, `infinitesp/auto_entities.py`, `sam_ascii/sam_ascii.cpp`. Production and phase-3/4 trees untouched. |
| `PHASE5.md` | This file. |

Design rules and how each is met:

1. **No unaudited write path.** The climate entity is gone
   (W1–W6, W10, W13 unreachable — no `InfinitESPClimate` object
   exists, so `control()` has no caller). The writable
   auto-spawns are removed at the source in `auto_entities.py`
   (W7 System Mode select, W8 Vacation Hours number, W9 clock
   button — the rows are deleted, with comments; the read-only
   spawns are unchanged). The sam_ascii write branch NAKs every
   `!`-verb before any setter is reached (W11; HELP text updated
   to match). The `infinitesp.sync_clock` automation action is
   not referenced by the yaml. Every remaining caller of the
   hub's stock setters in the compiled tree was enumerated by
   grep (§6, check 1): each belongs to an entity class that is
   neither declared nor spawned in this build, or to the gated
   console. The stock setters remain *compiled* (they are the
   hub's SAM-serving internals' siblings), but they have **no
   reachable caller** — that is the proof standard, and it is
   stated as such.
2. **One guarded write-core.** All 400A writes — the ten profile
   numbers, steering, fan circulation — funnel through
   `write_comfort_bytes_()` in the hub. The phase-3/4 public
   methods (`write_manual_heat/cool/fan`) are now wrappers over
   it; `write_activity_heat/cool/pair/fan` call it directly.
   Guards, in order: (1) SAM on; (2) activity/value ranges
   (setpoints 40–99 °F backstop, fan 0–3); (3) row cached;
   (4) row cache ≤ 10 min (phase-3 freshness); (5) equality
   no-op (returns success, no frame, no rate-limit cost);
   (6) deadband cool ≥ heat + 3 on the **resulting** pair;
   (7) **bus-health gate (new)**: a real thermostat reply to
   one of our polls within 60 s — stamped only in
   `handle_reply_()` on an actual 0x20 reply, never by our own
   write-through updates (which is exactly the hole guard 4
   alone would leave: a chain of our own writes could keep the
   row "fresh" forever on a dead bus); (8) **global rate limit
   (new)**: ≥ 10 s between queued comfort writes, all
   activities, all callers. A passed call queues exactly ONE
   frame — full-row func-0x0C RMW of 400A from the fresh cache,
   the shape proven 2026-10-30 — and updates the cache
   write-through.
3. **Profile control from HA.** Ten template numbers (heat/cool
   × home/away/sleep/wake/manual), each with the phase-3 pattern:
   set_action writes once through the core, then re-publishes
   the stored byte (a refused write snaps back visibly). A 45 s
   interval publishes stored bytes into all ten — publish-only
   (see the loop proof, §6 check 2). Editing a profile row
   changes the wall's **stored** profile; which profile is
   active remains the wall's business, and profiles stay fully
   editable at the wall.
4. **Fan byte — the safer option chosen.** Per-activity fan
   *numbers* are **omitted** (they would invite casual writes of
   an untested byte across five rows). All five fan bytes are
   exposed read-only as sensors. The manual row's fan byte is
   writable through exactly one path — fan circulation — and
   only while **both** "Fan Circulation" and the new "Fan
   Control Enable" switches are on (both RESTORE_DEFAULT_OFF).
   Rationale: byte 30 has never been write-tested live; the
   write itself rides the proven 400A RMW shape, but whether
   the wall adopts a fan byte from the row outside the active
   manual context is unknown. The double-switch gate makes the
   first test a deliberate, attended act (§7 check d).
5. **Phase-4 features merged, re-sourced.** Steering and fan
   circulation keep their safety semantics (sensor stale
   > 15 min → no writes; anticipation coast/restore; fan
   ownership rules) but read only live inputs (§3).
6. **No mode control.** There is deliberately **no HA control
   of HVAC mode on/off and no forcing of the active profile**:
   the bus mode byte is not identified (mode-experiment
   session 1 — the 88-read diff across Heat/Cool/Auto/Off —
   has not been run yet). Mode changes stay at the wall. When
   session 1 identifies the byte, mode control gets its own
   audited addition, not a resurrection of the stock path.

# 3. STEERING AND CIRCULATION IN PHASE 5 (what changed and why)

**Steering (30 s tick)** — feedback form. Phase 4's formula
needed the wall temperature twice (gradient offset, cutoff
guarantee); this Ion serves none (§1.3). Phase 5 computes
`err = Room Target − sensor temp` and moves the manual byte by
`clamp(round(err), −6..+6)` relative to the **stored** byte.
As the room converges, err → 0 and the desired byte → the
stored byte, so steering settles by construction (plus the
±0.7 °F settled deadband, as before). Direction comes from
live passive state: compressor running (ODU 0604 actual RPM,
the same decode as the stock Compressor Running sensor) →
steer cool; else room < target − 0.3 → steer heat; else room
> target + 1.5 → steer cool; else no direction, no writes.
Episodes/progress/anticipation keep the phase-4 state machine
on the sensor temperature. **One honest downgrade**: the
anticipatory cutoff can no longer guarantee ending the wall's
call (that needed wall temp − 1); it instead **undoes the
episode's boost** (restores the byte stored at episode start).
If that standing byte was itself calling, the call continues at
the standing rate — the wall's pre-existing behavior, not a
state this build created. Coast (120 s), single restore, and
the 1 °F-past-target release are unchanged. All steering writes
are **pair writes**: the final pair is computed first
(pair-unlock folded in — cool ≥ heat + 3 by construction, caps
88 / floor 50 as in phase 4) and lands as ONE core frame or
none — strictly safer than phase 4's two sequential frames,
which could half-land.

**Fan circulation (60 s tick)** — phase-4 ownership rules
verbatim (claim AUTO→LOW only if the byte is AUTO and not
ours; never touch the wall's own Low/Med/High; restore AUTO
only if we set it; ownership in RAM so a reboot can't strand a
restore). Call detection is passive: compressor running =
cool call; blower RPM > 0 with the fan byte at AUTO and no
ownership = treated as a heat call. Plus the §2.4 double
switch gate.

**The mirror (what HA shows now).** The ten profile numbers
(stored 400A bytes — real), five fan-mode sensors (real), Bus
Healthy + Bus Reply Age (the write gate's own inputs, real),
Room 1 BLE (real), WiFi/status, and the hub's stock telemetry
spawns. Of the stock spawns: furnace/ODU registers (blower RPM,
airflow, stages, runtimes, ODU temps) are passively snooped and
real; the accessory-life sensors read the 3B05 mirror — this
Ion's 3B05 replies were observed all-zero, so treat those
percentages as unverified. There is **no** wall-temperature,
mode, or preset entity, because the wall does not serve them
to us (§1.3). Gone with the climate block: the per-zone fossil
sensors (zone temperature/humidity/occupancy/hold state) —
they were seed/zero artifacts too.

---

# 4. FLASHING (first run, in this order)

1. In your build folder (the one holding `secrets.yaml`), copy
   in, side by side: `phase5.yaml` and `phase5-components/`.
2. `esphome run phase5.yaml` — **this compile is the first
   gate** (nothing was compiled in the preparation
   environment). If it errors, stop and send the full text back
   before flashing anything. OTA is fine (same device name).
3. After it boots, **wait ≥ 5 minutes** before judging
   anything: the node must complete slow-poll cycles so the
   400A row is cached and the bus-health gate opens (first
   thermostat replies arrive within seconds; the row within
   one 31 s rotation). Writes against an uncached/stale row or
   an unanswered bus are refused by the guards — harmless log
   lines, no frames.

# 5. FIRST-RUN CHECKS (in this order)

**(a) Entities.** On the DIY Thermostat device: ten profile
setpoint numbers (Home/Away/Sleep/Wake/Manual × Heat/Cool),
five fan-mode sensors, Bus Healthy (on), Bus Reply Age
(small), Room Target / Anticipation % / Fan Minutes Per Hour,
three switches (Sensor Steering, Fan Circulation, Fan Control
Enable — all OFF). **There must be NO climate entity, NO
System Mode select, NO Vacation Hours number, NO Hold
entities, NO Sync Thermostat Clock button.** The phase-3/4 HA
entities that no longer exist (House climate and friends)
become orphaned in HA — delete them there when convenient.

**(b) Convergence.** Within ~5 min the ten numbers equal the
wall's stored profile values (compare against the wall's
profile screens). The manual pair must show the living 70/73-style
values, not the 68/76 placeholders.

**(c) Profile write smoke test.** Change **Away Heat** by
1 °F in HA. Expect: the number snaps to the new value; in the
ESP log, one `400A away entry write queued` line; within a
poll cycle the value holds (the wall's row read-back agrees).
Then set it back. Also try breaking the deadband (e.g. set a
row's heat above its cool − 3): the number must snap back to
the stored value and the log shows the deadband refusal. This
is a stored-row edit only — the wall's active behavior does
not change unless that profile is active at the wall.

**(d) Fan byte FIRST LIVE TEST (attended, deliberate).** This
is byte 30's first write test ever. No heat/cool call running.
Turn **Fan Control Enable** ON, then **Fan Circulation** ON,
Fan Minutes Per Hour = 15, inside minutes 0–14 of an hour.
Expect the blower to start at low speed with no heat/cool
behind it (log: `fan_circ: window open ... manual fan AUTO ->
LOW`). At minute 15 it stops (`window closed ... restored to
AUTO`). If the blower never starts: turn both switches OFF and
send the log — worst case is a no-op (guards refused or the
wall ignored the byte); nothing else is affected. If it
starts but does not stop at window end: turn **Fan Control
Enable** OFF (the restore path runs on the next tick) and set
the wall's fan back to Auto at the Touch-N-Go screen.

**(e) Steering smoke test.** Same shape as phase 4's: wall in
Heat with Touch-N-Go manual active; **Sensor Steering** ON;
Room Target ~3 °F above the current Room 1 reading. Within a
minute the log shows `steering: episode start ...` and a
`steer: ... -> pair heat NN cool NN` line, and the Manual Heat
number moves. Watch one full episode in the log: progress
climbing every 30 s → `CUTOFF ... (boost undone); coast 120 s`
→ one `coast restore` → release after the room drifts 1 °F
past target. Turn the switch OFF when done testing.

**(f) Bus-health gate check (optional, conclusive).** With the
ESP log open, watch `Bus Reply Age`: it should sit in single
digits / low tens of seconds. (Do NOT yank bus wires to test
this — the 2026-10-28 lesson. The gate's logic is code-reviewed
in §6; its live proof comes free the first time the bus is
genuinely disturbed: writes refuse with `bus unhealthy` in the
log and resume when replies return.)

# 6. ROLLBACK

`esphome run phase3-control.yaml` (production kit, untouched).
The phase-5-only entities become orphaned in HA and can be
deleted there; the manual numbers and everything else carry on
untouched. Nothing on the wall needs undoing — if circulation
was mid-window when you roll back, set the wall's fan back to
Auto at the Touch-N-Go screen if it matters to you. Rolling
back restores the phase-3 build *including* its climate card —
if you roll back, do not use the House climate card, the
System Mode select, or the other auto-spawned writable
entities (§1); use only the two manual numbers, as before.

# 7. CHECKED 10 WAYS (verification performed)

ESPHome is not installed in the preparation environment: **no
compile was run here** and nothing was installed. The first
real gate is your local compile (§4). What was checked
instead:

1. **Write-path inventory.** Every `send_write_frame_()` call
   site in the phase5 hub source was enumerated (12 sites):
   the stock setters (set_zone_setpoint,
   command_setpoint_half's holding branch, set_zone_fan,
   set_zone_hold, apply_activity, set_vacation_hours,
   push_vacation_frame_, set_system_mode ×2,
   set_displayed_zone, set_displayed_clock), the one
   write-core site, plus the two direct queue pushes inside
   `send_write_frame_()` itself and in
   `defer_manual_row_write_()` (the latter reachable only
   from command_setpoint_half). Every caller of every stock
   setter was then
   enumerated by grep across the tree: climate `control()`
   (no climate block → no object → no caller), the
   select/number/datetime/button entity classes (their
   entities are neither declared in phase5.yaml nor spawned —
   climate-gated spawns die with the climate block; the three
   system spawns are deleted in `auto_entities.py`), sam_ascii
   verbs (NAK gate sits at the top of the write branch, before
   the first verb handler — verified by line order), and the
   `infinitesp.sync_clock` action (not referenced in the
   yaml). The only remaining reachable caller chain into
   `send_write_frame_()` is `write_comfort_bytes_()`.
2. **Loop analysis.** The 45 s read-back sync and the fan/bus
   publishers call only `publish_state()` and hub getters —
   no path from any publisher into a set_action or the core
   (checked by reading the lambdas). Even a hypothetical
   re-entry would hit guard 5 (equality no-op), because the
   published value IS the stored byte. Steering/circulation
   write at most once per tick (30 s / 60 s) and the core's
   10 s global rate limit bounds every caller anyway; a
   refused write changes no state (the state machines advance
   only on success, except coast entry, which is deliberately
   fail-safe: hands-off either way).
3. **Guard coverage per number.** All ten profile numbers use
   the identical set_action shape (write once via the core,
   re-publish the stored byte) — verified by reading all ten
   blocks; each passes its own activity index (0–4 in
   home/away/sleep/wake/manual order, matching the
   COMFORT_HOME/AWAY/SLEEP/WAKE/MANUAL constants) and its own
   getter for re-publish. The three setting numbers
   (Room Target etc.) publish only locally, as in phase 4.
4. **Cache-freshness path.** Guard 4 reuses the phase-3
   `register_fresh_` check on (0x20, 400A) verbatim. The
   write-through store refreshes that stamp — which is why
   guard 7 exists and is keyed on `last_tstat_reply_ms_`,
   stamped at exactly one place (`handle_reply_()`, src ==
   0x20). Verified by grep: no other assignment to
   `last_tstat_reply_ms_` exists in the tree.
5. **Rollback.** phase3-control.yaml + control-components/ are
   byte-untouched (this kit only added files and edited the
   phase5 copy — the sensor↔phase5 diff is confined to the 4
   files listed in §2, and the sensor↔control relationship is
   unchanged). Device name unchanged (`diy-thermostat`), so
   OTA rollback is a plain reflash.
6. **Name/OTA collision.** Same esphome name and friendly
   name as phases 2–4; the manual number ids
   (`manual_heat_setpoint`, `manual_cool_setpoint`) are kept,
   so HA keeps their history; all other ids are new or carried
   from phase 4 (`room_target`, `anticipation_pct`,
   `fan_minutes`, switches, globals). Every `id(...)`
   referenced in the yaml resolves to a declared id (checked
   programmatically: 29 used, 0 missing), and every hub method
   called from a lambda is declared in the hub header and
   defined in the hub source (checked programmatically).
7. **Sensor-stale path.** Steering checks the BLE age every
   tick (NaN, unsynced clock, or age > 900 s → log + no
   writes) before any direction/write logic — same posture as
   phase 4, re-verified in the new lambda. Circulation does
   not use the sensor at all. If the equipment getters go
   stale (> 120 s), they return "unknown" and both lambdas
   treat unknown conservatively (no cool-call assumption, no
   heat-call assumption).
8. **Deadband across all rows.** The core checks the
   RESULTING pair of the targeted activity for every write —
   single-byte, pair, and (vacuously) fan — against the cached
   row; verified by reading `write_comfort_bytes_()`. The
   steering pair-builder enforces the same rule by
   construction before calling, with phase-4's caps (cool
   unlock ≤ 88, heat floor 50). Yaml number ranges (heat
   50–85, cool 60–99) sit inside the core's 40–99 backstop.
9. **Rate-limit path.** Guard 8 stamps `last_comfort_write_ms_`
   at exactly one place (after a successful queue in the
   core) and checks it before queueing; equality no-ops and
   refusals do not consume budget (checked by reading the
   guard order). Worst-case bus load from ALL phase-5 control
   combined: one 38-byte frame per 10 s plus its ≤ 2
   retransmits — versus the incident surface's ~15 × 153-byte
   frames per card interaction.
10. **Doc/code consistency + offsets.** Every byte offset in
    the package was cross-checked against
    400A-TEST-RESULT.md and the captured row
    (`444C00… 3C5000… 444C00… 444C00… 4F5100…`): entry size
    7, order home/away/sleep/wake/manual, per-entry
    heat +0 / cool +1 / fan +2 (manual = 28/29/30) — the core
    computes `activity * 7 + {0,1,2}` from the COMFORT_*
    constants, matching both. `phase5.yaml` parses cleanly
    with a tolerant parser for ESPHome's `!secret` tags;
    edited C++ files are brace-balanced and the Python edits
    parse (`auto_entities.py` via ast). Every component name
    used in the yaml (`infinitesp`, `sam_ascii`, `bus_jsonl`,
    `uart_tcp_server`, template/atc_mithermometer platforms)
    exists in the local tree or the same git source phases
    2–4 used.

# 8. WHAT REMAINS UNPROVEN / LIVE-TEST-ONLY

- **Byte 30 (fan) adoption by the wall** — never write-tested.
  First test is §5(d), attended, behind two switches.
- **Profile-row writes for home/away/sleep/wake** use the
  identical frame and guards as the manual row (proven), and
  the rows are read back for real — but a non-manual row write
  has not been live-tested yet. First test is §5(c) (stored-row
  read-back proves adoption without disturbing the active
  profile).
- **Steering's feedback form** is new control logic (phase 4's
  gradient form never ran). Its bounds are conservative
  (±6 °F per tick around the stored byte, ±0.7 °F settled
  band, episode/coast machine unchanged), but the first
  episodes should be watched in the log (§5e).
- **Heat-call detection** for steering/circulation is an
  approximation (blower RPM > 0 + compressor off + fan byte
  AUTO). A fan-only circulation run by the WALL itself is
  indistinguishable from a heat call with these signals; the
  failure mode is benign (circulation defers; steering treats
  it as a heat call in progress).
- **The bus-health gate's live behavior** (refusals during a
  genuine disturbance, resumption after) — code-reviewed, not
  yet observed live (§5f).
- **Whether the Ion would ever adopt a 3B02/3B03 write** —
  moot in this build (those paths are unreachable), listed
  only because it bounded the incident analysis (§1.4).
- **HVAC mode on/off from HA** — not implemented, by design
  (§2.6). Next step is mode-experiment session 1, unchanged
  from the pre-incident plan.
