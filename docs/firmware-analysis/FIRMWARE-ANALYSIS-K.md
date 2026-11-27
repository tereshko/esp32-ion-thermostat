# FIRMWARE-ANALYSIS-K — Stage K: whole-image numeric census keyed to the author's equipment + catalog-block audit

Target: Carrier/ICP "Ion" wall control firmware **BINF0479, v4.79** (Renesas
SH7269, SuperH:BE:32:SH-2A, image base `0x18040000`). Source image as in
stages A–D: `firmware-re/stageB/flat.bin` (15,728,640 B, covers
`0x18040000–0x18F40000`, gap fill `0xFF`).

**Scope of this stage.** the author's hypothesis (2026-11-26): stage D showed
the indoor coil is encoded as pattern → float parameter (`EN(A,D)4X61` →
`0x3FD851EC` = 1.69, committed to field `0x59F` and sent to the ODU in
`061E`). Perhaps the furnace, the outdoor unit, or "the board itself"
encode their parameters in similarly non-obvious forms. Stage K therefore
(1) censuses the whole image for our equipment's numbers in every
plausible encoding, (2) audits the two catalog blocks stage D noticed at
`0x18404EC0` / `0x18405D40` but set aside, and (3) hunts for any further
pattern/parameter databases beyond the four coil arrays.

Equipment numbers censused (from the Ion equipment-summary screen,
2026-11-26): furnace `G80CTL1352422A2`, gas heat **2-stage 107K BTU/H**
(model stem implies 135K input), ODU `HVA960GKA201`, **MultiStg AC 60K**
(5.0 tons), coil `EN(A,D)4X61` (param **1.69**). Capture-observed CFM
values (protocol map §e): **379, 1166, 1232, 1617, 1710, 1760**. Nominal
size ladder: **18, 24, 30, 36, 48, 60, 61**.

**Method.** Raw Python scanning of `flat.bin` is the primary method
(offset = address − `0x18040000`); all scripts are new code in
`firmware-re/stageK/` (`census.py`, `contexts.py`, `streams.py`,
`catalog.py`, `catalog2.py`, `catalog2b.py`, `catalog3.py`, `closing.py`,
outputs in `stageK/out/`). Dual verification in this stage = two
independent raw methods per claim (full-image byte scan vs. geometry
walk / tiling; pool-reference scan vs. record dump), plus cross-checks
against stage D/E's published Ghidra results where a code-consumption
claim is involved. Ghidra was not re-run in stage K; where a claim would
require it, the claim is downgraded to inference and says so.

**Headline results.**

1. **No furnace/ODU capacity encoding exists in the image in any tested
   encoding** (§1). `107000`, `135000`, `107.0`, `107000.0`, `135000.0`,
   `96000.0` occur **zero times** in every integer/float/ASCII/UTF-16LE
   form. The single ASCII `"107"` in the image is a UI message index
   (`"107-LOW INDOOR"`). Capture CFM values occur **zero times** as
   float32. This extends stage D's model-string negative to the numeric
   domain: the furnace/ODU parameters are not in this firmware — they
   arrive over the bus, as stage D inferred.
2. **The coil parameter word `0x3FD851EC` occurs exactly twice in the
   entire image**, both times as coil-DB record params: the author's
   `EN(A,D)4X61` (CAT1 stride-8 [70], word @`0x182C4D64`) and `CNPV*61`
   (CAT0 stride-8 [72], word @`0x182C4B24`) (§2). No third copy, no
   literal-pool copy, no LE form. Consumption is exclusively through
   stage D's indexed accessor/commit path.
3. **The "two catalog blocks" are one giant catalog** (§3): a single
   run of **5,417 records** `{class byte, 00, id BE16}` at
   **`0x18404928–0x18409DCC`**, ids `0x0002–0x2222` strictly ascending.
   Stage D's blocks were the class-{1,2} slices of it. The command
   tables `060B/060D/0610/061A/061E` and SYSTIME `0202/0203` **are**
   catalogued; the demand trio **`0303`, `0305`, `0307` is not** — the
   only equipment-table absences inside the catalogued id range.
