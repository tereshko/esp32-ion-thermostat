# Table Scan Plan — enumerate what the Ion (0x20) serves and accepts

Date: 2026-10-30. Desk preparation only — nothing here has been flashed or
transmitted. Purpose: run a **read-only** register-table scan of the wall
control (ICP Ion SYST0101CW, bus `0x20`) from the existing InfinitESP node,
to enumerate every table the Ion serves, hunting for undocumented control
surfaces beyond the 400A comfort row. This is the "table scan of what you do
have" that nebulous suggested in issue #61.

Provenance labels: **Proven** = read directly in the local InfinitESP clone
(`~/workspace/diy-thermostat/infinitesp/`, file/line cited) or in our own
captures/docs. **Inferred** = reasoned from those sources, not directly
observed. Nothing below requires a write frame: **the scan is reads only.**

---

## 1. Mechanism verdict

**No component patch is needed. The scan runs on a stock phase2 build plus a
yaml-only driver.**

- There is **no arbitrary-read facility exposed to the user** in stock
  InfinitESP: the SAM ASCII console (TCP 23) has semantic verbs only
  (`MODE?`, `Z1HTSP?`, `REPORT?`, … — the full dispatch is in
  `components/sam_ascii/sam_ascii.cpp`; HELP lists `MODE RT RH HTSP CLSP FAN
  HOLD OAT TIME DAY ZONE NAME BLIGHT CFGEM REPORT`), the only registered
  ESPHome automation action is `infinitesp.sync_clock`
  (`components/infinitesp/__init__.py`), and there are no custom API services
  (grep: no `register_service` anywhere in `components/`). **Proven.**
