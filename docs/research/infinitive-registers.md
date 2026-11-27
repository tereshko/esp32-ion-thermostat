# infinitive (lurgh fork) — register extract & delta vs our protocol map

Harvested 2026-11-26 at the author's instruction («Бери эти данные и сохраняй.
Будем использовать»). Repo: https://github.com/lurgh/infinitive (живой форк
acd/infinitive, Go), cloned read-only into
`firmware-re/external/infinitive/` (текстовый анализ; код не запускался).

**License: MIT**, © 2016 Andrew Danforth (файл `LICENSE` в корне репозитория).
Код и данные можно переиспользовать с сохранением copyright/permission notice.
Сами факты форматов/раскладок лицензией не ограничиваются.

**Поколение — главная оговорка.** infinitive написан и тестируется на
**pre-Touch** контролях (UID/UIZ) в роли SAM (адрес 0x9201), тестовая система
автора — 2 зоны, 2-ступенчатая газовая печь, 2-ступенчатый компрессор
(README, «Protocol Notes»). Раскладки ниже — канонические SAM-таблицы; на
нашем Touch Ion доступность полей упирается в регистрацию SAM (наши стадии
C/D: незарегистрированному SAM Ion отдаёт нули). Issue #14 в репозитории:
автор прямо пишет, что на Touch не тестировалось; wire-протокол ABCD тот же,
«some differences in features and, evidently, data representation».

**Метод сверки.** Каждое утверждение проверено по коду/тексту репозитория
(не по сводке свип-агента), а затем сведено с двумя нашими источниками:
`THERMOSTAT-PROTOCOL-MAP.md` (захваты, 26,5 тыс. кадров) и локальной копией
InfinitESP (`infinitesp/components/infinitesp/infinitesp.h` — в ней есть
точные офсеты REG3B02_*/REG3B03_*/REG3B04_*, которых не было в [SRC] на
момент карты протокола). Ключевой результат сверки: **раскладки infinitive и
InfinitESP совпадают побайтово со сдвигом ровно +3** — InfinitESP считает
офсеты от начала тела регистра (первые 3 байта тела: [0] active-zones/zone,
[1..2] change flags), infinitive парсит структуру после 6-байтового заголовка
ответа (3 байта таблица + те же 3 байта), поэтому его офсеты на 3 меньше.
Размеры тел совпадают полностью: 3B02 = 29 B, 3B03 = 150 B, 3B04 = 11 B —
ровно те длины, что наш Ion отдаёт SAM в захватах (карта, §b).

---

## 1. Кадр и транспорт (frame.go, protocol.go)

- Адреса 16-битные: термостат `0x2001`, SAM `0x9201`, IDU `0x4001`,
  broadcast `0xF1F1`; снуп-диапазоны: ODU/HP `0x5000–0x51FF`, IDU
  `0x4000–0x42FF`, зонные контроллеры `0x6001/0x6101`.
- Кадр: dst u16 BE, src u16 BE, len u8, `00`, `00`, op u8, data,
  CRC-16 (poly 0x8005, reflected, init 0x0000) — оверхед 10 байт, шина 38400.
- Op-коды: RESPONSE `0x06`, READ `0x0B`, WRITE `0x0C`, ERROR `0x15`.
- SAM-клиент infinitive: таймаут ответа 500 мс, до 5 повторов.
- Ответ на READ: data = таблица (3 B) + префикс (3 B) + тело; для таблиц
  3Dxx префикс 1 байт (парсер пропускает 4, а не 6 — protocol.go, `reginfosz`).
- Когда термостат пишет SAM-у, infinitive (как SAM) отвечает RESPONSE с
  data = `{0x00}` (protocol.go, `writeAck`).

## 2. Раскладки регистров

Офсеты ниже — от начала тела регистра (конвенция InfinitESP / нашей карты);
в скобках — офсет в структуре infinitive (= наш минус 3).

### 3B02 — SAM state, тело 29 B (tables.go, `TStatCurrentParams`)

