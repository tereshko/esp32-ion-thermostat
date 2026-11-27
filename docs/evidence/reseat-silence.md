# Evidence — 36 s without the thermostat (reseat capture)

Source: `sam-reseat-20261029-151123.jsonl` — the thermostat was lifted off its
wall plate for ≈36 s while everything else stayed powered.

- Longest silence from `0x20`: **48.9 s** (2026-10-29T19:11:35.144Z →
  2026-10-29T19:12:23.999Z). This window counts the thermostat's own
  reboot: for its last ≈13 s the unit was already back on the bus as its
  boot persona `0x1F` (108 of the 133 frames below). The gap with **no
  thermostat persona at all** — what the equipment actually experienced —
  is the ≈36 s of the physical reseat.
- Frames on the bus during that silence: **133**, by source: 0x44 ×6,
  0x92 ×16, 0x53 ×3, 0x1F ×108
- Fault frames from the equipment during the silence: **none** — no error
  traffic, no reaction from furnace or outdoor unit.

Last thermostat frame before the silence:

`2026-10-29T19:11:35.144Z  20→44  func 0B  reg 0413  data `

First `0x20` frame after (the discovery sweep resuming):

`2026-10-29T19:12:23.999Z  20→58  func 0B  reg 030A  data `

This capture is the measured lower bound of the failover window in the guide
(§9): the equipment tolerates **more than 36 s** of thermostat silence. The
upper bound is the outdoor unit's ≈2 min standby after the last valid message.
