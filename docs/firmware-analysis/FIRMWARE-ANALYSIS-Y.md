# FIRMWARE-ANALYSIS-Y.md — ICP Ion BINF0479, RE stage Y: protections, timers, delays — full inventory with owners

Date: 2026-11-26. Desk work on files and published service literature only;
nothing was flashed or written to any device. Continues stages E and G
(this stage re-opens G's sys_ctrl timer question with the engine timer
primitives decompiled, and corrects one stage-G naming error — §2.3).

Labels: **[FACT]** = measured/decompiled/read directly this pass, with
the source named. **[INF]** = inference, reasoning shown. **UNPROVEN** =
searched, not found; the search space is stated. Every item in the two
final lists (§8, §9) carries its owner and its evidence status.

**Mission:** inventory ALL protections, timers and delays the
replacement (emulator) thermostat must implement, and assign each to
its owner — thermostat vs furnace board vs ODU board — for one specific
installation: 2-stage gas furnace Heil G80CTL1352422A2 (board soft
CESR*******), variable-speed AC Heil HVA960GKA201 (inverter board
HR46WR003, soft CESR*******), coil EN(A,D)4X61, single zone, no heat
pump, no separate aux heat, no zoning.

---

## 0. Headline results

1. **The sys_ctrl mystery values are engine countdown timers, and none
   of them is an equipment-control timer [FACT + INF].** This pass
   decompiled the engine timer primitives themselves (§2):
   `FUN_1809fa76` (register), `FUN_1809fde2` (arm: countdown := period
   := value, armed flag set, entry inserted into a sorted **delta
   list** by `FUN_180a006e`), `FUN_1809fec0` (acknowledge/stop),
   `FUN_1809fd7e` (status query). The seven sys_ctrl properties
   CF44–CF4A and the three timers of the 0x1816B/C subsystem are all
   entries in this one mechanism (table @ RAM `0xFFF84C74`, 12-byte
   entries, ≤ 0x46 entries). Their values (1, 10, 15, 30→45, 30–60,
   80/120, 120, 180, 300) time the **supervision state machine's own
   evaluation cadence, a wall-clock minute-boundary tick, a 300-unit
   statistics snapshot, and a discovery/identification sequence** —
   §3 gives the per-timer verdicts. No path from any of them to
   demand, staging, or an equipment output exists; the classes they
   post run evaluation/housekeeping actions only (stage G §4 map,
   re-verified where load-bearing).
2. **Units are seconds [INF, strong].** CF47's period is *computed*
   from the RTC as `clamp(60 − (seconds mod 60), 30, 60)` — seconds
   to the next minute boundary (§3.4). That arithmetic is meaningless
   in any other unit. Corroboration: CF4A = 300 → a 5-minute statistics
   period; CF48+CF49 = 45+15 = 60 → a 1-minute supervision supercycle;
   the dispatcher loop itself ticks at 1000 ms (stage G §1). The
   engine's tick function itself was not isolated, so this remains
   inference — but it is the only self-consistent reading.
3. **No thermostat-side compressor min-off, min-run, or staging timer
   exists in the isolated control code [FACT, negative — same space
   as stage E §12.8, now extended to the sys_ctrl timer system].**
   The staging machine is pure demand hysteresis (×1.25 / ×0.25 /
   ×0.01, stage E §3). Compressor short-cycle protection is owned by
   the **ODU board: 3.5 minutes** (HVA9 manual, §6.2) — the thermostat
   does not duplicate it. The wall control even has UI strings
   "Please wait for the Air Conditioner / Heat Pump / Furnace to
   restart" (`0x182CD2A8–0x182CD334`) — it *displays* equipment-side
   restart waits; it does not impose them.
4. **Thermostat-side defaults actually recoverable are few** (§4, §5):
   Smart Recovery start = **90 min** before a schedule change (help
   text, fixed — not learned); defrost interval default **AUTO**
   (30/60/90/AUTO selectable, HP only); defrost fan delay **≈12 s**
   (HP only); HP low-airflow multipliers **0.63 / 0.8** (non-
   communicating 2-stage ODU only). The descriptor-default route
   (task item 1) was executed in full and is a **documented negative**
   for named settings: the descriptor table's defaults cover the
   field store as coarse equipment *records*, not per-setting values
   (§5). Lockout/latch/deadband/stage-limit **defaults remain
   UNPROVEN** — the settings exist (dictionary + installer screens),
   their consumers and stored defaults sit behind the same runtime
   registration wall as stages E/I/J.
5. **The boards carry the entire safety chain** (§6): ignition
   trial/flame/limit/pressure supervision with a 3-hour ignition
   lockout (furnace), and pressure/brown-out/inverter-temperature
   protection with staged derating and lockouts (ODU). Two board
   behaviours directly size the emulator's design: the **ODU returns
   to standby 2 minutes after the last valid communication**, and the
   **furnace blower coasts 90–180 s after a heat call ends**
   (capture-confirmed, §7).

---

## 1. Sources and method

- Stage E (`FIRMWARE-ANALYSIS-E.md`): decision module, dictionary
  inventory (§9.2), installer help texts (§9.3), the no-timers
  negative (§12.8).
