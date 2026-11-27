# gofinity (bvarner) — Bootup Sequence: extraction + cross-check

> **Correction 2026-11-26 (verification fleet):** register `3E10` does NOT
> occur anywhere in this capture (two independent parses, count = 0). The
> handoff probe at frames 103–112 is `3E0A`. All `3E10` mentions in this
> note are erroneous and should read `3E0A` where they describe the 0x0E
> probes; treat any other `3E10` mention as unverified.

Source: https://github.com/bvarner/gofinity (Bryan Varner, 2017, dormant, MIT License).
Obtained 2026-11-26 via git clone + raw.githubusercontent.com (branch `master`, HTTP 200).
Note: no repository code was executed; sources were read as text and the binary
capture was parsed with our own parser implementing the framing from Frame.go.

## 0. The headline first: the README section is EMPTY

The README's "### Bootup Sequence" heading (under Protocol Basics) has **no body** —
the heading is followed by blank lines to end of file (README.md, 4,216 bytes, ends
at line 83). pkg.go.dev did not truncate anything; the author never wrote the section.

The actual bootup data in the repo is **`replays/bootup.bin`** — a 36,141-byte raw
ABCD bus capture of a real system power-up, meant for the repo's FileReplayer.
That capture is what this note extracts. (The .bin stays in the upstream repo;
this note carries the full extracted sequence.)

Author's system (from 0104 identities in the capture): Bryant Evolution, 2014-era —
furnace 0x40 "VARIABLE SPEED FURNACE", model 987MA42080V17A-, software CESR******-**;
ODU 0x50 "EVEREST TWO CAPACITY ODU", model 286BNA036000DCAA, software CESR******-**.
I.e. one platform generation older than our Ion (SYST0101CW, furnace 0x44 / ODU 0x53).

## 1. Frame format as documented by the code (Frame.go / Bus.go)

- Header 8 bytes: dst u16 LE [0:2], src u16 LE [2:4], payload length u8 [4],
  reserved [5]=0, reserved [6]=0, operation [7].
- Operations: 0x06 ACK, 0x0B READ_REQUEST, 0x0C WRITE_REQUEST, 0x15 ERROR.
- Frame total = length + 10; CRC-16 (poly 0x8005, reflected, init 0x0000),
  little-endian, over header+payload.
- Payload of a read/write: byte 0x00, then register BE16, then data.
  (The author's own model: "exports[idx].data[offset]" — pointer-struct index +
  offset; byte-identical to our (register, data) reading.)
- Addressing on the wire is 2-byte: our 1-byte addresses appear as 0x01xx
  (thermostat 0x0120, SystemInit 0x011F, broadcast 0xF1F1).
- Bus: 38400 8N1, half-duplex RS-485 + 24 VAC on C/D (README, matches ours).
- Author's stated long-term goals (README): control the system "like a SAM",
  **"Segment the RS-485 network to interdict system commands to subordinate
  devices"**, a zoning module, an economizer module. Heritage: acd/infinitive.
- utils/DeviceProbe.go: a deliberately rude active prober (own address default
  0x121, target 0xF1F1) that fires a single READ (register, offset) and waits;
  the author notes he never recorded a device-join while logging.

## 2. The extracted boot sequence (bootup.bin: 1,532 frames, 0 skipped bytes, all CRC-valid)

Ops total: 813 READ, 535 ACK, 184 WRITE, **0 ERROR**. The capture has **no
timestamps** (raw byte stream) — order only; wire-time lower bound ≈ 9.4 s.

### Phase 1 — SystemInit persona 0x1F (frames 0–106)

Opens with three broadcast writes to F1, in this order:

| # | Frame | Payload |
|---|-------|---------|
| 0 | 1F→F1 WRITE 0305 | 12 bytes, all zero |
| 1 | 1F→F1 WRITE 3E02 | 1 byte `00` |
| 2 | 1F→F1 WRITE 0605 | 7 bytes, all zero |

Then the probe sweep. Rule: **an unanswered probe is sent exactly twice; an
answered probe once** (a second pass re-tries the silent 0x42 slots, making ×4
totals for 030D/031B/0404→42):

