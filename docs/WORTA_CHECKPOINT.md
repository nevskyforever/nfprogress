# WORTA 6.0 — ПОЛНЫЙ ПРОЕКТНЫЙ ЧЕКПОИНТ

**Дата:** 23 сентября 2026 года.\
**Методика:** WORTA ROADMAP SCORING v1.0.\
**Официальный зачтённый прогресс:** **67,5%**.\
**Последний полностью закрытый этап:** **C15.7B — Atomic Local Apply**.\
**Текущий этап:** **Full Orchestration, ACK, Two-Device Acceptance** (вес 2,5), **IN PROGRESS / LOCAL ACCEPTANCE COMPLETE**: Slices 1–5B и единый headless cross-runtime proof реализованы и проверены локально; пакет не закрыт до пользовательского push и independently verified remote CI.\
**Следующий зачёт:** после полного закрытия этого пакета C15 — **70,0%**.\
**Последний независимо проверенный remote HEAD:** `9578706b9e86a12daceb42a3b69bdc8e60921ce9`.\
**Последняя независимая приёмка:** commit `feat(sync): add atomic encrypted inbox remote apply` для SHA выше; оба требуемых GitHub Actions workflow и все четыре relevant jobs — **SUCCESS**.
**Текущая задача Codex:** C15.7B закрыт. Slices 1–5B и headless TypeScript→FastAPI/PostgreSQL→Rust/SQLite apply/ACK proof локально реализованы; полный доступный CI-equivalent pass успешен. Локальный implementation commit создаётся после обновления этого checkpoint, без записи собственного SHA в commit. До закрытия пакета остаются пользовательский push и независимая проверка required remote CI на новом SHA. Desktop UI/startup wiring остаётся вне C15. Не начинать C16, C17 или иной следующий implementation stage без отдельного задания.

**ОБЯЗАТЕЛЬНО ДЛЯ СЛЕДУЮЩЕГО ЧАТА: внимательно прочитать разделы 3, 8–15 и 47–50 о методике работы, затем актуальные разделы C15.7B.** Terra Medium — модель по умолчанию. Следующий самостоятельный implementation stage не начинать. Codex может обновлять checkpoint-файл после meaningful slice, но **не имеет права самостоятельно объявлять новые этапы `CLOSED`, менять официальный процент или scoring methodology**.

Документ предназначен для переноса **всего существенного контекста разработки** в следующий чат. Старый чекпоинт от 23.09.2026 фиксировал C15.5C как CI PENDING и 60,0%; настоящий документ заменяет устаревший статус. **Не пересчитывать проценты по собственным ощущениям, числу коммитов или объёму локальных изменений.**

---

## 1. Репозиторий, ветка и проверенный baseline

- GitHub: `nevskyforever/nfprogress`.
- Основная ветка разработки WORTA 6.0: `6.0`.
- Последний независимо проверенный remote HEAD: `9578706b9e86a12daceb42a3b69bdc8e60921ce9`.
- Commit: `feat(sync): add atomic encrypted inbox remote apply`.
- В момент последней независимой проверки remote HEAD **совпадал с этим SHA**.
- C15.7B включён в этот remote commit и независимо принят по двум workflow. Локальный `git status` перед следующими изменениями всё равно проверяется в самом Codex worktree.
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
| Full Orchestration, ACK, Two-Device Acceptance | 2,5      | IN PROGRESS (Slices 1–5B local; remote acceptance pending) |
| **Итого**                                      | **20,0** |                    |

Доля исходного пакета «Decrypt and Local Apply» 2,0 разбита на C15.7A = 1,0 и C15.7B = 1,0; общая стоимость не изменилась.

## 6. Текущий расчёт прогресса

