# FIRMWARE-ANALYSIS.md — ICP Ion BINF0479 firmware, RE stage A

Date: 2026-10-30. Scope: desk analysis of files only; nothing was flashed or
written to any device. Source file: `ion-firmware/Version_0479_ICP.zip` →
`TSTAT/BINF0479.hex` (10,188,916 bytes; MD5 `e31903228bf39a4bc9c0a2a74192359e`;
SHA-256 `2d1a9ea3c723e245fbabe6089118f750adfc6dd249c9b2e76a79d3f8a4c90c04`).
Working scripts are preserved in `firmware-re/`; decoded region dumps were
produced in scratch space and can be regenerated with `firmware-re/decode.py`.

Labels: **[FACT]** = measured/parsed directly. **[INF]** = inference, with the
reasoning shown. Where a check came back negative, the exact space searched is
stated so the negative means something.

---

## 1. Container forensics

**[FACT]** Despite the `.hex` name and suffix, the file is a **binary
Intel-HEX-style record stream**, not text. Each record is:
`':' (0x3A) | count (1B) | address (2B, BE) | type (1B) | data | checksum (1B)`,
where the checksum is the standard Intel HEX two's-complement of
count+address+type+data. Record census: 76,040 type-0 (data), 152 type-4
(extended linear address), 1 type-5 (start address), 1 type-1 (EOF).
**All 76,193 record checksums verify — 0 bad.** There are no non-record gaps:
the entire 10.19 MB is records.

**[FACT] Decoded payload: 9,731,444 bytes**, in these load-address regions:

| Region | Load range | Size | Content (see §3/§4) |
|---|---|---|---|
| header | 0x18040000–0x18040023 | 35 B | block header (below) |
| boot/table | 0x18040024–0x18044E1C | 19,960 B | pointer/vector tables + startup code |
| main A | 0x18048000–0x18323602 | 2,995,715 B | code + data (strings, descriptors) |
| main B | 0x18323604–0x1844B339 | 1,211,702 B | string-pointer table, tables, fonts/code |
| main C | 0x1844B33C–0x18459E83 | 60,232 B | incl. OTTO font data |
| certs | 0x18800000–0x18800B57 | 2,904 B | PEM certificate bundle |
| pad | 0x1880FFFC–0x1880FFFF | 4 B | 0xFFFFFFFF (erased-flash padding) |
| resources | 0x18810100–0x18D40577 | 5,440,632 B | filesystem image (`\images`, `\fonts`, JPEGs, zlib blobs) |
| trailer word | 0x18F3FEF8–0x18F3FEFB | 4 B | 0x92B6CC87 (see §2) |
| trailer page | 0x18F3FF00–0x18F3FFFF | 256 B | all zeros |

Two programmed addresses are simply absent from the file (1-byte gap at
0x18323603, 2-byte gap at 0x1844B33A–B) — the packer skipped them; nothing can
be concluded from them beyond that.

**[FACT] Block header** (at 0x18040000): ASCII `!!START_OF_CODE!`, then ASCII
`CESR******-**.79`, a NUL, and a 2-byte field `0x044F` (meaning undetermined).
The three other `!!START_OF_CODE!` byte sequences in the image are **false
positives inside content**, not block headers: dealer-menu text at 0x182C79BC
("…system control / heat pump / furnace / wi-fi software update setup"), a
patent-number list at 0x182C9034, and stored-file content at 0x182F6680 (next
to a directory listing mentioning `SAVER.BMP`, `SCHE????.TXT`). **There is
exactly one code block.**

**[FACT]** The first data block (0x18040024) opens with a big-endian word
table whose first pairs are `(0x180405FC, 0x18F3FEF8)` and
`(0x18F3FEFC, 0x18F40000)` — i.e. it names the type-5 start value and the
trailer word/page addresses — followed by pairs in the 0x19xxxxxx range
(outside this image; purpose undetermined, plausibly updater/BSC segment
descriptors **[INF]**), then a function-pointer array whose entries land
inside the boot region (default handler 0x18044DD0 repeated).

**[FACT]** The type-5 (start) record is stored at the very end of the file
(file offset 0x9B7864), immediately before the EOF record, and carries
**0x180405FC**. The two trailer segments are the last data records before it.

## 2. Integrity test — verdict: UNDETERMINED, no signature evidence

**[FACT]** The only stored whole-image-looking check value found is the word
at **0x18F3FEF8 = 0x92B6CC87**, and the header table's first entry pair points
at exactly that address — strong circumstantial evidence it is the image
check word **[INF]**.

**[FACT]** It was tested, with **no match**, against: CRC-32 (zlib params),
Adler-32, plain 32-bit sum, CRC-32C (Castagnoli), CRC-32/MPEG-2, CRC-32/BZIP2,
CRC-32/POSIX-cksum, and MD5/SHA-1/SHA-256 first/last 4 bytes — over 15
candidate payload ranges (regions concatenated; spans 0x18040000→0x18459E84
and 0x180405FC→0x18F3FEF8 with zero- and 0xFF-gap fills; whole raw container;
per-region). The container's own record checksums are per-record only.