- But the hub class already contains a public one-shot read primitive built
  for exactly this: `void poll_register(uint8_t table, uint8_t row)`
  (`infinitesp.h:817`, commented "One-shot poll of a specific thermostat
  register (for discovery / debugging)"). It has **no stock caller** — it is
  dead code waiting for a lambda. It sends `FUNC_READ (0x0B)` with payload
  `{0x00, table, row}` to `ADDR_THERMOSTAT` (hardcoded `0x20`,
  `infinitesp.h:52`) from our node's address (`send_frame_` always sources
  `sam_address_` = `0x92` in the author's config, `infinitesp.cpp:1127`), and
  registers a `PendingPoll` so the reply/exception/timeout machinery tracks
  it like any standing poll (`infinitesp.cpp:2067`). **Proven.**
- Any public hub method is callable from an ESPHome lambda, so a template
  button + a 300 ms `interval:` walker over an embedded `(table,row)` list
  is a complete scan driver in pure yaml (§4). This mirrors how the 400A
  test build exposed its methods, except that test needed a *write* path
  with read-modify-write logic; a read scan needs nothing in C++.
  **Proven** (mechanism) / **Inferred** (that upstream would endorse the
  use — it is, however, exactly what the method's own comment describes).

Two stock facilities support the scan but cannot replace it:

- **Built-in table-name discovery** already probes every *observed*
  (device, table) pair's `0xNN01` tabledef register from source `0x93`
  (`ADDR_FAKESAM`), one probe per 3.5 s, with miss-backoff
  (`poll_discovery_()`, `infinitesp.cpp:1612`; gated off when
  `sam_address == 0x93`). It learns table **names only** — never rows — and
  only for tables already seen in snooped traffic. Its results surface in
  `REPORT?` under `"tables":[]`. **Proven.** Use it as the free pre-pass
  (runbook step 1), not as the scan.
- **`REPORT?`** (SAM ASCII port) streams a JSON snapshot: `"dev":[]`,
  `"tables":[]` (learned names + dropped pairs) and `"regs":[]` — the hub's
  whole register cache, i.e. everything snooped or polled so far
  (`stream_bus_report_`, `infinitesp.cpp:~3519-3620`). It dumps *known*
  state; it cannot enumerate unobserved rows. **Proven.**

**What our node already reads from 0x20 standing** (so the scan skips
these — their status is documented in `THERMOSTAT-PROTOCOL-MAP.md` §3):
fast poll every ~3 s: `3B02`, `3B03`; slow poll on a 31 s rotation
(`infinitesp.cpp:15-56`): `0104`, `3B04`, `4012`, `4202`, `3B05`, `3D02`,
`4608`, `4609`, `460A`, plus the per-zone comfort rows `400A…`. Known
results on this Ion: `0104`/`400A`/`4012`/`4202` return real data;
`3B02`/`3B03`/`3B04`/`3B05` return all-zero payloads (the unregistered-SAM
view); `3D02` is expected silence (ITC-line controls "refuse by silence",
per the slow-poll comment). **Proven** (code + MAP).

---

## 2. Scan matrix (destination `0x20` only, reads only)

Design rules:

- **Tabledef first, conceptually.** Every family's row `01` is its
  self-description: the reply carries the table name at data `[2..9]`,
  total allocated bytes at `[10..11]` (BE16) and the **declared row count
  at `[12]`** (parsed in `handle_discovery_reply_()`,
  `infinitesp.cpp:1735-1743`). Row ranges below are bounded by the
  infinitude register model; after the run, compare *answered rows* vs
  *declared rows* — a mismatch is itself a finding.
- **Skip-known:** rows already classified by standing polls/snooping are
  not re-probed (marked †).
- **Excluded by design:** table `46` rows `08`–`0C` (`4608` WiFi
  credentials, `4609` cloud, `460A` dealer, `460B` WiFi profiles, `460C`
  WiFi scan) — the firmware drops these registers from the JSONL stream
  and `REPORT?` entirely (`register_is_dropped_()`,
  `infinitesp.cpp:3291`), so their replies could not be classified from
  the capture anyway; they are also the credential-bearing rows and out of
  scope for a control-surface hunt. **Proven.**
- **PII flag:** `3B06` (dealer table) is probed as a read; if it answers,
  its payload (dealer name/phone) stays in the local capture — do not post
  that line publicly.

| Table | Family (model) | Rows probed | Notes |
|---|---|---|---|
| `01` | DEVCONFG | 01,02,03,05,06,07,08 | `0104`† real (120 B) |
| `02` | SYSTIME (tstat-owned) | 01,02,03,04 | tstat broadcasts 0202/0203; reads unclassified |
| `03` | RLCSMAIN | 01–14 (hex, 20 rows) | IDU/ODU-side family; tstat-side rows unknown |
| `04` | VARSPEED | 01,02,03,04,08,11 | sparse — IDU drive family, likely absent on tstat |
| `06` | VAR COMP | 01,02,04,05,08,0B,0E,1F | sparse — ODU drive family |
| `1F` | — | 01 | no evidence this is a table; one cheap probe |
| `30` | tstat SAM-interface (SAM spec) | 01,02,03,04,05,06 | a real SAM polls `3003`/`3005` — never tried by InfinitESP |
| `3B` | SAMINFO mirror | 01,06,07,08 | `3B02`–`3B05`† zero/served; `3B06` dealer (PII flag) |
| `3C` | tstat SAM-interface (SAM spec) | 01,02,03,04,05,06,0C,0D,14 | a real SAM polls `3C0C`/`3C0D`/`3C14` |
| `3D` | zone temps 1/16 °F | 01,02,03 | `3D02`† expected silence on this line |
| `3E` | 2-stage ODU family | 01,02,08 | on the tstat: unclassified |
| `3F` | — | 01,02,03,04 | `3F02` is read *from a SAM* at commissioning; tstat-side unknown |
| `40` | SCHEDULE | 01–09, 0B–11, 13–19 (23 rows) | `400A`† real, `4012`† real; 02–09 weekly rows, 0B–11 comfort rows z2–8, 13–19 vacation rows z2–8 unprobed |
| `42` | fault log family | 01,03,04 | `4202`† real (72 B) |
| `46` | WiFi/cloud/dealer family | 01,02,03,04,05,06,07,0D,0E,0F,10 | rows 08–0C **excluded** (see above) |

**Total: 112 probes.** At the §3 pacing of 300 ms that is ≈ 35 s of scan
transmissions per pass; the runbook runs **two passes** (a `SILENCE`
verdict requires two consecutive misses — a single miss can be a collision
or a dropped frame).

Families deliberately **not** probed: `05`, `07`–`0F` (on IDU/ODU these
return FUNC 0x15 wholesale per the header table notes,
`infinitesp.h:406-430`), and any other destination than `0x20` (the
furnace `0x44` and ODU `0x53` tables are already mapped by snooping in
`THERMOSTAT-PROTOCOL-MAP.md`; this scan is about the control).

---

## 3. Pacing and response classification

### Pacing (politeness on a live heating system)

- **One probe per 300 ms**, at most one scan probe outstanding at any
  moment (the walker is strictly sequential). Justification, all
  **Proven**: thermostat request→response latency is median 19 ms / p90
  48 ms (MAP, n=878); the firmware's own discovery poller uses 3.5 s and
  its fast poll ~3 s, so 300 ms is 10× denser than stock discovery yet
  leaves ~85 % of each slot idle; a read frame is ~13 B on a 38400 baud
  bus — 112 probes ≈ 1.5 KB of TX per pass, negligible next to the
  thermostat's own bursts.
- Exception frames (`FUNC 0x15`) carry **no register echo** — attribution
  is by dest + recency only (`handle_exception_()`,
  `infinitesp.cpp:1555`). The 300 ms spacing with ~20-50 ms replies is
  what makes scan-side attribution unambiguous; do not pace faster.
- `poll_register()` transmits immediately via `send_frame_` — it does
  **not** pass through loop()'s bus-idle gate or the install-discovery
  holdoff that protect the stock pollers (**Proven**, `infinitesp.cpp:
  2067` vs `357-516`). Consequences: (a) run the scan only in steady
  state — never while the thermostat is commissioning/relearning (no
  `0x1F` traffic), or a probe could land inside its discovery burst;
  (b) a rare collision with a thermostat burst is possible — that is what
  the two-pass rule and the CRC check (runbook step 5) are for.

### Classification (from the JSONL capture, port 2373)

The capture records **every** bus frame including our own probes
(`docs/bus-capture.md`). Scan probes are the lines
`src="92", dst="20", func="0B"` whose `reg` is in the §2 matrix — the
standing polls share that signature only for the skip-known rows, which
are excluded from the matrix, so matrix rows are attributable by
`(reg, order, timestamp)` inside the scan window. For each probe, take
the first frame `src="20", dst="92"` within **1 s** after it:

| Class | Signature | Meaning |
|---|---|---|
| `DATA` | `func="06"`, data non-zero | served with real content — record length + hex |
| `ZERO` | `func="06"`, data all `00` | served but empty / SAM-view zeroing (the `3B02` pattern) |
| `EXC-04` | `func="15"`, data `04` | register absent (permanent) |
| `EXC-0A` | `func="15"`, data `0a` | row exists but empty (device alive; can gain data) |
| `EXC-10` | `func="15"`, data `10` | write-only register — **a control-surface lead**: a row the control refuses to read because it is meant to be written |
| `SILENCE` | no `06`/`15` within 1 s, on **both** passes | ignored/absent (this line answers some tables by silence, e.g. `3D`) |

Codes per `handle_exception_()` comments (`infinitesp.cpp:1560-1565`):
`0x04` absent and `0x10` write-only are permanent; `0x0a` is
exists-but-empty. **Proven.**

Readout tooling after the run: filter the capture with `jq` —
probes: `select(.src=="92" and .dst=="20" and .func=="0B")`;
replies: `select(.src=="20" and .dst=="92")`. The ESPHome log also prints
`Manual poll: register XXXX` per probe (LOGI, `infinitesp.cpp:2069`) —
the live progress readout during the session. `REPORT?` before/after
corroborates: new `"tables"` names for `0x20` and new non-null `"regs"`
entries are the served rows the hub cached (replies to `poll_register`
go through the normal `handle_reply_` path and are stored,
`infinitesp.cpp:~786-812`). **Proven**, except the regs[] corroboration
for `ZERO` rows, which is **Inferred** (the report builder null-skips
some row classes; treat JSONL as authoritative, REPORT? as supporting).

**View caveat (important):** every probe is sourced from `0x92`, so the
scan maps *what the Ion serves to a SAM-addressed reader* — the same view
that zero-fills `3B02`/`3B03`. A row classified `ZERO`/`SILENCE` here
might still hold real data for the furnace/ODU; that direction is already
covered by passive snooping (MAP). There is no second transmit identity
available for reads: the `0x93` discovery path probes tabledef rows only
and is not user-steerable. **Proven.**

---

## 4. The scan driver (yaml only — add to a copy of phase2.yaml)

Build `phase4-scan.yaml` as a byte copy of `firmware/phase2.yaml` (stock
components — **not** the phase3-test tree; the scan is a separate concern
from the 400A test build) with this block appended. Rollback is reflashing
phase2, exactly like the test build.

```yaml
globals:
  - id: scan_idx
    type: int
    restore_value: no
    initial_value: '0'
  - id: scan_active
    type: bool
    restore_value: no
    initial_value: 'false'

button:
  - platform: template
    name: "Table Scan 0x20 Start"
    on_press:
      - lambda: |-
          id(scan_idx) = 0;
          id(scan_active) = true;

interval:
  - interval: 300ms
    then:
      - lambda: |-
          // TABLE-SCAN-PLAN.md §2 matrix — (table, row), dst is always 0x20.
          static const uint8_t SCAN[][2] = {
            {0x01,0x01},{0x01,0x02},{0x01,0x03},{0x01,0x05},{0x01,0x06},{0x01,0x07},{0x01,0x08},
            {0x02,0x01},{0x02,0x02},{0x02,0x03},{0x02,0x04},
            {0x03,0x01},{0x03,0x02},{0x03,0x03},{0x03,0x04},{0x03,0x05},{0x03,0x06},{0x03,0x07},
            {0x03,0x08},{0x03,0x09},{0x03,0x0A},{0x03,0x0B},{0x03,0x0C},{0x03,0x0D},{0x03,0x0E},
            {0x03,0x0F},{0x03,0x10},{0x03,0x11},{0x03,0x12},{0x03,0x13},{0x03,0x14},
            {0x04,0x01},{0x04,0x02},{0x04,0x03},{0x04,0x04},{0x04,0x08},{0x04,0x11},
            {0x06,0x01},{0x06,0x02},{0x06,0x04},{0x06,0x05},{0x06,0x08},{0x06,0x0B},{0x06,0x0E},{0x06,0x1F},
            {0x1F,0x01},
            {0x30,0x01},{0x30,0x02},{0x30,0x03},{0x30,0x04},{0x30,0x05},{0x30,0x06},
            {0x3B,0x01},{0x3B,0x06},{0x3B,0x07},{0x3B,0x08},
            {0x3C,0x01},{0x3C,0x02},{0x3C,0x03},{0x3C,0x04},{0x3C,0x05},{0x3C,0x06},{0x3C,0x0C},{0x3C,0x0D},{0x3C,0x14},
            {0x3D,0x01},{0x3D,0x02},{0x3D,0x03},
            {0x3E,0x01},{0x3E,0x02},{0x3E,0x08},
            {0x3F,0x01},{0x3F,0x02},{0x3F,0x03},{0x3F,0x04},
            {0x40,0x01},{0x40,0x02},{0x40,0x03},{0x40,0x04},{0x40,0x05},{0x40,0x06},{0x40,0x07},
            {0x40,0x08},{0x40,0x09},{0x40,0x0B},{0x40,0x0C},{0x40,0x0D},{0x40,0x0E},{0x40,0x0F},
            {0x40,0x10},{0x40,0x11},{0x40,0x13},{0x40,0x14},{0x40,0x15},{0x40,0x16},{0x40,0x17},
            {0x40,0x18},{0x40,0x19},
            {0x42,0x01},{0x42,0x03},{0x42,0x04},
            {0x46,0x01},{0x46,0x02},{0x46,0x03},{0x46,0x04},{0x46,0x05},{0x46,0x06},{0x46,0x07},
            {0x46,0x0D},{0x46,0x0E},{0x46,0x0F},{0x46,0x10},
          };
          static const int SCAN_N = sizeof(SCAN) / sizeof(SCAN[0]);
          if (!id(scan_active)) return;
          if (id(scan_idx) >= SCAN_N) { id(scan_active) = false; return; }
          id(infinitesp_hub).poll_register(SCAN[id(scan_idx)][0], SCAN[id(scan_idx)][1]);
          id(scan_idx)++;
```

Pressing the button again restarts the walker from index 0 — that is the
second pass. No `on_boot`, no automation fires it unattended; if the ESP
reboots mid-scan the globals reset and the scan simply stops.
**Proven** (all stock ESPHome constructs; `poll_register` is public,
`infinitesp.h:817`; hub id `infinitesp_hub` per `firmware/phase2.yaml:111`).

---

## 5. Risks and abort criteria

- **Reads only.** The driver cannot emit a write: `poll_register` builds a
  `FUNC_READ` frame and nothing else. The known worst case of a read on
  this bus is a reply, an exception, or silence. **Proven** (code).
- **No commissioning during the scan.** Do not combine with a FULL
  INSTALLATION / reseat window: `poll_register` bypasses the 180 s
  install-discovery holdoff (§3), and the SAM-registration question must
  not be confounded by 112 extra reads. Separate sessions.
- **System state:** run with the system in a normal steady state (idle or
  a normal call — either is fine; reads don't steer demand). Avoid the
  first ~5 min after any power event (the thermostat's own `0x1F` phase
  and the furnace's absent-node bursts, MAP §cold-start).
- **Abort if:** ESPHome `STATS` shows `crc_fail` climbing during the scan
  (collisions), the thermostat posts a communication fault, or HA climate
  state flaps. Any of these → stop pressing the button (the walker halts
  at the end of the current 300 ms step; a reboot also halts it) and let
  the bus settle.

---

## 6. Runbook — at-the-wall session (≤ 15 min)

Preconditions: ESP on reliable power for the session (wall USB, not the
power bank — two of yesterday's windows are still unexplained), laptop on
the LAN, system in steady state.

1. **(2 min) Baseline.** Start the JSONL capture
   (`python capture.py tablescan` in the flash-kit folder). Pull a
   `REPORT?` snapshot (recipe in `docs/sam-ascii.md`) and save it as
   `report-before.json` — its `"tables"` for address `20` are the free
   pre-pass (names the built-in discovery already learned).
2. **(3 min) Flash.** Copy `phase2.yaml` → `phase4-scan.yaml`, append the
   §4 block, `esphome run phase4-scan.yaml` (OTA). Wait for the hub to be
   back and the fast poll to resume in the capture.
3. **(1 min) Pass 1.** In HA, press **Table Scan 0x20 Start**. Watch the
   ESP log for `Manual poll:` lines (~35 s) — 112 probes.
4. **(1 min) Pass 2.** Press the button again. Same ~35 s.
5. **(2 min) Health check.** Read the `STATS` line: `crc_fail` must be
   unchanged from baseline, `reply_timeout` may rise by roughly the
   silence-class count (expected — those are the scan's misses, each
   pending poll times out at 5 s in the counters only).
6. **(2 min) Readout.** Pull `REPORT?` again (`report-after.json`), stop
   the capture. Reflash `phase2.yaml` (rollback; ~2 min OTA) — the scan
   build should not stay live.
7. **After the session (desk work, no wall time):** classify per §3,
   diff answered rows vs tabledef-declared rows, and fold anything
   `DATA`/`EXC-10` into the register map + the issue #61 follow-up.

Total wall time ≈ 11-13 min including both flashes.

---

## 7. NIM verdict — is "present as a NIM (0x80)" buildable today?

**Yes — buildable as a pure config change in the stock stack. No code
work. But it is the wrong shape for the author's control problem, and it is
experimental. Do not commission it on the live system for control
purposes.** Details:

- **Support exists and is complete enough to commission-shaped.**
  `nim_address:` (0 = disabled) plus a `nim:` block (defrost sensor,
  `on_heat_stage` / `on_cool_stage` / `on_defrost` automations) are in
  stock codegen (`__init__.py:57-65, 190-214, 369-385`). Setting
  `nim_address: 0x80` makes `initialize_defaults_()` seed a full NIM
  register set at that address — `0104` identity, `0302` descriptor
  (`04 11 00 00`), `0305` demand, `030D` diag, `030E` cfg status, `0310`
  cycles, `0311` runtime (with an hourly tick), `0316` status, plus the
  `3405` presence row the thermostat's install sweep probes at `0x80`
  (observed in our own cold-start capture, MAP §cold-start) — all served
  through the generic read handler, with faithful real-NIM quirks: reads
  of `031C` get deliberate silence and writes are never ACKed
  (`infinitesp.cpp:1190-1265, 2891-2984`). **Proven.**
- **Upstream labels it experimental**: header comments call it a
  "branch-local experiment" (`infinitesp.h:696`), and codegen emits a
  warning at config time — protocol shapes validated on an Infinity
  Touch, "no other control model has been tested" (`__init__.py:212-214`).
  The Ion is Touch-family, which is the one family named; the ICP build
  has still never seen it. **Proven** (the warning), **Inferred** (what it
  would do on the Ion).
- **Semantic direction is backwards for control.** A NIM is something the
  thermostat *commands*: it receives standing `0305` demand writes (heat
  stage `[0]`, cool stage `[2]`), mirrors them into `0316`, and the ESP
  side acts through the stage triggers (in upstream's design: relays to a
  dumb heat pump). Presenting as a NIM gives the Ion a fake
  non-communicating heat pump to drive — it creates **no setpoint/mode
  surface toward us**, and it invites the Ion to re-derive its equipment
  configuration around a bridged legacy unit mid-heating-season. The
  Ion's equipment screen tracks a NIM slot ("no NIM" placeholder, the author's
  photo 2026-10-29), so it *would* be looked for — which is precisely the
  risk.
- **`sam_address` and `nim_address` are independent switches**;
  codegen only rejects address collisions with fixed bus roles
  (`__init__.py:208`). Running both is possible in principle —
  **Inferred** (not tested in this clone's configs) — but irrelevant
  unless a future design wants the ESP to *receive* demand (e.g. the
  full-emulation endgame), where the NIM demand model is worth
  remembering.

---

## 8. Proven vs inferred — index

**Proven (source/captures):** SAM ASCII has no raw-read verb; the only
ESPHome action is `sync_clock`; `poll_register(table,row)` exists, is
public, uncalled by stock code, targets `0x20` from `sam_address_`, and
feeds the standard pending-poll/reply/exception machinery (5 s counter
timeout; exceptions carry no register echo; codes 04/0A/10 semantics);
the built-in discovery probes `0xNN01` tabledefs only, from `0x93`, one
per 3.5 s; tabledef payload layout (name `[2..9]`, alloc `[10..11]`,
rows `[12]`); standing poll sets and their known results on this Ion;
JSONL records all frames incl. our own, with registers `4608-460C`
dropped by design; thermostat reply latency median 19 ms / p90 48 ms;
NIM emulation is config-only to enable, seeds the full NIM table set,
implements the silent-031C / no-ACK write behavior, and is labeled
experimental by upstream.

**Inferred:** that `REPORT?` `regs[]` corroborates ZERO-class rows (JSONL
is authoritative regardless); that two-pass 300 ms probing stays
collision-free on this bus in practice (bounded by the §5 abort
criteria); that SAM+NIM addresses can be enabled simultaneously without
interaction; everything about how the Ion would react to a NIM
presentation (never attempted, and per §7 not recommended for control).
