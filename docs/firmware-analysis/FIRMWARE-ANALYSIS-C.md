# FIRMWARE-ANALYSIS-C.md — ICP Ion BINF0479 firmware, RE stage C

Date: 2026-10-30. Desk work on files only; nothing was flashed or written to
any device. Continues `FIRMWARE-ANALYSIS.md` (stage A) and
`FIRMWARE-ANALYSIS-B.md` (stage B). Work was done in the saved Ghidra
project **copied** to `firmware-re/stageC/proj/` (the stage-B original at
`firmware-re/stageB/proj/` is untouched); scripts and all intermediate
output are preserved in `firmware-re/stageC/` (`scripts/`, `out*/`).

Labels: **[FACT]** = measured/decompiled/disassembled directly this pass.
**[INF]** = inference, with reasoning shown. Negatives state the space
searched.

**Mission:** find the *writer* of field-store field **0xC4** (SAM-present,
`'Z'` = present) and the conditional that can skip the write.

---

## 0. Headline results

1. **The writer is found [FACT].** Exactly one instruction in the image
   writes field 0xC4 with the presence pattern: the setter-B call at
   **0x18147CBA** inside **FUN_18147c58**, a dedicated "SAM presence
   refresh" routine. Its twin **FUN_18147b00** is the only writer of the
   variant field 0x23 (call at 0x18147C10). Both write one byte: `0x5A`
   (`'Z'`) or `0x00`.
2. **The gate is found [FACT].** The `'Z'` value is produced only if a
   device-object binding check passes. The skipping branch is at
   **0x18147C6C** in FUN_18147c58 (`bf` after `tst r2,r2` at 0x18147C6A,
   testing the return of FUN_180bc460 called at 0x18147C66). The compared
   value's origin: the word stored in the SAM device record at
   data-space address **0x3C0D3EE4** is used as an object pointer, and
   the check reads the dword at **object + 0x38** (FUN_1817e7c6);
   `'Z'` is set **iff that dword is non-zero**. No application function
   in the image writes that record word or that object slot — they are
   managed by the Clarinox data-dictionary/binding engine (§5, §6).
3. **The full caller chain is mapped [FACT].** FUN_18147c58 runs only
   from state **0x17** of the SAM/B36 manager state machine
   FUN_1813f454 (call at 0x18140056), which is ticked only by the 1 s
   supervisor FUN_180ba20a (call at 0x180BA442), which is the body of a
   dedicated task thread FUN_180bb3a8. State 0x17 is reachable only from
   state 0x16's variant refresh (FUN_18147b00), through the classify
   branch at **0x18147BF0** (§4).
4. **Reachability verdict:** the gate operand is **not** a field-store
   field, **not** an ABCD bus table value, and **not** a stored config
   byte that any code on this path reads. It is an internal binding
   state of the Clarinox object engine, derived during device discovery.
   Nothing user-, menu-, or bus-reachable was found that writes it
   directly (§7). The one bus-visible footprint of the same state is the
   ABCD active-address bitmap (bits 0x92/0x94), which the refresh
   routines *clear* when the device is unbound — an output, not an input.

---

## 1. The field store and its setter twins (task item 1)

Stage B characterised the getter **FUN_1815927c** as
`get(offset, dest, len, hook_flag)`. Decompiling the whole implementation
cluster (38 functions, 0x18158C00–0x18159C00) shows the store is a **flat
byte array**; the "field index" of stages A/B is a **byte offset** into
it. Store parameters come from one shared literal-pool block, identical
in getter and both setters **[FACT]**:

- store base pointer cell 0x181593F4 → data-space **0x3C0E4A20**
- header/size cell 0x181593E0 → 0xFFF877DC (`[0]` = size, `[1]` = page size)
- mutex cell 0x181593E8 → 0xFFF8AD40; lock = FUN_180bc2d2, unlock = FUN_180bc36a
- copy primitives: memcpy = FUN_1823d404, memcmp = FUN_1823d3d8,
  memset = FUN_1823da24
