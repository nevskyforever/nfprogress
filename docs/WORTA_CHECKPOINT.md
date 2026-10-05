# WORTA 6.0 — ПОЛНЫЙ ПРОЕКТНЫЙ ЧЕКПОИНТ

**Дата:** 5 октября 2026 года.\
**Методика:** WORTA ROADMAP SCORING v1.0.\
**Официальный зачтённый прогресс:** **77.0%**.\
**Последний полностью закрытый этап:** **C17 Shared Conflict Handling**.\
**Текущий статус:** C16 Desktop Sync — **CLOSED**; C17 Shared Conflict Handling / Conflict Resolution — **CLOSED**.\
**Текущий этап:** C18 Complete Project Sync — **IN PROGRESS**; C18.4 — **CLOSED**; C18.5.01–.06 — **REMOTELY ACCEPTED**; C18.5.07 — **LOCAL COMPLETE / REMOTE CI PENDING**.\
**Текущий статус C18.5:** **CLOSURE CANDIDATE / REMOTE CI PENDING**, окончательное CLOSED требует независимой приёмки .07; C18.6 — **NOT STARTED**.\
**Последняя независимая приёмка:** C18.5.06 SHA `d34254fef37501e95d7b435f35e3106e6d8eda95`; SQLite `37212649560` и Cloud `37212649515` — **SUCCESS**, включая обязательные multi-device/ACK jobs. C18.4 независимо CLOSED для SHA `ddfe65c5b606fca259a88bfc6644074098e9faac` (SQLite `37004006923`, Cloud `37004006914`). Последний закрытый полный roadmap stage остаётся C17.\

**ОБЯЗАТЕЛЬНО ДЛЯ СЛЕДУЮЩЕГО ЧАТА: внимательно прочитать разделы 3, 8–15 и 47–50 о методике работы, затем разделы 60–65.** Terra Medium — модель по умолчанию. Следующий самостоятельный implementation stage не начинать. Codex может обновлять checkpoint-файл после meaningful slice, но **не имеет права самостоятельно объявлять новые этапы `CLOSED`, менять официальный процент или scoring methodology**.

Документ предназначен для переноса **всего существенного контекста разработки** в следующий чат. Старый чекпоинт от 23.09.2026 фиксировал C15.5C как CI PENDING и 60,0%; настоящий документ заменяет устаревший статус. **Не пересчитывать проценты по собственным ощущениям, числу коммитов или объёму локальных изменений.**

## C18.5.07 — Cloud CI runtime correction (5 октября 2026)

Implementation SHA: `9b2c7594589b7dfa58b5b7fe83905f0336a7c710`.
Независимые результаты: SQLite **37288645324 — SUCCESS**; Cloud
**37288645301 — CANCELLED**. Frontend admin — **SUCCESS**; PostgreSQL обязательная
sync ACK / multi-device приёмка — **SUCCESS**, 52 passed, 0 skipped.
Отмена произошла позже в `Run focused cloud and legacy API tests`.

Сохранённый завершённый лог прочитан до изменений: PostgreSQL job
09:13:47–09:54:06 UTC 2026-10-05; подготовка 1:25, native checks 3:38,
mandatory 33:49, focused 1:24 до отмены. Лог подтверждает минимум 72 прошедших
focused теста; quiet output не позволяет точно определить итоговый count или
активный node ID. Последняя идентифицируемая активность — отрицательные
constraint checks C14 encrypted blobs. Assertion/test failure перед отменой
не обнаружен. Архивная check-run annotation подтверждает:
`The job has exceeded the maximum execution time of 40m0s`.
Классификация: **40-minute CI job timeout / runtime**.

Коррекция только Cloud workflow/docs: mandatory разделена на стабильные
foundation (30 tests) и content-action (22), focused regressions (194) вынесены
в независимый Python-only job. Каждый PostgreSQL job имеет отдельный disposable
service/database и прежний лимит 40 минут. Все 246 уникальных Python tests,
native filters, frontend и zero-skip mandatory guard сохранены. Production
protocols и три integration fixes baseline не изменены. Coverage manifest и
локальные результаты: `docs/cloud/C18_5_INTEGRATION_ACCEPTANCE.md`.
Локально один раз прошли все группы: foundation **30/30, 462.82s**;
content-action **22/22, 740.64s**; regressions **194/194, 106.10s**;
**0 skips, 0 failures**. YAML/structure/bash syntax, collection union,
`git diff --check` проверены; защищённые pyc не затронуты.

C18.5.07 остаётся **LOCAL COMPLETE / REMOTE CI PENDING**, коррекция после локальной
проверки — **CI CORRECTION LOCAL COMPLETE / REMOTE CI PENDING**. C18.5 —
**CLOSURE CANDIDATE / REMOTE CI PENDING**; C18 — **IN PROGRESS**; официальный
прогресс строго **77.0%**. P0/P1 remaining: 0/0. Закрытие допускается только после
независимой полной green remote приёмки. C18.6 не начат.

После push ожидается **Cloud backend tests** (два mandatory shards, regressions,
frontend admin). Cloud-workflow/docs-only paths не запускают SQLite по текущим
filters; implementation SQLite SUCCESS **37288645324** сохраняется. Codex не
polls Actions и не ждёт CI. Published correction SHA сообщается в task result.

## Permanent Codex CI handling rule

После успешно завершённого и разрешённого локального commit Codex самостоятельно выполняет `git push origin 6.0`; обычный push больше не требует ручного действия пользователя. После push Codex не ждёт GitHub Actions и не проверяет workflow через `gh`, GitHub API, браузер или другой polling. Codex сообщает published SHA и ожидаемые workflow/jobs, считает опубликованный slice `REMOTE CI PENDING` и завершает задачу. Независимую проверку remote SHA и GitHub Actions выполняет GPT-чат. Собственный commit/push Codex не даёт права объявить roadmap stage `CLOSED` или изменить официальный процент. ChatGPT сообщает пользователю рекомендуемые модель/thinking и необходимость нового Codex-чата вне копируемого task prompt; эти инструкции не включаются в task prompts. Сохранять это правило во всех следующих checkpoint.

**Permanent execution notes:** C18.4.03 is the inserted UX/diagnostics slice; account-object v2 contract + transport/reader readiness is **C18.4.04**; actual catalog durable substrate, explicit migration and writers are the next bounded **C18.4.05**, with no scoring change. When C21 Web begins, **first** build locally in a browser, audit every Tauri/desktop-only dependency, define/repair browser adapters and stabilize Web locally; **only then** deploy Web/backend to VPS/production infrastructure. C21 is not implemented here. Preserve these notes during checkpoint compaction.

Для новых ограниченных implementation slices предпочтительны иерархические номера `C<stage>.<substage>.<slice-two-digits>`: `C18.3.01`, `C18.3.02`, `C18.4.01`. Третий компонент содержит две цифры. Исторические `C18.1`, `C18.2` и C17 H/E identifiers не переименовываются. Нумерация служит организации работы, не вводит веса roadmap и не создаёт проценты для отдельных slices; scoring остаётся stage-based.

---

## 1. Репозиторий, ветка и проверенный baseline

- GitHub: `nevskyforever/nfprogress`.
- Основная ветка разработки WORTA 6.0: `6.0`.
- Проверенный пользователем baseline для C18.1: remote `6.0` HEAD `5c90ad02a61f5f764851c9b097b42507c6d237d3` (docs/checkpoint-only commit после принятого C17 implementation `d6c6dd39cb479c2dcaf560622f1eb692dcaddaf1`).
- Исторический C15 closure commit: `cb44169adf60858b1ed312990cca312ba960fe06` (`docs(roadmap): close C15 after remote acceptance`).
- C15 implementation commit `5b379d32e84da99f13e7f4aee0e56d0267fac78d` и его Windows correction `25476c611b91e26e5b94798dcf33a55924a45e08` independently accepted по двум required workflow; детали сохранены в разделе 60. Локальный `git status` перед следующими изменениями всё равно проверяется в самом Codex worktree.
- Точная локальная ветка/путь и `git status` должны проверяться в самом Codex worktree перед изменениями, а не предполагаться по старому отчёту.

### Последовательность важнейших remote commits

| **Этап**         | **SHA**                                    | **Сообщение / назначение**         |
| ---------------- | ------------------------------------------ | ---------------------------------- |
| C15.4D1A         | `9014af63171f0a385e5a1a25cec30bdd51bec1ab` | Harden note sealing contracts      |
| C15.4D1B         | `d746f169076269632dbf4cbaa09adf537020d08b` | Prevent sealing queue starvation   |
| C15.4D2A         | `55cc59ae441d90adc6cef92a8e8e2237906fdbe1` | Authoritative user key context     |
| C15.4D2B         | `465d81330d8182c1e3c6d6be9a91e7b9866a66c2` | Authoritative note sealing lease   |
| C15.5A           | `e509a353f8ee0a519111b18852cc3c3af448fba5` | Sealed note outbox reader          |
| C15.5B           | `56fd0bae1252e946373a3ec96491f252fb758808` | Durable encrypted note upload      |
| C15.5C           | `c1fdb7eaa618dd539c020b293e70e730a667e91c` | Bounded note upload retries        |
| C15.6A           | `8ccb4b23f876dbebb7ddcb95b00cc270176482b2` | Authoritative encrypted pull       |
| C15.6A follow-up | `13ed18d95ec8947abe37bc187a1a9125b3ed1e1e` | Bounded encrypted pull limit tests |
| C15.6B           | `22d046a357991713bfe74121414865ff1a2c80fe` | Durable encrypted inbox            |
| C15.6B follow-up | `3e3059950ad631e02551726984979a963dd10ae5` | Legacy v6 migration fixture repair |
| C15.7A           | `c52ebf7861fdda94fc01b41021138a3a642bc8a8` | Verified note inbox decryption     |
| C15.7B           | `9578706b9e86a12daceb42a3b69bdc8e60921ce9` | Atomic encrypted inbox remote apply |

## 2. GitHub Actions — последний независимо подтверждённый статус

**Текущая приёмка C18.5.06, независимо предоставленная owner/GPT:** SHA
`d34254fef37501e95d7b435f35e3106e6d8eda95` — **REMOTELY ACCEPTED**.

- [SQLite sync substrate 37212649560](https://github.com/nevskyforever/nfprogress/actions/runs/37212649560) — SUCCESS: Python/Rust substrate, Game vectors и предыдущие native entity regressions.
- [Cloud backend 37212649515](https://github.com/nevskyforever/nfprogress/actions/runs/37212649515) — SUCCESS: frontend, PostgreSQL, mandatory sync ACK/multi-device acceptance и focused API tests.

C18.5.01–.05 также REMOTELY ACCEPTED; точные SHA/run evidence сохранены ниже.
Секции LOCAL COMPLETE / REMOTE CI PENDING предыдущих slices ниже являются
историческими записями и не заменяют эту текущую сводку. C18.5.07 локально завершён;
C18.5 — CLOSURE CANDIDATE / REMOTE CI PENDING; C18 остаётся IN PROGRESS, официальный прогресс **77.0%**.

### Исторические remote acceptance evidence

**Для correction SHA `25476c611b91e26e5b94798dcf33a55924a45e08` (C15 closure):**

- [Cloud backend tests — run 35908520926](https://github.com/nevskyforever/nfprogress/actions/runs/35908520926): **SUCCESS**.
  - Mandatory PostgreSQL/headless acceptance: **9 passed, 0 skipped**.
  - Broad backend: **151 passed**.
  - Frontend curated: **219 passed** в 39 files; typecheck и production build — **SUCCESS**.
- [SQLite sync substrate tests — run 35908521004](https://github.com/nevskyforever/nfprogress/actions/runs/35908521004): **SUCCESS**.
  - Python SQLite substrate: **75 passed**.
  - Windows Rust SQLite: **24 passed**; Notes Sync: **80 passed**; account binding: **10 passed**; отдельный `cargo check` — **SUCCESS**.

Remote results относятся к correction SHA и подтверждают C15 closure. Предыдущая C15.7B приёмка ниже остаётся историческим baseline.

**Для SHA `9578706b9e86a12daceb42a3b69bdc8e60921ce9` (C15.7B):**

- [Cloud backend tests — run 35868491726](https://github.com/nevskyforever/nfprogress/actions/runs/35868491726): **SUCCESS**.
  - PostgreSQL cloud backend: **SUCCESS**.
  - Frontend admin: **SUCCESS**.
- [SQLite sync substrate tests — run 35868491642](https://github.com/nevskyforever/nfprogress/actions/runs/35868491642): **SUCCESS**.
  - Python SQLite substrate: **SUCCESS**.
  - Rust SQLite substrate: **SUCCESS**.

Оба workflow выполнены именно для указанного SHA; независимо подтверждено, что новые C15.7B frontend tests, Python cross-runtime proof и Rust test filters входят в соответствующие CI-команды. Исторические C15.7A workflow results сохраняются в разделе 34.

## 3. Закреплённая методика прогресса

**WORTA ROADMAP SCORING v1.0**, введена 23 сентября 2026 года. Шкала — 100 процентных пунктов; прогресс = сумма фиксированных весов официально закрытых/принятых этапов. `IN PROGRESS`, `IMPLEMENTED`, `COMMITTED`, `CI PENDING`, локально пройденные тесты и отчёт Codex без подтверждённой приёмки **не прибавляют процент**. Для заранее разделённого этапа засчитывается вес только каждого действительно закрытого подэтапа.

Изменение scope крупного этапа требует явного пересмотра методики, версии и старых/новых весов; скрыто менять проценты запрещено. Тесты и небольшие исправления внутри существующего этапа не меняют его вес.

## 4. Фиксированные веса всей дорожной карты

| **Группа**                                     | **Вес**    |
| ---------------------------------------------- | ---------- |
| Исторический задел до C7                       | 18,0%      |
| C7–C14: облачная инфраструктура и криптография | 32,0%      |
| C15: полная синхронизация Notes                | 20,0%      |
| C16: Desktop Sync                              | 3,0%       |
| C17: Shared Conflict Handling                  | 4,0%       |
| C18: Complete Project Sync                     | 7,0%       |
| C19: Android Local SQLite                      | 3,0%       |
| C20: Android Sync                              | 3,0%       |
| C21: Web                                       | 4,0%       |
| C22: Production Hardening                      | 2,0%       |
| C23: Failure/Disaster Tests                    | 2,0%       |
| PF 6.0 + Release Candidate                     | 2,0%       |
| **Итого**                                      | **100,0%** |

Исторические 18 пунктов — перенесённая плановая оценка, а не новая независимая перепроверка всех ранних задач. Процент не равен доле фактически потраченного времени.

## 5. Детализация C15 — 20,0 пункта

| **Подэтап**                                    | **Вес**  | **Текущий статус** |
| ---------------------------------------------- | -------- | ------------------ |
| C15.1 Encrypted Transport                      | 1,5      | CLOSED             |
| C15.2 Durable SQLite Substrate                 | 2,0      | CLOSED             |
| C15.3 Protocol/Codec Boundaries                | 2,0      | CLOSED             |
| C15.4 Durable Note Sealing/Foundation          | 3,0      | ACCEPTED           |
| C15.5A Sealed Outbox Reader                    | 0,5      | CLOSED             |
| C15.5B Durable Encrypted Upload                | 1,0      | CLOSED             |
| C15.5C Upload Runner/Retry                     | 1,5      | CLOSED             |
| C15.6A Encrypted Pull                          | 2,0      | CLOSED             |
| C15.6B Durable Inbox                           | 2,0      | CLOSED             |
| C15.7A Verified Inbox Decryption               | 1,0      | CLOSED             |
| **C15.7B Atomic Local Apply**                  | **1,0**  | **CLOSED**             |
| Full Orchestration, ACK, Two-Device Acceptance | 2,5      | CLOSED |
| **Итого**                                      | **20,0** |                    |

Доля исходного пакета «Decrypt and Local Apply» 2,0 разбита на C15.7A = 1,0 и C15.7B = 1,0; общая стоимость не изменилась.

## 6. Текущий расчёт прогресса

- C15: 20,0 / 20,0 → 70,0%.
- C16 Desktop Sync: +3,0 → 73,0% (**CLOSED**).
- C17 Shared Conflict Handling: +4,0 → **77,0%** (**CLOSED** после независимой remote-приёмки).
- C18–RC: осталось 23,0 процентных пункта; следующий этап — C18 Complete Project Sync.

**Официальный прогресс сейчас 77,0%; осталось 23,0 процентных пункта.** Веса и WORTA ROADMAP SCORING v1.0 не менялись.

## 7. История прежних оценок

21 сентября фигурировала предварительная оценка около 58%; позже называлось 45% на другой методике. 23 сентября внедрена фиксированная v1.0: первоначально 60,0% на C15.5B. Старые значения — исторические ориентиры, а не сравнимые измерения по одной формуле. В последующих чатах применять только scoring v1.0.

## 8. Правила официального закрытия этапов

После реализации: проверить фактический `git status`, точный commit, remote HEAD, **оба** требуемых workflow, каждую relevant job, фактическое включение новых тестов в CI и отсутствие случайно добавленных пользовательских файлов. У GitHub Actions сверять SHA и curated test list/path filters, а не только зелёный индикатор. Если CI ещё работает, упал или не запускал нужные tests — этап не `CLOSED`. ChatGPT может независимо проверить GitHub, но не локальный worktree до push. Если ранее принятый этап официально переоткрыт из-за дефекта, явно пересмотреть зачёт, не менять показатель молча.

**Четыре разных уровня доказательства:** (1) утверждение Codex; (2) проверенный локальный тест и фактический `git status` в его worktree; (3) commit и push пользователя; (4) независимо проверенный remote SHA и remote CI. Не подменять один уровень другим. `Added test` ≠ `test passed`; `cargo command failed before tests` ≠ `Rust test failed` и ≠ `Rust tests passed`; `CI SUCCESS` на старом SHA ≠ успех новой реализации. По каждому test suite указывать точный статус: **passed / failed / not run / skipped**.

**Checkpoint authority:** локальный Codex-апдейт checkpoint не является независимой приёмкой. Codex может написать `LOCAL COMPLETE`/`CI PENDING`, но `CLOSED` и официальный процент требуют post-push independent remote verification.

## 9. Изменение дорожной карты

При появлении крупной новой работы или исключении этапа описать scope, старые и новые веса, утвердить v2.0 и при необходимости пересчитать исторические контрольные точки по новой версии. Простая перенумерация и дробление внутри C15 не меняют его 20 пунктов.

## 10. Строгая методика совместной работы ChatGPT / Codex / пользователя

- **ChatGPT:** план, ограниченные по scope и стоимости задачи, проверка каждого отчёта по выполненному/невыполненному, следующий bounded prompt, checkpoint, независимая GitHub-проверка после push. Нельзя выдавать собственное предположение за проверенное состояние локальных файлов.
- **Codex:** читает фактический локальный worktree и целевые файлы, реализует только поставленный scope, запускает минимальные необходимые targeted tests, сообщает точные результаты и отдельно незапущенные проверки.
- **Пользователь:** управляет рабочей сессией и выбирает модель. После разрешённого завершённого commit обычный push в `origin/6.0` выполняет Codex самостоятельно. Не менять модель, не запускать второй параллельный Codex и не прерывать уже работающую задачу без необходимости/поручения.
- Для промежуточных локальных slices C15.7B **никаких самовольных commit/push**. Один общий commit только после завершения и проверки согласованного scope; push — отдельное решение пользователя.
- **Сначала анализ текущего отчёта.** Если prompt уже запущен, дождаться результата в ходе пользовательского взаимодействия; не отправлять заново то же задание и не выдумывать результат. Не переходить к другой самостоятельной стадии без отдельного запроса пользователя.
- **Экономить лимиты и ресурсы.** Terra Medium по умолчанию; выбирать Sol Medium/High лишь по реальной сложности. Нельзя автоматически рекомендовать Sol High просто потому, что в задании присутствует слово security. Текущее задание **уже работает на Sol High**; задним числом смена модели не окупит повторный запуск.
- **Не устраивать бесконечных аудитов.** Простой ошибочный путь, patch-context mismatch, не написанный тест или локальная ошибка рабочего каталога — повод для минимального исправления, а не нового архитектурного цикла и не формального `BLOCKED`.
- При проблеме редактирования читать **реальные текущие строки**, править небольшими отдельными операциями и удостоверяться, что запись действительно сохранилась. Не откатывать всю локальную работу из-за частной ошибки.
- **Без расширения scope:** не чинить unrelated warnings, не запускать преждевременные тяжёлые матрицы, не переписывать frozen contracts и не объявлять готовой следующую архитектурную стадию по успешному unit test предыдущей.
- При обсуждении статуса сохранять границы достоверности: подтверждено ранее по remote, сообщено Codex локально, ещё не запускалось, уже отправлено Codex и выполняется.
- ChatGPT сообщает рекомендуемые модель/thinking и необходимость нового Codex-чата **вне копируемого Codex prompt**. Не включать эти организационные рекомендации внутрь будущих заданий Codex.

## 11. Обязательный формат заданий Codex

Перед большим заданием кратко изложить цель и ожидаемый практический результат. **Рекомендуемый вариант модели/thinking и необходимость нового Codex-чата сообщать пользователю вне копируемого task prompt**, только если это действительно нужно. По умолчанию **Terra Medium**. Сам prompt давать **одним цельным копируемым блоком** (в интерфейсе удобнее отдельный WritingBlock, не дробить на несколько разрозненных сообщений).

В prompt всегда включать: последний проверенный remote baseline SHA (не подменяет локальный HEAD); требование проверить реальный `git status`/working directory; файлы и ограниченный scope; frozen contracts; короткий read-only осмотр только если нужен; конкретные действия; security invariants; критерии готовности; targeted tests и удалённую CI coverage; **TEST BUDGET**; явный запрет на `reset/clean/checkout`, неразрешённый commit/push и изменение пользовательских `.pyc`; формат `=== CODEX TASK RESULT === ... === END CODEX TASK RESULT ===` с указанием `passed/failed/not run/skipped`. После разрешённого завершённого commit Codex публикует его самостоятельно и сообщает `REMOTE CI PENDING` без polling.

Короткие исправления команды, patch или одного теста не превращать в новый многопроходный архитектурный аудит. Если задание реально выполнено только частично, давать follow-up только на незакрытый scope; не заставлять Codex заново делать уже завершённую часть. **Если Codex уже работает, новый prompt не выдавать, пока не получен его ответ.**

## 12. Формат следующих чекпоинтов и репозиторный checkpoint

**Канонический рабочий checkpoint рекомендуется хранить в репозитории как `docs/WORTA_CHECKPOINT.md`** (после передачи этого файла Codex и отдельного задания на внедрение схемы). Codex обновляет его после законченного meaningful slice и обязательно перед общим commit, чтобы локальный worktree содержал актуальный переносимый контекст.

**Критическая граница полномочий:** Codex может фиксировать в checkpoint только фактический локальный статус (`IN PROGRESS`, `IMPLEMENTED LOCALLY`, `TESTS PASSED LOCALLY`, `CI PENDING` и т. п.). **Codex не объявляет этап `CLOSED`, не увеличивает официальный процент и не меняет WORTA ROADMAP SCORING v1.0 по собственной инициативе.** `CLOSED` и новый официальный процент записываются только после: (1) завершения согласованного scope; (2) общего commit; (3) пользовательского push; (4) независимой проверки ChatGPT нового remote HEAD, обоих требуемых GitHub Actions workflow и всех relevant jobs.

При подготовке каждого нового Codex prompt ChatGPT должен явно указывать, **нужно ли обновить checkpoint в рамках этого задания**. Обычно после meaningful slice Codex обновляет локальный статус и следующий шаг. При финальной приёмке после независимой remote verification отдельным заданием обновляются `CLOSED`, SHA, CI и официальный процент. Не заставлять Codex переписывать checkpoint после каждого мелкого теста.

Checkpoint остаётся **одним полным Markdown-документом**, а не кратким пересказом. Сохранять дату, scoring v1.0, официальный процент и расчёт, точный GitHub SHA/CI, архитектуру, frozen contracts, существенную историю C15, состояние локального worktree по последнему отчёту, regression tests с `passed/failed/not run/skipped`, риски, уже запущенный prompt, экономную модель, TEST BUDGET, roadmap до релиза и правила работы. **Не сокращать документ путём удаления архитектурного или исторического контекста.**

## 13. TEST BUDGET и ресурсы

Mac можно использовать для Rust, real SQLite, Python, TypeScript, временной PostgreSQL в Docker, restart/recovery, сетевых сбоев и disposable integration environments **только там, где они реально необходимы**. Порядок: focused tests → минимальное исправление → повтор только затронутого focused test → **один** CI-equivalent full pass после законченного интеграционного этапа перед общим commit. Обычно не больше двух циклов исправления одной ошибки без нового диагноза. Не повторять успешные suites без затронувшего их изменения. Длительные команды — с разумными timeout; Docker не диагностировать бесконечно. Пропущенные tests явно помечать `not run`/`skipped`.

**Исторический локальный статус тестов:** прежний manifest-path сбой закрыт. Rust golden create/update реально выполнены и прошли **2/2**. Privileged connection security suite прошла, а после atomic-apply изменений релевантные privileged/default-deny regressions прошли **6/6**. Atomic remote-apply focused suite прошла **8/8**. Эти локальные результаты дополнила independently verified remote CI приёмка C15.7B.

Remote CI проверять по фактическому curated test list и workflow path filters. Для каждого будущего крупного C15 scope нужен один финальный CI-equivalent full pass соответствующих Python/Rust/TS suites до commit, затем оба remote workflows на **новом SHA** после пользовательского push.

## 14. Экономный выбор модели Codex — ОБЯЗАТЕЛЬНО СОБЛЮДАТЬ

**Приоритет стоимости:**

- **Terra Medium — модель по умолчанию** для обычной реализации, локальных тестов, golden fixtures, workflow/CI, небольших исправлений и большинства ограниченных Rust/TS задач. Она использовалась ранее и предпочтительна для экономии пользовательских лимитов.
- **Sol Medium** — когда конкретный анализ показывает сложную межслойную интеграцию и Terra не справилась или риск ошибки заметно выше.
- **Sol High** — только для существенно сложной криптографии, опасной конкурентности, необратимых операций, тонких security boundaries и итоговых security-аудитов, когда дополнительный thinking действительно оправдан.

**Историческое замечание:** один follow-up по privileged connection был запущен на Sol High после избыточной рекомендации; его не прерывали и он успешно завершился. После него работа возвращена к экономной схеме. `PROTECTED TYPESCRIPT / TAURI INTEGRATION` и финальная локальная приёмка завершены. Следующие обычные bounded implementation/test задачи также планировать на Terra Medium; Sol Medium/High использовать только при конкретно выявленной необходимости или финальном security audit.


## 15. Worktree и файлы пользователя

Исторически в локальном worktree находятся два пользовательских изменённых файла:

- `__pycache__/engine.cpython-312.pyc`
- `__pycache__/game_data.cpython-312.pyc`

Нельзя `reset`, `clean`, `checkout` либо намеренно менять/стейджить/коммитить эти файлы. Точное их состояние перед новой задачей проверить через `git status`; не делать вид, что локальный статус доступен из GitHub. Также нельзя откатывать всю незакоммиченную PASS 1 / migration 015 / plaintext decoder / golden fixture работу, накопленную с C15.7B.

## 16. Целевая архитектура WORTA

**Desktop:** Vue/TypeScript → Tauri/Rust → local SQLite → Common Sync Engine → client-side E2EE → HTTPS → FastAPI → PostgreSQL.

**Android:** Vue/TypeScript → Capacitor → local SQLite → Common Sync Engine → client-side E2EE → cloud API.

**Web:** Vue/TypeScript → client-side E2EE → cloud-first API.

Desktop/Android — local-first; Web — cloud-first. Local-only проекты не отправляются в облако автоматически. **Не синхронизировать SQLite как один файл**. Синхронизировать сущности и изменения через общий протокол.

## 17. Common Sync Engine

Один общий движок: durable outbox/inbox, event identity, revisions/parents, retry/backoff, шифрование, upload/pull, server acceptance/ACK, конфликты и restart recovery. Entity adapters отдельно реализуют codec, валидацию, зависимости, local apply, tombstones и предметную семантику конфликтов. Notes — первая тестовая вертикаль, а не отдельный навсегда замкнутый sync engine.

## 18. Security invariants

Облачный сервер не знает master password, Recovery Key, plaintext AMK, Object Keys или содержимое проектов. Шифрование/расшифровка — только на клиенте. Сброс пароля не тождественен восстановлению E2EE данных. Нельзя необратимо уничтожать единственную восстановимую копию заметки или применять silent Last Write Wins к тексту. HTTP-отправка не доказывает доставку: acceptance только по валидному durable server receipt. Данные, полученные с сервера, не становятся доверенными без криптографической и протокольной проверки.

## 19. Исторически завершённые этапы

C7 Admin; C8 Cloud Project State; C9 Sync Protocol; C10 Crypto Threat Model; C11 Crypto Module; C12 Crypto Tests; C13 Encrypted Cloud Schema; C14 Cover Pipeline; C15.1 Encrypted Transport; C15.2 Durable SQLite Substrate; C15.3 Protocol/Codec Boundaries; C15.4 Durable Note Sealing/Foundation; C15.5A/B/C; C15.6A/B; C15.7A. Не переписывать frozen contracts без отдельного design amendment.

## 20. Frozen C11 / C15.3 contracts

**C11:** client-side authenticated encryption, canonical nonce, immutable crypto-v1 AAD, authenticated AMK unwrap, повреждённые crypto records должны отвергаться.

**C15.3:** calendar-valid timestamp; входные UTC `Z` либо корректный offset, дробная часть 1–6 цифр; canonical outbound UTC с **6 микросекундными цифрами**; canonical lowercase UUID; JavaScript-safe integer bounds; initial revision 1, `parent_event_id = null`.

Лимиты: Note plaintext 8 388 608 bytes; Note ciphertext 8 388 624 bytes; encrypted batch ciphertext 16 777 216 bytes; HTTP wire body 33 554 432 bytes. Не «чинить» legacy invalid timestamps их безмолвной заменой текущим временем.

## 21. C15.4 — durable Note capture

Мутации cloud-bound Notes должны атомарно сохранять durable intent: create, update, delete, reorder и косвенные пути (map reconciliation/load/save, stage/project deletion). Migration 010 защищает legacy/Python изменения cloud-bound Notes без соответствующего intent; local-only проекты не должны создавать cloud events. При ошибке Note mutation и intent откатываются совместно.

## 22. C15.4 — coalescing/sealing

`cloud_sync_outbox` — реальная durable очередь; `cloud_sync_note_intents` — временный plaintext sidecar до sealing. Unsealed события могут coalesce, сохраняя event_id/revision/parent/local_ordinal; snapshot обновляется и `mutation_generation` увеличивается. Rust generation-CAS не даёт зашифровать устаревший snapshot. Успешный commit сохраняет encrypted object, удаляет sidecar, переводит lifecycle в sealed. При rollback durable intent остаётся. Matching-envelope replay возвращает `already_sealed`; другой ciphertext отвергается.

## 23. C15.4D1A — contract hardening

Commit `9014af63171f0a385e5a1a25cec30bdd51bec1ab`: safe `mutation_generation`, read-only исторический timestamp preflight, shared Rust↔TS IPC fixture, security/protocol CI. Preflight не переписывает даты, не подменяет текущим временем и не удаляет Notes. Legacy repair policy — отдельный будущий operational follow-up.

## 24. C15.4D1B — fairness

Commit `d746f169076269632dbf4cbaa09adf537020d08b`, migration 011. Раздельные durable cursors `regular`/`retry_blocked`, round-robin listing, отсутствие starvation. Простое listing не должно удалять intent, менять lifecycle или без причины увеличивать attempts. Cursors restart-safe.

## 25. C15.4D2A — authority

Commit `55cc59ae441d90adc6cef92a8e8e2237906fdbe1`, migration 012. Normal-user auth, `/account/me`, immutable local-account/backend-user binding, scoped `/account/crypto`, wrapped AMK, authenticated unwrap, runtime-only key context (`authEpoch`, `keyEpoch`, `keyContextId`). Local `account_id` и canonical backend `userId` — разные identity domains. Caller-provided userId и произвольный raw-AMK provider не становятся authority.

## 26. C15.4D2B — protected sealing

Commit `465d81330d8182c1e3c6d6be9a91e7b9866a66c2`. Draining key lease: `lease.use()` синхронно резервирует authority и охватывает encryption + commit IPC, затем освобождается в finally. Logout/account switch/key lock запрещают новые uses и дожидаются уже начатых операций. SQLite transaction не держится во время encryption/lifecycle wait. Linearization point — успешный SQLite COMMIT. Исторический C15.4 acceptance основывался на композиции TS barriers, IPC tests и real Rust/SQLite; единого браузер→Tauri→SQLite race-теста тогда не было.

## 27. C15.5A — sealed outbox reader

Commit `e509a353f8ee0a519111b18852cc3c3af448fba5`. `list_sealed_note_sync_outbox(account_id, limit)` — bounded account-scoped reading только sealed Note envelopes; deterministic dependency-safe order, parent/revision validation, tombstones после удаления проекта, restart-safe. Reader не возвращает plaintext/AMK, не шифрует повторно, не меняет lifecycle.

## 28. C15.5B — encrypted upload

Commit `56fd0bae1252e946373a3ec96491f252fb758808`. Authenticated binding → sealed outbox reader → bounded single-device batch → encrypted transport → backend `POST /api/v1/sync/encrypted/push` → receipt validation → atomic SQLite acceptance. До 100 событий, read limit 200; persisted event_id/nonce/ciphertext неизменны при retry. Прямой HTTP status без валидного ответа не достаточен.

## 29. Migration 013 — receipts

`013_note_sync_upload_receipts.sql` добавила `cloud_sync_upload_receipts` (account/event/device/server_sequence/duplicate/accepted_at). `event_id` PK, UNIQUE(account_id, server_sequence). Транзакция сохраняет подтверждённый receipt и переводит sealed→accepted, не удаляя encrypted object. Push acceptance не продвигает inbound pull cursor или device ACK.

## 30. Unknown delivery outcome

Если сервер закоммитил событие, но HTTP-ответ потерялся, клиент сохраняет исходный sealed event и после restart повторяет **тот же envelope**. Сервер может ответить `duplicate=true`; после проверки receipt клиент durable фиксирует acceptance. Не использовать тот же event_id для другого ciphertext и не удалять исходное событие до подтверждения.

## 31. C15.5C — upload runner/retry

Remote commit `c1fdb7eaa618dd539c020b293e70e730a667e91c`, migration `014_note_sync_upload_fairness.sql`, целевая schema 14 на тот момент. Реализованы single-flight, account/device coordination, error classification, retry/backoff, durable failure recording, fairness между устройствами, корректность receipt identity при диагностическом duplicate. Исторический старый чекпоинт видел CI PENDING; **к текущей контрольной точке C15.5C закрыт**, что отражено в фиксированном подсчёте +1,5.

## 32. C15.6A — authoritative encrypted pull

Remote commits `8ccb4b23f876dbebb7ddcb95b00cc270176482b2` и `13ed18d95ec8947abe37bc187a1a9125b3ed1e1e`. Получение зашифрованных событий от сервера под действующей account/device authority, bounded limit, протокольные проверки, устойчивость к замене строк и невалидным данным. Pull сам по себе не означает применение: encrypted events должны быть durable сохранены, а затем расшифрованы и применены отдельной стадией. Закрыт, зачёт +2,0.

## 33. C15.6B — durable encrypted inbox

Remote commits `22d046a357991713bfe74121414865ff1a2c80fe` и `3e3059950ad631e02551726984979a963dd10ae5` (дополнительное исправление legacy v6 migration fixture). Зашифрованные события сохраняются durable до расшифровки; inbox имеет состояния, в том числе `received`, `unknown_entity`, `orphan`, `applied`, `conflict`, `rejected`. Дедупликация/связь с persisted encrypted objects и протокольная целостность обязательны. Закрыт, зачёт +2,0. Не смешивать сохранение inbox с применением plaintext.

## 34. C15.7A — verified inbox decryption

Remote HEAD/commit `c52ebf7861fdda94fc01b41021138a3a642bc8a8`. Реализован bounded read-only Rust reader для inbox `received` Note events, TypeScript `NoteSyncInboxDecryptor`, проверка authenticated event/envelope внутри `AuthoritativeKeyContextLease.use()`. Существующий приватный `withDecryptedReceivedNoteInbox(...)` предоставляет внутреннему visitor кратковременные decrypted bytes; публичный `decryptOnce()` возвращает **только metadata**, не plaintext, AMK или ключи. Transient plaintext bytes очищаются после visitor. Отдельный тип ошибок Rust/visitor не должен маскироваться как crypto protocol failure.

Remote CI обоих workflow для точного SHA **SUCCESS**, все четыре relevant jobs **SUCCESS**. C15.7A CLOSED; зачёт +1,0; показатель достиг **66,5%**.

## 35. C15.7B — границы, реализация и закрытие

**Статус: CLOSED.** Remote commit `9578706b9e86a12daceb42a3b69bdc8e60921ce9` (`feat(sync): add atomic encrypted inbox remote apply`) независимо принят: Cloud backend run 35868491726 и SQLite substrate run 35868491642 — **SUCCESS**, все четыре relevant jobs — **SUCCESS**. Verified decrypted received Note event применяется как безопасное атомарное изменение локальной SQLite. TypeScript выполняет E2EE расшифровку в lease; Rust получает только краткоживущий plaintext payload и маршрутизацию/метаданные, а не AMK. Rust повторно проверяет source inbox/ciphertext identity и актуальную локальную версию перед записью. Обычный local Notes CRUD для remote apply не используется. Один SQLite `BEGIN IMMEDIATE` объединяет Note mutation + `cloud_sync_entities` + `cloud_sync_inbox.state`; rollback не оставляет частичного применения.

Полный пакет C15.7 = 2,0: A 1,0 и B 1,0 зачтены. После independently verified remote CI C15.7B официальный прогресс достиг 67,5%.

## 36. C15.7B PASS 1 — migration 015 и remote-apply substrate (локально)

По предыдущим отчётам Codex локально созданы/изменены:

- Forward-only `nfprogress/core/sqlite/migrations/015_note_sync_remote_apply.sql`; schema version Python/Rust повышена до 15.
- `frontend/src-tauri/Cargo.toml`: нужная возможность rusqlite `functions`.
- `frontend/src-tauri/src/sqlite.rs`, `nfprogress/core/sqlite/connection.py`, `nfprogress/core/sqlite/schema.py`: fail-closed runtime UDF.
- Общий вызов `note_sync_remote_apply_authorized(capability)`; на обычном Python/Rust соединении всегда false; сырой SQLite без зарегистрированной UDF не должен иметь возможность подготовить авторизованный remote write.
- Таблица `cloud_sync_remote_apply_authorizations`, три protected remote branches и one-shot consume triggers для remote INSERT/UPDATE/DELETE.
- Локальные guard branches из migration 010 сохранены; remote mode нельзя получить обычной SQL-командой на непривилегированном соединении.
- `trusted_schema=1`, только `SQLITE_UTF8` UDF flags (без DIRECTONLY/INNOCUOUS/DETERMINISTIC там, где это ломает trigger contract). Выделенный privileged Rust connection/внутреннее API ещё **не построено**.

Отдельно исправлена полнота local DELETE predicate: stage_id, source_type, source_map_id, source_node_id, content_format и прочие NULL-safe поля tombstone должны совпадать; нельзя допустить обхода intent guard при DELETE. Реальная schema-15 SQLite regression suite: 5 полевых несовпадений отклоняются DELETE guard, несовпадение deleted_at отклоняется upstream insert-validator, корректный tombstone проходит — **7 targeted tests passed** по отчёту Codex. Дополнительно ранее сообщались успешные targeted Python migration/UDF, Rust sqlite15, cargo check и diff-check; полный CI-equivalent pass был завершён до общего commit, а Python/Rust substrate coverage затем independently verified remote CI.

`.github/workflows/sqlite-sync-tests.yml` обновлён под Python cross-runtime proof `tests/test_c15_7b_cross_runtime_udf_proof.py` и Rust suites. Эта migration-015 coverage была independently verified в успешном SQLite substrate workflow для SHA C15.7B.

## 37. C15.7B — Rust plaintext decoder (локально)

Новый модуль `frontend/src-tauri/src/note_sync_plaintext.rs`, подключённый из `frontend/src-tauri/src/lib.rs`. Типы NoteSyncHeader/Route/Record/Tombstone/ChecklistItem, discriminated create/update/delete model; bounded 8 MiB decoder и eligibility `eligible` / `dependency_not_synced` / `unsupported_content_format`. Явное exact-key validation root/header/record/tombstone/checklist перед Serde, обязательное присутствие nullable keys даже при null, canonical lowercase UUID, calendar-valid шестизначные UTC timestamps, safe revision, parent/mutation/operation/identity checks. Metadata допускает произвольные вложенные JSON значения.

Реальный найденный Rust-only bug: Rust первоначально требовал `sort_order >= 1`, хотя frozen TypeScript принимает **любой JavaScript-safe integer**, включая 0 и отрицательные значения. Исправлено на `-MAX_SAFE_INTEGER..=MAX_SAFE_INTEGER`; golden create с sort_order 0 стал проходить. Ошибки `serde(flatten)` оказались ложным первоначальным объяснением: serde conversion для create проходил, отказывала именно проверка sort_order.

Последняя самостоятельная локальная Rust plaintext suite до golden expansion: **5 passed, 0 failed**; cargo check и diff-check прошли. Это 5 test functions с несколькими table-driven cases, а **не доказательство исчерпывающей отрицательной матрицы**. Некоторые missing/extra root/header/tombstone/checklist, valid delete и крайние случаи ещё нужно подтвердить отдельно. CI `sqlite-sync-tests.yml` path filters расширены на новый Rust module для push и PR; существующая `cargo test ... note_sync` команда должна находить его tests.

## 38. C15.7B — golden cross-language fixtures: актуальный локальный статус

`frontend/src/cloud/__fixtures__/noteSyncPlaintextV1.json` содержит golden create и update, canonical JSON порождён production TypeScript `canonicalNoteSyncJson()`.

Подтверждено локальными отчётами Codex:

- TypeScript golden create/update suite: **2 passed, 0 failed**.
- Rust `golden_create` + `golden_update`: **2 passed, 0 failed** на тех же checked-in canonical bytes.
- Rust decoder принимает весь JavaScript-safe integer диапазон `sort_order`, включая 0 и отрицательные значения.
- Frozen TypeScript codec и исходный golden create не переписывались.

Golden delete, дополнительные eligibility fixtures и полная cross-language negative matrix не объявлены отдельным завершённым fixture package. Для закрытого C15.7B достаточность plaintext/apply contract подтверждена существующими focused tests и remote CI; расширять fixture matrix можно только отдельным будущим scope, если это будет обосновано.

## 39. C15.7B — privileged Rust connection: локально реализовано

Последний завершённый security slice реализовал внутренний API в `frontend/src-tauri/src/sqlite.rs`:

- `PrivilegedRemoteApplyConnection`
- `RemoteApplyAuthorization`
- `open_privileged_remote_apply_database()`
- `authorize_once()`
- позже для atomic apply добавлен internal `execute_planned_once()`

Основная модель authority:

- fresh 256-bit capability на операцию;
- capability хранится только в connection-local `Arc<Mutex<Option<String>>>`;
- ordinary Rust/Python connections default-deny;
- SQL-only insertion authorization row недостаточна без активной скрытой capability;
- capability выдаётся только непосредственно перед точно спланированной Notes mutation;
- migration-015 consume trigger обязан погасить authorization;
- RAII guard очищает capability при success, rollback и любой ошибке;
- важный edge case исправлен: revoker создаётся **до** fallible authorization SQL, чтобы ошибка самой вставки не могла оставить capability активной;
- API не экспортирован в frontend/Tauri IPC как механизм выдачи arbitrary capability.

Первоначальные focused security tests прошли 5/5; после доработки atomic apply релевантная privileged/default-deny regression suite прошла **6/6**.

## 40. C15.7B — Rust Atomic Local Apply: локально реализовано

Добавлен внутренний typed entry point `apply_verified_received_note()` в `frontend/src-tauri/src/note_sync.rs`.

Atomic apply выполняет единый `BEGIN IMMEDIATE` и внутри него повторно проверяет mutable/persisted state до записи. Реализованы remote create, update и delete/tombstone.

Локально заявленная и протестированная семантика:

- re-read source inbox и encrypted-object identity;
- account/device/project/entity binding;
- revision/parent/head classification;
- защита от local unsealed changes;
- точная one-shot remote authorization;
- Note mutation + `cloud_sync_entities` + inbox state в одном COMMIT;
- exact replay → `AlreadyApplied`;
- self-echo только по durable outbox + upload receipt + device/server-sequence/metadata evidence;
- self-echo не перезаписывает более новую local unsealed Note;
- missing project/parent → orphan;
- incompatible head/local unsealed mutation → conflict;
- envelope/metadata mismatch → rejected;
- delete уже отсутствующей Note продвигает tombstone head без создания placeholder Note;
- не изменяются local outbox/intents, pull cursors, ACK, receipts или encrypted objects;
- deterministic fault после Notes mutation подтверждает полный rollback.

Focused atomic remote-apply suite: **8 passed, 0 failed**.

Релевантные privileged/default-deny regressions после этих изменений: **6 passed, 0 failed**.

`cargo check --manifest-path frontend/src-tauri/Cargo.toml`: **passed**.
`git diff --check`: **passed**.
TypeScript typecheck в этом проходе не запускался, потому что TypeScript не менялся.

Локальные результаты выше сохранены как история разработки; их итог independently verified remote CI для commit C15.7B указан в разделах 2 и 35.

## 41. C15.7B — protected TypeScript / Tauri integration

Реализована композиция:

Durable encrypted inbox → authenticated decrypt внутри `AuthoritativeKeyContextLease.use()` → кратковременный canonical plaintext → узкий Tauri apply IPC → Rust structural validation → persisted inbox/encrypted-object re-check → существующий `apply_verified_received_note()` → atomic SQLite apply.

Фактические границы:

- `withDecryptedReceivedNoteInbox(...)` экспортирован только как `@internal` callback boundary; публичный `decryptOnce()` остаётся metadata-only;
- lease удерживается до завершения `await` Tauri IPC;
- AMK, Recovery Key, Object Keys и master password в Rust не передаются;
- IPC DTO принимает только bounded routing/envelope fields и plaintext bytes, запрещает неизвестные поля и не принимает SQL/path/capability;
- TypeScript и Rust очищают контролируемые ими mutable byte buffers best-effort; JavaScript/Tauri/serde могут создавать независимые копии, полное уничтожение которых не заявляется;
- decrypt failure не вызывает apply; IPC/apply failure не маскируется как `decrypt_failed` и не уничтожает durable inbox;
- Rust повторно проверяет account/device/project/entity, immutable inbox metadata, nonce/ciphertext identity, revision/parent/head и local unsealed state внутри `BEGIN IMMEDIATE`;
- create/update/delete, replay, self-echo, tombstone, rollback и default-deny authorization покрыты real-SQLite Rust tests;
- local outbox/intents, pull cursor, ACK, upload receipts и encrypted objects remote apply не меняет.

Focused integration results до финального pass: TypeScript decrypt/apply tests **7/7**, Rust `remote_apply_` tests **10/10**, relevant privileged tests **2/2**, TypeScript typecheck, cargo check и diff-check passed.

## 42. Основные риски и оставшиеся ограничения

1. **C15.7B remote acceptance завершён.** Commit `9578706b9e86a12daceb42a3b69bdc8e60921ce9` и оба required workflow independently verified SUCCESS; это закрывает C15.7B, но не запускает следующий пакет автоматически.
2. **IPC trust boundary:** зарегистрированный Tauri command технически renderer-callable. Это приемлемо в закреплённой C10/C11 модели, где compromised unlocked renderer/device находится вне E2EE storage guarantee; command не считается отдельной криптографической authority. CSP ограничивает scripts `self`, production использует bundled `frontendDist`, remote IPC scopes отсутствуют. XSS/supply-chain compromise остаётся честно зафиксированным риском C21/C22.
3. **Rust не повторяет AEAD verification:** authority authenticated decrypt остаётся в TypeScript key lease. Rust проверяет structure и persisted identity/state; произвольный код уже с правами разрешённого renderer остаётся вне этой локальной integrity guarantee.
4. **Plaintext lifecycle:** TS/Rust очищают доступные mutable buffers best-effort, но невозможно гарантировать уничтожение всех JavaScript/IPC/serde copies.
5. **Нет одного настоящего browser → Tauri → SQLite end-to-end harness:** boundary доказана композицией focused TypeScript mock-IPC tests и real Rust/SQLite tests. Full orchestration/scheduler относится к следующему пакету.
6. **Curated frontend local environment:** локальная среда ранее дала 190/191 с unrelated `src/api/admin.spec.ts`/`localStorage` failure. Однако обязательный remote Frontend admin job для SHA C15.7B — **SUCCESS**; production defect по этому локальному исключению не исправлялся.
7. **PostgreSQL cloud job:** локально не запускался, поскольку backend production code C15.7B не менялся; обязательный remote PostgreSQL cloud backend job для SHA C15.7B — **SUCCESS**.
8. **Два пользовательских `.pyc` остаются вне scope и не должны попасть в commit.**
9. **Официальный прогресс — 67,5%.** Остающиеся 32,5 пункта не начисляются до независимого закрытия следующих пакетов.

## 43. Оставшийся roadmap после C15

- **C16 Desktop Sync +3,0** → **73,0%**.
- **C17 Shared Conflict Handling +4,0** → **77,0%**.
- **C18 Complete Project Sync +7,0** → **84,0%**.
- **C21 Web +4,0** → **88,0%**.
- **C22 Production Hardening +2,0** → **90,0%**.
- **C23 Failure/Disaster Tests +2,0** → **92,0%**.
- **PF 6.0 + Release Candidate +2,0** → **94,0%**.
- **Первый публичный релиз:** Desktop + Web на отметке **94,0%** полной дорожной карты.
- **C19 Android Local SQLite +3,0** → **97,0%**.
- **C20 Android Sync +3,0** → **100,0%**.

Это утверждённый **Web First** порядок исполнения. C19/C20 не отменены: их суммарные 6,0 пункта перенесены после первого публичного релиза и не блокируют выпуск Desktop + Web. Номера, веса этапов и WORTA ROADMAP SCORING v1.0 не изменены; исторический прогресс не пересчитывается. Эти проценты — плановые суммы **при условии официального закрытия каждого этапа**, а не прогноз даты выпуска.

### Обязательное требование C18 — метаданные проекта

C18 Complete Project Sync обязан передавать между устройствами пользовательское название проекта, синхронизировать его переименования и остальные поддерживаемые пользовательские метаданные проекта. Названия и метаданные должны быть client-side E2EE; при конкурентном переименовании применяются правила conflict handling C17, без silent overwrite или LWW.

Нужна отдельная безопасная миграция уже подключённых C16 проектов: разные локальные названия на устройствах не являются доказательством общей истории и не дают права автоматически перезаписать одно из них. До завершения этой миграции C16 импорт честно требует обязательное локальное название для создания local project shell; оно не считается синхронизированным.

### Обязательное требование C18 — клиентское сжатие до E2EE

C18 должен спроектировать и реализовать сжатие подходящих plaintext-данных **до** E2EE-шифрования, прежде всего текстов, Notes и структурированных объектов. Версия и алгоритм сжатия обязаны однозначно определяться получателем; уже существующие encrypted objects остаются читаемыми, а frozen C11/C15 crypto/AAD/protocol v1 нельзя задним числом переопределять. Распаковка обязана иметь жёсткие ограничения итогового размера, памяти, CPU/времени и глубины/структуры, чтобы malformed или adversarial input fail closed.

Выбранный формат должен воспроизводимо работать на Desktop, Web и будущем Android. Уже сжатые медиа нельзя автоматически сжимать без измеримого выигрыша. Перед выбором сравнить размер, скорость, peak memory, browser/native/mobile compatibility и качество поддерживаемых реализаций. Zstandard — только кандидат, а не предрешённая зависимость; лицензии конкретных bindings/wrappers и их dependency tree проверяются отдельно от эталонной реализации.

### Обязательное требование C22 — квоты занятого облачного пространства

Существующий лимит количества cloud projects сохраняется. Дополнительно C22 вводит независимую серверную квоту фактически занятого пространства аккаунта: глобальное значение по умолчанию и индивидуальный override для конкретного пользователя. Учёт охватывает реально хранимые encrypted objects и attachments; политика учёта immutable versions/history должна быть явно определена. Enforcement при concurrent uploads должен быть атомарным, а exact immutable replay/retry не должен повторно списывать объём.

Переполнение квоты не уничтожает локальную работу: новые uploads получают понятный typed отказ, но получение и удаление данных не блокируются только из-за превышения лимита. Silent deletion старых версий запрещён без отдельного безопасного retention/compaction contract.

Административная панель C22 должна показывать использованное пространство каждого пользователя, effective quota, глобальную квоту, индивидуальный override и аккаунты, приближающиеся к лимиту. Пользовательские настройки Desktop и Web должны показывать used/total/free, визуальный индикатор, предупреждения при 80% и 95% и понятное сообщение о невозможности новых uploads при заполненной квоте. Admin UI, quota accounting/enforcement и эти user controls не относятся к C16 Pass 3C и сейчас не реализованы.

### Обязательный GPLv3 dependency gate

WORTA распространяется по GNU GPLv3. Для C18, C21, C22 и любой последующей новой зависимости до выбора/добавления библиотеки обязательно проверить точную лицензию используемой версии, транзитивные зависимости, условия распространения Desktop/Web/Android builds, необходимые notices/copyright statements и отсутствие commercial-only, restrictive source-available либо иных несовместимых условий. MIT, BSD и Apache 2.0 допустимы только после конкретной проверки совместимости и distribution obligations. Этот gate применяется ко всем новым runtime/build/test dependencies; compression packages в C16 не добавляются.

## 44. Принципы релиза

Первый публичный релиз WORTA 6.0 теперь означает готовые **Desktop + Web** после PF 6.0 / Release Candidate на отметке 94,0% полной roadmap. Android остаётся post-release scope C19/C20 и доводит полную roadmap до 100,0%. Desktop/Android local-first, Web cloud-first; local-only проекты не выгружать автоматически; E2EE не ослаблять; encrypted pull без verified apply — не завершённая синхронизация; нельзя silently overwrite пользовательский текст. Перед релизом отдельно спроектировать release automation; исторически обсуждавшаяся команда `npm run release -- 6.0.1 --all` и опции `--web`, `--desktop`, `--mobile`, `--dry-run` — план, **не утверждение об уже реализованном script**.

## 45. Правило ответа на вопрос «сколько процентов?»

Только WORTA ROADMAP SCORING v1.0. Называть последний закрытый этап, точный зачёт, следующий незавершённый этап и условие следующего прибавления. Текущий ответ: **77,0%; последний закрытый этап — C17; C18 Complete Project Sync начат как design/contract work, не закрыт и после полного закрытия добавит 7,0 пункта.** Не менять процент из-за объёма локальной работы или неподтверждённого результата.

## 46. Точка продолжения в новом чате — ТЕКУЩЕЕ СОСТОЯНИЕ

**C16 Desktop Sync и C17 Shared Conflict Handling закрыты после независимой remote-приёмки.** C17 включал durable conflict preservation, frozen resolution v2, transport-v2 cutover, causal continuation и coordinated two-/three-device acceptance.

**Repo/branch:** `nevskyforever/nfprogress`, `6.0`.
**Последний независимо подтверждённый remote HEAD:** `d6c6dd39cb479c2dcaf560622f1eb692dcaddaf1`.
**Official progress:** **77,0%**, WORTA ROADMAP SCORING v1.0.
**Last CLOSED:** C17 Shared Conflict Handling / Conflict Resolution.
**Now:** C16 Desktop Sync — **CLOSED**; C17 Shared Conflict Handling — **CLOSED**.
**Current:** C18 Complete Project Sync — **IN PROGRESS / C18.1 CONTRACT FROZEN LOCALLY**. Следующее начисление возможно после полного закрытия C18 (+7,0 пункта).
**Hard rules:** E2EE/lease; frozen crypto/protocol v1; account-wide reconciliation before pull/ACK; unsupported Notes fail closed; no silent data loss/merge/LWW; no reset/clean/checkout; no unrelated changes; commit только после разрешённых gates, затем самостоятельный push без CI polling; exact `passed/failed/not run/skipped`; не увеличивать процент до independently verified CLOSED.

## 47. МЕТОДИКА РАБОТЫ — ПРЯМОЕ ОБЯЗАТЕЛЬНОЕ УКАЗАНИЕ ДЛЯ СЛЕДУЮЩЕГО АССИСТЕНТА И CODEX

**ВНИМАТЕЛЬНО И В ПОЛНОМ ОБЪЁМЕ СЛЕДОВАТЬ МЕТОДИКЕ ЭТОГО ЧЕКПОИНТА.** Этот файл нужен не только как справка о коде, но и как защита от дрейфа процесса: повторных задач, лишнего расхода моделей, неподтверждённого `CLOSED`, повторных тяжёлых тестов и потери frozen contracts.

**Практический чек-лист перед КАЖДЫМ новым prompt или оценкой отчёта:**

1. Проверить последнее сообщение пользователя и самый свежий `=== CODEX TASK RESULT ===`: что реально выполнено, что только написано, что не запускалось и что уже выполняется. C16 и C17 закрыты после independently verified remote acceptance; C18.1 — только локально замороженный design-контракт, C18 не закрыт.
2. Всегда разделять: **independently verified remote** / **Codex-reported local** / **not run or unknown**.
3. WORTA ROADMAP SCORING v1.0 не импровизировать. Сейчас **77,0%**. C16 (+3,0) и C17 (+4,0) закрыты; Web First меняет порядок исполнения, но не номера, веса или формулу.
4. Выбирать минимальный достаточный следующий slice. Не повторять уже закрытый локальный scope без изменения, которое могло его сломать.
5. **Terra Medium first.** Sol Medium/High только по конкретной доказанной необходимости или на отдельный финальный security audit.
6. TEST BUDGET: focused tests → минимальный fix → repeat только затронутого → один full CI-equivalent pass перед общим commit.
7. Не ломать E2EE, draining lease, frozen codec, fail-closed SQL guards, one-shot capability, durable inbox/receipts, no-silent-LWW и no-echo.
8. Во всех prompts явно писать: `no reset/clean/checkout`, `no unrelated changes`, commit только после разрешённых local gates, затем Codex самостоятельно публикует завершённый slice; два `.pyc` не трогать.
9. После локальной реализации требовать точные test counts, `git status`, `git diff --check`, CI coverage. После push Codex сообщает опубликованный SHA и ожидаемые workflow без polling; GPT-чат независимо проверяет **новый SHA** и все relevant jobs обоих workflow.
10. При отсутствии доказательства писать `unknown/not run`, а не достраивать результат предположением.

## 48. ПРАВИЛО РЕПОЗИТОРНОГО CHECKPOINT — НОВЫЙ РАБОЧИЙ ПРОЦЕСС

Пользователь планирует передать этот файл Codex и хранить дальнейший checkpoint непосредственно в репозитории, предпочтительно как:

`docs/WORTA_CHECKPOINT.md`

После внедрения схемы Codex должен обновлять этот файл **после законченного meaningful slice и перед общим commit**, но не после каждого мелкого теста.

### Что Codex МОЖЕТ обновлять самостоятельно

- локально реализованные файлы/API;
- точные результаты targeted tests;
- `passed/failed/not run/skipped`;
- актуальные риски и ограничения;
- какой prompt/slice завершён;
- какой следующий минимальный технический шаг;
- локальный статус вроде `IN PROGRESS`, `IMPLEMENTED LOCALLY`, `LOCAL TESTS PASSED`, `CI PENDING`;
- фактический `git status`, если он только что прочитан Codex;
- новые архитектурные решения, принятые в рамках явного prompt и не меняющие frozen contracts.

### Что Codex НЕ МОЖЕТ объявлять самостоятельно

- `CLOSED` для любого текущего или будущего roadmap stage;
- новый официальный процент;
- новый independently verified remote SHA;
- успешный remote CI, которого он не проверял как независимую post-push приёмку;
- изменение WORTA ROADMAP SCORING v1.0 или весов;
- удаление существенной истории/методики ради сокращения файла;
- переход к следующему самостоятельному roadmap stage без задания.

### Как этап становится CLOSED в checkpoint

1. Codex завершает локальный scope и обновляет checkpoint как **LOCAL COMPLETE / CI PENDING**, если это соответствует фактам.
2. Выполняется один финальный CI-equivalent local pass.
3. Делается единый commit без пользовательских `.pyc`.
4. **Codex** самостоятельно выполняет `git push origin 6.0` после разрешённого успешного commit, сообщает published SHA и завершает задачу со статусом `REMOTE CI PENDING`, не ожидая Actions и не выполняя polling.
5. **ChatGPT независимо проверяет** новый remote HEAD, оба GitHub Actions workflow, relevant jobs, curated tests/path filters.
6. Только после этой проверки пользователь/ChatGPT дают Codex отдельное указание обновить `docs/WORTA_CHECKPOINT.md`: поставить `CLOSED`, новый SHA/CI и официальный процент.

Следовательно, в будущих prompts формулировка должна быть не «объяви этап завершённым», а:

**«Обнови `docs/WORTA_CHECKPOINT.md` по фактическому результату этого slice. Не ставь `CLOSED` и не меняй официальный процент без явно переданной independently verified remote acceptance. Если этот prompt содержит такую acceptance, внеси её точно как дано.»**

Это предотвращает ситуацию, когда Codex сам становится одновременно исполнителем и единственным приёмщиком собственной работы.

## 49. Ближайшее действие (историческая запись до закрытия C15)

На момент этой исторической записи roadmap package **Full Orchestration, ACK, Two-Device Acceptance** (2,5 пункта) был `IN PROGRESS` локально, не `CLOSED`. Этот план был завершён и затем принят remote; текущая точка продолжения указана в разделе 46.

Тогда уже были локально завершены Slices 1–3 durable ACK substrate/transport и bounded Notes orchestrator, Slices 4B1–4B2 durable identity/headless normal-user session runtime, а также Slice 5A file-backed SQLite lifecycle preparation. Следующим планировался отдельный bounded PostgreSQL two-device integration acceptance.

Далее:

- сохранить frozen contracts при scope pass и реализации Slice 4;
- не начинать two-device harness, scheduler, C17 или новую архитектуру автоматически;
- для закрытия будущего пакета повторить полный процесс: локальная приёмка, единый commit, пользовательский push и независимая remote-проверка SHA/workflows/jobs.

## 50. Финальная локальная приёмка и remote-закрытие C15.7B — 23 сентября 2026

**Security audit:** подтверждённых C15.7B privilege-escalation defects на renderer/Rust boundary не найдено. Tauri command renderer-callable, но в C10/C11 threat model тот же unlocked renderer уже владеет key-backed decrypt/plaintext authority; compromised unlocked client, XSS и privileged extension находятся вне E2EE storage guarantee. Новый command не принимает SQL, path, capability или keys, а Rust не доверяет caller routing assertions без durable account/device/inbox/encrypted-object/head checks. Production Tauri использует bundled frontend, `script-src 'self'`, и не объявляет remote-domain IPC access. Это не защита от compromised renderer; это bounded trusted-client boundary.

**Подтверждённая композиция:** authenticated TypeScript decrypt в draining lease → canonical plaintext bytes → narrow Tauri IPC → strict Rust decoder → `BEGIN IMMEDIATE` → one-shot connection capability → Note/head/inbox COMMIT. Decrypt/IPC/SQL errors fail closed; rollback сохраняет Note/head/inbox и возвращает connection в default-deny. Replay, durable-evidence self-echo, local-unsealed conflict и tombstones покрыты focused tests. AMK/Object Keys/password не пересекают IPC.

**Минимальные исправления финального pass:** legacy v6 fixture теперь удаляет migration-015 authorization table и consume triggers перед повторным upgrade; recovery schema matrix знает migration 015. Дополнительно закрыт реальный silent-overwrite риск: revision-1 remote create теперь конфликтует с уже существующей Note без подтверждённого remote head, вместо перезаписи только по совпадению ID; добавлен real-SQLite regression. Production migration/crypto/IPC contracts не менялись.

**CI-equivalent local results:**

- Python SQLite workflow command: **75 passed, 0 failed**, 1 unrelated deprecation warning.
- Rust `sqlite` filter: **21 passed, 0 failed**.
- Rust `note_sync` filter: **75 passed, 0 failed** (включая atomic apply, plaintext, golden cases и защиту unproven existing Note).
- Rust `account_binding` filter: **4 passed, 0 failed**.
- Frontend curated workflow command: **190 passed, 1 failed**, 31/32 files passed; единственный failure — известный unrelated `src/api/admin.spec.ts` из-за отсутствующего Node `localStorage`.
- TypeScript typecheck: **passed**.
- Frontend production build: **passed** с прежними chunk/dynamic-import warnings.
- Cargo check: **passed** с прежними unrelated warnings.
- PostgreSQL cloud backend suite: **not run** локально; backend production code не менялся и disposable PostgreSQL/Docker не поднимался.
- `git diff --check`: **passed** после установки этого checkpoint.

**CI wiring:** cloud workflow path filters охватывают `frontend/src/**`, Rust apply/lib и workflow; curated Vitest list содержит golden/decrypt/apply specs. SQLite workflow filters охватывают migration/Python substrate, Rust sqlite/note_sync/plaintext/lib/project files, Cargo manifests, shared fixture и C15.7B Python proof; команды запускают все соответствующие Python/Rust suites.

**Независимая remote-приёмка и закрытие:** commit `9578706b9e86a12daceb42a3b69bdc8e60921ce9` (`feat(sync): add atomic encrypted inbox remote apply`) pushed и independently verified. [Cloud backend tests 35868491726](https://github.com/nevskyforever/nfprogress/actions/runs/35868491726) — **SUCCESS**: Frontend admin и PostgreSQL cloud backend. [SQLite sync substrate tests 35868491642](https://github.com/nevskyforever/nfprogress/actions/runs/35868491642) — **SUCCESS**: Rust SQLite substrate и Python SQLite substrate. C15.7B — **CLOSED**; официальный прогресс — **67,5%**; последний `CLOSED` этап — C15.7B. Следующий пакет Full Orchestration, ACK, Two-Device Acceptance имеет локально реализованный Slice 1 и не закрыт.

## 51. Full Orchestration / ACK — Slice 1 durable ACK substrate (локально)

**Статус:** `IMPLEMENTED LOCALLY`; весь пакет Full Orchestration, ACK, Two-Device Acceptance остаётся `IN PROGRESS`, не `CLOSED`. Официальный прогресс остаётся **67,5%**; нового independently verified remote SHA или remote CI нет.

В `frontend/src-tauri/src/note_sync.rs` добавлены внутренние Rust/SQLite операции `prepare_note_sync_ack()` и `commit_note_sync_ack()`. Обе повторно подтверждают durable local-account/backend-user/device scope через существующий binding. Первая только читает максимальный непрерывный prefix от `ack_cursor + 1` до `pull_cursor`, состоящий исключительно из inbox rows со state `applied`; gaps, `received`, `orphan`, `conflict`, `rejected` и `unknown_entity` останавливают candidate. Вторая получает expected old cursor и уже подтверждённый transport candidate, повторно проверяет prefix в `BEGIN IMMEDIATE` и делает CAS-style advance только без регресса. Exact replay возвращает `already_acknowledged`; более новый cursor не откатывается; несовместимый expected cursor возвращает typed `stale`. Эти операции не вызывают HTTP и не меняют inbox, objects, outbox, intents, receipts, pull cursor, Notes или entity heads.

Real-schema Rust focused tests добавили empty/no-progress, contiguous/gap, четыре blocking states, pull bound, advance/replay/stale CAS, invalid candidate, account/device mismatch, reopen persistence и injected rollback cases. Локально `cargo test --manifest-path frontend/src-tauri/Cargo.toml note_sync -- --nocapture`: **79 passed, 0 failed** (включая четыре ACK test functions и существующие inbox/cursor regressions); `cargo check --manifest-path frontend/src-tauri/Cargo.toml` и `git diff --check`: **passed**. Общий `cargo fmt --check` не прошёл до tests из-за уже существующих unrelated format diffs в `game.rs`, `sqlite.rs` и других Rust files; accidental whole-file formatting `note_sync.rs` был отменён без reset/clean/checkout, поэтому diff ограничен ACK substrate. Remote CI и полный CI-equivalent pass ещё **not run**.

## 52. Full Orchestration / ACK — Slice 2 device registration and cloud ACK (локально)

**Статус:** `IMPLEMENTED LOCALLY`; весь пакет остаётся `IN PROGRESS`, не `CLOSED`. Официальный прогресс остаётся **67,5%**; нового independently verified remote SHA или remote CI нет.

Добавлены `frontend/src/cloud/noteSyncDeviceAck.ts` и узкий `SQLiteNoteSyncAckRepository`: `registerOnce()` сначала удостоверяет authoritative local account/backend-user/durable device scope через read-only Rust `prepare_note_sync_ack`, затем повторяемо регистрирует тот же durable device ID через существующий `syncApi.registerDevice()`. Ответ строго проверяется (protocol v1, exact canonical device ID, safe non-negative `last_ack_cursor`); server cursor остаётся только metadata и не копируется в SQLite. `ackOnce()` получает candidate, не делает HTTP при no-progress, отправляет существующий monotonic `syncApi.ack()` и только после успешного 204 вызывает conditional Rust commit. Timeout/lost response не вызывает local commit; post-204 local failure остаётся безопасно повторяемым. Stale auth/logout до commit блокирует SQLite write. Новые Tauri commands принимают только typed scope/cursors, а Rust повторно проверяет durable binding и prefix.

Focused TypeScript tests: `noteSyncDeviceAck.spec.ts` и `noteSyncAckRepository.spec.ts` — **7 passed, 0 failed**; TypeScript typecheck — **passed**. Они покрывают registration/repeat/malformed/timeout/server-higher-ACK, no-progress, HTTP-before-local-commit, replay/stale, lost ACK response, local failure after 204 and stale auth. Rust `note_sync` — **79 passed, 0 failed**; cargo check и diff check — **passed**. Existing `python3 -m pytest -q tests/test_cloud_sync.py` был запущен для backend monotonic ACK coverage: **7 skipped, 0 failed** в текущей local configuration; backend не менялся. Frontend curated list в `cloud-backend-tests.yml` теперь включает оба Slice 2 specs; path filters уже охватывают `frontend/src/**`, а SQLite workflow уже охватывает `note_sync.rs`/`lib.rs`. Remote CI, Docker/PostgreSQL и full CI-equivalent pass — **not run**.

## 53. Full Orchestration / ACK — Slice 3 bounded Notes orchestrator (локально)

**Статус:** `IMPLEMENTED LOCALLY`; весь пакет остаётся `IN PROGRESS`, не `CLOSED`. Официальный прогресс остаётся **67,5%**; нового independently verified remote SHA или remote CI нет.

Добавлен `frontend/src/cloud/noteSyncOrchestrator.ts`: внутренний `NoteSyncOrchestrator.runOnce()` объединяет existing device registration, sealing, upload, durable pull/inbox commit, protected decrypt/atomic apply и Slice 2 ACK adapter. Он не шифрует, не делает SQL и не реализует HTTP сам. Один запуск ограничен sealing batch, максимум четырьмя pull pages и максимум четырьмя apply passes (настраиваемые safe bounds); no-progress и budgets завершают цикл. Static single-flight key включает account/device/auth epoch/key-context identity, поэтому concurrent calls для того же current context объединяются, а после logout/account switch/key change старый Promise не переиспользуется. Ошибки registration останавливают dependent stages; upload/pull errors сохраняются в structured result и не уничтожают независимую durable inbound work. ACK вызывается только через adapter после apply passes; adapter/Rust самостоятельно сохраняют invariant applied-prefix и remote-then-local cursor commit. Результат не возвращает plaintext или keys и включает stages, bounded work, blocked inbox classifications, errors и remaining-work hint.

`noteSyncOrchestrator.spec.ts` добавлен в фактически выполняемый curated Vitest list. Focused orchestration + Slice 2 regressions: **13 passed, 0 failed**; TypeScript typecheck и `git diff --check`: **passed**. Это mock-boundary coverage, не browser→Tauri→SQLite или two-device E2E proof. Rust/backend code в Slice 3 не менялся: Rust suites, backend ACK suite, Docker/PostgreSQL и full CI-equivalent pass — **not run** в этом slice. Historical Slice 2 backend ACK check остаётся **7 skipped, 0 failed** и обязателен для финальной integration acceptance. Subsequent Slice 4A audit confirmed no production authenticated desktop composition root; Slice 4B1 then added only the durable identity prerequisite below.

## 54. Full Orchestration / ACK — Slice 4B1 durable cloud identity bootstrap (локально)

**Статус:** `IMPLEMENTED LOCALLY`; весь пакет Full Orchestration, ACK, Two-Device Acceptance остаётся `IN PROGRESS`, не `CLOSED`. Официальный прогресс остаётся **67,5%**; нового independently verified remote SHA или remote CI нет.

Read-only Slice 4A установил, что `platform/runtime.ts` запускает лишь независимый legacy document sync, а production normal-user session/key composition root и provisioning local account/device identity отсутствуют. В `frontend/src-tauri/src/account_binding.rs` добавлены internal-only Rust/SQLite `provision_cloud_identity()` и `read_cloud_identity()`, без Tauri IPC, frontend API, runtime trigger или UI. После явного authenticated flow с canonical backend user UUID provisioning в одной `BEGIN IMMEDIATE` transaction либо возвращает уже immutable bound local account/device identity, либо CSPRNG генерирует отдельные canonical UUID v4 для нового opaque `local_account_id` и durable `device_id`, вставляет `cloud_sync_state` с нулевыми cursors и затем immutable `cloud_account_bindings` row. Local account ID не равен и не подменяет backend user ID. Existing unbound legacy state никогда не присоединяется автоматически; incomplete/corrupt bound state fail-closed без repair/rebind. Existing `ensure_cloud_account_binding()` не изменён и по-прежнему отвергает отсутствующий local state.

Focused real-SQLite `cargo test --manifest-path frontend/src-tauri/Cargo.toml account_binding -- --nocapture`: **10 passed, 0 failed** (6 new cases: atomic first creation/non-Notes invariance, replay/read/restart, two-connection concurrency, unbound legacy non-adoption and rebind rejection, corrupt bound state, injected binding rollback; 3 historical account-binding cases and 1 historical SQLite migration regression also match the filter). `cargo check` и `git diff --check`: **passed**; existing unrelated Rust warnings remain unchanged. The SQLite workflow already includes `frontend/src-tauri/src/account_binding.rs` in path filters and runs `cargo test ... account_binding`; no workflow change is needed. TypeScript, Docker/PostgreSQL, two-device acceptance, full CI-equivalent pass and remote CI are **not run**.

Следующий минимальный шаг выполнен в Slice 4B2 ниже. Не подключать `platform/runtime.ts` legacy timer, не добавлять UI/scheduler/C16 и не начинать C17 без отдельного задания.

## 55. Full Orchestration / ACK — Slice 4B2 headless cloud session and Notes sync runtime (локально)

**Статус:** `IMPLEMENTED LOCALLY`; весь пакет Full Orchestration, ACK, Two-Device Acceptance остаётся `IN PROGRESS`, не `CLOSED`. Официальный прогресс остаётся **67,5%**; нового independently verified remote SHA или remote CI нет.

Добавлены узкие typed Tauri commands `provision_cloud_identity` и `read_cloud_identity` в `frontend/src-tauri/src/lib.rs`; они принимают только canonical backend user ID and delegate to Slice 4B1 Rust validation/transaction, without SQL, database path or caller-selected device ID. Rust validates the identity and immutable binding, but does not and cannot independently authenticate a server session; the TypeScript caller must obtain the supplied canonical user ID from current `NormalUserAuthRuntime.requireContext()` and re-check auth epoch after IPC.

Добавлены `frontend/src/infrastructure/sqlite/cloudIdentityRepository.ts` и `frontend/src/cloud/noteSyncRuntime.ts`. `NoteSyncRuntime` creates exactly one local composition of existing `NormalUserAuthRuntime`, authoritative binding, `RuntimeKeyContext`, Note repositories/adapters and `NoteSyncOrchestrator`. Its explicit headless API is `login`, `unlock`, `retry`, `lock`, `logout`, `dispose`. Login provisions/replays identity only for the current auth context; unlock separately accepts the E2EE passphrase, requires the existing wrapped AMK, verifies current auth/binding/lease and starts one bounded orchestrator cycle. Retry needs a current lease. It holds no password/passphrase/AMK durable state. A runtime-level flight joins concurrent retry triggers, while the established orchestrator keeps its own account/device/auth/key-context single-flight. Auth invalidation invokes the existing key-context draining lock; stale contexts cannot start subsequent stages. Correct durable identity/outbox/inbox are never deleted on logout or disposal. Local-only projects remain outside the sync path because the runtime neither enables project binding nor creates intents.

Focused TypeScript mock-boundary tests: `noteSyncRuntime.spec.ts` (10) + `cloudIdentityRepository.spec.ts` (2), plus affected auth/key/orchestrator regressions: **34 passed, 0 failed**. Coverage includes pre-login/pre-unlock no cycle, canonical-user provisioning/replay, successful unlock one bounded run, concurrent retry joining, bad/unprovisioned key, missing/malformed identity, stale provisioning, key lock, 401 invalidation and disposal. This is not a desktop E2E proof. Focused real-SQLite `cargo test --manifest-path frontend/src-tauri/Cargo.toml account_binding -- --nocapture`: **10 passed, 0 failed** (including Slice 4B1 replay/restart/concurrency/corruption/rollback cases); `npm run typecheck`, `cargo check` and `git diff --check`: **passed**. Existing unrelated Rust warnings remain. Curated `cloud-backend-tests.yml` now lists both new specs; its `frontend/src/**` filter covers runtime/IPC TS, and SQLite workflow already covers `account_binding.rs`/`lib.rs` and `cargo test ... account_binding`. Docker/PostgreSQL, backend ACK suite (historical **7 skipped**), two-device harness, full CI-equivalent pass and remote CI are **not run**.

Remaining production boundary: no call site creates `NoteSyncRuntime`; it is not auto-started for desktop users. A future explicitly scoped C16 UI/startup integration may own login/unlock forms, user-facing retry/status/settings and manual controls, but must not reuse the legacy document interval. Before C15 package acceptance, run the planned real SQLite/Tauri integration and two-device matrix, including restart, lost responses, stale lifecycle and backend ACK coverage.

## 56. Full Orchestration / ACK — Slice 5A real SQLite lifecycle integration and two-device preparation (локально)

**Статус:** `IMPLEMENTED LOCALLY`; весь пакет Full Orchestration, ACK, Two-Device Acceptance остаётся `IN PROGRESS`, не `CLOSED`. Официальный прогресс остаётся **67,5%**; нового independently verified remote SHA или remote CI нет.

Current environment has no browser→Tauri test runner, so this slice does **not** claim desktop E2E. `frontend/src-tauri/src/lib.rs` now factors the existing identity command bodies through connection helpers with the same `require_sqlite_notes_owner` guard and typed command DTO. New real file-backed SQLite tests call those native helpers after `initialize_fresh_desktop_database`, not mocks: provisioning/replay across reopen preserves immutable binding, local/device ID, nonzero pull/ACK cursors, durable outbox and inbox rows; a mismatched user binding is rejected; and non-native Notes ownership makes provisioning fail without creating state. A second fixture creates two independent fresh SQLite files for the same canonical cloud user and proves distinct local account/device IDs. Temporary directories are removed after each test. These are real SQLite/native command-body proofs, not renderer IPC or encrypted cloud transport E2E.

Focused Rust lifecycle tests: **3 passed, 0 failed** (`sqlite_file_backed_identity_command_helpers_preserve_sync_state_across_restart`, ownership guard, and two-file device fixture). Focused TypeScript identity IPC DTO + headless runtime boundary specs: **12 passed, 0 failed**. `cargo check` and `git diff --check`: **passed**; existing unrelated Rust warnings remain. New test names start with `sqlite_`, so the existing `sqlite-sync-tests.yml` command `cargo test ... sqlite` executes them; its `lib.rs` path filter already covers the modified native command file. Existing cloud frontend workflow continues to run the two TS specs; no new workflow path filter is needed. TypeScript typecheck was not rerun in this Rust-only slice (last Slice 4B2 typecheck passed).

**Backend ACK diagnosis:** `tests/test_cloud_sync.py` contains 7 tests and all depend on `cloud_client` → `migrated_database`; the fixture deliberately calls `pytest.skip('requires dedicated real PostgreSQL database in NFPROGRESS_TEST_DATABASE_URL')` if that variable is absent. This exactly explains the historical **7 skipped, 0 failed**. Docker CLI exists locally but its daemon is unavailable, so no local PostgreSQL was started. Slice 5B prerequisite is a disposable real PostgreSQL database and `NFPROGRESS_TEST_DATABASE_URL`, then run `NFPROGRESS_ENV=test NFPROGRESS_TEST_DATABASE_URL=<dedicated-url> python -m pytest -q tests/test_cloud_sync.py`; the CI workflow shows the matching PostgreSQL service/database setup. These tests remain **not run** in Slice 5A, not passed.

Slice 5B minimum acceptance environment: two isolated file-backed desktop SQLite roots provisioned for one backend user with their different durable device IDs; disposable PostgreSQL backend with real encrypted API and two authenticated sessions; client-side test AMK/wrapped key records only (never server plaintext/AMK). Matrix must cover encrypted create/update/delete, duplicate delivery/self-echo, independent pull/ACK cursors, lost upload/ACK outcomes, conflict/orphan no-silent-overwrite, restart of both roots and lifecycle stale/lock boundaries. Full matrix, Docker/PostgreSQL, remote CI and C16 UI are deferred.

## 57. Full Orchestration / ACK — Slice 5B encrypted two-device acceptance (локально)

**Статус:** `IMPLEMENTED AND VERIFIED LOCALLY AT SEPARATE REAL BOUNDARIES`; весь пакет Full Orchestration, ACK, Two-Device Acceptance остаётся `IN PROGRESS`, не `CLOSED`. Официальный прогресс остаётся **67,5%**; нового independently verified remote SHA или remote CI нет.

После первоначального `docker info` с ошибкой Docker API Docker Desktop был запущен через `open -a Docker`; повторная проверка подтвердила daemon/server **28.1.1**. Для тестов создан только disposable `postgres:16` container `nfprogress-c15-5b-postgres` на host port 55432, без named volume, с отдельной базой `nfprogress_c15_5b_test`. По завершении контейнер остановлен и, благодаря `--rm`, удалён; другие containers/databases/volumes не изменялись.

Добавлен `tests/test_cloud_two_device_acceptance.py`, использующий настоящий FastAPI TestClient, production encrypted sync routes и disposable PostgreSQL. Один cloud user регистрирует два разных device ID; тест проводит opaque encrypted create A→B, update B→A и tombstone A→B, проверяет exact immutable upload replay после потерянного ответа, repeated monotonic ACK после потерянного ответа, последовательности pull, разные per-device ACK cursors, отсутствие plaintext-маркера в server ciphertext и три разных nonce. Все исторические семь `tests/test_cloud_sync.py` теперь фактически выполнены, а не skipped. Production backend code и frozen protocol не менялись.

Добавлен `frontend/src/cloud/noteSyncTwoDeviceCryptoAcceptance.spec.ts`: production `sealNoteSyncEvent()`/`openNoteSyncEvent()` с одним generated AMK проверяют create/update/delete chain, parent/revision metadata, peer decrypt, отсутствие plaintext в wire ciphertext, fresh nonce, byte-identical retry envelope и fail-closed other-user context. Это реальная TypeScript crypto/codec boundary, но не сетевой mock и не замена PostgreSQL test. Существующие Rust real-SQLite tests отдельно доказывают file-backed two-device identity/restart, durable inbox/outbox/cursors, atomic apply, receipt-proven self-echo, conflict/orphan/rejected blocking и ACK CAS/replay.

В текущем проекте нет browser→Tauri automation или Node-callable native bridge, поэтому Slice 5B честно не заявляет один monolithic desktop E2E. Проверены три реальные границы: (1) PostgreSQL/FastAPI encrypted transport; (2) production TypeScript encryption/decryption и protected adapter/runtime regressions; (3) Rust command bodies и настоящие file-backed SQLite. Renderer invoke serialization между TypeScript repository DTO и registered Tauri commands остаётся покрыт typed/mock boundary tests, а не live desktop process.

**Матрица A–G:** A initial sync — `PARTIAL` (real backend transport + real TS crypto + real native apply, раздельно); B update/delete — `PARTIAL` по тем же границам; C duplicate delivery/self-echo — `PARTIAL` (real backend immutable duplicate и Rust receipt-evidence regression); D independent pull/ACK cursors — `PARTIAL` (real PostgreSQL per-device ACK и real SQLite contiguous-prefix/CAS отдельно); E lost upload/ACK responses — `PARTIAL` (real monotonic backend retry плюс durable client regressions отдельно); F conflict/orphan — `PARTIAL` (real SQLite classification/no-overwrite/ACK blocking, без общего PostgreSQL runner; resolution остаётся C17); G restart/lifecycle — `PARTIAL` (real file-backed reopen и TypeScript stale-auth/key lifecycle отдельно). Непокрытая единая cross-runtime граница явно не подменяется mock E2E.

**Локальные проверки:** `tests/test_cloud_sync.py` + new acceptance — **8 passed, 0 failed, 0 skipped**; encrypted schema/sync + new acceptance — **22 passed, 0 failed, 0 skipped**. Focused TypeScript selection — **85 passed, 0 failed** в 15 files, включая 2 new crypto-acceptance cases. Rust `note_sync` — **79 passed, 0 failed**; Rust `sqlite` — **24 passed, 0 failed**. TypeScript typecheck, cargo check, YAML parse обоих sync workflows и `git diff --check` — **passed**; прежние unrelated Rust warnings сохранены. Full package CI-equivalent pass, frontend production build и remote CI в Slice 5B не запускались.

`cloud-backend-tests.yml` переиспользует существующий PostgreSQL 16 service/database и теперь запускает mandatory ACK + two-device backend acceptance отдельным шагом с `-rs`; шаг явно падает при любом skipped test. Повторный запуск `test_cloud_sync.py` из broad suite удалён. Новый TypeScript spec и Slices 2–4 specs включены в curated Vitest command. Existing filters `tests/test_cloud_*.py` и `frontend/src/**` охватывают новые tests; SQLite workflow по-прежнему охватывает изменённые Rust files и реально запускает `sqlite`, `note_sync`, `account_binding` filters.

Следующее действие не является новым slice implementation: выполнить согласованный общий локальный CI-equivalent pass накопленного C15 package, проверить полный diff/отсутствие user `.pyc` в commit scope, затем только по решению пользователя создать единый commit/push и независимо проверить на новом SHA PostgreSQL cloud backend, frontend curated tests и Rust/Python SQLite jobs. До этого пакет не `CLOSED`, прогресс не меняется. C16 сохраняет production login/unlock UI, startup/manual trigger/status/settings; C17 сохраняет conflict resolution.

## 58. C15 final local acceptance — headless cross-runtime proof и CI-equivalent

**Статус:** `LOCAL ACCEPTANCE COMPLETE / REMOTE CI PENDING`; пакет Full Orchestration, ACK, Two-Device Acceptance остаётся `IN PROGRESS`, не `CLOSED`. Официальный прогресс остаётся **67,5%**. Этот checkpoint намеренно не содержит SHA создаваемого после него локального commit.

Добавлен `tests/test_cloud_c15_headless_cross_runtime.py`, который в одном pytest scenario связывает два независимых file-backed SQLite root, две provisioned durable device identities одного real PostgreSQL user, один настоящий client AMK, production TypeScript `sealNoteSyncEvent`/`openNoteSyncEvent`, authenticated FastAPI encrypted push/pull, Rust durable inbox commit, privileged transactional remote apply, SQLite Note/head/inbox verification, Rust contiguous ACK candidate, backend monotonic ACK и conditional local ACK CAS. После завершения проверяются Note payload непосредственно в базе B и равенство local/server ACK=1. Plaintext/AMK отсутствуют в backend request; server возвращает byte-identical encrypted envelope.

Cross-runtime glue ограничен test-only кодом: `noteSyncHeadlessCryptoBridge.spec.ts` вызывает production crypto/codec functions, а `c15_headless_test_bridge.rs` подключён только под `#[cfg(test)]`, не регистрирует Tauri command и не входит в production build. Native bridge не пишет Note или cursors прямым SQL: project/project-binding fixture создаёт только prerequisite scope, затем encrypted inbox, protected apply и ACK выполняются production Rust operations. Полноценный graphical renderer→live Tauri invoke остаётся неохваченным и относится к будущему desktop/C16 integration, но headless TypeScript→backend→native route теперь реально исполнен.

Первый сквозной прогон обнаружил конкретный production defect: FastAPI transport возвращает семантически эквивалентный timestamp без `.000000`, тогда как Rust protected apply сравнивал строку буквально и отвергал событие как `metadata_mismatch`. `note_sync.rs` теперь сравнивает уже валидированные transport/plaintext timestamps по UTC instant и microseconds, сохраняя frozen accepted timestamp grammar; добавлен Rust regression `remote_apply_accepts_equivalent_transport_timestamp_precision`. После минимального исправления end-to-end headless proof — **1 passed, 0 failed, 0 skipped**.

**Полный локальный CI-equivalent pass:** mandatory PostgreSQL ACK/two-device/headless acceptance — **9 passed, 0 failed, 0 skipped**; полный cloud workflow backend selection — **151 passed, 0 failed**; frontend curated selection под закреплённым workflow Node **20.19.0** — **219 passed, 0 failed** в 39 files; TypeScript typecheck и production build — **passed** с прежними size/dynamic-import warnings; Python SQLite workflow selection — **75 passed, 0 failed**; Rust `note_sync` — **80 passed**, `sqlite` — **24 passed**, `account_binding` — **10 passed**; cargo check, оба workflow YAML parse и `git diff --check` — **passed**. Локальный system Node 26 воспроизвёл известный unrelated broken experimental `localStorage` failure в `admin.spec.ts` (218 passed, 1 failed); exact workflow runtime Node 20.19.0 затем дал обязательный clean result 219/219 без code workaround.

Disposable Docker `postgres:16` container `nfprogress-c15-final-postgres`, host port 55433 и database `nfprogress_c15_final_test` использовались только для этого pass, затем container был остановлен и автоматически удалён; named volumes и чужие resources не затрагивались. Локальный Rust pass выполнен на macOS и не заменяет required Windows Rust SQLite job.

`cloud-backend-tests.yml` теперь устанавливает pinned Node, Rust и минимальные Linux Tauri compile dependencies в existing PostgreSQL job, выполняет обязательный headless proof вместе с ACK/two-device tests и падает при любом unexpected skipped. Path filters охватывают `tests/test_cloud_*.py`, `frontend/src/**`, test-only Rust bridge, `note_sync.rs`, `lib.rs` и workflow. Curated frontend command содержит оба Slice 5B crypto specs и headless crypto bridge. SQLite workflow без изменения запускает production Rust `sqlite`, `note_sync`, `account_binding` filters на Windows.

Следующие gates: единый локальный implementation commit без пользовательских `.pyc`; затем только пользовательский push; independently verify новый remote SHA, PostgreSQL cloud backend/headless no-skip execution, frontend curated/build и Windows/Python SQLite jobs. Только после этой remote acceptance внешний владелец checkpoint может объявить пакет `CLOSED` и изменить официальный прогресс на 70,0%. C16 остаются production login/unlock UI, live desktop composition/startup/manual trigger/status/settings; C17 — conflict resolution.

## 59. C15 Windows CI repair — SQLite file locks and fail-fast (локально)

**Статус:** `WINDOWS CI REPAIR / REMOTE RECHECK PENDING`. Пакет Full Orchestration, ACK, Two-Device Acceptance остаётся `IN PROGRESS`, не `CLOSED`; официальный прогресс остаётся **67,5%**.

Implementation commit `5b379d32e84da99f13e7f4aee0e56d0267fac78d` опубликован на `origin/6.0`. Independently reported remote результаты для этого SHA: Cloud backend run `35906517726` — **SUCCESS** (mandatory PostgreSQL/headless selection **9/9**, broad backend **151/151**, frontend curated **219/219**). SQLite run `35906517350` был визуально marked SUCCESS, но Windows Rust step фактически содержал три failure: `sqlite` **24 passed**; `note_sync` **79 passed, 1 failed**; `account_binding` **8 passed, 2 failed**. Все три упали с Windows `Os { code: 32, message: "The process cannot access the file because it is being used by another process." }`: `sealed_outbox_enforces_dependencies_objects_and_batch_limits_after_restart`, `provision_replays_and_read_returns_the_same_durable_identity_after_restart` и `concurrent_provisioning_returns_one_identity`.

Причина подтверждена в test lifecycle, а не в production sync: тесты удаляли SQLite file/directory, пока `rusqlite::Connection` (`reopened` или `connection`) всё ещё был live. В `note_sync.rs` и `account_binding.rs` добавлены минимальные explicit `drop(...)` непосредственно перед cleanup; assertions и file-backed real-schema tests сохранены. Не добавлялись sleep, ignored removal errors, mocks или production/migration/crypto changes.

Дополнительно Windows job в `sqlite-sync-tests.yml` раньше запускал три native `cargo test` и `cargo check` в одном PowerShell step без `$LASTEXITCODE` guard; успешный final `cargo check` мог скрыть test failure. Он разделён на четыре независимых Actions steps: `sqlite`, `note_sync`, `account_binding` и `cargo check`. Каждый native command теперь является единственной командой своего step, поэтому non-zero exit code немедленно завершает job failed; Rust/MSVC target, path filters и все три required filters сохранены.

Локальная macOS verification correction: три exact failed cases — **3 passed, 0 failed**; Rust `note_sync` filter — **80 passed, 0 failed**; `account_binding` — **10 passed, 0 failed**; `sqlite` — **24 passed, 0 failed**; `cargo check` — **passed** с прежними unrelated warnings. YAML обоих sync workflows и `git diff --check` — **passed**. Это не доказывает Windows behaviour: после user push требуется independently inspect новый SHA в обоих workflows, включая отдельные Windows `sqlite`, `note_sync`, `account_binding` и `cargo check` steps. Не записывать новый remote SHA/CI SUCCESS до этой проверки.

## 60. C15 remote acceptance closure

**Статус:** **C15 Full Orchestration, ACK, Two-Device Acceptance — CLOSED**. Приняты все **2,5** пункта пакета; официальный прогресс WORTA 6.0 — **70,0%**. Это закрытие основано на independently verified published commits и remote CI, а не на одном локальном отчёте.

**Публикации и remote acceptance:** implementation commit `5b379d32e84da99f13e7f4aee0e56d0267fac78d` был опубликован на `origin/6.0`; затем published correction commit `25476c611b91e26e5b94798dcf33a55924a45e08` исправил Windows-only test cleanup и workflow fail-fast behaviour. Последний SHA independently confirmed на `origin/6.0`.

- [Cloud backend tests — run 35908520926](https://github.com/nevskyforever/nfprogress/actions/runs/35908520926) на correction SHA — **SUCCESS**: mandatory PostgreSQL/headless acceptance **9 passed, 0 skipped**; broad backend **151 passed**; frontend curated **219 passed** в **39** files; TypeScript typecheck и production build — **SUCCESS**.
- [SQLite sync substrate tests — run 35908521004](https://github.com/nevskyforever/nfprogress/actions/runs/35908521004) на correction SHA — **SUCCESS**: Python SQLite **75 passed**; Windows Rust `sqlite` **24 passed**, `note_sync` **80 passed**, `account_binding` **10 passed**; отдельный Windows `cargo check` — **SUCCESS**.

**Предыдущее false-green объяснено и устранено:** на implementation SHA Windows Rust job визуально завершался SUCCESS, но содержал три failures с `Os { code: 32 }`, потому что tests удаляли file-backed SQLite path при ещё живом соединении; отдельный final `cargo check` в том же PowerShell step скрывал non-zero exit предшествующих native `cargo test`. Correction явно закрывает три соединения перед cleanup и разделяет `sqlite`, `note_sync`, `account_binding` и `cargo check` на самостоятельные fail-fast workflow steps. Новый remote run подтвердил все четыре steps; failures больше не скрыты.

**Доказанная и недоказанная граница:** C15 доказал настоящий headless маршрут TypeScript → FastAPI/PostgreSQL → Rust/SQLite → ACK, включая two-device acceptance и durable/restart invariants. Он **не** является полноценным graphical renderer→live Tauri E2E. Это ограничение сохраняется для планирования C16 и не должно записываться как уже проверенная часть Desktop Sync.

**Следующий этап:** C16 Desktop Sync (3,0) ещё не начат. Его scope: production normal-user login/unlock UI, подключение существующего headless Notes Sync Runtime к desktop lifecycle, user triggers, sync state и предусмотренные roadmap desktop controls — без смешения с legacy document interval. C17 сохраняет полноценное conflict resolution.

## 61. C16 Pass 1 — secure E2EE account provisioning (локально)

**Статус:** `IMPLEMENTED LOCALLY / REMOTE CI PENDING`. C16 остаётся `IN PROGRESS`; официальный прогресс WORTA 6.0 остаётся **70,0%**. Этот pass не создаёт desktop UI, Pinia session owner, scheduler, Tauri key storage, cloud-project switch или initial upload.

Добавлен authenticated create-only `POST /api/v1/account/crypto`. Сервер берёт user ID только из normal-user auth, принимает строго один C11 password wrapper и один Recovery-Key wrapper, отклоняет неизвестные поля, noncanonical Base64URL, неверные длины и неподдерживаемые v1/Argon2id13 parameters. Новая запись `UserCrypto` вставляется atomically без миграции: существующая PostgreSQL table уже содержит все required columns and constraints. Exact replay возвращает уже сохранённый record; different wrapper set возвращает only typed `409 crypto_already_provisioned`, without crypto material or overwrite. Primary-key `user_id` plus commit/`IntegrityError` recovery is the authority for concurrent creates; preflight read is only a fast path. Existing legacy record without Recovery wrapper is immutable and conflicts rather than being silently repaired. `GET /account/crypto` remains read-only and `Cache-Control: private, no-store` is preserved for both routes.

Добавлены typed frontend POST transport и `PendingAccountCryptoProvisioning`. После authenticated GET it refuses to generate a replacement AMK for an already provisioned account. For a new account it generates one client-side AMK, one Recovery Key, and the two production wrappers; AMK is cleared after wrapping. A future UI receives only a caller-owned transient Recovery-Key display copy, must call `confirmRecoveryKeySaved()`, and only then may submit wrapper records. No password, plaintext AMK, KEK, or Recovery Key enters HTTP, Pinia/localStorage/cookies/files/logging/Tauri IPC. On network-unknown POST outcome the same retained immutable wrappers are reconciled through authenticated GET; exact persisted match succeeds, mismatch fails closed, and absent state permits only exact replay—not new key generation. Controlled key/wrapper byte buffers are cleared on success/dispose; JavaScript string/copy erasure is intentionally not claimed. Recovery-Key-based password rewrap remains a separate future contract.

Focused local verification: real disposable PostgreSQL 16 FastAPI `tests/test_cloud_auth.py` — **20 passed, 0 failed, 0 skipped** (one existing TestClient deprecation warning), including authenticated create, user isolation, required recovery wrapper, malformed/noncanonical rejection, exact/different replay, PostgreSQL concurrent same/different creates, no plaintext marker and unchanged GET behaviour. New TypeScript transport/provisioning specs — **8 passed, 0 failed**; they use production generation/wrapping/unwrapping, confirmation gate, lost-response reconciliation/exact replay, stale auth and buffer cleanup. `npm run typecheck`, `python3 -m py_compile backend/app/cloud/router.py backend/app/cloud/schemas.py`, cloud workflow YAML parse and `git diff --check` — **passed**. Full curated frontend command, production build, Windows Rust, graphical Tauri E2E and remote CI are **not run**. The disposable container `nfprogress-c16-provisioning-postgres` used host port 55434 without a volume and is removed after this pass.

`cloud-backend-tests.yml` already runs `tests/test_cloud_auth.py` against PostgreSQL; its actual curated Vitest command now explicitly includes `src/api/accountCrypto.spec.ts` and `src/cloud/accountCryptoProvisioning.spec.ts`. Existing path filters cover both backend and frontend changes. Before C16 can close, remaining work is production desktop session/UI composition, explicit safe cloud-project bootstrap/initial upload contract, and live renderer→Tauri acceptance; C17 retains conflict resolution.

## 62. C16 Pass 2 — desktop cloud session and E2EE onboarding UI (локально)

**Статус:** `IMPLEMENTED LOCALLY / REMOTE CI PENDING`. C16 остаётся `IN PROGRESS`; официальный прогресс WORTA 6.0 остаётся **70,0%**. Этот pass не включает cloud-project enable/binding, initial upload, scheduler, Recovery-Key rewrap или conflict resolution.

В desktop-only Pinia owner `cloudSession` появился единственный `NoteSyncRuntime`; instance создаётся only after Tauri platform initialization, never on web/mobile and never from the admin route. Startup does not authenticate or sync: its safe initial state is `logged_out`. Runtime and pending provisioning context are lexical-only, not returned by Pinia and never persisted; visible state contains only redacted username/status, work/blocked hints and generic error text. Logout, 401/stale auth, lock and app unmount dispose pending byte buffers and invalidate the visible session; `NoteSyncRuntime` supplies narrow crypto-record/provision/reconcile methods without exposing its auth context or tokens.

`SettingsPage` now contains a desktop Notes-cloud card, separate from `background_synch` and legacy `run_all_document_sync`. It handles normal-user login, GET-based existing-AMK detection, separate encryption-password setup, client-only Recovery Key display, explicit saved-key confirmation before POST, unlock of an existing AMK, key lock/logout and manual bounded-cycle retry. The Recovery Key stays only in component-local caller-owned bytes; closing the onboarding clears it and disposes Pass 1 context. A lost POST response retains the same immutable wrapper set for retry/reconciliation, never creates another AMK. UI explicitly says that Recovery-Key rewrap is not yet available.

Status language distinguishes logged out, provisioning, key locked, syncing, completed bounded cycle, retryable error, blocked events and remaining work. It never says all data is synchronized after a cycle; with no approved project bootstrap it says that no cloud projects are connected and local projects are not uploaded automatically. Blocked events are displayed without automatic resolution. Existing `background_synch` remains legacy document-source behaviour.

Focused local frontend verification: `App`, `SettingsPage`, `cloudSession`, Settings-card, runtime, Pass 1 transport/provisioning specs — **37 passed, 0 failed** across 7 files; TypeScript typecheck and `git diff --check` — **passed**. The Vitest renderer run emitted only existing Ionic sourcemap and Node-localStorage experimental warnings. Localization catalog/frontend artifacts were regenerated from the shared extractor (110 previously missing source keys, including this UI); deterministic export check passes. Production backend/Rust suites, full curated/frontend build, Docker/PostgreSQL, Windows Rust and graphical live Tauri acceptance were not run in this pass. `cloud-backend-tests.yml` curated frontend command now explicitly includes `cloudSession.spec.ts` and `CloudSyncSettingsCard.spec.ts`; existing `frontend/src/**` filters cover the new files.

Remaining C16 gates: a separately approved safe initial cloud-project bootstrap (registration, durable binding, initial upload/pull and partial-failure rules), Recovery-Key-based rewrap contract, live renderer→Tauri desktop acceptance, and then full independent remote CI. C17 remains conflict resolution.

## 63. C16 Pass 3B — safe project bootstrap substrate + Web First roadmap (локально)

**Статус:** `IMPLEMENTED LOCALLY / REMOTE CI PENDING`. C16 остаётся `IN PROGRESS`; официальный прогресс WORTA 6.0 остаётся **70,0%**. `cloudProjectCapabilities.encryptedInitialUpload` остаётся `false`; UI выбора/включения проекта, scheduler и legacy document sync не подключены.

**Web First утверждён пользователем.** После C18 порядок исполнения теперь C21 Web → C22 Production Hardening → C23 Failure/Disaster Tests → PF 6.0 / Release Candidate. Первый публичный релиз определён как Desktop + Web на отметке 94,0% полной roadmap. C19 Android Local SQLite и C20 Android Sync не отменены и выполняются после первого публичного релиза, доводя roadmap до 97,0% и 100,0%. Номера, фиксированные веса и WORTA ROADMAP SCORING v1.0 не изменены.

**Backend control plane:** Alembic `c16_project_bootstrap` расширяет существующий `cloud_projects` минимальными lineage/state fields и PostgreSQL constraints. Authenticated bootstrap API предоставляет account-wide registry list, create-only initializing registration и immutable completion. Canonical `bootstrap_id` привязан к authenticated user, project и зарегистрированному origin device; exact replay идемпотентен, другая lineage даёт typed conflict, legacy reservation и remote history без registry fail closed. Пока project `initializing`, новые events принимает только origin device, но exact immutable replay ранее принятого event сохраняется. Completion становится `active` только после проверки фактически принятых origin-device events; bootstrap-managed project нельзя удалить legacy endpoint.

**SQLite/native substrate:** schema 16 добавляет `cloud_sync_project_bootstraps` с durable token, account/device/mode, фазами `prepared/registered/captured/completing/ready/paused/blocked`, initial cohort count/ordinal high-water, remote high-water/completion metadata и blocked reason. Все production operations проверяют account/device/token lineage. `BEGIN IMMEDIATE` атомарно создаёт binding и initial unsealed intents для всех eligible existing Notes либо откатывает всё. Повтор после restart возвращает тот же token/event IDs; receipt proof initial cohort отделён от одного HTTP response. Изменения во время bootstrap coalesce до sealing либо становятся ordered child events после sealed head. Unsupported stage/mind-map/plain Note блокирует весь project до server registration и повторно перед capture. Cloud-bound project deletion fail closed; pause сохраняет Notes, binding и queued work. Explicit second-device import создаёт минимальный local shell только для подтверждённой active lineage и отказывает при любом same-ID/name collision без доказательства происхождения.

**Coordinator/runtime gate:** `CloudProjectBootstrapCoordinator` выполняет device registration → server initializing registration → atomic capture → existing C15 seal/upload → durable cohort proof → immutable server completion → account-wide registry reconciliation → existing pull/protected apply/ACK → local `ready`. Все active remote projects аккаунта должны иметь matching local lineage; legacy, missing, initializing, paused, blocked или conflicting project запрещает обычный account-wide cycle. `NoteSyncRuntime.unlock()` больше не запускает upload/pull/ACK: он только unlock + reconciliation. `retry()` допускает обычный cycle лишь через gate. Pass 2 UI поэтому честно показывает blocked/not-connected состояние до отдельного Pass 3C, а local-only projects по-прежнему не подключаются автоматически.

**Фактическая локальная проверка:** disposable PostgreSQL 16 без volume удалён после тестов. Bootstrap backend — **5 passed**; targeted cloud auth/projects/encrypted regressions — **34 passed, 11 deselected**; новый mandatory C16 headless route A capture → partial encrypted upload → restart/same IDs → completion → A protected self-echo/ACK → B explicit import/protected apply/ACK — **1 passed**, без skips. Python SQLite migration suite — **21 passed**. Rust: bootstrap lifecycle/file-backed restart/concurrent edits/import — **7 passed**; migration 15→16 — **1 passed**; project lifecycle guards — **5 passed**; `cargo test --no-run` и `cargo check` — passed с прежними unrelated warnings. Focused frontend provisioning/bootstrap/runtime/session/UI/IPC/crypto — **36 passed** в **9 files**; TypeScript typecheck passed. Workflow YAML parse, deterministic frontend localization export and `git diff --check` passed. Исправленные в ходе focused reruns дефекты (double-encoded bootstrap JSON body, устаревший delete expectation и test-harness cursor/status assumptions) имеют зелёные regression reruns.

**CI wiring:** `cloud-backend-tests.yml` mandatory no-skip command теперь включает PostgreSQL bootstrap tests и C16 cross-runtime bootstrap proof; curated frontend command явно включает bootstrap API/coordinator/IPC specs. Path filters охватывают backend migration, native SQLite/project lifecycle и schema 16. `sqlite-sync-tests.yml` продолжает запускать Rust `note_sync`/`sqlite` filters и отдельно запускает `project_repository`, поэтому новый delete guard не может быть скрыт. Full C16 CI-equivalent pass, production frontend build, Windows Rust и graphical live Tauri renderer→IPC acceptance в этом pass **не запускались**.

**Осталось:** отдельный Pass 3C для явного выбора проекта и активации bootstrap UI/statuses без автоматической выгрузки; live desktop renderer→Tauri acceptance; затем общий C16 integration pass, commit/push пользователя и независимая проверка remote CI. Recovery-Key-based rewrap остаётся отдельным контрактом. C18 должен расширить entity coverage beyond project-level HTML Notes; C17 сохраняет conflict resolution. До этих gates C16 не `CLOSED`, официальный прогресс не меняется.

## 64. C16 Pass 3C — desktop project UI activation (локально)

**Статус:** `IMPLEMENTED LOCALLY / FINAL INTEGRATION AND REMOTE CI PENDING`. C16 остаётся `IN PROGRESS`; официальный прогресс WORTA 6.0 остаётся **70,0%**. Pass 3C не добавляет scheduler, Recovery-Key rewrap, conflict resolution, non-Note entity sync, quota enforcement или compression dependencies.

**Production desktop flow:** единственный desktop-only Pinia owner `cloudSession` по-прежнему владеет единственным `NoteSyncRuntime`. После normal-user login, E2EE onboarding/unlock и account-wide registry reconciliation Settings показывает local-only проекты, native eligibility, durable bootstrap phases, remote-only projects для explicit import, paused/blocked states и remaining work. Local project остаётся local-only до отдельного native preflight и второго явного подтверждения; unsupported Note блокирует весь project до любой server bootstrap registration. Повтор/resume вызывает тот же coordinator и сохраняет durable bootstrap token/event IDs/receipts; repeated click объединяется single-flight. Server token, AMK, KEK, passwords, Recovery Key и plaintext Notes не входят в Pinia/UI diagnostics.

Для второго устройства active remote project можно явно импортировать с обязательным локальным названием: C16 пока синхронизирует Notes, но не передаёт названия и остальные project metadata, поэтому название нужно только для создания local shell на этом устройстве и не выдаётся за синхронизированное. UI прямо указывает, что C18 добавит передачу names/metadata. Native transaction создаёт shell только после проверки remote lineage. Existing same-ID project без доказанной lineage показывает blocker; merge/overwrite не выполняются. Legacy/unknown remote и `initializing` другого устройства также fail closed. Pause/resume сохраняет Notes, binding и queued work. Logout, account switch, key lock, 401 и app disposal меняют lifecycle epoch; поздний async callback старого контекста не может переписать новый UI state.

**Truthful status/account-wide gate:** UI различает local-only/available, unsupported, registering, initial capture, uploading, server completion, pulling, initial Note completion, remaining work, paused и blocked. После bounded cycle не показывается «полностью синхронизировано»; явно указано, что C16 синхронизирует только поддерживаемые project-level HTML Notes, а не весь project. Обычный protocol-v1 pull/ACK доступен только при reconciled registry всего account; один missing/paused/blocked/unresolved project блокирует account-wide cycle и объясняется пользователю. Legacy `background_synch`/`run_all_document_sync` не подключены.

`cloudProjectCapabilities.encryptedInitialUpload` локально переключён в `true`, потому что production UI теперь использует explicit selection, double confirmation, complete native preflight, durable restart-safe bootstrap, safe resume, account-wide reconciliation, second-device explicit import и fail-closed unsupported content. Это не означает independent per-project ACK, complete entity sync или C16 closure.

**Localization:** 57 новых Pass 3C строк имеют явные overrides для `en`, `es`, `de`, `fr`, `pt_BR`; shared catalog и Vue generated locales обновлены. Прямой generator сначала не стартовал из-за отсутствующего PySide6, затем штатный network translation получил HTTP 429; системные packages не устанавливались и TLS validation не отключалась. С безопасным in-memory Qt import stub и checked-in overrides generator сообщил **0 missing** для всех пяти non-Russian languages, deterministic frontend export выполнен. Existing intentional stable system tag `#карта` остаётся одинаковым во всех locales. Полные Qt-dependent `tests/test_localization.py` не запускались из-за отсутствующего PySide6; Qt-free frontend export consistency — **2 passed**.

**Локальные проверки Pass 3C:** focused project capability/bootstrap/runtime/store/component/IPC selection — **46 passed** в 7 files; после отдельного lifecycle regression дополнительно `cloudSession.spec.ts` — **15 passed**. TypeScript typecheck — **passed**; production frontend build — **passed** с прежними chunk-size/dynamic-import warnings. Real file-backed Python SQLite migration/substrate — **21 passed**. Rust `note_sync` filter — **87 passed** (включая 7 bootstrap cases); `project_repository` — **5 passed**; `cargo check` — passed с прежними unrelated warnings. Localization consistency — **2 passed**. Workflow YAML parse и `git diff --check` — passed.

**CI wiring и недоказанная граница:** existing `cloud-backend-tests.yml` path filter `frontend/src/**` охватывает Pass 3C source/tests/locales; curated command реально содержит `cloudSession`, Settings card, project bootstrap/runtime/capability и SQLite bootstrap-repository specs, затем typecheck/build. Existing SQLite workflow охватывает migration 016, native `note_sync`, `lib.rs` и project lifecycle guards. Pass 3C не менял backend production code, поэтому PostgreSQL/headless Pass 3B matrix повторно не запускалась. Automated proof остаётся композицией Vue/Pinia focused tests, typed Tauri repository tests и real file-backed Rust/SQLite tests; полноценный live graphical renderer→Tauri process **не проверен** и остаётся обязательным отдельным финальным C16 gate. Windows Rust и remote GitHub Actions на накопленном локальном diff также не запускались.

**Roadmap requirements:** утверждённый Web First порядок сохранён без изменения номеров/весов. В разделе 43 закреплены future C18 client compression-before-E2EE contract, C22 account storage quota/admin+user UI requirements и обязательный GNU GPLv3 dependency compatibility gate. Новые compression/quota packages или production behaviour в C16 не добавлялись.

**Осталось до C16 closure:** отдельный final integration pass и live desktop smoke для реального renderer→Tauri IPC; полный согласованный C16 CI-equivalent run; user-controlled commit/push без двух `.pyc`; independent verification нового remote SHA и обоих workflows. Recovery-Key-based rewrap остаётся отдельным будущим contract; C17 сохраняет conflicts, C18 — остальные project entities и compression. До independent remote acceptance C16 не `CLOSED`, официальный прогресс остаётся **70,0%**.

## 65. C16 final local integration acceptance

**Статус:** `LOCAL INTEGRATION COMPLETE / LIVE DESKTOP ACCEPTANCE PENDING / REMOTE CI PENDING`. C16 остаётся `IN PROGRESS`, официальный прогресс остаётся **70,0%**. Не было commit, push, reset, destructive checkout, `git clean` или изменения двух пользовательских `.pyc`. `Run Tauri.sh --fresh` самостоятельно выполнил `cargo clean` только для превысивших лимит Tauri build-артефактов (21,8 GiB); source files и test/user data не удалялись.

**Объединённая production-проверка:** на новом disposable PostgreSQL 16 без volume выполнены **84 passed, без skips**: mandatory C15/C16 sync ACK, two-device и headless bootstrap route, C16 project bootstrap, cloud auth/projects/encrypted schema/sync/blob и PostgreSQL foundation. В ходе проверки исправлен только stale expectation `tests/test_cloud_postgresql_foundation.py`: Alembic head после migration должен быть `c16_project_bootstrap`, а не `c14_encrypted_cover_blobs`; отдельный migration regression — **11 passed**. Новый узкий launcher regression — **4 passed**: `backend.app.__main__` сохраняет уже заданный `NFPROGRESS_AUTH_SECRET` в фактическом runtime config, без БД или вывода секрета. Контейнер `nfprogress-c16-final-local-postgres` после проверки удалён. Уже зелёные Pass 3C frontend **46 passed**, TypeScript typecheck/build, file-backed SQLite **21 passed**, Rust note-sync **87 passed** и project-repository **5 passed** не повторялись после этого Python-only assertion fix.

**CI audit:** `cloud-backend-tests.yml` запускает mandatory PostgreSQL command с C16 cross-runtime proof и явно завершает job при `skipped`/`SKIPPED`; его path filters включают backend/migration, `frontend/src/**`, native bridge/runtime/SQLite/project files и schema. Curated frontend command содержит account provisioning, cloud session, Settings card, bootstrap/runtime/capability и SQLite repository specs, после чего выполняются typecheck/build. `sqlite-sync-tests.yml` path filters охватывают schema 16 и native files; Windows commands `sqlite`, `note_sync`, `account_binding`, `project_repository` и `cargo check` являются отдельными commands без `continue-on-error`, поэтому exit code и bootstrap guards нельзя молча скрыть. Windows matrix и GitHub runs остаются remote gates.

**Desktop/live boundary:** `./Run Tauri.sh --check` прошёл; `./Run Tauri.sh --fresh` собрал test-profile и использовал временный `NFPROGRESS_DATA_DIR`, не личную SQLite базу. В репозитории нет existing graphical automation harness. Пользователь вручную подтвердил основной live scenario: в профиле A создан и первоначально подключён тестовый проект, в отдельном профиле B он явно импортирован из облака и Notes успешно получены. После restart B повторный import не требуется: local data и durable cloud binding сохранены. Повторный ввод login/password ожидаем и не является scope C16 automatic session restore. Это **partial live desktop acceptance**, а не закрытие ручной матрицы. По-прежнему требуются safety scenarios (unsupported content/no auto-connect, logout/key lock), а также remote CI; C16 остаётся `IN PROGRESS`, официальный прогресс — **70,0%**.

**Localization и remaining gates:** все **58** Pass 3C/C16 UI override keys точно совпадают с generated `en`, `es`, `de`, `fr`, `pt_BR` catalogs, без Russian/source fallback. Qt-dependent localization suite по-прежнему не запущен: PySide6 не установлен и не добавлялся. До C16 closure остаются: remaining manual safety acceptance, user-controlled commit/push без `.pyc`, independent remote GitHub Actions (включая Windows Rust) на новом SHA. Recovery-Key rewrap, C17 conflicts и C18 remaining entities/compression остаются вне C16.

## 66. C16 remote CI correction (локально)

Remote run `36049416310` подтвердил Windows Rust и Frontend admin как **passed**, но Python SQLite упал с **74 passed, 2 failed**: stale v6 fixture не удалял child table `cloud_sync_project_bootstraps`, а recovery migration map не содержал key `16`. Исправлены только test fixtures; targeted cases — **2 passed**, затем точный Python SQLite workflow selection — **76 passed**. Production migration не менялась.

Remote PostgreSQL run `36049416227` упал в mandatory ACK/two-device step, но старый command substitution скрывал pytest output при non-zero exit. Workflow теперь исполняет те же пять mandatory modules напрямую через `2>&1 | tee` с `pipefail`, проверяет оба exit codes и затем fail-closed проверяет skipped output. Local isolated disposable PostgreSQL 16 выполнил эти пять modules: **15 passed, без skips**; remote failure локально не воспроизведён, его конкретная первоначальная причина остаётся неизвестной до нового visible GitHub log.

Correction опубликован в составе текущего remote HEAD `6c7edbfa24289fcfca39fc754eaff9a28e419dbc`; по подтверждению пользователя оба remote CI workflow прошли. C16 остаётся `IN PROGRESS`, официальный прогресс — **70,0%**: зелёный remote CI не закрывает remaining manual safety acceptance и последующий GUI blocker.

## 67. C16 Notes editor GUI blocker (локальное исправление ожидает live recheck)

После успешного live подключения проекта в профиле A и импорта Notes в профиль B пользователь обнаружил блокер: HTML был виден на карточке, но editor открывался пустым; после manual sync это воспринималось как невозможность редактирования заметок. До любых изменений согласованные SQLite snapshots обоих тестовых профилей сохранены через SQLite backup API; исходные профили, manual PostgreSQL/backend и аккаунт не очищались и не пересоздавались.

Проверка фактических A/B SQLite без вывода пользовательского текста показала: содержимое Notes сохранено и непусто, проекты и относящийся к заметке этап активны, а stored payload не содержит `read_only`. Native projection назначает `read_only` только завершённому project/stage. Следовательно, manual sync не переводил обычную Note в read-only и не терял её content; оба наблюдаемых проявления имели одну UI-причину.

Причина — lifecycle `IonModal`: watcher `open/note.id` вызывал `reset()`, а единственный `nextTick()` пытался записать HTML напрямую в `contentEditor.innerHTML` до асинхронного mount modal content. Если ref ещё отсутствовал, заполнение больше не повторялось. Editor теперь повторно гидратируется на Ionic `didPresent`; до успешной гидратации contenteditable и submit отключены, поэтому несмонтированное/пустое поле не может затереть существующую заметку. Повторное открытие снова загружает актуальный HTML.

Focused frontend regressions (`NoteEditorDialog`, `NoteCard`, `useProjectNotes`) — **10 passed**: delayed Ionic presentation, непустой HTML, safe reopen/no premature submit, editable cloud-applied Note, update/reload. TypeScript typecheck — **passed**. Узкий real-SQLite Rust regression доказывает, что локальное редактирование Note с remote entity head сохраняет новый HTML и создаёт следующий durable `upsert` с корректным parent/revision — **1 passed**. Полные PostgreSQL/CI suites не повторялись, потому что backend, protocol и sync production logic не менялись.

Исправление ещё не прошло пользовательскую live recheck на профилях A/B и не опубликовано. До подтверждения открытия/сохранения/reopen на A, отправки изменения и получения на B, а также remaining safety scenarios C16 остаётся `IN PROGRESS`; официальный прогресс — **70,0%**.

Повторная ручная проверка подтвердила двустороннее редактирование, но выявила периодическую блокировку навигации после sync и один повторный сбой открытия editor. Узкая проверка установила гонку Ionic overlay: `didDismiss` приходит после запроса закрытия асинхронно, тогда как Notes page сразу разрешала повторный click. Новое открытие могло быть закрыто запоздалым callback предыдущего modal; cached page в `IonRouterOutlet` также не имела явного editor cleanup на `ionViewWillLeave`, что позволяло backdrop/focus trap пережить переход страницы. Теперь card actions остаются заблокированными только на время реального dismiss transition, отдельный `dismissed` event завершает transition, а `onIonViewWillLeave` всегда инициирует закрытие editor. Delayed `didPresent` по-прежнему гидратирует HTML только для актуального открытого editor.

Отдельно исправлен подтверждённый session-state defect: auth failure/401 увеличивал lifecycle epoch внутри `setFailure()`, поэтому `finally` старой busy-operation уже не проходил epoch check и не сбрасывал `cloud.busy`. Auth invalidation теперь атомарно возвращает `busy=false`; это не создаёт глобального overlay, но предотвращает зависшую блокировку controls облачной карточки. `syncFlight`/`projectFlight` по-прежнему очищаются в своих `finally`; cloud sync не создаёт `IonLoading` или иной глобальный pointer-blocking слой.

После этих изменений focused Notes modal/page/card/composable и cloud-session suites — **30 passed** в 5 files; TypeScript typecheck и `git diff --check` — passed. Новая live GUI recheck ещё ожидается; C16 остаётся `IN PROGRESS`, **70,0%**.

## 68. C16 targeted GUI blocking regression (локальное исправление ожидает короткую live recheck)

**Точный результат последней пользовательской проверки:** (1) многократное быстрое открытие/закрытие существующей синхронизированной Note, включая восстановление HTML, — **PASS**; (2) после закрытия editor, перехода в Settings и возврата в Notes editor не открывался — **FAIL**; (3) переключение вкладок становилось недоступным — **FAIL**; (4) редактирование Note после sync — **NOT TESTED**; (5) повторный sync изменения — **NOT TESTED**. Пункт 1 повторять не требуется; пункты 4–5 не считаются проваленными.

Изолированное воспроизведение в настоящем Chromium с Ionic 8.8.18 подтвердило причину. Переход `/notes/:projectId` → `/settings` → тот же Notes route через sidebar возвращал cached `IonRouterOutlet` view с рассинхронизированным Vue subtree: click успешно менял `NotesPage.editingNote` с `null` на реальную Note, но фактический cached `NoteEditorDialog.open` оставался `false`, а `ion-modal` — `overlay-hidden`. Тот же дефект воспроизводился без предварительного открытия modal, что исключает stale `editingNote`, запоздалый `didDismiss`, sync и `cloudSession.busy` как root cause. После штатно завершённого dismiss активного `show-modal`/глобального backdrop не было; блокировка вкладок была проявлением stale cached view, а не неудалённого global overlay.

Минимальное исправление ключует основной `IonRouterOutlet` по `route.path` только для трёх Notes workspace routes; остальные разделы сохраняют прежнее Ionic cache behavior. Поэтому при уходе из Notes cached page и inline overlay размонтируются вместе, а query-only state внутри той же страницы remount не вызывает. Chromium regression подтвердил: на Settings остаётся **0** `note-editor-modal`; после возврата создаётся новый Notes instance, editor открывается с исходным HTML; уход при открытом editor также не оставляет overlay; быстрый close/reopen ждёт реальный `didDismiss` и снова восстанавливает HTML. Глобальное удаление Ionic overlays не использовано.

Focused frontend suites `NoteEditorDialog`, `NoteCard`, `useProjectNotes`, `NotesPage`, `cloudSession` и `AppShell` — **41 passed в 6 files**; TypeScript typecheck и `git diff --check` — passed. Unit/jsdom tests мокают Ionic lifecycle и не заменяют GUI acceptance; поэтому нужна короткая live desktop recheck только пунктов 2–5. Сценарий real manual cloud sync одновременно с route switch в изолированном Web Chromium недоступен; код подтверждает, что `cloudSession.busy` отключает только cloud controls, а не sidebar или Notes editor; сброс `busy` после auth invalidation остаётся покрыт store regression.

**Исторический контекст C17:** этот отдельный `6.0-C17` worktree относится к ранним Pass 1–2A. После merge PR №22 дальнейшая C17 работа ведётся непосредственно в основной ветке `6.0`; C16 CLOSED, C17 остаётся `IN PROGRESS`, официальный прогресс — **73,0%**. Утверждённый Web First roadmap, C18 compression-before-E2EE и encrypted project metadata, C22 storage quotas и GNU GPLv3 dependency gate сохраняются.

## 69. C16 final GUI manual acceptance (историческая запись до закрытия)

Пользователь завершил final manual acceptance C16: **все пять проверок PASS** — (1) многократное открытие/закрытие editor; (2) editor после Settings → Notes; (3) переходы между Settings, Notes и Projects; (4) редактирование и сохранение Note после sync; (5) повторный sync, его индикатор и доступность интерфейса после завершения. Это историческая запись: subsequent merge and remote acceptance закрыли C16. Текущее состояние — **C16 CLOSED**, C17 `IN PROGRESS`, официальный прогресс **73,0%**.

`6.0-C17` остаётся исторической веткой/worktree и не является рабочей линией после merge PR №22. Pass 2B–2E уже завершены в основной `6.0`; C16 CLOSED, C17 IN PROGRESS, официальный прогресс **73,0%**. Web First roadmap, C18 compression-before-E2EE и encrypted project metadata, C22 storage quotas и GPLv3 dependency gate сохраняются без изменений.

## 67. C17 Pass 1–2D — conflict preservation и resolution v2 (исторический отдельный worktree)

**Исторический статус на момент записи.** C17 тогда велась независимо в `6.0-C17`; subsequent PR №22 перенёс её в основную `6.0`. Текущее состояние — C16 CLOSED, C17 `IN PROGRESS`, официальный прогресс **73,0%**. Pass 1 остаётся источником frozen conflict guarantees; исторический worktree не трогается.

Design freeze закреплён в `docs/cloud/C17_CONFLICT_DESIGN.md`: E2EE, AMK, crypto/AAD v1 сохраняются; plaintext/protocol v2 только зарезервированы для будущих resolution events; сервер не видит plaintext и не выбирает победителя; все доказанные конкурирующие версии должны сохраняться. ACK означает durable receipt, поэтому допускает только atomic `conflict_preserved`, но не `received`, обычный `conflict`, `orphan` или `rejected`. ACK сам по себе не разрешает server-side pruning без отдельного будущего retention contract. Автоматического HTML merge не будет; пользовательское разрешение и ручное объединение относятся к следующим проходам C17. Конфликты E2EE project names/metadata остаются C18.

Pass 1 вводит forward-only SQLite migration 017 с immutable full Note versions/tombstones, applied remote causal history, conflict groups, normalized tips, generation/lifecycle и защищённой inbox-ссылкой. Native `BEGIN IMMEDIATE` сохраняет remote tip и точную local unsealed outbox/intent generation до `conflict_preserved`, не меняя отображаемую Note; remote/remote siblings используют causal history, записанную атомарно с более ранним apply. Общая причинность доказывается общим ненулевым durable parent и одинаковой revision; receipt timestamp/server order не используются как причинность. Revision-1 Note-ID collision и неподтверждённая binding/history остаются fail-closed. Contiguous ACK prefix перепроверяет внутри транзакции полноценную preservation proof; корректно сохранённый конфликт не блокирует последующие независимо обработанные Notes.

**TypeScript ↔ Rust IPC contract:** native apply после успешного atomic preservation намеренно возвращает `conflict`, а не `conflict_preserved`. Это сохраняет различие между неразрешённым пользовательским конфликтом и ошибкой применения: TypeScript показывает/учитывает unresolved classification, но всё равно вызывает native ACK. Только ACK-транзакция имеет authority проверить durable `conflict_preserved` proof и продвинуть contiguous prefix; обычный `conflict` остаётся недопустимым. Focused IPC/inbox/orchestrator tests подтверждают, что `conflict` не превращается в `error`, ACK может вернуть `advanced`, а после restart уже сохранённое событие не попадает в повторный apply-loop.

**Оставшиеся границы следующих проходов:** безопасная совместимость с pre-017 applied histories без сохранённого causal snapshot; sealed локальные delete-ветви без durable plaintext tombstone; новые coalesced generations, созданные после первоначального сохранения конфликта; resolution-event Note plaintext v2/encrypted protocol v2 и согласованный hard cutover. Эти случаи Pass 1 полностью не реализует и не выдаёт за ACK-eligible.

**Параллельные ветки и Git:** ветка/worktree `6.0` продолжает C16 с незакоммиченными GUI-исправлениями; оставшаяся ручная приёмка отложена. `6.0-C17` независимо ведёт C17 от baseline `6c7edbfa24289fcfca39fc754eaff9a28e419dbc`. После закрытия C16 его изменения переносятся в C17 отдельным контролируемым действием. После завершения C17 пользователь создаёт первый Pull Request с base `6.0` и compare `6.0-C17`; помощь с PR будет дана отдельным заданием, самостоятельный merge Codex запрещён. C16 и C17 остаются `IN PROGRESS`, официальный прогресс — **70,0%**.

Утверждённый **Web First** roadmap сохраняется: после C18 следуют C21 Web, C22 Production Hardening, C23 Failure/Disaster Tests и PF 6.0/RC; C19/C20 остаются после первого публичного Desktop + Web релиза. C18 по-прежнему обязан реализовать versioned client compression-before-E2EE с bounded decompression и E2EE project names/metadata. C22 сохраняет account storage quotas, atomic concurrent enforcement, admin/user usage UI и явную политику учёта immutable versions. Для C18/C21/C22 и любых новых dependencies действует обязательный GPLv3 compatibility/distribution gate.

**Проверки C17 Pass 1:** Python SQLite/recovery/metadata — **54 passed**; Rust migration — **2 passed**; Rust remote apply — **18 passed**; Rust ACK — **4 passed**; Rust SQLite — **18 passed**; `cargo check` — passed. `npm ci` завершён из существующего lockfile без его изменения; targeted TypeScript IPC/inbox apply/orchestrator/ACK — **18 passed в 4 files**, TypeScript typecheck и финальный `git diff --check` — **passed**. Pass 1 remote Cloud и SQLite/Windows workflow — **SUCCESS**.

**Pass 2A завершён и опубликован:** commit `698836f5502b48a9be57c31d42be519332c097c7` freeze-ит exact-key JSON Note plaintext v2: multi-parent resolution header, sorted unique complete `resolved_event_ids`, strategies `choose_version`/`manual_merge`/`keep_both`/`delete`, max-parent-revision rule, codec-vs-SQLite causal boundary и fail-closed protocol-v2 hard cutover. Общий fixture `frontend/src/cloud/__fixtures__/noteSyncPlaintextV2Resolution.json` содержит synthetic edit/edit choice, delete/edit choice и unequal-depth manual merge, плюс compact negative matrix. Cloud CI — **SUCCESS**; SQLite/Windows workflow на этом documentation-only commit не запускался.

**Проверки Pass 2A:** новый JSON fixture и все его canonical expected bytes проверены локальным JSON/canonicality validation; `git diff --check` — passed. Никакие TypeScript/Rust suites, dependencies, full matrices или production tests для несуществующего v2 parser не запускались.

**Pass 2B опубликован:** commit `9f6fd493606981da7bdb3e615f0c7984ca778f2d` добавил standalone `frontend/src/cloud/noteSyncResolutionV2Codec.ts` и strict Rust `decode_note_sync_resolution_v2(...)` в `frontend/src-tauri/src/note_sync_plaintext.rs`; они не подключены к upload/pull/ACK/remote apply. TS canonical encoder/decoder сверяет каждый UTF-8 byte с canonical JSON; Rust декодирует те же shared canonical fixture bytes. Оба проверяют exact keys, lowercase UUID, canonical timestamp, safe integers, 2–64 sorted unique parents, primary/additional equality, self-reference, all four strategy/result forms, route identity и v1 fail-closed boundary. Codec намеренно **не** доказывает source snapshot/clone provenance, actual tip revision, conflict generation freshness либо concurrent new tip — это будущая native SQLite transaction. Изменены также v2 TS spec и только необходимые CI path/curated entries. Cloud run `36132484361` и SQLite run `36132484391` — **SUCCESS**.

**Проверки Pass 2B:** targeted TypeScript v2 + v1 codec/golden — **13 passed в 3 files**; targeted Rust `note_sync_plaintext` v2 + v1 golden/negative — **9 passed**; TypeScript typecheck — **passed**; `cargo check` — **passed** с 15 прежними unrelated warnings; final `git diff --check` — **passed**. Полные PostgreSQL/Python SQLite/frontend build/Rust matrix — **not run** по scope. Изменённые Pass 2B файлы: standalone TS codec/spec, Rust plaintext module, оба targeted CI workflow и checkpoint; v2 fixture Pass 2A не менялась. Commit/push/merge запрещены этим pass.

**Pass 2C опубликован и remotely accepted:** commit `47b2a6c1be4746163488425c9a4afd001e6c9de9` содержит forward-only migration 018 и `prepare_note_conflict_resolution(...)`: immutable prepared identity/payload, exact tips/generation, shared causal and strategy proof, stale local-generation protection и exact replay. Cloud run `36162028427` и SQLite sync substrate run `36162028398` — **SUCCESS**. Preparation не меняет Note/group/inbox/outbox/ACK/receipts и не подключена к IPC/runtime.

**Проверки Pass 2C:** focused real-SQLite Rust preparation + remote/conflict regressions — **22 passed, 0 failed**; Rust schema migration 15/16/17→18/reopen — **3 passed, 0 failed**; targeted Python schema/recovery/metadata — **55 passed, 0 failed**; `cargo check` и `git diff --check` — **passed**. Два tracked root `__pycache__/*.pyc` остаются user-owned изменениями вне C17 scope и не должны включаться в будущий commit.

**Pass 2D реализован и опубликован:** commit `6712dd2943259f71396872e07703beff1886d9b2` добавляет forward-only migration 019 с immutable `cloud_sync_note_resolution_outbox` и `cloud_sync_note_resolution_dependencies`. Queue хранит canonical v2 plaintext, account/device/project/entity/group/generation/revision, полный sorted parent set, strategy/result и optional clone identity; каждый parent сохраняет immutable snapshot и remote sequence либо точную local mutation generation/outbox lifecycle/upload receipt. Локальный parent после application нельзя coalesce/rewrite; unsealed intent можно удалить только после durable encrypted object. Queue всегда `local_pending`, не считается готовой к upload и не входит в protocol-v1 outbox.

Внутренняя `apply_prepared_note_conflict_resolution(...)` использует ту же causal/strategy validation primitive, что preparation, и внутри одной `BEGIN IMMEDIATE` transaction повторно проверяет authoritative binding, canonical identity, prepared lifecycle, open group, exact generation/tips, immutable snapshots/lineage/revisions и отсутствие новых local/remote изменений. Protected batch capability разрешает ровно одну original Note mutation и optional clone mutation; все authorizations обязаны быть consumed до commit. `choose_version`, `manual_merge`, `delete` и `keep_both` применяются без auto-merge и без создания v1 intents. Только после Note/clone, v2 queue и dependency rows pending меняется `prepared→consumed`, group — `open→resolving`; `resolved` не используется. Exact restart replay возвращает `AlreadyApplied`; changed bytes/другое решение conflict, stale generation/tip/local coalescing fail closed. Injected failure после original mutation полностью откатывает Note, clone, queue и lifecycles. Новый competing event после local apply остаётся unresolved `conflict` и не объявляет прежнее решение окончательным.

**Локальные проверки Pass 2D:** targeted Rust application/preparation/conflict suite — **26 passed, 0 failed**; Rust migration 15/16/17/18→19 + reopen — **4 passed, 0 failed**; targeted Python schema/recovery/metadata — **56 passed, 0 failed**. Финальный safety audit добавил позитивный regression frozen local parent → штатный v1 sealing → sealed-outbox listing → upload acceptance (**1 passed**), подтвердил rollback при фактической ошибке второй `keep_both` mutation (**1 passed**) и повторил затронутые sealed-outbox/acceptance regressions (**6 passed**). Аудит выявил и исправил узкий дефект существующего v1 reader: durable remote causal-history parent теперь признаётся серверно доступным только при точном совпадении account/project/entity/type/revision; неизвестный parent остаётся fail-closed. `cargo check` и `git diff --check` — **passed**. TypeScript, PostgreSQL, frontend build, full Rust matrix и remote CI для локального Pass 2D diff — **not run**, skipped — **0**. Existing unrelated Rust warnings remain. Python выполнялся с `PYTHONDONTWRITEBYTECODE=1` и `-B`; SHA двух user-owned `.pyc` не изменились.

**Оставшиеся границы:** Pass 2D не подключает operation/queue к public IPC, UI/coordinator, uploader, backend, pull/ACK или peer apply и не выполняет E2EE sealing либо protocol-v2 cutover. Canonical plaintext пока хранится только в защищённой local SQLite boundary; queue намеренно не ready. Group остаётся `resolving`, а не `resolved`; post-apply competing conflict требует будущего coordinator contract. Pre-017 applied history, sealed local delete без durable tombstone и unsupported unequal-depth causal groups остаются fail-closed. Следующий отдельный шаг — durable v2 E2EE sealing/upload с explicit parent-publication prerequisites, затем согласованный backend/protocol-v2 cutover и только после этого integration/UI; не начинать автоматически.

## C17 Pass 2E-B — локальный durable v2 E2EE sealing

**Статус: IMPLEMENTED LOCALLY; C17 остаётся IN PROGRESS, официальный прогресс 73,0%.** После merge PR №22 основная ветка — `6.0`, independently verified HEAD `374ffb20dbd59d9ee6f685f9203fcf6ac418eeda`; Cloud backend `36184778505` и SQLite substrate `36184778474` — SUCCESS; C16 CLOSED. Migration 020 разрешает только `local_pending → sealed_local` и требует opaque envelope в той же SQLite transaction. Isolated Rust/IPC/TypeScript boundary encrypts stored canonical v2 bytes with existing AMK/object context; exact replay requires identical nonce/ciphertext. Readiness is internal and requires durable remote causal proof or accepted local parent plus receipt; v1 uploader/runtime/backend remain untouched. Local checks: TS v2 codec+sealing **7 passed**; typecheck **passed**; Rust `note_sync` **105 passed, 0 failed**; `cargo check` **passed** with existing warnings; Python schema/recovery **52 passed, 0 failed**; `git diff --check` passed. No commit/push; no protocol-v2 cutover.

### Pass 2E-C — direct sealing/readiness regressions

Прямые real-SQLite regressions закрыли atomic seal, injected rollback, restart/exact-envelope replay, conflicting object/envelope, account/device/project/entity/payload CAS, immutable queue/dependencies/envelope и динамическую parent readiness. Аудит исправил два найденных дефекта: commit теперь повторно проверяет authoritative account/key/device/project binding и exact canonical payload; readiness различает conflict-preserved `remote` proof через exact inbox/version evidence и `remote_applied` proof через causal history, включая scope/revision/sequence/snapshot. Local parent требует `accepted` outbox, matching frozen generation/snapshot и durable receipt. TS coordinator дополнительно прекращает commit при stale AMK lease; IPC repository передаёт полный CAS scope. Проверки: новые Rust sealing/readiness **4 passed**, затронутые v1/frozen-parent regressions **3 passed**, targeted TS codec/sealing/IPC **10 passed**, Python schema/recovery **52 passed**, TypeScript typecheck и `cargo check` — passed, `git diff --check` — passed; existing Rust warnings remain. C17 остаётся `IN PROGRESS`, официальный прогресс — **73,0%**; backend/protocol-v2, upload, peer apply, ACK, runtime и UI не подключены.

## C17 Pass 2F-A / 2F-B — dormant backend encrypted transport v2

**Статус: 2F-A DESIGN FREEZE; 2F-B IMPLEMENTED LOCALLY, НЕ АКТИВИРОВАН.** Основная ветка `6.0`; PR №22 merged. Published Pass 2E SHA `d2d3d99f404c765681e63f03539f3e9537f85b47`; Cloud backend `36218867612` и SQLite substrate `36218867600` — SUCCESS. C16 CLOSED; C17 IN PROGRESS; официальный прогресс остаётся **73,0%**.

Pass 2F-A зафиксировал независимость encrypted transport v2, Note plaintext codec v1/v2 и неизменных crypto/AAD v1. Сервер не получает AMK, plaintext resolution, causal DAG, snapshots или winner selection; historical Note v1 остаётся v1 decoder path, resolution — отдельным strict v2 path.

Pass 2F-B добавляет Alembic revision с account-scoped `writer_transport_version` (default `1`) и `cutover_epoch`, плюс server metadata allowance `resolution`. Authenticated `/api/v2/sync/encrypted/capabilities` возвращает только supported transport version, account mode и epoch. Separate `/api/v2/sync/encrypted/{push,pull,ack}` строго требуют protocol/encrypted version `2`, crypto/AAD `1`, принимают opaque Note `upsert/delete/resolution`, сохраняют exact replay и общую server sequence. Production mode-flip endpoint отсутствует; все existing/new accounts остаются mode `1`.

Authoritative mode check исполняется внутри той же locked `sync_user_state` transaction, что mutating push/ACK sequence work. Mode `1` rejects v2; test-only mode `2` rejects every v1 push/pull/ACK route, включая generic C9. Device registration version-neutral и не публикует events. V2 pull возвращает historical encrypted v1 Notes без rewrite, но fail-closed без cursor advance на metadata-only/future unsupported event. ACK — только durable device cursor; conflict decision и pruning не добавлены.

Focused PostgreSQL regression file покрывает default mode/capabilities, mode-1 v1 compatibility и v2 rejection, mode-2 v1 rejection, registration boundary, monotonic JavaScript-safe epoch и запрет `2→1` downgrade, opaque resolution replay/conflict, historical v1 pull, ACK/no-pruning, malformed v2 metadata/versions и metadata-only gap. Real disposable PostgreSQL 16 container `nfprogress-c17-2fb-postgres` использовал только host port `55435`, отдельную database `nfprogress_c17_2fb_test`, no volume; после проверки удалён. Alembic head upgrade twice, new v2 suite, affected v1 encrypted-sync и ACK regressions: **32 passed, 0 failed, 0 skipped** (one existing TestClient deprecation warning). Проверка выявила и исправила `CREATE FUNCTION` reuse after fixture table reset, SQL-level ban on `2→1` even with a higher epoch, v2 response DTO conversion, Alembic-head expectation и invalid short negative ciphertext fixture. Python syntax проверен через `ast.parse`, без `py_compile`. Cloud workflow явно перечисляет новый test file. Python bytecode caches теперь исключены из Git index: tracked `engine`, `game_data` и `main_UI` cache files оставлены локально, но игнорируются существующими root `.gitignore` rules. Client/Tauri/SQLite uploader, local resolution receipts, peer apply, ACK eligibility, runtime/UI и mode activation остаются deferred.

## C17 Pass 2F-C1 — local durable resolution upload substrate

**Статус: IMPLEMENTED LOCALLY; не опубликован.** Published Pass 2F-B acceptance остаётся `e0b53df98c9245fb4afbc3face39ac6f1784fa16`; Cloud run `36225667255` — SUCCESS. C16 CLOSED; C17 IN PROGRESS; официальный прогресс остаётся **73,0%**.

Forward-only SQLite migration 021 расширяет только lifecycle resolution outbox `local_pending → sealed_local → accepted`, сохраняет immutable canonical payload, parent dependencies и encrypted object, и вводит отдельный `cloud_sync_note_resolution_upload_receipts`: v1 receipts не меняются и не получают новый FK. SQL triggers требуют object до sealing/acceptance, durable resolution receipt до `accepted` и не допускают collision account/server-sequence между v1 и resolution receipt ledgers.

Новые narrow Rust/Tauri internal commands: bounded reader под повторной account/device/canonical-user scope proof возвращает только sealed envelope и v2 transport metadata, заново проверяя полный frozen parent-publication proof в одной read transaction; canonical plaintext, parent DAG и keys не возвращаются. Receipt commit использует `BEGIN IMMEDIATE`, заново проверяет binding, immutable event/object, lifecycle и server sequence; exact replay возвращает `AlreadyAccepted`, не перезаписывая nonce/ciphertext или diagnostic `duplicate`; один bad receipt откатывает batch. Runtime, TypeScript HTTP uploader, backend mode flip, v2 pull/peer apply/ACK/UI отсутствуют. Future uploader обязан повторно читать readiness immediately before dispatch; successful HTTP response без локально committed durable receipt не считается acceptance.

Local focused checks: Rust resolution regression filter **17 passed, 0 failed** (включая reader, parent proof, restart/exact receipt replay, duplicate diagnostic preservation, v1 sequence collision и injected receipt rollback), Rust migration/reopen **5 passed, 0 failed**, affected v1 sealed-outbox/receipt **2 passed, 0 failed**, targeted Python SQLite schema/recovery **23 passed, 0 failed**. `cargo check` и `git diff --check` passed; existing Rust warnings are unchanged. SQLite workflow path filters already cover migration files, `note_sync.rs`, `sqlite.rs`, `test_c9_sqlite_sync.py` and recovery tests; no workflow widening is required. Следующий отдельный pass — **2F-C2 TypeScript v2 transport/uploader**; не начинать автоматически.

## C17 Pass 2F-C2 — dormant TypeScript resolution v2 transport

**Статус: IMPLEMENTED LOCALLY; не опубликован.** Pass 2F-B remotely accepted; Pass 2F-C1 remotely accepted at `473b5951549a194d4b558573076aae50afca9756` (SQLite run `36235897082` SUCCESS). C16 CLOSED; C17 IN PROGRESS; официальный прогресс остаётся **73,0%**.

Добавлены отдельные v2 capabilities/push client, scoped C1 IPC repository и dependency-injected dormant resolution uploader. Client строго допускает только transport/encrypted version 2, crypto/AAD 1, canonical Base64URL opaque envelope, bounded 1–100 batch и exact complete response receipts. Uploader получает canonical user/device только из authenticated context, binding и durable identity, проверяет capability mode 2, заново читает C1 readiness непосредственно перед dispatch и batch-commits только полностью validated receipts. Mode 1, malformed/partial response, auth epoch/account switch и server `sync_transport_mode_incompatible` fail closed без SQLite acceptance. Нет E2EE sealing, plaintext/DAG network fields, runtime/scheduler/UI wiring, mode activation, v2 pull/ACK/peer apply. Pass 2F-D/2F-E остаются отдельными.

Behavioral acceptance and final safety audit added direct public-uploader coverage for mode gate, malformed capability/receipt fail-closed handling, authoritative identity, fresh ordered full-batch/envelope proof, exact duplicate receipt after lost response, native acceptance failure, auth invalidation/account switch, completion of an already-started scoped native commit, single-flight release, 100-event limit and aggregate/wire bounds. The uploader now revalidates injected capability/push values at its own boundary, requires an exact ordered fresh batch (not only a subset), validates native acceptance cardinality, and applies wire/envelope bounds before dispatch. The v2 client additionally rejects non-canonical/duplicate identities, invalid timestamp or bounded metadata, foreign receipts and duplicate server sequences before persistence. Local checks: the three new C2 specs **20 passed**; affected existing v1 API/upload/auth regressions **23 passed**; total **43 passed, 0 failed, 0 skipped**. TypeScript typecheck, production frontend build and `git diff --check` passed. Cloud frontend job mandatorily runs all three C2 specs. Pass 2F-C2 is locally complete; remote acceptance is still required before Pass 2F-D.

## C17 Pass 2F-C2 remote acceptance / Pass 2F-D2A

Pass 2F-C2 remotely accepted at `85e4ed985dcc5d31b2ae3fdcb4a2a096011c97d5`: Cloud run `36242908112`, Frontend admin and PostgreSQL cloud backend — SUCCESS. C16 remains CLOSED; C17 remains IN PROGRESS; official progress remains **73,0%**.

**D2A remotely accepted.** Commit `94823b8ef2ebe761442ba37bed99c9ea9b192bf1`; SQLite CI `36249365054` and Cloud CI `36249365016` — SUCCESS, all four mandatory jobs passed. Forward-only migration 022 extends the single durable inbox with opaque Note `resolution` while preserving the mixed account server-sequence uniqueness and legacy rows. Resolution metadata/object are immutable after receipt; inbound-page commit remains one `BEGIN IMMEDIATE` transaction with exact replay and cursor CAS. Resolution starts `received`, therefore the contiguous ACK proof blocks it until a later peer-apply transaction provides durable applied evidence. No peer resolution apply, self-echo reconciliation, v2 pull/ACK client, runtime/UI or mode activation is connected.

## C17 Pass 2F-D2B0A — durable applied-resolution proof

**Статус: REMOTELY ACCEPTED.** Commit `ee6b69eb72e7fb76673551efeea55f553da554f6`; SQLite CI `36260256520` and Cloud CI `36260256395` — SUCCESS. Forward-only migration 023 adds an immutable event-scoped `cloud_sync_note_applied_resolutions` ledger and ordered `cloud_sync_note_applied_resolution_parents`. It records authenticated sender group ID/generation separately from the receiver's proven local group ID/generation, full canonical parents, exact conflict-version snapshots and publication evidence, result/strategy, optional keep-both clone evidence and `applying → applied`. Completion requires all 2–64 edges to match both the stored canonical parent order and the receiver's current exact tip set/common-parent/generation proof. A resolution inbox row cannot enter `applied` without the completed matching ledger; incomplete `applying`, `received` and `orphan` evidence remains non-ACK-eligible. Ledger, edges and completed inbox state were proven commit-able in one transaction, with injected rollback and file-backed restart.

Migration 023 also extends resolution upload receipts with immutable `acceptance_source`: existing and ordinary push receipts remain `push_response` with their exact boolean `duplicate`; a future atomic self-echo may record `pull_self_echo` with unknown (`NULL`) duplicate. Cross-table account/server-sequence guards cover resolution/v1 receipts and applied-resolution/v1 causal history in both write orders. An accepted local resolution alone no longer releases v1 Note intents for its original or clone; a completed applied ledger is required. The normative C17 design now states explicitly that inbound group ID/generation are sender-scoped while local group identity/generation are an independent exact-tip CAS; the frozen v2 payload, codec, crypto and AAD remain unchanged, and uncoordinated v2 activation remains forbidden before 2F-E.

Final local safety audit fixed four fail-closed gaps without expanding D2B0A: parent publication proof now binds operation (and the local receipt device), applied-ledger insertion rejects a mismatched receipt sequence, an accepted local resolution releases v1 intents only after exact self-echo evidence, and Python migration failures roll back even when the SQL script itself fails. Python application-version tracking now also covers the receipt, applied-ledger and parent-edge tables. Added regressions cover migration rollback, account-scoped sequence isolation, mismatched publication operation, exact self-echo release and the new metadata triggers.

Local checks after the audit: mandatory Python SQLite/API workflow set **100 passed, 0 failed, 0 skipped** (one existing Starlette deprecation warning); Rust `note_sync` **114 passed, 0 failed, 0 ignored**; Rust `sqlite` **29 passed, 0 failed, 0 ignored**; `cargo check` passed with the existing 15 unrelated warnings; `git diff --check` passed. Clean/current, populated 022→023, historical v6→023, repeated open, file-backed restart and `PRAGMA foreign_key_check` are covered. D2B0A does not mutate Notes and does not implement peer apply, self-echo reconciliation, multi-parent causal continuation helpers, v2 pull/ACK, runtime/UI or mode activation.

## C17 Pass 2F-D2B0B — multi-generation conflict-tip repair

**Статус: REMOTELY ACCEPTED.** Commit `0e8dcca90db75be8ddcf8e722e11fabb1e015f67`; SQLite CI `36263778213` and Cloud CI `36263778260` — SUCCESS. Architectural preflight D2B1 proved that immutable conflict versions and tips retain the generation in which each sibling was discovered, while the conflict group generation advances when a later sibling arrives. Migration 023 incorrectly required every historical version/tip generation to equal the current group generation, so a valid three-branch conflict could not complete its applied-resolution proof.

Forward-only migration 024 replaces only `cloud_sync_note_applied_resolution_parent_insert_guard` and `cloud_sync_note_applied_resolution_completion_guard`. Parent evidence must still match the exact local group, account/project/entity scope, current group generation and lifecycle, immutable conflict version/event/revision/operation/snapshot/common parent, exact current tip membership, canonical ordinal and the complete remote/remote-applied/local-accepted publication proof. Completion retains the current local generation CAS, canonical order, cardinality, maximum-parent-revision rule and exact full current event/version tip set, but no longer equates an immutable tip's historical generation with the current group generation. A fourth sibling advancing the group invalidates an older applying ledger before completion.

Production-path Rust regressions cover a group at generation 2 containing two generation-1 tips and one generation-2 tip, successful three-parent completion and ACK eligibility, plus rejection and rollback after a fourth tip advances the group to generation 3. Python regressions cover missing/extra tips, wrong version, changed snapshot, wrong common parent, missing publication proof, populated file-backed 023→024 upgrade/reopen, preservation of all unrelated triggers and historical data, clean/historical upgrades and foreign-key integrity. The final safety audit additionally injects an SQL authorization failure after migration 024 has begun replacing its triggers and proves full trigger restoration with the schema marker retained at 23 before a successful retry. Final local checks: Rust `note_sync` **116 passed, 0 failed, 0 ignored**; Rust `sqlite` **29 passed, 0 failed, 0 ignored**; mandatory Python SQLite/API workflow set **108 passed, 0 failed, 0 skipped**; `cargo check` passed with the existing 15 unrelated warnings; `git diff --check` passed.

## C17 Pass 2F-D2B1 — dormant native peer resolution apply

**Статус: REMOTELY ACCEPTED.** Commit `e108ad68848f2145adfccfa4fb351bee38978a0d`; SQLite CI `36305312793` and Cloud CI `36305312773` — SUCCESS. A separate `apply_verified_received_resolution_v2` Tauri command accepts only TypeScript-authenticated canonical v2 plaintext plus authoritative inbox/envelope identity and immediately clears the command-owned mutable plaintext bytes. The privileged `BEGIN IMMEDIATE` transaction independently revalidates account/user/pulling-device binding, immutable resolution inbox metadata, source device and sequence, exact crypto/AAD/nonce/ciphertext, project binding and canonical frozen-v2 header. It never falls back to the v1 decoder and is registered but not called by the frontend, runtime, scheduler or UI.

Peer matching treats remote group ID/generation as sender-scoped and locates the one local open group by account/project/entity, exact sorted tip event set, immutable local version evidence, common parent and publication proof. Local group ID/generation remain an independent migration-024 CAS, so groups with historical tip generations `1,1,2` apply at current generation 2 while a later tip or unsealed local edit fails closed. All four strategies revalidate their authenticated result against immutable tips; `keep_both` additionally rejects clone collisions across Notes, entity heads, v1/resolution outboxes and applied ledgers.

Original/clone protected Notes mutations, applied ledger, ordered parent edges, resolution entity heads, ledger completion, group `resolved` CAS and inbox `applied` transition commit atomically. Exact replay after file-backed restart uses immutable inbox/object/canonical payload and completed ledger evidence, returns `AlreadyApplied`, and never replays Note mutation or clone creation. Missing group/parent/publication evidence remains durable `orphan` and ACK-blocking. Own-device resolution echoes return `SelfEchoPending` without mutation or receipt fabrication for future D2B2. No outgoing v1 or resolution event is created. Because v1 still cannot encode a multi-parent resolution head, native intent preparation now fails closed for original and clone entities whose current head is an applied resolution; full causal continuation remains separate work.

Focused peer tests **6 passed, 0 failed, 0 ignored** and cover four strategies, different remote/local IDs and generations, two- and three-parent groups, historical `1,1,2` tips, missing group/parent/publication, stale extra tip and local edit, immutable envelope/scope/source/sequence/snapshot mismatches, clone collision, two injected rollback points, ACK before/after commit, future-edit blocking, exact file-backed replay and self-echo isolation. The final safety audit additionally clears the owned canonical plaintext byte buffer on both decode failure and every transaction result; rejects unmatched same-device self echoes without mutation; rejects a changed canonical payload after restart; and proves the causal-continuation guard for both the original and `keep_both` clone while an unrelated Note can still create a normal v1 intent. Full Rust `note_sync` **122 passed, 0 failed, 0 ignored** and Rust `sqlite` **29 passed, 0 failed, 0 ignored**. `cargo check` passed with the existing 15 unrelated warnings; final scope and `git diff --check` passed.

D2B1 does not implement D2B2 self-echo reconciliation, TypeScript v2 pull/decrypt integration, v2 ACK transport, full multi-parent child publication, runtime/UI wiring or mode activation. The existing inbound reader selects only `state='received'`; D3 therefore must provide an explicitly scoped retry reader/path for durable resolution rows in `state='orphan'` before retryable missing group/parent/publication evidence can be rediscovered after restart. C16 remains CLOSED; C17 remains IN PROGRESS; official progress remains **73,0%**.

## C17 Pass 2F-D2B2 — dormant native resolution self-echo reconciliation

**Статус: IMPLEMENTED LOCALLY / REMOTE CI PENDING.** The separately registered `reconcile_verified_received_resolution_self_echo` Tauri command handles only a locally-created resolution returned by pull and remains disconnected from TypeScript, runtime, scheduler and UI. Inside one privileged immediate transaction it rechecks authoritative account/user/current-device scope, same-device source identity, immutable inbox metadata and encrypted object, the canonical frozen-v2 payload, exact local pending/outbox identity, the resolving local group, complete current tip set and publication proof. It never repeats the already-completed local Note mutation.

For an already accepted outbox, reconciliation requires and preserves the exact immutable `push_response` receipt, including its original `duplicate`. For a lost HTTP response, the same transaction inserts `acceptance_source='pull_self_echo'` with `duplicate=NULL`, advances only the matching outbox from `sealed_local` to `accepted`, writes the applied-resolution ledger and ordered parent edges, advances original/optional clone resolution heads, resolves the group and marks the inbox applied. V1/resolution receipt sequence collisions are rejected in both insertion orders. Four injected failure boundaries prove rollback of a newly inserted receipt, outbox acceptance, ledger/edges/heads, group and inbox as one unit. Completed replay validates the immutable inbox/object/payload/outbox/receipt, full ordered edge evidence and current resolution heads, then returns `AlreadyReconciled` without creating another receipt, clone or Note mutation.

Local production-path coverage adds **7 self-echo test groups**: all four strategies with an existing push receipt; lost-response recovery and `duplicate=NULL`; four rollback boundaries; scope/source/sequence/object/payload/outbox/lifecycle failures; multi-generation `1,1,2` tips and missing parent publication; bidirectional v1/resolution receipt collisions; and file-backed exact replay without a second clone or receipt. The final safety audit made a pre-existing `pull_self_echo` receipt acceptable only for a fully completed `applied` replay, removed `Debug` from plaintext-bearing command/plan structures, clears command-owned and SQLite-loaded mutable canonical-payload byte buffers, and explicitly proves fail-closed behavior for an unexpected pre-reconciliation Note state while a completed replay does not depend on current Note content. Strategy tests now assert the actual locally applied choose/merge/keep-both/delete results, zero reconciliation mutations, exact edge counts and the absence of a synthetic v1 causal row.

Final local checks: Rust `note_sync` **129 passed, 0 failed, 0 ignored**; Rust `sqlite` **29 passed, 0 failed, 0 ignored**; `cargo check` passed with the existing 15 unrelated warnings; `git diff --check` and staged diff validation passed. The Windows SQLite workflow path filters include both changed Rust files and its mandatory `note_sync`/`sqlite` commands.

D2B2 does not implement D3's scoped reader/retry path for durable `orphan` resolution rows, TypeScript v2 pull/decrypt-to-native integration, v2 ACK transport or full multi-parent causal continuation. Subsequent v1 intents over a resolution head remain fail-closed until causal continuation is implemented and tested. Pass 2F-E remains responsible for coordinated runtime cutover and real two-device acceptance. C16 remains CLOSED; C17 remains IN PROGRESS; official progress remains **73,0%**.

## C17 Pass 2F-D2B2 — remote acceptance

**Статус: REMOTELY ACCEPTED.** Commit `457b5ed8fdac11d457c087159090a1354b623e1f`; SQLite CI `36320191546` — **SUCCESS**; Cloud CI `36320191549` — **SUCCESS**. D2B2 is accepted with the same dormant boundary described above.

## C17 Pass 2F-D3A — durable orphan resolution retry reader

**Статус: REMOTELY ACCEPTED.** Commit `9cab70eb10ebcc4d72b6fb6901ae69acc8a7f03c`; SQLite CI `36322584300` — **SUCCESS**; Cloud CI `36322584262` — **SUCCESS**. A separate registered Tauri command `list_orphan_note_resolution_inbox` reads only the exact account-scoped durable `note` / `resolution` rows in state `orphan`. It repeats canonical-user and current pulling-device validation, uses a read-only SQLite transaction, returns immutable metadata plus the verified encrypted envelope, and never decrypts plaintext or mutates inbox state, errors, ACK, cursor or causal proof.

The reader accepts `limit` 1–32 and a non-negative safe-integer `after_server_sequence`, orders by ascending server sequence and applies a strict keyset boundary. It validates crypto/AAD versions, canonical nonce/ciphertext, individual object bounds and aggregate ciphertext bounds through the existing envelope validator. The TypeScript `NoteSyncInboxRepository` exposes a typed dormant `listOrphanResolutions(...)` adapter with literal `operation: 'resolution'`, canonical base64url decoding and explicit preservation/verification of native crypto/AAD versions. It is not called by the production runtime, orchestrator or UI, and does not route v2 resolutions through the v1 decryptor.

Focused Rust/SQLite coverage proves orphan-only filtering, exclusion of received/applied/v1 rows, scope failures, 1–32 limits, keyset pagination, missing durable objects, malformed envelopes and no SQLite mutation; existing received-reader coverage remains present. Focused `noteSyncInbox.spec.ts` coverage proves typed metadata/envelope decoding, IPC arguments and pagination validation.

## C17 Pass 2F-D3B — resolution v2 decrypt and native dispatch

**Статус: REMOTELY ACCEPTED.** Commit `bcab0b8fe0886dbca9df15edad5e9903e9e4fa29`; Cloud CI `36324229043` — **SUCCESS**. A separate dormant `NoteSyncResolutionInboxApplier` performs bounded resolution-v2 processing only inside the existing authoritative AMK lease. Before entering the lease it revalidates the current auth/account binding and native pulling-device scope. It uses production `decryptObjectBytes` with the same canonical-user/project/entity/`note` AAD context as resolution sealing, decodes only the frozen canonical v2 format, independently binds its complete header to durable inbox metadata, and passes exact scope, inbox identity, source device, encrypted envelope and canonical plaintext bytes to the existing native commands. Own-device events route only to self-echo reconciliation; peer events route only to peer apply, with no cross-path fallback.

The adapter clears decrypted bytes, IPC number arrays and local envelope buffers on success and every error, returns metadata/status or a bounded safe error code only, and does not persist or log plaintext. The mixed received-inbox contract now represents `resolution` explicitly; the frozen v1 decrypt/apply path classifies it as `resolution_v2_pending` without invoking the v1 decoder or changing durable state. Orphan retry uses the D3A keyset reader with default page size 8, maximum 32 and at most two pages per pass; an unresolved orphan does not block later entries, and a missing optional reader is reported as unavailable rather than an empty queue.

Focused production-crypto tests cover authenticated frozen-v2 decrypt, metadata binding, peer/self-echo routing, native status separation, IPC failure, auth/lease/device scope, tampered ciphertext, noncanonical v2, buffer cleanup and bounded orphan pagination. Existing v1 decrypt/apply and repository regressions remain in the final mandatory set, and the new spec is included in the curated Cloud CI command. D3B remains disconnected from the orchestrator, scheduler, UI, HTTP runtime and ACK transport.

## C17 Pass 2F-D4A1 — fair paginated mixed inbox readers

**Статус: REMOTELY ACCEPTED.** Commit `2416f382ad5fad93375f485e64a8f2aba3b615a1`; SQLite CI `36325320271` — **SUCCESS**; Cloud CI `36325320274` — **SUCCESS**. The new dormant native command `list_received_note_sync_inbox_page` splits the existing durable `received` Note inbox into independently keyset-paginated v1 (`upsert`/`delete`) and v2 (`resolution`) streams. It repeats authoritative account/canonical-user/current-pulling-device scope validation and returns only immutable metadata plus validated encrypted envelopes. Both streams require a limit of 1–32 and a non-negative safe server-sequence cursor, select strictly greater sequence values in ascending order, and do not decrypt or mutate inbox state, errors, cursors, ACK or causal proof.

The legacy mixed received reader and D3A orphan-resolution reader remain compatible and now share the same internal read-only envelope-validation path. Rust/SQLite regressions prove two-way starvation resistance across 32 earlier events, operation filtering, keyset order and replay determinism, state disappearance, limits, scope rejection, missing/malformed encrypted objects and zero write effects. The typed TypeScript repository exposes overloaded `listReceivedPage(...)` calls: v1 callers can receive only v1 items, and resolution callers only resolution items; canonical base64url and crypto/AAD checks are retained. No runtime, orchestrator, scheduler, polling, ACK transport or apply path is connected.

D4A1 is read-level fairness only. D4A2 must still supply bounded mixed-inbox orchestration, orphan retry and safe runtime integration; D4B retains v2 ACK transport. Multi-parent causal continuation remains required before new edits can safely follow a resolution head, and Pass 2F-E retains coordinated cutover and two-/three-device acceptance. C16 remains CLOSED; C17 remains IN PROGRESS; official progress remains **73,0%**.

## C17 Pass 2F-D4A2 — bounded mixed inbox orchestration

**Статус: IMPLEMENTED LOCALLY.** The v1 and resolution-v2 appliers now expose narrow page methods backed exclusively by D4A1 `listReceivedPage(...)`. Each page reports the number actually read, its final server-sequence cursor, per-event results and error count while retaining the established authoritative AMK lease, authenticated decrypt, immutable metadata binding, peer/self-echo separation, native dispatch and buffer clearing. Missing paginated readers fail explicitly; legacy `applyOnce` and `applyReceivedOnce` remain compatible and keep their prior behavior.

The orchestrator exposes a dormant internal `runMixedInboxOnce(...)` apply-only mode. Every bounded round offers at most one page to each of the independent v1 and resolution streams and advances their in-pass cursors by the final event actually read, including blocked or failed events. A top-level failure disables only that stream for the remainder of the pass, leaving the independent stream its turn. Per-event `orphan`, `self_echo_pending`, conflict, rejection and errors are not reported as successful completion; full final pages and exhausted pass budgets retain `hasRemainingWork`. Existing auth/key freshness checks and same-lifecycle single-flight joining remain in force.

After received processing, one bounded orphan retry pass resumes from an in-memory cursor scoped to the account, device, auth epoch and key lifecycle. The D3B adapter accepts an initial cursor, returns the last inspected sequence and whether the scan reached its end, and still reads at most two pages per call. A long orphan queue is therefore traversed round-robin across finite consecutive cycles; reaching the end resets the next cycle to sequence zero. This cursor is neither durable evidence nor an ACK/pull cursor and is safely lost on restart.

The production runtime remains on the established v1-only `runOnce(...)` route and does not compose or call mixed processing. The dormant mixed path performs no HTTP pull, upload, sealing or ACK and cannot emit a legacy v1 ACK for incomplete v2 work. D4B still owns v2 HTTP pull/ACK and coordinated activation. Multi-parent causal continuation and Pass 2F-E controlled two-/three-device acceptance remain deferred. C16 remains CLOSED; C17 remains IN PROGRESS; official progress remains **73,0%**.

## C17 Pass 2F-D4A2 — remote acceptance

Commit `bd22734160472da769dfbcf6139b426a8926bf07` independently verified on `origin/6.0`. Cloud backend tests run `36332040244`: Frontend admin — **SUCCESS**; PostgreSQL cloud backend — **SUCCESS**. SQLite workflow was not triggered because the D4A2 published diff contained only frontend TypeScript and this checkpoint.

## C17 Pass 2F-D4B1 — dormant encrypted transport v2 pull and ACK substrate

**Status: REMOTELY ACCEPTED.** Commit `67e2c10707f55c28147e199dcc33159923893f59` independently verified on `origin/6.0`; Cloud backend tests run `36412972270` — **SUCCESS**; Frontend admin — **SUCCESS**; PostgreSQL cloud backend — **SUCCESS**. SQLite workflow was not triggered because D4B1 changed only frontend TypeScript, workflow and checkpoint files, with no watched Rust/SQLite/Python substrate. The strict authenticated v2 pull API accepts the backend's mixed historical Note upsert/delete and resolution stream, validates exact metadata, ciphertext and pagination limits, and returns opaque envelopes without decryption. Unsupported/future or metadata-only events fail closed. The shared validated pull-batch type now carries resolution events into the existing atomic native inbound commit; the v1 HTTP parser still rejects resolution.

The dormant v2 inbox adapter reads the authoritative SQLite cursor after current-user/device binding, checks transport mode 2, and commits only a validated pull page after renewed auth checks. The dormant v2 ACK adapter uses the existing native contiguous ACK candidate, sends the version-2 ACK first, and then uses the native CAS commit result. Failed/lost responses leave local cursors unchanged; retry remains possible. No production runtime or `runOnce()` wiring was changed, and the existing device registration remains version-neutral.

Local checks: focused v2 API/adapter tests **17 passed, 0 failed, 0 skipped**; affected v1/runtime/mixed apply regression tests **74 passed, 0 failed, 0 skipped**; final v1+v2 transport tests **27 passed, 0 failed, 0 skipped**; TypeScript typecheck and production frontend build — **passed**. The frontend CI curated command includes the new adapter spec. C16 remains CLOSED, C17 remains IN PROGRESS, and official progress remains **73,0%**. Coordinated production activation, multi-parent continuation, Pass 2F-E acceptance and C18 remain deferred.

## C17 Pass 2F-D4B2A — dormant ordinary Note upload over encrypted transport v2

**Status: REMOTELY ACCEPTED.** Commit `60ef92cacd0d8d82ff638f304e5da69e8c4bc6e9`; Cloud backend tests run `36416417558` — **SUCCESS**. The v2 PUSH client now validates ordinary Note `upsert` and `delete` alongside frozen `resolution`, with operation-specific tombstones and revision floors and unchanged crypto/AAD 1, strict opaque envelope, aggregate, wire, UUID, timestamp and receipt checks. The backend's existing v2 schema/service already accepts these operations; no backend production code changed.

The separate dormant ordinary v2 uploader uses the existing sealed Note outbox and native `commit_note_sync_upload_acceptance` receipt transaction. It requires current authenticated user binding, durable account/device identity and exact scope for every listed row, orders listed sealed parents before children, bounds batches to 100 and ciphertext/wire limits, checks writer mode 2, rereads the selected sealed batch before dispatch, validates the complete server receipt and commits only after fresh auth checks. Mode 1 or a server mode flip leaves rows sealed and retryable; lost HTTP results and local acceptance failures do not mark acceptance. The resolution uploader and its separate ledger remain unchanged. The new uploader has no production caller: runtime `retry()`, project bootstrap and `runOnce()` still use the v1 route; mixed inbox remains dormant and no writer-mode flip was added.

Final focused v2 API/new uploader run: **24 passed, 0 failed, 0 skipped**. Seven affected v1/resolution/transport/orchestrator/runtime spec files: **73 passed, 0 failed, 0 skipped**. TypeScript typecheck, production frontend build and `git diff --check` — **passed**. The new uploader spec is listed in the curated Cloud frontend CI command. C16 remains CLOSED; C17 remains IN PROGRESS; official WORTA progress remains **73,0%**. At D4B2A, full dormant mode-2 orchestration, multi-parent continuation, production activation, Pass 2F-E and C18 remained deferred.

## C17 Pass 2F-D4B2B — dormant complete transport-v2 Notes cycle

**Status: REMOTELY ACCEPTED.** Commit `33e39f146f56af667a865aaaa53d13bc8a0538a7`; Cloud backend tests run `36418255742` — **SUCCESS**. A separate dormant `NoteSyncV2Cycle` composes authoritative auth/account/device/key and writer-mode preflight, version-neutral registration, frozen ordinary Note sealing, ordinary and resolution v2 uploads, bounded v2 pull, established fair mixed apply with orphan retry, and native-proof v2 ACK. It retains independent durable upload ledgers and the existing pull/ACK cursors. Failed registration, sealing, pull or top-level mixed apply stops the cycle; independent outbound queues are both attempted on non-mode upload errors, then the cycle stops before pull. Stale context or mode mismatch stops immediately without v1 fallback. A lifecycle-scoped single-flight map joins only matching account/device/auth/key contexts. Structured results preserve bounded stage, blocked and error evidence.

This is **not production activation**: runtime retry, bootstrap, UI, scheduler and ordinary production `runOnce()` remain on v1. No server writer-mode flip, multi-parent causal continuation, coordinated two-/three-device acceptance or C18 work is included. C16 remains CLOSED; C17 remains IN PROGRESS; official WORTA progress remains **73,0%**.

Local checks: new cycle spec **10 passed**; affected v1/v2 upload, transport, inbox apply, ACK, orchestrator and runtime specs **88 passed across 9 files** (including the initial cycle spec before its final two cases); TypeScript typecheck, production frontend build and `git diff --check` — **passed**. Rust, Python, PostgreSQL and full repository suites were not run because their production files did not change. The new cycle spec is included in the curated Cloud backend frontend command; independent remote CI subsequently passed.

## C17 Pass 2F-D4C1 — safe causal continuation after applied resolution

**Status: REMOTELY ACCEPTED.** Commit `cfec4bf689b5f0ce91d185c9ead83bf132bbc6e2`; SQLite sync substrate tests `36422645669` — **SUCCESS**; Cloud backend tests `36422645686` — **SUCCESS**. A new ordinary Note upsert or delete uses the exact applied resolution event as its immediate parent and the resolution revision plus one. The frozen ordinary plaintext v1, resolution plaintext v2, crypto/AAD versions and v2 transport remain unchanged. The complete multi-parent ancestry stays in the immutable applied-resolution ledger; a read-only proof checks account, project, exact original or `keep_both` clone identity, inbox application, revision and complete parent membership before the resolution can authorize a descendant or a later sibling conflict.

Prepared, local-pending, sealed and uploaded-but-unreconciled local resolutions block ordinary continuation for both the original and the clone. Applied peer and self-echo resolutions permit it. Ordinary orphan children can be retried after their resolution parent applies; post-resolution local/remote and remote/remote siblings retain their resolution common parent and can form a second conflict/resolution generation. Production remains on v1; dormant v2 cycle is not activated. C16 remains **CLOSED**, C17 remains **IN PROGRESS**, and official WORTA progress remains **73,0%**.

Local checks before remote acceptance: Rust `note_sync` filter **141 passed** before the final corruption, rollback and orphan-sibling cases; final focused `remote_apply_tests` filter **59 passed, 0 failed, 0 skipped**; Python SQLite substrate **43 passed, 0 failed, 0 skipped**; six focused TypeScript specs **61 passed, 0 failed, 0 skipped**; Rust `cargo check`, TypeScript typecheck and `git diff --check` — **passed**. Frontend build, PostgreSQL tests and full repository suites were not run locally because no frontend or backend production code changed.

## C17 Pass 2F-D4D1 — production mode-aware Notes runtime routing

**Status: REMOTELY ACCEPTED.** Commit `afce6d2f6fc478c9881cf372f665ffa30165a07b`; Cloud backend tests run `36460407612` — **SUCCESS**. The production Notes runtime reads strict, authorized server capabilities before each new top-level cycle. Writer mode 1 selects the established v1 orchestrator; mode 2 selects the existing full v2 cycle. The result identifies the selected transport and authoritative cutover epoch while retaining the exact version-specific cycle diagnostics. The runtime keeps its auth/key lifecycle single-flight and project registry gate. Project bootstrap retains version-neutral device registration and ordinary Note sealing, selects the server mode anew for each initial ordinary upload, and routes ready and import cycles through the same transport router. A selected operation never falls back to the other transport after failure; server mode changes fail through existing mode enforcement and a later operation re-reads capabilities. No production cutover endpoint exists, no account is automatically upgraded, and D4D2 remains required for explicit one-way cutover.

Local checks: ten focused frontend spec files **116 passed, 0 failed, 0 skipped**; TypeScript typecheck, one production frontend build and `git diff --check` — **passed**. Rust, Python, PostgreSQL and full repository suites were not run because their production code did not change. Cloud backend tests is the expected remote workflow; SQLite sync substrate tests is not expected because no native or SQLite production files changed.

C16 remains **CLOSED**. C17 remains **IN PROGRESS**. Official WORTA ROADMAP SCORING v1.0 progress remains exactly **73,0%**.

## C17 Pass 2F-D4D2 — explicit one-way transport-v2 account cutover

**Status: REMOTELY ACCEPTED.** Production cutover commit `0bbdd2aa66a749a2bbafa660e46915ed83cfcc63`; follow-up CI regression fix `88d571c8f695246be0f84c0586b63644065b2a04`; Cloud backend tests run `36464914424` — **SUCCESS**, independently verified. Historical run `36463255581` — **FAILURE** only because the test called the nonexistent `/api/v1/sync/encrypted/ack` route; the follow-up changed it to the established `/api/v1/sync/ack` route without modifying production behavior.

The authenticated account-local `POST /api/v2/sync/encrypted/cutover` accepts the observed `expected_cutover_epoch` and permits only a one-way writer transition from 1 to 2. Its PostgreSQL transaction locks the same per-account sync state row as push, compares the epoch under that lock, checks the entire retained event history for v2-readable encrypted Note metadata, then advances the epoch by exactly one with safe-integer overflow protection. Incompatible history blocks the transition without rewriting events. A retry after a committed transition returns mode 2 and the current epoch without another increment, including after a lost HTTP response. The server does not require device ACKs or modify devices, cursors, projects, events, or ciphertext.

The frontend provides a strictly validated explicit cutover API method. Login, unlock, runtime retry, project bootstrap, scheduler, and UI do not call it. The D4D1 production router reads the resulting server mode on its next top-level operation. No downgrade path or migration was added. Pass 2F-E remains required for coordinated two- and three-device acceptance and any acceptance-driven hardening. C16 remains **CLOSED**; C17 remains **IN PROGRESS**; official progress remains exactly **73,0%**.

## C17 Pass 2F-E1 — coordinated two-device transport-v2 cutover acceptance

**Status: REMOTELY ACCEPTED.** Commit `9f97938f11f944837f83644fa2a9283917fa4694`; Cloud backend tests run `36467782808` — **SUCCESS**. The mandatory PostgreSQL acceptance provisions two distinct file-backed SQLite devices and registers them to one authenticated cloud account. A shared AMK crosses only the existing headless test-process crypto boundary. Production TypeScript sealing/opening and protected native inbound/apply/ACK are used; the headless crypto bridge adds only an optional ordinary-event parent. No production runtime, backend, or native sync logic changed.

Local proof: Device A's revision-1 Note is encrypted and pushed over v1; both devices durably apply and ACK it. The real account cutover advances mode 1/epoch 0 to mode 2/epoch 1, capabilities immediately agree, the historical v1 ciphertext still decrypts from v2 pull, and v1 encrypted pull is rejected. Device B uploads revision 2 over v2, retries the exact request with an immutable duplicate receipt, then A decrypts, applies, and ACKs it. Before A receives it, A's ACK remains 1 while B's is 2, locally and on PostgreSQL. Device A uploads causal revision 3; B decrypts, applies, and ACKs it. Each device also applies and ACKs its own returned event so that both independent SQLite stores have the complete causal history. A v2 ACK replay is idempotent. Reopened SQLite files converge on the final Note, head, revision, applied inbox, causal parents, and pull/ACK cursors. PostgreSQL retains exactly three monotonic opaque events, three version-1 encrypted objects, distinct registered devices and their ACK positions, and mode 2/epoch 1. This acceptance exercises ordinary causal continuation only; it does not create or resolve conflicts.

Local checks: E1 PostgreSQL acceptance **1 passed**, C15 headless and D4D2 cutover regressions **2 passed**, focused headless crypto bridge **2 passed**, TypeScript typecheck and `git diff --check` **passed**; no test skips. The Cloud backend tests mandatory PostgreSQL step includes E1 without a skip path. C16 remains **CLOSED**; C17 remains **IN PROGRESS**; official progress remains exactly **73,0%**.

## C17 Pass 2F-H1 — ordinary self-echo timestamp proof

**Status: COMMITTED LOCALLY.** Commit `dc532e5a4c5d4b1449acf7974cdd16d15b326ba3`. An accepted ordinary Note self echo was missed when the durable outbox timestamp used `Z` and authenticated plaintext used the equivalent `.000000Z` form. The outbox lookup still requires exact identity and receipt evidence; the existing frozen timestamp helper compares `updated_at` and optional `deleted_at` by instant. Invalid timestamps fail closed. Encrypted-object and inbound metadata checks remain exact. Focused ordinary self-echo tests **4 passed**; remote-apply regressions **12 passed**; `cargo check` and `git diff --check` passed.

## C17 Pass 2F-H2 — visible conflict snapshot proof

**Status: COMMITTED LOCALLY.** Commit `925679fbc4e4661a9003d014ba2b2e17981601b9`. After an accepted local self echo, authenticated causal history represents a wire Note with local payload `revision: 0`, while the visible locally edited Note can have a higher local payload revision and a different spelling of the same timestamps. That local payload revision is distinct from the exact cloud causal revision. Conflict preservation now requires identical Note field sets, exact semantic JSON equality for every substantive content/routing field, valid local revisions under source-specific rules, and semantic created/updated timestamp equality. Unrelated visible content or routing remains rejected, and delete proof still requires the Note to be absent. Focused remote-apply regressions **65 passed**; `cargo check` and `git diff --check` passed.

## C17 Pass 2F-H3 — resolution inbox timestamp proof

**Status: COMMITTED LOCALLY.** Commit `58e009bacee5ae52fcb68813f9348bebf2da0779`. Peer resolution apply and resolution self echo both previously compared the inbox `updated_at` literally with the authenticated resolution header. Both now use the existing frozen semantic timestamp helper, which rejects invalid or different instants. The verified inbox spelling is stored in the applied ledger so its existing SQLite proof guard still requires exact inbox-to-ledger equality; replay compares that ledger timestamp semantically with the authenticated header. Account, event, sequence, source, project, revision, object bytes, canonical payload, receipt, conflict-tip, dependency and result evidence remain exact. Focused resolution regressions **3 passed**, complete native remote-apply filter **68 passed**; `cargo check` and `git diff --check` passed. No schema, codec, API, crypto or transport format changed.

## C17 Pass 2F-E2 — three-device conflict and resolution acceptance

**Status: REMOTELY ACCEPTED.** Final E2 commit `d6c6dd39cb479c2dcaf560622f1eb692dcaddaf1`; Cloud backend tests run `36524589994` — **SUCCESS**; SQLite sync substrate tests run `36524590005` — **SUCCESS**. The mandatory three-device PostgreSQL acceptance uses three distinct file-backed SQLite devices and real mode-2 transport after cutover. R1 converges at revision 1. Independent B2/C2 edits are accepted as revision-2 siblings with parent R1; A, B and C preserve the exact `{B2,C2}` generation-1 conflict without silent LWW. A prepares and applies manual-merge RES with exact multi-parent set `{B2,C2}`, seals it through the production resolution-v2 path, uploads over v2, and records the exact receipt. A reconciles its self echo; B/C apply RES as peers. Each device records the durable applied-resolution ledger and ordered parent edges, resolves the conflict lifecycle and becomes ACK-eligible only after durable apply. B4 is ordinary Note plaintext v1 at revision 4 with immediate parent RES. Reopened A/B/C stores converge on B4; PostgreSQL retains the opaque five-event R1/B2/C2/RES/B4 history.

## C17 — final closure

**Status: CLOSED.** Independent acceptance verified remote HEAD `d6c6dd39cb479c2dcaf560622f1eb692dcaddaf1`; Cloud backend tests `36524589994` — **SUCCESS**; SQLite sync substrate tests `36524590005` — **SUCCESS**. These workflows include the mandatory no-skip E1 and E2 PostgreSQL acceptance.

All agreed C17 scope is complete: durable conflict preservation; frozen resolution-v2 model and focused coverage for every strategy; encrypted resolution sealing/upload; peer apply; self-echo reconciliation; orphan retry; fair mixed inbox handling; v2 pull/PUSH/ACK; production mode-aware runtime; explicit irreversible account cutover; safe causal continuation after resolution; real two-device cutover and three-device conflict/resolution acceptance; and acceptance-driven H1/H2/H3 hardening. H1 `dc532e5a4c5d4b1449acf7974cdd16d15b326ba3`, H2 `925679fbc4e4661a9003d014ba2b2e17981601b9`, and H3 `58e009bacee5ae52fcb68813f9348bebf2da0779` are in the accepted branch history and covered by the successful workflows.

The server does not choose a conflict winner and stores only opaque E2EE content. Conflict resolution has no silent LWW. Ordinary descendants after RES use RES as their immediate parent; the complete multi-parent ancestry remains in the immutable applied-resolution ledger.

**Official WORTA progress: 77,0%.** Last closed stage: **C17**. Next: **C18 Complete Project Sync — NOT STARTED**.

## C18.1 — Complete Project Sync contract freeze (локально)

**Статус: IN PROGRESS — C18.1 CONTRACT FROZEN LOCALLY.** Это design/docs-only slice после initial read-only audit; production sync C18 не реализован, remote CI этого slice не проверялся, официальный прогресс остаётся **77,0%**. Последний закрытый этап — C17; C18 как целый этап не `CLOSED`.

Основной контракт: `docs/cloud/C18_PROJECT_SYNC_DESIGN.md`. Он классифицирует текущие проектные и связанные аккаунтные данные: E2EE metadata/rename, stages/order, progress facts, все поддерживаемые Note-маршруты, карты и производные map Notes, документы, обложки, папки/membership/order, project/account game facts; локальные внешние привязки и provenance остаются на устройстве, расчётные поля восстанавливаются. Неизвестные extensions сохраняются локально и блокируют ложный статус «complete sync», пока не определён versioned codec. У каждого типа обозначены владелец, причинная история, зависимости, конфликт, tombstone и условия ACK.

Для уже подключённых C16 проектов зафиксирован отдельный durable metadata-genesis процесс. Разные локальные имена на двух устройствах — независимые кандидаты без общего аутентифицированного предка. Одновременные genesis events образуют особый migration-genesis conflict; C17 principles используются для сохранения версий и явного разрешения, но фиктивный общий parent и автоматический winner запрещены. Новые C18 entity codecs получают аутентифицированный content frame **внутри** AEAD-объекта соответствующей версии; для account entities зафиксирован отдельный domain-separated crypto/AAD namespace, а исторические Note-v1/resolution-v2 objects и frozen C11 crypto/AAD/protocol-v1 не переопределяются. Алгоритм сжатия и пакет не выбран: **EXTERNAL LICENSE VERIFICATION REQUIRED** перед добавлением зависимости. Новые account entities и frame writers требуют отдельного явного capability/writer-format gate после необратимого transport-v2 cutover; автоматического upgrade сейчас нет.

**Open implementation-blocking design blockers:** нет на уровне C18.1 контракта. Точное байтовое кодирование новых formats, численные ресурсные пределы, platform benchmark и проверка лицензий являются обязательными gates соответствующих implementation slices до активации writers. Файлы этого slice: `docs/cloud/C18_PROJECT_SYNC_DESIGN.md`, `docs/WORTA_CHECKPOINT.md`. Tests/builds: **NOT RUN — docs-only slice**. Следующий ограниченный slice: **C18.2 metadata durable substrate**, без активации UI/runtime и без самостоятельного изменения официального процента. Ожидаемые workflow после будущих production изменений: Cloud backend tests и SQLite sync substrate tests с явным расширением curated test lists/path filters. Docs-only commit этого slice не требует Actions.

## C18.2 — project metadata durable substrate

**Статус: REMOTELY ACCEPTED; C18 остаётся IN PROGRESS.** Базовые C18.1 contract-freeze `b3740613abf57e04cec06d505cae3bfa1fecb18c` и process-rule `339a3fb0bf09e6dbdad66cf0c19cb9d9803edafe` опубликованы в `origin/6.0`; принятая C18.2 implementation chain: `1a4de6eed450da46ee2c89600e0321bac31beac6`, correction `cf5d1a3264cda3351e7ebbc069ce49ddcd1215c8`. Независимо проверены **SQLite sync substrate tests run `36555551021` — SUCCESS** (Python и Rust SQLite) и **Cloud backend tests run `36555567694` — SUCCESS** (PostgreSQL cloud backend и frontend admin). Предыдущие Cloud run `36552483297` — SUCCESS и SQLite run `36552483304` — FAILURE (`2 failed, 109 passed` в Python job при успешном Rust job) остаются в истории; оба fixture regressions исправлены correction commit. Официальный прогресс остаётся **77.0%**, этап C18 не `CLOSED`.

SQLite migration `025_project_metadata_sync.sql` добавляет локальные неизменяемые кандидаты, metadata event/intent, tip set, неэкспонируемую проекцию и apply ledger. Она повторно использует generic outbox, encrypted objects, upload receipts и inbox, сохраняя Note-таблицы и историю. Native Rust capture фиксирует allowlisted снимок и исходный payload, account/project/device/bootstrap lineage и неизвестные поля как явный blocker. Повтор capture/restart сохраняет ID; изменение метаданных создаёт новое поколение. Привязка без исторического bootstrap тоже сохраняется локально с blocker `bootstrap_lineage_missing` и не допускается к публикации. Явный prepare генерирует один устойчивый genesis event/outbox ID; автоматического capture/upload нет.

Отдельный TypeScript codec v1 принимает только name, goal/infinite/unit, deadline, status, personal goal, auto-freeze, streak enablement, work method, stage enablement и combine-map setting. Его canonical JSON обёрнут в authenticated C18 frame v1 (`compression_id=0`, предел 1 MiB), затем в существующий C11 project-object AEAD. Неверные поля, контекст account/project/entity/event, формат, размер и повреждённый ciphertext отвергаются. Note-v1 и resolution-v2 codec/crypto остаются прежними. Сервер хранит только opaque project-metadata event/object и exact replay; dormant transport mode 3 имеет отдельный push/pull route, но публичного mode-3 cutover или production writer нет. Старые mode-1/2 endpoints не принимают metadata.

Native apply принимает только предварительно аутентифицированный и расшифрованный canonical payload, повторно проверяет binding, bootstrap, inbox/object, scope, revision/parents и receipt для self echo. Первый genesis без local candidate создаёт скрытую проекцию; два parentless genesis остаются отдельными tip без winner, локальный legacy candidate не заменяется remote значением. Orphan остаётся durable и повторяется после рестарта; malformed/mismatched event откатывается. Tombstone не удаляет видимый проект. Финальная выдача метаданных в UI, activation mode 3, metadata ACK-интеграция и выбор/разрешение конфликтов принадлежат C18.3.

Локальные проверки C18.2 implementation: Python SQLite migration/регрессия **45 passed**; Rust metadata **5 passed**, Rust SQLite **29 passed**, Rust Note sync **153 passed**; TypeScript metadata/Note **16 passed** и typecheck **passed**; PostgreSQL targeted metadata **2 passed**, affected v2 Note/backend **14 passed**, Alembic-head **1 passed**; Rust `cargo check`, Python syntax и `git diff --check` — **passed**. Нерелевантные полные suites не запускались. CI path filters и curated commands расширены: **Cloud backend tests** запускает PostgreSQL metadata test и TypeScript codec spec; **SQLite sync substrate tests** запускает Python migration test и Rust metadata filter.

Узкий CI regression fix удаляет из исторического v6 fixture все таблицы, индексы и triggers, добавленные SQLite migration 025, до повторного forward migration; production migration не менялась. В `test_f8_recovery.py` карта исторических migration расширена файлом `025_project_metadata_sync.sql`, сохраняя exhaustive coverage версий 1–25. Две ранее падавшие проверки прошли локально: **26 passed** (включая все версии upgrade fixture). Точный Python SQLite CI-equivalent command прошёл: **111 passed**, одно существующее предупреждение deprecation. Исправленный commit независимо подтверждён обоими workflows выше.

Следующий после принятия C18.2 slice: **C18.3.01 metadata migration runtime activation**. Историческая запись C18.2 сохраняется; результат C18.3.01 описан ниже.

## C18.3.01 — metadata migration runtime activation

**Статус: REMOTELY ACCEPTED; C18 остаётся IN PROGRESS.** Реализация начата от `cf5d1a3264cda3351e7ebbc069ce49ddcd1215c8` и опубликована как `2709e81c45dfa04a408d23a597d4506e0bab37b0`. Независимо подтверждены **Cloud backend tests run `36573282324` — SUCCESS** и **SQLite sync substrate tests run `36573282210` — SUCCESS**. Официальный зачтённый прогресс остаётся **77,0%**; C18 не `CLOSED`.

Mode 3 включается отдельным явным cutover после mode 2 и объявления reader readiness всеми зарегистрированными устройствами. Alembic revision `c18_metadata_reader_gate` хранит readiness по устройству. Обычный Note writer остаётся на строго Note-only v2 endpoint, а metadata writer использует отдельный v3 endpoint с opaque ciphertext; v3 pull переносит оба типа с точной проверкой типа и контекста. Новые Tauri-команды подключают native candidate, статус, genesis seal/receipt, durable mixed inbox, apply и ACK. Вызов explicit internal migration `begin` не происходит при login/unlock/обычном подключении проекта; повтор использует ранее сохранённые candidate/event ID. Отсутствующий bootstrap и неизвестные legacy-поля дают видимые blockers.

Production mode-3 цикл сохраняет C17 Note sealing/upload/mixed apply, затем metadata seal/upload, общий durable pull, оба applier и contiguous ACK. Ошибка mode/auth останавливает цикл; потерянный ответ upload допускает self-echo pull и точное receipt reconciliation. Metadata frame v1 расшифровывается и проверяется на клиенте, native transaction повторно проверяет scope, inbox/object и lineage. Неверное событие остаётся в inbox и блокирует ACK; валидный event атомарно получает applied evidence или durable conflict evidence. Два независимых genesis сохраняются как две tip, без автоматического winner и без замены видимого C16 имени. Status API различает candidate, missing-bootstrap/unsupported blocker, pending, awaiting confirmation, active, genesis conflict и apply blocked. Финальная UI миграции/имен и разрешение конфликтов принадлежат следующему slice.

Ограниченное metadata-only multi-device доказательство: два независимых file-backed SQLite устройства публикуют разные legacy genesis, получают собственный self echo и чужой genesis, оба сохраняют tip set и conflict после рестарта; отдельный PostgreSQL API тест подтверждает две зарегистрированные reader-ready устройства, два opaque genesis и общий pull. Это компонентное bounded доказательство, не полный end-to-end desktop сценарий и не полный project sync.

Локальные проверки: TypeScript focused + затронутые Note regressions **98 passed** в 11 spec files, typecheck **passed**; Rust metadata **8 passed**, Rust Note sync **153 passed**, `cargo check` **passed**; Python SQLite metadata/C9 **45 passed**, полный SQLite CI-equivalent Python command **111 passed**; PostgreSQL metadata/Alembic/Note-v2 targeted **28 passed**, после добавления authorization и Note-v2-in-mode-3 assertions metadata subset **3 passed**; Python syntax **passed**. `git diff --check` проверяется перед commit. CI wiring: **Cloud backend tests** включает новые v3 API/runtime/cycle spec в curated frontend tests и metadata PostgreSQL test в mandatory backend acceptance; **SQLite sync substrate tests** уже запускает metadata Rust filter и Python SQLite migration tests по соответствующим path filters. Ожидаемые workflow после публикации: **Cloud backend tests** и **SQLite sync substrate tests**. Codex не опрашивает Actions; независимая remote-проверка остаётся за GPT-чатом.

Следующий ограниченный slice: **C18.3.02 — explicit legacy metadata migration/import authority and local-shell reconciliation**, включая пользовательское решение и разрешение genesis conflict, без автоматической замены имён до выполнения frozen authority conditions.

# КОНЕЦ ЧЕКПОИНТА


## C18.3.02 — legacy metadata authority and local-shell reconciliation

**Статус: REMOTELY ACCEPTED; C18 остаётся IN PROGRESS.** Accepted SHA `9abd6dfd922b125fca4d0779138e858b8c6dd1d1`; независимо подтверждены **Cloud backend tests `36826631635` — SUCCESS** и **SQLite sync substrate tests `36826631697` — SUCCESS**. Работа этого slice была начата в worktree/ветке `6.0` от принятого HEAD и `origin/6.0` `2709e81c45dfa04a408d23a597d4506e0bab37b0`. C18.3.01 REMOTELY ACCEPTED evidence приведён выше. Официальный прогресс остаётся **77,0% (77.0%)**. Commit этого slice и published SHA указываются в отчёте публикации; checkpoint не объявляет C18 CLOSED.

Forward-only SQLite migration **026_project_metadata_authority** добавляет durable reconciliation proof и decisions ledger: исходные переносимые значения, предложенный результат, полный ожидаемый tip set, стабильный event ID и pending/applied/conflict outcome. Identity решения неизменяема; reconciliation требует существующего authenticated applied event с точным portable payload. Python/Rust schema version — **26**. Старые C16 источники, metadata candidates, immutable events и Notes сохранены. Числовые SQLite REAL значения с целой частью нормализуются для семантического сравнения и совместимости с canonical TS codec.

Native authority view различает `local_legacy_only`, `local_candidate_ready`, `local_matches_authenticated`, `local_differs_from_authenticated`, `genesis_conflict`, `metadata_conflict`, `resolution_pending`, `active`, `blocked`. Чтение UI/login/unlock/подключение проекта не запускают публикацию или решение. Первоначальная публикация вызывает существующий candidate→genesis path только явно. UI отдельно предлагает подготовку frozen mode-2 prerequisite, reader readiness каждого устройства и account mode-3 cutover; серверный all-readers gate сохранён.

При одном authenticated head пользователь может принять облачную версию без новой cloud mutation, сохранить локальную как causal update или отредактировать все 12 frozen portable полей. Adoption проверяет ожидаемые head/local values и атомарно обновляет только переносимые поля и proof. Выбор ветки/manual merge при genesis/rename conflict создаёт новый authenticated event с полным tip set; прежние ветки не удаляются. Неполный/stale tip set отклоняется. Local decision/outbox/видимые значения сохраняются одной транзакцией, повтор использует immutable pending event. Восстановление после lost response и accepted upload receipt подтверждено self echo.

Обычные native `update_project_metadata` и `update_project` после active reconciliation записывают metadata update и видимый portable результат атомарно. Проекты без metadata history сохраняют прежний локальный путь. Pending/unresolved authority не допускает скрытой конкурирующей правки. Peer descendants обновляют shell только при действующем proof и неизменившихся локальных значениях; конфликт сохраняет варианты и не выбирает по времени/серверному порядку. Локальные пути, document bindings, обложки, provenance, extensions и остальные nonportable поля сохраняются. UI уведомляет открытые списки проектов о durable metadata изменениях.

Для явного второго импорта runtime до создания shell читает ограниченную полную account history, открывает E2EE frames, проверяет codec, descriptors, bootstrap lineage, dependencies и полный resolution tip set. Единственный authenticated head задаёт portable shell; при конфликте используется нейтральная оболочка с project ID без выбора ветки. Существующая отличающаяся shell не перезаписывается; без cloud metadata остаётся обязательное локальное название и отдельная первоначальная migration decision. Native constructor сохраняет C16 collision/binding guards. UTC server descriptors канонизируются на inbox boundary; opaque nonce/ciphertext не меняются.

Пользовательская панель в cloud settings показывает local values, каждую authenticated ветку и её immutable event identity, локальную candidate-ветку, state/blockers, явные publish/adopt/keep-local/manual-resolution/retry действия. Добавлен bounded editor 12 полей. Справка дополнена без изменения первого раздела «Быстрый старт». **36 новых ключей** переведены локальными overrides на en/es/de/fr/pt_BR; штатные catalog/export generators выполнены с **0 missing strings** и без внешней передачи. Сравнение существующих каталогов: **0 изменённых старых переводов**.

Локальные проверки (без remote Actions polling):

- Final focused authority UI/store/runtime/native-adapter group — **56 passed**, включая store import без придуманного локального имени; Chromium/Playwright production Vue fixture — **passed**: no automatic decision, обе ветки видны, exact full-tip branch choice, редактор 12 полей. Это проверка браузерного компонента с isolated fixtures, не graphical Tauri E2E.
- Curated Cloud frontend primary pass — **342 passed**, один existing admin test столкнулся с Node 25 global WebStorage; affected admin/transport retry с `NODE_OPTIONS=--no-experimental-webstorage` — **53 passed**, включая **5 admin** и **48 transport/metadata**. Последующие изменённые authority specs повторно проверены focused group выше; unrelated production/admin code не менялся.
- Rust metadata — **13 passed**: genesis/rename resolution, complete parents, restart/replay, rollback, device-only retention, accepted receipt/lost response, peer apply. Rust Note regressions — **153 passed**; Rust SQLite — **29 passed**. `cargo check` — **passed**, только существующие warnings.
- SQLite workflow-equivalent curated Python/API command — **112 passed**, 0 skipped. Legacy settings fallback изолирован в temporary data context; пользовательская база не использовалась. После добавления reconciliation guards focused metadata/application-metadata — **8 passed**.
- Localization/help native macOS Qt checks — **30 passed**. Offscreen native Help bridge не поддерживается; успешный pass выполнен через cocoa runtime. Python syntax affected files — **passed**.
- Targeted PostgreSQL metadata/C16/Note ACK pass — **17 passed**, 0 skipped. Включён production TS E2EE → PostgreSQL opaque events → file-backed SQLite bridge на **трёх устройствах**: explicit legacy genesis, authenticated import, pre-existing differing shell + keep-local causal update, concurrent Beta/Gamma renames, full-tip resolution, reopen/replay и convergence. Финальный повтор после SQL proof guards — **1 passed**. Disposable PostgreSQL 16 `worta-c18302-postgres`, host port 55436, no volume; остановлен и удалён до публикации. Собственные Run Web/backend/Vite процессы остановлены.
- TypeScript typecheck, frontend production build, YAML/curated wiring audit и `git diff --check` — **passed**. User `engine`/`game_data` `.pyc` не менялись и не входят в commit.

CI wiring: Cloud backend paths покрывают новые UI/runtime/native/SQLite файлы; curated frontend commands явно включают `ProjectMetadataAuthorityPanel.spec.ts` и `projectMetadataMigrationRepository.spec.ts`; mandatory PostgreSQL command явно включает `test_cloud_c18_authority_cross_runtime.py` с no-skips guard. SQLite workflow выполняет migration tests и Rust `project_metadata_` filter. Ожидаются **Cloud backend tests** и **SQLite sync substrate tests**. После разрешённого commit выполняется обычный `git push origin 6.0`; Actions независимо проверит GPT-чат.

Ограничения: import preview ограничен **16 страницами** account history и при превышении/неполной lineage блокируется; конфликт/изменение tip set во время resolution требует нового безопасного согласования, без автоматического победителя. Windows native runner и graphical Tauri E2E локально не выполнялись. Полная синхронизация проекта не заявляется; stages/maps/documents/progress/catalog/covers/game остаются за границей slice. Следующий bounded slice после независимого принятия: **C18.3.03 — metadata import/reconciliation edge acceptance**, включая large-history continuation и additional tip arrival during pending resolution; C18.4 не начинать автоматически.


## C18.3.03 — metadata import / reconciliation edge acceptance

**Статус: REMOTELY ACCEPTED; C18 остаётся IN PROGRESS.** Accepted SHA `055494f429256df193030b8bbbe41c906bcbe8cc`; независимо подтверждены **SQLite sync substrate tests `36831673946` — SUCCESS** и **Cloud backend tests `36831673941` — SUCCESS**. Исторический preflight: baseline текущего worktree/ветки `6.0`: HEAD и `origin/6.0` `9abd6dfd922b125fca4d0779138e858b8c6dd1d1`, worktree был чист. C18.3.02 remote acceptance записана выше. Официальный прогресс **77,0% (77.0%)**, C18 не CLOSED. Scope ограничен metadata; C18.4 и новые entity types не начаты.

Forward-only SQLite **027_metadata_edge_continuation** хранит account/project/bootstrap-scoped import cursor, running/complete/blocked state, проверенные canonical events, causal tips, immutable page identities и immutable invalidation evidence. До полного чтения не создаёт project shell/binding, не меняет sync pull/ACK cursor и не выдаёт authenticated head. Подтверждённые страницы коммитятся вместе с cursor/tips/counters; exact page replay идемпотентен, altered replay и cursor regression отвергаются. При restart чтение продолжает сохранённый prefix. Пустой terminal read не занимает cursor receipt: последующие события можно дочитать. Обновление account history между preview и shell construction требует нового explicit continuation, без создания shell по устаревшему preview.

Resource bounds: **200 generic v3 events/page**, **16 pages/explicit attempt**, **3 200 metadata events/import**, **16 MiB accumulated canonical payload**, прежний codec/frame maximum **1 MiB payload + 20-byte frame** и существующий AEAD/transport budget. 3 200 — прежний 16×200 event budget; 16 MiB — существующий v3 batch budget. Теперь число account-history страниц не ограничено terminal 16-page cutoff: очередное действие продолжает cursor. В памяти только bounded current page и текущие tip IDs; вся metadata history хранится в SQLite. При resource limit проверенный prefix остаётся на диске, возвращается `metadata_import_resource_limit`, head/metadata скрыты. История не усекается; автоматических retry loops нет.

Resolution race: изменение exact tip set переводит pending resolution decision в durable **conflict**, добавляя immutable `tip_set_changed` evidence. Original source/proposed/tips/event identity и sealed bytes сохраняются. Unsealed/sealed invalidated events исключены из writer lists; seal после invalidation отвергается. Если server уже принял event или response потерян, authenticated self echo сохраняет его как **conflict_preserved** historical branch, с receipt/ledger/inbox proof для безопасного ACK. Stale R(A,B) покрывает только A/B: uncovered C остаётся tip, causally correct equivalent — **{R,C}**, независимо от порядка R/C, timestamp или server sequence. R не переписывается и не становится authoritative при retry/restart. Новое explicit R2 строится по полному текущему sorted tip set. Metadata outbox допускает replacement resolution той же causal revision; существующие Note/other-entity uniqueness rules сохранены, metadata ограничены одним pending decision/project.

Full-tip validation: exact expected current tips CAS при authoring; полный canonical scope/account/project/bootstrap/entity, известные authenticated parents, `revision=max(parent revisions)+1`, generation выше всех causal parents, immutable event replay. Unknown parent остаётся orphan/ACK-blocking. Subset resolution сохраняет immutable causal history, но не создаёт authority или projection поверх uncovered tip. Только full-tip apply создаёт reconciliation proof. Remote full resolution применяет portable fields поверх неизменённого reconciliation либо покрытого authenticated local edit, сохраняя device-local fields и несогласованное ручное расхождение.

Acceptance: production TS E2EE → real PostgreSQL opaque transport → **четыре file-backed SQLite devices**. История из **23 events**, test page size **1** пересекает старую границу 16 страниц: 18-event baseline, A/B/C siblings, stale accepted R(A,B), explicit R2(R,C). Все A/B/C сходятся; fresh D импортирует историю с duplicate page, reopen после каждой страницы и identical final authority/history. На page 16 нет head/metadata; до полного чтения нет shell/pull/ACK movement. Сервер остаётся opaque и принимает stale R как immutable object без semantic winner.

Локальные проверки:

- TS/UI/runtime/native-adapter affected group — **75 passed**. После добавления arrival-order/duplicate/generation и shell-construction-race cases affected runtime — **9 passed**, bootstrap — **12 passed**; всего проверены **77 distinct current tests**, broad group не повторялся. TypeScript typecheck и production frontend build — **passed**.
- Native metadata filter — **15 passed**, включая пять durable timing cases/reopen, exact-tip recovery, preserved stale self echo, ACK, 35-page import/replay, missing dependency rollback и resource blocker. После уточнения обратного server-order timing и ограничения ancestry traversal только resolution path affected timing/peer tests — **1 + 1 passed**. Rust Note regressions — **153 passed**; Rust SQLite — **29 passed**; `cargo check` — **passed** с существующими warnings.
- SQLite CI-equivalent curated Python/API command — **113 passed / 1 fixture failure**: fixture исключал новые metadata triggers по принятому prefix. Новые triggers приведены к `cloud_sync_metadata_`; только affected C17 populated-upgrade test повторён — **1 passed**. Все **114 curated tests** покрыты успешными результатами. Focused metadata/application metadata — **9 passed**. Test data/settings fallback изолированы; пользовательская база не использовалась.
- Targeted PostgreSQL new edge acceptance — **1 passed**, 0 skipped; final affected acceptance после добавления явных shell/pull/ACK assertions — **1 passed**, 0 skipped. C18 metadata/authority, C16 bootstrap/import и Note transport/ACK regressions — **11 passed**, 0 skipped.
- Help/localization native macOS cocoa checks — **30 passed**; стандартные generators completed с **0 missing translations** во всех пяти языках. Добавлены 4 локализованных source keys; старые locale entries не изменены. Chromium production Vue fixture — **passed**: no action on form open, explicit continuation retry, preserved-progress resource blocker. Это browser component proof, не graphical Tauri E2E.

CI wiring: mandatory Cloud PostgreSQL command явно включает `test_cloud_c18_edges_cross_runtime.py`, no-skips guard сохранён; существующие curated TS commands уже выполняют все изменённые runtime/adapter/bootstrap/store/UI specs. Cloud path filters покрывают новые files. Windows Rust SQLite job выполняет `project_metadata_`: обе новые native edge tests включены этим именованием, без новой Windows архитектуры. Existing headless bridge расширен двумя import commands; graphical Windows/Tauri E2E остаётся later release-hardening coverage и не заявляется выполненным локально.

Перед публикацией выполнены complete diff review, `git diff --check`, syntax/CI wiring audit. Собственные Run Web/backend/Vite процессы остановлены; disposable PostgreSQL `worta-c18303-postgres` остановлен и удалён (no volumes). HEAD и fetched `origin/6.0` сохранили baseline. User `engine`/`game_data` `.pyc` не менялись. После единственного разрешённого implementation commit Codex выполняет `git push origin 6.0` и завершает с **REMOTE CI PENDING**, без Actions polling. Ожидаются **Cloud backend tests** и **SQLite sync substrate tests**; независимая remote проверка — GPT-чат.

Оставшиеся ограничения: deliberate import safety caps 3 200 events/16 MiB требуют отдельного явного решения при превышении; incomplete/unknown lineage остаётся blocker. Windows native проверяется remote job, graphical Tauri E2E отложен до release hardening. Complete-project sync не заявляется. Следующий bounded slice после независимого принятия: **C18.3.04 — metadata integration acceptance review / release-hardening disposition** по отдельному prompt, без автоматического начала C18.4.


## C18.3.04 — metadata integration acceptance review

**C18.3 METADATA MIGRATION / INTEGRATION — COMPLETE / REMOTELY ACCEPTED.** Accepted SHA: 5619ba4c839947952ac4fb11d9615ee9c2591c23. Независимые evidence предоставлены пользователем: **SQLite sync substrate tests 36882012844 — SUCCESS**. Initial **Cloud backend tests 36882012768**: Frontend admin — SUCCESS; PostgreSQL cloud backend — CANCELLED по job-level 30-minute timeout, assertion/test failure не установлен. **One-shot rerun на том же SHA 36886696888 — SUCCESS**. Отдельных roadmap points для C18.3 нет. **C18 Complete Project Sync — IN PROGRESS; official progress 77.0% (77,0%)**. Ниже сохранён исторический локальный отчёт .04; новое продолжение C18.4.01 приведено в следующем разделе. Codex Actions не опрашивал.

Preflight: `/Users/romankisockin/Desktop/nfprogress/ts_migration`, branch `6.0`, HEAD и local `origin/6.0` `055494f429256df193030b8bbbe41c906bcbe8cc`, clean worktree. C18.3.03 **REMOTELY ACCEPTED** по предоставленным пользователем runs `36831673946` / `36831673941` — SUCCESS; Codex Actions не опрашивал. Проверены frozen C18 design и production TS codec/runtime/store/Vue → SQLite adapter → registered Tauri commands → native transaction/ACK paths, migrations 025–027 и curated CI commands.

### Acceptance matrix

`PROVEN BY REMOTE CI` ниже относится к принятому baseline и указанным пользователем двум runs, а не к ещё не проверенной публикации .04. `PROVEN LOCALLY / CI-COVERED` относится к новым/расширенным proofs, включённым существующими CI commands. Незакрытых `GAP` после bounded proof additions нет.

| Contract row | Classification | Objective evidence |
| --- | --- | --- |
| A. Legacy C16 explicit migration; stable candidate/genesis IDs; restart before publication | PROVEN BY REMOTE CI | Rust `project_metadata_candidate_is_durable_and_reused`, `project_metadata_legacy_binding_without_bootstrap_is_preserved_but_not_publishable`; runtime explicit mode/begin test; PostgreSQL `test_metadata_migration_import_mismatch_and_concurrent_rename`. |
| A. Lost upload response, immutable retry, self echo, authenticated active state | PROVEN BY REMOTE CI | Rust `project_metadata_lost_upload_response_self_echo_is_durable_and_ack_safe`; runtime seals-once/retries-same-event; three-device authority acceptance with receipt/ledger/reopen. |
| B. Fresh authenticated second-device shell and existing differing shell; explicit adopt/keep/manual, no invented authority | PROVEN BY REMOTE CI | PostgreSQL authority acceptance, bootstrap/runtime/store import specs; Rust explicit adoption and peer-descendant tests. |
| C. Rename, causal parent, upload, peer apply, restart/exact replay | PROVEN BY REMOTE CI | PostgreSQL authority acceptance Beta/Gamma updates, Rust concurrent rename/peer descendant/replay, production crypto bridge. |
| C. All 12 fields together; fractional and integral numeric normalization; device-local retention; durable normal edit before upload | PROVEN LOCALLY / CI-COVERED | New Rust `project_metadata_acceptance_all_fields_peer_apply_rollback_and_restart`: full peer payload, all-field normal edit, exact causal parent, stable pending ID after reopen, private path/cover/extensions/Note retention. TS strict codec round trip remains CI-covered. |
| D. Concurrent genesis and updates; full-tip resolution, stale R, additional C while R pending; explicit R2 and convergence | PROVEN BY REMOTE CI | Rust genesis/concurrent rename and `project_metadata_edge_resolution_invalidation_all_durable_timings`; PostgreSQL `test_metadata_large_import_and_additional_tip_resolution`; runtime stale subset resolution in both arrival orders. |
| E. Beyond 16 pages, page restart/exact duplicate, incomplete lineage, event cap, final import | PROVEN BY REMOTE CI | Rust 35-page durable import; PostgreSQL four-device 23-event/limit-1 history and fresh D import; runtime continuation/lost persistence response and bootstrap high-water race. |
| E. 16 MiB cap and blocked restart preserve prefix without authority/cursor movement | PROVEN LOCALLY / CI-COVERED | New Rust `project_metadata_acceptance_import_byte_cap_preserves_prefix_on_restart`; aggregate is seeded at the boundary to keep fixture bounded, next valid causal event invokes production cap check. |
| F. Wrong account/project/entity/event context; tampered ciphertext; opaque backend and invalid mode/type pairing | PROVEN BY REMOTE CI | TS `projectMetadataCodec.spec.ts` AEAD negatives for all four scopes + tamper; PostgreSQL `test_cloud_c18_metadata.py` schema/opaque replay/all-readers strict pairing; Rust malformed/orphan rollback. |
| F. Frame/codec versions and compression flags; native account/project/bootstrap/event scope, foreign parent and resolution/adoption/candidate/import guards | PROVEN LOCALLY / CI-COVERED | Expanded codec frame positions 8–11; new Rust `project_metadata_acceptance_scope_isolation_and_foreign_parent`; native user/device scope checks and project/account-scoped parent lookup. |
| G. Outbox/receipt/inbox/apply/reconciliation/conflict evidence and continuation | PROVEN BY REMOTE CI | Native immutable ledgers, self echo/receipt proofs, five stale-resolution timing cases, page receipts and reopen; migrations 025–027 guards. |
| G. Failure during visible peer apply/proof commit; durable inbox restart; mixed Note/metadata contiguous ACK and tombstone replay | PROVEN LOCALLY / CI-COVERED | New full-field rollback test aborts reconciliation UPDATE after visible write and confirms rollback of authority, retained received inbox and ACK=1; reopened retry applies and ACK=2. New tombstone/mixed-ACK test preserves Notes and blocks at intervening received Note. |
| H. Note v1/v2, C17 conflict/resolution, C16 bindings/bootstrap and local-only behavior | PROVEN BY REMOTE CI | Accepted mandatory PostgreSQL C15/C16/C17/Note suites; Rust Note filter and Python populated C17 upgrade fixtures; store no auto connect/login/unlock migration tests. Rechecked locally below. |
| H. Populated C18.2/3 intermediate upgrade 25/26→27 preserves candidate/event/tips/reconciliation/pending decisions and Notes | PROVEN LOCALLY / CI-COVERED | New two-version `test_metadata_populated_intermediate_upgrade_preserves_exact_evidence` compares exact rows, foreign keys and repeated migration. Existing `test_each_supported_sqlite_schema_upgrades_to_latest` covers all 27 historical versions; fresh 0→27 and populated 24→27 tests retained. |
| UI. Production publish/adopt/manual/branch choice, no action on open/login/unlock, import continuation and visible errors | PROVEN BY REMOTE CI | Existing panel/store/runtime/adapter tests; registered native commands inspected; .03 Chromium explicit continuation/resource blocker evidence. |
| UI. Keep-local, pending retry/error/recovery and manual full-tip conflict submission | PROVEN LOCALLY / CI-COVERED | Three new `ProjectMetadataAuthorityPanel.spec.ts` cases invoke actual component actions with exact store arguments and visible alert. |
| Full graphical Tauri E2E | INTENTIONALLY DEFERRED | C22 Production Hardening / release hardening. Rust transactions, production crypto + PostgreSQL/file-backed SQLite bridges, runtime/store/component tests and accepted Windows Rust CI prove business/security logic below graphical shell. No new harness needed for metadata acceptance. |
| Destructive project-delete finalization/cleanup | INTENTIONALLY DEFERRED | Later C18 complete-project deletion work must prove complete child manifest/tombstones, dependencies, conflict resolution and retention policy. Current metadata tombstone only preserves causal deletion intent/history. |

### Findings and bounded changes

- **P0: none found. P1: none found.** No production behavior, field list, migration, backend, dependency, localization or workflow changed.
- **P2: resolved locally / CI-covered.** Added full-field native apply/edit/rollback proof; scope/foreign-parent negatives; tombstone/contents/shared ACK proof; byte-cap restart proof; populated 25/26 upgrade preservation; unsupported frame versions; missing explicit keep/retry/manual-resolution component wiring assertions. Changes live exclusively in test specs, Python tests and Rust `#[cfg(test)]` helpers/tests.
- Initial new-fixture failures: missing project_order in upgrade fixture and bound Note insertion without intent. Fixed fixtures by populating project_order and creating local Note before cloud binding; successful focused reruns and subsequent curated pass recorded below. No production failure was reproduced.

### Accepted boundaries and integration audit

**Resource-cap decision — ACCEPTED:** 200 generic events/page, 16 pages/explicit processing attempt, 3,200 metadata events and 16 MiB accumulated canonical metadata. Sixteen pages is a continuation bound: another explicit attempt resumes durable account-history cursor. The total reconstruction caps are an explicit supported resource boundary; exceeding either produces `metadata_import_resource_limit`, keeps verified prefix/events/tips, hides head/metadata, preserves local contents, and requires a future explicit resource-handling decision. Repeated retries remain blocked; automatic retry loops, silent truncation/deletion and partial shell authority are absent. Limits unchanged.

**UI/commands:** actual panel actions call `cloudSession.beginMetadataMigration`, `adoptMetadata`, `decideMetadata`, `retry`; store calls `NoteSyncRuntime` explicit methods and refreshes authority. Runtime requires unlocked/current user/device/key lease and mode 3, then calls `ProjectMetadataMigrationRuntime` and `SQLiteProjectMetadataMigrationRepository`. Adapter invokes production commands registered in `lib.rs`; `metadata_connection` validates native account/user/device. Import form submits the production bootstrap/import path, catches continuation/resource blockers and offers explicit retry. Test bridge commands are absent from production wiring. Inspection/mount/open/login/unlock never call begin/adopt/decide automatically. Existing generic errors and typed blockers remain visible; no text/help behavior changed.

**Portable-field contract:** exact fields are `name`, `goal`, `infinite`, `unit`, `deadline`, `status`, `personal_goal`, `auto_freeze`, `streak_enabled`, `work_method`, `stages_enabled`, `combine_stage_mindmaps`. TS codec, Rust allowlist/capture/visible reader/writer and editor agree. SQLite authoritative columns name/goal/infinite/unit/status agree with the updated compatibility payload; the payload retains other keys. Integral SQLite REAL values normalize to integer JSON; fractional goals survive. Apply requires authenticated scoped causal event and existing reconciliation proof/CAS; device paths, Word/Scrivener bindings, covers, extensions and child content stay local. Unknown legacy extensions preserve raw candidate and block publication.

**Tombstone/delete:** native apply records metadata tombstone/projection/ledger/tips but skips visible metadata write for delete. Runtime fresh import of a sole deleted head rejects with `metadata_import_deleted`. Visible project and children survive restart and exact replay. Metadata history ACK proves durable preservation of deletion intent; it authorizes no destructive complete-project cleanup. Complete-project delete UI/finalization requires the later manifest/dependency contract in frozen design §§6–7.

**Isolation/ACK:** all event, tip, proof, decision and continuation queries scope by account/project; candidate retrieval also scopes device and bootstrap. Cross-project parent lookup cannot borrow another project's event. AEAD context and inner header/outer descriptor are checked before native mutation. Native runtime additionally checks canonical user/device binding. Shared ACK reads only the contiguous account sequence prefix; metadata requires matching durable event + apply ledger, outcome and server sequence. Received/malformed/orphan events cannot unlock ACK. Conflict-preserved stale R has durable receipt/ledger proof but cannot remove uncovered C or choose a winner. Import cursor is separate from pull/ACK and cannot construct authority until complete. Migration and ordinary sync cursor guards remain forward-only.

**Upgrade/failure review:** fresh and every supported historical schema upgrade to 27; populated C16/C17 fixtures preserve inbox/conflict/resolution/receipts, and new populated 25/26 tests preserve metadata rows exactly. Current continuation is tested across reopen/idempotent migration and retained pages. Representative failures use existing infrastructure: adoption/decision-trigger rollback; peer visible apply/reconciliation-trigger rollback; durable event/outbox before upload; lost upload reply/self echo; persisted received inbox before retry; five stale pending resolution timings/restart; each import page reopened and exact lost-reply replay. Every case resumes or exposes a durable blocker, with no partial visible authority. No C23 disaster framework introduced.

**No-regression audit:** local-only has no cloud binding/event backfill, native edit without metadata history keeps local behavior, connect/login/unlock cannot publish legacy metadata. Timestamp, server sequence, upload order and device ID are descriptors/identities rather than conflict winner rules: accepted concurrent/stale arrival-order tests preserve all causal maxima. Unknown extensions block; external file paths are outside the frozen metadata allowlist. Old Note v1/v2 codec and crypto fixtures remain readable; no Note protocol or C17 ACK architecture changed.

### Exact local checks for .04

- New Rust focused tests: initial **3 passed**, then metadata filter **18 passed**, final expanded focused acceptance filter **4 passed**. Thus all **19 current metadata tests** have successful results; overlapping runs are not counted as distinct tests.
- Rust Note regressions **153 passed**; Rust SQLite **29 passed**. `cargo check` **PASS**, existing warnings only.
- TS/runtime/store/UI/native-adapter/bootstrap/v3 cycle: **78 passed / 9 files**; after three wiring additions affected panel **16 passed / 1 file**. All **81 distinct current cases** have successful results. TypeScript typecheck **PASS**, including final wiring additions. Frontend production build **not rerun**: no frontend production change; accepted .03 build remains baseline evidence.
- Python SQLite/API workflow-equivalent six-file curated pass **116 passed, 0 skipped**, includes all 27 historical upgrade fixtures and both new populated versions. Earlier targeted selection: **30 passed / 2 new-fixture failures**, affected fixture rerun **2 passed**; final curated pass is fully green.
- Python affected syntax parsed without writing bytecode. All data/settings isolated in temporary test contexts. Protected user `.pyc` untouched.
- PostgreSQL **not rerun**: no backend/crypto/runtime production change; .03 independently accepted Cloud run includes mandatory real PostgreSQL metadata/authority/edge and C16/C17/Note acceptance. This is prior accepted evidence, not a new local PG run.
- Full diff review and `git diff --check` **PASS**; no C18.4 implementation, no unrelated files, official progress unchanged.

**CI wiring:** Cloud filters include changed frontend specs/native metadata module; curated Vitest commands name both changed specs and mandatory PostgreSQL acceptance remains unchanged. SQLite filters include native metadata and `test_c18_metadata_sqlite.py`; Windows `project_metadata_` filter includes all four new Rust tests, Python curated command includes both new upgrade cases. Expected **Cloud backend tests** and **SQLite sync substrate tests**. Publish one `test(c18): close metadata integration acceptance` commit with autonomous `git push origin 6.0`; afterward only remote-ref/status verification, no Actions wait/poll. New tests remain **REMOTE CI PENDING** for GPT independent acceptance.

**Closure decision:** required metadata authority paths have objective accepted or local/CI-covered evidence; no unresolved P0/P1/P2 remains. C18.3 is COMPLETE under explicit slice closure authorization. Remaining risks/boundaries: supported reconstruction caps, incomplete/unknown lineage durable blockers, full graphical Tauri E2E at C22 and complete-project deletion/content work in later C18. C18 itself stays **IN PROGRESS**, official **77.0%**. Recommended next bounded slice after independent acceptance: **C18.4.01 — STRUCTURAL ENTITY SUBSTRATE / DEPENDENCY ORDER** (stages, stage order, dependency-safe structural apply and tombstone/dependency rules); implementation requires its own task scope.

## C18.4.01 — Stage structural substrate / dependency order

**C18 IN PROGRESS — C18.4.01 REMOTELY ACCEPTED. Official progress exactly 77.0% (77,0%).** Independent acceptance evidence for implementation/correction is recorded below; local implementation evidence remains historical. C18.3 COMPLETE / REMOTELY ACCEPTED, evidence записаны выше; C18 не CLOSED. Scope только project-scoped Stage и Stage-order. Account catalog, account-object crypto/AAD v2, C18.5 content/action entities и destructive complete-project cleanup не реализованы.

Preflight: pwd=/Users/romankisockin/Desktop/nfprogress/ts_migration; branch 6.0; HEAD и origin/6.0 — 5619ba4c839947952ac4fb11d9615ee9c2591c23; git status --short пуст. Protected __pycache__/engine.cpython-312.pyc и __pycache__/game_data.cpython-312.pyc не изменялись и не включаются в commit. Reset/clean/destructive restore не использовались.

### Exact Stage portable allowlist and ownership audit

Stage — canonical A, stable stage_id within authenticated account/project. SQLite stages.id — Stage.stage_id, stages.project_id — owning project, не унаследованный внутренний Stage.project_id. Codec v1 содержит **ровно 12 полей**, typed allowlist без blind payload serialization:

| Portable key | Type / bounds | Legacy owner / SQLite representation |
| --- | --- | --- |
| name | nonempty Unicode-scalar UTF-8 string ≤512 bytes | Stage._name / stages.name |
| goal | null or finite nonnegative number ≤9007199254740991 | Stage._goal in selected unit / stages.goal |
| infinite | boolean | infinite goal projection / stages.infinite |
| unit | nonempty string ≤512 bytes | Stage.unit / stages.unit |
| status | nonempty string ≤512 bytes | Stage._status / stages.status |
| deadline | null or nonempty string ≤512 bytes | Stage._deadline, no deadline normalized to null / payload |
| personal_goal | finite nonnegative number ≤9007199254740991 | personal_goal_for_the_day / payload |
| auto_freeze | boolean | Stage.auto_freeze / payload |
| streak_enabled | boolean | enable preference (streak_status != Off), no streak-history authority / payload |
| work_method | nonempty string ≤512 bytes | portable preference / payload; external binding never included |
| created_at | null or nonempty historical string ≤512 bytes | create_date / stages.created_at |
| completed_at | null or nonempty historical string ≤512 bytes | complete_date / payload |

Historical dates never select a winner. Strings are user data and are not translated. Bounds are explicit v1 admission limits: invalid legacy values retain raw source with invalid_stage_portable_fields, never truncation. Column/payload contradictions produce stage_column_payload_mismatch:<key>; wrong ID produces stage_identity_mismatch. Unknown source keys and nonempty stage project_extensions block publication. Malformed inherited nested-stage/cover/folder values produce unsupported_stage_legacy_field:<key> rather than invented portability.

Ownership audit: engine.Stage and inherited Project constructor/migrate; serializer _serialize_entity(kind=stage); SQLite mirror _entity_row/_extension_row/_binding_rows; Rust StageRecord and existing Stage editor. Exclusions retain their local sources:

- **D:** parent_project_name rebuilt from current owning project name; total/progress/remaining/added_today/today_goal/planning_date/plan_daily_goal/project_plan. deadline_set_date is used only as a planning-cache signature invalidator in get_today_goal_value(), not an independent portable choice. No competing cloud writer.
- **C:** synch/last_synch, filesystem paths/source IDs/diagnostics in project_bindings, sync_available, migration/application/device provenance. edit_date/updated_at are evidence, not precedence.
- **A/B in later content/action slices:** progress records/order; Stage Notes; mindmap and child timestamps; game transition/streak/freezes facts and projections, including last_streak_bonus, last_streak_lost_date, streaks and max_streak. Existing child rows/game state/historical sources remain intact. A structural event does not claim these children synchronized.
- **Type/structural markers:** is_stage, inherited project_id, forced false enable_stages/combine_stage_mindmaps, empty stages and Stage-inapplicable cover/folder fields are not independent Stage authorities. Constructor/migration/serializer enforce those constants; malformed persisted non-default values block publication.
- **F:** unknown/unadmitted extensions retain exact raw payload and extension contents in immutable candidate recovery source. No silent omission and no complete-project migration claim.

Shared stageCodecV1.json fixture and Python/Rust/TypeScript tests prove agreement between model projection, SQLite capture, native validation and TS codec on all twelve fields and canonical bytes. Numeric golden vectors include integer/fractional normalization, decimal/scientific notation and subnormals. Native UTF-16 key ordering agrees with TypeScript. Unknown root/header/payload keys, duplicate keys/noncanonical JSON, unsupported frame flags/versions and mismatched lengths/kinds fail closed.

Frame: existing **C18 frame v1**, 20-byte header, WORTA-C1 magic, **codec_id=2 Stage / codec_id=3 Stage-order, entity_codec_version=1, compression_id=0**. Equal declared raw/payload lengths; canonical deterministic JSON ≤1 MiB. Order ≤4096 IDs and ≤64 sorted unique dependency tips per Stage. **C11 project-object crypto_version=1 / aad_version=1** unchanged, entityType=stage|stage_order. Inner account/project/entity/type/event duplication binds authenticated outer context; native checks bootstrap/device/revision/operation/timestamps against exact inbox and nonce/ciphertext. Historical Note crypto/v1/v2 and metadata codec bytes unchanged; existing pure helper visibility is the only metadata implementation change.

### Durable substrate and internal activation boundary

Forward-only **028_stage_structural_sync.sql**, Python/Rust schema **28**. Earlier migrations untouched. New bounded project-structural tables: cloud_sync_stage_candidates, cloud_sync_structural_events, cloud_sync_structural_tips, cloud_sync_structural_projection, cloud_sync_structural_apply_ledger. Immutable frames, causal parent/metadata dependency, revisions/generations, tips, retained candidates and ledger provide conflict/history evidence. Immutable candidate/event/ledger/object guards. Generic C17/C18 inbox/outbox/objects/upload receipts reused; no duplicated generic transport or universal account abstraction.

Internal capture_candidate requires a connected project with reconciled active metadata authority. Candidate stores Stage ID, account/project/device/bootstrap lineage, metadata dependency, portable snapshot, exact raw payload/extensions and typed blockers. Restart reuses ID when snapshot/raw source/blockers/metadata head agree; otherwise deterministic max-generation+1 preserves the old source. Capture changes neither visible Stage nor outbox. No automatic publication.

Internal prepare/seal require exact expected tips, current candidate/portable values without blockers, metadata proof and causal revision. Exact prepare/seal retry reuses original event/frame/ciphertext, including after apply; duplicate pending writers for one entity are rejected. No automatic capture/publication on login/unlock/sync/mode cutover/UI opening. Crate-internal APIs are exercised through the existing test-only headless bridge; no new production Tauri command, UI or background structural writer is activated. Future integration needs explicit migration decisions, full-tip resolution and reader-format readiness before broad activation.

Stage native apply repeats strict frame/codec, authenticated account/project/bootstrap/entity/event/device scope, inbox descriptor, exact immutable object, metadata authority, parent scope and revision/generation checks in **BEGIN IMMEDIATE**. Ordinary apply updates portable fields only, preserves local-only/child payload, derives parent name and atomically writes tips/projection/ledger/inbox/ACK evidence plus exact self-echo receipt/outbox reconciliation. New Stage receives compatibility placement in local stage_order to maintain existing order invariants; this is explicitly not authenticated Stage-order authority. A separate authenticated permutation replaces it. Rollback injection proves no partial visible/head/ledger/ACK mutation. Untracked distinct local Stage values become retained candidate conflict evidence.

Missing binding/project/metadata head, unresolved genesis/metadata authority, unreconciled local shell or scope mismatch cannot authorize Stage. Missing parents/project are never fabricated. Exact replay is idempotent; complete concurrent rename/edit branches survive. Conflict clears authenticated projection while keeping local presentation and full branch/candidate evidence. Timestamp, transport sequence, device ID and arrival order never choose a winner.

**Tombstone guard:** immutable authenticated Stage tombstone and causal tip are retained, including delete/edit conflict. State tombstone_blocked and deterministic stage_tombstone_child_manifest_incomplete block visible cleanup, apply ledger and ACK. Even apparently empty Stage may have unknown C18.5 children; this slice admits no complete child-manifest proof. No Notes/maps/documents/progress/game references are erased; order removal is not inferred. No complete-project cleanup/retention policy invented.

**Stage-order contract:** separate canonical A, identity (project_id, stage_order). Exact ordered list plus per-Stage authenticated full current tip-set proof. No duplicate, foreign, unknown/unproven or omitted live Stage. All-live edit conflicts can prove membership when every tip is referenced; any tombstone branch blocks membership because child proof is incomplete. Native membership/head CAS, causal parent/revision, full permutation/head/ledger/inbox mutation are atomic. Concurrent full permutations remain separate conflict versions, without sorting/merge. Removal without valid tombstone/child proof stays blocked. Explicit full-tip conflict resolution belongs to next integration slice.

### Orphan, ACK and opaque transport

Existing mode-3 allowlist adds only stage and stage_order. Backend validates authenticated account/device/project, descriptor identity/type/operation and immutable ciphertext replay, then allocates monotonic transport sequence. Names/settings/order/dependency plaintext never enter server fields; backend never interprets semantic membership. Earlier encrypted modes still admit Notes only; unknown combinations fail closed. No account-object crypto introduced.

Received/orphan inbox and exact objects remain durable independently of dependencies. Internal retry(limit=1..32) rotates blocked authenticated structural frames with durable retry ordinals; later inbox events remain intact/applyable. Malformed frames retain inbox/object with invalid_stage_frame and no head. Metadata later valid → same Stage applies; missing Stage later applies → same order applies, including restart.

Existing **single contiguous account ACK** requires exact structural event+ledger+sequence+object proof for applied/conflict_preserved. Received/orphan/malformed/missing dependency/membership/tombstone-blocked events cannot unlock ACK; later proven events do not bypass an earlier gap. Metadata/Note shared infrastructure and C17 conflict/resolution semantics remain unchanged.

### Exact local checks and multi-device proof

- TS final focused/regression command: stageCodec, projectMetadataCodec, projectMetadataMigrationRuntime, noteSyncCodec, noteSyncResolutionV2Codec, noteSyncV3Cycle, encryptedSyncV3, noteSyncHeadlessCryptoBridge — **36 passed / 8 files**. **npm run typecheck PASS**. Initial new codec/v3 focused group 7 passed; later added structural descriptor case included in final count.
- Python Stage schema/source tests **31 passed**: supported 0..28, fresh/latest/idempotency, populated 27 Stage/order/metadata retention and no capture side effects. Existing populated metadata evidence tests extended to **25/26/27 →28**, including candidate/event/tips/reconciliation/pending decisions/Notes.
- Native **stage_sync 9 passed**: golden/frame rejection; candidate restart/recovery/publication replay; Alpha→Beta/Gamma; delete/edit/child retention; distinct three-Stage reorder permutations; invalid membership; orphan retry/restart/fair blocked ACK; scope/object/replay/rollback; metadata genesis conflict; untracked local edits.
- Rust metadata regressions **19 passed**, Note regressions **153 passed**, SQLite **29 passed**; **cargo check PASS**. Existing warnings plus intentional dead-code warnings for dormant crate-internal structural APIs; no dependency added.
- SQLite workflow-equivalent seven-file command: test_c9_sqlite_sync, test_c18_metadata_sqlite, test_c18_stage_sqlite, test_c15_7b_cross_runtime_udf_proof, test_application_metadata, test_f8_recovery, test_api — **149 passed, 0 skipped, 42.96 s**. Local launcher isolates default application data and legacy settings fallback in a temporary context. Initial unisolated collection hit sandbox read-only fallback without data write. Three old-fixture failures (new trigger prefix, reconstructed-v6 teardown, migration map) corrected narrowly; final curated pass fully green.
- Disposable real PostgreSQL postgres:16, no volumes: structural descriptors/opaque transport plus initial bounded multi-device proof **4 passed, 0 skipped, 24.62 s**. Final expanded multi-device proof **1 passed, 0 skipped, 26.21 s**: production TS seal/open → PostgreSQL opaque push/pull/exact replay → two file-backed native SQLite databases. A captures/publishes S1/S2; B authenticates/applies them and [S1,S2]. Concurrent S1 Beta/Gamma both survive. Independent same-parent changed [S2,S1] full-permutation events conflict even with equal payloads; distinct [S2,S1,S3] vs [S1,S3,S2] permutations proven natively. Full dependency tips, no conflict projection, eight-event contiguous server ACK/native ACK commit and reopen durability on both devices. Every bridge call reopens SQLite. An added ACK fixture initially omitted required project_id; corrected and affected proof rerun green. Exact prepare retry after restart also verified.
- Real PostgreSQL metadata and historical encrypted Note v1/v2 regressions: test_cloud_c18_metadata, test_cloud_encrypted_sync, test_cloud_encrypted_sync_v2 — **36 passed, 0 skipped, 20.71 s**. Structural acceptance stays below one minute locally; existing 30-minute Cloud timeout unchanged.
- Affected Python syntax compiled in memory without bytecode; full diff and git diff --check PASS. Protected .pyc unchanged; official progress 77.0%. Help/localization reviewed: only internal substrate/machine blockers added, no user-facing controls/text/workflow, so no help/catalog regeneration or browser UI claim. Windows native proofs wired to remote CI; graphical Tauri/Windows E2E remains release hardening.

**CI wiring:** expected **Cloud backend tests** and **SQLite sync substrate tests**. Both native path gates include stage_sync.rs. SQLite includes shared fixture/new Python tests and Windows stage_sync filter. Cloud mandatory no-skips PostgreSQL command includes both structural test files; frontend curated command includes Stage codec and changed v3 API spec. Job timeouts unchanged. One feat(c18): add stage structural sync substrate commit, push origin 6.0, then no Actions poll/wait/watch. New slice remains REMOTE CI PENDING for independent acceptance.

Remaining boundaries: internal/dormant substrate; no broad Stage migration/publication; explicit Stage/order full-tip conflict resolution still required; all Stage tombstones remain ACK/cleanup-blocked until complete child proof. Unsupported sources stay recoverable blockers. Account catalog/account-object v2 belong to later C18.4. Recommended next bounded slice after independent acceptance: **C18.4.02 — explicit Stage migration/integration, structural conflict decisions and reader-format readiness**, without account catalog or C18.5 activation. Official progress **77.0%**.

### C18.4.01 — CI portability / timeout correction

**Historical correction report: C18.4.01 was REMOTE CI PENDING at publication; subsequently REMOTELY ACCEPTED as recorded below. C18 IN PROGRESS; official progress 77.0% (77,0%).** Implementation SHA: `d0ba4b12299cfc307c3049e0f17d4c1685227a1b`. Independent remote evidence supplied by the user: **SQLite sync substrate tests run `36895240794` — FAILURE**; Python SQLite substrate — SUCCESS, Rust SQLite substrate — FAILURE. Stage filter reported 1 passed / 8 failed, all eight failures Windows file-lock error `Os { code: 32 }`: tests attempted to remove a file-backed SQLite database while their final `Connection` remained alive. This is test-cleanup portability evidence, not a demonstrated production Stage defect.

Correction is test-only: all eight Stage database cleanup sites now explicitly `drop(db)` before strict `std::fs::remove_file(path).unwrap()`. Earlier restart drops, every assertion and error check remain unchanged. Candidate durability/restart, atomic rollback, concurrent edit/delete, stage-order conflicts, orphan retry, ACK blocking, metadata dependencies, tombstone child preservation and scope guards retain the same coverage. No sleeps, retries, ignored cleanup errors, Windows bypasses or disabled tests. Production source, Stage codec/allowlist, migration 028, causal/conflict/tombstone/ACK contracts and metadata/Note/backend semantics are unchanged.

**Cloud backend tests run `36895240838` — CANCELLED at the 30-minute job boundary**; Frontend admin — SUCCESS; both PostgreSQL test steps (mandatory sync ACK/multi-device acceptance and focused cloud/legacy API tests) — SUCCESS. One read of the completed job timing confirmed PostgreSQL duration 30m03s, native dependency installation 16m59s, mandatory acceptance 9m37s and focused tests 2m33s. Workflow inspection found no obvious duplicate test invocation introduced by C18.4.01. The mandatory suite has grown with accepted C15–C18 cross-runtime proofs, and the previous 30-minute wall-clock budget has now caused repeated cancellations despite successful test steps (prior C18.3 evidence above). Only the **PostgreSQL cloud backend** job timeout changes **30 → 40 minutes** to provide explicit CI capacity/margin; mandatory coverage and acceptance checks remain intact, Frontend admin timeout stays 15 minutes. This is not an assertion failure or acceptance weakening.

Bounded local checks: Stage Rust filter `stage_sync::tests::stage_sync_` — **9 passed, 0 failed, 0 ignored** on macOS; test compilation succeeded with existing warnings. YAML parse and structural comparison — PASS, confirming timeout is the only workflow change. Exact source comparison — PASS, confirming eight cleanup drops are the only Rust changes and all assertions/production source remain identical. `git diff --check` — PASS. Rust SQLite filter not run (no shared helper changes); separate cargo check not run (focused cargo test compiled the affected source); Note/PostgreSQL suites not repeated. Protected engine/game_data `.pyc` untouched. Windows-specific correction still requires independent remote **SQLite sync substrate tests** success; local macOS success is not remote acceptance.

Publish one `test(c18): fix stage structural CI portability` commit to `origin/6.0`, then stop without Actions polling/wait/watch. Expected workflows: **Cloud backend tests; SQLite sync substrate tests**. C18.4.02 is not started; recommended next slice only after independent acceptance: **C18.4.02**.


### C18.4.01 — independent remote acceptance

**C18.4.01 — REMOTELY ACCEPTED.** Implementation SHA `d0ba4b12299cfc307c3049e0f17d4c1685227a1b`; Windows cleanup / PostgreSQL timeout correction SHA `f5cf41e5dea12e1db2f4a6fa079b8b6bd9fe5d08`. Independent evidence supplied by the user: [SQLite sync substrate tests 36912249285](https://github.com/nevskyforever/nfprogress/actions/runs/36912249285) — **SUCCESS** (Python SQLite substrate and Rust SQLite substrate / Windows); [Cloud backend tests 36912249047](https://github.com/nevskyforever/nfprogress/actions/runs/36912249047) — **SUCCESS** (Frontend admin and PostgreSQL cloud backend). Both corrections are remotely validated. Earlier CI-pending/failure paragraphs remain historical evidence, superseded by this acceptance. Codex did not poll Actions. **C18.4 IN PROGRESS; C18 IN PROGRESS; official progress remains 77.0%.**

## C18.4.02 — explicit Stage migration / integration / structural conflict decisions

**LOCAL COMPLETE / REMOTE CI PENDING. C18.4 IN PROGRESS; C18 IN PROGRESS; official progress exactly 77.0% (77,0%).** Preflight: `/Users/romankisockin/Desktop/nfprogress/ts_migration`, branch `6.0`, clean worktree; HEAD == origin/6.0 == required `f5cf41e5dea12e1db2f4a6fa079b8b6bd9fe5d08`. Protected `__pycache__/engine.cpython-312.pyc` and `__pycache__/game_data.cpython-312.pyc` untouched. No account catalog/account-object crypto v2 or C18.5 content writer activated.

**Reader readiness before explicit writer activation:** the existing mode-3 opaque descriptor router and native `commit_v3_sync_inbound_page` already accept Stage/order descriptors and persist exact ciphertext into the shared inbox/object tables. Production composition now always attaches `StageStructuralRuntime` to `NoteSyncV3Cycle`: Notes → metadata → Stage/order apply → shared contiguous ACK. Stage reader uses C11 project crypto/AAD v1, strict account/project/entity/type/event binding, inner/outer device/revision/operation/timestamps, frame and codec dispatch, then native authenticated apply. Failed authentication, invalid codec/frame or scope stays a durable typed inbox blocker; known dependency failures become native authenticated orphans with fair bounded retry. No reinterpretation as Note/metadata, silent skip, ciphertext discard, fallback or ACK for an unfamiliar event. Bootstrap/import uses the same composed mode-3 cycle once an authenticated metadata shell exists. Legacy Note v1/v2 and accepted metadata readers remain intact. Older unsupported readers fail closed; capability readiness does not imply an unsupported codec is ACK-safe.

**Migration state / trigger:** only explicit production “Опубликовать локальные этапы” calls begin. Login/unlock/startup/open/read/pull/retry never discovers or captures local Stage structure. Native commands reuse the accepted metadata owner/account/device guard, project binding/bootstrap and active authenticated metadata authority. States: `structural_local`, `candidate_captured`, `publication_pending`, `published_self_echo_pending`, `active`, `conflict`, `blocked`; derived from durable snapshot/history/tips/projection/inbox/outbox/local reconciliation, with latest migration state stored in schema **029**. Before any structural migration/inbound work, ordinary local Stage mutations retain their old behavior even if metadata is not activated. Once structural work exists, unresolved authority fails closed.

**Frozen migration set:** one BEGIN IMMEDIATE captures ≤32 exact Stage IDs in local permutation, candidate IDs, candidate source generations/snapshots, allocated Stage event IDs, immutable order event ID/header/permutation and metadata head proof. Unknown source fields block publication; after source repair an explicit begin may create a new generation while retaining the old snapshot. Parent-project ID is a validated local/derived foreign key and never enters the unchanged 12-field portable allowlist. All Stage genesis intents are committed atomically; no individually manual Stage publication. Prepared/sealed events never change on retry or untracked local edits.

**Publication / normal mutations:** metadata authority first; Stage immutable intents and C11 ciphertext next; migration order is prepared only after original Stage ledger proof plus current reconciled live projections and exact frozen membership. Its Stage-head dependency map is frozen at first prepare. Ordinary rename/goal/settings/status/completion uses v1 causal descendants with one exact tip, revision/generation parent+1, native durable outbox before upload and portable visible apply on authenticated self echo. Local-only fields remain on device. Later creation atomically preserves its Stage candidate/genesis and companion order intent; enabling the first Stage uses the existing metadata causal writer in the same transaction, rather than a cache write behind metadata authority. Existing local document/totals/completion hooks stay local; no new content/game transport. Ordinary reorder validates exact membership, full permutation and all current Stage/order heads; visible order waits for authenticated echo. A stale companion order requires explicit current-order reconciliation; a later proven active order prevents republishing its retained obsolete intent.

**Second device / conflict contract:** a fresh metadata shell imports Stages before order. Existing local Stage candidates and their original local permutation are preserved, not overwritten; explicit resolution is needed. Additive Stage/order codec **v2**, outer frame **v1**, codec IDs **2/3**, no compression; old codec v1 golden bytes unchanged. Full-tip decisions use sorted unique 1..64 exact parents, native CAS on full tips and exact local snapshot, max(parent revision/generation)+1, immutable frame and decision evidence. Choose a preserved branch or compose a valid Stage payload/permutation. Retry of the same pending decision returns the original event ID. R(A,B) followed by a newer C preserves C and R, clears false projection authority, and records `stale_structural_resolution`; a new explicit decision over every current tip is required, for Stage and order alike. Remote decisions prove the visible local snapshot belongs to authenticated parent lineage (bounded256) or retain it for local explicit reconciliation; local decision evidence is checked on self echo. No automatic merge or arrival/timestamp winner.

**Order reader proof:** writers require exact current live heads. Readers may authenticate a frozen Stage reference after a portable edit by proving bounded causal ancestry; every current tip and every referenced live tip must be covered within the same account/project/Stage scope. Unknown/sibling references, current tombstones or incomplete membership block apply/ACK. Limit 256 distinct traversed ancestry nodes per Stage; exceeding it is a durable `stage_dependency_proof_limit`, never a heuristic winner.

**Tombstone boundary:** selecting deletion can leave one causal tombstoned tip, explicitly distinguished in authority/UI from an unresolved branch conflict. Physical Stage cleanup, child deletion and order removal remain blocked with `stage_tombstone_child_manifest_incomplete`. Notes, maps, documents and progress are retained. Retrying a consumed old tombstone cannot resurrect its tip. No incomplete order is ACK-safe. Current delete command fails closed after structural activation; this slice does not authorize new destructive cleanup.

**UI / help / localization:** small Stage authority panel in existing project cloud settings provides inspect, explicit begin, retry, full-tip Stage/order branch choice and keep-local result. Friendly status/blocker text, readable portable fields, Stage names/permutations, explicit causal-deletion/physical-block distinction; no raw JSON or technical implementation flow. Native commands, SQLite adapter, composed runtime and cloud session store wired together; account-switch epoch guards retained. Existing help key `cloud_project_metadata` extended. Catalog regenerated through the real generator; all five non-Russian languages have zero missing strings. Semantic catalog diff: 20 new entries per language, **0 changed existing / 0 removed**.

**Bounded multi-device acceptance:** one real PostgreSQL scenario with two distinct repeatedly reopened file-backed SQLite devices and production TS crypto bridge. A explicitly migrates S1/S2 and [S1,S2]; B imports from active metadata shell. Exact lost-upload-response ciphertext replay, durable receipt and immutable event identity survive process restart. Both devices preserve concurrent Beta/Gamma renames, explicitly resolve full Stage tips, preserve concurrent divergent reorder, explicitly resolve full order tips, converge after reopen, and prove native/server ACK cursor 10. No Note/content event introduced. Every pull descriptor/ciphertext is committed to durable inbox before decryption/native apply. Synthetic PostgreSQL and local UI data isolated from production user data.

**Local verification (no broad green-suite repetition):**
- Rust `stage_sync` **20 passed, 0 failed**, including all nine accepted substrate tests plus migration/frozen restart/atomic rollback/source repair, normal writers/creation metadata coordination, full-tip/stale Stage and order, existing-local import, local CAS/retry, causal tombstone/child preservation, dormant local behavior, frozen-reference rename, stale companion reconciliation and remote-resolution preservation of unrelated local candidates.
- Rust `project_metadata_` **19 passed**; `sqlite` **29 passed**; focused `ack` **50 passed**, preserving Note/contiguous ACK/rollback protections. Full 153-test Note suite not claimed.
- Affected TS curated 16 files **129 passed**; final changed reader/codec/cycle/UI subset 4 files **29 passed** (includes added seal starvation and causal deletion cases). Accepted metadata/runtime/Note/Bootstrap/store regressions included in the curated pass.
- TypeScript typecheck **PASS**; production frontend build **PASS** (existing chunk/dynamic-import warnings only); Rust cargo check **PASS** (baseline warnings).
- Python SQLite CI-equivalent exact seven workflow files **152 passed, 0 skipped, 49.48s**: c9, metadata, Stage, C15 cross-runtime UDF, application metadata, F8 recovery, API. Fresh/all supported schema upgrades/reopen and populated28→29 preserve exact stored structural frames/ciphertext/rows.
- Help/localization **30 passed, 3.41s**; syntax compiled in memory without bytecode. Native AppKit tests run with required local window-system permission, no coverage disabled.
- PostgreSQL focused Stage/metadata regression bundle earlier **8 passed, 0 skipped**; final new structural proof **1 passed, 0 skipped; 63.42s call, 64.62s total**. Frontend reader negatives cover both entity kinds, unknown codec/frame, mismatched pairing, wrong project/device, metadata as Stage, Stage as Note, account-object crypto/AAD v2; typed blockers prevent ACK.
- Chromium via isolated `Run Web.sh`: actual production Vue panel explicit begin → pending → retry → active → full-tip choice; no automatic begin. Cloud actions mocked for UI verification, not claimed as graphical Tauri network E2E.
- Full diff review, YAML coverage review and `git diff --check` **PASS**. No full Nuitka build, dependency addition, broad refactor or generated source UI edits.

**CI wiring:** new single PostgreSQL integration file joins mandatory no-skips acceptance in Cloud backend tests; new TS runtime and Stage panel specs join curated frontend command; existing NoteSyncV3Cycle/codec specs already covered. New schema/native paths trigger both workflows. Windows Rust `stage_sync` filter stays mandatory and all new DB tests release final Connection before deleting files. Existing 40-minute PostgreSQL / 15-minute frontend budgets unchanged. Publish one `feat(c18): integrate stage structural migration` commit to origin/6.0; then stop, no Actions polling/wait/watch. Expected **Cloud backend tests; SQLite sync substrate tests**.

**Remaining boundaries / next bounded slice:** all physical Stage tombstone cleanup remains blocked without complete child manifest/retention proof; migration cap32 and reader ancestry cap256 are recoverable limits. Full graphical Tauri/Windows release E2E remains later hardening. Complete-project sync is not claimed. Next recommended scope after independent acceptance: **C18.4.03 — separate account catalog/account-object v2 contract and reader readiness**, requiring its own explicit task; do not begin folders/membership/order or C18.5 automatically. **C18.4 IN PROGRESS; C18 IN PROGRESS; official progress 77.0%.**


## C18.4.02 — independent remote acceptance

**C18.4.02 — REMOTELY ACCEPTED.** SHA `a9f175ef2481043c510c545e29332249a1d65b43`. Independent evidence supplied by the user: [SQLite sync substrate tests 36927729358](https://github.com/nevskyforever/nfprogress/actions/runs/36927729358) — **SUCCESS**, both Python SQLite substrate and Rust SQLite substrate / Windows; [Cloud backend tests 36927729419](https://github.com/nevskyforever/nfprogress/actions/runs/36927729419) — **SUCCESS**, both Frontend admin and PostgreSQL cloud backend. This supersedes the historical publication-time pending status above. Codex did not query Actions. **C18.4 IN PROGRESS; C18 IN PROGRESS; official progress exactly 77.0%.**

## C18.4.03 — friendly UX / application diagnostics

**LOCAL COMPLETE / REMOTE CI PENDING. C18.4 IN PROGRESS; C18 IN PROGRESS; official progress 77.0% (77,0%).** Organizational insertion only: account catalog/account-object v2 now belongs to **C18.4.04**. WORTA ROADMAP SCORING v1.0 is unchanged. Preflight: `/Users/romankisockin/Desktop/nfprogress/ts_migration`, branch `6.0`, clean worktree; HEAD == origin/6.0 == required `a9f175ef2481043c510c545e29332249a1d65b43`. Protected `.pyc` files untouched.

**UX architecture:** shared typed `UserFacingStatus` maps internal code to Russian title, explanation, suggested action, severity and separate technical code. Compile-time exhaustive session/project/metadata/Stage-state maps; explicit blocker mappings and deterministic unknown fallback. Human wording covers connection/import, metadata/Stage publication, competing versions, pending confirmation, stale choices, dependencies, encryption unlock, resource limits and failures. No state/enum/database/codec/protocol identifiers were renamed. Common `FriendlyStatus` and initially collapsed `DiagnosticDetails` replace component-specific dictionaries and primary protocol jargon. The local-version heading is outside the settings definition list, so labels and values stay paired in the two-column layout. Details show only a safe scalar code, subsystem, operation and generated correlation ID; no raw JSON. Unknown stable codes remain secondary; opaque suffixes/free-form strings are excluded.

**Existing facility audit:** backend/access logging and updater-specific logs are not a common durable support journal. Added a small shared diagnostic event contract and desktop adapter; no separate logging framework or dependency. Schema v1: UTC timestamp, severity, subsystem, operation, stable event code, generated UUID correlation and allowlisted scalar context. Subsystems prepared: application, sync, encryption, projects, stages, documents, migrations, game and developer. Representative instrumentation: application startup/Vue/unhandled errors; native startup/migration outcome; unlock; project create/update/connect/import; Stage create/update/reorder and decisions; explicit metadata/Stage migrations; Word import/file binding and document-sync timer failures; developer streak restoration. High-frequency editor saves/characters are deliberately not logged. Debug is excluded from default persistence.

**Persistence / retention:** independent desktop-local SQLite journal at the application data root `diagnostics/support.db`, isolated from entity databases and cloud transport. SQLite transactions provide durable/crash-safe completed writes. Debounced 150 ms append batches, maximum 64 queued events; oldest queue entries may be dropped under an exceptional burst. Retain latest 512 events and at most 512 KiB of serialized event data. Explicit page size 4096 and max_page_count 512 bound database high-water allocation to 2 MiB; temporary rollback journal is also bounded by this database. Native diagnostics commands use blocking-worker dispatch. Clear deletes the journal rows and vacuums this database only. A write failure never changes a game/sync result or ACK; UI receives a write-failure flag. Last unflushed events can be lost on an abrupt process exit; completed transactions survive reopen.

**Privacy contract:** frontend context allowlist plus independent native ingress reconstruction, and re-sanitization on copy/export. Keep only bounded counts, booleans, known status/error classes/codes and global/project/stage target type. Never persist arbitrary objects, caught messages/stacks, password/AMK/key/nonce/token/Authorization, backend bodies, content, names, emails, usernames, paths or entity IDs. Native streak errors are classified from the typed error enum, not serialized messages; no-history gets `streak_restore_no_history`. Allowlist parity is checked in Rust. Export header contains actual app version, build/runtime, OS/architecture, schema, export UTC, retained/included counts and explicit truncation/privacy markers. There is **no telemetry, cloud transmission or automatic upload**.

**Sync diagnostics:** one correlation spans explicit migration/decision → retry → cycle → terminal result. High-level request/start/result events; V3 pull/upload counts, metadata/Stage apply/conflict/orphan/blocked counts, ACK classification and at most eight individual blocker/error classifications per cycle. No per-byte/SQL logging. Logging reads existing results only; transport/CAS/full-tip decisions/contiguous ACK, crypto/AAD, Note/C17 history and backend semantics are unchanged.

**Support UI / manual workflow:** desktop Settings → Diagnostics shows count, approximate size, last UTC and privacy note. Clear → reproduce → return → Copy or Export → send the text/file for analysis. Copy returns latest up to 100 events and 60 KiB of event text plus header, with an explicit truncation flag. Export uses an explicit native save dialog and produces the full retained JSONL journal. Cancel does not write or claim success. Clear removes support history only. Existing Tauri capability adds only clipboard text-write and save-dialog permissions. Common event/service adapter stays reusable for a future browser adapter; no C21 adapter is implemented.

**Known streak case / objectively bounded fix:** actual frontend `developerRestoreStreak` passed the request fields at top level, but the registered native command requires a `payload: DeveloperStreakRequest` argument. The adjacent developer test-series action had the same mismatch. Both now wrap the camelCase request in `{payload: ...}`; restoration adds optional diagnostic correlation. HTTP bodies and game reward/streak rules are unchanged. Frontend requested/start are flushed before the rare native action; native validation/attempt/terminal classification and frontend terminal share one UUID. Failure uses a clear restoration message and secondary safe code. No-history remains a valid rule, not a guessed recovery; logs distinguish it. Global/project/Stage payload regression tests and existing native restore/series/target tests pass. Full graphical native-shell reproduction remains release hardening.

**Help / localization:** stable `cloud_project_metadata` key uses human settings/Stage wording and current action labels; new `application_diagnostics` guide explains local storage, privacy, limits, copy/export/clear and streak reproduction. Real generator used, with targeted manual terminology overrides for all five non-Russian languages. Catalog coverage has zero missing strings: 107 added entries per non-Russian language, 0 changed baseline entries and 0 removed. UI names/user data stay untranslated.

**Bounded validation:** 121 focused frontend tests across 18 files: diagnostic privacy/queue/correlation/failure isolation, desktop copy/save/cancel/clear/capabilities, presentation fallback/details, developer streak outcome/argument shape, affected Cloud/Stage/metadata/settings/project/document paths, existing Stage/metadata/V3/ACK and crypto-boundary regressions. Rust: diagnostics filter 5 PASS (file-backed reopen/pruning/size/copy/export/clear/privacy/tampered rows/allowlist parity/native streak tracing); developer filter 5 PASS (existing restore/series/target/logical-day/metadata-strip). Rust cargo check PASS with existing warnings. Frontend typecheck/build PASS with existing chunk warnings. Isolated Python help/localization 30 PASS; affected Python syntax compiled without bytecode. Chromium component flow checks explicit Stage/metadata actions, human stale/conflict states, collapsed secondary codes and diagnostic copy/export/clear with mocked native service boundary; no full Tauri E2E claim. No redundant local PostgreSQL multi-device run: backend/sync semantics unchanged.

**CI:** existing Cloud backend tests path filters include diagnostic module/capabilities; frontend job adds diagnostic/settings/developer/native-adapter tests, retains existing suites/build. Existing SQLite sync substrate tests add Windows Rust diagnostics and developer filters plus cargo check. Cloud PostgreSQL timeout remains **40 minutes**. Publish one `feat(c18): add user diagnostics and sync UX` commit to `origin/6.0`, then stop; expected workflows **Cloud backend tests; SQLite sync substrate tests**. New remote CI remains **PENDING — not polled by Codex**.

**Remaining boundaries / future notes:** bounded journal is best-effort support evidence, not an audit archive; buffered tail may be lost on abrupt termination and storage failures remain visible. No full graphical Tauri/Windows E2E claim until native release qualification. Stage physical cleanup still blocked without complete child proof. No account catalog/account-object v2, folders/membership/order, C18.5, new cloud writers, telemetry or C21 implementation. Recommended next authorized slice after independent acceptance: **C18.4.04 — ACCOUNT CATALOG / ACCOUNT-OBJECT V2 CONTRACT + READER READINESS**. For future **C21**, first local browser build + Tauri dependency audit + repaired browser adapters + stable local Web; VPS/production deployment only afterward. Preserve these notes across future checkpoint compaction. **C18.4 IN PROGRESS; C18 IN PROGRESS; official progress 77.0%.**


## C18.4.04 — account-object v2 transport / reader readiness — 2 October 2026

**C18.4.03 — REMOTELY ACCEPTED.** Implementation SHA `06ec3dd08dd5e6d5ab648be350ff0a47ae50e519`. Independent evidence supplied by the user: [SQLite sync substrate tests 36934668947](https://github.com/nevskyforever/nfprogress/actions/runs/36934668947) — **SUCCESS**; [Cloud backend tests 36934668936](https://github.com/nevskyforever/nfprogress/actions/runs/36934668936) — **SUCCESS**. Diagnostics/UX and developer streak restore payload correction accepted; no telemetry. Historical CI-pending statements above are superseded. Codex did not query Actions. **C18.4 IN PROGRESS; C18 IN PROGRESS; official progress exactly 77.0%.**

**C18.4.04 — LOCAL COMPLETE / REMOTE CI PENDING.** Baseline `06ec3dd08dd5e6d5ab648be350ff0a47ae50e519`, branch `6.0`, clean preflight with HEAD equal to origin/6.0. Protected engine/game_data `.pyc` untouched. No reset/clean/destructive checkout/restore. No dependency added and no crypto fallback introduced.

**Frozen account-object contract:** crypto/AAD **2/2**, XChaCha20-Poly1305-IETF, same authoritative account AMK lease. Identity tuple in exact order: authenticated canonical server user UUID, literal `account`, entity ID, entity type. Nonempty Unicode-scalar UTF-8; user/entity limits 512 bytes, type 128 bytes. Each field is u32 big-endian byte length + UTF-8 bytes. HKDF-SHA256 salt `worta/hkdf/account-object-key/salt/v1`, info `worta/account-object-key/v1` + `02 02` + tuple; AAD `worta/account-object-aad/v1` + `02 02` + same tuple. C11 implementation and vectors remain byte-for-byte unchanged. Production encryption uses fresh random 24-byte nonces.

**Transport/storage:** real authenticated `POST /api/v3/sync/encrypted/account/push`; no project field/sentinel. Canonical user UUID must equal authenticated user before event lookup; closed account schema permits only `folder`, `folder_order`, `folder_membership`, `project_order`, operation upsert/delete and v2/v2 object. Project push schemas remain project-only, v1/v1 crypto. Backend migration `c18_account_scope` follows `c18_metadata_reader_gate`: nullable project ID only for reserved account types, retaining the existing composite ownership/event PK, encrypted object FK and per-user sequence uniqueness. Same-ID exact replay remains immutable/idempotent; changed descriptor or envelope rejects. Server validates bounded opaque transport only, never catalog names/membership/order plaintext. Shared mode-3 pull returns the globally ordered mixed prefix under existing count/ciphertext budgets; no per-type filtering/starvation or separate ACK universe. Old project-only readers fail closed on account frames. Project registry enforcement remains on every project descriptor; account transport creates no project registry entries or local project binding.

**Local reader/ACK:** forward-only shared Python/Rust migration **030 / schema 30** introduces `cloud_sync_account_inbox` with authenticated account identity, no project column, exact nonce/ciphertext and descriptor, sequence, durable state/blocker. Cross-scope insert guards prohibit event/sequence collisions; immutable descriptor/object update guard permits only state/error changes. One native mixed-page transaction commits both scopes and their common pull cursor; lost IPC replay checks the complete combined page. Existing project command types remain accepted. Project/Note/metadata/Stage readers do not query account rows. Production composition wires `AccountObjectReader` before shared ACK: bounded keyset read, canonical account/auth epoch/key lease checks, v2 authentication, allowlisted scope/type dispatch, transient plaintext zeroing, durable `account_entity_codec_not_activated`. Bad scope/authentication stays blocked with safe typed classification. Download, authentication and descriptor recognition never constitute apply proof. Native ACK preparation and commit revalidation explicitly stop at every account row; a later applied project event cannot bridge it. Retained blocked bytes can be consumed by a future activated reader without server re-upload; no catalog apply proof/codec is activated here.

**Vectors/negatives:** synthetic `frontend/src/crypto/account-object-v2.vectors.json` fixes AMK, UUID/entity/type, Unicode tuple, info, key, AAD, nonce, plaintext and ciphertext. Production TS WebCrypto/libsodium verifies all bytes and AEAD round trip; independent Node HKDF and native Rust SHA256/HMAC test verifier independently reproduce tuple/key/AAD. Rust is an opaque persistence boundary, not a production AEAD runtime: no claim of Rust AEAD/decryption implementation. Native test preserves the same vector nonce/ciphertext through file-backed reopen. Changed user/scope/entity/type/versions, both project/account crypto directions including forced version relabeling, wrong Note/generic/metadata/Stage entry, invalid Unicode/bounds, altered immutable replay, atomic mixed-page rollback, restart blocker and ACK past a later project are covered. No normal account writer exists.

**Diagnostics/help:** existing local bounded journal receives safe stable blocker classifications only; mirrored TS/Rust allowlists include codec-not-activated, scope rejected and decrypt failed. No keys, UUIDs, nonce/ciphertext, catalog names/content, network export or telemetry. Existing friendly “Эти данные пока не поддерживаются” presentation precedes technical details. Cloud help explains retained unsupported data and local-only folder/order behavior. Generated catalog adds exactly one guide source per language without changing existing translations; curated overrides preserve accepted metadata/Stage paragraphs and add the new paragraph for EN/ES/DE/FR/pt_BR. No full future terminology audit performed.

**Validation:** focused PostgreSQL account API + metadata + encrypted Note v1/v2 **38 passed, 0 skipped**. Final isolated SQLite CI-equivalent affected bundle plus help/localization **214 passed**, covering fresh/all historical paths, populated latest-1 preservation, reopen, schema/source guards and existing API. Historical synthetic-downgrade fixture cleanup now removes migration-030 guards before replaying old migrations; original migrations/data behavior remain unchanged. Final help/localization after curated override refinement **30 passed**. Focused frontend crypto/reader/v3/metadata/Stage/diagnostics/streak **97 passed / 15 files**, plus accepted Note v1/v2 crypto/golden **13 passed / 3 files** and production runtime/router/settings/two-device crypto/ACK regressions **69 passed / 7 files**; final affected API parser **4 passed**. Rust account **4**, SQLite **29**, Note sync **153**, metadata **19**, Stage **20**, diagnostics **5**, developer streak **5** passed; cargo check and frontend typecheck/build PASS with existing warnings. Python syntax/import coverage, YAML parsing, translation semantic comparison and diff whitespace PASS. Heavy Stage PostgreSQL multi-device acceptance was not repeated. Local macOS checks do not claim Windows/remote acceptance.

**CI/publication:** new account API test is in mandatory no-skip PostgreSQL command; account TS crypto/reader tests in frontend curated command; native account/vector filter in Cloud and Windows SQLite; migration test/vector/native paths trigger workflows. PostgreSQL timeout stays **40 minutes**. Commit `feat(c18): add account object sync namespace`, push origin/6.0, then stop without Actions polling/wait/watch. Expected **Cloud backend tests; SQLite sync substrate tests**. This implementation remains **REMOTE CI PENDING** for independent SHA/job verification.

**Remaining catalog boundary / next recommended slice:** **C18.4.05 — ACCOUNT CATALOG DURABLE SUBSTRATE / EXPLICIT MIGRATION / WRITERS**. No folder CRUD/order/membership/project-order writers, catalog payload codecs, discovery, local catalog publication or account game ledger. C18.5 not touched. Keep frozen dependency graph: account folder + authenticated explicitly bound project → membership → account project order. Folder deletion must preserve membership until explicit handling; membership requires existing folder + bound project; cloud order contains only explicitly connected projects; local-only positions stay local; concurrent moves/reorders preserve conflicts. Future writer activation must respect reader compatibility and define durable apply/conflict ACK proof.

**Permanent release gate — preserve during checkpoint compaction:** **PF6.0/RC completion does NOT automatically open public registration.** Implement all WORTA 6.0 functionality and complete C18/C21/C22/C23/PF6.0/RC acceptance, keep registration **CLOSED**, then owner stabilization/dogfooding in normal real-world use. Do not invent a mandatory duration. Owner reports bugs/UX issues through the local diagnostic journal and normal manual testing; fix release blockers; perform final terminology/message audit after C18.5–C18.8/C21/C22 final states exist; repeat critical manual scenarios. Public registration opens **ONLY after the owner explicitly decides the build is ready**. `technical RC ready` and `publicly released` are distinct states. This paragraph records policy; it does not change registration configuration now.

**Required future C22/PF6.0 audit:** full UI terminology/error review before public release despite the accepted central presentation layer: no unnecessary protocol jargon, clear primary messages, useful actions, retained Technical Details, complete localization and safe stable diagnostic codes. Future entities/Web/hardening will introduce new states, so the final audit cannot be replaced by C18.4.03 or this slice.

**C21 execution order remains permanent:** local browser build → audit Tauri/desktop-only dependencies → implement/repair browser adapters → stable local Web behavior → only then VPS/production deployment. C21 is not implemented here. **C18.4 IN PROGRESS; C18 IN PROGRESS; official progress remains 77.0%.**


## C18.4.04 CI correction — stale Alembic head expectations

C18.4.04 implementation SHA `b3e3778c0bed2df221b66fdddea39ad5c00e7f61` received independent remote results supplied by the user: [SQLite sync substrate tests 36980811198](https://github.com/nevskyforever/nfprogress/actions/runs/36980811198) — **SUCCESS**; [Cloud backend tests 36980811196](https://github.com/nevskyforever/nfprogress/actions/runs/36980811196) — **FAILURE**. The Cloud frontend-admin job and mandatory account transport/crypto acceptance passed. In the focused legacy API test command, two migration-head assertions were stale: `test_cloud_postgresql_foundation.py::test_alembic_upgrade_empty_postgresql_database_to_head_twice` and `test_cloud_auth.py::test_c2_schema_and_repeated_head_upgrade` expected `c18_metadata_reader_gate` after upgrading to `head`; the intentional current revision is `c18_account_scope`. This failure was test expectation drift, not account crypto or transport behavior.

The two previously failing tests now pass locally together (**2 passed**). The exact focused Cloud and legacy API CI command also passes (**194 passed, 0 skipped**); it includes both corrected tests and the 192 passing cases from the supplied remote run. `alembic heads` confirms exactly one head, and `git diff --check` passes. The corrective change updates only those two current-head expectations. Historical `down_revision = 'c18_metadata_reader_gate'` and explicit historical references remain. `alembic heads` reports exactly one head, `c18_account_scope`, whose down revision is `c18_metadata_reader_gate`. No production code, workflow, timeout, schema, account protocol, or generated file changed. The checkpoint retains all prior release-gate, C22/PF6.0 terminology audit, C21 local-Web-first and C18.4.05 notes.

Correction status: **C18.4.04 CI CORRECTION — LOCAL COMPLETE / REMOTE CI PENDING** until independent verification of the new Actions SHA. C18.4 and C18 remain **IN PROGRESS**; official progress remains **77.0%**. Do not treat the earlier partial Cloud run as remote acceptance for the correction.

## C18.4.04 remote acceptance — independently supplied evidence

**C18.4.04 — REMOTELY ACCEPTED.** Implementation `b3e3778c0bed2df221b66fdddea39ad5c00e7f61`:
[SQLite 36980811198](https://github.com/nevskyforever/nfprogress/actions/runs/36980811198) — SUCCESS.
[Initial Cloud 36980811196](https://github.com/nevskyforever/nfprogress/actions/runs/36980811196) — FAILURE limited to two stale Alembic-head test expectations; mandatory crypto/account acceptance and frontend-admin passed.
Test/checkpoint-only correction `504355f94bf217b9e78d939b9aecef526b670deb`:
[Cloud 36983243423](https://github.com/nevskyforever/nfprogress/actions/runs/36983243423) — SUCCESS, Frontend admin and PostgreSQL cloud backend both green. No production/workflow/schema/protocol change in the correction. This supersedes the earlier pending status. Evidence comes from the user; Codex did not query Actions.

## C18.4.05 — encrypted account catalog activation — 2 October 2026

**LOCAL COMPLETE / REMOTE CI PENDING. C18.4 IN PROGRESS; C18 IN PROGRESS; official progress exactly 77.0%.** Preflight: `/Users/romankisockin/Desktop/nfprogress/ts_migration`, branch `6.0`, clean worktree; HEAD == origin/6.0 == required `504355f94bf217b9e78d939b9aecef526b670deb`. Protected engine/game_data `.pyc` files untouched. No reset/clean/destructive checkout/restore, dependency addition, telemetry, account game or C18.5 work.

**Codec/crypto:** production TS and native strict canonical codec v1 for folder, folder order, folder membership and project order. Closed header/account/entity/event/device/operation/revision/generation/sorted parents, exact dependency maps and allowlisted payloads; unsupported keys, duplicate IDs, stale membership/head proofs and foreign lineage fail closed. Accepted WORTA-C1 framing slots4–7, compression0, canonical UTC timestamps and UTF-16 canonical key ordering. Folder `{name}` or null tombstone, membership `{folder_id}` or null removal, orders `{ids}`. Account crypto/AAD exclusively2/2; account v2 golden vectors and C11 files/vectors unchanged. Backend remains ciphertext blind, with existing Alembic head `c18_account_scope`.

**Schema31 / common substrate:** `031_account_catalog.sql`, shared Python/Rust runner. Generic typed inbox blockers, retained candidates, immutable explicit migration snapshot, immutable events and sealed ciphertext, upload receipt, self-echo, history/tips, projection, exact apply ledger, full-tip decisions and local candidate conflicts. Existing `project_folders(id,name,position,payload_json)`, `project_folder_members(project_id,folder_id)` and full `project_order(project_id,position)` rows are preserved. Canonical source payload extensions/bounds are checked explicitly; unsupported source is preserved with a typed blocker. Explicit retry can recapture a repaired preflight source while retaining previous candidates.

**Explicit migration/state:** Cloud settings action “Опубликовать структуру проектов”; durable local/captured/publication_pending/self_echo_pending/active/conflict/blocked states. No publication/capture on login, unlock, read, startup, background cycle or first pre-authority folder edit. Explicit begin atomically freezes event IDs, candidate/source identities, payload frames and future dependency IDs. Folder roots publish first; confirmed/self-echo folder authority enables full live-folder permutation and eligible membership; membership confirmation enables project order. Sealed event ID/nonce/ciphertext never change on retry; later edits form new generations over durable queued predecessors. Native IMMEDIATE transactions cover causal/local CAS, preparation, readiness/blocker classification, seal, receipt, apply and ledger.

**Local-only boundary:** eligible IDs require explicit same-account binding, valid bootstrap and reconciled authenticated metadata head. Cloud order is the filtered relative order only. L1,C1,L2,C2,L3 emits C1,C2; cloud apply changes only cloud slots. Mixed folder C1+L1 retains L1 locally and emits C1 only; no local-only identity enters membership, order or project proof and no project is implicitly registered. Local source candidates on another device remain preserved; authenticated conflicting remote data do not overwrite them without explicit reconciliation.

**Writers/integration:** ordinary folder create/rename/delete queue causal account intent after authority; authoritative visible changes follow verified self echo. Folder order is a complete live permutation with exact head proof. Membership assign/move/null removal validates folder and project proofs; local-only changes remain local. Project reorder preserves local slots and queues only same-account eligible IDs. Native ordinary membership bridge now carries folderId and distinguishes absent vs explicit null, so removal reaches the writer. New connection eligibility derives restart-safe relation/order intents only after metadata authority; no unrelated reorder. Existing pause semantics remain non-destructive; local unbinding is guarded by typed `catalog_disconnect_requires_reconciliation`, not translated into remote deletion.

**Conflict/deletion/ACK:** all four types preserve causal branches and local candidates. Explicit decision uses exact full sorted current tips and local CAS; max-parent revision/generation+1; immutable event/object retry. A+B→R followed by C preserves C+R and requires R2 over current tips, including membership and project order. Folder tombstone retains history, row and all memberships; live/unresolved or local-only relations block completion/ACK until explicitly moved/removed and safely retried. No physical catalog/history cleanup. Shared ACK requires matching account inbox descriptor, event identity/sequence, canonical frame, ciphertext/nonce and immutable apply/conflict ledger; blocked/unknown/orphan events stop the global contiguous prefix. Existing project readers remain separate.

**Bounds:** 16,384 folders/eligible projects/memberships/order entries; folder name120 Unicode scalars and512 UTF-8 bytes, identity512 bytes; parent/tip limit64; canonical plaintext4 MiB; retained history131,072 events /256 MiB frames+ciphertext per account; publication8 items, reader1–32 ×1–8 passes (default8×4), accepted common pull/body/ciphertext budgets unchanged. Exceeded bounds preserve local/inbox progress and produce typed recoverable blockers, with no partial ACK. Compression remains C18.7.

**Diagnostics/UX/help:** safe local journal classifications for explicit migration, per-type apply/conflict, dependencies/blockers/resolution and shared ACK; mirrored static TS/Rust allowlists. No folder/project names, account UUIDs, payload, nonce/ciphertext or keys in journal. Existing centralized friendly status shows catalog states and secondary technical codes; explicit conflict branch/local selection, folder ordering and safe continuation in Cloud settings. Chromium exercises explicit begin, continuation and full-tip choice through the real Vue panel with mocked native/store boundary; no full graphical Tauri claim. Cloud guide and all five non-Russian languages describe explicit publication, local-only exclusion, mixed folders, concurrency and no cascading deletion. Catalog is regenerated through the existing generator; earlier curated guide paragraphs/translations preserved.

**Acceptance:** one bounded `test_cloud_c18_catalog_integration.py` uses real PostgreSQL16, production TS account-object v2 and two distinct file-backed native SQLite devices reopened by each bridge call. A has F1 Work/F2 Archive, C1/C2 connected, L1 local; encrypted migration excludes L1, B imports, concurrent folder rename/membership move/project reorder preserve conflicts and explicit resolution converges; upload/response-loss repeats exact bytes/IDs; duplicate apply retains proof; folder delete with live membership remains blocked without cascade; shared ACK stops one before it; A retains L1 in its local folder/slot. Mandatory CI commands include new native/codec/runtime/UI/schema and no-skips PG acceptance. PostgreSQL job stays40 minutes.

**Local validation:** catalog codec/production crypto/runtime/writer/UI and focused C11/metadata/Stage/Note/diagnostics/frontend regressions; TS typecheck and frontend build; native catalog and accepted account transport tests; SQLite/Note/metadata/Stage/diagnostics Rust regressions and cargo check; all supported schema prefixes and populated30→31/reopen; focused SQLite CI-equivalent Python/API checks; localization/help; Chromium flow; Python syntax in memory without bytecode and workflow YAML; full diff /git diff --check. Final bounded totals: 121 frontend tests across18 files (plus final15 diagnostics/desktop and3 reader checks); 237 Rust tests across catalog7/account transport4/SQLite29/Note153/Stage20/metadata19/diagnostics5; 218 SQLite CI-equivalent Python/API tests in two focused invocations; help/localization30; one mandatory real PostgreSQL acceptance, no skips. Final typed resource blocker persistence is verified after file-backed reopen; source inbox CHECK constraints remain unchanged. Build warnings remain the existing large chunks/dynamic-import warning. Full graphical native/Windows release E2E remains later qualification; Windows native proofs are wired to required CI.

**Remaining boundaries / next slice:** strict stale dependency, unsupported-source and resource blockers intentionally preserve data and require explicit reconciliation/continued support. Binding removal cannot claim remote deletion. Physical folder/history cleanup and project/structural destructive child manifests remain outside this slice. Recommend **C18.4.06 — STRUCTURAL / ACCOUNT CATALOG INTEGRATION ACCEPTANCE**, reviewing the complete metadata+Stage+catalog graph, destructive/tombstone boundaries, mixed local/cloud and shared ACK, residual blockers, convergence and any remaining child/delete-manifest proof before C18.4 closure. Do not close C18.4 or C18 here.

**Permanent release notes preserved:** registration remains CLOSED and opens only by an explicit owner decision, never automatically at PF6.0/RC. Stabilization/dogfooding precedes public release; no invented duration. Final C22/PF6.0 terminology/message audit remains required. C21 order remains local browser build → Tauri dependency audit → repaired browser adapters → stable local Web → VPS/production only afterward. No future-stage implementation here. Commit `feat(c18): activate encrypted account catalog`, push origin/6.0; after push stop without polling/watching Actions. Expected **Cloud backend tests; SQLite sync substrate tests**. **C18.4 IN PROGRESS; C18 IN PROGRESS; official progress77.0%.**

## C18.4.05 — independent remote acceptance

**C18.4.05 — REMOTELY ACCEPTED.** Implementation SHA `d95e4c0d8612783e13950bd1aac8cfded318b44b`.
Owner-supplied independent evidence: [SQLite sync substrate tests 36992277299](https://github.com/nevskyforever/nfprogress/actions/runs/36992277299) — **SUCCESS** (Python SQLite and Rust SQLite/Windows both green);
[Cloud backend tests 36992277357](https://github.com/nevskyforever/nfprogress/actions/runs/36992277357) — **SUCCESS** (Frontend admin and PostgreSQL cloud backend both green).
This supersedes C18.4.05 CI-pending statements above. Codex did not query Actions.
**C18.4 IN PROGRESS; C18 IN PROGRESS; official progress exactly77.0%.**

## C18.4.06 — structural / account catalog integration acceptance

**LOCAL AUDIT COMPLETE / C18.4 NOT CLOSED / NEW REMOTE CI PENDING.**
Preflight: `/Users/romankisockin/Desktop/nfprogress/ts_migration`, branch `6.0`;
HEAD == local origin/6.0 == required `d95e4c0d8612783e13950bd1aac8cfded318b44b`, clean worktree.
No reset/clean/destructive checkout/restore; protected engine/game_data `.pyc` untouched.

Auditable acceptance matrix A–R and production wiring are in
[C18.4 integration acceptance](cloud/C18_4_INTEGRATION_ACCEPTANCE.md).
Metadata, Stage, Stage order, account2/2 crypto, normal catalog graph, local-only/mixed
projection, conflicts/full-tip/stale decisions, retention, atomicity, security,
diagnostics and friendly UX have accepted baseline plus focused local evidence.
Project metadata tombstone ACK proves preserved intent only, as accepted in C18.3.04;
it authorizes no destructive cleanup. Stage tombstones remain child-manifest blocked.
Future child cleanup/manifests are **DEFERRED BY FROZEN DESIGN**, not manufactured gaps.

**P0: none found. P1-01: fixed locally.** Catalog previously admitted membership
through an old metadata ledger when current metadata was unreconciled. The failing
baseline regression returned `applied` instead of `catalog_project_unproven`.
The bounded production fix requires current referenced metadata authority `active`
inside catalog readiness/apply transactions. Reopen/reconciliation retries the same
retained event and safely obtains apply/ACK proof. No codec/crypto/schema/UI text changed;
existing help/friendly waiting messages remain accurate.

**P1-02: UNRESOLVED — blocks C18.4 closure.** A sealed folder-order event O captures
old F1/F2 heads; another device's ordinary F1 rename applies at sequence9; O arrives
at10 and remains `catalog_membership_changed`. A new explicit full-tip resolution R
applies at11, but after reopen/retry O still has no ledger, its exact nonce/ciphertext
remain unchanged, and the real common ACK candidate stays9. The new audit test
records this deficiency; green regression output is not a complete-acceptance claim.
Static project-order proof-map/current membership equality has the analogous recovery
boundary. Existing tip-only decisions cannot complete a dependency-blocked non-tip.
Retained data and safe ACK prevent P0, but permanent loss of progress is required C18.4
behavior missing, not a later-content deferment or harmless cap.

Do not weaken ACK, mutate old ciphertext, or silently drop the old operation.
Generic bounded ancestry/dependency reconciliation plus complete-preservation proof
affects multiple catalog entities and deserves corrective **C18.4.07 — CATALOG STALE
DEPENDENCY RECOVERY / SHARED ACK PROOF**. Stop integration closure work at the documented
evidence; C18.5 is not started and is not recommended before this corrective slice.

The accepted PG catalog scenario is extended, without duplicate account/bootstrap setup,
to one real account with metadata → two Stages → Stage order and folder/order → membership
→ project order on two separately reopened native SQLite devices. L1 exists only on A;
catalog conflicts resolve explicitly; both server and local ACK cursors converge before
the deliberate folder blocker; a subsequent Stage event applies on both devices while
the mixed contiguous ACK correctly stops before the account blocker.

Focused checks: **38 frontend PASS /8 files; 37 Rust PASS** (catalog9, metadata
acceptance4, Stage20, account transport4); cargo check PASS; **64 Python SQLite PASS**;
**one integrated PostgreSQL PASS, 0 skipped /99.49s**; affected Python syntax compiled
in memory without bytecode; `git diff --check` PASS. No TS/Vue changes, so no redundant
typecheck/build/browser run: independently accepted C18.4.05 results remain baseline
evidence. This is a focused SQLite subset, not a new full CI-equivalent claim.
Native new tests match existing Windows/Cloud catalog filters; PG modules are already
mandatory in Cloud. Workflow triggers already cover the changed native file; no workflow
change or timeout increase (PostgreSQL stays40 minutes).

**P2:** full graphical native/Windows E2E and broader manual device runs remain release
hardening at C22/C23/PF6.0. Preserve release gate unchanged: registration CLOSED until
owner dogfoods/stabilizes, fixes release blockers, reviews diagnostics, performs the
final terminology audit and critical manual tests, then explicitly decides to open it;
PF6.0/RC never opens it automatically. C22/PF6.0 final terminology audit remains required.
C21 remains local browser build → Tauri dependency audit → browser adapters → stable
local Web → VPS/production. No telemetry, account game, C18.5 or destructive cleanup work.

Publish a truthful bounded-fix/audit commit to origin/6.0, then stop without polling
Actions. Expected **Cloud backend tests; SQLite sync substrate tests**. New remote CI
**PENDING — not polled by Codex**. **C18.4 IN PROGRESS; C18 IN PROGRESS; official progress77.0%.**


## C18.4.06 — independent remote acceptance of integration audit

**C18.4.06 — REMOTELY ACCEPTED AS INTEGRATION AUDIT.**
Implementation/audit SHA `39022df6ff0f69cc7ec3f9a4b317e8c6eb6f8f39`.
Owner-supplied independent verification:
[SQLite sync substrate tests36996342190](https://github.com/nevskyforever/nfprogress/actions/runs/36996342190)
— **SUCCESS** (Python SQLite substrate and Rust SQLite/Windows);
[Cloud backend tests36996342235](https://github.com/nevskyforever/nfprogress/actions/runs/36996342235)
— **SUCCESS** (Frontend admin and PostgreSQL cloud backend). All four jobs green.
Codex did not query Actions. Audit intentionally kept C18.4 open: P0 none, P1-01
fixed, P1-02 unresolved. This supersedes the C18.4.06 remote-pending statement above,
without retroactively declaring structural/catalog closure.

## C18.4.07 — catalog stale dependency recovery / shared ACK proof

**C18.4 — LOCAL COMPLETE / REMOTE ACCEPTANCE PENDING.** Closure candidate only;
not CLOSED or remotely accepted. Preflight branch `6.0`, clean HEAD == local
origin/6.0 == required `39022df6ff0f69cc7ec3f9a4b317e8c6eb6f8f39`.
Protected engine/game_data bytecode untouched; no destructive checkout/reset/clean.

**Root cause / correction:** frozen heads and project-proof maps were compared
exactly with current heads. Rename9 stranded immutable O10, even after R11 and
restart, leaving shared ACK9. New catalog-scoped iterative causal coverage verifies
all frozen and traversed events against same account/type/entity authenticated
ledger; cycle-safe visited/cache, single resolved current tip and every frozen
reference covered. Bound256 distinct nodes per dependency unit /65,536 loads per
event; typed existing resource blocker if exceeded. Stage ancestry remains unchanged.

**Entity semantics:** folder rename preserves live identity; direct folder order
still requires exact live folder IDs. Membership can cover old target-folder and
metadata heads. Project proof retains explicit binding/bootstrap, frozen applied
non-delete metadata, active current authority (P1-01), and authenticated scoped
ancestry. Project order preserves exact eligible connected IDs while permitting
causal metadata update, folder move or null membership. Null relation is not project
removal. Local-only L1 is neither bound nor transported by reconciliation.

**Incompatibility / preservation:** known added/deleted folder set, proven folder
tombstone or added connected project set preserves old intent as conflict only;
no invalid order/deleted-folder membership is projected. Unknown/unproven/unrelated
history, invalid bootstrap/account, unbound project, unresolved metadata/dependency
tips and proof overflow remain legitimate blockers without ACK. Explicit full-tip
resolution enables retry; no arbitrary branch selection. No physical cleanup/cascade.

**Complete-preservation ledger:** existing `applied`/`conflict_preserved` binds exact
immutable ID/frame/nonce/ciphertext/sequence. Retained authenticated history, original
payload/dependencies, causal tips and local conflict candidate provide complete
preservation in the same transaction. No new table/schema/outcome, ignore flag,
replacement event or changed crypto/codec. Late O removes only named parents;
concurrent newer R survives, and explicit ordinary O+R resolution remains possible.
Common ACK does not require immediate user resolution, but still requires exact
proof for every sequence; `ack_proven` is unchanged.

**Restart / shared ACK:** renamed positive regression
`account_catalog_stale_dependency_recovery_preserves_newer_resolution_and_shared_ack`
retains the exact legacy blocker O10, applies R11 and real project Stage12, reopens,
recovers O as preserved conflict, checks O/R tips and unchanged R projection, and
uses real `prepare_note_sync_ack`:9 before recovery →12 afterward. Original sealed
bytes/frame survive. PG extension uses production TS crypto and reopened A/B files:
frozen order → folder rename → R → O/R conflict → explicit R2; frozen project order
survives metadata rename and null membership; both devices prove common ACK before
R2 and later confirm server/local convergence. Intentional later account blocker
still stops ACK despite an applied Stage afterward. No special catalog cursor.

**Fair retry / UX:** scoped ephemeral keyset scheduling continues across bounded
reader cycles so blocked prefixes cannot starve successors; end-of-list restarts old
blockers, auth epoch changes reset scope. Scheduling is not ACK/pull state. Existing
safe diagnostic/friendly waiting/conflict/resource mappings suffice; no new text,
localization change, plaintext logs, telemetry or server semantic knowledge.

**Evidence:**14 catalog Rust tests cover rename, metadata/move/null, unresolved
conflict → resolution, unrelated/missing/cyclic/over-budget history, set/tombstone
conflict preservation without invalid materialization, foreign/altered-byte negatives,
C3 addition/unproven C2/wrong bootstrap/local-only exclusion and reopen/mixed ACK.
Acceptance matrix F/G/H/J/K/N/O updated with named evidence in
[structural/catalog acceptance](cloud/C18_4_INTEGRATION_ACCEPTANCE.md).
P0:none found. P1-01:still fixed. P1-02:resolved locally. No new P1 found in this scope.
Every row PASS or legitimate DEFERRED BY FROZEN DESIGN; graphical shell remains P2.

**Local validation:**53 frontend tests /9 files PASS; TypeScript typecheck/frontend
build PASS (existing chunk/dynamic-import warnings);52 Rust tests PASS (catalog14,
metadata acceptance4, Stage20, account transport4, diagnostics5, developer/profile5);
cargo check PASS (existing warnings);64 focused Python SQLite/catalog/account PASS;
one extended real PostgreSQL16 two-device acceptance **PASS,0 skipped,258.56s**;
affected Python syntax in memory, no bytecode; full scoped diff /git diff --check.
Focused subset, no full legacy suite or full SQLite CI-equivalent claim. Mandatory
Cloud/Windows catalog filters and Cloud reader/PG commands already include new
proofs; workflows unchanged, PostgreSQL timeout40 minutes. Expected **Cloud backend
tests; SQLite sync substrate tests**. New remote CI **PENDING — not polled by Codex**.
Commit `fix(c18): recover stale catalog dependencies`, push origin/6.0, then stop.

**P2/deferred / release rules:** full graphical Tauri/Windows E2E and broader manual
device qualification remain C22/C23/PF6.0 hardening. Child manifests/physical history
cleanup/compression/content/game remain later frozen scope. Registration remains
CLOSED until owner stabilization/dogfooding, diagnostics/release blocker review,
final terminology audit and critical manual tests, followed by explicit opening;
PF6.0/RC never opens it automatically. C22/PF6.0 final terminology audit preserved.
C21 remains local browser build → Tauri dependency audit → browser adapters → stable
local Web → VPS/production. No C18.5 work. **C18 IN PROGRESS; official progress77.0%.**
After independent acceptance, recommend bounded **C18.5.01 — CONTENT ENTITY CONTRACT /
NOTE GATE / DEPENDENCY SUBSTRATE**; recommendation only, no implementation here.


## C18.4 final independent remote acceptance — 2 October 2026

Owner-supplied independent verification for implementation SHA
`ddfe65c5b606fca259a88bfc6644074098e9faac`:

- [SQLite sync substrate tests 37004006923](https://github.com/nevskyforever/nfprogress/actions/runs/37004006923) — **SUCCESS**: Python SQLite substrate and Rust SQLite substrate / Windows.
- [Cloud backend tests 37004006914](https://github.com/nevskyforever/nfprogress/actions/runs/37004006914) — **SUCCESS**: Frontend admin and PostgreSQL cloud backend.

**C18.4.07 — REMOTELY ACCEPTED.** **C18.4 STRUCTURAL / CATALOG ENTITIES — CLOSED.**
C18.4.06 found no P0; P1-01 remains fixed; C18.4.07 resolves P1-02. No new P1
remains; other matrix items are PASS or legitimate later-stage/P2 deferrals.
This closure uses the owner's independent evidence; Codex did not inspect Actions.
C18 remains **IN PROGRESS**, official progress exactly **77.0%**. No partial points.

## C18.5.01 — Content entity contract / Note gate / dependency substrate

Branch `6.0`; preflight cwd `/Users/romankisockin/Desktop/nfprogress/ts_migration`,
clean starting HEAD == local `origin/6.0` == `ddfe65c5b606fca259a88bfc6644074098e9faac`.
This is production **reader readiness**, with new Note migration/publication and
writers dormant. Legacy Project HTML writers/readers continue unchanged. C18.4
stays CLOSED; C18.5 and C18 stay IN PROGRESS at **77.0%**.

### Explicit format and routing

Next unoccupied entity codec **8**, codec version **1**, WORTA-C1 frame version
**1**, compression ID **0**. IDs1–7 remain metadata/Stage/Stage-order/catalog;
none is reused. Frame = ASCII `WORTA-C1`, bytes `[1,8,1,0]`, two identical
big-endian u32 payload lengths, canonical UTF-8 JSON. No compression or decoder
fallback. New opaque mode3 descriptor is `entity_type=note`, `operation=event`,
`deleted_at=null`; the actual upsert/delete/resolution is authenticated inside.
C11 crypto1/AAD1 and project Note key/context stay unchanged; account crypto2/2
cannot authenticate this route. Legacy outer upsert/delete explicitly use frozen
Note v1, outer resolution explicitly uses frozen resolution v2. Their bytes,
serializers, vectors and history are unchanged.

New admitted Note variants: **Project HTML, Project plain, Stage HTML, Stage plain**.
Source is exactly `project`, map/node IDs are null. No format conversion. Mindmap
Notes are class B materialization of future map authority; `content_note_map_owned`
retains source/event and grants no independent ACK/publication authority.
Unknown source or unclassified extension metadata uses `content_note_unsupported_source`;
unknown content format uses `unsupported_content_format`. No source/owner/format
move contract is introduced, including after the visible Note has been tombstoned.

### Canonical plaintext and field allowlist

Strict root (no extra fields):

```json
{
  "version": 1,
  "account_id": "canonical account UUID",
  "device_id": "canonical source device UUID",
  "dependencies": {
    "bootstrap_id": "canonical bootstrap UUID",
    "metadata_event_id": "canonical metadata event UUID",
    "stage_event_ids": []
  },
  "event": "exact embedded ordinary Note v1 or resolution v2 object"
}
```

`event` is an object, not a JSON string; the placeholder above refers to the
frozen C15/C17 structural schemas. Ordinary event fields are exactly
`version/header/mutation/note`; header is exactly event_id/parent_event_id/
project_id/entity_id/entity_type/operation/revision/updated_at/deleted_at.
Mutation create/update/delete keeps existing revision/parent/tombstone rules.
Resolution event is exactly version/header/mutation/resolution/result; retains
additional parent IDs, exact full-tip generation/set, strategy, selected/retained
IDs and the existing result/keep-both contract. All duplicated identity/route,
revision and timestamp facts must match the immutable authenticated inbox.
Timestamps validate identity and display data, never choose a winner.

Portable Note record fields (actual current model): `id`, `project_id`, `stage_id`,
`source_type`, `source_map_id`, `source_node_id`, `content_format`, `title`, `content`,
`checklist` (exact id/text/checked), `color`, `pinned`, `archived`, `sort_order`,
`tags`, `created_at`, `updated_at`, `metadata`. **metadata must be exactly `{}`**;
unclassified extensions are retained and block, never silently dropped.
Tombstone contains the seven route fields plus deleted_at. sort_order stays in
this Note conflict unit; no separate Note-order authority.

Excluded local/computed fields: revision bookkeeping outside the authenticated
header, display_title, system_tags, owner_type/owner_id/owner_order, stage_name,
read_only, editor focus/selection, local errors, migration/sync bookkeeping,
paths and diagnostics. Local rows are not scanned or stripped. An incompatible
existing local source/metadata row blocks remote overwrite and remains retained.

### Frozen resource bounds

- Canonical JSON **8,388,588 bytes** (8 MiB minus the 20-byte frame); frame
  **8,388,608 bytes**. This fits the unchanged encrypted object cap8,388,624 bytes
  including the 16-byte AEAD tag. Legacy v1's plaintext limit remains8 MiB.
- content7 MiB; title512 KiB; color512 UTF-8 bytes; Note/project/Stage/checklist IDs512 UTF-8 bytes.
- tags4096, each16 KiB UTF-8; checklist16384, each text64 KiB UTF-8, exact boolean checked.
- metadata extension count0; JSON depth12, total value nodes131072; malformed UTF-8/lone UTF-16 surrogates reject.
- resolution parents/tips64; ordinary parent1; sorted unique Stage event references0 for Project,1–64 for Stage.
- Stage ancestry256 distinct traversed nodes; metadata dependency256 per unit /65536 aggregate accepted catalog proof budget.
- read limit1–32, passes1–8; default8 ×4. Scope/auth-epoch keyset cursor is ephemeral,
  advances across cycles, resets at end-of-list and retries retained blockers.

Exceeded bounds preserve original encrypted source/event, produce a durable
resource blocker, and grant no partial projection/ACK. Oversized authenticated
frames are not duplicated into a plaintext receipt. Transport resource limits
remain unchanged.

### Dependency and native apply contract

Project proof consumes accepted C18.4 metadata/catalog coverage: explicit same
account/project binding and bootstrap, frozen applied non-delete metadata,
current active authority, authenticated scoped bounded causal coverage. Historical
metadata ledger alone cannot bypass current unresolved/local-divergent authority.

Stage proof consumes accepted Stage ancestry: same account/project/stable Stage
ID, frozen live authenticated references, one resolved live current tip, matching
local structural projection, no entity conflict or unsupported local Stage fields.
The consumer checks the named Stage only, using accepted snapshot/projection facts;
it does not load every unrelated Stage branch. A→B causal rename covers A;
matching names, timestamps or sequence proximity never prove ancestry. Unknown,
foreign/unrelated Stage or unresolved tips block. Current tombstone yields
`stage_tombstone_child_manifest_incomplete`; Note and Stage history/children remain,
with no fake Stage creation, physical cleanup or ACK.

TS performs C11 AEAD before frame validation/native submission; native rechecks
scope, immutable inbox/envelope identity and all dependencies inside the same
privileged IMMEDIATE transaction as C15/C17 projection/history/conflict application.
Schema32 adds only `cloud_content_note_receipts`: exact bounded frame + original
nonce/ciphertext/sequence, waiting/applied/conflict_preserved outcome and blocker.
Identity/frame/source bytes are immutable; completed outcome is final; no delete.
Waiting survives reopen and is not ACK authority. C17's existing resolution insert
and parent proof guards gain exact framed-receipt alternatives in forward32;
all legacy branches and historical migrations stay unchanged.

C15/C17 remain the single Note causal/conflict engine. Concurrent edit and delete
versus edit retain all branches; full-tip resolution applies exactly once; stale
decision cannot collapse a later child. Native failure rolls back receipt,
history and projection together. Replayed applied/conflict events retain their
original bytes and prove the same result without reopening current dependencies.
Common ACK requires exact completed frame/envelope/identity plus matching existing
history/conflict/resolution evidence and the existing complete conflict-tip proof.
A received/waiting/unsupported source never fills the shared ACK hole.

Durable blockers reuse project_metadata_authority_unresolved, stage_dependency_missing,
stage_dependency_proof_limit, stage_tombstone_child_manifest_incomplete,
unsupported_content_format, invalid_note_payload and decrypt_failed; new bounded
codes are content_note_codec_unsupported/content_note_map_owned/
content_note_unsupported_source/content_note_scope_mismatch/content_note_resource_limit.

### Production reader, diagnostics, server and future writer gate

Production mode3 dispatcher runs metadata → Stage → framed Note → account reader
before common ACK, with bounded retries and authoritative auth/key leases. Legacy
Note readers still process their independent explicit routes. No format sniffing.
Wrong codec IDs/versions/compression/length/canonical bytes reject; metadata,
Stage/order, catalog/future account and legacy Note bytes never fall back into8.

Backend change is only the mode3 opaque Note `event` allowlist and pull route.
Modes1/2 reject it; registration/binding, immutable replay and C11 envelope
checks stay intact. Server receives no Note content/title/tags/checklist/color/
pin/archive/Stage name or plaintext dependency semantics. No new endpoint.

Safe local diagnostics record frame receipt/apply/blocker/conflict status only,
with mirrored TS/Rust scalar allowlists. No names, content, UUIDs, ciphertext,
nonce, keys or tokens; no telemetry. Existing centralized friendly format,
dependency, conflict and resource messages are reused; technical codes stay in
details. No major UI/new labels/help claim is added. Existing help remains accurate
for activated Project HTML sync; Stage/plain publication is not advertised.

Before a future writer emits: active metadata authority; active Stage authority
when scoped; explicit participating-reader support for codec8; classified source,
format and local fields; durable candidate/outbox; explicit migration consent and
safe coexistence with old history. Transport-version3 alone is **not** the future
codec capability proof. Reader capability negotiation, capture/migration/writers
and new-format self-echo publication are deferred to C18.5.02. No publication on
login/startup/unlock/open/pull/background cycle is introduced by this slice.

### Local verification and remaining boundary

Stable `contentNoteCodecV1.json` adds four Project/Stage plain/HTML vectors with
canonical JSON, UTF-8 hex, frame hex, IDs/dependencies and explicit format numbers.
Production TS serializers match independent native serde validation; old fixtures
and crypto vectors unchanged. TS reader tests use actual production C11 AEAD;
native dependency/transaction fixtures inject at the authenticated IPC boundary
and do not claim Rust AEAD. PostgreSQL checks blind transport separately.

Local focused verification: frontend81 tests in12 files; typecheck and production
build PASS (existing chunk/dynamic import warnings). Rust Note filter165 tests,
including12 new reader/dependency/atomic/conflict tests; Stage20, metadata19,
SQLite29, diagnostics5 PASS; cargo check PASS (existing warnings). Python focused
SQLite/API252 PASS; final schema32 subset127 PASS plus receipt-focused35 PASS.
PostgreSQL transport/regressions43 PASS,0 skipped, on disposable PostgreSQL16; final Note transport2 PASS. Python fail-closed cross-runtime UDF2 PASS.
Workflow mandatory commands include the new codec/reader/native/schema32/transport
checks; PostgreSQL timeout remains40 minutes. No new Vue interaction requires
Chromium; no full Nuitka/platform build claim. git diff --check PASS.

C18.5.01 **LOCAL COMPLETE / REMOTE CI PENDING** after authorized commit/push;
expected Cloud backend tests and SQLite sync substrate tests. Codex stops after
push and does not poll Actions. No maps/documents/progress/game/compression,
C18.6+ or C21 implementation. Next: **C18.5.02 — NOTE EXPLICIT MIGRATION /
STAGE+PLAIN WRITERS / MULTI-DEVICE ACCEPTANCE**, including reader capability gate,
explicit local candidate capture, ordinary writers/conflict UI and two-device
PostgreSQL acceptance. This slice does not claim that activation or acceptance.

Permanent rules preserved: public registration CLOSED until owner dogfoods,
stabilizes/fixes blocking bugs, reviews diagnostics, completes final terminology
audit, repeats critical manual scenarios and explicitly opens registration;
PF6.0/RC completion does not open it. C22/PF6.0 final terminology audit remains
required. C21: local browser build → Tauri dependency audit → browser adapters →
stable local Web → VPS/production. Official progress remains exactly77.0%.


## C18.5.01 — independent remote acceptance

Owner-supplied independent GPT verification for implementation SHA
`c01ed8cd965a0e48fefb4f5b147ff3a99eccca31`:

- [SQLite sync substrate 37014080772](https://github.com/nevskyforever/nfprogress/actions/runs/37014080772) — **SUCCESS**.
- [Cloud backend 37014080630](https://github.com/nevskyforever/nfprogress/actions/runs/37014080630) — **SUCCESS**.

**C18.5.01 — REMOTELY ACCEPTED.** C18.4 remains CLOSED.
C18.5 and C18 remain **IN PROGRESS**. Official progress remains exactly **77.0%**;
no partial roadmap points. Evidence was supplied independently by the owner;
Codex did not inspect or poll GitHub Actions.

C18.5.02 preflight: cwd `/Users/romankisockin/Desktop/nfprogress/ts_migration`,
branch `6.0`, clean HEAD == local `origin/6.0` ==
`c01ed8cd965a0e48fefb4f5b147ff3a99eccca31` before changes.
The complete C18.5.02 task and the owner's continuation decision have been received.
SyncDevice remains a non-secret account-scoped transport identity. Codec capability
declarations are authorized by the authenticated account and restricted to device
IDs registered to that account. Production clients declare capabilities only for
their persisted local device ID. C18.5.02 does not introduce device PKI or
cryptographic device self-attestation. The stricter per-device cryptographic-auth
requirement was rejected by the owner as outside the current frozen trust model
and scope; the accepted account/device authorization model is preserved.
This acceptance record is retained as part of C18.5.02. Permanent release/terminology/C21 rules remain unchanged.


## C18.5.02 — local implementation / remote CI pending

Explicit Cloud “Опубликовать заметки” activates Project plain, Stage plain and
Stage HTML writers after the all-registered-device capability gate and verified
self-echo. Required evidence: mode3/frame1/codec8v1/compression0/ordinaryv1/
resolutionv2. PostgreSQL migration `c18_note_readers` is the single Alembic head;
same-account registered UUID authorization is preserved, foreign/unregistered
declarations rejected, production uses its persisted device ID. No device PKI.

SQLite33 atomically retains deterministic migration candidates, source and
generation evidence, canonical frames, future IDs, causal parents and metadata/
Stage dependencies. Local/captured/publication/self-echo/active/conflict/blocked
states survive restart. Unsupported source evidence is retained without field
dropping; map Notes stay local with no independent event/ACK. Local-only projects
remain excluded. Exact sealed replay and fair bounded queue scans are durable.

Existing Project HTML remains on its single C15/C17 v1/v2 writer, including
future Project HTML creates. No old history/ciphertext rewrite or duplicate
genesis. The new forms use the same ordinary/resolution queues with codec8
sidecars; after activation/import, ordinary create/edit/portable metadata/delete
works automatically. Post-capture local drafts become later causal events after
self-echo; child publication waits for authenticated parents. Ownership/format
transitions are rejected. Stage rename reuses proven ancestry; tombstones or
unresolved dependencies retain Note data and block unsafe apply without cascade.

C17 handles edit/edit, delete/edit and explicit full-tip choices with local CAS.
Later branches reject stale choices. Local same-ID unauthenticated content is
retained alongside remote evidence, requiring explicit choice; keeping it creates
a child of the imported authenticated parent. Already-published competing genesis
roots remain honestly blocked rather than fabricated or overwritten.
Shared contiguous ACK uses existing exact inbox/frame/encrypted-pair/sequence/
dependency/apply proofs, never capability declaration alone. Lost upload response
and reopen retry preserve exact event/frame/dependencies/nonce/ciphertext.

Bounded real PostgreSQL16 acceptance uses production TS C11 and two distinct
file-backed native SQLite devices. It covers legacy H1 coexistence, explicit
P1/S1/S2 publication, M1 exclusion, missing third-device capability then readiness,
local B candidate reconciliation, lost-response duplicate retry/reopen,
ordinary creation of all new forms, metadata edits, Stage HTML deletion,
concurrent Stage plain edits, later third branch/stale choice rejection,
full-tip convergence, Project plain delete/edit preservation and common ACK.
A blocked local-candidate prefix prevents advancing over later applied Notes;
native dependency tests additionally cover unresolved Stage prefixes and recovery.

Local validation: Python affected SQLite suites181 PASS, including every supported
prefix0–32, populated32 preservation and reopen. Remaining SQLite CI modules:
72 PASS; two historical fixtures updated for schema33, focused rerun2 PASS
(255 distinct SQLite/API checks across the bounded pass and repairs). PostgreSQL capability/foundation/
acceptance16 PASS; final resolved-state acceptance1 PASS.
Rust Note engine165, framed reader/writer15, project lifecycle5 and diagnostics5
PASS; cargo check PASS. Frontend focused91 tests PASS; final changed-area pass53
PASS, final UI/store/diagnostics38 PASS; TypeScript typecheck/production build PASS.
Help/localization29 PASS,1 deselected: native macOS Help bridge aborts in the
headless environment; no bridge code was changed. All five non-Russian locales
have complete new Note UI/help strings. Chromium verified real plain-text dialog
hydration/edit/save with literal HTML-looking text on isolated fixtures.
No full Nuitka/platform build claim; existing Rust/build warnings remain.
Final diff/syntax/import checks PASS; protected engine/game_data pyc unchanged.
Temporary PostgreSQL and isolated Web processes were removed/stopped.

Diagnostics use allowlisted codes/counts without content or telemetry.
User-visible publication, device-update blockers and Note version choice use
central presentation/localization. Dedicated help describes the real boundary.
C11, codec8/frame versions and fixtures, compression and game behavior unchanged.
No map/document/progress/game authority or C18.6+/C21 implementation.

C18.5.02 LOCAL COMPLETE / REMOTE CI PENDING after authorized commit/push;
expected Cloud backend tests and SQLite sync substrate tests. PostgreSQL timeout
stays40 minutes. Codex stops after push without inspecting/polling Actions.
C18.5/C18 remain IN PROGRESS, C18.4 CLOSED, official progress exactly77.0%.
Registration CLOSED until explicit owner decision after dogfooding/stabilization;
C22/PF6.0 final terminology audit and C21 local browser → Tauri audit → adapters →
stable local Web → VPS order preserved. Next recommendation only:
C18.5.03 — MAP AUTHORITY / DERIVED NOTE ANNOTATIONS / ATOMIC APPLY.


## C18.5.02 — independent remote acceptance

Owner-supplied independent verification for implementation
`33f0e1cdd0be7f8f3a216fc7635005160562f26d`:

- SQLite sync substrate [37057286547](https://github.com/nevskyforever/nfprogress/actions/runs/37057286547): SUCCESS; Python SQLite and Rust Windows jobs SUCCESS.
- Cloud backend [37057286590](https://github.com/nevskyforever/nfprogress/actions/runs/37057286590): SUCCESS; Frontend admin and PostgreSQL jobs SUCCESS.

**C18.5.02 — REMOTELY ACCEPTED.** C18.5/C18 remain IN PROGRESS;
official progress exactly77.0%. Codex did not poll Actions.

C18.5.03 preflight: cwd `/Users/romankisockin/Desktop/nfprogress/ts_migration`,
branch6.0, clean HEAD == local origin/6.0 ==
`33f0e1cdd0be7f8f3a216fc7635005160562f26d`.
Project/Stage maps become separate canonical authorities; combined view stays
derived. Map-derived Note text and annotations belong to the map, with atomic
local projection and no independent Note event/ACK. Implementation in progress.
Registration/terminology/C21 gates and all accepted C11/Note contracts preserved.

### C18.5.03 retained foundation and completed production authority (not remote acceptance)

Implemented codec9/version1/frame1/compression0 TS/native foundation with three
shared frame vectors, fractional-coordinate canonicalization, 8 MiB aggregate
UTF-8 budget, existing depth512/node50,000 limits, extension/reference/identity
blockers and floating-parent cycle rejection. Added separate map descriptor/API
helpers and normalized account-wide map reader evidence at Alembic head
`c18_map_readers`. Real isolated PostgreSQL checks cover a third Note-capable but
map-incapable device, exact opaque replay, reader downgrade, populated prior-head
upgrade/repeat upgrade and retained-history downgrade refusal.

Fixed the proven existing native map Note text edit regression: legacy floating
Notes work without `freeNodes`; matching native/legacy twins receive the same
text. This creates no independent Note event or additional canonical authority.

Verified during this continuation: PostgreSQL18 focused checks, frontend12
codec/transport checks, native5 codec checks and native6 mindmap checks; TypeScript
typecheck, frontend production build, cargo check and `git diff --check` passed.
Production map authority is locally complete on forward-only SQLite schema34.
All earlier partial work was preserved. The continuation started at HEAD ==
local origin/6.0 == `33f0e1cdd0be7f8f3a216fc7635005160562f26d`, with the deliberately
dirty authorized C18.5.03 worktree. Protected Python bytecode remains untouched.

- Explicit **Опубликовать карты** atomically captures Project and each Stage owner,
  exact event/dependencies/parents/frame, immutable source and Note annotation
  evidence. Opening, login, unlocking, reader declaration and background sync do
  not capture maps. Absent migration is displayed as local without creating rows.
- Per-owner captured/publication_pending/self_echo_pending/active/conflict/blocked
  state survives restart. Candidates/events/ciphertext/decisions/apply receipts
  are retained. Ordinary writes freeze complete new maps; later edits are durable
  drafts, never mutations of sealed history. Verified self echo activates authority
  and recovers lost HTTP receipts with exact descriptor/ciphertext replay.
- Map-owned linked Note text/title/checklist/tags/color/pin/archive/order/metadata
  and creation time migrate once by verified map/node/Note identity. Ambiguous
  links, global Note-ID collisions and unsupported extensions block capture with
  original evidence intact. Canonical timestamps/numbers do not lose source evidence.
  Project HTML v1/resolution-v2 and codec8 Notes retain their established authority.
- Native Project/Stage saves and linked Note text/annotation/delete/reorder writers
  produce map history only. SQLite Note rows are projections; there are no separate
  derived-Note events, outboxes, apply receipts or ACK units. Strict writers validate
  original data before renderer normalization can discard malformed nodes.
- One existing private remote-apply transaction covers map/tree/annotations,
  derived Note creation/update/removal, history/tips/projection, local candidate,
  inbox/conflict/apply receipt and own upload recovery. Fault injection proves full
  rollback; no Note capability or synthetic Note history authorizes map projection.
- Full-tip whole-map conflicts preserve all versions and dirty/preexisting local
  candidates. Decisions bind exact rendered tips and full local CAS; resolution uses
  max(parent revision)+1. Cloud or local versions are selected explicitly. A late C
  after R(A,B) retains R+C. Stale decisions retain evidence and publish nothing.
- Metadata/bootstrap ownership and live Stage ancestry are rechecked. Stage rename
  ancestry is accepted; Stage tombstones block children without deleting maps/Notes.
  Map tombstones remove only that owner's derived Note projections atomically.
- Combined view has no cloud entity. Editor lifetime CAS includes every displayed
  owner, local data/annotations, map and metadata/Stage heads. All owners/drafts/
  outboxes/group evidence commit together; any stale owner or failed final write
  rolls back the entire local group. Background refresh cannot replace rendered CAS.
- Maps share the established contiguous sequence and ACK with metadata/Stages/
  catalog/Notes. Exact immutable map receipts prove ACK eligibility; blocked N
  prevents N+1 crossing, while later independent events may apply. B's existing
  local map is retained and requires explicit reconciliation. Unbound/local-only
  projects are excluded from map publication.
- Local-only privacy-safe diagnostics and friendly explicit publication/conflict
  UI are wired into the mode3 runtime. Help and RU/EN/ES/DE/FR/PT_BR catalogs describe
  map ownership, capability blockers, replay and combined-save restrictions.

Validation during continuation:
- Mandatory real PostgreSQL16 + production TS C11 + two file-backed native SQLite
  map acceptance PASS, no skips: Project/Stage/annotations, Note-only third-device
  gate, exact retry/lost receipt/restart, second-device local reconciliation,
  concurrent maps/full-tip resolution, linked Note edits/deletion, combined group
  rollback/stale CAS, Stage rename ancestry, missing parent retry and blocked shared
  ACK with a later independent legacy Note. Final map/gate/codec8 acceptance: 5 PASS.
- Python SQLite CI-equivalent: **291 PASS**, including fresh/prefix0..33/populated33
  schema34 upgrades, reopen, existing data/trigger preservation and recovery/API.
- Native map authority: **7 PASS**; map codec5; SQLite29; Note sync165; binding10;
  repository5; metadata19; Stage20; diagnostics5; developer5; account transport4;
  catalog14; content Note15. cargo check PASS. Windows is wired into remote CI.
- Affected frontend: **88 PASS** in 12 files, including editor-CAS and map-cycle
  change reporting/ACK ordering/lost-upload recovery; typecheck/build
  PASS. Chromium explicit publication/full-tip selection PASS. Help/localization:
  30 PASS, all five translated languages have zero missing strings. Fixture and
  C11 cross-identity foundation checks remain green. `git diff --check` PASS.

CI now requires map schema/native/codec/runtime/UI tests and real map acceptance
without skips. Remote CI remains **PENDING — not polled by Codex**; expected
workflows: Cloud backend tests; SQLite sync substrate tests. Independent GPT remote
verification remains required. C18.5/C18 IN PROGRESS, official progress **77.0%**;
C18.4 CLOSED. Release registration gate, owner stabilization decision, terminology
C22/PF6.0 and C21 local-Web-first rules remain unchanged. Documents/Progress/Game,
compression, telemetry and C18.6+/C21 implementation are outside this slice.
Next recommended slice after independent acceptance:
C18.5.04 — DOCUMENT AUTHORITY / SCOPE MOVE / EXTENSION BLOCKERS.


### C18.5.03 remote CI harness correction — independent result and local repair

Implementation SHA: `6b3b19f860a87b9ecf2f4e3ecd835adbb3587833`.
Independent verification supplied by GPT: SQLite workflow `37107105194` —
**SUCCESS**, Python and Rust/Windows jobs green, including
`Verify map codec and durable authority`. Cloud workflow `37107105174`:
Frontend admin **SUCCESS**, PostgreSQL **FAILURE** in mandatory no-skip acceptance
(`1 failed, 38 passed`). At correction preparation time C18.5.03 was **NOT remotely accepted**; this historical status is superseded by the independent acceptance below.

Exact failing test:
`tests/test_cloud_c18_authority_cross_runtime.py::test_metadata_migration_import_mismatch_and_concurrent_rename`.
Exact error: `sqlite3.OperationalError: no such function: note_sync_remote_apply_authorized`.
Classification: **CI/test-fixture connection initialization regression**.
Schema34's persistent map UPDATE guards resolve the connection-scoped C15.7B UDF
while preparing ordinary SQL, even before map activation. The historical fixture
opened raw Python SQLite and performed a Project UPDATE without initialization.

Minimal test-only correction: call the existing
`register_remote_apply_authorization_guard(db)` before that fixture UPDATE.
It always returns **0**, matching ordinary production Python/native connections;
no remote capability or authorization rows are created. Production initialization
already installs the fail-closed function; **no production defect found and no
production code changed**. Schema34, triggers and map/Note/ACK authority unchanged.

Neighboring mandatory raw SQLite writes audited: remaining Project/Stage INSERTs
have no applicable UDF-bearing INSERT guard; ordinary Note INSERT fixtures already
register the fail-closed function. Read-only connections and isolated crash-trigger
DDL require no change. No broad helper/suite refactor.

Real two-device map acceptance additionally checks the ordinary initialized
connection's UDF returns 0 and rejects both an active Project map UPDATE and
its derived Note DELETE with the expected guards, preserving both payloads.
Original failure reproduced locally; exact corrected test **1 PASS** against
isolated PostgreSQL + file-backed native SQLite. One bounded mandatory Cloud
CI-equivalent PostgreSQL acceptance pass: **39 PASS, 0 skips** (533.18 seconds),
including metadata, maps, content Notes and the new fail-closed assertions.
Changed Python files parse successfully; `git diff --check` PASS. Protected
engine/game_data `.pyc` files untouched. Frontend/Rust not rerun: no code changed
and original independent SQLite/Windows and frontend jobs are green.

Correction status: **C18.5.03 CORRECTION — LOCAL COMPLETE / REMOTE CI PENDING**
after correction commit/push. Remote acceptance requires independent verification
of the new SHA.
Remote CI will not be polled by Codex. Expected workflows: Cloud backend tests;
SQLite sync substrate tests. C18.5 and C18 remain **IN PROGRESS**, official progress
**77.0%**. All permanent release/terminology/C21 rules remain unchanged.
No C18.5.04, Documents/Progress/Game, compression, C11 or codec8 changes.


### C18.5.03 independent remote acceptance; C18.5.04 started

**C18.5.03 — REMOTELY ACCEPTED**. Implementation
`6b3b19f860a87b9ecf2f4e3ecd835adbb3587833`: SQLite `37107105194` SUCCESS
(Python and Rust/Windows). Initial Cloud `37107105174`: Frontend SUCCESS,
PostgreSQL fixture initialization FAILURE as recorded above. Correction
`6f5ed95f1fb479cce3b3d246179068b918a525f0`: Cloud `37111787798` SUCCESS,
including mandatory ACK/multi-device acceptance, focused API, frontend,
typecheck/build. No correction SQLite run was required: production/native/schema
are identical to the accepted implementation. Independent results supplied by GPT.

C18.5.04 DOCUMENT AUTHORITY / SCOPE MOVE / EXTENSION BLOCKERS started from clean
branch6.0 HEAD/origin `6f5ed95f1fb479cce3b3d246179068b918a525f0`.
C18.5/C18 **IN PROGRESS**, official progress **77.0%**. No C18.5.05/C18.6 work.


### C18.5.04 — local implementation and acceptance

Status: **LOCAL COMPLETE / REMOTE CI PENDING**. Implementation SHA:
`cb120044763ba4e57094d561ebbbac86b83cc418`
(`feat(c18): activate encrypted document sync`). This checkpoint-only follow-up
records the exact validated implementation; published SHA is reported in the task result.
C18.5 and C18 remain **IN PROGRESS**; official progress remains exactly **77.0%**.
Permanent public release registration remains CLOSED pending C22/PF6.0 owner
stabilization; final terminology audit and C21 local-Web-first rule preserved.

Codec10/version1, frame1, compression0. Frozen portable fields:
`id/project_id/stage_id/title/content_json/content_format/created_at/extensions`.
Stable Document ID survives all supported same-project scope moves; cross-project
moves and occupied target scope are rejected. Current editor Tiptap nodes/marks
are strictly checked; frame8 MiB, 50k nodes, depth60, text1 MiB, attribute2 KiB,
64 parents/dependencies, causal proof4096, bounded cycle default8×4/hard32×8.
Empty extensions only. Unsupported extensions and migration orphan evidence are
retained verbatim locally and cannot become lossy cloud documents.

Schema35 and Alembic `c18_document_readers`; explicit project consent and reader
gate for all registered devices. Existing legacy migration marker respected;
SQLite documents are capture source. Durable captured/publication/self-echo/
active/conflict/blocked states, exact sealed retry and lost-response recovery.
Production editor/title/move/delete/accepted-Word writers use snapshot+heads CAS.
Paths/bindings remain local; file proposal revalidated; delete retains history and
external files. Atomic private native apply and exact contiguous shared ACK.

Acceptance: real PostgreSQL16 + two file-backed SQLite devices + production
TS C11/native codec10; Project/Stage publication/import, ordinary edits on A/B,
three move directions, collisions, concurrent edit/move/move/delete branches,
full-tip resolution and stale choice, Word import/file retention, lost upload
response and third-device reader gate. Server plaintext inspection passed.
Native negatives cover unsupported extensions/reopen/lossy replacement,
orphan/incomplete migration, foreign scope/object/replay, missing parents,
fabricated/tombstoned Stage, collision rollback and blocked contiguous ACK.
Cross-language Project/Stage/delete fixtures match. Focused tests and known
platform limitations are recorded in the final task result. No Actions polling
is authorized after push; independent remote acceptance remains required.

Final local validation: schema35 fresh/every prefix/populated34/reopen **36 PASS**;
affected Python SQLite/metadata/recovery **261 PASS**; help/localization/C9
**72 PASS** (one native macOS Help bridge test deselected after process abort
in this headless environment). Five non-Russian locales: **0 missing strings**;
existing translations unchanged. TypeScript/Vue focused integration **55 PASS**;
Chromium production Document panel with isolated store **PASS**; typecheck and
frontend build **PASS** (existing bundle warnings only). Rust codec/authority
**9 PASS**, document compatibility **10 PASS**, Note/shared-ACK **165 PASS**,
SQLite **29 PASS**, diagnostics **5 PASS**, cargo check **PASS**. PostgreSQL
capability/migration **3 PASS**, final production two-device acceptance **1 PASS,
0 skips**, now including frozen Stage-reference rename ancestry and Stage
tombstone edit/move blockers. Shared backend/auth/migration affected pass:
**41 PASS** after focused Alembic-head expectation repair. Diff check **PASS**;
protected bytecode, C11, codec8/9, Progress/Game/compression untouched.

### C18.5.04 independent remote acceptance; C18.5.05 started

Independent acceptance: implementation `cb120044763ba4e57094d561ebbbac86b83cc418`,
published/checkpoint SHA `ef89ff728b1daf179037d61f35042f8c59cc0c2f`.
SQLite sync substrate run `37124209205` — SUCCESS. Cloud backend run
`37124209225` — SUCCESS, including PostgreSQL, native document codec/authority,
mandatory ACK/multi-device acceptance, focused APIs, frontend and typecheck/build.
**C18.5.04 — REMOTELY ACCEPTED** (supersedes its local/pending record above).

C18.5.05 started from clean branch `6.0`; HEAD and origin/6.0 both matched
`ef89ff728b1daf179037d61f35042f8c59cc0c2f`. C18.5 and C18 remain IN PROGRESS;
official progress remains exactly77.0%. Game authority is outside this slice.


### C18.5.05 — causal Progress authority and local acceptance

Status: **LOCAL COMPLETE / REMOTE CI PENDING**. Started from
`ef89ff728b1daf179037d61f35042f8c59cc0c2f` on branch `6.0`.
C18.5 and C18 remain **IN PROGRESS**, official progress exactly **77.0%**.
Public release registration remains CLOSED pending C22/PF6.0 owner stabilization;
final terminology audit and C21 local-Web-first rule preserved.

Progress uses codec **11/version1**, frame1, compression0 and unchanged production
C11 encryption. Codec8 Note, codec9 Map and codec10 Document contracts and historical
readers remain unchanged. The canonical action fields are
`entry_id/new_total/delta/unit/occurred_at/writing_time/writing_day`.
Amounts are physical **symbols**, fixed signed decimal strings with six places;
absolute totals and genesis bases are nonnegative. Stable entry identity is retained
for original facts; event IDs identify immutable causal operations. Chain scope is
`(account, project, project)` or `(account, project, stage:<stable Stage ID>)`.
Project and Stage chains have separate genesis, parents, tips and projections.

Legacy capture follows relational `progress_order`, never timestamps. Base is the
first absolute symbols minus its delta; an empty nonzero history has an explicit
base without a fabricated writing action. Every step must agree within the frozen
one-micro-symbol compatibility tolerance; final displayed total must agree with the
existing unit conversion. IDs, timestamps, physical columns, missing order,
unsupported extensions and ambiguous mixed root/Stage histories fail closed and
retain immutable raw evidence. Genesis carries a frozen count/final-total coverage
proof; 256-fact migration batches resume from a durable cursor. Partial migration
never replaces the complete current history or exposes a partial derived total.
The native 600-fact acceptance reopens between 256/256/88 batches.

Historical unit is portable and never rewritten after metadata changes. Unknown
legacy display-unit provenance is recorded as symbols using its existing physical
symbol fields. Current projections use existing ceil page rounding and half-even
0.1 author-list rounding. On an ordinary append across a recorded unit change, its
proven base is the previous immutable absolute symbols projected through the existing
new-unit display rounding and converted back to symbols; this preserves the user's
visible action delta without inventing an adjustment action. The action unit is
checked against referenced authenticated historical metadata/Stage frames. Accepted
old facts remain readable after metadata renames or later unit changes. Rebase copies
explicit physical action deltas and preserves original historical unit/time/day.

Occurrence time uses the accepted strict UTC timestamp contract. Legacy naive time
with unknown original zone remains in `writing_time` verbatim, with no fabricated
UTC value. `writing_day` is an admitted versioned historical fact: current logical-day
rules depend on local timezone and the user's mutable start-day setting, so future
recomputation from UTC alone would change history. New writers freeze the existing
local logical-day rule at action time; legacy records retain their original date or
validated saved day. Projections retain the occurrence timestamp and expose the
frozen day separately; today/statistics group by it. `source_method` is excluded from
portable authority; local document bindings/domain-event provenance retain it.

SQLite schema **36**; backend Alembic **c18_progress_readers** after
`c18_document_readers`. All registered devices must advertise transport3 and the
accepted Note/Map/Document/Progress readers before publication; reader declaration
never captures data. Backend blocks both publication and unsupported-device pull
once Progress exists. Explicit connected-project publication alone captures history;
local-only projects never acquire a cloud binding. Durable captured/publication/
self-echo/active/conflict/blocked states retain source, exact frame, ciphertext,
receipts, decisions, branches and second-device local candidates across restarts.

Ordinary manual, in-app document and external Word writers use the same causal
Progress writer. Entry, derived rows, head and immutable outbox intent commit in one
immediate transaction; manual writes prove cached expected heads. Document source
hash/revision dedup and the local ProgressAdded event share that transaction. Remote
apply authenticates scope/object/dependencies and privately commits facts, derived
rows/order/scalars, head, inbox disposition and apply ledger atomically. Lost upload
responses recover through exact ciphertext retry or authenticated self echo.
Resolution only becomes authority after authenticated self echo.

Concurrent absolute totals preserve full independent branches; no automatic delta
sum and no timestamp winner. Explicit selection names all current tips. Explicit
rebase creates fresh IDs and preserves source action order. Correction/tombstone
must cover exactly the affected descendants with fresh facts; originals remain
immutable. Stale tips or changed local snapshots reject the decision. Independent
row scope moves, scalar overrides and order changes are guarded. `progress_order`
is solely a selected-chain projection: global compatibility positions stay contiguous,
per-scope order follows causality; gap compaction preserves other scopes' relative
order. Root history accepted before introducing Stages is retained, while current
Project totals derive from Stage totals and root ordinary writes are blocked.

Current total, percent, remaining, added_progress, today and statistics are derived
from selected facts plus current metadata, and can be rebuilt without publishing
scalars. Shared ACK requires exact Progress apply-ledger/object/inbox evidence.
Waiting or unsupported facts retain bytes and block the contiguous prefix; fully
preserved conflicts are ACK eligible. PostgreSQL acceptance proves missing-parent
Progress N blocks ACK while Document N+1 applies, then resumes after the parent.

Game remains local: one domain event for a successful local ordinary action; remote
import, replay, self echo, migration, resolution and rebuild produce zero game events.
Stable Progress entry IDs and existing document source IDs remain available for the
future explicit reward-once ledger. No Game cloud authority or completion/reward
synthesis is introduced. No compression or telemetry.

Frozen bounds: frame8 MiB, identity512 UTF-8 bytes, parents/dependencies64,
chain/DAG65536 facts/events, combined parent work2×65536, operation/descendants1024,
migration batch256, capture64 MiB, pending cycle8 events/2048 facts, absolute amount
1e12 symbols. Invalid/oversized/unproven events preserve evidence, do not partially
project and do not ACK. Cross-language Project/Stage/rebase fixtures and wrong-codec/
identity negatives pass. Diagnostics contain allowlisted codes/counts only.

Local evidence: PostgreSQL16 + two file-backed native SQLite devices + production
TS C11 proves Project/Stage genesis/import, concurrent A/B/B2, rebase, descendant
repair, derived rebuild, manual/document/Word writers, source dedup, reward boundary,
reader revoke, replay/lost-response and shared blocked prefix. Progress gate/schema/
acceptance **3 PASS, zero skips**. Earlier affected backend pass **25 PASS**, with two
obsolete Alembic expectations repaired and independently rechecked **2 PASS**.
Schema36 fresh/all0..35 prefixes/populated35/reopen **37 PASS**; affected SQLite CI
pass **364 PASS**, two fixture expectations repaired and rechecked **2 PASS**.
Native Progress/codec/production commands **9 PASS**; retained native SQLite18,
Document7, Note77 tests passed. Frontend focused acceptance **49 PASS**, additional
statistics/mapper26 and codec/runtime8 checks passed; typecheck/build **PASS**
(existing bundle warnings). Production Vue panel Chromium flow **PASS** using
isolated stores. Help/localization **29 PASS**; one existing native macOS Help bridge
case deselected after its known headless abort. All five non-Russian catalogs have
**0 missing strings**. Cargo check **PASS** (existing warnings). Protected engine/
game_data bytecode unchanged. Final full diff audit and diff check **PASS**.

Remote CI is pending independent verification of the published SHA; Codex must not
poll Actions after push. Expected workflows: Cloud backend tests; SQLite sync
substrate tests. Remaining C18.5 work: **C18.5.06 PROJECT / ACCOUNT GAME ACTION
LEDGERS / REWARD ONCE**; recommended only, not implemented in this slice.


### C18.5.05 — remote CI correction

Original published implementation: `fad87fc4111fe120de100094f5afdd1825bcfbd3`.
It is **NOT REMOTELY ACCEPTED**. The stored, completed logs were inspected before
editing and both failures were reproduced locally against this clean baseline.

SQLite run `37140312168` — **FAILURE**: Python SQLite substrate **SUCCESS**;
`Rust SQLite substrate` failed at `Run local diagnostics and developer streak
regression filters` (the diagnostics/developer regression step). Exact failing test:
`diagnostics::tests::diagnostics_frontend_and_native_allowlists_match`,
`src/diagnostics.rs:583`, `assertion left == right failed`. Frontend operations
started with the six Progress operations; native operations placed the same six
values after `note_migration`. All 36 values were identical as a set. Runtime
validation uses operation strings and allowlist membership, not ordinal identity.
Classification: cross-runtime allowlist ordering mismatch; not Windows-specific,
not a privacy failure, not a game/reward or SQLite schema defect. The frontend list
now follows the native ordered contract; the strict equality assertion is retained.
No allowlisted values or privacy filters changed. SQLite push/pull-request filters
now include `frontend/src/diagnostics/events.ts`, which this Rust test includes
at compile time, so the correction triggers the required workflow.

Cloud run `37140312183` — **FAILURE**: Frontend admin **SUCCESS**. Stored logs prove
`Run mandatory sync ACK and multi-device backend acceptance without skips` completed
with **46 PASS**, including Progress acceptance, before the later failure.
`PostgreSQL cloud backend` then failed at `Run focused cloud and legacy API tests`:
`tests/test_cloud_auth.py::test_c2_schema_and_repeated_head_upgrade`, line289,
`assert 'c18_progress_readers' == 'c18_document_readers'`; the rest had **193 PASS**.
The test calls `upgrade(..., 'head')` and correctly reaches the new Progress head,
but retained the previous Document-head literal. Classification: stale migration-head
expectation. Only that exact expected literal was updated. Repeated upgrade,
C2-prefix downgrade/reupgrade and all table assertions remain intact. Alembic has
exactly one head `c18_progress_readers`, directly after `c18_document_readers`.
No migration, schema36 rollback/renumber or schema37 was introduced.

Local validation: both exact failing tests independently pass. One bounded native
CI-step equivalent on macOS: diagnostics **5 PASS**, developer/streak **5 PASS**,
Progress codec/authority/local reward boundary **9 PASS**, cargo check **PASS**.
Frontend diagnostic privacy/retention/export **20 PASS** and typecheck **PASS**.
Schema36 fresh/every-prefix/populated35/reopen **37 PASS**. The single bounded local
Cloud focused-step equivalent, plus mandatory Progress acceptance: **197 PASS,
zero skips**; affected Python syntax and final diff check **PASS**.
No tests were skipped, ignored or removed; no assertions or privacy checks weakened.
Protected engine/game_data bytecode remains unchanged. Codec11/frame/compression
**11/1/1/0**, causal authority, derived totals/order/statistics, Stage dependencies,
conflict/rebase/correction/tombstone, remote reward boundary, exact ciphertext retry,
self echo and shared ACK remain unchanged; no C11/codec8/9/10, Game cloud authority,
compression or telemetry changes.

**C18.5.05 = LOCAL CORRECTION COMPLETE / REMOTE CI PENDING**.
C18.5 and C18 remain **IN PROGRESS**, official progress exactly **77.0%**.
Manual public-registration release gate, post-PF6.0/RC dogfooding/stabilization,
final user-facing terminology audit and C21 local-Web-first order remain unchanged.
After correction push, remote CI remains pending independent verification and Codex
must not poll Actions. Expected workflows: Cloud backend tests; SQLite sync substrate
tests. Next slice only after remote acceptance: **C18.5.06 PROJECT / ACCOUNT GAME
ACTION LEDGERS / REWARD ONCE**; not started by this correction.

### C18.5.05 — independent remote acceptance

**C18.5.05 = REMOTELY ACCEPTED**. Final accepted implementation and correction
SHA: `302a5fe1f7cda77bcc248994bf0b40cc1dcc6ad0`, following original Progress
implementation `fad87fc4111fe120de100094f5afdd1825bcfbd3`.
Independent verification supplied by the owner: SQLite sync substrate run
`37144592269` — **SUCCESS**, including Python/Rust substrate, repaired
diagnostics/developer-streak regression step and native Progress authority;
Cloud backend run `37144592250` — **SUCCESS**, including frontend, PostgreSQL,
mandatory shared-ACK/multi-device acceptance and focused cloud/legacy API tests.
This supersedes the pending remote status above. C18.5 and C18 remain
**IN PROGRESS**; official progress remains exactly **77.0%**. The manual release
gate and C21 local-Web-first order remain unchanged.

### C18.5.06 — work in progress, not publishable

Starting branch `6.0`, HEAD and origin/6.0 both
`302a5fe1f7cda77bcc248994bf0b40cc1dcc6ad0`; worktree clean at preflight.
The actual pre-implementation mutation inventory is in
`docs/cloud/C18_GAME_MUTATION_AUDIT.md`. It records the native/Python rule and
freeze differences, preparation/read mutations, and all current API families.

Current draft foundation: strict, bounded Game schemas for project codec12 and
account codec13, version/frame/compression1/1/0, with 19 shared TS/Rust syntax
vectors (genesis/adoption, writing source, completion, streak/freeze, linked reward,
inventory, compensation and resolution). These are **unactivated draft codecs**,
not authenticated causal apply or a reward-once implementation. Catalog IDs4–7
now have an explicit closed mapping independent of the account entity registry;
old codec8/9/10/11 fixtures remain unchanged. Project C11 and account crypto2/AAD2
implementation and registry are unchanged. Production crypto negative tests
cover cross-project, Project/Stage, account user/action identity, entity type and
cross-domain failure. Draft limits: 1MiB frame, 64 parents/references, 512 inventory
entries, 4096 claims/days, 512-byte identities, finite fixed decimals bounded1e12.

Backend capability groundwork adds zero-default independent project/account Game
frame/codec/reader versions and compression flags, a strict declaration endpoint
and account-wide registered-device gate requiring the existing Progress reader
prerequisites. Alembic has one forward head `c18_game_readers` after
`c18_progress_readers`; populated upgrade, reopen/repeated upgrade, third-device
missing/revoked reader and Progress dependency checks pass on real PostgreSQL.
No production client advertises Game support yet. Server Game descriptors/writers
remain unadmitted; this groundwork cannot publish Game actions. Existing head
expectations and focused CI filters/codec tests are updated together.

Current evidence: focused TS codecs/production-crypto/Game API **73 PASS**;
native shared codec vectors/resource negatives **3 PASS**, existing native Game
rules/developer/projection regressions **11 PASS**; PostgreSQL capability/upgrade,
Progress gate and repeated-head auth checks **6 PASS**, zero skips. Python syntax,
isolated imports and Alembic single-head checks pass. This is focused groundwork
evidence, **not** the mandatory two-device Game acceptance.
Frontend typecheck/build and cargo check pass (existing bundle warnings and new
unused draft-codec warnings until runtime wiring); final diff check passes.

Still required in this same slice: finalize rule interpretation and all admitted
effects; schema37 immutable ledgers/tips/reward uniqueness/blockers; explicit
migration and recovery evidence; ordinary native/Python persistence boundaries;
encrypted transport/outbox/self-echo; authenticated Progress/project/Stage and
account reward dependencies; transactional conflict/resolution/compensation;
compatibility projection rebuild; shared ACK proofs/fair reader scheduling;
localized Vue migration/status/conflict UX/help; real two-file SQLite + PostgreSQL
production-crypto reward-once/concurrency/restart/lost-response acceptance;
bounded final CI-equivalent verification, commit and push.

**C18.5.06 = IN PROGRESS / NOT LOCAL COMPLETE / NOT PUSHED**.
Do not replace this with LOCAL COMPLETE until the outstanding work is done.
C18.5 and C18 remain **IN PROGRESS**, official progress exactly **77.0%**.
Protected engine/game_data bytecode is untouched. No registration/release gate,
terminology audit or C21 local-Web-first order changes. No Game snapshot authority,
compression, telemetry, notification sync, developer authority or local-only
project binding has been activated. Continue from this working tree; do not start
C18.5.07 or claim remote acceptance of these unpublished changes.

### C18.5.06 continuation: durable native core (still unpublished)

The existing dirty worktree is preserved at baseline
`302a5fe1f7cda77bcc248994bf0b40cc1dcc6ad0`; no partial commit/push is made.
Schema37 now retains both Game histories, causal tips, immutable candidates,
source/reward uniqueness, decisions/compensations, exact envelopes/receipts,
apply evidence and compatibility-write recovery evidence. Native/Python domain
consumer savepoints prevent a failed processed marker from leaving half a reward.
Developer provenance remains local and prevents ordinary legacy genesis.

Explicit-only native capture retains legacy account/project/Stage sources and
blocks the whole capture on unsupported data/resource overflow. Missing old
project/Stage overlays fall back to the actual entity's saved series; orphan
Stage overlays are retained and blocked. Frozen default comparisons use canonical
numbers, so equivalent `1`/`1.0` persistence does not create false unsupported
extensions. The capture kernel is tested; the actual Vue publication action is
**not wired yet**. No automatic capture is introduced.

The native domain consumer now records admitted ordinary local writing as one
stable Project/Stage Game source and one account reward in the local semantic
transaction, and reuses its recorded source after restart/reprocessing. Admitted
writing freezes the real native coefficients/inspiration/bonus and validates the
complete resulting portable projection. Other incomplete effects remain F with
lossless local evidence. Project/Stage completion production writers, Python
positive ledger writers and account economy writers are **still outstanding**.

Internal paired native apply checks retained descriptors/envelopes, authenticated
Metadata/Stage/Progress dependencies, project-action reward proof, parent ancestry,
rule effects and causal tips. Waiting dependencies retain history without balance
mutation/apply proof. Projection/apply receipt failures roll back together.
Account migration self-echo cannot activate a partial multi-owner capture. A clean
second device receives derived compatibility state without re-executing legacy
rewards. Rebuild restores a damaged compatibility balance/derived projection from
immutable authenticated history, preserving local recovery evidence.

Both Game domains now participate in the single shared ACK proof. The bounded
native unit scenario proves Progress -> Project Game -> account reward prefix
holes, an unrelated processed Note beyond the hole, exact self-echo and repeated
pull without another reward. These are synthetic-envelope native tests, **not**
the mandatory PostgreSQL/production-TS-crypto/two-device acceptance. The durable
transport wrapper reuses generic project objects/outbox/receipts and retains
account envelopes in the account ledger; reopen/lost-response tests preserve exact
frame/ID/nonce/ciphertext. HTTP success is never an apply proof.

Mode3 opaque Game descriptors are admitted in the native/TS transport parsers;
ordinary catalog IDs4–7 and existing derivations/framing remain unchanged. Actual
paired TS Game readers, reader capability advertising, fair runtime scheduling,
localized publication/conflict UX/help and final production acceptance are still
required before activation/closure. No client advertises Game reader support yet.

Focused continuation evidence: native Game/core/transport/writer checks **28 PASS**
(the projection rebuild assertion was corrected and rerun independently after its
added recovery row changed the blocker query); shared ACK-related regression
selection **66 PASS**; schema37 upgrade/reopen/compatibility/Python consumer checks
**42 PASS**; frontend Game codecs/crypto/catalog **50 PASS**, V3 descriptor checks
**7 PASS**. Typecheck and cargo check pass at their checked revisions; final bounded
CI-equivalent verification remains pending after full runtime/UX integration.

**C18.5.06 = IN PROGRESS / NOT LOCAL COMPLETE / NOT PUSHED**.
C18.5 and C18 remain IN PROGRESS; official progress remains exactly **77.0%**.
Required real two-device/bidirectional/completion/concurrency acceptance is not
claimed. The original remaining closure requirements continue to apply.

Additional continuation checks: a duplicate local processing event referring to
an already recorded Progress entry also reuses the canonical pair without another
local reward. Legacy numeric inputs requiring more than the frozen six decimal
places are retained/blocked rather than silently rounded. Account catalog reader
selection remains explicitly limited to its four catalog types; Game ciphertext
is not handed to the catalog decoder. V3 Game descriptor negatives and the updated
frontend typecheck pass. Required runtime/UX/production acceptance remains open.

### C18.5.06 continuation: paired runtime, production writers and acceptance

The same authorized dirty worktree remains based on `302a5fe1f7cda77bcc248994bf0b40cc1dcc6ad0`; no partial commit or push.
The paired TS runtime now advertises Game only with SQLite ownership and all required
Progress readers, checks the all-device paired gate before each publication, seals
both existing crypto domains once, resumes exact durable envelopes, and imports
both domains through authenticated native transactions. Durable bounded rotation
includes blocked/decryption-failed rows and introduces neither a second cursor nor
a per-entity ACK. Background work never calls legacy capture.

Ordinary native writing/completion and buy/sell writers are wired. Python's ordinary
SQLite domain consumer also writes the same durable source/reward pair, preserving
its historical raw-XP and round-to-even completion rule. Its frames match all 19
frozen TS/Rust vectors. No native/Python rule is silently reinterpreted. Completion
uses the established Metadata/Stage writers and freezes the exact pending local
structural dependency; readers wait for authenticated echo. Display refresh retains
the last proven Progress projection while an exact local structural completion
awaits echo. It manufactures no import or ACK evidence.

Explicit migration can add a newly bound Project/Stage after existing Game owners
are active without regenerating their accepted bases. Missing/invalid/oversized
sources retain the original game_state plus a durable bounded recovery reference.
The Vue panel provides explicit publication, bounded versions/full-tip choice,
rebuild and separately confirmed reward compensation. Russian help and all five
translations are generated from reviewed source overrides.

Focused evidence at these revisions: native Game selection **32 PASS** and additional
earn/spend + compensation/spend conflict proof **1 PASS**; schema/vector Python
selection **61 PASS**; frontend crypto/runtime/diagnostics/codec regression selection
**165 PASS**; UI/runtime selection **16 PASS**; Chromium explicit publish/full-tip
choice/separate reversal confirmation/all six locales **PASS**; help/localization
**30 PASS**. Python Game regression selection had **88 PASS** plus one pre-existing
OpenAPI test error: the baseline `/api/game/developer` already returns
DeveloperModeResponse, not GameCommandResponse. Its assertion is now exact for that
existing read DTO while retaining the exact command DTO assertions; focused rerun
**1 PASS**. No application API behavior changed for this correction.

Real PostgreSQL + production TS crypto + two separate file-backed native SQLite
acceptance now proves legacy adoption without payment, bidirectional ordinary
writing, Python raw-XP continuation, Project/Stage completion, new Stage-only
migration, lost-response/replay, a Progress-only third reader blocking both unchanged
Game candidates, concurrent purchases, full-tip choice/stale CAS, and single
compensation retaining its reward. The complete scenario stores **19** opaque Game
events with **6** unique rewards and **1** compensation and converges both devices.
The mixed-account-stream variant additionally proves a processed legacy Note beyond
a Progress/G/R dependency hole cannot advance shared ACK past that hole (**PASS**).
Further rename/source-deletion/rebuild/Stage-tombstone acceptance and the bounded
final CI-equivalent audit are still running; their outcome is not yet claimed.

**C18.5.06 = IN PROGRESS / NOT LOCAL COMPLETE / NOT PUSHED**.
C18.5 and C18 remain **IN PROGRESS**; official progress remains exactly **77.0%**.

### C18.5.06 final bounded verification (continuation)

The accumulated implementation preserves codecs 1–11 and independently freezes
catalog IDs 4–7. Project/Stage Game is WORTA-C1 frame1/codec12/version1/compression0
in unchanged C11 crypto1/AAD1; account Game is frame1/codec13/version1/compression0
in unchanged AMK account crypto2/AAD2. Forward SQLite schema37 preserves existing
opaque transport and catalog evidence. Alembic `c18_game_readers` has the single
parent `c18_progress_readers`; both Game readers plus Progress prerequisites form
one all-registered-device gate. The server retains opaque ciphertext only.

Immutable source/action/reward relations use deterministic canonical namespace
identities and durable uniqueness. Same identity with different effect blocks
rather than replacing history. Frozen legacy/native/Python v1 rule facts preserve
historical semantics. Atomic apply proves Metadata/Stage → Progress → project Game
→ account reward, updates history/tips/snapshot/compatibility/receipt/ACK proof in
one transaction, and never treats an upload receipt as authority. Full-tip CAS
resolution retains both branches; idempotent negative compensation retains the
original reward. Mutable game_state is a compatibility projection, not a cloud
winner. Domain processing rows, notifications and developer/test provenance remain
local. No local-only project is automatically bound.

The final admission/deferred matrix is in `docs/cloud/C18_GAME_MUTATION_AUDIT.md`.
Native/Python writing and completion plus native catalog buy/sell are admitted;
explicit legacy adoption, resolution, rebuild and confirmed compensation are
closed controls. Other portable-changing families retain exact local recovery
and block complete sync until separately admitted; reserved codec variants alone
are not authority. This includes freeze transitions, bank, quests/challenges,
specialization/skill changes, custom awards and item-use effects.

Bounded SQLite CI-equivalent after old fixture repair: **428 PASS**, no skips.
Native CI-equivalent: **357 PASS** across all 17 workflow filters, no failures or
ignored cases in these selections. Frontend closure regression **165 PASS**;
final panel/codec selection **52 PASS**; help/localization **30 PASS**. Typecheck,
frontend build, cargo check, affected Python syntax and diff whitespace checks
pass. Chromium verifies explicit publication, full-tip choice, separate reversal
confirmation and all six locales. Protected engine/game_data pyc timestamps
remain unchanged.

The complete mandatory Cloud/PostgreSQL workflow selection finished **50 PASS**
and one Game acceptance fixture failure: a completed Stage's ordinary read-only
guard masked the tombstone guard intended by that scenario. The fixture now
reopens the Stage through its ordinary structural writer before tombstoning it;
the unchanged strict tombstone/reward assertions are being rerun in the complete
Game scenario. This outcome is not yet claimed. Earlier production acceptance
already proved source rename/deletion preservation, rebuild from authenticated
history and explicit reconciliation with immutable local recovery evidence.

**C18.5.06 = IN PROGRESS / NOT LOCAL COMPLETE / NOT PUSHED**.
C18.5 and C18 remain **IN PROGRESS**; official progress remains exactly **77.0%**.

### C18.5.06 LOCAL COMPLETE / REMOTE CI PENDING

The corrected complete Game production acceptance now **PASS** (222.59s), using
real PostgreSQL, production TypeScript crypto and two separate file-backed native
SQLite databases. The full mandatory Cloud selection had **50 PASS**; its only
failed fixture is now repaired and the whole affected Game scenario rerun **1 PASS**.
No mandatory tests were skipped or assertions weakened. The fixture reopens the
Stage through the ordinary writer before deletion, so the strict observed error
is `stage_tombstone_child_manifest_incomplete`, rather than an unrelated completed
entity read-only guard. Existing reward/history assertions remain exact.

Final production evidence: **22** opaque Game events, **6** unique rewards and
**1** compensation. Legacy bases pay nothing; ordinary native/Python Progress and
Project/Stage completion produce stable source/action/reward relations; remote
Progress produces no local reward. Lost response retries exact sealed bytes;
self-echo/replay/restart and completion retries do not pay twice. The third
Progress-only device blocks both Game domains, then unchanged pending candidates
resume after paired support. Spend/spend conflicts retain branches; full-tip CAS
choice converges and stale choice fails. Native earn/spend and compensation/spend
also retain conflict without partial invalid projection. Renames and Progress
source deletion preserve claims/rewards. Deliberately corrupted derived balance
rebuilds from authenticated history; explicit reconciliation retains immutable
OLD/NEW evidence and restores both devices' authority without repayment.
An authenticated Stage tombstone retains children and blocks new unsafe actions.
A legacy Note beyond a Progress/G/R dependency hole may apply, but shared ACK
cannot pass the unresolved Game prefix. Durable reader rotation survives restart.
No second cursor, per-entity ACK, plaintext server Game fields, notification cloud
authority, developer/test authority or automatic local-project binding was added.

Final bounded checks: SQLite **428 PASS**; native workflow selections **357 PASS**;
frontend closure **165 PASS**, final panel/codec **52 PASS**, UI/runtime **16 PASS**;
help/localization **30 PASS**; Cloud mandatory **50 PASS + repaired scenario 1 PASS**.
TypeScript typecheck, frontend build, cargo check, Python syntax/import checks,
Alembic single head, strict TS/Rust diagnostics contract and git diff whitespace
checks pass. Actual Chromium UX verification passes in all six languages.
Previously accepted C11, account crypto2/AAD2, catalog4–7 and codecs1–11 remain
unchanged. Protected pyc files remain untouched. The entire accumulated diff was
reviewed against `302a5fe1f7cda77bcc248994bf0b40cc1dcc6ad0` before the single commit.

**C18.5.06 = LOCAL COMPLETE / REMOTE CI PENDING**.
**C18.5 = IN PROGRESS; C18 = IN PROGRESS; official progress = 77.0%.**
Release gate, final terminology audit and C21 local-Web-first remain preserved.
Independent remote acceptance is required before recommending
`C18.5.07 — CONTENT/ACTION INTEGRATION AUDIT / C18.5 CLOSURE`; no C18.5.07 work is
included. After publication Codex stops without polling GitHub Actions.


### C18.5.06 — independent remote acceptance

**C18.5.06 — REMOTELY ACCEPTED.** Owner/GPT independent implementation SHA
`d34254fef37501e95d7b435f35e3106e6d8eda95`:

- SQLite [37212649560](https://github.com/nevskyforever/nfprogress/actions/runs/37212649560) — SUCCESS: Python/Rust SQLite substrate, Game codec vectors, preceding Note/Map/Document/Progress/native regressions.
- Cloud [37212649515](https://github.com/nevskyforever/nfprogress/actions/runs/37212649515) — SUCCESS: frontend, PostgreSQL, mandatory ACK/multi-device acceptance, focused cloud/legacy API tests.

This supersedes all historical .06 pending/work-in-progress sections. Accepted
slices .01–.06 and their exact evidence are enumerated in the integration document.

### C18.5.07 — local integration closure candidate

Branch6.0; starting clean HEAD == origin/6.0 ==
`d34254fef37501e95d7b435f35e3106e6d8eda95`. Implementation is this C18.5.07
commit; its published SHA is reported in the task result. Dedicated evidence:
[Content/action integration acceptance](cloud/C18_5_INTEGRATION_ACCEPTANCE.md).

**C18.5.07 — LOCAL COMPLETE / REMOTE CI PENDING.**
**C18.5 — CLOSURE CANDIDATE / REMOTE CI PENDING.**
Only owner/GPT independent Actions acceptance can establish final C18.5 CLOSED.
C18.4 CLOSED; .01–.06 REMOTELY ACCEPTED; C18 IN PROGRESS; official77.0%;
C18.6 NOT STARTED.

P0 found0; P1 found3 and resolved; remaining P0/P1=0; no open task-specific P2:

1. First remote Stage lacked empty Progress read-model defaults, falsely conflicting with admitted genesis. Initialize total0/empty entries only for a new Stage; preserve existing history.
2. Open Game authority could display stale success after a durable deferred mutation. Refresh on data changes and inspected idle sync cycles; unsubscribe on unmount, no automatic publication.
3. More than32 retained content events could indefinitely hide later owners across bounded cycles. Note8/Map/Document/Progress reuse schema37 durable reader visits; output remains sequence-sorted. Historical Note v1/v2 paging remains unchanged. No added sync cursor/ACK proof.

Registry1–13 and all golden bytes unchanged; project C11 and account2/2 domains
unchanged. Authenticated dependency DAG, explicit consent, staged capability gates,
ONE common ACK with held Progress plus later safe Note, reader fairness/reopen,
local-only exclusion with two cloud projects, Note/Map edit/delete single authority,
Document/Progress composition, one G/R reward, A→B→A and upgraded C convergence,
independent Note/Map conflicts, Stage tombstone with all child families retained,
server blindness and deferred/F source preservation verified. No codec14/schema38,
new crypto/AAD, telemetry, protocol redesign or C18.6 implementation.

Final local evidence:

- Python SQLite workflow selection442 PASS, zero skips; final production routing/F guard14 PASS.
- Native workflow17 filters358 PASS; explicit content/Game rotation2 PASS; cargo check PASS.
- Mandatory real-PG/production-TS/native-file acceptance52 PASS, zero skips; focused backend/API194 PASS, zero skips.
- Final mixed scenario including map-derived Note deletion1 PASS; local-only two-cloud-project scenario1 PASS.
- Frontend workflow381 PASS/60 files; typecheck/build PASS; Chromium blocker refresh without publication, explicit consent/full-tip/reversal flows and six locales PASS.
- Diagnostics TS/Rust equality/privacy, SQLite contiguous1–37/all-prefix/populated36 upgrade/reopen, single Alembic c18_game_readers head, Python syntax/imports, workflow YAML and git diff --check PASS.
- Protected engine/game_data pyc untouched, original mtimes/sizes retained. Existing frontend size/dynamic-import and native dead-code warnings remain outside the bounded slice.

Local platform macOS/Python3.12/Node26.4.0 with existing WebStorage compatibility
flag; independent Linux/Windows CI with pinned Python3.13/Node20.19.0 is pending.
An initial no-DB aggregate run with skips was rejected, then both Cloud workflow
selections passed with an explicit isolated PostgreSQL URL and zero mandatory skips.

Authorized single commit/push to origin6.0; afterward Codex does not poll Actions.
Expected: Cloud backend tests; SQLite sync substrate tests. Next ONLY after independent
remote acceptance: **C18.6.01 — COVER BLOB / REFERENCE / MISSING-BLOB ACCEPTANCE**.
Release gate unchanged: full C18 → C21 → C22 → C23 → PF6.0/RC → owner dogfooding /
stabilization → diagnostics review → final user-facing terminology audit → explicit
owner registration decision. PF6.0/RC does not automatically open registration.
C21 order remains local browser build → Tauri dependency audit → browser adapters →
stable local Web → VPS/production.
