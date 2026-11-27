# FIRMWARE AUDIT 2 — second pass: stages O, P, Q, R, S, AA, V, W, Series C

**Date:** 2026-11-26. **Scope:** the third-wave reports the first
audit (`FIRMWARE-AUDIT.md`) could not cover — `FIRMWARE-ANALYSIS-O`,
`-P`, `-Q`, `-R`, `-S`, `-AA`, plus `-V` and `-W` (delivered while
audit 1 ran) and `-SERIESC` where it interacts. Stages T, U, X, Y
were **not** in this pass's scope; where their results intersect
the gap list they are cited as *unaudited*.

**Method.** Same as audit 1: load-bearing claims re-derived from
primary material by the auditor, in `firmware-re/audit2/`
(`recheck2_image.py`, `recheck2_captures.py` — independent
implementations, no stage script reused): raw scans over
`firmware-re/stageB/flat.bin` (base 0x18040000), a full recount of
all 83,752 frames in `traces/*.jsonl`, and direct reads of the
stages' own listings, decompiles, pools and emulator outputs.
No stage report and not the protocol map was modified.

**Evidence classes:** `CAP` capture-proven · `DUAL` dual-verified
static · `STATIC` single-method static · `EXT` external document ·
`INF` inference.

---

## 1. Rulings on the seven referred tensions

### 1(a) CCC4: O's "cooling C870 = CCC4[CC5A−1]" vs the "heat-side table" label — shared use; the label, not the mechanics, was wrong

The mechanics are identical in every report that touches the
tables. Audit re-check of the three independent consumers:

- `FUN_1809f4a4` (O §3, pool-verified): `CD7D == 2` →
  `C870 := CCC4[CC5A−1]`; `CD7D == 1` → `C870` built from
  `CC34[CBFA−1]` and `CCDC[CC5A−1]`.
- `FUN_181f4308` (S §1d, Q §3 — two independent decompile passes,
  same result): `== 2` → `CD8C := interp(CCC4)`; `== 1` →
  `CD8C := interp(CC34) + interp(CCDC)`.
- `FUN_180c15d2` / `FUN_180c3418` (S §3, raw-verified pools
  0x180C3678→CCDC, 0x180C367C→CCC4): table CCDC selected for 1,
  CCC4 for 2.
- `FUN_180c54d8` (staging): audit-resolved pools from stage E's own
  decompile (`stageE/out/decomp2/decomp_180c54d8.c`) — reads CD44,
  CD7D, `CCC4` indexed by `CC5A`, writes CD49; constants 1.25
  (`0x3FA00000`) and 0.25 (`0x3E800000`) sit in its pool.

So CCC4 is consistently **the mode-2 table** — staging thresholds,
interpolation breakpoints and the demand ceiling are three
consumers of one table (this also settles audit 1 §2b.3's "dual
use": the uses are real and all on the same side). What made it
look like a "heat table" is the mode label: stage E assumed
`CD7D == 2` was heat, and that assumption propagated. With §1(b)/§2
below (mode 2 = COOL, settled), CCC4 is the **cool-side** table
and CCDC the heat-side (mode-1) table. **Ruling: no factual
contradiction; one inherited label correction, charged to Q in
§3.3 because Q repeats it as its own finding.**

### 1(b) The staging machine's side — FINAL: `FUN_180c54d8` is the COOL-side machine; the map's "[0] heat stage" survives only as a wire observation

- S §3 proves `CD7D == 2` = COOL three independent ways (arbiter
  sums, changeover tests, call flags). Audit re-checked the proof
  at its joints against stage L: L §3 (lines 113–116) has
  `FUN_1816deec` taking base = CADC with tracked max and **+0.75**
  offset for `CD7D == 1`, base = CABC with tracked min and
  **−0.75** for `== 2`; L §3 (line 109) fixes the array identities
  by copy source (CADC ← mirror 0xFFF83C38, CABC ← 0xFFF83C58 —
  the same mirrors S cites); O §2.2a independently recovers the
  same signs from `FUN_180c5dd0`'s listing (mode 1 →
  `e = CADC − CB60`). Two unrelated functions treat the CADC array
  as the heat side in mode 1; the swapped reading makes both
  physically backwards.
- `FUN_180c54d8` is gated on `CD7D == 2` (E §3, S §5 census) and
  thresholds over CCC4 (§1(a)) — i.e. it is the **cool-side
  staging machine**, output CD49 ∈ {0,1,2}. Stage E's matching of
  it to the 0305[0] heat staircase is **refuted as a producer
  claim** (the CD49→0305[0] link was never statically proven —
  stages F/N, restated by S).
