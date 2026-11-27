# FIRMWARE-ANALYSIS-Q — Stage Q: the interpolation engine and the 8-channel evaluator, named

Image: `BINF0479_Carrier.hex` (v4.79, byte-identical to the official ICP image —
stage VERSIONS). CPU Renesas SH-2A BE, base 0x18040000. All work in
`firmware-re/stageQ/` (project copy, scripts, `out/`); every Ghidra run EXIT=0
(runQ1–runQ5). Method: decompile + listing dual verification, literal pools
resolved from the flat image (`stageH/flat.bin`), two independent whole-image
scans for the naming question. [FACT] = shown in code/listing/pool; [INFERENCE]
= interpretation argued from the shown facts.

**Headline verdicts**

| Function | Named purpose |
|---|---|
| FUN_181f77f4 / FUN_181f77fc | get/set of **channel-1 demand coordinate** (float cell 0xFFF8CD94) |
| FUN_181f7822 / FUN_181f782a | get/set of **channel-2 demand coordinate** (float cell 0xFFF8CD98) |
| FUN_181f4d04 | equipment-dependent **clamp dispatcher** for both coordinates |
| FUN_180c15d2 | **demand → demand-coordinate converter**: inverse-interpolates total demand CD44 over the capacity breakpoint tables and writes the two coordinates; the "interpolation engine" of stages E/G |
| FUN_181f4308 | the **inverse direction**: coordinates → total demand CD8C (forward evaluation), plus equal split of CD8C over active zones |
| FUN_181f7050 | **per-zone call-session evaluator**: times each zone's active call, accumulates demand-weighted work, and at call end publishes session minutes, mean demand, demand share, and a ±10 end-of-call score per zone |
| FUN_181f4e60 | **decision-block mirror publisher** (~40 bracketed copies into the object instance at 0xFFF83E28–0xFFF84238) |

The two "properties" driven by the accessor pairs are **not dictionary-named
properties at all** — §2 proves this negatively and identifies what they are
instead: two continuous **stage coordinates** (fractional indices into the
capacity tables), clamped by equipment class/size/mode on every write.

---

## 1. The accessor pairs — resolved to cells, not property IDs

Listing-verified (`stageQ/out/listing_acc.txt`; decompile agrees):

- **FUN_181f77f4** (get №1, 8 B): returns float `*0xFFF8CD94`.
- **FUN_181f77fc** (set №1, 26 B): `CD94 := v; CD90 := v;` then calls
  `FUN_181f4d04(r4 = 0xFFF8CD90, r5 = 0x3C12EC6C)`.
- **FUN_181f7822** (get №2, 8 B): returns float `*0xFFF8CD98`.
- **FUN_181f782a** (set №2, 36 B): `local := v; FUN_181f4d04(r4 = 0xFFF8CD90,
  r5 = &local); CD98 := local; *0x3C12EC6C := local`.

[FACT] CD90/CD94/CD98 are three consecutive floats in the decision block,
immediately after CD8C (total demand). CD90 is a **staging cell**: both setters
route the candidate value through FUN_181f4d04 in CD90 (set №1) or in a local
that is then committed to CD98 **and to the object cell 0x3C12EC6C** (set №2 —
the asymmetry is in the listing: set №1 does not write 0x3C12EC6C).

[FACT] Users (UsersOf, `stageQ/out/usersQ.txt`): the pairs are used across the
whole decision module — FUN_180c15d2, FUN_181f4308, FUN_180c0fec, FUN_180c2b76,
FUN_180c32f2, FUN_180c3552, FUN_180c4fcc, FUN_181ac138, FUN_18183f1e,
FUN_181f026e — i.e. they are the module-wide get/set for two shared channels,
not a local helper of one function.

### FUN_181f4d04 — clamp dispatcher (202 B, decompile `out/decompQ2/`)

[FACT] Builds the effective equipment record: copies the 46-byte flash template
@ **0x1830B0A8**, then under dictionary brackets (FUN_180bc05a/FUN_180bc06e)
overlays the live 46-byte mirror record @ **0xFFF82CAC** via FUN_1823d404
(memcpy — verified by decompile, `out/decompQ3/`). Reads field-store field 1
(class word) and field 3 via FUN_1815927c. Gate predicate:
`record[6]==4 && record[0]∈{3,4} && record[5]==2`. Dispatch is by the system
mode byte CD7D: `==1` (cool) → FUN_181f4ad8; `==2` (heat) → FUN_181f4bca; those
dispatch again on **bit 0x20 of the class word**:

| mode | class bit 0x20 | handler | effect on the value(s) |
|---|---|---|---|
| cool | set | FUN_181f48de (406 B) | two-value clamp, bands below |
| cool | clear | FUN_181f4a74 (24 B) | if size <31 and v ≥ **2.0** → v := 2.0 |
| heat | set | FUN_181f4b4a (128 B) | size <31 → v := min(v, **1.3** if record[0]==4 else **1.4**); 31–60 → v := min(v, **1.0**); ≥61 → v := **0.0** |
| heat | clear | FUN_181f4b32 (24 B) | if size <31 and v ≥ **2.0** → v := 2.0 |

[FACT] FUN_181f48de additionally reads field 3 (2 B; flag bit 0x40), copies a
0x1B-byte record @0xFFF83058 and a 0x20-byte float array @0xFFF82160
(gate `array[0] ≥ 62.0`), and clamps its two float operands into the band set
{0.0, 1.0, 1.3 (record[0]==4) / 1.4} selected by the same size byte. All
constants are pool literals (0x181F4A90–0x181F4AD4, 0x181F4CE0–0x181F4CF0):
0.0, 1.0, 1.3, 1.4, 2.0, 62.0. The "size byte" is equipment-record byte
**[0x10]**, banded <31 / 31–60 / ≥61.

[INFERENCE] The size byte is the nominal equipment size code (bands align with
stage L's clamp X ∈ [12, 61] and with size-class strings like the "61" of
EN(A,D)4X61). The caps read as **maximum demand coordinate by equipment size**:
coordinate 1.0/2.0 = stage-1/stage-2 boundary scale (§4), de-rated to
1.3/1.4/1.0 — or forced to 0 in heat for the largest class — on
class-bit-0x20 equipment. Which physical equipment bit 0x20 encodes is not
statically resolvable (the class word arrives at runtime, stage L §3.2).

## 2. Why the pairs have no dictionary names (task item 1 — negative result)

Two independent whole-image scans were run for (name-string ↔ handle) pairs:

1. Stride-8 pair scan of the registration-record format (stage K's records
   @0x181C511C–0x181CC26C): 130 records, handles 0x3C126D19–0x3C129FCC.
2. Both-orders stride-4 scan of the entire image for any printable string
   paired with any value in 0x3C120000–0x3C140000: **324 distinct named
   handles**, range 0x3C121B90–0x3C12FED6, clusters at >>8 = 0x3C126D (69),
   0x3C128C (37), 0x3C1299 (23), 0x3C126E (18), 0x3C1270 (15), 0x3C128D (12),
   0x3C12A0 (12), 0x3C129F (11).

[FACT] **No pair names 0x3C12EC6C, and none names any of 0x3C12A838–0x3C12A84C**
(the only ECxx/E6xx hits are format-string false positives). The named handles
are the *settings dictionary* (stage K names: defrostbackup, coollatchtemp,
min/maxcoolstage, cfmlimitsvalid, …). The addresses this stage was asked to
name are **runtime object-instance field addresses in dictionary space** —
they are identified by the object/member registry mechanism (stage F:
member indices into the unified registry @0x182B6AC8), not by name→ID
registration records. The stage H inventory (902 names @0x18300000–0x1830B000)
is the same settings dictionary and likewise contains no binding for these
instance fields.

**Consequence for the emulator:** channels 1/2 and the A838-block fields
(§5) have no recoverable dictionary names because they never had any — they
are identified structurally, by their tables and consumers, which §§3–5 do.

## 3. FUN_180c15d2 — demand → demand-coordinate converter

Callers: refresh FUN_181efdfc and FUN_181f857c (sys_ctrl state 6) [stage G].
Pool fully resolved in `stageQ/out/pool_180c15d2.txt`; entry verified in
listing (`out/listing_15d2_head.txt`).

[FACT] **Entry (unconditional, listing 0x180C15D2–0x180C1606):** copies the
24-byte flash default record @0x182C3130 (all zeros — verified) to the stack;
byte 0xFFF874B0 := 0; **set №1(0.0); set №2(0.0)** — both coordinates are
zeroed, then recomputed from scratch on every evaluation. Default state is
therefore "no demand on either channel".

