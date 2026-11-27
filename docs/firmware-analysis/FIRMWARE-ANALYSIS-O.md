# FIRMWARE-ANALYSIS-O — Stage O: the demand formula in closed form

**Object:** Ion SYST0101CW firmware v4.79 (image byte-identical to the official
4.79, stage N), SuperH SH-2A, base `0x18040000`.
**Question (parent tasking, 2026-11-26):** extract the EXACT formula that
produces the demand float `0xFFF8CD44` — the heart of the control law — so
that it can be reimplemented from this report alone, for the target
installation (Heil G80CTL 2-stage gas furnace, Heil HVA9 variable-speed AC,
coil EN(A,D)4X61, **single zone**).
**Method:** decompile + full listing audit of `FUN_180c62fc` and all five
helpers in `firmware-re/stageO/` (project copy `stageO/proj`, Ghidra 12.2
headless), pool-constant resolution against the flat image, provenance from
stage L, and end-to-end verification in the stage-M PCode emulator harness
(10 synthetic vectors, §8).
**House rules:** `[FACT]` = established by listing/decompile + pool evidence
or by emulator execution; `[INF]` = inference, labelled with its strength.
Every load-bearing claim was checked by two independent routes where the
tooling allows it (decompiler vs listing; static oracle vs emulator).

---

## 0. Verdict

1. **[FACT] The demand formula is fully recovered** (§2) and **verified
   end-to-end in the emulator: 10/10 vectors match** the closed-form oracle
   on every demand output (`CD44`, `C8CC[]`, `C8EC[]`, contribution array)
   — §8. The formula is reimplementable from this report alone; the only
   quantities it needs that are *installation data* rather than code are
   listed in §9.
2. **[FACT] Shape of the law.** `CD44` is a sum over zones of a per-zone
   value `C8CC[i]`, where each zone combines (a) an **instantaneous
   proportional term** `CA04[i]·e_i` (×15 in one of the two configurations)
   and (b) a **recursive contribution** `P_i` that integrates across
   refresh cycles with gain `G`, clamped to `[0, C870]`. The signed error
   is `e_i = CADC[i] − CB60[i]` in heating (mode 1) and
   `e_i = CB60[i] − CABC[i]` in cooling (mode 2) — i.e. in both modes
   `e_i > 0` means "this zone is calling".
3. **[FACT] Two corrections to earlier stages** (§7): the `FUN_180c5fc6`
   coefficient is the **double `0.05`**, not `1.325` (a float misread of a
   double's high word — the same trap as stage E's `0.4472`); and the
   contribution clamp in `FUN_180c5e3c`/`FUN_180c5ebc` is **two-sided**
   `[0, C870]`, not "negatives pass".
4. **[FACT] Writer 2** (`FUN_180c4322`) is a verbatim pass-through
   `CD44 := param` selected by a band classifier (§5); it is not part of
   the refresh-cycle law. In the refresh, writer 1 is the operative
   producer.
5. **Single-zone reduction** (§6): with one zone, `multi` collapses off,
   the `C880` ceiling drops out of the final clamp, and `CD44` is one
   zone's `max(t + P, 0)` with `C870 = CCC4[CC5A−1]` exactly in cooling.

---

## 1. Evidence base

| Artifact | Location |
|---|---|
| Decompiles (25 functions) | `firmware-re/stageO/out/decomp/` |
| Listings: `FUN_180c62fc` (552 lines), helpers `5dd0/5e00/5e16/5e3c/5ebc`, `FUN_180c5fc6` | `firmware-re/stageO/out/listing/` |
| Pool resolutions | `firmware-re/stageO/out/pools/` (`resolve_pools.py`, raw flat-file reads) |
| Emulator harness + oracle | `firmware-re/stageO/scripts/EmuDemand.java`, results `out/emu_demand.txt` |
| Emulator debug (5fc6 unit tests) | `firmware-re/stageO/scripts/EmuDebug.java`, `out/emu_debug.txt` |
| Provenance of inputs | `FIRMWARE-ANALYSIS-L.md` (writer census, ingestion chain) |
| Downstream consumers of `CD44` | `FIRMWARE-ANALYSIS-E.md` (quantizer `FUN_180c576c`, staging `FUN_180c54d8`, …) |

