# Background — the HVAC situation this project grew out of

Why a bus-level replacement thermostat exists at all: the house's
conventional control path is half-broken, and the stock communicating
control is a single point of failure with a dead radio. Facts
established 2026-10-18 → 2026-10-25 (full working diagnosis kept in
the project archive).

## The ecobee path (conventional 24 V control) — heat only, degraded

- The furnace board's **W/W1 input is dead** (diagnosis 2026-10-18).
  The discriminating test: the same black wire carrying the ecobee's
  W1 signal produces heat on the board's W2 terminal and silence on
  W/W1. The violet wire, long suspected dead in the wall, was alive
  all along — that hypothesis was wrong.
- **Final working scheme (still the house's fallback):** one heat
  stage via W2 — board W2 ← black (ecobee W1); W/W1 empty; the white
  wire disconnected and insulated at both ends; on the ecobee, W2 ←
  white (leads nowhere). The house heats on the high stage only; a
  low stage cannot be had through this path.
- The board is marked **CEBD430988-10-RA** — a PCB fabrication
  number, not a catalog part number. ICP sells OEM boards through
  dealers; open pricing found: board $50–300, replacement with
  labour $300–700 (labour $75–175/h, 20–90 min). No factory defect
  or bulletin for the W1 failure was found; cracked solder at the
  terminal is the likely cause. **Owner's decision: do not repair
  or replace the board** — this is the project's starting point.
- **Cooling through 24 V is impossible in principle:** the
  HVA960GKA outdoor unit speaks only the digital bus; the furnace
  board does not translate a 24 V Y signal into bus commands (its
  Y/W terminals serve a conventional, non-communicating outdoor
  unit). **Never connect Y to DX+** — 24 V on the bus burns boards
  (vendor documentation warning).

## The stock Ion control — master of the bus, dead radio

- The SYST0101CW's **Wi-Fi module is dead**; with Wi-Fi disabled it
  works indefinitely as a local controller (diagnosis closed
  2026-10-25). There is no "forget network" function: the reset is
  Menu → Wireless → Wi-Fi DISABLED, wait ~10 s, ENABLED, then
  "Setup a Wi-Fi Connection" again; the radio is 2.4 GHz only.
- The control's firmware updates **offline via microSD** — the
  update path exists and does not affect the SAM gate.
- Replacement is **whole-control only**, and the 0101 is
  **discontinued**. The official successor is the Series C
  **SYST0201CW** (~$700+, mostly through dealers): same four wires,
  self-configures from the bus, USB-C instead of microSD, firmware
  v2.00.
- **Spare-control plan** (if the Ion dies before the replacement is
  ready): used/sealed 0101 units run **$200–400** (new old stock was
  found at $660); search under any ICP badge — Heil, Tempstar,
  Comfortmaker, Arcoaire, Keeprite, Kenmore are the same hardware.
  A used unit may be bound to the previous owner's **My Ion**
  account; ICP support can unbind it. A fresh control
  self-configures from the bus; profiles and schedules are set up
  from scratch.
- Rejected spares: the **Ion Gray TSTATIIEWF-01** is a
  non-communicating thermostat (standard 24 V terminals, no ABCD
  bus) — it cannot replace a 0101. A **Carrier SYSTXCCITC01-A**
  listing at $289.99 was internally contradictory (title/MPN of the
  older button unit vs. box photo/model of the ITC01-A); even if
  genuine, cross-brand Carrier↔ICP compatibility is not officially
  supported. No purchase was made.
- For scale: the stock control's visible display window is in the
  ~4.3″ class; the 5.6″ × 4.7″ "display size" in distributor data
  is the housing (4.7″H × 5.6″W × 1.1″D) — the manufacturer
  publishes no panel diagonal.

## Two design constraints that follow

- **Apple Home visibility is a requirement:** all temperatures and
  control must surface in Apple Home via the Home Assistant
  HomeKit Bridge — no extra hardware. (The reverse direction —
  the Logitech Circle View doorbell into HA via HomeKit
  Controller — is the panel's doorbell path, see `PANEL.md`.)
- **Zone-controller emulation is out of scope and dangerous
  here:** a zone controller (0x60) runs a daily duct checkout
  that stops heating/cooling until validated; this house has no
  real dampers. The ZC emulation present in the vendored
  component stays inert (see `ENTITY-INDEX.md`).
