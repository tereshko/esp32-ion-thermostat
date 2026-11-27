# Thermostat (0x20) Protocol Map — what an emulator must do to BE the Ion

Stage-1 desk analysis, 2026-10-29. Purpose: specify, from bus evidence,
everything an ESP32 emulator at address **0x20** must transmit, answer, and
time correctly to replace the ICP Ion SYST0101CW as the wall control for
the Heil G80CTL1352422A furnace (**0x44**) and HVA960GKA outdoor unit
(**0x53**).

Labels used throughout: **[OBS]** = counted/measured in the captures;
**[INF]** = inference from the data; **[SRC]** = InfinitESP source/docs
(`infinitesp/components/infinitesp/infinitesp.h`, `docs/entity-reference.md`);
**[RSCH]** = `SAM-REGISTRATION-RESEARCH.md`.

## Sources and method

| Capture | Frames parsed | Window (UTC) | Content |
|---|---|---|---|
| coldstart-20261029-125733.jsonl (+ 7 segments) | 17,600 | 16:57:50–17:24:50 | Full power-up, idle, fan-only, cool 70 °F, heat staircase 75→79 °F, rundown |
| sam-commissioning-20261029-143248.jsonl | 6,543 (1 line unparseable) | 18:32:49–18:48:57 | Phase-2 boot: 78 s thermostat silence, second commissioning, equipment wizard, SAM live |
| sam-control-test-20261029-145357.jsonl | 1,115 (2 lines unparseable) | 18:53:57–18:55:34 | SAM setpoint writes vs. unregistered control |
| full-install-20261029-150209.jsonl | 1,267 | 19:02:09–19:04:55 | Service-menu FULL INSTALLATION (decisive window not in file) |

Total ≈ 26,525 parsed frames. Cadences below were measured on segment 05
(off-pause, 180 s of pure idle steady state) and cross-checked against
whole-file counts (17,600-frame file: a 3 s-tier exchange appears ~523×,
a 10 s-tier write ~154× — consistent). All addresses hex.

**Frame inventory fact:** across all captures the only function codes on
the bus are `0B` (read request), `06` (read response), `0C` (write).
**No `0D` write-ack and no `0x15` exception frame appears anywhere** —
writes are never acked, and reads of absent devices are simply never
answered. [OBS]
Scope note: "never answered" is verified for 44/53 in this archive;
the dialect does have a real exception function `0x15` (code `0x04`),
exercised by SAM-side devices for absent tables — how 44/53 answer a
read of an unsupported register remains open (Gap G9).

---

## (a) Steady state — what 0x20 transmits

### Architecture

In steady state **0x20 is the only initiator on the bus**. The furnace
and ODU never transmit unsolicited and never read the thermostat; they
only answer. (Sole exception observed: at power-up the furnace emits
six 44→45 `030A` broadcasts before anything else — see (c).) [OBS: in the coldstart file, the only non-response frames
not from 0x20 are the 0x1F commissioning phase and 0x93's slow poll —
see (b).] Traffic is organized as bursts of requests ~15–50 ms apart;
request→response latency median **19 ms**, p90 48 ms (n=878 measured
pairs, segment 05). [OBS] An emulator must answer/keep this rhythm:
poll in bursts, expect answers within ~50 ms, retry on its own schedule
(1 of 879 steady reads in the sample went unanswered — ~0.1 % — and the
loop simply carried on). [OBS]

### Poll schedule (all reads are func `0B`, empty payload; answers func `06`)

Tier periods are medians; the "~11 s" tier drifts (min 9.9 s, max 12.7 s)
— likely slots in a ~60 s rotating schedule rather than a free-running
timer. [OBS + INF]

**Every ~3 s** (fast tier):
| Read | Answer | Answer payload |
|---|---|---|
| 20→44 `0104` | 120 B | Furnace identity (constant) |
| 20→44 `0306` | 10 B | IDU status: blower RPM = BE16 at [1..2] [SRC]; see (e) |
| 20→44 `030A` | 14 B | Constant in every capture: `014F4F02001F006B000010100115` |
| 20→53 `0104` | 120 B | ODU identity (constant) |

**Every ~5 s**:
| Read | Answer |
|---|---|
| 20→53 `0302` | 24 B TLV sensor block (raw/16 = °F/PSI [SRC]); bytes drift slowly with conditions |
| 20→53 `0303` | TLV, pressures [SRC] — semantics [SRC]-only, but the wire status is verified: 0x20 polls it 1,314× and receives live 4 B answers (96 distinct payloads). Firmware-side: 0303 **has** binding groups (device classes 0x51/0x52/0x56/0x57/0x5B) although it is absent from the unified catalog (this corrects stage N §8, which states the opposite) |
| 20→44 `0307` (read) | 3 B, always `000000` in every capture |
| 20→44 `0413`, `041B` | Table-04 (VARSPEED blower-drive) rows [SRC] |
| 20→53 `0604` | Compressor speed: target RPM [0..1], current [2..3] [SRC] |
| 20→53 `0608` | Compressor demand: EXV % [2], requested IDU CFM BE16 [5..6] [SRC] — the CFM field is [SRC]-only (no captured value is quoted anywhere); firmware-side the slot has **no consumer** — 0305 CFM does not follow it (J §5) |
| 20→53 `061F` | 81 B float32 array (superheat/subcooling etc. [SRC]); constant while ODU idle, live during cool — see (e) |