| Офсет | Поле | Семантика |
|---|---|---|
| 0 | active zones bitmask | (нет в infinitive — пропускается в префиксе) |
| 1–2 | change flags u16 BE (в записях) | см. §3 |
| 3–10 | zone current temp [8] u8 | целые градусы в единицах термостата |
| 11–18 | zone humidity [8] u8 | %RH |
| 19 | unknown | |
| 20 | outdoor air temp u8 | целые градусы |
| 21 | zone unoccupied bitmask | |
| 22 | **stagmode byte** | high nibble = stage, low nibble = mode |
| 23–24 | unknown / sched period | infinitive: DispSchedPeriod @20 |
| 25 | weekday | |
| 26–27 | minutes since midnight u16 BE | |
| 28 | displayed zone | |

Mode (low nibble, conversions.go `rawModeToString`): 0 heat, 1 cool, 2 auto,
3 electric (fan-coil; на печи, возможно, furnace-only — untested у автора),
4 heatpump, 5 off. Stage (high nibble / `Mode >> 5` в коде infinitive —
фактически старшие биты байта): 0 idle, 1/2 cooling, прочее heating
(`rawActionToString`, грубая эвристика автора). Цифра ступеней в stage —
та же семантика, что MODE? из SAM-спеки (COOL2).

### 3B03 — SAM zones, тело 150 B (tables.go, `TStatZoneParams`)

| Офсет | Поле |
|---|---|
| 0 | active zones bitmask |
| 1–2 | change flags u16 BE (в записях) |
| 3–10 | fan mode [8] u8: 0 auto, 1 low, 2 med, 3 high |
| 11 | zones holding bitmask (permanent hold) |
| 12–19 | heat setpoints [8] u8 — целые градусы, без масштабирования |
| 20–27 | cool setpoints [8] u8 — целые градусы |
| 28–35 | target humidity [8] u8 % |
| 36 | infinitive: `FanAutoCfg`; InfinitESP: `speed_controlled_fan` (ярлык Infinitude, unverified) — один и тот же байт, имя спорно |
| 37 | timed-hold state bitmask: infinitive `ZOvrdState` («hold until», совпадает с SAM S1Z1OVR); InfinitESP: «bit N = zone N+1 countdown running (verified 2026-08-27)» — описания сходятся |
| 38–53 | hold/override durations [8] u16 BE, минуты |
| 54–149 | zone names [8] × 12 chars |

### 3B04 — SAM vacation, тело 11 B (tables.go, `TStatVacationParams`)

[0–2] префикс/флаги, [3] Active (0/1), [4–5] Hours u16 BE,
[6] MinTemperature, [7] MaxTemperature, [8] MinHumidity, [9] MaxHumidity,
[10] FanMode. Полностью совпадает с read-format в InfinitESP
(«Active at [3], hours BE16 at [4..5]», флаги REG3B04_FLAG_* по тем же
офсетам). Дни в API infinitive = ceil(hours/24); InfinitESP добавляет:
термостат на readback показывает **принятое** значение, на day-flooring
семействах длительность округляется вниз до суток (команда 36 ч читается
обратно как 24).

### 3B06 — settings/dealer, размер спорный: 49 B (infinitive) vs 52 B (InfinitESP)

Первые 7 байт совпадают у обоих: [0] backlight, [1] спорный байт (см.
конфликты), [2] unknown, [3] deadband, [4] cycles per hour,
[5] schedule periods, [6] programs enabled. Дальше расходятся:
infinitive — [7] TempUnits, [8] unknown, [9] DealerName[20], [29] DealerPhone[20];
InfinitESP (наследовано из Infinitude CarBus::SAM, в основном unconfirmed) —
[12] dealer name[20], [32] dealer phone[20], размер 52.
README infinitive (про 3B06): «numbers probably correspond to settings from
the UI/SAM such as filter reminder, UV reminder, Humidifier reminder,
Backlight, units F/C, auto mode enabled, sys heat/cool/heatcool, deadband,
cycles/hr, programmable fan option» — это догадка автора, не раскладка.

### 3B07–3B0D — расписания, 7 таблиц × 160 B (только README, кода нет)

