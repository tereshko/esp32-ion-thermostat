# FIRMWARE ANALYSIS — STAGE T: THE COOLING PATH (this installation)

**Question.** What exactly does the Ion wall control do to run cooling on THIS
equipment, so the emulator can replace it for cooling as well as heating?

**Equipment in scope.** Outdoor: Heil HVA960GKA201 variable-speed AC
(communicating object at bus 0x53, "MultiStg AC 60K", 5-ton; AHRI: compressor
25–100%, 5 stages). Indoor coil: EN(A,D)4X61. Furnace/air handler: G80CTL
(object 0x44). Heat is gas; the ODU is cooling-only (no reversing valve).

**Sources.** THERMOSTAT-PROTOCOL-MAP.md (§a/§e); FIRMWARE-ANALYSIS-D (061E
construction), -E (staging/dictionary), -J (ODU parameterization); InfinitESP
register docs (local tree); the algorithms research
(`research_notes/thermostat-algorithms-research-20261126-0748/`); and a fresh
first-hand recount of every capture in `traces/` (scripts:
`firmware-re/stageT/analyze1–9.py`). Grades: [OBS] counted in captures,
[FIRM] proven in firmware, [INF] inference, [DICT] dictionary name/help only,
[UNK] unknown.

**Corrections this stage makes to earlier documents.**
1. Stage J called 0605 byte [4] "call-state (0 idle / 1 in call)". The full
   recount refutes the plain reading — §2.3.
2. The protocol map says 061F "fields at offsets ~40–52 change first" in
   cooling. Byte-level diff of the captured call shows the only varying bytes
   are 17–20, 30–33 and 58–61 — §5.4.
3. Stage D/map described 061E bytes [1..4] only. Full 9-byte layout and the
   cadence verdict are in §3.

---

## 0. Verdicts up front