- **Audit capture census** (all 674 src-0x20 0305 frames with a
  12-byte payload): `[0]=1` ×31, `[0]=2` ×26, `[2]=2` ×34, both
  zero ×583 — **`[0]` and `[2]` are never simultaneously
  nonzero**. The map's scenario reading ([0] carries the heat
  stage during heat calls, [2] the cool stage during cool calls)
  is capture-true and stands. What does not stand is any
  attribution of [0] to `FUN_180c54d8`.

**Ruling:** E §10's "gate consistent with heat" remark and every
downstream citation of `FUN_180c54d8` as the heat staging
producer are superseded. The heat-side staging producer remains
unisolated (S's candidates: `FUN_180c3012/3418/3814/3bee/46b8`) —
new gap B-11 (§5). For emulator coding this is not blocking: the
hysteresis *form* is proven (on the cool machine, emulated 12/12
by stage M) and the heat staircase's wire behaviour is captured.

### 1(c) AA vs the serializer boundary — audit 1's B-8 is INVALIDATED and replaced

AA's central claim re-derived by the auditor:

- **BE32 census:** the word `0x180A42DC` (CRC entry) occurs
  **exactly once** in the 15 MB image — at 0x180A5AC8, the
  descriptor slot. The slot's content is `0x180A42DC`; the
  descriptor header at 0x180A5AB0 is `0x006B0000`. Neither the
  slot address nor the descriptor base occurs as a BE32 word
  anywhere (the RX handler reaches the slot by PC-relative load,
  not by literal).
- **Branch census:** exactly **one** direct branch in the whole
  image targets the CRC entry — a BSR at 0x180A484A, inside the
  builder `FUN_180a44ee`. With the descriptor-mediated computed
  call in the RX island (0x180A5878), the caller map is exactly
  AA's: two call sites, one per direction.

**Ruling:** AA is right. The frame serializer is statically
linked ordinary code (the CCN module: builder `FUN_180a44ee`,
walkers `FUN_180a815c`/`FUN_180a7eb0`, directories DIR-A/B/C, the
15-state RX machine). Stages F/N's "runtime-registered transmit
pointers" boundary was an **analysis gap** with three compounding
causes, all now identified: the RX half lives in an island Ghidra
never turned into functions; the demand payloads are blob-copied,
so no per-table construction code existed to find; and the
censuses searched the *binding* directory (@0x182B5E3A) while the
serializer keeps its *own* directories. Audit 1's B-8 ("accepted
boundary — do not re-attack statically") and its §3.5 ledger rows
("serializer + bus CRC routine absent from statically reachable
code"; "the only CRC tables are … @0x182C4164 / BUYPASS";
"dynamic route cannot cross the serializer boundary") are
**overturned** and must not be quoted. Audit 1's narrower
byte-level CRC census is not itself contradicted (the nibble pair
@0x182B598C/0x182B59AC is a pair of 16-entry tables, not a full
256-entry table), but its conclusion was.

**Replacement (gap B-8′, §5):** AA §9's residue — (1) the RX
handler's invoker and the burst-cadence source; (2) descriptor
registration (stub `FUN_180a5aa2`, table @0x182FAC24); (3) the
demand staging buffers' content writers — which are the control
law itself, now specified by O/P/Q/R; (4) `FUN_180a49a8`
internals; (5) `FUN_180a7500`'s per-format conversion. None of
these blocks emulator coding (AA §10): an emulator replaces
(1)–(2) with its own scheduler and implements (3) from the
control-law stages.

### 1(d) P's directory correction vs audit 1's re-parse of F — audit 1 stands; P corroborates

P §8 item 9 states that stage D's binding-directory dump is stage
F's group table "read 6 bytes out of phase", verified from the
raw bytes at 0x182B5E3A. That is exactly audit 1 §1.2's finding
(D's base 0x182B5E40 vs F's base 0x182B5E3A — a 6-byte phase
difference; same 98-table set under both parses; decisive
member[324] test passes under F's parse). W §1 independently
reused the F-phase parse in five older versions, reproducing both
anchors in each. **Ruling: audit 1 §1.2 stands in full; P adds a
third corroboration and no contradiction.**

### 1(e) The {375, 400} pair — R upheld; audit 1 §2b.2 is RESOLVED (the branch is live)

Audit 1 left a tension: E's getter `FUN_18051cec` returns the
375/400 constants only for selector 5, while its only described
caller (`FUN_180c5c7c`) passes u ∈ {1, 2} — suggesting dead code.
R §2.2 places the constants on the cool detour
`FUN_1804f6cc → FUN_18051898 → FUN_18051cec(CD4A)`. Re-derived:

- Stage N's decompile of `FUN_18051898` (the copy lives in
  `stageN/out/decomp2/`): `if ((CC52 & 0xF) == 1) → 
  FUN_18051cec(*DAT_18051a78)`, else `FUN_18051908(f, *DAT_…)`.
  Audit pool resolution: `DAT_18051a74 → 0xFFF8CC52` (CC52),
  **`DAT_18051a78 → 0xFFF8CD4A` (CD4A)** — the argument is CD4A,
  as R says; the else-branch float is `*0x3C12EC6C − 1.0`
  (via `FUN_181f7816`), class-0x4000 variant `(X−1)/4.0`,
  floored at 0.0 — R §2.2 verbatim.
- **Caller census for `FUN_18051cec`, both encodings:** the BE32
  word occurs exactly once (pool @0x180C5D88 — the
  `FUN_180c5c7c` cluster, E's caller), **and** a BSR/BRA target
  scan finds exactly one direct branch — BSR @0x180518B2, inside
  `FUN_18051898` (distance 0x454, within BSR range). Two callers
  total. E's negative generalized from the pool-visible caller
  only; the second call is BSR-encoded and invisible to
  literal-pool censuses — the same blind spot AA exposed in the
  CRC census (and which AA's own census avoided by scanning
  branches).
- **Reachability of argument 5:** CD4A = 5 is a real state
  (S §7 transition table: CD49 == 2 → CD4A = 5, all branches;
  the arbitration runs in cool mode). The gate `(CC52 & 0xF)
  == 1` is satisfied by both primary candidates for our class
  word (0x8141/0x91C1, low nibble 1 — P §7.3). So on this
  installation the detour takes the `FUN_18051cec` branch, and
  at full cool stage-2 demand it returns the constant-array
  pointer.
- One refinement to both E and R: `FUN_18051cec`'s first-level
  selector is **CD4B** (audit-resolved pool `DAT_18051d54 →
  0xFFF8CD4B`), which selects between two overlapping windows
  of one constant run — {375.0, 325.0, 400.0, 350.0} @0x18051FF0
  (CD4B == 1) and {400.0, 350.0, …} @0x18051FF8 (CD4B ∈ {2,3,4}).
  "Returns pointers to 375/400 for argument 5" is correct but
  incomplete without the CD4B dependence. (The exact
  dereference step shares the variant-return ABI unknown R
  already lists for `FUN_1805002a`, §3.4.)

**Ruling:** {375.0, 400.0} are **live CFM/ton constants** on the
cool computation's detour path. Do not cite them as dead code;
do not cite them as "the CFM limits" either (audit 1's caution
stands) — they are entries of the constant run
{200, 275, 375, 325, 400, 350} @0x18051FE8 consumed through the
getter. Audit 1 §2b.2 is closed.

*Self-correction:* audit 1 §2.3 cited this run as "{375.0,
325.0, 400.0, 351.0} at 0x18051FF8". Audit re-read: the run at
0x18051FE8 is {200.0, 275.0, 375.0, 325.0, 400.0, 350.0}; at
0x18051FF8 the words are {400.0, 350.0}. Audit 1's base and its
fourth value (351.0) are both wrong; the substantive claim
(constants present and unchanged across versions) is unaffected.

### 1(f) Class-word bit 0x20: Q's clamp gate vs P's tail gate — same bit, consistent roles

Consumers of CC52 bit `0x0020` across the corpus: Q §1 (clamp
dispatcher `FUN_181f4d04` selects the two-value clamp variant),
P §2.7 (`FUN_1804e9ac` special-cases family 0x800 together with
bit 0x0020), R §2.1 (heat part-2 interpolation gate) and R §2.2
(cool main interpolation gate). In every consumer the bit gates
the *second channel / derived-table* processing — the CCDC-derived
part in R, the two-operand clamp in Q, the derived-array special
case in P's tail. **Ruling: one bit, several consistent
consumers; no contradiction.** P §6.1's gloss "interpolate flag"
[INF] is compatible with all four uses. Caution for future
citations: R §3's zoning predicate tests **CBF4** bit 0x20 — the
twin word, a different bit that happens to share the mask.

### 1(g) P's CC52 candidates vs R's "class fields 0x0000/0x1000" — same word, different quantities

R §4's sentence is about the **family field**: "the G80CTL class
words seen in stage L (0x8241/0x92C1 → field 0x0000/0x1000;
0x8141/0x91C1 → 0x0000/0x1000) never take this branch
[(CC52 & 0x7C00) == 0x800]". Audit arithmetic on the raw values:
0x8141 & 0x7C00 = 0x0000; 0x91C1 & 0x7C00 = 0x1000; 0x8241 →
0x0000; 0x92C1 → 0x1000. P §7.3's candidates are the **full
16-bit words** at store bytes [1..2]. **Ruling: no contradiction
— P quotes the word, R quotes its masked field; both agree on
the underlying values.** R's phrasing is compressed but correct
in context (the 0x800 test is a field test).

---

## 2. Per-stage rulings — O, P, Q, R, S

### 2.1 Stage O (demand formula) — UPHELD in full

- Emulator output re-read (`stageO/out/emu_demand.txt`): **10/10
  PASS** on CD44/C8CC/C8EC/P, including V10 (raw P = −210.67 →
  clamped to 0 — the two-sided clamp, §7.2 of O) and V6 (latch
  flag read back consumed). The one emulator-deviant output
  (CE00) is documented by O itself with unit tests and does not
  feed CD44.
- Correction 1 re-derived from raw bytes: the 8 bytes at
  0x180C6060 are `3FA99999 A0000000` = BE double **0.05**; the
  float at 0x180C6068 is 0.95. O's `CE00 := 0.95·CE00 + 0.05·|e|`
  stands; the earlier "1.325" reading is refuted.
- The formula's mode signs (mode 1 → `CADC − CB60`, mode 2 →
  `CB60 − CABC`) agree with S's independent proof (§1(b)) — the
  two stages reached the same assignment by different routes
  (aggregator listing vs mode machine), which is what settles
  the Q label question in §3.3.
