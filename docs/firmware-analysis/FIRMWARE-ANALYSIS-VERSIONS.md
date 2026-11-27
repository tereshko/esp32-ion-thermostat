# FIRMWARE-ANALYSIS-VERSIONS — Cross-version diff of the official BINF images

Date: 2026-11-26. Scope: every firmware version Carrier/ICP publicly distributes
for the communicating wall controls (Ion SYST0101CW / Infinity / Evolution,
**Series B**, firmware family BINF*, part CESR131626), diffed against each
other and against our unit's v4.79. Method: official public distribution
channel only; every image decoded with the record framing verified in
stage B (binary Intel-HEX-style records, checksum-validated, **0 bad
checksums in all 17 images**). Reference points for v4.79 are stages D/E/K
and the stage-H Clarinox fingerprint. Work dir: `firmware-re/versions/`
(downloads, extract, decoded, scripts, notes).

## 0. Headlines

1. **16 of the 25 referenced Series B versions were obtained** from the
   official ICP EULA channel (2.40–4.79, with gaps). 8 referenced versions
   are **not downloadable from any official public channel today**
   (1.30/1.31/1.32, Series B 2.00, 4.22, 4.38, 4.62, 4.64, 4.72) — live
   404 on all brand namings, no Wayback captures, web search negative.
2. **The official ICP BINF0479.hex is byte-identical to our unit's image**
   [FACT]: MD5 `e31903228bf39a4bc9c0a2a74192359e`, SHA-256
   `2d1a9ea3c723e245fbabe6089118f750adfc6dd249c9b2e76a79d3f8a4c90c04`,
   10,188,916 bytes — the file the author already had *is* the official image.
   Cross-brand identity also verified for 3.01: Carrier zip == Bryant zip
   image, MD5 `5e97e64db336671d389d659d4474c3ee` (zips differ only in
   EULA/notes PDFs). Per-version byte identity across brands is therefore
   confirmed wherever two brandings exist; only one branding was
   downloadable for most versions.
3. **The stage-E decision core's signature constants never changed in
   2019–2025.** The float pair {375.0, 400.0} (FUN_18051cec's literal pool
   in 4.79) exists exactly once in **every** BINF version 2.40→4.79, always
   as an adjacent pair; the 0.01 literal count is 5 in every version;
   0.63 (Bristol low-airflow multiplier family) count is 3 in every
   version. Whatever Carrier changed release-to-release, it was not these
   constants. [FACT at literal-census level; per-function attribution
   outside 4.79 is inference by address neighbourhood ~0x18051xxx.]
4. **the author's coil parameter never changed:** EN(A,D)4X61 → **1.69** in all
   16 BINF versions. The coil DB only grows/shrinks by whole model
   families (4.31 +EVD/ESD, 4.47 +CAP, 4.56 +CAA, 4.66 −CAA); **no
   pattern's parameter value changed in any consecutive pair, ever.**
5. **The two documented control-strategy changes leave no trace in any
   table, dictionary or constant this diff can measure** — the 4.05
   "airflow limited stage downs" fix and the 4.79 "removed compressor
   demand response from CFM calculation" are code-logic changes. What
   *did* change at data level in 4.79: the whole Sparkplug
   `system/utilityEvent/demand*` property group (present ≤4.74) is gone,
   replaced by a lone `totalDemandReductionPercent` — the demand-response
   subsystem was reworked in 4.79, consistent with (not proof of) the
   CFM claim.
6. **Layout generation break at 4.31**: single-span image (2.40–4.05)
   becomes main span + separate ROM-FS bank at 0x18810100 (4.31–4.79);
   the Sparkplug dictionary appears; the binding directory jumps
   235→306 records; the embedded equipment-CESR string list disappears
   (manifest era begins).
7. **Clarinox suite generations**: WiFi/SoftFrame records read
   **2.1.0 build 1686** (2.40–3.62) → **9.0.0 build 16695** with WiFi
   **9.0.0.p502 build 1874** (3.94) → WiFi **9.0.0.p3 build 2097**
   (4.05–4.79, frozen). **4.74 is anomalous**: the string-form version
   records are absent entirely (a `%u.%u.%u.p%u` format string and a BSP
   database manager appear instead) — its Clarinox versions are not
   determinable from image strings.
