# GitLab + Web Sweep — Carrier/Bryant/ICP Infinity/Ion, ABCD bus

Date: 2026-11-26. Scope: GitLab + wider web (GitHub covered by a sibling agent; GitHub-hosted
items appear below only where a web search surfaced them and they carry unique documentation —
flagged as cross-references). Purpose: prior art for firmware RE of the Ion SYST0101CW
(BINF0479, Renesas SH-2A) and for a future 0x20 thermostat emulator.

## TL;DR — ranked useful finds

1. **Official "SAM Remote Access Application Specification" (ASCII Protocol Information) is
   publicly mirrored** — the dealer-gated Carrier document describing the SAM RS-232 ASCII
   interface end-to-end (message definitions, status + configuration commands, response
   timeout, abnormal conditions). Mirror: silo.tips (see §2.1). Canonical dealer URL:
   `dms.hvacpartners.com/docs/1009/Public/02/SAM01-01XA.pdf`.
2. **Infinitude CarBus documentation (AGENTS.md in active forks)** — densest public register
   semantics for the ABCD bus, including **four different temperature encodings** used on the
   wire (§2.2). Directly applicable to our emulator and to validating stage D/E findings.
3. **US Patent 7,243,004 "Self-configuring controls for HVAC systems"** (Carrier, expired
   2024-11-21) — the patent frame for exactly the mechanism stage D found in firmware:
   units report their characteristics, the central control selects parameters/strategies for
   the combination (§4.1).
4. **Cocoontech "Carrier Infinity" mega-thread** — the original RE community (3tones/brybus,
   nebulous). Page 14 independently confirms two of our own observations: the thermostat
   interrogates newcomer devices from address **0x1F**, and frames can end with abort
   trailers **00FC–00FF**; also a fully identified heat-pump defrost sequence (§5.1).
5. **Official firmware distribution channel for BINF images** (EULA page + Ion release
   notes) — legal source of *other* firmware versions for cross-version algorithm diffing
   (§2.3). No leaked/third-party dump collections found anywhere.
6. **FCC filing 2AK6N-CCITC01B** — Carrier Infinity System Control (UTEC, Huntington IN):
   hardware identity/photos for the Carrier sibling of our ICP control (§3).

---

## 1. GitLab — NEGATIVE

Public project search via `gitlab.com/api/v4/projects?search=` for: `infinity`,
`carrier+infinity`, `infinitude`, `thermostat`, `hvac`, `systxcc`.

- **No relevant projects.** Results were unrelated noise/spam; `infinitude` matched only an
  unrelated French blog repo (nlune/tutorials).
- Public **snippets** search: API returned **401** (snippets search not usable anonymously) —
  inconclusive for snippets specifically, but combined with the project results and zero web
  references to GitLab-hosted Infinity work, GitLab is effectively empty for this topic.
- All known open-source work on this bus lives on GitHub (sibling agent's sweep).

## 2. Official / dealer documentation

### 2.1 SAM Remote Access Application Specification — FOUND, public mirror

- **What:** Carrier's official application specification for the System Access Module (SAM)
  home-automation interface: "SAM Remote Access — Application Specification — ASCII Protocol
  Information". Table of contents (from the mirrored PDF): Safety; Introduction (Infinity
  remote access & home automation interface); Home Automation ASCII Port (RS-232) — overview,
  input/output, RS-232 connector hardware configuration, **Process (Algorithm)**, general
  message formatting, connect auxiliary sensor, **abnormal conditions and responses**,
  **response timeout**; **ASCII Protocol Definition (pp. 4–13)** — message definitions,
  message examples, **ASCII Status Commands (p. 5)**, **ASCII Configuration Commands (p. 9)**.
- **Technical value:** This is the vendor's own description of the SAM-side protocol our node
  already speaks on TCP 23 (sam_ascii). It defines the *intended* semantics of the ASCII
  command set (vs. our reverse-engineered subset), incl. timeout/abnormal-condition behaviour
  — useful for hardening the emulator's SAM personality and for cross-checking which ASCII
  verbs map to which bus operations. Note it specifies the RS-232 side (9600 baud ASCII);
  the ABCD side stays proprietary binary.