- **0605 float** is the thermostat's compressor capacity command on a 0–5
  scale (matching this ODU class's 5-stage capacity model). 0.0 = no command.
  The only sustained value ever captured is **5.0 — full capacity, issued in
  the first burst of the call and held unchanged**; the ODU then ramps its own
  RPM underneath it. Partial values exist in the producer's range: exactly one
  frame of **3.0** exists in 651 bursts, a one-burst transient at a
  mode/setpoint transition. Sustained part-load commanding is **not observed**
  — summer capture target #1.
- **061E is written in every steady-state burst** (~10 s), not only at
  commissioning. Its *value* is commissioning-derived (the committed coil
  parameter) and never changes: `0F 3FD851EC 06 000000` in 651/651 bursts.
- **061F**: of its floats, exactly one in the documented first array moves
  during cooling (offset 17 — a signed control delta, −66.5…+25.2), plus one
  more at offset 58 and an unresolved integer/float region at bytes 29–33.
  InfinitESP's superheat/subcooling names for offsets 1–13 do **not** fit this
  unit: those four floats never move, even mid-call.
- Cooling behaviours actually captured: exactly **one** real cool call
  (2026-10-29, mild weather, ~6 min, ended by wall OFF — never satisfied).
  Everything load-dependent is still open; §9–§10 are the summer plan.

---

## 1. The cooling call, end to end [OBS]

The archive contains one genuine cooling call: coldstart session segment 04,
2026-10-29, setpoint 70 °F, OAT ≈ 65 °F. Sequence (UTC; bursts every ~10 s,
furnace and ODU writes interleaved ~5 s apart inside each cycle):

| Time | Event |
|---|---|
| 17:07:01 | 060D (ODU call flag) already `02` — it leads the demand bytes; it was set during the preceding auto-pause segment while 0305 was still all-zero |
| 17:07:26 | 0305 → cool stage byte [2]=`02`, CFM still 0 |
| 17:07:31 | **0605 float 0.0 → 5.0** (byte [4] → 1). Full command in the first burst; no ramp, no intermediate value |
| 17:07:36+ | 0305 CFM rises on the thermostat's own model: 0 → 1232 → 1710 → 1660 → 1760 |
| 17:08:05 | ODU 0604 target RPM 2180, current 960 — the ODU starts and ramps itself |
| 17:09–17:11 | Target RPM steps 2180 → 2850 → 3700 → 4140 under the *unchanged* 5.0 command; current RPM chases it. 0608 requested CFM steps with it: 938 → 1201 → 1485 → 1600. EXV = **100% the entire call** |
| ~17:09:36 | 060E stage index 0 → 5 once RPM ≳ 2850 (it reports the compressor's actual stage, it is not commanded) |
| 17:12:59 | Last full-speed readback: target = current = 4140 RPM |
| ~17:13 | the author sets the wall to OFF (call never satisfied). Last 5.0 burst 17:13:03; next burst 0605 = 0.0 — **the command drops in one step, no ramp-down** |
| 17:13:13–17:16:05 | 0605 float stays 0.0 but byte [4] stays 1 for 18 more bursts (≈3 min), then clears |

Readback cadence during the call (map §a, unchanged in cool): 0604 and 0608
polled alternately ≈ every 5 s, 060E ≈ every 10 s, 061F / 0302 / 0303 ≈ every
20 s, 0304 ≈ every 50 s.

Two structural facts the emulator must honour:

- **The thermostat does not modulate the compressor.** It issues a capacity
  ceiling (5.0) and the ODU's own inverter control does all ramping,
  staging and EXV work. 0608's "requested CFM" is the ODU asking the blower
  for air; the thermostat's 0305 CFM does **not** follow it (938→1600 vs
  1232→1760, different steps at different times) — corroborates stage J:
  CFM is computed thermostat/furnace-side, 0608 has no consumer.
- **The ODU is inert outside cooling.** During heat and fan-only, 0605 is
  rewritten in its idle form every burst, 0608 reads all-zero, 0604 returns
  the identity block with RPM fields zero.

## 2. Register 0605 — the compressor command (7 B, written every burst)

### 2.1 Payload census [OBS]

All 651 writes 0x20→0x53 across every top-level capture take exactly four
forms:

| Payload | Float [0..3] | [4] | [6] | Count | Where |
|---|---|---|---|---|---|
| `00000000000001` | 0.0 | 0 | 1 | 571 | idle / heat / fan |
| `00000000010001` | 0.0 | 1 | 1 | 45 | see §2.3 |
| `40A00000010001` | 5.0 | 1 | 1 | 34 | the one cool call, every burst |
| `40400000010001` | 3.0 | 1 | 1 | **1** | §2.2 |

Bytes [5] is always 0x00; byte [6] is 0x01 in every write addressed to the
ODU. (The all-zero 7-byte form exists only as the 0x1F boot broadcast and as
broadcasts to 0xF1 during the 1F→20 identity transition — never to 0x53.)

### 2.2 Float semantics [OBS + INF]

- Layout: big-endian IEEE-754 float32 at [0..3].
- 0.0 = no cooling command; the ODU stays off regardless of anything else.
- 5.0 = full capacity. It is the value for a real call from the first burst
  to the last; the firmware's own staging machinery (§6) never once produced
  a sustained intermediate value in the archive.
- 3.0 — the single frame: `phase3-validation3-20261103-145755.jsonl`,
  2026-11-03T20:03:34Z, five seconds after a heat call's 0305 demand zeroed.
  0305 stayed all-zero, 060D stayed `02`, no compressor start followed; the
  next burst was back to 0.0. Verdict: the producer's range includes
  intermediate values (the 0–5 scale is real, not a boolean in float
  clothing), but in this archive an intermediate value appears only as a
  one-burst transition transient — plausibly the arbitrator passing through a
  cooling state during a setpoint/mode change before settling off. Whether a
  mild sustained cool demand produces a sustained 1.0–4.0 is **unknown**
  (§10, item 1).
- The 0–5 range matches the equipment class, not the zone staging byte:
  stage E's staging machine outputs 0/1/2, while the AHRI rating for this
  ODU is 5 capacity stages / 25–100%. The float is a capacity-class command;
  the demand→float transfer function between the endpoints is not isolated
  in firmware (producer behind the runtime binding boundary, stage N) and
  not exercised by captures.

### 2.3 Byte [4] — not a plain call-state [OBS; semantics UNK]

Observed windows where [4]=1:

1. Every burst of the sustained cool call (with float 5.0).
2. For ≈3 min (18 bursts) *after* that call ended, float already 0.0.
3. The first 24 bursts (≈4 min) of `400a-test-20261030-141705`, float 0.0
   throughout, during a manual-mode wall session with intermittent heat
   stage — then 0 for the rest of the file.
4. From the 3.0 transient in validation3 to the end of that file (≥3 bursts).

And [4]=0 throughout: the Oct 29 heat call proper (its one [4]=1 burst is
the tail of window 2 crossing the segment boundary), fan-only, steady idle.

So [4] is an engine-side flag around the ODU command object — set during a
cool call and for minutes after nearby control activity — whose writer is
not isolated (stages F/J/N: the producer path is runtime-bound). It is
**not** needed to explain any ODU behaviour in the archive: compressor
behaviour follows the float + 060D completely. Emulator rule (§11): set
[4]=1 while a cool call is commanded and for ~3 min after it ends; treat
the exact trigger as a summer-capture item (§10, item 6).

### 2.4 Byte [6] = 0x01 [OBS]

Constant in 651/651 ODU-addressed writes (stage J's recount confirmed).
Absent (0x00) only in the pre-identity broadcast forms. Emulator: always 1.

## 3. Register 061E — the coil-parameter frame (9 B, written every burst)

**Layout** [OBS + FIRM]:

| Bytes | Value (ours) | Meaning |
|---|---|---|
| [0] | `0x0F` | unknown; constant in every capture |
| [1..4] | `3F D8 51 EC` = float32 **1.69** | **the committed coil parameter** for EN(A,D)4X61 (stage D: coil DB CAT1 stride-8 index 70; committed by FUN_18140BEA/FUN_18140C80 into object fields 0x59F/0x1C7C–E at commissioning) |
| [5] | `0x06` | unknown; constant |
| [6..8] | `00 00 00` | zero |

Full payload: `0F3FD851EC06000000`.

**Cadence verdict.** Periodic, not commissioning-only: 651/651 steady-state
bursts in every capture file carry this exact frame, including files recorded
weeks of bus-time after commissioning and a file recorded across a
re-commissioning (`sam-commissioning-20261029` — the value is identical
before and after, because the same coil was re-confirmed). What *is*
commissioning-derived is the value: change the coil at commissioning and
[1..4] would change. During identity-transition windows the whole ODU burst
pauses (no partial writes to 0x53) and resumes with the same frame.

Emulator: hard-code the frame verbatim for this installation; write it every
burst. (Per stage D, 061E bytes [1..4] are also what the thermostat would
re-derive if the coil were recommissioned — there is no other source.)

## 4. The constant companions

All written every burst, one payload each in 651 bursts [OBS]:

| Reg | Payload | Role |
|---|---|---|
| 0610 | `00000000` | unknown — no binding record (stage D); replay verbatim |
| 0612 | `22B80000000000000000` | unknown (0x22B8 = 8888 — possibly a model/size code; [UNK]); replay verbatim |
| 061A | `01` | unknown; replay verbatim |
| 060D | `00` or `02` | call-armed flag [INF]: `02` during heat and cool calls, and it **leads** demand bytes at call start by up to ~2 bursts (set during auto-pause before any 0305 demand); `00` in fan-only and satisfied idle. Emulator: `02` whenever a heat/cool call is active or pending, else `00` |

During heat, the ODU still receives the full burst set every ~10 s with the
idle 0605 — the emulator must keep writing the ODU burst in all modes.

## 5. Readback — what the ODU reports

### 5.1 0604 — compressor speed + identity (24 B) [OBS]

[0..1] target RPM (BE16), [2..3] current RPM (InfinitESP layout, confirmed by
the captured ramp: target steps first, current chases). Remainder is a static
identity block (contains the model string region; constant across captures).

### 5.2 0608 — EXV + requested CFM (7 B) [OBS]

EXV % at [2]; requested CFM BE16 at [5..6] (InfinitESP). Captured call: EXV
pinned at 100% for the whole run; requested CFM 938→1600 in steps locked to
the RPM steps. No thermostat-side consumer exists (stage J) — the emulator
reads it for logging/HA only. Whether EXV modulates at part load is unknown
(the one call ran at full command throughout).

### 5.3 060E — actual stage (2 B) [OBS]

[0] = the compressor's actual stage index: 0 at rest and during initial
spin-up, 5 once RPM ≳ 2850 in the captured call. Read-only feedback.

### 5.4 061F — the 81-byte refrigeration block [OBS; identities partly UNK]

Byte-diff of all 72 responses in the cool segment vs 41 idle responses:
**only bytes 17–20, 30–33 and 58–61 ever change**, and in idle/heat/fan the
frame is a constant (one payload in the whole archive outside cooling).
Float grid A starts at offset 1 (InfinitESP's layout), grid B at offset 34:

| Offset | Idle | During cool | InfinitESP name | Verdict for THIS unit |
|---|---|---|---|---|
| 1 (A1) | 8.6 | 8.6 (never moves) | superheat target | constant; name unverified here |
| 5 (A2) | 16.3 | 16.3 | superheat actual | constant — cannot be live superheat; name does not fit this class |
| 9 (A3) | 20.3 | 20.3 | subcooling target | constant; unverified |
| 13 (A4) | 18.3 | 18.3 | subcooling actual | constant; unverified |
| **17 (A5)** | **0.0** | **−66.5 … +25.2, continuously varying** | discharge-related control delta | **[OBS] the one live float in array A**; signed, negative most of the run — consistent with a control delta, not a temperature or a superheat |
| 21 (A6) | 0.039 | 0.039 | dimensionless constant | constant [OBS] |
| 25–28 | bytes `03 06 07 09`-type small ints | unchanged | — | constant small integers [OBS] |
| 29–33 | 0 | bytes 30–33 vary (49–52 distinct values/byte) | — | **not** clean floats in either grid — an integer/counter region or a differently-typed view (stage J: 061F is 5 overlapping typed views of one store); identity [UNK] |
| 34 (B1) | 18.3 | 18.3 | — | constant, temperature-like |
| 38 | word `00001000` | unchanged | — | constant flags/count word [OBS] |
| 42/46/50/54 (B) | 17.3 / 19.3 / 17.8 / 18.8 | unchanged | — | constant, temperature-like (deltas?) |
| **58 (B)** | **−13.18** | **rises to +5.38 by call end** | — | **[OBS] second live float**; identity [UNK] |
| 62–80 | zeros, tail `…1E00` | unchanged | — | constant |

The thermostat has no code consumer for 061F (stage J) — it polls it for
display/diagnostics. The emulator polls and republishes; it does not need
to *act* on any 061F field to reproduce Ion's cooling behaviour.

### 5.5 0302 / 0303 — TLV sensor channels [OBS values; types per InfinitESP]

0302 entries are (type BE16, value BE16 ÷16). Captured call, idle → late:

| Type | Idle | Cool-late | InfinitESP identification |
|---|---|---|---|
| 0x111 (273) | 65.2 | 65.6 | (steady while 0x112 rises — consistent with OAT) [INF] |
| 0x112 (274) | 66.1 | 75.7 | (rises as the outdoor coil heats — consistent with coil temp) [INF] |
| 0x130 (304) | 65.1 | 53.8 | suction line temp |
| 0x145 (325) | 94.1 | 124.6 | discharge line temp |
| 0x14A (330) | 0.0 | 32.0 | superheat channel (InfinitESP; value basis differs from their reference unit) |
| 0x14B (331) | 58.0 | 57.0 | unidentified |

0303 carries the pressure channels (types 0x100 suction / 0x148 discharge,
÷16) per InfinitESP; values were not needed for any verdict here.

## 6. The cooling staging law, as it applies to this VS AC

**Engine chain** [FIRM, stage E]: zone error → 4-level differential quantizer
(Schmitt +5/0/−5 on integrated error, ±1 deadband inside a ±6 °F window) →
dimensionless demand → staging machine (stage 2 above ×1.25 of threshold,
stage 1 above ×0.25, drop at ×0.01; **no minimum on/off timers in the
thermostat's staging code**) → source arbitrator (states: cooling, hpheat,
eheat, gas, reheat, fangas — for this installation only **cooling** and
**gas** are reachable) → demand published to the equipment objects, where
the 0605 producer turns it into the 0–5 capacity float (§2.2).

What this means in practice, per the one captured call: thermostat-side
timers do not shape the compressor's behaviour — protection and ramping
live in the ODU. The thermostat's contribution is: pick the capacity
command (observed: binary in effect, 0 or 5), set 0305 cool stage `02` +
its own blower CFM model, set 060D, and keep the burst going.

**Changeover** [OBS]: mode changes take effect at the next burst; there are
no changeover frames and no bus-visible changeover delay. The captured
session went fan → auto-pause → cool → off → heat within ~20 min with no
lockout behaviour visible on the bus. Heat/cool setpoint separation is
enforced at the UI level (dictionary help: a minimum enforced difference
between heating and cooling setpoints exists as a setting). Simultaneous
heat+cool demand handling (`system/cfgsimultheatcool`) is a **zoning**
feature — not applicable to this single-zone install.

**Cool lockout / latch / stage limits** [DICT only]: the dictionary carries
`odu/coollocktemp`, `odu/coollatchmode`, `odu/coollatchtemp`,
`odu/usercoollatch` (help: "Above this temperature, only high stage
operation is allowed", with an ALWAYS option), and
`odu/usermincoolstage` / `odu/usermaxcoolstage` (installer-set stage bounds,
optionally gated by outdoor temperature). **No numeric defaults are
extractable** — the settings' consumers were never isolated (stage E §12.8),
and no capture exercises any of them (the one call ran at 65 °F OAT,
presumably inside all limits). Emulator: leave all disabled (factory
behaviour as observed) until a capture says otherwise.

## 7. Dehumidification

- Dictionary [DICT]: `dehumidify` exists as a system setting, with
  per-activity humidity settings `humidityHome/Away/Vacation`, `cfghumid`,
  and `humidityfan` (a fan behaviour tied to humidity). No consumers or
  defaults isolated.
- Class evidence (algorithms research, Carrier Infinity owner's manual —
  sibling wall control, not this firmware): cooling humidity target is
  NONE or 55–65% RH; the system may **overcool up to 3 °F** below the cool
  setpoint to wring out humidity; dehumidification is normally paired with
  reduced blower CFM.
- Captured evidence: **none**. No humidity-driven call, no overcool, no
  CFM-for-dehumidification event exists in the archive (all captures are
  heating-season; the thermostat's RH readings were never logged as a
  control input).
- Emulator stance: dehumidification is an optional layer, default OFF.
  If enabled later, implement exactly the class behaviour (target band
  55–65% RH, overcool ≤3 °F, no other bus-visible changes) and mark it
  provisional until a humid-day capture confirms it on this unit (§10.4).

## 8. Explicitly NOT applicable to this installation

- **Heat-pump defrost** — dictionary `defrostInt`, `defrostbackup`,
  defrost fan-delay etc. and any ODU defrost behaviour: this ODU is a
  cooling-only AC (inverter board CESR*******), no reversing valve, no
  defrost. The furnace heats on gas.
- **Aux / electric heat** — `idu/auxheatlocktmp`, arbitrator states eheat /
  hpheat / reheat: no aux heat exists here.
- **HP heat lockout** (`odu/heatlocktemp`) and HP heating staging: no heat
  pump.
- **Bristol ×0.63 low-airflow multiplier**: applies to non-communicating
  2-stage Bristol compressors only — not a communicating VS unit.
- **3E01/3E02 two-capacity ODU family** (infinitive notes: OAT = BE16[0..1]
  ÷16, coil temp = BE16[2..3] ÷16, stage = [0]>>1): a different ODU class.
  Our ODU never serves 3E01/3E02; it uses 0302/0303 TLV + the 06xx set.
  (3E02 appears in our captures only as the thermostat's boot-phase
  broadcast of zeros, not as ODU telemetry.)
- **0602** (2-stage ODU object): not this unit; ours is the 0605 class.
- **Zoning behaviours** (simultaneous heat/cool, multi-zone arbitration):
  single-zone install.

## 9. Coverage table

| Cooling behaviour | Status | Evidence |
|---|---|---|
| Burst composition & ~10 s cadence incl. ODU set | **Captured** | 651 bursts, all files |
| 0605 = 5.0 from first burst, held constant | **Captured** | segment 04, 34 bursts |
| 0605 drop to 0.0 in one step at call end | **Captured** | segment 05 head (wall OFF; satisfied-call end not captured) |
| 0605 partial values, sustained | **Unknown** | one 3.0 transient only (§2.2) |
| 0605 byte [4] semantics | **Unknown** | windows observed (§2.3); writer unisolated [FIRM-negative] |
| 0605 byte [6] = 01 | **Captured** | 651/651 |
| 061E every-burst cadence; full layout | **Captured** | 651/651, one payload |
| 061E [1..4] = coil parameter 1.69 | **Firmware-proven** | stage D commit path |
| 061E [0]=0x0F, [5]=0x06 meanings | **Unknown** | constant, no consumer found |
| 0610 / 0612 / 061A roles | **Unknown** | constants replayed verbatim |
| 060D lead/lag vs demand bytes | **Captured** | §4 |
| 0305 cool stage = 02; thermostat CFM independent of 0608 | **Captured + Firmware** | segment 04; stage J |
| ODU self-ramp of RPM under constant command | **Captured** | 0604 timeline §1 |
| EXV behaviour at part load | **Unknown** | 100% in the only call (full command) |
| 060E stage follows actual compressor | **Captured** | segment 04 |
| 061F offsets 17 / 58 live in cool; rest constant | **Captured** | byte-diff §5.4 |
| 061F field identities (InfinitESP names) | **Dictionary-only** (third-party docs) | names don't fit offsets 1–13 here |
| 061F bytes 29–33 identity | **Unknown** | varies in cool; not float-aligned |
| Staging law (quantizer + ×1.25/×0.25/×0.01) | **Firmware-proven** | stage E; link to 0605 float values unproven |
| Thermostat-side compressor min on/off | **Unknown** | no timers in staging code [FIRM]; restart behaviour uncaptured |
| Changeover: next-burst effect, no special frames | **Captured** | coldstart session |
| Cool lockout temperature | **Dictionary-only** | default not extractable |
| Cool latch (mode/temp, "high stage only above…") | **Dictionary-only** | default not extractable |
| User min/max cool stage | **Dictionary-only** | — |
| Dehumidification target band / overcool ≤3 °F | **Dictionary + class evidence** | not this firmware, not captured |
| humidityfan blower behaviour | **Dictionary-only** | — |
| Defrost / aux heat / HP lockouts | **Not applicable** | §8 |

## 10. Summer capture plan (the unknowns, prioritized)

All captures: full-bus JSONL as usual, plus a note of wall mode/setpoints and
the wall's displayed RH at start/end. Nothing here needs the node to transmit.

1. **Sustained part-load call** (the big one): a mild day (OAT 75–82 °F),
   set cool 1–2 °F below room, let it run 30+ min untouched. Questions: does
   0605 ever sit at 1.0–4.0 for consecutive bursts? Does it step *down* as
   the room approaches setpoint? Does the call end by satisfaction (float →
   0.0 with 0305 [2] → 0 in the same burst?) or overshoot?
2. **Hot full-load call** (OAT ≥ 90 °F): RPM ceiling vs the 4140 seen at
   65 °F; EXV — still 100%?; 0305 CFM vs 0608 requested CFM at full load;
   061F offset-17/58 traces under real load.
3. **Restart cadence**: after a satisfied (or manual) call end, re-demand
   cooling at +2, +5, +10 min. Does the thermostat re-issue 5.0 immediately
   (protection purely ODU-side) or hold off (a thermostat-side min-off the
   staging code doesn't show)?
4. **Humid day / dehumidification**: RH ≥ 60% indoors; set the wall's
   humidity target if offered; room already at cool setpoint. Look for: a
   cool call with no temperature demand (overcool — room driven ≤3 °F below
   setpoint), 0305 CFM reduced vs a normal call, any payload change in
   0605/0610/0612/061A.
5. **Changeover transients**: in AUTO, drag setpoints across room temp both
   ways (heat↔cool) under capture, several times — characterize the 3.0-type
   intermediate floats and byte [4] around transitions.
6. **Byte [4] trigger hunt**: log wall mode changes (Off→Heat, Heat→Off,
   Fan→Auto…) against [4] windows in ordinary heating-season use; the Oct 30
   window (manual-mode session) is the clue to replicate.
7. **061F structure**: the long captures from items 1–2 give the sample size
   to resolve bytes 29–33 and the offset-58 float (correlate against 0302
   suction/discharge and RPM).
8. **Latch/lockout (opportunistic, only if settings are already non-default
   or the author chooses to test)**: toggle cool latch in the installer menu
   under capture on a hot day; look for 0605 forced to 5.0 where a part-load
   value was expected. Do not change installer settings solely for this if
   it risks the install's configuration — lowest priority.

## 11. Emulator requirements — cooling (normative)

1. Every ~10 s burst, in **all** modes, write to 0x53: 0605 (per rules
   below), 060D, 0610 `00000000`, 0612 `22B80000000000000000`, 061A `01`,
   061E `0F3FD851EC06000000` — verbatim constants for this installation.
2. 0605 float: 0.0 when no cool call; **5.0 for the whole of any cool call**
   (v1 law — matches 100% of sustained evidence); drop to 0.0 in one burst
   at call end. Intermediate values: do not emit until §10.1/§10.5 evidence
   exists.
3. 0605 byte [4]: 1 while a cool call is commanded and for ~3 min after it
   ends; else 0. Byte [5] = 0, byte [6] = 1.
4. 060D: `02` when a heat or cool call is active or pending (it may lead
   the demand bytes), else `00`.
5. 0305 during cool: stage byte [2] = `02` from the first demand burst;
   CFM per the thermostat-side model (stages P/R workstream — not from
   0608).
6. Poll readback on the captured cadence (0604/0608 ≈5 s alternating,
   060E ≈10 s, 061F/0302/0303 ≈20 s) and republish to HA; no control
   decision depends on 0608/061F.
7. No thermostat-side compressor timers in v1 (none exist in the staging
   code); rely on the ODU's own protection, exactly as Ion does. Revisit
   after §10.3.
8. Cool lockout/latch/stage limits: disabled (as-observed factory state).
   Dehumidification layer: off by default; if enabled, class behaviour
   only (§7), flagged provisional.
9. Nothing from §8 is implemented.

*Analysis scripts: `firmware-re/stageT/analyze1.py` … `analyze9.py`
(payload censuses, segment timelines, 061F byte-diff, transition windows).*