8. **Trap avoided/documented**: the `V0200` slot on the same channel is
   **not** Series B 2.00 — it serves the **Series C** control
   (SYST0201CW) v2.00 package (CINF0200.BEX, CESR131755, load base
   0x60100000, different platform; its own release notes state Series
   A/B incompatibility). It was downloaded and inventoried as a sibling,
   and excluded from all Series B diffs.

## 1. Channels and method

- ICP distributes each version behind an EULA page on
  `cacbdpapps.net/marketing/eula/`: `ICP_Ion_V{code}_EULA.html` →
  `ICP_Ion_eula_dl_V{code}.html` → `Version_{code}_ICP.zip`, each zip
  containing `TSTAT/BINF{code}.hex` + that version's own release-notes
  PDF + EULA PDF. The 4.79 package the author already owned
  (`Version_0479_Carrier.zip`, Carrier branding, same image) matches
  this layout.
- Version codes probed for EULA page, dl page and zip under all three
  brand suffixes (`_ICP`, `_Carrier`, `_Bryant`): all 24 versions from
  the v4.79 release-notes Revision History + 4.62 (referenced by a stale
  link in the 4.79 notes' installation section). Alternate page/zip
  namings for the missing ones also probed (404). Wayback CDX queries
  for the missing versions' pages/zips returned **no captures**.
  `dev.ioncomfort.com/Ion/Downloads` links only to the current EULA.
- Decode: record framing `':' cnt addr16 type payload checksum`
  (types 0/1/4/5), regions merged per load address. All BINF images:
  base **0x18040000**, entry point 0x180405E0 (2.40) → 0x180405F0
  (3.00–4.05) → 0x180405F4 (4.31) → 0x180405FC (4.47–4.79); header record
  payload carries `!!START_OF_CODE!CESR131626-{version}` [FACT, read
  from the files]. Same container, same CESR family, same base ⇒ same
  SH-2A platform as stage A/B established for 4.79 [inference, strong].
- Structural probes per version (scripts/fwprobe.py): CESR strings,
  Clarinox version records (stage-H layout), Sparkplug dictionary
  path strings, coil pattern→param pairs (stage-D record format:
  u32 BE string pointer + f32 BE param), unified catalog (stage-K
  record format), binding directory (stage-D 8-byte records), decision
  constant census (BE f32 literals). Pairwise byte diffs only where
  layout is shared.

## 2. Version inventory

Release dates from the Revision History in the official v4.79 release
notes (2025-11-12). "Obtained" = image downloaded from the official
channel in this pass and hash-inventoried (notes/inventory.json).

| Version | Date | Status | Image MD5 / size |
|---|---|---|---|
| 1.30 | Nov 2017 | **not obtained** — no package on channel | — |
| 1.31 | Dec 2017 | **not obtained** | — |
| 1.32 | Mar 2018 | **not obtained** (its notes mention the coil factor: CHPH**61 → 2.02 bug) | — |
| 2.00 (Series B) | Aug 2018 | **not obtained** — V0200 slot serves Series C instead | — |
| 2.00 (Series C, SYST0201CW) | Jul 2025 repackage | obtained as sibling: CINF0200.BEX, CESR131755 | `7eb77968…` / 8,896,064 |
| 2.40 | Jan 2020 | obtained (ICP) | `ef163d0f…` / 6,756,994 |
| 3.00 | Apr 2020 | obtained (ICP) | `a09cec7e…` / 6,464,402 |
| 3.01 | Jun 2020 | obtained (**Carrier + Bryant** zips; ICP zip 404) | `5e97e64d…` / 6,464,498 |
| 3.40 | Jun 2020 | obtained (ICP) | `b3e2a973…` / 7,004,986 |
| 3.60 | Sep 2020 | obtained (ICP) | `5eb15dae…` / 7,010,102 |
| 3.61 | Oct 2020 | obtained (ICP) | `1cb4aabd…` / 7,010,102 |
| 3.62 | Dec 2020 | obtained (ICP) | `c42d34db…` / 7,011,154 |
| 3.94 | Jul 2021 | obtained (ICP) | `44fc32ba…` / 6,949,334 |
| 4.05 | Sep 2021 | obtained (ICP) | `ddd4fa00…` / 6,962,000 |
| 4.22 | Aug 2022 | **not obtained** — 404 all brandings | — |
| 4.31 | Nov 2022 | obtained (ICP) | `e90f7732…` / 8,539,916 |
| 4.38 | Apr 2023 | **not obtained** — 404 all brandings | — |
| 4.47 | Aug 2023 | obtained (ICP) | `f0497d7d…` / 10,703,350 |
| 4.56 | Apr 2024 | obtained (ICP) | `34a44d21…` / 10,055,898 |
| 4.62 | (not in history; linked from 4.79 notes) | **not obtained** — even the notes' own link target is 404 today | — |
| 4.64 | Aug 2024 | **not obtained** — 404 all brandings | — |
| 4.66 | Oct 2024 | obtained (ICP) | `d95a0a67…` / 10,117,092 |
| 4.70 | Jan 2025 | obtained (ICP) | `07fecc59…` / 10,135,826 |
| 4.72 | Mar 2025 | **not obtained** — 404 all brandings | — |
| 4.74 | May 2025 | obtained (ICP) | `bc1778a9…` / 10,263,542 |
| 4.79 | Nov 2025 | obtained (ICP) — **byte-identical to our unit's file** | `e3190322…` / 10,188,916 |

Why the gaps [inference]: the channel keeps a *subset* of versions
online — plausibly the ones ICP still sanctions for field
up/downgrade (note 3.61, the known rollback target for the fault-126
issue, is present; several short-lived releases — 4.22, 4.38, 4.64,
4.72 — are absent). No statement of this policy was found on the pages
themselves.

## 3. Layout generations

[FACT, from decoded region maps]

- **Gen 1 (2.40–4.05)**: one contiguous span 0x18040000–~0x186Axxxx
  (~6.2–6.7 MB payload), trailer records at 0x18F3FEF8/0x18F3FF00. No
  second bank. The ROM FS lives in the span's tail.
- **Gen 2 (4.31–4.79)**: main span shrinks to 0x18040000–~0x1845xxxx
  (~4.2 MB); a new bank at **0x18810100** (4.19 MB in 4.31 → 5.98 MB in
  4.47 → ~5.4 MB in 4.56–4.79) holds the ROM FS — its header is a
  directory listing (`\images`, `\fonts`, UTF-16LE) [FACT, read from
  region bytes]; small segments at 0x18800000 (2,904 B) and the usual
  trailers. 4.31/4.47 additionally carry a 248-byte segment addressed
  at dictionary space 0x3C125DE4/0x3C1297E4 (mostly zeros with a small
  repeating pattern — a default-data segment [inference]).
- Total payload: 6.45 MB (2.40) → 6.65 MB (4.05) → 8.16 MB (4.31) →
  10.22 MB (4.47, the largest) → 9.73 MB (4.79).

## 4. Version × aspect matrix

Coil = distinct pattern→param pairs recovered by the stage-D-format
scan (4.79: 144 names over stage D's 263 records — arrays share
patterns). the author = param of EN(A,D)4X61. BD = binding-directory
records (gen-1 counts from a generic run scan, ±few; 4.31+ anchored by
the directory's first-record signature; 4.79 walk gives 386 vs stage
D's 385 — walk-termination off-by-one, stage D's own two walks also
differed). Catalog = stage-K-format parse (exact for 4.79 = stage K's
5,417; other gen-2 counts from the same unconstrained walk, see §6).
Dict = lowercase path identifiers in the dictionary block (windowed;
gen-2 only — the block does not exist in gen 1). Clarinox = WiFi
record (SoftFrame record in parentheses where isolated).

| Ver | Clarinox WiFi (SoftFrame) | Dict paths | Coil pairs | the author | BD recs | Catalog | {375,400} pair | Layout |
|---|---|---|---|---|---|---|---|---|
| 2.40 | 2.1.0 b1686 | — (no block) | 32 | 1.69 | ~205 | present¹ | yes | gen 1 |
| 3.00 | 2.1.0 b1686 | — | 32 | 1.69 | ~233 | present¹ | yes | gen 1 |
| 3.01 | 2.1.0 b1686 | — | 32 | 1.69 | ~233 | present¹ | yes | gen 1 |
| 3.40 | 2.1.0 b1686 | — | 32 | 1.69 | ~234 | present¹ | yes | gen 1 |
| 3.60 | 2.1.0 b1686 | — | 32 | 1.69 | ~234 | present¹ | yes | gen 1 |
| 3.61 | 2.1.0 b1686 | — | 32 | 1.69 | ~234 | present¹ | yes | gen 1 |
| 3.62 | 2.1.0 b1686 | — | 32 | 1.69 | ~234 | present¹ | yes | gen 1 |
| 3.94 | 9.0.0.p502 b1874 (9.0.0 b16695) | — | 32 | 1.69 | ~234 | present¹ | yes | gen 1 |
| 4.05 | 9.0.0.p3 b2097 (9.0.0 b16695) | — | 32 | 1.69 | ~235 | present¹ | yes | gen 1 |
| 4.31 | 9.0.0.p3 b2097 (9.0.0 b16695) | 82 | 71 | 1.69 | 306 | present¹ | yes | gen 2 |
| 4.47 | 9.0.0.p3 b2097 (9.0.0 b16695) | 78 | 144 | 1.69 | 345 | 5,577 | yes | gen 2 |
| 4.56 | 9.0.0.p3 b2097 (9.0.0 b16695) | 79 | 256 | 1.69 | 346 | 5,466 | yes | gen 2 |
| 4.66 | 9.0.0.p3 b2097 (9.0.0 b16695) | 78 | 144 | 1.69 | 382 | 5,474 | yes | gen 2 |
| 4.70 | 9.0.0.p3 b2097 (9.0.0 b16695) | 78 | 144 | 1.69 | 386 | 5,466 | yes | gen 2 |
| 4.74 | **records absent** (see §5) | 79 | 144 | 1.69 | 386 | 5,412 | yes | gen 2 |
| 4.79 | 9.0.0.p3 b2097 (9.0.0 b16695) | 79 | 144 | 1.69 | 386 | 5,417 | yes | gen 2 |

¹ Gen-1/4.31 catalog: the stage-K signature (head records
{2,2,2,2}→ids 2,4,6,8) does not match, but a generic scan finds a long
strictly-ascending run of the same record shape (2.40: ≥5,148 records,
max id ≥0x18D5; 3.61: ≥5,324, ≥0x1991; 3.94/4.05: ≥5,341, ≥0x19BC;
4.31: ≥5,607, ≥0x1ADC) — the catalog exists with a different head and a
smaller id space that grows toward 4.79's 0x2222 [FACT for presence;
exact extents not established for gen 1].

