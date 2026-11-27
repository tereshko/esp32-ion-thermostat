# Entity & configuration index — the file-level facts

The narrative documents describe behaviour; this page pins the exact
names and core blocks of the shipped files (`firmware/thermostat.yaml`,
`firmware/home-assistant.yaml`) so a rebuilder does not have to guess
them. Behavioural rules live in the guide (§11) and PHASE5/PHASE6.

## Node (ESPHome) core

- Device: substitutions `name: diy-thermostat`, friendly name
  "DIY Thermostat".
- `esp32:` board **esp32dev**, framework **esp-idf** (recommended
  version). (The mirror/replacement target hardware is ESP32-S3
  N16R8; the shipped node build targets the classic ESP32.)
- Blocks present: `logger:` (USB serial), `api:`, `ota:`, `wifi:`
  (credentials via `secrets.yaml`, never in the repo),
  `external_components:` — the local `components/` **plus a git
  component** (`esphome-uart-link`, provider of the two TCP servers;
  the build does not compile without it), `uart:` — bus UART
  38400 8N1, TX → GPIO17 side / RX → GPIO16 side of the RS-485
  module (module TXD → GPIO16, RXD → GPIO17), `esp32_ble_tracker:`
  (passive), `time:` — `sntp` (id `sntp_time`) next to the HA clock.
- TCP servers from the components: ASCII console on **23**, bus
  capture (JSONL) on **2373**.

## Room sensors

- **Room 1** — Xiaomi LYWSD03MMC with ATC firmware (ATC1441
  advertising, values in °C), ESPHome platform `atc_mithermometer`,
  bound by MAC (masked in this repo). This is the steering input.
- **Room 2** — a second LYWSD03MMC (ATC), telemetry only
  (temperature / humidity / battery); not a steering input.

## Home Assistant package — helpers

- `input_select.hvac_hold_mode` — Schedule / Temporary Hold /
  Permanent Hold / Vacation.
- `input_datetime.hvac_day_start` (10:00), `hvac_evening_start`
  (17:30), `hvac_night_start` (00:00) — profile period starts.
- `input_datetime.hvac_vacation_until`, `hvac_filter_changed_at`.
- `input_number.hvac_day_heat` / `hvac_day_cool` (70/74 °F),
  `hvac_evening_heat` / `hvac_evening_cool` (71/75),
  `hvac_night_heat` / `hvac_night_cool` (68/76),
  `hvac_vacation_heat` / `hvac_vacation_cool` (55/85),
  `hvac_filter_hours_limit` (default 1000 h).
- `input_boolean.hvac_filter_reminder_sent`; `input_button.hvac_filter_changed`
  (a momentary button, not a boolean).

## Home Assistant package — scripts & automations

