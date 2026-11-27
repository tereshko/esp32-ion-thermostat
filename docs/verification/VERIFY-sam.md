# VERIFY — SAM (0x92) surface on the bus (stage V claims)

Independent re-derivation from PRIMARY data: the capture corpus was parsed from
scratch for this check (no report prose trusted). Date: 2026-11-26.

## Method / scope

- Corpus: the 12 top-level JSONL captures in `traces/` — **83,758 frames**
  total (3 file lines contained two glued JSON objects; decoded as separate
  frames). `traces/segments/` excluded (duplicate splits of coldstart).
  `traces/external/gofinity-bootup.bin` excluded: a different system (Bryant),
  while stage V's claims concern this installation.
- Dialect key, derived from the data itself: **func 0x0B = read request**
  (empty payload), **func 0x06 = read response** (payload), **func 0x0C =
  write**. "Initiated" frame = a frame not preceded within 2 s by a same-reg
  request from the peer (reply latency in the corpus: median 49 ms, p95 54 ms,
  so 2 s is a generous matching window).

## Claim 1 — thermostat initiates nothing to 0x92 in steady state; every 20→92 frame is a func 0x06 response

**CONFIRMED** (with the claim-5 carve-out documented below).

- Frames involving 0x92: 4,214. Direction 0x20→0x92: **1,861 frames =
  1,855 × func 0x06 (99.68%) + 6 × func 0x0B**.
- Per file, every steady-state capture (all 400a-test, phase3-validation,
  sam-control-test files) shows 20→92 as **100% func 0x06**.
- The only 6 exceptions are func 0x0B reg **0104** probes, all inside
  boot/discovery windows (coldstart ×4, sam-commissioning ×1, sam-reseat ×1) —
  exactly the traffic claim 5 carves out.
- One boundary artifact: a lone func 0x06 3B02 reply in the first second of
  `400a-test-20261030-141705` whose request predates the capture start. It is
  still a response, not an initiation.

## Claim 2 — zero occurrences: 3B0E anywhere; thermostat writes (func 0x0C) to SAM; exception responses func 0x15 from furnace/ODU

**CONFIRMED on all three.**

- reg `3B0E`: **0** occurrences in 83,758 frames (any src/dst/func).
- func 0x0C with dst 0x92: **0** (from any source; 0x20→0x92 writes: 0).
- func 0x15: **0** anywhere in the corpus (from 0x44/0x53: 0).
- Context: bus writes exist only in the opposite direction — 47 × func 0x0C
  **from** 0x92 to the thermostat (400A ×36, 3B03 ×8, 3B02 ×3).

## Claim 3 — SAM polls 3B02/3B03 alternately at ≈3 s; ≈8% unanswered; replies zero-filled

Split verdicts:

- Poll mechanism — **CONFIRMED**: polls are func 0x0B requests 0x92→0x20;
  **1,811 polls** of the pair (3B02 ×905, 3B03 ×906) across 10 files.
- Cadence ≈3 s — **CONFIRMED**: median interval between consecutive polls of
  the pair = **3.00 s in every file** (means 2.97–3.26 s, commissioning file
  3.76 s due to wizard gaps); per-table cadence 6.02 s (3B02) / 6.03 s (3B03).
- Alternation — **CONFIRMED, stronger than claimed**: **100.0%** of
  consecutive poll pairs switch table (1,801/1,801).
- Zero-filled replies — **CONFIRMED**: 3B02 replies 865/865 are 29 bytes,
  all-zero; 3B03 replies 868/868 are 150 bytes, all-zero. (Same pattern for the
  other SAM-family tables: 3B04 → 11 B all-zero ×19; 3B05 → 11 B all-zero ×22.
  Real tables answer real content: 400A 35 B, 4202 72 B, 4012 7 B, 0104 120 B.)
- **Unanswered ≈8% — REFUTED.** Measured: **79/1,811 = 4.36%** (2 s matching
  window; identical at 5 s). Excluding `sam-reseat` (thermostat physically off
  its wall plate for ~36 s of that file): 66/1,794 = **3.68%**. Clean
  steady-state files only: 43/1,536 = **2.80%**. No defensible window
  reproduces ~8%: a 10 s window yields 2.04% only by absorbing the next
  cycle's reply (same table repeats every ~6 s) as a false match. The
  qualitative claim (a small minority of polls go unanswered) holds; the
  figure is overstated ≈2×.

