# VERIFY-romfs — independent re-derivation of stage X (ROM filesystem bank)

Verifier: fresh scripts written from the claim text (`/tmp/verify_romfs1.py`,
`/tmp/verify_romfs2.py`), run against the primary artifact only:
`firmware-re/stageB/flat.bin` (15,728,640 B = 0xF00000; base 0x18040000,
FS flat offset 0x7D0100). Stage X's own parsers were read for reference but
not executed; every number below is from the verifier's own parse.

**Headline: no claim REFUTED. All seven claims CONFIRMED; claims 1 and 4
carry the same ±1-byte end convention stage X itself disclosed.**

## Claim 1 — bank span 0x18810100–0x18D40577 (5,440,631 B) — CONFIRMED (±1 convention)

- Byte before the bank (flat 0x7D00FF) is 0xFF; bank content begins exactly
  at 0x18810100 with the root directory (`02 00 00 00 fa 77 7c 17 …`).
- The fonts record walk (claim 4) consumes content through FS+0x530477
  inclusive — i.e. the **last content byte sits at address 0x18D40577**
  (it is the final glyph payload byte, value 0x00). The walk end
  (exclusive) is FS+0x530478 = 0x18D40578, and from there the flat image is
  0xFF padding (flat 0xD00578 → 0xEFFEF8), then the 4-byte trailer
  `92 b6 cc 87`, then 0xFF/0x00 to the flat end — matching stage X §0.
- So the span endpoints are exact. The byte count is convention-dependent:
  5,440,631 B under stage X's exclusive-length slicing (region length
  0x530477), 5,440,632 B counting the last payload byte inclusively.
  This is precisely the off-by-one stage X §3/§6 disclosed vs stage H.

## Claim 2 — root directory format — CONFIRMED (exact)

Own parse of the root:

- `u32le @0x00 = 2` ✓
- Root id @0x04 = `fa777c17a0c90ca4`; u32be @0x0C = 0x04000200.
- Entry 1 @0x10: UTF-16LE name `\images`, 8-byte section id at 0x20 =
  `db61d30bd34ba2f4` ✓
- Entry 2 @0x28: UTF-16LE name `\fonts`, section id at 0x36 =
  `6e459b22438530d8` ✓
- Directory ends at FS+0x3E ✓.
- Each section id occurs **exactly twice** in the bank: in the directory
  and at its section start (images id at FS+0x16B8C, fonts id at
  FS+0x3E89B8) — sections are self-identifying, as stage X said.
- Derived section layout (from id scan, not from stage X constants):
  root = 93,068 B (0x16B8C), `\images` = 4,005,420 B, `\fonts` starts at
  FS+0x3E89B8. Each section opens with its 8-byte id + u32be 0.

## Claim 3 — record format + 0x80000000 flag — CONFIRMED

- The 12-byte header `{u16le fa, u16le fb, u32be 0, u32be count}` +
  `count×4` payload is proven constructively by the fonts walk (claim 4):
  7,251 consecutive records consume the section with no resync, every
  header's zero field = 0 and every count ≤ 417.
- The 0x80000000 flag: root-section index entries are BE u32
  `0x80000000 | word_offset`; masked value × 4 = byte offset into
  `\fonts` (verified exhaustively, claim 4). Precision note: the flagged
  entries live in the **root** section and point into `\fonts`; they are
  not inside `\fonts` itself. The claim's wording ("marks glyph-index
  tables in \fonts") is consistent with that reading.

## Claim 4 — inventory + glyph index verification — CONFIRMED (±1 end)

- Root region = 93,068 B ✓ (claim 2 derivation).
- Index tables in root: my run-detection (maximal runs of flagged BE u32,
  length ≥ 8) finds **33 tables, 7,251 entries total** ✓. (Segmentation
  into tables depends on the run rule; sizes found: mostly 211–226, plus
  422/426/432 merged pairs and short 17/20/125/217 runs — the totals,
  which are what the verification rests on, are exact.)
- Fonts walk: **7,251 glyph records** ✓. Header distributions reproduce
  stage X exactly: fa {132:1975, 133:1686, 134:1893, 135:1697};
  fb {58:23, 59:430, 60:6796, 67:2}; count min 1, max 417, total
  313,780 u32 items.
- **Index verification: table[k]×4 == byte offset of glyph record k for
  all 7,251 k — 0 mismatches** ✓ (independently re-walked).
- Measured end: the walk terminates at **FS+0x530478** (address
  0x18D40578, exclusive) — 1 byte past the 0x530477 region length, exactly
  the ±1 the claim allows. Consequently the walked `\fonts` content is
  1,342,144 B vs the 1,342,143 B region-based figure in the claim — the
  same single byte, not a second discrepancy.

