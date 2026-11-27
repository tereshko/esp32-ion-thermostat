# Upstream: nebulous/infinitesp issue #61

The project's one open upstream thread. Filed from this installation
during phase 2/3: the SAM-side behaviour of the Ion (zero mirror,
ignored writes, the 400A path) and the node's table scan of the
thermostat.

## The issue as filed

The Ion never registers a SAM (three attempts). In the commissioning
capture (6,543 frames) the thermostat made only **two 0104 reads
toward 0x92**, with `040E` = 0, `3F02` = 0, `031C` = 0 frames, and
answered the SAM's polls with **31 zero-filled 3B02/3B03 replies**.
The issue asks about brand gating; three JSONL captures were
attached.

## What the thread established

- 2026-10-31: nebulous replied with a proposed test — read the
  thermostat's table 0x40 row directly. That path was already
  covered by this project's captures; the registration gate is
  firmware-internal (see the SAM registration research), so the
  thread's open question is narrower than the issue title suggests.
- 2026-10-31: the project's **400A result** comment was posted: the
  test ran from 0x92 (not 0x93); baseline 70 → 76 armed at the wall;
  the 76 → 78 write landed on the wall's screen; a clean validation
  run held 71 °F (6 polls over 24 min, ~21k frames, **0
  exceptions**). The production variant adds the phase-5 guards.
- 2026-11-02: the project's **REG?/SCAN? results** comment was
  posted. REG? from 0x93: `3B02` zeros, `3B03` zeros, `400A`
  answered on the **second** attempt (the first timed out), manual
  pair 71/73. SCAN? — the thermostat serves **18 tables** at 0x20:
  `01` DEVCONFG, `02` SYSTIME, `03` INGUI, `04` SSSBCAST, `06`
  LINESET, `2F` STARTUP, `31` INGDATA, `3B` SAMINFO, `40` SCHEDULE,
  `41` TEMP, `42` LASTTEN, `46` MISC1, `47` RESTMR, `48` HEALTH,
  `49` SYSCTRL, `4A` MISC2, `4C` SYSMETRC, `4E` CHARGING. The sweep
  did **not** complete: ~2 hours in, the log ends after `4E` — no
  DONE signal exists; the furnace and ODU were not scanned. Tables
  the device ignores answer with silence, so each costs the full
  **5 s reply timeout**, and the scan's 8-consecutive-timeout
  ABSENT rule never fired on 0x20; a full single-device pass takes
  hours.

## The open item — schedule-row edit

The one missing piece for enabling the wall's Manual activity from
the bus is the **schedule-row edit**: writing one period's bytes so
the row lands on activity 4 (manual). The row addressing follows
`4002 + N − 1` per period. The project is ready to test this and is
waiting for **the maintainer's specification of that edit** — not
for another SCAN? run.

## Unpublished follow-up draft (2026-11-01) — preserved

A follow-up comment was drafted on 2026-11-01 and never posted; its
analysis is preserved here so it is not lost. The ICP image contains
the SAM/B36 user-interface strings — "Searching for SAM/B36
module", "Searching for B36 module", "SAMINFO", "SAM RADIO TEST",
"no SAM/B36" — and equipment-summary fields "SAM model", "SAM SN",
"SAM SW version" (with NIM equivalents): **the code is present in
the image, but the commissioning step that would run it never
launches** on this unit (the model/serial screen has no SAM slot).
Two questions for the maintainer were drafted with it. This is the
firmware-side counterpart of the runtime-binding conclusion in the
SAM registration research.

## Status (2026-11-26)

Waiting on the maintainer, specifically on the schedule-row edit
above. A daily watch checks the issue for new comments or a status
change; the project does not block on it — the 400A contract is
proven and in the firmware.
