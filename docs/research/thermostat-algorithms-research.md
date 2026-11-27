# Thermostat control-algorithms research (2026-11-26)

How production residential thermostats actually control HVAC — algorithms, protections, specifications — compared function-by-function (26 functions) against this project's DIY layer, with the implementation plan that phase 6 was built from. Full report below, in Russian.

# Как реально работают жилые термостаты HVAC: алгоритмы управления, защиты и спецификации — и сравнение с DIY-слоем поверх Carrier/ICP Ion

## Резюме

Главный вывод: современный термостат — это не «включить при −0,5°, выключить при +0,5°». В серийных изделиях поверх простого вызова тепла/холода лежат как минимум девять слоёв: (1) пропорционально-интегральное или TPI-управление циклом вместо чистого гистерезиса, (2) ограничение частоты циклов CPH, (3) минимальные времена включения/выключения и защита компрессора, (4) таймеры и droop ступеней, (5) обучаемая рампа восстановления, (6) семантика hold/расписания/occupancy, (7) влажность с outdoor-reset, (8) вентилятор/вентиляция по минутам в час, (9) failsafe при потере датчика, питания и связи. В conventional (24 VAC, клеммы W/Y/G) системе почти всё это живёт в термостате. В communicating системе типа Carrier Infinity/Ion — разделяется: настенный контроль — «командный центр» и источник уставок/режимов, а плата печи/наружного блока исполняет розжиг, продувки, задержки вентилятора, лимиты безопасности и, для инвертора, модуляцию мощности. Источник: Carrier Infinity — компоненты «continually communicate … via a four-wire connection called the ABCD bus», а «All system components are controlled through the wall-mounted Infinity Control» — https://itsmanual.com/carrier/systxccuid01-v-infinity-control-thermostat/ (index, прочитано 2026-11-26).

Для описанного DIY-слоя (ESP32 + Home Assistant, только запись heat/cool уставок в таблицу comfort-профилей Ion, только при manual/hold, без байта режима) это означает: большинство защитных алгоритмов ему **не нужно и нельзя** дублировать — они уже живут ниже, в Ion и в плате печи. Реальные пробелы DIY-слоя лежат выше: адаптивное восстановление, occupancy-setback с гистерезисом по времени, outdoor-reset влажности (косвенно, через уставку), TOU pre-cool/pre-heat, усреднение/взвешивание сенсоров с плавным переходом, контроль «залипания» и freeze-мониторинг с алармом. Подробно — сравнительная таблица в конце.

Обозначения: **[подтверждено]** — значение из мануала/официальной поддержки производителя; **[не подтверждено]** — источник не найден, значение не выдумывается.

---

## 1. Базовое управление: гистерезис, CPH, PID/TPI, min on/off

### 1.1 Гистерезис / swing / differential

Механизм: термостат включает оборудование не точно на уставке, а при отклонении на величину differential, и выключает при возврате к уставке (или за неё). Это предотвращает дребезг реле и короткие циклы.

- ecobee: **Heat Differential Temperature по умолчанию 0,5°F** — «minimum temperature differential before engaging heating» при ручной настройке staging; Cool Differential — Auto по умолчанию. Источник: ecobee Smart Thermostat Premium, Threshold Settings — https://thermostat.guide/ecobee/ecobee-smart-premium-thermostat-user-guide/ и официальная страница https://support.ecobee.com/s/articles/Threshold-settings-for-ecobee-thermostats (index, 2026-11-26) **[подтверждено]**.
- Siemens RDS110 (европейский on/off): гистерезис **0,5°C** — останавливает нагрев при +0,5°C выше уставки, запускает при −0,5°C ниже. Источник: https://sid.siemens.com/r/A6V10877569/20569912331_20569980683__en-US_13587374347 (index) **[подтверждено]**.
- EPH Controls (Великобритания/Ирландия, OpenTherm-термостаты): switching differential в Normal-режиме **0,4°C**. Источник: EPH COMBIPACK4 manual — https://manuals.plus/m/32217304b3b75ff0df024df899f5e65103070508b52b4007c6609bc7a13330bb.pdf (index) **[подтверждено]**.
- Honeywell VisionPRO/T-серии нового поколения: пользовательский «swing» как таковой убран — Product Data прямо говорит: алгоритм фиксирует **deadband 0°F** между включением и выключением цикла, а точность удержания обеспечивается P+I (см. 1.3). Источник: Honeywell Home T5+ Product Data — https://www.manualslib.com/manual/2325050/Resideo-Honeywell-Home-T5Plus.html?page=6 (index) **[подтверждено]**.

Итог по диапазону: у электронных термостатов дифференциал включения обычно **0,5°F (≈0,3°C) … 1°F**, а не 2–3°F, как у старых биметаллических. Больший видимый «swing» в доме создаётся не дифференциалом, а тепловой инерцией и CPH-логикой.

### 1.2 Cycle rate — CPH (cycles per hour)

Механизм Honeywell: вместо чистого гистерезиса термостат стремится выдержать заданное число циклов в час **при 50% нагрузке**; длительность on/off внутри часа подстраивается P+I-логикой. Меньше CPH — длиннее циклы, лучше для тяжёлых/инерционных систем и компрессора; больше CPH — точнее температура, но больше пусков.

Заводские значения Honeywell (installer setup, Pro 3000 / VisionPRO TH8000):

| Оборудование | CPH по умолчанию |
|---|---|
| Газ/масло печь <90% эффективности | **5** |
| Пар / гравитационные системы | **1** |
| Горячая вода и печи ≥90% | **3** |
| Электропечь | **9** (в части серий 6) |
| Компрессор, 1-я и 2-я ступень | **3** («Recommended for most compressors», варианты 1,2,4,5,6) |
| Aux / Emergency heat | как у heat: 5 / 1 / 3 / 9 |

Источник: Honeywell Pro 3000 Installation Instructions — https://thermostat.guide/honeywell-home/honeywell-home-pro-3000-non-programmable-digital-thermostat-installation-instructions/amp/ ; VisionPRO TH8000, функции 0220–0260 — https://archive.org/download/manualsbase-id-586048/586048.pdf (index, 2026-11-26) **[подтверждено]**. Диапазон настройки heat CPH в VisionPRO IAQ: 1–12 CPH, cool: 1–6 CPH — https://manuals.plus/m/f06dcb8f45c0c8d100a9583c205dc6fe6419e3b25b889c61701ff5d9a08f39e2 (index) **[подтверждено]**.

### 1.3 P+I у Honeywell и PID/TPI в Европе

**Honeywell P+I.** VisionPRO Product Data: «proprietary algorithm … eliminates … offset (droop)», алгоритм назван **proportional plus integral (P+I) control**: proportional error = уставка минус измеренная температура; integral error накапливается по времени отклонения; сумма определяет длительность включения ступени внутри цикла. Заявлено удержание «within 1 degree of the setpoint» в Comfort-режиме staging. Источник: https://www.manualslib.com/manual/1389597/Honeywell-Visionpro-8000.html?page=52 (index) **[подтверждено]**. Классический droop механического термостата с heat anticipator в мороз мог достигать **5–6°F** отклонения эффективной точки от уставки — именно это P+I и устраняет; источник: Honeywell Chronotherm T8621 — https://www.manualslib.com/manual/69807/Honeywell-Chronotherm-T8621a.html?page=28 (index) **[подтверждено]**.

**Европейский TPI (Time Proportional & Integral).** Механизм иной внешне, родственный по сути: пока температура вне пропорциональной полосы, котёл работает непрерывно; внутри полосы термостат начинает **циклировать on/off с фиксированным периодом**, а скважность (доля on внутри периода) пропорциональна ошибке плюс интегральная поправка — так тепловая мощность «дозируется» без модуляции горелки.

Конкретные настройки EPH Controls RFRP-OT / CP4M (типичная британская Boiler Plus практика):

- Число циклов в час: **выбор 2 / 3 / 6 / 12, по умолчанию 6** (т.е. период 10 мин при 6 CPH).
- Proportional Bandwidth (Pb): **по умолчанию 2,0°C, диапазон 1,5–3,0°C с шагом 0,1°C** — это отклонение ниже уставки, с которого начинается TPI-циклирование.
- Optimum Start (родственник adaptive recovery, см. §3): параметр Ti = **10 / 15 / 20 мин на 1°C** подъёма, максимум раннего старта **180 мин (3 ч)**.

