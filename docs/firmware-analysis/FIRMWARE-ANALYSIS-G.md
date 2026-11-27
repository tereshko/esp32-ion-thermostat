# FIRMWARE-ANALYSIS-G.md — ICP Ion BINF0479 firmware, RE stage G

Date: 2026-11-26. Desk work on files only; nothing was flashed or written to
any device. Continues `FIRMWARE-ANALYSIS.md` (stage A), `-B`, `-C`, `-D`,
`-E`. Work was done in the saved Ghidra project **copied** to
`firmware-re/stageG/proj/` (other stages untouched); scripts and all
intermediate output are preserved in `firmware-re/stageG/` (`scripts/`,
`out/`, `runG*.sh`, `runG*.log`). Image: `ion-firmware/carrier/
BINF0479_Carrier.hex` (binary), SH-2A BE, base 0x18040000, flat offset =
address − 0x18040000 in `firmware-re/stageB/flat_trim.bin`.

Labels: **[FACT]** = measured/decompiled/disassembled directly this pass.
**[INF]** = inference, with reasoning shown. Negatives state the space
searched. Extracted facts were confirmed by a **second independent
method** where the stage-E report had flagged single-method claims; the
dual-verification log is §7.

**Mission:** (1) enumerate the registration sites that populate the
`sys_ctrl_task` dispatcher's RAM/dictionary handler table and map the 12
message classes to handlers; (2) decompile and exhaustively analyze
FUN_180c15d2, stage E's prime suspect for producing the zone-demand
decision module's inputs (demand float 0xFFF8CD44, threshold-table index
byte 0xFFF8CC5A).

---

## 0. Headline results

1. **The handler table is never populated by any statically discoverable
   path [FACT, negative, dual-method].** The table base 0x3C12EC70 occurs
   exactly once in the whole image — the dispatcher's own pool cell
   0x181F81F4. No slot address (0x3C12EC70+4i) occurs anywhere; no
   function that could be a handler (the whole 0x181F8238–0x181F85E2
   helper family) appears as a data word in any table; neither the stage-C
   descriptor table (0x182B04D4) nor the sys_ctrl module descriptor
   (0x183B49C4) contains a handler array (§2). Consequence: at runtime
   every dispatched class takes the NULL branch into the "default
   handler" — which is not a stub but a complete 10-state supervision
   state machine, FUN_181f86cc (§4). **The class→handler map is therefore:
   classes 0–19 → FUN_181f86cc(class)**; the per-state action functions it
   invokes are all decompiled (§4, §5).

2. **The registration machinery that DOES exist was isolated [FACT].**
   sys_ctrl is driven by Clarinox engine *properties* whose change
   callbacks are the message-post stubs. FUN_181f8340 (run from state 1)
   registers six properties (ids cached at RAM 0xFFF8CF45–0xFFF8CF4A)
   with post-stub callbacks for classes 4, 12, 5, 6, 7, 8 and seeds their
   values (10, 30, 300); FUN_181f86ae (task init) registers a seventh
   (0xFFF8CF44, class 0). Property values are reprogrammed by the state
   machine's actions (30→45, 15, 80/120, a computed 30–60) — the values
   behave as periods/thresholds of the supervision timers [INF] (§5).

3. **The post side is fully mapped [FACT].** Twenty 20-byte stubs
   (0x181F7500–0x181F7694) each build a 4-byte message {class} and call
   the post API FUN_181f7694; the stub→class map (classes 0–19) is §3.
   FUN_181f7694 does lock, queue-occupancy bookkeeping against the same
   stats table the dispatcher maintains (0xFFF8C688), and the actual
   queue send (FUN_180bc558) — except class 8, which it consumes itself
   as a stats snapshot+reset command.

4. **Stage E's single-method dispatcher claims are now dual-verified
   [FACT].** The raw listing of FUN_181f7fc4 confirms at instruction
   level: 1000 ms receive timeout (`movi20 #0x3e8`), message = one int at
   0xFFF8CF40, dispatch `handlerTable[class]` with table 0x3C12EC70,
   NULL → FUN_181f86cc(class), stats only for class < 12, stats stride
   0x10 with count +2 / max +4 / min +8 / running-avg +0xC (§1,
   `out/listing_disp.txt`).