4. **No further pattern/parameter databases exist** in the shapes
   searched (§4): no other pattern-string cluster, no other
   `{ptr, float}` array. The nine apparent extra `{ptr, float}` runs
   are Clarinox dictionary name→ID registration records — their
   "floats" are `0x3C12Exxx` property IDs (≈0.008937), proven by the
   pointed-to dictionary property names.
5. **Resource-stream caveat** (§5): stage D's "90 zlib streams
   decompressed" could not be reproduced — the image contains exactly
   90 zlib-*header-shaped* offsets in the resources region and **zero**
   streams that decompress as zlib or raw deflate anywhere in the
   image (811 FCHECK-valid candidates tried). The bytes at those
   offsets are uncompressed 16-bit graphics data.

---

## 1. Numeric census — per-number verdicts

Hit counts below are whole-image. For small integers the i16/i32 counts
are dominated by incidental byte-pattern matches inside code, packed
dictionary data, and graphics; they are reported for completeness and
are **not** evidence. Evidence-grade encodings are the ones with exact,
isolated, structured occurrences: i32/f32 of the full values, ASCII, and
UTF-16LE.

### 1.1 Furnace capacity — 107 (out) / 135 (in)

| Encoding | 107 | 107000 | 135 | 135000 |
|---|---|---|---|---|
| i32 BE/LE | 208 / 301 (scattered) | **0 / 0** | 1389 / 68 (scattered) | **0 / 0** |
| f32 BE/LE | **0 / 0** (107.0) | **0 / 0** (107000.0) | — | **0 / 0** (135000.0) |
| ASCII | 1 (see below) | **0** | — | **0** |
| UTF-16LE | **0** | **0** | — | **0** |
| BCD `01 07` | 1297 (incidental) | — | — | — |

[FACT — full-image scans] The only ASCII `"107"` in the image is at
`0x182D0418`, inside a numbered UI text table: `"…106-LOW INDOOR..TEMP
ZONE4 AUX..107-LOW INDOOR..TEMP ZONE5 AUX..108-LOW INDOOR…"` — `107` is
a message index, not a capacity. **Verdict: the furnace's 107K/135K
ratings are not encoded in the image in any tested form.**

### 1.2 ODU size — 60K / 60000 / 5.0 tons / stem 96 / 96000

- `60000` i32 BE: **exactly 1 hit** @`0x1830CD1C`, inside a descriptor
  record sequence whose sibling value slots read `250, 1000, 1000, 500,
  15000, 6` next to code pointers (`0x181FDA64`, `0x1813A954`, …) and a
  source-path string (`"C:\Ing\Int\Software Construction\Wall…"`).
  [Inference — strong] this is a millisecond-timer family
  (250/500/1000/15000/60000 ms), not a BTU rating.
- `60000` i16 BE: 39 hits, several as adjacent pairs in code literal
  pools (e.g. `0x1812F4C8`/`0x1812F4D0`, `0x181892AA`/`0x181892B2`) —
  the classic 60000 ms constant shape. No table structure.
