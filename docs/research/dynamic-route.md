# Dynamic-analysis route for the Ion firmware — feasibility assessment

Stage M, 2026-11-26. Scope per the author's fallback ordering ("копать от
дескрипторов stage C, и если не понравится — в динамику уйдём"): assess
whether this firmware's code can be *executed and observed* without the
physical thermostat, build the harness skeleton for the most viable
route, and state honestly what a full dynamic campaign would need.
This is a feasibility pass, not the campaign.

Target recap: ICP Ion BINF0479 v4.79, Renesas SH-2A (SH7269),
big-endian, flat image at `0x18040000`, Ghidra 12.2 project from
stages B/C/E. Static references: FIRMWARE-ANALYSIS-C.md (Clarinox
binding/registration machinery), FIRMWARE-ANALYSIS-E.md (decision
module, RAM block `0xFFF8C8xx–0xFFF8CDxx`).

---

## 0. Verdict table

| Route | Verdict | One-line reason |
|---|---|---|
| **Ghidra PCode emulator (EmulatorHelper)** | **WORKS — demonstrated** | Two stage-E leaf functions executed against synthetic RAM; 23/23 test vectors reproduce the statically derived oracles. In-tree, free, scriptable. |
| Styx emulator (PCode/SLEIGH-based firmware fuzzer) | Plausible alternative, not evaluated hands-on | Lists SH2A support on the same SLEIGH spec Ghidra uses; would be a re-platforming, gain only if fuzzing throughput / peripheral scaffolding is needed. |
| QEMU | **NO** | Only `target-sh4` (SH7750 family, MMU machines). No SH-2A CPU model, no SH7269 machine; SH-2A ≠ SH-4. |
| Unicorn Engine | **NO** | No SuperH architecture exists in Unicorn at all (ARM/AArch64/M68K/MIPS/SPARC/PPC/RISC-V/S390X/TriCore/x86 only). |
| Renesas Simulator Debugger for SuperH | Real but impractical here | Genuine cycle-accurate SH2A-FPU simulator, but Windows/HEW, legacy (last release 2011, bundled with the paid compiler package, targets flagged obsolete), GUI-centric; loading a foreign flat image + hand-built middleware RAM state is not its workflow. |
| GNU GDB simulator (`sim/sh`) | Marginal fallback | Exists for `sh-elf` compiler testing; SH-2A extension coverage unverified and likely partial; no peripherals, no harness ecosystem. Not recommended. |
| On-device via E10A-USB (H-UDI) | Exists on paper, rejected as primary route | SH7269 silicon has H-UDI and E10A-USB supports SH-2/SH-2A (≈$1.2k, still sold) — but no evidence the SYST0101CW board routes H-UDI anywhere reachable, and the target is the only control that heats the house. Last resort, and only on a spare bench unit. |

**Bottom line:** the dynamic route is feasible *today* with the
toolchain already in this workspace, at function/module level, with
hand-built Clarinox state. Whole-firmware cold boot under emulation
is not a realistic goal on any surveyed route (peripherals + RTOS +
runtime registration). This validates the fallback ordering: the
descriptor pass (stage C lineage) produces exactly the state a
dynamic harness must seed; dynamics then execute what statics could
only describe.

---

## 1. Ghidra PCode emulator — the demonstrated route

### 1.1 What was built

Harness skeleton in `firmware-re/stageM/`:

- `proj/` — copy of the stage-E Ghidra project (program
  `flat_trim.bin`, SuperH:BE:32:SH-2A, base `0x18040000`).
- `scripts/EmuStageDemo.java` — headless GhidraScript using
  `ghidra.app.emulator.EmulatorHelper` (in Ghidra 12.2 it lives in
  `Ghidra/Framework/Emulation/lib/Emulation.jar`).
- `runM.sh` — runner (same pattern as stages B–E:
  `analyzeHeadless … -process flat_trim.bin -noanalysis
  -postScript EmuStageDemo.java <out>`).