Источник: EPH COMBIPACK4 / CP4M manuals — https://www.manualslib.com/manual/1758450/Eph-Controls-Combipack4.html?page=8 ; https://manuzoid.com/manuals/99WoO-EPH%20Controls%20CP4M%20Room%20Thermostat%20Installation%20guide (index) **[подтверждено]**.

Отличие TPI от гистерезиса: гистерезис задаёт **амплитуду** колебаний температуры и не управляет средней мощностью; TPI задаёт **период** и управляет средней мощностью скважностью, поэтому колебания внутри полосы малы, а перерегулирование (overshoot от остаточного тепла радиаторов) подавляется ранним отключением. Отличие от «настоящего» PID/OpenTherm-модуляции: при подключении по OpenTherm термостат может вместо on/off-циклов передавать котлу непрерывную уставку мощности/температуры подачи; TPI в мануалах EPH применяется и в on/off, и как логика поверх OpenTherm-подключения **[подтверждено по структуре мануала EPH; конкретные ID OpenTherm Data-ID в этом исследовании не проверялись — не подтверждено]**.

### 1.4 Minimum on-time / off-time (термостатный уровень)

- ecobee: **Compressor Min On Time = 5 мин**, **Heat Min On Time = 5 мин**, **Aux Min On Time = 5 мин** — заводские значения Premium. Источник: https://manuzoid.com/manuals/doXG8-ecobee%20Smart%20Thermostat%20Premium%20User%20guide (index) **[подтверждено]**.
- ecobee EMS (коммерческий): Min Cycle Off Time настраивается **240–900 с**. Источник: https://support.ecobee.com/s/articles/EMS-FAQs-Setup-Guide-and-Troubleshooting?language=en_US (index) **[подтверждено]**.

---

## 2. Защита оборудования

### 2.1 Защита компрессора от коротких циклов

- Honeywell: **5-минутное минимальное время выключения компрессора** — опция installer setup «5 = Five-minute compressor off time» против «0 = No compressor off time»; на дисплее в это время мигает Cool On / «Wait», подсказка troubleshooting: «Wait up to five minutes». Источники: Pro TH2000 manual — https://ia801903.us.archive.org/0/items/manualsbase-id-585732/585732.pdf ; Honeywell Store troubleshooting — https://www.honeywellstore.com/store/product-support/honeywell-thermostat-not-working.htm (index) **[подтверждено]**. Уточнение из вторичного разбора по мануалам Resideo: в ряде серий ISU позволяет 0–5 мин, но заводское/рекомендуемое — 5 мин **[подтверждено частично]**.
- ecobee: **Compressor Min Cycle Off Time = 300 с (5 мин)** по умолчанию. Источник: Premium Thresholds, см. выше **[подтверждено]**.
- Физический смысл: выравнивание давления хладагента перед повторным пуском; задержка срабатывает также после смены режима и после восстановления питания (см. 2.2).

Таким образом «типично 3–5 мин» из постановки вопроса уточняется: у Honeywell и ecobee заводской стандарт — именно **5 мин / 300 с**.

### 2.2 Задержка после восстановления питания

Тот же компрессорный таймер запускается при power interruption / initial startup: «for compressor protection, on initial startup, and during power interruptions the Thermostat will go into a 5 minute delay». Источник: Honeywell manual 69-1193 — https://staging.freshmanuals.com/manuals/manualsonline/brands/pages/honeywell/documents/69-1496.pdf (index) **[подтверждено]**. Carrier, по вторичному обзору его руководств, даёт **3–5 мин** и предупреждает, что выключение термостата перезапускает таймер — https://thehvacbrief.com/thermostat-says-cool-on-but-ac-not-running/ (index, вторичный источник) **[подтверждено частично]**. Отдельный «random restart delay» для разнесения пусков после блэкаута в жилых мануалах Honeywell/ecobee в этом исследовании **не подтверждён**.

### 2.3 Staging: upstage/downstage, droop, reverse staging

- **Droop-логика Honeywell (heat pump + aux):** ступень включается не по времени, а по глубине провала температуры ниже уставки. Backup Heat Droop: диапазон **2,0–15,0°F от уставки с шагом 0,5°F**; режим Comfort (droop = 0 в терминах T6) = термостат держит температуру **в пределах 1°F** от уставки, включая aux по потребности. Dual Fuel Droop Temperature по умолчанию **2°F** (варианты 2–5°F в TH8000; в IAQ — 3°F). Источники: VisionPRO 8000 Wi-Fi Product Data — https://manualmachine.com/honeywell/visionpro8000wifi/16687920-specification-sheet/ ; T6 Pro ISU 340 — https://www.manualslib.com/manual/3236674/Honeywell-Home-Lyric-T6-Pro-Wi-Fi.html?page=12 (index) **[подтверждено]**.
- **Droopless / capacity staging:** VisionPRO заявляет: 2-я ступень включается, когда 1-я ступень достигает **90% capacity** (по P+I-оценке скважности), а не по фиксированному ΔT. Источник: VisionPRO IAQ — https://manuals.plus/m/f06dcb8f45c0c8d100a9583c205dc6fe6419e3b25b889c61701ff5d9a08f39e2 (index) **[подтверждено]**.
- **Upstage timer:** Backup Heat Upstage Timer (ISU 311): **Off по умолчанию; варианты 30/45/60/75/90 мин, далее 2–16 ч**. Dual Fuel upstage to furnace (ISU 0346): **по умолчанию 1 ч**, варианты Off, 0,5, 1,5, 2–6, 8, 10, 12, 14, 16 ч — после этого компрессор отключается и дом догревает печь. Источники: те же Product Data VisionPRO (index) **[подтверждено]**.
- **ecobee Automatic staging / Aux Savings Optimization:** по умолчанию термостат сам решает staging «smart algorithms»; Aux Savings Optimization упрощённо задаёт, при каком отклонении+времени подключать aux: диапазон в Carrier-варианте ecobee Lite **2,0–3,2°F, по умолчанию 2,9°F**, при этом «heat pump would run for the minimum **60 minutes** AND delta > 2,9°F» до включения aux, а отключение aux — при возврате в пределы **2,2°F** (встроенный reverse staging). Источник: ecobee for Carrier Lite Advanced Instructions — https://assets-f02205d260.cdn.insitecloud.net/a2bec37b8b7130d/EBSTATE7ICR-01SI.pdf (index) **[подтверждено]**. В Premium Aux Savings Optimization по умолчанию указан как **2°F** — расхождение между линейками фиксируем как есть **[подтверждено, значения различаются по моделям]**.
- **ecobee Manual staging:** задаются Stage 2 Temperature Delta, Stage 1 Max Runtime, Reverse Staging (On/Off, по умолчанию **Off**) отдельно для компрессора и печи; по умолчанию большинство — **Auto**. Источник: Premium Thresholds (index) **[подтверждено]**.
- **Модулирующие/инверторные системы:** у Carrier Infinity модулирующая печь 59MN7 имеет **60 положений газового клапана**; решение о модуляции принимается communicating-системой по ABCD-шине, а не дискретными вызовами термостата. Источник (вторичный обзор по данным Carrier): https://www.aireonebarrie.ca/carrier-furnace-series-comparison/ (index) **[подтверждено частично]**. Общий принцип: инверторный наружный блок сам выбирает частоту компрессора по целевой нагрузке от wall control; термостатный «upstage timer» там заменён непрерывной модуляцией и фирменными ограничениями в прошивке оборудования — конкретные таймеры Carrier Ion в открытых мануалах **не подтверждены**.

### 2.4 Heat pump: balance point, aux lockout, compressor lockout

- ecobee Premium: **Compressor Min Outdoor Temperature: AC — 35°F**, heat pump — задаётся пользователем; **Aux Heat Max Outdoor Temperature = 35°F** в таблице Premium (aux не работает выше этой наружной температуры). В документации ecobee Lite встречается **50°F** для Aux Heat Max Outdoor — расхождение по линейкам/прошивкам, фиксируем оба. Источники: Premium guide и Lite manual — https://manuals.plus/ecobee/202428847pr-smart-thermostat-lite-manual.pdf (index) **[подтверждено с расхождением]**.
- ecobee EMS: Min Outdoor Temp диапазон **0–65°F** или отключено; одновременно служит и защитой компрессора, и точкой подключения aux. Источник: EMS guide (index) **[подтверждено]**.
- Honeywell: ISU 355 Compressor Lockout / Balance Point: **Off или 5–60°F с шагом 5°F**; ISU 356 Aux Heat Lockout: **Off или 5–65°F с шагом 5°F**; требуется наружный датчик. Источник: T5+ Product Data, ISU 355/356 — https://www.manualslib.com/manual/2325050/Resideo-Honeywell-Home-T5Plus.html?page=6 (index) **[подтверждено]**.
- Nest Heat Pump Balance: не цифра, а шкала Max Savings ↔ Max Comfort; термостат учит, при какой наружной температуре дом перестаёт удерживаться одним компрессором, и pre-heat делается через Heat Pump Balance вместо Early-On. Источник: Google Support — https://support.google.com/googlehome/answer/9244728?hl=en-CA (index) **[подтверждено качественно; числовых порогов Google не публикует — не подтверждено]**.

