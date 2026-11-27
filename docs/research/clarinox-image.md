# Clarinox fingerprint — Ion firmware BINF0479 (v4.79), in-image evidence

Stage H, 2026-11-26. Source: `ion-firmware/carrier/BINF0479_Carrier.hex`, decoded to a flat
image (base 0x18040000, offset = address − 0x18040000) and scanned raw; cross-checked against
the stage-B/C Ghidra project (copied to `firmware-re/stageH/proj`, never modified in place).
Full string extraction: 108,960 strings (ASCII ≥4 + UTF-16BE/LE) in
`firmware-re/stageH/out/all_strings.tsv`; 132 lines / 96 distinct strings mention "Clarinox"
(case-insensitive); 76 distinct `Clx*` identifiers; 48 distinct full build paths.

Claims are tagged [FACT] (bytes/strings at the cited address) or [INF] (inference, with the
reasoning stated). Negatives list the space actually searched (§7).

## 1. Verdict

The firmware embeds the **Clarinox protocol-stack suite, version family 9.0.0**, in three
components, each carrying an embedded version/build record [FACT, §2]:

| Component | Version record in image | Build | Record address |
|---|---|---|---|
| ClarinoxBlue (Bluetooth BR/EDR + BLE stack) | `9.0.0` / vendor `Clarinox` | 11452 | 0x1831EAFC / 0x1831EB02 / 0x1831EB08 |
| Clarinox SoftFrame (the framework the stacks run on) | `9.0.0` | 16695 | 0x1831FF40 / 0x1831FF46 |
| ClarinoxWiFi / ClarinoxWLAN (Wi-Fi stack) | `9.0.0.p3` | 2097 | 0x18320020 / 0x18320029 |

Supporting platform [FACT]: Clarinox OS abstraction layer `cos_al` in its **FreeRTOS**
variant only; FreeRTOS kernel + Amazon FreeRTOS libraries (AWS IoT c_sdk, device-metrics
string `SDK=AmazonFreeRTOS&Version=4.0.0` @ 0x182EF740); **lwIP v2.1.2**, shipped *inside
the Clarinox BSP tree* and ported via its `Generic/FreeRTOS` sys_arch; **mbedTLS** present
(error-string blocks ~0x182F4C7C–0x182F5Axx, version string not found, §7); SEGGER embOS
survives only as Clarinox's per-RTOS build-folder naming (`Build\embOS\...`) — the embOS
kernel itself is **not** what runs here (§7).

Two build trees are fused into one image [FACT, §4]: Carrier's integration tree
`C:\CING_Int\E5.SoftwareConstruction\WallControl\...` and Clarinox's own tree
`C:\BingClarinox\...`. "BING" is the wall-control board/project codename in both trees.
The RTOS port target in the Clarinox BSP is the Renesas **RSK2_SH7269** starter kit —
the dev-kit origin of the SH7269 (SH-2A) port.

## 2. Version evidence (the pin-down material for web research)

Three adjacent-string records of the form {version, build, name/vendor} sit in the Clarinox
data cluster 0x1831E800–0x18322000 [FACT]:

1. **ClarinoxBlue**: `9.0.0` @ 0x1831EAFC, `11452` @ 0x1831EB02, `Clarinox` @ 0x1831EB08,
   immediately followed by the stack's configuration-key table (`InitSoftFrameWithStack`,
   `MaxNoOfPairedDevices`, `Hci.*`, `L2cap.*`, `Ble.AttChannel.*`, `Ble.Smp.ER/IR`,
   transports `\\.\CSR0`, `TT_USB`, `TT_VENDOR_H4`, 0x1831EB14–0x1831EF38) and the assert
   path `C:\BingClarinox\System\ClarinoxBlue\Stack\ClxHci.cpp` @ 0x1831EF8C.
   Attribution of this record to ClarinoxBlue is [INF] — strong: the record directly heads
   the Blue configuration table; the literal component name is not adjacent.
