# FIRMWARE-ANALYSIS-S — Stage S: system MODE semantics, settled from code

Image: `BINF0479_Carrier.hex` (official 4.79, byte-identical to the unit's, per
FIRMWARE-ANALYSIS-VERSIONS). CPU Renesas SH-2A BE, base 0x18040000.
Work dir: `firmware-re/stageS/` (decompiles in `out/`, censuses in `out/users_*.txt`).
[FACT] = proven from the image with address + mechanism. Inference is labelled.

## 0. Verdict

**The internal mode byte CD7D (0xFFF8CD7D) is: 1 = HEAT, 2 = COOL, 3 = AUTO /
no-single-direction.** Proven three independent ways (§3). The external
SYSCTRL-49 hypothesis (heat 0 / cool 1 / auto 2 / off 5) does **not** match
either internal encoding (§6) — it is a third, SAM-side encoding whose
firmware-side bridge is runtime-bound (stages F/N boundary); the live
mode-experiment session is still needed for that one byte, and only that byte.

## 1. The mode chain end-to-end [FACT]

Three writer paths converge on CD7D (stage L §3.5), now fully traced:

### 1a. The mode state machine — FUN_1815d67e (the authority)

`FUN_1815d67e` (0x1815D67E, 1004 B) maintains a byte pair in a dedicated RAM
record at **0xFFF8AE44**:

| Cell | Role |
|---|---|
| AE44 | coarse mode — the byte FUN_1815da86 returns into CD7D |
| AE45 | detailed state ∈ {1..5} (the machine's state variable) |
| AE46 | previous AE47 (edge copy, written at exit) |
| AE47 | **requested-mode byte R** ∈ {0..4} (see §4) |
| AE48 | call flag for direction 2 (set by FUN_1815daaa) |
| AE49 | call flag for direction 1 (set by FUN_1815daaa) |
| AE4C/AE4D | auto-arbiter decision flags (FUN_1815e01c) |
| AE4E | "pair changed" flag (set by FUN_1815dfd2, returned, cleared at entry) |
| AE50 | equipment class word (field-store field 1, via FUN_1815927c) |
| AEC4 | field 0x1B byte — changeover timer minutes (×60 in FUN_1815dfb0 → FUN_1809fde2) |
| AEC5 | this group's registered dictionary property (FUN_1809fa76/FUN_1809fd7e) |

Ingestion `FUN_1815dc40` (called at FUN_1815d67e entry) copies, per run:
AE84 ← mirror 0xFFF83C58 (32 B), AE64 ← mirror 0xFFF83C38 (32 B),
AEA4 ← mirror 0xFFF82160 (32 B), AE52 ← 0xFFF821A0 (8 B), AE5A ← 0xFFF83CB3
(8 B), **AE47 ← 1 byte from mirror 0xFFF82EED**, AE50 ← field 1,
AEC4 ← field 0x1B.

The (AE44, AE45) pairs the machine writes are exactly
{(3,1), (1,2), (1,3), (2,4), (2,5)} — i.e. AE45→AE44: **1→3, 2→1, 3→1, 4→2,
5→2**. Default (AE45 ∉ {1..5}, incl. power-on garbage): registers the property
(FUN_1809fa76 on 0xFFF8AEC5, callback FUN_181f75de) and parks at **(3,1)**.
When AE44 == 3 at exit, `FUN_1815dcee` publishes the pair to mirrors
0xFFF83E28 (AE45) / 0xFFF83E2C (AE44) under lock (FUN_180bc05a/180bc06e),
unless the zone predicate FUN_181abce0 fires, in which case FUN_181abdfa runs.

### 1b. Refresh path — FUN_181efdfc → FUN_1815da86

Refresh writes `CD7D = FUN_1815da86()` (pool 0x181F00DC → 0x1815DA86,
raw-verified). FUN_1815da86: if the zone predicate FUN_181abce0() == 0
(field 0x11E bit0 vs. count of flagged zones among 8 bytes at 0xFFF8BB6E,
predicate FUN_181f0344) → return **AE44**; else return *(byte*)**0xFFF8BB5C**
(a second mode mirror, hub functions FUN_181ab600/FUN_181ab6ec — a sibling
binding group; its value semantics were not separately decoded, flagged in §8).

### 1c. FUN_181f5d8a path — the EC64 byte is a validity flag, not the mode

FUN_181f5d8a: `c = FUN_181f6ffe(); if (c == 0) { c = FUN_1815da86(); CD7D = c; }`
— the CD7D store happens **only in the fallback branch** (decompile,
`firmware-re/stageS/out/decomp_181f5d8a.c`). FUN_181f6ffe returns
*(byte*)**0x3C12EC64**, a byte inside the sys_ctrl dictionary object
(0x3C12EC68 = its FSM state, 0x3C12EC70 = handler table, stage G). Its only
pool-cell writers are FUN_181f6fee (`*EC64 = 0`, called from the sys_ctrl post
helper FUN_181f84fc) and FUN_181f6ff6 (`*EC64 = 1`, called at the head of
FUN_181f4308). So EC64 ∈ {0,1} statically: a "mode already ingested from the
record" flag. When EC64 == 1, FUN_181f5d8a skips the CD7D write and uses the
local value 1 only for its own C874/C878 branch selection. The dictionary does
contain mode properties — `system/mode` @0x1830098C and bare `opmode`
@0x18307F14 (stage H inventory) — but no static path ties either name to
EC64's byte; the name↔cell binding is runtime-built (stage F/N boundary).

### 1d. Record path — FUN_181f4308 ← mirror record at 0xFFF82E0D

FUN_181f4308 first sets EC64 = 1 (FUN_181f6ff6), then copies 11 bytes
0xFFF82E0D → 0xFFF8C5A0 (FUN_1823d404) and writes **CD7D = C5A0[0]**, plus
mirror 0xFFF83E2C = CD7D, presets CB4D=1, CD3F=1, CD43=1, **CD4B=4**, CB48=0,
and CD4A = 4 if (byte 0xFFF8CA94 ≠ 0 && CD7D == 2) else 0; then computes
CD8C by CD7D (==2 → interp(CCC4); ==1 → interp(CC34)+interp(CCDC);
else → interp(CCDC)).

The record's producer is **FUN_180ecb96**: assembles at scratch 0xFFF8796A —
[0]=param_3, [1..4]=param_1 BE, [5..8]=param_2 BE, [9]=param_4, [10]=0 — and
publishes to 0xFFF82E0D under lock. All five caller groups
(FUN_180eb67e, FUN_180ec188, FUN_180ec36c, FUN_180ec7ce, FUN_180ec850 — the
0x180EB/EC replication cluster for dictionary object 0x3C12A8xx) pass
**param_3 ∈ {0,1,2} only** (1/2 selected by class-word bits and dictionary
bytes; 0 from FUN_180ec850 and one FUN_180ec7ce branch). The two floats seen:
1.0/2.0/3.0 (FUN_180ec188, by dictionary byte 0x3C12A8E0 ∈ {1,3,5}), a computed
float (FUN_180ec36c), 0.0/2.0 (FUN_180eb67e), integer 3 (FUN_180ec7ce) —
semantics not mode-relevant, not decoded (§8).
[INFERENCE] Record[0] is the **active direction** (0 none, 1 heat, 2 cool —
same values as CD7D), not the user mode: it never carries 3, while AE44
carries 3 for AUTO. In AUTO the two differ; which path wins a given refresh
cycle is a runtime scheduling question (§8).

## 2. AE45 — the five detailed states [FACT for structure]

State variable AE45, coarse projection AE44 in brackets:

- **1 [3]** — AUTO / no-direction state. Entered at power-on default and from
  any direction state when R ∈ {3,4}. With R == 0 it arbitrates direction by
  demand (FUN_1815e01c, §3) → exits to state 3 or 5.
- **2 [1], 3 [1]** — direction-1 states; toggled by call flag AE49
  (state 2: AE49 == 0 → 3; state 3: AE49 ≠ 0 → 2).
- **4 [2], 5 [2]** — direction-2 states; toggled by call flag AE48
  (state 4: AE48 == 0 → 5; state 5: AE48 ≠ 0 → 4).

Transitions: R == 1 → direction-1 states; R == 2 → direction-2 states
(crossing to the opposite direction passes through (3,1) when the equipment
word AE50 has &0x20 set and &0x7C00 ≠ 0x800, calling FUN_181f026e);
R ∈ {3,4} → (3,1); R == 0 in state 3: if zone cool-demand test FUN_1815defc
passes → state 5; in state 5: if zone heat-demand test FUN_1815de74 passes →
state 3. FUN_1815dfb0 arms an engine timer of AEC4×60 s on several
transitions (changeover delay; field 0x1B = delay minutes).

## 3. Which direction is heat — the proof [FACT, triple-verified]

Array identities are proven by FUN_1815dc40's copy sources: AE64 ← 0xFFF83C38
= the CADC source mirror and AE84 ← 0xFFF83C58 = the CABC source mirror
(stage L §3.3), AEA4 ← 0xFFF82160 (zone temperatures). The demand chain
(stage L §3.4) forces CADC = heat setpoints, CABC = cool setpoints:
CD7D==1 demand = max(CADC) + 0.75 − temp (positive when cold),
CD7D==2 demand = temp − (min(CABC) − 0.75) (positive when hot); the swapped
assignment makes both demands physically backwards.

1. **Auto arbiter FUN_1815e01c**: sums over active zones
   heat-demand Σ(AE64 − AEA4) and cool-demand Σ(AEA4 − AE84); if
   heat-sum < cool-sum → AE4C=1 → direction **2**; else AE4D=1 → direction
   **1**. The larger demand wins ⇒ 1 = heat side, 2 = cool side.
2. **Changeover tests**: FUN_1815defc (AEA4 − AE84 ≥ 0.5 °F, i.e.
   temp − coolSP) is consulted in state 3 [dir 1] and switches to state 5
   [dir 2]; FUN_1815de74 (AE64 − AEA4 ≥ 0.5, heatSP − temp) in state 5
   switches to state 3. A state leaves for the opposite direction when the
   *opposite* demand appears ⇒ dir 1 = HEAT, dir 2 = COOL.
3. **Call flags FUN_1815daaa**: with demand float > 0, AE44==2 sets AE48,
   AE44==1 sets AE49; AE49 toggles only the dir-1 states (2↔3) and AE48 only
   the dir-2 states (4↔5) in FUN_1815d67e — internally consistent.

**∴ CD7D / AE44: 1 = HEAT, 2 = COOL, 3 = AUTO (no single direction).**
Corroborated across the cluster: every consumer distinguishes {1, 2, other}
the same way — FUN_180c15d2 and FUN_180c3418 select table CCDC for 1, CCC4
for 2 (raw-verified pools 0x180C3678→CCDC, 0x180C367C→CCC4);
FUN_180c5dd0 normalises CD7D to {0,1,2}; FUN_181f07ec branches ==1;
FUN_180c46b8 composes outputs for 1/2/3; FUN_180c3012 (defrost evaluator)
selects direction-specific thresholds for 2 vs 1 with a 300 s timer.

**Cross-stage flag:** stage E matched FUN_180c54d8 (gate CD7D==2) to the
0305[0] heat staircase from captures. With ==2 now proven COOL, that machine
is the **cool-side staging machine** (or the CD49→0305[0] capture reading is
wrong — the link was never statically proven, stages F/N). For the author's gas
furnace the heat staging producer remains unisolated; the sibling evaluators
(FUN_180c3012/3418/3814/3bee/46b8) are the candidates. This does not affect
the mode verdict, but stage E §10's "gate consistent with heat" remark is
superseded by this stage.

## 4. R (AE47) — the requested-mode byte [FACT for behaviour]

R is copied each cycle from mirror 0xFFF82EED (no pool-cell writer exists —
runtime/bulk-written, §8). Its effect in FUN_1815d67e:

| R | Effect |
|---|---|
| 0 | demand decides (auto behaviour: arbiter in state 1, defc/de74 changeover in states 3/5) |
| 1 | force direction 1 (HEAT) |
| 2 | force direction 2 (COOL) |
| 3 | park at (3,1) — no direction |
| 4 | park at (3,1) — no direction |

[INFERENCE — strong] R = {0 auto, 1 heat, 2 cool, 3 fan-only, 4 off}: the
value order matches the UI help-string order in the image
(auto / heat / cool / fan only / off @0x182D7CEC–0x182D7DD8), and fan-only and
off are exactly the two user modes that park the direction machine. Code
alone cannot separate 3 = fan-only from 3 = off.

## 5. CD7D comparison map (decision cluster) [FACT]

| Consumer | CD7D use |
|---|---|
| FUN_180c54d8 (staging) | gate == 2 (cool staging, §3 flag) |
| FUN_180c5832 (source arbitration) | gate == 2 (and 0xFFF8CB5C == 1), else CD4A=CD4C=0 |
| FUN_180c62fc (zone aggregator) | == 3 → FUN_180c5f5c per-zone path; else FUN_180c5dd0/5e00/5e16/5e3c/5ebc |
| FUN_1816deec (demand) | == 1 heat chain (CADC, +0.75, tracked max); == 2 cool chain (CABC, −0.75, tracked min); else demand = 0 |
| FUN_181f5d8a (C874/C878) | == 2 → getter FUN_180504f2 only; == 1 → getter FUN_18050a68 only; else both, max, floored by CC1C table |
| FUN_181f4308 (CD8C) | == 2 → interp(CCC4); == 1 → interp(CC34)+interp(CCDC); else interp(CCDC) |
| FUN_180c15d2 (interpolator) | == 1 → CCDC set; == 2 → CCC4 set; CD4A 0..3 segment adjust |
| FUN_180c3418 | == 1 → table CCDC; == 2 → table CCC4; else 0.0 |
| FUN_180c5dd0 | returns 1 / 2 / 0 (clamp) |
| FUN_18183ecc | requires CD7D == 2 (with two more bytes == 2) |
| FUN_18086a8c | == 1 / == 2 select float compare sides |
| FUN_180c3012, 180c3814, 180c3bee, 180c46b8, 1804e4b6, 1805002a, 18052354, 1809f4a4, 180d28c8, 181f4d04, 181f017e, 181f7050, 18226ab4 | read CD7D; distinguished values never outside {1,2,3} (full census: `out/users_cd7d.txt`, 46 pool cells) |

No consumer anywhere tests CD7D == 0, == 4 or == 5: outside {1,2,3} the byte
is inert ("other" branch). The emulator needs exactly three values.

## 6. SYSCTRL-49 hypothesis — REJECTED as an internal encoding [FACT]

Three distinct encodings exist and must not be conflated:

| Encoding | Values | Source |
|---|---|---|
| CD7D / AE44 (internal coarse) | **1 heat, 2 cool, 3 auto** | this stage, §3 |
| R / AE47 (internal requested) | **0 auto, 1 heat, 2 cool, 3 fan-only?, 4 off?** | this stage, §4 |
| SYSCTRL byte 49 / 3B02[22] stagmode (SAM-side) | 0 heat, 1 cool, 2 auto, 3 electric, 4 heatpump, 5 off | infinitive (external), MODE-EXPERIMENT.md |

The hypothesis "heat 0 / cool 1 / auto 2 / off 5" matches the *external*
stagmode list, not anything inside the decision module: no internal byte
uses 0 = heat or 5 = off. The translation between the SAM-side byte and R
happens in the sys_ctrl object's runtime-registered replication (the same
boundary stages F and N hit for the frame serializer); it is not statically
recoverable. The dictionary names `system/mode` and `opmode` exist, but
their storage cells are assigned at discovery time.