### 2.5 Defrost

Defrost живёт **в наружном блоке** (плата defrost / demand defrost по датчику змеевика), не в термостате. Механика: реверсивный клапан переводит цикл в охлаждение на несколько минут, наружный вентилятор останавливается, aux/strip-тепло температурит подачу, на термостате может показываться AUX. Типичная длительность **2–10 мин**; классическое окончание по датчику — змеевик ≈ **57°F**. Источники: Trane — https://www.trane.com/residential/en/resources/blog/what-is-heat-pump-defrost-cycle/ ; InterNACHI — https://www.nachi.org/defrost-cycle-heat-pump.htm ; учебный разбор — https://www.hsmuniversity.org/us/course/rac-320-air-conditioning-and-heat-pumps/lesson-3-heat-pump-defrost-and-supplementary-heat (index) **[подтверждено]**.

### 2.6 Что где живёт: conventional vs communicating

| Функция | Conventional 24V термостат | Communicating (Infinity/Ion) |
|---|---|---|
| Вызов ступеней, CPH, droop, lockout'ы | Термостат (он замыкает W1/W2/Y1/Y2) | Wall control задаёт потребность/уставки; оборудование по ABCD-шине само распределяет ступени и модуляцию |
| Розжиг, продувки, лимиты (high limit, rollout, pressure switch) | Плата печи (IFC) — всегда | Плата печи — всегда |
| Задержки вентилятора печи | Плата печи (DIP/джамперы) | Плата печи / communicating-логика |
| Defrost | Плата наружного блока | Плата наружного блока |
| Компрессорный min-off | Термостат **и часто дублируется** в наружном блоке | Оборудование + wall control |

Обоснование по плате печи — §7. По Infinity — ABCD-шина и «command center», источники выше **[подтверждено]**.

---

## 3. Адаптивное восстановление (Adaptive Recovery)

Общий механизм у всех трёх вендоров одинаков: термостат **учит скорость изменения температуры дома (°/ч) при работающем оборудовании**, с поправкой на историю погоды/наружную температуру, и каждый день пересчитывает момент старта так, чтобы уставка была достигнута **к** запрограммированному времени, а не начиная с него. Ошибка «рано/поздно» корректирует рампу следующего дня.

- **Honeywell Adaptive Intelligent Recovery (AIR):** рампа считается по расстоянию до уставки, прошлой производительности оборудования и истории погоды; для heat pump — **две рампы**: компрессора и aux; если температура не растёт достаточно быстро и пересекает вторую рампу — включается aux (это экономит aux по сравнению с conventional recovery, где aux включился бы сразу в начале периода). Настройка занимает **около одной недели**. Источник: VisionPRO 8000 Product Data, стр. 52 — https://www.manualslib.com/manual/1389597/Honeywell-Visionpro-8000.html?page=52 (index) **[подтверждено]**. Альтернатива — Conventional Recovery: старт ровно в начале периода, оборудование «как обычный термостат».
- **ecobee Smart Recovery → Pre-Heat / Pre-Cool:** официальное описание: термостат учит поведение системы нагрева/охлаждения и достигает уставки к назначенному времени; использует локальную погоду, паттерны occupancy и текущий анализ HVAC. Источники: ecobee Support, Preferences — https://support.ecobee.com/s/articles/How-to-adjust-the-preferences-on-your-ecobee-thermostat ; страница SmartSensor/функций ecobee — https://www.abt.com/ecobee-SmartSensor-2-Pack-EBRSHM2PK01/p/136159.html (index) **[подтверждено качественно; максимальный ранний старт ecobee официально не публикует — не подтверждено]**. Важная деталь: Smart Recovery/Pre-Heat не работает при бессрочном hold «until I change it» (вторичный источник, **[подтверждено частично]**).
- **Nest Early-On:** учится несколько дней; после улучшенных алгоритмов может начинать нагрев/охлаждение **до 5 часов** до запрограммированного времени (ранее лимит был 2 часа); есть настройка Max Duration для ограничения ночного раннего старта; учитывает прогноз погоды и Time-to-Temperature. Для radiant — аналог True Radiant (ранний старт + раннее выключение против overshoot), для heat pump с aux — Heat Pump Balance. Источники: Google Support (через копию страницы) — https://www.dejavu.org/cgi-bin/get.cgi?ver=96&url=https%3A%2F%2Fsupport.google.com%2Fgooglenest%2Fanswer%2F9246532 ; True Radiant — https://support.google.com/googlehome/answer/9250165?hl=en-NZ (index) **[подтверждено]**.
- **Европейский аналог — Optimum Start (EPH):** не обучающийся, а параметрический: Ti = 10/15/20 мин на 1°C, потолок 180 мин (см. §1.3) **[подтверждено]**. Это хорошая модель для DIY: простая, предсказуемая, без «чёрного ящика».

---

## 4. Расписания, holds, occupancy, сенсоры

### 4.1 Семантика hold

Honeywell (VisionPRO / T6 Pro Smart):

- **Temporary Hold / Hold Until:** держит ручную уставку **до начала следующего периода расписания** или до заданного пользователем времени; в T6 Pro Smart временный hold ограничен **максимум 12 часами**. По окончании — автоматический возврат к расписанию.
- **Permanent Hold:** держит уставку, пока пользователь вручную не отменит (Cancel / Run Schedule).
- **Vacation Hold:** уставка на **заданное число дней**, с автоматическим возвратом; в T6 Pro Smart активируется только из приложения Resideo.

Источники: VisionPRO IAQ User Manual, стр. 29 — https://www.Manualslib.com/manual/69975/Honeywell-Visionpro-68-0287-04.html?page=29 ; T6 Pro Smart User Guide — https://thermostat.guide/honeywell-home/honeywell-home-t6-pro-smart-thermostat-user-manual/ (index) **[подтверждено]**.

ecobee: **Hold Action Duration** настраивается: **2 ч, 4 ч, до следующего периода, до ручной отмены, или «спрашивать каждый раз»**. Источник: ecobee Support / разбор настроек — https://ecohomeintelligence.com/blog/ecobee-keeps-changing-temperature (вторичный, со ссылками на меню ecobee) и https://support.ecobee.com/s/articles/How-to-adjust-the-preferences-on-your-ecobee-thermostat (index) **[подтверждено]**.

Ключевой вывод для DIY: «hold» — это не состояние оборудования, а **правило истечения ручной уставки**. DIY-слой в описанной системе как раз и работает только при manual/hold у Ion — то есть Ion исполняет роль permanent hold, а вся временная семантика (истечение, resume) должна жить в Home Assistant.

### 4.2 Occupancy-based setback

- **ecobee Smart Home/Away (часть eco+):** если по расписанию Home, но occupancy не детектируется **2 часа**, термостат уходит в энергосберегающую уставку; при обнаружении occupancy уставка Home восстанавливается **в течение 30 минут**. Обратно: если по расписанию Away, но occupancy обнаружена после **минимум 1 часа** Away — переключается на Home. Ночью (Sleep) Smart Away не срабатывает. Важная деталь: Smart Away **не использует уставку Away** — выбирается уставка, из которой Home достижим за 30 минут. Источники: ecobee — https://www.ecobee.com/en-us/citizen/smart-thermostat-room-sensors-how-do-they-work-and-why-do-they-matter/ ; разбор со ссылкой на правила ecobee — https://ecohomeintelligence.com/blog/ecobee-keeps-changing-temperature (index) **[подтверждено]**.
- **Nest Home/Away Assist:** источники присутствия — геолокация телефонов всех пользователей дома **и** датчики активности в устройствах Nest; в Away термостат переходит на **Eco Temperatures**; в Eco термостат **не делает Early-On** к расписанию. Источник: Google Support — https://support.google.com/googlehome/answer/9261489?sjid=7304741177066085043-AP (index) **[подтверждено]**.
- **Geofencing как класс:** телефон пересекает радиус вокруг дома → Home/Away. Компромисс радиуса (малый — ложные Away от дрейфа GPS, большой — запаздывание) описан во вторичной литературе; конкретные радиусы вендоров официально не нормируются — **[не подтверждено для конкретных значений]**.

