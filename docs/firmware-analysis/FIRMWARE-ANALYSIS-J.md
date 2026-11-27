# Firmware Analysis — Stage J: How the Outdoor Unit (0x53) Parameterizes Control

Image: `ion-firmware/carrier/BINF0479_Carrier.hex` (flat binary, MD5 e31903228bf39a4bc9c0a2a74192359e)
CPU: Renesas SH-2A (SH7269), big-endian; load base 0x18040000; flat offset = address − 0x18040000.
Unit under test: Heil HVA960GKA201 variable-speed ODU ("MultiStg AC 60K", 5-ton), bus address 0x53.
Question: stage D proved there is **no ODU model-string database** in the thermostat firmware. So what
ODU-reported values, if any, actually steer the thermostat's control?
Method: full accessor census over the field store (getter FUN_1815927c / setter-B FUN_181592e4 /
setter-A FUN_18159220), cross-checked against stage D's binding directory and stage E's float census.
All work on copies in `firmware-re/stageJ/`; intermediates in `firmware-re/stageJ/out/`.

## Verdict (up front)

**Almost nothing the ODU reports parameterizes control — as far as static analysis can see, nothing
does.** The binding directory dutifully maps every ODU table into the field store, but a complete
census of every field-store read/write in the image finds **zero code consumers** of the
control-relevant ODU slots: the 0608 requested-CFM slot, the 0604 compressor-speed slots, the 060E
actual-stage slot, and all five 061F float-array slots are never read or written by any
constant-offset accessor call anywhere in the firmware, and no function even mentions their
addresses as constants. The only accessor traffic numerically inside the 06xx store span belongs to
an unrelated dictionary record-maintenance family (0x181A cluster). Consistently:

- There is **no capacity constant in code**: integer 60000 appears once (@ 0x1830CD1C) with zero code
  references (dictionary data); float 60000.0 appears once (@ 0x181F7310) and is a
  milliseconds→minutes divisor in a timing-statistics function (FUN_181f7050), not 60K BTU.
- Stage E's control math is **dimensionless** (staging = demand ratios ×1.25 / ×0.25 / ×0.01; trim
  capped at 70.0) — it never needs a tonnage, which is why no capacity constant exists.
- The firmware's own dictionary vocabulary assigns CFM authority to the **IDU side**
  (`idu/mincfm`, `idu/maxcfm`, `calcMinCFM`, `vcap*cfm*`, `blowerCoolingCFM`, `systemCFM`); there is
  **no ODU-requested-CFM metric name** at all. Answer to the headline question — *does the 0305 CFM
  command follow the ODU's 0608 request?* — **no static evidence that it does; the model vocabulary
  points the other way.** (The 0305 writer itself remains unisolated, so descriptor-driven
  consumption cannot be formally excluded; see §7.)
- What the ODU *does* parameterize is the **settings plane**, not the control loop: the dictionary's
  `odu/*` names are all thermostat→ODU settings (lockout/latch temperatures, defrost backup,
  min/max stage limits, `oducoolafl`/`oduheatafl`, `flowratesetting`, `quietshift`). The ODU's
  telemetry (0302/0303 TLVs, 0604, 0608, 061F) lands in the store and the dictionary/display plane;
  the shared 03xx TLV slots do see dense code traffic (§4), but per-table attribution is not
  statically decidable, and none of it is traceable into the demand/staging path.

## 1. The binding directory's ODU records [FACT]

Directory @ 0x182B5E40–0x182B6A48, 385 records `[len][00][table BE16][field][flags][store_offset
BE16]` (stage D). Full extraction for all 0x53 tables: `stageJ/out/odu_bindings.txt` (99 records).
Caveat carried from stage D and confirmed relevant here: **the directory has no destination field** —
03xx tables exist on both 0x44 and 0x53, so 0302/0303/0304/0310/0311 bindings cannot be attributed
to the ODU instance specifically. 06xx tables exist only on 0x53.

Control-relevant records (directory address, len, table, field, flags, store offset):

