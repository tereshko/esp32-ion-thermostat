# FIRMWARE-ANALYSIS-B.md — ICP Ion BINF0479 firmware, RE stage B

Date: 2026-10-30. Desk work on files only; nothing was flashed or written to
any device. Continues `FIRMWARE-ANALYSIS.md` (stage A). Tooling and all
intermediate output are preserved in `firmware-re/stageB/` (Ghidra project in
`firmware-re/stageB/proj/`, scripts in `…/scripts/`, decompilations and xref
dumps in `…/out/`).

Labels: **[FACT]** = measured/decompiled directly this pass. **[INF]** =
inference, reasoning shown. Negatives state the space searched.

---

## 0. Headline results

1. **The check word is SOLVED [FACT].** The word at 0x18F3FEF8
   (0x92B6CC87) is a **plain 32-bit additive byte sum** over the raw image
   span **0x18040000–0x18F3FEF8** (end exclusive), with unprogrammed gaps
   counted as 0xFF (erased flash). It reproduces the stored value *exactly*.
   No cryptographic signature exists anywhere in the integrity path this
   image shows. → Stage A's blocker (b) against patching ("unexplained
   check word would likely trip any byte flip") is **removed**: a modified
   image can be made self-consistent by recomputing one word.
2. **The SAM gate branch itself was NOT located [honest negative].** The
   descriptor-interpreter and string-renderer roads were followed to their
   ends and are mapped below; both terminate in the Clarinox runtime's
   registry layer, upstream of which static xrefs dissolve. §5 lists every
   anchor searched. §6 gives the single concrete stage-C step that remains:
   it starts from a function identified this pass (the field-store getter
   FUN_1815927c and the SAM-present field 0xC4), not from strings.
3. **The device-presence model is now concrete [FACT].** Presence of each
   bus device is a byte in a runtime field store; `'Z'` (0x5A) = present.
   SAM-present is field **0xC4**, read by FUN_1806fe8c; the SAM-vs-B36
   variant selector is field **0x23**, read by FUN_1806a110; both go through
   the shared field-store getter **FUN_1815927c**. These flags are *outputs*
   of the discovery process — the gate is whatever decides to set them.

---

## 1. Environment built (stage B infrastructure)

**[FACT]** Ghidra **12.2** headless (`analyzeHeadless`) + Temurin JDK **25**
(Ghidra 12.2 rejects JDK 21) were installed under `firmware-re/stageB/`
(`jdk/`, `ghidra/`). The decoded image was imported as a flat binary at base
**0x18040000**, language **`SuperH:BE:32:SH-2A`**, trimmed to
0x18040000–0x18459E84 (boot + all main regions; certificates/resources not
needed in the project and were analysed bytewise in stage A).

**[FACT]** Because a raw import has no entry points, disassembly was seeded
from 3,284 harvested function pointers (vector-table entries + every aligned
word in code regions pointing at a known SH prologue pattern); all 3,284
seeds materialised as functions. Full auto-analysis then ran to completion:
**10,853 functions**. The saved project (`firmware-re/stageB/proj/Bing`) is
directly reusable for stage C — no re-import needed.

Tooling notes: capstone 5.0.7's SH backend still segfaults on long streams;
all capstone work was subprocess-chunked (`dis_range.py`). `/tmp` is a
512 MB tmpfs in this environment — everything lives on the workspace disk.

---

## 2. Check word — SOLVED (task 4, second attempt)

**[FACT] Algorithm:** `stored_word == sum(all bytes in [0x18040000, 0x18F3FEF8)) mod 2^32`,
where addresses not programmed by any record contribute 0xFF (their erased-
flash value — which is also what a verifier reading raw flash would see).

**[FACT] Verification** (script `cksweep.c`, sweep of 13 named CRC models ×
12 ranges × 3 fill treatments, plus word/byte sums, XOR, Adler-32, FNV-1/1a;
the one hit was then re-verified independently in Python):

- bytesum(0x18040000..0x18F3FEF8, 0xFF fill) = **0x92B6CC87** = stored. ✔
- Start perturbed to the entry point 0x180405FC → 0x92B55C63 ✗
- Range extended to include the word itself → 0x92B6CF22 ✗
- Same range with 0x00 gap fill → no match ✗
- Concatenated-segments CRC-32/Adler → no match ✗