### 4.3 Сенсоры: усреднение, участие, Follow Me

- **Участие по периодам:** каждый Comfort Setting (Home/Away/Sleep/пользовательский) у ecobee имеет свой набор участвующих сенсоров; отображение температуры — **среднее участвующих**; каждый Comfort Setting обязан иметь минимум один участвующий сенсор; внутренний сенсор термостата можно исключить. Переход сенсоров при смене периода — **плавный, около 30 минут** (phase in/out). Источники: ecobee (index, выше) и https://myintelligenthouse.com/how-does-ecobee-smart-sensor-work-to-regulate-temperature/ (index) **[подтверждено]**.
- **Follow Me:** вместо равного среднего — взвешивание по occupancy: приоритет комнатам, где люди проводят время недавно; вес ушедшей комнаты **спадает до нуля примерно за 30 минут**; резких скачков управляющей температуры нет. Источник: ecobee / Abt product guide (index) **[подтверждено]**.
- **Honeywell:** выбор источника температуры: термостат / удалённый сенсор / **среднее термостата и сенсоров** (ISU 340 VisionPRO IAQ: 0/1/2). Источник: https://manuals.plus/m/f06dcb8f45c0c8d100a9583c205dc6fe6419e3b25b889c61701ff5d9a08f39e2 (index) **[подтверждено]**.

### 4.4 Отказ сенсора

Официальная документированная политика ecobee «при потере участвующего SmartSensor управлять по внутреннему» в открытых источниках в этом исследовании **не найдена — не подтверждено**. Наблюдаемое поведение экосистемы: сенсор помечается offline/unavailable, вычисленная occupancy считается по окну 30 мин. Для Honeywell проводных сенсоров отказ сенсора даёт код ошибки и возврат к внутреннему сенсору — **[не подтверждено по первоисточнику в этом исследовании]**. Практический стандарт де-факто, который стоит принять и для DIY: исключать молчащий сенсор из среднего и, если сенсоров не осталось, **прекращать руление** (что DIY-слой уже делает при молчании >15 мин — это строже и безопаснее вендорской практики).

---

## 5. Влажность

### 5.1 Cool-to-dehumidify / overcool

- Honeywell Prestige IAQ / T10: overcooling limit **ISU 9070: 0–3°F** ниже текущей cool-уставки (для high-speed fan конфигурации — 1–3°F); охлаждение идёт, пока не достигнута уставка влажности. Источники: https://www.manualslib.com/manual/3825097/Honeywell-Thx9421-Prestige-Iaq-2-0-With-Eim.html?page=21 ; https://www.manualslib.com/manual/3711539/Honeywell-Home-T10.html?page=95 (index) **[подтверждено]**. В одной из пользовательских документаций T10 встречается цифра «up to 5°F» — противоречие внутри линейки Resideo; installer-значение ISU 9070 (0–3°F) считаем основным **[расхождение зафиксировано]**.
- Carrier Infinity: cooling humidity — максимум NONE или **55–65% RH**, опция over-cool **до 3°F**; heating humidity — минимум **5–45% RH**. Источник: Infinity SYSTXCCWIC01-B Owner's Manual — https://www.manua.ls/carrier/infinity-systxccwic01-b/manual?p=28 (index) **[подтверждено]**. Это прямо относится к классу Ion: та же шкала, те же 3°F.
- ecobee: **AC Overcool Max** — по умолчанию **Disabled**, задаёт допустимый переохлад ради влажности. Источник: Premium Thresholds (index) **[подтверждено]**.
- Если одновременно настроены увлажнение и осушение в одном режиме, Honeywell принудительно держит **15% RH deadband** между их уставками. Источник: Prestige IAQ (index) **[подтверждено]**.

### 5.2 Увлажнитель и outdoor-reset против конденсата на окнах

Типы управления: (а) ручной гигростат — пользователь сам крутит шкалу по наружной температуре; (б) автоматический с outdoor-датчиком и «frost factor / window protection».

Классическая таблица Honeywell (рекомендуемая RH по наружной температуре):

| Наружная t | −20°F | −10°F | 0°F | +10°F | +20°F | +30°F | +40°F |
|---|---|---|---|---|---|---|---|
| Макс. RH в доме | **15%** | **20%** | **25%** | **30%** | **35%** | **40%** | **45%** |

Источник: Honeywell HE420A / HE225 Owner's Guides — https://electronicaircleaners.com/docs/honeywell_he420a_owners.pdf ; https://ia601008.us.archive.org/13/items/manualsbase-id-616860/616860.pdf (index) **[подтверждено]**.

Window Protection у Resideo ElitePRO/T10: шкала **1–10** (10 = плохо утеплённые окна, сильнее ограничивает влажность; 1 = хорошо утеплённые); термостат может выключить увлажнитель **до** достижения уставки, чтобы не было инея/конденсата; нужен наружный датчик или интернет-погода. Источник: Honeywell Home IAQ docs — https://docs.honeywellhome.com/elitepro-im/Indoor%20Air%20Quality.htm (index) **[подтверждено]**.

Carrier Humidi-MiZer Adaptive — это **не** настенная функция, а оборудование packaged rooftop: hot-gas reheat, осушение без переохлаждения за счёт перегрева; к жилым Ion прямого отношения не имеет. Источник: Carrier 18-811-055 — https://www.shareddocs.com/hvac/docs/1001/Public/03/18-811-055.pdf (index) **[подтверждено; применимость к жилой системе — нет]**. Жилой аналог у Carrier — Ideal Humidity / управление влажностью из Infinity/Ion control (см. 5.1).

### 5.3 Frost protection (влажность и температура)

Защита от инея на окнах — это §5.2. Защита труб от замерзания — §8.

---

## 6. Auto changeover

Три разных понятия, которые нельзя смешивать:

1. **Минимальное разделение уставок heat/cool (setpoint deadband).** VisionPRO IAQ ISU 310 Deadband: **по умолчанию 3°F, диапазон 2–9°F** — пример из мануала: при deadband 3°F и cool 75°F самая тёплая допустимая heat-уставка — 72°F. Источник: https://manualzilla.com/doc/7281018/honeywell-68-0287-04-thermostat-user-manual (index) **[подтверждено]**. ecobee Heat/Cool Min Delta: **по умолчанию 5°F**. Источник: Premium Thresholds (index) **[подтверждено]**. Таким образом «типично 2–3°F» из вопроса верно для Honeywell, но ecobee строже — 5°F. DIY-гард «cool ≥ heat + 3°F» попадает точно в норму Honeywell и мягче нормы ecobee.
2. **Changeover differential (T-серия Honeywell, T10):** минимальное изменение температуры, чтобы переключиться с последнего активного режима на противоположный: ISU 303, **0–5°F**; при 0 термостат скрытно применяет **1,5°F**. Пример T10: при differential 3° и обеих уставках 70°F охлаждение включится только при росте на 3° выше heat-уставки. Источники: T10 User Guide — https://lockeproductionblob.blob.core.windows.net/storage/products/attachments/2021/11/10/3ebb1c861af2e7a8a72b1636061aa251a34a2b5b430f53c37391af12d46d45e0.pdf ; T5+ Product Data (index) **[подтверждено]**. Отдельной временной «changeover delay» сверх компрессорного min-off в жилых мануалах не нормируется — фактически её роль играет 5-мин защита компрессора **[подтверждено косвенно]**.
3. **Droop** — см. §2.3: провал ниже уставки для подключения следующей ступени/aux, а не переключения heat↔cool.

---

## 7. Вентилятор и вентиляция

### 7.1 Circulation

- Honeywell **Circ**: вентилятор работает **случайно ≈33% времени** (≈20 мин/ч). Источник: T6 Pro User Guide 33-00182EFS — https://manuals.plus/m/388c60c1d1d5cdbd79df99e57bf9c643796b9e59ef7f95d0aa1bab523c88088a.pdf (index) **[подтверждено]**.
- ecobee **Fan Min On Time**: диапазон **0–60 мин/ч, по умолчанию 0** (API/настройки); руководство ecobee3: настройка 0–55 мин, термостат набирает минимум **блоками не короче 5 минут**. Источники: ecobee API — https://www.ecobee.com/home/developer/api/documentation/v1/objects/Event.shtml ; ecobee3 User Guide — https://ia801802.us.archive.org/4/items/manualzilla-id-5723690/5723690.pdf (index) **[подтверждено]**. DIY-реализация «Low, N мин/ч» концептуально совпадает с ecobee-моделью; отличие вендоров — они считают уже отработанные с вызовами минуты внутрь часового минимума, а не добавляют circulation поверх.

