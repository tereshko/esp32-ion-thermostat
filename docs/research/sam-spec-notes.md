# SAM01-01XA — «SAM Remote Access Application Specification»: разбор

Источник: `SAM01-01XA.pdf` в этой же папке (скачан Антоном с зеркала silo.tips 2026-11-26; канонический URL — dms.hvacpartners.com/docs/1009/Public/02/SAM01-01XA.pdf).

## 1. Идентичность документа

| Поле | Значение |
|---|---|
| Название | SAM Remote Access — Application Specification — ASCII Protocol Information |
| Catalog No | **SAM01—01XA** |
| Edition Date | **04/13** (апрель 2013) |
| PDF metadata | Title `SAM01-01XA`, Author `bac0304`, Creator PScript5.dll 5.2.2, Producer Acrobat Distiller 10.1.4, CreationDate **2013-05-08** |
| Copyright | © 2013 Carrier Corp., 7310 W. Morris St., Indianapolis, IN 46231 |
| Replaces | NEW (первое издание) |
| Объём | 14 страниц (PDF); TOC обещает протокол на стр. 4–13 |

Применимость по железу SAM: SYSTXCCSAM01 — только legacy UID/UIZ, софт ≤ v12; SYSTXCCRCT01 / SYSTXCCRWF01 — UID/UIZ софт ≥ v14 и **Infinity Touch софт ≥ v08**. Наш случай — Ion (Touch-семейство), поэтому для всех команд ниже решающая колонка — **«When using Touch wall controls»**.

## 2. Что этот документ есть — и чем он НЕ является

- Это спецификация **RS-232 ASCII-грани** модуля SAM: что хост домашней автоматизации (Crestron/AMX/HomeLogic названы прямо) шлёт в DB-9 порт SAM и что получает назад.
- Это **НЕ** спецификация ABCD-шины. В документе нет ни одного шинного регистра (0104, 3B02, 400A…), ни адресов устройств, ни процедуры регистрации/commissioning SAM. SAM внутри документа — чёрный ящик, который сам переводит ASCII ↔ шину.
- Следствие: документ полностью покрывает поведение нашей ASCII-консоли (InfinitESP `sam_ascii` — её прямая реализация, вплоть до ссылок на примеры Table 1 в комментариях кода) и лишь косвенно — шинную сторону.
- Прямо заявлено: **faults/diagnostics по ASCII-порту недоступны** («Notification of system malfunctions, routine maintenance reminders, and equipment diagnostics are not available over the ASCII/RS-232 home automation port») — это привилегия интернет-мониторинга. (Шинный 4202 fault log при этом существует — но ASCII-грань его прячет.)
- SAM обслуживает **до 2 систем × до 8 зон**; адресация — иерархия System → Zone → параметр.

## 3. Транспорт и кадрирование (стр. 3)

| Параметр | Значение |
|---|---|
| Порт | DB-9 female, SAM = subset DCE; только RxD (pin 2), TxD (pin 3), GND (pin 5); уровни ±9 В |
| Скорость | **9600 bps, half-duplex, 8N1** |
| Терминатор команды | **CR/LF** |
| Регистр букв | Хост может слать в любом; SAM всё парсит как **uppercase** |
| Макс. длина сообщения | **64 символа, включая CR/LF** |
| Межсимвольный таймаут | Пауза **5 с** между принятыми символами → receive buffer сбрасывается |
| Ответ | SAM обязан ответить **в течение 5 с**; не успел построить ответ за 5 с → **NAK**, команда игнорируется, хост должен переслать |

## 4. Process (Algorithm) — суть дословно (стр. 3)

«The intent of the SAM ASCII interface is to provide easy home automation system access into select portions of the Infinity system. The SAM ASCII interface will respond to the messages in the Tables, below, as long as they are formatted as follows:» — далее параметры 9600/8/N/1 и терминатор CR/LF (таблица выше). Вся «алгоритмика» документа — это кадрирование + правила NAK + семантика hold в таблицах команд (раздел 6–7); отдельного алгоритмического текста в секции Process нет.

Дополнительно из General Message Formatting (стр. 3): «drill down»-иерархия — сначала номер системы (S1/S2), потом зона (Z1–Z8), потом пользовательские/сервисные настройки. Запрос несуществующей системы или зоны → NAK.

## 5. Ошибки и аномальные ответы (стр. 3)