**SH float-compare convention** (used throughout, verified against three
helper listings): `fcmp/gt FRm,FRn` sets T = (FRn > FRm) — the *second*
printed operand is the subject.

**A decompiler trap that shaped this stage:** the Ghidra decompiler does
not model SH FPU register arguments/returns. `FUN_180c5dd0` decompiles to
an empty body and `FUN_180c5e3c`'s prototype is wrong; both were recovered
from listings. Any future work on this module must read listings, not
decompiles, for float helpers.

---

## 2. The demand formula

### 2.1 Cycle skeleton — `FUN_180c62fc` (called from the refresh `FUN_181efdfc`)

All addresses are RAM cells unless noted. `[FACT]`, listing-audited
(`out/listing/list_62fc.txt`, instruction references below).

```
entry:
  if C8C8 (0xFFF8C8C8) != 0:  for all i: zero_zone(i)     ; FUN_180c6266 → FUN_180c5f5c ×8
                              C8C8 := 0
  n     := #{ i : CBA9[i] ∉ {0,5} }                        ; FUN_180c5d90 → FUN_181f035c → FUN_181f0344
  multi := (n > 1) && (CBDC (0xFFF8CBDC) != 0)             ; @180C631A–632A
  acc0  := C90C (0xFFF8C90C)          ; entry value, see §2.2 note
  gate  := (C870 <= acc0)                                  ; @180C6334: !(C870 > acc0)
  acc   := 0.0 ;  C90C := 0.0
  for i in 0..7:  per-zone step (§2.2)
  CD44  := acc                                             ; @180C6784
  CE60  := max(CE60 − Σ_{active(i)} C8CC[i], 0)            ; via FUN_180c613a, @180C6786–67AC (side state, §4)
  FUN_180c61a4()                                           ; per-zone flag pass (side state, §4)
```

`zero_zone(i)` = `FUN_180c5f5c`: `C8EC[i] := 0`, `C910[i] := 0`,
`P[i] := 0`, `W2[i] := 0` (scratch `0xFFF874E8`), `C930[i] := P[i]` (= 0).

**Note on `acc0`:** `C90C`'s entry value is whatever the last writer left.
The ingestion function `FUN_181f4308` sets `C90C := CD8C` (stage L §3.5);
if it has not run since the previous refresh, `acc0` is the previous
cycle's `CD44`. The static cycle order of `FUN_181f4308` vs the refresh is
not resolvable (stage L §7) — **[FACT] the dependency, [UNKNOWN] the
order**. The `gate` therefore compares the full-scale ceiling `C870`
against (normally) the interpolated demand scale `CD8C`.

### 2.2 Per-zone step

Predicates `[FACT]` (`FUN_181f0428` → `FUN_181f0408`, decompiled this
stage):

```
present(i) := (CBA0[i] == 1) && (CBA9[i] ∉ {0,5})
active(i)  :=  CBA9[i] ∉ {0,5}
```

If `!present(i)` **or** `CD7D == 3`: `zero_zone(i)`; the zone contributes
nothing (the accumulate at @180C675A is inside the compute branch only).

Otherwise, in this exact order:

**(a) Signed error** — `FUN_180c5dd0(CB60[i], CADC[i], CABC[i])`,
listing-verified (@180C6384–63B0 loads `fr4=CB60[i]`, `fr5=CADC[i]`,
`fr6=CABC[i]`; helper listing `list_helpers.txt`):

```
e_i = CADC[i] − CB60[i]    if CD7D == 1   (heating)
      CB60[i] − CABC[i]    if CD7D == 2   (cooling)
      0.0                  otherwise
```
stored to scratch `W1[i]` (`0xFFF8750C`).

**(b) Correction term** `h_i` (stored to scratch `W2[i]`, `0xFFF874E8`):

```
h_i = FUN_180c5e00(C8EC[i], C880[i]) + FUN_180c5e16(CD8C, CD1C[i], C8CC[i], gate)
    = min(0, C880[i] − C8EC_prev[i])
      + ( (gate && CBDC != 0) ? CD8C·CD1C[i] − C8CC_prev[i] : 0 )
```
`[FACT]`, both helpers listing-verified. `C8EC[i]`/`C8CC[i]` here are the
**previous cycle's** values (neither has been overwritten yet this
iteration). Semantics `[INF, strong]`: the first term is a penalty that
only bites when last cycle's raw zone demand exceeded the zone cap
`C880[i]`; the second drives `C8CC[i]` toward this zone's share
`CD8C·CD1C[i]` of the interpolated demand scale.

