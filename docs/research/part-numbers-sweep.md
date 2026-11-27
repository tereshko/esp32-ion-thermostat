# Part-Numbers Sweep — внешняя литература по нашим точным номерам

Дата: 2026-11-26. Метод: веб-поиск (browser.search) по каждой точной строке отдельно и в
комбинациях + полный текст официальных release notes v4.79 (фетч + поиск внутри документа).
Цель: сервисная литература, таблицы параметров, дампы прошивок, RE-заметки, привязанные
именно к нашему железу: печь Heil G80CTL1352422A2, ODU HVA960GKA201, коил EN(A,D)4X61,
софты CESR******-**.79 (стена) / CESR******-** (печь) / CESR******-** (ODU), BINF0479,
SYST0101CW.

Главный итог одной строкой: **протокольных карт регистров / документации ABCD-шины в
публичном доступе нет** (ничего в свипе этому не противоречит), но нашлась почти вся
заводская сервисная литература по железу с реальными таблицами параметров (CFM, capacity),
а CESR-номера оборудования публично почти не индексируются — единственный след CESR*******
ведёт к плате инвертора HR46WR003.

---

## Ранжированные находки

### 1. F80CTL/G80CTL Installation Instructions — Table 4 «Air Delivery — CFM (With Filter)»
Полные таблицы CFM нагнетателя по внешнему статическому давлению 0.1–1.0" w.c. для всех
размеров, включая наш **1352422**, плюс DIP-конфигурация SW1/SW2/SW3 для некоммуникационного
режима (Clg / Low-Clg / Max Clg / Cont Fan / High Heat / Low Heat airflow) и поправки
CFM/ton: номинал 350; SW1-5 → 400 CFM/ton (+15%); SW4-3 → 325 (−7%); оба → 370 (+7%).
Это заводская «оболочка» тех CFM-значений, что Ion командует по шине.
- ManualsLib, стр. 16: https://www.manualslib.com/manual/3165333/Carrier-F80ctl.html?page=16

### 2. F80CTL & G80CTL (Series B) Installation, Start-Up, Operating and Service Instructions
Официальный PDF на ICP doc-сервере (shareddocs). Для нас ценное: раздел **«Furnace Control
Programming and Navigation»** (стр. 31+) — Table 21 System Status Display Codes, Table 22
Main Menu Options, Table 23 Test Sequence; airflow-таблицы; Troubleshooting Guide;
Parts Replacement Information Guide (стр. 53). Отдельного HK-номера платы для G80CTL в
открытых источниках нет — документация платы живёт внутри этого мануала.
- https://www.shareddocs.com/hvac/docs/1011/Public/0F/FG80CTL2-02SI.pdf
- Series A (предыдущее поколение того же мануала): https://www.shareddocs.com/hvac/docs/1011/Public/07/44101350001.pdf
  (наша печь по шине — G80CTL1352422A2; к какому поколению относить суффикс A2, из открытых
  источников однозначно не следует — держать оба мануала.)

### 3. HVA9 Application Guideline & Service Manual (421 08 5600 02, 2017)
Сервисный мануал на всю семью variable-speed ODU CVH8/HVH8/TVH8/CVA9/**HVA9**/TVA9:
Communication and Status Function Lights, Fault Codes/Descriptions, Factory Supplied Model
Plug Information, Variable Speed Drive LED, MOC LED, wiring diagrams, refrigeration system.
Это главный публичный источник по поведению нашего наружного блока и его индикации фолтов.
- https://manualmachine.com/airquest/cvh8hvh8tvh8cva9hva9tva9/27310740-service-manual/
- PDF-зеркало: https://images.tradeservice.com/ATTACHMENTS/DIR100423/Carrier-InternationalComfortProducts-TempstarHeating%26CoolingProducts_00318_1-40_OTHER2.pdf

### 4. Technical Support Manual — N Coils END4X/ENW4X/ENA4X (484 04 3600 00)
ICP TSM по коилам: **Airflow Tables (стр. 3–5)** и **Cooling Capacities** (TC/SHC/BF по CFM
и температуре насыщения). Самые «параметрические» данные по коилу, доступные публично;
наш EN(A,D)4X61 — тот же фамильный паттерн (E=evaporator, N=N-coil, (A,D)=варианты casing,
4=R-410A, X=TXV, 61=60 000 BTUH / 5 ton).
- http://icpindexing.toddsit.com/documents/086477/48404360000.pdf
- Installation Instructions END4X/ENW4X (484 01 3601 02), Table 1: END4X61 = 5 tons,
  24-1/2" width, liquid 3/8, suction 7/8; ориентир 350–400 CFM/ton:
  https://manualmachine.com/internationalcomfortproducts/end4x/8869186-installation-manual/
- Product Specifications ENH4X (484 61 3701 00), nominal acceptable CFM ranges:
  http://icpindexing.toddsit.com/documents/003350/48461370100.pdf
