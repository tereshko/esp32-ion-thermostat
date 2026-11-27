# VERIFY — EMULATOR-SPEC.md fidelity to sources

**Date:** 2026-11-26. **Target:** `EMULATOR-SPEC.md` (1,408 lines).
**Method:** the spec's concrete claims were extracted section by section
and checked against the cited source text (stage reports O/P/Q/R/S/T/U/V/Y/AA/B7,
FIRMWARE-AUDIT-2.md, THERMOSTAT-PROTOCOL-MAP.md as errata-corrected).
Verdicts: CONFIRMED / REFUTED / IMPRECISE (content traceable but stated
loosely) / UNVERIFIABLE. Failures quote spec line + source line.

---

## REFUTED

### R-1. §6.6 — 061F length stated as 72 B; every source says 81 B

- Spec §6.6: "`061F` (72 B status frame)".
- Source T §5.4 heading: "061F — the **81-byte** refrigeration block".
- Source Map (a): "20→53 `061F` | **81 B** float32 array"; Map (c):
  "`061F`→53 (**answered, 81 B**)"; Map (e): "ODU `061F` (81 B floats)".
- The spec contradicts itself: its own §1.2 tier table says
  "`061F`→53 (**81 B** refrigeration block)".
- 72 B is the size of `4202` (§4.1) — a probable slip. **Fix: 72 → 81.**

### R-2. §6.2 — 0605 value census mislabels a payload-form count

- Spec §6.2: "Observed values: **571 idle bursts at 0.0**; 34 bursts
  at 5.0; exactly one frame at 3.0."
- Source T §2.1 census table (all 651 writes): payload
  `00000000000001` (float 0.0, [4]=0) ×**571**; payload
  `00000000010001` (float **0.0**, [4]=1) ×**45**; `40A00000010001`
  (5.0) ×34; `40400000010001` (3.0) ×1.
