# DIY Thermostat for the Carrier/ICP "Ion" Bus

Reverse engineering of the RS-485 communication bus used by Carrier / ICP
**Ion System Control** (SYST0101CW) communicating thermostats, and an
ESPHome-based path to first *mirror*, then *back up*, and eventually
*replace* the wall control — without ever leaving the furnace and outdoor
unit without their own board-level protections.

Test installation: Heil G80CTL two-stage gas furnace (107K BTU/h) +
Heil HVA9 variable-speed outdoor unit (5 ton) + EN(A,D)4X61 evaporator
coil, one zone, thermostat firmware v4.79.

> **Safety first.** All compressor and ignition protections (anti-short-cycle,
> pressure-switch lockouts, purge/proving timings) live in the furnace and
> ODU control boards, not in the thermostat — verified against the factory
> service manuals. The thermostat layer only computes setpoints and demand.
> Nothing in this repository has ever driven the equipment without the stock
> wall control present and able to take over. Proceed at your own risk; if
> you are not comfortable around 24 VAC control wiring and RS-485, do not
> replicate this.

## Start here

**[`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md)** — the distilled guide:
the wire protocol, the poll/burst schedule, boot and commissioning, the
tables that matter (including the writable 400A comfort table), why SAM
registration is a dead end and how 400A control works anyway, the recovered
control law (demand, staging, CFM), where the protections live, the
failover design, hardware/wiring/power, and what is still unknown.
The full wiki behind it — evidence, derivations, verification — is mapped
below.

## Status (2026-11-26)

- **Protocol: fully mapped and independently re-verified** — frame layer,
  schedule, boot, served tables and the complete control law were extracted
  from the thermostat firmware image and re-derived from primary artifacts
  in a 20-way independent verification pass.
- **Working today (honest status, 2026-11-26):** setpoint control via
  the 400A comfort table is proven live (phase 3, in service
  2026-11-03 → 2026-11-24). The node is currently **off the bus** —
  disconnected after the 2026-11-24 power incident and running on
  USB — and the unified firmware (`firmware/thermostat.yaml`) is
  written but **not yet compiled or flashed**. Returning to the bus
  is gated on the power-supply decision; full status, decisions and
  the plan: [`docs/STATUS-AND-PLAN.md`](docs/STATUS-AND-PLAN.md).
- **Next:** a shadow (mirror) node on ESP32-S3 that runs the full control
  law in parallel with the stock thermostat, logs divergences, and takes
  over only if the stock control goes silent (measured safe window:
  between >36 s and ~2 min of silence; the stock control always wins the
  bus back the moment it speaks).
- **Open items are data, not code:** the equipment class word and several
  control-law constants cannot be read off the unit and will be calibrated
  in shadow mode; sustained part-load cooling behaviour awaits a summer
  capture.

## The knowledge base (wiki)

Everything the project has established, organised so a new reader — human
or AI — can go from zero to full context without asking anything:

**Reading order**

1. **[`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md)** — the distilled
   guide: how the bus, the control law and this node work, in one file.
2. **[`docs/THERMOSTAT-PROTOCOL-MAP.md`](docs/THERMOSTAT-PROTOCOL-MAP.md)**
   — the wire truth in full detail: steady state, served tables, cold
   start, cadence limits, scenario deltas, the gap list, errata and the
   2026-11-26 verification corrections.
3. **[`docs/EMULATOR-SPEC.md`](docs/EMULATOR-SPEC.md)** — the
   implementation-ready specification of a replacement thermostat:
   frame layer, boot, served tables, control law, protections,
   failover constraints, open gaps.
4. **[`docs/evidence/`](docs/evidence/)** — proof from the capture
   logs: the corpus inventory and session index, and exhibits computed
   from ≈84 000 frames — boot milestones, burst anatomy, the all-zero
   SAM mirror by count, the honoured 400A writes, heating/cooling
   calls, and the 36 s thermostat-silence capture.
