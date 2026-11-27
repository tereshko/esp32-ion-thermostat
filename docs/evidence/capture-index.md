# Bus traces — Ion ABCD bus, Heil G80CTL + HVA960GKA, thermostat SYST0101CW

## coldstart-20261029-125733.jsonl (17,600 frames, 2026-10-29 12:57:50–13:24:50 EDT)
Single continuous capture via capture.py (TCP 2373, cleaned JSONL, InfinitESP passive).
Timestamps in file are UTC; segments below in EDT (UTC-4). Split copies in segments/.

| # | Segment | EDT | What's in it |
|---|---------|-----|--------------|
| 01 | coldstart+idle | 12:57:33–13:02 | Power-up: 0x1F commissioning sweep polls 0104 ID tables at all addresses incl. 0x92 (SAM) and 0x94; ID tables: furnace 0x44 "VARIABLE SPEED FURNACE" CESR******-** G80CTL1352422A; ODU 0x53 "VAR SPD COMP VERSION" CESR******-** HVA960GKA201; thermostat 0x20 takes over the steady ~10 s poll/command cycle |
| 02 | fan-only | 13:02–13:06 | Ion set Fan (end of 13:02), blower physically started 13:03, stopped by itself 13:04–13:05 |
| 03 | auto-pause | 13:06–13:07 | Everything back to Auto |
| 04 | cool-70F | 13:07–13:13 | Cool call, setpoint 70 °F; ODU command blocks active |
| 05 | off-pause | 13:13–13:16 | System OFF at the thermostat |
| 06 | heat-75-79F | 13:16–13:22 | Heat call; setpoint staircase 75 °F (13:16) → 76 (13:19) → 77 (13:20) → 79 (13:21), room showed 72 °F — forced staging demand |
| 07 | heat-rundown | 13:22–13:24:50 | OFF at 13:22; blower kept running until 13:24 (rundown profile), capture ends 13:24:50 |

Timeline source: the author's messages 2026-10-29 13:03–13:24 EDT.
Note: thermostat also broadcasts time/date (dst F1, regs 0202/0203) about every 60 s (measured 2026-10-29 in THERMOSTAT-PROTOCOL-MAP.md; earlier "~25 min" estimate was wrong).

## sam-commissioning-20261029-143248.jsonl (6,543 frames, 2026-10-29 14:32:49–14:48:57 EDT)
Phase-2 flash + thermostat power-up (14:34 EDT). The 0x1F sweep polls 0x92's
0104 ID table and the ESP answers as a SAM: "SYSTEM ACCESS MODULE / Oct 29 2026 /
InfinitESP--SAM / 1726". SAM<->thermostat table traffic (3B02/3B03/400A reads,
thermostat replies) runs both ways for the whole capture (302 frames from 0x92,
276 to it). The thermostat then ran its equipment-identification wizard
(evaporator confirm EN(A,D)4X61; equipment summary matched the installed
system). No setpoint writes yet — control acceptance test is via HA climate.

## sam-reseat-20261029-151123.jsonl (1,611 frames, 2026-10-29 15:11:24–15:14:56 EDT)

Thermostat-only reseat (Ion off its wall plate ~36 s, rest of system powered) —
the capture long believed lost at 0 KB; the author recovered it from the terminal
buffer on 2026-10-30. Verdict-changing file:

- The SAM was ALIVE the entire window: its ~3 s polls to 0x20 run throughout
  (zero-filled replies until 15:11:34), go unanswered 15:11:36–15:12:12 while
  the thermostat is physically off the plate, then the reboot sweep arrives.
- After reseat, the control reads the SAM's 0104 exactly twice: from 0x1F at
  15:12:18 and from 0x20 at 15:12:40; both answered "SYSTEM ACCESS MODULE".
- Registration probes in the whole file: 040E = 0, 3F02 = 0, 031C = 0,
  030D = 0. SAM-initiated polls stop after 15:12:40 — consistent with the
  component's 180 s discovery holdoff after the 0x1F sweep.