- dirty-page bitmap cell 0x181593E4 → 0x3C0E6A20; timestamp via FUN_180bc150

Two write twins exist **[FACT]**:

| Function | Signature | Behaviour |
|---|---|---|
| **FUN_18159220** ("setter-A") | `(offset, src, len)` | lock → refuse if store-frozen byte ≠ 0 → **memset** (FUN_1823da24) into store → mark dirty pages (FUN_181591e4) → update timestamp (FUN_181591c8) |
| **FUN_181592e4** ("setter-B") | `(offset, src, len)` | lock → refuse if frozen → **memcmp** store vs src; only if different: memcpy into store, update timestamp, mark dirty pages inline |

Confirmation that both write the *same* store the getter reads: identical
base/header/mutex cells and identical bounds checks
(`offset < size`, `offset + len ≤ size`) in all three functions
**[FACT]**.

Call volumes **[FACT]**: setter-A's address occurs as a word **exactly
once** in the image (pool cell 0x18166574); its only call site is inside
FUN_181664da (§2.3). Setter-B's address occurs in 279 pool cells; 894
call expressions were extracted from the 347 distinct calling functions.

The store is **NVRAM-backed [FACT]**: the same cluster contains the page
engine — FUN_1815941c (background flush of dirty pages) and FUN_18159540
(page verify/repair) — so field bytes persist across power cycles, loaded
from NVRAM at boot. A field that discovery never sets keeps its stored
value (for 0xC4, the descriptor default is 0x00, §2.3).

---

## 2. Write sites for fields 0xC4 and 0x23 (task item 2)

### 2.1 Method

All 894 setter-B call expressions were extracted from decompiled callers
and their first arguments classified; all constant first arguments were
tabulated (399 distinct constants). Setter-A has a single call site,
analysed separately. Non-constant first arguments were reviewed
individually (§2.4).

### 2.2 The only semantic writers

**Field 0xC4 — one write site [FACT]:**

- Function **FUN_18147c58**, call instruction **0x18147CBA**
  (`jsr/n @r3 → FUN_181592e4` via pool cell 0x18147D04; offset materialised
  by `movi20 #0xc4` at 0x18147CB2).
- Arguments: `(0xC4, &local_byte, 1)`. Values written: **0x5A or 0x00**,
  conditions in §3.
- This is also the routine stage B's readers pair with: FUN_1806fe8c
  (SAM-present predicate) reads exactly this byte.

**Field 0x23 — one write site [FACT]:**

- Function **FUN_18147b00**, call instruction **0x18147C10**, arguments
  `(0x23, &local_byte, 1)`, values **0x5A or 0x00**, conditions in §3.

Neighbouring presence bytes for context **[FACT]**: field **0xC2** is
written by FUN_181423ba / FUN_18142762 `(0xC2, DAT_181428ac, 1)` and field
**0xC3** by FUN_18066c40 `(0xC3, DAT_18066e10, 1)` — the store holds a
small block of per-device presence bytes around 0xC2–0xC4; which physical
devices 0xC2/0xC3 belong to was not determined and is not needed here.

### 2.3 The descriptor-restore path can only clear 0xC4/0x23

