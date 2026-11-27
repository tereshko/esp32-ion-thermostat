# VERIFY — Decision-module machines (stage E, as corrected by S / audit-2)

Independent re-derivation from primary artifacts only: stage E decompiles/listings
(`firmware-re/stageE/out/`), pool words read raw from the flat image
(`firmware-re/stageB/flat.bin`, base 0x18040000, big-endian). Report prose was not trusted;
every constant below was read from the image bytes.

## Claim 1 — FUN_180c54d8 staging hysteresis — **CONFIRMED**

Pool resolution (raw u32 @ pool slot → target/value):

| Pool slot | Value | Role |
|---|---|---|
| 0x180C562C | 0xFFF8CD7D | gate byte (CD7D) |
| 0x180C561C | 0xFFF8CD49 | state byte read **and written** (CD49) |
| 0x180C5630 | 0xFFF8CCC4 | table base = CCC4 |
| 0x180C5634 | 0xFFF8CC5A | index byte (CC5A) |
| 0x180C563C | 0xFFF8CD44 | demand (CD44) |
| 0x180C5638 | 0x3FA00000 = **1.25** | stage-2 multiplier |
| 0x180C5640 | 0x3E800000 = **0.25** | stage-1 multiplier |
| 0x180C5644 | 0x3C23D70A = **0.0099999998** | drop multiplier (×0.01) |

Listing (`listing_stage.txt`, FUN_180c54d8 section) semantics:

- Entry: `cmp/eq 0x2` on CD7D; if ≠ 2 → write 0 to CD49 and return. **Gate CD7D==2 confirmed.**
- State 0: demand > CCC4[CC5A−1] × 1.25 → 2; else CD49 := (CCC4[1] × 0.25 < demand) ? 1 : 0.
- State 1: demand > CCC4[CC5A−1] × 1.25 → 2; else CD49 := (CCC4[1] × 0.01 < demand) ? 1 : 0
  (stage 1 drops at demand ≤ table[1] × 0.01).
- State 2: if demand ≤ CCC4[1] × 0.01 → 0; else rollback: demand < CCC4[CC5A−1] × 1.00
  (bare table value, no multiplier) → 1, else stay 2.
- All four claimed constants (×1.25 engage-2, ×0.25 engage-1, ×0.01 drop, ×1.00 rollback)
  verified exactly, including which table element each uses: engage/rollback use
  CCC4[CC5A−1]; engage-1/drop use CCC4[1] (base+4).
- **No timers:** the function's full listing contains zero `jsr`/`bsr`/computed calls —
  it is a pure state machine over CD49. Confirmed.
- Output cell is CD49; table is CCC4 as audit-2 ruled.

## Claim 2 — Quantizer FUN_180c576c — **CONFIRMED**

Pool: input = float @0xFFF8CB58 − (float)byte @0xFFF8CABB (same differential source as the
trim, claim 4); state cell = 0xFFF8CD4B (CD4B), read and written (4 writes to 0xFFF8CD4B
in `listing_quant.txt`). Constants in its pool: +5.0 (0x180C58B0), −5.0 (0x180C58B4),
4.0, 6.0, −1.0, +1.0, −6.0, −4.0. State-dependent band edges:

| Current CD4B | Upper edge (→1 above) | Mid edge | Lower edge (→4 below) |
|---|---|---|---|
| 1 | 4.0 | 0.0 | −5.0 |
| 2 | 6.0 | −1.0 | −5.0 |
| 3 | 5.0 | +1.0 | −6.0 |
| 4 | 5.0 | 0.0 | −4.0 |

That is exactly nominal Schmitt thresholds **+5 / 0 / −5** with **±1 hysteresis**
(each edge sits at threshold ± 1 depending on the current state). Output ∈ {1,2,3,4}
written to CD4B. Confirmed.

## Claim 3 — Arbitration FUN_180c5832 — **CONFIRMED** (table extracted independently)

Pool resolution: gate = CD7D (0x180C58DC → 0xFFF8CD7D) **and** byte @0xFFF8CB5C
(0x180C58E0) == 1; if either fails → CD4A := 0, CD4C := 0, return (matches stage S:
runs only in cool, CD4A ≡ 0 in heat). Inputs: CD4A-in (0xFFF8CD4A), CD4B (0xFFF8CD4B,
tested ∈{1,2} vs {3,4}), CD49 (0xFFF8CD49, tested 0/1/2). Outputs: CD4A (writes of
0,1,2,3,4,5 all present) and latch CD4C (0xFFF8CD4C); auxiliary byte @0xFFF8CB48 also written.

**Latch rule — exact match to the claim:** CD4A-in == 0 → CD4C := 0; == 1 → CD4C := 1;
∈ {2,3,4,5} branch → CD4C := 0 if CD4A-in ∈ {4,5}, else 1. Net: **CD4C = 1 iff
CD4A-in ∈ {1,2,3}; 0 iff ∈ {0,4,5}.** Confirmed.

Transition table (CD4A-out), extracted from the decompile with pools resolved.
Entries marked † depend on boolean helper predicates (FUN_180C5C7C, FUN_181F066C/672/678 —
getter-style calls whose semantics are outside this function):

| CD4A-in | CD4B band | CD49=0 | CD49=1 | CD49=2 |
|---|---|---|---|---|
| 0 | {1,2} | 0 or 1 † (also pre-gated by FUN_181F0672()==0 → 0) | 3 | 5 |
| 0 | {3,4} | 0 | 4 | 5 |
| 1 | {1,2} | 0, 1 or 2 † | 3 | 5 |
| 1 | {3,4} | 0 or 4 † | 4 | 5 |
| 2–5 | {1,2} | 2 (or 0 †) | 3 | 5 |
| 2–5 | {3,4} | 4 or 0 † | 4 | 5 |

