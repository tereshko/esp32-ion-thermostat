# Evidence — capture corpus

Every claim in this knowledge base traces to a bus capture. This page is the
inventory of the corpus the exhibits below are computed from. Captures are
JSONL, one frame per line: `ts, src, dst, func, reg, data` (data = payload hex).
Raw capture files are not redistributed; the exhibits quote the decisive
frames verbatim (equipment serial numbers masked) and give the counts a
reader can reproduce from the same files.

- **400a-test-20261030-141705.jsonl** — 5,149 frames, 7 min, 2026-10-30T18:17:06.181Z … 2026-10-30T18:24:30.308Z; top talkers: 20→44 ×1375, 20→53 ×1275, 44→20 ×1159
- **400a-test-20261030-142628.jsonl** — 2,252 frames, 3 min, 2026-10-30T18:26:29.875Z … 2026-10-30T18:29:43.045Z; top talkers: 20→44 ×602, 20→53 ×555, 44→20 ×508
- **400a-test-20261030-145226.jsonl** — 2,197 frames, 3 min, 2026-10-30T18:52:27.150Z … 2026-10-30T18:55:37.222Z; top talkers: 20→44 ×588, 20→53 ×548, 44→20 ×497
- **400a-test-20261030-145554.jsonl** — 21,377 frames, 31 min, 2026-10-30T18:55:55.000Z … 2026-10-30T19:26:39.914Z; top talkers: 20→44 ×5707, 20→53 ×5314, 44→20 ×4828
- **coldstart-20261029-125733.jsonl** — 17,600 frames, 27 min, 2026-10-29T16:57:50.999Z … 2026-10-29T17:24:50.130Z; top talkers: 20→44 ×4847, 20→53 ×4500, 44→20 ×4096
- **full-install-20261029-150209.jsonl** — 1,267 frames, 3 min, 2026-10-29T19:02:09.285Z … 2026-10-29T19:04:55.940Z; top talkers: 20→44 ×298, 44→20 ×259, 20→53 ×195
- **phase3-validation-20261103-142517.jsonl** — 4,520 frames, 7 min, 2026-11-03T19:25:16.999Z … 2026-11-03T19:31:47.107Z; top talkers: 20→44 ×1209, 20→53 ×1124, 44→20 ×1020
- **phase3-validation2-20261103-143328.jsonl** — 15,806 frames, 23 min, 2026-11-03T19:33:27.113Z … 2026-11-03T19:56:08.429Z; top talkers: 20→44 ×4223, 20→53 ×3924, 44→20 ×3569
- **phase3-validation3-20261103-145755.jsonl** — 4,315 frames, 6 min, 2026-11-03T19:57:55.542Z … 2026-11-03T20:04:07.154Z; top talkers: 20→44 ×1151, 20→53 ×1068, 44→20 ×970
- **sam-commissioning-20261029-143248.jsonl** — 6,545 frames, 16 min, 2026-10-29T18:32:49.000Z … 2026-10-29T18:48:57.223Z; top talkers: 20→44 ×1687, 44→20 ×1505, 20→53 ×866
- **sam-control-test-20261029-145357.jsonl** — 1,119 frames, 2 min, 2026-10-29T18:53:57.403Z … 2026-10-29T18:55:34.046Z; top talkers: 20→44 ×299, 20→53 ×269, 44→20 ×254
- **sam-reseat-20261029-151123.jsonl** — 1,611 frames, 4 min, 2026-10-29T19:11:24.000Z … 2026-10-29T19:14:56.344Z; top talkers: 20→46 ×314, 20→44 ×201, 44→20 ×174

Main files total: **83,758 frames** (plus the seven coldstart segments in `segments/`, which are time-slices of the coldstart file, and the external gofinity boot capture cross-checked in `../research/gofinity-bootup.md`).

Counting rules, reconciled: **83,758** above is the line-by-line total of
the main files; the protocol map's **83,752** is the distinct-session total
(six glued/duplicated lines counted once — verification correction V-9);
**101,352** adds the coldstart segment files; the guide's "≈84,000" is the
rounded main-file figure; the "~75,000" in firmware-history/PHASE5 §1.3 is
an early estimate from before this inventory existed.
