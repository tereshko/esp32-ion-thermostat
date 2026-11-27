# FIRMWARE-ANALYSIS-E.md — ICP Ion BINF0479 firmware, RE stage E

Date: 2026-11-26. Desk work on files only; nothing was flashed or written to
any device. Continues `FIRMWARE-ANALYSIS.md` (stage A), `-B` (stage B) and
`-C` (stage C). Work was done in the saved Ghidra project **copied** to
`firmware-re/stageE/proj/` (the stage-B/C originals are untouched); scripts
and all intermediate output are preserved in `firmware-re/stageE/`
(`scripts/`, `out/`, `run*.sh`, `run*.log`). Stage D (bus transmit path,
poll schedule, per-model equipment database) is a parallel pass in
`firmware-re/stageD/` and was not touched.

Labels: **[FACT]** = measured/decompiled/disassembled directly this pass.
**[INF]** = inference, with reasoning shown. Negatives state the space
searched. Per the owner's requirement, every extracted constant, threshold
and decision rule was confirmed by a **second independent method**; the
dual-verification log is §11. Single-method results are marked as such.

**Mission:** the CONTROL-DECISION CORE — the code that computes the values
refreshed in the ~10 s write burst of `THERMOSTAT-PROTOCOL-MAP.md` §a:
furnace demand table `0305` (heat stage [0], cool stage [2], blower CFM
[4..5], constant `0x78` at [11]), ODU stage table `0605` (float32 stage)
and call flag `060D`; staging / changeover / defrost decision parameters;
and the timing structure that produces the ~10 s burst.

---

## 0. Headline results

1. **The equipment-command writers were NOT isolated [FACT, negative].**
   No statically reachable code path was found that assembles the `0305`
   or `0605` payloads. The reason is the same architectural wall stages B
   and C hit: the application is a Clarinox data-binding engine — computed
   properties are evaluated through runtime-registered function-pointer
   tables and device objects living in the `0x3C…` dictionary space, so
   static call chains dissolve at the registration boundary (§1, §8).
   The `0x78` byte at `0305[11]`, the CFM computation, and the `060D`
   flag writer remain unisolated (§12).

2. **A complete zone-demand decision module WAS isolated [FACT].** A
   family of computed properties around `0x180C54xx–0x180C5Dxx` plus
   `0x18183Cxx–0x18184xxx`, all evaluated by one binding refresh function
   (**FUN_181efdfc**), implements: a 4-level demand quantizer with ±1
   hysteresis (§2), a 0/1/2 staging state machine with droop ratios
   **×1.25 / ×0.25 / ×0.01** against a runtime threshold table (§3), a
   per-zone setpoint adjustment (clamp 0…6, halved, capped at **70.0**)
   (§4), a per-zone satisfaction averager with decision thresholds
   **1.5 / 2.5** writing a flag byte into the dictionary (§5), a
   heat/cool source arbitration machine over a 0…5 state (§6), and a
   weighted zone-demand sum (§7). All constants dual-verified (§11).

3. **The staging machine's shape matches the capture staircase [INF].**
   Captures show heat stage 1 at moderate demand and stage 2 only at the
   top of a 75→79 °F staircase, with one residual stage-2 write after the
   call ends. FUN_180c54d8 (§3) is exactly one 0/1/2 machine whose
   stage-2 entry requires demand > **125 %** of a table threshold, whose
   stage-1 entry is **25 %**, and whose stage-1 drop-out is **1 %** —
   i.e. once staged up, the machine holds stage ≥ 1 until demand nearly
   vanishes. This is consistency, **not identity**: no static link from
   its output byte `0xFFF8CD49` to `0305[0]` was found (§10).

4. **Gap G8 (partial ODU stages 1.0–4.0) stays open [FACT, negative].**
   A whole-image float-constant census (FloatHunt, §9.1) found **no**
   function that selects among the float constants 1.0/2.0/3.0/4.0/5.0
   as a stage set; the only discrete demand levels isolated anywhere are
   the 4-level quantizer of §2 (levels 1–4 over a ±6 differential) and
   the 0/1/2 machine of §3. The firmware therefore contains no evidence
   of a constant-table 0605 stage selector; whether the ODU stage float
   is computed (int→float / demand-scaled) could not be settled because
   the 0605 writer itself is unisolated. The capture fact (only 0.0 and
   5.0 ever observed) is **not contradicted** by anything found.

5. **`sys_ctrl_task` is identified — and it is a dispatcher, not the
   control loop [FACT].** Created at FUN_181f81be (name string
   `0x1830B12C`, entry FUN_181f81ae, create wrapper FUN_180bc084), its
   loop body FUN_181f7fc4 blocks on a queue with a **1000 ms** timeout
   and dispatches one of **12** message classes through a
   runtime-registered handler table, keeping per-class execution-time
   statistics. The ~10 s burst period was **not** found as a constant:
   a raw scan shows the BE word `10000` occurs only 5 times in the image,
   none with a code reference (§8). The cadence is most plausibly a
   1 s tick × counter inside a registered handler — unproven (§12).

6. **Staging/changeover/defrost parameters exist as settings, not as
   isolated code [FACT].** The Sparkplug data-dictionary names and the
   installer help texts prove the thermostat-side parameter set —
   aux-heat lockout temp, HP heat/cool lockout temps, cool/heat latch
   mode+temp, defrost backup + defrost interval, user min/max heat/cool
   stages, furnace staging mode (System / Furnace / Low / High), HP low
   airflow multiplier **0.63 / 0.8**, recovery start **90 min** before a
   schedule change (§9). The code that consumes these settings was not
   isolated; no numeric lockout/latch/defrost defaults were extracted.

---

## 1. Method and the shape of the code

