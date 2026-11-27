# GitHub-sweep: внешний RE Carrier/Bryant/ICP Infinity / Ion (ABCD bus)

Дата: 2026-11-26. Задача: найти всё внешнее reverse engineering по Infinity/Ion и шине ABCD
помимо известного нам nebulous/InfinitESP, включая форки, гисты, заметки по протоколу и
параллельные проекты. Метод: browser.search (несколько волн, включая site:github.com и
site:gist.github.com) + browser.open ключевых страниц. Все URL ниже — дословно из выдачи
поиска или открытых страниц.

---

## Главный вывод (честно, первым)

**Никто из найденных не публикует конструкцию payload термостат→оборудование (наши 0305/0605)
и не публикует staging-логику термостата.** Все живые проекты — SAM-стороны: они эмулируют SAM
(0x92) и говорят с термостатом, который остаётся мастером шины. Наш пробел (писатели 0305/0605,
байт 0x78, вычисление CFM) этим свипом НЕ закрывается. Ценность свипа — перекрёстная проверка
наших карт регистров, framing/bootup-детали, кодировки температур и пара конкретных находок
по регистрам, которых у нас не было (3B07–3B0D расписания, 3D02/3D03, 041F, заметки по 0316).

---

## Ранжированные находки

### 1. lurgh/infinitive — живой форк acd/infinitive (Go, SAM-эмулятор)

URL: https://github.com/lurgh/infinitive/tree/master?tab=readme-ov-file

- Что это: форк Infinitive с read/write API и UI для мультизонных систем (до 6–8 зон),
  MQTT + MQTT Discovery для Home Assistant, захват шины в JSONL (`-buscap`, сырые кадры
  hex + декод, tx и rx), почасовой лог `-rlog`. Активная разработка: README обновлён под
  май 2025, пример buscap в README датирован мартом 2026. ~13 звёзд, 3 форка.
- Что знает сверх нашего RE:
  - **Регистры 3B07–3B0D — расписания**: семь 1-дневных расписаний (по дню недели), 160 байт:
    8 зон × 4 периода × (uint16 старт в минутах от полуночи, uint8 heatSP, uint8 coolSP,
    uint8 0xFF — «fan setting or placeholder»). Это прямая подсказка для нашего mode-experiment
    и для эмулятора (формат расписаний термостата).
  - **3B06**: dealer name/phone + биты настроек UI/SAM (filter/UV/humidifier reminders,
    backlight, F/C, deadband, cycles/hr, programmable fan).
  - **3D02** (чтение из термостата): реальные температуры зон — raw ×16 °F + сглаженное
    целое для дисплея; префикс a5, флаги зон.
  - **3D03**: outdoor temp ×16, indoor humidity smoothed + raw.
  - **0316** (air handler → thermostat): байт HS = furnace heat stage (00 off, 01/02/03
    low/med/hi), CC = cooling flag. Сверка с нашим 0316 (конфиг печи) — у них это ответ
    оборудования; стоит перепроверить нашу трактовку по захватам.
  - **041F**: WRITE термостат → smart sensor: период программы зоны, heat/cool setpoints.
  - **0420**: регулярный broadcast WRITE на F1F1: outdoor ×16, indoor humidity.
  - **Побочный эффект записи глобальных параметров** (режим heat/cool/auto/off и др. в том же
    регистре): термостат откатывает часы до ~1 минуты на каждую запись; у них добавлен фикс —
    перестановка времени после записи. Релевантно нашим записям режима/уставок.
  - 3C03 — «buffering remnants» (мусор), 3C0A — имена 8 зон, 3C0D/3C0E/3C0F/3C14 — частичные
    заметки со сэмплами hex.
  - Airflow weighting по зонам: считается из damper states + duct assessment (capacity %
    с экрана контроллера, `-ductCap`); статические факторы по шине НЕ отдаются — подтверждено
    и ими.
- Лицензия: в прочитанном тексте README не указана (проверить файл LICENSE в репозитории).
- Свежесть: самый живой из всех SAM-проектов на сегодня.

### 2. bvarner/gofinity (Go, 2017)

URL: https://pkg.go.dev/github.com/bvarner/gofinity@v0.0.0-20170305213718-5604cdad5133

- Что это: библиотека для Infinity/Evolution: bus snooping/decoding, device state tracking,
  RE-инструменты. Наследник Infinitive. Своё железо pi485 (TTL↔RS-485 для Pi/Arduino).