- Stage G (`FIRMWARE-ANALYSIS-G.md`): dispatcher, post stubs,
  supervision FSM, registration sites — used as the map; this pass
  re-decompiled the timer primitives and the 0x1816B/C cluster in a
  fresh project copy (`firmware-re/stageY/proj/`, from stage G's).
- Stage H dictionary inventory (`firmware-re/stageH/out/
  dictionary_names.txt`, `all_strings.tsv`) — re-mined this pass for
  every protection/timer/limit name (§4.1) and for the full installer
  help-text region `0x182D8800–0x182DA700` plus the lockout/blower
  texts at `0x182DE214–0x182DE390` (`stageY/out/help_region.txt`,
  `help_keyword.txt`).
- Descriptor table (stage F dump, 860 entries) × binding directory
  (stage D dump, 385 records) cross-reference with default-pointer
  dereference into the flat image — §5, data in
  `stageY/out/desc_defaults.txt`.
- Algorithms research report (2026-11-26) — industry context and the
  UL 60730 Class A/B framing (§8 note).
- Service literature (fetched this pass, 2026-11-26):
  - **F80CTL & G80CTL (Series B) Installation, Start-Up, Operating
    and Service Instructions** (ICP, shareddocs FG80CTL2-02SI.pdf) —
    Sequence of Operation (p. 46), safety-control checks, status
    codes. Our furnace is G80CTL1352422**A2**; whether the A2 suffix
    is Series A or B is not publicly settled (part-numbers sweep) —
    the safety sequence quoted here is the Series B text; the Series A
    predecessor manual is the fallback and was not separately mined.
  - **CVH8/HVH8/TVH8/VA9/HVA9/TVA9 Application Guideline & Service
    Manual 421 08 5600 02** — Time Delays, Communication and Status
    Lights, High/Low Pressure Protection, Brown-Out Protection,
    Fault Code Table 10. Model-number decode in the same manual:
    position 3 **A = Air Conditioner**, H = Heat Pump — our HVA9**A**
    is cooling-only, so every defrost/HP item below is platform-only
    for this install.
- Captures: `THERMOSTAT-PROTOCOL-MAP.md` (burst cadence, rundown) and
  `400A-TEST-RESULT.md` (timed write→demand sequence) — §7.

---

## 2. The engine timer mechanism (new this pass)

### 2.1 The three primitives [FACT]

Decompiled in `stageY/out/decompY/`; pool cells resolved raw against
`firmware-re/stageH/flat.bin`.

**`FUN_1809fa76(idSlot, flagA, flagC, callback)` — register.** Allocates
the next free entry in a table at RAM **`0xFFF84C74`** (count byte in
dictionary space `0x3C12A5E0`, capacity `0x46` = 70 entries). Entry
layout (12 bytes, stride `0xC`):

| off | content |
|---|---|
| +0x0 | callback function pointer |
| +0x4 | countdown / delta (u16) |
| +0x6 | period (u16) |
| +0x8 | flagA (registration param 2) |
| +0x9 | armed/active flag |
| +0xA | flagC (registration param 3; overwritten by arm) |
| +0xB | delta-list next index (written by `FUN_180a006e`) |

The assigned id (entry index) is stored back through `idSlot`.

**`FUN_1809fde2(id, value, flagC)` — arm.** Detaches the entry
(`FUN_180a017c`), writes **countdown (+4) := value** and
**period (+6) := value**, sets **armed (+9) := 1**, flagC (+0xA), then
**inserts the entry into a sorted delta list** (`FUN_180a006e` — it
subtracts predecessors' deltas and links via +0xB: a textbook software
timer delta queue).

**`FUN_1809fec0(id)` — acknowledge/stop.** Clears armed (+9) := 0,
detaches from the delta list, zeroes the delta (+4) := 0.

**`FUN_1809fd7e(id)` — status query** (used by the 0x1816B/C checks,
§3.6; identified by pool resolution `PTR_FUN_1816c208 →
0x1809FD7E`, body not decompiled — role from call pattern only).

### 2.2 What this proves

The sys_ctrl "properties" CF44–CF4A of stage G are **ids in this
timer table**, and the state machine's "reprogramming" actions are
arm/acknowledge operations on countdown entries whose expiry invokes
the registered callback — a post stub that enqueues the associated
message class into `sys_ctrl_task`. Stage G's structural reading
(values behave as periods) is therefore upgraded: they **are**
countdown periods in a delta-list timer service. The engine-side tick
that decrements the head of the delta list was not isolated (the
fourth pool user of the table base, in `FUN_180a0212`, is an engine
registration call, not the tick) — the expiry path is proven by the
arm/ack symmetry of every consumer (§3), not by the tick's code.

### 2.3 Correction to stage G

Stage G named `FUN_1809fec0` "get a property value". It returns no
value; operationally it is the **acknowledge/stop** above. Every
sys_ctrl action begins by acknowledging its own timer
(`FUN_181f8592` acks CF48, `FUN_181f85c0` acks CF49, `FUN_181f862a`
acks CF47, the teardown `FUN_181f85e2` acks CF48+CF49) — the pattern
is "my timer fired; clear it, run, arm the next one". Stage G §5's
registration census and values are unaffected.

### 2.4 The flagC (+0xA) values

At registration and at arm time, CF45 and CF4A are always given
flagC = 1; CF46/CF47/CF48/CF49 always flagC = 0; CF44 flagC = 1.
[INF] flagC = 1 marks the two entries that are never re-armed by a
handler (CF45 = 10, CF4A = 300) — consistent with **auto-reload /
periodic** semantics in the engine, versus one-shot entries the FSM
re-arms manually. Not proven; no verdict below depends on it.

---

## 3. The sys_ctrl timers — per-timer verdicts

Slots are RAM id bytes `0xFFF8CF44–0xFFF8CF4A` (stage G §5, pool-
verified this pass: `DAT_181f8790 → 0xFFF8CF48`, `DAT_181f87A4 →
0xFFF8CF49`, `DAT_181f8784 → 0xFFF8CF46`, `DAT_181f87C0 →
0xFFF8CF47`). "Class" = the sys_ctrl message class the entry's post
stub enqueues on expiry (stage G §3 stub map). FSM behaviour per
class/state is stage G §4.

### 3.1 CF44 → class 0 — armed once at task init with value **1**

`FUN_181f86ae` registers it (flagC 1) and arms it := 1. Class 0 has no
branch anywhere in the supervision FSM. [INF] A one-unit boot/
kickstart tick for the supervision object. **Not a control timer.**

### 3.2 CF45 → class 4 — **10**, flagC 1 (periodic-looking)

Armed once in the state-1 registration sequence (`FUN_181f8340`);
never re-armed, never acknowledged. Class 4 has no FSM branch — the
message runs only the FSM entry actions (records the class into
`0xFFF8CF4B`, accumulates a byte via `FUN_181f7c2c`). [INF] A 10-unit
periodic supervision housekeeping tick. **Not a control timer.**

### 3.3 CF48 ⇄ CF49 → classes 6 / 7 — the evaluation cadence pair

- CF48 (class 6): armed := **30** at registration; re-armed := **45**
  by the class-7 action `FUN_181f85c0`.
- CF49 (class 7): armed := **15** by the class-6 action
  `FUN_181f8592`.
- Class 6 in state 2 (the hub) runs `FUN_181f8592`: acknowledge CF48 →
  ingest dispatcher `FUN_181f5d08` → **decision-module refresh
  `FUN_181efdfc`** (stage E's module: quantizer, staging machine,
  arbitration) → elapsed-time/rate evaluator `FUN_181f7050` →
  `FUN_1815dcee` → block mirror `FUN_181f4e60` → arm CF49 := 15.
- Class 7 in state 2 runs `FUN_181f85c0`: acknowledge CF49 → small
  evaluator `FUN_181f015a` → arm CF48 := 45 → `FUN_181f69bc`.

**Verdict [FACT for the actions, INF for the unit]:** this pair is
the supervision object's periodic **re-evaluation cadence** — a
15 + 45 = 60-unit supercycle that re-runs the binding refresh and the
rate evaluator even when nothing changed. It is the closest thing in
the firmware to a "control loop period", and it is a *refresh*
cadence, not a protection: nothing in either action enforces a
minimum on/off, a staging delay, or a lockout. The actual bus output
keeps its own ~10 s rhythm (§7) through the engine's per-object
timers (stage N), and the refresh additionally fires on input
changes (binding semantics, stage E §8).

### 3.4 CF47 → class 5 — **30–60, computed from the RTC**

Provider `FUN_181f862a` (one of the sys_ctrl module-descriptor
providers, stage G §2) — re-decompiled and pool-verified this pass
(`stageY/out/decompY/`, stage G `out/decomp1/decomp_181f862a.c`):
acknowledge CF47 → copy the 7-byte RTC-mirror block at `0xFFF8207A` →
`x = block[0]` → `value = 60 − (x mod 60)`, clamped up to a minimum of
30 → arm CF47 := value. Byte 0 of an RTC-shaped block, combined with
the `60 − (x mod 60)` form, is **seconds within the minute** [INF,
strong]: CF47 fires at the next minute boundary, never sooner than
30 units out. Class 5 has no FSM branch. **Verdict: a wall-clock
minute-boundary housekeeping tick** (schedule/clock evaluation
territory). **Not a control timer** — and the single strongest piece
of evidence that the timer unit is the second (§0.2).

### 3.5 CF46 → class 12 — **80 or 120**, the states 6–9 sequence timer

Armed only by the FSM state-6 action `FUN_181f8568(value)` with
**120** (`0x78`) if a device-type condition holds, else **80**
(`0x50`) (stage G §4). Class 12 in state 7 runs the 0x1816B/C
completion action `FUN_1816c03e` (§3.6) and moves to state 8; class
12 in state 9 exits to the hub (state 2). **Verdict: a timeout for
the supervision sequence of §3.6** (device-type-dependent duration),
not an equipment timer.

### 3.6 The 0x1816B/C subsystem's own three timers — **120 / 180 / 300**

Decompiled this pass (`stageY/out/decompY/`). At FSM state 1,
`FUN_1816bf7e` zeroes four mirror bytes (`0xFFF8B50B–B50E` region),
registers **three** timer entries (id slots `0xFFF8B508/B509/B50A`)
whose callbacks are the post stubs for **classes 10, 13, 11**
(pool-resolved: `0x181F75B4`, `0x181F75DC`, `0x181F766C` — stage G §3
map), and arms them:

| slot | arm wrapper | value |
|---|---|---|
| `0xFFF8B508` (class 10) | `FUN_1816c198(v)` | **120** (`0x78`) |
| `0xFFF8B509` (class 11) | `FUN_1816c1ac(v)` | **180** (`0xB4`) |
| `0xFFF8B50A` (class 13) | `FUN_1816c218(v)` | **300** |

It then acknowledges the first two entries (`FUN_1816c064`,
`FUN_1816c072` = `FUN_1809fec0` on B508/B509) — the net armed state
after state 1 therefore depends on the unisolated tick/ack interplay
and is **not claimed**; what is proven is that this subsystem owns
exactly three countdowns of 120/180/300 and manipulates them at
(re)registration. Further behaviour:

- `FUN_1816bfe2` (also state 1) reads field-store **field 1** (the
  equipment type word) and **field 3** via the stage-C getter and
  calls `FUN_1816c0d6(field1, field3)`: if the FSM state byte
  `0x3C12EC68` == 9 and type-word conditions hold (bit `0x20` set,
  class ≠ `0x800`), it **re-arms the 120 timer** (`FUN_1816c198(0x78)`).
- `FUN_1816c03e` (state 7, on class 12): acknowledges the 300 timer
  (`FUN_1816c080`), sets mirror byte `0xFFF83E84 := 1` under
  dictionary brackets, touches object `0xFFF83E88` (`FUN_180bc47a`).
- State 8's stay-predicate `FUN_1816bf24` returns "done" iff three
  status queries (`FUN_1809fd7e` on each of B508/B509/B50A, via
  `FUN_1816c08e/c0a6/c0be`) are all non-zero — state 8 waits on this
  subsystem's three timers/flags.
- The subsystem coordinates with dictionary object `0x3C0D8EFC`
  (FSM predicate PB, stage G §4) and with field-store identity
  fields 1 and 3.

**Identity [INF]:** a device **discovery / identification
supervision sequence** — it is (re)registered in the FSM's
registration state, is driven by equipment identity words, runs on
80–300 s timescales through the "active" FSM states 6–9 (stage G
§4: exit action sets an "active" flag for states 6–9), and its
completion is a mirror byte + an object operation, not an equipment
command. The alternative readings (SAM supervision, zoning-board
supervision) cannot be excluded from static evidence; the load-
bearing fact does not depend on the name: **these are supervision-
sequence timers. None of them gates, delays, or limits any heating
or cooling output.**

### 3.7 CF4A → class 8 — **300**, flagC 1: statistics snapshot

Class 8 never reaches the FSM: the post API `FUN_181f7694` intercepts
it and performs a **snapshot + reset of the dispatcher's per-class
execution-time statistics** (stage G §3). CF4A is armed := 300 once
at registration and, with flagC 1, is the periodic-looking one.
**Verdict [FACT]: telemetry housekeeping — a 300-unit (5-minute)
statistics snapshot. Definitively not a control timer.**

### 3.8 Overall verdict for task item (2)

Of the ten countdowns examined (CF44–CF4A + the three of §3.6):
**zero are equipment-control timers, zero are communication
watchdogs in the equipment sense, and zero are UI timers.** They are
the wall control's internal supervision machinery: evaluation
cadence (15/45), minute-boundary clock tick (30–60), statistics
(300), boot/housekeeping ticks (1, 10), and a discovery-sequence
timeout set (80/120, 120/180/300). The one comm-watchdog-flavoured
behaviour in the whole system is **board-side** (ODU standby after
2 min of bus silence, §6.2) — it is not implemented by these timers.

Adjacent machinery, for completeness: `FUN_181f7050` (invoked from
the class-6 action) is an 8-channel **elapsed-time / rate**
evaluator over per-zone arrays (stage G §4) — it *measures* runtimes
and rates; no evidence it *enforces* any limit, and its published
arrays' consumers are engine-side and unisolated [FACT for the
measurement, UNPROVEN for any enforcement].