**Every ~7 s**: 20→44 `0404`, `040D` (table-04 rows).

**Every ~10 s — the command/write burst** (see below) plus reads:
20→53 `031F`, `0320`, `0321`, `060A`.

**Every ~11 s** (drifting tier): 20→44 `030D` (7 B zeros), `0316`
(IDU config: heat stage [0], CFM [4..5], static pressure [7..8] [SRC]),
`0402`, `0409` (read); 20→53 `0304` (16 B temps/pressures [SRC]), `030D`,
`060E` (actual stage index, byte 0 [SRC]).

**Every ~17 s**: 20→44 `0304`; 20→53 `0602`.

**Every ~20 s**: 20→53 `0310`, `0311` (cycle/runtime counters); writes
`060B`→53 and `0414`→44 (see below).

**Every ~29 s**: 20→53 `0625`.

**Every ~31 s**: 20→44 `030E`, `0310`, `0311`; 20→53 `030E`;
write `031D`→44 (below).

**Every ~60 s**: broadcast writes to **F1**: `0202` (3 B) and `0203`
(3 B) — the SYSTIME table (thermostat-owned time/date [SRC]). `0202`
bytes tick as time fields (minute byte increments 1/min); `0203` was
constant `1C0A1A` during the capture. Period measured 55.6–61.0 s,
median ≈ 60.2 s. (This corrects INDEX.md's "~25 min" note.) [OBS]

**Irregular**: 20→44 `0302` read — 277× in the coldstart file, gaps
0.4–28 s, median ~5.7 s; looks like two interleaved schedule phases.
Answer 12 B, constant — a single payload (`041100000000000000000000`)
in all 1,255 answers corpus-wide. [OBS, verification 2026-11-26]

### The 10 s write burst (the actual control output)

Every ~10 s (median 10.00 s, min 9.0, max 11.2) 0x20 refreshes ALL of
the following, in one burst. Nothing is event-driven: mode/setpoint
changes appear by the *next* burst carrying new values. [OBS]

To furnace 0x44:
| Reg | Len | Idle payload | Semantics |
|---|---|---|---|
| `0305` | 12 | `000000000000000000000078` | **THE demand write.** [0] = heat stage, [2] = cool stage, [4..5] = BE16 blower CFM command [SRC]. Last byte `78` in all steady-state writes (`00` in the SystemInit frames and the two commissioning windows — 25 frames in the archive); verified on all 677 deduplicated 0305 writes in the current archive. Scenario values in (e). Producer attribution: [0]'s heat staging producer is unisolated in firmware — see (e). |
| `0403` | 4 | `00010100` | Constant in every scenario [OBS]; semantics unknown |
| `0409` | 4 | `00010000` | Constant in every scenario [OBS]; semantics unknown (note: `0409` is also *read* from 44 on the ~11 s tier) |
| `0307` | 4 | `00000000` | Constant write; distinct from the 3 B `0307` read answer |

To outdoor unit 0x53:
| Reg | Len | Idle payload | Semantics |
|---|---|---|---|
| `0605` | 7 | `00000000000001` | Compressor command, all 7 bytes: [0..3] float32 BE stage (0.0 idle / up to 5.0), [4] call-state 0/1, [5] = 0 always, [6] = 1 on directed frames / 0 on broadcast frames [SRC + OBS] |
| `060D` | 1 | `00` | `02` during any heat or cool call, `00` idle/fan-only [OBS → call-active flag, INF] |
| `0610` | 4 | `00000000` | Constant everywhere [OBS] |
| `0612` | 10 | `22B80000000000000000` | Constant everywhere [OBS] |
| `061A` | 1 | `01` | Constant everywhere [OBS] |
| `061E` | 9 | `0F3FD851EC06000000` | Constant everywhere [OBS] |

Firmware-side (stage AA; audit-2 §3.1): frame construction is
statically known — builder `FUN_180a44ee`, payload walkers
`FUN_180a815c` (writes) / `FUN_180a7eb0` (reads/serves), directories
DIR-A/B/C, CRC `FUN_180a42dc` (appended on TX, verified on RX).
Stage N's serializer-boundary conclusion is **retracted**. The
serializer's DIR-B records are per-device-class; for this
installation's classes the payloads are blob-copied from RAM staging
buffers: `0305` (class 0x40) 12 B @ `0xFFF85802`, `0605` (class
0x52) 7 B @ `0xFFF85C8D`, `061E` (class 0x52) 9 B @ `0xFFF85D44`.
The `0307` write length (4 B, class 0x40) and `060D` length (1 B,
class 0x52) above are confirmed code-side by these records — do
**not** import AA §7's first-record lengths (`0307` = 3, `060D` =
13; classes 0x3E/0x51) into this map.

Every ~20 s additionally:
| Reg | Len | Payload pattern |
|---|---|---|
| 20→53 `060B` | 7 | `0104XX00000000` |
| 20→44 `0414` | 6 | `0104XX010320` |

`XX` is one byte, **identical in both writes at the same tick**, drifting
slowly: 0x48 at cold start, rising through the first minutes, 0x79–0x7D
during the heat call, 0x91–0x99 during/immediately after cool, decaying
in rundown. [OBS] Per [SRC], `060B`[2] is "target value, native °F, label
TBD"; the observed range (70–194 corpus-wide) and its drift do not match room or
outdoor temperature — semantics unresolved (Gap G4). An emulator can
replay a plausible slowly-varying byte; nothing in the data suggests the
calls depend on it.

