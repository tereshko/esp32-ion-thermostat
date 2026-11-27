# Why the Ion SYST0101CW never registers the emulated SAM — research

Date: 2026-10-29. Scope: primary sources only (local InfinitESP source, Infinitude wiki,
GitHub issues/discussions of nebulous/infinitesp + nebulous/infinitude, Carrier and ICP
installation manuals, ICP product data). No one was contacted; nothing was posted.

**System under test:** ICP Ion System Control SYST0101CW, firmware 131626-04.79
(CESR******-**.79), InfinitESP build 2026.10.19, `sam_address: 0x92`.
Established local facts (from the parent session's captures, not re-derived here):
three registration attempts failed (full power cycle; service-menu FULL INSTALLATION;
thermostat-only reseat). In every capture the control **never** read SAM registers
040E/3F02, **never** wrote SAM register 031C, and in steady state **never polls 0x92**.

---

## TL;DR

The single best-supported explanation is documentary, not protocol-level: **the ICP Ion
variant of this control has no SAM support at all.** Carrier's Infinity Touch
installation instructions contain a dedicated commissioning step "Searching for SAM
Module (If Applicable)"; the ICP Ion SYST0101CW installation manual — the same platform,
adapted document — has **no such step and never mentions SAM, "System Access Module", or
home automation anywhere in the document**. In the Ion ecosystem "remote access" is
exclusively the control's own built-in Wi-Fi (IonComfort.com); ICP's product data lists
no SAM accessory. The Ion therefore never *starts* the SAM discovery sequence, which is
exactly what the bus captures show: the failure is upstream of everything InfinitESP
serves — no register content change on the SAM side can fix a search that never runs.

This is an inference from documentation + capture evidence (see §B, reason #1), not a
statement from ICP/Carrier engineering. It is, however, the only hypothesis consistent
with *all* observations, including the negative ones (no 040E probe, no 031C write, no
steady-state 0x92 polling, no SAM line in Equipment Summary).

---

## (a) The registration sequence on controls where it works

Provenance tags: **[code]** = InfinitESP source in the local clone
(`~/workspace/diy-thermostat/infinitesp/components/infinitesp/`);
**[issue #41]** = nebulous/infinitesp issue #41 (UID01, SW16) incl. maintainer and
reporter follow-ups; **[issue #40]** = issue #40 (Touch ITN01-A);
**[wiki-discovery]** = Infinitude wiki `System-Setup-Discovery-Protocol.md`;
**[wiki-known]** = wiki `Infinity---known-devices.md`;
**[wiki-sam]** = wiki `SAM-ASCII-Protocol.md` (sourced from Carrier Application
Specification SAM01-04XA, 09/21); **[manual-C]** = Carrier Infinity Touch Installation
Instructions (SYSTXCCITW01-A / ITN01-A / ITC01-A); **[matrix]** = Infinitude
Compatibility Matrix.

### Step 0 — the SAM must be fully served before commissioning

InfinitESP seeds these SAM (0x92) tables at boot so reads succeed with real-SAM-shaped
data — `infinitesp.cpp`, `initialize_defaults_()` **[code]**:

| Register | Meaning | Seeded content |
|---|---|---|
| 0104 | device info (120 B block) | "SYSTEM ACCESS MODULE", software = build `__DATE__`, model "InfinitESP--SAM", serial "1726ESP32SAM01" |
| 030D | SAM status (7 B) | all zeros (a 61/62/63 seed caused false "SAM RADIO TEST FAILED" events on UID01; fixed in commit b8ea9a0) |
| 040E | SAM interface part number (17 B) | byte-exact from a physical SAM: `P3534315\0…\0x02` (captured 2026-06-26, re-verified 2026-09-28) |
| 0420 | SAM interface config (20 B) | byte-exact from the same physical SAM scan |
| 3B02 / 3B03 / 3B05 / 3B06 | SAM state / zones / accessories / dealer | state + zones seeded; accessories zero; dealer seeded from config |
| 3B04 | — | deliberately **not** seeded; real thermostats never read it from a SAM |

Unseeded/unknown register reads return a bus exception (function 0x15, code 0x04);
register **table 3F is rejected wholesale by real hardware** the same way, so exception
behavior matches a real SAM **[code, infinitesp.h comments]**. Writes to the SAM are
stored generically (only 0104 is write-protected) and ACKed by echoing the payload
**[code, `on_write_frame_`/store path]**. There is **no SAM-specific 031C register in
the code**: 031C is `REG_NIM_CONFIG`, a NIM (0x80) table; a 031C write addressed to the
SAM is handled by the generic SAM store+ACK path, i.e. InfinitESP accepts it silently,
which is all a real SAM needs to do **[code]**.

### Step 1 — recommissioning is mandatory

"Recommissioning is required when emulating a SAM or zone controller… Run it from the
thermostat's advanced setup menu. **Until commissioning completes, the thermostat
ignores the emulated device.**" — InfinitESP README **[code/README]**. On Carrier Touch
controls this is the FULL INSTALLATION flow in the service menu **[manual-C, §6.2]**.

### Step 2 — discovery sweep (control acts as 0x1F, "SystemInit")

During System Setup the thermostat changes its source address 0x20 → **0x1F** and runs
an ordered multi-phase discovery **[wiki-discovery]**:

- **Phase 1:** broadcast WRITE triplets (0305 / 3E02 / 0605) every ~1.3 s; probe of
  address 0x42.
- **Phase 2** (control back at 0x20): scans ODU slots, probes NIM 0x80 (register 3405),
  zone controllers 0x60/0x61 (3405), secondary thermostats 0x21–0x28 (041E).
- **SAM probe (per the wiki's probe table): READ 0104 and READ 030D at 0x92, 3
  attempts, "continuous".** Devices answering here (IDU, ODU2, SAM) are treated as
  "already known from pre-setup steady-state polling and are not re-discovered"
  **[wiki-discovery]** — i.e. on Carrier controls a SAM that answers the ordinary
  0104/030D polls is carried into setup.
- **Phase 3:** configuration screens, T+45–250 s.
- Note: register 031C appears in this trace only in **Phase 4/5, written to the indoor
  and outdoor units** as a setup-complete marker — not to the SAM **[wiki-discovery]**.
  (The 031C-to-SAM write is attested separately, at startup/INSTALL, in issue #41 —
  see Step 3.)

While 0x1F frames are on the bus, InfinitESP deliberately **holds off its own
initiated transmissions for 180 s** after the last 0x1F frame (discovery holdoff,
`DISCOVERY_HOLDOFF_MS`), so it cannot corrupt the sweep; its *reactive* read/write
handling is not gated, so it stays discoverable **[code]**.

### Step 3 — the "searching for remote access" probe (the decisive gate)

On the UID01-generation control (issue #41, SW16), during INSTALL the control reaches a
step shown on screen as **"searching for remote access"** and **[issue #41]**:

1. READ **040E** from 0x92, and READ **3F02** from 0x92.
2. Before the fix, InfinitESP exceptioned both (0x15/0x04) → control retried **6 times
   at 2 s intervals** → displayed "nothing found" → **SAM absent from Equipment
   Summary** — even though ordinary SAM polling to 0x20 worked the whole time.
3. Maintainer's diagnosis (nebulous, in #41): "UID01-generation thermostats probe 040E
   during INSTALL… and **refuse to register a SAM that excepts it**" **[code comment,
   infinitesp.h]**.
4. Fix: serve **040E and 0420 byte-exact** as captured from a physical SAM02
   (commit 47747b5). A real SAM also exceptions 3F02 — that part is normal and not the
   gate **[issue #41]**.
5. Result (reporter, on 2026.9.9): "**it works now**", SAM registered, Equipment
   Summary shows **"Remote Access: Yes"**. The control writes **031C to the SAM during
   INSTALL and at startup** (startup exchange: one 3F02 read that exceptions, plus 031C
   writes, all ACKed) **[issue #41]**. The same gate is independently documented for a
   second legacy control in **issue #42** (SYSTXCCUID01-B, fw 18): INSTALL search reads
   SAM 040E/3F02, NAK → SAM never listed; seeding 040E fixes commissioning. On every
   control that *has* the search, the search is visible on the bus.

On Carrier Touch controls the same step exists as a named commissioning phase:
**"Searching for SAM Module (If Applicable)"** — "to determine if a System Access
Module, used for home automation only, is connected to the system", referencing the
"Carrier Communicating HVAC System" application specification (v2+) and the SAM
Installation Instructions **[manual-C, Commissioning]**. Carrier's SAM01 literature
states compatibility: "Legacy UID/UIZ controls — SW v14+; **Infinity Touch controls —
SW v08+**", with the caveat that the SAM "is designed for legacy UID/UIZ wall controls;
with Infinity Touch systems some commands return NAK or behave differently"
**[wiki-sam]**. The matrix confirms a Carrier **SYSTXCCITC01-B on CESR******-**.79**
(the same firmware version as this Ion) "responds to SAM and SAM emulation" (reporter
feisley) **[matrix]**.

### Step 4 — steady state after registration

On a working install the control continuously supervises the SAM **[issue #41]**:

- READ **040E** ≈ every **10 s**; READ **030D** ≈ every **23 s** (reporter's
  post-registration numbers).
- Regular READ **0104** (typically ×3) and READ **030D** (×3) cycles **[wiki-discovery,
  wiki-sam]**.
- The control pushes its dealer table **3B06** to the SAM every poll cycle
  **[wiki entity-reference / code comment]** and writes **3B0E** (activity flag 0x01)
  to acknowledge SAM-initiated changes **[wiki-sam]**.
- 031C is written to the SAM at **startup** and at **INSTALL** **[issue #41]**.
- The (real) SAM conversely polls the thermostat ~every 65 ms (3005/3003/3C0C/3C0D/
  3C14…) and notifies changes by writing **3B03** to the thermostat; sync is declared
  after 10+ successful bidirectional exchanges **[wiki-sam, wiki-known]**.

**Summary of the gate:** registration = (recommission) + (SAM answers 0104/030D) +
(the control's remote-access search reads 040E successfully) → control records
"Remote Access: Yes", starts 040E/030D supervision polling, and writes 031C at
startup/INSTALL. Every element after the arrow is control-initiated. If the control
never runs the search, none of the rest can happen.

---

## (b) Why the Ion never starts it — ranked hypotheses

### #1 — The ICP Ion firmware variant has SAM support removed/not present. **(Best supported; documentary + capture evidence)**

Evidence:

- The **Ion SYST0101CW Installation Manual** (ICP doc 616 01 1600 01, 06/19 — the
  Ion-adapted edition of the same manual family as Carrier's SYSTXCCITC instructions)
  lists its Commissioning sequence as: 5.1 Searching for Indoor Unit, 5.2 Searching
  for Outdoor Unit, 5.3 Indoor Evaporator Selection, 5.4 Electric Heater Selection,
  5.4.1 Hydronic Heat, **5.5 Searching for Zones**, 5.6 Filter Type, 5.7 Humidifier,
  5.8 UV Lights, 5.9 Equipment Summary… **There is no "Searching for SAM Module" step.**
  The Carrier Touch manual's Commissioning TOC has that step in exactly the slot
  between Hydronic Heat and Searching for Zones **[manual-C vs Ion manual]**.
- Full-text check of the Ion manual: **zero** occurrences of "System Access", "home
  automation", or SAM-as-a-module (the only "SAM" strings are OCR fragments of
  "same"). Every "remote access" mention in the Ion manual refers to the control's own
  Wi-Fi connection and registration at IonComfort.com **[Ion manual]**.
- ICP product data for SYST0101CW describes remote access solely as the built-in Wi-Fi
  feature, and the Ion ecosystem accessory list (product specification) contains **no
  System Access Module**: controls are SYST0101CW and the SYST0101RM remote-access
  module; zoning via SYST0101ZP etc. SAM is a Carrier/Bryant-branded accessory
  (SYSTXCCSAM01) **[ICP product spec / product data]**.
- Consistent with the local captures: across a cold start, a FULL INSTALLATION, and a
  thermostat reseat, the Ion performed its documented learn sequence (indoor, outdoor,
  coil ID — the steps its manual *does* list) and the Equipment Summary matched the
  system with no SAM line; it never probed 040E/3F02, never wrote 031C, and never polls
  0x92 in steady state. A control that *had* the search but rejected our SAM would
  still have shown the probe-and-retry signature seen in issue #41 (6× 040E reads).
  **The total absence of any 0x92-directed traffic is the signature of a step that
  does not exist, not of a step that failed.** [established facts + inference]
- Consistent with upstream silence: exhaustive GitHub search of nebulous/infinitesp
  and nebulous/infinitude (issues + discussions, plus the issue-index search API) for
  SYST0101 / Ion / ICP / Tempstar / Heil / "remote access" / "SAM not registered"
  returns **zero** ICP-Ion SAM reports — nobody has a working (or even attempted-and-
  debugged) Ion SAM registration on record, while Carrier Touch on the identical
  firmware version string is a confirmed "responds to SAM and SAM emulation" entry
  **[matrix; GitHub search 2026-10-29]**. The single "ION" hit anywhere
  (infinitude #168, "Not working with ION Home Comfort", 2023) concerns the control's
  Wi-Fi cloud-proxy path, not SAM/bus emulation. The Ion is simply off the SAM map.

What this does *not* prove: that the SAM code is physically absent from the 131626
binary rather than disabled by brand/product configuration. The firmware version
string is shared with Carrier (CESR******-**.79), so a brand-gated feature flag is
plausible. Either way, from the bus side the behavior is identical and not fixable from
the SAM side. **[inference]**

### #2 — The Ion is a Wi-Fi control, and Carrier's own SAM is documented as incompatible with Wi-Fi Touch controls. **(Supported for the physical SAM; partially transferable)**

- Infinitude's own SAM-emulation documentation warns: "**WiFi-enabled Touch controls
  (SYSTXCCITW01) impose additional restrictions: a physical SAM cannot be used with
  them**, and InfinitESP must be the only SAM-protocol participant on the bus"
  **[wiki-sam / infinitude SAM docs]**. The Ion SYST0101CW is exactly that class of
  device: a Wi-Fi Touch-generation control whose remote-access role is already filled
  internally — the same product slot a SAM would occupy.
- Caveat: that restriction is documented for the Carrier ITW01 + *physical* SAM
  combination, and the matrix shows a (non-Wi-Fi-named) ITC01-B working with SAM
  *emulation* on this firmware. So #2 explains why Carrier/ICP would design SAM out of
  Wi-Fi controls, but as a standalone mechanism it is weaker than #1's direct
  documentary evidence for the Ion specifically. **[proven for ITW01+physical SAM;
  inference for Ion]**

### #3 — The discovery sweep never actually ran in the attempts (wrong trigger). **(Largely refuted by the captures, kept for completeness)**

- On Carrier controls the SAM search runs inside the (re)commissioning flow; the author ran
  FULL INSTALLATION from the service menu (Ion manual §6.2: "perform the start-up
  process in order to learn all equipment in system") plus a full power cycle plus a
  reseat — the documented triggers — and the control demonstrably *did* re-learn the
  indoor unit, outdoor unit and coil in those runs. The learn sequence ran; it simply
  contains no SAM step on this control (see #1). For the reseat attempt specifically,
  the capture file came back empty (capture fault), so that one attempt is
  individually unverifiable — but it adds nothing the other two didn't already show.
  **[established facts]**

### #4 — SAM-side serving deficiency (wrong/missing register content). **(Refuted as the primary cause)**

- The #41 failure mode is precisely this, and it looks different: the control *probes*
  040E, gets exceptions, retries 6×, then gives up. Here there are **no probes at
  all** to fail. The build in use (2026.10.19) already contains the #41 fix
  (byte-exact 040E/0420, zeroed 030D), and the SAM demonstrably answers the control's
  traffic on the bus (its 0104 identity was read during the 0x1F sweep in the
  commissioning capture; the control answers SAM-initiated reads). A content problem
  cannot produce a *missing question*. **[code + established facts]**
- One genuine SAM-side nuance worth recording: InfinitESP's discovery holdoff
  suppresses its *initiated* polls for 180 s after any 0x1F frame **[code]**. On
  Carrier controls that's harmless (registration is control-driven). It does not
  explain the Ion, whose steady state contains no 0x1F and no 0x92 traffic at all.

### #5 — Address or bus-topology issue (0x92 filtered/not reached). **(Refuted)**

The SAM was *seen* by the control during commissioning (its 0104 was requested in the
0x1F sweep and answered with "SYSTEM ACCESS MODULE / InfinitESP--SAM"), and two-way
table traffic with 0x20 exists in the captures. The path works; the control chooses
not to use it outside that one identity read. **[established facts]**

---

## (c) The single most promising next step

**File one upstream issue in nebulous/infinitesp** documenting the Ion as (apparently)
the first tested ICP-branded Touch control, with the captures attached. Rationale:
every SAM-side avenue is exhausted and evidence-backed (the serving stack is byte-exact
and proven on UID01 and Carrier Touch); the open question — *is SAM discovery
brand-gated out of the ICP build of 131626, or is there an undiscovered trigger?* — is
exactly the kind the maintainer (nebulous) and the #41/#40 reporter pool can answer,
and the compatibility matrix currently has **no ICP entry at all**, so this data is
net-new to the project. Do not buy hardware, do not change register content, and do not
keep re-running FULL INSTALLATION: three attempts already establish the negative.

Attach/include in the issue:

1. **Control identity:** ICP Ion SYST0101CW, firmware CESR******-**.79; system: Heil
   G80CTL1352422A furnace (0x44 in captures), HVA960GKA outdoor unit (0x53), no zoning.
2. **The three captures** (JSONL from `traces/`):
   - `coldstart-20261029-125733.jsonl` — clean cold start; Ion's 0x1F sweep *does*
     request 0x92's 0104 and gets "SYSTEM ACCESS MODULE / InfinitESP--SAM"; no 040E,
     no 031C, no steady-state 0x92 polling afterwards.
   - `sam-commissioning-20261029-143248.jsonl` — phase-2 firmware live, full equipment
     ID wizard completed (coil EN(A,D)4X61 confirmed), Equipment Summary correct but
     no SAM / no "Remote Access" line; two-way 0x92 traffic present (302 frames from
     SAM, 276 to it) yet zero 040E/3F02 reads and zero 031C writes.
   - `sam-control-test-20261029-145357.jsonl` — SAM-initiated setpoint writes reach
     the control and its 3B02/3B03 replies are all-zero tables; control never reacts.
   - (`full-install-20261029-150209.jsonl` optional — the decisive window fell
     outside that capture; say so honestly rather than presenting it as evidence.)
3. **The negative checklist**, stated plainly: in N minutes across cold start + FULL
   INSTALLATION: 040E reads to 0x92 = 0; 3F02 reads = 0; 031C writes to 0x92 = 0;
   steady-state polls to 0x92 = 0.
4. **The documentary contrast:** Carrier SYSTXCCITC Installation Instructions include
   commissioning step "Searching for SAM Module (If Applicable)"; the ICP SYST0101CW
   Installation Manual (616 01 1600 01) has no such step and no SAM mention at all;
   ICP product data lists no SAM accessory for Ion. Ask explicitly: *has anyone ever
   seen an ICP/Ion (or Tempstar/Heil-branded) Touch control emit the 040E probe? Is
   SAM discovery known to be brand-gated in the 131626 builds?*
5. **Config/firmware identity of the SAM side:** InfinitESP 2026.10.19 (includes the
   #41 byte-exact 040E/0420 fix), `sam_address: 0x92`, ESP32 + auto-direction RS485
   module; note phase-1 passive monitoring on the same wiring works perfectly (so
   this is not a "device not seen on bus" report like #40).

Expected outcomes, in order of value: (i) maintainer/community confirms Ion/ICP builds
lack SAM discovery → phase 2 closes as *impossible on this control*, and the project
falls back to its documented resting state (phase-1 monitoring now, full 0x20
thermostat emulation as the long-term path — for which the trace archive is already
being collected); (ii) someone names a trigger or menu path not in the Ion manual →
one targeted test; (iii) silence → the documentary conclusion stands as the working
answer.

---

## Proven facts vs inference — index

**Proven (primary source in hand):**
- InfinitESP serves 0104/030D/040E/0420/3B02/3B03/3B05/3B06 with the contents in §(a);
  040E/0420 are byte-exact physical-SAM captures; 031C has no SAM-specific handler and
  is ACKed via the generic store path; unknown reads exception 0x15/0x04; discovery
  holdoff = 180 s after last 0x1F frame. [local source]
- UID01 registration gate = 040E read at the "searching for remote access" INSTALL
  step; fix and successful registration ("Remote Access: Yes", 031C writes at
  INSTALL/startup, 040E ≈10 s / 030D ≈23 s supervision) documented in issue #41.
- Carrier Touch manual contains the "Searching for SAM Module (If Applicable)"
  commissioning step; the ICP Ion SYST0101CW manual does not, and contains no SAM
  reference at all; Ion remote access = built-in Wi-Fi only (manual + product data).
- Carrier SAM01 literature: Touch controls supported at SW v08+, SAM designed for
  legacy UID/UIZ; matrix entry SYSTXCCITC01-B @ CESR******-**.79 "responds to SAM and
  SAM emulation"; infinitude docs warn a physical SAM cannot be used with Wi-Fi Touch
  controls (ITW01).
- No ICP/Ion/Tempstar/Heil SAM report exists in nebulous/infinitesp or
  nebulous/infinitude issues/discussions as of 2026-10-29 (search: SYST0101, Ion, ICP,
  Tempstar, Heil, "remote access", "SAM not registered" — all zero relevant hits).

**Inference (labeled as such):**
- That the Ion's missing manual step reflects missing/disabled SAM discovery in its
  firmware build (vs. an undocumented trigger) — strongly supported by the total
  absence of 0x92-directed traffic across three documented triggers, but not confirmed
  by ICP/Carrier or by upstream.
- That the shared firmware version string (131626-04.79) implies a brand-level
  feature gate rather than wholly separate codebases.

**Known tension in sources (recorded, unresolved):** the wiki SAM page's 2026-03-30
testing notes say "0420 was never observed; likely a thermostat register, not SAM",
while InfinitESP seeds 0420 at the SAM from a physical-SAM scan and issue #41's fix
(040E+0420) produced a registration. The 0420-as-SAM-table claim rests on the
maintainer's hardware scan; the wiki note rests on one comparator session. Immaterial
here: the Ion never reads either register.

## Sources

- Local: `~/workspace/diy-thermostat/infinitesp/components/infinitesp/infinitesp.h`,
  `infinitesp.cpp`, `climate.cpp`, `docs/bus-capture.md`, `docs/entity-reference.md`,
  `README.md`; captures in `~/workspace/diy-thermostat/traces/` (+ INDEX.md).
- Infinitude wiki (github.com/nebulous/infinitude.wiki): `SAM-ASCII-Protocol.md`,
  `System-Setup-Discovery-Protocol.md`, `Infinity---known-devices.md`,
  `Infinitude-Compatibility-Matrix.md`, `Infinity-Protocol-Main.md`.
- GitHub: nebulous/infinitesp issues #41, #42, #40; nebulous/infinitude issue #168
  (Wi-Fi proxy path only); issue/discussion searches listed above.
- Carrier: Infinity Touch Control Installation Instructions (SYSTXCCITW01-A /
  SYSTXCCITN01-A / SYSTXCCITC01-A), Commissioning — "Searching for SAM Module
  (If Applicable)".
- ICP: Ion System Control SYST0101CW Installation Manual, 616 01 1600 01 (06/19),
  §5 Commissioning, §6.2 Installation; SYST0101CW Product Specifications / Product
  Data (remote access via built-in Wi-Fi; no SAM accessory listed).