- O §3's `FUN_1809f4a4` branch predicates remain
  decompiler-transcribed (O flags this itself); its outputs and
  constants are pool-verified, and the load-bearing one for the
  formula — cooling `C870 = CCC4[CC5A−1]` — is corroborated by
  the §1(a) consumer agreement.

### 2.2 Stage P (table producers, class word) — UPHELD, with one prose counting defect

- **Store offsets verified from the producer's own listing**
  (`stageP/out/listing/lst_main.txt`, head): `FUN_181f21d4`
  calls getter `FUN_1815927c` with r4 = 0x2F → CC56, r4 = 0x31 →
  CC58, r4 = 0x1 (len 2) → CC52 at 0xFFF8CC52 — exactly P §1's
  table. R = store[8]/12.0, descriptor default 24 → R = 2.0,
  stands on the same evidence class.
- **Branch census:** P enumerates 21 compared class words
  (§2.3: 11 analytic/selector, §2.5: 8 parameterized, §2.6: 2
  string) plus the 0x8000 fallback. Audit found 20 of the 21 as
  immediates in the producer listings (`lst_main` + `lst_epi`);
  the 21st, 0x92C2, is in P's own instruction-level classhunt
  (`out/classhunt.txt`: `181f261e val=0x92c2 movi20`) — inside
  the function body. The branch *set* is therefore corroborated
  at 21 + fallback. **But P §0.1/§6.1's headline "18 compared
  class words" matches neither its own enumeration (21) nor the
  census** — a counting defect of the same class audit 1 found
  in VERSIONS §4. The formulas are unaffected; do not cite "18".