Every ~30 s: 20→44 `031D` write, 1 B `01` (50× in coldstart file). [OBS]

Boot-only: 20→44 `0418` write, 3 B `000000`, twice in segment 01. [OBS]

---

## (b) Reverse direction — tables 0x20 must SERVE

Key fact first: **in steady state the furnace and ODU ask 0x20 nothing —
zero frames.** [OBS] The serve obligations come from three other actors:

### 1. The 0x1F commissioning prober (power-up only)

During System Setup the prober reads `030A` **from 0x20** twice
(coldstart +6.0 s into the 1F phase; sam-commissioning likewise). No
response from 0x20 appears — because the prober and the thermostat are
the same physical device (see (c)) [INF]. An emulator never has to
answer this; it has to *be* the prober.

The prober also reads `0104` from 0x92/0x94 and the whole address map —
full probe list in (c).

### 2. Node 0x93 — every ~300 s, forever

An unidentified bus node at **0x93** reads 0x20's `3B05` (SAM accessories
table [SRC]) on a strict ~300.0 s period (measured gaps 299.95–300.52 s,
6 reads in the coldstart file). The thermostat answers func `06`, 11 B,
all zeros (no accessories configured). [OBS] 0x93 was already present in
the phase-1 passive capture, before any SAM existed in this house — it
is part of the installed system, identity unknown (Gap G7). The
emulator must keep answering it: 11 zero bytes every 5 min is the whole
job.

### 3. A SAM at 0x92 (only in the phase-2 captures)

With InfinitESP as SAM, 0x92 reads the thermostat exactly like a real
SAM would [RSCH]. What it asked, and what this Ion served:

| Read from 0x20 | Cadence | Served payload |
|---|---|---|
| `3B02` (SAM state, 29 B) | every ~3 s alternating with `3B03` (129 reads / 16 min) | **29 B, all zeros** |
| `3B03` (SAM zones, 150 B) | same loop | **150 B, all zeros** |
| `0104` | a few | The 120 B identity below |
| `3B04` (vacation state) | a few | 11 B, all zeros |
| `3B05` (accessories) | a few | 11 B, all zeros |
| `400A` (zone-1 comfort profiles, 5×7 B [SRC]) | a few | 35 B: `444C0044891E1E3C50004F001E1E444C0044891E1E444C0044891E1E4F510044891E1E` (constant across both SAM captures) |
| `4012` (vacation settings, 7 B [SRC]) | a few | `3C50001F001E1E` |
| `4202` (thermostat fault log [SRC]) | a few | 72 B, constant in captures: starts `D2200003028E86B3200139028D81B2…` (entries visible; nominal layout 10×7 B [SRC], observed payload 72 B) |

**Critical caveat:** the `3B02`/`3B03` zero contents are what the Ion
serves an **unregistered** SAM [RSCH]. Whether a registered peer would
see real zone state in them cannot be learned from this archive
(Gap G3). For a 0x20 emulator these two tables matter only if it also
wants to serve a SAM — the furnace/ODU never read them.
Quantification (PHASE5.md §1.3): no `3B02`/`3B03` broadcast (mirror)
write from the thermostat exists in 83,752 captured frames — the
passive-mirror path never fires on this Ion; wall room temperature
and system mode are **not** obtainable over the SAM interface
(`3D02` slow-poll reads were never answered). Field layouts for the
served tables now also exist from code (AA's DIR-A members / DIR-C
descriptors), complementing the infinitive layouts; `3B02`'s member
binds store buffer `0x3C0D8D7D`, length 29 — the *contents* question
(registered peer) is unchanged.

Cadence note: the ~3 s `3B02`/`3B03` alternation in the table above
is InfinitESP's polling, not a protocol constant — a real SAM polls
the thermostat at ~65 ms, and infinitive's client uses 500 ms
timeout × 5 retries. An emulator serving a SAM must not assume a
3 s client.

The emulator's SAM-facing behaviour is fully specified in
FIRMWARE-ANALYSIS-V §3.

### Writes addressed to 0x20

In all phase-1 captures: **none, ever.** In the control test, the SAM
wrote `3B03` 6× (150 B) and `3B02` 1× (29 B) carrying the HA setpoint
drags (payloads contain `4F`=79, `45`=69, `41`=65 at the setpoint
offsets; `00000C`/`000010` are the **change-flag words** at body
[1..2]: 0x000C = heat-SP + cool-SP flags; 0x0010 = mode flag).
[OBS] The Ion **never acked**
(no func `0D` exists on this bus) and never reacted — consistent with
the SAM-registration conclusion [RSCH]. An emulator that wants to
accept SAM control must implement `3B02`/`3B03` writes itself; the
archive shows the InfinitESP dialect of those writes, not a real
SAM01's (Gap G6).

### The 0104 identity of THIS Ion (serve verbatim)

Answer to any `0104` read, 120 B, constant [OBS, both captures]:

```
494E4649 4E495459 204E4558 54204745 4E205549 20202000   "INFINITY NEXT GEN UI   "
00000000 00000000 00000000 00000000 00000000 0000       (zero pad)
43455352 31333136 32362D30 342E3739                     "CESR******-**.79"
53595354 30313031 43570000 00000000 000000               "SYST0101CW"
33333230 2A2A2A2A 2A2A2A2A 33333230 2A2A…(2A to 120 B)  "3320********3320********…"
```

