# PHASE 6 — SENSORLESS AUTONOMY (phase 5 + everything that needs no room sensors)

Built 2026-11-26, on the author's scope: **"мы пока не имеем сенсоров
никаких. Просто пока голая esp и плата захвата. Давай реализуем
все нужные вещи"** — implement everything from the thermostat-
algorithms research that works on a bare ESP + RS-485 board,
with zero room sensors.

**Status: BUILT, NOT COMPILED, NOT FLASHED** — same as every
prior kit, the first gate is your local `esphome run
phase6.yaml` compile. Base is phase5.yaml copied verbatim;
components are the unchanged `phase5-components/` tree;
the write-core, all guards, the profile numbers, steering
and the read-back sync are phase 5 untouched. Rollback:
reflash phase5.yaml (or phase3-control.yaml).

---

# 1. WHAT'S IN

## 1.1 ESP side (`phase6.yaml`)

1. **SNTP clock** (`sntp_time`) next to the HA clock. Phase 5's
   only time source was Home Assistant — the dead-man below has
   to judge time exactly when HA is the thing that died.
2. **"HA Heartbeat" number** — local-only (the phase-4 settings
   pattern): HA writes the current epoch into it every 5 min;
   the set_action only stores it in a global. `restore_value:
   false` on purpose — after a reboot the heartbeat is 0
   ("never received") until HA writes again. (The value travels
   as a float; at ~1.79e9 the float32 spacing is 128 s, so the
   stored epoch can be off by ~64 s. The limit is in hours —
   irrelevant.)
3. **Dead-man return** — switch "Dead-man Return" (default OFF
   at every reboot, like all control switches here) + setting
   "Dead-man Hours" (1–24, default 6). While armed: if the
   heartbeat is older than the limit AND the stored manual
   pair is outside the **safe band** (heat 60–72 °F, cool
   74–85 °F), the node writes the **baseline pair 68/78**
   through the same guarded write-core — once per outage; the
   flag re-arms when the heartbeat is fresh again. A pair
   already inside the band is left alone (nothing is
   stranded). It can never fire before the first heartbeat
   since boot, so a node without the HA package installed is
   inert. All hub guards still apply — on a dead bus the
   write is refused and retried a minute later.
4. **Fan circulation accounting** — replaces the phase-5 fixed
   window (first N minutes of the hour). The hourly target is
   now a budget: minutes the blower already ran on **real
   calls** this hour are credited toward "Fan Minutes Per
   Hour" (passive detection, same as phase 5: compressor
   running = cool call; blower turning with the fan byte at
   AUTO and no ownership = heat call), and circulation tops up
   only the missing minutes. Ownership rules are phase-5
   verbatim (claim AUTO→LOW only if not ours, never touch the
   wall's Low/Med/High, restore only our own Low, never touch
   the byte while a compressor call runs). One bounded
   inaccuracy, stated in the code: a heat call that starts
   while OUR Low is on the byte is indistinguishable from our
   own circulation — its minutes count as circulation instead
   of credit. Benign either way.

Sensor steering stays in the build and stays **inert** while
the BLE sensor is absent/stale — phase 5 designed it that way
(stale > 900 s → no writes). Nothing to remove.

## 1.2 HA side (`phase6-ha.yaml`, an HA package)

