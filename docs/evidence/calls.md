# Evidence — heating and cooling calls

Sources: coldstart segments `04-cool-70F.jsonl` and `06-heat-75-79F.jsonl`.

## Cooling — the 0605 capacity command

- 0605 frames in the cooling segment: **36**; capacity values seen: 0.0 ×3, 5.0 ×33

The call switching on — last idle frames, then the first at full capacity:

`2026-10-29T17:07:01.082Z  20→53  func 0C  reg 0605  data 00000000000001`  → capacity 0.0, call-state byte [4] = 0

`2026-10-29T17:07:11.081Z  20→53  func 0C  reg 0605  data 00000000000001`  → capacity 0.0, call-state byte [4] = 0

`2026-10-29T17:07:31.090Z  20→53  func 0C  reg 0605  data 40A00000010001`  → capacity 5.0, call-state byte [4] = 1

`2026-10-29T17:07:41.093Z  20→53  func 0C  reg 0605  data 40A00000010001`  → capacity 5.0, call-state byte [4] = 1

`2026-10-29T17:07:51.090Z  20→53  func 0C  reg 0605  data 40A00000010001`  → capacity 5.0, call-state byte [4] = 1

## CFM / stage progression (0305 to the furnace; only changes listed)

Cooling segment (ts, CFM, heat stage, cool stage):

- 2026-10-29T17:07:05.999Z — CFM 0, heat stage 0, cool stage 0
- 2026-10-29T17:09:27.116Z — CFM 1232, heat stage 0, cool stage 2
- 2026-10-29T17:10:57.000Z — CFM 1760, heat stage 0, cool stage 2
- 2026-10-29T17:11:37.579Z — CFM 1710, heat stage 0, cool stage 2
- 2026-10-29T17:12:38.000Z — CFM 1660, heat stage 0, cool stage 2

Heating segment (setpoint staircase 75→79 °F at the wall):

- 2026-10-29T17:16:00.128Z — CFM 0, heat stage 0, cool stage 0
- 2026-10-29T17:16:19.999Z — CFM 1166, heat stage 0, cool stage 0
- 2026-10-29T17:17:30.072Z — CFM 384, heat stage 0, cool stage 0
- 2026-10-29T17:18:30.272Z — CFM 384, heat stage 1, cool stage 0
- 2026-10-29T17:19:20.967Z — CFM 0, heat stage 1, cool stage 0
- 2026-10-29T17:20:11.000Z — CFM 1368, heat stage 1, cool stage 0
- 2026-10-29T17:20:31.253Z — CFM 1368, heat stage 2, cool stage 0
- 2026-10-29T17:20:51.233Z — CFM 1617, heat stage 2, cool stage 0

The thermostat commands; the boards execute and protect. The cooling call
runs at capacity 5.0 from its first burst — sustained part-load has never
been observed (open gap B-5 in the guide).
