# 400A direct-write test — RESULT (2026-10-30)

Test: `DIRECT-WRITE-RESEARCH.md` §5, Variant B. Build:
`firmware/phase3-test.yaml` (phase2 + additive test methods in
`firmware/test-components/`; write only on HA button press, full-row
read-modify-write from the node's cache, func 0x0C to 0x20).

**Verdict: PASS.** Decision-tree criteria (§5): **6a PASS** (the Ion
stores foreign table-40 writes), **6b PASS** (the engine consults the
manual entry live), **6c PARTIAL** (demand-side movement observed, no
isolated sustained-call run).

Setup: ESP flashed phase3-test by OTA on 2026-10-30 before the session;
SAM node 0x92 in its usual UNREGISTERED state (this ICP control never
registers it — see SAM-REGISTRATION-RESEARCH.md). Thermostat
SYST0101CW, firmware CESR******-**.79. the author at the wall. Evidence: four captures in `traces/` (30,975 frames total)
and four photos in `evidence/`, listed at the end. Zero func-0x15
exception frames in all four captures.

Session wrinkle, stated up front: the author's standing system mode on this
control is **Off**. His first "hold" actions edited the Touch-N-Go
manual values in the Off-mode UI, and mid-session he switched
Off→Auto→Off. That confusion turned out to be informative (it exposed
the manual entry's re-seed semantics, below) and does not compromise
the verdicts, because the decisive final check ran with no wall or
mode interaction at all.

## Timeline (all EDT, from the captures)

| Time | Event | Evidence |
|------|-------|----------|
| 14:17:20 | Baseline 400A poll reply: manual heat **70**, cool **74** (bytes 28/29) | trace 141705 |
| ~14:20 | the author sets wall manual heat to **76** (room displayed 74 °F) | his message |
| 14:22:00 | Poll reply: manual **76/78** — the wall writes its own manual edits into the row; the node's RMW cache is refreshed from this row | trace 141705 |
| 14:26:40 | Poll reply: still **76/78** (ROW1) | trace 142628 |
| 14:26:49 | **WRITE 1** (0x92→0x20, func 0x0C, 35-byte row): byte 28 76→**78**, every other byte identical to ROW1. A second identical frame followed at 14:26:53 (same payload) | trace 142628 |
| ~14:29 | Photo: Ion Touch-N-Go **manual** screen, mode auto, manual profile active — **HEAT TO 78 / COOL TO 78**, room 73 °F. The heat value 78 was never entered at the wall; the only source is the bus write | evidence/ion-manual-screen-after-write-78-20261030.jpg |
| 14:29:16 / 14:29:20 | ODU 060D flag flips 00→**02**; furnace 0305 demand payload gains **0x048E (1166)** at bytes [4..5] — the only demand change in that capture, coinciding with Auto+manual becoming active at heat-to 78 vs room 73 | trace 142628 |
| 14:53:29 | **WRITE 2** (heat): byte 28 → **75** (row carries the then-cached cool 78) | trace 145226 |
| 14:54:17 | **WRITE 3** (cool): byte 29 → **74** — HA field and frame agree on 74; the "72" in the author's chat message was a typo | trace 145226; evidence/ha-test-fields-75-74-20261030.jpg |
| 14:54:40 | Poll reply: manual **68/76** — the entry had been **re-seeded from the active home profile** (68/76) after the author's Off→Auto switching; his home-screen photo at 14:55 shows schedule values 68/76 in auto | trace 145226; evidence/ion-home-screen-auto-schedule-20261030.jpg |
| 14:58:55 | **WRITE 4 — clean final check** (heat): byte 28 → **71**, based on the re-seeded row (payload b28=71, b29=76). **No wall or mode touches after this point** | trace 145554; HA press log: evidence/ha-button-history-20261030.jpg |
| 14:59:21 → 15:22:43 | **Six consecutive poll replies, all b28=71, b29=76**: 14:59:21, 15:04:01, 15:08:41, 15:13:21, 15:18:01, 15:22:43 — 24 minutes, zero drift, zero regeneration | trace 145554 |

## Per-criterion verdicts (§5 decision tree)

- **6a — storage: PASS.** The thermostat's own re-reads return the
  foreign-written byte, six polls in a row over 24 minutes, in a
  window with no other writers. Writes from an unregistered node are
  NOT source-gated on this ICP build; the pessimistic branch of the
  research ("the whole direct-write family is dead here") is excluded.
- **6b — live consultation: PASS.** The wall display adopted the
  bus-written 78 as the active manual setpoint (photo ~14:29) without
  any wall-side setpoint interaction; 76 was the only heat value ever
  entered locally. The engine reads the manual entry live, not only
  at profile-switch time.
- **6c — real call: PARTIAL.** In the one window where Auto+manual
  was active with heat-to 78 against a 73 °F room, the demand side
  moved within seconds (060D 00→02 at 14:29:16; 0305 CFM field
  0→1166 at 14:29:20). But the control's standing mode is Off and
  the session never ran an isolated, sustained heat call under a
  bus-written setpoint, so a full 6c is not claimed. A five-minute
  mode-Heat window would settle it; it is not needed for the
  control-path conclusion (6a+6b are the gate for Variant B).

## Semantics learned — and what they mean for the design

1. **The manual entry is scratch "deviation from the current
   schedule", not persistent storage.** On mode/profile re-entry
   (observed: Off→Auto) the control re-initializes the manual entry
   from the active schedule profile (home 68/76 overwrote 75/74
   between 14:54:17 and 14:54:40). This is the control's own design,
   not a write rejection — no exceptions were returned at any point.
2. **While the manual context stays continuously armed, written
   values persist indefinitely** (proven ≥24 min / 6 polls) and are
   consulted live. So the working composition is exactly the
   researched Variant B: keep a manual profile/hold armed, steer
   bytes 28/29 from Home Assistant. The SAM registration gate is
   irrelevant to this path.
3. **Next surface (Variant A): the profile entries themselves.** The
   same 400A row carries home/away/sleep/wake pairs (already fully
   decoded: home 68/76, away 60/80, sleep 68/76, wake 68/76). If the
   control consults the active profile entry the way it consults
   manual, steering the home pair would move the setpoint in plain
   Auto/schedule operation — no hold to arm, no re-seed caveat.
   Untested; that is the follow-up experiment, not part of this
   build.
4. Nothing outside the manual scratch entry was ever written:
   profiles, schedule, and all other rows are byte-identical to
   their pre-test state (verifiable in the captures — every write
   frame differs from its base row in exactly one byte).

## Leftover oddity (unrelated, noted for later)

The Ion's on-screen clock is wrong: photos taken at 14:29 and 14:55
EDT show "Fri 1:10a" and "Fri 1:36a". The clock advances correctly
(+26 min over +26 min) but sits at a ~13 h 19 m offset. With the
Wi-Fi module dead the control has no NTP source; what it expects
time from — and whether the node's time broadcast should discipline
it — is an open side question.

## Evidence index

Traces (`traces/`): `400a-test-20261030-141705.jsonl` (baseline +
wall arming), `400a-test-20261030-142628.jsonl` (write 1 + display/
demand window), `400a-test-20261030-145226.jsonl` (writes 2–3 +
re-seed), `400a-test-20261030-145554.jsonl` (clean check, six polls).

Photos (`evidence/`): `ion-manual-screen-after-write-78-20261030.jpg`
(HEAT TO 78 / COOL TO 78, manual active),
`ion-home-screen-auto-schedule-20261030.jpg` (auto home screen,
schedule 68/76), `ha-test-fields-75-74-20261030.jpg` (HA number
fields 75/74), `ha-button-history-20261030.jpg` (HA press log
14:26:49 / 14:53:30 / 14:58:56, matching the write frames).

Rollback: reflash `firmware/phase2.yaml`; the test number/button
entities in HA become orphaned and can be deleted there.
