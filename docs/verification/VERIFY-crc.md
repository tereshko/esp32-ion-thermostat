# VERIFY-crc — CRC and frame integrity (stages AA / SC)

Independent re-derivation from primary artifacts only: flat image
`firmware-re/stageB/flat.bin` (MD5 `6dc76d180037d563d5d625efc8b8b5f7`, byte-identical to
`firmware-re/stageAA/flat.bin`; base 0x18040000, 15,728,640 B), Ghidra dumps in
`firmware-re/stageAA/out/`, Series C image `firmware-re/stageSC/region0_60100000.bin`
(base 0x60100000), captures in `traces/` and `traces/external/gofinity-bootup.bin`.

Method note: every numeric test below uses a **bit-by-bit reference CRC written from the
polynomial definition** (reflected, poly 0xA001, no tables anywhere). The reference was
anchored before use: with init 0 it reproduces the published CRC-16/ARC check value
`CRC("123456789") = 0xBB3D`. Scripts: `/tmp/verify_crc_p1.py`, `/tmp/verify_crc_p2.py`,
`/tmp/verify_crc_p3.py` (part 3 run under the stageSC capstone venv).

---

## Claim 1 — CRC routine is FUN_180a42dc, nibble-wise, tables via pool, final byte-swap

**CONFIRMED.**

- Ghidra dump `stageAA/out/fun_180a42dc.txt`: body 0x180a42dc..0x180a4371; decompile is
  exactly the claimed loop — `crc = crc>>8 ^ *(PTR_DAT_180a4560 + ((crc^b)&0xF)*2) ^
  *(PTR_DAT_180a4564 + (((crc^b)&0xF0)>>4)*2)`, counter over `param_2` bytes, and the
  return is `CONCAT11((byte)crc, crc._0_1_)`, i.e. a byte swap of the final CRC.
- Raw image reads (mine): pool word @0x180A4560 = **0x182B598C**, @0x180A4564 =
  **0x182B59AC** — exactly as claimed.
- Tables extracted raw (BE u16 ×16): A @0x182B598C =
  `0000 C0C1 C181 0140 C301 03C0 0280 C241 C601 06C0 0780 C741 0500 C5C1 C481 0440`;
  B @0x182B59AC =
  `0000 CC01 D801 1400 F001 3C00 2800 E401 A001 6C00 7800 B401 5000 9C01 8801 4400`.
  These are the canonical A001 nibble tables (A = byte-table[0..15], B = byte-table[j<<4]);
  the decomposition `bytetab[(j<<4)|i] == A[i]^B[j]` holds for all 256 entries against a
  byte table regenerated bit-by-bit from the polynomial.
- Caveat of scope: the body *bounds* (…–0x180a4371) are taken from the Ghidra dump; the
  algorithm, pointers, tables and swap were each re-derived from raw bytes / numeric
  identity, not from report prose.

## Claim 2 — equals standard reflected CRC-16 poly 0xA001, init 0

**CONFIRMED.** The image-table nibble form vs the bitwise reference: **5000/5000** random
buffers (lengths 0–299, seed 20261126) and **500/500** with random non-zero inits
(the routine as built starts at 0; the form itself is init-agnostic).

## Claim 3 — wire verification: gofinity 1532/1532; own corpus 101352/101352

**Gofinity half: CONFIRMED. Own-corpus half: count CONFIRMED, wire-match UNVERIFIABLE
from the corpus as recorded.**

- Gofinity: my own parse of `traces/external/gofinity-bootup.bin` (length byte at +4,
  frame total = len+10) yields **1532 frames consuming exactly 36,141/36,141 bytes**;
  bitwise CRC over each frame body equals the 2-byte trailer read little-endian on
  **1532/1532**. (Read big-endian it matches only 19/1532 — coincidence level — so the
  wire order is unambiguously LE.)
- Own corpus recount (mine): 19 JSONL files (`traces/*.jsonl` 83,755 lines +
  `traces/segments/*.jsonl` 17,600 lines) = 101,355 non-empty lines, of which **101,352
  parse as JSON records** — the claimed total is exactly the parsed-record count.