Deterministic core matches stages E/S exactly: driven by CD49 + CD4B band; CD49=2 → 5
always; CD49=1 → 3 (band {1,2}) / 4 (band {3,4}); state is sticky (self-preserving
outcomes on most CD49=0 paths). Confirmed, with the † caveat recorded.

## Claim 4 — Setpoint trim FUN_180c55f2 — **CONFIRMED**

Listing head: x = float @0xFFF8CB58 − (float)byte @0xFFF8CABB; then clamped against
constant @0x180C5650 = **6.0** (upper) and @0x180C5894 = **0.0** (lower):
**D = clamp(x, 0, 6)** exactly. In the per-zone loop (8 zones), zone values are
compared/clamped against the float @0x1830B128 = **70.0** (raw 0x428C0000) — the
claimed cap. (Loop also divides by 2.0, constant @0x180C58A4.) Confirmed.

## Claim 5 — Satisfaction averager FUN_18183d34 — **CONFIRMED**

Averages per-zone satisfaction deviations over ≤ 8 zones (arrays @0xFFF8CABC /
0xFFF8CB60, presence @0xFFF8CBA9, getter FUN_181F0428), per-zone deviation clamped
to [0.0, 3.0] (constants @0x18183E70 = 0.0, @0x18183EB0 = 3.0). Output state cell is
the dictionary cell **0x3C12E6C4** (@0x18183EBC), driven by two thresholds:
@0x18183EB8 = **2.5**, @0x18183EC0 = **1.5**. Logic: average > 2.5 → state := 0;
average < 1.5 → state := 1; between → no write (hold). That is a 2.5/1.5 hysteresis
exactly as claimed. Confirmed.

## Claim 6 — Source enum dictionary @0x18302E1C — **CONFIRMED**

Raw bytes at 0x18302E1C read directly from the image:

```
cooling\0 hpheat\0\0 eheat\0\0\0 gas\0 reheat\0\0 fangas\0\0 fan\0 looppump\0 …
```

The first six strings are exactly `cooling, hpheat, eheat, gas, reheat, fangas`
in that order (followed by `fan`, `looppump`, `day1`, …). Confirmed verbatim.
(This verifies the dictionary contents/order only; the index↔CD4A binding remains
unproven, as stage S already ruled — the claim tested here was the dictionary itself.)

## Claim 7 — Refresh FUN_181efdfc over block 0xFFF8C8xx–0xFFF8CDxx — **CONFIRMED** (bounds from its own accesses)

All 60 pool references in `decomp_181efdfc.c` were resolved from the image.
19 distinct targets fall in the decision block, spanning **0xFFF8C8CC … 0xFFF8CD8C** —
inside the claimed 0xFFF8C8xx–0xFFF8CDxx block (includes CD44 demand, CD49/CD4A/CD4B/
CD4C, CD7D mode, CD8C). Two further RAM targets sit below the block
(0xFFF8C560, 0xFFF8C580); they do not contradict the claim that the refresh operates
over the C8xx–CDxx decision block. The "Clarinox computed properties" characterization
is stage H's platform interpretation and is not itself testable from this function;
the block-bounds substance is confirmed.

## Claim 8 — The "0.4472" coefficient (stage E history) — **CONFIRMED** (trap verified from raw bytes)

The constant sits in FUN_180C5EBC's pool at **0x180C6044**: word `0x3EE4F8B5`,
which read as float32 is **0.44720998** — the stage E reading. The 8 bytes at
0x180C6044 are `3E E4 F8 B5 80 00 00 00`, i.e. the big-endian **double
9.9999997e-06 ≈ 1.0e-5**. True form: the path-B increment's lower band edge
(1e-5 ≤ |e| ≤ 2.0; the upper edge 2.0 sits @0x180C6038 = 0x40000000), matching
stage O's correction. The misread mechanism (high word of a double taken as a
float32) is reproduced exactly from the bytes. Confirmed.

## Claim 9 — Dictionary/settings spot-checks — **CONFIRMED** (with one precision)

- **Defrost fan delay ≈12 s:** present as installer help text in the image —
  setting title "Heat Pump Defrost Fan Delay Selection" @0x182D8DDC; help body
  @0x182D8E54: "Turns on the outdoor unit fan at the end of a defrost cycle for
  **approximately 12 seconds** to help reduce nuisance refrigerant noise…".
  Precision: the 12 s exists as help-text documentation of the setting, not as a
  numeric code constant — which is how stages E/Y themselves sourced it.
- **HP low-airflow multipliers 0.63 / 0.8:** help text @0x182D8FF6–0x182D9068
  ("Heat Pump Low Airflow Multiplier … **0.63 is used for Bristol compressors and
  0.8 is used for Copeland compressors**") verbatim. Numeric float **0.63**
  (0x3F2147AE) sits in the flash parameter record @0x1830B120 (3 occurrences
  image-wide; neighbours in the record: 1.05 @0x1830B124, 70.0 @0x1830B128 —
  the same record the trim's cap comes from). Float 0.8 (0x3F4CCCCD) occurs
  13× image-wide. Both values exist as constants as claimed. Confirmed.

## Summary

9 / 9 claims CONFIRMED, 0 REFUTED, 0 UNVERIFIABLE. Precisions recorded:
claim 3's CD49=0 transitions additionally depend on three boolean helper predicates;
claim 7 has two refresh targets just below the block; claim 9's 12 s is help text,
not a code constant. Stage E's mechanics, as corrected by S and audit-2, survive
independent re-derivation intact.