### 7.2 Dissipation / blower purge — где живёт

- ecobee Heat/Cool Dissipation Time: по умолчанию **Auto = печь сама решает**, сколько вентилятор дует после вызова, чтобы выгнать остаточный тёплый/холодный воздух. Источник: ecobee Enhanced manual — https://cdn.iwae.com/media/manuals/ecobee/7364-owner.pdf (index) **[подтверждено]**.
- Плата печи (Carrier-совместимый IFC, BASO CF830CA как прямой аналог HK42FZ): Heat Delay-To-Fan-On **25 с**, Heat Delay-To-Fan-Off **90/120/150/180 с, заводски 120 с**, Cool Delay-To-Fan-Off **90 с**. Источник: https://www.baso.com/wp-content/uploads/2023/03/BASO-INS-CF830CA-QRG_REVC.pdf (index) **[подтверждено]**. ICP modulating furnace manual: blower-on 25 с при max-heat / 45 с при intermediate, blower-off те же 90–180 с, заводски **120 с**, post-purge индуктора 15 с. Источник: https://www.manualslib.com/manual/977568/Icp-G9mae0601714a.html?page=35 (index) **[подтверждено]** — это прямо класс оборудования из контекста миссии.

Вывод: продувка — функция платы печи, термостат/DIY её не дублирует и дублировать не должен.

### 7.3 Вентиляция по ASHRAE 62.2 из термостата

- Норма whole-dwelling: **Qtot = 0,03 × A_floor (ft²) + 7,5 × (N_bedrooms + 1) cfm**; допускается прерывистая работа с пересчётом на средний расход, с запуском **не реже одного раза в 3 часа** (пример из учебных материалов 62.2-2016: HRV 150 cfm при потребности 50 cfm — 20 мин/ч). Локальная вытяжка: ванная **50 cfm по требованию или 20 cfm непрерывно**, кухня **100 cfm**. Источники: ASHRAE 62.2-2016 workshop materials — https://www.scribd.com/document/746560170/ASHRAE-62-2-2016-Presentation ; таблица Honeywell по 62.2-2007 — http://kitchen.manualsonline.com/manuals/mfg/honeywell/vnt5200e1000.html?p=5 (index) **[подтверждено]**.
- Реализация у ecobee: ventilator min on time отдельно для occupied/unoccupied, runtime разбивается на **15-минутные блоки**, минимум блока 5 мин; **pre-occupancy purge — 60 минут** до ожидаемого возвращения (не регулируется, только вкл/выкл). Источник: ecobee Enhanced manual (index) **[подтверждено]**.
- Взаимодействие вентилятор+увлажнение: bypass-увлажнитель работает только при работающем вентиляторе/вызове тепла; форсирование fan ради увлажнения повышает испарение, но fan On в охлаждении возвращает влагу с мокрого змеевика обратно в дом — поэтому вендоры не рекомендуют Circ/On при проблемах влажности летом **[качественно подтверждено руководствами по увлажнителям Honeywell; числовой нормы нет]**.

---

## 8. Замерзание, failsafe, стандарты

### 8.1 Safety Temperatures

- Nest: Safety Temperature нагрева **по умолчанию 40°F**, включена всегда — термостат включит тепло **даже в Off и в Away/Eco**, диапазон настройки нижней границы примерно **35–45°F**; верхняя (cooling) по умолчанию выключена. Источники: https://www.howtogeek.com/251727/how-to-turn-off-your-nest-thermostat/ ; https://www.androidpolice.com/nest-thermostat-settings-for-winter/ (вторичные, со ссылкой на Google Help; сама Google в текущих help-страницах число по умолчанию не публикует — в одном из разборов это прямо отмечено) **[подтверждено частично]**.
- Eco Temperatures Nest: heat диапазон настройки **40–70°F**, cool **76–90°F**. Источник: https://homebec.com/how-to-turn-off-eco-mode-on-nest/?amp=1 (index, вторичный) **[подтверждено частично]**.
- Honeywell: диапазон heat-уставок VisionPRO IAQ — **40–90°F**, т.е. 40°F — аппаратный пол программирования. Источник: 68-0287-04 (index) **[подтверждено]**.
- Европейские термостаты: frost protection обычно **5°C** — для EPH это значение встречается в спецификациях линейки **[не подтверждено по конкретной странице в этом исследовании — помечено как общепринятое, требует проверки по мануалу конкретной модели]**.

### 8.2 Поведение при отказах

- **Потеря связи с облаком:** ENERGY STAR требует, чтобы термостат работал как базовый термостат **без connectivity**: показ температуры, просмотр/изменение уставки, off/heat/cool локально. См. 8.4.
- **Потеря связи термостат↔оборудование (communicating):** в Infinity/Ion это диагностируемая ошибка шины; оборудование без команд wall control не поддерживает комфорт — fail-safe горения при этом обеспечивает плата печи своими лимитами, а не термостат **[качественно; конкретные коды ошибок Ion в открытых источниках не подтверждены]**.
- **Восстановление питания:** расписание и настройки хранятся в энергонезависимой памяти; компрессор — в 5-мин задержке (§2.2); часы реального времени переживают outage (VisionPRO IAQ: «real-time clock keeps time during power failures») — https://manuals.plus/m/f06dcb8f45c0c8d100a9583c205dc6fe6419e3b25b889c61701ff5d9a08f39e2 (index) **[подтверждено]**.

### 8.3 UL 60730 / IEC 60730

Ключевой и контринтуитивный факт: по таблице классов IEC 60730 Annex H **«room thermostats, temperature control» — это Class A**, т.е. функции, **не** относимые к безопасности: их отказ не должен сам по себе создавать опасность, потому что безопасность обеспечивают отдельные защитные устройства оборудования (лимиты печи, предохранители). Class B — функции, предотвращающие небезопасную работу (over-temperature shutdown и т.п.): для них требуются диагностики CPU/регистров, памяти, тактирования, программного счётчика, прерываний и **watchdog supervision**. Class C — защита от специальных опасностей, обычно двухканальная архитектура. Источники: TI, Implementing IEC 60730 / UL 1998 Compliance — https://www.ti.com/document-viewer/lit/html/SPRT759 ; обзор IEC 60730 Class B — https://geekchamp.com/guidelines-for-obtaining-iec-ul-60730-certification-for-self-test-library-implementations/ (index) **[подтверждено]**.

Практический вывод для DIY: самодельный «furnace watchdog с force Off» **не становится** средством безопасности уровня Class B от того, что он написан; наоборот, стандартная архитектура отрасли — термостатный слой Class A + независимые аппаратные лимиты в оборудовании. Watchdog в DIY имеет смысл как **комфортно-диагностическая** функция (аларм, снятие boost), а не как единственная защита от перегрева/замерзания.

### 8.4 ENERGY STAR Connected Thermostat (Smart Thermostat) v1.0

Требования, касающиеся именно поведения управления (спецификация v1.0, действует с 2017-01-01):

- Локальная работа без сети провайдера (см. 8.2).
- Статическая точность температуры **±2,0°F или лучше**.
- Сетевое standby-потребление **≤3,0 W** в среднем, время ухода в standby ≤5 мин.
- Расписание, устанавливаемое и изменяемое потребителем; обратная связь о последствиях настроек; информация о runtime HVAC.
- Demand Response: коммуникация по **открытым стандартам**, API/спецификация интерфейса для DR, и обязательный **consumer override** любого DR-сигнала.
- Полевой критерий экономии: статистически подтверждённое снижение runtime (≥8% heating по нижней границе 95% CI в методике v1.0).