| Table | Records | Store layout |
|---|---|---|
| 0604 compressor speed | 5 @ 0x182B66C8–0x182B66E8, flags=01 | f51 len3 @0x2E9; f52 len5 @0x2EE; f56 len1 @0x2EF; f57 len6 @0x2F5; f5B len6 @0x2FB |
| 0605 commanded stage | 3 @ 0x182B66F0–0x182B6700, **flags=03** | f56 len6 @0x301; f57 len1 @0x302; f5B len1 @0x303 |
| 0608 EXV + requested CFM | 5 @ 0x182B6748–0x182B6768, flags=01 | f51 len16 @0x35F; f52 len3 @0x362; f56 len2 @0x364; f57 len3 @0x367; f5B len2 @0x369 |
| 060E actual stage | 1 @ 0x182B6790, flags=01 | f52 len5 @0x37C |
| 061F float array (81 B) | 5 @ 0x182B67F0–0x182B6810, flags=01 | f51 len10 @0x3D9; f52 len19 @0x3EC; f56 len19 @0x3FF; f57 len17 @0x410; f5B len25 @0x429 |

061F's five records are **overlapping views** of one object (spans interleave and total 0x3D9–0x442 ≈
the 81-byte payload), not five concatenated fields — the same union-view pattern stage D found in
0104. Also bound: 0602 (5 records, the 2-stage-ODU family object; never seen on the wire for this
variable-speed unit), 0606/0607/060A/0612/0613/0615/0616/0618/0625, 0302 (14 records, store
0x68–0xC0), 0303 (5, 0xC2–0xCE), 0304 (9, 0xD2–0xF2), 0310 (9, 0x15D–0x184), 0311 (10, 0x18C–0x1B4).

flags: 210 records image-wide are 01, 140 are 00, 35 are 03. Every flags=03 table is a
command/bidirectional object (0307, 030D, 0605, 0615, 0618, 07xx zone outputs) — consistent with
bit0 = read/ingest binding, bit1 = write/command binding [inference, pattern over all 35].

## 2. The accessor census — method and coverage [FACT]

Field store: base 0x3C0E4A20, NVRAM-backed (stages C/D). All code access goes through three
functions, called almost exclusively through per-function literal-pool cells (rendered by the
decompiler as `(*(code *)PTR_FUN_<cell>)(offset, buf, len[, hook])`):

- Getter **FUN_1815927c**: 2,461 references, 638 pool cells, **903 distinct caller functions**.
- Setter-B **FUN_181592e4**: 894 call expressions / ~349 caller functions (stage C extraction,
  re-filtered here).
- Setter-A **FUN_18159220**: exactly 1 call site (FUN_181664da, stage C).

Coverage proof: cell-derived getter site functions = 899; xref-derived code-ref functions = 903.
The 4-function delta was decompiled and reconciled: FUN_1815989a / FUN_181598b0 are the store
engine's own internal get-byte / get-short wrappers (offset passed in by caller; their only caller
is FUN_18159712, inside the accessor cluster 0x18158C00–0x18159C00); FUN_180e77b8 / FUN_180e77d0 are
typed getters of store offsets **3** and **1** (system fields, not ODU). No consumer population
hides behind the wrappers.

From the 899 decompiled getter-site functions I parsed **2,275 rendered accessor calls** (only 34
have a non-constant first argument — the descriptor-provider pattern of stage C §2). I then filtered
every constant-offset call against the ODU store ranges, and separately grepped all 899 decompiles
for the slot-base constants in both hex and decimal rendering.

## 3. Result: the 06xx slots have no code consumers [FACT]

Constant-offset accessor calls with offset in the whole 06xx binding span (0x2DD–0x44C) — the
**complete** list, from both the getter census and stage C's setter-B extraction:

- FUN_181a4f08 / FUN_181a52ca: get/set offsets **0x318, 0x35E, 0x3A4, 0x3EA**, length 0x46 each.
- FUN_181a2f6e: get 0x430. FUN_181a58de / FUN_181a5992: get/set **0x430**, len 8.
  FUN_181a5ab8 / FUN_181a5b4a / FUN_181a5c86: get/set **0x438**, len 0x38.