[FACT] **Inputs:** total demand **CD44** (float, from the zone aggregator
FUN_180c62fc, stage L §3.1); mode byte **CD7D** (1 = cool, 2 = heat); gate
byte FUN_181f7004() = *0xFFF8C5B6 (a byte of the input record mirrored at
C5A0). In cool mode CD44 is first capped at the last CCDC table entry:
if CD79≠0 and CCDC[CC5A−1] < CD44 and CD7D==1 → CD44 := CCDC[CC5A−1].

[FACT] **Excess latch (cool, gated):** under flags (CC52 & 0x100, CD7C≠0,
CD7D==1, CC54≠3, CBF4 bits 0x40/0x20) and (CC52 & 0x7C00)==0x400 with the
C5B6 gate: `excess = CD44 − CCDC[CC5A−1]`, floored at 0;
**0x3C12A844 := max(0x3C12A844, excess)** — a latched maximum of the demand
that channel 2's cool table cannot cover; if the latch is < 1.0 then
CD7B := 0 and **0x3C12A848 := 1**. The channel-1 input is then this excess
(fStack_48); without the gate it is CD44 itself. Separately, if CD44 <
0x3C12A84C the latch is reset (0x3C12A844 := 0.0, tail block).

[FACT] **Channel-1 half (table CC34):** segment search of the input over
**CC34** (count **CBFA** = (class & 3) + 1, built by FUN_181f07ec, stage L
§3.8), honouring flag word CBF4 and the cap cell 0xFFF874A4; segment indices
→ CA5A (lo) / CA59 (hi), endpoint values → CA54 / CA50. On segment change vs
the mirrors, FUN_181f062c + FUN_181f063c run and the mirrors update (§5).
The interpolation written through set №1 is the **inverse** one:

```
P1 = CA5A + (x − CC34[CA5A]) · (CA59 − CA5A) / (CC34[CA59] − CC34[CA5A])
```

i.e. P1 is the **fractional index of the demand x in table CC34**. The
forward value `CC34 at P1` is reconstructed into scratch 0xFFF874A8 (capped
by 0xFFF8749C). Reset branch (CD7B==0 or FUN_181abdf4()≠0): indices and
P1 := 0, and under the 0x400-class gate 0x3C12A848 := 0.

[FACT] **Channel-2 half (tables CCDC / CCC4):** the local table pair is
mode-selected — CD7D==1 → x-array **CCDC**, y-array **CC94**; CD7D==2 →
x-array **CCC4**, y-array **CC64** (counts **CC5A** = (CC52 & 0xF) + 1);
auxiliary bytes CBB3/CBB1 ride along as uStack_40/bStack_3c (defaults
0 / 10). Same segment search over the raw (cool-capped) CD44 → indices
CA76/CA75, endpoints CA70/CA6C; mirrors 0x3C12A83A/3B; inverse interpolation
through set №2 (caps via scratch 0xFFF874A0 / 0xFFF87498); forward value →
0xFFF874AC. Boundary forcing: CD4A ∈ {1,2,3} forces segment index 1;
CD7D==2 with CD4A==0 forces segment 0. A disjoint fallback path
(FUN_180c3e5c, constant 99999.0) exists when CD73/CD75/CD74 conditions hold.

[FACT] **Tail:** sibling evaluators run (FUN_180c2b14, FUN_180c2b76,
FUN_180c3012, FUN_180c3232, FUN_180c3552, FUN_180c35dc, FUN_180c32f2,
FUN_180c3418, FUN_180c3bee); then **CD8C := 0xFFF874A8 + 0xFFF874AC** — total
demand recomputed as the sum of the two channels' forward-evaluated values;
byte CAA9 := activity flag. Under (CC52 & 0x7C00)==0x400:
**0x3C12A84C := CA70 / 2.0** (or CA6C / 2.0 when CA70 ≤ 0, CA94==1, CA6C>0).

### The paired forward evaluator — FUN_181f4308 (refresh path)

[FACT] (decompile + stage L pools) FUN_181f4308 is the same computation in
the forward direction, which is what fixes the coordinates' meaning:

- Seeds: input record copy C5A0 ← 0xFFF82E0D (11 B); **CD7D := record[0];
  set №1(record[1]); set №2(record[5])**; FUN_181f5d08() (table producers).