1. **Time-of-day profiles** — Day / Evening / Night pairs
   (helpers, defaults 70/74, 71/75, 68/76; starts 10:00 /
   17:30 / 00:00 — the author's 2026-11-17 example) written into the
   manual row at each period start. This is the profiles-by-
   time engine decided 2026-11-17, now with real hold
   semantics:
   - **Schedule** — periods apply as they come.
   - **Temporary Hold** — your manual pair stands until the
     NEXT period start, then Schedule resumes automatically.
     (To use: pick the mode, then set the pair on the device.)
   - **Permanent Hold** — the pair stands until you change
     the mode.
   - **Vacation** — the vacation pair (default 55/85) applies
     immediately; Schedule resumes automatically at
     "Vacation Until".
2. **Heartbeat automation** — epoch → "HA Heartbeat" every
   5 min and at HA start.
3. **Node-offline alert** — if the node is unavailable > 1 h,
   a persistent notification (cleared when it returns).
4. **Filter reminder by real run hours** — a "Furnace Running"
   template sensor (compressor running OR blower RPM > 0)
   feeds a history_stats counter from "Filter Changed At";
   at the limit (default 1000 h) a notification fires once;
   pressing "HVAC Filter Changed" after a swap resets both.

# 2. WHAT'S DELIBERATELY NOT IN (and why)

All five need an indoor temperature/humidity the node does
not have without room sensors — the wall serves neither to a
SAM (PHASE5.md §1.3):

- **Adaptive recovery / Optimum Start** — needs the room's
  measured °F/h rate. First in line when sensors return.
- **Occupancy setback from room sensors** — no occupancy
  source. (HA phone presence is a separate, later option.)
- **Multi-sensor averaging / participation** — Room 2's
  telemetry is already in the build (2026-11-24); averaging
  waits for sensors to actually be in play.
- **Humidity overcool** — no humidity source.
- **Freeze monitoring** — no indoor temperature. The
  dead-man (§1.1.3) covers the other half of that research
  item: a setpoint stranded by a dead controller.

**Setpoint separation stays cool ≥ heat + 3 °F.** The
research found ecobee's 5 °F minimum — but +5 would forbid
the proven 70/73 manual pair, and +3 is exactly Honeywell's
default. Not changed.

# 3. INSTALL ORDER

1. Flash-kit folder: replace `phase5.yaml` with `phase6.yaml`
   (keep `phase5-components/` and `secrets.yaml` as they are).
   `esphome run phase6.yaml` — compile is the first gate; on
   error, send the full text back before flashing anything.
2. HA: drop `phase6-ha.yaml` into the packages folder (needs
   `packages: !include_dir_named packages` in
   configuration.yaml), restart HA once.
3. **Check two entity ids** in the package's template sensor
   (marked CHECK): `binary_sensor.diy_thermostat_compressor_running`
   and `sensor.diy_thermostat_blower_rpm` are the hub's stock
   telemetry spawns — if your HA named them differently, fix
   the two lines there. Everything else hangs off the
   phase-3/5 device entities, unchanged.
4. The wiring/power order from 2026-11-24 still stands:
   **power decision and a clean bus first** — phase 6 changes
   nothing about that gate. On the bench (no bus), expect the
   guards to refuse writes; that's the design working.

# 4. FIRST-RUN CHECKS (after the phase-5 §5 checks pass)

(a) **Entities.** Phase-5 list, plus: numbers "HA Heartbeat"
and "Dead-man Hours", switch "Dead-man Return" (OFF). In HA:
the HVAC helpers, "Furnace Running", "Filter Runtime Hours".

(b) **Heartbeat.** Within 5 min of HA being up, "HA Heartbeat"
shows a current epoch and keeps advancing every ~5 min.

(c) **Profiles.** Set hold mode to Schedule, set Day start a
few minutes ahead, watch the boundary: the manual pair in HA
takes the Day pair and the ESP log shows one queued 400A
write. Then set "Temporary Hold", change the pair by hand,
wait for the next boundary: the mode flips back to Schedule
and the period pair applies.

(d) **Circulation accounting.** Needs byte 30's first live
test (PHASE5.md §5d) done first — same attended procedure.
Then: run a real heat/cool call for ~10 min inside an hour,
watch the log — credit minutes accumulate and circulation
starts that hour only for the remainder of the target.

(e) **Dead-man live test (attended).** Wall in Manual. Set the
manual pair outside the band (e.g. heat 74). "Dead-man
Hours" = 1, "Dead-man Return" ON. Disable the heartbeat
automation in HA. Within ~65 min the ESP log shows the
dead-man line and the pair becomes 68/78. Re-enable the
heartbeat automation; the flag re-arms (log goes quiet). Set
"Dead-man Hours" back to 6.

(f) **Vacation.** Set "Vacation Until" ~10 min ahead, switch
the mode to Vacation: the pair becomes 55/85 at once; at the
until-time the mode returns to Schedule and the current
period's pair applies.

# 5. CHECKED BEFORE DELIVERY (no compile here, as always)

- phase6.yaml parses with a tolerant parser (!secret stubbed);
  every `id(...)` used in a lambda resolves to a declared id
  (checked programmatically: 0 missing); the four edits are
  the only diff vs phase5.yaml besides the header (the build
  script asserted each anchor exactly once; the old fixed-
  window circulation block is gone, replaced, not duplicated).
- phase6-ha.yaml parses as plain YAML; 8 automations,
  2 scripts, all helper references are to helpers the same
  file defines, except the diy-thermostat device entities
  (§3.3 caveat).
- Every new ESP write path funnels into the existing guarded
  core (`write_activity_pair` / `write_activity_fan`) — the
  dead-man and circulation add no new frame shapes.

# 6. UNPROVEN / LIVE-TEST-ONLY

- Everything in PHASE5.md §8, unchanged (byte 30 adoption,
  non-manual row writes, steering's feedback form, the
  bus-health gate live).
- The circulation credit for heat calls rests on the same
  passive approximation as phase 5 (blower + AUTO byte).
- The dead-man's full loop (heartbeat stale → baseline on the
  wall) is test §4(e) — until it runs, the proven part is
  "guards refuse on a dead bus" and the code path.
- history_stats filter hours depend on the two CHECK entity
  ids (§3.3) and on HA recorder history being enabled.
