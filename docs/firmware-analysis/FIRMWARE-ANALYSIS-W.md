# Firmware Analysis — Stage W: the 0305 data plane in the older versions (4.47–4.74), where the catalog still lists it

**Target:** Carrier/ICP "Ion" wall control firmware family `BINF*` (Renesas
SH-2A, SuperH BE, image base `0x18040000`), versions **4.47, 4.56, 4.66,
4.70, 4.74** vs our unit's **4.79** (MD5 `e31903228bf39a4bc9c0a2a74192359e`).

**Task:** stage K found that the unified catalog lists objects
`0303/0305/0307` in 4.47–4.74 but not in 4.79. Stage F proved that in
4.79 the dictionary binding layer (group table @ `0x182B5E3A`, member
registry @ `0x182B6AC8`) has **no group at all for `0305`** — while
`0303` and `0307` *are* bound. Question: in the older versions, where
`0305` was still catalogued, was it also *bound* — with member records
that map its 12-byte payload to named fields? If so, the payload
construction the serializer hides in 4.79 might be visible there.

**Method:** raw Python over the decoded images in
`firmware-re/versions/decoded/` (read-only; all stage-W work in
`firmware-re/stageW/`). The 4.79 group table / registry were re-parsed
from scratch as a control: the parse reproduces stage F's two
independent anchors exactly — member[98] = SAM record
`{0x3C0D3ED4, 0x3C0D3EE4, 0x43100002, 0x01000000}` and group
(`030D`, sub `0x42`) → member 324 buf `0x3C0D41D0`. Group-table
location in each older version was found by geometry (the D-phase
first-record signature minus the 6-byte phase offset stage F
established), then validated by the same two anchors plus a strict
tiling invariant: member ranges of all groups tile `[0, N)` with no
gaps or overlaps, and the table ends exactly where the bucket index
begins. Every load-bearing claim below is dual-verified (walk +
alignment-strict raw scan, or parse + byte comparison).

---

## 0. Verdict

**No leak. The older data plane is the same wall, one release earlier.**

- [FACT] **Table `0305` has no binding group in any gen-2 version
  checked — 4.47, 4.56, 4.66, 4.70, 4.74, 4.79.** Neither do `060D`,
  `0610`, `061E`. The demand write was never bound into the
  group/member layer, including in every version where the catalog
  still listed it. There are no member records for `0305` anywhere,
  hence no field mapping to recover.
- [FACT] **The group table is byte-identical across 4.70 → 4.74 →
  4.79** (all 386 records + the 128-byte bucket index), and the member
  registry is identical except 9 records whose only differing field is
  a code-pointer `aux` (relocation noise; owners: tables
  `0410/050E/0625/0716` — none on the demand path). The entire binding
  data plane was frozen from Jan 2025 on; the 4.79 change is confined
  to the catalog.
- [FACT] **What 4.79 actually changed is only the catalog** (the
  dictionary-object index): the records for `0303`, `0305`, `0307`
  (and also `0301`, `0309`) were deleted, the surviving even `030x`
  records (`0302/0304/0306/0308/030A`) and `061E` were reclassed
  1 → 2 — and, in the opposite direction, `060D` *gained* a catalog
  record in 4.79 (class 1) after being absent in 4.47 and 4.74.
  Catalog membership churns in both directions across releases and is
  fully decoupled from binding: `0305` was catalogued-but-unbound for
  its whole catalogued life; `060D` is bound in no version yet was
  catalogued in 4.79.
- [FACT] `0303`/`0307` bindings are stable across all versions
  (§3): no shrink, no deprecation trail on the binding side. The
  catalog removal in 4.79 is a single-step data-model edit, not the
  end of a gradual withdrawal.