- Stage bytes: CA80 := (int)P1; CA94 := (int)(P2 + 0.0001) (FUN_1815d62a —
  epsilon-truncation, constant 0x38D1B717 ≈ 1e-4); CD7B := CA80; CD7C := CA94;
  CD86 := (CA80≠0 || CA94≠0); CD4A := 4 if CA94≠0 and CD7D==2 else 0.
- Forward evaluation with P as the continuous coordinate:
  `local = interp over CC34 at P1` (indices CA59/CA5A);
  `f1 = interp over CCC4 at P2`, `f2 = interp over CCDC at P2`.
  Combine by mode: **CD7D==2 → CD8C := f1; CD7D==1 → CD8C := local + f2;
  else CD8C := 0**. C90C := CD8C.
- Split: count zones with FUN_181f035c(i)≠0 (i = 0..7); each such zone gets
  **C8CC[i] := CD8C / count**, C9AC[i] := 0 (others 0/0). CD7E[i] := 0x0F.
  Then FUN_181f4e60() (publish, §6) and FUN_181f69bc() (sibling, §7).

## 4. Physical meaning of the interpolation (task item 3)

[FACT] The tables are **computed at runtime from the equipment class**, not
copied from flash (stage L §§3.2/3.8): FUN_181f21d4 builds CCC4/CCDC/CD04
with CCC4[1] = R · 12000.0 and CCDC[1] = R · 34.286 · (137.0 + 3.5·X),
R = field8 / 12.0, X = clamp(*(float*)0xFFF820F8, 12.0, 61.0); FUN_181f07ec
builds CC04/CC1C/CC34 with factors 0.6/0.4 and constant 3414.0. Stage P
(pools resolved, report pending) is re-deriving the same producers and had
not landed when this stage ran; nothing in its intermediate output
contradicts stage L.

[INFERENCE — strong] **The table axis is demanded capacity on a
nominal-capacity scale.** 12000.0 is BTU/h per ton; R·12000 is the
equipment's nominal capacity (the author's ODU: 60K BTU/h → R = 5). 34.286 =
12000/350 is the same scale expressed through the nominal 350 CFM/ton air
volume. Demand CD44 and the table entries share these units; CD8C (their
sum after evaluation) is the same quantity, which is why FUN_180c62fc's
zone-contribution total and FUN_181f4308's split use it interchangeably.

[FACT + INFERENCE] **The coordinate (the accessor-pair value) is a
continuous stage coordinate along the capacity curve**: 15d2 inverts the
curve (capacity → coordinate), 4308 evaluates it (coordinate → capacity),
the setters clamp the coordinate to equipment-dependent maxima
{0.0, 1.0, 1.3, 1.4, 2.0} (§1), and 4308 truncates it to the integer stage
bytes CA80/CA94 that the rest of the module (and the staging machine of
stage E) consume. In cool mode total demand is the **sum of both channels**;
in heat mode **channel 2 alone** carries it; channel 1's cool input is
specifically the **excess over channel 2's table maximum** (latched at
0x3C12A844). [INFERENCE] The two channels are two capacity sources staged
in sequence — channel 2 primary, channel 1 spillover — e.g. two compressor
circuits or compressor + auxiliary capacity; heat uses a single source.
Which physical sources, and what class bit 0x20 selects, depend on the
runtime class word of the author's installation and are **not** statically
resolvable (§7).

## 5. The dictionary mirrors 0x3C12A838–0x3C12A84C (task item 2)

[FACT] These are fields of one dictionary-space object, written **directly**
by FUN_180c15d2 (its pool DATs are the literal addresses) — a different
mechanism from FUN_181f4e60's RAM-object mirror (§6). Field map, from the
resolved pool of FUN_180c15d2 (`out/pool_180c15d2.txt`):

| Address | Type | Content |
|---|---|---|
| 0x3C12A838 | byte | channel-1 segment **hi** index (mirror of CA59) |
| 0x3C12A839 | byte | channel-1 segment **lo** index (mirror of CA5A) |
| 0x3C12A83A | byte | channel-2 segment **hi** index (mirror of CA75) |
| 0x3C12A83B | byte | channel-2 segment **lo** index (mirror of CA76) |
| 0x3C12A844 | float | **latched maximum excess demand** over CCDC max (cool; §3) |
| 0x3C12A848 | byte | excess-latch state flag (set when latch < 1.0; cleared in the ch-1 reset branch) |
| 0x3C12A849 | byte | read in the tail gate (with CD71/CD7A) for the "any residual activity" test |
| 0x3C12A84C | float | **half of channel 2's active segment endpoint** (CA70/2, or CA6C/2 in the boundary case), written under class gate (CC52 & 0x7C00)==0x400 |