Источник: README, «Protocol Notes»: «Register 3b.07 - 3b.0d: seven 1-day
schedules each corresponding to a day of week, encoded in 160 bytes as:
for each of 8 zones → for each of 4 time periods → uint16 start time
(min past midnight), uint8 heatSP, uint8 coolSP, uint8 0xff (optional fan
setting or placeholder for it?)». Проверка арифметики: 8 × 4 × 5 = 160 ✓.
Единицы уставок в README не названы (по аналогии с 3B03 — целые градусы).
Заявка свипа подтверждена дословно; оговорка: в коде infinitive расписания
не реализованы («No access is provided for the scheduling features»),
раскладка существует только как текст README.

### 3Cxx — наблюдения из README (раскладок нет)

- 3C03: «semi-random garbage remnants of other response data» (буферный мусор).
- 3C0A: список 8 имён зон (повторяет имена из 3B03) + нулевой паддинг.
- 3C0B: неясные, но стабильные значения. 3C0C: все нули.
- 3C0D: байты 01–02 инкрементятся ежечасно, стоп на 870 (90 дней) — похоже на
  счётчик часов; пример кадра приведён в README.
- 3C0E: паттерны как 3C0D, не менялся днями. 3C0F: последний байт — часы с
  полуночи, предпоследний — дни (база неясна). 3C14: стабилен днями.
Не путать с RAM-пространством словаря 0x3Cxxxxxx из стадий E/G — это разные
«3C»: здесь шинные таблицы термостата 003Cxx.

### 3D02 — живые температуры зон (tables.go, `TStatTemps` + README)

Читается с термостата. Ответ: таблица (3 B) + байт 0xA5 + 8 зон × 5 B:
flags u16, raw temp u16, smoothed temp u8. Raw: значение = BE16 / 16
(в коде `Temp16[0]*16 + Temp16[1]/16` — та же величина), точность 1/16°;
smoothed — целое для дисплея, «smoothed and not just rounded».
Пример из README: зона 1: flags `0101`, raw `046F` = 70.94°, smoothed `46` = 70;
зона 2: flags `0104`, raw `0462` = 70.13°, smoothed 70. Флаги зон
(0x0101, 0x0104) автор не декодировал («may indicate Tstat, Temp Sensor,
Smart Sensor»).
**Touch-ограничение (InfinitESP README, §Zone temperature sourcing):**
контроли touch-поколения 3D02 **не отдают** («Controls that refuse 3D02
(the touch-generation line, our SYSTXCCITC01 among them)»); InfinitESP
опрашивает 3D02 в медленной ротации и перестаёт после 5 пустых чтений.
Для нашего Ion таблица мертва, раскладка — legacy-справочник и модель того,
что эмулятор 0x20 *мог бы* отдавать SAM-клиентам.

### 3D03 — живые actuals: OAT + влажность (только README)

Пример: `003d03 a5 01 0337 0100 31 00 31 a5a5a55a5aa5` (тело 15 B).
По диаграмме README: байт 0xA5, `01`, OOOO = OAT ×16 BE (`0337` = 51.4°),
далее `0100` (не подписано), HH = indoor humidity smoothed %RH (`31` = 49),
`00`, HR = indoor humidity raw %RH (`31`), хвост — филлер A5/5A.
В коде infinitive структуры нет: 3D03 опрашивается сырым `getRawData`
в ротации монитора (main: rawMonTable = 3B05, 3B06, 3B0E, 3B0F, 3D03;
закомментированный расширенный список включает 3C01, 3C03, 3C0A–3C0F,
3C14, 3D02, 3D03).

### 0306 / 0316 — IDU (снуп ответов печи, infinitive.go `attachSnoops`)

- 0306: blower RPM = BE16 @ [1..2] тела ответа.
- 0316 (14 B): [0] heat stage; **[2] cooling flag** (биты 0–1: ≠0 → cooling;
  в примере README `02` = cooling on); [4..5] airflow CFM BE16;
  [7..8] static pressure BE16 / 65536 (шкала 0..1, у автора — с округлением
  до 4 знаков). ElecHeat = `[0] & 0x03 != 0`; Action: heating если
  `[0]&0x03`, cooling если `[2]&0x03`, иначе idle.
  Разобранные примеры: лог README — ответ `000316 00 00 00 00 03BA 00 4A2F
  78 01 00 03 7A`: stage 0, CFM 0x03BA = 954, SP 0x4A2F/65536 ≈ 0.290.
  Protocol Notes — `000316 00 00 02 00 02C1 00 4DE9 5A 01 00 02 03`:
  HS [0] = 0, CC [2] = 02, CFM = 0x02C1 = 705, SP ≈ 0.304.