Series C 2.00 (for contrast): CESR131755, base 0x60100000, entry
0x60100331, payload 8,662,920 B in one span; contains `spBv1.0` and
`idu/maxcfm`-style paths and an EN(A,D)4X61 *string*, but no
stage-D-format (ptr,f32) coil pairs and no Clarinox strings were
recovered — a different platform generation, not diffed further.

## 5. Clarinox evolution

[FACT, from the {version, build} string records; 4.79 values cross-check
exactly against stage H: Blue 9.0.0 b11452 @0x1831EAFC, SoftFrame 9.0.0
b16695 @0x1831FF40, WiFi 9.0.0.p3 b2097 @0x18320020.]

- 2.40–3.62: one record family reading **2.1.0 / build 1686** (found in
  the WiFi record position, immediately before the ClxWlan* API name
  table, e.g. 2.40 @0x185B8B50). The WiFi chip is TI WL18XX in both
  eras (WL18XX_* config keys present in 2.40 and 4.79).
- 3.94: suite jumps to **9.0.0**: SoftFrame 9.0.0 b16695
  (@0x185F2C0C), WiFi **9.0.0.p502 b1874** (@0x185F2CEC).
- 4.05: WiFi moves to **9.0.0.p3 b2097**; SoftFrame unchanged. Both
  records then stay frozen through 4.31/4.47/4.56/4.66/4.70/4.79.
