# Evidence — anatomy of a command burst

Source: `phase3-validation3-20261103-145755.jsonl`. All frames within ±1.2 s of a
0305 demand frame at 2026-11-03T19:57:56.000Z — one ≈10 s burst, in wire order:

`2026-11-03T19:57:55.542Z  92→20  func 0B  reg 3B02  data `

`2026-11-03T19:57:55.562Z  20→92  func 06  reg 3B02  data 0000000000000000000000000000000000000000000000000000000000`

`2026-11-03T19:57:56.000Z  20→44  func 0C  reg 0305  data 000000000000000000000078`

`2026-11-03T19:57:56.045Z  20→44  func 0C  reg 0403  data 00010100`

`2026-11-03T19:57:56.090Z  20→44  func 0C  reg 0409  data 00010000`

`2026-11-03T19:57:56.135Z  20→44  func 0C  reg 0307  data 00000000`

`2026-11-03T19:57:56.217Z  92→53  func 0B  reg 0304  data `

`2026-11-03T19:57:56.241Z  53→92  func 06  reg 0304  data 0118003C011700F40541000000440000`

`2026-11-03T19:57:57.000Z  20→44  func 0B  reg 0104  data `

`2026-11-03T19:57:57.046Z  44→20  func 06  reg 0104  data 5641524941424C45205350454544204655524E4143452020000000000000000000000000…`

`2026-11-03T19:57:57.079Z  20→53  func 0B  reg 0104  data `

`2026-11-03T19:57:57.125Z  53→20  func 06  reg 0104  data 5641522053504420434F4D502056455253494F4E00000000000000000000000000000000…`

`2026-11-03T19:57:57.159Z  20→44  func 0B  reg 0306  data `

`2026-11-03T19:57:57.175Z  44→20  func 06  reg 0306  data 010000000000C808CA00`

The same cycle's outdoor-unit group follows ≈5.7 s later (timestamps
relative to the 0305 above):

`2026-11-03T19:58:01.702Z  20→53  func 0C  reg 0610  data 00000000`

`2026-11-03T19:58:01.747Z  20→53  func 0C  reg 0612  data 22B80000000000000000`

`2026-11-03T19:58:01.792Z  20→53  func 0C  reg 0605  data 00000000000001`

`2026-11-03T19:58:01.835Z  20→53  func 0C  reg 061A  data 01`

`2026-11-03T19:58:01.880Z  20→53  func 0C  reg 060D  data 00`

`2026-11-03T19:58:01.927Z  20→53  func 0C  reg 061E  data 0F3FD851EC06000000`

`2026-11-03T19:58:01.972Z  20→53  func 0C  reg 060B  data 0104BE00000000`

`2026-11-03T19:58:02.000Z  20→44  func 0C  reg 0414  data 0104BE010320`

The burst is the thermostat's heartbeat, in two groups ≈5.7 s apart:
the furnace group (0305 demand, 0403, 0409, 0307) and the outdoor-unit
group (0605 compressor capacity, 060D call flag, 061E coil parameter,
the constants 0610/0612/061A and the paired 060B/0414), interleaved
with the poll tiers.
