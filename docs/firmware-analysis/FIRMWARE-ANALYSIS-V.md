# FIRMWARE-ANALYSIS-V.md — Thermostat ↔ SAM bus relationship: full specification

Stage V, 2026-11-26. Desk work only; nothing transmitted. Purpose: specify
completely how a thermostat at **0x20** relates to a SAM at **0x92** on the
ABCD bus, so that (a) the future 0x20 emulator treats a SAM exactly as the
Ion SYST0101CW does — and does not care when no SAM is present — and (b) our
current InfinitESP node (which lives at 0x92 today) can be audited against
real-SAM behaviour.

**Source classes** — every claim is tagged:
- **[CAP]** = counted/measured in our captures (`traces/`, ≈26.5k frames,
  plus the 2026-11-02 `evidence/` diagnostic logs; full-archive scans were
  re-run for this stage)
- **[FW]** = firmware RE (stage C: `FIRMWARE-ANALYSIS-C.md`)
- **[EXT]** = external documentation (Infinitude wiki, InfinitESP issues
  #41/#42 and README, infinitive code/README, SAM01-01XA spec as mined in
  `external-research/sam-spec-notes.md`)
- **[INF]** = inference, reasoning shown

The single most important framing fact: **almost everything the outside
world "knows" about thermostat↔SAM interaction happens on Carrier/legacy
controls that register a SAM. This Ion does not.** The two regimes are
specified separately below and never blended.

---

## 1. Interaction inventory

### 1.1 On THIS Ion (ICP SYST0101CW, CESR******-**.79) — the only regime we must reproduce

#### Thermostat → SAM: essentially nothing, ever

| Interaction | Detail | Source |
|---|---|---|
| Steady-state polls to 0x92 | **None.** Across cold start, FULL INSTALLATION, reseat, and 16 min of live SAM presence, the thermostat initiates zero frames to 0x92. Every 20→92 frame in the archive is a func `06` answer to a SAM read. | [CAP] |
| Commissioning probe | The 0x1F SystemInit prober reads `0104` from 0x92 **once** during its sweep (answered: SAM identity). The subsequent 0x20-persona sweep also probes `0104`→92 (×4 in the phase-1 capture, unanswered then; ×1 in the phase-2 capture). This is the only thermostat-initiated SAM traffic ever observed. | [CAP] |
| `3B0E` acknowledgement writes | **Never.** Full-archive scan: zero `3B0E` frames from any source, zero 20→92 func `0C` frames of any register. | [CAP] |
| `3B06` dealer-table push | Never (same scan — no thermostat→SAM writes exist at all). | [CAP] |
| `031C` writes to SAM | Never. | [CAP] |
| `040E` / `030D` supervision reads | Never. The registration gate probes (see §2) do not occur on this control. | [CAP] |
| SYSTIME broadcast | `0202`/`0203` written to broadcast **F1** every ~60 s. Not addressed to the SAM, but a SAM snoops time from it; part of the ambient contract. | [CAP] |

#### SAM → thermostat: reads served, writes ignored

Reads the SAM (InfinitESP) issued and what this Ion served [CAP,
`sam-commissioning` + `sam-control-test` captures]:

| SAM read of 0x20 | Cadence | Served payload |
|---|---|---|
| `3B02` (SAM state, 29 B) | alternating with `3B03`, 129 reads / 16 min (≈3 s combined cycle) | **29 B, all zeros** |
| `3B03` (SAM zones, 150 B) | same loop, 129 reads | **150 B, all zeros** |
| `0104` | a few | Real 120 B identity ("INFINITY NEXT GEN UI", CESR******-**.79, SYST0101CW) |
| `3B04` (vacation) | a few | 11 B, all zeros |
| `3B05` (accessories) | a few | 11 B, all zeros |
| `400A` (comfort profiles) | a few | **35 B of real data** (constant across captures) |
| `4012` (vacation settings) | a few | 7 B, real data |
| `4202` (fault log) | a few | 72 B, real data |

Notes:

- **Not every SAM read is answered:** 129 asked vs 118 answered (`3B02`),
  129 vs 117 (`3B03`) — ≈8 % of polls silently dropped; the SAM simply
  continued its schedule. [CAP]