**Consequence:** the serializer boundary of stages F/N is not a 4.79
regression that an older image can undo. In every obtainable gen-2
version, the layers that describe device data (catalog, groups,
members) describe the *mirror/poll* side only; the demand frame's
construction was equally outside them in 4.47 as in 4.79. The payload
mapping for `0305` remains known only from the wire (protocol map:
[0] heat stage, [2] cool stage, [4..5] BE16 CFM, [11] `0x78` const).

---

## 1. Locating the structures in the older images

[FACT — per-version addresses; all in the main span, base
`0x18040000`]

| Version | Group table | Groups | Members tiled | Registry | Catalog |
|---|---|---|---|---|---|
| 4.47 | `0x182A90AA` | 345 | 1,123 | `0x182A9BF0` | `0x183F9ADC` (5,577 rec) |
| 4.56 | `0x182A976E` | 346 | — | — | — |
| 4.66 | `0x182AD77A` | 382 | — | — | — |
| 4.70 | `0x182B1362` | 386 | — | — | — |
| 4.74 | `0x182CF66E` | 386 | 1,321 | `0x182D02FC` | `0x1842AEC0` (5,412 rec) |
| 4.79 | `0x182B5E3A` | 386 | 1,321 | `0x182B6AC8` | `0x18404928` (5,417 rec) |

Anchors reproduced in 4.74 [FACT]: group (`0104`, sub `0x92`) starts
at member 98; member[98] = `{buf 0x3C0D3ED4, aux 0x3C0D3EE4, type
0x43100002, flag 0x01000000}` — byte-identical to 4.79's SAM record.
Group (`030D`, sub `0x42`) starts at member 324, buf `0x3C0D41D0` —
stage F's decisive-test value, again identical. In 4.47 the same
anchors hold with shifted indices (SAM at member 91, buf
`0x3C0D3D68`; (`030D`,`0x42`) at member 284, buf `0x3C0D4014`, same
type word `0x03070002`), because 4.47's `0104` family has fewer class
groups. The structures are the same structures, at version-specific
addresses — not analogues guessed by shape.

Note on counts: stage F reported "385 groups" for 4.79; the tiling
parse here accepts 386 records and ends exactly at the bucket index
`0x182B6A4A` with 1,321 members tiled — the 386th record is the one
stage F's walk stopped short of. Immaterial to every conclusion.

## 2. The target tables in the binding layer, per version

[FACT — group = (table, device-class sub) with member range in the
registry; full dumps in `stageW/out/groups_*.txt`]

| Table | 4.47 | 4.56 | 4.66 | 4.70 | 4.74 | 4.79 |
|---|---|---|---|---|---|---|
| `0303` | 4 groups (51/52/56/57) | 4 | 5 (+5B) | 5 | 5 | 5 |
| **`0305`** | **none** | **none** | **none** | **none** | **none** | **none** |
| `0307` | 3 groups (3E/40/42) | 3 | 3 | 3 | 3 | 3 |
| `0304` (calibration) | 8 groups | — | — | — | 9 (+5B) | 9 |
| `0306` (calibration) | 3 groups (3E/40/42) | — | — | 3 | 3 | 3 |
| `0605` | 2 groups (56/57) | — | — | 3 (+5B) | 3 | 3 |
| `060D`, `0610`, `061E` | none | — | — | — | none | none |

The only motion in the whole target set across six versions is the
addition of device class `0x5B` groups (for `0303`, `0304`, `0605`)
between 4.56 and 4.66 — an equipment-coverage accretion of the same
kind the versions diff found everywhere else, not a change to any
existing binding. `0305` is absent for **every** device class in
**every** version: there is no class for which a demand binding ever
existed in the obtainable history.

### What a "normal" binding looks like (calibration, 0304/0306)

