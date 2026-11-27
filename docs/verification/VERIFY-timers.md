# VERIFY — Protections & Timers (stage Y claims, independently re-derived)

Verification pass, 2026-11-26. Method: every claim re-derived from primary
artifacts only — decompiles in `firmware-re/stageY/out/decompY/` and
`firmware-re/stageG/out/decomp{1,2}/`, pool cells resolved raw against
`firmware-re/stageB/flat.bin` (base 0x18040000, big-endian), the two factory
manuals fetched fresh (G80CTL Series B install/service, shareddocs
FG80CTL2-02SI.pdf; HVA9 service manual 421 08 5600 02, tradeservice PDF),
and the capture corpus in `traces/` re-measured directly. Report prose of
stage Y / stage G was used only to locate artifacts, never as evidence.

**Headline: no claim REFUTED.** Two purpose *labels* could not be
independently re-derived (CF4A "statistics snapshot", CF45 "housekeeping")
— their values are code-confirmed; the labels rest on stage Y/G's consumer
analysis, which is outside the decompiled set re-read here.

---

## Claim 1 — Engine timer mechanism; fde2 arms, fec0 is ack/stop (not "get")

**CONFIRMED** (stage Y right, stage G's "get" label wrong).

- Pool resolution (raw, this pass): `DAT_1809fea0` and `DAT_180a0170` in both
  primitives → **0xFFF84C74** (timer table base); count cell 0x3C12A5E0;
  two list-head bytes 0x3C12A5E1/0x3C12A5E2 (selected by record byte [+8]).
- Record stride is **0xC = 12 bytes** in all three primitives
  (`param_1 * 0xc` throughout `decomp_1809fde2.c`, `decomp_1809fec0.c`,
  `decomp_180a006e.c`).
- `FUN_1809fde2(id, value, flag)` **arms**: unlinks the record
  (FUN_180a017c), writes [+6]=value, [+4]=value, [+9]=1 (active),
  [+10]=flag, then inserts via FUN_180a006e.
- `FUN_180a006e` is a **sorted delta-list insertion**: it walks the list via
  the next-pointer at record [+0xB], subtracting each node's delta [+4]
  from the new value until the insertion point, links in, and decrements
  the successor's delta. `FUN_180a017c` is the matching removal (splices
  out, adds the removed delta back to the successor).
- `FUN_1809fec0(id)` **stops/clears**: writes [+9]=0 (inactive), unlinks,
  writes [+4]=0, returns only a success bool. A getter does not mutate
  state; fec0 is a cancel, used by handlers as the expiry-ack. Stage G's
  "get" characterisation is refuted by the body.

## Claim 2 — The ten sys_ctrl timers

Timer IDs are byte cells in the decision block: CF44=0xFFF8CF44 …
CF4A=0xFFF8CF4A (pool-verified). Registration is `FUN_1809fa76(cell,1,flag,cb)`
in FUN_181f8340 / FUN_181f86ae; expiry callbacks post classes via
FUN_181f7694 (each callback body read this pass):

| Timer | Callback → class | Arming site (code read this pass) | Value |
|---|---|---|---|
| CF44 | FUN_181f7500 → class 0 | FUN_181f86ae: register + `fde2(*CF44, 1, 1)` at init | **1** |
| CF45 | FUN_181f7550 → class 4 | FUN_181f8340 tail: `fde2(*CF45, 10, 1)` | **10** |
| CF46 | FUN_181f7680 → class 12 | FUN_181f8568(v) wrapper; called in FUN_181f86cc state 6 with **0x78** and **0x50** | **{80, 120}** |
| CF47 | FUN_181f7564 → class 5 | FUN_181f862a (self re-arm, formula below) | **30–60** |
| CF48 | FUN_181f7578 → class 6 | FUN_181f8340 tail: `fde2(*CF48, 0x1E, 0)`; FUN_181f85c0: `fde2(*CF48, 0x2D, 0)` | **30, then 45** |
| CF49 | FUN_181f758c → class 7 | FUN_181f8592 tail: `fde2(*CF49, 0xF, 0)` | **15** |
| CF4A | FUN_181f75a0 → class 8 | FUN_181f8340 tail: `fde2(*CF4A, 300, 1)` | **300** |