2. **SoftFrame**: `9.0.0` @ 0x1831FF40, `16695` @ 0x1831FF46, then `SoftFrame.cfg` /
   `Cannot open SoftFrame.cfg` @ 0x1831FF4C/0x1831FF5D and transport-endpoint config keys
   (`TE_MEDIUM`, `TE_PORT_NAME`, `TE_BAUD_RATE`, …) plus `TerminalRxThread` @ 0x18320000.
   Attribution [INF], same reasoning.
3. **ClarinoxWiFi**: `9.0.0.p3` @ 0x18320020, `2097` @ 0x18320029, immediately followed by
   the `ClxWlan*` API name table (`ClxWlanStartInterface`, `ClxWlanScan`, `ClxWlanConnect`,
   … 0x18320048+) and WLAN config keys (`Ap.EncryptionProtocol` @ 0x18320030).
   Attribution [INF], same reasoning.

Other version/build strings [FACT]:

- Firmware build identity: `CESR******-**.79` (stage A; the "04.79" is the thermostat
  firmware version). No Clarinox marketing banner (e.g. "ClarinoxBlue v…") exists anywhere
  in the image (§7) — the records above are the only version evidence.
- Amazon FreeRTOS device metrics: `?SDK=AmazonFreeRTOS&Version=4.0.0&Platform=Unknown&
  AFRDevID=%.*s` @ 0x182EF740 (from `FreeRTOS libs\c_sdk\...\iot_device_metrics.c`).
  Caution: "4.0.0" is the metrics-string version, not necessarily the AFR release.
- lwIP **v2.1.2** — embedded in 30+ assert paths, e.g. `...\Third_Party\lwip_v2.1.2\
  src\core\tcp.c` @ 0x1830B6D8 [FACT].
- Stack configuration files named in-image: `ClarinoxBlue.cfg` @ 0x182AF7DC, 0x182C7874,
  0x1831F564; `ClarinoxBlueLowEnergy.cfg` @ 0x18320788; `SoftFrame.cfg` @ 0x1831FF4C
  [FACT]. The stacks are configured by key=value .cfg files; the full key vocabulary for
  Blue is the table at 0x1831EB14–0x1831EF38.
- License machinery: `Demo license expired! Please contact Clarinox.` @ 0x18320A3D [FACT].
  The stack contains a demo-license check string. Whether the check is armed in this
  production build cannot be decided from strings alone — do not read this as "the
  thermostat runs a demo license".

## 3. Component inventory (in-image surface)

### 3.1 ClarinoxBlue — full Bluetooth stack, BR/EDR + BLE

Log-module table, 45 contiguous `CLARINOXBLUE_*` / `CLARINOXWIFI_*` names @
0x1831F950–0x1831FD54 [FACT]. Blue modules: GLOBAL, TRANSPORT, ACL, COMMON, L2CAP_COMMON,
L2CAP_CLASSIC, NETWORKING, HCI, SCO_OVER_HCI, SCO, RFCOMM, OBEX, OBEX_OVER_L2CAP, BNEP,
AVCTP, AVDTP, SDP, MCAP, SDAP, SPP, A2DP, AVRCP, HIDP, PAN, HDP, MAP_CLIENT, PBAP_CLIENT,
HFP_HF, HFP_AG, HSP_HS, HSP_AG, BPP_PRINTER, BIP, HRCP, FTP, OPP, CTN_CLIENT — i.e. the
complete classic profile set — plus BLE: BLE_GLOBAL, BLE_ACL, BLE_ATT_CLIENT,
BLE_ATT_SERVER, BLE_L2CAP, BLE_IPSP, BLE_SMP, BLE_ATT.

