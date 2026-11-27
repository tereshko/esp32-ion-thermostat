# VERIFY — Mode semantics (stage S claims), independent re-derivation

Date: 2026-11-26. Method: pool pointers resolved directly from the flat image
(stageB/flat.bin, base 0x18040000, BE32) for every function cited; decompiles
read in stageS/out, stageL/out (decomp + pools + decomp_ann), stageE/out
(decomp1/decomp2 + users2.txt census); FUN_180c5dd0 checked at listing level
(stageO/out/listing/list_helpers.txt). Report prose was not trusted; every
address below was resolved in this session.

## Claim 1 — CD7D (0xFFF8CD7D): 1 = HEAT, 2 = COOL, 3 = AUTO — **CONFIRMED**

### 1(a) Ingestion copy sources — CONFIRMED
FUN_1815dc40 pool resolution:
- copy(dst 0xFFF8AE84, src 0xFFF83C58, 32 B) → AE84 ← mirror 0xFFF83C58
- copy(dst 0xFFF8AE64, src 0xFFF83C38, 32 B) → AE64 ← mirror 0xFFF83C38
- copy(dst 0xFFF8AEA4, src 0xFFF82160, 32 B) → AEA4 ← 0xFFF82160 (zone temps)
- copy(dst AE47 0xFFF8AE47, src 0xFFF82EED, 1 B) → R byte (see claim 6)

Mirror→setpoint-array link: FUN_181f54e8 (stageL pools + decompile) copies
0xFFF83C58 → CABC array (0xFFF8CABC) and 0xFFF83C38 → CADC array (0xFFF8CADC),
32 B each. AE64/AE84 and CADC/CABC therefore carry identical source data
under either copy-direction convention.

CADC = heat setpoints, from the demand signs at **listing level**
(FUN_180c5dd0, stageO listing): CD7D==1 → `fmov fr5,fr0; fsub fr4,fr0`;
CD7D==2 → `fmov fr4,fr0; fsub fr6,fr0`; else → constant (0.0). The caller
FUN_180c62fc (stageL decomp_ann, pools 180c6584/6588/658c) passes
(temp=CB60[i], CADC[i], CABC[i]) into fr4/fr5/fr6. Hence mode 1 error =
CADC[i] − temp (positive when setpoint exceeds room temperature = heating
demand) and mode 2 error = temp − CABC[i]. Swapping CADC/CABC makes both
errors physically backwards. Signs force CADC = heat SP, CABC = cool SP.

### 1(b) Auto arbiter FUN_1815e01c — CONFIRMED
Pool resolution: accumulators over zones passing the AE52/AE5A predicate:
fVar4 += AE64[i] − AEA4[i] (= Σ(CADC − temp), heat-demand sum);
fVar3 += AEA4[i] − AE84[i] (= Σ(temp − CABC), cool-demand sum).
fVar4 < fVar3 → *0xFFF8AE4C = 1, *0xFFF8AE4D = 0; else AE4C = 0, AE4D = 1.
Consumer: FUN_1815df84 returns AE4C; in FUN_1815d67e state AE45==1,
df84()==0 → (AE44,AE45) = (1,3) [heat], df84()!=0 → (2,5) [cool].
So heat-sum < cool-sum selects direction 2, larger sum wins. End-to-end chain
verified in the decompiles, not just the arbiter in isolation.

### 1(c) Changeover tests + call-flag consistency — CONFIRMED
Shared threshold pool cell 0x1815e0f0 resolves to float **0.5** exactly.
- FUN_1815defc: any zone AEA4[i] − AE84[i] ≥ 0.5 (temp − coolSP ≥ 0.5) →
  flag AE4A = 1. Called in state AE45==3 → writes (AE44,AE45) = (2,5).
- FUN_1815de74: any zone AE64[i] − AEA4[i] ≥ 0.5 (heatSP − temp ≥ 0.5) →
  flag AE4B = 1. Called in state AE45==5 → writes (AE44,AE45) = (1,3).
- FUN_1815daaa: if demand arg > 0 and *AE44 == 2 → AE48 = 1, AE49 = 0;
  if *AE44 == 1 → AE48 = 0, AE49 = 1; else both 0. AE49 is set only in
  direction-1 states, AE48 only in direction-2 states. (Companion getters:
  FUN_1815ddd6 returns AE49, FUN_1815dddc returns AE48.)