FUN_181664da is a generic "restore field range from descriptor table"
dispatcher (table at flash 0x182B04D4, 0x35C entries × 0x18 B; lookup by
field-offset key). Per entry: if the entry's provider pointer (+0x10) is
NULL or the sentinel 0x182F6D10, it calls **setter-A (offset, 0, len)** —
a memset of 0; else it calls **setter-B (offset, provider_ptr, len)**.
The table *does* contain entries for offset 0x23 (#66) and 0xC4 (#181),
both len 1, provider = 0x182F6D1C — and **the byte at 0x182F6D1C is
0x00 [FACT]**. So through this path fields 0xC4/0x23 can only ever be
written **0x00**, never `'Z'`, regardless of which of its 29 calling
functions invokes it or with what key. (Which callers pass key 0xC4 was
not enumerated; it cannot matter for presence, only for clearing.)

### 2.4 Residual generic paths (honest caveat)

Two extracted setter-B calls take a non-constant, caller-supplied offset:
FUN_180a757a (`arg1 = param_1`, a pointer-typed parameter — a bounds-
checked no-op for any realistic pointer value) and FUN_181545bc
(`arg1 = *DAT_1815484c`, a descriptor-driven binding-engine move).
Neither shows any semantic connection to field 0xC4, and neither can
produce the `'Z'`/0x00 presence pattern paired with the 0xC4 readers.
They are recorded here so the "only writer" claim is scoped correctly:
**FUN_18147c58 is the only writer that writes 0xC4 as a presence flag**;
a pathological descriptor configuration driving the generic binding
engine onto offset 0xC4 cannot be excluded by static analysis alone, and
no evidence for one was found.

---

## 3. The writer routines, instruction-precise (task item 3, lower half)

### 3.1 FUN_18147c58 — SAM presence refresh (writes 0xC4)

Logic (instruction addresses from the listing dump,
`firmware-re/stageC/out9/listing_refresh.txt`):

```
local = 0
r0 = FUN_180bc460(record = 0x3C0D3EE4)        ; call @ 0x18147C66
tst r2,r2 @ 0x18147C6A ; bf 0x18147C8C @ 0x18147C6C   ; ← GATE (§5)
if (r0 == 0) {                                 ; object "bound"
    FUN_180bc42a(record)                       ; @ 0x18147C72 (result unused)
    bracket_begin(); memcpy(tmp, record_base 0x3C0D3ED4, 0x10); bracket_end()
    local = 'Z'                                ; mov #0x5a @ 0x18147C86
}
if (local == 'Z'                               ; cmp/eq 0x5a @ 0x18147C94, bt @ 0x18147C96
    || FUN_1809fd7e(*0xFFF8AAFF) != 0) {       ; call @ 0x18147CA0; bt @ 0x18147CAA (else exit @ 0x18147CE4, NO write)
    FUN_181592e4(0xC4, &local, 1)              ; call @ 0x18147CBA
    timestamp byte 0xFFF8377F = byte @ flash 0x182AE60D
    FUN_1813edd2(0x11)                         ; call @ 0x18147CD2 — post state 0x11
    if (local != 'Z') FUN_180c6988()           ; call @ 0x18147CE2 — clear bus bit 0x92
}
```

So the write happens in exactly two situations **[FACT]**:
- object bound → writes **'Z'**;
- object unbound *but* the device-table check FUN_1809fd7e succeeds →
  writes **0x00** and clears the SAM's bus-activity bit;
- object unbound *and* table check fails → **no write at all** (the byte
  keeps its previous/NVRAM value), no state post, no cleanup.

### 3.2 FUN_18147b00 — variant presence refresh (writes 0x23)

Structurally identical twin against the variant record
(base 0x3C0D3F08, handle word 0x3C0D3F18), with one extra decision after
its write-gate (same shape: registry call @ 0x18147B0E, `bf` @
0x18147B14; table check call @ 0x18147B48, exit `bt` @ 0x18147B52):

- if local == 'Z' → FUN_1813edd2(0x11) (call @ 0x18147B64);
- else → FUN_180c6978() (call @ 0x18147BD2 — clear bus bit **0x94**),
  then classify the byte at RAM **0xFFF82089** via FUN_1815e1ea
  (call @ 0x18147BE8; bit 0x02 → 1, else bit 0x08 → 2, else 0):
  - `cmp/eq #0x2` @ **0x18147BEE**, `bf` @ **0x18147BF0**:
    - classify **== 2** → FUN_180c6988() (clear bus bit **0x92**, call @
      0x18147BF4) and FUN_1813edd2(0x11) — **state 0x17 is NOT entered**;
    - classify **!= 2** → FUN_1813edd2(**0x17**) (call @ 0x18147C04) —
      the only post of state 0x17 in the image;
- then FUN_181592e4(0x23, &local, 1) (call @ 0x18147C10) and the
  timestamp byte 0xFFF8377E is updated.

In plain terms: state 0x16 asks "is the B36-form accessory bound?"; only
if the slot is *not* positively classified as the B36 form does the
machine go on to ask the SAM question in state 0x17. **[FACT for the
branches; INF for the "B36 form" naming of classify value 2 — see §8]**

### 3.3 The two checks used by both twins

- **FUN_180bc460(record_handle_addr)** — the binding check. Listing
  (0x180BC460): loads the word at the record's handle address
  (0x3C0D3EE4 for SAM), calls **FUN_1817e7c6** with it, returns
  `1` iff the result is 0 (`tst`/`movt` @ 0x180BC470–72).
  FUN_1817e7c6(obj) returns the **dword at obj + 0x38**, read under a
  lock pair, with a null-pointer assertion that logs a
  `C:\CING_Int\...` source path. Combined with the caller's branch
  (§3.1): **`'Z'` is written iff dword[obj + 0x38] ≠ 0**, where obj is
  the pointer stored in the SAM device record. Offset +0x38 is a slot of
  the Clarinox device object — the "bound/context" slot **[INF: role
  name; the address arithmetic and the branch are FACT]**.
- **FUN_1809fd7e(idx)** — the device-table check. Returns
  `FUN_1809ff4a(idx) == 0`. FUN_1809ff4a walks a RAM device table
  (base cell → DAT_180a0170, count cell → DAT_180a016c, 0xC-byte
  entries): returns the entry's short at +4 directly, or accumulates
  along a linked list (next index at +0xB) in the flagged case. The
  index byte is the module-global at RAM **0xFFF8AAFF**, read by both
  twins and by several state-machine states. This check never produces
  `'Z'`; it only enables the write-0x00-and-clean-up path.

### 3.4 The clean-up helpers are bus-bitmap clears

FUN_180c6988 → `FUN_180a71cc(0x92)`; FUN_180c6978 → `FUN_180a71cc(0x94)`.
FUN_180a71cc clears bit (addr & 7) of byte (addr >> 3) in a bitmap
(base cell DAT_180a74d0) — i.e. "device at ABCD address 0x92 / 0x94 is
no longer active" **[FACT]**. These are outputs of the refresh, driven
by it, not inputs to the gate.

---

## 4. Caller chain upward (task item 3, upper half)

### 4.1 The state machine FUN_1813f454

Both refresh routines have exactly **one caller each [FACT]** — the
state machine **FUN_1813f454** (2,774 B), a switch on the state byte at
RAM **0xFFF8AB3D**:

- case **0x16**: `FUN_18147b00()` called unconditionally at the end of
  the case (instruction **0x1813FF6C**, via pool cell 0x18140010);
- case **0x17**: `FUN_18147c58()` called unconditionally (instruction
  **0x18140056**, via pool cell 0x18140254).

State transitions are posted exclusively through **FUN_1813edd2(n)**,
which writes n to the state byte 0xFFF8AB3D and sets the "init arm" byte
**0xFFF8AB73** = 1; **FUN_1813ede0** clears the arm byte (each state's
init block runs once per entry, guarded by `*0xFFF8AB73 != 0`). The
state byte has exactly three pool cells in the image — FUN_1813edd2's,
the switch's, and an epilogue shadow copy — so **FUN_1813edd2 is the
only writer of the state byte [FACT]**.

A completion dispatcher, **FUN_18140580** (called at the end of most
states), maps an async result code to the next state
(0→goto 1, 1→goto 0x18, 2→goto 7, 4→goto 0x11, 5→goto 0x14, …).

Relevant postings of the refresh states **[FACT, extracted from all 18
goto-calling functions]**:

- **goto(0x17)**: posted *only* by FUN_18147b00 (§3.2). No other path
  into the SAM refresh exists.
- **goto(0x16)**: posted by the machine itself in case 9 (under a
  device-table check), and by the identification-result handlers
  FUN_18146712, FUN_181470f0, FUN_18147250, FUN_18147540. These handlers
  share a signature pattern: they consume a device identification
  result and branch on the **device-type word masked with 0x7C00** —
  values **0x4400 / 0x4800** route to other states (0x0C / 0x10), and
  the remaining types fall through to **goto(0x16)** (e.g.
  FUN_181470f0 @ its PTR_FUN_18147244 call; FUN_18147540 likewise;
  FUN_18147250 else-branch). The same 0x7C00 mask and the same two
  constants appear in the supervisor (§4.2) reading the type word at
  field-store offset 1. Bits 10–14 of the identification word are
  therefore the device-class field the discovery flow routes on
  **[FACT for the mask/constants/branches; INF for "device class" as
  the semantic name]**.
- The machine's own case 0 is the entry/init state (writes defaults via
  setter-B at offsets 0x3D, 6, 0x14, 0x6EC and descriptor-restores 11
  keys via FUN_181664da: 0x471, 0x494, 0x4B7, 0x4DA, 0x4FD, 0x520,
  0x543, 0x566, 0x589, 0x590, 0x598). Case 0x14 is the sequence's
  completion latch: it writes 'Z' to field offset **5** via setter-B
  and performs a binding-record operation FUN_180a8da2(0x42, 3, 0x0D,
  buf @ 0x3C0D41D0).

