# Hardware, procurement and power

Everything the project physically consists of: what was ordered, what
arrived, what is installed, and the power-supply design — including the
incident that produced the project's hardest hardware rule.

Status dates are as of 2026-11-26.

---

## Part 1 — Hardware inventory

### 1.1 The bus node (the working unit at the wall)

| Item | Key specs | Purpose | Status |
|---|---|---|---|
| ESP32 DevKit (classic ESP32, CP2102 USB-UART) | The original node MCU | Runs the ESPHome node firmware: bus telemetry into Home Assistant and 400A setpoint control from the SAM slot (0x92) | Was installed at the wall from phase 1 (2026-10-29); currently disconnected from the furnace and USB-powered since the 2026-11-24 power incident (see Part 2) |
| HW-451 carrier/shield board | Per-GPIO colour-coded pin triplets: **black row = G (ground), red row = V (power), blue row = S (signal)** | Carries the ESP32 and breaks out the wiring to the RS-485 module | Installed with the node. Root cause of the 2026-10-28 incident: all ESP-side wires landed in the black (G) row instead of blue (S), which keyed the bus — see the protocol/incident notes |
| RS-485 module, MAX13487E | Auto-direction transceiver; A → DX+, B → DX−, module GND = bus common (C, white wire) | The node's only physical interface to the Ion bus (38400 8N1) | Installed with the node. One module is enough — a second one was considered only as a spare and is not needed; the same module moves to the panel carrier later |
| Bus wiring at the wall | 4 wires: **DX+ green, DX− blue, C white, D red (24 VAC)**; TTL side module↔ESP: module TXD (green) → GPIO16, module RXD (yellow) → GPIO17, VCC (red) → 3V3, GND (black) | Connects the node to the furnace bus and to the C/D power pair | Verified against a wall photo 2026-10-28. TTL signal wires land **only** in the blue (S) row of the HW-451 triplets. **Power the module from 3.3 V ONLY — 5 V on the TTL lines kills ESP32 GPIOs** |

### 1.2 ESP32-S3 boards (mirror node + future panel)

| Item | Key specs | Purpose | Status |
|---|---|---|---|
| ESP32-S3-DevKitC-1 **N16R8**, GlobalGo, Type 2 ×2 | 16 MB flash, 8 MB PSRAM, CP2102, header pre-soldered (Type 2); $5.33 each (11.11 sale; regular $6.30) | Board №1 — mirror / shadow emulator: RX-only bus listener that runs the control law in parallel and logs divergences from the real Ion. Board №2 — the gradual sensor/panel build (the full thermostat) | Ordered 2026-11-18; **both arrived 2026-11-26** |

### 1.3 Panel kit (all ordered 2026-11-12, AliExpress; delivery window 22–28 Nov)

| Item | Key specs | Price | Purpose | Status |
|---|---|---|---|---|
| Display 3.5″ IPS Touch | ST7796U controller + FT6336U capacitive touch, 480×320, module 98×56 mm | $9.29 ($18.91 with delivery) | The panel screen | Ordered 2026-11-12 |
| Light sensor TSL2591, Qwiic | I2C 0x29; chosen over BH1750 for auto-brightness (wider range, no saturation in bright light, sensitive in the dark) | $3.70 | Auto-brightness via a window in the panel face | Ordered; sensors partially arrived by 2026-11-22 |
| Temp/humidity sensor SHT40, Qwiic | I2C 0x44 | $2.40 | The panel's own room temperature — the future emulator's temperature input if the Ion dies; lives in an isolated vented chamber in the enclosure's lower-right corner so self-heating does not bias it | Ordered |
| Spare Qwiic cable (single head) | JST SH 1.0 mm | $1.10 | Spare sensor interconnect | Ordered |
| QT → Dupont female cables 200 mm ×3 | Qwiic (JST SH) to Dupont | $3.89 | Solderless sensor wiring | Ordered |
| Presence radar LD2410C | 24 GHz mmWave; sits behind plain plastic in the enclosure's upper-right zone, clear of the display board and metal | $3.38 | Wakes the panel screen on presence | Ordered |
| Microphone SPH0645 | I2S MEMS (WCMCU board) | $3.47 | Voice input for the panel | Ordered |
| Amplifier MAX98357A | I2S, mono | $1.98 | Speaker output (media player / doorbell chime in HA) | Ordered |
| Speakers 40 mm, 4 Ω, 3 W ×2 | With PH2.0 leads. On the mono amplifier the pair is wired **in series only (8 Ω total)** | $4.13 | Panel audio out | Ordered |
| Collet (turned-pin) sockets 1×40, PH3mm, Gold | Low-profile (~3 mm) | — | The ESP sits removable on the panel carrier — no desoldering | Ordered (confirmed 2026-11-17) |
| JST SH sockets, horizontal (side-entry), 4-pin | Side entry keeps the stack thin: cable leaves parallel to the carrier (~3 mm instead of +8–10 mm vertical) | — | Qwiic sensor sockets soldered onto the carrier | Ordered (confirmed 2026-11-17) |
| Screw terminals KF301-2P | ~9–10 mm tall — the tallest part on the carrier | — | Bus/power connections on the carrier | Ordered (confirmed 2026-11-17) |
| Silicone wire set, QianFang 24 AWG | — | — | Carrier wiring | Ordered (confirmed 2026-11-17) |
| Barrel → USB Type-C adapter (JCD) | — | $2.59 | Adapting the ordered AC/DC converter output to the node | Ordered |

