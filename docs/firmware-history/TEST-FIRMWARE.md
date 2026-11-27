# TEST FIRMWARE — Variant B direct-write test build

One-off, supervised test build for the experiment specified in
`../DIRECT-WRITE-RESEARCH.md` §5 (Variant B): steer a **wall-armed** hold
by rewriting the thermostat's zone-1 comfort row (register **400A**),
manual entry, one byte at a time (offset **29** = manual cool,
offset **28** = manual heat), whole °F, full-row read-modify-write,
func 0x0C frame to 0x20: `[0x00, 0x40, 0x0A]` + 35-byte row.

**Status: TESTED 2026-10-30 — PASS.** Flashed by OTA and run at the
wall: the Ion stores this build's 400A manual-entry writes from the
unregistered SAM node (six consecutive polls over 24 min returned the
written byte) and its manual screen adopts bus-written setpoints
(criteria 6a/6b pass, 6c partial). Full report:
`../400A-TEST-RESULT.md`. Roll back to phase2 after use.

---

## 1. What differs from phase2 (complete list)

**Components** — `phase3-test.yaml` points ESPHome's local
`external_components` at `test-components/` (in this folder) instead of
the stock `components/`. `test-components/` is a byte-for-byte copy of
the stock tree (`infinitesp/components/`: bus_jsonl, infinitesp,
sam_ascii, uart_rmtx) with exactly **one additive change**, verified by
diff: 0 stock lines modified or removed.

In `test-components/infinitesp/infinitesp.h` / `infinitesp.cpp`, three
methods were added next to the existing `command_setpoint_half()`:

- `bool test_write_manual_cool(uint8_t fahrenheit)` — public
- `bool test_write_manual_heat(uint8_t fahrenheit)` — public
- `bool test_write_manual_entry_(bool is_heat, uint8_t fahrenheit)` —
  private shared core