### 4.2 The supervisor FUN_180ba20a and the task thread

FUN_1813f454 has exactly **one caller [FACT]**: the supervisor
**FUN_180ba20a** (call instruction **0x180BA442**, via pool cell
0x180BA658). FUN_180ba20a is a periodic supervisor (it ends with a
1000 ms delay call) whose body is the loop function of a dedicated task
thread **FUN_180bb3a8** (`FUN_180ba14c()` once, then
`FUN_180ba20a()` forever; pool cells 0x180BB580/0x180BB584) **[FACT]**.

The state-machine call inside the supervisor is nested under all of
**[FACT, from the decompilation]**:

1. mode byte at data-space **0x3C12A700** == 0;
2. active flag **0x3C12A6F9** != 0;
3. session pre-check **FUN_180b9ecc(*0x3C12A6F8-ish args)** returns 0;
4. latch field (store offset **5**, read via the getter) != 'Z' — if it
   *is* 'Z', the supervisor instead calls FUN_18149906 (the "already
   registered" path) and never ticks the machine.

The latch is the same field case 0x14 sets: once the manager sequence
has run to completion, the supervisor stops driving it. The supervisor's
state bytes live in one data-dictionary block, 0x3C12A6F8–0x3C12A700.

---

## 5. The gate (task item 3, the conditional itself)

**Operative gate for the `'Z'` write — precisely:**

> **FUN_18147c58, instruction 0x18147C6C: `bf 0x18147C8C`**, testing
> (via `tst r2,r2` at 0x18147C6A) the return of **FUN_180bc460** called
> at **0x18147C66** with argument = the SAM device record handle address
> **0x3C0D3EE4**. If FUN_180bc460 returns non-zero, the branch skips the
> block at 0x18147C6E–0x18147C88 that materialises `'Z'`
> (`mov #0x5a,r7` at 0x18147C86).
>
> FUN_180bc460 returns non-zero **iff the dword at (object + 0x38) is
> zero**, where *object* is the word stored at 0x3C0D3EE4, and the dword
> is read by FUN_1817e7c6 (called at 0x180BC46A). Equivalently:
> **field 0xC4 becomes 'Z' iff dword[SAM_device_object + 0x38] ≠ 0.**

**Origin of the compared value [FACT for the chain of reads; INF for
the role names]:** a slot inside a Clarinox device-object record in the
0x3C data-dictionary space. The SAM device record itself occupies
0x3C0D3ED4–0x3C0D3EE4+ (16 bytes are memcpy'd out of its base on the
bound path). This value is **not** computed in FUN_18147c58, **not** a
compile-time constant, **not** a field-store field, and **not** copied
from any ABCD frame by any code on this path — it is state owned by the
binding/registry engine (the same engine whose accessor brackets
FUN_180bc05a/FUN_180bc06e wrap every dictionary access in this module).

**Pre-emption levels above the gate** (each can prevent the write from
ever being considered, in walk-up order):

1. **0x18147CAA `bt`** — if the device-table check also fails, the
   routine exits without writing even 0x00 (§3.1).
2. **0x18147BF0 `bf`** (in FUN_18147b00, on classify == 2) — state 0x17
   is never posted; the SAM refresh never runs (§3.2). The classify
   operand is the byte at RAM 0xFFF82089 (bit 0x08), a bound variable
   whose writer was not isolated this pass (§6).
3. **State reachability** — states 0x16/0x17 are entered only via the
   posted transitions of §4.1; the identification handlers route whole
   device classes (type word & 0x7C00 == 0x4400 / 0x4800) away from
   goto(0x16).
4. **Supervisor gating** (§4.2) — mode byte, active flag, session
   pre-check, and the offset-5 completion latch decide whether the
   machine is ticked at all.

---

## 6. Who writes the gate operand? (the registrar question)

Searched explicitly **[FACT negatives]**:

- The SAM record handle word **0x3C0D3EE4** is referenced by exactly
  five pool cells in the image: FUN_18147c58 (0x18147D18), FUN_1814aace
  (0x1814ABD4), FUN_18116d4c (0x18116F48), a static descriptor table at
  0x182B70EC, and one cell (0x18099C00) with no code references. The
  three functions all **read** it (binding check + 16-byte record copy —
  FUN_1814aace is a status consumer that also reads fields 0xC4/0xC2;
  FUN_18116d4c has the same consumer shape). **No function writes it.**
- No application-level assignment to the object +0x38 slot appears
  anywhere on the analysed path; the slot is reached only through the
  engine accessors FUN_180bc460 / FUN_180bc42a / FUN_1817e7c6 /
  FUN_1817e2e0.
- The writers of the two auxiliary bound bytes — device index
  0xFFF8AAFF (28 pool cells across the module) and classify byte
  0xFFF82089 (single reader: FUN_18147b00) — were **not isolated**:
  no direct `*cell =` assignment to either appears in the decompiled
  users; they are presumably maintained by the binding engine from bus
  data / NVRAM shadow state. This is a genuine open point, flagged
  rather than papered over. It does not affect the gate's identity:
  neither byte can produce 'Z' (§3.3).

**Conclusion [INF, strongly supported]:** the SAM device object's bound
state is established inside the Clarinox binding/registry machinery as
an outcome of the discovery process (bus identification → manager state
machine → object binding). There is no single application-level
"register SAM" store instruction to point at; the application-visible
decision points are exactly the conditionals catalogued in §5.

---

## 7. Reachability verdict (task item 4)

Can anything settable flip the gate?

- **A field-store field?** No. Field 0xC4 is the gate's *output*. The
  compared dword (object + 0x38) is not a field-store field, and no
  field-store write path reaches it. (Writing 0xC4 itself from the bus
  side — the subject of the separate direct-write investigation — would
  change what the *readers* see, not what this refresh computes; the
  refresh would overwrite it on its next run with the binding-derived
  value.)
- **An ABCD bus table value?** No code-proven path. The ABCD-facing
  quantities on this chain are: the identification type word
  (& 0x7C00 routing, §4.1) and the active-address bitmap (§3.4) — the
  first influences *whether the machine progresses toward* the refresh
  states, the second is *written by* the refresh. Neither is the gate
  operand. No mapping between field-store offsets (0xC4 etc.) and ABCD
  table/row IDs is proven by the code; they are different address
  spaces and this report does not equate them.
- **Nonvolatile config loaded at boot?** Not on this path. The field
  store is NVRAM-backed (§1), but the gate operand is runtime binding
  state, re-derived each discovery cycle; no NVRAM/config read feeds
  FUN_180bc460's result in any code examined.
- **A service-menu path?** None found. The only callers above the state
  machine are its dedicated task thread and supervisor (§4.2); no menu
  or UI function calls FUN_1813edd2, FUN_1813f454, or the refresh twins.
- **Purely internal derivation?** Yes — this is the verdict: the gate
  operand is **derived purely internally**, by the Clarinox binding
  engine, from whether the discovery process has bound a device object
  to the SAM slot. The realistic external levers over it are the
  *inputs to discovery itself* — what answers on the bus at 0x92 during
  commissioning, and how the identification handlers classify the
  answer (type-word routing, §4.1) — not any writable flag.

---

## 8. Cross-check against THERMOSTAT-PROTOCOL-MAP.md (task item 4)

- The map's commissioning prober (its §(b)1, from live captures) reads
  `0104` from **both 0x92 and 0x94** during System Setup. Stage C
  independently finds the firmware's SAM/B36 module treating exactly
  the pair {0x92, 0x94} as the two forms of one accessory slot
  (bitmap-clear helpers FUN_180c6988/FUN_180c6978, §3.4). The
  identification of **0x94 as the B36's bus address** is therefore
  **[INF, strong]** — consistent from both sides. (The map itself
  lists 0x94 only as a probed address; the "B36" naming of the variant
  form rests on stage B's screen-builder evidence: field 0x23 is the
  SAM-vs-B36 selector in FUN_1819ee96 case 5.)
- The map's SAM-interface tables (`3B02`/`3B03` served as zeros to an
  unregistered SAM) are the thermostat's *bus-served* surface. Stage C's
  field store is the thermostat's *internal* dictionary. No code found
  in stages A–C maps internal offset 0xC4 to any bus table; any future
  claim of such a mapping needs its own evidence.