- **4.74 anomaly** [FACT]: the strings `16695`, `2097`, `11452`,
  `9.0.0.p3` do not occur anywhere in the image; `9.0.0` occurs once
  inside non-string data. Around `SoftFrame.cfg` (0x1833A358) there
  are instead BSP database-manager strings
  (`clxBspSoftFrameDatabaseManager->openDatabase`), a `$Rev: 19618 $`
  tag and a `%u.%u.%u.p%u` version *format* string @0x1833A4F4 —
  evidence that 4.74 formats component versions numerically at runtime
  rather than storing them as strings [inference]. Whether 4.74's
  suite version differs from 9.0.0/p3 cannot be determined from the
  image. 4.79 returns to the string-record form with the same values
  as 4.70 — the 4.74 form looks like a one-release experiment.
- The Clarinox Blue record was isolated only for 4.79 (stage H); for
  other versions the Blue config-key tables are present but the
  {version, build} pair was not separately recovered — not claimed.

This also dates the 4.72 release-note line "Include DHCP fixes from
Clarinox": the Clarinox *DHCP-relevant* stack in 4.72's era is the
9.0.0/p3 build already present since 4.05 (4.72 itself not obtained;
the fixes may be in Carrier-side integration code, not the Clarinox
build number).

## 6. Catalog and binding directory