## 7. State bytes CD49 / CD4A / CD4B / CD4C [FACT, except CD4A names]

- **CD49 (0xFFF8CD49) — staging output ∈ {0,1,2}**, written by FUN_180c54d8
  (thresholds CCC4[CC5A], ratios ×1.25 up / ×0.25 hold / ×0.01 drop, stage E
  §7–8), gated CD7D == 2 → cool-side staging per §3. Consumed by
  FUN_180c5832 and the bulk mirror FUN_181f4e60.
- **CD4B (0xFFF8CD4B) — demand quantizer state ∈ {1,2,3,4}**, written by
  FUN_180c576c (state cell raw-verified → CD4B): a 4-level Schmitt quantizer
  of a demand differential (stage E §6: bands at +5 / 0 / −5), preset to 4 by
  FUN_181f4308. Consumed by FUN_180c5832 (branches on CD4B ∈ {1,2} vs {3,4})
  and FUN_180c15d2's neighbourhood.
- **CD4A (0xFFF8CD4A) — source-arbitration state ∈ {0..5}**, written by
  FUN_180c5832 and preset by FUN_181f4308 (4 if CA94≠0 && CD7D==2, else 0).
  FUN_180c5832 runs **only when CD7D == 2 and 0xFFF8CB5C == 1**; otherwise it
  forces CD4A = 0, CD4C = 0. So for heating (CD7D == 1) CD4A is pinned to 0 —
  the arbitration is cool-side only (heat-pump / reheat equipment variants).
  Transition table (gate passed; inputs CD49 stage, CD4B band):
  CD49 == 2 → CD4A = 5 (all branches); CD49 == 1 → 3 if CD4B ∈ {1,2},
  4 if CD4B ∈ {3,4}; CD49 == 0 → 0/1/2 by predicates FUN_180c5c7c and
  PTR_FUN_180c5b78 when CD4B ∈ {1,2}, 0/4 when CD4B ∈ {3,4}; CD4A is sticky
  (previous value selects the branch family). Consumed by FUN_180c15d2
  (segment adjust for values 0..3), FUN_180c3012, FUN_180c3fea, FUN_180c4224,
  FUN_18051898, FUN_180d2728, FUN_1816deec, FUN_18183ecc.
  The dictionary enum at 0x18302E1C lists `cooling, hpheat, eheat, gas,
  reheat, fangas` — **the index↔name binding remains UNPROVEN** (stage E's
  guess stands as a guess; the observed transitions — 5 at full stage-2
  demand in a cool-gated machine — do not sit comfortably with 5 = fangas,
  so the listed order is probably not index order). For the emulator:
  implement the transition table, not the names; on the author's equipment
  CD4A ≡ 0 in heat and follows the table in cool.
