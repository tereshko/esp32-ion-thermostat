# Evidence — 400A writes from an unregistered SAM are honoured

Sources: the four `400a-test-20261030-*.jsonl` captures of the 2026-10-30 session
(30,975 frames). Full narrative: `../firmware-analysis/400A-TEST-RESULT.md`.

- Func-0C writes to 400A from the SAM node (0x92): **5**
- Func-0x15 exception frames in the whole session: **0**

## The writes (manual row: byte 28 = heat, byte 29 = cool)

`2026-10-30T18:26:49.225Z  92→20  func 0C  reg 400A  data 444C0044891E1E3C50004F001E1E444C0044891E1E444C0044891E1E4E4E0044891E1E`  → manual pair (78, 78)

`2026-10-30T18:26:53.234Z  92→20  func 0C  reg 400A  data 444C0044891E1E3C50004F001E1E444C0044891E1E444C0044891E1E4E4E0044891E1E`  → manual pair (78, 78)

`2026-10-30T18:53:29.279Z  92→20  func 0C  reg 400A  data 444C0044891E1E3C50004F001E1E444C0044891E1E444C0044891E1E4B4E0044891E1E`  → manual pair (75, 78)

`2026-10-30T18:54:17.811Z  92→20  func 0C  reg 400A  data 444C0044891E1E3C50004F001E1E444C0044891E1E444C0044891E1E4B4A0044891E1E`  → manual pair (75, 74)

`2026-10-30T18:58:55.524Z  92→20  func 0C  reg 400A  data 444C0044891E1E3C50004F001E1E444C0044891E1E444C0044891E1E474C0044891E1E`  → manual pair (71, 76)

## What the thermostat answered afterwards (400A poll replies, manual pair)

- 2026-10-30T18:17:20.589Z — manual pair **70/74**
- 2026-10-30T18:22:00.364Z — manual pair **76/78**
- 2026-10-30T18:54:40.729Z — manual pair **68/76**
- 2026-10-30T18:59:21.023Z — manual pair **71/76**

The pair changes exactly when a write lands or the wall re-seeds the slot
(mode/profile change at the wall) — and otherwise holds for tens of minutes
across six consecutive polls. Storage and live consultation: proven.