- So the float value 0.0 occurs in **616** bursts, not 571; 571 is the
  count of one payload *form*. As a value census the sentence is
  wrong; the [4]=1 windows are discussed later in the same §6.2, so
  the section is repairable by rewording ("571 bursts of the
  [4]=0 idle form, plus 45 at 0.0 with [4]=1"). **Fix the sentence.**

---

## IMPRECISE (minor; content traceable, statement loose)

### I-1. §5.6 step 5 — floor selector byte misattributed

- Spec: `floor = FUN_1804fca0() = max( C750 ? C750 : 300 , 175 )`.
- Source R §1.2: `max(C74F ? C750 : 300, 175)` — the condition is the
  separate byte **C74F**, not `C750 ≠ 0`. Whether the two are
  effect-equivalent is not established in R. One-token fix.

### I-2. §1.2 — one poll row omitted

- Map (a): "**Every ~17 s**: 20→44 `0304`; **20→53 `0602`**."
- Spec §1.2's ~17 s row lists only `0304`→44; the `0602`→53 read is
  absent from the tier table (0602 appears in the spec only in §6.7's
  not-applicable list). Omission, not invention; a poll-faithful
  emulator should include it or note the omission.

### I-3. §6.6 — TLV tag list carries the wrong provenance tag

- Spec tags the 0302/0303 TLV tag assignments [Map (a)]; the Map does
  not enumerate the tags. The assignments are in **T §5** (lines
  253–260: 0x111 OAT [INF], 0x112 coil [INF], 0x130 suction, 0x145
  discharge, 0x14A superheat; 0303 types 0x100/0x148 ÷16). Content is
  correct; the tag should read [T §5].

### I-4. §1.3 — burst-spacing citation

- Spec cites the +41/+45/+45 ms spacing as "[AA via U B7]". The
  spacing is stated in **U** (B7 section: "Burst internal spacing:
  0305 → +41 ms 0403 → +45 ms 0409 → +45 ms") and in N's timeline;
  AA is not the source. Content correct.

---

## Mandated checks

### (1) Q-derived material uses audit-2-corrected labels — CONFIRMED

Grep scan of the whole spec for reversed readings (`CCDC`↔cool,
`CCC4`↔heat, "cool excess latch", "heat ≥61 derate"): **no hits**.
Positive confirmations:

- §5.3: "CCC4 (mode-2/cool table), CCDC (mode-1/heat table)".
- §5.4 inverse: "heat (CD7D == 1): CCDC; cool (CD7D == 2): CCC4".
- §5.4 step 3: the excess latch is over **CCDC's** maximum and is
  explicitly "in **heat**" (matches Q §3's gated latch at CD7D==1 as
  re-labelled by Audit-2 §2.3 consequence 2).
- §5.4 forward combine: "heat (==1): CD8C := interp(CC34, P1) +
  interp(CCDC, P2) — heat demand is the sum of **both** channels;
  cool (==2): CD8C := interp(CCC4, P2) — channel 2 alone" (Audit-2
  §2.3 consequence 3 verbatim in substance).
- §5.4 clamp table: the size-band derate with **≥61 → v := 0.0** is
  assigned to **cool (==2), bit 0x20 set**; heat (==1) set gets the
  two-value band clamp {0.0, 1.0, 1.3/1.4}. Cross-checked against
  Q §1's own table (Q lines 67–69 + the FUN_181f48de band-set text)
  under Audit-2 §2.3 consequence 1: FUN_181f4b4a (size bands) =
  cool chain via FUN_181f4bca; FUN_181f48de (two-value clamp) =
  heat chain via FUN_181f4ad8. Spec matches. Both "clear" rows have
  identical content in Q (size <31, v ≥ 2.0 → 2.0), so their
  assignment is safe either way.

### (2) DIR-B lengths/blobs are the audit-2 per-class values — CONFIRMED

Spec §2.4 table vs Audit-2 §3.1 table:

| Table | Spec §2.4 | Audit-2 §3.1 (our class) | Verdict |
|---|---|---|---|
| 0305 | 0x40, 12 B, 0xFFF85802 | 0x40: 12 B, blob 0xFFF85802 | ✓ |
| 0307 | 0x40, 4 B, 0xFFF85841 | 0x40: 4 B, blob 0xFFF85841 | ✓ |
| 0605 | 0x52, 7 B, 0xFFF85C8D | 0x52: 7 B, blob 0xFFF85C8D | ✓ |
| 060D | 0x52, 1 B, 0xFFF85CCE | 0x52: 1 B, blob 0xFFF85CCE | ✓ |
| 061E | 0x52, 9 B, 0xFFF85D44 | 0x52: 9 B, blob 0xFFF85D44 | ✓ |
| 3E02 | 0x0E, 1 B | AA §7: class 0x0E, len 1 | ✓ |

AA §7's first-record values (0307 = 3, 060D = 13, blobs
0xFFF857F6/85C86/85CC1/85D3B) appear **nowhere** in the spec. The
spec's header note also states the correction explicitly.

### (3) DIR-C length discrepancy flagged open — CONFIRMED

§4.1 carries the note ("**Discrepancy, unresolved:** the DIR-C
length fields for `0302`/`0304`/`0307` (32/24/24) exceed the answer
sizes observed on the wire … wire-observed sizes govern"), and §11
lists "DIR-C lengths" as an open item with what closes it.

### (4) Provenance tags and [INF] marking — CONFIRMED

Every normative block carries a bracketed source tag (≈260 "§"
references). Inferences are marked: R = 3/4 identities "[INF
strong]" (§5.1, matching S §4's "[INFERENCE — strong]"), CD1C
Σ = 1 "[INF, unproven]" (§5.2), X = 60 "[INF]" (§9.1), size-byte
semantics "[INF]" (§5.4), 0302 tag identities "[INF]" (§6.6),
heat-staging form "[INF: same form, unverified producer]" (§5.5).

### (5) §9.1 completeness vs Audit-2 B-12 — CONFIRMED