Panel platform decision (2026-11-17): the panel is built on the
ESP32-S3 N16R8. An ESP32-P4 upgrade (Waveshare all-in-one boards) was
evaluated and **rejected** — the S3 stays.

### 1.4 Room sensors (BLE)

| Item | Key specs | Purpose | Status |
|---|---|---|---|
| LYWSD03MMC №1 | ATC firmware v5.9, ATC1441 advertising, values in °C, ESPHome platform `atc_mithermometer`, bound by MAC | Room temperature input for sensor steering; physically in the children's room ("Room 1" in the firmware) | Installed and live since phase 4; advertising interval is the factory 2500 ms |
| LYWSD03MMC №2 | ATC firmware, ATC1441, °C, advertising interval set to **5000 ms** | Second room sensor ("Room 2") | Ordered with the 2026-11-12 panel batch; configured 2026-11-24; telemetry only — not a steering input |
| CR2032 cells | Sensors often ship without batteries | Power for the BLE sensors | Purchase not confirmed in the project records |

Why BLE: it is already in the ESP32 — no hub or coordinator needed
(a Zigbee coordinator would add ~$30 and a Home Assistant binding;
Wi-Fi sensors drain batteries). Each unit runs about a year on its
CR2032; the battery level is advertised and the panel design shows
a low-battery warning.

### 1.5 Bench and consumables already on hand

| Item | Notes | Status |
|---|---|---|
| Phenolic prototyping boards 5×7 cm ×10 | 1.2 mm, single-sided; two butted (100×70) suffice for a prototype carrier | On hand |
| Breadboard MB-102 (830 points) | Panel bench-test layout and firmware (`panel-bench-test`) are written for it; the classic ESP32 from the wall node serves as the bench MCU while the S3 boards were in transit | Bench assembly not confirmed in the project records |
| AHT10 sensor | I2C 0x38, with header | Bench/spare only — the panel gets the SHT40 |
| Heat-set brass inserts M2 + screws, 500 pcs | Enclosure fasteners for the 3D-printed case | On hand — enclosure fastening closed |
| USB power bank / any 5 V USB charger | Interim node power, independent of the furnace breaker (actually ideal for cold-start captures) | In use as the interim supply |
| Enclosure design | 150 × 118 × 28 mm; SHT40 in an isolated vented chamber, LD2410C behind plain plastic, speakers in closed cups against the front wall | Designed (`panel/PANEL-LAYOUT.html`); depth is set by the power-supply zone — see Part 2 |

### 1.6 Rejected / forbidden hardware

| Item | Verdict |
|---|---|
| **XWST sealed AC 24 V → DC 5 V converter, 3 A variant** (ordered 2026-11-12, $7.10, "3A With DC Output") | **Never connect to the bus, in any wiring variant.** Non-isolated — see the incident in Part 2. |
| Earlier "waohei" sealed converter found 2026-10-24 | DC-input only, does not run from furnace 24 VAC at all — rejected before purchase |
| ESP32-P4 / Waveshare all-in-one panel boards | Evaluated 2026-11-17, rejected by decision — panel stays on ESP32-S3 |

---

## Part 2 — Power: feeding the node from C/D, and the isolation rule

### 2.1 The problem

There is **no mains outlet at the wall**. The only energy available to
the node is the thermostat pair itself: **C (white, common) and D
(red, 24 VAC)**. Any wall/panel build therefore has to derive its 5 V
from 24 VAC — and do it without ever disturbing the bus that shares
those wires.

### 2.2 The incident (2026-11-24): a non-isolated buck shorted C to D

The ordered XWST AC24V→5V module was connected to power the node from
C/D. On power-up there was a pop, the furnace stopped, and the Ion
showed **INDOOR UNIT COMMUNICATION FAULT** with outdoor temperature
"---".

Mechanism, established afterwards from the manufacturer's own
specification (the whole XWST line is non-isolated):

- In a **non-isolated** buck converter the output negative is tied to
  the input. Feed it 24 VAC through a bridge and the output ground
  ends up connected to one side of the AC input.