- **URLs:**
  - Public mirror (full PDF): https://silo.tips/download/application-specification-ascii-protocol-information
    (search index crawled it ~2026-11-20; on 2026-11-26 the site showed "under maintenance"
    and a direct fetch of the dealer URL failed — content above is from indexed excerpts,
    re-download when the mirror is back.)
  - Canonical dealer copy (HVACpartners DMS, cited verbatim by Hubitat/HomeSeer posts):
    https://dms.hvacpartners.com/docs/1009/Public/02/SAM01-01XA.pdf
  - The spec is referenced by name in current Product Data (e.g. SYSTXCCITC-07PD §"Home
    Automation System Interface": "Reference the latest version of the Application
    Specification titled 'SAM Remote Access Application Specification,' available on
    HVACpartners.com"): https://www.shareddocs.com/hvac/docs/1009/Public/04/SYSTXCCITC-07PD.pdf

### 2.2 Infinitude CarBus register documentation (cross-reference — GitHub-hosted)

- **What:** `AGENTS.md` in active Infinitude forks (joechiarella, NateCCIE) documents the
  CarBus layer: SAM emulation (`EMULATE_SAM`), `lib/CarBus/SAM.pm` register definitions,
  `docs/SAM-ASCII-Protocol.md` (RS-232 ASCII at 9600 baud; ABCD side 38400 baud).
- **Technical value — four temperature encodings on the bus** (the single most useful
  protocol fact from this sweep; matches and extends our own map):
  1. Registers **3B02** (room temp / outdoor air temp), °F mode: raw byte = whole °F.
  2. Setpoints **400A / 3B0A**, °C mode: **half-degree °C** units.
  3. Active setpoints **3B03 / 3B04**, °C mode: whole °C.
  4. Zone-controller sensor **0302**, ODU **0302**, IDU **0306**: always **uint16 BE in
     1/16 °F**.
  Also: register semantics for SAM emulation and the caveat (NateCCIE README) that if SAM
  emulation stops, "the thermostat continues operating with a communication error" — a
  field report relevant to our comm-fault timeout question (G1), though not a number.
- **URLs:**
  - https://github.com/nebulous/infinitude/blob/HEAD/AGENTS.md
  - https://github.com/NateCCIE/infinitude

### 2.3 Official firmware channel (BINF*) — no leaks, but a legal multi-version source

- **What:** ICP distributes Ion control firmware publicly behind an EULA page:
  `cacbdpapps.net/marketing/eula/ICP_Ion_V0479_EULA.html` (for our exact v4.79 image);
  release notes: https://preprod.ioncomfort.com/Content/docs/v0479-20251112.pdf
  (v4.79, dated 2025-11-12); downloads also via `dev.ioncomfort.com/Ion/Downloads`.
  Carrier-side updates are via USB / HVACpartners / MyInfinityTouch per Product Data.
- **Technical value:** Older/newer BINF versions from the same official channel enable
  **cross-version diffing** of the algorithm constants found in stages D/E (staging
  thresholds, CFM strategy) — hvactechgroup users report airflow/CFM strategy changed
  between versions (fault code 126 appeared after the 4.05 update; rollback to 3.61 cleared
  it), i.e. control parameters demonstrably live in the thermostat firmware and change
  between releases.
- **Negative:** no firmware dump collections, no leaked BINF archives, no third-party
  mirrors found on GitLab, forums, or the open web. The version string **CESR131626**
  (e.g. CESR******-**.79) appears only in version-reporting contexts.

### 2.4 Other official literature (public)

- Product Data SYST0101CW (doc 616 31 1600 01) and Installation Instructions — public via
  shareddocs.com / manuals.plus / ManualsLib. Installation-level only (wiring, setup menus);
  no register/protocol content.
- NIM / translator-board manuals (SYSTXXXTRB01) give the canonical ABCD pinout:
  **A = Green RS-485+, B = Yellow RS-485−, C = White 24 VAC COM, D = Red 24 VAC HOT**.
  (Note: our wall harness has B as **blue**, not yellow — harness colour variance; pin
  functions match.)
- Series C controls (SYSTXCCITC01-C) moved home automation to a cloud **Open API**
  ("Infinity Systems Open API Getting Started Guide", HVACpartners; contact
  InfinityOpenAPI@carrier.utc.com) plus the SYSTXNNRCT01 SAM — the SAM ASCII path remains
  the only local protocol Carrier documents.
- OpenADR 2.0b PICS listings include SYST0101CW / SYSTXCC* models — demand-response profile
  only, **no bus-protocol value**.

## 3. FCC filings

- **FCC ID 2AK6N-CCITC01B** — "Carrier Infinity System Control", grantee **United
  Technologies Electronic Controls Inc. (UTEC), 3650 W 200 N, Huntington, IN 46750**;
  grant 2017-07-19; Wi-Fi 2412–2462 MHz (0.0495 W) + Bluetooth 2402–2480 MHz.
  Filing includes test report #316398 (2017) and internal/external photos — hardware
  identity for the Carrier -B control (same UTEC platform family as the Ion).
  URL: https://fccid.io/2AK6N-CCITC01B
- Related UTEC grants: **2AK6N-TSTWHA01** (Côr 5C thermostat, 2017);
  **2AK6N-MICROLINK5** ("Micro-Link 5 Controller", 2019; a 2026 Class II permissive change
  adds a second antenna/2×2 MIMO and BLE — likely the radio platform of the newest
  controls). URL: https://fccid.io/2AK6NMICROLINK5
- **Negative / unconfirmed:** no separate FCC ID for the ICP **SYST0101CW** was established
  by direct search; fccid.io blocked direct API-style queries (401/403). The Ion control is
  presumably certified under the same UTEC platform filings, but this is **not verified**.

## 4. Patents & litigation

### 4.1 US 7,243,004 — "Self-configuring controls for HVAC systems" (Carrier; Shah/Ryan)

- Filed 2004-01-07; **expired 2024-11-21**. Concept: each unit in an HVAC system reports its
  characteristics/capabilities to the central control, which then **selects the optimal
  control strategies/parameters for that specific combination of equipment**.
- **Technical value:** this is the patent frame for the exact mechanism stage D isolated in
  the firmware (equipment self-identifies over the bus → thermostat commits model-derived
  parameters, e.g. coil EN(A,D)4X61 → float 1.69 into field 0x59F → ODU command 061E). The
  specification's description of what data units report and how strategies are chosen is the
  best public prose description of the self-configuration flow our emulator must reproduce
  when the furnace/ODU commission.
- Source: Google Patents, US7243004.

### 4.2 US 7,775,452 — the ABCD data-bus patent

- The bus patent asserted alongside '004 in Carrier v. Goodman: the serial communicating
  bus where **C and D carry 24 VAC power** while A/B carry data — the physical-layer frame
  of the ABCD system.

### 4.3 Carrier v. Goodman litigation materials

- Case 12-930-SLR (D. Del.); claim-construction materials for '004/'452 are on CourtListener
  / archive.org. Value: court-tested plain-language definitions of the bus and
  self-configuration claims — occasionally clearer than the patents themselves.

### 4.4 Negative

- **US 7,415,102 (pointSET Corp)** — programming appliance features via a web server;
  **not** Carrier, **not** control algorithms. Dead end.
- No Carrier patent found that discloses the on-wire register map, staging demand
  computation, or frame timing — the patents describe architecture and strategy selection,
  not the wire protocol. Our stage E demand/staging constants remain RE-only knowledge.

## 5. Forums & community RE

### 5.1 Cocoontech "Carrier Infinity" thread — the origin community

- URL: https://cocoontech.com/threads/carrier-infinity.11372/page-14 (thread runs from
  ~2010; participants include **3tones** — author of brybus, ancestor of finitude — and
  **nebulous**).
