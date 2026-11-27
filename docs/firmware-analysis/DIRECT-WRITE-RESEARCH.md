# Direct 4xxx writes — can the Ion be steered without SAM registration?

Date: 2026-10-29. Desk research only (local InfinitESP source, project bus
captures, infinitude source + wiki, InfinitESP issues). Nothing was written
to the live bus; nothing was posted anywhere.

**Target:** ICP Ion SYST0101CW at bus 0x20, firmware CESR******-**.79.
**Our node:** ESP32 + InfinitESP 2026.10.19 at SAM address 0x92, present on
the bus full-time, **not** registered as a SAM by the Ion (established in
`SAM-REGISTRATION-RESEARCH.md`: the Ion has no SAM discovery at all).
**Trigger for this research:** nebulous in issue #61 — *"years ago I was able
to control my Touch model with direct writes to one of its 4xxx state
registers, so that might be an option with a bit of fiddling."*

Labels: **[PROVEN]** = primary source in hand (code / capture / doc quoted);
**[INFERRED]** = conclusion drawn from proven items, not itself observed.

---

## TL;DR / verdict

The register is **0x400A — the zone-1 comfort-profile row** (table 0x40
"SCHEDULE"). It is the only 4xxx register that contains setpoints, and
InfinitESP already writes it directly to Touch controls today: a full-row
func-0x0C write whose proven effect is that the wall follows the row's
**manual entry** while a hold/override is active. Critically, **that write
path contains no registration check anywhere** — the only gates are
config-level (`sam_address` set) and, in the one existing caller, a °C-bus /
half-degree restriction that does not apply to the mechanism itself.

The Ion serves its complete 400A row to our unregistered node (4 of 4 reads
answered with real data, one single stable payload across the whole
archive) — even though it deliberately serves an *empty* SAM mirror
(3B02/3B03 = zeros) to the same reader. Read-side, table 0x40 is not
SAM-gated on this control. Whether **writes** from 0x92 are stored is the
one thing never yet tried on this unit — and it is cheap, safe, and
byte-exactly revertible to test.

**GO** — for one supervised test (Variant B, §5): the author arms a hold **at the
wall** (the one arming path that works on this Ion), our node writes the
400A row with the manual entry's cool byte lowered 2 °F, success is judged
by re-read + wall display + demand burst. **NO-GO** for editing the active
profile entry as a first move (Variant A): it mutates persistent config and
is confounded by schedule-engine caching. If Variant B's re-read shows the
byte was *not* stored, the direct-write family is source-gated on this ICP
build — stop there and report that to issue #61.

---

## 1. Three different "control" mechanisms — do not conflate them

| # | Mechanism | Path | Needs registration? |
|---|-----------|------|---------------------|
| M1 | **SAM override** (classic infinitude + InfinitESP default) | SAM writes its mirror tables 3B02/3B03 *to* the thermostat (change flags + hold encoding); thermostat acks with 3B0E and pulls the SAM's tables | **Yes** — dead on this Ion (no discovery; mirror reads return zeros; control-test writes changed nothing) |
| M2 | **Direct comfort-row write** (this research) | Any bus node writes the thermostat's *own* config table row 400A (func 0x0C, full 35-byte row) | **No check exists in the sender's code**; thermostat-side acceptance from an unregistered writer is the open question the test answers |
| M3 | **Profile edit at the wall** | User edits Comfort Profiles in the Ion UI | n/a — this is what M2 mimics from the bus: same store, same bytes |

**Hold does not live in 400A.** There is no hold flag anywhere in the comfort
row. In InfinitESP, hold is encoded into the **3B03** write
(`encode_hold_()`: change-flag 0x02 = permanent, 0x82 = timed, plus the
zone's `zones_holding` bit and a duration slot at `REG3B03_HOLD_DURATIONS`
= offset 38) — i.e. hold is an M1/SAMINFO concept [PROVEN, infinitesp.h /
infinitesp.cpp]. What M2 relies on instead: *while an override is active
(however it was armed), the wall consults the comfort row's **manual** entry
as its live setpoint store* — the row is "the wall's source of truth"
(infinitesp.h, `comfort_refine_setpoints` comment) [PROVEN for Touch]. On
our Ion an override can still be armed — **at the wall itself**, by tapping
the setpoint. M2 then steers it from the bus. That composition — wall arms,
bus steers — is the whole trick.

