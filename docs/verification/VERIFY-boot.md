# VERIFY-boot — independent re-derivation of stage U (boot/commissioning, 0x0E)

Verifier: independent parse of primary data only (own JSONL parser; own gofinity
frame parser validated by CRC — reflected A001, init 0 — 1532/1532 frames OK,
36,141/36,141 bytes consumed). Report prose was not trusted; stage F's
`group_table.txt` (dumped from the flat image by `scan5_final.py`) was used for
claim 9's firmware half. Note: no `firmware-re/stageU/` artifact directory exists.

## Claim 1 — corpus: 19 captures, 101,352 frames — **CONFIRMED (with caveat)**
19 files = 12 session JSONL in `traces/` + 7 files in `traces/segments/`.
Valid-JSON frame counts sum to **exactly 101,352** (top-level 83,752 + segments
17,600). `wc -l` gives 101,355 — 3 lines are non-frame garbage (sam-commissioning
6,544 lines/6,543 frames; sam-control-test 1,117/1,115). Caveat: the 7 segment
files are split copies of coldstart (their counts sum to coldstart's 17,600), so
the corpus double-counts coldstart; distinct-session frames = 83,752.

## Claim 2 — B0: furnace boots first, autonomous 44→45 030A — **CONFIRMED**
Coldstart frames 0–5 are all `44→45 func 0B 030A` at ~45 ms spacing, before any
other device speaks (a `93→20 3B05` follows at +0.281 s, the 0x1F triplet at +6 s).

## Claim 3 — B1: ≈+6 s, 0x1F broadcast triplet, exact payloads — **CONFIRMED**
Coldstart: at **+6.001 s** `1F→F1 0C 0305` = 12×00; +6.039 `3E02` = `00`;
+6.076 `0605` = 7×00. Gofinity frames 0/1/2 are the identical triplet
(0305 12×00, 3E02 `00`, 0605 7×00), CRC-verified.

## Claim 4 — B2 sweep: cadence ≈95 ms; retry ×2 unanswered / ×1 answered; first ODU touch 061F→0x53
- Cadence — **CONFIRMED**: median inter-frame delta of the pre-handoff 0x1F sweep
  (108 frames) is exactly **95.0 ms** (mean 99.7 ms).
- First ODU touch — **CONFIRMED**: first frame to dst 0x53 is `1F func 0B 061F`
  at +12.756 s.
- Retry ×1 answered — **CONFIRMED**: all 7 answered poll targets were polled
  exactly once.
- Retry ×2 unanswered — **REFUTED as a universal rule**: of 43 unanswered
  targets, 34 were polled ×2, but **7 were polled ×4** — (46,030D), (46,031B),
  (46,0404), (5A,0326), (5A,0327), (5C,0326), (5C,0327), i.e. the zone/damper-class
  addresses get a second double-pass — and 2 were polled ×1 ((44,041F), (46,030A)).
  ×2 is the dominant base pattern, not the rule.

## Claim 5 — B3 handoff 0x1F→0x20 at ≈+16.7 s; gofinity frame 106/107 — **CONFIRMED**
Coldstart: first src=0x20 frame at **+16.695 s** (frame idx 122). Gofinity:
frame **106** is the last 0x1F frame, frame **107** the first 0x20 frame —
and both are the same probe (3E0A→0x0E, see claim 10): the handoff is seamless
mid-probe, exactly as stage U described.

## Claim 6 — B4: 0418 ×2 at ≈+62 s; boot-to-steady ≈62 s; first command burst +39.1 s / gofinity frame 646
- 0418 — **CONFIRMED**: `20→44 func 0C 0418 000000` at **+62.000 s and +62.045 s**,
  exactly two, nothing else in the capture.
- Boot-to-steady ≈62 s — **CONFIRMED** in the sense that the device-directed
  command phase opens at exactly +62.0 s (0418, then 0610/0612→53 at +66.0 s,
  first 0305 at +71.65 s).
- "First command burst at +39.1 s (ours)" — **REFUTED**: at +39.096/+39.131 s the
  only 0x20 writes are the **SYSTIME broadcast** (`0202`/`0203`→F1). No
  device-directed command write exists before +62.0 s. (+39.1 s is merely the
  first func-0C write of any kind.) This matches the doubt the errata agent had
  already recorded against the map's "39.10 — first command burst" row.
- Gofinity frame 646 — **CONFIRMED**: frame 646 is the first `20→40 func 0C 0305`
  write, payload `000000000000000000000078`.

## Claim 7 — 031C: zero in our captures; gofinity furnace frame 534, ODU from 584, byte 0 incrementing — **CONFIRMED**
Ours: **zero 031C frames of any function** in all 12 session captures.
Gofinity: first furnace 031C write (func 0C) is exactly **frame 534** (dst 0x40 —
that system's canonical furnace class; 37 furnace writes total, byte 0 constant
0x22). ODU 031C writes start exactly at **frame 584** (dst 0x50; 47 writes).
Byte 0 does rise, but in plateaus, not +1 per write:
0x10 (×10) → 0x19 (×5) → 0x1F (×5) → 0x20 (×6) → 0x2D (×5) → 0x2E (×4) →
0x2F (×7) → 0x35 (×5). Monotonic non-decreasing — "incrementing" in substance.

## Claim 8 — commissioned reboot: no configuration writes; 0316 → field store
- No configuration writes — **CONFIRMED for the installed equipment**: in the
  sam-reseat boot window (120 s from the first 0x1F frame) the only writes are
  the broadcast triplet (0305/3E02/0605→F1), the SYSTIME broadcast (0202/0203),
  and one `20→46 func 0C 031B` probe-write to the *absent* zone address 0x46.
  Nothing is written to 0x44 or 0x53. Devices are indeed configured by reading
  (0316 is read 142× in coldstart, 2× in reseat).
- "0316 → field store 0x1BC–0x1C3" — **UNVERIFIABLE from captures** (firmware-side
  claim; captures show only that 0316 is read, not where the values land).

## Claim 9 — 0x0E: never probed by our Ion; probed unanswered in gofinity; firmware bindings — **CONFIRMED**
- Ours: **zero frames to or from 0x0E in all 19 files** (83,752 distinct-session
  frames + segments).
- Gofinity: **110 frames to 0x0E** (first: 3E08 reads at frames 61–70),
  **zero frames from 0x0E** — probed, never answered.
- Firmware (stage F group table @0x182B5E3A, re-read from the dump): every 3Exx
  binding group has sub ∈ {0x0E, 0x50} and no other — 3E01/02/03/04/0A/0C/0D have
  both subs; 3E07/08/09/0B/0E exist **only** for sub 0x0E. The 25 groups of table
  0104 have subs {0x21–0x28, 0x3E, 0x40, 0x42, 0x50, 0x51, 0x52, 0x54, 0x56, 0x57,
  0x5B, 0x5F, 0x60, 0x61, 0x69, 0x80, 0x92, 0x94} — **no 0104 group for 0x0E**. ✓

## Claim 10 — gofinity: handoff probe is 3E0A; table 3E10 does not occur — **CONFIRMED**
3E10 frames in gofinity-bootup.bin: **0**. The 0x0E probe straddling the handoff
is 3E0A: frames 103–106 from 0x1F, frames 107–112 from 0x20, all `func 0B 3E0A`
to dst 0x0E, unanswered. The correction to `gofinity-bootup.md` is right.

## Score: 8 CONFIRMED, 1 REFUTED in part (claim 6's +39.1 s "command burst";
claim 4's ×2 retry is a dominant pattern with ×4/×1 exceptions), 1 sub-claim
UNVERIFIABLE from captures (0316 → field store, claim 8).