- **CD4C (0xFFF8CD4C) — arbitration-internal latch ∈ {0,1}**: referenced
  only inside FUN_180c5832 (census: 2 pool cells, both in that function).
  Set 1 when CD4A-in == 1 or ∈ {2,3}; 0 when CD4A-in ∈ {4,5}, CD4A-in == 0,
  or the gate fails. No external consumer — the emulator may treat it as
  internal state of the arbitration machine (roughly "arbitration in the
  primary-source region").

## 8. What still needs the live mode-experiment session

1. **SYSCTRL byte 49 (and 3B02[22]) per wall state** — the only remaining
   mode unknown. Read both in Heat / Cool / Auto / Off (kit already built:
   MODE-EXPERIMENT.md) and correlate against the now-known internal values:
   expect SYSCTRL to follow the external list in §6, R to follow §4.
   This also separates R's 3 vs 4 (fan-only vs off) — set fan-only on the
   wall and watch which value appears.
2. **Record[0] in AUTO** — whether the 0xFFF82E0D record carries the active
   direction while AE44 carries 3 (inference in §1d). Bus-visible only
   indirectly; low priority — the emulator controls both paths itself.
3. **0xFFF8BB5C mirror semantics** — the alternate CD7D source FUN_1815da86
   returns when the zone predicate fires. Not decoded (hub FUN_181ab600 /
   FUN_181ab6ec); if its values ever disagreed with AE44, CD7D could take
   non-{1,2,3} values. A capture-driven check (correlate CD7D-visible
   behaviour) or a follow-up static pass on the 0x181AB6xx group closes it.
4. **CD4A name binding** — only if the emulator ever needs heat-pump/reheat
   sources; irrelevant for gas heat + inverter cool.
5. Record floats at 0xFFF82E0D[1..8] (values 0.0/1.0/2.0/3.0/integer 3 seen)
   — not mode semantics; left for the stage/capacity stages (O/R).

## 9. Emulator encoding table (implement this)

```
User mode      R (AE47)   AE44/CD7D   AE45 states        Notes
AUTO           0          3           1 ⇄ 3/5 by demand  arbiter FUN_1815e01c; changeover tests 0.5 °F; delay = field 0x1B min
HEAT           1          1           2 ⇄ 3 by AE49      demand: max(heatSP)+0.75 − temp
COOL           2          2           4 ⇄ 5 by AE48      demand: temp − (min(coolSP) − 0.75); staging FUN_180c54d8; arbitration FUN_180c5832
FAN ONLY       3 (inf.)   3 (parked)  1                  no direction, no demand
OFF            4 (inf.)   3 (parked)  1                  no direction, no demand
```
CD49 ∈ {0,1,2} stage (cool side proven; heat-side producer unisolated).
CD4B ∈ {1..4} Schmitt quantizer of demand differential (bands +5/0/−5).
CD4A ∈ {0..5} cool-side source arbitration per §7 table; 0 in heat.
CD4C ∈ {0,1} arbitration-internal latch per §7.
