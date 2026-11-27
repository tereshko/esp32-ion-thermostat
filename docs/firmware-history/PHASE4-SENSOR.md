# PHASE 4 SENSOR — steering by the room sensor + fan circulation

Phase 3 control stays exactly as it is (HA owns the Ion's Touch-N-Go
**manual** heat/cool setpoints via guarded 400A writes — see
`PHASE3-CONTROL.md`). Phase 4 adds two autonomous features on top,
both driven by entities on the same DIY Thermostat device, both OFF
by default:

**Sensor steering.** The wall thermostat heats the room IT sits in;
the BLE sensor in Room 1 is the room that actually matters, and the
two disagree by a gradient. Every 30 s the firmware computes
`desired = Room Target °F + (wall temp − room-sensor temp)` — the
gradient offset is clamped to ±6 °F — and writes that as the manual
setpoint, so the **sensor's room** lands on target instead of the
wall's room. Only the byte for the active direction is steered
(Heat mode → heat byte, Cool → cool byte; in Auto it follows the
running call, and when idle it steers the side the room is on).

**Episodes and anticipation.** A push toward target is tracked as
an *episode*: progress is measured from the temperature where the
episode started to the target, and at **Anticipation %** of the way
(default 80 %) the boost is cut early — the setpoint is dropped to
a value that ends the wall's own call on the spot — because the
furnace and ducts keep delivering roughly 2 minutes of residual
heat after the call ends, and that residual heat carries the room
the rest of the way instead of overshooting. Then: 120 s of total
hands-off while the room coasts, the standing setpoint is restored
to target + current offset, and steering stays hands-off until the
room drifts 1 °F past the target on the other side.

**Fan circulation.** For the first **Fan Minutes Per Hour** minutes
of every hour, if the system is not OFF and no heat/cool call is
running, the manual entry's fan setting is switched from Auto to
Low so the blower stirs the air by itself; at the end of the window
it is switched back to Auto. This is the wall's own "run the fan
sometimes" mode, implemented through the manual entry's fan byte
(register 400A, byte 30 — the same write path as the setpoints).

**Status: BUILT, NOT FLASHED.** The first real gate is your local
compile (§2). The fan byte rides the same proven 400A read-modify-
write path as the setpoint bytes, but byte 30 itself has **not**
been write-tested at the wall yet — check (d) in §3 is its first
live test. Worst case there: nothing happens (the hub guards refuse
or the wall ignores the byte) and the log says so.

---

## 1. What's in the kit

| Piece | What it is |
|---|---|
| `phase4-sensor.yaml` | phase3-control.yaml + the phase 4 surface below. Same device name, same SAM 0x92, same phase 3 entities (unchanged, byte-for-byte in the config). |
| `sensor-components/` | Copy of control-components/ with ONE additive hub feature, verified by diff: `write_manual_fan(mode)` / `get_manual_fan()` for byte 30, confined to `infinitesp/infinitesp.h` / `.cpp`, 0 lines removed or changed. |
| `phase3-control.yaml` | The rollback build, included for parity with earlier kits. |
| `PHASE4-SENSOR.md` | This file. |

New entities (all start inert):

| Entity | Type | Default | Role |
|---|---|---|---|
| `Sensor Steering` | switch | OFF (every reboot) | Master switch for steering. |
| `Room Target °F` | number 60–80 | 72 (remembered) | The temperature the SENSOR room should reach. |
| `Anticipation %` | number 50–95, step 5 | 80 (remembered) | How far through an episode the boost is cut. |
| `Fan Circulation` | switch | OFF (every reboot) | Master switch for fan circulation. |
| `Fan Minutes Per Hour` | number 5–60, step 5 | 15 (remembered) | Circulation window length at the top of each hour. |

The phase 3 entities (`Manual Heat Setpoint °F`, `Manual Cool
Setpoint °F`, the House climate card, all telemetry) are untouched
and keep working exactly as before. With both new switches OFF,
this build **is** phase 3.

## 2. How to flash it