5. **TARGET 2 verdict: FUN_180c15d2 does NOT compute the demand float or
   the index byte [FACT].** Both 0xFFF8CD44 and 0xFFF8CC5A are read-only
   inputs to it (7 pool cells for CC5A, 2 for CD44, every use a load —
   decompile + raw cell resolution, §6). FUN_180c15d2 is the decision
   module's **piecewise-linear table-interpolation engine**: it consumes
   CD44 (and an adjusted copy) over three breakpoint tables (0xFFF8CC34,
   0xFFF8CCDC, 0xFFF8CCC4) and writes segment indices, interpolated
   outputs (via binding property setters FUN_181f77fc / FUN_181f782a) and
   state flags into 0xFFF8CA44–0xFFF8CAAA and dictionary
   0x3C12A838–0x3C12A84C. It has exactly two callers: the refresh function
   FUN_181efdfc and FUN_181f857c (a 4-call evaluator group invoked from
   sys_ctrl state 6). **The producers of CD44/CC5A remain unisolated**
   (§8).

---

## 1. The dispatcher, dual-verified (FUN_181f7fc4, FUN_181f816c)

Stage E §8 described the dispatcher from the decompiler only and flagged
it single-method. This pass re-derived it from the raw listing
(`out/listing_disp.txt`, ListingDump = method 2):

- Per iteration: service call FUN_180b9bba(0x10) at 0x181F7FC8.
- Receive: `FUN_180bc5e8(queueHandleAddr=0xFFF8CF28, msgAddr=0xFFF8CF40,
  size=4, timeout=0x3E8)` at 0x181F7FD2–0x181F7FE0 — the 1000 is the
  instruction `movi20 #0x3e8,r1`. Return byte 0 → iteration ends
  (0x181F7FF6 `tst`/`bf`). **[FACT]**
- Dispatch: `idx = *(int*)0xFFF8CF40`; `handler = *(0x3C12EC70 + idx*4)`
  (0x181F7FFE–0x181F800A, `shll2` = ×4). No bounds check before the table
  read. NULL → `FUN_181f86cc(idx)` (0x181F8026–0x181F802C, idx in r4);
  non-NULL → `jsr @handler` with no argument setup (0x181F8010–0x181F8020).
  **[FACT]**
- Stats (only reached after a dispatch): bound `cmp/ge` against 12 at
  0x181F8048–0x181F8050; entry = 0xFFF8C688 + idx*16 (`shll2` twice);
  max at +4 (compare/store 0x181F8056–0x181F8082), min at +8
  (0x181F8088–0x181F80B6), count short at +2 incremented
  (0x181F80B8–0x181F80E0), running average float at +0xC recomputed with
  the 2^32/2^31 wrap-correction constants from cells 0x181F8200/8204/8208
  (0x181F80E2–0x181F8160). **[FACT]** — matches stage E §8 exactly.
- Init FUN_181f816c (listing): queue create
  `FUN_180bc4b2(0xFFF8CF28, itemSize=4, length=5, storage=0xFFF8CF2C)` at
  0x181F816E–0x181F8178; then FUN_181f86ae(); ready-poll on FUN_181597c4
  with FUN_180b9bba(0x10) + FUN_180bc0e4(100); finally FUN_181f861c() at
  0x181F81A6–0x181F81A8. **[FACT]**

Pool of the module (raw reads, `out/derived_maps.txt`): handler table
0x181F81F4→0x3C12EC70; default handler 0x181F81F8→0x181F86CC; stats
0x181F81FC→0xFFF8C688; msg int 0x181F81E4→0xFFF8CF40; queue handle
0x181F81E8→0xFFF8CF28; queue storage 0x181F820C→0xFFF8CF2C.

## 2. TARGET 1 — the handler table has no registration sites

Four independent searches, all negative:

1. **Literal scan (whole image, BE words).** 0x3C12EC70 occurs once (cell
   0x181F81F4, the dispatcher's). Individual slot addresses
   0x3C12EC70+4i: zero occurrences. Vicinity bases 0x3C12EC00–0x3C12EC10:
   zero occurrences (the lowest referenced field of the object is EC14).
   The queue handle 0xFFF8CF28, msg int 0xFFF8CF40 and queue storage
   0xFFF8CF2C likewise occur only in the module's own pool — so external
   code cannot even name the queue; posting goes through the module API
   (§3). **[FACT]**
2. **Function-address scan (whole image).** Every address in
   0x181F6800–0x181F9200 that appears as a data word was enumerated
   (55 addresses). The state machine's helper family
   (0x181F8238–0x181F85E2) appears **nowhere** as data — no flash table
   holds them, so no ROM template / descriptor lists them as handlers.
   The only module functions in any data table are the five binding
   providers in the module descriptor (next item) and ordinary pool
   cells. **[FACT]**
3. **Module descriptor 0x183B49C4–0x183B4A8C (raw dump).** Contents:
   config bytes 0x01010101 / 0x01010100; provider pointers FUN_181f8612,
   FUN_181f861c, FUN_181f862a, FUN_181f86ac, FUN_181f86a2; flags word
   0x20000000; a log template string `"FFsy s0000.log"` (fixed-width 'F'
   field); dictionary field 0x3C12ED02; RAM pointers 0xFFF8D17C,
   0xFFF8D1A0, 0xFFF8D1B8, 0xFFF8CF4C; terminator 0xFFFFFFFF. The five
   providers are computed-property providers for the object's fields
   (FUN_181f861c is also called at the end of task init and calls
   FUN_180c0444(0,0); FUN_181f862a is the timer-alignment provider of
   §5) — **not** message handlers. RangeRefs over 0x183B4800–0x183B4B00
   returned no Ghidra references at all: the region is consumed through
   an indirect engine path that does not materialize slot addresses.
   **[FACT]**
4. **Stage-C descriptor table scan.** No word in 0x3C12EC00–0x3C12ED00
   anywhere in the 0x35C-entry table at 0x182B04D4; stage D's
   field-binding directory (0x182B5E40) maps bus fields to field-store
   offsets and contains no dictionary addresses at all. **[FACT]**

The only population path not excluded is a runtime write through a
computed object pointer inside the dictionary engine (the same wall as
stages B/C/E) — but unlike the binding providers, for which descriptor
evidence exists, **no evidence of any handler registration exists in
this build**, and the fallback state machine (§4) is a complete,
self-sufficient consumer of every class the rest of the firmware posts
(§3). [INF] The table is an extension point the Clarinox framework
provides; in BINF0479 it stays NULL and FUN_181f86cc is the de-facto
handler for all classes.

## 3. The post side: stubs and the post API

**Post API FUN_181f7694(int *msg)** (294 B; decompile `out/decomp1/`,
pool resolved in `out/derived_maps.txt`): **[FACT]**

- FUN_180bc22a() (engine lock); queue handle = FUN_181f8168() (4-byte
  getter beside the init function); occupancy byte =
  FUN_180bc602(handle); max-occupancy tracker at 0xFFF8C748 updated.
- If `msg[0] == 8`: under dictionary brackets (FUN_180bc05a/06e) it
  memcpy's the 0xC0-byte stats table (12 × 0x10) from 0xFFF8C688 to
  0xFFF840C8, copies the max-occupancy byte to 0xFFF84188, resets all 12
  stats entries (count 0, +2 0, avg 0, max 0, min 0xFFFFFFFF) and the
  tracker — and does **not** queue the message.
- Else: posted-count short at stats+0 for the class (only class < 12)
  incremented; if occupancy < 5 (the queue length from init), the
  message is sent: `FUN_180bc558(handle, msg, 4)`.
- FUN_180bc234() (unlock).

**Stub→class map [FACT]** (each stub: `local[0] = class;
FUN_181f7694(local)`, decompiles in `out/decomp2/`):

| stub | class | stub | class |
|---|---|---|---|
| FUN_181f7500 | 0 | FUN_181f75b4 | 10 |
| FUN_181f7514 | 1 | FUN_181f766c | 11 |
| FUN_181f7528 | 2 | FUN_181f7680 | 12 |
| FUN_181f753c | 3 | FUN_181f75de | 13 |
| FUN_181f7550 | 4 | FUN_181f761a | 14 |
| FUN_181f7564 | 5 | FUN_181f75f2 | 15 |
| FUN_181f7578 | 6 | FUN_181f762e | 16 |
| FUN_181f758c | 7 | FUN_181f7642 | 17 |
| FUN_181f75a0 | 8 | FUN_181f7656 | 18 |
| FUN_181f7606 | 9 | FUN_181f75c8 | 19 |

So 20 classes exist on the post side; the dispatcher's stats cover
classes 0–11; the fallback state machine explicitly tests classes
1, 2, 6, 7, 12 (§4). Posters are image-wide (pool-cell users of the
stubs), e.g. class 1 is posted from the 0x180EBxxx supervisor region,
classes 6/14/15/16/17/18 from the 0x181ABxxx–0x181ACxxx subsystem.
**[FACT]** (users in `out/usersG1.txt`, `out/usersG2.txt` and the
data-word scan.)

## 4. The de-facto handler: FUN_181f86cc state machine

FUN_181f86cc(int class) — 1198 B body (Ghidra; body is fragmented, refs
attributed up to 0x181F8C5C). Decompile `out/decomp1/decomp_181f86cc.c`;
all pool cells resolved raw (`out/derived_maps.txt`). **[FACT]** unless
marked.

**State variable:** dictionary byte **0x3C12EC68** — the field
immediately below the handler table in the same object (object fields
EC14–EC6C are the ones stage E §6 found the zone binding module
binding). Three pool cells (0x181F87EC, 0x181F8A2C, 0x181F8C5C) all
resolve to EC68 (read + next-state writes). The only other consumer is
FUN_1816c0d6 (checks EC68 == 9 plus the type-word masks, then
FUN_1816c198(0x78)).

**Entry actions:** if state ∉ {0,1,5}: `v = FUN_1815d64c(class)`;
0xFFF8CF4B := v; FUN_181f7c2c() (adds FUN_181f7b1c()'s result into the
short at 0xFFF84236, bracketed memcpy); FUN_180bb6e0(). Then, under
dictionary brackets: shadow copy 0xFFF84230 := state. Then the
field-store identification type word is read via the stage-C getter
FUN_1815927c(offset 1, buf, 2, 1) — the same word/masks (0x7C00, bit
0x20) as stages C–E.

**Predicates** (all decompiled, `out/decomp2/`):
- P5 = FUN_181f823e: RAM byte 0xFFF830AE == 5 (bracketed read).
- P3a = FUN_181f8280: RAM byte 0xFFF830AD == 3.
- P3b = FUN_181f82a4: FUN_1815da86() == 3.
- PB = FUN_181f82c0: binding check FUN_180bc460(0x3C0D8EFC) == 0 — a
  *different* dictionary object (0x3C0D8xxx) the machine coordinates
  with; FUN_181f8448 also operates on it (FUN_180bc42a(0x3C0D8EFC),
  byte 0x3C0D8EF8).
- PD = FUN_181f82da: copies RAM byte 0xFFF82044 into dict field
  0x3C12ECC0, returns "any of ECC0 / 0xFFF83DB0 / 0xFFF83DB1 set".
- PA = FUN_181abdf4 (in the 0x181ABxxx subsystem; not decompiled
  further).

**Transitions** (decompiler-derived; `state :=` writes EC68):
- **1**: FUN_1816bf7e(); FUN_1816bfe2(); **FUN_181f8340()** (the §5
  registration sequence); → 2.
- **2** (hub): P5 → FUN_181f85e2(), → 10. P3a → FUN_181f8544()
  (= FUN_181f5d08 + FUN_180c4fcc + FUN_181f4e60), → 6. class 1 →
  FUN_181f8336() (= FUN_181f4308()), → 5. PD → FUN_181f85e2(), → 4.
  PB false → FUN_181f8448(). PB true → PA true → stay 3-path (state :=
  3); PA false → FUN_181f8238() (6-byte getter) true → FUN_181f84fc();
  false → class 6 → **FUN_181f8592()**, → 2; class 7 →
  **FUN_181f85c0()**, → 2; else → 2.
- **3**: P5 → FUN_181f85e2(), → 10. class 1 → FUN_181f8336(), → 5.
  PA → stay 3. else FUN_181f84fc(), → 2.
- **4**: class 1 → FUN_181f8336(), → 5. PD → stay 4. else
  FUN_181f84fc(), → 2.
- **5**: class 1 → FUN_181f8336(), stay 5. class 2 → FUN_181f84fc(),
  → 2. else stay 5.
- **6**: P5 → FUN_181f85e2(), → 10. P3b → FUN_181f84fc(), → 2.
  FUN_181f8280() → stay 6. Else, gated by FUN_181f8324() and the type
  word (bit 0x20 set, class-of-device ≠ 0x800): if the type condition
  fails → FUN_181f8556() (= FUN_181f5d08 + FUN_181f026e + FUN_181f4e60),
  set property CF46 := 120 (FUN_181f8568(0x78)), → 7. Otherwise set
  CF46 := 80 (FUN_181f8568(0x50)), → 9, and if the type condition
  holds also run **FUN_181f857c()** — the evaluator group
  FUN_181f062c + FUN_181f063c + **FUN_180c15d2** + FUN_181f4e60 (§6).
- **7**: P5 → FUN_181f85e2(), → 10. P3b → FUN_181f84fc(), → 2.
  class 12 → FUN_1816c03e(), → 8. else stay 7.
- **8**: P5 → FUN_181f85e2(), → 10. P3b → FUN_181f84fc(), → 2.
  FUN_1816bf24() → stay 8. else FUN_181f84fc(), → 2.
- **9**: P5 → FUN_181f85e2(), → 10. P3b → FUN_181f84fc(), → 2.
  class 12 → FUN_181f84fc(), → 2. else stay 9.
- **10**: P5 → stay 10. else FUN_181f84fc(), → 2.
- **default** (state 0 or >10): state := (FUN_181f8264() != 0), where
  FUN_181f8264 returns RAM byte 0xFFF82077.

**Exit action:** under brackets, byte 0xFFF841F4 := (state ∈ {6,7,8,9})
— an "active" flag for the machine's run states. [INF] States 6–9 are
the operating states, 10 the fault/reset sink reached via FUN_181f85e2
(a teardown sequence: two property gets, FUN_181f026e, conditional
FUN_181f48b8 on dict byte 0x3C12ECC0, FUN_181f4e60, FUN_181f69bc), 5 a
wait state entered on class 1, 2 the decision hub, 1 the
(re)registration state.

**Recurring action FUN_181f84fc** (72 B, 12 entry refs): runs five
binding setters (FUN_181f6fee, FUN_181f062c, FUN_181f063c, FUN_181f064c,
FUN_181f065c), reads the type word, and if its class is 0x4000 also
runs FUN_180c3f98 + FUN_180c3f90; then **posts class 6** (stub
FUN_181f7578). [FACT] — i.e. most state exits re-trigger evaluation via
a fresh class-6 message.

**FUN_181f8592** (state 2 / class 6): property get CF48;
FUN_181f5d08(); **FUN_181efdfc()** (the decision-module refresh of
stage E); **FUN_181f7050()**; FUN_1815dcee(); FUN_181f4e60(); set
property CF49 := 15. FUN_181f7050 (1030 B) is an 8-channel
elapsed-time/rate computation over per-zone arrays (timestamp deltas
with the same 2^32/2^31 wrap correction, per-channel state bytes,
float accumulators) that publishes four result arrays (8 floats,
8 bytes, 8 floats, 8 floats) under dictionary brackets. [FACT]

**FUN_181f85c0** (state 2 / class 7): property get CF49;
FUN_181f015a(); set property CF48 := 45; FUN_181f69bc(). [FACT]

## 5. The registration machinery that exists (engine properties)

The engine primitives, identified by their call pattern across ~50 /
~150 call sites image-wide (users in `out/usersG2.txt`): **[FACT]**
- FUN_1809fa76(idSlotPtr, 1, flag, callback) — register a callback
  against a property; the assigned property id is stored at *idSlotPtr.
- FUN_1809fde2(id, value, flag) — set a property value.
- FUN_1809fec0(id) — get a property value (used by FUN_181f8592,
  FUN_181f85c0, FUN_181f85e2, FUN_181f862a).

**FUN_181f86ae** (called from task init FUN_181f816c): registers
property id-slot 0xFFF8CF44 with callback FUN_181f7500 (class-0 stub),
then sets it: FUN_1809fde2(*CF44, 1, 1). **[FACT]**

**FUN_181f8340** (called from state 1): chained registrations, each
gated on the previous one's success: **[FACT]**
- id-slot 0xFFF8CF45 ← callback FUN_181f7550 (class 4), flag 1
- id-slot 0xFFF8CF46 ← callback FUN_181f7680 (class 12), flag 0
- id-slot 0xFFF8CF47 ← callback FUN_181f7564 (class 5), flag 0
- id-slot 0xFFF8CF48 ← callback FUN_181f7578 (class 6), flag 0
- id-slot 0xFFF8CF49 ← callback FUN_181f758c (class 7), flag 0
- if all succeeded: id-slot 0xFFF8CF4A ← callback FUN_181f75a0
  (class 8), flag 1
Then: set CF45 := 10, CF48 := 30, CF4A := 300; post class 5.

**Reprogramming by the state machine [FACT]:** CF46 := 120 or 80
(FUN_181f8568, state 6); CF48 := 45 (FUN_181f85c0); CF49 := 15
(FUN_181f8592); CF47 := 60 − (x mod 60), clamped ≥ 30, where x is
byte 0 of a 7-byte block memcpy'd from RAM 0xFFF8207A (an RTC-shaped
block beside stage C's classify byte 0xFFF82089) — computed by
**FUN_181f862a**, one of the module-descriptor providers (§2).
[INF] The seven properties CF44–CF4A are the supervision timers: when
a timer property is set/expires, its callback posts the associated
class into sys_ctrl, and the state machine runs the corresponding
evaluation and reprograms the next period (10 / 30→45 / 15 / 300 /
80 vs 120 / seconds-to-minute-boundary 30–60). Units (s vs ticks) are
not proven.

This — not the dispatcher's table — is the runtime-registration
surface that matters for the sys_ctrl object, and it is fully static:
every registration site is enumerated above.

## 6. TARGET 2 — FUN_180c15d2 exhaustive

**Identity [FACT]:** entry 0x180C15D2, body 4610 B (Ghidra). Exactly
two callers, both computed calls through pool cells (UsersOf,
`out/usersG1.txt`):
- FUN_181efdfc (the decision-module refresh) at 0x181F0046 via cell
  0x181F0128 — matches stage E's decompile of the refresh.
- **FUN_181f857c** at 0x181F8588 via cell 0x181F878C — a 22-byte
  evaluator group in the sys_ctrl cluster: FUN_181f062c();
  FUN_181f063c(); FUN_180c15d2(); FUN_181f4e60(). Invoked from
  FUN_181f86cc state 6 (§4). So FUN_180c15d2 runs both in the periodic
  refresh and on the sys_ctrl state-6 path.

**Method:** full decompile (`out/decomp1/decomp_180c15d2.c`, 522 lines)
+ raw resolution of all 191 pool cells it references
(`out/derived_maps.txt`). Every module-block access below is therefore
dual-sourced (decompiler operand + raw cell value).

**Reads of the decision module's headline variables [FACT]:**
- Demand float **0xFFF8CD44**: cells 0x180C17D4 (`fStack_44 =
  *DAT_180c17d4`) and 0x180C2AD0 (compared against dict field
  0x3C12A84C). **No store to CD44 anywhere in the body.**
- Index/count byte **0xFFF8CC5A**: cells 0x180C17E0, 0x180C1D54,
  0x180C1EE4, 0x180C21E0, 0x180C24CC, 0x180C27B0, 0x180C2A8C — used as
  table index+1 (`table[CC5A−1]`), as breakpoint count for the table
  copies, and as loop bound. **No store to CC5A anywhere in the body.**
- Threshold tables: **0xFFF8CCC4** (cell 0x180C1EE8) is only one of
  three breakpoint arrays the function interpolates over:
  0xFFF8CC34 (count at 0xFFF8CBFA), 0xFFF8CCDC (parallel value array
  0xFFF8CC94), 0xFFF8CCC4 (parallel value array 0xFFF8CC64). Table
  selection: mode byte 0xFFF8CD7D == 1 → CCDC set, == 2 → CCC4 set
  (stage E's CCC4 is the mode-2 table).
- Also read: type word 0xFFF8CC52 (0x7C00 classes 0x400 / 0x4000
  tested — the stage-C/D identification word, module copy), mode byte
  0xFFF8CD7D, source-state byte 0xFFF8CD4A (stage E's arbitration
  output, values 0–3 adjust segment choice), flags 0xFFF8CD71–CD7C,
  0xFFF8CBxx state bytes, segment state in 0xFFF8CAxx.

**Writes into the module block [FACT]** (all via resolved cells):
segment endpoint copies 0xFFF8CA50 / 0xFFF8CA54, segment indices
0xFFF8CA59 / 0xFFF8CA5A (interp 1) and 0xFFF8CA6C / 0xFFF8CA70,
0xFFF8CA75 / 0xFFF8CA76 (interp 2); selected index 0xFFF8CA80;
selected breakpoint index 0xFFF8CA94; state bytes 0xFFF8CA44 /
0xFFF8CA45 (zeroed on one path); output bool 0xFFF8CAA9; state flag
0xFFF8CAAA; flag 0xFFF8CD7B (set 0/1); flag 0xFFF8CD7C (set 1); tail
sum 0xFFF8CD8C := (float at 0xFFF874A8) + (float at 0xFFF874AC).
Dictionary writes: max-demand tracker 0x3C12A844 (raised to the running
max of the adjusted demand; reset to 0.0 on the idle path), segment
mirrors 0x3C12A838 / 0x3C12A839 and 0x3C12A83A / 0x3C12A83B, flag
0x3C12A848, and 0x3C12A84C := (segment endpoint)/2.0. Scratch writes
to 0xFFF87494–0xFFF874B0 (shared evaluator scratch area).

**What it computes [FACT, structure from the decompile]:**
1. Loads the default breakpoint table from flash 0x182C3130 (4 floats
   + 2 dwords) into locals; reads CD44 into `fStack_44`; computes an
   adjusted demand `fStack_48` (clamped against `table[CC5A−1]`, the
   running max in dict 0x3C12A844, and 0.0) under device-type/flag
   gates (type class 0x400 + FUN_181f7004()).
2. Interp 1: piecewise-linear over array 0xFFF8CC34 with input
   `fStack_48` — finds the segment, writes segment indices/values,
   and drives a property through the binding accessor pair
   FUN_181f77fc (set) / FUN_181f77f4 (get) with linear interpolation
   and clamping; on the idle branch it resets the same state to the
   table base point.
3. Table copy: the mode-selected breakpoint table (CCDC or CCC4) and
   its parallel value array are copied into local arrays.
4. Interp 2: piecewise-linear over the selected table with input
   `fStack_44` (raw CD44) — segment search (with source-state
   0xFFF8CD4A adjustments for states 1/2/3), interpolated output via
   the second accessor pair FUN_181f782a (set) / FUN_181f7822 (get),
   result mirrored to 0xFFF874AC; a special device class (type
   0x4000 + FUN_181abdf4()) delegates the whole interp to
   FUN_180c3e5c (after FUN_180d2728(0)).
5. Tail: FUN_180c2b14(); a change-propagation block (property
   get/set pairs FUN_181f77f4, FUN_180868f4, FUN_18086950, FUN_18086942,
   FUN_18086948, FUN_181f77fc, FUN_1808699e, FUN_180869a4) gated on
   0xFFF8CBDC; a near-zero-demand check (|selected − current| <
   0.001) that can raise flag 0xFFF8CD7C; demand-vs-limit bookkeeping
   against dict 0x3C12A84C (recomputed as endpoint/2.0 for type class
   0x400); direct calls to the sibling sub-evaluators FUN_180c2b76,
   FUN_180c3012, FUN_180c3232, FUN_180c3552, FUN_180c35dc,
   FUN_180c32f2, FUN_180c3418 and FUN_180c3bee(locals); final writes
   0xFFF8CD8C (sum) and 0xFFF8CAA9 (bool = "interp-1 active &&
   0xFFF8CAAA clear", inverted).

**Callees [FACT]:** the binding accessor wrappers FUN_181f77fc /
FUN_181f77f4 / FUN_181f782a / FUN_181f7822 (the module cluster's
heavily-referenced 8–36 B utilities, 40–55 entry refs each), binding
setters FUN_181f062c / FUN_181f063c / FUN_181f064c / FUN_181f065c,
FUN_181f7004, FUN_181abdf4, FUN_180c15a6 (reset helper immediately
before it), FUN_180c36c4, FUN_180c3814, FUN_180c3e5c, FUN_180d2728,
FUN_180d3fc0, FUN_180d4024, the 0x180869xx property family, and the
direct tail calls listed above.

**Verdict [FACT]:** FUN_180c15d2 is a **consumer** of the decision
module's inputs, not their producer. It reads the demand float
0xFFF8CD44 and the index/count byte 0xFFF8CC5A and turns them, via
breakpoint-table interpolation, into segment indices, interpolated
property outputs and state flags. Stage E's suspicion is therefore
resolved negatively for production and positively for role: this is
the module's interpolation core, one level *below* the refresh
function. Whoever writes CD44/CC5A is a different evaluator — still
unisolated (§8).

## 7. Dual-verification log

| Claim | Method 1 | Method 2 |
|---|---|---|
| 1000 ms timeout, 4-byte msg, table 0x3C12EC70, NULL→FUN_181f86cc, stats <12 / stride 0x10 / +2,+4,+8,+0xC | stage E decompile | raw listing this pass (§1) |
| Table base & slots occur nowhere else | Ghidra reference index (RangeRefs/UsersOf) | whole-image BE word scan (python) |
| No handler array in any descriptor | raw dump of 0x183B49C4 record | function-address data-word scan (55 addrs) + stage-C table scan |
| Stub→class map | decompile of all 20 stubs | stub pool-cell users + FUN_181f7694's class-8 special case matching stub FUN_181f75a0 |
| FUN_180c15d2 reads (not writes) CD44/CC5A | decompile operand analysis | raw resolution of all 191 pool cells |
| FUN_180c15d2 callers = exactly 2 | UsersOf two-level (Ghidra refs) | whole-image data-word scan: 0x180C15D2 occurs only in cells 0x181F0128 / 0x181F878C |
| FUN_181f8340 registrations | decompile | pool resolution: callbacks are the class-4/12/5/6/7/8 stubs, id-slots are consecutive CF45–CF4A |

## 8. Not isolated / still open

- **Producers of the demand float 0xFFF8CD44 and index byte
  0xFFF8CC5A.** FUN_180c15d2 only reads them; the refresh function
  FUN_181efdfc calls ~25 evaluators — the producer is among the
  not-yet-decompiled siblings (candidates from stage E §12 and this
  pass: FUN_181f4e60, FUN_181f5d08, FUN_181f026e, FUN_181f015a,
  FUN_181f69bc, the FUN_180c3xxx family).
- **Semantics of classes 0–19 and of states 1–10** beyond the
  structural map of §4: no string names exist for them in the image;
  the timer-period reading of the CF44–CF4A property values (10, 15,
  30→45, 80/120, 300, 30–60) is inference, units unproven.
- **FUN_181abdf4** (predicate PA) and the 0x3C0D8xxx object
  (0x3C0D8EFC / 0x3C0D8EF8) the state machine coordinates with —
  identified, not analyzed.
- **The dictionary-engine instantiation path** for the object at
  0x3C12ECxx: the module descriptor (0x183B49C4) has no Ghidra-visible
  consumer (RangeRefs empty), so how the engine walks it — and
  whether it could ever write the handler table — remains the same
  runtime wall as stages B/C/E. No evidence it writes handlers.
- FUN_181f7050's four published arrays' dictionary destinations
  (bracketed copies — destinations are engine-side, not literal).
- Stage E's remaining gaps are unaffected: the 0305/0605/060D payload
  writers, the 0x78 byte at 0305[11], the CFM computation, numeric
  lockout/defrost defaults, and gap G8 (partial 0605 stages) stay
  open. (Note: the constant 0x78 now also appears as a *property
  value* — FUN_181f8568(0x78) sets property CF46 := 120 in state 6,
  and FUN_1816c0d6 calls FUN_1816c198(0x78) when EC68 == 9 — a
  coincidence of value, not evidence about 0305[11].)

## Intermediates

`firmware-re/stageG/`: `scripts/` (DecompileScript, ListingDump,
UsersOf copied from stage E; RangeRefs, ClusterInv new), `out/`
(usersG1.txt, usersG2.txt, cluster.txt, rangerefs.txt [empty —
negative result], listing_disp.txt, derived_maps.txt, decomp1/ —
FUN_180c15d2, FUN_181f86cc, FUN_181f857c, FUN_181f7694, FUN_181f8612,
FUN_181f861c, FUN_181f862a, FUN_181f86a2, FUN_181f86ae, FUN_1816c0d6;
decomp2/ — all 20 post stubs, FUN_181f7050, FUN_181f7c80, FUN_181f7c2c
and the 16 state-machine helpers), `runG*.sh`, `runG*.log` (all
EXIT=0).