The definition is precise, not a family resemblance: header included, check
word excluded, erased flash counted as 0xFF.

**[FACT] Who consumes it in-image: nobody, as code.** The address
0x18F3FEF8 occurs exactly twice as data and nowhere as a code literal:
(1) the header segment table at 0x18040028 (§3); (2) inside the system
control's own device-info field list at 0x180BB55C, alongside pointers to
the version string (`CESR******-**.79` at 0x18040010), the model string
(`INFINITY NEXT GEN UI …`) and field IDs 0xFFF82046/2058–2060 — i.e. the
check word doubles as a **displayed data field** on the control's own info
screen (a "software checksum" readout) **[INF: role identification from
field-list context; the field list itself is fact]**.

**[FACT]** No in-image code references the header table base 0x18040024
either (zero occurrences as a literal anywhere). ⇒ The segment table and
the check word are consumed by the **off-image updater/bootloader**, not by
application code **[INF, strong: both addresses have no code consumer in a
fully analysed 10,853-function image]**.

**Consequence for the patch plan:** the integrity scheme is an additive
checksum — the weakest standard option, chosen for corruption detection,
not tamper resistance. If a future stage ever identifies a byte worth
flipping, keeping the image self-consistent costs one recomputed word.
The residual unknown is unchanged from stage A §7: an off-image bootloader
could *additionally* check something else; nothing in this image evidences
that, and the only check value present is now fully explained.

---

## 3. Boot/table region 0x18040024–0x18044E1C — read end-to-end

**[FACT]** Contents, in order:

- **0x18040024–0x1804006C:** segment descriptor pairs:
  (0x180405FC, 0x18F3FEF8), (0x18F3FEFC, 0x18F40000), then seven pairs in
  the 0x19C50000–0x1A000000 range (outside this file — sibling images /
  external regions of the update set; purpose undetermined, as in stage A).
  The first pair brackets exactly the checksummed span of §2, ending where
  the check word sits.
- **0x1804006C onward:** the SH-2A exception vector table — (PC, SP) reset
  pair (PC = 0x180405FC, the type-5 start value) followed by handler
  pointers; default handler **0x18044DD0** repeated; real handlers at
  0x1804060C, 0x18040628, 0x18040672, 0x180406BC, … (Renesas RSK2 BSP
  startup/interrupt code; `rte`-terminated).
- **Entry stub 0x180405FC [FACT]:** loads r4 = 0x90D04 and calls two
  main-region functions via literal pool: **0x1816DEE6** and **0x18185900**
  (BSP/Clarinox init and the application entry, in some order) **[INF for
  the roles]**.

No checksum loop, no SAM logic, and no reference to the descriptor records
exists in this region — it is Renesas BSP startup only. The boot region
does **not** contain the gate, and does not itself verify the check word.

---

## 4. The descriptor road — followed to its end

Stage A's "device-info descriptor records" are not data records.
**[FACT]** Each is a **cluster of small functions plus their literal pools**:
the pool cells hold the label-string pointers and field IDs that stage A
read as record fields. Per device there is a getter trio (model / serial /
SW-version) plus predicate helpers, e.g.:

| Device slot | Model getter | SN getter | SW getter | Notes |
|---|---|---|---|---|
| 1 – system control | 0x18057862 | (pool 0x1819EFBC…) | | builder case 1 |
| 2 | 0x1806BD16 | … | … | |
| 3 | 0x1806D2B6 | … | … | |
| 4 | 0x18071E0A | … | … | presence probe FUN_181e9512(idx 5..8) |
| **5 – SAM/B36** | **0x1806FCDE** | **0x1806FD60** | **0x1806FDD0** | see below |
| 6 – NIM | 0x1806C366 | 0x1806C3E8-cluster | | |
| 7 – IDU/ODU | combined builder | | | appends " - IDU"/" - ODU" |

