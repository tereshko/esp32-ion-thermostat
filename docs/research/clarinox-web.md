# Clarinox — web research notes

**Question:** In the Carrier/ICP Ion thermostat firmware (Renesas SH-2A / SH7269,
in-house Ghidra work), the middleware/binding layer behaves like a "Clarinox
engine": runtime-registered property bindings, a dictionary-space object model,
computed properties, message classes with RAM-registered handler tables.
Is this technology publicly known/documented, and is any of it reusable for
our reverse engineering?

**Date:** 2026-11-26. Method: web search + page fetches. Every claim below
carries its source URL. Vendor marketing is flagged as such; absence of a
result is reported as "not found", not filled in.

---

## 1. What Clarinox is (vendor facts)

- **Clarinox Technologies Pty Ltd**, Cheltenham/Melbourne, Australia, founded
  2001 by Trish Messiter (with Gokhan Tanyeri, CTO). Small unfunded licensing
  company (~11–50 staff). It licenses embedded **wireless protocol stacks** —
  it does not sell an application framework product line.
  - https://www.crunchbase.com/organization/clarinox-technologies
  - https://tracxn.com/d/companies/clarinoxtechnologies/__XAf2vzh7JIAb2_ev_GkKGgEm5AFuX3_hx2i_sJnGVs8
  - https://alchetron.com/Clarinox-Technologies-Pty-Ltd