- The same surface is served to a non-SAM reader: the 2026-11-02
  diagnostic session reading **as 0x93** got zeros for `3B02`/`3B03` and
  real data for `400A` (after one timeout/retry). The zero-content of
  `3B02`/`3B03` is therefore not SAM-specific addressing behaviour; it is
  the content those tables have on this unit, for anyone. [CAP]
- The SAM also reads equipment directly (92→53 `0304`, 24 frames in the
  commissioning capture, answered by the ODU). Not a thermostat
  interaction, but it is part of a real SAM's bus footprint. [CAP]

SAM writes to the thermostat [CAP, control test]:

- `3B03` written 6× (150 B), `3B02` once (29 B), in the InfinitESP dialect:
  body [0] = zone/active-zones, [1..2] = change flags — the captured words
  decode (per infinitive/InfinitESP flag tables) as `0x000C` = heat+cool
  setpoints only, and `0x0010` = mode only [CAP + EXT].
- Thermostat reaction: **none.** No acknowledgement (no func `0D` exists
  anywhere in this bus dialect — writes are never acked, to any device),
  no state change, no follow-up traffic. [CAP]

SAM behaviour during thermostat absence [CAP]: through the 78 s
whole-system power cycle, the SAM kept polling `3B02`/`3B03` every ~3 s —
≈26 unanswered polls, no retry storm, no fault frames — and resumed being
answered when 0x20 returned.