## Claim 2 — Mode authority FUN_1815d67e, (AE44, AE45) @0xFFF8AE44 — **CONFIRMED**
Pool resolution: state read cell → 0xFFF8AE45 (AE45); both write pairs
(0x1815d8d0/0x1815d8cc and 0x1815db38/0x1815db3c) resolve to AE44/AE45 —
one (coarse, detailed) pair at 0xFFF8AE44. Full transition reading of the
1004-byte decompile:
- AE45==1: auto branch (arbiter runs when R==0) → (1,3) or (2,5).
- AE45==2 ↔ AE45==3 interconvert with AE44=1 (heat pair); AE45==3 →(defc)→ (2,5).
- AE45==4 ↔ AE45==5 interconvert with AE44=2 (cool pair); AE45==5 →(de74)→ (1,3).
- AE44 only ever written 1, 2, or 3; the (3,1) pair is the parked state,
  also the else/error default. Matches "AE45 1=AUTO, 2/3=heat, 4/5=cool".
Changeover delay: FUN_1815dfb0 calls the timer-arm primitive FUN_1809fde2
with value (uint)*0xFFF8AEC4 × 0x3c (60). AEC4 is loaded by FUN_1815dc40
through the field-store getter with field id **0x1B**. Delay = field 0x1B
minutes × 60, armed on transitions (dfb0 calls sit on the arbiter and
changeover paths in d67e; FUN_1815df8a polls the timer on states 3/5).
Mechanics CONFIRMED; "changeover delay" as the timer's role is the natural
reading of where it is armed/polled.

## Claim 3 — CD7D written from FUN_1815da86() — **CONFIRMED** (one refinement)
FUN_1815da86: if FUN_181abce0() (zone predicate: field 0x11E bit vs count of
nonzero bytes in an 8-byte array copied from 0xFFF83CB3) returns 0 → returns
*AE44; else returns FUN_181abdee() = *0xFFF8BB5C (pool 0x181abf8c resolves to
0xFFF8BB5C exactly). Fallback mirror CONFIRMED.
Refinement: the actual store lives in FUN_181f5d8a (stageL decompile + pools:
slots → FUN_181f6ffe, FUN_1815da86, 0xFFF8CD7D): `if (FUN_181f6ffe() == 0)
CD7D = FUN_1815da86();` — the write is gated by the claim-5 flag byte. When
the flag is 1, this function does not overwrite CD7D. FUN_181f5d8a then
branches on CD7D == 2 / == 1 / else with distinct capacity computations
(else-branch takes the max of both + floor), consistent with 1/2/3 semantics.

## Claim 4 — Record path (mirror 0xFFF82E0D, producer FUN_180ecb96) carries only {0,1,2} — **CONFIRMED** (bounded)
FUN_180ecb96 builds an 11-byte record in staging 0xFFF8796A — byte [0] =
param_3, [1..4] = param_1 BE32, [5..8] = param_2 BE32, [9] = param_4,
[10] = 0 — and copies 11 bytes to 0xFFF82E0D (pool 0x180ecc6c). Every direct
call site passes param_3 as a literal in {0,1,2} and nothing else:
FUN_180ec188 ×3 → 1; FUN_180ec36c → 1 and 2; FUN_180ec7ce → 1 and 0;
FUN_180ec850 → 0. Bounded caveat: five computed call sites via
FUN_180eb67e (users_mode_src.txt) are not literally inspectable in the
decompiles; no contrary value exists at any static site.

## Claim 5 — Byte 0x3C12EC64 behind FUN_181f6ffe is a {0,1} validity flag, NOT mode — **CONFIRMED**
Pool slot 0x181f7048 resolves to **0x3C12EC64** exactly. FUN_181f6ffe returns
the byte; FUN_181f6fee writes 0 to it; FUN_181f6ff6 writes 1 to it (8-byte
bodies, read in full). StageS census (users_dictmode.txt): this is the only
pool cell for 0x3C12EC64 in the corpus and those three functions are its
only users. Its sole consumer (FUN_181f5d8a) uses it as a boolean gate.
It cannot be a mode byte: its only writers write 0/1 and no mode value
(2/3) is ever stored. (FUN_181f4308 sets it to 1 via FUN_181f6ff6 at
ingestion — consistent with a validity flag.)

## Claim 6 — Requested-mode byte R (AE47 ← mirror 0xFFF82EED) — **CONFIRMED**
Source: FUN_1815dc40 copies 1 byte 0xFFF82EED → AE47 (pool 0x1815de24/28).
All consumers test AE47 through 16-byte getters:
FUN_1815dd88: R == 0; FUN_1815dda6: R == 1; FUN_1815dd96: R == 2;
FUN_1815ddb6: R ∈ {3,4}.
In FUN_1815d67e: R==0 gates the arbiter path (demand decides) in state 1;
R==1 drives transitions to AE44=1 pairs ((1,2) from state 4, (1,3) from
state 5); R==2 drives transitions to AE44=2 pairs ((2,4) from state 2,
(2,5) from state 3); in every state that tests it (2, 3, 4, 5),
R ∈ {3,4} (ddb6 true) writes (AE44,AE45) = (3,1) — parked; in state 1 the
machine is already at (3,1) and R∈{3,4} cannot leave it (dd88 requires
R==0). So 0=auto, 1=heat, 2=cool, 3 and 4 both park at (3,1). The 3-vs-4
name split (fan-only vs off) remains inference, as stage S stated.

