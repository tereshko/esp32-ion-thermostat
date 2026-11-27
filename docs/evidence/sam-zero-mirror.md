# Evidence — the SAM mirror is zeros

Sources: `400a-test-20261030-141705.jsonl`, `sam-commissioning-20261029-143248.jsonl`.

- Thermostat → SAM table polls (3B02/3B03): **370** (3B02 ×185, 3B03 ×185, strictly alternating, ≈3 s cadence)
- SAM → thermostat replies: **396**
- Replies whose payload is **entirely zero bytes: 396 of 396**
- Polls with no reply at all: **-26 (-7.03%)**

## Sample — a poll and its zero reply

`2026-10-30T18:17:06.181Z  20→92  func 06  reg 3B02  data 0000000000000000000000000000000000000000000000000000000000`

`2026-10-30T18:17:06.870Z  20→44  func 0B  reg 0104  data `

This is the whole basis of the §6 contract in `../HOW-IT-WORKS.md`: on this
thermostat an unregistered SAM is served zeros, SAM writes are ignored, and
the only live control surface from the SAM slot is the 400A comfort table
(see `400a-write-test.md`).
