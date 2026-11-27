# VERIFY — Series C probe (FIRMWARE-ANALYSIS-SERIESC.md)

Independent re-derivation from primary artifacts only: the original
`firmware-re/versions/extract/0200/TSTAT/CINF0200.BEX`, the decoded
`firmware-re/stageSC/region0_60100000.bin` / `seriesC_flat.bin`, the
4.79 flat image `firmware-re/stageB/flat.bin`, and the wire capture
`traces/external/gofinity-bootup.bin`. Report prose was used only to
locate targets; every number below was recomputed. Date: 2026-11-26.

## Claim 1 — BEX identity: size, hashes, span, CESR******-**.00 — **CONFIRMED**

- File size recomputed: **8,896,064 bytes** (0x87BE40) — exact.
- MD5 recomputed: `7eb779687c9db1a500e79dc1ddb84c46` — matches claim prefix `7eb77968…`.
- SHA-256 recomputed: `820df3f37fcc5eae55d9d203ba0f52d4851eb5a5e86c0a3709827d42a6f3ae3d` — matches claim prefix `820df3f3…`.
- Span: decoded region0 file is **8,662,808 bytes = 0x842F18**, exactly
  `0x60942F18 − 0x60100000`; region base 0x60100000, end-exclusive 0x60942F18 — exact.
- `CESR******-**.00`: present **once** in the BEX at offset 0x87BDC9, inside the
  trailer `!!START_OF_CODE!CESR******-**.00` (in the full flat image at
  0x60CFFE10, trailer start 0x60CFFE00). Note: the string is **not** inside
  region0 (the code region carries only `CESR131755` @0x608B38D0, in a
  Sparkplug-style record) — the version suffix lives in the container trailer,
  which is what the claim asserts.

## Claim 2 — Not SH-2A: Cortex-M vector table — **CONFIRMED**

First words of region0, parsed little-endian by hand:

| slot | value | reading |
|---|---|---|
| [0] initial SP | `0x80800000` | top of SRAM-class address, not code |
| [1] reset | `0x60100331` | in-image address, bit0 = 1 (Thumb) |
| [2] NMI | `0x6010042D` | odd (Thumb) |
| [3..6] faults | `0x6025433F / 49 / 53 / 5D` | odd (Thumb) |
| [7..10] reserved | `0` | Cortex-M reserved slots, zero as architected |
| [11] SVCall | `0x60121281` | odd |
| [14] PendSV | `0x601212B1` | odd |
| [15] SysTick | `0x60181DB5` | odd |

Every populated handler entry is odd and in-image; reserved slots are zero.
This is a textbook Cortex-M (Thumb-2, LE) vector table and is incompatible
with an SH-2A layout. The BEX container header corroborates: at BEX offset
0x10 the same vector words appear (`00 00 80 80 31 03 10 60 …`).

## Claim 3 — Strings: "CCN Task", Sparkplug/broker present, Clarinox absent — **CONFIRMED**

- `CCN Task` — found @0x6089E438, inside a task-name table (`…Touch Task,
  CAT Task, CCN Task, NVM Task, System C…`).
- `spBv1.0` — found @0x608B0EF0 (context: `WallCtrl\0 spBv1.0\0 %s/%s/%s/%s/%s`).
- `mqtt.res.carrier.io` — found @0x608B0F54 (in the Sparkplug topic table
  next to NDEATH/NBIRTH/DBIRTH/NCMD/DCMD records).
- `Clarinox` — **zero** occurrences in region0 and in the whole flat image:
  ASCII (any case, case-insensitive scan = 0) and UTF-16LE (both cases = 0).
  `SoftFrame` likewise zero in both encodings.

## Claim 4 — Directory 72 entries; descriptors ≈243 — **CONFIRMED**

- Directory @0x608AFBD0 parsed independently as 8-byte records
  `{u16 id, u16 type, u16 first_field, u16 field_count}`: exactly **72**
  records, terminated by a zero record @0x608AFE10 (72 × 8 = 0x240;
  0x608AFBD0 + 0x240 = 0x608AFE10 ✓). First record id 0x0102, last 0x5703.
- Descriptors @0x608AFEC0 (16-byte records): the directory's field space is
  exact — Σ field_count over the 72 records = **243**, first_field indices run
  0…242 (last record: first_field 242, count 1). The claim's "~243" is in fact
  exactly 243 by the directory's own arithmetic.

## Claim 5 — Builder, walkers, CRC FUN_6012F160 — **CONFIRMED** (one nuance on "7 kinds")

**Builder FUN_6012B7FC** — exists at the address; my own Thumb-2 disassembly
(Capstone) shows: header assembled from a runtime device record; kind byte
dispatched first by header variant (kinds 0 / 1–2 / 3–5 / 6), then by a
6-entry jump table @0x6012B900 (targets 0x6012B92F, B941, B97F, B9D5, B919,
B9E7) on (kind − 1) ∈ 0…5. The six frame-producing cases assign func bytes
**0x0B** (len 11), **0x0C** (walker E4F4), **0x06** (walker E308), **0x06**
(len 9, no walker), **0x15** (len 9), and **raw 0x00** (len 1, CRC append
skipped by an explicit kind == 6 test @0x6012B9FE). Tail: CRC via wrapper
FUN_602369B4 over the assembled frame, return value appended high byte then
low byte (the CRC function byte-swaps, so the wire order is true-CRC
little-endian), then transmit FUN_6012B7BC.
*Nuance:* the kind argument domain is 0…6 (seven values, as the report
states), but only kinds 1–6 produce frames through the jump table; kind 0
falls through both dispatches to the valid-flag-clear path and emits no
frame in this function as read. The "7 frame kinds" phrasing is the
report's; the six producing kinds + kind-0 domain are what the code shows.