The core is the proven holding branch of `command_setpoint_half()`
(reply to issue #49's table-40 path) with the two caller-side gates
removed — no °C-bus requirement, no fractional-target requirement —
because on this °F bus the row byte is simply the whole °F value. It
also drops the no-hold deferral and arms **nothing**: the override must
already be armed at the wall. Per call it:

1. refuses if SAM emulation is off (same backstop as stock);
2. refuses values outside 40–99 °F (sanity clamp; every setpoint ever
   observed on this system is 60–81 °F);
3. refuses if the zone-1 comfort row is not in the register cache yet
   (populated by the stock slow poll — wait a few minutes after boot);
4. copies the cached 35-byte row, changes **exactly one byte**
   (28 heat / 29 cool), queues the stock write frame
   `[0x00, 0x40, 0x0A]` + row via the stock `send_write_frame_`
   (bus-idle gated, stock retries of the identical payload — the write
   is idempotent), and updates the local cache to the written row
   (the next slow poll reconciles the cache with the wall's stored row
   either way);
5. logs `TEST 400A manual cool byte 29: 76 -> 74 F (full-row write
   queued)` (tag `InfinitESP`) — your confirmation in the ESP log.

**Config** — `phase3-test.yaml` is phase2.yaml with the components path
changed and four entities appended (see §3). Device name, substitutions,
`sam_address: 0x92`, climate "House" (zone 1), BLE/Wi-Fi/status sensors,
UART, TCP servers (23 / 2373) are all identical, so the HA device and
its existing entities are untouched.

**No other differences.** The stock local component tree in
`../infinitesp/` is untouched; phase1/phase2 builds are unaffected.

## 2. The 3B03 confound — audited, climate entity KEPT

Research §5 requires **zero 3B03 writes during the test window** (on
Touch evidence, a 3B03 write regenerates the manual entry from the
override's rounded value and would stomp/confound the test write).
Audit of every write path in this exact configuration:

- All 11 `send_write_frame_` call sites in the component are behind
  explicit commands: HA climate `control()` (setpoint/fan/mode/preset/
  hold → 3B03/3B02/3B04), setter entities (number/select/datetime/
  button — **none are declared in this config**, so their paths,
  including the debounced `pending_hold_sets_` drain in `loop()`, can
  never be armed), and SAM ASCII console commands (only if someone
  connects to TCP port 23 and types them).
- There are **no autonomous writers**: nothing in `setup()`, `loop()`,
  the poll engine, or the climate entity emits a bus write on a timer,
  at boot, or on HA reconnect. Polls are reads; replies are reactive.
- Therefore the climate entity does **not** need to be disabled, and it
  is kept (entity stability + the research's own preconditions assume
  it exists and is simply not used). The discipline that makes the test
  valid is procedural, and it is strict:

> **During the whole test window: do NOT touch the "House" climate
> card in HA (no setpoint, mode, preset, or fan changes), do NOT use
> any HA automation/scene that targets it, and do NOT connect to the
> SAM ASCII console (port 23).** Any of those emits exactly the 3B03
> traffic the test forbids.

## 3. What you'll see in Home Assistant

Same **DIY Thermostat** device, all phase2 entities as before, plus:

| Entity | Type | Role |
|---|---|---|
| `Test Manual Cool °F` | number (50–90, step 1) | Inert value holder for the cool byte. Setting it writes **nothing**. |
| `Test Manual Heat °F` | number (50–90, step 1) | Inert value holder for the heat byte. Setting it writes **nothing**. |
| `TEST Write 400A Manual Cool` | button | On press: the single 400A write with byte 29 = the cool number. |
| `TEST Write 400A Manual Heat` | button | On press: the single 400A write with byte 28 = the heat number. |

The write happens **only** on a button press. There is no `on_boot`,
interval, or automation anywhere in this build that can call the test
methods.

## 4. How to flash it (your usual flow)

1. In your build folder (the one holding `secrets.yaml` and the phase2
   kit), copy in, side by side:
   - `phase3-test.yaml` (from this folder)
   - `test-components/` (this whole folder)
   
   (`secrets.yaml` stays as-is; the YAML finds components at
   `./test-components` and secrets at `./secrets.yaml`.)
2. `esphome run phase3-test.yaml` — OTA to the running device is fine
   (same device name), USB works too. First compile takes a while, as
   before; the git uart-link component is fetched exactly as in phase2.
3. After it boots, **wait ≥ 5 minutes** before the test: the node must
   complete a slow-poll cycle so the 400A row is in its cache (a press
   before that just logs a refusal — harmless, but don't mistake it for
   a result).
4. Confirm the four test entities appeared on the DIY Thermostat device
   in HA.

Rollback at any time: `esphome run phase2.yaml` (it uses the stock
`components/`). The test number/button entities in HA become orphaned
and can be deleted there. The build itself changed nothing on the wall;
only the test-day button presses write anything, and §5 ends with a
byte-exact revert.

## 5. Test-day sequence (Variant B, from the research, adapted)

Preconditions: you are home, watching the Ion screen; bus capture
running (`capture.py`, JSONL on :2373) **before** step 1 and until after
the revert; system in **Cool**, Per Schedule; a mild moment. Hands off
the wall between steps 2 and 7 except as written. Hands off the HA
climate card for the entire window (§2).

0. *(Research's optional 4001 flags read — SKIPPED in this build: no
   stock tool or button reads register 4001 on demand. Per the
   research, a read-only flag would downgrade expectations but not
   cancel the test, so we proceed without it.)*
1. **Fresh read.** In the capture, wait for a 400A exchange
   (0x92 → 0x20 read of 400A, then the 0x20 reply with 35 bytes).
   Save those 35 bytes as **ROW0**. (Expected from the archive:
   `444C0044891E1E3C50004F001E1E444C0044891E1E444C0044891E1E4F510044891E1E`
   — but the fresh read rules.)
2. **Arm the hold at the wall.** Tap the cool setpoint on the Ion to
   arm a manual hold at value **V**. Note V and the room temperature R
   shown on the wall.
3. **Re-read.** Wait for the *next* 400A exchange in the capture;
   save the reply bytes as **ROW1**. This reply also refreshes the
   node's cache, so the button's read-modify-write is based on the
   true current row. Per the Touch model, expect `ROW1[29] == V`. If
   it isn't, note it and proceed anyway (the write then tests raw
   steering directly, per the research).
4. **Set the target.** In HA, set `Test Manual Cool °F` to **V − 2**.
   Choose V so that V − 2 < R if you want a real cooling call as the
   strong signal; otherwise the display signal (6b) is the criterion.
5. **Write once.** Press `TEST Write 400A Manual Cool` **once**. Check
   the ESP log for `TEST 400A manual cool byte 29: V -> V-2 F`.
6. **Observe**, in the research's order of strength:
   a. Next 400A reply in the capture == ROW2 (ROW1 with byte 29 = V−2)
      → the Ion **stores** foreign table-40 writes.
   b. Wall display (wake the screen first) shows the held cool
      setpoint as V−2, untouched → the engine **consults** the row live.
   c. Demand burst in the capture: furnace 0305 byte[2] = 0x02 /
      CFM > 0 and ODU 0605 staging float > 0 → a real cooling **call**
      started (only expected if V−2 < R).
7. **Hold the observation ~3–5 min** (several burst cycles, at least
   two 400A poll cycles) to catch any delayed regeneration back to V.
8. **Revert (byte-exact).** Set `Test Manual Cool °F` back to **V** and
   press `TEST Write 400A Manual Cool` once. Under the window's
   no-other-writers discipline this retransmits ROW1 (same row, byte 29
   restored to V — every other byte is the cached current row, which
   nothing else has touched). Wait for the next 400A reply and confirm
   it equals ROW1. Then cancel the hold at the wall (resume schedule).
   The manual entry is scratch space the wall rewrites on its next
   manual interaction, so even a missed revert self-heals; nothing in
   any profile or schedule was touched.

**Heat twin (winter):** identical with mode **Heat**, a wall-armed heat
hold at V, `Test Manual Heat °F` set to **V + 2**, button
`TEST Write 400A Manual Heat` (byte 28), and the same revert with the
number set back to V.

**Reading the result** (research decision tree): 6a fails → writes from
an unregistered node are not stored on this ICP build; stop, that is a
reportable answer for issue #61. 6a passes but 6b fails → storage works,
live consultation doesn't; Variant A (profile-entry edit) is the
follow-up, not part of this build. 6b/6c pass → phase 2 is alive in
direct-write form.

## 6. Validation performed (and its limit)

- **ESPHome is not installed in the preparation environment** (no
  `esphome` binary, no Python module), and per instructions nothing was
  installed — so `esphome config` / a compile could **not** be run here.
  **The first real gate is your local `esphome run` compile.** If it
  errors, send the full text back before flashing anything.
- What was checked instead:
  - `phase3-test.yaml` parses cleanly as YAML (tolerant parser for
    ESPHome's `!secret` tags); its structural diff vs phase2.yaml is
    exactly: components path, header comments, and the added
    `number:`/`button:` sections.
  - The component copy's diff vs the stock tree is purely additive
    (0 stock lines changed) and confined to `infinitesp.h` /
    `infinitesp.cpp`.
  - The lambda binding was verified against the component's codegen:
    the hub id is declared as `InfinitESPComponent` (`__init__.py`),
    so `id(infinitesp_hub).test_write_manual_cool(...)` resolves to the
    new public methods; the inserted C++ block is brace/paren balanced
    and mirrors the stock holding-branch code line-shape (same
    `get_register` / `send_write_frame_` / `store_register_` usage).

## 7. Deviations from the research spec (with reasons)

1. **Research step 0 (read 4001 flags) not implemented** — optional in
   the research, no on-demand register-read facility exists in the
   stock build, and its outcome would not cancel the test either way.
2. **Revert uses the same button** (re-press with the number restored
   to V) instead of a separate raw-frame sender. Equivalent under the
   test window's no-other-writers discipline, and the capture re-read
   (step 8) is the ground-truth check either way.
3. **Sanity clamp added** (firmware refuses < 40 or > 99 °F; HA numbers
   limited to 50–90 °F). The research doesn't ask for one; it only
   constrains implausible fat-finger values and cannot block any value
   the research's test uses.
4. **Zone hardwired to 1** inside the test methods
   (`comfort_reg_for_zone(1)` = 0x400A). This is a single-zone install
   and the research's spec is zone-1-only.
5. **Climate entity kept, not disabled** — §2's audit shows the stock
   build emits zero autonomous 3B03 writes in this configuration, so
   disabling it is unnecessary; the research's own preconditions
   (human discipline during the window) are the operative control.
