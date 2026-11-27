# VERIFY-map — post-errata protocol map vs primary sources

Date: 2026-11-26. Object: `THERMOSTAT-PROTOCOL-MAP.md` as it stands after
errata E-1…E-22 (633 lines). Method: independent re-measurement from
primary sources only — the capture corpus (`traces/*.jsonl`, 12 top-level
files, **83,752 parsed frames**; `traces/segments/` are split copies of
coldstart), `traces/external/gofinity-bootup.bin` (own parser, CRC
reflected 0xA001 init 0), and `firmware-re/stageB/flat.bin`. The map and
its errata changelog were treated as claims, not evidence. Scripts:
`firmware-re/verify/verify_map.py`, `verify_map2.py`.

---

## REFUTED — read this first

**R1. §(c) boot table row "39.10 — First 10 s command-write burst
(0305 etc.)" is wrong.** In the coldstart capture, the first func-0C
write from 0x20 occurs at **+39.096 s** and it is the SYSTIME broadcast
(`0202` = `172803` to F1, `0203` at +39.131) — no command burst exists
at that time; 0x20 is still mid-sweep (frames +37…+42 s are sweep reads
to 46/58/55/5A/5C/60/61/80/3F). The first `0305` write from 0x20 is at
**+71.650 s** from capture start (= **+65.649 s** from 1F start, idle
payload, [11] already 0x78). Corollary: §(c) obligation 3's "first
demand writes ~22 s into it [the 0x20 phase]" is also wrong — the first
demand write is **54.96 s** into the 0x20 phase; the ~22 s figure
(39.096 − 16.695 = 22.40 s) is the position of the SYSTIME write, which
is what the 39.10 row actually measured. The origins note's anchor
(first 0305 = +65.6 s from 1F start) is the correct one (see C6).

