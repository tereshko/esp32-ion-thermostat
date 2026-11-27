# PHASE 3 CONTROL — production direct-write build

Production build on the path proven at the wall on 2026-10-30
(`../400A-TEST-RESULT.md`): Home Assistant owns the Ion's Touch-N-Go
**manual** setpoints via guarded direct writes to register **400A**
(zone-1 comfort row, byte **28** = manual heat, byte **29** = manual
cool, whole °F, full-row read-modify-write, func 0x0C to 0x20).

**Product contract (the author's decision, 2026-10-30):** the wall lives on
Touch-N-Go **MANUAL**; HA owns the two manual setpoints. Schedule
profiles (home/away/sleep/wake) are **never** written by this build.

**Status: FLASHED 2026-11-03, VALIDATED the same day (criterion 6c
PASSES — see traces/INDEX.md, phase3-validation3). In service: the
wall lives on Touch-N-Go MANUAL, HA owns the two manual setpoints.**

---

## 1. What's in the kit

| Piece | What it is |
|---|---|
| `phase3-control.yaml` | phase2.yaml + control surface (§3). Same device name, `sam_address: 0x92`, climate "House", BLE/Wi-Fi/status entities — the HA device and all its existing entities are untouched. |
| `control-components/` | Byte-for-byte copy of the stock tree (`../infinitesp/components/`: bus_jsonl, infinitesp, sam_ascii, uart_rmtx) with **one additive feature** in the infinitesp hub, verified by diff: 0 stock lines modified or removed, changes confined to `infinitesp/infinitesp.h` / `infinitesp.cpp`. |
| `PHASE3-CONTROL.md` | This file. |

## 2. The hub feature (control-components/infinitesp)

Public methods added next to `command_setpoint_half()`; private core
`write_manual_entry_(bool is_heat, uint8_t fahrenheit)` next to
`defer_manual_row_write_()`:

- `bool write_manual_heat(uint8_t fahrenheit)` / `bool write_manual_cool(uint8_t fahrenheit)`
- `int get_manual_heat_f() const` / `int get_manual_cool_f() const` — the
  node's current knowledge of bytes 28/29, −1 while the row is uncached.
- `uint32_t get_comfort_cache_age_ms() const` — age of the (0x20, 0x400A)
  cache entry; `UINT32_MAX` if never stored.

**The write core is the proven test core carried over, not redesigned.**
Frame shape and semantics are identical to `test_write_manual_entry_`
(same as `command_setpoint_half`'s holding branch): copy the cached
35-byte row, change exactly one byte, queue payload `[0x00, 0x40, 0x0A]`
+ row via the stock `send_write_frame_` (bus-idle gated, stock retries
of the identical payload — the write is idempotent), then
**write-through cache update** via `store_register_` with the written
row.

*Write-through verification (required by the build spec):* it is real
in the code — the `store_register_(ADDR_THERMOSTAT,
comfort_reg_for_zone(1), new_row)` call immediately after
`send_write_frame_` is present in the stock holding branch, in the test
core, and in this core, in the same position. It is also what the test
session showed: write 2's frame (14:53:29) read-modify-wrote from the
row as established by write 1 instead of a pre-write-1 snapshot. The
stock slow poll reconciles the cache with the wall's stored row on its
next cycle either way (~4 min 40 s observed).

### Guards (all in the core; a refused write queues NO frame)

Order of checks; every refusal logs a `ESP_LOGW` line under tag
`InfinitESP` and returns false:

1. SAM emulation off → refuse (stock backstop).
2. Value outside 40–99 °F → refuse (backstop behind the HA ranges).
3. Zone-1 comfort row not in cache yet → refuse (wait for a poll).
4. **(a) Freshness:** row cache older than **10 minutes**
   (`register_fresh_(..., MANUAL_WRITE_MAX_CACHE_AGE_MS = 600000)`)
   → refuse + log. Rationale: the RMW base must be current knowledge
   of the wall's row; writing from a stale snapshot could resurrect
   bytes the wall has since changed.
5. **(c) Equality no-op:** value == stored byte → log + return true,
   no frame. (Load-bearing for §3's loop argument.)
6. **(b) Deadband:** the pair after the write must satisfy
   **cool ≥ heat + 3 °F**, computed against the other byte's **CURRENT
   STORED** value (the cached row). Otherwise refuse + log naming both
   values. The other byte is never silently clamped, rounded, or
   co-written — the frame changes exactly one byte, as proven.

A queued write logs: `400A manual heat byte 28: 76 -> 78 F (full-row
write queued)`.

## 3. The HA interface (phase3-control.yaml)

| Entity | Type | Range | Role |
|---|---|---|---|
| `Manual Heat Setpoint °F` | number (step 1, box) | 50–85 °F | The manual heat byte, owned by HA |
| `Manual Cool Setpoint °F` | number (step 1, box) | 60–99 °F | The manual cool byte, owned by HA |

**Write path.** Each number's `set_action` (ESPHome invokes it only for
an external set call — HA UI, service call, automation) calls the hub
write **once** with the requested whole °F, then re-publishes the
**stored** byte from the cache getter. Consequences: a successful write
shows the new value immediately (write-through cache = stored
knowledge); a refused write visibly snaps the entity back to the truth
instead of displaying a phantom setpoint.

**Read-back sync.** A single `interval: 45s` lambda publishes the
stored bytes into the number states, only when they differ. Boot state:
numbers show their `initial_value` placeholders (68/76) until the first
poll populates the cache (row is polled ~4 min 40 s cadence) and the
next sync tick converges them — allow ~5 min after flashing before
judging or steering, same as the test build. (The ~4 min 40 s is the
full cycle of the node's own slow-poll rotation over all its tables;
PHASE5 §1.2 states the same rotation as a 31 s step. Not to be
confused with the thermostat's ~3 s 3B02/3B03 polling of the node —
different tables, opposite direction.)

### Why sync can never cause a write — the loop argument, airtight

Two independent layers, either of which alone suffices:

1. **Structural (no code path).** The sync lambda's only effector is
   `publish_state()`. In ESPHome, `publish_state()` updates the
   entity's local state and reports it to HA; it does **not** invoke
   `set_action`. `set_action` is reached exclusively from
   `Number::control()`, i.e. an external set request arriving over the
   API. There is no `on_value` trigger, no automation, no other caller
   of `write_manual_*` anywhere in this config or component — the only
   callers are the two `set_action` lambdas. A bus-originated value
   therefore has no path back into the write method. (This is why
   `set_action` was chosen over an `on_value` design: `on_value` DOES
   fire on `publish_state`, which would have made correctness depend
   on a runtime flag instead of on the absence of a path.)
2. **Equality (even if a path existed).** Sync publishes *the stored
   byte itself*. Any re-entry with that value hits guard (c): equal to
   the stored byte → no frame, return. The fixed point is exact, not
   statistical: sync output ≡ write input that is defined to no-op.

**Re-seed convergence.** When the wall re-seeds the manual entry from
the active schedule profile (mode/profile re-entry — observed
2026-10-30: writes of 75/74 replaced by home's 68/76 after Off→Auto),
the next poll updates the cache and the next sync tick moves both
entities to **the thermostat's** values. HA never "fights" the wall by
re-writing its own last values: nothing in this build remembers a
desired setpoint. What HA shows is what the wall holds. That is the
designed behavior, not a bug (see §5).

## 4. How to flash it (your usual flow)

1. In your build folder (the one holding `secrets.yaml`), copy in,
   side by side:
   - `phase3-control.yaml` (from this folder)
   - `control-components/` (this whole folder)

   (`secrets.yaml` stays as-is; the YAML finds components at
   `./control-components` and secrets at `./secrets.yaml`.)
2. `esphome run phase3-control.yaml` — OTA to the running device is
   fine (same device name), USB works too. First compile takes a
   while; the git uart-link component is fetched exactly as in phase2.
   **This first local compile is the gate** (see §7): if it errors,
   send the full text back before flashing anything.
3. After it boots, **wait ≥ 5 minutes**: the node must complete a
   slow-poll cycle so the 400A row is cached (a set before that just
   logs a refusal — harmless, but don't mistake it for a result).

Rollback at any time: `esphome run phase2.yaml` (stock `components/`).
The two numbers from this build become orphaned in HA and can be
deleted there (same procedure as the TEST entities, §5).

## 5. The wall contract — read before first use

- **Touch-N-Go stays on MANUAL.** The numbers steer the manual entry;
  the manual entry governs only while it is the active Touch-N-Go
  selection (or an armed hold derived from it — the Variant B
  composition proven on 2026-10-30). If the wall is switched back to a
  schedule profile (home/away/sleep/wake) or the system mode is
  re-entered, the Ion runs its schedule and the HA numbers have no
  effect **until manual is active again** — and on re-entry the manual
  entry is **re-seeded from the then-active profile**, so the entities
  will move to the profile's values (e.g. 68/76). All of that is the
  control working as designed; HA's job in this build is to show the
  wall's truth, which the sync does within one poll + one tick.
- **What the Ion screens show:** the home screen displays the ACTIVE
  setpoints — the manual pair while manual is active (that's where the
  photographed HEAT TO 78 appeared), the schedule profile's pair in
  auto/schedule (68/76 in the photos). The Touch-N-Go screen shows the
  manual pair and is where the author arms/selects manual at the wall.
- **Do not steer with the "House" climate card.** It is kept for
  display/telemetry parity with phase2, but its setpoint path is the
  stock SAM 3B03 route — on this unregistered control the Ion ignores
  it, and a 3B03 write can regenerate the manual entry and stomp a
  value set here. The two numbers are the only steering surface.
- **Cleanup of the TEST entities:** in HA, the four orphaned entities
  from the test build — `Test Manual Cool °F`, `Test Manual Heat °F`,
  `TEST Write 400A Manual Cool`, `TEST Write 400A Manual Heat` — can be
  deleted (Settings → Devices → DIY Thermostat → select entity →
  delete) once this build is flashed; they were orphaned already by
  the rollback to phase2, and this build does not resurrect them (the
  production entities have different names and ids).
- **Standing cautions unchanged:** ESP on reliable power for control
  duty (the power-bank caveat from phase 2 applies doubly now — if the
  node dies, the wall simply keeps the last manual values; nothing
  unsafe happens, control just stops). System mode on the wall is
  the author's choice; this build writes setpoint bytes only, never mode.

## 6. First-run checks + validation session

### First-run checks (right after §4, no capture needed)

1. Two new entities on the DIY Thermostat device: `Manual Heat
   Setpoint °F`, `Manual Cool Setpoint °F`. Within ~5 min they show
   the wall's current manual values (compare with the Touch-N-Go
   screen), not the 68/76 placeholders.
2. ESP log shows no `400A write refused` lines while idle, and no
   writes at all while idle — the build writes only on a user set.
3. Change heat by 1 °F in HA: entity keeps the new value (does not
   snap back); log shows `400A manual heat byte 28: OLD -> NEW F
   (full-row write queued)` exactly once.
4. Try to break the deadband (set heat to stored-cool − 2): log shows
   the deadband refusal and the entity snaps back to the stored value.
   This is the refusal path working — then set it back if needed.

### Validation session (closes criterion 6c — do once, supervised)

Preconditions: the author home at the wall; capture running
(`capture.py`, JSONL on :2373) before step 1; a moment when a heat
call is acceptable. Wall: Touch-N-Go **manual** active, system mode
**Heat**. Hands off the HA climate card throughout (§5).

1. In the capture, wait for a 400A poll reply; note byte 28 (heat) —
   this is the stored manual heat the session starts from.
2. In HA, raise `Manual Heat Setpoint °F` above the room temperature
   (room + 2 or more). In the capture: exactly **one** func-0x0C
   400A write frame from 0x92; the next 400A poll reply returns the
   new byte 28.
3. Watch the demand side: furnace 0305 payload gains a nonzero stage/
   CFM and the blower/burner start — a real heat call, on the HA
   number, with no wall touch. Photograph the Ion manual screen
   showing the HA-set HEAT TO.
4. Hold ~5 min (at least two 400A poll cycles): byte 28 stable in
   every reply; no regeneration; no extra write frames.
5. In HA, lower `Manual Heat Setpoint °F` below the room temperature:
   one write frame; demand falls to zero; the call ends.
6. Stop the capture. Set the wall and the HA numbers to the values
   the author wants to live with (mode/profile state is his standing
   choice). Archive the capture into `../traces/`.

Reading the result: steps 2–3 + 5 clean = criterion 6c passes and the
control loop HA → bus → Ion → furnace is proven end to end. If the
poll reply does NOT return the written byte, that contradicts
2026-10-30 and everything stops — keep the capture and escalate
before any further writes.

## 7. Validation performed (and its limit)

- **ESPHome is not installed in the preparation environment** — so
  `esphome config` / a compile could **not** be run here, and nothing
  was installed. **The first real gate is your local `esphome run`
  compile**, exactly as with the test build.
- What was checked instead:
  - `phase3-control.yaml` parses cleanly as YAML (tolerant parser for
    ESPHome's `!secret` tags); its structural diff vs phase2.yaml is
    exactly: components path, header comments, and the added
    `number:` / `interval:` sections (functional body verified
    token-identical to phase2 apart from the path line).
  - The component diff vs the stock tree is **purely additive**
    (0 lines removed/changed) and confined to
    `infinitesp/infinitesp.h` / `infinitesp.cpp`; the added C++ block
    is brace/paren balanced and mirrors the test core (itself proven
    on hardware) line-shape: same `get_register` /
    `register_fresh_` / `send_write_frame_` / `store_register_` usage.
    `register_fresh_` and `register_last_ms_` are stock members; the
    getters read the same stamp map `register_fresh_` reads.
  - The lambda bindings were verified against the component's codegen:
    the hub id is declared as `InfinitESPComponent` (`__init__.py`),
    so `id(infinitesp_hub).write_manual_heat(...)` /
    `.get_manual_heat_f()` resolve to the new public methods.
    Template-number `set_action` receives the requested value as `x`
    (float); `publish_state(float)` is the stock Number API used by
    the sync and the post-write republish.

## 8. Deviations from the test build (with reasons)

1. **Buttons removed; numbers write directly.** The test build needed
   a human-pressed, two-step action for a supervised experiment. The
   production contract is a thermostat, not an experiment: a set IS
   the command. The one-frame-per-set property is preserved by the
   set_action wiring (§3), not by a button.
2. **Freshness and deadband guards are new** (test core had only the
   SAM/range/cache-presence checks). They constrain only states that
   were out of scope for the supervised test (stale base row,
   inverted pair); every value exercised on 2026-10-30 passes them.
3. **Zone hardwired to 1** inside the control methods
   (`comfort_reg_for_zone(1)` = 0x400A), same as the test build —
   single-zone install.
4. **HA ranges differ per direction** (heat 50–85, cool 60–99) per the
   product spec; the hub's 40–99 backstop is unchanged.