Decoded: device name **INFINITY NEXT GEN UI**, software
**CESR******-**.79**, model **SYST0101CW**, serial field
`3320********3320` + asterisks. The asterisks are literal in the
cleaned capture — the capture pipeline masked the middle serial digits
(Gap G2). For comparison, the peers' identities (0x20 reads these every
3 s): furnace `VARIABLE SPEED FURNACE` / `CESR******-**` /
`G80CTL1352422A2` / `2821********A213…`; ODU `VAR SPD COMP VERSION` /
`CESR******-**` / `HVA960GKA201` / `5422********3521…`. [OBS]

---

## (c) Cold start — commissioning obligations

Canonical run: coldstart file, t=0 = 16:57:50.999Z (capture starts
essentially at power-up; the furnace is already awake, the thermostat
is not). The sam-commissioning capture repeats the same sequence with
the same timings (1F phase at +82 s after its own power event). [OBS]

| t (s) | Event |
|---|---|
| 0.00 | Furnace already polling: bursts of 6 reads `44→45 030A`, ~45 ms apart. Address 0x45 never answers (no src=45 frame exists in any capture). Bursts repeat at +62.3, +124.1, +185.0, +247.5 s — then never again in 27 min. [OBS] (Furnace looking for an absent node during its first ~4 min [INF]; the thermostat is not involved.) |
| 0.28 | 0x93 reads 0x20 `3B05` — unanswered (thermostat still booting); 0x93 retries on its normal 300 s schedule and is answered from +196.6 s on. No fault traffic. [OBS] |
| **6.00** | **SystemInit phase opens.** Source address **0x1F** broadcasts writes to F1: `0305` (12 B zeros), `3E02` (1 B `00`), `0605` (7 B zeros). |
| 6.0–16.7 | **0x1F probe sweep**, ~95 ms spacing, each unanswered probe sent **exactly twice**; answered probes once, answers addressed to dst=1F. Order observed: `030A`→20 ×2 · `030D`,`031B`→46 ×2 · `0326`,`0327`→5A,5C ×2 · `0404`→46,5F,69 ×2 · `0104`→21…28 ×2 · `0104`→5F,69 ×2 · `0104`→92 (**answered** in phase 2: SAM identity), `0104`→94 ×2 (0x94 is the **B36** slot — stage C §8, strong inference from the bitmap-clear pair 0x92/0x94) · `0302`→60,61 ×2 · `0307`→3F ×2, →44 (**answered**, 3 B), →46 ×2 · `0402`→3F ×2 · `041C`→44 (**answered**, 1 B) · `041F`→3F ×2, →44 · `0438`→3F ×2 · `061F`→53 (**answered**, 81 B) · `3405`→80 ×2 · then a second pass: `030D`/`031B`→46, `0326`/`0327`→5A/5C, `0404`→46, `0104`→3F, →44 (**answered**, 120 B), →46, →58, →53 (**answered**, 120 B), →55, →5A, →5C, →60, →61, →80 · `0306`→3F ×2, →44 (**answered**, 10 B) · `030A`→3F ×2, →44 (**answered**, 14 B), →46 ×2. |
| **16.67** | Last 1F frame. |
| **16.69** | **0x20 transmits for the first time** — 29 ms after 1F stops. The prober *is* the thermostat (SystemInit persona), per the handoff timing + [SRC]/wiki discovery description. [INF, strongly supported] |
| 16.7–61.8 | 0x20 runs its **own discovery sweep interleaved with the start of steady polling**: probes to 21–28 (`041E`,`0104`), 3F, 46, 55, 58, 5A, 5C, 5F, 60, 61 (`3405`,`0302`,`0104`), 69, 80 (`3405`), 92, 94 (`0104`) — retry counts ×2/×4/×8 per (address, register) (e.g. `030D`→46 ×12 total across both phases' tables, `0104`→58 ×8, `0104`→92 ×4 in phase 1 where no SAM answered). |
| 23.95 | First steady-state read: 20→44 `0104`. |
| 39.10 | First func-0C write of any kind — the SYSTIME broadcast (0202/0203→F1) only; 0x20 is still mid-sweep. The first `0305` write is at +71.65 s. |
| 61.76 | Last sweep probe. Boot-to-fully-steady ≈ **62 s**. |

Origins (audit §2.4): every boot figure must be quoted with its
origin — t=0 above is power/capture start. Audit-reconciled anchors:
0x1F opens +6.0 s from power; the 0x1F→0x20 handoff is +16.7 s from
power; the first 0x20 `0305` write is +65.6 s from 0x1F start (audit
measurement on coldstart); steady state ≈62 s. Cross-doc confusion
on these numbers is documented in audit §2.4.

Note: address `0x0E` is never probed by this Ion. Per stage U
(unaudited) it is a reserved discovery slot for a 3E-family
two-capacity ODU on other systems — the gofinity capture's 0x0E
probes are that system's configuration.

Obligations this creates for an emulator:
1. After a **system** power-up it must run the 0x1F phase itself
   (~11 s, broadcast triplet + the probe order above, ×2 retries at
   ~95 ms) *before* speaking as 0x20 — the furnace and ODU demonstrably
   answer a 1F prober (0307/041C/0104/0306/030A from 44; 061F/0104 from
   53) [OBS], so they expect this ritual.
2. It must then run its own ~45 s discovery sweep as 0x20 (this is how
   it would learn the equipment map: which of 44/53/60/61/80/92/94…
   actually answer).
3. Steady polling may start ~7 s into the 0x20 phase; first demand
   writes ~55 s into it (first `0305` at +71.65 s from power; ~22 s is
   where the SYSTIME broadcast write falls). Devices tolerate this pacing because it is
   what the real control does. [OBS]

In the sam-commissioning capture the thermostat additionally re-ran
**equipment-identification scans** as 0x20 after the sweep (bursts of
reads to 46: `0403`,`0404`,`0407`,`040B`,`040C`,`040F`; to 60/61: `3405`;
to 5F/69: `0404` — the wizard hunting coil/zone/accessory variants),
during which its max transmit gap stretched to 4.90 s repeatedly.
[OBS] The full-install capture shows the same 4.90 s wizard cadence but
contains no 1F phase and no sweep (capture started after them). [OBS]

---

## (d) Cadence & silence — how quiet can 0x20 be?

### Normal gaps (0x20's own transmissions)

Measured on segment 05 (idle): median inter-transmission gap **0.05 s**,
p90 0.41 s, p99 1.96 s, **max 2.81 s**. Segment 01 agrees (max 2.76 s).
Bus-wide, the largest silence in 27 min of steady operation is **2.79 s**
(the 5.72 s gap at +6 s is the boot sequence). During wizard scans the
max 0x20 gap is **4.90 s**, repeating. [OBS]

Rule of thumb from data: **a healthy thermostat never goes >~3 s
without transmitting in steady state, >~5 s even mid-wizard.**

### Observed silences and peer behavior

1. **78.23 s of total 0x20 silence** (sam-commissioning,
   18:33:03.796→18:34:22.030) — the thermostat power-cycle for the
   phase-2 test. During it [OBS]:
   - The SAM (0x92) kept reading `3B02`/`3B03` every ~3 s — **all ~26
     polls unanswered**, no retries storm, no fault frames; it simply
     kept its schedule and was answered again when 0x20 returned.
   - The furnace produced **one** `44→45` burst at +60 s into the
     silence — which coincides with system power returning (the 1F
     phase follows 7 s later, matching cold-start offsets), i.e. it is
     the furnace's own power-up behavior, not a watchdog action.
   - Recovery was a full commissioning (1F phase + sweep + wizard) —
     clean, no fault traffic before, during, or after.
   ⚠ This event was a **whole-system power cycle**: furnace/ODU
   watchdogs, if any, were reset by the same outage. It proves peers
   tolerate ≥78 s of silence *across a shared power event* — nothing
   about a live-bus thermostat failure.
2. **0x93's boot-time read** went unanswered for ~196 s (thermostat
   booting); 0x93 just retried 5 min later. No faults. [OBS]
