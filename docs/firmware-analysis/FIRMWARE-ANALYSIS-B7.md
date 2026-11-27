# B-7 — The 0414/060B shared byte: offline capture analysis

Closes audit gap **B-7** (FIRMWARE-AUDIT.md §4.1) by offline analysis only.
Corpus: all 12 captures in `traces/` (83,755 frames, 2026-10-29 …
2026-11-03). The `segments/` copies of coldstart were excluded to avoid
double counting. Method scripts were run from scratch space; this file
is the only project file created.

## 0. Verdict

**The byte is a thermostat-internal modelled temperature state — not a
function of outdoor temperature, not of any polled equipment channel,
not of the setpoints, and not a counter, checksum, or flag field.**
Every hypothesis that is testable from bus data is rejected below with
numbers. The exact physical referent cannot be named from this corpus,
because the thermostat's own local inputs (its indoor temperature and
humidity sensors) appear **nowhere** in the captures — that is the
bounded residue, with the deciding observations listed in §5.

For the emulator this gap is nevertheless **closed in practice**: no
equipment behaviour in 83,755 frames observably depends on the byte
(§4), so a plausible synthesized value is indistinguishable from the
real one in every captured scenario.

## 1. The byte, exactly [OBS]

- `0414`→44 (6 B) is always `0104 XX 010320`; `060B`→53 (7 B) is always
  `0104 XX 00000000`. Every byte except `XX` (payload byte [2]) is rigid
  across the whole corpus.
- Counts: 325 × `0414` + 327 × `060B` = 652 writes; one pair per ~20 s
  tick (the pair members land ~0–1 s apart inside the burst).
- Pairing test: 153 pairs matched within 3 s in the same file —
  **153/153 carry the identical XX, zero mismatches**. (Unpaired events
  are capture edges and the sam-commissioning power-off window.) It is
  one thermostat-owned variable broadcast to both devices.