**[FACT]** Signature search: **no fixed 128/256/512-byte high-entropy block**
exists at any region tail or at the trailer (tail entropies 4.3–6.0 bits/byte;
main-C tail is zeros; the 256-byte trailer page is all zeros). The 0x18800000
PEM bundle is a TLS trust store (first cert is Amazon-issued — the AWS IoT
cloud chain), not an image-signing chain, by content.

**Verdict:** no evidence of cryptographic signature verification *in this
image*. The check scheme behind 0x92B6CC87 is **undetermined** — it may be a
checksum over a range/parameterisation not tried, a truncated hash, or a
packer ID. **Honest caveat:** this pass cannot rule out a bootloader *outside
this file* verifying something with data stored off-image (OTP/eFuse/config
partition). It also cannot rule out that the on-device updater checks only
the header (model/version) plus per-record checksums — in which case the word
would be informational. Both possibilities must be resolved before any flash
experiment (see §6).

## 3. CPU fingerprint — Renesas SH-2A (SH7269), big-endian [FACT]

Build-path strings burned into the image name the target outright:

- `C:\CING_Int\E5.SoftwareConstruction\WallControl\Clarinox\Applications\KoalaApplication\embOS\RSK2_SH7269\BSP\BspBING.cpp`
- `…\Clarinox\System\BSP\embOS\RSK2_SH7269\NetworkAccessInterface.Layer2.LWIP_Socket…`
- `C:\BingClarinox\Build\embOS\Projects\Bing\SHC\…` (SHC = Renesas SuperH C/C++ compiler)

Stack **[FACT, from strings]**: FreeRTOS + Amazon FreeRTOS AWS IoT SDK
(`?SDK=AmazonFreeRTOS&Version=4.0.0…`, `iot_secure_sockets.c`), lwIP v2.1.2,
Clarinox Blue/WiFi middleware, SEGGER embOS heritage in the Clarinox BSP,
project codename **"BING" / "WallControl"**, integrator tree `CING_Int`.

Disassembly proof (capstone, SH-2A BE) — coherent code with textbook
prologues and literal pools:

```
0x1804060C: sts.l pr,@-r15 ; movi20 #589820,r1 ; mov r1,r4
            mov.l 0x18040620,r3 ; jsr/n @r3 ; mov.l 0x18040624,r3 ; jsr/n @r3
            lds.l @r15+,pr ; rts/n
0x18040628: movml.l r7,@-r15 ; sts.l pr,@-r15 ; …
0x1827C000: byte-swap routine (shlr16/shlr8/shll8 chains), mov.l literal
            pools at 0x1827C2AC/0x1827C2B0, jsr @r14 — real application code
```

ARM (A32/Thumb, both endians), PowerPC, MIPS, M68K and SPARC were all tried
first and decode to garbage everywhere; the pointer/table data is uniformly
**big-endian**, consistent with SH7269 in BE mode. (Tooling note: capstone
5.0.7's SH backend segfaults on long uninterrupted streams; all scanning here
was done in crash-isolated 16 KB chunks, so the code-extent map is a *lower
bound*: verified-dense windows at 0x1827C000–0x18280000, 0x18373604–0x1837B604,
0x183AB604–0x183AF604, plus the boot region.)

Runtime addresses = load addresses is supported by thousands of
self-referential BE pointers resolving inside the image **[INF, strong]**.

## 4. String xrefs

Target strings (load addresses) and every reference found in the image.
References are BE 32-bit words; "table" references are slots in data tables,
not code literal pools (see the negative result at the end of this section).

| String | String addr | Referenced from | Form |
|---|---|---|---|
| `Searching for SAM/B36 module` | 0x182CA8E8 | **0x183B1534** | master UI string table, entry **#180** |
| `Searching for B36 module` | 0x182CA908 | **0x183B1538** | string table entry **#181** |
| `no SAM/B36` | 0x182CA580 | **0x183B13F8** | label table (equipment summary labels) |
| `SAM RADIO TEST` | 0x182D07D4 | **0x183B318C** | alert/event text table |
| `SAM model` | 0x182AE58C | **0x1806FEBC** | device-info descriptor record (below) |
| `NIM model` | 0x182AE540 | **0x1806C568** | twin descriptor record (below) |
| ` SAMINFO` | 0x182AFF9C | **none found** | sits in the ABCD-bus table-name list (neighbours ` INGDATA`, ` SCHEDULE`, ` TEMP`) → referenced by protocol table ID, not by pointer **[INF]** |