3. **The furnace's own polls to absent 0x45** (6 retries per burst,
   ~62 s between bursts, 5 bursts, then permanent silence) show the
   local style: unanswered reads are retried a few times, then dropped
   quietly. No fault frames exist in this protocol dialect as captured.
   [OBS]

### The comm-fault timeout: **bounded below (> ~36 s); exact value underived.**

The one real thermostat-only outage — the wall-plate reseat on
2026-10-29 ~15:11 — **is** recorded: `sam-reseat-20261029-151123.jsonl`
(1,611 frames). SAM polls went unanswered for ~36 s
(19:11:36.999–19:12:12.999Z); no fault frame, no fault broadcast, no
device reaction of any kind; recovery ran the full 1F phase. [OBS]
The timeout is therefore **> ~36 s**; no longer thermostat-only
silence exists in the archive.

**Test that would measure it** (Gap G1): ESP capturing, Ion running a
known heat call in mild weather → pull ONLY the Ion off its plate →
at 30 s / 2 min / 5 min / 10 min marks (separate runs or one long run),
watch for: furnace behavior (does the call drop? blower rundown?),
any new frame types or dst=F1 broadcasts from 44/53, `44→45`-style
polling resuming, the furnace's physical fault LED/code, and what the
Ion demands on return (full recommissioning vs. silent resume).
Repeat once with no call active. This is also the safety-critical
number for emulator watchdog design: it defines how long the emulator
may be down before the furnace faults, and whether a mid-call death
drops the call cleanly.

---

## (e) Scenario deltas — the minimal call implementation

Everything a mode/setpoint change touches, and nothing else. The
setpoint value itself **never appears in thermostat→device traffic**
[OBS]: devices see only demand. (Setpoints travel the other way —
SAM→thermostat in `3B02`/`3B03` writes, §b.)

### Furnace demand write `0305` (12 B, every 10 s) — the whole story

Layout [SRC + OBS]: `[0]` heat stage · `[2]` cool stage · `[4..5]`
BE16 blower CFM command · `[11]` = `78` in all steady-state writes
(`00` in the SystemInit frames and the two commissioning windows —
see (a)). Producer attribution: the firmware function computing
[0]'s heat staging is *unisolated*; `FUN_180c54d8` is the
**cool-side** staging machine (gated CD7D == 2 — CD7D: 1 = heat,
2 = cool, 3 = auto, stage S; thresholds CCC4, the mode-2/cool-side
table, CCDC being the heat-side table; output CD49) and must not be
cited for [0]. The wire roles above are unchanged (audit-2 census:
[0]/[2] never co-active in 674 frames).