## Claim 7 — CD49 / CD4B / CD4A / CD4C — **CONFIRMED**
- CD49: FUN_180c54d8 gate pool cell 0x180c562c → 0xFFF8CD7D; `if (CD7D != 2)
  CD49 = 0`. Output cell 0x180c561c → 0xFFF8CD49; all writes are 0, 1, 2 or
  a boolean comparison result (0/1). Staging output ∈{0,1,2}, gated
  CD7D==2 (cool side). CONFIRMED.
- CD4B: FUN_180c576c state cell 0x180c58c0 → 0xFFF8CD4B; writes only
  1, 2, 3, 4. Input differential *0xFFF8CB58 − *0xFFF8CABB against band
  constants resolved from the image: −5.0 / 0.0 / +5.0 with state-dependent
  offsets +4/+6/−1/+1/−6/−4 — a 4-level Schmitt quantizer. CONFIRMED.
- CD4A: FUN_180c5832 gate: CD7D (cell 0x180c58dc → 0xFFF8CD7D) != 2 OR
  *0xFFF8CB5C (cell 0x180c58e0) != 1 → CD4A := 0 and CD4C := 0. Output cells
  0x180c5d4c and 0x180c5b54 both → 0xFFF8CD4A; written values {0,1,2,3,4,5};
  inputs CD49 (cells → 0xFFF8CD49) and CD4B (cell → 0xFFF8CD4B).
  Arbitration state ∈{0..5}, runs only when CD7D==2 (and CB5C==1), else
  forced 0. CONFIRMED.
- CD4C: written only via cells 0x180c5b44 / 0x180c5d5c, both → 0xFFF8CD4C,
  both used inside FUN_180c5832; values 0/1 with the exact rule
  CD4C = 1 iff CD4A-in ∈ {1,2,3} (in==1 → 1; in ∈{2,3} → 1 unless CD4A
  already 4/5; in==0 → 0; in ∈{4,5} → 0). No external consumer found:
  stageE census (users2.txt) attributes both CD4C pool cells to
  FUN_180c5832 only, and the only candidate external function,
  FUN_180c5c7c, shows no CD4C slot in two independent decompiles (stageE
  decomp2, stageR) — it reads CD4A, not CD4C. Note: the stageS census file
  users_r_src.txt attributes cell 180c5d5c's use at 0x180c5c2a to
  "func 180c5c7c"; that is a function-boundary artifact of that project
  (raw bytes at 0x180c5c10–0x180c5c2e are a three-cell zeroing sequence;
  stageE's census attributes the same instruction to FUN_180c5832).
  CONFIRMED with the artifact noted.

## Claim 8 — SYSCTRL-49 rejection (no internal byte uses 0=heat or 5=off) — **CONFIRMED** (spot-check scope)
Targeted search of the mode cluster (FUN_1815d67e + helpers, FUN_181f5d8a,
FUN_180c5dd0 listing, FUN_180c54d8, FUN_180c5832):
- AE44 is written only 1/2/3; CD7D is compared only ==1 / ==2 / else in
  every consumer read (5d8a, 5dd0, 54d8 gate, 5832 gate).
- R (AE47) is compared ==0 (auto), ==1, ==2, ∈{3,4} — 0 means AUTO here,
  never heat.
- The value 5 appears only as AE45 detailed state (cool pair member) and
  as a CD4A arbitration state — never as a mode value meaning "off", and
  no mode byte is ever compared against 5.
No internal byte in the mode machine uses the infinitive/SAM encoding
0=heat … 5=off. CONFIRMED within the spot-check scope (mode cluster +
direct CD7D consumers), which is the scope stage S claimed.

## Summary
8/8 claims CONFIRMED, none REFUTED, none UNVERIFIABLE. Two bounded caveats
(claim 4 computed call sites; claim 8 spot-check scope) and two refinements
worth recording: (i) the CD7D store in FUN_181f5d8a is gated by the EC64
flag (claim 3 × claim 5 interaction, already implicit in stage S);
(ii) the stageS census's CD4C attribution to FUN_180c5c7c is a boundary
artifact — stageE's census and two independent decompiles agree CD4C is
internal to FUN_180c5832.
