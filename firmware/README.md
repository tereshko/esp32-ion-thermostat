# Node firmware

The unified ESPHome build for the ESP node on the Ion bus, plus its
Home Assistant package. Background and protocol details:
[`docs/HOW-IT-WORKS.md`](../docs/HOW-IT-WORKS.md).

## Files

- `thermostat.yaml` — the node firmware (ESP32 / ESP32-S3).
- `components/` — the local ESPHome components: the hardened
  InfinitESP-derived bus component (telemetry + the single guarded
  400A write-core), the bus JSONL capture streamer, the ASCII console,
  and the RMT UART for auto-direction transceiver boards.
- `home-assistant.yaml` — HA package: Day/Evening/Night profiles,
  hold modes, the 5-minute heartbeat the node's dead-man return
  watches, offline alert, filter-hours reminder.
- `secrets.yaml.example` — copy to `secrets.yaml` and fill in.

## Build and flash

1. Copy `secrets.yaml.example` to `secrets.yaml`; set Wi-Fi and the
   BLE sensor MAC addresses (the ones in the configs are
   placeholders).
2. `esphome run thermostat.yaml`
3. In Home Assistant, include `home-assistant.yaml` as a package and
   check the two entity ids the package references against your own:
   `binary_sensor.diy_thermostat_compressor_running` and
   `sensor.diy_thermostat_blower_rpm`.

## Operating contract (do not relax)

- Setpoint writes only while the wall control is in Touch-N-Go
  Manual; the thermostat re-seeds the manual slot from the active
  profile at every mode/profile change.
- All writes go through the single write-core: full-table
  read-modify-write, cool ≥ heat + 3 °F, cached image ≤ 10 min old,
  bus healthy (a thermostat reply within 60 s), 10 s global rate
  limit.
- There is deliberately **no climate entity**. The stock climate
  component's extra write paths into the (dead) SAM mirror caused a
  furnace communication fault in this installation; plain number
  entities plus the write-core are the whole control surface.
- Sensor steering never writes on stale sensor data (>15 min).
- The dead-man return is off by default; arm it only after the
  heartbeat automation runs reliably.
