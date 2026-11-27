# VERIFY-external — независимая перепроверка внешних источников

Дата: 2026-11-26. Метод: каждое утверждение перепроведено по первичным
артефактам (клон `firmware-re/external/infinitive/`, PDF
`external-research/SAM01-01XA.pdf` через pdftotext/pdfinfo, плоский образ
`firmware-re/stageB/flat.bin` поиском по сырым байтам, захват
`traces/external/gofinity-bootup.bin` собственным парсером кадров с
пересчётом CRC), а не по прозе нот. Локальная копия InfinitESP
(`infinitesp/components/infinitesp/infinitesp.h`) использована как второй
первичный источник для сверки сдвигов/флагов.

Итог: **REFUTED — нет.** Все утверждения подтверждены; три нюанса отмечены
внутри (текстовая ошибка 3E10 в gofinity-bootup.md, составное доказательство
флагов 0x80/0x100, единственная строка mbedTLS).

---

## 1. infinitive (infinitive-registers.md)

### 1.1 Сдвиг +3 и размеры тел 3B02/3B03/3B04 — CONFIRMED

Структуры Go в `tables.go` кодируются `encoding/binary` последовательно,
без выравнивания. Размеры структур: `TStatCurrentParams` = 26 B,
`TStatZoneParams` = 147 B, `TStatVacationParams` = 8 B. Ответ на READ в
`protocol.go` парсится с `reginfosz = 6` (3 байта таблица + 3 байта
префикс), поэтому тело регистра = префикс 3 B + структура =
**29 / 150 / 11 B** — ровно заявленные размеры и ровно константы
InfinitESP `REG3B02_SIZE=29`, `REG3B03_SIZE=150`, `REG3B04_DATA_BYTES=11`.

Сдвиг проверен по **всем** именованным полям (офсет InfinitESP минус офсет
поля в структуре infinitive = 3 в каждом случае):

- 3B02: temps 3−0, humidity 11−8, OAT 20−17, unoccupied 21−18,
  stagmode 22−19, weekday 25−22, minutes 26−23, dispzone 28−25.
- 3B03: fan 3−0, holding 11−8, heat SP 12−9, cool SP 20−17, humidity SP
  28−25, byte36 36−33, timed holds 37−34, durations 38−35, names 54−51.
- 3B04: active 3−0, hours 4−1, minT 6−3, maxT 7−4, minH 8−5, maxH 9−6,
  fan 10−7 (по `REG3B04_FLAG_*` в InfinitESP).

### 1.2 Stagmode-байт по 3B02[22] — CONFIRMED

InfinitESP: `REG3B02_STAGMODE = 22` («high nibble=stage, low nibble=mode»).
infinitive: поле `Mode` структуры стоит на офсете 19 (= 22 − 3); код
(`infinitive.go`, getZonesConfig) декодирует `params.Mode & 0xf` как режим
и `params.Mode >> 5` как ступень; `conversions.go rawModeToString`:
0 heat, 1 cool, 2 auto, 3 electric, 4 heatpump, 5 off.

### 1.3 Расписания 3B07–3B0D: 7 × 160 B, только README — CONFIRMED

README, Protocol Notes: «Register 3b.07 - 3b.0d: seven 1-day schedules …
encoded in 160 bytes: for each of 8 zones × for each of 4 time periods ×
uint16 start + uint8 heatSP + uint8 coolSP + uint8 0xff» — арифметика
8 × 4 × 5 = 160 ✓. В коде таблиц 3B07–3B0D нет (grep по всем .go —
ноль обращений); README прямо: «No access is provided for the scheduling
features».

### 1.4 Флаговые слова записи — CONFIRMED (с оговоркой по паре 0x80/0x100)