Источник: сводка требований v1.0 со ссылкой на документы EPA — https://safeguard.sh/resources/blog/how-a-smart-thermostat-is-made-sensors-relays-wi-fi-socs-firmware-and-energy-data (index, вторичный разбор первоисточника EPA) **[подтверждено частично — по вторичному разбору; полный текст спецификации EPA в этом исследовании постранично не вычитывался]**. Для оборудования CAC/HP «Connected» критерии EPA прямо называют CTA-2045A и OpenADR 2.0 как пути DR-сообщений с таблицей маппинга curtailment-уровней — https://www.energystar.gov/sites/default/files/ENERGY%20STAR%20Version%206.1%20CACHP%20Final%20Specification%20and%20Partner%20Commitments%20%28Rev.%20January%20%202022%29_0.pdf (index) **[подтверждено]**.

### 8.5 Demand response / TOU на практике: ecobee eco+

- **Time of Use:** pre-cool/pre-heat в дешёвые часы, затем дрейф уставки в пике. Из рецензируемого исследования внедрения eco+ TOU (AEJ: Applied Economics, 2025): алгоритм поднимает запрограммированную уставку охлаждения в пике **на 1–4°F** в зависимости от «slider» агрессивности **1–5**; измеренный эффект — сокращение работы компрессора в пике 11:00–17:00 примерно на **44 минуты (−88%)** ценой роста среднего дискомфорта **0,20–0,25°** в пиковые часы. Источник: https://derekwietelman.github.io/files/Blonz_etal_2025.pdf (index) **[подтверждено]**.
- **Community Energy Savings:** коммунальная компания присылает события «несколько раз в год, на несколько часов»: pre-cool/pre-heat, затем небольшая корректировка уставки; пользователь может выйти из события hold'ом. Источник: ecobee eco+ — https://www.ecobee.com/en-us/eco-plus/ (index) **[подтверждено качественно]**.
- **Adjust for Humidity (eco+):** уставка фактически сдвигается так, чтобы «ощущаемая» температура соответствовала заданной при текущей влажности **[подтверждено качественно, ecobee]**.

---

## 9. Самонагрев, стенные эффекты, калибровка, размещение

### 9.1 Что делают серийные термостаты

- **Заводская калибровка и offset в прошивке:** сенсор калибруется на производстве; пользовательский/инсталляторский **Temperature Correction у ecobee: ±10°F (5,6°C)** в Thresholds. Источник: ecobee Threshold settings — https://support.ecobee.com/s/articles/Threshold-settings-for-ecobee-thermostats (index) **[подтверждено]**. Точность сенсора ecobee заявляется порядка ±1°F чувствительности **[подтверждено частично, вторичный разбор страницы ecobee]**.
- **Компенсация самонагрева электроники:** вендоры не публикуют алгоритмы компенсации самонагрева (величина сдвига, тепловая модель платы) в пользовательских/инсталляторских мануалах — **[не подтверждено]**. Косвенные меры, которые документируются: вентиляционные прорези корпуса, вынос сенсора, рекомендация дать термостату «устояться» после включения, и поле Temperature Correction как конечный инструмент. Утверждения вида «Nest компенсирует X°F самонагрева» без первоисточника в отчёт не включаем.
- **Стенной эффект / сквозняк из отверстия проводов:** документированная причина ошибок — холодный воздух из полости стены через незапечатанное отверстие проводки; лечение — герметизация отверстия. Honeywell также объясняет, что её термостаты считывают комбинацию температуры воздуха и **радиационной температуры стен/мебели** («как ощущает человек»). Источники: разборы со ссылками на Honeywell/ecobee support — https://askabouthvac.com/thermostats/why-is-my-thermostat-showing-the-wrong-temperature/ ; https://bayareahvacservice.com/blog/thermostat-reads-the-wrong-temperature-calibration-placement-and-senso/ (index, вторичные) **[подтверждено частично]**.
- **Sunblock у Nest:** функция игнорирования прямого солнца на термостат (датчик освещённости + алгоритм) — упомянута в настройках Nest Sense, Google Support — https://support.google.com/googlehome/answer/9244728?hl=en-CA (index) **[подтверждено качественно]**.

### 9.2 Правила размещения (одинаковы у всех вендоров)

- Высота **≈5 ft (1,5 м)** над полом; внутренняя стена часто используемой комнаты; хорошая циркуляция при средней температуре.
- НЕ: сквозняки/мёртвые зоны за дверями и в углах, горячий/холодный воздух из воздуховодов, радиационное тепло солнца и приборов, скрытые трубы и дымоходы, за стеной — неотапливаемое помещение/наружная стена.

Источник: Honeywell Q7300A / T10 placement — https://www.manualsLib.com/manual/529284/Honeywell-Q7300a.html?page=2 ; Carrier Infinity Control location — https://itsmanual.com/carrier/systxccuid01-v-infinity-control-thermostat/ (те же правила: ≈5 ft, inside wall, not close to window/outside wall/door) (index) **[подтверждено]**.

Для BLE-сенсоров DIY это транслируется один в один: высота груди, не над регистром, не на наружной стене, не на солнце; плюс радиотень/батарея как аналог «проводного» отказа. Калибровочный offset каждого BLE-сенсора относительно эталона — прямой аналог ecobee Temperature Correction, и его отсутствие — реальный пробел DIY, если сенсоры «из коробки» расходятся на 1–2°F.

---

## Сравнительная таблица: DIY-слой vs норма отрасли

Статусы: **Есть** / **Частично** / **Нет, реализуемо на уровне записи уставок** / **Нет и НЕ реализуемо на этом уровне**.