[FACT] A bound table has one group per device class; each group owns
a contiguous member range. Member records are 0x10 B
`{buf, aux, type_word, flag_word}` where `buf` is a RAM address in
the device-object space (`0x3C0D…`), the type word is
`{field-key byte, length byte (1|2), 0, 0}` and the flag word's high
byte is a datatype/scale class (`0x01` raw 1-byte; `0x0A`/`0x0B`
2-byte scaled — the `0302`/`0306` ×1/16 °F uint16 fields of the
infinitive data carry `0x0A`; `0304`'s 2-byte fields carry `0x04`).
Bufs tile the object's buffer contiguously with spacing = field
length. Two properties matter for the leak question:

1. **Members describe the thermostat's RAM mirror object, not the
   wire payload.** The same field keys recur across device classes
   at different bufs, and member order within a group is not payload
   order (e.g. `0302` sub `0x3E`: keys run `0x0B, 0x0D, 0x03, 0x05,
   0x07, 0x09` while bufs ascend). Even a hypothetical `0305` binding
   would have described dictionary-object fields, and stage F proved
   the layer's only code consumer is membership bookkeeping
   (`FUN_180a8da2`) — it never serializes.
2. `0303`'s bindings illustrate the point concretely: `0303` is the
   ODU-side TLV/pressures *read* (protocol map: `20→53 0303`), and
   its groups exist only for ODU classes
   (`0x51/0x52/0x56/0x57/0x5B`) — e.g. sub `0x52` = two members,
   `{key 0x05, len 2, flag 0x0A}` @ buf `0x3C0D401C` and
   `{key 0x03, len 1, flag 0x01}` @ buf `0x3C0D401E`, identical in
   4.74 and 4.79 (in 4.47 the same pair sits at `0x3C0D3E94/96`).
   A read-mirror binding, stable across the whole span — and of no
   help for a *write* payload.

## 3. The catalog side: what 4.79 changed, exactly

[FACT — tolerant walk + alignment-strict raw scan agree; catalog
records are `{class, 00, id BE16}`, ids strictly ascending]

- **4.47** (catalog `0x183F9ADC`, 5,577 records): `0303` @
  `0x183FA598`, `0305` @ `0x183FA5A0`, `0307` @ `0x183FA5A8` — three
  adjacent records, **all class 1**. `060D`, `0610`, `061E` absent.
- **4.74** (catalog `0x1842AEC0`, 5,412 records): `0303` @
  `0x1842B9F8`, `0305` @ `0x1842BA00`, `0307` @ `0x1842BA08` — again
  adjacent, **all class 1**. The whole run `0x02FE–0x030C` is class 1.
  `060D` absent (no record-shaped hit in an alignment-strict scan of
  the full catalog span); `0610` class 2; `061E` class 1.
- **4.79** (catalog `0x18404928`, 5,417 records): the trio is gone.
  The neighbourhood diff against 4.74 is broader than the trio:
  **deleted** = `0301, 0303, 0305, 0307, 0309` (every odd id in
  `0301–0309`); **reclassed 1 → 2** = `0302, 0304, 0306, 0308, 030A`
  (every even id) and `061E`; **unchanged** = `030B, 030C` (class 1),
  `030D` (class 1), `0605` (class 1), `0610` (class 2 in both);
  **added** = `060D` (class 1, record @ `0x18405D88`) — absent from
  both older catalogs. The only `0303/0305/0307`-shaped aligned hits
  in 4.79 lie *past* the catalog end (`0x18409DCC`), at
  `0x18409EE0+`, with class byte `0x00` — a value that never occurs
  inside the catalog — in the post-catalog structure stage K
  identified. They are not records.
- **Class semantics:** `0305` carried class **1** for its entire
  catalogued life — the generic majority class (79 % of 4.79's ids;
  also the class of `0104`, `0316`, `0604`, `0605`). Stage K rejected
  the field-count and record-length readings of the class byte, and
  stage W adds the decisive behavioural evidence: class-1 catalog
  membership coexisted, in every version, with total absence from
  the binding layer. **The class byte therefore carries no
  serializer-treatment information**; a class-1 `0305` was treated by
  the data plane exactly as an uncatalogued one. [The 4.79 edit
  itself is consistent with the dictionary data-model cleanup the
  versions diff independently found in 4.79 — the
  `system/utilityEvent/demand*` group removal — but that linkage is
  inference; the deletions/reclasses above are fact.]

## 4. Answers to the task's five questions

1. **4.74 group table / registry located** by geometry and proven by
   stage F's own anchors (SAM member 98, (`030D`,`0x42`) member 324,
   both byte-identical to 4.79) — §1.