## Claim 4 — same zero surface served to 0x93; 0x93 reads 3B05 every ~300 s; thermostat answers 11 bytes

- 3B05 cadence — **CONFIRMED**: 0x93→0x20 func 0x0B 3B05 polls ×6, all in
  coldstart; after the boot-phase first poll the intervals are exactly
  **300.0 s** (median 300.0 s).
- Answer length — **CONFIRMED**: 5 replies, each **11 bytes, all zero**. The
  first poll (16:57:51Z, thermostat still in its 0x1F boot phase) went
  unanswered.
- "Same zero surface to 0x93" — **PARTIALLY CONFIRMED / partly
  UNVERIFIABLE**: 0x93 never requested 3B02/3B03 anywhere in the corpus, so
  that exact surface toward 0x93 is untested by the data. The one SAM-family
  table 0x93 did read (3B05) returned the identical 11 zero bytes the
  thermostat serves to 0x92 (22/22). Supporting evidence that the surface is
  reader-independent: real tables return real content to 0x93 exactly as to
  0x92 (0x93's reads in `400a-test-20261030-141705`: 4001 → 59 B, 0101 →
  25 B, 4201 → 21 B, 4601 → 45 B, all non-zero).

## Claim 5 — thermostat→SAM traffic exists only as 0104 probes during discovery

**CONFIRMED.**

- Initiated 0x20→0x92 frames in the whole corpus: **exactly 6**, all func 0x0B
  reg 0104, all inside discovery windows:
  coldstart 16:58:24Z ×2 and 16:58:45Z ×2 (post-handoff sweep),
  sam-commissioning 18:34:38Z ×1, sam-reseat 19:12:40Z ×1 (each ~22 s after the
  corresponding 0x1F-persona probe). Plus 4 × 0104 probes from the 0x1F boot
  persona itself.
- Each probe was answered by the SAM with a func 0x06 0104 identity payload
  ("SYSTEM ACCESS MODULE … Oct 29 2026 … InfinitESP--SAM", 120 B) — 4 such
  answers (to 0x1F ×2, to 0x20 ×2; repeated probes in coldstart went
  unanswered because the node was not yet acting as SAM in that capture).
- Every other 20→92 frame is a response (classifier in Method; sole boundary
  case is the capture-start reply under claim 1).
- Context that does not affect the claim: the SAM itself polls the
  thermostat's 0104 about every ~280 s (20 polls / 19 replies; thermostat
  identity "INFINITY NEXT GEN UI … CESR******-**.79 SYST0101CW") — that is
  SAM-initiated. The SAM also polls the ODU (0x53) directly, reg 0304 ×180
  across all files — SAM↔ODU traffic, not thermostat→SAM.

## Claim 6 — SYSTIME broadcast cadence ≈60 s to F1

**CONFIRMED.**

- Broadcasts src 0x20 dst 0xF1: reg 0202 ×132 + reg 0203 ×131 (paired).
- 0203 inter-arrival: **median 60.2 s, mean 60.0 s** over 119 intervals across
  11 files; per-file medians 58.3–61.1 s.

## Summary

| Claim | Verdict |
|---|---|
| 1. Nothing initiated to 0x92 in steady state; 20→92 = func 0x06 responses | CONFIRMED (6 discovery-probe exceptions = claim 5) |
| 2. Zero 3B0E / zero writes to SAM / zero func 0x15 | CONFIRMED |
| 3a. Poll cadence ≈3 s, alternation | CONFIRMED (alternation 100%) |
| 3b. Replies zero-filled (3B02 29 B, 3B03 150 B) | CONFIRMED |
| 3c. ≈8% of polls unanswered | **REFUTED** — measured 4.36% (2.80% clean steady-state) |
| 4a. 0x93 reads 3B05 every ~300 s, answer 11 B | CONFIRMED |
| 4b. Same zero surface served to 0x93 | PARTIALLY CONFIRMED (3B05 yes; 3B02/3B03 never requested by 0x93 — UNVERIFIABLE) |
| 5. Thermostat→SAM only as 0104 discovery probes | CONFIRMED |
| 6. SYSTIME broadcast ≈60 s to F1 | CONFIRMED |
