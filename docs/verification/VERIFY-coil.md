# VERIFY-coil — independent re-derivation: coil DB, catalog, numeric censuses (stages D/K/I)

Verifier pass, 2026-11-26. Everything below was re-derived from primary artifacts —
`firmware-re/stageB/flat.bin` (Intel-HEX flat image, base 0x18040000, 0xFF-padded),
stage D/K output files, stage L decompiles, decoded per-version region files
(`firmware-re/versions/decoded/`) and the trace corpus (`traces/*.jsonl`) — not from
report prose. Report prose was read only afterwards, to locate where a claim diverges
from its own underlying data.

## Claim 1 — coil record for "EN(A,D)4X61" with parameter 1.69 — **CONFIRMED**

- ASCII search of the whole image: the string `EN(A,D)4X61` occurs exactly once, at
  **0x182C59A8** (file offset 0x2859A8), inside the model-name string pool
  (neighbours: `EA*4X61`, `ENH4X61`, `CVA**1814`, `CVAV*24`).
- The record referencing it sits in the CAT1 stride-8 array (base 0x182C4B30),
  **index 70, record @0x182C4D60**: `{u32 str_ptr = 0x182C59A8, float32 param}` with
  param bytes at 0x182C4D64 = **`3F D8 51 EC` = 1.69** (float value 1.6900000572).
- Surrounding structure verified by parsing the array: records are uniformly
  `{u32 BE str_ptr, f32 BE param}`, stride 8 — e.g. [68] `EA*4X61` → 1.93,
  [69] `ENH4X61` → 2.02, [70] ours → 1.69, [71] `OTHER` → 0.0.

## Claim 2 — word 0x3FD851EC occurs exactly 2 times — **CONFIRMED**

Byte-pattern census over the full 15 MB flat image:

- BE bytes `3F D8 51 EC`: **exactly 2**, both 4-aligned:
  - **0x182C4B24** — parameter of `CNPV*61` (CAT0 stride-8 array, record @0x182C4B20,
    str_ptr 0x182C56C4);
  - **0x182C4D64** — parameter of `EN(A,D)4X61` (claim 1).
- LE bytes `EC 51 D8 3F`: 0.

## Claim 3 — stage D extracted 263 coil records — **CONFIRMED**

Independent parse of all four model arrays from the image (bases/strides/counts taken
from the array geometry, every record's name pointer dereferenced and checked
printable): CAT0 stride-8 = 74, CAT1 stride-8 = 72, CAT0 stride-14 = 54,
CAT1 stride-14 = 63. **Total = 263**, all 263 records parse with valid model names.
Matches stage D's `model_arrays.txt` (74+72+54+63).

## Claim 4 — unified catalog spans 0x18404928–0x18409DCC with 5,417 records — **CONFIRMED**

Independent anomaly-tolerant walk (record = `{class byte ≠ 0, 0x00, id BE16}`,
ids strictly ascending) from seed 0x18404EC0:

- start **0x18404928**, end **0x18409DCC**, **5,417 records**;
- ids strictly ascending, all distinct, 0x0002..0x2222;
- exactly one anomalous record (class 0xD2 @0x18406D64, id 0x101B) inside the run;
- the walk breaks cleanly at both ends (adjacent words on both sides carry id 0x0000);
- my parse matches stage K's `catalog_full.txt` **line for line, 0 mismatches**.

Note on method: stricter walks reproduce stage K's intermediate results, not the
final one — class ∈ {1,2} gives a 550-record sub-block, class ≤ 0x40 stops at the
0xD2 anomaly with 2,319 records. The 5,417 figure depends on the anomaly-tolerant
rule; under that rule it is exact.

## Claim 5 — 0303/0305/0307 absent in 4.79's catalog, present in 4.47–4.74 — **CONFIRMED**

- 4.79 (claim-4 parse): ids **0x0303, 0x0305, 0x0307 absent** (0x0304, 0x0306,
  0x0605, 0x060D, 0x061E, 0x0104, 0x0316 present). The neighbouring odd ids 0x0301
  and 0x0309 are likewise absent.
- Older versions, catalogs reconstructed from the decoded region files and walked
  with the same rule (full catalogs, ids 0x0002..):

  | version | catalog span | records | 0301 | 0303 | 0305 | 0307 | 0309 |
  |---|---|---|---|---|---|---|---|
  | 0447 | 0x183F9ADC–0x183FF4F8 | 5,767 | YES | YES | YES | YES | YES |
  | 0456 | 0x183F6624–0x183FBB8C | 5,466 | YES | YES | YES | YES | YES |
  | 0466 | 0x183FBFE4–0x18401604 | 5,512 | YES | YES | YES | YES | YES |
  | 0470 | 0x18400164–0x184057BC | 5,526 | YES | YES | YES | YES | YES |
  | 0474 | 0x1842AEC0–0x184303DC | 5,447 | YES | YES | YES | YES | YES |

## Claim 6 — numeric census: 107000 / 135000 / 96000 = 0 in all encodings; CFM floats = 0 — **PARTIALLY REFUTED**

Full-image byte-pattern census, any offset, run independently for this pass:

| value | i32 BE | i32 LE | f32 BE | f32 LE | f64 BE/LE | ASCII | UTF-16LE |
|---|---|---|---|---|---|---|---|
| 107000 | **0** | **0** | **0** | **0** | **0** | **0** | **0** |
| 135000 | **0** | **0** | **0** | **0** | **0** | **0** | **0** |
| 96000 | 2 | 5 | **0** | **0** | **0** | **0** | **0** |
| 1617.0 (CFM) | — | — | **0** | **0** | **0** | — | — |
| 1760.0 (CFM) | — | — | 1 | **0** | **0** | — | — |