**[FACT] The Model/Serial Numbers screen builder is FUN_1819ee96(short
device_index)** (decompiled, `out/decomp_1819ee96.c`): a 7-way switch that
fills screen fields 0xCF3 (model), 0xCF5 (SN), 0xCF9 (SW) and extra rows
0xCE7–0xCF1 by calling the selected device's getter trio through a
literal-pool function table (0x1819EF84–0x1819F5E0). This is the screen from
the user's photograph; the builder contains **no presence gating of its
own** — row inclusion happens in whoever calls it per device.

**[FACT] Case 5 (SAM/B36) detail:** a predicate selects between two getter
trios — if `FUN_1806a110()` is true, the trio at
0x18069F1A / 0x18069FC6 / 0x1806A072 (the B36 cluster); else, if
`FUN_1806fe8c()` reports presence, the SAM trio above. Both predicates are
9-instruction field-store reads:

```c
bool FUN_1806fe8c(void) {          // SAM present?
    char buf[8];
    FUN_1815927c(0xC4, buf, 1, 1); // field-store get, field 0xC4
    return buf[0] == 'Z';          // 0x5A
}
bool FUN_1806a110(void) {          // variant selector (SAM vs B36 form)
    char buf[8];
    FUN_1815927c(0x23, buf, 1, 1); // field 0x23
    return buf[0] == 'Z';
}
```

**[FACT]** The shared getter is **FUN_1815927c** — the same value
(0x1815927C) that sits as a trailing word in every device cluster's pool
(stage A noted it without identifying it). The screen-side setter/getter
pair used by the builder is FUN_183c30be / FUN_183c30b8.

**[FACT] The "field tables" of stage A (0x1815B29C / 0x1815B530 /
0x1815B538)** are registries of tiny generated getter functions (the
0x1C-stride repeated prologues at 0x1806FEF0… are individual functions, not
array elements). Their consumer FUN_1815b1ec (decompiled) calls four of
them and packs the results into a byte record with per-field defaults
(0x5F, 0x32, 0x50, 0x0F) and a validity bitmask — a data-binding combiner,
representative of thousands like it. FUN_1815b0e6 likewise walks a
(data-ptr, code-ptr) pair table. **FUN_1823d404**, the "shared callee" of
all clusters, is plain **memcpy** — that lead is closed.

**Verdict on this road:** it is the UI/data-binding layer end to end. It
reads presence flags; it never decides them. The interpreter the task
brief hoped would lead into commissioning logic leads into screen
plumbing instead. **[FACT for the functions named; INF for the layer
characterisation, which the decompilations support directly]**

---

## 5. The gate — searches performed, all negative

**[FACT]** Each of the following was executed and came back empty or
false-positive-only:

1. **String-table slots for IDs 177–182** (0x183B1528–0x183B153C): *zero*
   references of any type in the fully analysed program. The table base
   0x183B1264 (verified exact this pass: run of 243+ string pointers,
   entry [0] = `enable`, slot arithmetic (0x183B1534−0x183B1264)/4 = 180
   exactly) **never occurs as a literal anywhere in the image**, nor do
   its header words at 0x183B1234–0x183B1260. ⇒ The renderer reaches the
   table only through a runtime-registered resource pointer; the 180-path
   and 181-path are *the same code* at the string layer — there is no
   branch there to diff. The asymmetry is upstream, in discovery.
2. **ABCD table-definition records** (SAMINFO at 0x182AFF9C, INGDATA,
   SCHEDULE, TEMP — variable-length records ≈120 B: header, 8-char name,
   field-descriptor bytes): zero code xrefs to any of them. Also
   runtime-registered; the protocol stack finds them by scan/registry,
   not by address.
3. **Registration-step ID clusters:** no occurrence of table IDs
   0x040E / 0x3F02 / 0x031C clustered within ±96 B anywhere in code
   regions (the only clusters are coincidental bytes inside compressed
   resources). No static per-device step-descriptor table exists in that
   form.
4. **String-ID descriptor arrays:** u16/u32 values 177–182 clustered in
   data were all false positives — font glyph metrics (0x184xxxxx),
   SH opcode bytes (0x1817B4xx), and a hash-prime table (0x182AF0E0).
5. **The header table / trailer word as code operands:** none (§2, §3).