По коду infinitive (`infinitive.go` putConfig / writeZoneOverrideDuration):
fan `0x01`, hold `0x02`, heat SP `0x04`, cool SP `0x08`, override `0x80`
(отдельная запись длительности), mode `0x10`, displayed zone `0x200` —
каждый выставляется индивидуально. Пара weekday/minutes: infinitive
выставляет только объединённое `flags |= 0x180` при каждой глобальной
записи; индивидуальное разложение weekday=`0x80`, minutes=`0x100`
подтверждается константами InfinitESP (`CHANGE_WEEKDAY=0x080`,
`CHANGE_MINUTES=0x100`, `CHANGE_DISPLAYED_ZONE=0x200`) и арифметикой
0x180 = 0x80 | 0x100. Итог: значения верны, но внутри одного infinitive
по отдельности не встречаются.

### 1.5 Откат часов ≤1 мин, компенсация +30 с, флаги 0x180 — CONFIRMED

README §«Changing global parameters»: изменение глобальных параметров
«has a side effect of setting back the system clock by up to one minute».
Код `putConfig` (глобальная ветка): комментарий «setting these parameters
can make our thermostat lose up to 1 min of time keeping … adding 30s
helps in rounding to the nearest minute given truncation to one-minute
resolution»; реализация: `tnow := time.Now().Add(time.Second * 30)`,
DispDOW/DispTimeMin из tnow, `flags = flags | 0x180`.

### 1.6 0316: static pressure /65536, примеры CFM 954 и 705 — CONFIRMED

`infinitive.go` (snoop IDU): `data := frame.data[3:]`; CFM =
`binary.BigEndian.Uint16(data[4:6])`; StaticPressure =
`Uint16(data[7:9]) / 65536` (с округлением до 4 знаков).
Примеры из README дословно: лог ответа `000316 0000000003ba004a2f78…` —
CFM по [4..5] = 0x03BA = **954**, SP = 0x4A2F/65536 ≈ 0.290; Protocol
Notes `000316 00 00 02 0002c1004de9…` — CFM = 0x02C1 = **705**,
SP = 0x4DE9/65536 ≈ 0.304.

---

## 2. SAM01-01XA.pdf (sam-spec-notes.md)

### 2.1 Метаданные: 14 страниц, 2013-05-08, 496 140 байт — CONFIRMED

`pdfinfo`: Pages: **14**; CreationDate: **Wed May 8 13:24:18 2013 UTC**;
File size: **496140 bytes** (совпадает со `stat`). Title SAM01-01XA,
Creator PScript5.dll, Producer Acrobat Distiller 10.1.4.
(Утилита `file` показывает «10 page(s)» — её эвристика неверна; pdfinfo
и фактический pdftotext дают 14.)

### 2.2 Охват: только RS-232 ASCII, без шинных регистров и регистрации — CONFIRMED

По полному извлечённому тексту (110 538 символов): вхождений
«register» — **0**, «regist» — **0**, «3B02» — **0**, «3B03» — **0**.
Документ с титула и введения описывает только ASCII-интерфейс RS-232
порта SAM («ASCII--character--based, RS--232 communication port»);
процедуры регистрации/commissioning SAM в нём нет как класса.

### 2.3 Запись уставки = MANUAL activity + hold — CONFIRMED

Table 3 (команды уставок HTSP!/CLSP!, колонка Touch и legacy): при записи
уставки выдаётся «a 'hold until' in MANUAL activity … otherwise a 'hold
permanent' in MANUAL activity will be issued if not already in the MANUAL
activity».

### 2.4 DAY! запрещён на Touch — CONFIRMED

Команда `S1DAY!0-6`, колонка Touch: «Not Supported. A NAK will be
returned. The ING calculates the day of the week based on the date, so
explicitly setting the day is not permitted.»

### 2.5 VACMINH {0,10,15,20}, VACMAXH {55,60,65,100} — CONFIRMED

Table 3: `S1VACMINH!XXX` — «Valid values are 0, 10, 15, and 20» (Touch:
«0 (NONE), 10, 15, and 20»); `S1VACMAXH!XXX` — «Valid values are 55, 60,
65, and 100 (NONE)».

### 2.6 BLIGHT! ON = Level 8, OFF = Level 2 — CONFIRMED