**(c) Normalisation** (@180C6430–6476):

```
d_i = (e_i < 0) ? K9F4 : 1.0          ; K9F4 = *(float*)0xFFF8C9F4, scalar
q_i = CA24[i] / d_i
s_i = (0.9 · CA24[i]) / d_i           ; 0.9 = 0x3F666666, pool-verified
```
`s_i` is also written to the dictionary scalar `0x3C12A860` (overwritten
per zone; path A below reads the current zone's value). Negative errors
are divided by `K9F4` in both `q_i` and `s_i` — an asymmetric gain for
"zone satisfied" vs "zone calling" `[INF]`.

**(d) Recursive contribution** `P_i` — dictionary array
`0x3C12A864[i]`. Skipped entirely if `CD73 (0xFFF8CD73) != 0` (the
previous `P_i` is kept; step (e) still runs with it). Otherwise the
field-store byte `FS_1FDF` (read via `FUN_180c6246` →
`FUN_1815927c(0x1FDF,…)`) selects the path:

*Path A* (`FS_1FDF == 0`) — `FUN_180c5e3c(e_i, h_i, q_i, s_i, i)`,
listing-verified:
```
if C950[i] != 0:                       ; one-shot latch
    C950[i] := 0
    P_i := C958[i]                     ; UNCLAMPED
else:
    P_i := clamp( P_i_prev
                  + G·(CA04[i]·e_i / q_i)
                  + G·(h_i · (1.0 / s_i)) , 0, C870 )
```
`G = *(float*)0x3C12A85C` (dictionary scalar). The two `fmac`s execute in
the order shown (proportional term first, then the `h_i` term) — relevant
for bit-exact reimplementation. Edge: `CA24[i] == 0` ⇒ `s_i == 0` ⇒
`1.0/s_i = +Inf`; the code has no guard `[FACT]`.

*Path B* (`FS_1FDF != 0`) — `FUN_180c5ebc(e_i, q_i, i)`, listing-verified:
```
P_i := clamp( P_i_prev + Δ , 0, C870 )
Δ = G·(CA04[i]·e_i / q_i)   if 1e-5 ≤ |e_i| ≤ 2.0
    0                        otherwise (P_i holds, subject to the clamp)
```
Band constants are **doubles** compared in double precision:
`2.0` at `0x180C6038`, `9.9999997e-06` at `0x180C6044` (words
`0x3EE4F8B5/0x80000000`). Band edges are inclusive (compares are strict
`>` / `<`). Path B has no latch and no `h_i` term: it is a pure
integrator with a deadband window `[INF, strong]`.

The clamp, both paths `[FACT]` (listing tails @180C5E9A–5EB8 and
@180C5F3C–5F58; the branch on `v < 0` returns the constant `0.0` sitting
in `fr0`, not `v`):
```
clamp(v) = 0        if v < 0
           min(v, C870)  otherwise        ; i.e. clamp(v, 0, C870)
```

**(e) Instantaneous term and zone outputs** (@180C6530–6646):

```
t_i     = CA04[i] · e_i · (FS_1FDF != 0 ? 15.0 : 1.0)   ; 15.0 = 0x41700000
C910[i] := t_i
C8EC[i] := t_i + P_i
C930[i] := P_i
```
The same `FS_1FDF` byte selects both the contribution path (d) and the
×15 proportional multiplier here `[FACT]` — the two configurations are
two control-law personalities `[INF]`.

**(f) Final zone value and accumulation** (@180C6648–6760):

```
C8CC[i] := multi ? clamp(C8EC[i], 0, C880[i]) : max(C8EC[i], 0)
acc     += C8CC[i]
```
**The `C880[i]` ceiling applies only in multi-zone operation.** In
single-zone operation the cap enters only through the penalty term in
`h_i` (§2.2b).

**(g) Side state** (does not feed `CD44`; §4): `CE00[i]` leaky integrator,
`CE64 += |e_i|`, `FUN_180c6070(i)` updates.

### 2.3 Per-mode reading

| `CD7D` | `e_i` | Result |
|---|---|---|
| 1 (heating) | `CADC[i] − CB60[i]` | full law; `C870` from heat tables (§3) |
| 2 (cooling) | `CB60[i] − CABC[i]` | full law; `C870 = CCC4[CC5A−1]` exactly (§3) |
| 3 | — | every zone zeroed ⇒ **`CD44 = 0`** |
| other (0, 4…) | `0.0` via (a) | compute branch still runs with `e_i = 0`: `t_i = 0`, contributions update through `h_i` only; not an operating mode `[INF]` |

---

## 3. Producer of the ceiling `C870` — `FUN_1809f4a4`

`C870` is the demand full-scale for the current mode. `[FACT]` for
outputs/inputs/pool constants (decompile + pool resolution,
`out/decomp/decomp_1809f4a4.c`, `out/pools/pools_1809f4a4.txt`); branch
predicates are decompiler-transcribed, not listing-audited — flagged
where used. The function also writes `C87C (0xFFF8C87C)`, `C8A0`, `C8A4`
(not inputs to the demand formula).

- Entry: `C87C := 1.0`.
- **`CD7D == 2` (cooling):** `C8A0 := 0`; `C8A4 := CCC4[CC5A−1]`;
  **`C870 := CCC4[CC5A−1]`** — the ceiling *is* the staging threshold
  selected by `CC5A` (stage E); `C87C := CD04[0]/4.0`.
- **`CD7D == 1` (heating):** with `f8 = CC34[CBFA−1]`, `f9 = CCDC[CC5A−1]`:
  - *Branch A* — `(CC52 & 0x100)`, `CC54 != 4`, `CD71 == 0`, `CD7A == 0`,
    `(CBF4 & 0x40) || (CBF4 & 0x20)`, `CD48 == 0`, `CBF6 != 4`:
    `C870 := f8 + f9`; `C8A0 := 0`; `C8A4 := f9`;
    `C87C := max(f8/51210.0, CD04[0]/4.0)`.
  - *Branch B* — same gates but `(CBF4 & 0x80)`, and `CBF6 != 4`:
    `C870 := max(f8, f9)`; `C8A0 := f8`; `C8A4 := f9`;
    `C87C := max(f8/100000.0, CD04[0]/4.0)`.
  - *Branch C* — `((CC52 & 0x100)==0 || CC54 == 4 || CD71 != 0 ||
    CD7A != 0)`, `CD48 == 0`, `CBF6 != 4`:
    `C870 := f8`; `C8A0 := f8`; `C8A4 := 0`;
    `C87C := (CBF4 & 0x80)==0 ? f8/51210.0 : f8/100000.0` (no floor).
  - *Branch D* — otherwise: if `(CC52 & 0x100)`, `CC54 != 4`,
    `CD71 == 0`, `CD7A == 0`, and `(CD48 != 0 || CBF6 == 4)`:
    `C870 := f9`; `C8A0 := 0`; `C8A4 := f9`; `C87C := CD04[0]/4.0`;
    else all four outputs `:= 0`.
  Constants verbatim: `51210.0 = 0x47480A00`, `100000.0 = 0x47C35000`,
  divisor `4.0`.
- **`CD7D` other:** `C870 := C8A0 := C8A4 := C87C := 0`.

`[INF, strong]` `C87C` is a per-unit scaling of the same table values
(÷51210 / ÷100000 with a `CD04[0]/4` floor) for a different consumer;
it plays no role in `CD44`.

---

## 4. Side state maintained by the same pass (not inputs to `CD44`)

`[FACT]` unless noted; listed for reimplementation completeness — a
replacement thermostat does not need any of these to compute demand.

- **`CE00[i]`** (`0xFFF8CE00`) — leaky integrator of `|e_i|`, via
  `FUN_180c5fc6(CE00[i], e_i)` (@180C671C):
  `CE00[i] := 0.95·CE00[i] + 0.05·|e_i|`. The `0.05` is a **double**
  constant at `0x180C6060` (words `0x3FA99999/0xA0000000`); the `0.95` is
  a float at `0x180C6068`. The helper computes in double mode (FPSCR.PR
  toggle, `fcnvsd/fabs/fmul dr/fcnvds` idiom — listing
  `out/listing/list_5fc6.txt`). Consumed by `FUN_180c6070` against the
  threshold `0.13` (`0x3E051EB8`). Sibling `FUN_180c5ff6(a,b) =
  0.95·a + 0.05·b` (floats at `0x180C6068/0x180C606C`) is the same shape
  without the `|·|`.
- **`CE20[i]` / `CE40[i]`** — updated by `FUN_180c6070(i)`: if the zone's
  `CBA9` state changed since last cycle (copy at `0xFFF8752C`) or the
  zone is inactive, both are zeroed; else if `CE00[i] < 0.13` and the
  zone is in state 1, `CE20[i] := 0.95·CE20[i] + 0.05·(CD8C·CD1C[i])`
  (via `FUN_180c5ff6`) and `CE40[i] := 0`. `[INF]` a "zone recently
  satisfied" timer pair.
- **`CE64`** (`0xFFF8CE64`) — `+= |e_i|` for every computed zone
  (@180C64F8–652E; double-mode fabs idiom, no multiply). A per-cycle
  total-error accumulator `[INF]`.
- **`CE60`** (`0xFFF8CE60`) — tail update in §2.1: decays by the active
  zones' current contributions, floored at 0. Also written by
  `FUN_180c15d2` (stage G). `[INF]` a residual-demand decay cell for the
  staging/arbitration side, not for `CD44`.
- **`FUN_180c61a4`** (tail call) — gated on `CAA9 != 0`; per active zone
  with `C8CC`-family compare and `CBDC != 0`, sets the complementary
  flag bytes `CAAB[i]`/`CAB3[i]` (stage L §3.6). Flags only.

---

## 5. Writer 2 — `FUN_180c4322` and its dispatcher

`[FACT]` (decompiles + pools, this stage). `FUN_180c406e(param)` first
re-registers its property group (`FUN_180c4212` → `FUN_180c4588(param,
0x182C3148, …)`; `0x182C3148` is a float table `1.0, 2.0, 3.0, 4.0, 5.0…`,
not a string), then dispatches on `FUN_180c4224(param)`:

```
sel = 1   if *0xFFF874CC < *0xFFF874D0            (also clears 874D8, sets 874D9)
    = 0   else if dict byte 0x3C12A852 == 0
    = (CD4A ∈ {1,2,3} ? 3 : 1)   else if param ≤ 0.1   (0x3DCCCCCD; sets 874D9)
    = (CD4A ∈ {1,2,3} ? 3 : 2)   else if param ≤ 1.0   (clears 874D9)
    = 4   otherwise
```

Case 2 → **`FUN_180c4322`: `CD44 := param` verbatim** (store via pool
`0x180C4404`). Its remaining work is bookkeeping in `0xFFF874xx` scratch:
`CA75 := (byte)(int)*0xFFF874D0`, `0xFFF874DC := CD44`, a threshold flag
`0xFFF874D8 := ((table[idx]·0.5 ≤ CD44) || flag) && !0xFFF874D9`, and
`CA94 := *0xFFF874DA`. The sibling cases (`FUN_180c42dc/4316/446c/4478`)
do not write `CD44`.

So writer 2 fires only for a normalised argument in `(0.1, 1.0]` with
`CD4A ∉ {1,2,3}` and the dictionary byte set — a binding-property
pass-through of an externally computed value, **not** the cyclic control
law. Its argument's producer (the calling property of the `0x180C4xxx`
group) was not isolated — **[UNKNOWN]**, and stage L's conclusion
stands: in the refresh cycle, writer 1 (§2) is the operative producer.