---

## 4. Thermostat-side inventory (firmware dictionary + help texts)

### 4.1 Dictionary names with protection/timer/limit semantics [FACT — names exist]

From the stage H inventory (addresses in `stageY/out/` extracts;
full list stage E §9.2). Grouped:

- **Lockouts:** `idu/auxheatlocktmp`; `odu/coollocktemp`,
  `odu/heatlocktemp`; bare `coollocktemp`, `heatlocktemp`;
  `lockoutcount`, `lockoutactive`, `lockouttime`, `lockactive`;
  `freezelimit`; `system/odtmpoff` (OD-temp offset, name only).
- **Latches:** `odu/coollatchmode`, `odu/coollatchtemp`,
  `odu/heatlatchmode`, `odu/heatlatchtemp`, `odu/usercoollatch`,
  `odu/userheatlatch`; bare `coollatchtemp`, `heatlatchtemp`,
  `userheatlatch`.
- **Defrost:** `odu/defrostbackup`; bare `defrostbackup`,
  `defrostInt`.
- **Stage limits:** `odu/usermincoolstage`, `odu/usermaxcoolstage`,
  `odu/userminheatstage`, `odu/usermaxheatstage`; bare
  `mincoolstage`, `maxcoolstage`, `minheatstage`, `maxheatstage`,
  `opminheatstage`, `opmaxheatstage`, `opmincoolstage`,
  `opmaxcoolstage`, `idu/furnstages`, `idustages`.
- **Delays (wall-set, equipment-executed):** `idu/heatoffdelay`;
  bare `heatoffdelay`, `hydronicondelay`, `hydronicoffdelay`.