| Ситуация | Ответ SAM |
|---|---|
| Invalid command | Эхо команды + `:NAK CMD` |
| Invalid parameter | Эхо команды + `:NAK VAL` |
| CCN Error (ошибка шины/CCN за SAM) | Эхо команды + `:NAK` |
| Response Timeout | Эхо команды + `:NAK` |
| Неподдерживаемая на Touch команда (затенена в таблицах) | NAK |
| Неверная проводка Rx/Tx | Не должна вызывать повреждений, потери CCN-коммуникаций или wireless (требование к железу, не ответ) |

Формат успеха: чтение — `КОМАНДА: значение`; запись — `КОМАНДА: ACK`.

## 6. Справочник команд — Status (`?`), Table 2

Обозначения: S1 = система 1, Z1 = зона 1. Колонка Touch: «—» = поведение как legacy.

| Команда | Ответ | Семантика / примечания | Touch |
|---|---|---|---|
| `S1Z1RT?` | `S1Z1RT: xxx°F/C` | Комнатная температура зоны, как отображается | — |
| `S1Z1RH?` | `S1Z1RH: xx%` | Влажность; датчик в системе один, зона — на будущее; значения >99% возвращаются как 99% | — |
| `S1OAT?` | `S1OAT: xxx°F/C` | Уличная температура системы | — |
| `S1Z1FAN?` | `S1Z1FAN: AUTO/LOW/MED/HIGH` | Настройка вентилятора зоны; AUTO = continuous fan OFF | — |
| `S1MODE?` | `S1MODE: (HEAT/COOL/AUTO/OFF) #` | Режим системы (без зоны!); **цифра после режима = число активных ступеней demand** (напр. `COOL2`) | — |
| `S1Z1HOLD?` | `S1Z1HOLD: ON/OFF` | Hold: legacy — program hold; Touch — «hold permanent» | семантика переименована |
| `S1Z1UNOCC?` | `S1Z1UNOCC: ON/OFF` | Unoccupied: Touch — зона в AWAY в состоянии hold permanent | семантика переименована |
| `S1Z1HTSP?` / `S1Z1CLSP?` | `…: xxx°F/C` | **Активные** уставки зоны (heat/cool) | — |
| `S1Z1RHTG?` | `S1Z1RHTG: xx%` | Цель увлажнения; кап 99% | — |
| `S1HUMID?` | `S1HUMID: ON/OFF` | Состояние выхода увлажнителя | — |
| `S1DAY?` | `S1DAY: MONDAY…` | День недели | — |
| `S1TIME?` | `S1TIME: HH:MM A/P` | Время, 12-часовой формат | — |
| `S1Z1OVR?` | `S1Z1OVR: ON/OFF` | Активен ли override-таймер («hold until») | — |
| `S1Z1OTMR?` | `S1Z1OTMR: HH:MM` | Остаток override-таймера; 00:00 если неактивен | — |
| `S1ZONE?` | `S1ZONE: 1-8` | Зона, отображаемая на термостате; в unzoned системе всегда 1 | — |
| `S1Z1NAME?` | `S1Z1NAME: (≤11 chars)` | Имя зоны, усечение при необходимости | — |
| `S1FILTRLVL?` / `S1UVLVL?` / `S1HUMLVL?` | `…: xxx%` | Износ фильтра / UV-лампы / пада увлажнителя | — (VENTLVL? в Table 2 не listed, но VENTLVL! есть в Table 3) |
| `S1FILTRRMD?` / `S1UVRMD?` / `S1HUMRMD?` | `…: ON/OFF` | Настройки напоминаний аксессуаров | — |
| `S1BLIGHT?` | `S1BLIGHT: ON/OFF` | Подсветка: legacy ON = continuous активна; Touch ON = continuous на уровне ≥3, OFF = ≤2 | пороги различаются |
| `S1VACAT?` | `S1VACAT: ON/OFF` | Состояние отпуска | — |
| `S1VACDAYS?` | `S1VACDAYS: ###` | Оставшиеся дни отпуска | — |
| `S1VACMINT?` / `S1VACMAXT?` | `…: ### xxx°F/C` | Мин/макс температура отпуска | — |
| `S1VACMINH?` / `S1VACMAXH?` | `…: ### xxx%` | Мин/макс влажность отпуска (0% / 100% = NONE на соответствующих концах) | — |
| `S1VACFAN?` | `S1VACFAN: AUTO/LOW/MED/HIGH` | Вентилятор на отпуск | — |
| `S1CFGEM?` | `S1CFGEM: F/C` | Единицы термостата. Асимметрия: на запись командуются `E`/`M`, на чтение возвращаются `F`/`C` | — |
| `S1CFGAUTO?` | `S1CFGAUTO: ON/OFF` | Разрешён ли режим Auto | — |
| `S1CFGTYPE?` | `S1CFGTYPE: COOL/HEAT/HEATCOOL` | Тип системы | — |
| `S1CFGDEAD?` | `S1CFGDEAD: #` | Deadband heat/cool (мин. разнос уставок) | чтение ок |
| `S1CFGCPH?` | `S1CFGCPH: #` | Cycles per hour | чтение ок |
| `S1CFGFAN?` | `S1CFGFAN: ON/OFF` | Programmable fan; на Touch **всегда ON** | — |
| `S1PER?` | `S1PER: WAKE/DAY/EVE/SLEEP` | Текущий период программы | **NAK** |
| `S1CFGPER?` | `S1CFGPER: #` | Периодов в день (2 или 4) | **NAK** |
| `S1CFGPGM?` | `S1CFGPGM: ON/OFF` | Программирование включено | — |
| `S1Z1PGM<day><PERIOD>?` | строка периода | В Table 2 строки PGM оформлены как записи `!` (см. §7) | **NAK** |
| `S1DEALER?` / `S1DEALERPH?` | `…: (≤18 chars)` | Имя/телефон дилера, усечение до 18 | — |