2. **`0303/0305/0307` groups in 4.74:** `0303` — 5 groups, 16 members
   (ODU classes only; field pairs of §2); `0307` — 3 groups, 3
   members (one 1-byte object per furnace-side class
   `0x3E/0x40/0x42`, bufs `0x3C0D40B0/B1/B2`); **`0305` — no group, no
   members, nothing to map.** Calibration against `0304` (9 groups,
   36 members) and `0306` (3 groups, 5 members) shows what a bound
   table's footprint looks like; `0305` has none of it.
3. **4.47 (and 4.56/4.66/4.70 spot checks):** identical picture. The
   `0305` group does not shrink or change across versions — it never
   exists. The only trail is accretion (class `0x5B` added to other
   tables in 4.66) and the frozen table from 4.70 on.
4. **What changed in 4.79:** not a deletion of a binding and not a
   reclassing of the object in any layer that touches the wire — the
   group table and registry are byte-identical to 4.74. Only the
   catalog (dictionary-object index) lost the trio's records (plus
   `0301/0309`), reclassed their even neighbours, and gained
   `060D`'s. `0305`'s catalog class in 4.47–4.74 was **1**, the
   generic class — no special serializer semantics attach to it (§3).
5. **Verdict:** the older data plane does **not** reveal the `0305`
   payload construction. The serializer is equally opaque in 4.47,
   4.74 and 4.79, because the demand object was never registered in
   the descriptive layers in the first place — its 4.79 catalog
   removal changed nothing about how (or how visibly) the frame is
   built. The one concrete payload mapping that exists remains the
   wire-derived one in the protocol map.

## 5. Explicit negatives

- No group record with table `0x0305` (any sub) in the group tables
  of 4.47 / 4.56 / 4.66 / 4.70 / 4.74 / 4.79 — the parse is
  data-complete (tiling-validated), not call-site-based, so computed
  arguments cannot hide one.
- No member record attributable to `0305` in the 4.47 (1,123) or
  4.74/4.79 (1,321) registries: every member is owned by exactly one
  group under the tiling, and no group is `0305`'s.
- No catalog record for `0303/0305/0307` in 4.79 under either a
  tolerant walk or an alignment-strict scan (the two class-`0x00`
  shaped hits are post-catalog data).
- No difference at all in the group table or bucket index between
  4.70, 4.74 and 4.79; registry differences are confined to 9
  `aux`-only code-pointer values in unrelated tables
  (`0410/050E/0625/0716`).

## 6. Artifacts (all under `firmware-re/stageW/`)

- `w1_parse.py` → `out/groups_0479.txt`, `out/groups_0474.txt`,
  `out/groups_0447.txt` (all groups with member bufs),
  `out/registry_0479.txt`, `out/registry_0474.txt`,
  `out/registry_0447.txt` (all member records verbatim),
  `out/w1_full.txt` (target-table groups + members + catalog classes
  for the three versions).
- `w2_diff.py` → `out/w2_full.txt` (byte identity of group table /
  bucket index, registry diff, tolerant catalog walks, cross-version
  group signatures, `0303` member sequences).
- `w3_checks.py` → `out/w3_full.txt` (owners of the 9 differing
  registry records; alignment-strict catalog scans; catalog
  neighbourhood `0x02FE–0x030C` in 4.74 vs 4.79).
- `w4_spotcheck.py` → `out/w4_full.txt` (group parses for
  4.56/4.66/4.70; 4.70 group-table byte identity vs 4.74).
- `firmware-re/versions/` originals and all other stages were not
  modified.
