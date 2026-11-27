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
  `external_components:` (local `components/`), `uart:` — bus UART
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
- `input_boolean.hvac_filter_reminder_sent`, `hvac_filter_changed`.

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