- Twin `FUN_181f07ec`: 8 of its 11 branch values found as
  immediates in the listing; the remaining three (0x59/0x5B/0x39)
  rest on P's decompile + pool evidence (single-method here).
  The twin's gate, prologue and 0x39 branch were not
  independently re-derived; nothing contradicts them.
- The bounded negative on our CC52 (§7.2) and the candidate set
  {0x8141, 0x91C1} primary / {0x8142, 0x91C2, 0xC195} not
  excluded stand; §1(e) adds one consistency point in the
  primary candidates' favour (their low nibble 1 arms the cool
  detour's analytic branch). P §8 item 9's directory note is
  ruled on in §1(d).

### 2.3 Stage Q (interpolator + evaluator) — MECHANICS UPHELD; MODE LABELS REVERSED (the pass's main correction)

Q's structural results agree with S/O/R at every checkable
joint: the accessor pairs resolve to CD94/CD98 with CD90 as the
staging cell; `FUN_180c15d2` inverse-interpolates CD44 over CC34
(ch 1) and the mode-selected ch-2 table; `FUN_181f4308`'s combine
(==1 → CC34 + CCDC terms; ==2 → CCC4 term) is stated identically
by S §1d; `FUN_181f7050`'s session arithmetic (60000.0 divisor,
±10 score at |diff| ≥ 1.875, share over CE60) is consistent with
O §4's CE60 provenance and audit 1's ruling on the 60000.0
constant. Q's negative naming result (no dictionary names exist
for the channels — runtime object fields, not registration
records) was not re-run but is consistent with AA's directory
picture and with audit 1 §1.2's registry semantics.