- **CFM limits:** `idu/mincfm`, `idu/maxcfm`, `idu/mincfmenable`,
  `idu/maxcfmenable`; `absmincfm`, `absmaxcfm`, `calcMinCFM`,
  `cfmlimit`, `cfmlimitsvalid`, `vcapfloorcfm`, `vcapceilingcfm`,
  `vcapcfmfloor`, `vcapcfmceiling`, `vcapcfmuplimit`, `maxrpm`.
- **Recovery / scheduling:** `system/cfgrecovery`; bare `recovery`.
- **Setpoint / profile limits:** `highTempThreshold`,
  `lowTempThreshold`, `highHumThreshold`, `lowHumThreshold`
  (alert-threshold shaped); `system/vacat/vacmint`,
  `system/vacat/vacmaxt` (vacation bounds).
- **Window protection (humidity):** `system/windowprotect/enabled`,
  `system/windowprotect/rhtg`, `system/windowprotect/ventprotect`;
  help text: window protection "may override" humidification to
  prevent window condensation (`0x182DE468`, `0x182DE020`).
- **Static-pressure monitoring:** `system/statpressmon`.
- **Occupancy timing:** `system/occSustainTime` (name only).
- **Demand response:** `system/utilityEvent/priceLimit`,
  `priceOffset`, `minLimit`, `maxLimit`; `totalDemandReductionPercent`,
  `totalPowerReductionPercent`; bare `dissipation`, `Precond`.
  (Versions stage: the whole `system/utilityEvent/demand*` group was
  **removed in 4.79** — the demand-response subsystem was reworked in
  this build; the §4.3 trim code below is what remains isolated.)
- **Runtime accumulators (telemetry, not limits):** `hpRuntime`,
  `dailyCoolRuntime`, `gfRuntime`, `powercycles`, `lowheatcycles`,
  `medheatcycles`, `highheatcycles`, `blowercycles`, `onhours`,
  `*coolcycles`, `defrostcycles`, `defrosthours`, `lockoutcount`.

### 4.2 Help-text semantics [FACT — texts at the cited addresses]

- **Cooling lockout** (`0x182D88E8`): "Cooling operation is not
  allowed below the lockout temperature. Select NONE to disable
  cooling lockout and make low ambient cooling function available."
- **Heat-source lockouts need valid OAT** (`0x182DE214`): "Adjust the
  desired lockout temperatures for the heat sources shown. **The
  system must read a valid OAT for a heat source lockout to occur.**"
  → lockouts are gated on a valid outdoor-temperature reading; on
  OAT loss they do not engage. (And the wall *displays* the state:
  "'lockout' text indicates operation is lockout due to OAT is
  outside of…", `0x182E0F84`.)
- **Latches** (`0x182D8CB4`, `0x182D8D20`): cool latch — "Above this
  temperature, only high stage operation is allowed"; heat latch —
  "Below this outdoor temperature, only high stage operation is
  allowed"; an `ALWAYS` option makes high stage the only stage.
- **Stage limits with latch option** (`0x182D90A8–0x182D91F4`):
  installer-set min/max stage per mode; for the minimum stage, an
  outdoor temperature at which the limit is enforced, or "always".
- **Defrost interval** (`0x182D89B0`): "Set the time interval between
  defrost cycles. Auto means the defrost interval is optimized by
  the outdoor control." (Execution and the AUTO adaptation are
  board-side, §6.2.)
- **Defrost fan delay** (`0x182D8DDC`): the outdoor fan runs
  "approximately **12 seconds**" at the end of a defrost cycle to
  reduce reversing-valve noise.
- **Defrost backup** (`odu/defrostbackup`): name only in firmware;
  semantics from the platform: which backup heat source runs during
  defrost. HP only.
- **HP low-airflow multiplier** (`0x182D8FEC`): "used for
  non-communicating two-stage outdoor units. **0.63** is used for
  Bristol compressors and **0.8** … for Copeland compressors."
- **Smart Recovery** (`0x182D9E98`): "System will start recovery
  **90 minutes** prior to schedule change in both heating and
  cooling modes." — a fixed 90-minute early start in this build's
  own documentation; no learned-ramp claim is made by the text.
- **Heat/cool deadband** (`0x182D9C40`): "The minimum difference
  enforced between heating and cooling desired temperatures" — a
  setting exists; changing it does not retroactively move existing
  setpoints. **Default value: not in the text — UNPROVEN.**
- **Setpoint limits** (`0x182DA07C`): max heating / min cooling
  setpoint limits exist, and "will take into account the heat/cool
  deadband". **Defaults UNPROVEN.**