- **107000 and 135000: CONFIRMED** — zero in every encoding at any offset.
- **96000 as an integer: REFUTED as stated.** There are 2 BE + 5 LE byte-pattern
  hits — the identical hits stage K's own `census_full.txt` prints. All are
  incidental: the BE hits sit at odd addresses (0x1841E029 in data, 0x18862051 in
  the FS bank); four LE hits are unaligned, and the one 4-aligned LE word
  @0x18449504 is a cell inside a dense u32le table of similarly-shaped values
  (context `… 00 72 02 00 | 00 74 01 00 | 00 75 02 00 | 00 77 01 00 | 00 78 08 00 …`),
  not an isolated constant. 96000 as float/double/ASCII/UTF-16LE is genuinely 0.
  So the substantive conclusion (96000 is not stored as an equipment constant)
  stands, but the blanket "0 times in all encodings" is false for the int
  encodings — and stage K's §7 "explicit not-found list" (`96000` as i32 BE/LE: 0
  everywhere) contradicts stage K's own §1.2, which lists these hits correctly.
- **CFM floats: 1617.0 CONFIRMED 0; 1760.0 REFUTED literally.** Exactly one f32 BE
  hit @**0x18328042** — unaligned (≡ 2 mod 4), a cross-boundary byte artifact
  inside unrelated data, with no references. Stage K §7 and stage I §6 both print
  this same hit and classify it as "not a stored float / unlinked", so again the
  underlying data is sound and the zero-claim survives only in its substantive
  form: no stored, referenced CFM float constants.

## Claim 7 — 061E payload decode + commit path — **CONFIRMED**

- Traces: **651 frames** with reg `061E` across `traces/*.jsonl`, and **all 651**
  carry the identical payload `0F 3F D8 51 EC 06 00 00 00` (src 0x20 → dst 0x53,
  func 0x0C; first in coldstart @2026-10-29T16:58:58Z). Bytes [1..4] =
  `3F D8 51 EC` = the coil parameter of claim 1.
- Commit path, from stage D's decompiles (`stageD/out/decomp_18140bea.c`,
  `decomp_18140c80.c`): both functions write through the field-store setter
  (pool pointer `PTR_FUN_18140ea0`):
  - FUN_18140bea: writes the 4-byte parameter to field **0x59F**.
  - FUN_18140c80: writes **0x59F ← param (4 B)**, **0x1C7C ← b4 (1 B)**,
    **0x1C7D ← b5 (1 B)**, **0x1C7E ← (u16)(int)(f1 × DAT_18140EB0)**.
  - The multiplier was verified in the image: word @0x18140EB0 = `0x477FFF00` =
    **65535.0** exactly. The claim's `(u16)(f1 × 65535.0)` is exact.

## Claim 8 — stage I's negative vs stage L's producer reading — **stage L STANDS; stage I's headline REFUTED in its broad form, its narrow negative confirmed in part**

- **Producer question — stage L CONFIRMED from primary artifacts.**
  FUN_181f21d4's pool cells resolve in the image: `DAT_181f24a0 → 0xFFF8CCC4`
  (CCC4), `DAT_181f24a8 → 0xFFF8CCDC` (CCDC), `DAT_181f24ac → 0xFFF8CD04` (CD04),
  and stage L's decompile (`stageL/out/decomp/decomp_181f21d4.c`) shows indexed
  writes through all three pointers (`*DAT_181f24a0 = …`, `DAT_181f24a0[1] = …`,
  `[2]`, `[3]`, likewise for the other two) — the function computes the threshold
  tables; it is not a mere consumer. Any broad reading of stage I's headline
  ("no static path from furnace data to control") that denies this producer is
  refuted; this matches audit-1's ruling.
- **Constants leg of the narrow negative — CONFIRMED with one prose defect.**
  107000 is absent in every encoding (claim 6). For 53500: BE32 / f32 BE / f32 LE /
  f64 = 0, but stage I's prose ("107000 / 53500 in int32 BE/LE, float32, float64 —
  zero hits in every encoding") overclaims its own scan: stage I's `scan1.py`
  scanned 53500 **only as BE32** (its §6 table says exactly that), and one
  unaligned LE byte-pattern hit exists @0x18C1D9F7 in the FS bank — an incidental
  substring, not a constant. Substantively 53500 is absent as a stored value.
- **Remaining leg — UNVERIFIABLE in this pass.** Stage I's "no consumer of furnace
  (0316) data inside the control loop" rests on its 899-function accessor census;
  re-running that census function-by-function was outside this pass's scope. It is
  corroborated by audit-1's ruling but was not independently re-derived here.

## Scoreboard

| # | claim | verdict |
|---|---|---|
| 1 | coil record EN(A,D)4X61 → 1.69 | CONFIRMED |
| 2 | 0x3FD851EC exactly 2× | CONFIRMED |
| 3 | 263 coil records | CONFIRMED |
| 4 | catalog 0x18404928–0x18409DCC, 5,417 records | CONFIRMED |
| 5 | 0303/0305/0307 absent in 4.79, present 4.47–4.74 | CONFIRMED |
| 6 | census zeros (107000/135000/96000; CFM floats) | 107000/135000/1617.0 CONFIRMED; 96000-int and 1760.0 REFUTED as stated (incidental hits only; substantive conclusion stands) |
| 7 | 061E decode + commit path | CONFIRMED |
| 8 | stage I headline vs stage L producer | L CONFIRMED; I headline REFUTED (broad form); I narrow negative confirmed for constants, UNVERIFIABLE for the consumer census |
