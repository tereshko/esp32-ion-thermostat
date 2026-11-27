# Evidence — exhibits from the capture logs

Computed directly from the bus captures. Each exhibit states the claim,
the source file, and quotes the decisive frames verbatim (equipment
serial numbers masked). Raw JSONL captures are not redistributed; the
counts below are reproducible from the same files.

- [`corpus.md`](corpus.md) — the capture inventory: every file, frame
  counts, spans, top talkers. 83,758 frames across the main files.
- [`capture-index.md`](capture-index.md) — the session-by-session index
  of what was done at the wall during each capture and what it proved.
- [`boot-commissioning.md`](boot-commissioning.md) — cold start: the
  furnace speaks first, the thermostat appears as 0x1F at +6.0 s, hands
  over to 0x20 at +16.7 s, first addressed write at +62.0 s, first
  0305 demand at +71.65 s; equipment self-identification frames.
- [`burst-anatomy.md`](burst-anatomy.md) — one ≈10 s command burst,
  frame by frame, in wire order.
- [`sam-zero-mirror.md`](sam-zero-mirror.md) — thousands of SAM polls
  answered with all-zero payloads: the mirror is dead, by count.
- [`400a-write-test.md`](400a-write-test.md) — the writes from the
  unregistered SAM and the thermostat's own poll replies showing the
  manual pair change and persist. Zero exception frames.
- [`calls.md`](calls.md) — a cooling call switching on (0605 capacity
  0.0 → 5.0 in the first burst, call-state byte with it) and the
  CFM/stage progression of cooling and heating calls.
- [`reseat-silence.md`](reseat-silence.md) — 36 s with the thermostat
  physically off the wall: who kept talking, and the equipment's
  complete non-reaction. The measured lower bound of the failover
  window.
