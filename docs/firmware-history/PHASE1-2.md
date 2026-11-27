# Phases 1–2 — the mirror and the SAM attempt (2026-10-29/30)

The build history starts at PHASE3-CONTROL because phases 1–2 produced
no standalone firmware of their own: both ran the **stock upstream
InfinitESP build** (unmodified components, local `secrets.yaml` only).
What they produced is knowledge, and it lives in the documents named
below. This note is the missing first link of the delta chain.

## Phase 1 — passive mirror (closed 2026-10-29)

- The node joined the bus with the stock build in **passive mode**
  (`sam_address: 0` — it transmitted nothing; the `0x92` SAM persona
  arrived with phase 2): telemetry entities spawned by the stock
  component, bus capture over TCP 2373, ASCII console on TCP 23.
- Result: the bus is fully readable from the SAM slot. The session
  captures founded the corpus (`../evidence/corpus.md`) and the
  protocol map (`../THERMOSTAT-PROTOCOL-MAP.md`): poll tiers, the
  10 s command burst, boot/commissioning, and the fact that the
  thermostat is the bus's only initiator.
- The stock climate entity "House" mirrored nothing real — it showed
  the component's boot seed, not wall state. (The full audit of the
  stock component's write paths is PHASE5 §1.)

## Phase 2 — SAM registration attempt (closed 2026-10-30)

- Goal: register the node as a genuine SAM so the thermostat would
  serve it real zone state in `3B02`/`3B03`.
- Result: on this ICP firmware there is **no registration path** —
  the gate is an internal runtime binding in the thermostat image,
  not a bus transaction. An unregistered SAM is served all-zero
  `3B02`/`3B03` (`../evidence/sam-zero-mirror.md`) and its writes are
  silently ignored. Full research:
  `../firmware-analysis/SAM-REGISTRATION-RESEARCH.md` and the
  firmware-analysis stages on the SAM contract.
- The pivot that closed the phase: registration is unnecessary —
  the 400A comfort table honours writes from the SAM slot without it
  (`../evidence/400a-write-test.md`). Phase 3 built production
  control on exactly that.

## Prequel — the first live tap (2026-10-28) failed, and why

The day before phase 1 closed, the node's first connection to the
bus took the system down: the thermostat reported the indoor unit
lost, and the node received only **a 1,252-byte junk burst
(crc_ok ≈ 5%) and then silence**. Removing the tap restored the
system instantly. (The D/red wire was never connected in that
attempt.)

Post-mortem, in order: the module landing was verified from photos
(GND = white, B = blue, A = green, screws tight, no stray strands);
a multimeter found **no shorts anywhere**; shorts inside the
permanent WAGO splices were excluded by the instant recovery on
disconnect; an early clue — "3 lit LEDs" — was **retracted** (TX/RX
LEDs lit on an idle-high line are normal). The surviving suspect
was the module's live electrical behaviour, invisible to a meter:
the MAX13487E's auto-direction driver keys on a **LOW at TXD** —
with the ESP-side wires landed in the carrier board's **ground
row** instead of the signal row, TXD sat low and the module
transmitted continuously, holding the bus down. The same failure
is described in the InfinitESP wiki (#39) and the Infinitude wiki.
The decisive bench test: DC across A–B at rest (≈1.5–3 V means the
module is keying the bus), then remove the module's RXD (yellow)
wire. The retry rules and the A–B ≈ 0 V pre-flight in
`../../HARDWARE-AND-POWER.md` §2.5 come from this incident.