`S1BLIGHT!ON/OFF`, колонка Touch: «ON requests continuous backlighting,
and will set the backlight to the factory default level (Level 8). OFF
will set the backlight to Level 2.»

### 2.7 Восстановленный хвост §8.2/§8.3 sam-spec-notes.md — CONFIRMED (5+ точек)

1. Множества VACMINH/VACMAXH из п. 6 §8.2 — совпадают с PDF (см. 2.5).
2. BLIGHT Level 8 / Level 2 из п. 7 §8.2 — совпадает (см. 2.6).
3. VACDAYS 0–365, ведущие нули (`!001`), 0 = завершение отпуска —
   PDF: «maximum of 365 days. Setting days to 0 will terminate an active
   vacation … leading zeros for numbers less than 100» ✓.
4. Touch-запреты п. 5 §8.2: `DAY!` (см. 2.4); `PGM` — «A NAK will be
   returned. This type of programming is not supported»; группа CFG —
   дословно «wall control algorithms changed to remove need for this
   command» (CFGAUTO!/CFGDEAD!/CFGCPH!); factory reset — Touch-колонка
   по `S1CFG!A5A5`/`S1CFG!RESET`: «Not Supported. A NAK will be
   returned», сама двухшаговость и окно 10 с — в legacy-колонке;
   `DEALER!`/`DEALERPH!` — «A NAK will be returned. Not Supported,
   Dealer Name/Phone is set via direct online connection or USB
   device»; `MODE!EHEAT` — «(EHEAT can be commanded, but will always
   result in a NAK.)» ✓ по всем пунктам.
5. Эррата спеки из п. 8 §8.2: «Auxiliary» встречается в извлечённом
   тексте PDF ровно **1** раз (только TOC); опечатка `S1CFGCPY:
   ACK/NAK` в ответе на `S1CFGCPH!#` — есть; команда `S1FILTRMD!ON/OFF`
   при ответе `S1FILTRRMD:` — есть ✓.

---

## 3. Clarinox и платформа в образе (clarinox-image.md) — CONFIRMED

Поиск по сырым байтам `flat.bin` (база 0x18040000); адреса совпали с
нотами точно:

| Утверждение | Свидетельство в образе |
|---|---|
| ClarinoxBlue 9.0.0, build 11452 | `9.0.0` @0x1831EAFC, `11452` @0x1831EB02, следом `Clarinox`; контекст — ClarinoxBlue config-ключи (Hci.*, MaxNoOfPairedDevices) |
| SoftFrame 9.0.0, build 16695 | `9.0.0` @0x1831FF40, `16695` @0x1831FF46, следом `SoftFrame.cfg` / «Cannot open SoftFrame.cfg» |
| WiFi 9.0.0.p3, build 2097 | `9.0.0.p3` @0x18320020, `2097` @0x18320029, следом семейство `ClxWlan*` |
| FreeRTOS | assert-пути `FreeRTOS\Source\event_groups.c / queue.c / tasks.c / timers.c` и др. |
| Amazon FreeRTOS libs 4.0.0 | строка `?SDK=AmazonFreeRTOS&Version=4.0.0&Platform=Unknown&AFRDevID=%.*s` @0x182EF745 (контекст `FreeRTOS libs\c_sdk\…\iot_device_metrics.c`) |
| lwIP v2.1.2 | 30+ assert-путей `…\Third_Party\lwip_v2.1.2\src\…`, включая порт `port\Generic\FreeRTOS\sys_arch.c` |
| mbedTLS присутствует | одна дословная библиотечная строка @0x182F4CB0: «X509 - Signature algorithms do not match. (see \c ::mbedtls_x509_crt sig_oid)» |

Оговорка по mbedTLS: присутствие подтверждено одной verbatim-строкой
библиотеки; версионной строки mbedTLS в образе нет (ноты это честно
фиксируют — версия и не заявлялась).

---

## 4. gofinity bootup (gofinity-bootup.md) — CONFIRMED