**Zero** calls — getter or setter, constant or rendered — touch the actual ODU slots:
0604 @ 0x2E9–0x300, 0605 @ 0x301–0x303, **0608 @ 0x35F–0x36B**, 060E @ 0x37C, 061F @
0x3D9/0x3EC/0x3FF/0x410/0x429. The slot-base constants (0x35F, 0x3D9, 0x2E9, 0x301, 0x302, 0x303,
0x37C; decimals 863, 985, 745, 769, 770, 771, 892) appear in **0 of 899** decompiled functions.

The 0x181A traffic is an unrelated record-maintenance family [FACT: decompiles in
`stageJ/out/decomp_key/`]:

- FUN_181a4f08 (body 946 B): maintains 8 records of 0x46 bytes at bases 0x200 + 0x46·k (k = 0..7 →
  0x200, 0x246, 0x28C, 0x2D2, 0x318, 0x35E, 0x3A4, 0x3EA); each record holds 7 slots × 10 bytes;
  absent slots are filled with (0x60, 0x00) word pairs; writes back only on change (FUN_181a49f2
  compare, dirty-flag byte). No float math, no demand/CFM logic.
- FUN_181a58de: 8-byte per-index state array @ 0x430 + mask byte @ 0x470, change-detected.
- FUN_181a5b4a: 8 × 7-byte string slots @ 0x438 + type bytes @ 0x5A7, change-detected.

[inference] This is a dictionary bookkeeping family (per-index named/state records). Its record
bases step through the same numeric range the binding directory assigns to 06xx fields — i.e. the
directory's store offsets and this family's records interleave in one flat store, and the directory
offsets for 06xx do **not** correspond to slots that ordinary code reads. The same 0x46-byte record
pattern appears in the 0311 span: FUN_180d0518 / FUN_180d10d8 read+write offset 0x190 with len 0x46.

As with ingest (which also has no constant-offset setter calls for 06xx), any engine-internal
movement of these objects would be descriptor-driven (computed offsets) and is therefore invisible
to a constant census — the same Clarinox registration wall stages D and E hit. What the census
*does* prove: **no application-level code** — no control, UI, or telemetry function that addresses
fields by constant offset, the way all other consumers in this firmware do — ever touches the ODU
command/telemetry slots.

## 4. The shared 03xx tables: dense traffic, undecidable attribution [FACT + limit]