**Why the xref well runs dry [INF, well-supported]:** this application is
built on the Clarinox object system — ~10,800 functions in which screens,
devices, protocol tables and strings are all runtime-registered objects
addressed by numeric IDs (the 0xFFF8xxxx field-ID space and the
0x3C12xxxx object-ID space, both enumerated in stage B working notes),
and called through function-pointer registries and a field store.
 statically, almost nothing references anything else by address; the
wiring is assembled at init from registry tables. The commissioning
driver is one of the ~10,800 functions, but no static anchor reachable
from the UI side names it.

**What the gate most plausibly is, given all evidence [INF]:** a
discovery-time decision whose *result* is recorded in (a) the field store
(SAM-present byte 0xC4 etc.) and (b) the control's nonvolatile equipment
configuration. The deciding input is device-resident data (stage A §5:
the image is brand-universal), with the ranked candidates from stage A
unchanged: nonvolatile config/personality data not present in this image
(consistent with the header table's external 0x19xxxxxx segment
descriptors), a value in the control's own bus-served config tables, or a
hardware/SKU strap sampled at boot. Stage B found **no** evidence of
eFuse/OTP involvement and no model-string comparison in the paths it
decompiled; the control's own model string (`SYST0101CW`) does not occur
in the code regions at all — identity strings are data, supplied at
runtime.

---

## 6. Reachability assessment — can anything a user (or the bus) touch flip it?

- **microSD update path:** changes nothing about the gate (Carrier image
  is byte-identical — stage A). It is, however, now known to be *safe to
  reason about* for patching: the only in-image integrity value is an
  additive byte sum (§2), recomputable after any edit. Patching remains
  pointless until the gate is located — there is still no known byte to
  flip — and the off-image bootloader caveat of §2 stands.
- **Service/dealer menus:** the image contains a brand-selection setting
  ("Select an ICP brand to display on the Home screen") — branding is a
  runtime menu value **[FACT: string exists]**, but it controls the home-
  screen logo, and no menu string suggests a SAM/accessory enable.
  Nothing found indicates a menu-reachable SAM switch **[INF]**.
- **The ABCD bus (the control's own tables):** the most plausible
  user-reachable channel **[INF]**. The control serves its configuration
  as bus tables (the thermostat-protocol map from the earlier project
  phase documents config-bearing tables, and the pending direct-write
  programme — 400A test, table scan — probes exactly this surface). If
  the gate reads a config value that is also bus-visible, the table scan
  can find it and a bus write could flip it, subject to the same
  source-gating question the 400A test is designed to answer. This is
  testable with equipment the user already runs; no firmware modification
  is required to test it.
- **Fused/internal-only:** cannot be excluded, but nothing in two stages
  of analysis points at OTP/eFuse; the architecture (field store +
  nonvolatile config + runtime registries) points the other way **[INF]**.

---

## 7. Single concrete next step (stage C)

**Find the writer of field-store field 0xC4.** Concretely, in the saved
Ghidra project: (1) identify the field-store *setter* (the write twin of
getter FUN_1815927c — expected adjacent in the field-store implementation
cluster around 0x181592xx); (2) enumerate callers of the setter and filter
for call sites passing field index **0xC4** (and, secondarily, 0x23);
(3) the caller that writes `'Z'` to field 0xC4 sits inside the SAM
registration routine — walk *up* from it to the first conditional that
can skip the routine, and read what *it* compares. That conditional is
the gate, and its operand will name the data source directly (config
field, identity value, or strap). Estimated effort: one focused session
in the existing project; all anchors are in hand.

Secondary, cheap: the same filter on the equipment-config persistence
write (the routine that commits discovered devices to nonvolatile
storage) — its caller set overlaps discovery by construction.

---

## 8. What stage B cannot claim

- The gate's address, comparison, or operand — **not found** (§5). Any
  document claiming them from this pass would be inventing them.
- That the off-image bootloader verifies *only* the §2 byte sum — the
  image proves the sum is *the* stored check value and matches it
  exactly; a bootloader could still apply additional policy off-image.
- The roles of entry-called functions 0x1816DEE6 / 0x18185900 beyond
  "BSP/app init" **[INF]** — not decompiled this pass.
- Full code coverage: the seed+analysis pipeline found 10,853 functions,
  but computed-call targets inside registry tables can hide leaf
  functions from static enumeration; the discovery driver may be among
  the less-connected functions for exactly that reason.