- Исторический задел: 18,0 / 18,0.
- C7–C14: 32,0 / 32,0.
- C15 до C15.5B включительно: 10,0.
- C15.5C: +1,5 → 61,5% общего прогресса.
- C15.6A: +2,0 → 63,5%.
- C15.6B: +2,0 → 65,5%.
- C15.7A: +1,0 → **66,5%**.
- C15.7B: +1,0 → **67,5%**.
- После полного C15, включая оркестрацию: 70,0%.
- C16–RC пока 0 / 30,0.

**Официально сейчас 67,5%; осталось 32,5 процентного пункта.** C15.7B увеличил показатель только после commit, пользовательского push и независимой проверки remote SHA и всех required jobs.

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
- **Пользователь:** управляет рабочей сессией, выбирает модель и самостоятельно делает push, если не дал иного конкретного указания. Не менять модель, не запускать второй параллельный Codex и не прерывать уже работающую задачу без необходимости/поручения.
- Для промежуточных локальных slices C15.7B **никаких самовольных commit/push**. Один общий commit только после завершения и проверки согласованного scope; push — отдельное решение пользователя.
- **Сначала анализ текущего отчёта.** Если prompt уже запущен, дождаться результата в ходе пользовательского взаимодействия; не отправлять заново то же задание и не выдумывать результат. Не переходить к другой самостоятельной стадии без отдельного запроса пользователя.
- **Экономить лимиты и ресурсы.** Terra Medium по умолчанию; выбирать Sol Medium/High лишь по реальной сложности. Нельзя автоматически рекомендовать Sol High просто потому, что в задании присутствует слово security. Текущее задание **уже работает на Sol High**; задним числом смена модели не окупит повторный запуск.
- **Не устраивать бесконечных аудитов.** Простой ошибочный путь, patch-context mismatch, не написанный тест или локальная ошибка рабочего каталога — повод для минимального исправления, а не нового архитектурного цикла и не формального `BLOCKED`.
- При проблеме редактирования читать **реальные текущие строки**, править небольшими отдельными операциями и удостоверяться, что запись действительно сохранилась. Не откатывать всю локальную работу из-за частной ошибки.
- **Без расширения scope:** не чинить unrelated warnings, не запускать преждевременные тяжёлые матрицы, не переписывать frozen contracts и не объявлять готовой следующую архитектурную стадию по успешному unit test предыдущей.
- При обсуждении статуса сохранять границы достоверности: подтверждено ранее по remote, сообщено Codex локально, ещё не запускалось, уже отправлено Codex и выполняется.

## 11. Обязательный формат заданий Codex

Перед большим заданием кратко изложить цель, ожидаемый практический результат, **экономный рекомендованный вариант модели/thinking** и необходимость нового Codex-чата, только если она действительно есть. По умолчанию **Terra Medium**. Сам prompt давать **одним цельным копируемым блоком** (в интерфейсе удобнее отдельный WritingBlock, не дробить на несколько разрозненных сообщений).

В prompt всегда включать: последний проверенный remote baseline SHA (не подменяет локальный HEAD); требование проверить реальный `git status`/working directory; файлы и ограниченный scope; frozen contracts; короткий read-only осмотр только если нужен; конкретные действия; security invariants; критерии готовности; targeted tests и удалённую CI coverage; **TEST BUDGET**; явный запрет на самовольный `reset/clean/checkout`, `commit/push` и изменение пользовательских `.pyc`; формат `=== CODEX TASK RESULT === ... === END CODEX TASK RESULT ===` с указанием `passed/failed/not run/skipped`.

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