Toolchain (verified working this pass): Ghidra 12.2 headless from
`firmware-re/stageB/ghidra/support/analyzeHeadless`, JDK in
`firmware-re/stageB/jdk`, project copy `firmware-re/stageE/proj`,
processor SuperH:BE:32:SH-2A, image base `0x18040000`. The flat image
`firmware-re/stageB/flat_trim.bin` maps file offset = address −
`0x18040000` exactly (header `!!START_OF_CODE!` / `CESR******-**.79` at
offset 0), which makes raw big-endian word reads of the file a valid
independent check on anything Ghidra reports. Scripts written this pass:
`FloatHunt.java`, `IntHunt.java`, `UsersOf.java` (two-level pool-cell
tracing), plus stage-C's `DecompileScript.java` / `ListingDump.java`.

Search strategy, in order:

1. **String recon** (`recon1_strings.py`, `recon2_dict.py` →
   `out/recon1.txt`, `out/recon2.txt`): 34,639 strings ≥ 6 chars; the
   application is nearly devoid of its own assert/path strings (81 build
   paths, almost all lwIP/FreeRTOS/Clarinox BSP), so the assert-string
   route into control code is weak. The region `0x18300000–0x1830A200`
   is a **Sparkplug B** metric-name dictionary (§9).
2. **Float-constant census** (`FloatHunt.java` → `out/floathunt.txt`):
   every BE float word in 0.5…5.0 scanned with Ghidra references
   (§9.1). No staging table surfaced; two multi-value consumers did —
   FUN_180c576c and FUN_18183d34 — and they led to the module of §2–§7.
3. **Pool-cell two-level tracing** (`UsersOf.java`): because code reaches
   RAM variables and functions only through literal-pool cells, each
   interesting RAM address was resolved cell → users.
4. **Task-table route**: the string `sys_ctrl_task` (`0x1830B12C`) was
   traced to its creation call (§8).

Architectural finding that frames everything below **[FACT]**: the
decision logic that *is* statically visible lives in the Clarinox
**binding layer** — "computed properties" over a RAM variable block at
`0xFFF8C8xx–0xFFF8CDxx`, re-evaluated by the refresh function
FUN_181efdfc when zone data changes. FUN_181efdfc is the *sole* caller of
FUN_180c549c (init), FUN_180c55f2 (§4), FUN_180c576c (§2) and
FUN_180c5832 (§6) — each reached through a pool cell as a computed call
(`out/users1.txt`, `out/users2.txt`). The equipment-side writers sit
behind further runtime registration and were not reached.

### 1.1 The zone-demand RAM block [FACT]

All addresses below were read from literal-pool cells in the decompiled
functions and cross-checked against the raw image (§11). `0xFFF8C…` is
the SH-2A on-chip / external RAM window used by the binding model.

| Address | Type | Role (evidence) |
|---|---|---|
| `0xFFF8CB58` | float | scalar input X to §2 and §5 |
| `0xFFF8CB5C` | byte | gate input of §6 (must == 1) |
| `0xFFF8CB60` | float[8] | per-zone array B (§5) |
| `0xFFF8CBA9` | byte[8] | per-zone flag array (§4, §5) |
| `0xFFF8CABB` | byte | scalar input Y; X−Y is the §2/§5 differential |
| `0xFFF8CABC` | float[8] | per-zone array A (§4, §5) |
| `0xFFF8C8BC` | byte[8] | second per-zone flag array (§6 helper; zeroed by init) |
| `0xFFF8CC52` | byte | mode nibble tested by §6 helper (`& 0xF < 2`) |
| `0xFFF8CC5A` | byte | 1-based index into the §3 threshold table |
| `0xFFF8CCC4` | float[] | runtime threshold table of §3 (and §7 cap table) |
| `0xFFF8CD44` | float | demand input of §3 |
| `0xFFF8CD49` | byte | output state 0/1/2 of §3 |
| `0xFFF8CD4A` | byte | state 0…5 of §6 (read and written) |
| `0xFFF8CD4B` | byte | state 1…4 of the §2 quantizer |
| `0xFFF8CD4C` | byte | flag output of §6 |
| `0xFFF8CD50` | float[8] | adjusted per-zone array, output of §4 |
| `0xFFF8CD7D` | byte | global mode/enable byte; §3 and §6 require == 2 |
| `0xFFF8CB48` | byte | flag output of §6 |
| `0x3C12E6C4` | byte | dictionary-space flag written by §5 |

`0xFFF8CD7D` is image-wide popular (46 distinct pool cells,
`out/users2.txt`) — a global mode byte **[INF]**. It is *written* inside
FUN_181efdfc from a getter result (cell `0x181F00E0`, writes at
`0x181EFFD4`/`0x181F0024` in the decompile), i.e. the refresh function
itself maintains it before evaluating the gated properties.

---

## 2. FUN_180c576c — four-level demand quantizer with hysteresis

**[FACT]** Body 198 B, entry `0x180C576C`. Sole caller: FUN_181efdfc
(computed call at `0x181EFFDA` via pool cell `0x181F00E4`). Evidence:
`out/decomp1/decomp_180c576c.c`, instruction listing
`out/listing_quant.txt`, raw pool reads (§11).

Input: `x = *(float*)0xFFF8CB58 − (float)*(byte*)0xFFF8CABB`.
State: byte at `0xFFF8CD4B`, values 1…4. Output: the state byte only —
the listing shows **no return value** is produced (`rts/n` at
`0x180C582E` with no result setup); the decompiler's "returns a pointer
to a threshold constant" rendering is an artifact and is **corrected
here** on listing evidence.

The function selects three thresholds (upper / mid / lower) **by current
state**, then re-classifies x:

| current state | upper | mid | lower |
|---|---|---|---|
| 1 | 4.0 | 0.0 | −5.0 |
| 2 | 6.0 | −1.0 | −5.0 |
| 3 | 5.0 | +1.0 | −6.0 |
| 4 | 5.0 | 0.0 | −4.0 |
| other (default) | 5.0 | 0.0 | −5.0 |

Transition (listing `0x180C57F2–0x180C582C`, `fcmp/gt` chain):
`x > upper → 1`; `mid ≤ x ≤ upper → 2`; `lower ≤ x < mid → 3`;
`x < lower → 4`.

This is a textbook Schmitt structure **[INF]**: the 1↔2 boundary sits at
5 with a ±1 deadband (from state 1, x must exceed 6 while in state 2 to
come back — read the table by *current* state), the 2↔3 boundary at 0
with ±1, the 3↔4 boundary at −5 with ±1. The differential x spans
roughly −6…+6; with a float minus a whole byte, and §4's 70.0 °F cap in
the same module, x is plausibly a temperature differential in °F
**[INF]**. What physical pair (CB58, CABB) feeds it was not isolated
(§12) — in particular it is **not** proven to be setpoint−room of the
main zone.

Consumers of the state byte **[FACT]**: FUN_180c5832 (§6, distinguishes
only 1 vs 2), FUN_18051cec (§7), and the sibling evaluators FUN_180c15d2
et al. (§12).

---

## 3. FUN_180c54d8 — 0/1/2 staging state machine (droop ratios)

**[FACT]** Body 282 B, entry `0x180C54D8`. Evidence:
`out/decomp3/decomp_180c54d8.c`, instruction listing
`out/listing_stage.txt`, raw pool reads (§11).

- Gate: if `*(byte*)0xFFF8CD7D != 2` → output `0xFFF8CD49 := 0`, done.
- Inputs: demand float `X = *(float*)0xFFF8CD44`; threshold table
  `T[i] = *(float*)(0xFFF8CCC4 + 4·i)` (runtime-filled); selected
  threshold `Tsel = T[*(byte*)0xFFF8CC5A − 1]` (1-based index).
- Constants (pool cells `0x180C5638/5640/5644`, raw-verified):
  **1.25** (`0x3FA00000`), **0.25** (`0x3E800000`), **0.01**
  (`0x3C23D70A`).
- State machine on current `S = *0xFFF8CD49` ∈ {0,1,2}:

| S | rule (listing-verified) |
|---|---|
| 0 | `X > Tsel×1.25` → **2**; else `S := (T[1]×0.25 < X) ? 1 : 0` |
| 1 | `X > Tsel×1.25` → **2**; else `S := (T[1]×0.01 < X) ? 1 : 0` |
| 2 | if `T[1]×0.01 < X`: `S := (Tsel ≤ X) ? 2 : 1`; else `S := 0` |
| other | `S := 0` |

Reading **[INF]**: stage 2 demands 125 % of the selected table
threshold; stage 1 engages at 25 % of `T[1]` from rest but, once
engaged (from S=1 or S=2), is held until demand falls to 1 % of `T[1]`;
stage 2 falls back to 1 at 100 % of `Tsel`. The 0.25-vs-0.01 asymmetry
is a wide stage-1 hysteresis — a minimum-demand hold, functionally a
droop/anti-short-cycle shape in the *demand* domain (not a timer; no
time constants appear in this function). The table at `0xFFF8CCC4` and
the index byte are runtime data — who fills them was not isolated
(§12); the heavyweight sibling FUN_180c15d2 reads the same table, index
and demand float (`out/users4.txt`).

---

## 4. FUN_180c55f2 — per-zone setpoint adjustment

**[FACT]** Body 322 B, entry `0x180C55F2`, sole caller FUN_181efdfc.
Evidence: `out/decomp1/decomp_180c55f2.c`, listing
`out/listing_stage.txt`, raw pool reads (§11).

- `D = clamp( *(float*)0xFFF8CB58 − (float)*(byte*)0xFFF8CABB, 0.0, 6.0 )`
  (pool `0x180C5894` = 0.0, `0x180C5650` = 6.0).
- For each zone i = 0…7, with presence check FUN_181f0428(i) (pool
  `0x180C5898`):
  - absent → `out[i] = A[i]`;
  - present, flag `0xFFF8CBA9[i] == 1` → `out[i] = A[i] − D/2`
    (divisor pool `0x180C58A4` = **2.0**), then if `out[i] < 70.0`,
    `out[i] = min(A[i], 70.0)`;
  - present, flag != 1 → `out[i] = min(A[i], 70.0)`.
- A = float[8] at `0xFFF8CABC`; out = float[8] at `0xFFF8CD50`.
- The 70.0 cap is read through pool cell `0x180C58AC` → flash address
  `0x1830B128`, whose stored word is `0x428C0000` = **70.0** (raw-read;
  the same cell is used by §5). The flash record around `0x1830B128`
  also contains floats **0.63** (`0x1830B120`) and **1.05**
  (`0x1830B124`) and the name `sys_ctrl_task` (`0x1830B12C`) — a
  descriptor/log-config record; only the 70.0 field is referenced by
  this module **[FACT]**, the neighbours' roles are unproven (§12).

**[INF]** With A read as per-zone setpoints, this is a demand-response /
load-shed style trim: flagged zones give up half of a system-wide offset
D (0…6 degrees), nobody exceeds 70.0. The dictionary names
`totalDemandReductionPercent` and the demand-response help texts (§9)
support the reading; the trigger (what sets CB58/CABB) is unisolated.

---

## 5. FUN_18183d34 — per-zone satisfaction averager