Audit-2 B-12 enumerates: G, K9F4, CA04/CA24/C880/CD1C, FS_1FDF,
store[8], X (+ CD1C normalisation). Spec §9.1 contains **all** of
them, plus CC52 with primary candidates **{0x8141, 0x91C1}** and
{0x8142, 0x91C2, 0xC195} not excluded (P §7.3 verbatim), plus
legitimate extras (CD73, CBF4, U1/U2, C74D/C74E, CFM store limits,
CFM table contents, field 0x1B). §9.3's snapshot addresses match
P §7.4 exactly (CC52 @0x3C0E4A21, CBF4 @0x3C0E4A23, R @0x3C0E4A28,
twin @0x3C0E4A32, tables @0xFFF8CCC4/CCDC/CD04/CC04/CC1C/CC34,
"24 B each"; debug ports 4002/14321 flag-disabled — P §7.4).

---

## Section-by-section spot verdicts

- **§1.2 poll tiers** — CONFIRMED vs Map (a): tier structure, the
  030A constant `014F4F02001F006B000010100115` (Map line 66), 0302→44
  irregular gaps 0.4–28 s median ~5.7 s (Map line 107), ~11 s tier
  drift 9.9–12.7 s (Map line 57), 0625 ~29 s (Map line 95), 031D
  write ~30 s (Map line 163). Exception: I-2 (0602 omission).
- **§1.3 burst** — CONFIRMED: 0305 12 B idle `…78`; 0403 `00010100`;
  0409 `00010000`; 0307 write 4 B (Audit-2 E-22); ODU set and idle
  payloads = T §11 items 1–8. Spacing: I-4.
- **§1.4 tolerances** — CONFIRMED: latency median 19 ms / p90 48 ms
  and 0.6 % unanswered (Map lines 49–52); max steady TX gap 2.81 s
  (Map line 333); wizard gap 4.90 s (Map lines 322–336).