Exception behaviour [CAP]: **no func `0x15` frame exists in any local
capture, in either direction.** Our SAM only ever read served tables, so
the thermostat's exception path toward a SAM was never triggered locally.
Reads of absent devices on this bus are simply never answered (the
furnace's polls to absent 0x45 are the type example).

### 1.2 On controls that register a SAM (Carrier Touch / UID01) — external record, NOT this Ion

Specified here because the emulator checklist (§3) must consciously
*decline* most of it, and because it defines what "registered" means.

**Discovery & the gate** [EXT — Infinitude wiki discovery protocol;
infinitesp issues #41, #42]:

- Discovery sweep: the control (as 0x1F, then 0x20) probes the SAM slot
  with READ `0104` and READ `030D` at 0x92, 3 attempts.
- Inside (re)commissioning, the control reaches a step displayed as
  **"searching for remote access"** and reads **`040E`** and **`3F02`**
  from 0x92. `040E` must be answered with byte-exact real-SAM content;
  if it exceptions (func `0x15`, code `0x04`), the control retries
  **6 times at 2 s intervals**, then reports "nothing found" and the SAM
  is absent from the Equipment Summary. `3F02` exceptions on real SAM
  hardware too and is **not** the gate.

**After registration** [EXT — issue #41 reporter data; wiki SAM page]:

- Equipment Summary shows "Remote Access: Yes".
- The control writes **`031C`** to the SAM during INSTALL and at startup
  (the SAM side needs no special handler; a generic store+acknowledge
  suffices).
- Supervision polling: READ `040E` ≈ every **10 s**, READ `030D` ≈ every
  **23 s**, plus regular `0104`/`030D` read cycles.
- The control **pushes its dealer table `3B06`** to the SAM every poll
  cycle.
- The control writes **`3B0E`** (activity flag `0x01`) to the SAM to
  acknowledge SAM-initiated changes.
- The SAM, conversely, polls the thermostat ≈ every **65 ms**
  (`3005`/`3003`/`3C0C`/`3C0D`/`3C14`/…), notifies changes by writing
  `3B03` to the thermostat, and sync is declared after 10+ successful
  bidirectional exchanges.

**Exception flood** [EXT — Infinitude passive capture, via GitHub sweep]:
the SAM's poll list includes registers the thermostat does not serve
(`3C14`, `3C0D`, `3C0C`, `3005`, `3003`, `3104`, `0104`, `0420`, `0202`);
the thermostat answers each with an exception func `0x15`, code `0x04`,
1:1 — **54,076 exception frames in 10.5 h**, all thermostat→SAM. So on
that generation, exception is the normal answer to an unserved read, and
a SAM generates them continuously by design of its poll list.

**What a SAM setpoint write does on a registering Touch control** [EXT —
SAM01-01XA Touch semantics + InfinitESP's Touch model + infinitive]:

- The ASCII face's contract (HTSP!/CLSP!) is: the zone enters the
  **MANUAL activity** — "hold until" if a duration is given, "hold
  permanent" if not. HOLD!ON = hold permanent on the currently executing
  activity.
- On the bus, InfinitESP's verified Touch model is two-step: a `3B03`
  notification write **with change flags** primes the thermostat, then a
  direct data write delivers the values. Both are required; neither alone
  works.
- Change-flag dialect (identical in infinitive and InfinitESP): `3B03` —
  fan `0x01`, hold `0x02`, heat SP `0x04`, cool SP `0x08`, override
  `0x80`; `3B02` — mode `0x10`, weekday `0x80`, minutes `0x100`,
  displayed zone `0x200`. Setpoints are whole degrees in the thermostat's
  configured units.
- Side effect: writing global parameters via `3B02` **rolls the
  thermostat clock back up to 1 minute per write** (the thermostat
  re-reads its minute-granularity time). infinitive compensates by
  bundling a time/day setting (+30 s) into every such write.
- SAM client timing expectations (infinitive): answer within **500 ms**,
  up to 5 retries — far stricter than the ASCII spec's 5 s budget (which
  governs the serial face, not the bus).

---

## 2. Registration — the final form

**Firmware level** [FW — stage C, instruction-precise]: SAM presence in
the thermostat is one byte, field-store field `0xC4`, written `'Z'`
(0x5A) by exactly one routine (FUN_18147c58, state 0x17 of the SAM/B36
manager state machine, ticked by a 1 s supervisor task). `'Z'` is
written **iff the dword at (SAM device object + 0x38) is non-zero**,
where the object pointer lives in the SAM device record at
0x3C0D3EE4. That dword is Clarinox binding-engine state, established
inside the engine's discovery/binding machinery. Stage C searched
exhaustively: **no application instruction, no field-store field, no
ABCD bus table value, no NVRAM config byte, and no service-menu path
writes it.** The refresh routine only *reads* the binding state; when
unbound it writes `0x00` to field `0xC4` and clears the SAM's
bus-activity bitmap bit (an output, not an input). The state machine
itself is complete and runs on this Ion — what never happens is the
binding becoming bound.

**Product level** [EXT + CAP]: on the ICP Ion variant, the discovery
side never even asks the question. The Ion's installation manual
contains **no "Searching for SAM Module" commissioning step** (the
Carrier Touch manual has exactly that step), never mentions a SAM or
home automation anywhere, and ICP lists no SAM accessory for the Ion —
its remote access is the built-in Wi-Fi. Consistent with this, across
three documented triggers (cold start, FULL INSTALLATION, reseat) the
Ion emitted zero `040E`/`3F02` probes, zero `031C` writes, and zero
steady-state polls to 0x92. A control that *had* the search but rejected
our SAM would still show the probe-and-retry signature (issue #41);
the total absence of 0x92-directed traffic is the signature of a step
that does not exist, not of a step that failed. (Whether the SAM code is
physically absent from the shared CESR131626 binary or brand-gated off
is not provable from outside; from the bus side the behaviour is
identical.) [INF, strongly supported — `SAM-REGISTRATION-RESEARCH.md`]

**The wire difference, registered vs unregistered — precisely:**

- On a control with the feature, registration is a **frame-level
  relationship**, not a data detail: an `040E` probe at INSTALL, `031C`
  writes at INSTALL and startup, `040E`/`030D` supervision polling
  (~10 s / ~23 s), `3B06` dealer pushes every cycle, `3B0E`
  acknowledgements of SAM changes, and `3B02`/`3B03` carrying real zone
  state instead of zeros.
- On this Ion there is **no second state**: the relationship never
  forms, so none of those frames exist in either "state". The complete
  SAM-facing behaviour is the §1.1 read surface plus silently ignored
  writes.
- The one element attributable purely to internal data content is the
  zero-vs-real content of `3B02`/`3B03`: the tables are served (correct
  lengths, correct cadence) but their zone-state payload is zeros
  because the SAM object behind them was never bound [INF: contents are
  served from the unbound SAM-interface object; stage C proves the
  presence flag is binding-derived, captures prove zeros are served
  while `400A`/`4012`/`4202`/`0104` serve real data to the same reader].

---

## 3. Emulator checklist — SAM-facing behaviour of the 0x20 replacement

**Serve (exactly as Ion does):**

1. ✅ The read surface, to any reader, at bus rhythm (answer within
   ~50 ms; Ion's median request→response is 19 ms):
   `0104` — real 120 B identity; `3B02` — 29 B; `3B03` — 150 B;
   `3B04` — 11 B; `3B05` — 11 B; `400A` — real profile data;
   `4012` — real vacation settings; `4202` — fault log. [CAP]
2. ✅ Content policy for `3B02`/`3B03`: **default = Ion-faithful zeros.**
   Proven safe: a real SAM client (InfinitESP) polled them for 16 min
   and through a 78 s thermostat outage without faulting or escalating.
   Serve real zone state (layouts in `infinitive-registers.md`) only if
   a future client demonstrably needs it — it is a deviation, not a
   requirement.
3. ✅ `3B05` to **any** reader: node 0x93 polls it every ~300 s forever,
   SAM or no SAM — 11 zero bytes while no accessories are configured.
   [CAP]

**Accept:**

4. ✅ SAM writes to `3B02`/`3B03`: accept silently. **Never emit an
   acknowledgement frame** — func `0D` does not exist in this dialect;
   Ion never acks any write from anyone. [CAP]
5. ✅ Default write policy = **ignore entirely** (Ion-faithful).
6. ⚠️ OPTIONAL control acceptance — a deliberate, documented deviation
   from Ion, only if SAM control is ever wanted: parse the change-flag
   dialect (§1.2), apply the two-step prime-then-data model, land
   setpoint changes as **MANUAL activity + hold** (hold-until with a
   duration, hold-permanent without), and after accepting a change,
   write `3B0E` (activity flag `0x01`) to the SAM as registering
   controls do [EXT]. Budget the side effect: each `3B02` global write
   may roll the emulator's clock back ≤1 min — re-sync time after
   global writes (infinitive's +30 s bundling is the reference
   workaround). [EXT]

**Never do:**

7. ❌ **Do not poll the SAM.** No `040E`/`030D` supervision, no `0104`
   SAM polls in steady state. Ion initiates nothing to 0x92; the
   emulator's silence toward an absent SAM must be total and
   indefinite. [CAP]
8. ❌ Do not write `031C`, `3B06`, or `3B0E` to a SAM (outside the
   optional item 6). Ion never does; a SAM does not need them to
   function against this thermostat. [CAP]
9. ❌ Do not add a SAM search to commissioning. Run the standard 0x1F
   sweep — which includes single `0104` probes to 0x92/0x94 — and let
   silence be silence. The equipment ritual is unchanged by SAM
   presence or absence. [CAP]
10. ❌ Exception policy — choose silence: reads of unserved registers
    get **no answer**, matching every locally observed behaviour on
    this dialect (absent devices are simply never answered). The
    `0x15`/`0x04` exception style is attested on another generation
    [EXT]; adopting it is defensible but is *not* what this Ion was
    ever observed doing, and inventing other exception codes is not
    acceptable either way.
11. ✅ Keep broadcasting SYSTIME `0202`/`0203` to **F1** every ~60 s —
    a SAM takes time from the broadcast; never address it to 0x92.
    [CAP]

**Absence requirement (explicit):** with no SAM on the bus, items 1–11
reduce to: serve `3B05` to 0x93, broadcast time, and nothing else. No
timeouts, no retries, no fault state may be keyed to SAM presence.

---

## 4. Reverse checklist — our current node (InfinitESP at 0x92) vs a real SAM01

| # | Behaviour | Real SAM01 / spec | Our node | Can Ion tell? |
|---|---|---|---|---|
| 1 | ASCII `ACK` semantics | Spec: `ACK` = command accepted (applied) | `sam_ascii` ACKs writes that the thermostat silently discards (unregistered SAM) — the ACK is transport-level, not adoption | No — ACK lives on the serial/TCP face, never on the bus [CAP] |
| 2 | Diagnostic verbs `SCAN?` / `REG?` / `REG!` | **Do not exist** in SAM01-01XA; a real SAM01 has no such commands | Present on the TCP-23 console; `REG!` performs raw register writes, gated by `sam_ascii raw_writes: true`, bypassing all spec clamp/deadband/hold semantics — test-bench only, by design | Only via their bus footprint (next row) |
| 3 | Bus footprint of diagnostics | — | `REG?` reads are emitted **from source 0x93** ("SENT 20 3B02 AS 93" in the 2026-11-02 logs), i.e. diagnostics impersonate the 0x93 node, not the SAM | Ion served 0x93 the same surface (zeros for `3B02`/`3B03`, real `400A`) and reacted in no way [CAP] |
| 4 | Poll cadence & list | Real SAM polls the thermostat ≈ every 65 ms across a wide table list incl. unserved registers (which draw `0x15`/`0x04` exceptions on registering controls) [EXT] | Polls `3B02`/`3B03` on a ~3 s alternating cycle, served tables only — which is exactly why no exception was ever triggered locally | No behavioural difference Ion-side; an outside observer could tell [CAP + EXT] |
| 5 | Discovery holdoff | Real SAM polls continuously | InfinitESP suppresses its *initiated* transmissions for 180 s after any 0x1F frame (protects the sweep; reactive handling stays live) | No — Ion initiates nothing and reacts to nothing from 0x92 [CAP] |
| 6 | Identity served (`0104`) | Real SAM01 reports its own model/serial | Seeded "SYSTEM ACCESS MODULE / InfinitESP--SAM", software = build date | No — Ion read it during the sweep and proceeded identically [CAP] |
| 7 | `040E` / `0420` content | Byte-exact real-SAM captures are what Carrier controls gate on | Seeded byte-exact (the issue-#41 fix) — but Ion never reads either register; dead weight here, decisive elsewhere | No [CAP] |
| 8 | Setpoint-write dialect | A real SAM01's exact `3B02`/`3B03` write frames have **never been captured anywhere** (protocol-map Gap G6) | InfinitESP dialect: change flags `0x000C` (heat+cool SP) / `0x0010` (mode), prime-then-data model | Unknowable — no reference exists to differ from [EXT] |
| 9 | Writes received from thermostat (`3B06`, `3B0E`, `031C`) | Real SAM stores them and acknowledges with a RESPONSE `{0x00}` [EXT — infinitive writeAck model] | Generic store + same acknowledgement model | Untestable here — Ion sends none [CAP] |
| 10 | Exception behaviour as a *server* | Real SAM exceptions unknown-register reads with func `0x15` code `0x04`; table `3F` rejected wholesale [EXT — InfinitESP source, hardware-derived] | Identical (implemented from the same hardware observations) | n/a (SAM-side behaviour) |
| 11 | `030D` content | Real SAM status semantics | Seeded all-zeros deliberately (a 61/62/63 seed caused false "SAM RADIO TEST FAILED" on UID01) | No [EXT] |

**Verdict:** from the bus side, on this Ion, our node is
indistinguishable from a real SAM in every way that has an observable
consequence — because Ion initiates nothing to 0x92, reacts to nothing
from 0x92, and serves the same surface to 0x92 and 0x93 alike. Every
deviation lives on the serial/ASCII face (items 1–2) or in observer-
visible timing (items 4–5), none of which Ion acts on. The one
certifiably non-spec surface is the diagnostic console (`SCAN?`/`REG?`/
`REG!`) — it exists only in InfinitESP, is gated for writes, and its
bus footprint borrows the 0x93 identity rather than the SAM's.

---

## 5. Open items (explicit)

- **G6 (unchanged):** a real SAM01's `3B02`/`3B03` write dialect is
  unobserved anywhere; if the emulator ever implements §3 item 6, the
  InfinitESP dialect is the only reference.
- Whether a *registered* SAM on a Carrier Touch running this exact
  firmware (CESR******-**.79) sees real `3B02`/`3B03` contents rests on
  the compatibility-matrix report ("responds to SAM and SAM emulation")
  [EXT], not on a local capture — impossible on this Ion by §2.
- The thermostat's exception response to a SAM reading an unserved
  register **on this Ion** is unobserved (never triggered); §3 item 10
  resolves it by policy (silence), not by evidence.