**[FACT]** Body 284 B, entry `0x18183D34`. Sole caller: FUN_18183c44
(direct call at `0x18183C78`), itself a coordinator that runs the
averager only when three enable bytes are all non-zero, then calls
FUN_18183d32 and FUN_18183f1e, and — if a flag byte is set and another
byte has bit `0x20` set — FUN_18184006. Evidence:
`out/decomp1/decomp_18183d34.c`, `out/decomp1/decomp_18183c44.c`,
listing `out/listing_quant.txt`, raw pool reads (§11).

Per present zone i (presence via FUN_181f0428, pool `0x18183EA0`):

- flag `0xFFF8CBA9[i] == 1`: contribution `3.0 − clamp(A[i] − B[i], 0.0, 3.0)`
  where A = `0xFFF8CABC`, B = `0xFFF8CB60` (pools `0x18183EA8/EAC`;
  clamps from pools `0x18183E70` = 0.0, `0x18183EB0` = 3.0);
- flag != 1: contribution `max(0.0, B[i] − 70.0)` — the same 70.0 flash
  constant at `0x1830B128` (pool `0x18183EB4`).

**Both** kinds of present zones count in the divisor (listing: the
count increment at `0x18183DF4` is reached from both branches — this
**corrects** the decompiler-only reading "averages over flagged zones").
If count = 0 the average is 0.0.

Decision on the average (pools `0x18183EB8` = **2.5**, `0x18183EC0` =
**1.5**; write target pool `0x18183EBC` → `0x3C12E6C4`):

- avg > 2.5 → `*(byte*)0x3C12E6C4 := 0`
- avg < 1.5 → `*(byte*)0x3C12E6C4 := 1`
- 1.5 ≤ avg ≤ 2.5 → byte unchanged (a hysteresis band).

The function returns nothing (listing `rts/n` at `0x18183E4E`); the
decompiler's "returns &2.5 / &1.5" is an artifact, corrected here. Its
prologue also computes the §2 differential `CB58 − CABB` into a register
that the loop then overwrites — dead code, noted for completeness.

**[INF]** B behaves like a per-zone temperature (compared against
70.0 °F), A like a per-zone target: for flagged zones the contribution
is a 0…3 "satisfaction" that falls as A−B grows; the output byte at
`0x3C12E6C4` is a dictionary-visible satisfied/not-satisfied flag with a
1.5/2.5 hysteresis. Which of A/B is setpoint vs temperature is not
provable from this function alone.

---

## 6. FUN_180c5832 — heat/cool source arbitration machine

**[FACT]** Body 884 B, entry `0x180C5832`, sole caller FUN_181efdfc
(computed call at `0x181F0002` via pool cell `0x181F0108`). Evidence:
`out/decomp1/decomp_180c5832.c`, pool resolution table in §11.

- Gates: if `*(byte*)0xFFF8CD7D != 2` or `*(byte*)0xFFF8CB5C != 1` →
  outputs `0xFFF8CD4A := 0`, `0xFFF8CD4C := 0`, return.
- Otherwise it is a state machine over its own state byte
  `0xFFF8CD4A` ∈ {0…5} (read at entry, rewritten in branches), driven by
  three sub-inputs: the §3 stage byte `0xFFF8CD49` ∈ {0,1,2}, the §2
  quantizer state `0xFFF8CD4B` (only values 1 vs 2 distinguished), and
  the helper FUN_180c5c7c (below). Outputs: `0xFFF8CD4A` (rewritten),
  flag `0xFFF8CD4C`, flag `0xFFF8CB48`, plus calls to eight tiny binding
  setters/getters at `0x181F066C…0x181F0752` in specific branches.
- Helper **FUN_180c5c7c** (204 B): scans the second flag array
  `0xFFF8C8BC[0…7]` for any zone == 1 (presence via FUN_181f0428);
  computes `u = (CD4A == 0 || (CD4A == 1 && FUN_181f066c() == 0)) ? 1 : 2`;
  picks a float threshold via FUN_18051cec(u) when
  `(*(byte*)0xFFF8CC52 & 0xF) < 2`, else via FUN_18051908(0, u) (§7);
  returns 1 iff some zone is flagged **and** threshold ≤
  FUN_18051e4e(`0xFFF8C8BC`) (the §7 weighted sum).

**[INF]** A 0…5 state with inputs {stage 0/1/2} × {quantizer 1/2} ×
{demand-met boolean} matches the dictionary's six-value heat-source
enumeration found at `0x18302E1C` — `cooling, hpheat, eheat, gas,
reheat, fangas` (§9) — i.e. this machine plausibly arbitrates *which
source serves the current demand* (dual-fuel / simultaneous heat-cool
territory). The exact state↔name mapping was **not** established; the
enum strings have no code references (dictionary-only), so the mapping
is recorded as inference, not fact.

The module initializer **FUN_180c549c** (60 B, sole caller FUN_181efdfc)
zeroes `0xFFF8CD49`, `0xFFF8CD4A`, `0xFFF8CD4B` and the byte[8] at
`0xFFF8C8BC` **[FACT]**.

---

## 7. Weighted zone demand and threshold getters

**FUN_18051e4e** (218 B) **[FACT]** — weighted sum over 8 zones:
`sum += zoneByte[i] × weight[i]`, weights = ushort table reached via
pool `0x18052004`; the result is then capped by a float-table value
`table[*(byte*)0xFFF8CC5A − 1]` from the table at `0xFFF8CCC4` (pools
`0x1805200C/10`) — the *same* runtime table and index byte as §3.
Evidence: `out/decomp3/decomp_18051e4e.c`.