| Алгоритм / функция | Где обычно живёт | Статус DIY-слоя |
|---|---|---|
| Гистерезис, P+I/TPI-циклирование, CPH | Термостат (conventional) / wall control + оборудование (communicating) | **Не нужен**: Ion держит свой контур; DIY пишет только уставку. Попытка «эмулировать TPI» дёрганием уставки разрушит родной контур |
| Min on/off, защита компрессора 5 мин/300 с | Термостат + дубль в наружном блоке / оборудование | **Есть по наследству** (Ion+оборудование); DIY-гард 1 запись/10 с и no-write при молчании Ion 60 с — корректный дополнительный слой |
| Задержка после восстановления питания | Термостат/оборудование | **Есть по наследству** |
| Staging, droop, upstage timers, модуляция инвертора | Термостат (conventional) / оборудование+wall control | **Нет и НЕ реализуемо**: нет доступа к ступеням; и не нужно — Ion/плата решают по ABCD |
| Balance point, aux/compressor lockout по наружной t | Термостат с outdoor-датчиком | **Нет и НЕ реализуемо напрямую** (нет байта режима/лок-аута); косвенно — только сдвигом уставки, что не эквивалентно lockout |
| Defrost | Плата наружного блока | **Есть по наследству**, DIY не участвует |
| Adaptive recovery (AIR/Smart Recovery/Early-On, лимиты 5 ч Nest / параметрический Optimum Start 180 мин EPH) | Термостат (обучение скорости дома) | **Нет, реализуемо**: HA знает расписание и BLE-температуры — можно учить °F/ч и сдвигать момент записи комфортной уставки; это запись уставок, а не вызов оборудования |
| Расписания Wake/Leave/Return/Sleep | Термостат | **Частично**: профили есть в Ion, временная логика планируется в HA; нужно довести до полноценного расписания HA с resume-семантикой |
| Hold: temporary (до след. периода / ≤12 ч) / permanent / vacation | Термостат | **Частично**: Ion в manual/hold = permanent hold; temporary/vacation с авто-истечением в HA **реализуемо** и отсутствует |
| Occupancy setback (Smart Home/Away: 2 ч пусто → setback, возврат ≤30 мин; Away→Home после ≥1 ч) | Термостат + сенсоры / облако (геофенс) | **Нет, реализуемо**: BLE/PIR/присутствие в HA + запись Away-уставок; нужны именно вендорские временные пороги против ложных срабатываний |
| Геофенсинг | Облако + телефон | **Нет, реализуемо** в HA (приложение/зоны), вне термостатного слоя |
| Усреднение сенсоров, участие по периодам, Follow Me-взвешивание с затуханием ~30 мин | Термостат | **Частично**: руление по BLE-сенсорам есть (feedback + антиципация 80%), но нет усреднения нескольких комнат, участия по периодам и плавного 30-мин перехода между наборами сенсоров — **реализуемо** |
| Отказ сенсора → fallback | Термостат | **Есть, даже строже нормы**: молчание >15 мин блокирует записи. Не хватает fallback «управлять по оставшимся сенсорам» вместо полной блокировки при нескольких сенсорах |
| Overcool ради влажности ≤3°F (Honeywell/Carrier), AC Overcool Max ecobee | Термостат / wall control | **Частично/по наследству**: у Ion своя логика влажности; DIY может **реализуемо** добавить: при высокой RH (если есть датчик) снижать cool-уставку максимум на 3°F с обязательным возвратом |
| Outdoor-reset увлажнения (таблица −20°F→15% … +40°F→45%), Window Protection 1–10 | Термостат + outdoor-датчик | **Нет и НЕ реализуемо**, если Ion не отдаёт DIY управление увлажнителем; реализуем только аларм/рекомендация. Если Ion-профиль влажности доступен записи — становится реализуемым (в контексте миссии доступ не заявлен) |
| Auto changeover: разделение уставок | Термостат | **Есть**: гард cool ≥ heat + 3°F = норма Honeywell (3°F); ecobee требует 5°F — можно ужесточить. Само переключение режима — **НЕ реализуемо** (нет байта режима), его делает Ion |
| Changeover differential 0–5°F (скрытно 1,5°F при 0) | Термостат | **Есть по наследству** в Ion |
| Fan circulation: Honeywell Circ ≈33% случайного времени; ecobee min min/h блоками ≥5 мин | Термостат | **Есть частично**: DIY пишет blower Low N мин/ч; не хватает учёта уже отработанных с вызовами минут внутри часового минимума (модель ecobee) |
| Blower purge / dissipation (90–180 с, завод 120 с) | Плата печи | **Есть по наследству**, дублировать нельзя и не нужно |
| Вентиляция ASHRAE 62.2 (Qtot-формула, min on time occupied/unoccupied, pre-purge 60 мин) | Термостат → HRV/ERV | **Нет и НЕ реализуемо**, если у DIY нет канала управления вентилятором/ERV; fan-circulation ≠ вентиляция свежим воздухом. Реализуем только подсчёт/аларм дефицита, если появится ERV-канал |
| Freeze safety: Safety Temp 40°F даже в Off | Термостат | **Частично**: если у Ion есть собственный safety — по наследству **[не подтверждено для Ion]**. DIY-мониторинг BLE «ниже X°F → аларм» **реализуем**; активный догрев упирается в отсутствие байта режима — при hold/heat уже активном реализуем записью уставки |
| Watchdog оборудования (force Off при аварии) | Class B живёт в оборудовании (лимиты, UL 60730); термостат — Class A | **Нет и НЕ реализуемо как задумано**: заблокировано неизвестным байтом режима; и по архитектуре 60730 это не функция термостатного слоя. Реализуемый остаток: детект аварии по телеметрии Ion → аларм + снятие всех boost-записей |
| ENERGY STAR: локальная работа без облака, точность ±2°F | Термостат | **Частично**: Ion работает локально по наследству; DIY/HA при потере сети не должен оставлять «зависшую» повышенную уставку — нужен dead-man возврат к базовой уставке, **реализуемо** |
| Demand response / TOU: pre-cool + сдвиг 1–4°F в пике (eco+) | Облако + термостат | **Нет, реализуемо**: HA знает тарифные окна; pre-cool до пика и +1–4°F дрейф в пике — чистые записи уставок |
| Компенсация самонагрева сенсора | Заводская прошивка термостата | **Не применимо** к BLE-сенсорам в той же форме; применимый аналог — per-sensor calibration offset (аналог ecobee ±10°F Correction) — **нет, реализуемо** |
| Правила размещения сенсоров (1,5 м, не солнце/не регистр/не наружная стена) | Инсталлятор | **Частично**: зависит от фактического размещения BLE; чек-лист из §9.2 применим напрямую |

---

## Приоритетный список: чего не хватает, но реализуемо на уровне записи уставок

1. **Adaptive recovery по модели Optimum Start, затем обучаемая.** Сначала параметрически: измерять фактическую скорость нагрева/охлаждения по BLE (скользящая оценка °F/ч, раздельно heat/cool и по наружной температуре), стартовать запись комфортной уставки за ΔT/скорость до времени периода, с потолком раннего старта (ориентир: 180 мин EPH; 5 ч Nest — избыточен для большинства домов). Выгода: комфорт точно к времени подъёма/возврата + меньше aux/пиковой работы, чем при старте «в период». Это самый большой функциональный разрыв с серийными термостатами.
2. **Временная семантика hold в HA:** temporary hold до следующего периода (и лимит ≤12 ч по образцу Honeywell), vacation hold на N дней с авто-resume, явный «resume schedule». Выгода: устраняет класс ошибок «забытый permanent hold неделями ест энергию».
3. **Occupancy-setback с вендорскими порогами:** Away-setback только после ~2 ч подтверждённой пустоты, возврат при occupancy с восстановлением за ~30 мин, не срабатывать ночью. Выгода: экономия на ложных «уехали» без риска заморозить/перегреть дом при ложном Away; пороги ecobee — готовые, проверенные на миллионах устройств числа.
4. **TOU / demand-response слой:** pre-cool/pre-heat перед пиковым окном тарифа и дрейф уставки на 1–4°F внутри пика (шкала агрессивности 1–5 как в eco+). Выгода: по измеренным данным eco+ это −88% компрессорного времени в пике ценой 0,2–0,25° дискомфорта.
5. **Мультисенсорное усреднение с участием по периодам и плавным переходом (~30 мин) + per-sensor offset-калибровка.** Выгода: спальня ночью и гостиная днём управляют по очереди без скачков уставки; offset убирает систематические 1–2°F расхождения BLE-сенсоров, которые сейчас напрямую превращаются в ошибку регулирования (при clamp ±6°F это существенно).
6. **Учёт fan-circulation по модели ecobee:** засчитывать минуты работы с вызовами heat/cool внутрь часового минимума circulation, блоки ≥5 мин. Выгода: меньше лишних пусков blower и точнее перемешивание воздуха перед замерами BLE (улучшает качество самого feedback-контура).
7. **Humidity-aware overcool с жёстким потолком 3°F** (если в HA есть RH): снижать cool-уставку не более чем на 3°F при RH выше цели, с гистерезисом и обязательным возвратом; плюс аларм «RH высокая, а overcool исчерпан». Выгода: повторяет документированное поведение Honeywell/Carrier, а не произвольный переохлад.
8. **Freeze-мониторинг и dead-man поведение DIY-слоя:** при BLE-температуре ниже порога (ориентир 45–50°F в жилых комнатах, не 40°F — 40°F это пол для пустого дома у Nest) — аларм и, если активен heat-hold, запись защитной уставки; при потере HA/ESP32 дольше заданного срока Ion должен оставаться на последней **безопасной базовой**, а не boosted уставке (boost-записи делать самоподдерживающимися: нет heartbeat — Ion-профиль возвращается к базе средствами самого HA при восстановлении, плюс минимизировать «зависание» boost ограничением его длительности). Выгода: закрывает главный риск именно DIY-архитектуры — зависший софт с экстремальной уставкой.
9. **Ужесточение гарда разделения уставок до 5°F в Auto-режиме Ion** (норма ecobee) при сохранении 3°F, если режим heat-only/cool-only достоверно известен. Выгода: меньше риск борьбы heat/cool в межсезонье.

Что сознательно **не** делать: не эмулировать CPH/TPI дёрганием уставок, не дублировать компрессорные таймеры и продувки, не позиционировать DIY-watchdog как средство безопасности уровня UL 60730 Class B — безопасность горения и лимитов остаётся за платой печи, а force-Off заблокирован неизвестным байтом режима и архитектурно не принадлежит этому слою.

---

## Не удалось подтвердить

- Числовой максимальный ранний старт ecobee Smart Recovery / Pre-Heat — ecobee официально не публикует.
- Числовые пороги Nest Heat Pump Balance (Max Savings/Max Comfort) — Google публикует только качественное описание.
- Алгоритм и величина компенсации самонагрева у Nest/Honeywell/ecobee — в открытых мануалах не документируется.
- Официальная политика fallback ecobee при потере участвующего SmartSensor и коды возврата Honeywell при отказе проводного сенсора — по первоисточникам не подтверждены.
- Наличие и порог собственной Safety Temperature у Carrier Ion, таймеры staging инверторного наружного блока Carrier/ICP и поведение Ion при потере ABCD-связи — в открытых источниках не найдены.
- Значение frost protection 5°C для EPH — требует проверки по мануалу конкретной модели.
- Aux Heat Max Outdoor у ecobee: 35°F (Premium guide) против 50°F (часть Lite-документации) — расхождение зафиксировано, вероятно различие линеек/прошивок.
- Overcool limit T10: 3°F по installer ISU 9070 против «up to 5°F» в одном пользовательском документе Resideo — за основное принято installer-значение.