- Public product portfolio (complete, per the vendor's own developer site):
  1. **ClarinoxBlue™** — Bluetooth Classic (BR/EDR) + BLE protocol stack,
     incl. Mesh and Auracast; Bluetooth company ID 0x00B3.
  2. **ClarinoxWiFi™** — WLAN stack (AP / STA / P2P / WPS / Mesh).
  3. **ClarinoxSoftFrame™** — the portable middleware/abstraction layer both
     stacks run inside (see §2).
  4. **ClariFi™** — debugger/protocol analyser for the stacks (incl. the
     "ClariFi Insight" non-intrusive trace buffer feature, 2022).
  5. Supporting items: **Jannal** IDE (trademarked "Intelligent Design
     Environment" for developing/testing embedded firmware) and the
     **Koala** EVM development board.
  - https://develop.clarinox.com/products/softframe/ (products & solutions list)
  - https://www.clarinox.com/products/clarinoxblue/
  - https://www.clarinox.com/company/partners/ (Jannal, Koala mentions)
  - https://www3.wipo.int/madrid/monitor/en/showData.jsp?ID=ROM.1202129
    (WIPO trademark record: IDE for development/testing of embedded firmware)

- Ecosystem presence: Renesas partner (Synergy Gallery contributor, R-Car
  Consortium; stacks licensed for Renesas RA MCUs), TI partner (CLRNX),
  NXP Gold Partner, Green Hills, IAR, Wind River, SYSGO partner listings.
  Note the Renesas connection — the Ion's SH7269 is a Renesas part, and
  Clarinox explicitly markets Renesas platform support.
  - https://www.renesas.com/en/about/press-room/renesas-synergy-platform-revs-ecosystem-growth-engine
  - https://www.businesswire.com/news/home/20200728005379/en/ (Renesas RA ecosystem, Clarinox listed)
  - https://www.Ti.com/partner/CLRNX

## 2. ClarinoxSoftFrame — the only "framework" product (Q1, in part)

What SoftFrame publicly **is** (vendor description, consistent across the
vendor site, a TI technical article, and a 2014 book chapter by Clarinox's
own staff):

- An RTOS/OS abstraction layer: applications are written once against the
  SoftFrame API (developed on desktop in MSVC/GNU), then recompiled per
  target. It supplies **threading, timers, semaphores, mutexes, IPC message
  passing, event handling, finite state machines**, standard libraries, and
  fragmentation-free deterministic memory management (pools).
  - https://develop.clarinox.com/products/softframe/
  - https://www.ti.com/lit/ta/ssztbf3/ssztbf3.pdf (TI article SSZTBF3, Apr 2016)
  - http://develop.clarinox.com/site/assets/files/1214/whitepaper_07_qnx.pdf
    (Clarinox whitepaper: the same feature list verbatim)
- Architecture sketch (2008/2010 vendor deck): USER APPLICATION →
  ClarinoxSoftFrame API → "MEDIATOR" → OS-specific interface / kernel /
  I/O subsystem / HAL. Also: a **configuration interface** — "interface
  provided to change parameters without requiring compilation… Plain Text
  or XML configuration" — plus trace/debug/profiling hooks.
  - http://develop.clarinox.com/site/assets/files/1209/ct2010_softframe4nicta.pdf
- Application and protocol stack can be separated via **inter-process
  communication**, allowing the stack and the app to run on different CPUs.
  - https://develop.clarinox.com/products/softframe/
- Supported RTOS list (marketing): FreeRTOS, ThreadX/Azure RTOS, eCos,
  embOS, INTEGRITY, Linux, MQX, Nucleus, QNX, RTX, TI-RTOS, uC/OS-II/III,
  VxWorks, Windows/CE, AUTOSAR, etc. CPU/MPU ports listed publicly are
  ARM-centric plus TI DSP/Sitara, NXP i.MX/Kinetis/LPC, STM32, Renesas
  Synergy S5/S7, RH850, R-Car — **no Renesas SuperH/SH-2A port is mentioned
  in any public material found** (the SH7269 predates most of this list;
  absence here is weak evidence only).
  - https://en.wikipedia.org/wiki/WIDCOMM (ClarinoxBlue section, CPU list)
  - https://www.ghs.com/partners/clarinox_partner.html

**What SoftFrame is not, publicly:** nothing in any vendor page, datasheet,
whitepaper, or the academic chapter describes a *data dictionary of device
objects*, *property binding*, *computed properties*, or a *property
registration* API. Those terms simply do not occur in Clarinox's public
vocabulary. See §5.

## 3. Public technical substance about SoftFrame's internals (Q3, in part)

The single substantive public technical description is a book chapter by
Clarinox's founders:

- Tanyeri, Messiter, Beckett — **"Framework-Based Debugging for Embedded
  Systems"**, in *Advances in Systems Analysis, Software Engineering, and
  High Performance Computing*, IGI Global, 2014, ch. 18, pp. 424–454,
  DOI 10.4018/978-1-4666-6194-3.ch018. It uses the "ClarinoxSoftFrame®
  Suite" as its example framework and discusses thread interaction,
  timers/semaphores/mutexes, IPC message passing, event handling and FSM
  organisation, plus a modular/open debugging architecture. Abstract and
  sample pages are public; the full chapter is paywalled (purchase).
  - https://www.igi-global.com/chapter/framework-based-debugging-for-embedded-systems/116121
  - https://www.igi-global.com/viewtitlesample.aspx?id=116121&ptid=102212&t=Framework-Based+Debugging+for+Embedded+Systems
  - https://www.igi-global.com/dictionary/embedded-framework/44532

- A later Clarinox conference-style paper, "Deal with Component Shortages
  Using Abstraction Based Connectivity Solutions", describes SoftFrame
  abstraction layers (processor, MCU/MPU, OS/RTOS, BT/Wi-Fi chipset) with a
  block diagram — marketing-level, no internal data structures.
  - http://develop.clarinox.com/site/assets/files/1333/wirelesssoftwareabstraction_1.pdf
  - Vendor-hosted PDF also at https://clarinox.com/site/assets/files/1328/wirelesssoftwareabstraction.pdf
    (linked from Crunchbase profile)

- **Patents: not found.** Multiple searches (assignee name, inventor names
  Tanyeri/Messiter, Google Patents phrasing) surfaced **no patent filings
  by Clarinox Technologies**. Their registered IP visible publicly is
  trademarks (CLARINOX word mark AU 920288; Koala AU 1547905; Jannal IDE
  AU 1547907 / WIPO IR 1202129). If Clarinox holds patents, they are not
  indexed under the company name in the sources searched — treat as
  "no public patent trail".
  - https://aubiz.net/company/clarinox-technologies-pty-ltd-062954170/ (trademark list)
  - https://www3.wipo.int/madrid/monitor/en/showData.jsp?ID=ROM.1202129

- **Open-source code / leaked SDK: not found** for SoftFrame or the stacks
  themselves. GitHub/web searches for Clarinox headers or source returned
  no Clarinox code (only unrelated projects). The stacks are commercial,
  licensed per-project; there is no public download on clarinox.com or
  develop.clarinox.com (the developer site hosts product pages and PDFs
  only — documentation/SDK are behind the commercial licence).
  - One concrete third-party eval channel: NXP's **EasyEVSE** development
    platform ships a downloadable ~83 MB software package (EasyEVSE-SW
    Rev 3.0) that includes a **Clarinox Wi-Fi stack under an evaluation
    licence** (for the u-blox MAYA-W1 / IW416 target). This is the only
    publicly downloadable artefact found that contains actual Clarinox
    deliverables (typically headers + binary libraries + reference app).
    It is Wi-Fi-stack material for an ARM target — it would show Clarinox
    API/header style, but nothing about a dictionary/binding engine.
    - https://www.nxp.com/design/design-center/development-boards-and-designs/CONNECTED-EVCH
...[truncated 5832 chars]