| Scenario | Payload examples | Reading |
|---|---|---|
| Idle / off | `000000000000000000000078` ×all | stages 0, CFM 0 |
| Fan-only | `00000000048E000000000078`, `00000000017B…` | stages stay 0; **CFM 1166, then 379** as the blower ramps/settles to the fan setting |
| Cool 70 °F | `0000020004D0000000000078`, `…06AE…`, `…067C…`, `…06E0…` | **[2] = 02**; CFM 1232 → 1760 → 1710 → 1660 |
| Heat 75→79 °F | `010000000180…`, `020000000651…`, `00000000048E…` (transitions) | **[0] = 01** at moderate demand, **[0] = 02** at the top of the staircase (79 °F vs room 72 °F); CFM 384 / 1166 / 1617 |
| Rundown after OFF | one residual `020000000651…`, then idle payload | demand byte persists into the first burst after OFF, then clears; the blower coast itself is furnace-side (segment 07: thermostat already idle while blower still runs) [OBS] |

Also during heat, `060D`→53 = `02` and `0605` stays 0.0 — the ODU is
told "call active" but no compressor stage (gas heat). [OBS]

### ODU command writes during cool (every 10 s)

| Reg | Idle/heat/fan | Cool 70 °F |
|---|---|---|
| `0605` (stage, float32 [0..3]) | `00000000000001` (0.0) | **`40A00000010001`** (float 5.0; the changing byte is [4], call-state 00→01; [5] = 0 in both, [6] = 1 in both — directed frames) — full-capacity command from the first burst; no partial stages observed in this capture (Gap G8) |
| `060D` | `00` (heat: `02`) | `02` |

All other 10 s writes (`0403`,`0409`,`0307`→44; `0610`,`0612`,`061A`,
`061E`→53) are **bit-identical across every scenario** — an emulator
replays them as constants. [OBS]

### Response-side deltas (what the emulator should expect back)

- Furnace `0306` (10 B): idle `010000000000C808CA00` (RPM [1..2] = 0).
  Fan-only: `010452048E00C808CA08` — RPM 1106, CFM echo 1166 at [4..5],
  last byte `08`. Heat: `010511065102A808CA18` — RPM 1297, CFM echo
  1617, bytes [6..7] `02A8` (vs `C808` idle — gas-side state [INF]),
  last byte `18`. Cool similar to fan with `18` at high CFM. [OBS]
- ODU `061F` (81 B floats): a single constant payload in idle, heat,
  and fan-only (160 reads / 161 answers in segments 01/02/06, the
  except-3-frames detail stands);
  during cool, 62 distinct payloads in 72 reads — compressor floats go
  live. Corpus-wide the varying offsets are exactly {17–20, 30–33, 41,
  58–61} (byte 41 = low byte of the word at [38..41], toggles 0↔2).
  [OBS, verification 2026-11-26]
- ODU `0302` (24 B TLV): drifts slowly always; changes fastest during
  cool (68 distinct / 72 reads). [OBS]
- Furnace `030A` (14 B): **constant in all 17,600 coldstart frames** —
  no scenario information. [OBS]

### Minimal emulator call set (conclusion)

To reproduce every call in the archive, an emulator needs exactly:
1. The 10 s write burst with constants replayed verbatim;
2. `0305` computed as: heat stage 0/1/2, cool stage 0/2, CFM per
   the computation specified in FIRMWARE-ANALYSIS-R §9
   (interpolation over the capacity tables + demand floor
   `325·CD8C/12000` + per-mode store clamps). Observed 0305 CFM
   values in this archive: {0, 378, 379, 382, 384, 1166, 1232,
   1368, 1617, 1660, 1710, 1750, 1760} — observed values, not a
   range; another system's capture shows 360 (gofinity), so the
   low end is not a clamp;
3. `0605` float stage 0.0 / 5.0 (cool), `060D` = 02 during any
   heat/cool call;
4. The full poll schedule of §(a) (peers' answers are its telemetry;
   the polls themselves are also its presence signal);
5. The §(b) serve list and §(c) boot ritual.

---

## GAP LIST — what the archive does NOT establish

Each gap: why it matters → the test that closes it.

- **G1. Comm-fault timeout & mid-call death behavior.** How long may
  0x20 be silent (live bus, devices powered) before the furnace/ODU
  fault, drop a call, or change behavior? The reseat capture bounds
  it below at > ~36 s (see (d)); the exact value is unmeasured. → Controlled reseat test with capture running, Ion
  pulled only, escalating silences 30 s → 10 min, once idle and once
  mid-heat-call, logging bus + furnace fault LED. **Do this before any
  live emulator test — it sizes the emulator's watchdog budget.**
  Equipment-side bound (stage Y, unaudited): the HVA9 service manual
  documents the ODU entering standby ~2 min after the last valid
  message; the furnace comm-fault timeout itself remains unmeasured.
- **G2. Exact serial digits in the 0104 identity.** Cleaned captures
  mask them (`3320********3320`); the raw tap (port 4242) is off-limits
  by project rule (carries credentials). → Read the serial off the
  Ion's About screen or the unit's sticker and hand-enter it into the
  emulator's identity block. No bus test needed.