**Ruling out the other 4xxx candidates** [PROVEN unless noted]:
- **0420** ("SAM Sync", table 0x04 row 32): infinitude wiki — "SAM polls
  routinely but never observed as sync mechanism. Returns zeros";
  infinitude `CarBus::SAM.pm` — "never observed during override/setpoint
  commands — likely routine background polling, not setpoint-linked". Not a
  control register.
- **4012** vacation row (7 B): only consulted while a vacation is active;
  arming vacation is again an M1 path (3B04 change-frames).
- **4202** fault log (72 B): a log the thermostat writes; no control
  semantics.
- **4608/4609/460A/460B/460C**: Wi-Fi SSID/passwords, cloud host, dealer
  info — no setpoints.
- **4002–4009** weekly schedules (70 B): period *times and activity
  indices*, no setpoint values. (Changing them re-programs the schedule —
  a blunter, riskier instrument than 400A, and unnecessary.)
- ⇒ **400A is the only 4xxx register a setpoint can be written into.**
  [INFERRED: that this is what nebulous meant. He named no register; but
  his own current codebase contains exactly one direct-4xxx-write control
  path, and it is this one — §2.]

---

## 2. Local source: the 400A write path (InfinitESP 2026.10.19)

### 2.1 The one function that writes 400A: `command_setpoint_half()`