[FACT] Change notification: when a segment index pair changes vs its
mirror, FUN_180c15d2 calls FUN_181f062c + FUN_181f063c (channel 1) or
FUN_181f064c + FUN_181f065c (channel 2) before updating the mirror bytes —
paired helpers, exact role unresolved (§7). [INFERENCE] 0x3C12A84C = a
half-demand threshold: the latch at A844 is reset when CD44 falls below it,
so it behaves as the midpoint of the active capacity segment (e.g. a
per-circuit share of the segment's demand).

Per §2, no dictionary *names* exist for these fields; the map above is
their complete structural identification.

## 6. FUN_181f7050 — per-zone call-session evaluator (task item 4)

Caller/cadence [FACT, stage G §6]: invoked from **FUN_181f8592** (sys_ctrl
state 2, class-6 message) in the sequence refresh FUN_181efdfc →
**FUN_181f7050** → FUN_1815dcee → FUN_181f4e60. Class 6 is the hub's
evaluation trigger (most state exits post a fresh class-6 message), so the
evaluator runs **once per hub evaluation cycle**; its own time base is
milliseconds (FUN_180bc636), so session timing does not depend on cadence —
only the accumulation sampling does. Pool fully resolved
(`out/parse_reg.txt`).

[FACT] The 8 channels are the **8 zones**: every array it touches is a
per-zone array of stages E/L (mode bytes CBA9[8], temperatures
CABC/CB60/CADC[8], weights CD1C[8]). Per zone i:

- **Idle (state C618[i] == 0):** if **CBA9[i] == 4** (zone call active):
  start_ts C5B8[i] := now; state := 1. Otherwise the zone's session data
  is cleared (accumulator, minutes, score, mean, share := 0).
- **Timing (state == 1, CBA9[i] still 4):**
  `accum C5F8[i] += CD8C · CD1C[i]` — total demand × the zone's weight,
  once per cycle.
- **Call end (state == 1, CBA9[i] != 4):**
  - `minutes C620[i]` = wrap-corrected (now − start) / **60000.0**, with
    the 2^32 / 2^31 correction idiom (constants 0x4F800000 / 0x4F000000).
  - If the zone-active predicate **FUN_181f0428(i)** holds (the same
    getter stage L §3.5 uses for "zone active"), an end-of-call deviation
    is formed from the zone temperature arrays, sign arranged per mode:
    cool (CD7D==1): `diff = CADC[i] − CB60[i]`; heat (CD7D==2):
    `diff = CB60[i] − CABC[i]`; else 0.
  - **Score byte C640[i] := −10 (0xF6) if |diff| ≥ 1.875, else +10 (0x0A)**
    (threshold constant 0x3FF00000 = 1.875; the comparison reaches the
    decompiler float/int-punned — the ±10 writes and the constant are
    literal, the fabs reading is [INFERENCE] from the idiom's shape).
  - **Mean C648[i]** := accum / minutes if minutes > 1.875, else 0.
  - **Share C668[i]** := mean / **CE60** if CE60 > 1.875, else 0. (CE60 is
    the decaying correction cell written by the demand aggregator
    FUN_180c62fc, stage L §3.1.)
  - state := 0.
- **Publish** (FUN_1823d404 copies under FUN_180bc05a/06e brackets) into
  the object instance at 0xFFF84xxx: minutes[8] (0x20 B) → **0xFFF8418C**;
  score[8] (8 B) → **0xFFF841AC**; mean[8] (0x20 B) → **0xFFF841B4**;
  share[8] (0x20 B) → **0xFFF841D4**. This closes stage G's open item
  "FUN_181f7050's four published arrays' dictionary destinations" — they
  are fields of the same RAM object family that FUN_181f4e60 mirrors into.

[INFERENCE] Functionally this is a **zone performance / demand-attribution
scorer**: for each zone call it records how long the call lasted, how much
weighted demand it consumed on average, its share of the (decaying) total,
and a ±10 verdict on whether the zone ended the call within 1.875
(array units — the same °F-scale arrays stage E §4 uses with 3.0 clamps
and ±0.75 offsets) of its target-side temperature. Who consumes the
published arrays (an adaptive re-weighting of CD1C is the obvious
candidate) was not traced — §7.

### FUN_181f4e60 — mirror publisher (bonus, closes the pair)

[FACT] ~40 bracketed copies (FUN_180bc05a/06e + FUN_1823d404) from the
decision block into the object instance **0xFFF83E28–0xFFF84238**,
including CD7B/CD7C/CD86, CD8C → 0xFFF83E34, CE60 → 0xFFF84018, the CA48–
CA94 segment/coordinate state (CA59/CA5A → 0xFFF83FE5/E6, CA75/CA76 →
0xFFF84001/02, CA80 → 0xFFF83FAC, CA94 → 0xFFF83FC0), and the C8CC/C9AC/
C880/C910/C930/C950/C958/C978/C988/C9AC/C9CC/C9EC arrays. It is the
publish step at the end of both the hub cycle (stage G) and
FUN_181f4308.

## 7. Unresolved residue (exact)

1. **Dictionary names for channels 1/2 and the A838-block fields: proven
   nonexistent** in the registration-record mechanism (§2). A name could
   in principle exist in the runtime-registered member registry (stage F
   mechanism); extracting it needs the runtime registration trace, i.e.
   dynamic analysis (stage M route) or a live snapshot — not static work.
2. **Physical identity of the two capacity channels** and of class-word
   bit 0x20 (the clamp-dispatch selector): depends on the author's runtime
   class word CC52 — readable from a live unit, not from the image.
3. **CC94/CC64 (the y-arrays loaded beside CCDC/CCC4 in FUN_180c15d2):**
   loaded into the local table pair and passed to the fallback evaluator
   FUN_180c3e5c, but their role in the main interpolation path is not
   visible in the decompile; FUN_180c3e5c itself (99999.0 constant) is
   undecompiled.
4. **FUN_181f062c/063c and FUN_181f064c/065c** (segment-change helper
   pairs), **FUN_181abdf4** (gate predicate in both halves),
   **FUN_181f69bc / FUN_181f6ff6** (sibling evaluators called by
   FUN_181f4308), **FUN_180c3814** (called between the two halves of
   FUN_180c15d2): called, not decompiled — none of them alters the
   dataflow named above.
5. **FUN_181f7050's consumers:** who reads 0xFFF8418C/AC/B4/D4 (minutes /
   score / mean / share) — the presumed adaptive-weight feedback into
   CD1C is unverified. Also the exact comparison semantics behind the
   decompiler's float/int punning at the 1.875 thresholds, and the units
   of CD1C[i] weights.
6. **FUN_181f48de's two-operand clamp:** which of its two float operands
   is the coordinate and which is the companion value (it receives
   &CD90 and the field-3 cell through FUN_181f4d04) is not fully pinned;
   the band constants are exact either way.
7. Stage P (table construction, parallel stage) had not delivered when
   this stage ran; §4's axis inference rests on stage L's producer
   formulas and should be cross-checked against P's report when it lands.

## 8. Evidence inventory (stageQ/out/)

- `listing_acc.txt` — listings of FUN_181f77f4/77fc/7822/782a/7864.
- `decompQ2/` — FUN_181f4d04; `decompQ3/` — FUN_1823c6e4 (memcpy),
  FUN_181f4c9e, FUN_181f4ad8, FUN_181f4bca.
- `decompQ4/` — FUN_181f48de, FUN_181f4a74, FUN_181f4b4a, FUN_181f4b32,
  FUN_1815d62a, FUN_181f0428, FUN_181f035c, FUN_181f4e60.
- `pool_180c15d2.txt` — full literal pool of FUN_180c15d2 (0x180C17B8–
  0x180C2B0C) resolved from the flat image.
- `parse_reg.txt` / `regmap.json` — registration-record parse + pools of
  FUN_181f7050 (0x181F72D0–0x181F7500).
- `usersQ.txt` — UsersOf for the accessor pairs and FUN_181f4d04.
- `listing_15d2_head.txt` — listing of FUN_180c15d2 entry (zeroing proof).
- Background scan (both-orders name↔handle, whole image): 324 named
  handles, none in 0x3C12A8xx / 0x3C12ECxx.