1. In your build folder (the one holding `secrets.yaml`), copy in,
   side by side:
   - `phase4-sensor.yaml`
   - `sensor-components/` (this whole folder)
2. `esphome run phase4-sensor.yaml` — OTA is fine (same device
   name). **This first local compile is the gate** (ESPHome is not
   installed in the preparation environment, same as every prior
   kit): if it errors, stop and send the full text back before
   flashing anything.
3. After it boots, **wait ≥ 5 minutes** before judging anything:
   the node must complete a slow-poll cycle so the 400A row is
   cached — the same rule as phase 3. Writes against an uncached
   or stale row are refused by the hub guards (harmless log lines,
   no frames).

The wall contract is unchanged: **Touch-N-Go stays on MANUAL** and
the system mode is yours to choose at the wall. If the wall is
switched back to a schedule profile, the written bytes stop
governing until manual is active again, exactly as in phase 3.

## 3. First-run checks (in this order)

**(a) Entities + phase 3 parity.** The five new entities from §1
exist on the DIY Thermostat device. The two manual setpoint numbers
converge to the wall's Touch-N-Go values within ~5 min (not the
68/76 placeholders), same as phase 3. Flip nothing yet.

**(b) Verify T_w before trusting steering.** Turn **Sensor
Steering** ON with the room a couple of degrees below target so an
episode starts, and watch the ESP log. Episode lines look like:

```
steering: episode: T_s=70.2 F T_w=73.0 F offset=2.8 target=72.0 F desired=75 stored=71 progress=35%
```

Compare **T_w** against the room temperature on the wall's screen —
they must match (both °F). If T_w instead shows a number like 24
(a °C-looking value), **stop: turn steering OFF and report it** —
that would mean the climate entity's temperature unit differs from
what this build assumes, and steering would compute garbage
offsets. (A built-in tripwire also refuses to steer and logs
`implausible gradient` if |wall − sensor| ever exceeds 15 °F.)

**(c) Steering smoke test, Heat mode.** Wall: mode Heat, Touch-N-Go
manual. Set **Room Target °F** about 3 °F above the current Room 1
sensor reading. Within ~5 min the `Manual Heat Setpoint °F` number
should move (log: `steering: steer: ... -> heat NN` or an
`episode start` line) — that's the boost being written from the
sensor, with nobody touching the manual numbers. Then watch one
full episode in the log: episode start → progress climbing every
30 s → a `CUTOFF at progress NN%` line → quiet → a
`coast restore -> NN` line about 2 min later → the room coasting
up to the target on the sensor graph. If the room overshoots a
lot, lower **Anticipation %**; if it stalls short and a second
episode has to finish the job every time, raise it.

**(d) Circulation smoke test.** No heat/cool call running. Turn
**Fan Circulation** ON, **Fan Minutes Per Hour** = 15. Inside the
first window (minutes 0–14 of an hour) the blower should start at
low speed with **no** heat or cool behind it — listen for it, and
the log shows `fan_circ: window open ... manual fan AUTO -> LOW`.
At minute 15 it stops (`window closed ... restored to AUTO`).
This is byte 30's first live write test (see the status note at
the top): if the blower never starts, turn the switch OFF and
send the log — worst case is a no-op, nothing else is affected.

## 4. Behavior notes

- **All writes go through the phase 3 hub guards**, unchanged:
  SAM on, row cached, row cache ≤ 10 min old, equality = no-op.
  Setpoint writes additionally keep the deadband pair rule
  (cool ≥ heat + 3 against the stored bytes); steering moves the
  other byte first ("pair-unlock", capped at 88 / floored at 50)
  when a jump would otherwise be refused. A refused write is a log
  line, never a partial state.
- **Stale or missing sensor = no writes.** Steering checks the BLE
  reading's age every tick: older than 900 s (or no valid clock)
  → it logs a warning and does nothing. The wall simply keeps
  running on the last setpoints, on its own sensor — the phase 3
  failure posture. Circulation doesn't use the sensor at all.