**FUN_18051cec** (288 B) **[FACT]** — state-dependent constant getter:
if its selector argument == 5 and the §2 quantizer state
`0xFFF8CD4B` == 1 → returns the bits of **375.0** (flash `0x18051FF0` =
`0x43BB8000`, raw-verified); if the state is 2, 3 or 4 → **400.0**
(flash `0x18051FF8` = `0x43C80000`); otherwise returns its argument
unchanged. Evidence: `out/decomp1/decomp_18051cec.c` + raw reads.
**[INF]** 375/400 sit in a CFM-like numeric range and this getter feeds
the §6 helper's threshold comparison, but no unit is provable statically.

**FUN_18051908** (894 B) **[FACT, structure only]** — a two-point
interpolation getter: branches on a device-class word masked with
`0x7C00` (== `0x800` / == `0x4000` — the same class mask as stage C),
fetches two table values via FUN_18050c26(1)/(2), linearly interpolates
`(f4 + p·(f5 − f4))`, then applies a two-point slope correction through
function pointers (pools `0x18051D34/38/44`). It reads all three of
`0xFFF8CB58`, `0xFFF8CABB`, `0xFFF8CD4B`. Its exact physical meaning was
not settled (§12); it is the §6 helper's alternate threshold source.

---

## 8. Control-cycle timing and `sys_ctrl_task`

**[FACT]** Task creation, FUN_181f81be (34 B; `out/decomp2/`):

```
FUN_180bc084( *0xFFF8CE68, "sys_ctrl_task", FUN_181f81ae, 100,
              (void*)0x3C13790C, 0x800, 0 )
```

(name via pool `0x181F822C` → `0x1830B12C`; entry via pool `0x181F8228`
→ `0x181F81AE`; argument pointer `0x3C13790C` is dictionary space;
create wrapper FUN_180bc084 is in the same `0x180BCxxx` Clarinox helper
family as stage C's accessors. The `100` and `0x800` argument roles —
priority/stack in some order — are **[INF]**.)

Entry FUN_181f81ae (14 B): `FUN_181f816c(); do { FUN_181f7fc4(); } while (true);`

Init FUN_181f816c (66 B): registers a queue (call with args
`(DAT_181f81e8, 4, 5, DAT_181f820c)`), then polls a ready flag in a loop
whose body calls a delay with argument **100** (pool `0x181F821C` callee)
until the flag is non-zero, then calls one more setup function.

Loop body FUN_181f7fc4 (420 B; `out/decomp4/`):

- calls `PTR_FUN_181f81e0(0x10)` (a per-iteration service call —
  watchdog/notify role unproven);
- blocks on a queue receive with timeout **1000** (pool-rendered
  constant in the call `(queue, &msgIndex, 4, 1000)`);
- on a message: dispatches `handlerTable[msgIndex]()` — the table is a
  RAM function-pointer array (pool `0x181F81F4`); a NULL entry falls
  back to a default handler called with the index;
- measures the handler's duration with a time function called before
  and after, and maintains per-class statistics for indices < 12 in a
  0x10-byte-stride table: count (short, +2), max (+4), min (+8),
  running average (+0xC, float math with wrap correction constants).

**Conclusions [FACT]:** `sys_ctrl_task` is an event-driven message
dispatcher with a 1 s wake-up floor — not itself the HVAC algorithm.
The HVAC decisions (§2–§7) are binding computed properties, evaluated
when their inputs change, not on a visible fixed period.

**The 10 s burst period was not isolated [FACT, negative].** IntHunt
(`out/inthunt.txt`) + raw scan: BE word `10000` occurs 5 times in the
image (`0x182535B2`, `0x18261D9E` — unreferenced pool/data words;
`0x183DEF46`, `0x183DFCE6`, `0x18443CB3` — inside structured `0x27xx`
ID tables, increments of 8, i.e. not the number 10000 at all), **none
with a code reference**; `60000` occurs once (`0x1830CD1C`, dictionary
area, unreferenced); `30000` twice, unreferenced. There is no
`delay(10000)`-style constant in referenced code. Combined with the
stage-C precedent (a 1000 ms supervisor loop, FUN_180ba20a) and the 1 s
queue timeout above, the burst cadence is **[INF]** most plausibly
produced by a 1 s-ticked handler counting to 10 — consistent with the
captured 9.0–11.2 s jitter — but no counter was isolated (§12).

---

## 9. Parameter vocabulary: what exists on the thermostat side

### 9.1 Float-constant census [FACT]

FloatHunt (`out/floathunt.txt`) — BE float words in the image with
Ghidra code references: 0.5 → 131 occ / 38 refs; 1.0 → 1147 / 91;
1.5 → 7 / 3; 2.0 → 2024 / 47; 2.5 → 240 / 6; 3.0 → 21 / 12; 3.5 → 19 / 5;
4.0 → 170 / 4; 4.5 → 3 / 2; 5.0 → 69 / 8; doubles: zero references.
Functions referencing ≥ 3 of the stage-range values: FUN_18087c54,
FUN_180dd4a8, FUN_180ec188, FUN_18190684 (each {1,2,3} — unit-conversion
families on inspection), FUN_18183d34 ({1.5, 2.5, 3.0} — §5),
FUN_180c576c ({1, 4, 5} — §2), FUN_18206d84 ({2, 2.5, 5} — unit
conversion, decompiled and excluded). Two other 5.0-referencing
families (FUN_181a2dc2/FUN_181a2e74, FUN_18206cbc/d10/d84) were
decompiled and are field-store unit conversions (offset `0xD` selects
affine vs helper conversion) — **not** control code [FACT].

### 9.2 Sparkplug dictionary names [FACT]

