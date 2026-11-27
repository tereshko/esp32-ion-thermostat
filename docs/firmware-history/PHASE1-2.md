# Phases 1–2 — the mirror and the SAM attempt (2026-10-29/30)

The build history starts at PHASE3-CONTROL because phases 1–2 produced
no standalone firmware of their own: both ran the **stock upstream
InfinitESP build** (unmodified components, local `secrets.yaml` only).
What they produced is knowledge, and it lives in the documents named
below. This note is the missing first link of the delta chain.

## Phase 1 — passive mirror (closed 2026-10-29)

- The node joined the bus as a SAM at `0x92` with the stock build:
  telemetry entities spawned by the stock component, bus capture over
  TCP 2373, ASCII console on TCP 23.
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
  silently ignored. Full research: `../research/` (SAM registration
  research) and the firmware-analysis stages on the SAM contract.
- The pivot that closed the phase: registration is unnecessary —
  the 400A comfort table honours writes from the SAM slot without it
  (`../evidence/400a-write-test.md`). Phase 3 built production
  control on exactly that.