- **§2.1 frame layout** — CONFIRMED vs AA §3 (AA lines 112–113:
  [4] length, [5] = rec[2], [6] = rec[3] XOR 0xC0 when nonzero;
  kind table: kind 1 [4] = 3 with empty payload ⇒ length =
  3 + payload; kinds 4/5/6 as spec'd).
- **§2.3 CRC** — CONFIRMED vs AA §1: nibble formula with tableA
  @0x182B598C / tableB @0x182B59AC (AA line 62), byte-swapped
  return → wire little-endian; verification counts 2000/2000,
  1532/1532, 101352/101352 as in AA.
- **§2.5 RX classification** — CONFIRMED: broadcast test
  "frame[0]==frame[1] and frame[0] > 0xF0" is AA's (AA line 131).
- **§3 boot** — CONFIRMED vs U: B0 furnace bursts (U line 43:
  ×6, ~45 ms, repeated +62.3/+124.1/…); B1 triplet and the
  78.23 s-silence re-commissioning note (U line 70); first 3B05
  answer +196.6 s (U line 49); B4 first steady read +23.95 s, last
  probe +61.76 s, boot-to-steady ≈62 s (U lines 121–124); 0418 ×2
  at ≈+62 s (U line 129); B5 031C "byte 0 = per-device counter"
  (U line 162) and never written by our Ion in 101,352 frames;
  B7 first burst +39.10 s (U line 192); B2 "do not probe 0x0E"
  (U §2). Handoff +16.7 s and sweep retry rules per Map (c)/U B2–B3.
- **§4.1 served sizes** — CONFIRMED: 3B02 29 / 3B03 150 / 3B04 11 /
  3B05 11 zeros [V §1.1]; 4012 7 B real data (V line 56); 4202 72 B
  [Map (b)]; ~8 % dropped SAM polls (V line 62); DIR-C list = AA §7
  with the discrepancy note (see mandated check 3).
- **§4.3 SAM writes** — CONFIRMED: "3B03 written 6× (150 B), 3B02
  once (29 B)" (V line 75); change-flag dialect per V §3 item 6.
- **§4.4 / §10 SAM holdoff** — CONFIRMED: 180 s after a 0x1F frame
  (V line 293).
- **§4.5 identity** — CONFIRMED vs Map (b) (line 255 hex + decoded
  line 262): INFINITY NEXT GEN UI / CESR******-**.79 / SYST0101CW.
- **§5.1 mode machine** — CONFIRMED vs S: CD7D 1/2/3 (S, adopted by
  Audit-2 as reference); field 0x1B changeover minutes ×60
  (S line 37); arbiter sums (S line 133); R = {0,1,2,3,4} with
  3/4 marked [INF strong] (S lines 176–180); ±0.75 demand forms
  (S §5 via FUN_1816deec; joints re-verified in Audit-2 §1(b)).
- **§5.2 demand formula** — CONFIRMED vs O, in several places
  verbatim: path A/B selection by FS_1FDF (O lines 165–184),
  `t_i = CA04·e·(FS_1FDF ≠ 0 ? 15.0 : 1.0)` (O line 207), the
  single-zone reduction block (O lines 474–477) matches the
  spec's reduction formula term for term, including
  `h`'s share term `CD8C·(CD1C[k] − 1)`; side state CE00/CE64
  (O lines 227, 300). C870 branches per O §3 (Audit-2 §2.1 notes
  the branch predicates are decompiler-transcribed — the spec
  flags exactly this provenance).
- **§5.3 threshold tables** — CONFIRMED vs P: K = 34.286 ×
  (137.0 + 3.5·X) (P line 177); branch rows 0x8242/0xA2C2 and
  0x8142/0xA1C2 (P lines 224–225); bounded tables {0, 60000, 0, 0}
  / {0, 59486.2, 0, 0} / CD04 {5.0,…} (P line 832); sensitivity
  24000/23794.5 and 72000/71383.5 (P lines 819–823); class-word
  encoding and category map (P §6); twin 3414.0 multipliers and
  0.4/0.6 tapering (P lines 490–494).
- **§5.4 coordinate conversion** — CONFIRMED (see mandated
  check 1); latch reset via 0x3C12A84C = segment endpoint / 2
  (Q line 245); clamp dispatcher band set {0.0, 1.0, 1.3/1.4, 2.0}
  (Q lines 73–77).
- **§5.5 staging/arbitration** — CONFIRMED: ×1.25 / ×0.25 / ×0.01
  hysteresis, no timers (E via Audit-2 §1(b), emulator-verified
  12/12 by M); heat producer = gap B-11 with S's five candidates;
  [0]/[2] never co-active in 674 frames (Audit-2 §1(b) census);
  CD4A transition table and unproven enum binding (S §7).
- **§5.6 CFM** — CONFIRMED vs R: producer FUN_1804e4b6; floor
  block {175, 300, 200, 300, 350, 325, 325, 325, 350, 350, 400}
  @0x1830B108 (R lines 149–151; Audit-2 §2.4 re-derived, entry
  @…112 = 325); the `if (C9F0 != 0)` demand-floor gate (R line
  119); step-5 gating "any of CD86/CD87/CB55/CB56 ≠ 0" (R line
  107); min-raise family {200, 325, 350, 0.85, 1.0} (R line 273);
  {375,400} live via the CD4B-windowed getter (Audit-2 §1(e));
  capture anchors (1368→1617, 1166, 1760 ≈ 5 t × 352, 1750
  commissioning) = R §8/§9. Exception: I-1.
- **§5.7 0305 assembly** — CONFIRMED vs Map (e)/R §7/T: [0] heat
  stage, [2] cool stage, [4..5] BE16 CFM, [11] 0x78.
- **§6.1/6.3/6.4 cooling payloads** — CONFIRMED vs T §11 items
  1–8 and §3: 061E `0F3FD851EC06000000` in 651/651 bursts
  (T line 43); 060D 02/00 behaviour and ~2-burst lead.
- **§6.2 v1 law "5.0 whole call"** — CONFIRMED as T §11 item 5's
  implementable rule; the single 3.0 transient (2026-11-03) and
  the [4] ≈3 min (18-burst) tail are T §2.2/§2.3 verbatim.
  Exception: R-2 (the census sentence).
- **§6.5 ODU self-ramp** — CONFIRMED: target RPM 2180 → 2850 →
  3700 → 4140, 0608 CFM 938 → 1600, EXV 100 % (T lines 67–68).
- **§6.6 readbacks** — 0604/0608/060E items CONFIRMED (T §5.4,
  Map (a)); 061F changing-byte ranges (17–20, 30–33, 58–61)
  CONFIRMED (T §5.4); **length REFUTED (R-1)**; TLV tags IMPRECISE
  provenance (I-3).
- **§7 B-7 byte** — CONFIRMED vs B7: identical XX in 153/153
  pairs, 63 values, range 70–194 (B7 §1); exclusions incl.
  r = −0.23 vs OAT (B7 §2); fingerprint drifts heat −0.76, fan
  −0.47, cool −0.24, idle +0.32 (B7 lines 149–151); recipe
  "init at room temperature, +0.3/tick idle, −0.8/tick heat,
  −0.5/tick fan, clamped to ~70–195" (B7 lines 183–184) —
  the spec's recipe matches verbatim.
- **§8 protections** — CONFIRMED on spot checks vs Y: freeze
  T-14 (Y line 792 — spec's T-12 reproduces Y's "no evidence /
  emulator's own decision / ≈40 °F industry norm" framing
  exactly); cooling blower-OFF 5/30/90 factory 90† (Y line 816);
  heat blower-OFF 90/120/150/180 factory 120 (Y §6); ignition
  B-1: prepurge 15 s, warm-up 17 s, proving 2 s from 5 s after
  valve, ≤4 trials → 3 h lockout (Y line 808); fault memory
  7 codes / 72 h (Y line 607); ODU anti-short-cycle 3.5 min,
  PEV 150 s + 15 s (Y lines 652, 820), sump warm-up 10 min
  (Y line 655), standby ≈2 min (Y §6). §8.1 T-15's "no thermostat
  min-off/min-run" = Y §4.3 T-21 as cited.
- **§9 parameters** — CONFIRMED (mandated check 5); §9.2's linear
  sensitivity and "one staging observation pins store[8]" =
  P §7.5 (P line 839).
- **§10 failover** — CONFIRMED on its factual anchors: max
  steady TX gap 2.81 s (Map line 333); ODU standby ≈2 min
  (Y §6; Audit-2 E-19); T-1 quantities (Ion recovery time,
  furnace comm-fault timeout) correctly stated as **both
  unmeasured**. The "listen silently ≥ 2 min" rule is presented
  as the parent *design*, not as a source fact — it is a design
  decision, not a fabricated evidence claim.
- **§11 gap list** — CONFIRMED vs Audit-2 §5.1/§5.2: B-2 (open,
  candidates as in P §7.3), B-5 (behavioural only), B-11 (new,
  heat producer), B-12 (data), B-7 residual (correctly reconciled
  with the B7 report that Audit-2 predates), B-8′ residue
  (non-blocking), DIR-C lengths (spec's own addition, flagged),
  T-1…T-5 with the ODU ~2 min addition to T-1. Closed-gaps record
  matches Audit-2 §5.3.

## UNVERIFIABLE

- None load-bearing. Two areas rest on a single audited source
  rather than independent re-derivation here: O §3's
  FUN_1809f4a4 branch predicates (decompiler-transcribed; flagged
  in the spec itself) and S §2's AE45 toggle-direction details
  (S upheld in full by Audit-2 §2.5). Both are cited with correct
  provenance and neither is contradicted by any other source.

## Bottom line

No spec-only inventions were found: every load-bearing number,
formula and rule traces to a stage report, an audit ruling, or
the map. Two statements are REFUTED as written (R-1: 061F = 72 B;
R-2: the 0605 0.0 census count) and four are IMPRECISE (I-1…I-4).
All six are one-line fixes; none touches the control law, the
frame layer, or the failover design.