Region `0x18300000–0x1830A200` is a packed Sparkplug B name dictionary
(`spBv1.0`, `WallCtrl`, NDATA/DDATA/NBIRTH/DBIRTH/NDEATH/NCMD/DCMD).
Control-relevant metric names (addresses in `out/recon2.txt`):
`system/heatsource`, `system/gasunit`, `system/cfgsimultheatcool`;
`idu/heatoffdelay`, `idu/auxheatlocktmp`, `idu/reheat`, `idu/mincfm`,
`idu/maxcfm`, `idu/mincfmenable`, `idu/maxcfmenable`, `idu/furnstages`;
`odu/coollocktemp`, `odu/heatlocktemp`, `odu/coollatchmode`,
`odu/coollatchtemp`, `odu/heatlatchmode`, `odu/heatlatchtemp`,
`odu/defrostbackup`, `odu/usercoollatch`, `odu/userheatlatch`,
`odu/usermincoolstage`, `odu/usermaxcoolstage`, `odu/userminheatstage`,
`odu/usermaxheatstage`, `odu/oducoolafl`, `odu/oduheatafl`,
`odu/quietshift`; bare `defrostInt`, `mincoolstage`, `maxcoolstage`,
`minheatstage`, `maxheatstage`, `opminheatstage` (`0x183029F8`) and
sibling `user*/avail*/op*` stage limits, `lockoutcount`,
`lockoutactive`, `lockouttime`, `lowstage`, `absmincfm`, `absmaxcfm`,
`calcMinCFM` (`0x1830289C`), `blowerSpeed`, `iducfm`, `pwmblower`,
`cfmlimitsvalid`, `vcapfloorcfm`, `vcapceilingcfm`, `vcapcfmfloor`,
`vcapcfmceiling`, `vcapcfmuplimit`, `blowerActualCFM`,
`blowerCoolingCFM`, `blowerHeatingCFM`, `blowerPower`, `systemCFM`,
`cfmlimit`, `heatMITO`, `coolMITO`, `totalDemandReductionPercent`.
Heat-source enumeration strings at `0x18302E1C`:
`cooling, hpheat, eheat, gas, reheat, fangas` (repeated slash-prefixed
at `0x183030A4`).

These names prove the *settings and telemetry exist* in the data model
— including thermostat-side lockout temps, latch temps, defrost backup
and interval, user stage limits, and a CFM limit model (`calcMinCFM`,
`vcap*cfm*`). **No code consumer of any of these names was isolated**
(the dictionary is name-only; bindings are runtime-registered), so no
numeric defaults for lockouts/latches/defrost could be extracted this
pass (§12).

### 9.3 Installer help texts [FACT — texts; INF — algorithm reading]

Contiguous UI help strings at `0x182D8C08–0x182DA6D0` (raw-extracted)
document, in the installer's own words:

- High-stage latches: "Above this temperature, only high stage
  operation is allowed" (cool latch), "Below this outdoor temperature,
  only high stage operation is allowed" (heat latch), an `ALWAYS`
  option (`0x182D8CD8–0x182D8DB4`).
- Defrost fan delay: fan runs "approximately **12 seconds**" after a
  defrost cycle to reduce reversing-valve noise (`0x182D8DDC`).
- HP low airflow multiplier: "used for non-communicating two-stage
  outdoor units. **0.63** is used for Bristol compressors and **0.8**
  …" (`0x182D9010`). A float **0.63** also sits in the flash record at
  `0x1830B120` (§4) — single-method co-location, role unproven.
- Stages/Latch Cooling/Heating: installer-set min/max stage, with an
  optional outdoor temperature at which the minimum stage limit is
  enforced, or "always" (`0x182D90C0–0x182D91F4`).
- GeoHP staging override: overrides the **down-staging algorithm** so
  the system "will meet the heat demand and not allow down-staging"
  (`0x182D9350`); GeoHP WindUp "decreases the rate at which the Heat
  Pump will stage up" (`0x182D983C`) — direct evidence a stage-up /
  stage-down *rate* algorithm exists in the control core.