The 0302/0303/0304 slots are the opposite picture: ~200 constant-offset accessor calls land exactly
on directory offsets (0302 f3E @0x68, f40 @0x70 — FUN_181b9448, FUN_180b8eec, FUN_180b966a; 0303 f51
@0xC2 — many callers; 0304 f3E @0xD2 …), in clusters at 0x1805–0x1806 (device-object layer),
0x1810fca8/0x18112fba (paired extractors sweeping 0xB7–0xC3), and 0x181B (TLV handling). So the TLV
sensor/pressure values (OAT, coil temp, suction/discharge, superheat per InfinitESP's type map) do
reach the device-object layer. Two hard limits:

1. The directory binds table IDs, not device instances — 0302/0303/0304 exist on the furnace too,
   so this traffic cannot be attributed to the ODU's instance over the furnace's.
2. The flat store aliases unrelated system fields into the same spans (the coil-model index 0x9A
   sits inside 0302's nominal span; stage C's presence field 0xC4 sits inside 0303's) — an offset
   census cannot be read 1:1 as "control consumption of table X".

And the endpoint that matters is still missing: stage E could not isolate the producers of the
zone module's inputs either. No path from any 03xx slot into FUN_180c54d8 (staging) or the demand
chain is statically visible.

## 5. The CFM question (0608 → 0305) [FACT + verdict]

- 0608 field 51 (len 16 @ store 0x35F) is the slot the directory reserves for the object whose
  payload carries, per InfinitESP, EXV position % and the ODU's requested IDU airflow (uint16 BE,
  payload bytes [5..6]). **No code reads or writes 0x35F** (§3). The constant 0x35F appears nowhere
  in 899 decompiled accessor users, hex or decimal.
- The firmware's own data-model vocabulary (stage E dictionary dump, re-grepped here) contains
  **no ODU-requested-CFM metric**. CFM names are: `idu/mincfm`, `idu/maxcfm`, `idu/maxcfmenable`,
  `idu/mincfmenable`, `calcMinCFM`, `absmincfm`, `absmaxcfm`, `cfmlimit`, `cfmlimitsvalid`,
  `vcapcfmfloor`, `vcapcfmceiling`, `vcapcfmuplimit`, `vcapfloorcfm`, `vcapceilingcfm`, `iducfm`,
  `systemCFM`, `blowerActualCFM`, `blowerCoolingCFM`, `blowerHeatingCFM` — every one IDU/system-side
  or a variable-capacity limit computed in the thermostat. The `odu/*` namespace is settings-only
  (see Verdict).
- Verdict: **the thermostat's CFM command is, on all static evidence, computed on the IDU side**
  (furnace model + vcap limits), **not** slaved to the ODU's 0608 request. The 0608 request is
  ingested into the store/dictionary plane and, statically, goes no further. Formal exclusion of a
  descriptor-driven path inside the unisolated 0305 writer is impossible statically (§7 gives the
  dynamic test).

## 6. Constants hunt [FACT]

**Capacity 60K / 5-ton.** BE32 60000: exactly 1 occurrence, @ 0x1830CD1C — XrefDump: **0 code
references** (dictionary data region, consistent with stage E). Float 60000.0: exactly 1 occurrence,
@ 0x181F7310 — referenced **only** by FUN_181f7050, where it divides a millisecond-tick delta
(pool companions raw-read: 0x181F730C = 2³², 0x181F7314 = 2³¹ — uint32 wrap correction; result is
elapsed minutes over 8 channels, a timing-statistics aggregator; final setter-like calls publish
0x20- and 8-byte arrays). Float 60.0: 14 occurrences, each referenced by exactly one function, in
TLV/unit-conversion clusters (0x181B…) and the binding cluster (0x181F…) — no capacity use.
**Conclusion: capacity in BTU/tons exists nowhere in code.** The control never needs it: stage E's
staging is ratio-based and its only magnitude cap is 70.0 (0x1830B128). Parameterization by model
therefore reduces to what stage D found for the coil (a dimensionless float, 1.69) plus the IDU-side
CFM limit model — the ODU contributes no number the control math consumes.

**Partial-stage floats (gap G8).** Independent corroboration of stage E: my raw occurrence count
for float 5.0 is **69 — identical to stage E's independently produced census**. None of the
functions referencing float 5.0 in stage E's FloatHunt (interpolation FUN_18051908, quantizer
FUN_180c576c, unit conversions, averaging FUN_18183d34…) touches the ODU store span, and the only
functions that touch the 06xx span (0x181A family) contain no float math at all. **No partial-stage
table or stage-float selection exists in any ODU-adjacent code. G8 remains open exactly as stage E
left it**; the 0605 float (0.0 / 5.0 in captures) is produced by the unisolated TX path, plausibly
from stage E's staging/quantizer outputs [inference].

