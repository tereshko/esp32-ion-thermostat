# Evidence — the SAM mirror is zeros

Sources: `400a-test-20261030-141705.jsonl`, `sam-commissioning-20261029-143248.jsonl`.
Direction: the node (`0x92`, acting as SAM) polls the thermostat (`0x20`);
the thermostat replies.

- SAM → thermostat polls (3B02/3B03): **396** (3B02 ×198, 3B03 ×198,
  strictly alternating, ≈3 s cadence)
- Thermostat → SAM replies: **370**
- Replies whose payload is **entirely zero bytes: 370 of 370**
- Polls with no reply at all: **26 (6.6%)**

## Sample — a poll and its zero reply

`2026-10-30T18:17:12.000Z  92→20  func 0B  reg 3B02  data ` (empty payload — a read)

`2026-10-30T18:17:12.018Z  20→92  func 06  reg 3B02  data 0000000000000000000000000000000000000000000000000000000000` (29 B, all zero)

This is the whole basis of the §6 contract in `../HOW-IT-WORKS.md`: on this
thermostat an unregistered SAM is served zeros, SAM writes are ignored, and
the only live control surface from the SAM slot is the 400A comfort table
(see `400a-write-test.md`).
