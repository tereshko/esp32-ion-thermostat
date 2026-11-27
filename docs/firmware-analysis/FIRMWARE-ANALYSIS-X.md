# FIRMWARE-ANALYSIS-X — ROM filesystem inventory (the last unsearched space)

Stage X closes the one region stages H and K left unexamined: the ROM resource
filesystem bank. Stage H identified the region and its directory names but did not
parse it; stage K confirmed the data is uncompressed but left a residual caveat
("if some resource file used a non-deflate codec, its content is not covered").
This stage parses the FS structure, inventories every named entry and every
record class, content-checks all non-graphics structures, and closes the codec
caveat. **Verdict up front: the bank contains only UI assets — a directory, a
glyph index, font glyph records, bitmap records and UI metric/attribute tables.
No configuration, no protocol data, no text resources, no code.**

## 0. Layout used (reconciliation)

- Worked on `firmware-re/stageB/flat.bin` (MD5 `6dc76d180037d563d5d625efc8b8b5f7`,
  15,728,640 B; stage H's copy is byte-identical). Flat offset = address −
  0x18040000, the layout of stages B–N.
- The versions report's "ROM FS bank at 0x18810100" is in the same decoded
  address space — consistent, no conflict. The bank exists only in the decoded
  layout; the distribution file `BINF0479_Carrier.hex` (10,188,916 B) is the
  encoded container stage B decoded.
- FS bank: **0x18810100–0x18D40577**, 0x530477 = 5,440,631 B (flat offsets
  0x7D0100–0xD00577). After the bank: one 0x00 byte, then 0xFF padding to the
  end of the flat image (plus the image's own 4-byte trailer `92 b6 cc 87`
  near flat end — not part of the FS). [FACT — byte census, §5]

## 1. FS format [FACT, dual-verified: byte parse + code xref]

Container structure, three sections in one bank:

| Section | FS offset | Address | Size | Content |
|---|---|---|---|---|
| root | 0x000000 | 0x18810100 | 93,068 | directory + glyph index + metric tables |
| `\images` | 0x016B8C | 0x18826C8C | 4,005,420 | bitmap records, RLE streams, attribute tables |
| `\fonts` | 0x3E89B8 | 0x18BF8AB8 | 1,342,143 | glyph records |

**Root directory** at FS+0x00:

- `u32le count = 2` @0x00.
- Root id, 8 bytes @0x04: `fa 77 7c 17 a0 c9 0c a4`; one further u32 @0x0C
  (`04 00 02 00` as stored; semantics unresolved).
- Per entry: UTF-16LE NUL-terminated name, then an 8-byte **section id**:
  - `\images` @0x10 → id `db61d30bd34ba2f4`
  - `\fonts` @0x28 → id `6e459b22438530d8`
- Directory ends at FS+0x3E (2 bytes padding to 0x40).

**Section ids are content ids, stored twice**: each section's data begins with
its own 8-byte id (images @FS+0x16B8C = `db61d30b…`, fonts @FS+0x3E89B8 =
`6e459b22…`), matching the directory entries exactly. [FACT — byte compare]

**There are no other names.** An exhaustive UTF-16LE scan of the bank finds
exactly two meaningful names (`\images`, `\fonts`); an ASCII scan finds no words
at all (§4). Files inside sections are **unnamed records**, reached by index —
there is no per-file name table to inventory beyond the two directory entries.

**Runtime access** [FACT — Ghidra, `firmware-re/stageX/out/fshunt.txt`]:
function FUN_1805261a (in the code island at 0x18052410–0x18052CBC, next to the
stage-N BUYPASS CRC routine) returns a section base from a path string: NULL →
0x18810100 (root), path whose UTF-16 char at +2 is `'f'` (0x66, i.e. `\fonts`)
→ 0x18BF8AB8, `'i'` (0x69, i.e. `\images`) → 0x18826C8C. The three bases are
literal-pool constants at 0x18052744/48/4C. The function is referenced only
through a vtable-like struct at 0x183C66E0 (with FUN_18052654 and stub
FUN_18052618) — the UI framework reaches the FS through that interface; no
other code in the image references the bank base.

**Record format** (fonts, proven §3; images, same family §2): 12-byte header
`{u16le fa, u16le fb, u32be 0, u32be count}` followed by `count` × 4 bytes of
payload. Each section starts with a 12-byte section header (8-byte id + u32 0)
before its first record.

**The 0x80000000 flag**: glyph-index entries are BE u32 `0x80000000 | x` where
`x` is an offset **in u32 words** into the `\fonts` section (§3). The flag bit
marks a valid index entry (offset present); offsets are word-granular because
all records are 4-byte aligned.

## 2. `\images` section (4,005,420 B)

Content classes found by structure scan (full census in
`firmware-re/stageX/out/inventory.txt`):

- **Bitmap records** in the family format. Record 0 fully verified: section
  header, then header `{fa=132, fb=67, 0, count=16320}` + 16,320 u32 payload =
  32,640 pixels, **every u32 = 0xFFFFFFFF** (opaque white, ARGB8888 layout) —
  a blank/white bitmap. Record 1 begins at FS+0x26AA4 (payload dominated by
  0x007F007F words at its head).
- **ARGB pixel data** in payloads: e.g. at FS+0x27650 the repeating unit is
  `ff` + RGB (`ff353535`, `ffcbcbcb`, …) — 32-bit pixels with 0xFF alpha.
- **RLE-like streams**: long runs and opcode-like `ff01/ff02/ff03` markers in
  payload areas (e.g. around FS+0x6C4B2) — a graphics RLE, i.e. compressed
  *bitmaps*, not compressed files (see §5).
- **Attribute tables**: 11 runs, 217 records total, of 16-byte records
  `{u32 a, u32 0, u32 b, u32 0xFFFFFFFF}` (a ≈ 8–13, b increasing ≈ 0x3C, 0x40,
  0x42, 0x44…) — UI object attribute/geometry lists [INF by form].

Not isolated: a strict sequential record walk of `\images` diverges after
record 1 — the section interleaves record subtypes (raw bitmaps, RLE streams,
attribute tables) whose per-type headers were not fully reversed. The section
is therefore inventoried by content class, not per-record. Nothing in the
section is text, config or code by any scan in §4–§5.

## 3. `\fonts` section (1,342,143 B) — fully walked [FACT]

Sequential walk with the §1 record format consumes the section exactly:
**7,251 glyph records**, walk end FS+0x530478 — 1 byte past stage H's stated
region end 0x530477 (the byte at 0x530477 is the last payload byte; H's end
offset is off by one, immaterial).

- Header fields across all 7,251 records: `fa` ∈ {132: 1975, 133: 1686,
  134: 1893, 135: 1697} — four font faces/variants [INF]; `fb` ∈ {60: 6796,
  59: 430, 58: 23, 67: 2} — glyph height class ≈ 58–60 [INF].
- Payload: `count` u32 items per glyph, min 1, max 417, total 313,780 items.
  Sampled payloads show interleaved, smoothly decreasing coordinate-like
  sequences (e.g. glyph 1 of the section: paired values descending
  0x64,0x5D,0x56,0x4E… and 0xE3,0xDC,0xD4,0xCD…) — outline/vector glyph data
  [INF by structure]; the exact outline encoding was not reversed and does
  not affect the verdict.

**Glyph index verification (the root tables decoded)** [FACT]: the root
section holds **33 index tables** of flagged BE u32 entries, 7,251 entries in
total, and for every k:

```
table[k] × 4 == byte offset of glyph record k in \fonts
```

verified for all 7,251 entries with zero mismatches. Table sizes are
211–226 entries (mostly 216), i.e. one table per font instance covering a
~216-glyph repertoire [INF: codepoints ≈ 0x20–0xF7]; two runs of 422–432
entries are adjacent table pairs with no unflagged separator. Between tables
sit variable per-font metadata blocks (1–57 u32s, unflagged) — not decoded;
they contain no text (§4 scans cover the whole root).

## 4. Content check — no technical content [FACT]

Whole-bank scans (`inventory.py`):

- ASCII strings ≥8 chars: 1,698 hits, **all graphics-data noise** (short,
  punctuation-heavy); no words, no XML (`<?xml`: 0), no URLs (`http`: 0).
- UTF-16LE strings ≥3 chars: 123 hits; meaningful names: only `\images`,
  `\fonts` (remaining "alphabetic" hits — `oooooooo`, `xxxxxxl` — are bitmap
  runs).
- Technical constants: coil parameter float 1.69 (`3F D8 51 EC`): **0 hits**.
  `SAM01`: 0. `Clarinox`: 0. `Carrier`: 0. Bus table id `03 05` occurs only
  inside RLE graphics streams (context bytes are RLE opcodes), not as data.
- Pointers: BE u32s in the bank falling in the main-span range
  (0x18040000–0x18460000) occur at exactly chance rate (1,399 observed vs
  ≈1,330 expected for random data) and are scattered in payload data — no
  pointer tables, no code references into or out of the bank besides §1's
  three base constants.
- **Stage H's "some XML/text resources" in this region does not reproduce**:
  zero XML and zero readable text exist in the bank. (Plaintext UI/help
  strings live in the main span, 0x18323000–0x1846xxxx, as stage H itself
  maps — outside this bank.)

Root-section residue, characterised but not fully decoded: after the glyph
tables (FS+0x7708–0x16B8C, ≈61 KB) sit a 138-entry unflagged u32 table
(values 0xCCBD3–0xF3ECC, byte-granular) and u16-pair metric tables
(e.g. pairs (3,29), (5,29), (9,29)… at FS+0x7B9C — advance/height metrics
[INF]). These are UI metric/index data by form; the 138-entry table's target
section could not be determined (it matches no record-header pattern in any
section above chance) and is listed as unresolved in §6. All of it is covered
by the scans above: no text, no constants, no config values.

## 5. Codec caveat — closed [FACT]

Stage D's "90 zlib streams" were already disproven by H and K (0 valid zlib
streams). This stage closes the remaining "non-deflate codec" caveat:

- Magic census: PNG 0, GIF 0, ZIP 0, LZ4 frame 0, OTTO 0, WOFF 0, XML 0.
  gzip magic: 3 isolated hits inside bitmap payloads — all 93 header-shaped
  candidates in the bank (zlib/gzip/raw-deflate, all window variants) were
  decompression-tested: **0 successes**. 1,328 raw-deflate attempts at 4 KB
  boundaries: 0 successes.
- LZ4 block: no frame magic anywhere; token decompression attempts at section
  payload starts: 0 successes.
- **Entropy argument (the decisive one)**: Shannon entropy of every 16 KB
  window in the bank was computed; the maximum is **7.31 bits** (at
  FS+0x118000) and no window reaches 7.5. Any LZ77-family, LZ4 or heatshrink
  stream of nontrivial size has entropy ≈ 7.9–8.0 bits/byte. The bank's
  uniformly low/mid entropy (long runs, repeated u32 patterns, structured
  tables) is quantitatively incompatible with compressed or encrypted blobs.
  The only compression present is the §2 graphics RLE (visible runs/opcodes,
  low entropy) — a bitmap codec, whose decoded content is pixels by
  construction.
- Structural coverage: the fonts section (1.34 MB) is walked record-by-record
  to its exact end and the root (93 KB) is table-parsed end to end, so no
  unexamined blob space remains there; the images section is covered by the
  entropy bound plus the §4 constant/string census over every byte.