1. →20 READ 030A ×2 (unanswered — probes the thermostat's own future address)
2. →42 READ 030D ×2, 031B ×2, 0404 ×2 (unanswered)
3. →40 READ 0104 → **ACK 120 B**: "VARIABLE SPEED FURNACE", CESR******-**, 987MA42080V17A-
4. →42 READ 0104 ×2 (unanswered)
5. →50 READ 0104 → **ACK 120 B**: "EVEREST TWO CAPACITY ODU", CESR******-**, 286BNA036000DCAA
6. →51, →52, →54 READ 0104 ×2 each (unanswered — ODU address scan)
7. →40 READ 0306 → ACK 10 B (`01000e000001c205aa00`); →40 READ 030A → ACK 14 B
8. →42/50/51/52/54 READ 030A (only 0x50 answers, 14 B)
9. →42 READ 0403, 0407, 040B, 040C, 040F, 0410, 0411, 0413, 0414 ×2 each (unanswered)
10. →60, →61 READ 3405 ×2 (unanswered)
11. →50 READ 3E01 → ACK 13 B (`03b9039903ff03ff000000013c`); →50 READ 3E10 → ACK 3 B
12. →0E READ 3E08 ×10 total in this phase (unanswered, heavily retried)
13. →92 READ 0104 ×2 (unanswered — the SAM slot is scanned at boot)
14. →60, →61 READ 0302 ×2 (unanswered)
15. →52 READ 060E ×2; →51 READ 061F ×2; →52 READ 061F ×2 (unanswered)
16. →80 READ 3405 ×2 (unanswered)
17. →0E READ 3E01 ×10, 3E10 ×3 (unanswered) — tail of the 1F phase

### Handoff (frames 106–107)

Frame 106 is the last 0x1F frame (READ 3E0A→0E, third repeat). Frame 107 is the
first 0x20 frame — **the same probe** (READ 3E0A→0E), repeated ×4 by 0x20.
The 0x20 persona takes over mid-probe-stream with no gap marker.

### Phase 2 — 0x20 discovery sweep, interleaved (frames 107–~716)

0x20 re-runs the probe set against the live devices (0104/0306/030A/0402/0404/
0409/040D/031C→40; 0104/030A/3E01/031C→50; retries to 42/51/52/54; SAM 0104→92
×4 more at frames 271–272 and 401–402), keeps hammering the silent 0x0E
(3E08 ×40, 3E0A ×26, 3E01 ×20 over the whole capture), and only then starts
writing:

- First 0x20 WRITE: frame 534 — WRITE 031C→40 (configuration write precedes demand).
- First demand: frame 646 — WRITE 0305→40, all-zero demand **with the 0x78 byte
  at data[11]**; subsequent 0305 writes carry live CFM: data[4..5] = 0x02C2 (706),
  last captured 0x0168 (360). 9 × 0305 writes in the capture.
- **No 0605 writes by 0x20 anywhere in the capture** (system idle — all demands
  zero throughout; or a generation difference — unresolved).
- New (dst, register) probes stop appearing after frame 716; the tail of the
  capture is cyclic polling (his thermostat re-reads 0104 identities ×37 per
  device — a poll mix unlike our Ion's).

## 3. Cross-check against our knowledge (THERMOSTAT-PROTOCOL-MAP.md, stages C/D)

| Step / fact | Verdict | Note |
|---|---|---|
| 1F opens with F1 writes 0305 (12 B 0), 3E02 (1 B 0), 0605 (7 B 0) | **CONFIRMS** | Byte-identical to our Ion boot (map §boot: +6.00 s). Platform-level ritual, not model-specific. |
| Unanswered probe ×2, answered ×1 | **CONFIRMS** | Same rule as our sweep (~95 ms spacing is ours only — gofinity has no timing). |
| Sweep probes thermostat's own 0x20 and SAM 0x92 | **CONFIRMS** | Both present in our sweep too (030A→20 ×2; 0104→92 answered by our SAM in phase 2 there, silent here — he had no SAM). |
| 1F prober = the thermostat; 0x20 follows seamlessly | **CONFIRMS, stronger** | Here the handoff is visible mid-probe: 0x20 continues 1F's exact in-flight probe (3E10→0E). Our evidence was a 20 ms gap; his is frame-adjacent continuation. |
| 0x20 runs its own sweep interleaved with polling start; writes come late | **CONFIRMS** | His first WRITE at frame 534, first 0305 at 646; our map: sweep interleaved 16.7–61.8 s, steady ≈62 s. |
| 0104 identity answer = 120 B, model + CESR + model/serial | **CONFIRMS** | Same layout as 0x44/0x53 answers in our system. |
| 0x78 byte at 0305 data[11] | **CONFIRMS + extends** | Present on a 2014 Bryant Evolution too → platform-wide constant, not an Ion quirk. Still unexplained semantically. |
| Address 0x0E probed persistently with 3E01/3E08/3E10 (+3E0A by 0x20), never answers | **ADDS** | No 0x0E in our captures/map. An expected-but-absent device class on his system; identity unknown. |
| Furnace scan slots 0x40 (answered) + 0x42 (silent); ODU scan 0x50/51/52/54 | **ADDS** | Our Ion: furnace only 0x44, ODU only 0x53 probed in the excerpts. Scan ranges are wider than our single-device view. |
| 0x20 steady poll re-reads 0104 ×37/device; no 0605 writes in capture | **DIFFERS (generation)** | Older Evolution control ≠ Ion poll mix; not a conflict with our boot data — steady state only. |
| Timings (1F at ~+6 s, ~95 ms spacing, handoff ~16.7 s, steady ~62 s) | **NOT ADDRESSED** | bootup.bin has no timestamps. Our captures remain the only timing source. |
| Conflicts with our boot ritual | **NONE** | Every sequence element that overlaps matches. |

## 4. Relevance to the failover 0x20 emulator

What the emulator must reproduce at power-up, now doubly sourced (our captures
+ gofinity's independent 2014 system):

1. Stay silent, then speak **as 0x1F**: broadcast-write 0305 (12 B zeros),
   3E02 (1 B 00), 0605 (7 B zeros) to F1 — in that order.
2. Run the discovery sweep as 0x1F: ×2 for unanswered, ×1 for answered;
   probe candidate slots for furnace/ODU/zone/sensor classes, its own 0x20
   address, and the SAM slot 0x92 (0104).
3. Switch persona to 0x20 and re-run discovery against what answered;
   configuration writes (031C-class) come **before** the first demand write.
4. First 0305 carries zero demand with the 0x78 byte at [11]; live CFM follows
   the demand computation.

What remains unknown after gofinity:

- **All timings** — gofinity contributes sequence, not timing. Our measured
  values (SystemInit ~+6 s, ~95 ms probe spacing, ~45 s of 0x20 sweep,
  boot-to-steady ≈62 s) stay authoritative for the Ion.
- **The 0x0E device class** — his thermostat expects something at 0x0E that
  neither system has. Whether the Ion probes 0x0E too (not seen in our boot
  excerpts) and what answers would look like is open; an emulator can omit
  0x0E probing initially, flagged as a gap.
- **0605 write cadence on ODU-equipped systems** — absent here because the
  system was idle (or generation-specific); our own map's ~10 s burst
  (0605 in the command burst) remains the Ion source.
- Steady-state poll mix is generation-specific; for the Ion, our protocol
  map governs — gofinity validates the boot skeleton, not the steady state.

## 5. Provenance / method

- README.md, Frame.go, Bus.go, Transceiver.go, utils/*.go read as text
  (2026-11-26, master branch). License: MIT (© 2017 Bryan Varner,
  © 2016 Andrew Danforth).
- bootup.bin parsed with an in-house Python parser implementing §1 framing:
  1,532 frames decoded, 0 bytes skipped, every frame CRC-valid — the framing
  and CRC config in Frame.go are confirmed against real traffic.
- No code from the repository was built or executed.
