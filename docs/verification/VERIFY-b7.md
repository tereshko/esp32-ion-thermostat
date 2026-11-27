# VERIFY-b7 — Independent re-derivation of FIRMWARE-ANALYSIS-B7.md claims

Method: fresh parsing written for this check (no reuse of firmware-re/audit or
B-7 scripts). Corpus parsed directly from `traces/*.jsonl` (JSONL frames:
ts/src/dst/func/reg/data). OAT channel located independently (see claim 3).
Gofinity checked by raw header-pattern scan + CRC-verified frame walk of the
boot triplet (CRC = reflected 0xA001, init 0, over F1F1..data, LE trailer —
validated on the file's first frames).

## Claim 1 — corpus size and write counts: CONFIRMED (with reconciliation)

- Files: **12** ✓.
- My count: **83,752 parseable frames**; the files contain **83,755 lines**,
  3 of which are unparseable (1 in sam-commissioning — 6,543 frames of 6,544
  lines; 2 in sam-control-test — 1,115 of 1,117). B-7's "83,755 frames" is the
  line count; the parseable-frame count 83,752 matches audit-2's independent
  recount. Substance unaffected.
- Writes (src 0x20, func 0x0C): **0414 → 325** ✓ exact; **060B → 327** ✓ exact.

## Claim 2 — payload rigidity, pair identity, distinct values, range: CONFIRMED (pair count differs)

- Rigidity: **0 nonconforming payloads out of 652**. Every 0414 payload is
  exactly `01 04 XX 01 03 20` (6 B); every 060B payload is exactly
  `01 04 XX 00 00 00 00` (7 B) ✓.
- Distinct XX values: **63** ✓ exact (same set in both tables).
  Range: **70–194** ✓ exact.
- Pairing: in my data **every** 0414 write has a 060B partner 17–757 ms
  earlier in the same burst (median Δ = −45 ms): **325 pairs, 325/325
  identical XX, 0 mismatches**. B-7's "153/153" identity claim is therefore
  confirmed and strengthened, but their pair *count* (153) does not
  reproduce under any pairing window (≥313 pairs even at a 0.1 s window;
  325 at ≥1 s). Their 153 evidently counts a subset; the identity itself
  holds universally.

## Claim 3 — not OAT: CONFIRMED (all numbers reproduced)

OAT channel found independently: ODU (0x53) answer to table **0302**,
big-endian u16 at bytes [2..3], value/16 = °F (range over corpus
65.1–71.1 °F). Sampling the last 0302 answer at each 0414 tick (n=325):

- Ticks with OAT ∈ [65.0, 66.5] °F: **n = 182** — exactly B-7's n.
  XX span over those ticks: **72–194** ✓ exact.
- Pooled Pearson r(XX, OAT) = **−0.228** (B-7: ≈ −0.23) ✓.
- Idle level at OAT ≈ 65 °F: Oct 29 coldstart plateau **145–146** ✓
  (B-7: ~146); Nov 3 phase3-validation files idle median **191–192**
  (validation2: median 192, span 190–194) ✓ (B-7: ~192). Same OAT,
  ~46-count different XX level — decisively not an OAT function.

## Claim 4 — not any polled channel: CONFIRMED in substance

Correlations at ticks vs the named channels (0302 u16 fields /16, 0305
commanded CFM, 0605 float):

| channel | r |
|---|---|
| 0302 field [6] (coil-side temp) | −0.314 |
| 0302 field [22] | −0.286 |
| 0305 CFM | −0.244 |
| 0302 field [18] | −0.188 |
| 0302 field [10] | +0.135 |
| 0302 field [14] | −0.128 |
| 0605 stage float | −0.089 |

All |r| ≤ 0.36 ✓. My own brute-force scan (every u16/f32 decoding at every
offset of every 0x44/0x53 answer table in the three long files) found 89
single-file hits with |r| > 0.5, max **0.66** — all misaligned decodings of
mostly-static tables (060A f32@109, 060E f32@18, 0302 u16@22). Every such
candidate flips sign or collapses across files (0302@22: −0.60 / +0.16 /
−0.11; 060E@18: +0.59 / −0.53; 060A@109: −0.66 / −0.39) — artefacts of
monotonic segments, not channels. B-7's literal "nothing above 0.6" is
slightly imprecise (single-file artefacts reach 0.66), but the substantive
claim — no polled channel explains XX — holds.

## Claim 5 — boot fingerprint: CONFIRMED (τ only loosely reproducible)

Every genuine thermostat boot in the corpus re-initialises XX at 70–72:

- coldstart (1F sweep at file +6 s): first XX = **72**
- full-install: first XX = **70**
- sam-reseat (post-reboot): XX = **72** (the file's only 0414 write)
- sam-commissioning (post-power-up, 1F sweep at +82 s): XX = **72**

Files with no boot start mid-state (146–192), as expected. Coldstart ramp:
72, 72, 78, 88, 97, 105, 112, 118, 123, 127, 130, 134, 136, 139, 141, 144,
145, 145… — delayed exponential-like climb to a 145–146 plateau in ~5.5 min
while equipment channels are flat ✓. τ is asymptote-sensitive: my fits give
**85 s** (log-linear, asymptote 146) to **~105 s** (pairwise median), up to
~166 s if the asymptote is assumed to be 160. B-7's "τ ≈ 2–3 min" sits at
or above the top of that range — the shape and endpoints reproduce exactly;
the τ number itself is only order-of-magnitude reproducible.

## Claim 6 — drift by mode: CONFIRMED (exact reproduction)

Classification from the live bus state at each tick (0305 heat-stage byte,
0605 float, 0305 CFM), deltas between consecutive ticks < 60 s apart:

- **Heat: n = 29 ticks, mean Δ = −0.76/tick, rises = 0** — exactly B-7's
  n, mean, and "never rises during a heat call" ✓✓.
- **Fan-only: n = 32, mean Δ = −0.47/tick** ✓ exact.
- **Idle: n = 234, mean Δ = +0.32/tick** ✓ exact.
- Cool: n = 17, mean −0.24, rises 6 / falls 6 — mixed ✓.
- Steady |Δ| ≤ 3 per tick: excluding the coldstart boot ramp (first
  420 s), the maximum |Δ| over all 312 consecutive deltas is **3**, zero
  violations ✓ (the only larger steps, up to +10, are inside the boot ramp).

## Claim 7 — not a counter / checksum / setpoints: CONFIRMED

- Not a counter: pooled consecutive deltas = 59 rises / 62 falls / 191 flat
  — non-monotonic, saturating ✓.
- Not a checksum: the 325 burst pairs are two frames whose remaining bytes
  differ completely (`0104XX010320` to the furnace vs `0104XX00000000` to
  the ODU, different destinations) yet carry identical XX in the same
  burst — a frame checksum cannot do that ✓.
- Not setpoints: in 400a-test-20261030-145554 the 400A answer payload is
  bit-constant across 6 answers / 23 min while XX moves 149→156 over 70
  ticks; a second constant stretch (phase3-validation2, 14 min) has XX
  moving 191–194 ✓.

## Claim 8 — gofinity-bootup.bin has zero 0414/060B writes: CONFIRMED (strengthened)

Raw scan of all 36,141 bytes: write-header pattern `00 0C 00 04 14` = 0,
`00 0C 00 06 0B` = 0. Stronger: the byte pair `06 0B` occurs **nowhere in
the file at all** (0 occurrences in any position). The pair `04 14` occurs
10 times, all as read-probe headers (`00 0B 00 04 14`, the commissioning
sweep probing table 0414) — never a write. Sanity patterns behave (0305
write headers found). That generation's dialect probes 0414 but never
writes 0414/060B ✓.

## Bottom line

No claim is REFUTED. Claims 3 and 6 reproduce to the exact published
numbers (n=182, span 72–194, r=−0.228; heat n=29 / −0.76 / 0 rises; fan
−0.47; idle +0.32). Four minor numeric discrepancies, none substantive:
(1) frame total is 83,752 parseable frames vs B-7's 83,755 (line count,
3 corrupt lines); (2) matched-pair count is 325, not 153 (identity holds
325/325); (3) boot-ramp τ fits to ~85–105 s for the natural asymptote vs
B-7's 2–3 min; (4) brute-force single-file artefacts reach |r| = 0.66 vs
B-7's "nothing above 0.6" wording — all sign-flipping misaligned
decodings. B-7's conclusion stands: XX is a thermostat-internal modelled
state, not a function of OAT or of any polled channel, and the emulator
synthesis recipe is unaffected.