- Furnace staging control: "**System staging** provides full
  modulation. **Furnace staging** uses the furnace['s] internal staging
  algorithm. **Low staging** runs the furnace at its lowest stage.
  **High staging** runs the furnace at its highest stage."
  (`0x182DA4C4–0x182DA5A8`)
- Simultaneous Heating and Cooling Demand Mode for zoning
  (`0x182D9B74`); a minimum enforced difference between heating and
  cooling setpoints (deadband, `0x182D9C5C`); recovery: "System will
  start recovery **90 minutes** prior to schedule change"
  (`0x182D9EE0`); heat-off delay = blower run-on after heating
  (`0x182DA5E8`, cf. `idu/heatoffdelay`).

---

## 10. Cross-check against captures (THERMOSTAT-PROTOCOL-MAP.md)

| Capture fact | Firmware finding | Verdict |
|---|---|---|
| `0305[0]` heat stage ∈ {0,1,2}; stage 2 only at top of a 75→79 °F staircase vs 72 °F room; stage 1 at moderate demand | FUN_180c54d8 (§3) is a 0/1/2 machine: stage 2 needs demand > 125 % of threshold, stage 1 engages at 25 % | **Consistent in shape** [INF]; identity unproven — no static path from `0xFFF8CD49` to the `0305` payload |
| One residual stage-2 write after the call, then idle | §3 holds stage ≥ 1 until demand ≤ 1 % of `T[1]`, and stage 2 until demand ≤ 100 % of `Tsel` — a demand-domain rundown, no timer | **Consistent** [INF]; a timer-based rundown is neither proven nor excluded |
| `0305` idle = all zeros + `0x78` at [11] | No writer of either the payload or a `0x78` constant in a demand context was isolated | **Open** — neither agreement nor contradiction obtainable |
| CFM values 0, 379…1760 in `0305[4..5]`; fan-only 1166 → 379 | CFM exists as a data-model (`calcMinCFM`, `absmincfm/maxcfm`, `vcap*cfm*`, `blower*CFM`, §9.2); the §7 constants 375.0/400.0 are CFM-range but unlinked; no CFM computation isolated | **Open** |
| `0605` float stage: only 0.0 and 5.0 ever observed (gap G8) | No constant-selecting stage table exists in code (§9.1); the only discrete demand levels found are 4 (quantizer) and 3 (staging machine), neither tied to `0605` | **Not contradicted**; G8 remains open — code does not prove partial stages are ever emitted, nor that they cannot be |
| `060D` = 02 during any heat/cool call, 00 idle/fan-only | Writer not isolated. The §6 machine's flags (`0xFFF8CD4C`, `0xFFF8CB48`) are candidate-shaped (set during arbitrated calls) but unlinked to the bus | **Open** |
| Write burst every ~10 s (median 10.00, 9.0–11.2) | No 10000 ms constant in referenced code (§8); control task is a 1 s-timeout dispatcher; decisions are change-driven binding properties | **Consistent with** a 1 s tick × 10 structure [INF]; the producer of the period is unisolated |
| Furnace is 2-stage gas, 107K BTU/H (installer photo) | Furnace staging help (§9.3) confirms a thermostat-side staging mode exists ("System staging provides full modulation" vs furnace-internal) | **Consistent**; which mode the author's install uses is a setting, not visible in firmware |

No capture fact was **contradicted** by the firmware this pass. The two
hard capture numbers that firmware constants could have falsified —
stage cardinality (0/1/2) and the absence of partial 0605 stages — both
survived contact with the code.

---

## 11. Dual-verification log

Methods: **D** = Ghidra decompiler; **L** = Ghidra instruction listing;
**R** = raw big-endian word read of `flat_trim.bin` (offset = addr −
0x18040000); **G** = Ghidra reference graph (UsersOf two-level trace);
**S** = raw string/byte scan.

| Claim | Methods | Result |
|---|---|---|
| §2 thresholds 5.0 / 0.0 / −5.0 defaults; state overrides 4.0, 6.0, −1.0, +1.0, −6.0, −4.0 | D + L + R (pools `0x180C5894…0x180C58D8`) | Agree. **Listing corrects the decompiler** on which state owns −1.0 vs +1.0 (state 2 → −1.0, state 3 → +1.0); table in §2 is the listing version |
| §2 transition map (x>upper→1, mid≤x≤upper→2, lower≤x<mid→3, x<lower→4) | D + L (`fcmp/gt` chain `0x180C57F2–582C`) | Agree |
| §2 returns nothing; output is state byte only | L (no result setup before `rts/n`) vs D (claimed pointer return) | **Listing wins**; decompiler artifact recorded |
| §2/§4/§5 input pair `0xFFF8CB58` float, `0xFFF8CABB` byte | D + L (`fmov.s @r1` vs `mov.b @r1` + `float fpul`) + G (pool cells) | Agree |
| §3 constants 1.25 / 0.25 / 0.01 | D + L (`fmul` at `0x180C551A/5538/5580`) + R (`0x3FA00000/0x3E800000/0x3C23D70A`) | Agree |
| §3 gate `0xFFF8CD7D == 2`, state dispatch, write-backs to `0xFFF8CD49` | D + L (`cmp/eq 0x2` at `0x180C54E0`; `mov.b r1,@r7 -> fff8cd49 WRITE`) | Agree |
| §3 table base `0xFFF8CCC4`, index byte `0xFFF8CC5A` (1-based), demand `0xFFF8CD44` | D + R (pool cells `0x180C5630/34/3C`) + G | Agree |
| §4 clamp [0.0, 6.0], divisor 2.0 | D + R (pools `0x180C5894/5650/58A4`) | Agree (listing spot-checked) |
| §4/§5 cap constant 70.0 at flash `0x1830B128` | D + L (`fmov.s @r1 -> 1830b128 READ` in §5) + R (`0x428C0000`) | Agree |
| §5 clamps [0.0, 3.0]; thresholds 2.5 / 1.5; output byte `0x3C12E6C4` | D + L (`0x18183DA2–DB4`, writes at `0x18183E34/E46`) + R (pools `0x18183E70/EB0/EB8/EC0`) | Agree on values; **listing corrects** the divisor set (both zone kinds count) and the void return |
| §6 gates, state byte `0xFFF8CD4A`, sub-inputs `0xFFF8CD49/CD4B` | D + R (full pool resolution of FUN_180c5832, 48 cells) | Single-function D+R; no listing pass — marked **one-and-a-half method** |
| §7 constants 375.0 / 400.0 | D + R (`0x18051FF0 = 0x43BB8000`, `0x18051FF8 = 0x43C80000`) | Agree |
| §7 weighted sum + cap via same table/index as §3 | D + R (pools `0x18052004/0C/10`) | Agree (structure) |
| §8 task name/entry/args | D + R (pools `0x181F8224…8234`: entry `0x181F81AE`, name `0x1830B12C`, arg `0x3C13790C`) + S (string bytes at `0x1830B12C`) | Agree |
| §8 queue timeout 1000; 12 message classes; stats stride 0x10 | D only | **Single-method** — flagged |
| §8 negative: no referenced `10000` constant | G (IntHunt: 5 occ / 0 refs) + S (raw scan, same 5 sites, contexts inspected) | Agree |
| §9.1 float census counts | G (FloatHunt) + S spot checks | Agree |
| Module caller graph (FUN_181efdfc sole caller of §2/§4/§6/init) | G (UsersOf F: mode, computed-call sites + pool cells) | Single-method (reference graph only) — flagged |

---

## 12. Not-isolated list

Explicitly **not** found this pass, with the space searched:

1. **The `0305` payload writer** (heat stage [0], cool stage [2], CFM
   [4..5]) and **the `0x78` constant at [11]**. Searched: float/int
   constant censuses, the full zone-demand module and its consumers
   (UsersOf over every module variable), task creation records. The
   writer sits behind runtime-registered dispatch / dictionary device
   objects (stage D's transmit path may bound it from the other side).
2. **The `0605` stage-float writer and the `060D` flag writer.** Same
   search space. G8 (partial stages) therefore stays open (§10).
3. **The CFM computation** behind `0305[4..5]` (observed 379–1760).
   The CFM *limit model* exists as dictionary names (§9.2); no consumer
   code isolated. The 375.0/400.0 constants of §7 are unlinked.
4. **Physical identity of the §2/§5 inputs** — who writes `0xFFF8CB58`,
   `0xFFF8CABB`, the arrays `0xFFF8CB60/CABC`, flags `0xFFF8CBA9/C8BC`,
   and which array is setpoint vs temperature. UsersOf shows only
   pool-cell loads (read/write of the target byte is not distinguishable
   in the reference graph); the producers are other binding properties.
5. **Who fills the §3 threshold table** `0xFFF8CCC4`, the index byte
   `0xFFF8CC5A`, and the demand float `0xFFF8CD44`. The prime suspect,
   **FUN_180c15d2** (the module's heavyweight evaluator, reading the
   whole variable cluster), was identified but **not decompiled** this
   pass; same for siblings FUN_180c3012, FUN_180c3418, FUN_180c3814,
   FUN_180c3bee, FUN_180c46b8, FUN_180c49ec, and consumers FUN_18184006,
   FUN_181f21d4, FUN_181f4308, FUN_181f4e60, FUN_1816deec, FUN_180d2728.
6. **The §6 state↔source mapping** (which of 0…5 is gas vs hpheat vs
   eheat…): the enum strings are dictionary-only, no code references.
7. **FUN_18051908's physical meaning** (interpolation getter, §7) and
   the tiny binding functions at `0x181F0428` (zone presence),
   `0x181F066C…0x181F0752` (used by §6), `0x181F06AE` family.
8. **Numeric defaults for lockouts / latches / defrost** (aux-heat
   lockout temp, HP lockout temps, latch temps, defrost interval,
   min/max stage defaults): settings exist (§9.2/§9.3); their storage
   (field-store offsets) and consumers were not isolated.
   Min on/off times and stage timers: **no timer constants were found
   in any isolated decision function** — the staging hysteresis found
   is purely demand-domain (§3). Whether timer-based staging exists in
   the unisolated core is unknown; the GeoHP texts (§9.3) prove a
   stage-rate algorithm exists somewhere.
9. **The producer of the ~10 s burst period** (§8): no referenced
   10000 ms constant; the dispatcher's handler table is RAM-registered,
   so the periodic handler (if any) is not statically enumerable.
10. **The flash record at `0x1830B108–0x1830B13B`** (halfword pairs
    175/300, 200/300, 350/325, 325/325, 350/350, 400/0; floats 0.63,
    1.05, 70.0; name `sys_ctrl_task`; followed by a log-module name
    pointer table): only the 70.0 field is code-referenced (§4). The
    rest is **[INF]** a per-module descriptor/log config; the 0.63
    co-location with the help text's Bristol multiplier is noted but
    unproven.

---

## Appendix A. Function inventory (this pass)

| Function | Size | Role |
|---|---|---|
| FUN_181efdfc | 638 B | zone-model binding refresh; sole caller of §2/§4/§6/init; writes `0xFFF8CD7D` |
| FUN_180c549c | 60 B | module init (zeroes CD49/CD4A/CD4B, `0xFFF8C8BC[8]`) |
| FUN_180c54d8 | 282 B | §3 staging machine 0/1/2 |
| FUN_180c55f2 | 322 B | §4 per-zone setpoint adjustment |
| FUN_180c576c | 198 B | §2 four-level quantizer |
| FUN_180c5832 | 884 B | §6 source arbitration 0…5 |
| FUN_180c5c7c | 204 B | §6 helper (demand-met check) |
| FUN_18183c44 | 102 B | §5 coordinator |
| FUN_18183d34 | 284 B | §5 satisfaction averager |
| FUN_18051cec | 288 B | §7 state-dependent constant (375.0/400.0) |
| FUN_18051908 | 894 B | §7 interpolation getter (meaning open) |
| FUN_18051e4e | 218 B | §7 weighted zone-demand sum |
| FUN_181f81be | 34 B | `sys_ctrl_task` creation |
| FUN_181f81ae | 14 B | `sys_ctrl_task` entry (init + loop) |
| FUN_181f816c | 66 B | task init (queue register; ready-poll, delay 100) |
| FUN_181f7fc4 | 420 B | dispatcher loop (1000 ms timeout, 12 classes, stats) |
| FUN_180bc084 | — | Clarinox task-create wrapper (stage-C helper family) |

## Appendix B. Artifacts

All under `~/workspace/diy-thermostat/firmware-re/stageE/`:
`scripts/` (FloatHunt.java, IntHunt.java, UsersOf.java + stage-C
scripts), `run1.sh…run10.sh` with logs, `out/recon1.txt` (string recon),
`out/recon2.txt` (dictionary recon), `out/floathunt.txt`,
`out/inthunt.txt`, `out/users1.txt…users4.txt` (reference traces),
`out/decomp1…decomp4/` (decompilations), `out/listing_quant.txt`,
`out/listing_stage.txt` (instruction listings). The Ghidra project copy
is `proj/`; stage-B/C projects and `stageD/` were not modified.
