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

## The issue as filed (full text)

Title: *ICP Ion SYST0101CW (CESR131626-04.79) never registers emulated SAM — control never probes 040E/3F02, never writes 031C, never polls 0x92*

**Summary**

First field report (as far as I can tell) of InfinitESP SAM emulation against an
ICP-branded Ion System Control. Passive monitoring works perfectly on this wiring;
the SAM identity is read during the commissioning sweep; but the control never runs
any SAM registration sequence — across a cold start, a service-menu FULL
INSTALLATION, and a thermostat-only reseat it never reads the SAM's 040E/3F02,
never writes 031C to it, and never polls 0x92 in steady state. Documentary evidence
suggests the ICP Ion firmware variant may have SAM discovery removed entirely
(details at the bottom). Posting to confirm whether SAM discovery is known to be
brand-gated in the 131626 builds, and to put the captures on record either way.

**Setup**

- Wall control: ICP **Ion System Control SYST0101CW**, firmware **CESR131626-04.79**
  (same version string as the Carrier SYSTXCCITC01-B matrix entry that "responds to
  SAM and SAM emulation")
- Furnace: Heil **G80CTL1352422A** (bus 0x44), software CESR131672-04
- Outdoor unit: Heil **HVA960GKA** inverter (bus 0x53), software CESR131564-11
- No zoning, no other accessories on the bus
- InfinitESP **2026.10.19** (includes the issue #41 byte-exact 040E/0420 fix),
  `sam_address: 0x92`, ESP32 + auto-direction RS485 module
- Phase 1 (passive monitoring) on the same hardware/wiring works flawlessly —
  full telemetry in Home Assistant. This is **not** a #40-style "device not seen
  on the bus" case: the SAM demonstrably transmits to and receives from the control.

**What was tried (3 registration attempts, all captured)**

1. Whole-system power cycle with phase-2 firmware live
2. Service menu → Installation & Service → **Full Installation** (equipment wizard
   completed; correct indoor/outdoor/coil summary)
3. Thermostat-only reseat (pulled off the wall plate for ~30 s, rest of the system
   left powered) — the pattern that worked in issue #17

**Observed**

- During the power-up commissioning sweep (control acting as 0x1F), the control
  **does** read the SAM's 0104 and receives
  `SYSTEM ACCESS MODULE / InfinitESP--SAM` — the SAM is known to the bus.
- In the commissioning capture (6,543 frames; 302 from the SAM, 276 addressed to
  it) the only reads ever addressed to 0x92 are two 0104 reads. **040E reads to
  0x92: 0. 3F02 reads: 0. 031C writes to 0x92: 0.**
- Steady state: **zero polling of 0x92** (compare issue #41 post-registration:
  040E ≈ every 10 s, 030D ≈ every 23 s).
- SAM-initiated reads of 3B02/3B03 are answered by the control with **zero-filled
  tables** (31 replies, all zeros); SAM setpoint writes (func 0x0C to 3B02/3B03)
  reach the control and are ACK-shaped, but the control never changes mode or
  setpoint, and the SAM never appears in the Equipment Summary (no "Remote Access"
  line).

A control that *has* the remote-access search but rejects the SAM still shows the
search (issue #41: six 040E retries). Here there is no search traffic at all —
which points at the step not existing on this control rather than failing.

**Documentary contrast**

- The Carrier Infinity Touch installation instructions (same platform) include a
  commissioning step **"Searching for SAM Module (If Applicable)"**.
- The ICP Ion SYST0101CW installation manual (616 01 1600 01) lists the same
  commissioning sequence **without** any SAM step, and never mentions SAM / System
  Access Module / home automation anywhere; Ion "remote access" is documented
  solely as the control's built-in Wi-Fi (IonComfort.com). ICP product data lists
  no SAM accessory for the Ion line.

**Questions**

1. Has anyone ever seen an ICP / Ion (or Tempstar / Heil-branded) Touch-generation
   control emit the 040E probe — i.e., a working SAM on an ICP control?
2. Is SAM discovery known to be brand-gated in the CESR131626 builds, given the
   firmware version string is shared with Carrier?
3. If there is an alternative trigger for the search on these controls (a menu
   path not in the ICP manual), I'd happily run one more targeted test.

**Attachments**

JSONL bus captures (parsed frames):

- `coldstart-20261029-125733.jsonl` — full cold start; 0x1F sweep reads 0x92's
  0104; no 040E/031C; no steady-state 0x92 polling
- `sam-commissioning-20261029-143248.jsonl` — phase-2 firmware, equipment wizard
  run to completion; two-way 0x92 traffic, zero registration probes
- `sam-control-test-20261029-145357.jsonl` — SAM setpoint writes reach the
  control; 3B02/3B03 replies are zero-filled; control never reacts

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

A follow-up comment was drafted on 2026-11-01 and never posted;
its three data points and two questions are preserved here in
full so the analysis is not lost.

1. **The SAM machinery ships in the ICP build.** The stock image
   (the exact build running on this control) contains the strings
   "Searching for SAM/B36 module", "Searching for B36 module",
   "SAMINFO", "SAM RADIO TEST", "no SAM/B36", and the
   equipment-summary fields "SAM model", "SAM SN", "SAM SW
   version" (plus NIM equivalents). The code is present — the
   step just never engages for a SAM on this unit.
2. **The image is universal.** The Carrier-branded v4.79 package's
   image is byte-identical to the ICP one (same MD5/SHA-256; the
   packages differ only in EULA/release-notes branding), yet the
   Carrier control registers SAMs and this ICP one does not — so
   the gate cannot live in the image bytes; the decision is taken
   at runtime, from state built during commissioning. In the
   shared commissioning string table the SAM/B36 search is entry
   **#180** and the B36 search is **#181** — and #181 demonstrably
   runs on this unit while the SAM branch of #180 never engages.
3. **The screens agree.** During a reset-driven relearn the
   screen does show "Searching for B36 module" — that step
   visibly runs. On the model/serial-numbers screen the absent
   optional modules get greyed placeholders — "no zone board",
   "no B36", "no NIM" — but there is **no SAM slot at all**.

The two drafted questions: (i) during power-up discovery the
control reads the SAM's 0104 and gets a valid "SYSTEM ACCESS
MODULE" identity, but the 040E registration probe never follows —
**is the SAM branch of that search step gated on anything**:
Wi-Fi-equipped SKUs, a field in the 0104 response, the 030D
status table, the control's own commissioned-equipment
configuration? (ii) The equipment screen has a NIM slot, and a
NIM is also a remote-access module on this platform — **would
presenting as a NIM (0x80) fare any better**: does the control
run a registration handshake for NIMs that it skips for SAMs?

This is the firmware-side counterpart of the runtime-binding
conclusion in the SAM registration research.

## Status (2026-11-26)

Waiting on the maintainer, specifically on the schedule-row edit
above. A daily watch checks the issue for new comments or a status
change; the project does not block on it — the 400A contract is
proven and in the firmware.