`components/infinitesp/infinitesp.cpp`, lines 2134–2167. Purpose per its
header comment (infinitesp.h ~745–760): on Touch-generation controls, 3B03
cannot carry half-degree °C setpoints, so fractional targets are landed in
the comfort row instead — *"the proven 2026-09-08 table-40 path"*,
live-verified in three experiments on 2026-10-13 (issue #49). Verbatim
core:

```cpp
bool InfinitESPComponent::command_setpoint_half(uint8_t zone, bool is_heat, float target_c) {
  if (!sam_enabled() || !bus_uses_celsius())
    return false;
  if (fabsf(target_c - roundf(target_c)) < 0.01f)
    return false;  // whole-degree target: the proven 3B03 path handles it
  auto *row = get_register(ADDR_THERMOSTAT, comfort_reg_for_zone(zone));
  if (!row || row->size() < COMFORT_ACTIVITY_COUNT * COMFORT_ENTRY_SIZE)
    return false;
  std::vector<uint8_t> new_row = *row;
  uint8_t off = COMFORT_MANUAL * COMFORT_ENTRY_SIZE + (is_heat ? 0 : 1);
  new_row[off] = (uint8_t) roundf(target_c * 2.0f);

  bool holding = get_zone_hold_duration(zone) != 0;
  if (holding) {
    std::vector<uint8_t> payload = {0x00, (uint8_t)(comfort_reg_for_zone(zone) >> 8),
                                    (uint8_t)(comfort_reg_for_zone(zone) & 0xFF)};
    payload.insert(payload.end(), new_row.begin(), new_row.end());
    send_write_frame_(ADDR_THERMOSTAT, 0x01, payload);
    ...
    return true;
  }
  // No hold yet: caller's 3B03 write arms the override; row write deferred ~10 s
  defer_manual_row_write_(comfort_reg_for_zone(zone), new_row, 10000);
  return false;
}
```

Byte-level facts [all PROVEN from the code]:
- **Exactly one byte changes**: offset `COMFORT_MANUAL*7 + (heat?0:1)` =
  **28 (heat) or 29 (cool)** of the 35-byte row. The rest of the row is a
  read-modify-write of the cached row, byte-identical.
- **Frame**: func 0x0C (WRITE), src = our SAM address, dst = 0x20
  (`ADDR_THERMOSTAT`, dst_bus 0x01), payload = `[0x00, 0x40, 0x0A]` + the
  full 35-byte row (38 bytes total).
- **Hold-active branch**: row-only write. Header comment records the Touch
  experiments: *"row-only held across polls"*, while any accompanying 3B03
  write *"regenerates the manual entry from the override's rounded value
  and stomps the half"* — i.e. on Touch the engine treats the row as the
  live store during a hold and re-derives the manual entry whenever an
  M1 write lands. (Consequence for our test: send **no** 3B03 writes in
  the test window.)
- **No-hold branch**: the row write is deferred ~10 s so an M1 (3B03) write
  can arm the override first and the thermostat can regenerate the manual
  entry from it; the row write then adjusts the regenerated entry. On our
  Ion the M1 arming step is precisely the broken link — hence Variant B
  substitutes a wall-armed hold.

### 2.2 The gates — and the absence of a registration gate

- `sam_enabled()` is defined as `return sam_address_ != 0;`
  (infinitesp.h:608) — a **configuration** predicate. the author's phase-2
  config sets `sam_address: 0x92`, so it is true.
- `command_setpoint_half` additionally requires a **°C bus** and a
  **fractional** target. Both are properties of that one caller (the
  half-degree feature), not of the write mechanism: on a °F bus the row
  byte is simply the whole °F value (§3 decodes the Ion's own row proving
  this: 0x44 = 68 °F etc.). Stock firmware on the author's system will therefore
  never emit this frame by itself — the test needs a one-off build that
  relaxes those two caller gates (or a small test button assembling the
  same payload via `send_write_frame_`). Everything downstream — the write
  queue, bus-idle gating, retries — is stock machinery, reused as-is.
- `send_write_frame_()` (infinitesp.cpp:1149) refuses only when
  `!sam_enabled()` ("a passive install must refuse to queue one at all",
  issue #38 backstop). The queue drain in `loop()` is gated on
  `!discovery_holdoff && bus_idle_ms > 50` — the discovery holdoff is the
  180 s window after 0x1F commissioning frames, not a registration state.
- `sam_state_received_` / `has_real_state()` is set when the SAM mirror
  fills and is consumed only by entity/HA state presentation. **No write
  path — setpoint, fan, mode, hold, vacation, or the 400A row write —
  consults it.** [PROVEN by exhaustive grep of the component.]
- Prerequisite that *is* real: the row must have been read once
  (`get_register(ADDR_THERMOSTAT, 0x400A)` populated by the slow poll) —
  on the author's node it already is (§3).

### 2.3 What the HA climate actions actually trigger (contrast)

`infinitesp_climate.cpp` `control()`:
- **SET_TEMPERATURE** → `command_setpoint_half()` first; if it declines
  (always, on the author's °F/whole-degree system), `set_zone_setpoint()` → an
  **M1 3B03 write**. This is exactly what the 2026-10-29 control test did
  (69→66→65→62 °F): seven 3B03 writes, zero adoption. The 400A path has
  **never been exercised on this Ion**.
- **PRESET home/away/sleep/wake** → `apply_activity()` (infinitesp.cpp:
  2362): despite its header one-liner ("writes setpoints+fan from the
  zone's comfort row and sets hold"), it does **not** write the row — it
  *reads* the row's values and pushes them via an **M1 3B03 write** with
  `encode_hold_()` flags. Also dead on this Ion.
- **Hold entities / `Z1HOLD!`** → `set_zone_hold()` → M1 3B03 write.

So every stock control surface on this firmware funnels into M1 except the
°C-only row write. The fiddling nebulous hinted at = using M2 deliberately.

---

## 3. The Ion's actual 400A row, decoded from our captures

All four 400A reads in the entire trace archive were issued by our node
(0x92 → 0x20) and **all four were answered in full** by the unregistered
Ion (sam-commissioning ×3, sam-control-test ×1). There is exactly **one
distinct payload** in the archive — the row never changed across
2026-10-29's sessions:

```
444C0044891E1E 3C50004F001E1E 444C0044891E1E 444C0044891E1E 4F510044891E1E
```

Layout per infinitesp.h (~199–211): 5 activities × 7 bytes
`[heat_sp, cool_sp, fan_mode, rclg_rhtg, hum_vent, unk5, unk6]`, order
home, away, sleep, wake, manual. Bus is °F ⇒ bytes are whole °F
(`comfort_byte_to_celsius`: "In °F mode, comfort bytes are whole °F"):

| # | Activity | Row bytes (hex) | Heat | Cool | Fan | b3 | b4 | b5–b6 | Heat byte @ | Cool byte @ |
|---|----------|-----------------|------|------|-----|----|----|-------|----|----|
| 0 | home   | `44 4C 00 44 89 1E 1E` | 68 °F | 76 °F | 0 (auto) | 0x44 | 0x89 | 1E 1E | 0 | **1** |
| 1 | away   | `3C 50 00 4F 00 1E 1E` | 60 °F | 80 °F | 0 | 0x4F | 0x00 | 1E 1E | 7 | 8 |
| 2 | sleep  | `44 4C 00 44 89 1E 1E` | 68 °F | 76 °F | 0 | 0x44 | 0x89 | 1E 1E | 14 | 15 |
| 3 | wake   | `44 4C 00 44 89 1E 1E` | 68 °F | 76 °F | 0 | 0x44 | 0x89 | 1E 1E | 21 | 22 |
| 4 | **manual** | `4F 51 00 44 89 1E 1E` | **79 °F** | **81 °F** | 0 | 0x44 | 0x89 | 1E 1E | **28** | **29** |

(Offsets are 0-based within the 35-byte row; byte[3] is the
(rhtg<<4)|rclg dehumidify-index pair, byte[4] a humidifier/vent flag field,
bytes 5–6 are the constant 0x1E pair the header notes as "always 0x1E on
this system".)

Observations:
- **Manual entry = heat 79 / cool 81.** The heat value matches the last
  wall-side manual heat adjustment in the session timeline (the author's
  75→79 °F staircase during the cold-start scenarios) — consistent with
  the wall storing its live override setpoints into the manual entry
  [INFERRED: the archive contains no 400A read from before that staircase,
  so the update moment itself was not captured]. The cool value 81 matches
  no setpoint used on 2026-10-29 (cool test ran at 70) — a leftover from
  an earlier manual interaction.
- During both captures the wall was in mode **Off** (Ion screen + protocol
  map), so no activity was being enforced; home/sleep/wake are identical
  anyway (68/76), and only away differs — setpoints alone cannot identify
  the schedule's current activity on this system. For a live test, the
  active activity must be taken from the wall display at test time.
- Cross-checks from the same captures: 4012 (vacation) served as
  `3C50001F001E1E` = 60/80 °F; 4202 served in full (72 B). Table 0x40/0x42
  reads from an unregistered node are simply answered. Contrast, same
  captures: 3B02/3B03 reads returned **31 zero-filled replies** and zero
  adoption of writes — the Ion's gate is specifically around the SAMINFO
  mirror (table 0x3B), not around its own config tables. [PROVEN]

---

## 4. Upstream history: how control worked before, and what it proves

### 4.1 Infinitude's override = M1, and it is registration-shaped

- Wiki (`Infinity---interpreting-data.md`, "SAM→Thermostat Notification
  Mechanism"): *"After accepting an ASCII zone command, the SAM actively
  writes one of the registers 3B03–3B0D to the thermostat on the ABCD bus.
  The thermostat acknowledges by writing 3B0E (value 0x01) back to the
  SAM. This is the primary change notification mechanism — the thermostat
  does not discover changes through polling alone."* The Z1OVR concept in
  the SAM ASCII spec is the *query* side of this (timed-override state);
  the verbs that move setpoints are `Z1HTSP!`/`Z1CLSP!`/`Z1HOLD!`, all
  implemented as M1 writes (InfinitESP `docs/sam-ascii.md` lists the same
  verbs; SAM.pm's flow comment: ASCII cmd → SAM updates its register →
  writes 3B03 → thermostat writes 3B0E → thermostat reads SAM 0104+030D).
- **The caution that must be quoted** (infinitude `lib/CarBus/SAM.pm`):
  *"Direct CarBus writes to SAM registers do NOT trigger this notification
  flow. The SAM may store the value but does not notify the thermostat."*
  I.e. in the mirror-table world, a raw write can land in storage and
  still be behaviorally inert without the adoption handshake. §6 weighs
  this against M2 honestly.

### 4.2 Table 0x40 is a documented, writable-by-design thermostat table

Wiki table listing for the thermostat (0x20), confirmed on SYSTXCCITC01
(CESR******-**.02) and also ITW01/UIZ/UID: **table 0x40 = "SCHEDULE",
1,017 bytes, 23 rows — "Zone schedules, comfort profiles, vacation
settings."** The same page documents the table-definition scheme: row 1 of
every table lists each row's size and flags, **bit 1 = writable
(0x03 = read+write)** — rows are individually declared writable by the
device firmware. The wiki (infinitude-era) never enumerates SCHEDULE's
rows; their semantics (4002 weekly, 400A comfort, 4012 vacation) come from
InfinitESP's 2026 live characterization ("Verified live 2026-08-19 against
every zone's 3B03 setpoints", infinitesp.h). So: the comfort row is a
first-class config store the thermostat itself maintains — the same store
its own UI edits — not a mirror/cache like SAMINFO. [PROVEN as cited;
whether the Ion build declares row 400A's writable flag is not yet read —
see test step 0 in §5, which can read the table definition row 4001
before writing anything.]

### 4.3 Where nebulous's sentence most plausibly points

[PROVEN] His current codebase contains exactly one direct-4xxx control
path (M2, §2), live-verified by him on a Touch control, and his
compatibility matrix lists a Carrier SYSTXCCITC01-B on the *same firmware
string* as the author's Ion (CESR******-**.79) as SAM-responsive.
[INFERRED] "Years ago … direct writes to one of its 4xxx state registers"
is the same table-40 technique remembered loosely — the comfort row is
literally part of the thermostat's SCHEDULE state table. No other 4xxx
register fits the sentence (§1).

---

## 5. The concrete test for this Ion

### Step 0 (optional, read-only, do first if convenient)
Read register **4001** (table 0x40's definition row) from the Ion and
check row 400A's flags byte for the writable bit (0x03 = r/w per the wiki
scheme). A declared-writable row upgrades the test from "plausible" to
"firmware says yes". A read-only flag does **not** cancel the test —
flags describe the intended interface, and InfinitESP's Touch results are
empirical — but it downgrades expectations and must be reported as-is.

### Variant B (primary): steer a wall-armed hold via the manual entry

**Preconditions**
- the author home, watching the Ion screen; bus capture running (JSONL :2373);
  heating/cooling demand safe to run (mild moment, windows as needed).
- One-off firmware build on our node that can emit the §2.1 frame on a °F
  bus (relaxed caller gates or a test button); no other behavior changed.
  During the whole test window: **no HA setpoint/preset/hold commands**
  (nothing may emit an M1 3B03 write — per the Touch evidence it would
  regenerate the manual entry and confound the result).
- System in **Cool** mode, Per Schedule.

**Sequence**
1. Read 400A fresh → save the 35 bytes as `ROW0`. (Expected today:
   `444C0044891E1E3C50004F001E1E444C0044891E1E444C0044891E1E4F510044891E1E`,
   but use the fresh read, not this document.)
2. **the author, at the wall**, taps the cool setpoint down/up to arm a manual
   hold at some value V (e.g. current displayed value unchanged is fine if
   the tap itself arms the hold; otherwise V = displayed ±1 and back is
   *not* needed — any wall-armed hold counts). Note the wall's displayed
   setpoint and room temperature R.
3. Read 400A again → `ROW1`. Per the Touch model, the wall will have
   regenerated the manual entry from the override: expect `ROW1[29] == V`
   (and `ROW1[28]` = the held heat setpoint). If `ROW1` == `ROW0`, the
   wall does not use the manual entry the Touch way — record it; the
   write test below still proceeds (it then tests raw steering directly).
4. Compute `ROW2` = `ROW1` with **byte 29 := V − 2** (cool). Choose the
   sign so the result is *below* room temperature R if a real cooling
   call is wanted as the strong signal; if V−2 ≥ R, the display signal
   (step 6b) is the criterion instead.
   Worked example with the archive's values (if the wall hold regenerated
   manual cool to 76): byte 29 goes `0x4C (76) → 0x4A (74)`, full row:
   `444C0044891E1E3C50004F001E1E444C0044891E1E444C0044891E1E4F4A0044891E1E`.
5. Transmit once: src 0x92 → dst 0x20, func 0x0C, payload
   `[0x00, 0x40, 0x0A] + ROW2` (the stock queue's retries of the identical
   payload are acceptable — the write is idempotent).
6. Observe, in order of evidentiary strength:
   a. **Re-read 400A** → stored bytes == `ROW2`? (proves the Ion *stores*
      foreign table-40 writes)
   b. **Wall display** → held cool setpoint now shows V−2 without anyone
      touching the wall? (proves the engine *consults* the row live —
      wake the screen first; Touch-family controls can defer UI-visible
      application until wake)
   c. **Demand burst** → in the thermostat's standing 10 s write burst
      (per THERMOSTAT-PROTOCOL-MAP): furnace 0305 byte[2] becomes 0x02 /
      CFM > 0 and ODU 0605 staging float > 0, i.e. a real cooling call
      starts (only expected if V−2 < R). (proves *actuation*)
7. Hold the observation for ~3–5 min (several burst cycles + at least two
   400A slow-poll cycles from our own node) to catch any delayed stomp or
   regeneration back to V.

**Revert (byte-exact, rehearsed before starting)**
1. Transmit the same frame with payload `[0x00, 0x40, 0x0A] + ROW1`
   (the pre-write row as read in step 3 — not a reconstructed value).
2. Re-read 400A → confirm bytes == `ROW1`.
3. the author cancels the hold at the wall (resume schedule). System is back
   to its exact prior state: the manual entry is scratch space the wall
   itself rewrites on its next manual interaction, and no profile,
   schedule, or setting was touched.

**Heat-side twin** (for a winter run): identical with byte **28**,
V = held heat setpoint, write V + 2 to force a heat call.

### Variant A (follow-up only): edit the active profile entry
Write 400A with the *currently active activity's* cool byte (offsets 1/8/
15/22 for home/away/sleep/wake) changed by −2 °F while Per Schedule runs
with no hold. Tests whether the schedule engine re-reads the row outside
period boundaries. Confounds: engine may cache at period start (observe
across a boundary before judging); the change is a **persistent profile
edit** (survives until reverted — revert with the captured original row,
byte-exact, same as above). Only worth running if Variant B proves
storage (6a) but not steering (6b) — it would then separate "row is
writable" from "manual entry is consulted".

### Decision tree after Variant B
- 6a fails (re-read shows `ROW1`): writes from an unregistered node are
  not stored → the ICP build source-gates table writes too. **Stop.**
  Report to issue #61; remaining paths are nebulous's table scan (science
  value only, by his own assessment) or the full 0x20-emulation arc.
- 6a passes, 6b fails within the window: storage works, live consultation
  doesn't (caching/regeneration difference vs Carrier Touch). Try Variant
  A across a period boundary before concluding.
- 6b (and ideally 6c) passes: **phase 2 is alive in M2 form.** Productize:
  HA climate setpoint = wall-armed hold + row steering; document the
  caveat that an at-wall hold (or an HA-side surrogate for arming) is
  part of the control loop on this control.

---

## 6. Risks and unknowns — stated plainly

1. **The unregistered-writer question is genuinely open.** For it: the
  Ion serves table 0x40 fully to our unregistered node while deliberately
  zeroing the SAMINFO mirror — its gating is table-specific, and the
  sender-side code has no registration concept at all. Against it: the
  SAM.pm caution (§4.1) proves this protocol family *does* contain
  store-but-ignore write semantics, and every live verification of M2 to
  date ran on installs where the writing node was also a commissioned
  SAM — thermostat-side source acceptance was never isolated as a
  variable. [Both sides PROVEN as cited; the resolution is empirical —
  that is what step 6a measures.]
2. **Storage ≠ steering.** Even a stored write may only take effect at
  the next schedule-period boundary (engine caching), or the engine may
  regenerate the manual entry over our value (Touch evidence shows
  regeneration happens on M1 writes; whether anything on the Ion
  regenerates it absent M1 traffic is unknown). The 3–5 min observation
  window + Variant A boundary test are the mitigations.
3. **No acknowledgments exist on this bus** (THERMOSTAT-PROTOCOL-MAP: no
  func-0D frames anywhere in 26.5k frames). Success can only be judged by
  re-read and behavior — both are in the test design.
4. **Race with the wall's own row access.** If the author touches the wall
  mid-test, the wall may rewrite the manual entry concurrently. Mitigate:
  hands off the wall between steps 2 and 7 except the planned revert;
  the full-row read-modify-write uses a seconds-old read, and any garble
  is detectable by re-read and repairable by the byte-exact revert.
5. **The write is a config-table write.** Variant B confines the mutation
  to the manual entry — scratch space the wall overwrites on its next
  manual interaction, so even a forgotten revert self-heals. Variant A
  lacks that property; hence its follow-up-only status.
6. **What M2 does not give us** (even if it works): mode changes
  (heat/cool/off live in M1 3B02 space), fan-mode steering, and hold
  *arming* from the bus. M2 is setpoint steering under an existing hold —
  a real but partial control surface. A complete remote-control story on
  this Ion still needs either an arming surrogate or the 0x20-emulation
  arc. Do not oversell a Variant-B pass as "remote control solved".
7. **Firmware-family inference.** The Touch that M2 was verified on is a
  Carrier ITC01; the Ion shares the firmware string (CESR******-**.79)
  but is a different brand build — the same situation as SAM registration,
  where the ICP build silently lacked a feature the Carrier build has.
  Prior from that experience: absence is a live possibility, priced into
  the decision tree.

---

## 7. Proven vs inferred — index

**Proven**
- 400A layout, activity order, per-entry heat/cool/fan offsets
  (infinitesp.h; independently confirmed by decoding the Ion's own row).
- The Ion's current row contents: home 68/76, away 60/80, sleep 68/76,
  wake 68/76, manual 79/81 °F; single stable payload across the archive;
  served in full to an unregistered reader (4/4 reads).
- `command_setpoint_half` writes exactly one byte (28/29) in a full-row
  func-0x0C frame to 0x20; holding branch is row-only; Touch experiments
  recorded in its comments (row-only holds across polls; M1 writes
  regenerate the manual entry).
- No registration/commissioning check exists in any InfinitESP write
  path; gates are `sam_enabled()` (config), the °C/fractional caller
  restriction, the 180 s discovery holdoff, and the bus-idle queue gate.
- HA climate temperature/preset/hold actions all funnel to M1 (3B03)
  writes on this system — and M1 is inert on this Ion (control test +
  zero-filled mirror reads).
- Hold is encoded in 3B03 (SAMINFO), not in 400A; the manual entry is
  consulted only while an override is active (InfinitESP comments).
- Table 0x40 = SCHEDULE (comfort profiles inside), documented on Touch
  thermostats; per-row writable flags are a protocol-level concept
  (infinitude wiki).
- 0420 is not setpoint-linked (wiki + SAM.pm); infinitude's override flow
  is the 3B03-write/3B0E-ack handshake; raw writes without the handshake
  can be inert in the mirror-table world (SAM.pm).

**Inferred**
- That nebulous's "4xxx state register" = 400A (only setpoint-bearing
  candidate; matches his own codebase's sole direct-write path).
- That the Ion's manual-entry heat byte (79) was stored by the author's
  2026-10-29 wall staircase (no pre-staircase 400A read exists).
- That a wall-armed hold on the Ion makes its engine consult the manual
  entry the way the Carrier Touch does (same platform/firmware string;
  brand-build divergence is the documented risk, §6.7).

---

## Sources

- Local: `~/workspace/diy-thermostat/infinitesp/components/infinitesp/
  infinitesp.h` (table defs ~97–211, comfort/hold comments ~745–1010,
  sam_enabled ~608), `infinitesp.cpp` (send_write_frame_ ~1149,
  command_setpoint_half ~2134, defer_manual_row_write_ ~2169,
  apply_activity ~2362, set_zone_hold ~2313), `infinitesp_climate.cpp`
  (control() ~84–215), `docs/sam-ascii.md`.
- Captures: `~/workspace/diy-thermostat/traces/
  sam-commissioning-20261029-143248.jsonl`,
  `sam-control-test-20261029-145357.jsonl` (+ archive-wide 400A scan:
  coldstart & full-install contain no 400A traffic — no SAM existed /
  decisive window missed, as previously established).
- Project docs: `SAM-REGISTRATION-RESEARCH.md`,
  `THERMOSTAT-PROTOCOL-MAP.md` (burst contents, no-ack finding).
- Upstream: nebulous/infinitude `lib/CarBus/SAM.pm` (override flow,
  store-but-ignore caution, 0420 note); infinitude wiki
  `Infinity---interpreting-data.md` (register map, SAM notification
  mechanism, table listing incl. 0x40 SCHEDULE, row-flag scheme);
  nebulous/infinitesp issues #49 (half-degree/table-40 live verification),
  #61 (the 4xxx remark; first-ICP confirmation), #41 (registration gate
  contrast).