### 0319 — положения заслонок (tables.go, `DamperParams`)

Ответ на READ 00319 от зонных контроллеров (0x6001/0x6101): 8 байт позиций,
по одному на зону; 0xFF = зоны нет. Первый контроллер несёт зоны 1–4,
второй — 5–8 на своих позициях. Шкала позиции: infinitive публикует
`pos * 100 / 15` процентов (pos 0–15 → 0–100%).

### 3E01 / 3E02 — наружный блок / тепловой насос (снуп, infinitive.go)

- 3E01: outside temp = BE16 [0..1] / 16; coil temp = BE16 [2..3] / 16.
- 3E02: stage = [0] >> 1.
InfinitESP подтверждает роль 3E01: «register 3E01 on two-capacity units»
несёт OAT наружного датчика в 1/16 °F (на variable-speed — 0302).

### 041F — термостат → smart sensor, WRITE (только README)

Пример: `00041f 10 03 00000000 42 52 000004000000000000000000` (тело 20 B).
По диаграмме README: TP = program time period зоны (0 Wake … 3 Sleep) —
байт со значением `03` в примере; HS = heat setpoint (`42` = 66);
CS = cool setpoint (`52` = 82). Уставки — целые градусы (66/82 осмысленны
только как °F на системе автора). Точные офсеты TP/HS/CS в диаграмме
показаны позиционно, не численно — помечаю как «по диаграмме README».

### 0420 — broadcast термостата на F1F1, WRITE (только README)

Пример: `000420 c002c0000f01 056b 0102 2f 3c5000405600000000` (тело 20 B).
TTTT @ байты 6–7 тела = outdoor temp ×16 BE (`056B` = 86.7°);
HH @ байт 10 = indoor humidity %RH (`2F` = 47). Остальные байты автором
не подписаны.

## 3. Диалект записи (field flags) — infinitive и InfinitESP совпадают

Запись таблицы = READ-модель наоборот: кадр WRITE, data = таблица (3 B) +
тело, где байт [0] тела — зона/активные зоны, байты [1..2] — change flags
u16 BE; применяются только поля, отмеченные флагами. Биты флагов
(infinitive `putConfig`/`putZNConfig` и InfinitESP `infinitesp.h`
CHANGE_* — **идентичны**):

3B03: fan 0x01, hold 0x02, heat SP 0x04, cool SP 0x08, override 0x80.
3B02: mode 0x10, weekday 0x80, minutes 0x100, displayed zone 0x200.

Отсюда декодируются наши собственные захваты (карта, §b): SAM писал 3B03
со словами `00000C` = флаги 0x000C (heat+cool setpoints, без всего
остального) и 3B02 с `000010` = флаг 0x0010 (только mode). Карта называла
их «mode words» — теперь у них есть точная семантика.

Семантика hold/override (infinitive.go):
- ZoneHold (бит зоны в [11]) = permanent hold; ZOvrdState ([37]) = активный
  «hold until» отсчёт; ZOvrdDuration ([38..]) = оставшиеся минуты,
  потолок 1439 (23:59).
- Флаг 0x80 выставляет таймер override независимо от уставок.
- Запись длительности 0 «сырым» путём override надёжно не снимает —
  infinitive переводит API-«0» в запись ZoneHold=false.
- InfinitESP добавляет модель Touch: «a 3B03 notification write (with
  change flags) primes the thermostat, then a direct data write delivers
  the actual values. Both are required. Neither alone works»
  (README InfinitESP, §Mode and setpoint changes).

## 4. Откат часов при записи глобальных параметров

Источник 1 — README, §«Changing global parameters» (строки 629–635):
«changing global parameters including operating mode (heat/cool/auto/off),
as well as some experimental and future ones that are set via the same bus
register (displayed zone, day of week, unoccupied zones), has a side effect
of setting back the system clock by up to one minute. This was discovered
when automating changes to the operating mode multiple times per day, and
the thermostat would lose a couple minutes more each day.»