API name tables [FACT]: GAP/BLE + GATT-client event API `ClxGapBle*` / `ClxGattClient*`
@ 0x1831F000–0x1831F564 (e.g. `ClxGapBleConnectionComplete`, `ClxGattClientDiscoverAll-
PrimaryServices`); `ClarinoxBlue GAP` @ 0x1831EFD4. Threads [FACT]: `ClarinoxMainThread`
@ 0x182AFB78, `ClarinoxBlueStackThread` @ 0x183208EC, `ClarinoxBlueApplicationThread`
@ 0x18320594 (+ `...MessageHandler` @ 0x1832056C).

Carrier-side application of the stack [FACT]: CING adapter `BleTask\BleTask_mainAppCentral-
.cpp` @ 0x182AF75C (a BLE *central*), test-app remnant name `ClxBleClientTestApp`
@ 0x182AF644, runtime task `BLE_Main_App_Task` @ 0x182F8578. This matches the product
behaviour (the wall control talks BLE to room sensors / phone).

Chip-vendor name table @ 0x1832063C–0x18320694 [FACT]: `Clarinox`, `Intel`, `Broadcom`,
`Qualcomm`, `STMicro`, `MediaTek`, `Marvell`, `Nordic` — the HCI vendor-identification
table of the transport layer (the second bare "Clarinox" string lives here; it is a
vendor name, not a version record).

### 3.2 ClarinoxWiFi / ClarinoxWLAN

Log modules `CLARINOXWIFI_STACK` @ 0x1831FD40, `CLARINOXWIFI_CHIP_DRIVER` @ 0x1831FD54,
and **`WPA_SUPPLICANT_PKG`** @ 0x1831FD70 [FACT] — the Wi-Fi stack bundles a wpa_supplicant
package. Name string `ClarinoxWLAN Stack` @ 0x18321434; threads `ClarinoxWlanApplication-
Thread` @ 0x183211A0 (+ MessageHandler @ 0x18321178); event API `ClxWlan*` (BssDiscovered,
StationJoined/Disconnected, Authentication/Association Initiated/Completed, HardwareError,
ApDisconnected, LinkLost) @ 0x183211C0–0x183212E4 [FACT]. Carrier adapter:
`WiFiTask\WiFi_task_Clarinox.cpp` @ 0x1831D0B4; task name `WiFi Task` @ 0x182F8590.
Anchor xref: `ClarinoxWLAN Stack` is passed as a parameter by function **0x18250F3C**
[Ghidra refs, stageH `out/anchor_xrefs.txt`] — a WLAN-stack code anchor.

### 3.3 SoftFrame framework + portability layer (the "Clx" runtime)

Clarinox's own source files named in asserts [FACT]: `System\Common\ClxCQueue.cpp`
@ 0x1831F698, `System\Common\ClarinoxTasks\ClxTaskScheduler.cpp` @ 0x18320CE4,
`System\Common\ClxThreadSleepSemaphore.cpp` @ 0x18320FA0, `System\Portability\ClxThread.cpp`
@ 0x1831FD9C, `System\Common\ClxNetworkTransportInterface.h` @ 0x183221C0, and
`System\CommonAPI\ClxQueueTemplate.h` — the single most-referenced Clarinox header,
cited by 30+ assert sites spanning 0x1831F5BC–0x183234EC. Also `ClxUIEngine::InputThread`
@ 0x1831FE8C [FACT] — a Clarinox UI-engine component exists in the build (whether the
thermostat UI actually runs on it is [INF] — unproven; Carrier's UI strings/help texts
live elsewhere, §6).

Anchor xrefs [Ghidra]: `ClxThread.cpp` path is referenced from function **0x182368F8** and
the `ClxQueueTemplate.h` assert from 0x18236B50 (in function 0x18236B3A) — the Clarinox
common/portability code has a sampled code anchor at **≈0x18236800–0x18236E00**.

### 3.4 Clarinox OS abstraction layer (cos_al)

