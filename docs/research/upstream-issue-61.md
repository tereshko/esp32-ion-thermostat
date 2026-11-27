# Upstream: nebulous/infinitesp issue #61

The project's one open upstream thread. Filed from this installation
during phase 2/3: the SAM-side behaviour of the Ion (zero mirror,
ignored writes, the 400A path) and the node's table scan of the
thermostat.

- 2026-10-31: nebulous replied with a proposed test — read the
  thermostat's table 0x40 row directly. That test was already
  covered by this project's captures; the registration gate is
  firmware-internal (see the SAM registration research), so the
  thread's open question is narrower than the issue title suggests.
- 2026-11-02: the project's scan results were posted: a `SCAN?` map
  of **18 tables the thermostat serves at 0x20** (including the
  SYSCTRL table 49), with the conclusion that no stock "DONE"
  completion signal exists for the schedule-row edit the maintainer
  asked about.
- Status (2026-11-26): waiting on the maintainer. A daily watch
  checks the issue for new comments or a status change; the project
  does not block on it — the 400A contract is proven and in the
  firmware.