**0605 tail bytes.** Captures: idle `00000000000001`, max-cool `40A00000010001` — by direct recount
of the hex strings, byte [4] is 0x00 idle / 0x01 during a call and byte [6] is 0x01 always. (The
protocol map says "[5] also changes" — the recount disagrees; the map's index is off by one.)
0605's directory fields are flags=03 (bidirectional command object, §1), so the payload is assembled
by the engine from the 0605 object: float field + two 1-byte fields @ store 0x302/0x303. **No writer
of 0x302/0x303 exists in the complete accessor census.** The always-0x01 byte is consistent with a
descriptor-defaulted bound byte in the NVRAM-backed store (stage C showed descriptor defaults
initializing fields) [inference]; the call-state byte [4] is consistent with an engine-set
valid/active flag [inference]. Origin: **not isolated** (§8).

**061F semantics.** To the thermostat, statically, the 81-byte float array (superheat, subcooling,
temperatures per InfinitESP) is a store/dictionary object with five overlapping typed views (§1)
and **no code consumer**. Whatever meaning its floats have is exercised, if anywhere, inside the
unisolated engine/dictionary plane (display, logging, Sparkplug publish) — not in any
constant-addressed control or telemetry function.

**060E actual stage.** One binding (f52 len5 @ 0x37C), zero accessor traffic. The thermostat tracks
its *commanded* stage through its own 0605 object; the ODU's actual-stage readback has no visible
consumer.

## 7. What would settle the open points (dynamic, for the parent plan)

1. **CFM authority test** (settles §5): on the live bus, vary the load so the ODU's 0608 requested
   CFM changes (it does across a call), and check whether the 0305 CFM word tracks it or tracks the
   IDU-side model instead. Captures already in hand may suffice: correlate 0608 [5..6] against the
   following 0305 CFM across the cold-start and scenario captures.
2. **0605 tail test**: the [4] byte against call state is already in captures; whether [6] is ever
   ≠ 0x01 (e.g. during defrost or a fault) decides "constant enable" vs "mode bit".
3. Nothing dynamic can resurrect a static consumer for 0604/061F/060E — if a future capture shows
   control behavior changing with those values, the path is descriptor-driven inside the engine and
   only a bus-in-the-middle experiment (spoofed 0x53) will find it.

## 8. Dual-verification log

1. Directory records: stage D's parsed dump vs my independent raw re-parse of the image at 15
   probed record addresses (0602/0605/0606/0607/0608/061F) — table, field, flags, len, store offset
   agree on all 15 (e.g. 0608 f51 @ 0x182B6748: len16, store 0x35F; 061F f5B @ 0x182B6810: len25,
   store 0x429).
2. Getter coverage: cell-derived site list (899 functions) vs xref-derived code-ref list (903) —
   delta of 4 explicitly decompiled and classified (§2).
3. Setter-side census: stage C's independent decompile-based extraction (894 calls) re-filtered
   here — same 06xx-span hits (0x430/0x438 writes by FUN_181a58de/FUN_181a5b4a) as my getter-side
   parse; two methods, one result.
4. Float 5.0 occurrence count: 69 by my raw scan = 69 by stage E's FloatHunt.
5. FUN_181f7050's divisor: decompiler rendering vs raw pool reads at 0x181F730C/0x181F7310/0x181F7314
   (2³² / 60000.0 / 2³¹).
6. Integer 60000 reference count: 0 by XrefDump here = "no code refs" by stage E's recon.

## 9. Not isolated / not proven

- The 0305 writer and the whole TX/burst path (stages D/E wall) — hence descriptor-driven
  consumption of any store slot cannot be formally excluded; the census bounds it to the engine
  interior.
- The producers of the zone module's inputs (stage E) — hence no proven path from 03xx TLV values
  into demand, in either direction.
- Origin of 0605 payload bytes [4] and [6] (no writer at store 0x302/0x303 in the census).
- Whether the binding directory's store is byte-identical with the accessor store in the 06xx span
  (stage D item 9): the 0x181A record family interleaving the same numeric range suggests the
  directory's 06xx offsets are engine-private views, but identity was not proven.
- The role of the 0x181A record family itself (classified as dictionary bookkeeping from its
  shape — 8 records × 7 slots, 7-byte strings, change detection — its registration name is unknown).
- FUN_181a49f2 / FUN_181a496c / FUN_181a498e (compare / lock / unlock helpers of that family) were
  classified from use, not decompiled.
- 0310/0311 counter fields: no field-specific consumer found; only the bulk 0x46-byte record
  traffic at 0x190. Who increments runtime/cycle counters is not isolated.