Источник 2 — infinitive.go, `putConfig` (комментарий у строки 393):
«setting these parameters can make our thermostat lose up to 1 min of time
keeping so we include a time/day setting with every command; adding 30s
helps in rounding to the nearest minute given truncation to one-minute
resolution». Компенсация в коде: каждая запись глобального параметра
добавляет DispDOW + DispTimeMin = время хоста + 30 с, флаги |= 0x180.

Механизм (по объяснению автора): термостат хранит время с минутной
гранулярностью; запись полей 3B02 заставляет его перечитать/перезаписать
время с усечением — теряется до минуты на запись. Метрика контроля —
`infinitive/dispTimeDiff`: перекос минут термостата против хоста
(−720…+719, README строка 495).

Для нас: наши записи режима идут через 400A, а не 3B02, — эффект напрямую
не бьёт. Но любой будущий путь записи mode/DOW/time через 3B02 (диалект
InfinitESP sync_clock — одиночная запись 3B02) должен учитывать цену
до −1 мин на запись и/или закладывать компенсацию в стиле +30 с.

## 5. Дельта против THERMOSTAT-PROTOCOL-MAP.md

### CONFIRMS (подтверждает наше, независимо)

1. **0316**: офсеты heat stage [0], CFM [4..5], static pressure [7..8] —
   побайтово как в карте ([SRC]); плюс два разобранных живых примера.
2. **0306**: blower RPM BE16 @ [1..2] — как в карте.
3. **Размеры SAM-таблиц**: тела 3B02/3B03/3B04 = 29/150/11 B — ровно
   «served payload» из наших захватов; раскладки infinitive и InfinitESP
   совпадают со сдвигом +3 (заголовок), т.е. формат один.
4. **Флаги записи**: слова `00000C`/`000010` в наших захватах SAM-записей
   декодируются флаг-таблицей infinitive/InfinitESP (см. §3).
5. **Уставки 3B03 — целые градусы без масштаба**: код infinitive пишет
   uint8 напрямую; наши захваченные байты SAM-записей (0x4F=79, 0x45=69,
   0x41=65) осмысленны только так. InfinitESP: 3B02 «quantizes to whole
   degrees in its display unit».
6. **Только 06/0B/0C на практике**: infinitive определяет opERROR 0x15 в
   frame.go, но живых приёмов не показывает; InfinitESP (заголовок таблиц
   IDU/ODU) независимо документирует ответы FUNC 0x15 на чтение
   отсутствующих таблиц — 0x15 в диалекте существует (направление
   устройство→термостат при битом чтении), в нашем архиве просто не
   триггерился (наш G9 остаётся открытым по нашему железу).
7. **3E01 как источник OAT ×16** на двухступенчатых ODU (InfinitESP —
   та же роль); у нас variable-speed ODU, OAT едет в 0302 TLV — как в карте.

### ADDS (у нас этого не было)

1. **Полные полевые раскладки 3B02, 3B03, 3B04** (карта знала только
   размеры и «нули незарегистрированному»). Включая stagmode-байт 3B02
   [22]: mode = low nibble (0/1/2/3/4/5 = heat/cool/auto/electric/
   heatpump/off), stage = high nibble.
2. **Расписания 3B07–3B0D**: 7 дней × 160 B, формат периодов
   (u16 start-min, heatSP, coolSP, 0xFF). В карте отсутствовали полностью.
3. **3D02/3D03**: живые температуры зон ×16 + smoothed, OAT ×16 +
   влажность raw/smoothed. Оговорка: на Touch 3D02 не отдаётся (InfinitESP).
4. **0316 cooling flag [2]** и ElecHeat = [0]&0x03; формула static pressure
   /65536. В карте 0316 был только [SRC]-минимум без [2].
5. **0319 damper positions** — целый класс устройств (зонные контроллеры
   0x6001/0x6101), шкала ×100/15 %.
6. **3E01/3E02** раскладки ответов ODU (coil/OAT ×16, stage = [0]>>1).
   У нас в карте 3E02 мелькал только как boot-broadcast 1 B.
7. **041F** семантика: WRITE термостата смарт-сенсору (период программы,
   heat/cool setpoints зоны). В карте 041F — только цель пробинга 1F.
