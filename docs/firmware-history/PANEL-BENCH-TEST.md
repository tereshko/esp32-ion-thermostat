# PANEL BENCH-TEST — test firmware for the breadboard stand

Bench firmware for the panel hardware, matching the breadboard
layout delivered 2026-11-20 (classic ESP32 from the working
node; everything imagined arrived except the new S3 boards).
One file: `panel-bench-test.yaml`, in this folder. No local
components, no secrets beyond the usual `secrets.yaml` in the
build folder.

**Status: WRITTEN 2026-11-20 — NOT COMPILED HERE.** ESPHome is
not installed in the preparation environment (same limit as
`TEST-FIRMWARE.md` §6), so `esphome config` / a compile could
not be run. **The first real gate is your local `esphome run`
compile.** If it errors, send the full text back before
flashing anything.

---

## 1. What it covers (one block at a time, as in the layout)

| Block | What the build does | Pass sign |
|---|---|---|
| I2C | `scan: true` logs every address at boot | Log shows `0x29, 0x38, 0x44` |
| SHT40 + TSL2591 | `sht4x` 0x44, `tsl2591` 0x29, 10 s | HA sensors `Bench Temperature / Humidity / Illuminance` update |
| Screen | `ili9xxx` ST7796, 480×320 | Title, values, red/green/blue bars on screen |
| Touch | `ft63x6`, INT→GPIO34 | Touch logs `Touch at x=… y=…`, coords appear on screen |
| Radar | `ld2410` on UART1 16/17 @256000 | `Bench Radar Presence` flips when you move; distance in metres |
| Audio out | MAX98357A, I2S DIN→GPIO13 | `Bench Speaker` media player in HA — play any sound/TTS, hear it |
| Mic | SPH0645, I2S DOUT→GPIO35 | `Bench Mic` entity exists (voice pipeline is a later step, not this test) |
| Backlight | LED→GPIO32 via LEDC | `Bench Backlight` light in HA, dimmable |

Deliberately NOT in this build: InfinitESP hub, RS-485 bus,
climate entity, 400A writes — nothing here can touch the
furnace. Device name is `thermostat-bench`, separate from the
live `diy-thermostat`, so no HA entity or OTA collision.

## 2. Pin map (identical to the 2026-11-20 layout message)

Screen ST7796U (VCC → 5V rail): SCK→18, MOSI→23, CS→5,
DC→27, RST→33, LED→32. MISO not wired.
Touch FT6336U: SDA→21, SCL→22, INT→34.
I2C (21/22, 3.3V): SHT40 0x44, TSL2591 0x29, touch 0x38.
LD2410C (5V): TX→16, RX→17.
Audio I2S (BCLK→26, WS→25): MAX98357A DIN→13, SPH0645
DOUT→35, SEL→GND (left channel). Speakers in series (8 Ω).
Power: 5V rail from a separate 2A USB charger, not the ESP;
grounds of the ESP and the 5V rail common.

Pin audit done here: no GPIO is used twice; 34/35 are
input-only pins used as inputs only (touch INT, mic DOUT);
16/17 are free on the bench because there is no RS-485 in
this build.

## 3. How to flash it

1. In the build folder (the one holding `secrets.yaml`), copy
   `panel-bench-test.yaml` next to it.
2. First flash **over USB**: `esphome run panel-bench-test.yaml`
   — OTA cannot reach it under the new name yet. Pick the USB
   port when asked.
3. After it boots, it appears in HA as a new device
   `Thermostat Bench` — the live `DIY Thermostat` device stays
   untouched (it will show offline while its ESP is on the
   bench, which is expected).
4. Check order — one block at a time, as in the layout:
   1. Only I2C in the log: addresses 0x29, 0x38, 0x44.
   2. Plus screen: bars + text; touch logs coordinates.
   3. Plus LD2410C: presence and distance.
   4. Plus audio: a tone/TTS from HA through `Bench Speaker`.

## 4. Two things that can bite on the classic ESP32

- **No PSRAM, big screen.** A 480×320 16-bit framebuffer is
  307 KB and does not fit in the classic ESP32's RAM — that is
  why the build sets `color_palette: 8BIT` (154 KB). If the log
  still says `Could not allocate buffer for display`, the bench
  ESP genuinely cannot drive this screen in ESPHome and the
  display check moves to the S3 when it arrives; the I2C, radar
  and audio blocks are unaffected.
- **Orientation.** The build uses `rotation: 90` (the 320×480
  controller is mounted landscape in this module). If the
  picture is sideways or mirrored, change `rotation` to 270
  first — nothing else.

## 5. Validation performed (and its limit)

- The YAML parses cleanly (tolerant parser for ESPHome's
  `!secret` tags); structure mirrors the house style of
  `phase3-control.yaml` (esp-idf, `esp32dev`, logger 115200,
  plain `api:`/`ota:`, `!secret` Wi-Fi).
- Pin map cross-checked against the 2026-11-20 layout message
  and the panel review (S3 pinout NOT reused — DC/LED/RESET/
  INT here are 27/32/33/34 because GPIO 10–13 are flash/PSRAM
  strapping territory on the classic ESP32, and the S3-only
  mapping would not work on this chip).
- Component names verified against ESPHome docs 2026-11-20:
  `ili9xxx` model `ST7796`, `ft63x6` touchscreen, `sht4x`,
  `tsl2591`, `ld2410` hub + sensors, `i2s_audio` speaker /
  microphone / media-player chain.
- NOT validated here: the compile itself, the display
  orientation, and the audio chain (I2S speaker + mic sharing
  one bus is the least-proven block — if the speaker fails to
  initialise, comment out the `microphone:` block and recompile
  before suspecting the wiring).

## 6. Rollback

`esphome run phase3-control.yaml` on this ESP, then reinstall
it at the wall. The bench build changed nothing on the wall;
while the ESP is on the bench the Ion heats from the wall
alone, HA control paused.