- Wiring the converter across C/D therefore **shorts C to D** through
  the converter — the bus common and the 24 VAC line are bridged.
- The short blew the furnace control-board fuse. The fuse was
  replaced and the furnace restarted; the node was disconnected from
  the furnace entirely.

Two aggravating details from the same day: while the converter was
being fitted, the white (C) wire had also been lifted off the RS-485
module at one point, leaving the module without the bus common — and
an earlier suggestion to tee the white wire to both the module ground
and the converter input is **withdrawn as dangerous**: with a
non-isolated converter, any such tee shorts C↔D just the same.

### 2.3 The hard rule

> **Bus power comes only through a converter with galvanic isolation
> stated in its datasheet.** "AC input" on a marketplace listing is
> not evidence of isolation — the XWST listing never claimed it.
> (Provenance, kept deliberately: the XWST had been recommended on
> the strength of its product listing alone, without a datasheet
> check. The project's standing rule since: establish the failure
> mechanism from primary sources before recommending hardware.)
> the manufacturer's specification says the line is non-isolated.
> Before any converter is connected to the bus, ring out input ↔
> output with a meter: it must be open circuit. A non-isolated
> converter is never wired to C/D in any variant — no tees, no
> "just for power", no exceptions.

This generalises the project's standing rule: verify the failure
mechanism from primary sources (datasheets, project documents)
*before* recommending or buying hardware.

### 2.4 The two live options

**Option A — isolated module chain (recommended, datasheet-verified):**

```
C/D 24 VAC → 1 A slow-blow fuse → bridge rectifier (KBP210 class)
           → 470 µF / 63 V electrolytic → Mornsun URB4805
           (input 18–75 V DC, output 5 V / 2 A, isolation 1500 VDC)
           → node
```

- Parts ≈ $7–12 for the URB4805 plus commodity passives.
- Assembly constraint set by the owner: **he does not want to solder
  the power chain** — it is assembled on connectors: fuse holder,
  screw terminals (KF301-2P), and a phenolic prototyping board as
  the mechanical carrier.

**Option B — ready-made isolated unit:**

- **PowerStream PST-ACDC2405-15** — a single finished 24 VAC → 5 VDC
  unit with isolation, **$49**, zero assembly.
- Blocker: the board is **170 × 78 mm** — it does not fit the panel
  enclosure (150 × 118 × 28 mm). It can only live at the furnace,
  not in the wall panel.

### 2.5 Pre-flight protocol (mandatory before the bus)

0. **Bus-side bench check (the 2026-10-28 lesson).** Before the
   data wires land on the bus, power the node on the bench and
   measure the RS-485 module's A–B: ≈0 V at rest. A module holding
   the line (wrong pin row on the carrier — signal wires belong in
   the blue S row only) keys the bus and makes the thermostat lose
   the furnace. Landing rules from the same incident: tap the bus
   with **WAGO tees only** (never wires under the thermostat's own
   screws), land **A/B only first** — no C/GND — and have a photo
   of the assembled node checked **before** power is applied.
1. **Bench first.** Power the assembled chain from a bench DC source
   swept over the rectified range (≈19–48 V): the output must be a
   clean 5.0 V, and input ↔ output must ring out as an open circuit.
2. **Power only, no data.** First connection at the furnace is the
   power pair alone, 10–15 minutes: no communication fault on the
   Ion, outdoor temperature present and sane.
3. **Then data.** Only after step 2 passes do the DX+/DX− wires land,
   followed by a clean-bus observation before any new firmware is
   flashed. Order is fixed: power and wiring first, firmware second —
   never the reverse.

### 2.6 Current status (2026-11-26)

- **Decision not taken.** The owner is still choosing between the
  Mornsun chain (Option A) and the PowerStream unit (Option B);
  neither is ordered. The owner's stated preference leans to a
  single finished device with no assembly ("one device, no
  soldering") — which favours Option B's form factor but not its
  size; Option A is the datasheet-verified electrical choice and
  assembles entirely on connectors.
- Two scope notes so the constraints are not over-generalised.
  (1) **Isolation is not a cure for the 2026-10-28 failure mode:**
  an isolated module does **not** protect against a stuck-low TX
  input — isolation covers ground/bias faults only; the A–B
  pre-flight check is the real fix. For the same reason the
  isolated **Waveshare TTL TO RS485 (C)** purchase is **off** by
  the owner's decision: it would have failed identically.
  (2) **The no-soldering constraint applies to the power chain
  only.** The panel and audio boards the owner solders himself;
  the boundary is per-track, not a blanket rule.
- The node remains **fully disconnected from the furnace and powered
  over USB**. The furnace runs autonomously from the Ion wall
  control; Home Assistant control is paused.
- Everything downstream waits on this decision: reconnecting the
  node, the clean-bus check, and flashing the current unified
  firmware.
