# FIRMWARE-ANALYSIS-I — Stage I: parameterization of control BY THE FURNACE (0x44)

Question (the author's premise, proven for the coil in stage D): the thermostat tailors its
algorithms to the installed equipment. Stage D proved the indoor coil's parameter is
committed to the field store and sent to the ODU in 061E. Is the **furnace** likewise
parameterizing control — and if so, through which values? Stage D proved there is **no
furnace model-string database** in the image, so any furnace parameterization must come
from values the furnace itself reports over the bus.

Method: (1) re-walked the stage-D binding directory and extracted every record for
tables read from 0x44; (2) resolved the field-store accessor pair and extracted the
constant first argument of **every** getter/setter call in all 721+ decompiled functions
(stages C/D/E/I corpus, `stageI/argextract.py`); (3) cross-checked the full Ghidra
caller census of the accessor pair (899 getter-caller functions); (4) decompiled the
stage-E producer suspects (FUN_180c15d2 + 6 siblings) and every control-adjacent getter
caller; (5) constant hunts for the furnace's ratings (107K BTU/H, CFM range) in all
encodings; (6) pool-cell census (raw BE32 occurrence scan) for the field-store base and
for the control RAM tables. All stage-I work products in `firmware-re/stageI/`.

---

## 1. Verdict (first)

**[FACT] No statically visible path carries a furnace-reported value into a control
decision.** The complete parameterization picture for the furnace is three-layered:

1. **Data plane exists and is fully bound.** Every furnace table the thermostat polls
   (0316 IDU config, 0306/0307 status, 030A, table-04 VARSPEED rows, shared
   0302/0304/030D/030E/0310/0311, 0104 identity) has binding-directory records mapping
   it into a field store (§2). The thermostat *receives and stores* the furnace's
   self-reported configuration — including the exact bytes the task singled out:
   0316 heat stage [0], CFM [4..5], static pressure [7..8] land at store offsets
   0x1BC–0x1C3.
2. **No consumer in the control lineage reads them.** The control core and all its
   producer properties work exclusively on the RAM block 0xFFF8C8xx–0xFFF8CDxx and
   never call the field-store accessor at all (§4, §5). Across the entire decompiled
   corpus there is **no read of the 0316 offsets (0x1BC–0x1C3), the 0306/0307 offsets
   (0xF2–0xF9), or the table-04 offsets (0x262–0x2B7)** by any function, control or
   otherwise — and no application-code write to them either (they are written only by
   the binding engine on RX). The few getter reads that numerically coincide with
   other furnace-table spans (0304/030A/0310/0311) are all in UI / config-import /
   dictionary-publish functions and are provably the thermostat's own fields (§5).
3. **Parameterization, where it exists, is dictionary-mediated and runtime-registered**
   — the same Clarinox wall as stages A–E. The control evaluators consume
   runtime-filled RAM breakpoint/threshold tables (0xFFF8CC34/CC64/CC94/CCC4/CCDC,
   index 0xFFF8CC5A) and branch on a device-class word (mask 0x7C00: 0x0400 vs
   0x4000). The data model carries an explicit furnace-settings vocabulary
   (`idu/furnstages`, `idu/mincfm`, `idu/maxcfm`, `idu/mincfmenable`,
   `idu/maxcfmenable`, `idu/iduairflow`, `idu/heatoffdelay`, `idu/auxheatlocktmp`,
   `idu/reheat`, `idu/dehumdrain`, `idu/altitudeselect`, `idu/elevation`
   @ 0x18300D80–0x18300E38) edited by the dealer "Furnace Setup / Furnace Airflow
   Setup / Furnace Modulation Limits Setup / Furnace Staging Setup" screens.
   Whether the *furnace-reported* 0316/table-04 values feed those properties (vs.
   installer-entered values only) is decided inside runtime-registered bindings and
   is **not statically decidable** — stated plainly, not papered over.

And the negative space is clean: **the furnace's ratings are not in the firmware at
all.** 107000 / 53500 in int32 BE/LE, float32, float64 — **zero hits** in every
encoding (§6). The thermostat never knows the furnace is 107K BTU/H; staging is
demand-driven (stage E), and firing-rate knowledge stays on the furnace board —
consistent with the help text *"Furnace staging uses the furnace controls…"*
@ 0x182DA520 (the System-vs-Furnace staging-mode setting).

**Practical consequence for the emulator project:** an emulated 0x20 does not need to
replicate any furnace→control parameterization to behave like the real thermostat in
steady state — the visible control law (demand, thresholds, staging hysteresis,
interpolation) is equipment-independent given the RAM tables. What it cannot inherit
statically is how those RAM tables get populated for a given installation; that is a
commissioning-time, engine-mediated process (§7, not-isolated list).

---

## 2. Task (1) — binding records for furnace-read tables [FACT]

Directory re-walk (`stageI/scan1.py` → `stageI/out/scan1.txt`): **385/385 records
byte-identical to the stage-D dump, 0 mismatches** (dual verification). 144 records
bind tables read from 0x44. Record format per stage D:
`[len][00][table BE16][field][flags][store_offset BE16]`, directory @
0x182B5E40–0x182B6A48.

Furnace-exclusive tables and their store spans:

| table | meaning (protocol map) | directory @ | store span |
|---|---|---|---|
| 0306 | IDU status, 3 s poll | 0x182B5FE0 | 0x00F2–0x00F7 |
| 0307 | 5 s read | 0x182B5FF8 | 0x00F7–0x00F9 |
| 030A | 3 s constant | 0x182B6010 | 0x00FA–0x0139 |
| **0316** | **IDU config, 11 s** | **0x182B6210** | **0x01BC–0x01C3** |
| 0402 | tbl-04, 11 s | 0x182B64F0 | 0x0262–0x0271 |
| 0404 | tbl-04, 7 s | 0x182B6518 | 0x0278–0x028A |
| 0409 | tbl-04, 11 s (also written) | 0x182B6558 | 0x028F |
| 040D | tbl-04, 7 s | 0x182B6578 | 0x0295–0x0298 |
| 0413 | tbl-04 VARSPEED, 5 s | 0x182B65B0 | 0x02A1–0x02A9 |
| 041B | tbl-04 VARSPEED, 5 s | 0x182B65D0 | 0x02B1–0x02B7 |
| 041C/041F | commissioning probes | 0x182B65E8/6640 | 0x02B4–0x02B5 / 0x02C9–0x02CA |

0316 in full (the task's focus — heat stage [0], CFM [4..5], static pressure [7..8]
of the 8-byte payload):

| directory @ | len | field | flags | store_off |
|---|---|---|---|---|
| 0x182B6210 | 8 | 3E | 01 | 0x01BC (whole payload) |
| 0x182B6218 | 1 | 40 | 00 | 0x01BD |
| 0x182B6220 | 1 | 42 | 00 | 0x01BE |
| 0x182B6228 | 1 | 54 | 00 | 0x01BF |
| 0x182B6230 | 1 | 56 | 01 | 0x01C0 |
| 0x182B6238 | 1 | 80 | 00 | 0x01C1 |

Shared with the ODU (0x53) — same bindings serve both devices' instances of the
table: 0302 (store 0x0068–0x00C1), 0304 (0x00D2–0x00F1), 030D (0x013A–0x0152),
030E (0x0153–0x015C), 0310 (0x015D–0x0185), 0311 (0x018C–0x01B5), 0104 identity
(0x0005–0x0067). Full 144-record listing: `stageI/out/scan1.txt` §(1).

Also bound, immediately after 0316 in the layout: 0317 (0x01C4), 0319 (0x01C5–0x01C6),
031B (0x01C7–0x01C9), 031C (0x01CA–0x01D5), 031E (0x01D6–…) — semantics not decoded in
captures; see §5.3 for the one code touch in this range.

Consistent with stage D §3: the command tables (0305, 060B, 060D, 0610, 061A, 061E,
031D, 0202/0203, 400A, 3B02/3B03) have **no** records — the TX/burst side is built
programmatically, so no binding-level parameterization exists on the command side
either.

## 3. The field store and its only accessor [FACT]

Stage D left open whether the directory's offsets and the application field store are
one space. Stage I decompiled both accessors (`stageI/out/decomp_1815927c.c`,
`decomp_181592e4.c`):

- Getter **FUN_1815927c**(offset, buf, len, flag): bounds-checks offset+len against a
  runtime size word @ 0xFFF877DC, then memcpy(buf, **0x3C0E4A20** + offset, len) under
  a lock (lock object 0xFFF8AD40; memcpy = FUN_1823D404). If flag set, post-read
  notify FUN_18166394.
- Setter **FUN_181592E4**(offset, buf, len): same base; writes, then marks dirty
  pages in a bitmap @ **0x3C0E6A20** (= base + 0x2000; page size is a runtime word) —
  the store is paged and change-tracked for dictionary sync.

So there is exactly **one flat field store @ 0x3C0E4A20** behind the only accessor
pair, and both the directory region (≤ 0x524) and app fields (0x59F coil param,
0x1C7C…) fit inside it. Pool-cell census: the base value 0x3C0E4A20 occurs in exactly
**3 cells in the whole image** — 0x181593F4 (the accessors' own pool), 0x18159688,
0x181598F0 (sibling helpers in the same accessor module, 0x181592xx–0x181598xx).
**No code outside the accessor module holds the store base** → no manual
base+offset bypass reads exist anywhere, control code included. Any consumption of
store data must go through FUN_1815927c — which makes the consumer census in §5
complete, not sampled.

## 4. The control lineage never touches the field store [FACT]

Ghidra caller census of FUN_1815927c (`stageI/out/hunt_getset.txt`): 2,461 references,
638 pool cells, **899 unique caller functions**. Membership check against the whole
control lineage — **none of these call the getter**:

- control core (stage E): FUN_180c54d8, FUN_180c576c, FUN_180c5832, FUN_18051cec,
  FUN_18051e4e, FUN_18051908, FUN_18183d34, refresh FUN_181efdfc;
- producer suspects (stage E §12.5): FUN_180c15d2, FUN_180c3012, FUN_180c3418,
  FUN_180c3814, FUN_180c3bee, FUN_180c46b8, FUN_180c49ec;
- stage-E RAM consumers: FUN_18184006, FUN_181f4308, FUN_181f4e60, FUN_1816deec,
  FUN_180d2728.

The single exception, FUN_181f21d4, reads store offsets **0x01, 0x08, 0x2F, 0x31**
(thermostat's own identity/config bytes at the head of the store, inside the 0104
region) to assemble a dictionary record — housekeeping, not furnace data, not control
(`stageI/out/argextract.txt`).

### 4.1 What the producers actually consume — FUN_180c15d2 decompiled [FACT]

FUN_180c15d2 (4,610 B; `stageI/out/decomp_180c15d2.c`) is the master demand/staging
evaluator, and its input set is now fully visible:

- It reads demand float **0xFFF8CD44** (= stage-E CD44; its pool cell DAT_180c17d4 →
  0xFFF8CD44) and caps it by `table[index−1]` — the stage-E §7 cap, seen in the
  producer itself.
- It runs **two breakpoint-interpolation passes** (the FUN_18051908 pattern) over
  runtime RAM tables, selected by mode byte from **three sources**: a flash default
  @ **0x182C3130** (degenerate: floats 0.0,0.0,0.0,0.0 + 1.0 — a template, not data),
  mode-1 tables @ **0xFFF8CCDC** (breakpoints) / **0xFFF8CC94** (values), mode-2
  tables @ **0xFFF8CCC4** / **0xFFF8CC64** — i.e. mode 2 *is* stage E's CCC4 table
  with index byte **0xFFF8CC5A** (CC5A). Breakpoint array base for both passes:
  **0xFFF8CC34**.
- Equipment behaviour branches on the device-class word @ **0xFFF8CC52**
  (`& 0x7C00 == 0x0400` vs `== 0x4000`) at five separate decision points.
- It tail-calls the sibling evaluators FUN_180c3012 and FUN_180c3418. All six
  siblings decompiled (`stageI/out/decomp_180c3*.c`, `decomp_180c4*.c`): small
  RAM-only evaluators, three of them with the same 0x7C00 class masks, zero
  field-store calls.

So control **is** parameterized — but by (a) the contents of the RAM tables
CC34/CC64/CC94/CCC4/CCDC, (b) the table index CC5A, and (c) the device-class word
CC52. All three are properties in the data model, filled at runtime. Their pool-cell
census (raw scan, dual to the failed script hunt — §8): users are the control module
itself, the generated binding-accessor forest 0x181F1xxx–0x181F4xxx (the engine's
property plumbing, read/write), the satisfaction cluster 0x181841xx, the
interpolation cluster 0x1804Exxx–0x18052xxx, and a run of pure data cells @
0x18226D4C–0x18226F80 — the property-registration descriptor table. **No identifiable
"load furnace config" function writes the tables**; writes flow through the generic
property plumbing when the engine updates properties from dictionary values.

## 5. Task (2) — consumers of the furnace-bound fields [FACT]

Constant-argument extraction over the full decompiled corpus (1,275 constant-arg
getter/setter calls; `stageI/out/argextract.txt`):

### 5.1 The control-relevant spans have no consumers at all

- **0316 (0x1BC–0x1C3): zero GET, zero SET** in application code. The only writer is
  the binding engine on RX; nobody reads it back through the accessor.
- **0306 (0xF2–0xF5) / 0307 (0xF7–0xF9): zero GET, zero SET.**
- **Table-04 rows (0x262–0x2B7): zero GET** (one block read at 0x28C, len 0x46, by
  FUN_181a4f08 — that offset is table 0407's field 3E, and the function is in the
  0x181Axxxx dictionary/UI family; a 70-byte block shuttle, no arithmetic on values).
- Stage-C setter census agrees: no app-code writes anywhere in 0x1BC–0x1C3,
  0xF2–0xF9; the single tbl-04-range write (0x28C, FUN_181a4f08) is the same
  dictionary-family function.

### 5.2 Coincident reads in shared-table spans — all classified, none is furnace data

| reader | offsets | what it actually is |
|---|---|---|
| FUN_1805dd40 | 0xC9, 0xD4 | reads *and writes* the same offsets itself (stage-C census) — own working fields in the UI cluster |
| FUN_18160b34 | 0xE8 (40 B) | **config import/sync**: reads store blocks 0xE8/0x712/0x744/0x758, memcmps against externally parsed data, writes back via the setter on mismatch (`stageC/out3/decomp_18160b34.c`) |
| FUN_181d92c8 | 0xE8 (40 B) | same 40-byte own-config record, second user |
| FUN_18070858 | 0x122, 0x123, 0x125, 0x126 | copies bytes into static display buffers, interleaved with fixed-length string copies (0x2E/0x5B) — data shuttling for a screen/record, no arithmetic, no thresholds (`stageD/out_cluster_70/decomp_18070858.c`) |
| FUN_181a6454 / FUN_181a650a / FUN_181bef80 | 0x125, 0x126 | same display-buffer family |
| FUN_18067e92 / FUN_180ba074 | 0x111 | single-byte own-field reads in UI clusters |
| FUN_180d0518 / FUN_180d10d8 / FUN_181018f4 | 0x190 (70 B) | block copy of a record struct (dictionary publish family) |
| FUN_1821835a | 0xD7 (17 B) | block copy, dictionary family |

These offsets sit inside the directory spans of tables 0304/030A/0310/0311 **and**
are written by application code for the thermostat's own purposes (FUN_18160b34
proves it for 0xE8: the app treats it as its own 40-byte config record). Two readings
remain possible — one store with overlapping uses, or a per-device store distinct
from the app store (stage D §6 item 9) — but under **either** reading the conclusion
is the same: no control code consumes furnace-table data through the store. [The
readings differ only in *why* the offsets coincide, not in the consumer census.]

### 5.3 The one control-adjacent getter touch — a calendar counter [FACT]

FUN_180cb792 (`stageI/out/decomp_180cb792.c`, 96 B) is the only function in the
0x180Cxxxx range that calls the getter. It reads a 7-byte clock-like value, and when
the hour byte reaches **0x17 (23)** it reads field **0x1D6**, increments it, and
writes it back via the setter. 0x1D6 is table 031E field 3E in the directory layout;
in the app store it is plainly a **daily counter** (days counter incremented at
23:00 — e.g. filter/maintenance days). Not a control input; not furnace data.

### 5.4 The settings vocabulary — where furnace parameterization would live [FACT + inference]

The data model names the furnace-side control settings explicitly (metric dictionary
@ 0x18300D80–0x18300E38): `idu/iduairflow`, `idu/heatoffdelay`, `idu/auxheatlocktmp`,
`idu/reheat`, `idu/dehumdrain`, `idu/mincfm`, `idu/maxcfm`, `idu/mincfmenable`,
`idu/maxcfmenable`, `idu/furnstages`, `idu/altitudeselect`, `idu/elevation`. The
dealer help texts (0x182DA148–0x182DA648) describe exactly the parameterization
surface: *Furnace Airflow Setup* ("Selects the desired airflows for furnace…"),
*Furnace Modulation Limits Setup* ("Limits the maximum and minimum furnace airflow
during furnace heating"), *Furnace Staging Setup* ("Selects how the furnace stages
are controlled. Furnace staging uses the furnace controls…"), *Furnace Off Delay
Setup*. Zoning adds per-zone CFM limits ("Configure a maximum CFM limit for each
zone" @ 0x182DC46C; "Zone CFM limit set." @ 0x182C3F94) and a computed floor
("calculated minimum CFM:" @ 0x182CAB68 — the `calcMinCFM` of stage E §9.2).

[INFERENCE] These `idu/*` properties are the channel through which furnace
characteristics steer control (min/max CFM clamps on airflow commands, stage-count
limits, staging ownership). They are properties of the IDU *device object* in the
dictionary — populated by the installer UI and/or by the binding engine from
furnace-reported tables. Which of the two, per property, is a runtime-registration
fact that static analysis cannot reach (§7).

## 6. Task (3) — furnace-keyed constant hunt [FACT]

Full-image scans (`stageI/out/scan1.txt` §(3)); BE/LE, int and float encodings:

| pattern | result |
|---|---|
| 107000 (0x0001A218) BE32 / LE32 / f32 (47D0FC00) / f64 | **0 hits in all encodings** |
| 53500 (half of 107K) BE32 | 0 hits |
| 60000 BE32 | 1 hit @ 0x1830CD1C — the known dictionary-string region (stage D), not code |
| 60000.0 f32 | 1 hit @ **0x181F7310** — inside the binding-accessor/sys-ctrl region; **0 pointer-cell references**; PC-relative pool use not excluded, no control consumer identified → **unlinked** |
| CFM floats 1200 / 1600 / 1750 / 1800 / 2200 .0 f32 | 0 hits |
| 1760.0 f32 | 1 hit @ 0x18328042, 0 refs → unlinked (resource data) |
| 2000.0 f32 | 3 hits (0x181A2158, 0x1821022C, 0x182B1724), 0 pointer refs → unlinked |
| 1000.0 f32 | 13 hits; the only one with refs (0x181F2800) is referenced from the untrimmed resource tail (0x18B7xxxx–0x18BCxxxx), not from code → unlinked |

No BTU figure, no CFM figure, no per-model furnace constant exists in code. Combined
with stage D's "no furnace model database", the furnace's identity reaches the
thermostat **only** as (a) its 0104 identity strings (display/records) and (b) the
live values of its polled tables (§2) — and §5 shows (b) has no static consumer.

## 7. Task (4) — verdict: what actually parameterizes control from the furnace side

**Proven (static, dual-verified):**

1. The thermostat's control law is parameterized by **runtime data-model
   properties**, concretely: RAM breakpoint/threshold tables **0xFFF8CC34 /
   0xFFF8CC64 / 0xFFF8CC94 / 0xFFF8CCC4 / 0xFFF8CCDC**, table index **0xFFF8CC5A**,
   device-class word **0xFFF8CC52** (mask 0x7C00), consumed by FUN_180c15d2 and the
   stage-E module. Flash holds only a degenerate default table @ 0x182C3130.
2. The furnace-reported configuration (0316: stage count, CFM, static pressure;
   table-04 VARSPEED rows) is received and stored via bindings (§2) but has **no
   consumer in any statically reachable code** — not in control, not in UI, not
   anywhere (§5.1). The same holds for 0306/0307 status fields.
3. No furnace rating (BTU, CFM range, model key) exists as a constant in the image
   (§6). the author's furnace being "2-stage 107K" is a fact the thermostat's firmware
   literally does not contain.
4. The one proven equipment-parameterization mechanism in this firmware remains the
   stage-D coil path (model-pattern match → parameter float → field store 0x59F →
   061E to the ODU) — and it has **no furnace analogue**: no furnace model arrays,
   no furnace pattern matcher, no furnace commit function were found (stage D §2/§4
   + this stage's hunts).

**Not statically decidable (the Clarinox wall, same as stages A–E):**

5. Whether the engine's runtime-registered bindings copy furnace-reported values
   (0316/table-04, via the IDU device object) into the `idu/*` properties
   (furnstages/mincfm/maxcfm…) and from there into the RAM control tables — or
   whether those properties are installer-entered only. The plumbing for the first
   hop (bindings, §2) and the last hop (property accessors + registration
   descriptors @ 0x18226D4C–0x18226F80) both provably exist; the middle registration
   is runtime data.
6. Consequently: whether swapping the furnace (different stage count / blower)
   would change thermostat behaviour *without* installer re-commissioning cannot be
   answered from the image. It can be answered on the bench: change what the
   furnace reports in 0316 (or fit a different IDU) and watch whether the RAM
   tables / `idu/*` properties move — a dynamic test, matching the author's
   "if the static route fails — go dynamic" direction.

## 8. Method notes / verification

- Directory re-walk independently re-parsed from the image and diffed against the
  stage-D dump: 385/385 identical.
- Accessor-pair bodies decompiled this stage; store base/size/lock resolved from
  their literal pools (0x181593E0–0x18159410).
- Getter caller census from Ghidra's reference manager (2,461 refs), not from
  decompile text; the constant-arg extraction was run twice (before/after the
  producer decompiles landed) with identical furnace-range results.
- The stage-I copy of SetterHunt.java lacks the `V:` value-target syntax
  (NumberFormatException at SetterHunt.java:17 — `stageI/run4.log`); the two
  value hunts (`hunt_base.txt`, `hunt_tables.txt`) are therefore empty **by script
  error, not by absence of references**, and were replaced by the raw pool-cell
  occurrence census reported in §3/§4.1 (occurrence scan bounds the user set; it
  cannot distinguish read vs write per cell — stated where relied upon).
- The original run2 Ghidra process was killed by a service restart mid-decompile;
  the batch was re-run cleanly as run2b (all targets produced). No results from the
  killed run were used.

## 9. Not isolated / not proven

1. Writers of the RAM control tables (CC34/CC64/CC94/CCC4/CCDC) and of CC5A/CC52 —
   engine property plumbing; no discrete writer function identified.
2. Whether `idu/*` properties are populated from furnace-reported tables or only
   from the installer UI (§7.5) — runtime registration.
3. Semantics of tables 0317/0319/031B/031C/031E (bound, §2; not decoded in captures;
   031E's first field is reused by app code as a daily counter, §5.3).
4. The 60000.0 float @ 0x181F7310 — unlinked; a PC-relative pool load by a
   neighbouring accessor function is not excluded.
5. The 0305/0605/060D payload writers (command side) — programmatic, per stages
   D/E; any parameterization inside them inherits the same wall.
6. Identity of the two store readings in §5.2 (one overlapping store vs per-device
   store) — immaterial to the verdict, still formally open (stage D §6 item 9).

## 10. Stage-I deliverables

- This file: `~/workspace/diy-thermostat/FIRMWARE-ANALYSIS-I.md`
- `firmware-re/stageI/out/scan1.txt` — directory extraction (144 records) + constant hunts
- `firmware-re/stageI/out/hunt_getset.txt` — Ghidra census of getter/setter references
- `firmware-re/stageI/out/getter_sitefuncs.txt` — 899 getter-caller functions
- `firmware-re/stageI/out/argextract.txt` — constant-arg extraction over 721+ decompiles
- `firmware-re/stageI/out/decomp_*.c` — accessors, FUN_180c15d2 + 6 siblings, FUN_181f21d4, FUN_180cb792, FUN_180ea238
- `firmware-re/stageI/out/furn_strings.txt` — furnace/CFM/stage string harvest (320)
- Scripts: `stageI/scan1.py`, `stageI/argextract.py`, `stageI/run*.sh`, `stageI/scripts/`