---

## 6. Input semantics

All `[FACT]` for address/producer (stage L census + this stage's pools);
semantics column is `[FACT]` where the arithmetic forces it, else
`[INF]` as marked. Temperatures `CB60/CABC/CADC` share one unit (they are
subtracted); demand is dimensionless (compared downstream against the
`CCC4/CCDC/CD04` threshold family, stage E).

| Cell | Type | Meaning | Producer |
|---|---|---|---|
| `CB60[i]` `0xFFF8CB60` | float[8] | measured zone temperature | field-store bulk copy (stage L §3.4) |
| `CADC[i]` `0xFFF8CADC` | float[8] | heating target per zone — `e = CADC − CB60` in mode 1 forces this reading | mirror of `0xFFF83C38` via `FUN_181f54e8` |
| `CABC[i]` `0xFFF8CABC` | float[8] | cooling target per zone — `e = CB60 − CABC` in mode 2 | mirror of `0xFFF83C58` via `FUN_181f54e8` |
| `CD7D` `0xFFF8CD7D` | byte | mode: 1 heat, 2 cool, 3 = zero-demand | `FUN_181f4308`, `FUN_181f5d8a`, refresh |
| `CBA0[i]` `0xFFF8CBA0` | byte[8] | zone configured/present flag (`==1` required) | `FUN_181f59e0` |
| `CBA9[i]` `0xFFF8CBA9` | byte[8] | zone state; `∉{0,5}` = active | `FUN_181f59e0` + refresh |
| `C870` `0xFFF8C870` | float | demand full-scale / contribution ceiling | `FUN_1809f4a4` (§3) |
| `CD8C` `0xFFF8CD8C` | float | interpolated demand scale (threshold tables by class/indices, stage L §3.5) | `FUN_181f21d4` family via ingestion |
| `C8CC[i]` `0xFFF8C8CC` | float[8] | per-zone demand value; pre-refresh = equal split of `CD8C` over active zones | `FUN_181f4308` (split), `FUN_180c62fc` (law) |
| `C8EC[i]` `0xFFF8C8EC` | float[8] | previous cycle's raw zone demand `t_i + P_i` | `FUN_180c62fc`, `FUN_180c5f5c` |
| `C880[i]` `0xFFF8C880` | float[8] | per-zone cap (multi-zone clamp + penalty reference) | `FUN_18226ab4` |
| `CA04[i]` `0xFFF8CA04` | float[8] | per-zone proportional gain | `FUN_181f017e` |
| `CA24[i]` `0xFFF8CA24` | float[8] | per-zone normalisation scale (divides the error terms via `q_i`, `s_i`) | `FUN_181f017e` |
| `CD1C[i]` `0xFFF8CD1C` | float[8] | per-zone distribution weight `[INF]` — multiplies `CD8C` as the zone's target share | `FUN_180d208c`, refresh |
| `CBDC` `0xFFF8CBDC` | byte | multi-zone / demand-response enable: gates `multi`, the `h_i` share term, and `FUN_180c61a4` | `FUN_181f59e0` |
| `K9F4` `0xFFF8C9F4` | float | divisor applied to negative errors only | `FUN_181f5d08` |
| `G` `0x3C12A85C` | float | global gain of the recursive contribution | **no writer found** (§9) |
| `FS_1FDF` | byte | field-store field `0x1FDF`: selects contribution path A/B **and** the ×15 multiplier | field store (via `FUN_1815927c`) |
| `CD73` `0xFFF8CD73` | byte | `!=0` freezes contribution recomputation for the cycle | refresh `FUN_181efdfc` |
| `C950[i]`/`C958[i]` | byte[8]/float[8] | one-shot contribution latch (path A only) | `FUN_1812b48c` (arms all zones with `0.0`), refresh (value not isolated) |
| `P[i]` `0x3C12A864` | float[8] | the recursive per-zone contribution itself (dictionary-resident state) | `FUN_180c62fc`, `FUN_180c5f5c` |
| `C910[i]`/`C930[i]` | float[8] | mirrors of `t_i` / `P_i` | `FUN_180c62fc`, `FUN_180c5f5c` |

State a reimplementation must carry across cycles, per zone: `P[i]`,
`C8EC[i]`, `C8CC[i]` (and `C950/C958` if latch behaviour is replicated).
Everything else is a per-cycle input.

---

## 7. Corrections to earlier stages

1. **`FUN_180c5fc6` coefficient.** Stage L's notes (and this stage's
   intermediate work) recorded `1.325·|e| + 0.95·prev`. **Wrong.** The
   constant at `0x180C6060` is a **double** `0.05` (words
   `0x3FA99999/0xA0000000`); `1.325` is its high word misread as a float
   — the identical trap to stage E §5ebc's `0.4472` (in fact the high
   word of `0.05` and of `1.325`'s double differ; the misread came from
   reading 4 bytes only). Correct: `CE00 := 0.95·CE00 + 0.05·|e|`,
   matching the sibling `FUN_180c5ff6 = 0.95·a + 0.05·b`.