Heatshrink specifically was not executable here (no library), but it is an
LZ77 variant and is excluded by the same entropy bound.

## 6. Not found / not isolated (explicit)

1. No per-file names inside sections — by design of the format (index-based),
   not a search failure: full-bank UTF-16/ASCII census in §4.
2. No XML or text resources in the bank (contra stage H §6's parenthetical) —
   searched: ASCII ≥4/≥8, UTF-16LE/BE, `<?xml` magic.
3. No configuration data, no equipment/protocol parameters, no coil table, no
   code — searched by constant census (§4) and pointer census (chance rate).
4. No compressed streams of any tested family (§5); heatshrink excluded by
   entropy, not by direct test.
5. Not isolated: exact glyph-outline encoding inside fonts payloads; the
   `\images` per-subtype record headers (walk diverges after record 1);
   semantics of the per-font metadata blocks between glyph tables; the
   138-entry unflagged table at FS+0x7708; the 3 u32s at FS+0x40
   (`0x80001e45, 0x3, 0x3fc6` — note 0x3fc6 words = 0xFF18 B = offset of
   images record 1, suggesting an images-index fragment [INF], unverified);
   the u32 @root+0x0C.
6. Region end: glyph walk terminates at FS+0x530478 vs stage H's 0x530477 —
   a 1-byte discrepancy in H's end offset; the bank is followed by 0xFF
   padding either way.

## 7. Verdict

The ROM FS contains **only UI assets**:

- a 2-entry directory (`\images`, `\fonts`) with content ids;
- a 33-table glyph index (7,251 entries) in the root section;
- 7,251 font glyph records (4 faces, ≈58–60 px class) in `\fonts`;
- bitmap records (raw ARGB + RLE), attribute tables and metric tables in
  `\images` and the root tail.

No hidden tables, configs or technical text exist in the blobs. The last
unsearched space is searched: **nothing protocol-, equipment- or
control-related lives in the resource bank** — consistent with stages D–N,
where every technical structure was found in the main span.

## Artefacts

- `firmware-re/stageX/inventory.py` — full census/parse script (rerunnable).
- `firmware-re/stageX/out/inventory.txt` — complete inventory (per-table
  listing, distributions, all test counts).
- `firmware-re/stageX/out/fshunt.txt` — Ghidra xrefs + decompiles for
  FUN_1805261a and its island; `out/dis_52480.txt` — capstone disassembly.
- `firmware-re/stageX/parse_fs.py` — section record parser.
- Project copy: `firmware-re/stageX/proj/` (from stage N; original image and
  other stages untouched).