- **Supercycle CF48⇄CF49 — CONFIRMED.** Class-6 handler FUN_181f8592:
  `fec0(*CF48)` → FUN_181f5d08 (ingestion) → **FUN_181efdfc (the refresh)**
  → FUN_181f7050 → FUN_1815dcee → FUN_181f4e60 (mirror) → `fde2(*CF49,15,0)`.
  Class-7 handler FUN_181f85c0: `fec0(*CF49)` → FUN_181f015a →
  `fde2(*CF48,45,0)` → FUN_181f69bc. Steady cycle 45+15 = **60 units**;
  first CF48 interval is 30 (init arm in FUN_181f8340).
- **CF47 formula — CONFIRMED.** FUN_181f862a acks CF47, reads a 7-byte
  clock structure, computes (compiler modulo-60 idiom)
  `v = 60 − (seconds mod 60)`, then `if (v < 0x1E) v = 0x1E`, and re-arms
  `fde2(*CF47, v, 0)` — i.e. clamp(60 − (sec mod 60), min 30) ∈ [30, 60],
  a minute-boundary tick.
- **Unit = seconds — CONFIRMED.** The CF47 computation only makes sense
  if the timer unit is the same unit as the clock's seconds field:
  60 − (sec mod 60) with a 30 floor. Corroborated by the 45+15 = 60
  supervision supercycle.
- **CF46 purpose (state-sequence timeout) — CONFIRMED functionally.**
  CF46 is armed (80 or 120) inside FUN_181f86cc's state-6 handler exactly
  when the machine enters sequence states 7/9, and its expiry posts
  class 12, which those same states consume (state 7: `param_1 == 0xC`
  branch; state 9 likewise). It times the sequence states, nothing else.
- **CF44 = 1 "boot kick" — value CONFIRMED; label consistent** (registered
  and armed with 1 in the init-adjacent FUN_181f86ae, called from
  0x181F86BA/86C6 immediately before the state machine FUN_181f86cc).
- **CF45 = 10 — value CONFIRMED; "housekeeping" label UNVERIFIABLE** from
  the artifacts re-read here (class-4 consumer not in the decompiled set).
- **CF4A = 300 — value CONFIRMED; "statistics snapshot" purpose
  UNVERIFIABLE** from the artifacts re-read here (class-8 consumer not in
  the decompiled set; neither confirmed nor contradicted).
- **Subsystem 0x1816B/C timers 120/180/300 — values CONFIRMED.**
  FUN_1816bf7e registers three timers (ID cells 0xFFF8B508/B509/B50A) on
  the same engine primitives (arm wrappers FUN_1816c198/1ac/218 → fde2;
  ack wrappers FUN_1816c064/72/80 → fec0, pool-verified) and arms them
  **300 / 0x78=120 / 0xB4=180**. Purpose "equipment discovery supervision"
  is consistent with the subsystem's code (FUN_1816c0d6 gates on equipment
  class-word bits 0x7C00/0x20 and device-found flags; FUN_1816bf24 ANDs
  three discovery checks) — CONFIRMED as characterised by stages G/Y.
- **"None is a control or comm watchdog" — CONFIRMED** within the
  decompiled corpus: all seven sys_ctrl callbacks only post classes
  (0,4,5,6,7,8,12) into the supervision machine; every arming site is an
  init function or a state handler — no timer is armed or acked by bus/RX
  activity, and no callback touches bus, fault, staging or demand cells.
  CF46 is an internal sequence timeout, not a comm watchdog (it is armed
  on state entry, not refreshed by message arrival).

## Claim 3 — No compressor min-off / min-run / staging timers in the thermostat