- Что знает: README содержит раздел **Protocol / Device Information → Protocol Basics →
  Bootup Sequence** — единственное найденное публичное описание последовательности загрузки
  шины. Для нашего failover-эмулятора 0x20 (порядок появления устройств, кто кого опрашивает
  при старте) это самый релевантный внешний источник. ВАЖНО: рендер pkg.go.dev обрезал README
  ровно на заголовке «Bootup Sequence» — само содержимое секции в этом свипе НЕ прочитано,
  нужен отдельный заход в репозиторий.
- Заявленные автором цели (не реализовано): «segment the RS-485 network to interdict system
  commands to subordinate devices» — то есть перехват команд термостат→оборудование был целью,
  но опубликованного результата по payload команд нет.
- Лицензия: не подтверждена из прочитанного текста. Свежесть: 2017, dormant.

### 3. nebulous/infinitude — CarBus (Perl) + вики протокола

URL AGENTS.md: https://github.com/nebulous/infinitude/blob/HEAD/AGENTS.md
Вики, Framing Protocol: https://github-wiki-see.page/m/nebulous/infinitude/wiki/Infinity-Framing-Protocol
Вики, Infinity Touch (hardware): https://github-wiki-see.page/m/nebulous/infinitude/wiki/Infinity-Touch

- Что это: родительский проект nebulous. Perl: lib/CarBus.pm, CarBus/Frame.pm, CarBus/SAM.pm
  (эмуляция SAM + определения регистров), CarBus/SAM/ASCII.pm, docs/SAM-ASCII-Protocol.md,
  contrib/cardump/. Эмуляция ZC (зонного контроллера) помечена high-risk.
- Что знает (верифицировано чтением страницы Framing Protocol 2026-11-26):
  - Кадр: 8-байтный заголовок (dst addr, dst bus, src addr, src bus, length, PID, EXT,
    function) + данные + CRC16 по заголовку+данным; bus byte всегда 0x01, PID/EXT = 0.
  - Функции: 0x02 ACK02, 0x06 ACK06 (len=1/data=0x00 — ACK на WRITE; len>3 — ответ на READ,
    первые 3 байта данных = номер регистра), 0x0B READ_TABLE_BLOCK, 0x0C WRITE_TABLE_BLOCK,
    0x15 NAK/exception (0x04 = register not served, 0x0A = no such table / not writable /
    invalid data), 0x10 CHGTBN, 0x1E ALARM, 0x22 OBJRD, 0x62 RDVAR, 0x63 WRVAR («FORCE»),
    0x64 AUTO, 0x75 LIST.
  - **SAM пишет регистр 3B03 (sam_zones) в термостат; термостат отвечает записями 3B0E** —
    внешнее подтверждение нашего пути записи.
  - SAM непрерывно читает 3C14, 3C0C, 3C0D, 3003, 3005 — термостат стабильно отвечает
    exception 0x04; за 10,5 ч пассивного захвата все 54 076 exception-кадров — thermostat→SAM
    с байтом 0x04 (1:1 с чтениями неслужимых регистров: 3C14, 3C0D, 3C0C, 3005, 3003, 3104,
    0104, 0420, 0202). Согласуется с нашим «незарегистрированный SAM получает нули/отказы».
  - Термостат broadcast-ит дату/время (регистры 0202/0203) на F1F1 каждые ~60–90 с;
    **тач-термостат с адресом источника 1F01 делает дополнительные broadcast'ы при старте** —
    релевантно нашему SystemInit-персоне 0x1F и failover-детекту присутствия Ion.
  - Устройство 0x4001 однажды посылало READ в 0x4101 без ответа (необъяснённый пир).
  - AGENTS.md содержит раздел «Bus Temperature Encodings» — 4 кодировки температур на шине
    (сверить с нашими декодами).
  - Страница Infinity Touch: SoC SuperH SH2A 7267/7269 (совпадает с нашим SH7269), 16 MB flash,
    MAX3443, H-UDI debug; прошивка — Intel hex, штатные конвертеры не справились из-за
    endianness, @Zhentar писал свой ihex_to_bin (отдельный репозиторий поиском не подтвердился).
  - В вики также есть страницы: Infinity Protocol Main, Infinity — interpreting data,
    Infinity — Known Devices, serial protocol (URL этих страниц в выдачу дословно не попали —
    читать через вики репозитория).
- Форки: https://github.com/NateCCIE/infinitude (свежий, создан 2026-08-03); onetrueandrew/infinitude
  (в AGENTS.md: «not compatible with thermostat firmware versions newer than 4.05» — наш Ion на
  4.79, т.е. Infinitude-путь для тач-поколения официально ограничен старыми прошивками).