## 7. Справочник команд — Configuration (`!`), Table 3

| Команда | Ответ | Семантика / примечания | Touch |
|---|---|---|---|
| `S1Z1FAN!AUTO/LOW/MED/HIGH` | `S1Z1FAN: ACK/NAK` | Вентилятор зоны; AUTO = continuous OFF | — |
| `S1MODE!HEAT/COOL/AUTO/OFF/EHEAT` | `S1MODE: ACK/NAK` | Режим системы; NAK, если система режим не поддерживает (heat-only + AUTO/COOL → NAK) | **EHEAT командуем, но всегда NAK** |
| `S1Z1HOLD!ON/OFF` | ACK/NAK | Hold зоны; на Touch ON = «hold permanent» для **текущей исполняемой активности** зоны | семантика переименована |
| `S1Z1UNOCC!ON/OFF` | ACK/NAK | Legacy: NAK в unzoned системе; Touch: ON = AWAY в hold permanent, OFF = HOME в hold permanent | — |
| `S1Z1HTSP!XX[, HH:MM]` | ACK/NAK | Уставка heat. Legacy: без длительности — override-таймер по умолчанию **3:00**. Touch: с длительностью — «hold until» в **MANUAL activity**; без — «hold permanent» в MANUAL activity (если ещё не в ней). Вне диапазона для текущих единиц: legacy — NAK; **Touch — значение поджимается (clamp)**, а парная уставка может быть сдвинута под deadband. Ведущие нули обязательны (`S1Z1HTSP!06, 01:00`) | clamp вместо NAK |
| `S1Z1CLSP!XX[, HH:MM]` | ACK/NAK | То же для cool; legacy-дефолт override — **2:00** (асимметрия с heat!) | clamp вместо NAK |
| `S1DAY!0-6` | ACK/NAK | День недели, 0 = воскресенье | **NAK — не поддерживается**: «The ING calculates the day of the week based on the date» |
| `S1TIME!HH:MM A/P` | ACK/NAK | Время; 12-часовой формат, ведущие нули обязательны (`S1TIME!09:01P`) | — |
| `S1Z1OTMR!HH:MM` | ACK/NAK | Override-таймер зоны → зона в MANUAL activity; 00:00 отменяет hold until; максимум 23:59, выше — NAK | значения **усекаются вниз до ближайших 15 минут** |
| `S1ZONE!1-8` | ACK/NAK | Какую зону показывает термостат | — |
| `S1Z1NAME:<text>` | ACK/NAK | Имя зоны ≤11 символов + NUL, регистр сохраняется. В спеке синтаксис именно с `:` , не `!` | — |
| `S1FILTRLVL!0` / `S1UVLVL!0` / `S1HUMLVL!0` / `S1VENTLVL!0` | ACK/NAK | Сброс монитора аксессуара в 0%; любое значение ≠0 → NAK (для FILTRLVL текст мягче, для остальных — прямо) | — |
| `S1FILTRRMD!ON/OFF` (в ответе опечатка спеки: `S1FILTRRMD`) / `S1UVRMD!` / `S1HUMRMD!` / `S1VENTRMD!` | ACK/NAK | Напоминания аксессуаров | — |
| `S1BLIGHT!ON/OFF` | ACK/NAK | Подсветка: Touch ON = заводской Level 8, OFF = Level 2 | уровни фиксированы |
| `S1VACDAYS!###` | ACK/NAK | Дни отпуска 0–365; 0 завершает активный отпуск; ведущие нули до 3 цифр (`!001`) | — |
| `S1VACMINT!XX` / `S1VACMAXT!XX` | ACK/NAK | Температуры отпуска; парная граница может сдвинуться под deadband; Touch — clamp вместо NAK при выходе за диапазон | clamp |
| `S1VACMINH!XXX` | ACK/NAK | Допустимые значения только **0, 10, 15, 20** | — |
| `S1VACMAXH!XXX` | ACK/NAK | Допустимые значения только **55, 60, 65, 100 (NONE)** | — |
| `S1VACFAN!AUTO/LOW/MED/HIGH` | ACK/NAK | Вентилятор на отпуск | — |
| `S1CFGEM!E/M` | ACK/NAK | Единицы: команда `E`/`M`, чтение возвращает `F`/`C` | — |
| `S1CFGAUTO!ON/OFF` | ACK/NAK | Разрешение Auto | **NAK**: «wall control algorithms changed to remove need for this command» |
| `S1CFGDEAD!#` | ACK/NAK | Deadband 0–6 (legacy) | **NAK** (та же причина) |
| `S1CFGCPH!#` | ACK/NAK (в спеке ответ напечатан `S1CFGCPY`) | Cycles per hour 2–6 (legacy) | **NAK** (та же причина) |
| `S1CFGFAN!ON/OFF` | ACK/NAK | Programmable fan | **NAK** |
| `S1CFGPER!#` | ACK/NAK | Периодов в день 2/4 | **NAK** |
| `S1CFGPGM!ON/OFF` | ACK/NAK | Программирование вкл/выкл | **NAK** |
| `S1Z1PGM<day><PERIOD>!HH:MM A/P, HEAT, COOL, FAN` | ACK/NAK | Запись периода расписания (дни MON…SUN; периоды WAKE/DAY/EVE/SLEEP); fan игнорируется при programmable fan OFF; время строго с ведущими нулями | **NAK** — «This type of programming is not supported» |
| `S1CFG!A5A5` затем `S1CFG!RESET` | `S1CFG: ACK/NAK` ×2 | Factory reset: две команды подряд, вторая в течение **10 с**; любая команда между ними или просрочка отменяет сброс | **NAK — не поддерживается** |
| `S1DEALER!<≤18 chars>` / `S1DEALERPH!<≤18 chars>` | ACK/NAK | Имя/телефон дилера | **NAK**: задаётся через online/USB |