- **C15 завершение (+2,5 пункта от текущих 67,5):** Full Orchestration/ACK/Two-Device Acceptance +2,5 → **70,0%**. Полный цикл outbound sealing/upload/retries/acceptance/pull/inbox/decrypt/atomic apply/cursor & device ACK/restart/two-device tests. Внутреннее разделение этого пакета не утверждено в данном checkpoint; перед реализацией нужен отдельный ограниченный design/scope pass.
- **C16 Desktop Sync +3,0** → 73,0%: интегрировать Common Sync Engine в пользовательский desktop workflow.
- **C17 Shared Conflict Handling +4,0** → 77,0%: безопасное разрешение конфликтов между устройствами; до этого конфликты сохраняются, без silent LWW.
- **C18 Complete Project Sync +7,0** → 84,0%: Documents, Mind Maps, Stages/Sources, Rewards и другие данные проекта.
- **C19 Android Local SQLite +3,0** → 87,0%.
- **C20 Android Sync +3,0** → 90,0%.
- **C21 Web +4,0** → 94,0%.
- **C22 Production Hardening +2,0** → 96,0%.
- **C23 Failure/Disaster Tests +2,0** → 98,0%.
- **PF 6.0 + Release Candidate +2,0** → **100,0%**.

Эти проценты — плановые суммы **при условии официального закрытия каждого этапа**; не прогноз даты выпуска и не оценка потраченного времени.

## 44. Принципы релиза

Desktop/Android local-first, Web cloud-first; local-only проекты не выгружать автоматически; E2EE не ослаблять; encrypted pull без verified apply — не завершённая синхронизация; нельзя silently overwrite пользовательский текст. Перед релизом отдельно спроектировать release automation; исторически обсуждавшаяся команда `npm run release -- 6.0.1 --all` и опции `--web`, `--desktop`, `--mobile`, `--dry-run` — план, **не утверждение об уже реализованном script**.

## 45. Правило ответа на вопрос «сколько процентов?»

Только WORTA ROADMAP SCORING v1.0. Называть последний закрытый этап, точный зачёт в процентных пунктах, текущий незавершённый этап и условие следующего прибавления. Прямо сейчас ответ: **67,5%; последний закрытый C15.7B; следующий пакет Full Orchestration, ACK, Two-Device Acceptance весит 2,5 и после независимого закрытия даст 70,0%.** Не менять процент из-за большого объёма локальной работы, убедительного отчёта или одноразового зелёного теста.

## 46. Точка продолжения в новом чате — ТЕКУЩЕЕ СОСТОЯНИЕ

**C15.7B закрыт после независимой remote-приёмки.** Следующий implementation prompt не выдавать без отдельного ограниченного design/scope pass для следующего C15 package.