- Scripts: `script.hvac_apply_period`, `script.hvac_apply_current_period`.
- Automations: `hvac_period_boundaries`, `hvac_hold_mode_changed`,
  `hvac_vacation_end`, `hvac_ha_heartbeat` (writes the epoch into the
  node's "HA Heartbeat" number every 5 min), `hvac_node_offline_alert`,
  `hvac_node_back_alert_clear`, `hvac_filter_reminder`,
  `hvac_filter_changed`.

Entity ids the package expects on the node side (check at install):
`binary_sensor.diy_thermostat_compressor_running`,
`sensor.diy_thermostat_blower_rpm`.

## Node entity inventory (as defined in `firmware/thermostat.yaml`)

- Numbers: the ten profile setpoints ("Home/Away/Sleep/Wake/Manual
  Heat Setpoint °F" and "… Cool Setpoint °F"), "Room Target °F",
  "Anticipation %", "Fan Minutes Per Hour", "Dead-man Hours", and
  **"HA Heartbeat"** — a template number, min 0 / max 2,000,000,000 /
  step 1, mode box, `restore_value: false` (it reads 0 = "never
  received" after every reboot, by design).
- Template sensors (read-only): "Home/Away/Sleep/Wake/Manual Fan
  Mode" — they mirror the 400A fan bytes; not selects, not settable.
- Switches: "Sensor Steering", "Fan Circulation",
  "Fan Control Enable", "Dead-man Return" (all default OFF).
- Sensors: "Room 1 Temperature / Humidity / Battery",
  "Room 2 Temperature / Humidity / Battery" (both `atc_mithermometer`),
  "Bus Reply Age", "WiFi Signal"; binary sensors "Bus Healthy" and
  "Device Status" (ESPHome status platform).
- Hub-spawned telemetry (defined by the `infinitesp` component, not
  the YAML): furnace/ODU registers — blower RPM, airflow, stages,
  runtimes, ODU temperatures/pressures — and accessory-life sensors.
  The two ids the HA package depends on are listed in the CHECK note
  above; the full spawn set is the component's entity reference.

## Home Assistant package — automation logic in one line each

- `script.hvac_apply_period` — writes one period's pair (or the
  vacation pair, in Vacation mode) into the node's Manual Heat/Cool
  numbers. `script.hvac_apply_current_period` — picks the period
  from the current time against the three start datetimes, then
  applies it.
- `hvac_period_boundaries` — time triggers at the three period
  starts: in Schedule mode applies the new period; in Temporary
  Hold a boundary ends the hold (mode returns to Schedule, the new
  period applies). Permanent Hold and Vacation ignore boundaries.
- `hvac_hold_mode_changed` — on any change of `hvac_hold_mode`:
  entering Schedule applies the current period; entering Vacation
  applies the vacation pair; Temporary/Permanent Hold change
  nothing until the user sets a pair on the device / the next
  boundary.
- `hvac_vacation_end` — at `hvac_vacation_until`: if the mode is
  Vacation, returns it to Schedule and applies the current period.
- `hvac_ha_heartbeat` — every 5 min (and at HA start) writes the
  current epoch into `number.diy_thermostat_ha_heartbeat`.
- `hvac_node_offline_alert` — the node's Manual Heat number
  unavailable for over an hour → persistent notification
  `hvac_node_offline`. `hvac_node_back_alert_clear` — the number
  returns → the notification is dismissed.
- `hvac_filter_reminder` — hourly check: real blower hours since
  `hvac_filter_changed_at` at or over `hvac_filter_hours_limit`
  and the reminder not yet sent → notification + sets
  `hvac_filter_reminder_sent`. `hvac_filter_changed` — when the
  `input_button.hvac_filter_changed` button is pressed: stamps
  `hvac_filter_changed_at` to now, clears the reminder flag and
  notification.

## Settings defaults and steering clamps (code values)

- "Room Target °F": default 72, range 60–80. "Anticipation %":
  default 80, range 50–95. "Fan Minutes Per Hour": default 15,
  range 5–60.
- After the ±6 °F steering step, the desired pair is clamped into
  the corridors heat 60–80 / cool 68–86 before the write-core sees
  it. The ten profile numbers' boot placeholders: Home 68/76,
  Away 60/80, Sleep 68/76, Wake 68/76, Manual — the wall's stored
  pair once read.

## The HA package's own entities

- `binary_sensor.furnace_running` (template: compressor running OR
  blower RPM > 0) and `sensor.filter_runtime_hours` (history_stats
  over Furnace Running since `hvac_filter_changed_at`) — defined by
  the package itself, not by the node.

## HA package — edge cases a rebuilder must keep

- Time triggers have **no catch-up**: if HA is down across a period
  boundary, that period's pair is not applied until the next
  boundary. If HA is down at "Vacation Until", the mode stays
  Vacation (boundaries ignore it) until HA is back *and* the end is
  re-triggered or the mode is changed by hand.
- `input_datetime.hvac_vacation_until` has **no initial value**:
  set it before choosing Vacation — a Vacation with no end date
  never ends on its own.
- `hvac_apply_current_period` assumes the period order
  night < day < evening in its template comparisons; keep the three
  start helpers in that order.

## What the node serves as a SAM (its own register image)

The hub answers reads at 0x92 from its seeded register image
(unknown registers get a func-0x15 exception, code 0x04):

- `0104` (120 B): device "SYSTEM ACCESS MODULE", model
  "InfinitESP--SAM", serial "1726ESP32SAM01", software = build date.
- `040E` (17 B): "P3534315" + 0x02 — byte-exact from a physical SAM;
  an exception here makes a thermostat disown the SAM.
- `0420` (20 B): captured interface config, undecoded.
- `3B02` (29 B): seed — active zones 0x01, 70 °F temps, 50 %
  humidity, stagmode OFF, displayed zone 1.
- `3B03` (150 B): seed — heat 68 / cool 76 per zone, names
  "Zone 1"…"Zone 8".
- `3B05` (11 B): zeros until the thermostat's own image replaces
  them via the slow poll. `3B06` (52 B): dealer/config seed
  (dealer "InfinitESP"). `3B0E` (1 B): 0. `030D` (7 B): zeros.
- Writes addressed to the SAM are stored (except `0104`, which is
  identity-protected) and ACK-echoed.
- Also in the component, inert in this build (no addresses in the
  YAML): full ZC (0x60/0x61) and NIM emulation subsystems.

## Console surface (TCP 23, no authentication — LAN trust only)

- **Write verbs are disabled in this build**: any line containing
  `!` is answered `NAK DISABLED` before any setter is reached
  (HELP states it plainly). The stock implementations remain
  compiled below that early return — see the standing warning in
  `firmware/README.md`.
- Read grammar (live): system `MODE? OAT? DAY? TIME? ZONE? CFGEM?`;
  per-zone `Z#RT? Z#RH? Z#HTSP? Z#CLSP? Z#FAN? Z#HOLD? Z#NAME? …`;
  accessories `FILTRLVL? UVLVL? HUMLVL? VENTLVL?` + `…RMD?` forms;
  vacation `VACAT? VACDAYS? …`; config/dealer `CFGDEAD? CFGCPH?
  DEALER? BLIGHT? …`; `HELP`.
- `REPORT?` streams the hub's full JSON bus diagnostic (register
  census, poll diagnostics, hold-event audit ring) to any connected
  client. On this thermostat the read verbs answer from the node's
  seed/zero mirror — they describe the node's image, not the wall.

## Room-sensor flashing (owner-performed)

The LYWSD03MMC units are flashed with ATC firmware via the Telink
web flasher. Load-bearing details: advertising must be **ATC1441**
(the `atc_mithermometer` platform parses only that format; PVVX is
ignored), values in °C, and the advertising interval is set in the
flasher (Room 2 = 5000 ms). MAC addresses and flasher settings live
only in the owner's `secrets.yaml` / flasher session — the repo
carries placeholders by design.