**But Q's mode words are backwards.** Q §1 ("CD7D: ==1 (cool) →
FUN_181f4ad8; ==2 (heat) → FUN_181f4bca"), §3 ("mode byte CD7D
(1 = cool, 2 = heat)"), §4 and §6 all use the assignment stage E
assumed and stage S disproved (§1(b): 1 = HEAT, 2 = COOL,
triple-proven; O's error signs concur). Q's own arithmetic
agrees with S everywhere — only the English words are flipped.
Consequences that must be applied when citing Q:

1. **Clamp dispatcher (§1 table):** the rows swap modes. The
   size-band derate with **≥61 → coordinate := 0.0**
   (`FUN_181f4b4a`, bit-0x20 set) is the **cool-mode (==2)**
   handler chain via `FUN_181f4bca`, not heat; the two-value
   clamp `FUN_181f48de` chain via `FUN_181f4ad8` is heat (==1).
2. **Excess latch (§3):** the cap-and-latch over `CCDC[CC5A−1]`
   at `CD7D == 1` is the **heat-side** spillover: channel 1
   carries demand above the heat table's maximum. (Parent-era
   summaries repeating "spillover above channel 2's cool
   maximum" inherit Q's error.)
3. **Channel roles (§4):** in **heat** (==1) total demand is the
   sum of both channels; in **cool** (==2) channel 2 (over
   CCC4) alone carries CD8C in the `FUN_181f4308` combine.
4. **Evaluator deviations (§6):** "cool (CD7D==1): CADC−CB60" is
   the **heat** deviation (it is O's mode-1 error verbatim);
   "heat (CD7D==2): CB60−CABC" is the cool deviation.

Minor: Q §3's "count CBFA = (class & 3) + 1" conflates the two
counts — CBFA is `(CBF4 & 3) + 1` (P §3, twin head
listing-verified); CC52's count is `(CC52 & 0xF) + 1` = CC5A,
which Q states correctly for channel 2 in the same paragraph.

**Ruling:** cite Q for mechanics, never for mode words; the
corrected reading is Q-with-labels-swapped, and under that
reading Q, S, O and R are in full agreement.

### 2.4 Stage R (CFM) — UPHELD, with two refinements

- **Demand-floor literals re-derived raw:** the ushort block at
  0x1830B108 is exactly {175, 300, 200, 300, 350, 325, 325,
  325, 350, 350, 400}; the entry at 0x1830B112 is **325** — R
  §1.2/§1.3 verbatim. The floor form `max(FUN_1804fca0(),
  325 × CD8C / 12000.0)` stands (divisor 12000.0 = 0x463B8000,
  5 occurrences image-wide).
- CD88 as the commanded-airflow cell, `FUN_1804e4b6` as
  producer, the per-mode store clamps ([197]/[199] heat,
  [4062]/[4064] cool — R's labels agree with S), and the
  closed input set (no demand-response term in 4.79) were not
  contradicted by any check; the capture signature (§8 of R)
  is consistent with audit 1's CFM census {0, 378…1760}.
- Refinement 1 (evidence index): R §11 lists
  `decomp_18051898.c` among stage R's files; it is not in
  `stageR/decomp/` — the copy is stage N's. The detour claim
  itself is verified (§1(e)); this is a citation-hygiene
  defect only.
- Refinement 2: §1(e)'s CD4B-window point — `FUN_18051cec`'s
  array selection depends on CD4B, which R does not mention.
- R §4's class-field statement is ruled on in §1(g): correct.

### 2.5 Stage S (mode semantics) — UPHELD in full; adopted as this audit's reference for mode

The triple proof was re-checked at its joints (§1(b)) and the
consumer census (S §5) agrees with O/Q/R at every shared
function once Q's labels are corrected (§2.3). The SYSCTRL-49
rejection stands: the hypothesis matches only the external
SAM-side stagmode list; no internal byte uses 0 = heat or
5 = off. The remaining live unknown is exactly the one S §8
names — SYSCTRL byte 49 / 3B02[22] per wall state (mode-experiment
session 1, gap T-4). S's §9 emulator table is implementable as
written.

---

## 3. Per-stage rulings — AA, V, W, Series C

### 3.1 Stage AA (serializer) — UPHELD in substance; §7's headline lengths/addresses are first-record values and are wrong for our equipment classes

The caller census (§1(c)) and the module organization (builder,
walkers, directories, RX machine, descriptor) are upheld. The
directory census, however, is **per-device-class**, and AA's §7
headlines quote the first record of each table:

Audit DIR-B parse (186 records) + capture census:

| Table | AA §7 (class) | Our class record | On the wire (audit census) |
|---|---|---|---|
| 0305 → 44 | 12 B, blob 0xFFF857F6 (0x3E) | 0x40: 12 B, blob **0xFFF85802** | 12 B ×652 ✓ |
| 0307 → 44 | 3 B, blob 0xFFF8583E (0x3E) | 0x40: **4 B**, blob 0xFFF85841 | **4 B ×650** ✓ class-0x40 |
| 0605 → 53 | 7 B, blob 0xFFF85C86 (0x51) | 0x52: 7 B, blob **0xFFF85C8D** | 7 B ×651 ✓ |
| 060D → 53 | 13 B, blob 0xFFF85CC1 (0x51) | 0x52: **1 B**, blob 0xFFF85CCE | **1 B ×651** ✓ class-0x52 |
| 061E → 53 | 9 B, blob 0xFFF85D3B (0x51) | 0x52: 9 B, blob **0xFFF85D44** | 9 B ×651 ✓ |

So for this installation 0307 is 4 bytes (not 3) and 060D is
1 byte (not 13) — matching the protocol map, which already had
both right from the wire. AA §12 flagged the 0307 uncertainty
itself ("whether other 0307 records/classes differ was not
enumerated"); the 060D class dependence it did not flag. The
staging-buffer addresses AA quotes are likewise the class-0x3E/
0x51 records'; ours are the 0x40/0x52 records' (table above).
Side benefit: the wire lengths match exactly the records
selected by stage F's canonicalizer (0x44→0x40, 0x53→0x52) —
an independent confirmation of the canonicalizer assignments
that P §5.4 also relies on. **Ruling: AA's mechanism is proven;
read its §7 per-class, using the 0x40/0x52 rows for this
installation.**

### 3.2 Stage V (SAM relationship) — UPHELD

Audit capture census reproduces V §1.1's load-bearing counts:
**zero** func 0x15 frames in the whole archive; **zero** 3B0E
frames from any source; **zero** 20→92 func 0C frames;
thermostat-initiated traffic to 0x92 consists solely of func 0B
`0104` probes (0x1F ×4, 0x20 ×6 across the archive — V's
per-capture ×4/×1 sit inside this); every 20→92 func 06 frame
(3B02 ×865, 3B03 ×868, …) is a reply to a SAM read, matching
audit 1's recount. The unanswered-poll fraction (~8%) was not
recounted line-by-line. Audit 1 §2b.9's worry — that V might
rest on the truncated tail of `sam-spec-notes.md` — is moot
twice over: the file has since been repaired (171 lines, the
§8.3/§8.4 tail present on disk), and V's spec-derived claims
(ASCII hold/MANUAL semantics) sit in the part that was never
missing. V §3's emulator checklist is adopted as the SAM-facing
spec (closes gap B-10).

### 3.3 Stage W (older-version data plane) — UPHELD

The headline identity claim re-derived directly: the 3,216-byte
span (386 group records + 128-byte bucket index) at 4.74's
0x182CF66E and 4.79's 0x182B5E3A is **byte-identical**. Group
counts (386) and the calibration footprints (0304: 9 groups;
0306: 3; 0303: 5; 0307: 3; 0305/060D/0610/061E: none, all
versions) agree with audit 1 §1.2's parse and with the §3.1
directory picture: the demand tables were never in the binding
layer in any version — and, per AA, were never supposed to be:
they live in the serializer's DIR-B. W's conclusion ("no leak in
older versions") stands and is now explained, not just observed.

### 3.4 Series C probe — UPHELD as a probe; one inference superseded by AA

SC's sharp lead — the nibble pair at 0x182B598C/0x182B59AC with
its single pool reference at 0x180A4560/0x180A4564 — is exactly
what AA §1–§2 confirmed and completed (the pool belongs to
`FUN_180a42dc`'s module). SC §5.1's linkage claim ("4.79's
walker is dispatched through runtime-registered pointers") is
refined by AA §8: builder and walkers are called through
ordinary pool-held pointers from statically visible state
machines; only the RX handler calls through the descriptor
record. SC's headline 3 (the demand family is absent from
Series C's served-table directory) stands, and §3.1 supplies
the symmetric explanation for 4.79.

---

## 4. New defects found by this audit (consolidated)

1. **Q's mode labels reversed** throughout §§1, 3, 4, 6 —
   mechanics sound, words flipped (§2.3). The largest single
   defect in the third-wave corpus; it also infects any summary
   that repeated Q's "cool excess latch" or "heat forces 0.0 at
   size ≥61" phrasings.
2. **AA §7's lengths/staging addresses are first-record
   (class 0x3E/0x51) values**, wrong for our classes on 0307
   (4, not 3) and 060D (1, not 13) (§3.1).
3. **P's "18 compared class words"** matches neither its own
   enumeration (21) nor the listing/classhunt census (§2.2).
4. **Audit 1 §2.3's constant-array citation** — wrong base and
   fourth value (§1(e), self-correction).
5. **R §11's evidence index** lists a decompile under the wrong
   stage directory (§2.4) — citation hygiene only.
6. **Q §3's CBFA count conflation** (CBF4's `(x & 3) + 1` vs
   CC52's `(x & 0xF) + 1`) in one sentence (§2.3).

None of 2–6 touches a formula, a table value, or a wire fact.

---

## 5. Master gap list — consolidated (supersedes audit 1 §4)

### 5.1 Blocks coding the emulator

| # | Gap | State after audit 2 |
|---|---|---|
| B-1 | Exact demand formula | **CLOSED by O** (closed form, emulator-verified 10/10). Residue is configuration *data* → B-12 |
| B-2 | Threshold tables for OUR installation — our CC52 | **OPEN.** P's bounded negative stands: not derivable from captures or the image. Primary candidates {0x8141, 0x91C1} (formula-identical); {0x8142, 0x91C2, 0xC195} not excluded. Closing routes unchanged: live snapshot (addresses in P §7.4; **no read channel known**) or behavioural pinning (P §7.5 — one staging observation pins store[8]; the shadow emulator calibrates the rest) |
| B-3 | CFM computation | **CLOSED as a formula by R** (CD88 via `FUN_1804e4b6`; floor `max(cfg, 325·CD8C/12000)`; per-mode store clamps). Residue: runtime contents of CC04/CC1C/CC7C/CC64/CC94/CCAC (builders identified in the 0x181F0xxx/0x181F3xxx clusters, not decompiled) — calibration data; R §9's capture anchors suffice to start |
| B-4 | Interpolation engine + evaluator semantics | **CLOSED by Q** (with the §2.3 label correction applied) |
| B-5 | Cooling behaviour at part load | **OPEN, behavioural only.** Firmware side specified (T, unaudited); the archive still shows 0605 ∈ {0.0, 5.0} plus exactly one transitional 3.0 frame (T). Closes only with a long mild-weather cool capture |
| B-6 | Commissioning/discovery spec for our configuration | **CLOSED for our configuration by U** (unaudited in this pass). Residue: one full wizard capture if the Ion is ever recommissioned |
| B-7 | The 0414/060B shared byte | **OPEN, unchanged.** Offline correlation against OAT/demand channels across the archive; no live session needed; not yet run |
| B-8 | Serializer construction | **CLOSED by AA** — replaced by B-8′ |
| B-8′ | Serializer residue (AA §9) | RX invoker + burst cadence source; descriptor registration; `FUN_180a49a8` internals; `FUN_180a7500` format codes. **None blocks coding** (emulator substitutes its own scheduler; content production is the control law) |
| B-9 | Mode semantics, firmware side | **CLOSED by S** for all internal encodings (CD7D, R, CD49/4A/4B/4C + transition tables). The SAM-side SYSCTRL-49 byte remains for the live session (T-4) — it concerns the *current* SAM project, not the emulator |
| B-10 | SAM-facing behaviour of the emulator | **CLOSED by V** (§3 checklist) |
| B-11 | **Heat-side staging producer unisolated** (new, from §1(b)) | Blocks only a *faithful* copy of Ion's heat staging law. The hysteresis form is proven on the cool machine; S's five sibling candidates are named. An emulator may stage heat from the captured staircase behaviour meanwhile. Low rank |
| B-12 | **Configuration values for the control law** (new; generalizes B-2's residue) | Data, not code: G (`0x3C12A85C`, no writer found), K9F4, CA04/CA24/C880/CD1C per zone, the FS_1FDF personality byte, store[8], X, CD1C normalization. One live RAM/dictionary read would close all of it; no channel is known (P §7.4), so the practical route is behavioural calibration against captures on the shadow emulator |

### 5.2 Blocks live testing (needs the author at the equipment)

Audit 1's T-1…T-5 carry over unchanged, with one addition:

| # | Gap | Note |
|---|---|---|
| T-1 | G1 — comm-fault timeout & mid-call death behaviour | Still the gating measurement. **Addition (stage Y, unaudited):** the HVA9 service manual documents the ODU entering standby ~2 min after the last valid message — an equipment-side upper bound on the failover takeover window; the T-1 protocol should watch the ODU at the ~2 min mark as well as the furnace |
| T-2 | G5 variants (furnace-only power cycle; thermostat reseat with verified capture) | Unchanged |
| T-3 | G9 — exception behaviour of 44/53 | Unchanged; only with the author's explicit go-ahead |
| T-4 | Mode-experiment session 1 | Now narrower: internal encodings are settled (S); the session only needs SYSCTRL-49 + 3B02[22] in the four wall states, plus a fan-only setting to separate R's 3 vs 4 |
| T-5 | Seasonal captures (cool part-load for B-5) | Unchanged; opportunistic/summer |

### 5.3 Closed since audit 1 (for the record)

B-1, B-3 (formula), B-4, B-6 (our configuration), B-8, B-9
(internal), B-10. Audit 1 tensions resolved: §2b.2 ({375,400}
reachability → §1(e)), §2b.3 (CCC4's role → §1(a): one cool-side
table, three consumers). Audit 1 items superseded: B-8 and the
§3.5 serializer/CRC ledger rows (§1(c)); E's heat-staircase
attribution (§1(b)).

### 5.4 Nice to have

Audit 1's N-1…N-8 carry over. Add: **N-9** `FUN_180a49a8`
internals + `FUN_180a7500` format codes (B-8′ residue);
**N-10** CD4A index↔name binding (S §7: implement transitions,
not names); **N-11** which CFM producer (direct vs zoning
`FUN_180511da`) ran during the captures (R §10.4); **N-12** the
twin's three listing-unverified branch values (0x59/0x5B/0x39)
and `FUN_1809f4a4`'s branch predicates (decompiler-transcribed
in O §3) — both single-method spots in otherwise dual-verified
stages.

---

## 6. Protocol-map errata — consolidated checklist

Audit 1's E-1…E-14 (FIRMWARE-AUDIT.md §5) **all still apply** —
the map has not been modified since. New items from this pass:

- [ ] **E-15 (producer attribution) — §(e) 0305 layout line and
  §(a) burst table:** add a note that [0]'s heat staging
  producer is *unisolated*; `FUN_180c54d8` is the **cool-side**
  staging machine (gated CD7D == 2, thresholds CCC4, output
  CD49) and must not be cited for [0]. The wire roles themselves
  are unchanged (audit-2 census: [0]/[2] never co-active in 674
  frames). (S §3; audit 2 §1(b).)
- [ ] **E-16 (CFM pointer) — §(e), minimal call set item 2:**
  the CFM computation is now specified in FIRMWARE-ANALYSIS-R
  (interpolation over the capacity tables + demand floor
  `325·CD8C/12000` + per-mode store clamps); point the "own
  blower model" sentence at R §9. Observed-values presentation
  (E-9) stands.
- [ ] **E-17 (one frame) — G8:** add: exactly one transitional
  `0605 = 3.0` frame exists in the full archive (2026-11-03,
  stage T, unaudited here); sustained part-load remains
  unobserved.
- [ ] **E-18 (code-derived layouts) — §(b) and G3:** add: field
  layouts for the served tables now also exist from code
  (AA's DIR-A members / DIR-C descriptors), complementing the
  infinitive layouts; 3B02's member binds store buffer
  0x3C0D8D7D, length 29. The *contents* question (registered
  peer) is unchanged.
- [ ] **E-19 (equipment-side bound) — G1:** add: the HVA9
  service manual (stage Y, unaudited here) documents ODU
  standby ~2 min after the last valid message; the furnace
  comm-fault timeout itself remains unmeasured.
- [ ] **E-20 (0x0E note) — §(c) sweep list:** add: address 0x0E
  is never probed by this Ion; per stage U (unaudited here) it
  is a reserved discovery slot for a 3E-family two-capacity
  ODU on other systems — the gofinity capture's 0x0E probes are
  that system's configuration. (Extends audit 1 §2.4.)
- [ ] **E-21 (SAM spec pointer) — §(b) SAM table and G6:**
  annotate that the emulator's SAM-facing behaviour is fully
  specified in FIRMWARE-ANALYSIS-V §3; G6 remains open only
  for a real SAM01's exact write frames.
- [ ] **E-22 (no change — guard against a future import):**
  the map's 0307 write length (4 B) and 060D length (1 B) are
  correct and are confirmed code-side by the DIR-B records
  for our device classes (0x40 / 0x52). Do **not** import
  FIRMWARE-ANALYSIS-AA §7's first-record lengths (0307 = 3,
  060D = 13 — classes 0x3E / 0x51) into the map. (Audit 2 §3.1.)

---

## 7. Audit trail and scope notes

- Re-check artifacts: `firmware-re/audit2/recheck2_image.py`,
  `recheck2_captures.py` — independent implementations; no
  stage script reused; no stage file or the protocol map was
  modified.
- Corpora: `firmware-re/stageB/flat.bin` (15,728,640 B);
  `firmware-re/versions/decoded/0474/flat.bin` (group-table
  identity check); all 12 top-level `traces/*.jsonl` (83,752
  frames; 3 unparseable lines in the two SAM captures, as
  before); the stages' own listings/decompiles/pools/emulator
  outputs under `firmware-re/stage*/`.
- Spot-check coverage, per the tasking: (1) O's formula vs its
  emulator vectors + the 0.05-double and clamp corrections —
  done (§2.1); (2) AA's CRC caller census + DIR-B lengths and
  staging addresses — done, and extended per-class (§1(c),
  §3.1); (3) P's branch census + store offsets — done (§2.2);
  (4) R's floor literals — done (§2.4); (5) S's sign proof vs
  L's demand signs — done (§1(b)).
- Not audited in this pass: stages T, U, X, Y (out of scope) —
  their claims are cited only where the gap list needs them
  and are marked *unaudited* wherever used. Q's whole-image
  naming scans and V's per-poll answer counts were accepted
  from their artifacts after consistency checks, not re-run.