## Источники

Все прочитаны через веб-индекс 2026-11-26; пометка [подтверждено] в тексте относится к этим источникам.

- Honeywell Pro 3000 Installation (CPH, compressor protection): https://thermostat.guide/honeywell-home/honeywell-home-pro-3000-non-programmable-digital-thermostat-installation-instructions/amp/
- Honeywell PRO TH2000 (CPH, 5-min compressor protection, Early Start): https://ia801903.us.archive.org/0/items/manualsbase-id-585732/585732.pdf
- Honeywell VisionPRO TH8000 Installation (CPH 0220–0260, dual fuel 0345–0347): https://archive.org/download/manualsbase-id-586048/586048.pdf
- Honeywell VisionPRO 8000 Product Data p.52 (AIR, P+I, droop): https://www.manualslib.com/manual/1389597/Honeywell-Visionpro-8000.html?page=52
- Honeywell Chronotherm T8621 (AIR, droop 5–6°F): https://www.manualslib.com/manual/69807/Honeywell-Chronotherm-T8621a.html?page=28
- Honeywell VisionPRO 8000 Wi-Fi Product Data (staging, droop 2–15°F, upstage timer, balance point): https://manualmachine.com/honeywell/visionpro8000wifi/16687920-specification-sheet/
- Honeywell VisionPRO IAQ manual (deadband ISU 310 = 3°F, holds, ISU 340 sensor averaging): https://manuals.plus/m/f06dcb8f45c0c8d100a9583c205dc6fe6419e3b25b889c61701ff5d9a08f39e2 и https://manualzilla.com/doc/7281018/honeywell-68-0287-04-thermostat-user-manual
- Honeywell T5+ Product Data (deadband 0°F algorithm, ISU 303/355/356): https://www.manualslib.com/manual/2325050/Resideo-Honeywell-Home-T5Plus.html?page=6
- Honeywell T6 Pro (auto differential, aux droop): https://www.manualslib.com/manual/3236674/Honeywell-Home-Lyric-T6-Pro-Wi-Fi.html?page=12
- Honeywell T6 Pro User Guide (Circ 33%): https://manuals.plus/m/388c60c1d1d5cdbd79df99e57bf9c643796b9e59ef7f95d0aa1bab523c88088a.pdf
- Honeywell T6 Pro Smart User Guide (holds, 12 h temporary): https://thermostat.guide/honeywell-home/honeywell-home-t6-pro-smart-thermostat-user-manual/
- Honeywell T10 Product Data (overcool ISU 9070, differential 1,5°F hidden): https://www.manualslib.com/manual/3711539/Honeywell-Home-T10.html?page=95 и https://lockeproductionblob.blob.core.windows.net/storage/products/attachments/2021/11/10/3ebb1c861af2e7a8a72b1636061aa251a34a2b5b430f53c37391af12d46d45e0.pdf
- Honeywell Prestige IAQ (overcool 0–3°F, 15% RH deadband): https://www.manualslib.com/manual/3825097/Honeywell-Thx9421-Prestige-Iaq-2-0-With-Eim.html?page=21
- Honeywell IAQ / Window Protection 1–10: https://docs.honeywellhome.com/elitepro-im/Indoor%20Air%20Quality.htm
- Honeywell humidifier RH table: https://electronicaircleaners.com/docs/honeywell_he420a_owners.pdf и https://ia601008.us.archive.org/13/items/manualsbase-id-616860/616860.pdf
- Honeywell placement Q7300A: https://www.manualsLib.com/manual/529284/Honeywell-Q7300a.html?page=2
- EPH Controls COMBIPACK4 / CP4M (TPI 6 CPH, Pb 2°C, Optimum Start): https://www.manualslib.com/manual/1758450/Eph-Controls-Combipack4.html?page=8 и https://manuzoid.com/manuals/99WoO-EPH%20Controls%20CP4M%20Room%20Thermostat%20Installation%20guide
- Siemens RDS110 differential 0,5°C: https://sid.siemens.com/r/A6V10877569/20569912331_20569980683__en-US_13587374347
- ecobee Thresholds (официальная поддержка): https://support.ecobee.com/s/articles/Threshold-settings-for-ecobee-thermostats
- ecobee Premium Thresholds (300 s, 5 min, 5°F delta, 35°F): https://manuzoid.com/manuals/doXG8-ecobee%20Smart%20Thermostat%20Premium%20User%20guide и https://thermostat.guide/ecobee/ecobee-smart-premium-thermostat-user-guide/
- ecobee EMS (Min Cycle Off 240–900 s, Min Outdoor 0–65°F): https://support.ecobee.com/s/articles/EMS-FAQs-Setup-Guide-and-Troubleshooting?language=en_US
- ecobee for Carrier Lite (Aux Savings 2,9°F, 60 min): https://assets-f02205d260.cdn.insitecloud.net/a2bec37b8b7130d/EBSTATE7ICR-01SI.pdf
- ecobee Preferences / Pre-Heat Pre-Cool: https://support.ecobee.com/s/articles/How-to-adjust-the-preferences-on-your-ecobee-thermostat
- ecobee SmartSensors, Follow Me, Smart Home/Away: https://www.ecobee.com/en-us/citizen/smart-thermostat-room-sensors-how-do-they-work-and-why-do-they-matter/
- ecobee fan min runtime / ventilator / dissipation: https://cdn.iwae.com/media/manuals/ecobee/7364-owner.pdf и https://www.ecobee.com/home/developer/api/documentation/v1/objects/Event.shtml
- ecobee eco+: https://www.ecobee.com/en-us/eco-plus/ ; исследование TOU (1–4°F, −44 мин): https://derekwietelman.github.io/files/Blonz_etal_2025.pdf
- Google Nest settings / Early-On / Heat Pump Balance / True Radiant: https://support.google.com/googlehome/answer/9244728?hl=en-CA ; https://support.google.com/googlehome/answer/9250165?hl=en-NZ ; Early-On до 5 ч: https://www.dejavu.org/cgi-bin/get.cgi?ver=96&url=https%3A%2F%2Fsupport.google.com%2Fgooglenest%2Fanswer%2F9246532
- Google Home/Away Assist: https://support.google.com/googlehome/answer/9261489?sjid=7304741177066085043-AP
- Nest Safety Temperatures 40°F (вторичные по Google Help): https://www.howtogeek.com/251727/how-to-turn-off-your-nest-thermostat/ ; https://www.androidpolice.com/nest-thermostat-settings-for-winter/
- Carrier Infinity System (ABCD bus, command center, размещение): https://itsmanual.com/carrier/systxccuid01-v-infinity-control-thermostat/
- Carrier Infinity Owner's (humidity 5–45% / 55–65%, overcool 3°F): https://www.manua.ls/carrier/infinity-systxccwic01-b/manual?p=28
- Carrier Humidi-MiZer (rooftop, не жилой): https://www.shareddocs.com/hvac/docs/1001/Public/03/18-811-055.pdf
- Плата печи: BASO CF830CA (fan on 25 с, off 90–180 с, завод 120 с): https://www.baso.com/wp-content/uploads/2023/03/BASO-INS-CF830CA-QRG_REVC.pdf ; ICP modulating furnace: https://www.manualslib.com/manual/977568/Icp-G9mae0601714a.html?page=35
- Defrost: https://www.trane.com/residential/en/resources/blog/what-is-heat-pump-defrost-cycle/ ; https://www.nachi.org/defrost-cycle-heat-pump.htm
- ASHRAE 62.2-2016 (Qtot, intermittent, local exhaust): https://www.scribd.com/document/746560170/ASHRAE-62-2-2016-Presentation ; таблица Honeywell 62.2: http://kitchen.manualsonline.com/manuals/mfg/honeywell/vnt5200e1000.html?p=5
- ENERGY STAR: сводка CT v1.0 https://safeguard.sh/resources/blog/how-a-smart-thermostat-is-made-sensors-relays-wi-fi-socs-firmware-and-energy-data ; CAC/HP Connected / CTA-2045 / OpenADR: https://www.energystar.gov/sites/default/files/ENERGY%20STAR%20Version%206.1%20CACHP%20Final%20Specification%20and%20Partner%20Commitments%20%28Rev.%20January%20%202022%29_0.pdf
- UL/IEC 60730 классы A/B/C, watchdog-диагностики: https://www.ti.com/document-viewer/lit/html/SPRT759