- **G3. Real contents of 3B02/3B03.** The archive only shows what an
  *unregistered* SAM is served (zeros). If the emulator ever serves a
  SAM/client, real zone-state layout must come from elsewhere. →
  Capture a *registered* SAM pairing (impossible on this Ion [RSCH]) or
  a real SAM01 on a Carrier control; or accept the InfinitESP source's
  own 3B02/3B03 model [SRC] as the reference implementation.
  **Partially closed** by infinitive-registers: full 3B02/3B03/3B04
  layouts, the flag dialect, and the Touch two-write model
  (notification write primes, direct write delivers) are now
  documented from external sources, and code-derived layouts now
  exist as well (AA's DIR-A members / DIR-C descriptors; 3B02's
  member binds store buffer 0x3C0D8D7D, length 29). What remains
  unknowable is only the registered-on-this-Ion contents
  (registration is gated, stage C).
- **G4. Semantics of the constant/unknown payloads**: `030A` (14 B
  constant), `0403`/`0409` writes, `0610`/`0612`/`061E`, `0625`, `031D`,
  `0307` (read vs write), `0305` byte [11] = `78`, the `060B`/`0414`
  shared byte (70–194 range), `4202` length 72 vs nominal 70. → Not
  needed for calls (replay verbatim); decode opportunistically from
  [SRC] and future captures where a config change is made on the Ion
  while capturing (e.g. flip a furnace config option in the installer
  menu and diff the constants).
- **G5. Who must run SystemInit, and when.** Data + [SRC] say the
  thermostat runs the 1F phase after a *system* power-up. Unobserved:
  furnace power-cycling alone while the thermostat stays up (does 44
  expect a new 1F phase? does the real Ion re-run one?), and the
  thermostat booting while devices are already warm (the reseat case —
  its capture exists: 1,611 frames, ~36 s outage, no reaction; see (d)). → Two captures: (i) furnace breaker
  cycle only, Ion live; (ii) Ion reseat only, with the capture stream
  verified flowing first (the 15:15 lesson).
- **G6. Real SAM01 write dialect for 3B02/3B03.** Only InfinitESP's own
  writes were captured. → Only matters if the emulator must accept
  control from a hardware SAM; deprioritize (no SAM will be installed).
  **Partially closed:** the flag dialect and the Touch two-write
  model are documented from external sources (infinitive-registers),
  and the emulator's SAM-facing behaviour is fully specified in
  FIRMWARE-ANALYSIS-V §3. G6 remains open only for a real SAM01's
  exact write frames.
- **G7. Identity of node 0x93** (polls `3B05` every 300 s). Behavior is
  fully specified (answer 11 zero bytes); identity is not needed. →
  None. Revisit only if it ever asks for something else.
- **G8. Part-load behavior**: the cool capture starts at full demand
  (0605 = 5.0 immediately) and the heat staircase reaches stage byte 02
  quickly; whether the control ever commands 0605 ∈ {1.0…4.0}, heat
  stage >2, or CFM outside 378–1760 in real part-load is unseen.
  Update: exactly one transitional `0605 = 3.0` frame exists in the
  full archive (2026-11-03, stage T, unaudited); sustained part-load
  remains unobserved. →
  The planned opportunistic captures: a long mild-weather cool run and
  the winter stage-2 heat soak (already on the project list).
- **G9. Exception behavior.** No exception (0x15) frames exist in the
  archive; how 44/53 answer a read of an unsupported register is
  unobserved (unanswered? exception? zeros?). → One bus-safe probe
  session: from the existing SAM node, read a spread of undefined
  registers on 44/53 and log raw replies via InfinitESP logs — do
  **not** improvise this against the live system without the author's
  go-ahead; it is the only gap whose test transmits.
- **G10. Clock contents of 0202/0203.** Bytes tick like time/date, but
  the Ion's own clock was known-wrong on capture day, so field mapping
  is unverified. → One capture while the Ion clock is deliberately set
  to a known value; diff the two broadcasts.
- **G11. Wizard/commissioning variants**: equipment-identification
  scans (to 46/5F/69/60/61) were captured mid-flight in two files but
  never start-to-finish in one file, and the FULL INSTALLATION decisive
  window is missing entirely (0 KB / out-of-window captures). → Only
  needed if the emulator must survive a *device-initiated*
  recommissioning; the furnace has never been observed initiating one.
  Capture a full installer-menu run if the Ion is ever recommissioned
  for other reasons.

---

## One-paragraph summary

The thermostat's job, as measured: run an ~11 s 0x1F SystemInit ritual
at system power-up, sweep for equipment for ~45 s, then forever poll
the furnace and ODU on a 3/5/7/10/11/17/20/29/31 s tiered schedule,
refresh a constant 10 s command burst whose only live contents are the
`0305` demand (heat stage / cool stage / blower CFM), the `0605`
compressor-stage float, and the `060D` call flag; broadcast time every
60 s; answer a 300 s `3B05` poll from node 0x93 and any SAM's reads.
It is never polled by the equipment it controls. The single
safety-critical unknown is the comm-fault timeout (G1) — measure it
before the emulator ever holds a call alone.

---

## Errata applied 2026-11-26 (audit-1 §5 + audit-2)

Applied from FIRMWARE-AUDIT.md §5 (E-1…E-14) and FIRMWARE-AUDIT-2.md
§6 (E-15…E-22):

- E-1: 0605's changing byte is [4] (call-state); full 7-byte layout
  stated in (a) and (e).