- **Direction gating.** Steering only ever writes the byte for the
  direction the system is actually in (Heat→heat, Cool→cool,
  Auto→the running call's side). Mode OFF at the wall = steering
  does nothing. It never changes the system mode and never
  touches schedule profiles.
- **Deadband / settled.** When the sensor room is within ±0.7 °F
  of target and the stored byte already equals the computed
  desired value, a tick is a no-op. Steering does not hunt.
- **Coast is sticky on purpose.** After a cutoff, steering will
  not re-boost just because the room is still a degree short —
  it waits for the restore (target + offset, once, at +120 s) and
  then for a full 1 °F drift past target before a new episode can
  start. If the wall re-seeds its manual entry mid-coast (someone
  switches profiles at the wall), the restore write may land on
  re-seeded values or be skipped by the guards — the ordinary 45 s
  read-back sync keeps the HA numbers truthful either way; no
  state can wedge.
- **Circulation touches byte 30 only**, and only ever writes
  AUTO(0) or LOW(1). A fan speed set at the wall is never
  overridden: if the byte already holds Low when a window opens,
  the build treats it as the wall's own and never claims or
  restores it; Med/High are never written at all. Ownership is
  remembered in RAM, so a reboot mid-window can't strand the fan:
  the byte might stay Low until the wall's next profile/mode
  change re-seeds it, but this build will never "restore" a Low
  it didn't set.
- **Circulation never fights a call.** While the climate action
  is HEATING or COOLING the circulation tick returns immediately;
  the fan byte is left wherever the call wants it.
- **Both feature switches reset to OFF at reboot** (deliberate:
  after any power event, autonomy resumes only when you switch
  it back on). The three setting numbers remember their values.
- **Logs.** Tag `steering`: one line per episode tick (with
  progress %), every cutoff/restore/release, every steered write;
  idle ticks are DEBUG-level. Tag `fan_circ`: window transitions
  only. Hub refusals appear under tag `InfinitESP` as in phase 3.

## 5. Rollback

`esphome run phase3-control.yaml` (in this kit). The five phase 4
entities become orphaned in HA and can be deleted there; the
manual numbers and everything else carry on untouched. Nothing
on the wall needs undoing — if circulation was mid-window when
you roll back, set the wall's fan back to Auto at the Touch-N-Go
screen if it matters to you.

## 6. Validation performed (and its limit)

- **ESPHome is not installed in the preparation environment** —
  no compile was run here and nothing was installed. **The first
  real gate is your local `esphome run` compile**, exactly as
  with the phase 3 kits.
- What was checked instead:
  - `phase4-sensor.yaml` parses cleanly (tolerant parser for
    ESPHome's `!secret` tags). Its diff vs `phase3-control.yaml`
    contains only: the rewritten header, the components-path
    line (+ its descriptive comment), the climate `id`, the
    globals block, the BLE sensor `id`/`on_value`, the appended
    setting numbers/switches/intervals. The two manual setpoint
    number blocks and the 45 s read-back sync interval are
    byte-identical to phase 3 (verified programmatically).
  - The component diff vs control-components/ is confined to
    `infinitesp/infinitesp.h` (+19 lines) and
    `infinitesp/infinitesp.cpp` (+64 lines), **0 lines removed
    or changed**; the added C++ is brace/paren balanced and
    mirrors the proven setpoint core's guard order, frame shape
    and write-through cache.
  - Every `id(...)` referenced in the new lambdas is declared in
    the config (checked programmatically). Climate mode/action
    enum names (`CLIMATE_MODE_HEAT_COOL`, `CLIMATE_ACTION_HEATING`,
    …) and the `current_temperature` member were cross-checked
    against the infinitesp climate sources in the tree, which
    publish mode/action/current temperature from the bus state.
  - The steering state machine (episode → progress → cutoff →
    120 s coast → restore → release at 1 °F past target) and the
    circulation ownership rules were re-read against the spec
    after implementation, including the pair-unlock caps
    (88/50) shared with the phase 3 steering rules.
