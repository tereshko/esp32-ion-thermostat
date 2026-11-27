# VERIFY — versions corpus (independent re-derivation)

Verification date: 2026-11-26. Method: all results below were re-derived from the
primary artifacts on disk (packages under `firmware-re/versions/downloads|extract/`,
decoded regions under `firmware-re/versions/decoded/`, `ion-firmware/carrier/`) with a
freshly written decoder and extractors — report prose (FIRMWARE-ANALYSIS-VERSIONS.md,
stage D) was used only to locate formats, never as evidence. Working scripts:
`/tmp/verify_versions/` (`mydecode.py`, `decode_all.py`, `coils4.py`, `claims5678.py`,
`claim4.py`).

## Claim 1 — 16 official Series B images present, decodable, 0 bad checksums — **CONFIRMED**

On disk: 16 Series B packages (BINF????.hex) for exactly the claimed versions
2.40, 3.00, 3.01, 3.40, 3.60, 3.61, 3.62, 3.94, 4.05, 4.31, 4.47, 4.56, 4.66, 4.70,
4.74, 4.79 (plus the 0200 package, see claim 4). No packages for the 9 "not obtained"
versions exist on disk.

My own decoder (binary Intel-HEX-style records, two's-complement checksum per record)
was run on all 17 packages: **bad checksums = 0 in every package**, gap resyncs = 0,
record counts identical to the stored `meta.json` (e.g. 4.79: 76,194 records), and my
decoded regions are byte-identical to the on-disk `decoded/<ver>/region*.bin` in all
17 cases; rebuilt flat images are byte-identical to on-disk `flat.bin` wherever one
exists (0431/0447 ship regions only — they decode fine regardless).

Note: 0301 exists in two brand variants on disk (Carrier and Bryant); the corpus
decodes the Carrier one. This does not affect the count of 16.

## Claim 2 — official 4.79 byte-identical to our image — **CONFIRMED**

Computed directly:

| file | size | MD5 | SHA-256 |
|---|---|---|---|
| `ion-firmware/carrier/BINF0479_Carrier.hex` | 10,188,916 | `e31903228bf39a4bc9c0a2a74192359e` | `2d1a9ea3c723e245fbabe6089118f750adfc6dd249c9b2e76a79d3f8a4c90c04` |
| `versions/extract/0479/TSTAT/BINF0479.hex` | 10,188,916 | identical | identical |
| `versions/extract/0479_icp/TSTAT/BINF0479.hex` | 10,188,916 | identical | identical |

MD5, SHA-256 prefix (`2d1a9ea3…`) and size all match the claim exactly; all three
copies on disk are the same bytes.

## Claim 3 — coil EN(A,D)4X61 = 1.69 in all 16 versions; no coil parameter ever changed — **CONFIRMED**

Extraction (per version, from the decoded regions): the record for `EN(A,D)4X61`
carries parameter bits `0x3FD851EC` = float32 1.69 in **all 16 versions** (exactly one
parameter value per version; string/record addresses move, the value never does).

Full-catalog comparison: I extracted every coil catalog record in every version.
The catalog *layout* changes across eras — stride-12 paired records
`{ptr, ptr, param}` (two brand variants sharing one parameter) in 2.40–4.31,
stride-8 `{ptr, param}` from 4.31/4.47, plus stride-14 `{ptr, b4, b5, f1, f2}`
catalogs in 4.66–4.79 — so records were normalised to name → value before comparing.
Result: **270 distinct model names** in the parameter catalogs, **0 names with more
than one parameter value across the 16 versions**; **116 stride-14 names** (4.66–4.79),
**0 changes**. Extractor validation: for 4.79 my extraction reproduces stage D's
independent dump exactly (145 parameter names, 116 stride-14 names, 0 mismatches,
0 extras). Values never changed; only the container format did.

## Claim 4 — the V0200 slot package is Series C, not Series B 2.00 — **CONFIRMED**

`downloads/Version_0200_ICP.zip` contains `TSTAT/CINF0200.BEX` (CINF prefix, not
BINF). Decoded: load base **0x60100000** (not the Series B SH-2A base 0x18040000);
the image opens with a Cortex-M vector table — first u32 LE `0x80800000` (initial SP),
second `0x60100331` (Thumb reset vector). It carries board id **`CESR******-**.00`**
(the Series C control board) and 19 `Infinity` strings. It is architecturally
impossible for this to be a Series B 2.00 image. Caveat: the literal string
`SYST0201CW` does not occur in the image (count 0) — the Series C attribution rests on
the CINF package, the Cortex-M memory map, and the CESR131755 board id, not on an
in-image model string.

## Claim 5 — layout break at 4.31 (Sparkplug dictionary + ROM FS bank appear) — **CONFIRMED**

Per-version region maps and string census from my decode:

- 2.40–4.05: 6 regions each; `spBv1.0` count 0; `sparkplug` count 0; no region at
  0x18810100.
- 4.31 and later: region at **0x18810100** (ROM FS bank) plus 0x18800000/0x1880fffc
  regions appear; `spBv1.0` count 1; `sparkplug` strings present (2–4). 4.31/4.47
  packages additionally carry a separate dictionary region at 0x3C125DE4/0x3C1297E4.

The break is exactly at 4.31, with no precursors in 4.05.

## Claim 6 — 3.61 differs from 3.60 by only 568 bytes; the only true hotfix pair — **CONFIRMED**

Byte diffs over the main span 0x18040000–0x18F40000 (0xFF-filled), adjacent pairs:

| pair | differing bytes |
|---|---|
| 3.60 → 3.61 | **568** |
| 4.66 → 4.70 (next smallest) | 3,934,155 |
| 3.00 → 3.01 | 4,235,613 |
| all other 12 pairs | 4.17M – 9.44M |

3.60 and 3.61 also have identical payload sizes (6,695,346 bytes each). Every other
adjacent pair is a multi-megabyte rebuild. 568 confirmed to the byte.

## Claim 7 — 4.79 removes `system/utilityEvent/demand*`, adds `totalDemandReductionPercent` (vs 4.74) — **PARTLY REFUTED**

Removal half **CONFIRMED**: 4.74 contains the full group
`system/utilityEvent/{enabled, priceResp, demandResp, priceLimit, priceOffset,
priceHtAbs, priceClAbs, demandOffset, demandHtAbs, demandClAbs, minLimit, maxLimit,
restoreDefaults}`; in 4.79 the four demand members (`demandResp`, `demandOffset`,
`demandHtAbs`, `demandClAbs`) are gone. The rest of the utilityEvent group remains —
it is the `demand*` subgroup that was removed, not the whole group.

Addition half **REFUTED**: `totalDemandReductionPercent` is present (×1) in **both**
4.74 and 4.79. Scanning all versions, it first appears in **4.66** (absent ≤4.56,
present 4.66/4.70/4.74/4.79). It was not added in 4.79.

## Claim 8 — VERSIONS' exact constant counts (audit-1 said non-reproducible) — **audit-1 CONFIRMED; VERSIONS' counts REFUTED**

Recount by me, big-endian float32 patterns over the full flat image (counts over the
main span are identical):

| constant | 4.79 | 2.40 |
|---|---|---|
| 400.0 (`43C80000`) | **4** | **3** |
| 375.0 (`43BB8000`) | 1 | 1 |
| adjacent pair {375.0, 400.0} | **0** | **0** |
| 0.01 (`3C23D70A`) | **5** | **4** |

So "{375,400} exactly once in every version" is false (400.0 occurs 4× in 4.79 and
3× in 2.40; the adjacent pair occurs 0× in both), and "0.01 = 5 everywhere" is false
(2.40 has 4). My counts reproduce audit-1's recount exactly (400.0: ×4 in 4.79, ×3 in
2.40; 0.01 in 2.40: ×4). The qualitative point behind the original claim — the numeric
core is stable across versions — is not decided by these counts either way; the exact
numbers in VERSIONS are not reproducible and should not be cited.