- `out/emu_stage_demo.txt` — the recorded run; `runM.log` — headless
  log, `EXIT=0`, zero warnings on the final run.

Mechanics of the harness:

- The stage-E project contains exactly **one** memory block:
  `ram  0x18040000–0x18459E83` (the flat image, initialised). There
  is **no** on-chip RAM block — the script creates an uninitialised
  block `EMU_RAM` at `0xFFF8C000`, size `0x4000` (covers the whole
  decision block `0xFFF8C8xx–0xFFF8CDxx` plus stack headroom), inside
  the stage-M project copy only.
- CPU context is set explicitly per call: `pc` = function entry,
  `pr` = sentinel `0xFFF8FF00` (SH returns via PR, not the stack),
  `r15` (the language's stack-pointer register) = `0xFFF8F800`,
  `sr` = 0. A breakpoint on the sentinel stops the run; success =
  execution state `BREAKPOINT` at the sentinel.
- Inputs are written as explicit big-endian bytes
  (`writeMemory`), outputs read back from emulator memory
  (`readMemoryByte`). The image itself — including the literal-pool
  cells through which all decision code reaches RAM — is loaded by
  EmulatorHelper from the program, unmodified.

### 1.2 The demo runs

**FUN_180c54d8** (stage-E §3, the 0/1/2 staging state machine; pure
leaf, 282 B, no calls). Inputs seeded per vector: gate byte
`0xFFF8CD7D`, demand float `0xFFF8CD44`, threshold table
`T[0..1]` at `0xFFF8CCC4`, index byte `0xFFF8CC5A`, state byte
`0xFFF8CD49`. Oracle: the §3 state table re-implemented in Java
(stage 2 at demand > 1.25·Tsel; stage-1 engage 0.25·T[1]; hold to
0.01·T[1]; stage-2 fallback at 1.00·Tsel; gate ≠ 2 forces 0).
**Result: 12/12 PASS**, including the gate-off case, the
index-selects-T[1] case, and the invalid-state case.

**FUN_180c576c** (stage-E §2, the four-level demand quantizer;
198 B). Inputs: float `0xFFF8CB58`, byte `0xFFF8CABB` (x = float −
byte), state `0xFFF8CD4B`; oracle = the per-state Schmitt threshold
table of §2. **Result: 11/11 PASS**, including the hysteresis case
(x = 5.5 yields state 1 from state 1 but state 2 from state 2).

Combined: **23/23 vectors**, every run terminating cleanly at the
return sentinel. This is dynamic confirmation, by execution, of two
statically derived state machines — the first executed (not just
read) behaviour recovered from this firmware.

### 1.3 Known caveats of the route

- First run warned `Uninitialized register read at 180c54e0: sr`;
  fixed by initialising SR = 0 in the harness. Any wider harness
  must treat *all* CPU context as an explicit input.
- PCode floating point is IEEE semantics from the SLEIGH spec; the
  SH-2A's FPSCR precision/size modes are not modelled as dynamic
  state. For the single-precision decision leaves the agreement
  with the static oracle is exact on all 23 vectors; a campaign
  should add numeric sweeps before trusting FP edge behaviour.
- No interrupts, no timing, no MMIO: reads of unmapped/peripheral
  space fault unless the harness seeds or stubs them (see §4).
- Speed is interpreter-class (fine for decision logic; irrelevant
  for boot, which is out of scope anyway).

---

## 2. Other software routes — why they don't beat §1

**QEMU.** The SuperH target is `target-sh4` only: SH7750-family
CPUs with an MMU, machines `shix`/`r2d`. There is no SH-2A CPU
model and no SH7269 machine. SH-2A is a different core (no MMU,
different peripheral map at different addresses, SH-2A instruction
extensions); partial instruction overlap with SH-4A does not make
this image runnable. Building an SH7269 machine model in QEMU is a
project larger than the RE itself.

**Unicorn.** No SuperH support exists in the engine — the
architecture list is closed and SH is not on it. (Capstone
*disassembles* SH; that is not execution.)

**Styx** (open-source firmware emulation/fuzzing framework) is the
one alternative worth a bookmark: its primary backend is Ghidra
PCode and its supported-architecture list explicitly includes
**SH2A** via the SuperH SLA — the same SLEIGH semantics proven in
§1, wrapped in a fuzzing-oriented harness with peripheral-model
hooks. Not evaluated hands-on; adopting it is a re-platforming
decision to make only if the campaign outgrows headless Ghidra
scripts (e.g. coverage-guided fuzzing of the refresh function).

**Renesas Simulator Debugger for SuperH Family.** A real
cycle-accurate SH2A-FPU simulator with cache and some peripheral
models (timers etc.). Disqualifiers for this project: Windows +
High-performance Embedded Workshop only; last release V.9.10.01
(2011); distributed inside the SuperH C/C++ Compiler Package;
Renesas itself flags all target devices obsolete/not recommended.
Its workflow assumes *your* project built with *their* toolchain,
not a stripped foreign image plus hand-assembled middleware state.

**GNU GDB `sim/sh`.** Exists (used for GCC `sh-elf` testing). It is
an instruction simulator of SH-1…SH-4 vintage; coverage of SH-2A
extensions is unverified and likely partial, there are no
peripherals, and there is no state-seeding harness comparable to
§1. Recorded for completeness; not recommended.

---

## 3. On-device route (E10A-USB / H-UDI) — evidence and verdict

Facts:

- The SH7269 MCU has the H-UDI debug interface; Renesas's E10A-USB
  on-chip emulator (HS0005KCU01H, 14-pin H-UDI) explicitly supports
  the SH-2/SH-2A device groups, offers breakpoints, branch trace
  and RAM monitoring, and is still sold (≈ $1,164–1,187, Newark).
  Renesas's own SH7269 CPU board routes H-UDI to 38-pin and 14-pin
  connectors — on a *development* board.
- In the firmware image: **no** H-UDI/JTAG/E10A strings. The only
  debug-flavoured strings are a Clarinox framework config block
  (`DEBUG_MEDIUM = SOCKET`, `DEBUG_LOCAL_PORT = 4002`,
  `DEBUG_REMOTE_PORT = 14321`, `DEBUG_FLAG = 0000000000000`) — a
  socket debug-console configuration of the middleware, apparently
  disabled by its flag. Whether any of it is reachable in this
  build is unknown; it is a question, not a route.
- In this pass, no FCC internal-photo exhibit or teardown of the
  SYST0101CW surfaced showing a debug header or test-pad field.
  A production wall control breaking out H-UDI would be unusual;
  reaching the pins would in practice mean soldering to a
  256-pin-package board.

Verdict: the silicon capability exists, the product access does
not (unproven at best), the probe is ~$1.2k, and the target unit
is the house's only heating control — a halted CPU mid-winter is
precisely the comm-fault scenario the project still hasn't
measured (protocol-map gap G1). **Rejected as a primary route.**
It becomes discussable only with a spare SYST0101CW bought for
the bench, and even then the emulator route (§1) answers the
decision-logic questions without touching hardware.

The microSD update path is an *input* channel (that's where our
image came from), not an observation channel: nothing found
suggests the updater offers tracing, logging export, or a debug
mode.

---

## 4. What blocks scaling from leaves to the interesting code

The demo functions are leaves: no calls, all state in one RAM
block. Everything above them is gated by runtime-built state:

1. **Clarinox registration state.** Stage C's core finding: the
   SAM object's bound state — and by extension the binding layer's
   behaviour — is *derived by the discovery process* inside the
   Clarinox engine; there is no application-level "register"
   store to seed with one write. Descriptor tables, the field
   store (NVRAM-backed), dictionary-space objects at `0x3Cxxxxxx`
   (the Sparkplug metric dictionary), and RAM function-pointer
   tables (e.g. `sys_ctrl_task`'s handler table) are all built at
   runtime. A cold emulator starts with none of it.
2. **The refresh function's environment.** FUN_181efdfc (the sole
   caller of the §2/§3/§4/§6 leaves, via computed calls through
   pool cells) also *maintains* the mode byte `0xFFF8CD7D` from a
   getter result before evaluating the gated properties.
   Emulating it means seeding whatever that getter reads —
   dictionary/binding objects — not just the decision block.
3. **Unknown input producers.** Who writes the module's inputs
   (demand float `0xFFF8CD44`, threshold table `0xFFF8CCC4` +
   index, zone arrays) was not isolated statically (prime suspect
   FUN_180c15d2 and sibling evaluators). Dynamics can *find*
   them — run candidates and watch the decision block — but each
   candidate drags in its own input state.
4. **RTOS primitives.** Tasks, queues and delays sit behind
   Clarinox wrapper families (task creation FUN_180bc084;
   `sys_ctrl_task` blocks on a queue receive, 1000 ms timeout,
   then dispatches a RAM-registered handler). Execution above
   the binding layer needs those wrappers stubbed — EmulatorHelper
   `registerCallOtherCallback` / targeted function stubs with a
   cooperative model — or the run dies at the first queue call.
5. **Peripherals / MMIO.** SH7269 on-chip modules (the SCIF that
   carries the ABCD bus, timers, ADC, DMAC, display) are outside
   the image block. Any code that polls a status register needs a
   scripted responder policy per address range (memory-fault
   handler or pre-seeded values), or it spins forever on a ready
   bit that never sets.
6. **No timing truth.** The 10 s command cadence is, per stage E,
   most plausibly a 1 s-ticked handler counting to 10. Emulation
   reproduces *logic*, never wall-clock cadence; questions of the
   "how long until comm fault" class (G1) remain bench questions,
   untouched by this route.

---

## 5. What a full dynamic campaign would need

In dependency order; items 1–2 are days-scale, item 3 is the
campaign's centre of gravity.

1. **Leaf sweep (generalise this skeleton).** Extend the runner
   to the remaining stage-E leaves — FUN_180c55f2 (§4 setpoint
   adjustment), FUN_18183d34 (§5 satisfaction averager),
   FUN_180c5832 (§6 source arbitration) plus helpers
   FUN_18051e4e / FUN_18051cec / FUN_180c5c7c — with vector sweeps
   (boundary + randomised) against the static oracles from
   FIRMWARE-ANALYSIS-E. Output: an executed-behaviour spec of the
   whole decision module, cross-verified against statics.
2. **Input-producer hunt.** Emulate FUN_180c15d2 and the sibling
   evaluators with memory-write tracking enabled
   (`enableMemoryWriteTracking`) on the decision block: observe
   who writes `0xFFF8CD44` / `0xFFF8CCC4` / the zone arrays, and
   what state they consume to do it. This converts stage E's
   prime suspect into a traced dataflow.
3. **Refresh-level run.** Hand-build the binding environment for
   FUN_181efdfc: seed dictionary-space objects and descriptor
   tables (artifacts exist from stages C/D), maintain the mode
   byte, stub the getter layer. Validate end-to-end: zone inputs
   in → §2–§6 outputs out, compared against capture-derived
   expectations (THERMOSTAT-PROTOCOL-MAP scenario deltas, e.g.
   the heat staircase). This is the run that answers "what does
   the module compute for *our* equipment profile".
4. **Stub layer (only if execution climbs higher).** MMIO
   responder policies for SH7269 peripheral ranges; CallOther /
   stub implementations for the Clarinox task/queue/delay
   wrappers. Needed for supervisor/state-machine code
   (stage C's FUN_1813f454 chain), not for the decision module.
5. **Explicit non-goals.** Cold boot to UI/touch/Wi-Fi; cycle
   accuracy; anything involving the physical unit. The emulator
   replaces Ion *logic* questions, not Ion *hardware* questions.

Artifacts of this stage: `firmware-re/stageM/` (project copy,
`scripts/EmuStageDemo.java`, `runM.sh`, `runM.log`,
`out/emu_stage_demo.txt` — 23/23 PASS).