`Middleware\cos_al_freertos.c` (CING tree) @ 0x182C2E9C [FACT] — the only cos_al variant
whose assert path exists in the image (no `cos_al_embos.c`, §7). Decisive xref evidence:
the path is passed as a parameter by **eight functions in 0x180BC294–0x180BC528** — the
0x180BCxxx helper family that stages C/E identified as the runtime's task-creation and
object-binding helpers (FUN_180bc084 task-create wrapper, FUN_180bc460 binding check,
FUN_180BC05A/06E accessor brackets). I.e. the dictionary/object runtime's helper family is
compiled **on top of the Clarinox OS AL** [FACT at the xref level; the family-to-runtime
identification is stages C/E's].

### 3.5 BSP

`Clarinox\Applications\KoalaApplication\embOS\RSK2_SH7269\BSP\BspBING.cpp` @ 0x182AFAEC
[FACT] — the board support for "BING" derives from Clarinox's **KoalaApplication**
reference application for the Renesas RSK2_SH7269 kit. Network interface:
`Clarinox\System\BSP\embOS\RSK2_SH7269\NetworkAccessInterface.Layer2.LWIP_Socket.Bsp.cpp`
@ 0x182F6C88 [FACT].

## 4. Build-tree evidence (48 distinct full paths)

Two trees [FACT, full list in `stageH/out/paths_full.txt`]:

- **`C:\CING_Int\E5.SoftwareConstruction\WallControl\`** — Carrier's integration tree
  ("CING"). Contains: the application tasks (`BleTask\`, `WiFiTask\`), FreeRTOS kernel
  sources (`FreeRTOS\Source\event_groups.c` @ 0x182C5EF4, `queue.c` @ 0x182FA044,
  `tasks.c` @ 0x1830B584, `timers.c` @ 0x1830CE78), Amazon FreeRTOS libs (`FreeRTOS libs\
  c_sdk\...`, `abstractions\platform\freertos\...`, `ports\secure_sockets\...`),
  `Middleware\cos_al_freertos.c`, and a vendored copy of the Clarinox tree
  (`WallControl\Clarinox\System\BSP\...`) including lwIP v2.1.2 under
  `Clarinox\System\BSP\Boards\Utilities\Third_Party\lwip_v2.1.2\` (30+ files: api_lib,
  sockets, tcpip, sntp, dhcp, tcp/tcp_in/tcp_out, pbuf, memp, dns, ethernet, and the
  `port\Generic\FreeRTOS\sys_arch.c` port @ 0x1830AFE8).
- **`C:\BingClarinox\`** — Clarinox's own build tree for the project "Bing": compiler
  **SHC** (Renesas SuperH compiler), per-RTOS folder `Build\embOS\Projects\Bing\SHC\`,
  sources under `System\...` (ClarinoxBlue stack, Common, CommonAPI, Portability).
  The "embOS" folder name is Clarinox's port-organization heritage [stage A]; the kernel
  actually linked is FreeRTOS (kernel assert paths + cos_al_freertos + the event_groups
  code cluster at 0x180FC544–0x180FC9E0 whose functions reference `event_groups.c`
  [Ghidra xrefs]).

Compiler/toolchain [FACT]: SHC (paths), Renesas SH-2A/SH7269, big-endian (stage B).
Copyright strings present [FACT]: `Carrier Corporation 2016` @ 0x182DD030, `Bryant 2016`,
`United Technologies Corp. 2018` (UI/resource area). No Clarinox copyright line exists
anywhere in the image (§7).

## 5. Architecture as seen in the image (dictionary / object system)

This is the layer stages B–E reverse-engineered; stage H adds the attribution evidence.
Summary with addresses (details: FIRMWARE-ANALYSIS-C/-D/-E):

- **Field store**: one flat byte array; field id = byte offset; database magic 0x3C0E4A20.
  Getter FUN_1815927c; setter-A FUN_18159220 (memset semantics); setter-B FUN_181592e4
  (memcmp+memcpy "publish"; 279 pool cells, 894 call sites, 347 calling functions —
  stage C `out/setterB_calls.txt`). Accessor cluster 0x18158C00–0x18159C00.
- **Descriptor table** @ 0x182B04D4: 0x35C records × 0x18 B; provider/computed-property
  function pointer at +0x10; sentinel name @ 0x182F6D10; restore dispatcher FUN_181664da.
  These records are the bridge between the flat store and computed values.
- **Binding directory** @ 0x182B5E40 (stage D): 385 records × 8 B
  `[len][00][table BE16][field][flags][store_offset BE16]` — declarative bindings from
  store fields to protocol tables. The bus command tables themselves (0305, 060D, 061E,
  400A, 3B02/3B03…) are **not** in this directory — the command burst is built
  programmatically (stage D), which is why the payload writers remained un-isolated.
- **Binding/object helpers** family 0x180BCxxx (FUN_180A8DA2 binding op emitting
  (0x42, 3, 0x0D, buf) in state 0x14; FUN_180bc460 "bound" check on dword[obj+0x38];
  FUN_180bc084 task-create wrapper) — compiled over cos_al (§3.4). Device objects live in
  the dictionary address space 0x3C… (e.g. SAM record @ 0x3C0D3ED4, its handle 0x3C0D3EE4).
- **Dictionary publish path**: FUN_180EA4EC emits frames (0x4F, 3, 0x32, buf, 0xFE) with a
  fixed 30-byte record serializer FUN_180EA704 using the image's only CRC-16 table
  @ 0x182C4164 (CRC-16/MODBUS family, stage D). The dictionary engine's own code logs
  assert paths from the **CING** tree (FUN_1817e7c6) [stage C/D] — i.e. the engine is
  Carrier-tree code built on the Clarinox runtime, not a Clarinox-tree binary blob.
  Attribution wording for external use: "Clarinox-based object/dictionary runtime,
  integrated and extended in Carrier's CING tree" — calling the whole engine
  "Clarinox software" overstates what the image proves.
- **Sparkplug B dictionary**: `spBv1.0` @ 0x18300264, node id `WallCtrl` @ 0x1830026C;
  the metric-name space occupies 0x18300000–0x1830A200. Stage H inventory
  (`stageH/out/dictionary_names.txt`): **902 identifier-like names** in
  0x18300000–0x1830B000; namespaces: `system/` ×70, `odu/` ×19, `idu/` ×12, `dealer/` ×4,
  `Updates/` ×4, `eula/` ×3, `history/` ×2, `debug/` ×1, plus 785 bare names (zone
  metrics, NBIRTH/DBIRTH/NDATA/DDATA/NCMD/DCMD vocabulary, stage E §9). This dictionary
  is the thermostat's external data model (Sparkplug/MQTT-facing), distinct from the
  internal field store above.
- **Task inventory** (name table @ 0x182F8508–0x182F85Cx) [FACT]: `SPARKPLUG_Task`,
  `dataTransferTask`, `NgipDataLogging_Task`, `BLE_Main_App_Task`, `REST_Task`,
  `WiFi Task`, `MSD Update Task`, `SDCard Task`, `sys_ctrl_task`, `Touchscreen Task` —
  plus the Clarinox threads of §3. `sys_ctrl_task` is the message dispatcher of the
  control core (stage E), not the control loop itself.

## 6. Code footprint and the middleware/application boundary

Function census (Ghidra, stageH copy; `stageH/out/functions.tsv`) [FACT]: **10,853
functions, 1,724,101 total body bytes**, entry points 0x180405FC–0x183D69B8.

| 1 MiB bucket | Functions | Body bytes |
|---|---|---|
| 0x18000000 | 3,727 | 585,376 |
| 0x18100000 | 4,276 | 751,412 |
| 0x18200000 | 2,742 | 342,577 |
| 0x18300000 | 108 | 44,736 |

Region map (string density per 64 KiB in `stageH/out/density.txt` + stages C–E clusters):

- **0x18040000–0x182B0000 — the code mass**: ~10,745 of 10,853 functions (≈1.68 MB of
  function bodies; a lower bound — un-functioned code, literal pools and alignment are
  excluded). Application and middleware code are **interleaved at link level**; there is
  no contiguous "Clarinox region". Known application clusters inside it: field-store
  cluster 0x18158C00–0x18159C00, zone decision module 0x180C54xx–0x180C58xx, dictionary
  engine ≈0x180EAxxx/0x1817E7C6, binding helpers 0x180BCxxx, SAM cluster
  0x180AFxxx–0x180B2xxx (stage C). Sampled middleware anchors inside it: FreeRTOS
  event-groups ≈0x180FC544–0x180FC9E0; Clarinox common/portability ≈0x182368F8–0x18236D40;
  WLAN stack function 0x18250F3C; HCI references ≈0x18229C08/0x18229CB8 (DATA refs only —
  weak).
- **0x182B0000–0x182C0000 — structured data**: descriptor table 0x182B04D4, binding
  directory 0x182B5E40 (only 63 strings in this 64 KiB bucket — it is tables, not text).
- **0x182C0000–0x1830B000 — rodata/string mass** (31–48 KB of strings per 64 KiB bucket):
  assert paths, coil-pattern arrays 0x182C48E0–0x182C51xx, help texts
  0x182D8C08–0x182DA6D0, AWS-IoT/Sparkplug strings, dictionary names 0x18300000–0x1830A200.
- **0x1830B000–0x18323000 — mixed data**: UI strings + the **Clarinox data cluster
  0x1831E800–0x18322000** (config-key tables, the three version records, API name tables,
  log-module table, chip-vendor table). This cluster is the fingerprint's centre of mass:
  if a future image diff is needed, diff here first.
- **0x18323000–0x1846xxxx — UI/localization data** (incl. French UI strings ~0x183Dxxxx)
  with a few function entries (the 108 in the 0x183xxxxx bucket) that are [INF] most
  likely data misidentified as code or small islands — not relied on anywhere here.
- **0x18810100–0x18D40577 — ROM resource filesystem**: directories `\images`, `\fonts`
  (UTF-16 names at 0x18810100+), multi-level offset tables (first table: 216 entries
  0x80000000|offset from 0x1881014C). Plaintext inside it (some XML/text resources) is
  covered by the main string extraction; the binary blobs are not (§7).

**Boundary estimate** [INF, stated with its basis]: a defensible split cannot be drawn by
address. By evidence type: (a) code whose asserts name the `C:\BingClarinox\` tree or
`Clx*`/`cos_al` symbols is Clarinox's; (b) code whose asserts name `C:\CING_Int\` is
Carrier's integration build — which *includes* vendored Clarinox BSP sources, FreeRTOS,
lwIP and AFR, so (b) overcounts "Carrier" if read naively; (c) everything else is
unattributed. Sampled anchors suggest the Clarinox stack code is a minority of the
1.72 MB body total — the stacks' data footprint (config/API/log tables) is only ~16 KB
(0x1831E800–0x18322000), and their code anchors occupy compact neighbourhoods — but no
percentage is quoted: producing one would require a full xref sweep from every Clarinox
string, which was not run.

## 7. Not found / not reproduced (searched space stated)

1. **No Clarinox version banner or copyright line.** Searched all 108,960 extracted
   strings (ASCII ≥4, UTF-16BE/LE) for `clarinox` (132 hits, all inventoried above),
   `copyright`, `(C)`, `©`, `version`, `v[0-9]` patterns. The only Clarinox version
   evidence is the three {version, build} records of §2. No mbedTLS version string
   either (library proven only by its X.509/BIGNUM error-string blocks ~0x182F4C7C+).
   No FreeRTOS kernel version string (`tskKERNEL_VERSION_NUMBER`-style) found.
2. **No embOS kernel.** Only folder naming (`Build\embOS\...`, BSP folder `embOS\`)
   and no embOS API/task strings; the linked kernel is FreeRTOS (§4). No
   `cos_al_embos.c` assert path — only the FreeRTOS variant of the Clarinox OS AL.
3. **The "90 zlib streams" of stage D could not be reproduced from flat.bin.** The whole
   flat image was scanned for valid zlib framing (0 hits); the resources region
   0x18810100–0x18D40577 additionally tested for gzip magic (0) and for raw-deflate at
   the FS offset-table entries (only false positives yielding repeated-byte runs — the
   blobs behave like raw graphics/font data, not deflate). Stage D's stream contents
   were therefore **not** re-grepped by stage H; plaintext resources in the region are
   covered by the main string extraction, compressed/binary blobs (fonts, images) are
   the one unsearched space. If the streams matter later, the FS directory format at
   0x18810100 (hash pairs + UTF-16 names + 0x80000000|offset tables) is the way in.
4. **No payload-writer functions for the bus command tables** (0305/0605/060D writers) —
   unchanged from stages D/E; static analysis terminates at Clarinox's runtime-registered
   dispatch. The fingerprint does not change that conclusion; it only attributes the
   dispatch layer (§5).
5. **No per-component code ranges for the stacks** beyond the sampled anchors of §6;
   Ghidra reference recovery on SH-2A literal pools is partial (several anchor refs
   resolve as DATA from non-function addresses).

## 8. What public documentation would most help (for the web-research agent)

In expected-value order:

1. **ClarinoxBlue / ClarinoxWiFi 9.0.0 release notes or datasheets** — to confirm the
   {9.0.0 build 11452 / 9.0.0.p3 build 2097} records map to the public product versions,
   and the exact product names ("ClarinoxBlue", "ClarinoxWiFi") and profile coverage.
2. **SoftFrame framework documentation** — SoftFrame.cfg key vocabulary
   (`TE_MEDIUM`, `TE_PORT_NAME`, …), the `Clx*` API conventions, and how stacks register
   version/build records — would confirm the §2 record format and the §3.3 attribution.
3. **Clarinox OS Abstraction Layer (cos_al) documentation** — the API surface that the
   0x180BCxxx helper family and the dictionary runtime sit on; the most direct public
   handle on the runtime-registered dispatch that blocks stages D/E.
4. **ClarinoxBlue .cfg configuration reference** — the key table at 0x1831EB14–0x1831EF38
   (HCI/L2CAP/ATT/SMP buffer and timeout keys) is complete in-image; a public reference
   would let us read the thermostat's actual BT configuration values out of the image.
5. **KoalaApplication / RSK2_SH7269 BSP materials** — would confirm the dev-kit lineage
   of the BING board support and possibly the transport (H4/UART) wiring assumptions.
6. Anything on Clarinox's **license module** ("Demo license expired!") — to determine
   whether the check is a live gate in production builds or a dormant string.

## Appendix — stage H artifacts (`firmware-re/stageH/`)

- `out/all_strings.tsv` — all 108,960 strings (addr, encoding, text)
- `out/paths_full.txt` — the 48 distinct full build paths with addresses
- `out/version_strings.txt`, `out/keywords.txt` — targeted greps (keyword counts in
  `keywords.txt` are case-sensitive for some patterns; the TSV is authoritative)
- `out/dictionary_names.txt` — 902 dictionary identifiers, 0x18300000–0x1830B000
- `out/density.txt` — ASCII string density per 64 KiB bucket
- `out/functions.tsv` — 10,853 Ghidra functions (entry, body size, name)
- `out/anchor_xrefs.txt` — references to the seven Clarinox anchor strings
- `extract_strings.py`, `grep_surface.py`, `zlib_streams.py`, `density.py`,
  `scripts/FuncDump.java`, `flat.bin` (working copy), `proj/` (Ghidra project copy)