- Лицензия: из прочитанных текстов не подтверждена. Свежесть: репозиторий жив (коммиты 2026),
  вики — накопленная база знаний сообщества.

### 4. acd/infinitive (оригинал, Andrew Danforth, Go)

Issue #5: https://github.com/acd/infinitive/issues/5
Issue #20: https://github.com/acd/infinitive/issues/20
Форки на pkg.go.dev: https://pkg.go.dev/github.com/mww012/infinitive ,
https://pkg.go.dev/github.com/5310h/infinitive-1

- Что это: первый Go SAM-эмулятор; `tables.go` — структуры таблиц термостата, маппящиеся
  1:1 на wire frames (offset = позиция поля в структуре); `scandevtable.py` — сканер таблиц
  устройств (формат вывода переиспользовал ещё brybus/3tones).
- Что знает / подтверждает:
  - **Issue #5 (Bryant Evolution, 2017)**: на тач-термостатах таблицы **3B02/3B03 возвращают
    все нули** — внешнее подтверждение нашего вывода 2026-11-03 (Ion незарегистрированному SAM
    отдаёт нулевые 3B02/3B03). Гипотезы из треда: данные тач-поколения лежат в UI PARMS
    (003C02/03), DISPDATA (003D02/03) или DCLEGACY (003F02/03). Подтверждено lurgh: 3D02/3D03
    действительно содержат живые данные (см. п.1).
  - Issue #20: логи кадров с ответом печи 0104 «VARIABLE SPEED FURNACE … CESR1313 12-06
    58MVP08…» — пример самоидентификации оборудования (внешняя сверка с нашим 0104).
- Статус: оригинал dormant с ~2018 (116★); развитие ушло в форк lurgh (п.1) и mww012
  (автор HA-интеграции hass-infinitive). Лицензия не подтверждена из прочитанных текстов.

### 5. 3tones/brybus (Python, 2010–2014) + CocoonTech-тред

URL: https://github.com/3tones/brybus
Вики: https://github-wiki-see.page/m/3tones/brybus/wiki
First Run: https://github-wiki-see.page/m/3tones/brybus/wiki/First-Run
Форум: https://cocoontech.com/threads/carrier-infinity.11372/page-13 ,
https://cocoontech.com/threads/carrier-infinity.11372/page-14 ,
https://cocoontech.com/threads/carrier-infinity.11372/page-23

- Что это: старейший публичный проект по шине (с 2010): python-пакеты для прямого общения
  на Evolution/Infinity bus, сканирование устройств и таблиц, SQL-логгинг всех кадров
  с хранением только изменившихся, инжект запросов на шину. Вики: First Run, Scanning
  Devices, Scanning Data, Contribute, SQL Logging. Сам 3tones называет infinitude/wiki
  «центральным репозиторием» знаний о протоколе.
- Что знает сверх нашего RE: исторические табличные определения с CocoonTech (формат
  «Addr,TBLName,TblAddr,TblRow,RowLen,…,Name,Interpretation» — напр. SYSTIME 2001 табл. 02),
  наблюдения про abort-сигналы в конце передач (00FC–00FF) и про то, что **термостат от
  адреса 1F немедленно допрашивает любое новое устройство на шине** — прямо релевантно
  нашему failover (появление нового пира провоцирует interrogation от 1F).
- Лицензия не подтверждена. Свежесть: unmaintained с 2014; ценность — архивная/историческая.

### 6. finitude (Python, PyPI 0.1.1, 2021)

URL: https://pypi.org/project/finitude/ ; https://libraries.io/pypi/finitude

- Что это: декодер ABCD-шины: Prometheus /metrics + сервер, сохраняющий **все WRITE и ACK06
  кадры в JSON**; `analysis.py` — функции поиска смысла в кадрах. Автор dulitz@gmail.com.
  Основан на brybus + infinitude + infinitive.
- Что может дать: готовый подход «корпус всех WRITE-кадров» и анализ-инструменты — методология
  прямо под нашу задачу поиска писателей payload; сам по себе новых декодов не заявляет.
- Свежесть: релиз 2021, Snyk: inactive, ~14★, 3 форка, last commit ~4 года назад. GitHub-репозиторий
  поиском отдельно не локализован (PyPI/libraries.io ведут на него, точного URL в выдаче не было).

### 7. nebulous/infinitesp + esphome-uart-link (известный нам проект — для полноты)

Профиль: https://github.com/nebulous
Коммит: https://github.com/nebulous/infinitesp/commit/01fa9576ecdeb6182dfdb25c1f7532557de21970
Issue: https://github.com/nebulous/infinitesp/issues/20