2. **Contribution clamp is two-sided.** The decompiler renders
   `FUN_180c5e3c`/`FUN_180c5ebc` as if negative results pass through.
   The listings show the `v < 0` branch returns the constant `0.0` held
   in `fr0`. Emulator vector V10 (§8) confirms: an oracle predicting
   `−210.67` fails, the real code returns `0`. Clamp is `[0, C870]`.
3. **`FUN_180c5dd0` is not empty.** Its decompile shows no arithmetic
   because the decompiler drops FPU args/returns; the listing gives the
   mode-signed difference (§2.2a) — the single most important line of
   the law.

---

## 8. Emulator verification

**Harness:** stage-M pattern (`EmuDemand.java`): the real
`FUN_180c62fc` executes end-to-end in the Ghidra PCode emulator on
synthetic RAM (blocks `0xFFF80000+0x10000`, `0x3C120000+0x10000` created
in the `stageO/proj` copy), entered with `PR` = sentinel. **One stub:**
`FUN_180c6246` (the field-store getter) is intercepted at its entry
breakpoint — `r0` is set to the vector's selector byte and `PC := PR`.
That byte is an *input* to the formula (§2.2d/e), not part of it; every
other callee (`FUN_180c5d90`, `FUN_181f0428`, the five helpers,
`FUN_180c6070`, `FUN_180c613a`, `FUN_180c61a4`, …) runs as real code.
**Oracle:** an independent Java implementation of §2
(`EmuDemand.oracle`), compared on `CD44`, all `C8CC[]`, `C8EC[]`,
`P[]` with tolerance `0.02 + 0.1%`.