Примеры Table 1 (стр. 4) — нормативные краевые случаи: `S2TIME! 8:10A` (пробел + нет ведущего нуля) → `NAK VAL`; `S1MODE:HEAT` (нет `!`) → эхо + `:NAK CMD`; `S1DAY!9` → `NAK VAL`; запрос зоны 5 при её отсутствии → `S1Z5RT:NAK CMD` (именно CMD, не VAL); `S1Z1MODE?` (зона там, где её быть не должно) → `NAK CMD`; запись в read-only команду (`S1Z5RT!`) → `NAK CMD`, причём в примере эхо напечатано как `S1Z1RT:NAK CMD` (несоответствие зоны в эхе — опечатка спеки).

## 8. Дельта-анализ против наших знаний

### 8.1 ПОДТВЕРЖДЕНО спекой

1. **Грамматика консоли InfinitESP — вендорная.** Набор глаголов `sam_ascii` (MODE/OAT/TIME/DAY/ZONE/BLIGHT/CFGEM/CFGDEAD/CFGCPH/CFGPER/CFGPGM/DEALER*/FILTRLVL/UVLVL/HUMLVL/VENTLVL/*RMD/VAC*/Z#RT/RH/RHTG/HTSP/CLSP/FAN/HOLD/OVR/OTMR/UNOCC/NAME) — это Table 2/3 документа 1-в-1, минус префикс системы `S1` (у нас одна система — префикс опущен реализацией). Код `sam_ascii.cpp` прямо ссылается на примеры Table 1 (строгий один знак для DAY!, NAK VAL вне 0–6) и реализует межсимвольный сброс буфера.
2. **Кадрирование:** CR/LF, uppercase-парсинг, лимит 64 символа, 5-секундный межсимвольный сброс, ответ ≤5 с иначе NAK — всё совпадает с Process/General Formatting спеки. (Наш транспорт — TCP 23 вместо 9600 8N1 RS-232; спека определяет именно физический порт SAM, транспорт у InfinitESP свой по дизайну компонента.)
3. **Запись уставки = вход в MANUAL activity с hold.** Спека (Touch-колонка HTSP!/CLSP!): с длительностью — «hold until» в MANUAL activity, без длительности — «hold permanent» в MANUAL activity. Это вендорное объяснение нашего эмпирического контракта фазы 3: рулить можно только при активном manual/hold, manual-слот пересеменивается из активного профиля при входе. HOLD!ON на Touch = hold permanent «для текущей исполняемой активности» — согласуется с картой 400A (5 активностей × 7 байт, manual — пятая).
4. **MODE? цифра ступеней.** Ответ `MODE: COOL2` — цифра = число ступеней demand. Наша система: газ 2 ступени, ODU мультистейдж — поле осмысленно и наблюдаемо.
5. **Мёртвые 3B02/3B03 для незарегистрированного SAM спекой не противоречат** — спека вообще не описывает шинную сторону; см. §8.3.
6. **Запись глобальных параметров откатывает часы** (находка свипа по infinitive) согласуется со спекой косвенно: TIME!/DAY! — полноправные команды записи, а на Touch DAY! вообще запрещён, потому что день считается из даты («The ING calculates the day of the week based on the date»). InfinitESP это знает: его TIME!-расширения ставят день и время одной записью, ACK трактуется как транспортный, не как adoption (Touch применяет при пробуждении UI).

### 8.2 НОВОЕ (спека добавляет то, чего у нас не было)

1. **Точные правила NAK-таксономии:** `:NAK CMD` vs `:NAK VAL` vs голый `:NAK` (CCN error / response timeout). Запрос отсутствующей зоны/системы — **NAK CMD** (не VAL). Это готовая таблица для нашей консоли и для тестов.
2. **Clamp вместо NAK на Touch при уставках:** HTSP!/CLSP!/VACMINT!/VACMAXT! вне допустимого диапазона на Touch **поджимаются**, а парная уставка может быть сдвинута под deadband. На legacy в той же ситуации — NAK. Развилка поколений — новая для нас.
3. **Асимметричные дефолты override (legacy):** HTSP! без времени → override **3:00**, CLSP! без времени → **2:00**. На Touch дефолта нет — вместо него hold permanent в MANUAL.
4. **OTMR! усечение:** на Touch длительность hold-until усекается вниз до ближайших **15 минут**; потолок 23:59 в обеих ветках.
5. **Touch-запреты (NAK) полны<!-- ВОССТАНОВЛЕНО 2026-11-26: файл был обрезан при сохранении ровно на этом месте — после слова «полны» стоял буквальный маркер «...[truncated 8182 chars]»; конец §8.2 (п. 5 и далее) и §8.3 на диске отсутствовали (аудит FIRMWARE-AUDIT.md, п. 2b.9). Текст ниже восстановлен по PDF SAM01-01XA из этой же папки и по внутренней ссылке §8.1 п. 5; уцелевший текст выше не изменялся. -->й список:** чтения `PER?` и `CFGPER?`; записи — все `PGM` (периоды расписания, «This type of programming is not supported»), `DAY!` (день недели считается из даты), `CFGAUTO!`, `CFGDEAD!`, `CFGCPH!`, `CFGFAN!`, `CFGPGM!` (обоснование CFG-группы дословно: «wall control algorithms changed to remove need for this command»), двухшаговый factory reset `CFG!A5A5` → `CFG!RESET` за 10 с, `DEALER!` / `DEALERPH!` (дилер задаётся через online-подключение или USB). Механизм задан самой спекой: позиции, затенённые (shaded) в Table 2/3, на Touch не поддерживаются, и SAM возвращает на них NAK [FACT, PDF]. Сюда же: `MODE!EHEAT` — командуем, но на Touch всегда NAK («EHEAT can be commanded, but … will result in a NAK»).
6. **Дискретные множества vacation-влажности:** `VACMINH!` принимает только **{0, 10, 15, 20}**, `VACMAXH!` — только **{55, 60, 65, 100 = NONE}** [FACT, PDF, Table 3]; непрерывного диапазона нет, значение вне множества — `NAK VAL` по таксономии §5. `VACDAYS!` — 0–365 дней, с ведущими нулями до трёх цифр (`!001`).
7. **BLIGHT! на Touch — фиксированные уровни:** ON ставит заводской **Level 8**, OFF — **Level 2** [FACT, PDF, Table 3]; промежуточные уровни по ASCII недоступны (чтение `BLIGHT?` при этом пороговое — см. §6).
8. **Эррата самой спеки:** (а) секция «Connect Auxiliary Sensor» существует **только в оглавлении** — в теле документа её нет (слово «Auxiliary» встречается в тексте PDF ровно один раз, в TOC) [FACT, проверено по извлечённому тексту PDF]; (б) ответ на `CFGCPH!` напечатан с опечаткой — `S1CFGCPY: ACK/NAK`; (в) команда сброса напоминания фильтра напечатана `S1FILTRMD!` при ответе `S1FILTRRMD:` — расхождение в одну букву внутри самой Table 3.

### 8.3 НЕ ОБЪЯСНЕНО спекой

Тема задана ссылкой из §8.1 п. 5: спека описывает только ASCII-грань SAM, и всё шинное остаётся за её пределами — по построению документа, а не по недосмотру.

1. **Регистрация и commissioning SAM отсутствуют как класс.** В документе нет ни discovery, ни привязки SAM к термостату, ни одного шинного идентификатора (0104, 030D, 031C, 040E в тексте отсутствуют), ни адресов устройств. Нулевые 3B02/3B03 незарегистрированному SAM спекой **не объясняются и ей не противоречат** — это поведение шинной стороны, которую документ не покрывает. Единственное объяснение остаётся за стадиями C/D (гейт — runtime-привязка по device ID); зазоры G3/G6 карты протокола эта спека не закрывает.
2. **Шинный диалект SAM не специфицирован.** Как ASCII-команды отображаются в шинные чтения/записи SAM (включая ответы термостата класса 3B0E на записи SAM), документ не говорит вообще. Источник по шинной стороне — InfinitESP и наши захваты, не спека.
3. **Отображение на активности 400A из спеки не выводится.** Спека оперирует именами состояний (MANUAL activity, AWAY/HOME в hold permanent для UNOCC), а не байтами строки 400A; соответствие «UNOCC = AWAY-профиль» ↔ конкретная активность установлено нами эмпирически по карте протокола, а не документом.
4. **Молчание спеки:** polling-каденция SAM на шине не задана; поведение при двух SAM на одной системе не описано; ретрансмиты после NAK определены только для хоста ASCII-стороны (переслать команду после NAK по таймауту ответа), про шинную сторону — ничего; семантика цифры ступеней в `MODE?` для мультистейдж-ODU не разобрана (цифра определена лишь как число активных ступеней demand).

### 8.4 Следствия для эмулятора и флаги текущего узла

1. **Контракт hold/MANUAL — вендорный, а не только эмпирический:** запись уставки = MANUAL activity + hold (с длительностью — hold until, без — hold permanent), `HOLD!ON` = hold permanent на текущей исполняемой активности. Временной бюджет SAM-стороны: ответ ≤ 5 с, иначе SAM шлёт NAK и ждёт пересылки; межсимвольный сброс — 5 с. Это тестовые параметры для нашей консоли и для SAM-грани эмулятора.
2. **NAK-таксономия (§8.2 п. 1) и clamp-семантика (§8.2 п. 2) — готовые тестовые векторы:** на Touch уставка вне диапазона поджимается, а не отклоняется; отсутствующая зона — NAK CMD, а не VAL.
3. **MODE с цифрой ступеней — ожидаемый формат** (`COOL2`): эмулятор термостата обязан воспроизводить цифру активных ступеней demand, а не только имя режима.
4. **Флаги текущего узла (расхождения осознанные):** пассивный ACK у InfinitESP — по спеке ACK означает «принято», наш узел подтверждает транспорт, а не adoption (ср. §8.1 п. 6 о TIME!); команды `SCAN?` / `REG?` / `REG!` — внеспецификационная диагностика стенда, на реальном SAM01 их нет; при `raw_writes` команда `REG!` по дизайну обходит семантику clamp/deadband/hold, которую эта спека задаёт для штатного пути записи.