- CONCLUSION: attempt #3 is a SOLID negative after all (live SAM, genuine
  thermostat-only reboot + relearn, no registration). The powerbank-death
  hypothesis is retracted for this window. Only attempt #2 (FULL INSTALLATION,
  15:02) remains unverified — the SAM was inexplicably silent in that file.

## 400A direct-write test session (2026-10-30) — full result in ../firmware-analysis/400A-TEST-RESULT.md

Four sequential captures of one session (the author at the wall). Verdict:
writes from the UNREGISTERED SAM node to the thermostat's 400A row
(zone-1 comfort profiles, manual entry bytes 28/29) are stored and
consulted live — 6a PASS, 6b PASS, 6c partial. Zero func-0x15
exceptions in all four files (30,975 frames total).

## 400a-test-20261030-141705.jsonl (5,149 frames, 14:17:06–14:24:30 EDT)
Baseline + wall arming. 400A poll replies: 14:17:20 manual 70/74;
14:22:00 manual 76/78 — the author's wall-side manual edits (heat 76) land
in the row itself; this reply also refreshes the node's RMW cache.

## 400a-test-20261030-142628.jsonl (2,252 frames, 14:26:29–14:29:43 EDT)
Write 1: poll 14:26:40 still 76/78 (ROW1); 14:26:49 func 0x0C write
0x92→0x20, byte 28 76→78, all other bytes identical (repeated once,
same payload, 14:26:53). Ion manual screen then showed HEAT TO 78
(photo in ../evidence/). Demand movement in the Auto+manual window:
060D 00→02 at 14:29:16, furnace 0305 gains 0x048E (1166) at 14:29:20.

## 400a-test-20261030-145226.jsonl (2,197 frames, 14:52:27–14:55:37 EDT)
Writes 2–3: 14:53:29 heat byte 28 → 75; 14:54:17 cool byte 29 → 74
(HA field and frame agree; "72" in chat was a typo). Poll 14:54:40
replies manual 68/76: after the author's Off→Auto switching the control
had RE-SEEDED the manual entry from the active home profile —
manual-slot semantics discovered (re-initializes on mode/profile
re-entry; not a rejection).

## 400a-test-20261030-145554.jsonl (21,377 frames, 14:55:55–15:26:39 EDT)
Clean final check. 14:58:55 write byte 28 → 71 (base row = re-seeded
68/76), then NO wall/mode interaction. Six consecutive 400A poll
replies — 14:59:21, 15:04:01, 15:08:41, 15:13:21, 15:18:01, 15:22:43 —
all return b28=71, b29=76. Storage proven over 24 minutes.

## phase3-validation-20261103-142517.jsonl (session #1, aborted procedure)
the author edited the Home profile hold at the wall; Touch-N-Go Manual was
never selected. Auto→Heat switch re-seeded the manual entry from Home
(400A reply 14:28:01 EST: 70/76). Zero writes from the node; no demand.

## phase3-validation2-20261103-143328.jsonl (session #2, write path)
Wall on Manual + Heat, room 75. HA sets at 14:54:37–14:54:49 EST:
cool 77→82, then heat 72→79 (14 write frames from 0x92, one per step).
400A reply 14:56:00 returns 79/82 — wall stored the HA pair. Demand
(0305) stayed idle: the author switched the system off at the wall ~1 min
after applying; Oct 30 precedent put demand lag at ~2.5 min.

## phase3-validation3-20261103-145755.jsonl (session #3, 6c PASS)
Manual + Heat; stored pair 79/82 survived the earlier Off→Heat cycle
with Manual active. Demand: 14:58:37 CFM 1166 (0x048E) → 14:59:46 CFM
382 → 15:00:48 stage byte 02 → 15:01:59 CFM 1617 (0x0651); gas ignition
observed at the wall ~15:01, room 76. HA end-of-call writes 15:02:34–
15:02:46 (heat →70, cool →73); demand back to idle by ~15:03:3x.
Criterion 6c PASSES: sustained heat call started and ended purely by
HA setpoint writes. Production control loop in service 2026-11-03.