5. **[`docs/firmware-analysis/`](docs/firmware-analysis/)** — how each
   fact was derived from the firmware image: the stage reports
   (B–Y, AA, Series C, versions, the 060B byte), two independent
   audits, SAM registration research, the direct-write research and
   the live 400A test report.
6. **[`docs/verification/`](docs/verification/)** — the 20-report
   independent re-derivation of every load-bearing claim from the raw
   artifacts, CONFIRMED / REFUTED per claim.
7. **[`docs/research/`](docs/research/)** — external sources: the
   SAM01-01XA ASCII spec analysis, infinitive register layouts, the
   gofinity boot-capture cross-check, Clarinox stack notes, sweeps,
   and the open upstream thread (nebulous/infinitesp#61).
8. **[`docs/firmware-history/`](docs/firmware-history/)** — the
   build-by-build write-ups of the node firmware (what each iteration
   changed and why), the mode-experiment plan and the bench-test
   notes. The code itself is unified — see `firmware/`.

**Project state, hardware, panel**

- **[`docs/STATUS-AND-PLAN.md`](docs/STATUS-AND-PLAN.md)** — where the
  project actually stands, the decision log, and the 10-step plan to
  replace the stock control.
- **[`docs/HARDWARE-AND-POWER.md`](docs/HARDWARE-AND-POWER.md)** — the
  full parts inventory and the power-supply design space, including
  the isolation rule learned from the 2026-11-24 incident.
- **[`docs/PANEL.md`](docs/PANEL.md)** — the wall-panel build (ESP32-S3
  + display): hardware, UI specification, owner decisions. (Currently
  in Russian.)
- **[`docs/ENTITY-INDEX.md`](docs/ENTITY-INDEX.md)** — the file-level
  index: core config, entity ids, helper/automation logic, what the
  node serves as a SAM, the console surface.

## Repository layout

- `docs/` — the knowledge base above.
- `firmware/` — the unified ESPHome node firmware (`thermostat.yaml`),
  its components, the Home Assistant package (`home-assistant.yaml`),
  and build/operating notes (`firmware/README.md`). Copy
  `firmware/secrets.yaml.example` to `secrets.yaml` and fill in your own
  values; sensor MAC addresses in the configs are placeholders.
- `tools/capture.py` — the bus capture client used to record the JSONL
  traces the analysis is derived from.

## Hardware (current node)

- ESP32 (DevKit, CP2102) on a perfboard carrier, MAX13487E RS-485 module.
- Bus: 38400 8N1; wall cable DX+ green, DX− blue, C white, D red (24 VAC).
- LYWSD03MMC BLE room sensors (ATC firmware, ATC1441 advertising).
- Target platform for the mirror/panel builds: ESP32-S3 (N16R8).

⚠️ **Power warning, learned the hard way:** never power the node from the
C/D pair through a non-isolated buck converter — the C wire is the bus
common, and a non-isolated converter shorts C to D through its bridge.
Use a converter with datasheet-rated isolation and bench-verify
(input↔output open circuit, clean 5.0 V out) before connecting anything
to the bus. Details in the guide, §10.

## Development workflow

One firmware, one knowledge base. Every validated build lands here as its
own commit with the matching notes, so the history doubles as the lab
notebook.

## Credits and license

This project builds on — and would not exist without:

- [InfinitESP](https://github.com/nebulous/infinitesp) by nebulous
  (MIT) — the ESPHome SAM implementation the node firmware derives from;
  a vendored copy with its license lives under `firmware/components/`.
- [infinitive](https://github.com/lurgh/infinitive) by Andrew Danforth
  (MIT) — SAM register layouts that cross-checked byte-for-byte.
- [gofinity](https://github.com/bvarner/gofinity) by Bryan Varner (MIT) —
  the 2014 Bryant Evolution boot capture used as an independent corpus.

Every load-bearing claim is tied to a primary artifact and was
independently re-verified.

Repository content is released under the MIT License (see `LICENSE`
and `NOTICE`). Vendor firmware images, vendor manuals and raw bus
captures are **not** included in this repository.