**Binding directory** [FACT, record/table sets per version]:
205 records / 62 tables (2.40) → 233/76 (3.00: adds tables 0605, 0613,
0615, 0616, 0618, the 0702–0708 zoning family, 0317, 0322, 0323) →
234 (3.40: +0715) → 235 (4.05: +041F, the thermostat→smart-sensor
table) → 306/90 (4.31: +0104 at the head — the signature start stage D
found — plus the 2403/2406/2415–241C families and 0307) → 345/96
(4.47: +0424/0428/0429/0434/0438, +0716) → 346 (4.56) → 382/99
(4.66: +0326/0327/0612) → 386/99 (4.70) → **frozen 4.70→4.74→4.79**
(same count, same table set). The data plane the thermostat polls has
not changed since Jan 2025.

**Unified catalog** (gen-2, same walk that reproduces stage K's 4.79
extent exactly): 5,577 (4.47) → 5,466 (4.56) → 5,474 (4.66) → 5,466
(4.70) → 5,412 (4.74) → 5,417 (4.79). Object-id presence in the low
range [FACT at parse level]: ids **0x0303, 0x0305, 0x0307 exist
(class 1) in the 4.47–4.74 catalogs and are absent in 4.79** (4.79
absence independently verified by stage K's tiling); id 0x0304's
class changes 1 → 2 in 4.79. Id 0x060D parses as present in
4.56/4.66/4.70/4.79 but absent in 4.47/4.74 — this one is
parse-sensitive and is **not** claimed as a real difference.
Interpretation stays as stage K framed it: catalog ids are
dictionary-space objects whose numbering coincides with bus table
numbers; the 4.79 removal of the 0303/0305/0307 objects is a real
data-model change between 4.74 and 4.79, but it does not by itself
prove how the 0305 demand frame is constructed in either version.

## 7. Dictionary (Sparkplug) evolution

The path-identifier dictionary block **does not exist in gen 1**
(2.40–4.05: no `spBv1.0` string anywhere; the handful of path-like
strings are UI/config text). It appears at **4.31** with the gen-2
restructure (82 windowed path identifiers; stage H counted 902
identifier strings of all shapes in 4.79's block — the windowed
lowercase-path subset used here is 79, a consistent relative measure,
not the same census).

Consecutive diffs after 4.31 are small and clean [FACT]:
- 4.31→4.47: −`utility_event/message`, `utility_event/prop/process_income_package`,
  `utility_event/status`, `utility_event/type` (the underscore
  namespace starts retiring);
- 4.47→4.56: +`system/timesync`;
- 4.56→4.66: −`utility_event/id` (underscore namespace fully gone);
- 4.66→4.70: no path changes (but the camelCase
  `system/utilityEvent/demand*` group is present in both);
- 4.70→4.74: +`system/ehub` (SmartSave Energy Hub, matches the notes);
- 4.74→4.79: no windowed-path changes — **but** the camelCase group
  `system/utilityEvent/demandClAbs`, `demandHtAbs`, `demandOffset`,
  `demandResp` (present in 4.70 and 4.74) is **entirely absent from
  4.79's strings**, the "Demand Response Settings" UI strings are
  gone, and a new single property `totalDemandReductionPercent`
  appears. The demand-response data model was replaced in 4.79
  [FACT at string level].

**CFM vocabulary** [FACT]: `calcMinCFM`, `cfmlimitsvalid`,
`absmaxcfm`, `absmincfm`, `vcapcfmfloor`, `vcapcfmceiling`,
`vcapcfmuplimit`, `blowerActualCFM`, `blowerCoolingCFM`,
`blowerHeatingCFM`, `systemCFM`, `iducfm` are present in **every**
version 2.40→4.79 (and in the Series C BEX). Changes are marginal:
`CFMTARGET` present 3.00–4.56, gone from 4.66; `CFMVAPOR` appears in
4.66/4.70 only; `idu/maxcfm`/`idu/mincfm` path forms are added at
4.31 alongside the bare names (namespace migration, both kept).
**No CFM property was added or removed between 4.74 and 4.79.**

## 8. Coil DB evolution

[FACT, stage-D-format scan; a "pair" is a distinct pattern string with
at least one (pointer, f32) record.]

- **2.40→4.05: zero changes** — the same 32 pairs in all nine versions.
- **4.31: +39 pairs, none removed, none re-valued** — new EVD**/ESD**
  families (the modulating-furnace-era coils; params reuse the same
  ladder 0.10/0.12/0.21/0.23/0.27/0.29…).
- **4.47: +80, −7** — the CAP** family arrives (params now include
  non-round values: CAP**3717 = 0.7716, CAP**3721 = 0.9258 — computed-
  looking numbers, unlike the round ladder); 7 EVD** entries dropped.
- **4.56: +112** — a whole parallel CAA** family whose params are the
  CAP** values rounded (0.7716→0.77, 0.9258→0.93; CAP**60 1.93 ==
  CAA**6024 1.93). [Inference: the same coils under the uncased-A-coil
  naming for the R-454B line 4.56 introduced.]
- **4.66: −112** — the entire CAA** family is removed again; it exists
  only in 4.56.
- **4.66→4.70→4.74→4.79: zero changes.**
- **No parameter value of any surviving pattern ever changed** in any
  consecutive pair (and the author's EN(A,D)4X61 = 1.69 in all 16). The
  1.32 release-note anecdote (CHPH**61 factor wrongly 0 instead of
  2.02) predates every obtainable image; in all obtainable versions
  the 61-class values are already the stage-D ones (ENH4X61 = 2.02
  included).

## 9. Release-notes claims vs binary evidence

- **4.05 "airflow strategy"** (notes: Proteus FER continuous-fan min
  CFM; limit-33 excess-airflow redistribution; "addressed airflow
  limited stage downs … with older 2-stage ODUs and v3.94"): between
  3.94 and 4.05 the coil DB is identical, the CFM vocabulary is
  identical, the decision-constant census is identical (375×1 pair,
  0.01×5, 0.63×3, 1.25×14, 0.25×7→6), the binding directory gains
  exactly one table (041F, unrelated — smart sensors). **No
  table/constant-level change: the fix is in code logic**, not
  measurable by this diff. The hvactechgroup field report (4.05
  lowered CFM minimums, fault 126 on 59MN7, rollback to 3.61 cured
  it) is likewise not contradicted — minimums are computed, and the
  computed values are not stored as literals we can isolate here.
- **4.70 "ODU staging control enhancements"**: 4.66→4.70 shows no
  dictionary, coil, catalog-count or constant-census signature
  (1.25 count 13→14 is within noise of a census this coarse). Code-
  level change, not measurable here.
- **4.79 "Removed compressor demand response from CFM calculation to
  prevent fan surges"**: supported at data-model level (the whole
  `utilityEvent/demand*` group removed in 4.79, §7) and *not*
  contradicted anywhere: CFM vocabulary and constants unchanged,
  binding directory frozen, catalog loses the 0303/0305/0307 objects
  (§6). A code-level proof (diffing the CFM computation itself)
  would require per-version Ghidra work on the relevant functions —
  explicitly **not done** in this pass.
- **3.61 (MTU fix) is the one true hotfix**: 3.60 vs 3.61 images have
  identical size and payload; **only 568 bytes differ (0.004%)** in 24
  small ranges (largest clusters ~0x18053600 and ~0x181BF000–
  0x181C4700) [FACT]. Every other consecutive pair — including 3.01,
  whose notes say only "bug fixes" — is a full rebuild (26.9% of
  bytes differ 3.00→3.01; 26.5% 3.61→3.62): **byte-level diffing
  across versions is meaningless except for patch pairs**; structural
  diffing (this report) is the meaningful level.
- **3.94→4.05 Clarinox WiFi p502→p3** coincides with the 4.05 notes'
  "Compliance to 802.11n connectivity standard" — the connectivity
  claim has a concrete binary correlate (new WiFi stack build).

## 10. What the diffs teach us (algorithm evolution)

1. **The control core is frozen; the surface evolves.** Across 16
   releases and 6 years, everything stage E isolated as the decision
   core leaves the same literal fingerprint ({375, 400} pair, 0.01×5,
   0.63×3), the coil parameters never move, and the CFM vocabulary
   never changes. Releases change connectivity stacks, equipment
   *coverage* (coil families, binding tables), the cloud/data model
   (Sparkplug dictionary, demand-response rework) and GUI — not the
   demand/staging arithmetic we recovered. For the emulator spec this
   is good news: the 4.79 constants are not a moving target, and
   4.79's behaviour should match field reports from much older
   versions.
2. **Equipment coverage grows by accretion, in families, at platform
   breaks** — 4.31 (gen-2 restructure: EVD/ESD coils, 24xx binding
   tables, Sparkplug) and 4.47 (CAP coils, 042x/043x tables) are the
   two expansion releases; 4.56's CAA family shows Carrier also
   *retracts* a family within one release cycle when the product line
   changes its mind.
3. **The demand-response subsystem is the most volatile control-
   adjacent code**: underscore `utility_event/*` (≤4.66) → camelCase
   `system/utilityEvent/demand*` (4.70–4.74) → removed and replaced
   by `totalDemandReductionPercent` + OpenADR/SmartSave rework
   (4.79). It is also the subsystem named in the 4.79 CFM claim —
   the CFM calculation evidently *consumed* demand-response state,
   and 4.79 cut that coupling.
4. **The poll data plane stabilised in Jan 2025** (binding directory
   frozen 4.70→4.79) — captures taken on 4.79 describe the same
   binding surface as 4.70/4.74, which widens the capture corpus the
   emulator spec can safely lean on.

## 11. Not obtained — explicit list

Referenced but **not downloadable** from official public channels as
of 2026-11-26 (live 404 for EULA page, dl page and zip under ICP /
Carrier / Bryant namings; alternate namings 404; Wayback CDX: no
captures; web search: no mirrors):

- **1.30, 1.31, 1.32** (2017–2018) — predate the channel's retained
  set entirely.
- **Series B 2.00** (Aug 2018) — the V0200 URLs serve the Series C
  SYST0201CW package instead (see §0.8).
- **4.22** (Aug 2022), **4.38** (Apr 2023), **4.64** (Aug 2024),
  **4.72** (Mar 2025) — released versions the channel no longer
  serves.
- **4.62** — referenced only by a stale link inside the 4.79 release
  notes (and absent from the Revision History); its own EULA URL is
  404 today.

Consequence: the 3.94→4.05 airflow question cannot be bracketed any
tighter (both sides obtained — good), but the 4.64/4.72 Clarinox-DHCP
era and the 4.22/4.38 dictionary pre-history (gen-2 began somewhere
between 4.05 and 4.31; 4.22/4.38 would pin the transition) remain
unexaminable. If the author ever meets a dealer laptop with the HVACpartners
cache, 4.22 and 4.38 are the two images worth asking for.

## 12. Artifacts (firmware-re/versions/)

- `downloads/` — 19 zips as downloaded (16 ICP + 0301 Carrier +
  0301 Bryant + the local-equivalent 0479 ICP), plus the v4.79 notes
  PDF fetched from preprod.ioncomfort.com.
- `extract/<ver>/` — unzipped packages (image + per-version release
  notes + EULA PDFs).
- `decoded/<ver>/` — per-version decoded regions, region maps
  (regions.txt), meta.json (entry/records/checksums), probe.json
  (all structural probe results used above).
- `scripts/` — fwdecode.py (framing decoder), fwprobe.py (structural
  probes), fwdiff.py / fwdiff2.py (set + pair diffs), probe_eula.sh.
- `notes/` — inventory.json (hashes/sizes/payload per image),
  dict_sets.json (windowed dictionary sets), v0479_notes.txt,
  EULA page captures.