**Walkers** — both exist at the claimed addresses and are called from the
builder: FUN_6012E4F4 (BL @0x6012B960, kind-0x0C case) iterates directory
records with stride 8 (`index << 3`) and field descriptors with stride 16
(`index << 4`), checks the directory record's validity flag (byte +2 & 2),
special-cases record[0] == 0x20 via lookup FUN_6012D734, copies bound
variables via FUN_60263930 / FUN_60235FDE. FUN_6012E308 (BL @0x6012B9B6,
kind-0x06 case) iterates records of stride 120 bytes
(((i<<4)−i)<<3) for i = 0…0x11 (18 records) — the canned-payload serve path.

**CRC FUN_6012F160** — disassembly matches the claim instruction-for-
instruction: prologue copies two 32-byte blocks to the stack from literal
pools @0x6012F23C → **0x6084F2E0** and @0x6012F240 → **0x6084F300**; loop
state init **0** (strh 0 @[r7,#0x56]); per byte
`crc = (crc >> 8) ^ A[(crc^b) & 0xF] ^ B[((crc^b) >> 4) & 0xF]` (lo-nibble
load from the A stack copy, hi-nibble load from the B stack copy); return
byte-swapped `((crc & 0xFF) << 8) | (crc >> 8)`.
Table bytes extracted from the image: A == regenerated reflected-A001
entries tab[0..15] exactly; B == tab[j<<4] exactly (and B ≠ tab[16..31]).
A full byte-wise A001 table also exists @0x608B1F1C and matches all 256
regenerated entries.
Numerical verification (my code, tables taken from the Series C image):
- random buffers: extracted algorithm == standard reflected A001, init 0
  (modulo the documented final byte-swap) — **3000/3000**.
- real wire frames (gofinity bootup, Series B bus; framing: length byte at
  offset 4, total = len + 10; wire CRC = last 2 bytes LE): **1532/1532**
  frames match, consuming all 36,141 bytes exactly. The Series C algorithm
  is byte-identical to the Series B wire CRC.

## Claim 6 — Coil DB is the LE twin; EN(A,D)4X61 = 1.69 — **CONFIRMED**

- String `EN(A,D)4X61` occurs once in region0 @0x608B270C. The record
  pointing to it sits @**0x608B30D8**: `{LE32 ptr = 0x608B270C, LE f32 bytes
  EC 51 D8 3F}` = **1.69** (float32 1.6900000572). This is the last record of
  the 32-record array @0x608B2FE0 (0x608B2FE0 + 31×8 = 0x608B30D8 ✓).
- An independent scan for all `{ptr→pattern-string, f32}` records with
  f32 == 1.69 found exactly two: `CNPV*61` and `EN(A,D)4X61` — mirroring
  stage K's 4.79 finding of exactly two 1.69 words.
- Endianness cross-check: Series C image contains exactly **2** LE
  float-1.69 byte patterns and **0** BE; the 4.79 flat image contains
  exactly **2** BE and **0** LE. Same `{string-ptr, param}` 8-byte record
  format, byte-swapped — the LE-twin claim holds in both directions.

## Claim 7 — The 4.79 lead: CRC table pair @0x182B598C/0x182B59AC before "CCN" — **CONFIRMED**

In `firmware-re/stageB/flat.bin` (base 0x18040000), read big-endian:
- @0x182B598C: 16 BE u16 = `0000 C0C1 C181 0140 C301 03C0 0280 C241 C601 06C0
  0780 C741 0500 C5C1 C481 0440` == reflected-A001 tab[0..15] exactly.
- @0x182B59AC (+0x20): 16 BE u16 == tab[j<<4] exactly.
- @0x182B59CC (+0x20 again): bytes `43 43 4E 00` = **`CCN\0`**, followed by zeros.
- The 4.79 BE tables are value-identical to the Series C LE tables of
  claim 5 (A79 == A_SC, B79 == B_SC). The lead stage AA followed is real,
  at the exact addresses, in the exact layout claimed.

## Summary

| # | Claim | Verdict |
|---|---|---|
| 1 | BEX size/hashes/span/CESR******-**.00 | CONFIRMED (all values exact) |
| 2 | Cortex-M vector table, SP 0x80800000, reset 0x60100331 | CONFIRMED |
| 3 | "CCN Task", spBv1.0, mqtt.res.carrier.io present; Clarinox absent | CONFIRMED |
| 4 | Directory 72 entries; ~243 descriptors | CONFIRMED (243 exact by field arithmetic) |
| 5 | Builder FUN_6012B7FC, walkers E4F4/E308, CRC FUN_6012F160 nibble A001 init 0 | CONFIRMED (nuance: 6 frame-producing kinds, kind domain 0…6; CRC 3000/3000 random + 1532/1532 wire frames) |
| 6 | Coil DB LE twin, EN(A,D)4X61 = 1.69 @0x608B30D8 | CONFIRMED |
| 7 | 4.79 table pair @0x182B598C/AC (BE) before "CCN" @0x182B59CC | CONFIRMED |

No claim is REFUTED or UNVERIFIABLE. The only wording-level correction:
claim 5's "7 frame kinds" — the builder's kind domain is 0…6, but the jump
table produces frames for kinds 1–6 only (funcs 0x0B / 0x0C / 0x06 / 0x06 /
0x15 / raw-0x00); kind 0 emits no frame in FUN_6012B7FC as read.
