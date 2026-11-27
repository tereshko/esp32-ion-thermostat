# MODE EXPERIMENT — find the System Mode byte (session 1: diff hunt)

Purpose: Home Assistant cannot change the Ion's System Mode — mode commands
ride the SAM channel, which this unregistered control ignores, so today
Heat/Cool/Auto/Off can only be set at the wall. This experiment dumps the same
set of thermostat registers in all four wall modes and diffs them: the byte
that tracks System Mode — and changes with nothing else — is the candidate for
a later, separately gated write test ("true Off" from the bus).

Session 1 is **reads only**. The write test is NOT part of it.

---

## 1. What's in the kit

| File | What |
|---|---|
| `mode-experiment.yaml` | One-session build. Body = `scan.yaml` unchanged (SAM 0x92, climate House, BLE, JSONL on 2373, ASCII console on 23); the ONLY functional edit is `raw_writes: true` under `sam_ascii` (see the warning below). Header comment rewritten for this experiment. |
| `scan-components/` | **Pristine** upstream tree, InfinitESP **2026.10.21** @ `ee0fadb` — the same tree as the scan kit. Zero component changes. |
| `mode-diff-session.py` | Python driver/logger for the session (stdlib only; Python ships with the ESPHome toolchain). Sends **only** `REG?` reads — it contains no write path at all. |
| `scan.yaml` | Reference copy of the build this one derives from. |
| `MODE-EXPERIMENT.md` | This file. |

Why the diff: the thermostat maintains its own state in registers it serves
over the bus (the same mechanism that made the 400A setpoint writes work).
Somewhere in the tables it served in the 2026-11-02 scan, a byte holds the
current System Mode. Dumping the candidate tables plus controls in four
known wall states isolates it: setpoint-ish bytes stay put under a mode
flip, time/telemetry bytes drift on their own schedule, and the mode byte
steps exactly with the wall setting (four distinct states → a strong
signature).

Per state the script reads 88 registers: controls `400A`, `3B02`; full
SYSCTRL rows `4900`–`490A`; full INGUI rows `0300`–`0309`; full INGDATA
rows `3100`–`3133`; and the first row of every other served table
(`0100`, `0200`, `0400`, `0600`, `2F00`, `4100`, `4200`, `4600`, `4700`,
`4800`, `4A00`, `4C00`, `4E00`).

## 2. Flash

1. Copy `mode-experiment.yaml` and the `scan-components/` folder into your
   build folder, next to your existing `secrets.yaml` (same place the
   scan kit went).
2. `esphome run mode-experiment.yaml` — **the first real gate is this
   local compile** (ESPHome is not installed in the preparation
   environment; the yaml parses and the components are a pristine upstream
   tree, but the compile itself is unverified here). If it errors, stop
   and send the full text back before flashing anything.
3. OTA flash is fine. Same device name — HA sees the same DIY Thermostat
   (the Phase 4 entities will show unavailable while this build runs;
   they come back with the reflash in §6).

> **WARNING — this build's console CAN write to the bus.**
> Unlike the scan build, `mode-experiment.yaml` sets
> `sam_ascii raw_writes: true`, so a hand-typed `REG!` command on the
> TCP 23 console would really be sent (from bus seat 0x93) and could
> change thermostat registers. Session 1 does not use writes:
> `mode-diff-session.py` sends only `REG?` reads, and **no `REG!`
> command is to be typed by hand** in this session. If you open the
> console interactively at all, treat it as read-only. (Tables 04/3F
> and register 0104 stay refused by the firmware even with raw_writes
> on — that much protection remains.)

## 3. Pre-flight (after flashing)

1. Wait **≥5 minutes**: the hub must observe the bus devices and settle;
   the diagnostic seat reads through the same engine.
2. Confirm in HA that DIY Thermostat telemetry is live (House Temperature
   updating). The thermostat does **not** need re-commissioning: the SAM
   identity (0x92) is identical to the other builds'.
3. Pick a time when flipping the system through Cool and **Off** for a
   few minutes each is acceptable — the house will actually change modes
   during the session (Off means no heating until the session ends and
   you set the wall back).

## 4. The session

From your build folder:

```
python mode-diff-session.py
```

The script connects to 192.168.1.72:23, echoes everything to the screen,
and saves the **complete raw session** to `mode-diff-YYYYMMDD-HHMMSS.log`
in the same folder. It needs you at the wall, four times:

1. Script prompts: **Set the wall System Mode to HEAT.** Do it at the
   Ion's screen (System Mode setting). Touch-N-Go selection does not
   matter for this experiment — leave it, and leave all setpoints,
   exactly as they are.
2. **Wait the 15 seconds the prompt asks for** (lets the control finish
   the mode transition and update its tables), then press Enter in the
   terminal. The script runs that state's 88 reads — a few minutes —
   printing each result line as it lands. A read that times out is noted
   and the dump moves on; that is expected noise, not a failure.
3. Repeat for **COOL**, then **AUTO**, then **OFF**, same pattern each
   time: flip at the wall when prompted, wait 15 s, press Enter.
4. After the OFF dump the script prints **"DONE"** and exits. Leave the wall in OFF for the moment, or set it
   back to your normal mode right away — the dumps are already complete
   either way.

Whole session: roughly 15–25 minutes, most of it the script reading.

Rules during the session:

- **Don't type anything into the console except the script's Enters.**
  In particular, no hand-typed console commands (see the §2 warning).
- Don't run the session during a thermostat commissioning/install flow.
- Abort criteria (stop the script with Ctrl+C, reflash per §6, report
  instead of results): a comm fault on the Ion screen, repeated bus
  errors, or the thermostat otherwise misbehaving. Read-only probing is
  the same class of reads the stock discovery performs, so none of this
  is expected.

## 5. Send the log

Keep the resulting `mode-diff-YYYYMMDD-HHMMSS.log` for analysis
(same as the scan logs).

## 6. What happens next (not this session)

1. The four dumps get diffed byte-by-byte to name the candidate
   byte(s) for System Mode — the ones that step HEAT/COOL/AUTO/OFF and
   track nothing else.
2. Only then, as a **separate gated step** (its own go-ahead from
   the author): a short write test with this same build — with the wall in
   Heat, one `REG!` flipping the candidate byte to its OFF value,
   typed by hand under supervision. Judged by the wall screen and a
   `REG?` readback, **not** by the write acknowledgement.
3. The wall always wins locally: at any moment you can set the mode
   back at the Ion screen, whatever the bus wrote. If the write is
   refused, ignored, or does anything unexpected, the test stops there
   and the finding is "mode is not bus-writable this way" — also a
   result worth having.

## 7. Restore

Reflash the daily driver when the experiment is done:

```
esphome run phase4-sensor.yaml
```

(or `phase3-control.yaml`, if that was the build live before this
session). The raw_writes console goes away with this build — the
control builds have no write-enabled console.