**Repo/branch:** `nevskyforever/nfprogress`, `6.0`.
**Последний independently verified remote HEAD:** `9578706b9e86a12daceb42a3b69bdc8e60921ce9`.
**Remote CI на нём:** [Cloud backend run `35868491726`](https://github.com/nevskyforever/nfprogress/actions/runs/35868491726) — SUCCESS (PostgreSQL cloud backend, Frontend admin); [SQLite run `35868491642`](https://github.com/nevskyforever/nfprogress/actions/runs/35868491642) — SUCCESS (Python SQLite substrate, Rust SQLite substrate).
**Official progress:** **67,5%**, WORTA ROADMAP SCORING v1.0.
**Last CLOSED:** C15.7B Atomic Local Apply.
**Now:** Full Orchestration, ACK, Two-Device Acceptance — **IN PROGRESS** (Slices 1–3 local), вес 2,5; пакет не закрыт. C15.7B commit не включал пользовательские `.pyc`; migration 015/fail-closed substrate, Rust plaintext decoder, golden create/update, privileged Rust connection, Rust Atomic Apply и protected TS/Tauri integration приняты remote CI.
**Next:** отдельный ограниченный design/scope pass для Full Orchestration, ACK, Two-Device Acceptance; не начинать реализацию, ACK, scheduler или C17 автоматически.
**Hard rules:** E2EE/lease; frozen TS codec и C11/C15.3; fail-closed schema-15 guards; no silent data loss/echo; no reset/clean/checkout; no unrelated changes; no autonomous commit/push; Terra Medium by default; exact `passed/failed/not run/skipped`; не увеличивать процент до independently verified CLOSED.

## 47. МЕТОДИКА РАБОТЫ — ПРЯМОЕ ОБЯЗАТЕЛЬНОЕ УКАЗАНИЕ ДЛЯ СЛЕДУЮЩЕГО АССИСТЕНТА И CODEX

**ВНИМАТЕЛЬНО И В ПОЛНОМ ОБЪЁМЕ СЛЕДОВАТЬ МЕТОДИКЕ ЭТОГО ЧЕКПОИНТА.** Этот файл нужен не только как справка о коде, но и как защита от дрейфа процесса: повторных задач, лишнего расхода моделей, неподтверждённого `CLOSED`, повторных тяжёлых тестов и потери frozen contracts.

**Практический чек-лист перед КАЖДЫМ новым prompt или оценкой отчёта:**

1. Проверить последнее сообщение пользователя и самый свежий `=== CODEX TASK RESULT ===`: что реально выполнено, что только написано, что не запускалось и что уже выполняется. C15.7B закрыт после independently verified remote acceptance; следующий C15 package `IN PROGRESS` локально, Slices 1–3 реализованы.
2. Всегда разделять: **independently verified remote** / **Codex-reported local** / **not run or unknown**.
3. WORTA ROADMAP SCORING v1.0 не импровизировать. Сейчас **67,5%**. C15.7B уже дал +1,0 после полного acceptance; следующий пакет C15 весит 2,5 и требует отдельного полного acceptance.
4. Выбирать минимальный достаточный следующий slice. Не повторять уже закрытый локальный scope без изменения, которое могло его сломать.
5. **Terra Medium first.** Sol Medium/High только по конкретной доказанной необходимости или на отдельный финальный security audit.
6. TEST BUDGET: focused tests → минимальный fix → repeat только затронутого → один full CI-equivalent pass перед общим commit.
7. Не ломать E2EE, draining lease, frozen codec, fail-closed SQL guards, one-shot capability, durable inbox/receipts, no-silent-LWW и no-echo.
8. Во всех prompts явно писать: `no reset/clean/checkout`, `no unrelated changes`, `no autonomous commit/push`, два `.pyc` не трогать.
9. После локальной реализации требовать точные test counts, `git status`, `git diff --check`, CI coverage. После push — проверить **новый SHA** и все relevant jobs обоих workflow.
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
4. **Пользователь** выполняет push, если не поручено иначе.
5. **ChatGPT независимо проверяет** новый remote HEAD, оба GitHub Actions workflow, relevant jobs, curated tests/path filters.
6. Только после этой проверки пользователь/ChatGPT дают Codex отдельное указание обновить `docs/WORTA_CHECKPOINT.md`: поставить `CLOSED`, новый SHA/CI и официальный процент.

Следовательно, в будущих prompts формулировка должна быть не «объяви этап завершённым», а:

**«Обнови `docs/WORTA_CHECKPOINT.md` по фактическому результату этого slice. Не ставь `CLOSED` и не меняй официальный процент без явно переданной independently verified remote acceptance. Если этот prompt содержит такую acceptance, внеси её точно как дано.»**

Это предотвращает ситуацию, когда Codex сам становится одновременно исполнителем и единственным приёмщиком собственной работы.

## 49. Ближайшее действие

Текущий roadmap package — **Full Orchestration, ACK, Two-Device Acceptance** (2,5 пункта). Он `IN PROGRESS` локально, не `CLOSED`.

Slices 1–3 durable ACK substrate/transport и bounded Notes orchestrator, Slices 4B1–4B2 durable identity/headless normal-user session runtime, а также Slice 5A file-backed SQLite lifecycle preparation локально завершены. Runtime deliberately remains unconnected to `main.ts`, `platform/runtime.ts`, UI, scheduler and legacy document sync. Ближайший минимальный технический шаг — отдельная bounded PostgreSQL two-device integration acceptance; она не должна неявно добавлять C16 UI или C17.

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

# КОНЕЦ ЧЕКПОИНТА