- Consistency note: the bus captures show the thermostat answering a
  SAM's polls with zeros and never emitting registration probes
  (040E/3F02/031C in stage B's terms). Stage C's picture — a complete
  SAM/B36 manager that runs, refreshes presence from an internal
  binding that never becomes bound, and clears the 0x92 activity bit —
  is fully consistent with those captures.

---

## 9. What stage C cannot claim

- The semantic name of the object +0x38 slot ("bound/context") and of
  classify value 2 ("B36 form") are inferences from usage, not from
  symbols; the image has no symbol table. The branches, addresses, and
  compared values are facts.
- The writers of bound bytes 0xFFF8AAFF (device index) and 0xFFF82089
  (classify byte) were not isolated (§6). In particular it was not
  determined what sets bit 0x08 of 0xFFF82089 on a unit with a real B36
  attached, beyond "the binding engine maintains it".
- The internal decision by which the Clarinox engine sets the SAM
  object's +0x38 slot during a *successful* registration on Carrier
  hardware is inside engine code not traced this pass; stage C traced
  every application-level path that reads or routes around that state.
- FUN_180a8da2(0x42, 3, 0x0D, …) in state 0x14 is a binding-record
  lookup/mark operation over descriptor tables; its parameters are
  reported verbatim and not equated with ABCD address/table/row IDs.
- Dynamic behaviour (what these routines actually do on the author's unit,
  in what order, with what values) cannot be proven from the static
  image; the bus captures of the earlier project phases are the
  observational counterpart and agree with the static picture (§8).

---

## Appendix — method and artifacts

- Project: copy of the stage-B Ghidra project in
  `firmware-re/stageC/proj/` (original untouched); Ghidra 12.2 headless,
  `SuperH:BE:32:SH-2A`, base 0x18040000.
- Scripts (`firmware-re/stageC/scripts/`): `ClusterSurvey.java`,
  `SetterHunt.java`, `CellUsers.java`, `ListingDump.java`,
  `DecompileScript.java` (reused from stage B).
- Key intermediate output: `out/setterB_calls.txt` (894 extracted
  setter-B calls with arguments), `out/setter_hunt.txt`,
  `out6/goto_cellmap.txt` + the goto-argument extraction,
  `out9/listing_refresh.txt` (instruction listings of FUN_18147c58 /
  FUN_18147b00), `out9/listing_bc460.txt`.
- Enumeration completeness: setter-B call sites were enumerated both
  from Ghidra references (279 pool cells) and by a raw scan of the
  image for the setter's address as a big-endian word (257 occurrences);
  every Ghidra cell was followed to its code users. Setter-A: single
  raw occurrence, single call site.