**Master UI string table [FACT]:** approx. 0x183B1264–0x183B33E0, 2,144 BE
pointer entries (base is approximate — walked outward while entries pointed
at plausible strings). The commissioning sequence is consecutive in it:
#177 `Searching for indoor unit` (slot 0x183B1528), #178 `…outdoor unit`
(…152C), #179 `…heater` (…1530), **#180 `…SAM/B36 module` (…1534)**,
#181 `…B36 module` (…1538), #182 `…refrig dissipation board` (…153C).
The SAM step is a first-class entry in the same display sequence as the
steps that do run — from the table alone there is no sign of special-casing.

**Device-info descriptor records [FACT]:** the `SAM model` reference at
0x1806FEBC sits inside a statically-initialised record whose neighbouring
fields are `{…, 0x18067F02, 0x3C225910, →'SAM model', 0x180BC05A, 0xFFF8348D,
0x1823D404, 0x180BC06E, →'--------------', 0x181EF47C, →'SAM SN', 0xFFF8349D,
→'SAM SW version', 0xFFF834AD, 0xFFF8377F, 0x1815927C, …}`. The `NIM model`
record at 0x1806C568 has **identical surrounding field values** with only the
label pointers swapped to the NIM strings — the UI's per-device info screens
are data-driven from these records. A separate field table references fields
*inside* the SAM record: words at 0x1815B29C→0x1806FEF0, 0x1815B530→0x1806FF0C,
0x1815B538→0x1806FF28.

**Negative result [FACT]:** apart from the slots above, there are **zero**
absolute pointers anywhere in the image into the string table's address range
(0x183B0000–0x183B4000), and zero pointers to the individual SAM strings other
than those listed. ⇒ Code does **not** reach these strings by absolute
address; it must go through an indirect (RAM-resident) pointer, an ID-based
resource/screen manager, or the descriptor records. **Consequence:** the
commissioning gate instruction cannot be located by pointer xref alone —
this pass has taken the strings route as far as it goes.

## 5. Carrier image — byte-identical [FACT]

Carrier's own v4.79 package (`Version_0479_Carrier.zip`, 5,324,979 B) was
downloaded on 2026-10-30 from the EULA-gated link that Carrier's Series B
4.79 release notes point to (`cacbdpapps.net/marketing/eula/…`, release notes
hosted at cetechsupport.com / legacy.myinfinitytouch.carrier.com; saved to
`ion-firmware/carrier/`). Its `BINF0479.hex` is **byte-for-byte identical** to
the ICP one — same size (10,188,916), same MD5, same SHA-256, same ZIP member
CRC (0x4502FD5A). The two zips differ *only* in the EULA PDF (Carrier vs Ion
branding) and in the release-notes PDF branding.

⇒ **One universal image** serves Carrier SYSTXCCITC01-B / SYSTXCCWIC01-B /
SYSTXCCICF01-B / SYSTXCCWIF01-B and the ICP SYST0101CW. Therefore the SAM gate
is **not** a difference in this image **[FACT]**; it is decided at runtime
from device-resident data (model/brand configuration in NVRAM/EEPROM,
hardware identity, or provisioned state) — or Carrier -B units behave
identically and field differences come from that same device-side data
**[INF]**.

## 6. GO / NO-GO assessment

- **"Flash the Carrier image to unlock SAM": NO-GO — moot.** It is already
  running those exact bytes (§5).
- **"Patch the image": NO-GO today.** Two blockers: (a) the gate has not been
  located (§4 negative result); (b) the whole-image check word at 0x18F3FEF8
  is unexplained (§2) — if the on-device boot chain verifies it, any flipped
  byte bricks the update until its scheme is known.
- **"Find the gate" (continued RE): GO.** The plan is unusually tractable for
  a binary-only target: known CPU (SH-2A BE), known RTOS/middleware, fully
  parsed container, mapped string table and descriptor records, verified code
  anchors, no signature evidence in-image.

**Single concrete next RE step:** load the decoded main image into Ghidra
(processor `SuperH:BE:32:SH-2A`, base 0x18040000) and start from the
*descriptor interpreter*, not the strings: follow the field-table references
at 0x1815B29C/0x1815B530/0x1815B538 into the code that consumes the SAM/NIM
device-info records, and separately find the code that renders string-table
IDs 177–182; the gate is the conditional that treats ID 180 (SAM/B36)
differently from ID 181 (B36) — comparing those two paths is the cheapest
diff in the whole firmware. In parallel, identify the check-word algorithm
by finding its consumer: the only code guaranteed to run before the app is
the 20 KB boot region at 0x18040024, which is small enough to read end-to-end.

## 7. What this pass cannot prove (honesty box)

- That the on-device updater/bootloader doesn't verify a signature using
  data held off-image (OTP, config partition). The image alone can't settle
  this; §2's verdict is "no evidence in-image", not "no signature anywhere".
- The full code extent (capstone's SH crashes forced chunk isolation; the
  density map is a lower bound).
- The meaning of header field 0x044F, of the 0x19xxxxxx table pairs, and of
  check word 0x92B6CC87.
- Whether the runtime SAM gate reads brand, model, or a provisioned flag —
  only that it is *not* in this image's bytes (§5) and not reachable by
  string xref (§4).