## Claim 5 — \images walk diverges after record 1 — CONFIRMED

- Strict sequential walk of `\images` (same header rule): record 0 at
  FS+0x16B98 parses exactly as stage X verified — `{fa=132, fb=67, 0,
  count=16320}`, and I confirmed its 16,320-u32 payload is **entirely
  0xFFFFFFFF** ✓.
- One further header-shaped record is consumed at FS+0x26AA4 (its field
  values — fa=14468, fb=180 — are already implausible as a record header;
  stage X describes this offset's content as pixel data). The walk then
  **fails at FS+0x27650** on a non-header (`z = 0xFF000002`) — the exact
  offset stage X independently identified as ARGB pixel data
  (`ff353535…`). A strict record walk therefore does not survive the
  section; divergence point reproduced. The claim's "after record 1"
  matches: records 0 and the header-shaped 1 are consumed, the third
  header position is not a record.

## Claim 6 — no hidden technical content — CONFIRMED

Own scans over the whole bank:

- Float 1.69: BE `3FD851EC` **0 hits**, LE `EC51D83F` **0 hits**,
  float64 BE/LE also 0 ✓.
- Protocol/technical strings: `SAM01` 0, `Clarinox` 0, `Carrier` 0,
  `Infinity` 0, `http` 0, `<?xml` 0, ASCII `0305`/`0605` 0 ✓.
- Text: ASCII printable runs ≥8 chars = 2,026 raw; with stage X's filter
  (≥1 letter) = **1,698 — exactly stage X's number**. Every sampled hit is
  graphics noise: glyph-outline coordinate sequences (e.g.
  `fUWZfTWZfTVZ…` descending letter walks) and repeated-pattern runs.
  Pure letter runs ≥5 (640) are the same noise class — no words, no
  sentences, no markup anywhere.
- UTF-16LE strings ≥3 chars = **123 — exactly stage X's number**; the
  only meaningful entries are `\images` and `\fonts` (remainder are
  bitmap runs: `oooooooo`, `xxxxxxl`, repeated-pattern strings — as stage
  X listed). UTF-16BE scan (133 hits) likewise yields only the two names
  plus noise. No third name exists in either encoding.

## Claim 7 — entropy + codec candidates — CONFIRMED (exact)

- Entropy, aligned 16 KB windows (333 windows): **max 7.3121 bits at
  FS+0x118000** — same value (7.31) and same offset as stage X;
  **0 windows ≥ 7.5** ✓. Robustness check with sliding windows (4 KB
  step): max 7.3246, still 0 windows ≥ 7.5.
- Header-shaped candidates (offsets of gzip magic `1F 8B` or zlib headers
  `78 01/5E/9C/DA`): **exactly 93** ✓. Decompression attempted at every
  candidate with wbits {15, −15, 31}: **0 successes** ✓.
- Raw-deflate sweep at 4 KB boundaries: 1,328 attempts, 0 successes ✓.
- Magic census: PNG 0, GIF 0, ZIP 0, LZ4 frame 0, OTTO 0, WOFF 0;
  gzip magic 3 isolated hits inside bitmap payloads (all inside the 93
  failed candidates) ✓.

## Summary table

| # | Claim | Verdict |
|---|---|---|
| 1 | Bank span 0x18810100–0x18D40577, 5,440,631 B | CONFIRMED — endpoints exact; count is the exclusive-length convention, last content byte at 0x18D40577 (inclusive total 5,440,632 B) |
| 2 | Root dir: u32le count 2, UTF-16LE names, ids db61…/6e45… | CONFIRMED — byte-exact, ids occur exactly twice each |
| 3 | 12-byte record header + count×4; 0x80000000 flag | CONFIRMED — flag lives on root index entries pointing into \fonts |
| 4 | Root 93,068 B, 33 tables, 7,251 records, index check 0 mismatches | CONFIRMED — walk end measured FS+0x530478 (the allowed ±1) |
| 5 | \images 4,005,420 B; strict walk diverges after record 1 | CONFIRMED — record 0 all-white verified; walk fails at FS+0x27650 |
| 6 | No readable text, no 1.69, no protocol strings | CONFIRMED — 1.69 BE/LE/f64 = 0; only names are \images, \fonts |
| 7 | Max entropy 7.31, none ≥7.5; 93 candidates → 0 | CONFIRMED — max 7.3121 @FS+0x118000; 93 candidates, 0 decompress |

Stage X's verdict stands in full: the bank contains only UI assets
(directory, glyph index, glyph records, bitmap/RLE data, metric tables) —
no configuration, protocol data, text resources or code, and no compressed
blob of any tested family.