- E-2: `0305` [11] = 0x78 qualified to steady-state writes (0x00 in
  the SystemInit frames and the two commissioning windows).
- E-3: 0305 write count corrected — 677 deduplicated writes in the
  current archive (was "1,811").
- E-4: `00000C`/`000010` are change-flag words at body [1..2], not
  "mode words".
- E-5: G3/G6 annotated as partially closed (infinitive-registers:
  full 3B02/3B03/3B04 layouts, flag dialect, Touch two-write model).
- E-6: "reads of absent devices are never answered" scoped to 44/53;
  the dialect's exception function 0x15 (code 0x04) noted.
- E-7: §(b) quantified — no 3B02/3B03 broadcast (mirror) write in
  ~75,000 captured frames; wall room temperature and system mode are
  not obtainable over the SAM interface.
- E-8: 0608 "requested IDU CFM" marked [SRC]-only; firmware-side the
  slot has no consumer.
- E-9: §(e) CFM presented as the observed value set, not a
  379–1760 range (gofinity shows 360 — the floor is not a clamp).
- E-10: 0303 marked [SRC]-only/unverified; firmware-side correction
  added — 0303 has binding groups although absent from the unified
  catalog (corrects stage N §8).
- E-11: §(c) boot figures given explicit origins (audit §2.4
  reconciled anchors).
- E-12: the ~3 s 3B02/3B03 cadence annotated as InfinitESP's
  polling, not a protocol constant (real SAM ~65 ms).
- E-13: probed address 0x94 identified as the B36 slot (stage C §8).
- E-14: no change — 4202's 72 B observed vs 70 B nominal verified
  still open.
- E-15: 0305 [0] producer attribution — the heat staging producer is
  unisolated; FUN_180c54d8 is the cool-side staging machine (gated
  CD7D == 2, thresholds CCC4, output CD49) and must not be cited
  for [0]. Wire roles unchanged.
- E-16: §(e) minimal call set item 2 now points at the CFM
  computation in FIRMWARE-ANALYSIS-R §9.
- E-17: G8 — exactly one transitional 0605 = 3.0 frame exists in
  the archive; sustained part-load remains unobserved.
- E-18: code-derived served-table layouts (AA's DIR-A members /
  DIR-C descriptors) added in (b) and G3; 3B02's member binds store
  buffer 0x3C0D8D7D, length 29.
- E-19: G1 — equipment-side bound added: ODU standby ~2 min after
  the last valid message (HVA9 service manual, stage Y).
- E-20: §(c) — address 0x0E is never probed by this Ion; reserved
  discovery slot for a 3E-family two-capacity ODU on other systems
  (stage U).
- E-21: §(b)/G6 — the emulator's SAM-facing behaviour is fully
  specified in FIRMWARE-ANALYSIS-V §3; G6 remains open only for a
  real SAM01's exact write frames.
- E-22: no change (guard) — the map's 0307 write length (4 B) and
  060D length (1 B) are correct and confirmed code-side by the
  DIR-B records for our device classes (0x40 / 0x52); AA §7's
  first-record lengths (0307 = 3, 060D = 13 — classes 0x3E / 0x51)
  must not be imported. Per-class staging buffer addresses added
  in (a). Stage N's serializer-boundary conclusion is retracted:
  the frame builder, walkers, DIR-A/B/C and CRC FUN_180a42dc
  (TX + RX roles) are statically known (stage AA; audit-2).

## Verification corrections 2026-11-26 (fleet re-derivation, VERIFY-map)

Applied from firmware-re/verify/VERIFY-map.md (independent parsers over
the 83,752-frame corpus, gofinity .bin, flat.bin):

- V-1: §(c) 39.10 row — SYSTIME broadcast, not a command burst; first
  0305 at +71.65 s. Obligation 3 corrected (~55 s into the 0x20 phase).
- V-2: §(d)/G5 — the reseat capture EXISTS (sam-reseat-20261029-151123,
  1,611 frames): ~36 s thermostat-only outage, no reaction; G1 timeout
  bounded below at > ~36 s.
- V-3: §(a) furnace `0302` answer — 12 B constant, not "24 B, slowly
  varying" (that is the ODU's 0302).
- V-4: §(e) `061F` varying offsets = {17–20, 30–33, 41, 58–61}
  (byte 41 verified by direct recount: {0: 554, 2: 936} of 1,490
  responses — VERIFY-map's own "nothing in 40–52" sub-conclusion was
  itself wrong; VERIFY-cooling's set plus byte 41 stands).
- V-5: §(a) unanswered reads — 1 of 879, not 5.
- V-6: §(e) heat example `01000000048E…` removed — zero occurrences in
  the corpus (stage 1 + CFM 1166 never co-occur).
- V-7: §(e) `061F` segment counts — 160 reads / 161 answers, not 168.
- V-8: §(a) `0303` — wire status verified (1,314 polls, live 4 B
  answers, 96 distinct payloads); semantics remain [SRC].
- V-9: corpus size is 83,752 frames wherever "~75,000" appeared in the
  body (E-7's changelog figure above is superseded likewise).
- Minors: handoff gap 29 ms (not 20 ms); cool CFM order
  1232 → 1760 → 1710 → 1660; B-7 byte range 70–194 (§(b) and G4);
  G8 range floor 378 (E-9's "379–1760" above superseded); §(a)
  architecture note on the furnace's power-up 44→45 broadcasts.