Common vector setup (unless overridden): zone 0 present+active, others
absent; `G=1`, `K9F4=2`, `CA04=CA24=CD1C=1`, `C880=1000`, `CD8C=100`,
`acc0=100`, `C870=100`, `P_prev=50`, `C8CC_prev=100`, `CBDC=1`, `CD73=0`.

| # | Vector | `CD44` emu = oracle | Key intermediate |
|---|---|---|---|
| V1 | cool, `e=+6`, path B, out-of-band | **140 = 140** | `P=50` (held), `C8EC=140` |
| V2 | cool, `e=+6`, path A | **62 = 62** | `P=56`, `C8EC=62` |
| V3 | heat, `e=+4`, path B, `C870=40` | **100 = 100** | `P=40` (ceiling clamps 50→40) |
| V4 | cool, `e=−4`, path A, divisor `K9F4=2` | **38 = 38** | `P=42` (`q=0.5`) |
| V5 | two zones, `multi`, `C880[0]=120` | **130 = 130** | zone0 clamped 140→120, zone1 `P=10` held (`e=0` below band) |
| V6 | path A latch `C958=77` | **83 = 83** | `P=77`, and `C950[0]` read back **0** (flag consumed) |
| V7 | `CD7D=3` | **0 = 0** | all zone state zeroed |
| V8 | `CD73=1` (frozen contribution) | **56 = 56** | `P` stays 50 while `C8EC=56` — distinguishes from V2 |
| V9 | cool, `e=+1`, path B in-band | **66 = 66** | `P=51` |
| V10 | path A, penalty+share (`C8EC_prev=1300`, `C8CC_prev=40`) | **6 = 6** | raw `P=−210.67` → clamped to **0** (proves §7.2) |