- Technical nuggets (page 14):
  - "The mysterious 1F device/broadcast from thermostat shows up whenever a newcomer arrives
    on the bus… if I fake a frame from an as-yet-unknown device, the thermostat immediately
    interrogates it from 1F01." — **independently confirms our 0x1F SystemInit observation**
    and its trigger condition.
  - Transmissions sometimes end with an **abort signal: 00FC, 00FD, 00FE or 00FF** —
    candidate explanation for truncated frames in captures.
  - 3tones identified the **entire heat-pump defrost sequence** from trend logs, which pinned
    down several registers — methodology + register hints for ODU/defrost work.
  - SAM note: "the data tables in the [Touch] stat are slightly different than those in older
    models… it is definitely possible to control the devices (furnace/blower/etc) but not
    necessarily the thermostat" — matches our finding that Ion serves all-zero 3B02/3B03 to
    an unregistered SAM.
  - The SAM01-01XA spec (§2.1) is the document this community built RS-232 integrations on.

### 5.2 Other forums

- **Hubitat community** — SAM RS-232 ASCII integrations; confirms SAM01-01XA.pdf as "the
  protocol" document and Global Caché IP2SL-style serial bridges as the common path.
  https://community.hubitat.com/t/serial-bridge-infrared-ir-contact-closure-etc/7030