- However: **all 101,352 records have exactly the field set
  {ts, src, dst, func, reg, data} — no CRC bytes were ever recorded.** A wire-CRC match
  on the own captures therefore cannot be tested from this corpus at all. The stage-AA
  artefact (`stageAA/out/crc_test.txt`, its script §3) in fact only demonstrated
  nibble==std *self-consistency on reconstructed bodies*, which follows trivially from
  Claim 2 and is not wire evidence. The CRC's wire correctness for this bus rests on the
  gofinity proof above (same dialect, 1532/1532), not on a 101,352-frame wire check.
  Any retelling of the claim as "own-capture wire CRC verified 101352/101352" overstates
  the evidence; the correct statement is "101,352 own-capture records recounted;
  wire CRC unverifiable from JSONL (no CRC field); gofinity wire proof 1532/1532".

## Claim 4 — caller census: BE32 once; two call sites (BSR in builder; computed jsr via slot 0x180a5ac8)

**CONFIRMED.**

- Whole-image byte search (mine, unaligned): BE32 `18 0A 42 DC` occurs **exactly once,
  at 0x180A5AC8** — the descriptor slot itself (word read back @0x180A5AC8 =
  0x180A42DC). LE32 form occurs **zero** times.
- Whole-image scan of aligned halfwords for BSR (0xB…) / BRA (0xA…) with target
  0x180A42DC: **exactly one BSR, at 0x180A484A** (halfword 0xBD47, disp −697 →
  0x180A484A+4−1394 = 0x180A42DC), inside builder FUN_180a44ee; **zero BRA**.
  BSRF/register-indirect forms are not statically resolvable and are outside the claim.
- Computed site independently corroborated: halfword @0x180A5876 = 0xD394 =
  `MOV.L @(0x94,PC),R3` → PC-aligned (0x180A587A & ~3 = 0x180A5878) + 0x250 =
  **0x180A5AC8**, i.e. R3 is loaded with the descriptor slot's contents (= the function
  address); Ghidra records the following instruction @0x180A5878 as COMPUTED_CALL and
  the read of the slot from 0x180A5876 (`stageAA/out/dumpAB.txt`,
  `fun_180a42dc.txt` refs: 180a484a UNCONDITIONAL_CALL, 180a5878 COMPUTED_CALL,
  180a5ac8 DATA — consistent with the raw census).

## Claim 5 — builder appends high byte of swapped return first → true CRC little-endian on the wire

**CONFIRMED** (both halves).

- Code half (`stageAA/out/dumpAB.txt`, FUN_180a44ee decompile): after
  `uVar1 = FUN_180a42dc(buf, len)` the builder stores
  `buf[len] = (char)(uVar1 >> 8)` then `buf[len+1] = (char)uVar1`. Since FUN_180a42dc
  returns the byte-swapped CRC (Claim 1), the first stored byte is the true CRC's **low**
  byte and the second its high byte — little-endian on the wire.
- Wire half: gofinity trailers match the CRC read little-endian on 1532/1532 and
  big-endian on only 19/1532 (Claim 3) — the captured frames show exactly this order.

## Claim 6 — Series C twin FUN_6012F160 verified 1000/1000

**CONFIRMED** (re-run independently; the original stage's own test used 500 buffers —
mine used 1000, verdict unchanged).

- My own Thumb disassembly (capstone, `region0_60100000.bin`) of FUN_6012F160: prologue
  copies two 32-byte tables from pool-pointed sources (pool @0x6012F23C = 0x6084F2E0,
  @0x6012F240 = 0x6084F300) onto the stack, CRC cell initialised to 0, loop computes
  `x = crc ^ byte; crc = (crc>>8) ^ A[x&0xF] ^ B[(x>>4)&0xF]` (stack-table loads at
  −0x30/−0x50 offsets), and the tail (0x6012F21A–0x6012F230) returns
  `((crc&0xFF)<<8) | (crc>>8)` — the same byte swap as 4.79.
- Tables @0x6084F2E0 / @0x6084F300 (LE u16 ×16) are **byte-identical to the 4.79
  tables** of Claim 1 and satisfy the same 256-entry decomposition.
- Random test (mine): Series C nibble form vs bitwise reference = **1000/1000**
  (lengths 0–299, seed 6012).

---

## Summary

No claim is REFUTED. Claims 1, 2, 4, 5, 6 are CONFIRMED outright. Claim 3 splits:
gofinity 1532/1532 CONFIRMED by an independent parse + bitwise CRC; the own-corpus
total 101,352 is CONFIRMED as a record count, but a *wire* CRC verification over the
own captures is UNVERIFIABLE — the JSONL corpus contains no CRC bytes (field set
{ts,src,dst,func,reg,data} on all 101,352 records), and the underlying stage-AA test
only showed nibble==std consistency on reconstructed bodies.
