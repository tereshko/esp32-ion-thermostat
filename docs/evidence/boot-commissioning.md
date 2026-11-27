# Evidence — boot & commissioning (coldstart capture)

Source: `coldstart-20261029-125733.jsonl` (17,600 frames). Timestamps below are UTC as recorded; relative times are from the first frame.

## The furnace speaks first

`2026-10-29T16:57:50.999Z  44→45  func 0B  reg 030A  data `
  decoded: ``

## Milestones

- First thermostat frame, as persona `0x1F`: **+6.0 s**

`2026-10-29T16:57:57.000Z  1F→F1  func 0C  reg 0305  data 000000000000000000000000`

- Handover: first frame from operational persona `0x20`: **+16.7 s**

`2026-10-29T16:58:07.694Z  20→46  func 0B  reg 030A  data `

- First func-0C write of any kind from `0x20` (the SYSTIME broadcast, reg 0202): **+39.1 s**

`2026-10-29T16:58:30.095Z  20→F1  func 0C  reg 0202  data 172803`

- First **addressed** write from `0x20` (to the furnace, reg 0418): **+62.0 s**

`2026-10-29T16:58:52.999Z  20→44  func 0C  reg 0418  data 000000`

- First `0305` demand frame: **+71.65 s**

`2026-10-29T16:59:02.649Z  20→44  func 0C  reg 0305  data 000000000000000000000078`

## Equipment self-identification (0104 replies during the sweep)

`2026-10-29T16:58:05.614Z  44→1F  func 06  reg 0104  data 5641524941424C45205350454544204655524E4143452020000000000000000000000000…`
  decoded: `VARIABLE SPEED FURNACE  ························CESR13*****-04   G80CTL13*****A2·····2821********A213********************`

`2026-10-29T16:58:06.046Z  53→1F  func 06  reg 0104  data 5641522053504420434F4D502056455253494F4E00000000000000000000000000000000…`
  decoded: `VAR SPD COMP VERSION····························CESR13*****-11···HVA960GKA201        5422********3521********************`

The furnace and the outdoor unit name themselves — model strings and serials
come from the equipment, which is why the thermostat firmware needs (and has)
no equipment model database. The evaporator coil the wizard confirmed in the
companion capture (`sam-commissioning-20261029-143248.jsonl`) is the
EN(A,D)4X61, whose stored parameter is 1.69.