- `60000.0` f32 BE: **exactly 1 hit** @`0x181F7310` (code region, near
  stage E's `sys_ctrl_task` neighbourhood); LE 0. Isolated literal,
  consumer not attributed in this stage. A model-keyed size encoding
  would require a lookup structure; none exists (§4). Not claimed as
  the AC size.
- `60.0` f32 BE: 14 hits in three clusters — code literal pools
  (`0x181B0FA8…0x181B17B8`; `0x181F7C68`, where it sits paired with
  `30.0` @`0x181F7C6C` in a pool that also holds stage-C RAM addresses
  `0xFFF820F8/0xFFF84236`), a stride-24 float-field record array at
  `0x182B3B08…` whose rows repeat `{…, 60.0, 100.0, 1.0, …}` and
  `{…, 30.0, 90.0, 1.0, …}` (generic property limit/default records),
  and `0x1831EA54/0x1831EA64`. None is keyed to equipment.
- `5.0` f32 BE: 69 hits (9 code pools, 60 packed data) — a generic
  float; f64 BE 1 hit @`0x182F6F97` (unaligned, incidental). No
  tonnage structure.
- `96000`: i32 BE 2 hits (one in resources = graphics bytes, one
  unaligned @`0x1841E029`); i32 LE 5 unaligned hits; f32 **0/0**;
  ASCII/UTF-16LE **0**. No credible encoding.
- `"60K"` ASCII: **0**.

**Verdict: neither the 60K rating nor the 5-ton size is encoded as a
value anywhere identifiable; `60`/`60000` occur only as generic
time/limit constants.**

### 1.3 "2-stage" markers

No binary marker exists. The concept lives only in UI/dictionary text
[FACT: string extraction, `out/contexts.txt`]: labels `"AC 2 Stage"`
@`0x182CA414`, `"HP 2 Stage"` @`0x182CA42C`, `"heat stage 1:"` /
`"heat stage 2:"` @`0x182CBC1C/2C`, `"electric heat stage 3:"`, and
installer help text (`"two- stage outdoor units. 0.63 is used for…"`
@`0x182D903C` — the Bristol-multiplier help stage E found). The raw
`'stage'` count is 145, all in the dictionary/text span
`0x182B0000–0x18459E84`. The furnace's 2-stage nature is therefore a
bus-reported/configured property, not a flash constant — consistent
with §1.1.

### 1.4 Capture CFM values (379 / 1166 / 1232 / 1617 / 1710 / 1760)

- **As f32 BE/LE: 0 hits for 379, 1166, 1232, 1617, 1710.** For 1760.0
  a single f32 BE match @`0x18328042` is a cross-boundary artifact:
  the bytes sit inside pointer records (`0x18244512`, `0x182444DC`,
  `0xFFFFFFF8` neighbours) — not a stored float. [FACT: context dump]
- As integers: scattered hits (i16 BE 22–425 per value) across code,
  packed data, and graphics, with no array, no stride structure, and
  no clustering at any single address range. The one structured-looking
  cluster (CFM 1232 as i32 LE, 19 hits at stride 8 in
  `0x1844246E–0x18447F0E`) is the low half of LE words in post-catalog
  dictionary data — on this big-endian target a CFM table would be BE;
  the BE forms show no such cluster.
- **Verdict: the CFM values seen on the bus are computed at runtime**
  (stage E: the CFM computation itself was not isolated; a
  `cfmlimitsvalid` dictionary property exists, §4) **and are not
  stored as constants in any encoding.**

### 1.5 Nominal sizes 18/24/30/36/48/60/61

- **Size-ladder sequences: 0 hits** in every encoding tried (raw byte
  run, i16 BE run, f32 BE run, with and without 61). There is no
  size table.
- Sizes exist in the image only where stage D already found them: as
  the `b5` byte of coil stride-14 records and inside pattern strings
  (`CVPM*2414`, `…4X60`, `…4X61`).
- f32 singles are non-evidence: `18.0` ×4 (one inside a UI list
  descriptor table @`0x1830D3B0` whose records pair
  {8,10,12,15,18} with {24,36,48,60,72} — a settings-list descriptor,
  not model data), `24.0` ×0 BE, `30.0` ×6 (incl. the §1.2 property
  records), `36.0` ×2, `48.0` ×29 — the 48.0 matches cluster in packed
  data at `0x18395E3E–0x183F0593` at irregular, mostly unaligned
  offsets: the byte pattern `42 48 00 00` recurring in dense binary,
  with no record structure. Not a parameter table.

---

## 2. The coil parameter word `0x3FD851EC` — complete census

[FACT — dual: BE/LE byte scans + stage D record dump cross-check]

| Form | Hits | Locations |
|---|---|---|
| BE bytes `3F D8 51 EC` | **2** | `0x182C4B24`, `0x182C4D64` |
| LE bytes `EC 51 D8 3F` | **0** | — |

- `0x182C4D64` = the param field of the author's record: CAT1 stride-8 [70]
  @`0x182C4D60`, pattern `EN(A,D)4X61` (stage D §3.3).
- `0x182C4B24` = the param field of CAT0 stride-8 [72] @`0x182C4B20`,
  pattern **`CNPV*61`** (stage D `out/model_arrays.txt` line 74) — the
  CAT0 sibling of the author's coil, same 61 size class, same param 1.69.
- Pool-reference scan (BE32 word equal to the address, whole image):
  **0 references** to either param address, and 0 to the author's record
  base `0x182C4D60`. The only pointer to the pattern string
  `0x182C59A8` is the record's own `str_ptr` field. This matches stage
  D's architecture: params are reached by index through
  `FUN_180FC3B4`, never by absolute address — so "who else reads that
  word" has a clean answer: **no other copy and no direct reader exist
  in flash; the sole consumption path is the indexed accessor →
  commit (`FUN_18140BEA`/`FUN_18140C80`) → field `0x59F` → the
  unisolated `061E` frame copy (stage D §3.4, §6.4).**

---

## 3. Catalog audit — the blocks at `0x18404EC0` / `0x18405D40`

### 3.1 Corrected geometry: one catalog, 5,417 records

Stage D reported "4-byte table-catalog blocks at
`0x18404EC0–0x1840575C` (551 records `{type ∈ {1,2}, 00, table BE16}`,
ids `0x0194–0x03CF`) and `0x18405D40+` (06xx ids)". Stage K walked the
structure with the validator progressively relaxed (record =
`{byte0 ≠ 0, 00, id BE16}`, ids strictly ascending, one anomalous
record tolerated and logged). [FACT — dual: three independent walks
({1,2}-only, class ≤ 0x10, anomaly-tolerant) agree on one continuous
structure; verbatim dump `out/catalog_full.txt`]

- **Extent: `0x18404928–0x18409DCC`, 5,417 records, 21,668 bytes.**
- **Ids `0x0002–0x2222`, all distinct, strictly ascending** — no gaps
  in the *walk*; ids absent from the sequence (e.g. `0x0303`) have no
  record (§3.3).
- Boundaries: before `0x18404928` sits unrelated data (hash-like
  words, a stray `{0x27,00,0x0430}` in a different structure); after
  `0x18409DCC` a different record family begins
  (`01 00` + ascending u32 offsets `0x389, 0x394, …`).
- Reconciliation with stage D: D's block 1 is exactly the
  class-{1,2} slice of this catalog starting at their seed (stage K's
  {1,2}-walk: 550 records, ids `0x0194–0x03CC`; D's 551st record is the
  class-3 record `0x03CF` at `0x18405758`). D's block 2 seed
  `0x18405D40` lies inside the same catalog (stage K {1,2}-walk from
  it: start `0x18405C44`, 109 records, ids `0x05AC–0x0632`). There are
  not two blocks; there was never a gap — the "gap" bytes are
  records whose class byte is ≥ 3.
- **Pool references to the catalog base `0x18404928`: 0** (BE32 scan)
  — runtime-registered/found by the engine, like every other
  Clarinox structure in this image (stage D §2.1 pattern).
- Exactly **one anomalous record**: @`0x18406D64`, class `0xD2`, id
  `0x101B`, in sequence. Either a class value with flag bits or a
  one-off data quirk; it does not break the id ordering.

### 3.2 The class byte — histogram and failed semantics

Class-byte histogram over 5,417 records: `1: 4271, 2: 690, 3: 132,
4: 114, 5: 53, 6: 37, 7: 17, 8: 20, 9: 10, 10: 9, 11: 22, 12: 6, 13: 5,
14: 1, 15: 10, 16: 8, 17: 1, 19: 1, 32: 1, 36: 4, 48: 2, 50: 2,
0xD2: 1`. ~79 % of ids are class 1.

Semantics **not established**. Two hypotheses tested and rejected:
(i) *field count* — table `0304` has class 2 but 9 binding-directory
records (stage D §2.2); `0604` class 1 vs 5 records; `061F` class 1 vs
5. (ii) *record length of the table* — `0304`'s answer is 16 B,
class 2; `0104`'s is 120 B, class 1. Key tables' classes (from
`out/catalog_full.txt`): `0104:1, 0202:1, 0203:1, 0302:2, 0304:2,
0306:2, 030A:2, 030D:1, 0316:1, 031D:1, 0604:1, 0605:1, 060B:1,
060D:1, 061E:2`. The byte is reported as an uninterpreted per-id
class; the emulator does not need it (the catalog carries no periods,
no destinations, no parameters — stage D's "not a poll schedule"
conclusion stands and now covers the whole structure).

### 3.3 Presence / absence of equipment tables

[FACT: id-set membership in the §3.1 walk] Inside the catalogued id
range, the equipment tables of the protocol map are present —
including the pure command outputs that the binding directory lacks:
`0202, 0203, 0302, 0304, 0306, 030A, 030D, 0316, 031D, 0604, 0605,
060B, 060D, 0610, 061A, 061E` — **except exactly three: `0303`,
`0305`, `0307` are absent**, while their immediate neighbours
(`0302, 0304, 0306`) are present. `0305` is the demand write itself.
[Inference] the catalog is the dictionary's index of *modelled*
tables; the demand path (and the `0303`/`0307` pair) is handled
outside the dictionary model — the same boundary stage D found from
the binding side (§2.2 there: `0305` unbound; here: `0305`
uncatalogued, but `0303` is bound-yet-uncatalogued and `0307` is
bound-yet-uncatalogued, so the two structures' exclusions differ and
are table-specific, not a single rule).

Outside the id range: the catalog ends at `0x2222`, so the SAM tables
(`3B02–3B05`), comfort/vacation/fault tables (`400A, 4012, 4202`) and
the `24xx/34xx/3Exx` families have no catalog records — the catalog's
id space simply does not extend there.

---

## 4. Hunt for further pattern/parameter databases

### 4.1 Pattern-string clusters — none new

[FACT] Extracting all NUL-terminated pattern-like strings
(wildcard-bearing or model-shaped, with digit+letter mix) in
`0x18040000–0x18459E84` yields 329 candidates; they form exactly
**one** cluster of ≥ 5: the known coil string region
`0x182C53D8–0x182C5EF4` (259 strings). The remaining 70 are isolated
singles. No air-handler, zone-board, humidifier, or other accessory
pattern list exists in string form. (Stage D's four arrays are the
only pattern DB; its CAT0/CAT1 split already covers coils *and* fan
coils.)

### 4.2 `{ptr, float}` arrays — none new; nine false positives explained

A fixed-stride-8 detector for `{u32 ptr → printable string, f32 param
∈ [0.005, 500]}` over the main image re-finds the two known coil
stride-8 arrays as its control (73 and 71 records — each stops one
short of the true 74/72 because the terminating `OTHER` record's
param is 0.0, outside the float range — detector behaves as
designed). It also fires on nine runs at `0x181C511C–0x181CC26C`.

[FACT — the pointed-to strings decide it] Those runs are **not**
parameter databases: their "float" fields are the words
`0x3C12E6xx…0x3C12Fxxx` — as integers, Clarinox dictionary property
IDs (float ≈ 0.008937, smoothly incrementing like assigned IDs, not
physical quantities) — and their pointers name dictionary properties:
`defrostbackup`, `coollatchtemp`, `heatlatchtemp`, `mincoolstage`,
`maxcoolstage`, `minheatstage`, `maxheatstage`, `usermincoolstage`,
`usermaxheatstage`, `freezelimit`, `cfgcph`, `cfmlimitsvalid`,
`powercycles`, `lowheatcycles`, `defrostcycles`, `onhours`,
`uvpresent`, `humpresent`, `ventpresent`, `sampresent`, `b36present`,
… (verbatim: `out/catalog4.txt`). These are dictionary
name→ID registration records in code space — the same dictionary
stage E sampled (its flag `0x3C12E6C4` is one such ID). No parameters
are stored in them.

### 4.3 UTF-16LE forms

[FACT] UTF-16LE encodings of `107, 107000, 135000, 96000, 60000,
1.69, G80CTL, HVA9, EN(A,D)4X61, 4X61`: **0 hits each**, whole image.
(The resources filesystem uses UTF-16LE for *names* — §5 — but holds
none of our strings in that form either.)

---

## 5. Resource streams — a discrepancy, reported not resolved

Stage D (§3.1 there) states all 90 zlib streams in the resources
region `0x18810100–0x18D40577` were decompressed and searched. Stage K
could not reproduce any decompression:

- The region opens with a filesystem directory: entry count
  `02 00 00 00`, hash-like u32s, UTF-16LE path names `"\images"`,
  `"\fonts"` [FACT: hex dump, `out/contexts.txt`]. Block profile
  (256 KiB blocks): 0x00 fraction 0.10–0.40, 0xFF fraction 0.03–0.29 —
  low-entropy, graphics/font-like content, not compressed-stream
  density.
- Offsets whose first two bytes look like a zlib header
  (`78 9C / 78 01 / 78 DA / 78 5E`): **exactly 90** in the region —
  the same count stage D reported. Whole image: 811 FCHECK-valid
  `0x78` offsets.
- Decompression attempts (zlib wrapper and raw deflate, at all 90
  region candidates and all 811 image-wide candidates, accepting any
  output ≥ 16 B reaching stream end): **0 successes.** The bytes at
  the candidate offsets are uncompressed 16-bit graphics data
  (e.g. @`0x188F7952`: `78 9C 9D 00 79 9D 97 00 74 97 9B 00 …` —
  smoothly varying BE16 samples).

[Inference] stage D's "90 streams" was most likely the candidate-
header count, with the decompression step either applied to a
different container or not saved — no saved script in
`firmware-re/` mentions zlib at all. **Consequence for the census:**
none for plain encodings — every byte of the region was covered by
the whole-image ASCII/UTF-16LE/binary scans above, and the region's
content is (per its profile) uncompressed resources. Residual caveat:
if some resource file used a non-deflate codec, its *content* is not
covered by a stream census; no evidence of such a codec was found.

---

## 6. Verdict — the author's hypothesis, answered

**No. Beyond the coil database, there are no model→parameter
encodings in this image** — not for the furnace, not for the outdoor
unit, not for "the board itself" — in any form tested: model strings
(stage D), pattern databases (§4), numeric constants in
BE/LE int16/int32, float32/64, BCD, ASCII, or UTF-16LE (§1), size
ladders (§1.5), or catalogued parameters (§3 — the catalog holds ids
and a class byte only, no values).

The asymmetry has a clean architectural reading, now supported from
three independent directions (stage D strings, stage D binding
directory, stage K numerics): **the coil is the only component that
cannot speak for itself.** The furnace and ODU are bus devices that
report their identity and configuration (`0104`, `0316`, …) and
receive computed commands; the thermostat's firmware therefore needs
no stored parameters for them. The passive coil can report nothing,
so — and only so — the firmware carries its pattern→parameter table,
and the chosen parameter leaves in `061E`. For the emulator this
means: replay/derive furnace and ODU behaviour from the bus
(protocol map + stages D/E), and take exactly one equipment
parameter from firmware — the coil's, selected by the commissioned
pattern (the author: `EN(A,D)4X61` → 1.69).

## 7. Explicit not-found list

- `107000`, `135000`, `96000` as i32 BE/LE, f32 BE/LE, ASCII,
  UTF-16LE: **0** everywhere.
- `107.0`, `107000.0`, `135000.0`, `96000.0` as f32: **0**.
- CFM 379/1166/1232/1617/1710 as f32: **0**; 1760.0: one
  cross-boundary artifact, not a stored float.
- Size ladders (18/24/30/36/48/60[/61]) as bytes, i16, f32 runs: **0**.
- `"60K"` ASCII; `"107"` ASCII except the UI message index; all
  UTF-16LE needles of §4.3: **0**.
- The `0x3FD851EC` word in LE form, in literal pools, or anywhere
  outside the two coil-DB param fields: **0**.
- Pattern-string clusters other than the coil strings: **0**.
  `{ptr, float}` arrays other than the coil arrays: **0** (nine
  dictionary-registration false positives, §4.2).
- Pool references (BE32) to the catalog base `0x18404928`, to
  the author's coil record `0x182C4D60`, or to either `1.69` param word:
  **0**.
- Decompressible zlib/deflate streams anywhere in the image: **0**
  (§5).
- Catalog records for `0303`, `0305`, `0307` (in-range absences) and
  for any id > `0x2222`: **0**.

## 8. Not isolated / not established in this stage

1. Semantics of the catalog class byte (§3.2) — two hypotheses
   tested and rejected; a code-side consumer was not traced
   (would need a Ghidra pass from the catalog's runtime users,
   who are themselves unregistered-by-pointer, §3.1).
2. The consumer of the single `60000.0` f32 literal @`0x181F7310`
   and of the `60.0/30.0` pool pair @`0x181F7C68/6C` — unattributed
   code constants; neither sits in any table.
3. Whether any resource file uses a non-deflate codec (§5 caveat).
4. The physical unit of the coil param (stage D §6.5) — unchanged:
   the census adds that the same value 1.69 serves both 61-class
   coils (`CNPV*61`, `EN(A,D)4X61`), i.e. it is a size-class
   parameter, not a per-model unique.

## Appendix — stage K artifacts (`firmware-re/stageK/`)

- `census.py` + `out/census_full.txt` — the numeric census (all
  counts, region histograms, hit lists) and the stream census.
- `contexts.py` + `out/contexts.txt` — context dumps: ASCII-`107`
  site, the `60000` descriptor family @`0x1830CD1C`, the
  `0x1830D3B0` list descriptors, the stride-24 float records
  @`0x182B3B08`, the `0x181F7C68` pool, the 1760.0 artifact, all
  `stage`-bearing strings, resources header/signatures.
- `streams.py` + `out/streams_diag.txt` — resources block profile
  and decompression diagnostics (§5).
- `catalog.py`, `catalog2.py`, `catalog2b.py`, `catalog3.py` +
  `out/catalog_part.txt`, `out/catalog2.txt`, `out/catalog3.txt`,
  `out/catalog4.txt`, `out/catalog_full.txt` — the catalog walks
  (v1 {1,2}-slices, v2, v3 final: 5,417 records verbatim), the
  field-count test, and the stride-8 run dumps.
- `dbhunt.py` + `out/dbhunt.txt` — string clusters, `{ptr, float}`
  detector (v1, superseded by the fixed-stride version in
  `catalog2b.py`), UTF-16LE needles.
- `closing.py` + `out/closing.txt` — f32 big-BTU needles, the
  whole-image zlib attempt, catalog class bytes for key tables.
- Stage B/C/D/E artifacts, the source image, and `firmware/` were
  not modified.