- **Furnace staging mode** (`0x182DA4C4`): "System staging provides
  full modulation. Furnace staging uses the furnace['s] internal
  staging algorithm. Low staging runs the furnace at its lowest
  stage. High staging runs the furnace at its highest stage." — i.e.
  the wall can *delegate* staging to the furnace board's own
  algorithm (the board's adaptive mode of §6.1) or pin a stage.
- **Furnace heat-off delay** (`0x182DA5D0`): "The amount of time the
  blower will continue to run after heating has shut off" — the
  wall-side setting for the board-executed delay of §6.1.
- **Dehumidify drain time** (`0x182DA684`): continuous fan turns off
  for a set time at the end of cooling to drain the coil. Setting
  exists; default UNPROVEN.
- **GeoHP protections (platform only, NOT this install)**
  (`0x182D9218–0x182D9320`): HP shuts down when loop liquid is colder
  than the **freeze limit**; HP locked out after **2 or 4 HPS/LPS
  trips in an hour**; HP shut down during **brownout** unless
  override is active. The `freezelimit`/`lockoutcount` dictionary
  names belong to this GeoHP context — they are **not** evidence of
  a house freeze-protection safety temperature (see §8, item T-14).
- **GeoHP WindUp** (`0x182D983C`): "decreases the rate at which the
  Heat Pump will stage up and enable electric heat" — proof a
  stage-up *rate* algorithm exists in the platform core (stage E
  §9.3); GeoHP only, and no numeric rate is given.
- **Restart-wait displays** (`0x182CD2A8–0x182CD334`): "Please wait
  for the System Control / Heat Pump / Air Conditioner / Furnace to
  restart" — the wall surfaces equipment restart delays (§0.3).
- **Brownout disable (HP)** (`0x182D8EBC`): "Brownout protection may
  be disabled if nuisance brownout errors are experienced" — the
  protection itself is ODU-side (§6.2); the wall holds a disable
  flag for it.

### 4.3 Code-isolated thermostat-side control behaviours [FACT]

From stage E (dual-verified there), restated because they are
protections/limits the emulator's control law inherits:

- **Staging hysteresis (demand domain):** stage 2 requires demand >
  **×1.25** of the selected runtime threshold; stage 1 engages at
  **×0.25** of `T[1]`, is held until demand < **×0.01** of `T[1]`,
  and stage 2 falls back at ×1.00 (FUN_180c54d8). No time constants.
- **Demand quantizer hysteresis:** ±1 deadband around the 5 / 0 / −5
  Schmitt thresholds (FUN_180c576c).
- **Satisfaction hysteresis:** zone-satisfaction average sets a
  dictionary flag at > **2.5**, clears at < **1.5** (FUN_18183d34).
- **Demand-response trim:** flagged zones give up half of a system
  offset D = clamp(x, **0…6**), and no adjusted setpoint exceeds
  **70.0** (FUN_180c55f2) — the isolated remnant of the DR subsystem.
- **CFM-range constants:** the arbitration helper's getter returns
  **375.0 / 400.0** by quantizer state (FUN_18051cec) — CFM-range
  values in the demand path; exact role unproven (stage E §7).

### 4.4 What was NOT found on the thermostat side [FACT, negatives]

Searched spaces: the isolated decision module (stage E), the
sys_ctrl timer system (§2–§3), the descriptor/validator system
(stage F), the dictionary (names only prove existence of settings,
not consumers).

- **Compressor min-off / min-cycle timer:** not found. (Owner is
  the ODU board, 3.5 min — §6.2.)
- **Min run time (heat or cool):** not found anywhere.
- **Upstage/downstage timers for the gas furnace:** not found; the
  staging machine is demand-hysteresis only. (A stage-rate algorithm
  exists *somewhere* for GeoHP — §4.2 — but no consumer was isolated
  for any equipment class.)
- **Changeover delay (heat↔cool):** not found as a timer; only the
  setpoint deadband *setting* (§4.2).
- **Numeric defaults** for: aux-heat lockout temp, HP heat/cool
  lockout temps, latch temps/modes, user min/max stages, heat/cool
  deadband, setpoint limits, `idu/heatoffdelay`, dehumidify drain
  time, CFM limits. All UNPROVEN (§5 explains why the descriptor
  route cannot supply them).

---

## 5. Descriptor-default dereference — method and negative result

Task item (1) asked for defaults via the descriptor table
(`0x182B04D4`, entry +0x10 = default pointer, +0x04/+0x08/+0x0C =
min/max/step; stage F §1). This pass:

1. Parsed all **860** descriptor entries (stage F dump).
2. Parsed all **385** binding-directory records (stage D dump:
   bus table + field → field-store offset).
3. For every field of the equipment tables (0302/0304/0306/0307/
   030A/0310/0311/0316, 0402–041B, 0604/0608/060E/0612/061F), found
   the descriptor(s) covering its store offset and **dereferenced
   the default pointer** into the flat image. Full output:
   `stageY/out/desc_defaults.txt`.

**Result [FACT]:** the store ranges bound to equipment bus tables
are covered almost exclusively by **coarse record descriptors**
(len 40 or 70, min 0, max 255, step 1) whose defaults are either all
zeros (0316/0311 record: `00…00`) or a repeating record template
(the 06xx/04xx records: `18 00 20 01 44 00 58 02 58 02 …`). The
descriptor schema treats equipment tables as **opaque byte records**,
not as individually typed settings. A handful of scalar descriptors
exist inside telemetry tables (e.g. table 0304 field 3E: min 2560,
max 7680, default 3840 — a raw scaled value whose engineering
meaning is not established), none of them a protection setting.

**Conclusion:** the named protection settings of §4.1 are
**dictionary properties**, and their stored defaults do **not** live
behind the descriptor table's +0x10 pointers for these ranges. The
defaults loaders (`FUN_1809c378` et al., stage F §2.1) restore
field-store ranges from these record templates — consistent with
the record-level result. Per-setting defaults for lockouts,
latches, deadband and stage limits therefore remain **UNPROVEN**,
exactly as stages E/I/J left them; closing them needs either the
dictionary-property registration records (stage I noted a property-
registration descriptor table at `0x18226D4C–0x18226F80` — not mined
for defaults) or a live NVRAM dump from the unit. This is a
documented dead end for the descriptor route specifically, not for
the question.

---

## 6. Board-side inventory (service literature)

### 6.1 Furnace board — G80CTL Series B Service Instructions

All values from the Sequence of Operation (p. 46) and the safety-
control checks, fetched this pass. The sequence text is written for
conventional (24 V) thermostat wiring; in communicating mode the
wall control supplies stage/CFM commands over the bus, but the
board still proves the same safety chain before and during firing —
the manual describes one control CPU and one sequence, and the
COMM LED note ("When communications with the thermostat is present,
the green COMM light on the furnace control will be on") confirms
the communicating mode runs on this same board. Items marked
† are documented for the conventional sequence and their
communicating-mode equivalence is **[INF]** (same board, same
safety chain; not separately documented).

**Ignition and flame supervision (board, hard safety):**
- Self-check on a heat call; verifies low/high pressure-switch
  contacts LPS/HPS are **open** before starting the inducer.
- Inducer **prepurge 15 s** after the pressure switch closes.
- Hot-surface igniter warm-up **17 s**.
- Trial-for-ignition: gas valve opens; the **2-second flame-proving
  period begins 5 s after** the valve relay closes. If flame is not
  proved within that window: gas valve closes, sequence repeats for
  **up to 3 more trials**, then **Ignition-Lockout**.
- **Ignition-Lockout reset: automatically after 3 hours**, or by
  momentarily interrupting 115 VAC, or 24 VAC at SEC1/SEC2.
- **Flame proved when it should not be present** → the control locks
  out of gas-heating mode and runs the inducer on high speed until
  flame is no longer proved.
- Pressure-switch failure to close → no ignition (status 32.2);
  HPS failure after LPS closes → low-heat operation **until HPS
  closes, max 2 minutes after ignition**.

**Limits (board, hard safety):**
- **Main limit switch:** on overheat it shuts off the combustion
  system and **energizes the circulating blower**; auto-resets on
  cool-down and the burners re-light.
- **Draft safeguard switch** (blocked-vent/rollout protection):
  shuts the furnace down; **if it remains open longer than
  3 minutes, the control board locks the furnace out for 3 hours**
  (reset: remove the heat call / set thermostat OFF **and** cycle
  115 V power).
- Ground/polarity faults prevent heating (status 10.1); the 24 V
  circuit is fused at **3 A** on the board (status 24.1).
- Fault memory: last **7** fault codes, retained **72 hours** of
  powered operation.

**Blower and purge delays (board-executed):**
- Blower-ON delay after the gas valve opens: **45 s (low-heat) /
  25 s (high-heat)**.
- Inducer **post-purge 5 s** after the call ends.
- **Blower-OFF (heat) delay: 90 / 120 / 150 / 180 s selectable,
  factory-set 120 s.** In communicating mode the *value* is the
  wall control's `idu/heatoffdelay` setting (§4.2); execution is
  the board's. (Owner split: value = thermostat, timing = board.)
- Cooling blower-OFF delay (Cod) †: **5 / 30 / 90 s, factory 90 s**.
- **Power interruption during a heat call → 90-second blower-only
  period** starting 2 s after power is restored (code 12), before
  the furnace responds to the call again. A 90 s blower run also
  follows the pressure-switch test sequence.

**Board-side staging algorithms — conventional mode only †:**
- Adaptive heating (single-stage thermostat): the board selects
  low/high heat from stored cycle history; low-heat on-time before
  upstaging is **0–16 min** (after a power interruption, history is
  erased and low-heat runs up to 16 min).
- Adaptive cooling: low-cool on-time **0–20 min** before upstaging;
  on a low→high cooling transition the **compressor shuts down for
  1 minute** while the blower transitions.
- With a two-stage thermostat (Htt = 2St) the board follows the
  thermostat's staging directly. In communicating mode the wall
  control commands stage/CFM — the emulator must therefore command
  staging **explicitly** and must not expect the board's adaptive
  algorithm to rescue a lazy demand signal.

### 6.2 ODU board (AOC + inverter drive) — HVA9 family Service Manual

All values from the Time Delays / Communication / Protection
sections, fetched this pass. The AOC (outdoor control) function list
itself includes "Time Delays", "Pressure switch monitoring",
"Crankcase heater operation", "Defrost operation" — these live in
the unit, not the wall control.

**Compressor timing (board):**
- **3.5-minute time delay** after the last cycle, at initial
  power-up, and on return from a brown-out, before the compressor
  may run again. (Service bypass exists via the Forced Defrost pins
  — a technician action, not a control path.)
- **PEV pressure equalization:** at the end of every compressor ON
  cycle, **150 s** of PEV-open equalization followed by **15 s** of
  PEV-off must elapse before the next compressor ON cycle. "This
  delay cannot be bypassed."
- **10-minute sump warm-up delay** at the beginning of each
  high-voltage power-up; "The compressor will not run during this
  process."
- Crankcase heater: energized during the off cycle, "intelligently
  demanded" by the system.

**Communication behaviour (board) — the emulator's watchdog budget:**
- Green COMM LED: on once a valid command is received; **if no
  communication is received within 2 minutes, the LED turns off**
  until the next valid communication.
- **"Two minute time delay to return to standby operation from last
  valid communication"** — if the wall control dies mid-call, the
  ODU winds down to standby ≈2 min after the last valid frame. It
  does not run away, and it does not stop instantly.
- Internal AOC↔MOC (inverter) communication loss raises a fault
  **after 2 minutes** of no communication (fault 33; elevates after
  repeated failures) — internal to the unit, listed so the emulator
  does not mistake its fault reporting for a bus problem.

**Pressure and electrical protection (board):**
- **Brown-out:** line voltage **< 187 V for ≥ 4 s** → compressor and
  outdoor fan to 0 rpm; operation inhibited until voltage ≥ **190 V**;
  the 3.5-minute delay then applies.
- **High-pressure switch:** opens at **600 ± 5 psig**, closes at
  **470 ± 10 psig**. On a trip: fault displayed; after a **6-minute
  delay**, PEV opens 150 s; the unit restarts **one stage lower**.
  Each further trip stages down again; reaching the lowest stage
  with a further trip = system malfunction/lockout. The
  reduced-capacity state **clears after 2 hours** of accumulated
  operation without further trips.
- **Low-pressure (suction transducer):** compressor+fan stop if
  suction < **15 psi** at any time, or < **33 psi for 5 minutes**.
  Resume: after a **15-minute delay**, if suction has risen >
  **43 psi** (cooling). **Three consecutive** < 15 psi trips →
  **4-hour lockout**; the trip counter resets after **15 minutes**
  of successful operation. Stage ramps are gated per step: suction
  must be ≥ **45 psi** to ramp to the next stage, else the unit
  waits at the current stage.
- **Inverter over-temperature:** the unit keeps running with speed
  reduction; at demand end it shuts down; the outdoor fan continues
  at **500 rpm** until the inverter cools below threshold; **the
  compressor will not restart while the fault is active**.
- **Thermistor supervision:** OAT vs coil-sensor plausibility
  comparison in cooling/heating (out-of-range bands ±10/25 °F
  cooling, ±35/10 °F heating); failed-sensor default operation is
  defined (defrost-related, HP only).

**Defrost (board-executed; HP variants only — NOT applicable to
this AC-only install, listed for platform completeness):**
- Interval **selected at the wall control**: 30 / 60 / 90 min or
  **AUTO (default)**; a 90-min selection defaults to 60 below
  37 °F. First interval after power-up: 30 min.
- AUTO adaptation by the board: last defrost < 5 min → next
  interval 90; 5–7 min → 60; > 7 min → 30.
- Demand: coil temperature ≤ **32 °F for 4 minutes** within the
  interval; defrost only below **50 °F** outdoor ambient.
- Termination: coil > **60 °F** (OAT > 25 °F; minimum 1 min), or
  coil > **45 °F** (OAT ≤ 25 °F; minimum 2 min), or **10 minutes**
  elapsed. Outdoor fan turns on **10 s** before the reversing valve
  switches back; **15 s** delay after defrost before auxiliary heat
  is de-energized.

---

## 7. Capture cross-check (task item 4)

From `THERMOSTAT-PROTOCOL-MAP.md` and `400A-TEST-RESULT.md`
([OBS] = measured on the bus):

- **Output cadence [OBS]:** the command burst repeats every
  **~10 s (median 10.00 s, min 9.0, max 11.2)** and "nothing is
  event-driven: mode/setpoint changes appear by the next burst".
  Consistent with stage N's per-object engine timers and
  independent of the sys_ctrl 15/45 supervision cadence (§3.3) —
  two different rhythms, neither of them a protection.
- **No min-on/min-off signature [OBS, negative]:** in the coldstart
  capture's heat staircase, `0305[0]` = 1 at moderate demand and 2
  only at the top (79 °F setpoint vs 72 °F room), matching the
  demand-hysteresis shape of §4.3. No capture shows a call being
  held or extended by a timer, and no capture is long enough to
  prove the *absence* of a min-run over full cycling — the honest
  statement is: **captures contain no timer-shaped behaviour, and
  the firmware's isolated decision code contains no timers**; two
  independent negatives pointing the same way.
- **Rundown [OBS]:** after the call ends there is exactly **one
  residual stage-2 demand write**, then the idle payload — a
  demand-domain rundown (the ×0.01 hold of §4.3), not a timed one.
  In the same segment the **thermostat is already idle while the
  blower still runs** — direct capture evidence that the blower
  coast is furnace-board-side (§6.1 heat-off delay).
- **Cool call [OBS]:** `0605` = **5.0 from the first burst** of the
  call — no thermostat-side compressor ramp or staging delay is
  visible on the wire; any ramping is the inverter's own (§6.2
  stage-gating).
- **Demand response latency [OBS, confounded]:** in the 2026-10-30
  400A test, a bus-written setpoint at 14:26:49 was followed by the
  demand move (`060D` 00→02, `0305` CFM 0→1166) at 14:29:16–20 —
  but the test record itself attributes the move to Auto+manual
  becoming active in that window and states the demand "moved
  within seconds" of activation. **No clean demand-recompute lag
  can be quoted from the archive**; the often-cited "~2.5 min" is
  the write→photo interval of that test, not a measured control
  lag. Flagged here so the emulator spec does not inherit it as a
  timer.
- **Furnace-side autonomy [OBS]:** the furnace polls an absent node
  (0x45) in bursts at ~62 s intervals five times in its first
  ~4 min after power-up, then stops — board-side behaviour the
  thermostat neither drives nor needs to answer.
- **Comm-fault display [OBS, project incident 2026-11-24]:** with
  the bus disturbed, the Ion showed **INDOOR UNIT COMMUNICATION
  FAULT** and outdoor temperature "---" — the wall control surfaces
  equipment communication faults; §8 item T-15 carries this into
  the emulator list.

---

## 8. FINAL LIST A — thermostat-side: the emulator implements

Owner: the replacement thermostat (today: Ion). "Default" is given
only where a source above proves it; everything else is flagged.
"Applies" = to this install (2-stage gas + VS AC, single zone).

| # | Item | Behaviour / default | Status | Applies |
|---|---|---|---|---|
| T-1 | Demand staging hysteresis (heat & cool) | Stage 2 at demand > ×1.25 of threshold; stage 1 on at ×0.25, held to ×0.01; fallback at ×1.00 (§4.3) | **[FACT]** code | Yes |
| T-2 | Demand quantizer + satisfaction hysteresis | ±1 Schmitt deadband (5/0/−5); satisfaction flag 2.5 / 1.5 (§4.3) | **[FACT]** code | Yes |
| T-3 | Command refresh cadence | Full demand burst every **~10 s**, change or no change (§7) | **[FACT]** captures | Yes |
| T-4 | Supervision re-evaluation cadence | Binding refresh + rate evaluation on a 15 + 45 (≈60 s) supercycle plus on input change (§3.3) | **[FACT]** code; unit **[INF]** | Yes (internal) |
| T-5 | Smart Recovery (early start) | Start recovery **90 min** before a schedule change, heat and cool (§4.2) | **[FACT]** help text | Yes |
| T-6 | Heat/cool setpoint deadband | Minimum enforced heat↔cool separation; a setting exists (§4.2) | Exists **[FACT]**; **default UNPROVEN** | Yes |
| T-7 | Setpoint limits | Max heating / min cooling setpoint limits, deadband-aware (§4.2) | Exists **[FACT]**; **defaults UNPROVEN** | Yes |
| T-8 | Furnace staging mode selection | System (wall stages/modulates) / Furnace (board's adaptive algorithm) / Low / High (§4.2) | **[FACT]** help text | Yes — emulator must pick explicitly; "System" is the communicating norm |
| T-9 | Heat-off delay **value** (`idu/heatoffdelay`) | Wall-side setting for the board-executed blower run-on (§4.2, §6.1) | Exists **[FACT]**; **default UNPROVEN** (the board's conventional factory value is 120 s — do not assume it is the communicating default) | Yes |
| T-10 | CFM limit model | `calcMinCFM`, abs min/max CFM, vcap floor/ceiling/uplimit, min/max CFM enable flags (§4.1) | Names **[FACT]**; **values/defaults UNPROVEN** (equipment-derived at commissioning) | Yes |
| T-11 | Demand-response trim | Flagged zones shed D/2, D = clamp(offset, 0…6 °F), adjusted setpoint capped at 70.0 °F (§4.3) | **[FACT]** code | Optional (DR events) |
| T-12 | Window protection (humidity) | May override humidification to prevent window condensation (§4.1/§4.2) | Exists **[FACT]**; **defaults UNPROVEN** | Only with a humidifier (none known) |
| T-13 | Vacation setpoint bounds | `vacmint` / `vacmaxt` exist (§4.1) | Exists **[FACT]**; **defaults UNPROVEN** | Yes |
| T-14 | Freeze safety temperature (house) | **No evidence Ion has one.** The only `freezelimit` in the firmware is the GeoHP loop freeze limit (§4.2). The research report likewise could not confirm a Nest-style 40 °F safety for Ion | **UNPROVEN — existence itself unproven.** The emulator must decide this itself (industry norm: heat call at ≈40 °F even in Off — research report §8.1) and must not claim it is "inherited" | Yes — emulator's own policy decision |
| T-15 | Equipment comm-fault surfacing | On bus fault the wall displays INDOOR UNIT COMMUNICATION FAULT and blanks OAT (§7) | **[FACT]** observed | Yes — emulator must surface, not mask, equipment comm faults |
| T-16 | Lockout state display + valid-OAT gating | Lockouts engage only with a valid OAT reading; the wall displays "lockout" (§4.2) | **[FACT]** help text | Partially (see T-17) |
| T-17 | HP lockouts & latches | `coollocktemp`, `heatlocktemp`, aux-heat lockout temp; cool/heat latch mode+temp (high-stage-only beyond the latch temp, or ALWAYS); user min/max stages with optional OAT enforcement (§4.1/§4.2) | Exist **[FACT]**; **all defaults UNPROVEN** | **No** — no heat pump, no separate aux in this install. (Cooling lockout `coollocktemp` is the one member that could apply to a plain AC; whether Ion applies it to AC-only systems is UNPROVEN) |
| T-18 | Defrost interval selection | 30 / 60 / 90 min or **AUTO (default)**; executed by the ODU board (§4.2, §6.2) | **[FACT]** manual + help | **No** — AC only |
| T-19 | Defrost backup + defrost fan delay | Backup source selection; fan delay **≈12 s** (§4.2) | **[FACT]** help text | **No** — AC only |
| T-20 | HP low-airflow multiplier | **0.63** (Bristol) / **0.8** (Copeland), non-communicating 2-stage ODU only (§4.2) | **[FACT]** help text | **No** |
| T-21 | Compressor min-off / min-run; furnace upstage timer | **Do not implement as "inherited Ion behaviour" — Ion has none in the isolated code (§4.4).** If the emulator adds its own min-off, it is a new policy, and it must be ≥ the board's enforcement to avoid demand/board fighting (§9 notes) | **[FACT]** negative | Policy decision |

## 9. FINAL LIST B — board-side: the emulator respects, never replicates, never fights

Owner: furnace board (F) or ODU board (O). All values **[FACT]**
from the service literature of §1 unless marked.

| # | Item | Owner | Value / behaviour | Emulator implication |
|---|---|---|---|---|
| B-1 | Ignition sequence & flame supervision | F | Prepurge 15 s; igniter warm-up 17 s; flame proving window 2 s (from 5 s after valve opens); ≤ 4 trials → **ignition lockout 3 h** | A heat demand is not heat: expect up to ~35 s + retries before fire; never interpret ignition retries as a demand problem |
| B-2 | Flame-present fault | F | Flame proved when not called → gas-heat lockout, inducer high until cleared | Surface as equipment fault |
| B-3 | Main limit switch | F | Overheat → combustion off, blower energized; auto-reset on cool-down | Demand may be silently overridden; do not escalate demand to "push through" a limit trip |
| B-4 | Draft safeguard / rollout | F | Shutdown; open > **3 min → 3 h board lockout** (reset needs call removal + power cycle) | After a lockout, removing demand is part of the reset path — the emulator must be able to fully drop a call |
| B-5 | Pressure-switch proving | F | No ignition without LPS/HPS proof; HPS failure → low-heat fallback ≤ 2 min after ignition | — |
| B-6 | Blower-ON delays | F | **45 s** low-heat / **25 s** high-heat after gas valve opens | Airflow lags fire by design |
| B-7 | Blower-OFF (heat) delay | F executes (value from T-9) | 90/120/150/180 s, conventional factory **120 s** | Blower coast after a call is normal (capture-confirmed, §7); do not treat as a stuck call |
| B-8 | Inducer post-purge | F | **5 s** | — |
| B-9 | Cooling blower-OFF delay | F | 5/30/90 s, factory **90 s** † | Same as B-7 for cool calls |
| B-10 | Power-restoration behaviour | F | **90 s blower-only** period after power returns mid-heat-call | After an outage, expect ~90 s of blower-only before heat responds |
| B-11 | Board adaptive staging (conventional mode only) | F | Low-heat 0–16 min / low-cool 0–20 min history-based upstage; compressor 1-min stop on low→high cool transition † | Not active in communicating mode; the emulator commands stages explicitly (T-8) |
| B-12 | Compressor restart delay | O | **3.5 min** after last cycle / power-up / brown-out return | **The** short-cycle protection. The emulator may re-demand sooner, but the compressor will not start; do not diagnose as non-response |
| B-13 | PEV equalization | O | **150 s open + 15 s off** before any next compressor start, non-bypassable | Adds to B-12; a restart can legitimately take ≈3.5 min + equalization sequencing |
| B-14 | Sump warm-up | O | **10 min** at each HV power-up, compressor held off | After an outage, up to 10 min without compressor is normal |
| B-15 | Brown-out protection | O | < 187 V for ≥ 4 s → compressor/fan stop; inhibited until ≥ 190 V; then B-12 | — |
| B-16 | High-pressure protection | O | Trip 600 psig; **6-min delay** + PEV; restart **one stage lower** per trip; lockout at lowest stage; clears after **2 h** clean run | Expect unexplained capacity reduction after trips — it is the board derating, not a demand error |
| B-17 | Low-pressure protection | O | Stop < 15 psi (or < 33 psi for 5 min); resume after **15-min delay** if > 43 psi; 3 consecutive trips → **4 h lockout**; stage ramps gated at suction ≥ 45 psi/step | Cool demand may pause for 15 min–4 h with a healthy bus; surface, don't fight |
| B-18 | Inverter over-temperature | O | Speed derate; fan 500 rpm until cool; **no compressor restart while active** | — |
| B-19 | Bus-silence behaviour | O | **Standby 2 min after the last valid communication**; COMM LED off after 2 min | **Sizes the emulator's watchdog budget:** the burst/poll cadence must never gap anywhere near 2 min; conversely, killing the emulator's output safely winds the ODU down in ≈2 min |
| B-20 | Crankcase heater | O | Intelligent demand during off cycles | — |
| B-21 | Defrost execution | O | §6.2 values (demand, termination, AUTO adaptation) | **N/A** — AC-only install; listed so a future HP swap re-opens it |
| B-22 | Furnace comm-fault timeout | F | **UNPROVEN.** The manual does not state how long the furnace tolerates bus silence mid-call (project gap G1 — a controlled reseat test is the only closer). The ODU's 2 min (B-19) is the only documented number on the system | Emulator design must use the ODU's 2 min as the binding constraint until G1 is measured |

† Conventional-wiring documentation; communicating-mode equivalence
inferred, not documented (§6.1).

### Interaction rules that fall out of List B

1. **Demand ≠ motion.** Between B-1, B-12, B-13, B-14, B-16, B-17,
   a perfectly healthy system can take from ~35 s (ignition) to
   10 min (post-outage sump warm-up) to answer a fresh demand, and
   can refuse for hours under lockouts. The emulator's fault logic
   must key on the boards' own fault reporting (4202 log, status
   tables), never on "demand sent, nothing moved".
2. **Never out-shout a protection.** Raising demand during a limit
   trip (B-3), a pressure derate (B-16/B-17) or a lockout (B-1,
   B-4) does nothing except corrupt the demand signal the boards
   recover into. The correct emulator response to a board
   protection is: hold or drop demand, surface the fault.
3. **The bus cadence is a safety input.** B-19 makes the ~10 s
   burst + poll schedule (T-3) part of the protection envelope:
   an emulator that gaps its output for >2 min stands the ODU
   down mid-call. (The DIY layer's existing guards — no writes if
   the wall has been silent 60 s, max 1 write / 10 s — are
   compatible with, and stricter than, this budget.)

---

## 10. Unproven register — everything flagged above, in one place

| Item | State | What would close it |
|---|---|---|
| Timer unit = seconds | [INF, strong] (§0.2, §3.4) | Dynamic: arm CF47 on a live unit and time the class-5 post against the wall clock |
| flagC (+0xA) = auto-reload | [INF] (§2.4) | Engine tick isolation, or live observation of CF4A/CF45 periodicity |
| 0x1816B/C subsystem identity (discovery supervision) | [INF] (§3.6) | Live trace of states 6–9 during a commissioning event |
| Defaults: lockout temps, latch temps/modes, min/max stages, deadband, setpoint limits, heatoffdelay (communicating), drain time, CFM limits, vacation bounds | UNPROVEN (§4.4, §5) | Mine the property-registration records @ `0x18226D4C–0x18226F80` for default values, or dump the unit's NVRAM |
| Ion house freeze-protection (T-14) | UNPROVEN, existence itself | Installer documentation for SYST0101CW specifically, or a cold-room live test |
| Cooling lockout applied to AC-only systems (T-17 note) | UNPROVEN | Same as above |
| Thermostat min-on/min-off | Negative in all isolated code (§4.4) | Only a dynamic discovery could overturn; treat as absent |
| Furnace bus-silence timeout (B-22 / gap G1) | UNPROVEN | Controlled reseat test with capture (already planned in the protocol map) |
| Series A vs B manual for suffix A2 | Open bibliographic point (§1) | ICP doc for the exact serial; safety sequences are expected to match, values quoted are Series B |

---

## 11. Artifacts

All under `~/workspace/diy-thermostat/firmware-re/stageY/`:
`runY1.sh`–`runY4.sh` with logs (all EXIT=0); `out/decompY/`
(timer primitives `FUN_1809fa76/fde2/fec0`, delta-list insert
`FUN_180a006e`, sys_ctrl providers `FUN_181f8340/8568/862a` via
stage G + this pass, the full 0x1816B/C cluster
`FUN_1816bf24/bf7e/bfe2/c03e/c064/c072/c080/c08e/c0a6/c0be/c198/
c1ac/c218`, `FUN_181f015a`, `FUN_1815dcee/da86/d64c`);
`out/help_region.txt` (installer help region, address-ordered);
`out/help_keyword.txt` (protection/timer keyword census over all
image strings); `out/desc_defaults.txt` (the §5 cross-reference,
all equipment tables). Ghidra project copy: `stageY/proj/`
(stage G's project, extended; stages A–H untouched).