**CONFIRMED** (bounded to the decompiled corpus). Census this pass:
`grep` for the timer primitives and the timer table (1809fde2 / 1809fec0 /
0xFFF84C74) across the stage E, O and S decompile outputs — **zero hits**
outside user-lists. The staging machine FUN_180c54d8 and the demand writer
FUN_180c62fc contain no timer references (consistent with stage E's
pure-hysteresis finding: thresholds ×1.25 / ×0.25 / ×0.01, no time terms).
No timer callback writes a staging or demand cell (callback bodies above).
Compressor protection timing therefore cannot live in the thermostat's
control path; it matches the manuals (claim 5: the ODU board owns the
3.5-min anti-short-cycle).

## Claim 4 — Furnace G80CTL (Series B manual, Sequence of Operation)

**CONFIRMED — every value verbatim** (FG80CTL2-02SI.pdf, fetched fresh):

- Prepurge **15 s**: "begins a 15-second prepurge period" (both low- and
  high-heat paths).
- HSI warm-up **17 s**: "the Hot-Surface Igniter HSI is energized for a
  17-second igniter warm-up period."
- Flame proving **2 s**: "Five seconds after the GVR closes, a 2-second
  flame proving period begins"; not proved within two seconds → valve
  closes.
- Trials: initial trial + "up to three more Trials-For-Ignition" (= **4
  total**) → Ignition-Lockout; "Lockout will be reset automatically after
  **three hours**."
- Draft safeguard: "Should switch remain open longer than **3 minutes**,
  furnace control board will lockout the furnace for **3 hours**."
- Blower-ON delay: **Low-Heat 45 s / High-Heat 25 s** after GV-M opens.
- Blower-OFF (heat): "**90, 120, 150, or 180 seconds** … factory-set for a
  **120-second** Heat-OFF delay."
- Power restore: "the control will start a **90-second blower-only ON
  period** two seconds after power is restored, if the thermostat is still
  calling for gas heating" (corroborated in the safety-check section:
  "Blower will run for 90 seconds before beginning the call for heat
  again").

Caveat carried from stage Y and unchanged: the installation's furnace is
suffix **A2**; the quoted text is the Series B manual (the A-vs-B suffix
question is bibliographic, not settled publicly). The values above are
the Series B text exactly as claimed.

## Claim 5 — ODU HVA9 (Service Manual 421 08 5600 02)

**CONFIRMED — every value verbatim** (manual fetched fresh):

- Anti-short-cycle **3.5 min**: "3.5 minute time delay after last cycle,
  initial power up, return from brown-out condition" (Time Delays).
- PEV equalisation **150 s + 15 s**: "At the end of every compressor ON
  cycle, there will be 150 seconds of PEV open period for pressure
  equalization followed by 15 seconds of PEV Off period before the next
  compressor ON cycle. This delay cannot be bypassed."
- Sump warm-up **10 min**: "10 minute sump warm-up delay … at the
  beginning of each high voltage power up."
- Brownout: "If the line voltage is **less than 187V for at least
  4 seconds**, the Compressor and OD fan goes to 0 rpm" (restart at
  ≥190 V).
- HPS: switch "open **600+/−5 psig**, close 470+/−10 psig"; on trip,
  "**After a 6 minute delay**, if there is a call … PEV opens for
  150 seconds … Compressor and fan will then ramp to the **next lower
  stage** of operation."
- LPS (suction transducer): resume only "after the **15 minute delay**"
  with pressure recovered; "three (3) consecutive trips … the low
  pressure switch will **lock out operation for 4 hours**."
  *Footnote:* Table 10 lists fault code 32 (low-pressure trip) with a
  "6 Minutes" reset-time entry while the Low Pressure Protection body
  text specifies the 15-minute resume delay. The claim follows the body
  text; the table entry appears to be a display/fault-reset quantity.
  Flagged as an internal inconsistency of the manual, not of the claim.