8. **0420** broadcast термостата на F1F1: OAT ×16 + indoor RH. В карте из
   broadcast-ов были только SYSTIME 0202/0203.
9. **3C0A** — таблица имён зон; 3C0D/3C0F — счётчики часов/дней
   (наблюдения без полной раскладки).
10. **Диалект записи целиком** (§3): флаги полей, hold vs timed-override
    семантика, потолок override 1439 мин, квирк «0 не снимает override».
11. **Откат часов ≤1 мин на запись глобальных параметров 3B02** (§4)
    + компенсация автора (+30 с, флаги 0x180 в каждой записи).
12. **SAM-тайминги клиента infinitive**: ответ ≤500 мс, 5 повторов —
    заметно строже SAM-спеки (≤5 с); для эмулятора ориентир — infinitive.
13. **3B05/3B0E/3B0F в ротации сырого мониторинга** infinitive — таблицы
    существуют и опрашиваются, раскладок у автора нет (3B05 у нас
    декодирован InfinitESP: filter/UV/humidifier life % и reminder-флаги
    @ [3..10], размер 11 — здесь уже мы впереди).

### CONFLICTS / напряжения (и чья сторона сильнее)

1. **Единицы уставок 3B03.** Infinitude (через GitLab-свип) утверждает
   «активные уставки 3B03 — целые °C». infinitive: масштаба нет вообще,
   значения — в единицах, сконфигурированных на термостате (TempUnits
   читается из 3B06; issue #6 подтверждает unit-agnostic поведение и что
   путаница была на стороне HA). Наши захваты: байты 79/69/65 — °F.
   **Вердикт: прав infinitive — целые градусы в настроенных единицах;
   формулировка Infinitude описывает °C-сконфигурированную систему.**
   (400A — полуградусы °C по InfinitESP, другая таблица, конфликта нет.)
2. **3B06: байт [1] и офсеты дилера.** infinitive: [1] = AutoMode,
   [7] = TempUnits, имя @9, размер 49. InfinitESP: [1] = metric_units
   (0=English, 1=Metric; «live-test backing», зеркало @10),
   [7] на Touch наблюдается 0xFF, имя @12, размер 52.
   **Вердикт: по байту [1] сильнее InfinitESP (живой тест против ярлыка
   без подтверждения); по офсетам дилера — unresolved, обе раскладки
   на Touch не подтверждены.**
3. **Байт 3B03 [36].** infinitive `FanAutoCfg` vs InfinitESP
   `speed_controlled_fan` (ярлык Infinitude, unverified у обоих).
   Офсет один, семантика не доказана ни одной стороной.
4. **Нотация адресов.** infinitive: 16-битные (0x2001/0x4001/0x9201/
   0xF1F1), IDU-диапазон снупа 0x4000–0x42FF. Наша карта пишет адреса
   одним байтом (0x20/0x44/0x53/0x92/0xF1), как их отдаёт наш захват.
   Это разница записи, а не протокола (в issue #14 cardump на Touch
   показывает те же 0x2001/0x4201 в сыром потоке), но константы из кода
   infinitive в наш стек переносить без сверки ширины адреса нельзя.
5. **ACK на запись.** infinitive-как-SAM отвечает на WRITE термостата
   RESPONSE `{0x00}`; наш Ion на записи SAM→термостат не отвечает вообще
   (карта §b). Не конфликт: разные направления и роли; фиксирую, чтобы
   эмулятор 0x20 не ждал ACK от Ion и не удивлялся ACK-ам настоящего SAM.

## 6. Что сохранено

- Репозиторий целиком: `firmware-re/external/infinitive/` (клон 2026-11-26).
- Этот файл: раскладки, диалект записи, откат часов, дельта против карты.
- Ключевые источники внутри репозитория: `tables.go` (структуры),
  `conversions.go` (mode/fan enum), `frame.go` + `protocol.go` (кадр,
  заголовки ответов, writeAck, тайминги), `infinitive.go` (снупы
  0306/0316/0319/3E01/3E02, putConfig и компенсация часов ~строка 393),
  `README.md` §Protocol Notes (расписания, 3Cxx, 3D02/3D03, 041F, 0420)
  и §Changing global parameters (откат часов).
