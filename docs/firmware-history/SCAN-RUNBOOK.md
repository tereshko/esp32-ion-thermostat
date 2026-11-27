# SCAN RUNBOOK — issue #61 diagnostic session (planned 2026-11-01)

What nebulous asked for in issue #61 (2026-10-31): run his new ASCII-console
bus workbench from bus seat **0x93** and attach the output — `SCAN?` (map every
observed device's tables; he wants to compare what the ICP build serves against
Carrier/Bryant logs), plus `REG? 20 3B02` and `REG? 20 3B03` re-checks from 0x93.

**This session is READS ONLY.** `REG!` (writes) is not part of it: the scan
build deliberately leaves `sam_ascii raw_writes` unset, so a write command is
refused by the firmware itself (`REG: NAK LOCKED` + "ENABLE WITH sam_ascii
raw_writes: true"). If the 400A write test from nebulous's comment is ever run,
that is a separate decision and a separate build with `raw_writes: true`.

This kit supersedes the home-grown TABLE-SCAN-PLAN.md approach for this task:
upstream implemented the scan himself (better: his frames come from the
dedicated 0x93 seat and never touch the register store or poll health).

---

## 1. What's in the kit

| File | What |
|---|---|
| `scan.yaml` | One-session build. Body = `phase2.yaml` unchanged (SAM 0x92, climate House, BLE, JSONL on 2373, ASCII console on 23); only the local components path differs. |
| `scan-components/` | **Pristine** upstream tree at the diagnostics commit — InfinitESP **2026.10.21**, upstream `main` @ `ee0fadb` ("add scan and reg commands to sam ascii", 2026-10-31), extracted from the local clone (`~/workspace/diy-thermostat/infinitesp`). No local modifications of any kind. |
| `scan-session.py` | Python driver/logger for the session (stdlib only; Python ships with the ESPHome toolchain). |
| `SCAN-RUNBOOK.md` | This file. |

Why a separate build instead of refreshing `control-components/`:
the diagnostics are **not** a sam_ascii-only feature. The new `sam_ascii`
calls a scan/read engine that lives in the **hub** component
(`diag_scan_start*`, `diag_read_request`, … in `infinitesp.cpp/.h`, +991/−44
lines across 8 files vs the 2026.10.19 tree the control build is layered on),
and the same upstream step also carries an unrelated change (3B06 dealer-info
fallback). A partial refresh will not compile, and a full refresh would
re-base the daily-driver control build and force its re-validation — not a
morning-of job. The scan build leaves `phase3-control` exactly as it is;
diagnostics work in any mode (passive included) with the SAM live at 0x92.

## 2. Flash

1. Copy `scan.yaml` and the `scan-components/` folder into your build folder,
   next to your existing `secrets.yaml` (same place `phase3-test.yaml` went).
2. `esphome run scan.yaml` — **the first real gate is this local compile**
   (ESPHome is not installed in the preparation environment; the yaml parses
   and the components are a pristine upstream tree, but the compile itself is
   unverified here). If it errors, stop and send the full text back before
   flashing anything.
3. OTA flash is fine. Same device name — HA sees the same DIY Thermostat
   (the two Manual Setpoint number entities from the control build will show
   unavailable while this build runs; they come back with the reflash in §6).

## 3. Pre-flight (after flashing)

1. Wait **≥5 minutes**: the hub must observe the bus devices (thermostat
   0x20, furnace 0x44, outdoor unit 0x53) — `SCAN?` sweeps devices the bus
   has *shown*, and a fresh boot starts with an empty list.
2. Confirm in HA that DIY Thermostat telemetry is live (House Temperature
   updating). The thermostat does **not** need re-commissioning: the SAM
   identity (0x92) is identical to phase2's.
3. The wall needs nothing: no mode changes, no hold. Leave the system
   exactly as it normally runs.
4. *Optional, cheap:* in a second window start your usual JSONL capture
   (`python capture.py scan-session`) — the 0x93 diagnostic frames appear
   in it as corroboration. Not a substitute for the console log.

## 4. The session

### Primary method — scripted (recommended)

From your build folder:

```
python scan-session.py
```

It connects to 192.168.1.72:23, sends the command sequence below, echoes
everything to the screen, and saves the **complete raw session** to
`scan-YYYYMMDD-HHMMSS.log` in the same folder. It sends nothing else — in
particular nothing while the scan is streaming (see the hard rules).

### Fallback method — PuTTY (manual)

Connection type **Raw** (not Telnet — telnet negotiation bytes would land
in the command buffer), host 192.168.1.72, port 23. Before connecting:
Session → Logging → "All session output", pick a file name. After the
banner, type the commands from §5 one at a time, waiting for each result.

## 5. Command sequence and what to expect

| # | Command | Expected output | Duration |
|---|---|---|---|
| 1 | `SCAN?` | `SCAN: STARTED`, then per device: `SCAN 20 BEGIN`, one `SCAN 20 <table> HIT NAME=… ALLOC=… ROWS=… LEN=… DATA=…` line per served table, `SCAN 20 REFUSED_TABLES=…`, `SCAN 20 TIMEOUT_TABLES=…`, `SCAN 20 DONE HITS=… REFUSED=… TIMEOUTS=…`; final line `SCAN DONE DEVICES=3` (device count = whatever the bus showed) | ~1–3 min per responsive device; see below |
| 2 | `REG? 20 3B02` | `REG: SENT 20 3B02 AS 93`, then `REG 3B02: <hex>` (or `REFUSED <code>` / `TIMEOUT`) | seconds (reply ~20 ms typ.; 5 s worst case) |
| 3 | `REG? 20 3B03` | same shape, `REG 3B03: …` | seconds |
| 4 | `REG? 20 400A` | same shape, `REG 400A: <70 hex chars>` — the comfort row as served from the 0x93 seat | seconds |

Scan timing, from the firmware's own constants: one tabledef probe per
device table (0x01–0xFF) at a 250 ms pace; a hit or an exception-refusal
costs ~0.3 s, a table the device ignores costs a full 5 s reply timeout;
a device that times out 8 tables in a row is marked `ABSENT` and skipped
(~40 s). Budget **~10 minutes** for the whole sweep; the script allows 25.
Long silent stretches are normal (refusals/timeouts are aggregated and
printed only at each device's DONE line) — silence is not a hang.

### Hard rules during `SCAN?`

- **Type nothing.** Any line sent to the console — even an empty Enter —
  aborts the running scan by design ("SCAN DONE … ABORTED"). This includes
  a second client: don't open another console and type into it.
- **Stay connected.** Scan lines are rendered live and are not buffered
  for replay; if Wi-Fi drops the connection mid-scan, that output is lost.
  Reconnect and simply run `SCAN?` again.
- Don't run the session during a thermostat commissioning/install flow.

Abort criteria (stop, restore per §6, report instead of results): repeated
`crc_fail` climbing in the JSONL capture, a comm fault on the Ion screen,
or the thermostat otherwise misbehaving. The scan is read-only probing of
tabledefs — the same reads the stock discovery already performs — so none
of this is expected.

## 6. After the session

1. Attach the session log to issue #61: GitHub issue comment → attach
   `scan-YYYYMMDD-HHMMSS.log`. If the web UI refuses the `.log` extension,
   rename the same file to `scan-output.txt` and attach that. A one-line
   comment is enough ("SCAN? + REG? output from the ICP unit, as requested —
   SAM at 0x92 live, diagnostics from 0x93, reads only"); the author posts it
   himself, as always.
2. Restore the daily driver: `esphome run phase3-control.yaml`
   (or `phase2.yaml`, if that was the build live before this session).
3. Keep the log file — the output gets a local read-through against the protocol map before or after
   posting, your choice.