- infinitesp (C++, 25★/11 форков), esphome-uart-link (C++, 28★/7), infinitude (259★/54).
  Коммиты в infinitesp — ноябрь 2026, проект активен. Коммит выше: POLL_REGS/SLOW_POLL_REGS,
  400A comfort profiles, discovery probe 0xNN01 — совпадает с нашим стеком. В infinitesp есть
  Kaitai Struct (.ksy) определение кадра (вики Framing ссылается на него).

### 8. HA-экосистема (НЕ шина: облако/прокси — RE-ценность низкая, для полноты карты)

- https://github.com/mizterb/homeassistant-infinitude/blob/HEAD/README.md — интеграция через
  Infinitude; не поддерживается с 2025-01-01.
- https://github.com/MizterB/homeassistant-infinitude-beyond — продолжение.
- https://github.com/dahlb/ha_carrier/blob/HEAD/README.md — облачный Carrier API (GraphQL),
  тест на SYSTXCCWIC01-B fw 4.31; к ABCD-шине отношения не имеет.
- mww012/hass-infinitive — HA-интеграция поверх Infinitive (упомянута в README lurgh).

### 9. НЕ наш протокол (важное разграничение)

- CZII / Comfort Zone II: https://github-wiki-see.page/m/mhightower83/CZII_to_MQTT/wiki/Interpreting-Data
  Формат «somewhat similar, but a very simplified version» of Infinity — не путать с ABCD.
  Рядом: jwarcd/CZII_to_MQTT, ronisaacson/cz2.
- Awesome-список для контроля полноты:
  https://github.com/alexgaoth/awesome-reverse-engineered/blob/main/categories/industrial-building-automation.md
  — по Carrier Infinity там значится только infinitive.

### 10. Гисты

- https://gist.github.com/scyto/c66a053477b05552ef9f33fb1abed4a2/revisions — docker-compose
  для Infinitude (SERIAL_SOCKET на RS485→IP). RE-ценности нет.
- Гист TheCase с логом Bryant Evolution упомянут внутри acd/infinitive issue #5; отдельного
  URL в выдаче не было.

---

## Отдельно: thermostat→equipment command path (наш главный пробел)

Прямых внешних данных по конструкции 0305/0605 и staging НЕТ ни у кого из найденных.
Косвенно полезное:

1. **gofinity, Bootup Sequence** — единственное описание инициализации шины; читать первым
   при проектировании failover (содержимое секции в этом свипе не прочитано — рендер обрезан).
2. **brybus/CocoonTech**: термостат от 1F допрашивает новое устройство немедленно — наш
   эмулятор при взятии управления должен ожидать interrogation; и наоборот, появление
   настоящего 0x20/1F — надёжный сигнал уступки.
3. **Infinitude framing**: touch-термостат 1F01 broadcast-ит при старте — ещё один маркер
   присутствия Ion для failover-сторожа.
4. **lurgh**: побочный эффект записи глобальных параметров на часы термостата — учитывать
   в эмуляторе при записях режима.
5. **finitude**: методология корпуса WRITE/ACK06 + analysis.py — образец для нашего поиска
   писателей 0305/0605 по сезонным захватам.

## Отрицательные результаты (искали — ничего)

- `SYST0101CW` на GitHub — ничего релевантного (только шум выдачи).
- `BINF0479` — ничего. `CESR131626` — ничего.
- `"G80CTL"` site:github.com — ноль результатов.
- GitLab по Carrier Infinity / ABCD — ничего релевантного.
- Wireshark dissector для ABCD — не найден (есть только Kaitai .ksy внутри infinitesp).
- `"Ion System Control"` / ICP Ion GitHub-RE — ничего; только OEM-документация и маркетинг.
- Репозиторий Zhentar ihex_to_bin поиском site:github.com не подтвердился (упоминание — только
  в вики Infinitude).
- `"SAM01" / "SYSTXCCSAM"` — только OEM-документация SAM (shareddocs.com, SAM-ASCII RS-232)
  и мануал Elk M1XSP; GitHub-RE по SAM-железу нет.
- Гисты по Carrier Infinity ABCD — только docker-конфиг scyto (см. п.10).

## Оговорки

- Лицензии: ни для одного проекта лицензия не была подтверждена из прочитанного текста
  страниц в этом свипе — перед переиспользованием кода проверять файл LICENSE в репозитории.
- Содержимое секции Bootup Sequence в gofinity не прочитано (pkg.go.dev обрезал README).
- Вики Infinitude читалась через зеркало github-wiki-see.page; страницы Interpreting Data /
  Known Devices / Protocol Main поименно известны, их URL дословно в выдачу не попали.