**Result: 10/10 PASS** (`out/emu_demand.txt`).

**The one emulator-deviant output — `CE00` (excluded from pass/fail).**
`FUN_180c5fc6` computes its `|e|` term in double mode; the PCode
emulator executes that `FMUL` as single-precision on the double's high
word and corrupts the result. Unit tests (`EmuDebug.java`,
`out/emu_debug.txt`): `5fc6(0, 6)` → emu `50.8` vs true
`0.95·0 + 0.05·6 = 0.30`; `5fc6(10, −3)` → emu `29.7` vs true
`0.95·10 + 0.05·3 = 9.65`; `5fc6(0, 0)` → `0` (matches). The corrupted values are
consistent with the single-precision-on-high-word prediction
(`(float)0x40180000 = 2.375`; `2.375 × 1.325` re-interpreted as a
double's high word ≈ `50.8`). `CE00` does not feed `CD44` (§4), so the
demand verification is unaffected; `CE00`'s closed form rests on the
listing idiom + verbatim constants (§4, §7.1). On real hardware (or a
PR-faithful emulator) it will read `0.95·prev + 0.05·|e|`.

---

## 9. Single-zone reduction (the target installation)

One present/active zone `k`, all others absent `[FACT]` (derived from
§2; exercised by vectors V1–V4, V6, V8–V10):

- Absent zones are zeroed by `FUN_180c5f5c` and contribute exactly `0`.
- `n = 1` ⇒ **`multi = false`** regardless of `CBDC` ⇒ the `C880` ceiling
  **drops out of the final clamp**: `C8CC[k] = max(C8EC[k], 0)`.
- Ingestion's equal split gives the single zone the whole scale:
  `C8CC_prev[k] = CD8C`, and `acc0 = CD8C`, so
  `gate = (C870 ≤ CD8C)`.
- The law collapses to:

```
e   = (mode 1) CADC[k] − CB60[k]  |  (mode 2) CB60[k] − CABC[k]
h   = min(0, C880[k] − C8EC_prev[k])
      + ( (C870 ≤ CD8C && CBDC != 0) ? CD8C·(CD1C[k] − 1) : 0 )
d   = e < 0 ? K9F4 : 1 ;  q = CA24[k]/d ;  s = 0.9·CA24[k]/d
P  := (CD73 != 0) ? P
    : (FS_1FDF == 0) ? (latch ? C958[k]
                        : clamp(P + G·CA04[k]·e/q + G·h/s, 0, C870))
    :                  clamp(P + (|e| ∈ [1e-5, 2] ? G·CA04[k]·e/q : 0), 0, C870)
CD44 = max( CA04[k]·e·(FS_1FDF != 0 ? 15 : 1) + P , 0 )
```

- In cooling, `C870 = CCC4[CC5A−1]` exactly (§3) — the contribution
  ceiling is the staging threshold itself.
- `[INF, unproven]` if the single zone's distribution weight
  `CD1C[k] = 1` (the natural normalisation), the share term of `h`
  vanishes and `h = min(0, C880[k] − C8EC_prev[k])` — a pure overshoot
  penalty. Whether `CD1C` is normalised this way is installation data
  (§10.1).

For the replacement thermostat this is the whole law: carry `P`,
`C8EC[k]` (for `h`), and the latch state; everything else is a
per-cycle input (temperatures, targets, mode, and the configuration
scalars of §10.1).

---

## 10. Explicit unknowns

1. **Runtime values of configuration inputs** (the formula is exact;
   these are data, set by commissioning/binding, not code): `G`
   (`0x3C12A85C` — no writer found in any stage's census; dictionary-
   resident), `K9F4` (writer `FUN_181f5d08`, value configuration-
   dependent), `CA04[i]`/`CA24[i]` (writer `FUN_181f017e`), `C880[i]`
   (writer `FUN_18226ab4`), `CD1C[i]` (whether the weights are
   normalised, e.g. `Σ = 1`), the installation's `FS_1FDF` byte
   (path A vs B personality), and `CD73`'s setting logic inside the
   refresh. All are readable from a live unit's RAM/dictionary or from
   bus captures in one session — none requires more RE.
2. **Writer 2's argument producer** (§5) and whether writer 2 ever
   fires under this installation's configuration.
3. **Latch arming by the refresh:** `FUN_1812b48c` arms all zones with
   `C958 = 0.0` `[FACT]`; the refresh also writes `C950/C958` (stage L
   census) but the value it arms was not isolated.
4. **Cycle ordering** of `FUN_181f4308` vs the refresh (§2.1 note) —
   affects `acc0` and the `C8CC_prev` read by the share term; not
   statically resolvable.
5. **`FUN_1809f4a4` branch predicates** are decompiler-transcribed
   (§3); its outputs, table reads and constants are pool-verified, but
   the 802-byte body was not listing-audited line by line.
6. **Temperature unit** of `CB60/CABC/CADC`: shared, so the formula is
   unit-consistent as written; the absolute unit does not affect
   reimplementation of the law, only calibration of `CA04/CA24/G`
   against the threshold tables.

---

*Stage O deliverable. Work products: `firmware-re/stageO/` (project
copy, scripts, decompiles, listings, pools, emulator outputs). No files
outside `firmware-re/stageO/` and this report were created or modified.*