**R2. §(d)'s reseat claim is stale: the "0 KB capture" exists and
records the exact event §(d) says is unrecorded.** §(d) states the
~30 s wall-plate reseat "produced a 0 KB capture file (capture stream
never started), so there is no recording of a live system losing only
its thermostat." On disk: `traces/sam-reseat-20261029-151123.jsonl`,
**1,611 frames**, recovered 2026-10-30 (per `traces/INDEX.md`). It
records a live-bus, thermostat-only outage: SAM (0x92) polls go
unanswered **19:11:36.999Z–19:12:12.999Z (~36 s, 14 polls)**, the only
funcs present are 0B/06/0C (no fault frames of any kind), no furnace
frames appear during the silence (one ODU `0304` answer at the boundary
answers a pre-silence read), and recovery is a full 1F recommissioning
(first 1F frame 19:12:13.318Z). G5's "the reseat case — its capture is
the 0 KB file" is refuted by the same file. Consequence for G1: its
framing ("nothing in the archive shows a live system losing only its
thermostat") is outdated — a ~36 s thermostat-only outage with zero
peer reaction **is** on record; the comm-fault timeout itself remains
unmeasured (36 s produced no reaction, so the timeout is > 36 s or
nonexistent at that scale — the archive now bounds it from below).

**R3. §(a) irregular tier: furnace `0302` "Answer 24 B, slowly varying"
— wrong on both facts.** The furnace's `0302` answers are **12 B**
(payload `041100000000000000000000`) and **constant**: exactly 1
distinct payload across 1,255 answers in the corpus. (The 24 B figure
belongs to the ODU's `0302` answers, which do vary.) The read count
(277× in coldstart) is correct.

**R4. §(e) `061F` "fields at offsets ~40–52 change first" — wrong
offsets.** Measured against the idle-constant payload, the byte offsets
that vary during the cool segment are exactly
**{17, 18, 19, 20, 30, 31, 32, 33, 58, 59, 60, 61}**; nothing in
40–52 ever changes. This matches stage T's correction; no erratum
covered this line.

**R5. §(a) "5 of 879 steady reads in the sample went unanswered —
0.6 %" — wrong count.** Segment 05 has 879 reads from 0x20; **878**
are answered (exactly the map's own latency n=878), and **1** is
unanswered (0.11 %) under two independent pairing rules (answer within
1 s; answer before the next read of the same table). The map's "5" is
internally inconsistent with its own n=878 (878 + 5 > 879).

**R6. §(e) heat example `01000000048E…` does not exist.** Zero
occurrences in coldstart and in the full 83,752-frame corpus: stage
byte 1 and CFM 1166 never co-occur (CFM 1166 appears only with stage
byte 0 — fan-only and heat transitions). The other three listed heat
examples exist (`010000000180…`, `020000000651…`, `00000000048E…`).

**R7. §(e) `061F` "all 168 reads in segments 01/02/06" — wrong count.**
Measured: **160 reads / 161 answers** across segments 01+02+06. The
companion claim "except 3 frames" is confirmed: exactly 3 non-modal
answers, all in segment 06.

**R8. §(a) `0303` row's status "[SRC]-only, unverified … (no payload
example exists in this map)" is stale.** 0x20 polls `0303` from the
ODU **1,314×** in the corpus and receives **4 B answers — 96 distinct
payloads** (e.g. `01300BB0`, `01300C10`), i.e. a live, varying table.
The field semantics remain [SRC], but the register is not unverified
on the wire. (E-10's firmware-side annotation — 0303 has binding
groups despite catalog absence — is a separate claim and stands.)

**R9 (numeric). §(b)'s "~75,000 captured frames" matches no counting
of the current archive.** The 12-file corpus is **83,752** parsed
frames (audit-2's figure reproduced exactly). The underlying fact the
number supports — zero 3B02/3B03 mirror writes from the thermostat —
was verified over all 83,752 frames (0 occurrences, any dst incl. F1),
so the conclusion stands; the figure should read ~83,750.

---

## Check (1) — §(a) frame inventory spot rows

Verdicts per row (all counts over the full corpus unless noted):

| Row | Verdict | Evidence |
|---|---|---|
| `0605` 7 B, [0..3] float, [4] call-state, [5]=0, [6]=1 directed / 0 broadcast | **CONFIRMED** | 651 directed writes (dst 53): [5]=0 in 651/651, [6]=1 in 651/651, [4] ∈ {0,1} (571/80); floats {0.0 ×616, 5.0 ×34, 3.0 ×1}; 25 broadcast writes (dst F1): [6]=0 in 25/25; all 676 writes are 7 B |
| `0305` [11]=0x78 steady-state, 0x00 in SystemInit + commissioning (25 frames) | **CONFIRMED** | 652 src-0x20 writes with [11]=0x78; exactly **25** frames with [11]=0x00, all all-zero payloads: 3 SystemInit broadcasts (1 each in coldstart, sam-commissioning, sam-reseat) + 11 + 11 src-0x20 writes in the two commissioning windows (sam-commissioning, sam-reseat) |
| `0305` write itself: 12 B, 20→44, func 0C | **CONFIRMED** | 674 src-0x20 writes, all 12 B |
| `0104` answers 120 B (44 and 53) | **CONFIRMED** | 2,510 / 2,483 answers, all 120 B, each a single distinct payload |
| `0306` answer 10 B | **CONFIRMED** | 2,498 answers, all 10 B |
| `030A` (44) answer 14 B, constant `014F4F02001F006B000010100115` | **CONFIRMED** | 2,499 answers, 1 distinct payload, byte-identical to the map's string |
| `0302` (53) answer 24 B, TLV, drifts | **CONFIRMED** | 1,316 answers, all 24 B |
| `0302` (44) answer "24 B, slowly varying" | **REFUTED** | see R3 (12 B, constant) |
| `0307` read answer 3 B, always `000000` | **CONFIRMED** | 1,504 answers, 1 distinct payload `000000` |
| `0307` write 4 B `00000000` (distinct from read) | **CONFIRMED** | 650 writes, 1 distinct payload |
| `061F` answer 81 B | **CONFIRMED** | 1,490 answers, all 81 B |
| `0316` (44) answer | **CONFIRMED** (length 14 B; map claims no length) | 597 answers, all 14 B |
| `0304` (53) answer 16 B | **CONFIRMED** | 775 answers, all 16 B |
| `030D` (44) answer 7 B zeros | **CONFIRMED** | 597 answers, 1 distinct payload (7 zero bytes) |
| `0403` write 4 B `00010100` constant; `0409` write 4 B `00010000` constant | **CONFIRMED** | 650 writes each, 1 distinct payload each, byte-identical |
| `060D` write 1 B, `02` in calls / `00` idle & fan-only | **CONFIRMED** | corpus payloads {`00` ×140, `02` ×511}; segment 02 (fan-only): 23/23 `00`; segment 06 (heat): 35 `02` |
| `0610` `00000000`, `0612` `22B80000000000000000`, `061A` `01`, `061E` `0F3FD851EC06000000` — all constant | **CONFIRMED** | 651 writes each, exactly 1 distinct payload each, byte-identical to the map |
| `060B` 7 B `0104XX00000000` / `0414` 6 B `0104XX010320`, XX identical at the same tick | **CONFIRMED** | 327 / 325 writes, 100 % pattern-conforming; nearest-tick pairing per file: **325/325 identical XX**; coldstart XX range 72–153 as printed |
| `031D` write 1 B `01`, 50× in coldstart | **CONFIRMED** | exactly 50, all `01` |
| `0418` boot-only write 3 B `000000`, twice | **CONFIRMED** | exactly 2 in coldstart, at +62.0 s (sweep phase, cf. stage U's ~+62 s) |
| SYSTIME `0202`/`0203` 3 B to F1, period 55.6–61.0 s, median ≈60.2 | **CONFIRMED** | 27 each in coldstart, all 3 B to F1; intervals min 55.6, median 60.3, max 61.0 (median differs by rounding only) |
| Frame inventory: only funcs 0B/06/0C on the bus | **CONFIRMED** | over all 83,752 frames: {0B: 39,566, 06: 36,414, 0C: 7,772}; func 0x15: **0**; reg 3B0E: **0** |

Firmware-side note in §(a) (stage AA): the wire lengths it predicts
(0305 12 B, 0605 7 B, 061E 9 B, 0307 write 4 B, 060D 1 B) are all
confirmed on the wire above. The CRC claim was spot-verified from
primary sources: the nibble tables stored at `0x182B598C`/`0x182B59AC`
in `flat.bin` are **byte-identical** to the generated reflected-0xA001
nibble tables, and the table-driven CRC reproduces the gofinity wire
CRC on **1,532/1,532** frames. Builder/walker addresses and DIR-B blob
addresses are Ghidra-level claims — **UNVERIFIABLE** by the cheap
methods of this pass (audit-2 re-derived them).

## Check (2) — the 677 deduplicated 0305 count

**CONFIRMED, exact.** Func-0C `0305` writes in the 12 top-level files:
**677** (674 from 0x20 + 3 from 0x1F). Including the segment copies the
raw count is **832**; deduplicating on the full frame tuple across all
19 files returns **677**. Both audit figures (677 / 832) reproduce.

## Check (3) — §(b) SAM claims

- "No 3B02/3B03 broadcast mirror write in ~75,000 frames": the **fact
  is CONFIRMED** — zero writes from 0x20 to `3B02`/`3B03` to any
  destination (incl. F1) in the corpus; the **number is REFUTED**
  (R9: basis is 83,752 frames, not ~75,000).
- Served `3B02`/`3B03` zeros: **CONFIRMED** — 865 replies of 29 B and
  868 replies of 150 B to the SAM, **100 % all-zero**.
- "`3D02` slow-poll reads were never answered": **CONFIRMED with a
  caveat** — exactly **1** `3D02` read exists in the entire corpus
  (from 0x92, in 400a-test-20261030-141705) and it drew **0** answers.
  The plural "reads" overstates the sample; the fact stands at n=1.
- Cadence note: **CONFIRMED as measured for this archive** — in
  sam-commissioning the SAM makes **129 reads of each table** (258
  combined); per-table median gap 6.00 s, combined-stream median gap
  **3.00 s**, i.e. the map's "every ~3 s alternating (129 reads /
  16 min)" is exact. The "real SAM ≈65 ms" and "infinitive 500 ms × 5
  retries" figures are documentary, not measurable here —
  **UNVERIFIABLE from captures**, but the pointers check out
  (FIRMWARE-ANALYSIS-V.md lines 124/292 and 157–158;
  SAM-REGISTRATION-RESEARCH.md lines 44/321).
- Supporting rows: served `400A` payload byte-identical to the map's
  35 B string (×4 in the SAM captures); `4012` = `3C50001F001E1E` ✓;
  `4202` = 72 B with the printed prefix ✓; `3B04`/`3B05` served as
  11 B zeros ✓; control-test SAM writes `3B03` ×6 (150 B) and `3B02`
  ×1 (29 B) — exactly as §(b) states ✓; the `00000C`/`000010`
  change-flag reading is consistent with those payloads.
- 0x20 `0104` identity: **CONFIRMED in content** — 19 answers, 1
  distinct payload; `INFINITY NEXT GEN UI` at [0:24],
  `CESR******-**.79` at [48], `SYST0101CW` at [64], serial
  `3320********3320` at [84]/[96] with asterisks to byte 120. (The
  map's hex block is schematic in its line lengths; every decoded
  field it prints matches byte-for-byte.)
- Node 0x93: **CONFIRMED** — 6 `3B05` reads in coldstart, steady gaps
  299.95–300.51 s (the first gap is the 196.28 s boot gap), 5 answers
  of 11 zero bytes, first answer at +196.6 s.

## Check (4) — §(c) boot anchors (coldstart, t0 = first frame)

| Anchor | Map | Measured | Verdict |
|---|---|---|---|
| First 1F frame | +6.00 s | **+6.001 s** | CONFIRMED |
| Last 1F frame | +16.67 s | +16.666 s | CONFIRMED |
| First 0x20 frame | +16.69 s | +16.695 s | CONFIRMED |
| Handoff gap | "20 ms after 1F stops" | **29 ms** | minor numeric slip |
| First steady read 20→44 `0104` | +23.95 s | +23.951 s | CONFIRMED |
| Row "39.10 — first command-write burst" | +39.10 s | first 0x20 write at +39.096 s is **SYSTIME**; first `0305` at **+71.650 s** | **REFUTED (R1)** |
| First 0x20 `0305` (origins note) | +65.6 s from 1F start | **+65.649 s** | CONFIRMED |
| Last sweep probe | +61.76 s | +61.761 s | CONFIRMED |
| 44→45 bursts | 0, +62.3, +124.1, +185.0, +247.5, 6 reads each | 0, +62.327, +124.109, +185.001, +247.488; sizes 6,6,6,6,6 | CONFIRMED |
| 0x93 first read / first answer | +0.28 s / +196.6 s | +0.281 s / +196.6 s | CONFIRMED |

**Ruling on the known leftover:** the capture shows the +39.10 s event
is the thermostat's first-ever write as 0x20 and it is the SYSTIME
broadcast pair (`0202`/`0203`), sent while the discovery sweep is
still running. The command burst (0305/0403/0409/0307 → 44,
0605/060D/… → 53) first appears together with the first `0305` at
+71.650 s. The table row and obligation 3's "~22 s to first demand
writes" both descend from misreading the SYSTIME write as the burst;
the origins note (+65.6 s from 1F start) is the correct anchor.

## Check (5) — §(e) minimal call set

- CFM observed set: **CONFIRMED, exact.** Over all src-0x20 `0305`
  writes in the corpus the BE16 [4..5] set is
  {0, 378, 379, 382, 384, 1166, 1232, 1368, 1617, 1660, 1710, 1750,
  1760} — identical to the map's list.
- Gofinity 360: **CONFIRMED.** Own parse of `gofinity-bootup.bin`:
  1,532 frames, 0 bytes skipped; its thermostat's `0305` CFM values
  are {0, 360, 706} — 360 present.
- E-15 producer notes: the wire half is **CONFIRMED** — in **674**
  src-0x20 `0305` frames (recount exact), [0] and [2] are **never
  simultaneously nonzero** (joint census: [0] ∈ {0,1,2}, [2] ∈ {0,2},
  no mixed frame). The firmware half (FUN_180c54d8 = cool-side,
  CD7D mapping, CCC4/CCDC roles) is a stage-S/audit-2 code claim —
  consistent with everything measurable here, not independently
  re-derived in this pass.
- Scenario payloads: fan-only CFM transitions 0 → 1166 → 379 → 0
  **CONFIRMED**; rundown = exactly one residual `020000000651…` then
  idle **CONFIRMED**; `0306` examples (idle / fan / heat) all present
  verbatim **CONFIRMED**; heat example `01000000048E…` **REFUTED**
  (R6); the cool CFM value *order* printed in §(e)
  (1232 → 1710 → 1660 → 1760) does not match the capture — observed
  order is **1232 → 1760 → 1710 → 1660** (the set is right, the
  sequence is not; minor).
- §(e) pointer to the CFM computation in FIRMWARE-ANALYSIS-R §9:
  pointer valid (R's floor formula `325 × CD8C / 12000.0` present at
  R lines 114–115 as quoted).

## Check (6) — G-items

- **G1:** status text accurate today — ODU ~2-min standby bound
  (stage Y) is present, furnace timeout still unmeasured. Caveat from
  R2: the gap's motivating premise (via §(d)) is outdated; the archive
  now contains a ~36 s thermostat-only outage with no peer reaction,
  so any future timeout is > 36 s. **CONFIRMED as annotated, premise
  softened by R2.**
- **G3:** annotation accurate — partially closed by infinitive layouts
  + AA code-derived layouts (3B02 member → store buffer 0x3C0D8D7D,
  length 29; the served length 29 is wire-confirmed in check (3));
  registered-on-this-Ion contents remain unknowable. **CONFIRMED.**
- **G6:** annotation accurate — remains open only for a real SAM01's
  exact write frames; V §3 pointer valid. **CONFIRMED.**
- **G8:** "exactly one transitional `0605` = 3.0 frame" —
  **CONFIRMED, exact**: one frame in the corpus
  (phase3-validation3-20261103-145755, 2026-11-03T20:03:34.122Z,
  `40400000010001`); directed floats are otherwise only 0.0 (×616)
  and 5.0 (×34). Residual staleness inside G8's own text: it still
  says "CFM outside **379–1760**" although 378 is observed (E-9 fixed
  §(e) only) — minor.
- **G9:** scope note accurate — func 0x15 occurs **0** times in
  83,752 frames, so 44/53 exception behaviour remains unobserved;
  the SAM-side existence of 0x15/0x04 is a stage-V documentary claim
  (pointer valid). **CONFIRMED.**

## Check (7) — remaining stale/wrong claims found by full read

Beyond R1–R9 above:

- **M1 (§(a) architecture):** "the only non-response frames not from
  0x20 are the 0x1F commissioning phase and 0x93's slow poll" is
  overbroad — the furnace's `44→45 030A` bursts (30 frames in
  coldstart) are also non-response frames not from 0x20. They are
  documented in §(c); the §(a) sentence omits them. Minor.
- **M2 (§(d) corroboration):** the 78 s silence endpoints are exact
  (measured 78.234 s, 18:33:03.796 → 18:34:22.030) and segment-05
  silence statistics reproduce exactly (median 0.05 s, p90 0.41,
  p99 1.96, max 2.81); wizard gaps measure 4.91 s vs the map's 4.90
  (rounding). **CONFIRMED.**
- **M3 (G4):** the shared-byte range printed in G4 ("72–153") is the
  coldstart range; corpus-wide the byte spans **70–194** (060B and
  0414 both; B7's finding). §(a)'s coldstart-scoped presentation is
  correct; G4's unscoped range is stale. Minor.
- **M4 (Sources table):** the §Sources table still covers only the
  original 4 captures (its arithmetic is exact for them:
  17,600 + 6,543 + 1,115 + 1,267 = 26,525) while §(b)/§(e) and the
  errata cite the 12-file, 83,752-frame corpus. Scope staleness, no
  wrong number within its own scope.
- No lingering "mode words" (the term survives only inside the
  errata changelog as a quoted old value), no `0307`=3 / `060D`=13
  lengths anywhere outside the E-22 do-not-import guard, and no
  remaining heat-attribution for `FUN_180c54d8` — the E-15 notes are
  in place in both §(a) and §(e). The `0305` row's "[0] = heat stage,
  [2] = cool stage" is a wire-role statement and is wire-true
  (check (5)); it is not a producer claim.

## Scoreboard

- Check (1): 20 rows spot-verified — 18 CONFIRMED, 1 REFUTED (44/0302,
  R3), 1 status REFUTED (0303, R8).
- Check (2): CONFIRMED (677 exact; 832 with segment copies).
- Check (3): facts CONFIRMED; "~75,000" figure REFUTED (83,752);
  3D02 CONFIRMED at n=1; 65 ms / 500 ms×5 UNVERIFIABLE from captures
  (pointers valid).
- Check (4): anchors CONFIRMED except the 39.10 row — REFUTED (R1);
  handoff gap 29 ms vs "20 ms" (minor).
- Check (5): CFM set, gofinity 360, 674-frame co-activity, scenario
  payloads CONFIRMED; one heat example REFUTED (R6); cool CFM order
  misprinted (minor).
- Check (6): G1/G3/G6/G8/G9 annotations CONFIRMED as accurate today
  (G1 with the R2 premise caveat; G8 with a stale "379–1760" remnant).
- Check (7): additional REFUTED items R2 (reseat/0 KB — the most
  consequential after R1), R4 (061F offsets), R5 (5-of-879), R7
  (168 reads), plus minors M1/M3/M4.