- Точная строка **EN(A,D)4X61** встречается дословно в ICP combination ratings: с печью
  *8MV*1352422** (тот же размерный код 1352422) — 58 500 BTUH @ 95°F, S/T 0.75, EER 12.0,
  SEER 14.5 (спеки CXA6, док. 421 56 6300 00):
  https://www.yumpu.com/en/document/view/34542668/product-specifications-green-comfort-heating-air-conditioning-inc/35

### 5. G80CTL Product Specifications (441 51 3500 01)
По нашему размеру **G80CTL1352422**: input 132 000 BTUH, 80% AFUE, **CFM range 690–2265
@ 0.5" w.c.**, output high 107 000 / low 70 000 BTUH (согласуется с equipment summary:
2-stage, 107K), certified ESP heat/cool 0.20/0.50.
- https://aciq.com/wp-content/uploads/2024/05/G80CTL-SpecSheet.pdf
- Тот же док на shareddocs: https://www.shareddocs.com/hvac/docs/1011/Public/0E/44156350001.pdf
- Series B Product Data (high-heat CFM по размерам, nomenclature): https://www.shareddocs.com/hvac/docs/1011/Public/08/G80CTL2-56-01PD.pdf

### 6. Официальные release notes v4.79 (BINF0479) — Ion и Carrier, ноябрь 2025
Подтверждают: один и тот же BINF0479.hex обслуживает SYST0101CW (Ion) и Carrier Infinity
Series B (SYSTXCCITC01-B и др.) / Bryant Evolution Series B. Пункты, релевантные управлению:
«Equipment FW update enhancements»; **«Removed compressor demand response from CFM
calculation to prevent fan surges»**; OpenADR 2.0; AHRI 1380. В истории версий (4.72)
прямо назван вендор связующего ПО: «Include DHCP fixes from **Clarinox** and reinitialize
sparkplug state after disconnect» — сходится с нашими stage-C находками по Clarinox.
**Проверено поиском по полному тексту: строки CESR в документе отсутствуют полностью** —
номера софтов оборудования в release notes не печатаются.
- Ion: https://preprod.ioncomfort.com/Content/docs/v0479-20251112.pdf
- Carrier Infinity: https://cetechsupport.com/wp-content/uploads/2025/12/sw_infinity_notes_0479.pdf

### 7. CESR******* → плата инвертора HR46WR003 (единственный публичный след)
eBay-листинг: «SANAHUA INTERNATIONAL **HR46WR003/CESR******-**** 5 TON INVERTER BOARD».
Т.е. CESR******* — софт инверторной (VFD) платы 5-тонного ODU; HR46WR003 — Carrier-номер
этой платы («INVERTER 5T», Radwell). Открывает поиск по HR46WR003 в Carrier-литературе
25VNA/189BNV-класса (там же model plug HK70EZ004 для 060-размера и таблица сопротивлений
пинов model plug).
- https://www.ebay.ie/itm/276714756826
- https://www.radwell.co.uk/Buy/UNITED%20TECHNOLOGIES/CARRIER/HR46WR003

### 8. HVA960GKA — кросс-референсы эквивалентов и рейтинги
HVACDirect по системе с HVA960GKA даёт эквиваленты: **Carrier 24VNA960A003, Tempstar
TVA960GKA, Bryant 189BNV060000** — ключи для поиска той же литературы под Carrier/Bryant.
Baker Distributing: 5 ton, 19 SEER, компрессор **5 stages, capacity range 25–100%**,
outdoor fan 4500 CFM, нужен Observer/Ion wall control v5.0+. AHRI certificate (ref 9891998):
HVA960GKA** + FCM4X60***L + WALLCON = 57 000 BTUH cooling, SEER2 16.50.
- https://hvacdirect.com/5-ton-16-seer-96-afue-120-000-btu-airquest-gas-furnace-and-air-conditioner-system-upflow-downflow-id47127.html
- https://www.bakerdist.com/5-ton-19-seer-a-c-condensing-unit-208-230-1-60-r-410a--74b4233
- https://www.scribd.com/document/763408862/Ahr-i-Certificate

### 9. CESR131626 — форумный след по соседней версии
hvactechgroup: SYSTXCCITC01-B с «System Control Firmware Version **CESR******-**.05**»,
fault 126 HIGH HEAT CYCLE ACTIVE на 59MN7; в треде: в 4.05 менялась airflow strategy
(понижены CFM-минимумы), откат на 3.61 убрал код 126. Поведенческие заметки о различиях
версий нашей семьи софта; таблиц параметров нет.
- https://www.hvactechgroup.com/hvacforum/index.php?topic=3244.0

### 10. Прочее полезное
- **Патент US 7,243,004** «Self-configuring controls for HVAC systems» (Carrier) — описан
  сам принцип: юниты сообщают свои характеристики центральному контрол
...[truncated 2705 chars]