- XX takes **63 distinct values** (matching the audit's "63 distinct
  payloads each"), range **70–194** over the full corpus; the coldstart
  file alone spans 72–153, as the audit stated.

## 2. Rejected hypotheses

### 2.1 Not OAT — under any encoding [OBS]

Any encoding (raw, offset, scaled, inverted) is still a *function* of
OAT, so the decisive test is OAT-matched contrast:

- Ticks with OAT (ODU `0302` tag 0x111, ÷16 °F) inside [65.0, 66.5] °F:
  **n = 182, XX spans 72–194** — essentially its full range at one OAT.
- Pooled Pearson r(XX, OAT) = **−0.23** (n = 325); per-file signs and
  magnitudes wander (−0.12 / −0.54 / −0.08 in the three long files).
- Cross-day: 2026-10-29 idle settles at XX ≈ 146 (OAT 65.2); 2026-11-03
  idle sits at XX ≈ 190–194 (OAT 65.1–66.6). Same OAT, 46+ apart.

### 2.2 Not any polled equipment channel [OBS]

LOCF-joined at all 325 ticks, Pearson/Spearman vs XX:

| Channel | Source | Pearson | Spearman |
|---|---|---|---|
| OAT | ODU 0302 tag 0x111 | −0.23 | −0.24 |
| Outdoor coil temp | ODU 0302 tag 0x112 | −0.31 | −0.30 |
| Suction line temp | ODU 0302 tag 0x130 | +0.14 | +0.04 |
| Discharge line temp | ODU 0302 tag 0x145 | −0.29 | −0.18 |
| Unidentified tag 0x14B | ODU 0302 | −0.19 | −0.05 |
| Superheat channel | ODU 0302 tag 0x14A | −0.13 | +0.24 |
| Suction pressure (PSI) | ODU 0303 tag 0x130 | +0.14 | +0.04 |
| Commanded CFM | 0305 [4..5] | −0.24 | +0.15 |
| Blower RPM | IDU 0306 [1..2] | −0.24 | +0.11 |
| Compressor command | 0605 float | −0.09 | +0.36 |

Per-file signs flip (discharge temp: +0.16 coldstart, −0.60 in
400a-test-145554, −0.11 in phase3-validation2) — the weak pooled values
are co-drift artefacts, not coupling. A brute-force scan of **every**
byte / BE16 / LE16 / float32 field of **every** answer frame and every
thermostat write in the three long files found no channel with
|r| > 0.6 except the two writes themselves (r = 1.000, trivially).

Two suggested channels do not exist in this corpus at all: the `0420`
broadcast (0 frames in 83,755) and any indoor RH/temperature channel —
`3B02`/`3B03` are served as zeros (unregistered SAM), `3D02` was read
once and never answered, `3D03` never appears, and the furnace `0302`
answer is a single constant payload (`041100000000000000000000`)
corpus-wide. **The corpus contains no indoor temperature and no
humidity data whatsoever.**

### 2.3 Not the setpoints [OBS]

400A rows (served replies + SAM writes) LOCF-joined where present:
r(XX, manual heat SP) = +0.28 (400a-test-141705), −0.42
(phase3-validation2), +0.85 (phase3-validation3, n = 11, both series
co-trending under the test script — a confound, not coupling). XX
wanders 149–156 for 30 min with 400A bit-constant (400a-test-145554),
and setpoints step 71→79 while XX sits at 190–194
(phase3-validation2). No consistent relationship.

### 2.4 Not a counter [OBS]

Non-monotonic (rises and falls), saturates for hours (190–194 for
23 min), and its drift direction is mode-dependent (§3). A counter
does none of these.

### 2.5 Not a checksum [OBS]

The same XX appears in the same tick in two frames whose remaining
bytes differ (`…010320` vs `…00000000` tails, different lengths,
different destinations) — 153/153 pairs. A checksum over either payload
would differ between the pair members. XX also moves in smooth ±1
steps (§3); checksums avalanche.

### 2.6 Not a status/flag bitfield [OBS]

63 distinct values, reached by ±1 steps and slow drift through
intermediate values; the same value (e.g. 145) occurs in idle, fan and
post-cool states alike. No per-state value sets exist to decode.

### 2.7 Not time of day [OBS]

Same afternoon hours on three days sit at incompatible levels
(2026-10-29 14:54 → 158–165 and rising; 2026-10-30 14:17 → 152–161;
2026-11-03 14:25–14:56 → 190–194), and within single files XX is flat
for 20–30 min stretches. No diurnal pattern is visible at this scale.

### 2.8 Humidity — untestable offline

No RH channel exists in the corpus (§2.2), so an indoor-RH (or
dew-point / enthalpy) driver can be neither confirmed nor rejected.
It remains a live candidate for the *input* of the state in §3,
alongside the thermostat's own room-temperature sensor.

## 3. What the byte does — positive characterization [OBS]

- **Boot initialization at room temperature.** After every observed
  thermostat boot the first value is 70–72: coldstart 72,
  sam-reseat 72, sam-commissioning (post-wizard) 72, full-install 70.
  In coldstart the displayed room temperature was 72 °F — the state
  initializes at (or indistinguishable from) the thermostat's own
  indoor temperature reading. [INF: identity of the init value with
  room temp rests on that one confirmed reading plus three
  70–72 landings.]
- **Smooth, slow, analog dynamics.** Per-20 s-tick deltas (n = 312):
  191 zero, +1 ×41, −1 ×38, ±2 ×26, ±3 ×7, and +4…+10 only on the boot
  ramp. Steady-operation |Δ| ≤ 3 per tick.
- **Boot ramp.** From 72 it climbs 72 → 78 → 88 → 97 → 105 → … → 145
  in ~6 min at idle with every equipment channel flat — a delayed,
  exponential-like approach (τ ≈ 2–3 min) toward ~146–160. It is
  computed, not sensed: nothing physical in the system warms up then.
- **Mode-dependent drift** (mean ΔXX per tick, by the mode entered):
  heat **−0.76** (29 ticks: 0 up, 14 flat, 15 down — *never rises
  during a heat call*), fan **−0.47**, cool **−0.24** (mixed: the one
  captured call rises 146 → 153 in its first ~2 min, then declines
  steadily to 142), idle **+0.32** (48 up, 161 flat, 25 down — net
  recharge at rest).
- **Long memory.** The level encodes history over hours: post-cool
  coldstart decays to ≈ 121 and stays; an unobserved afternoon later
  (sam-commissioning, 14:32) it sits at 180; the 2026-11-03 session
  lives at 164–194 all afternoon, falling ~2/tick through a heat call
  (validation3: 190 → 164 in 6 min).

[INF] Together: a first-order-style modelled temperature in °F (the
unit per InfinitESP's header note on `060B`, from independent systems),
integrating inputs the thermostat has locally — its own indoor
sensors and/or an internal equipment model — discharged by equipment
operation (heat fastest) and recharging at rest. This is consistent
with, but does not prove, InfinitESP's upstream guess for the same
register: *"varies independently of OAT and zone setpoints … likely a
refrigerant-loop coil/discharge control target"* (their installs show
25–115 °F; ours extend to 194, so if it is the same quantity its range
is equipment/firmware-dependent).

Cross-system check: the gofinity boot capture (Bryant Evolution 2014,
furnace 0x40 / two-capacity ODU 0x50; 1,532 frames re-parsed for this
note, 0 skipped) contains **no `0414`/`060B` writes at all** — that
generation's dialect uses 3E/05xx ODU tables instead. It offers no
data point for this byte.

## 4. Emulator consequence [OBS/INF]

Across all captures, calls start, stage, and stop identically at XX
levels from 70 to 194; neither device ever answers, flags, or faults
in correlation with the byte, and stage T/J found no thermostat-side
consumer logic for the *receiving* end to honour beyond the write
itself. An emulator may therefore emit a synthesized state — e.g.
init at room temperature, +0.3/tick at idle, −0.8/tick during heat,
−0.5/tick fan, clamped to ~70–195 — or, on the archive's evidence,
even a constant, with no observable behavioural difference. B-7 does
not block coding; it only leaves the byte's *name* open.

## 5. Bounded residue — what would decide the exact semantics

Any **one** of these settles it; none is in the current corpus:

1. A capture logged simultaneously with the thermostat's own indoor
   temperature **and** RH (wall display readings, or a SAM ASCII
   session), spanning an idle soak and a heat call — allows direct
   regression of XX against the two local inputs it most plausibly
   integrates.
2. A capture at constant OAT with indoor conditions deliberately
   swung (humidifier on/off; windows open in winter) — separates an
   RH/enthalpy driver from a room-temperature/model driver.
3. A long (multi-hour) idle soak capture after a known cold boot —
   pins the idle asymptote and time constant, testing whether the
   asymptote is a fixed parameter or itself drifts with indoor
   conditions.
4. Firmware-side: if a future stage names the RAM cell that stages
   the `060B`/`0414` blobs (producer is runtime-bound per stages
   F/N/AA), the fingerprint to match is §3: boot init ≈ room temp,
   τ ≈ 2–3 min, drift −0.76/+0.32 per 20 s (heat/idle).

## Appendix — counts

| Item | Count |
|---|---|
| Captures analysed | 12 (83,755 frames) |
| `0414` writes / `060B` writes | 325 / 327 |
| Matched pairs, XX identical | 153 / 153 |
| Distinct XX values | 63 |
| XX range (corpus / coldstart) | 70–194 / 72–153 |
| Ticks with full channel join | 325 |
| `0420` frames in corpus | 0 |
| `3D03` frames in corpus | 0 |
| gofinity frames re-parsed / `0414`+`060B` found | 1,532 / 0 |