Собственный парс `traces/external/gofinity-bootup.bin` (36 141 байт):
кадр = dst u16 BE, src u16 BE, len u8, 00, 00, op u8, data, CRC-16
(poly 0x8005 reflected = 0xA001, init 0) в конце, wire — little-endian.

- **1 532 кадра, файл разобран без остатка** (consumed = 36 141) —
  CONFIRMED.
- **CRC валидна на всех 1 532 / 1 532** (0 несовпадений) — CONFIRMED.
- **0x1F открывает broadcast-триплетом**: кадры 0–2, WRITE от 0x1F01 на
  0xF1F1: `0305` + 12 нулевых байт, `3E02` + `00`, `0605` + 7 нулевых
  байт. Сверка с нашим захватом `traces/coldstart-20261029-125733.jsonl`:
  src 1F, func 0C, dst F1 — `0305` data `000000000000000000000000` (12×00),
  `3E02` data `00`, `0605` data `00000000000000` (7×00). **Байт-в-байт
  идентичен нашему** — CONFIRMED.
- **Handoff на кадрах 106/107** (нумерация ноты — 0-based): кадр 106 —
  последний от 0x1F01, кадр 107 — первый от 0x2001 — CONFIRMED.
  Нюанс прозы ноты: кадр 106 подписан в gofinity-bootup.md как «READ
  3E10→0E», фактически его данные — `003E0A` (READ **3E0A** на 0x0E01).
  Ошибка текста ноты (уже известная по stage U), не данных.
- **Первый demand — кадр 646**: WRITE 0305 от 0x2001 на 0x4001, payload
  весь нулевой, кроме байта [11] = 0x78 — CONFIRMED.
- **Байт 0x78 присутствует**: во всех 9 направленных записях 0305
  payload[11] = 0x78 (единственное исключение — broadcast-кадр 0, где
  payload весь нулевой) — CONFIRMED.
- **0x0E пробится без ответа**: 110 кадров на dst 0x0E01 (первый — кадр
  61, READ 3E08 и др.), ответов от src 0x0E — **0** — CONFIRMED.

---

## Сводка вердиктов

| # | Утверждение | Вердикт |
|---|---|---|
| 1.1 | Сдвиг +3; тела 29/150/11 | CONFIRMED |
| 1.2 | Stagmode @ 3B02[22] | CONFIRMED |
| 1.3 | Расписания 7×160 B, README-only | CONFIRMED |
| 1.4 | Флаги fan/hold/heat/cool/override/mode/weekday/minutes/dispzone | CONFIRMED (0x80/0x100 — составное доказательство) |
| 1.5 | Откат часов ≤1 мин, +30 с, 0x180 | CONFIRMED |
| 1.6 | 0316 SP /65536; CFM 954 и 705 | CONFIRMED |
| 2.1 | PDF: 14 стр., 2013-05-08, 496 140 B | CONFIRMED |
| 2.2 | Только RS-232 ASCII; нет регистров/регистрации | CONFIRMED |
| 2.3 | Уставка = MANUAL + hold | CONFIRMED |
| 2.4 | DAY! на Touch запрещён | CONFIRMED |
| 2.5 | VACMINH/VACMAXH множества | CONFIRMED |
| 2.6 | BLIGHT! Level 8 / Level 2 | CONFIRMED |
| 2.7 | Восстановленный хвост §8.2/§8.3 соответствует PDF | CONFIRMED |
| 3 | Clarinox 9.0.0 (Blue 11452, SoftFrame 16695, WiFi 9.0.0.p3 2097), FreeRTOS, AFR 4.0.0, lwIP 2.1.2, mbedTLS | CONFIRMED (mbedTLS — одна строка, без версии) |
| 4 | Gofinity: 1 532 кадра, CRC 100%, триплет = наш, handoff 106/107, demand 646, 0x78, 0x0E без ответа | CONFIRMED (в прозе ноты — опечатка 3E10 вместо 3E0A) |