- **HomeSeer forum** — Infinitude/SAM integration history; a user with an HAI Omni-II
  controlling Infinity via SAM ASCII. Low new technical content.
  https://forums.homeseer.com/forum/homeseer-products-services/general-discussion-area/1616056-support-for-carrier-infinity-bryant-evolution-ion-hvac-smart-thermostats/page2
- **Home Assistant community** — Infinitive + mww012 component setups (multi-unit,
  per-unit Pi). Deployment lore only.
  https://community.home-assistant.io/t/carrier-infinity-integration/17161?page=2
- **hvactechgroup.com** — installer chatter: firmware-version-dependent airflow behaviour
  (see §2.3). No protocol data.
- **hvac-talk.com / Reddit (r/hvac, r/homeautomation)** — **negative**: searches surfaced no
  register-level or protocol RE threads; discussion is at the "replace with ecobee and lose
  features" level.

## 6. Other projects surfaced by web search (GitHub — sibling's scope, listed for context)

- **infinitive** (acd; forks mww012, lurgh — lurgh adds multi-zone + MQTT, active May 2025):
  SAM impersonation on the bus for non-Touch stats; README confirms ABCD split (A/B RS-485,
  C/D 24 VAC) and 1-second thermostat polling.
  https://github.com/lurgh/infinitive/tree/master?tab=readme-ov-file ·
  https://pkg.go.dev/github.com/5310h/infinitive-1
- **gofinity** (bvarner, 2017): Go library + "Protocol / Device Information", bootup
  sequence notes, pi485 hardware.
- **finitude** (PyPI): ABCD frame decoder, descendant of 3tones' brybus (2014).
- **carrier-api** (PyPI): Carrier cloud GraphQL API — **not** the bus; no use for RE.
- **Infinitude wiki "Infinity Protocol Hardware"** — mirrored at github-wiki-see.page under
  nebulous/infinitude.

## 7. Explicit negative results

1. **GitLab:** no relevant public projects for any search term; snippets API not anonymously
   searchable (401). Nothing to mine.
2. **Firmware leaks/dumps:** none. BINF* images exist only through Carrier/ICP's official
   EULA/USB/HVACpartners channels (§2.3).
3. **FCC for SYST0101CW specifically:** not confirmed (see §3).
4. **Patents:** no disclosure of wire-level registers, demand/staging math, or frame timing.
5. **hvac-talk / Reddit:** no protocol-level RE content found.
6. **OpenADR PICS for SYST0101CW:** exists but contains no bus information.
7. **Service/training literature:** beyond the SAM spec (§2.1), no dealer diagnostic document
   describing ABCD register traffic was found in public sources; Carrier's ABCD training
   material remains behind HVACpartners dealer login.

## 8. What each top find could give the project

| Find | Gives us |
|---|---|
| SAM Application Specification (SAM01-01XA) | Vendor semantics for the ASCII command set our node speaks; timeout & abnormal-condition rules for the emulator's SAM personality |
| Infinitude CarBus docs (AGENTS.md / SAM.pm) | Register semantics + the four temperature encodings — validation layer for our protocol map and emulator setpoint handling |
| US 7,243,004 | Authoritative description of the self-configuration flow (units report → control selects parameters) behind the stage D coil/equipment mechanism |
| Cocoontech thread | Independent confirmation of 0x1F newcomer interrogation + abort trailers 00FC–FF; defrost-sequence register hints |
| Official BINF channel | Legal multi-version firmware set for diffing algorithm constants across releases |
| FCC 2AK6N-CCITC01B | Hardware photos/identity of the UTEC control platform (Carrier sibling of the Ion) |