- Standby ≈2 min: "Two minute time delay to return to standby operation
  from last valid communication" (Amber Status Light section);
  corroborated by the COMM-light rule: "If no communication is received
  within 2 minutes, the LED will be turned OFF."

## Claim 6 — Burst cadence median 10.00 s, not event-driven

**CONFIRMED** (re-measured this pass). All 0305 writes (src 0x20,
func 0x0C) in every `traces/*.jsonl`; steady-state gaps (5–20 s) pooled:
**n = 631 gaps, median 10.02 s, mean 10.07 s**, 520/631 gaps round to
exactly 10 s. Per-file medians: coldstart 10.001, phase3-validation2
10.006, 400a-test files 10.05–10.07. The 400A test captures contain
mid-call setpoint writes from the SAM side, yet the 0305 cadence stays
locked at ~10 s — the burst is a fixed engine cadence, not event-driven.
(The claim's "10.00" vs the pooled 10.02 is within capture timestamp
jitter; the largest file, coldstart, medians exactly 10.001.)

## Claim 7 — Smart Recovery 90 min; defrost AUTO; freeze protection

- **Smart Recovery 90 min — CONFIRMED as a fixed help-text value.**
  Installer help text in the image @0x182D9EE0: "System will start
  recovery **90 minutes** prior to schedule change in both heating and
  cooling modes." The text states the number flatly, with no parameter;
  stage Y's descriptor-path search for a backing default was a documented
  negative (not re-run here).
- **Defrost interval AUTO — CONFIRMED, including "default".** Thermostat
  help @0x182D89B0: "Heat Pump Defrost Interval Selection … Auto means
  the defrost interval is optimized." The HVA9 manual independently
  states the selection set "30, 60 and 90 minutes, or AUTO. **The default
  is AUTO**." (Platform-only for this install — the HVA9A is cooling-only.)
- **Freeze protection — CONFIRMED.** The dictionary token `freezelimit`
  exists only inside the GeoHP/hydronic property clusters (@0x18302804
  and @0x1830613C), neighboured by `hydronicoffdelay`, `hydronicafl`,
  `lpumppowersetting` (loop-pump power), `flowratesetting` — geothermal
  vocabulary. The remaining "freeze" strings in the image are
  equipment-side texts ("freeze sensor", "freeze lockout fault" — coil
  freeze protection on the ODU side). There is **no** thermostat freeze
  limit for the air system / this installation's control loop; a house
  freeze guard in an emulator is the emulator's own design decision,
  not inherited Ion behaviour.

---

## Verdict summary

| # | Claim | Verdict |
|---|---|---|
| 1 | Timer table 0xFFF84C74, 12-B records, sorted delta-list; fde2 arms, fec0 ack/stop (Y over G) | **CONFIRMED** |
| 2 | Ten timers: values, supercycle 45+15 (init 30), CF47 formula, CF46 {80,120}, subsystem 120/180/300, unit = s, none a control/comm watchdog | **CONFIRMED** (CF4A/CF45 purpose *labels* UNVERIFIABLE here; values confirmed) |
| 3 | No compressor min-off/min-run/staging timers in the thermostat | **CONFIRMED** (corpus-bounded census) |
| 4 | G80CTL manual values (15/17/2 s, 4 trials → 3 h, draft >3 min → 3 h, 45/25 s, 90/120/150/180 def. 120, 90 s power-restore) | **CONFIRMED** (Series B text; A2-suffix caveat stands) |
| 5 | HVA9 manual values (3.5 min, 150+15 s, 10 min, <187 V ≥4 s, HPS 600 → 6 min + step down, LPS 15 min / 3 trips → 4 h, standby ~2 min) | **CONFIRMED** (Table-10 vs body-text footnote on LPS reset) |
| 6 | Burst cadence median 10.00 s, not event-driven | **CONFIRMED** (pooled median 10.02 s, n=631) |
| 7 | Smart Recovery 90 min fixed help text; defrost AUTO (default); no thermostat freeze limit outside GeoHP | **CONFIRMED** |
