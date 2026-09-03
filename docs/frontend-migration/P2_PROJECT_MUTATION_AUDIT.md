# P2 project mutation audit

| Operation | Current caller/API | Python boundary | P2 decision |
| --- | --- | --- | --- |
| Rename, goal, unit, deadline, infinite | Project edit → `PATCH /projects/{id}` | `ProjectService.update_project` | Safe metadata whitelist; new `/metadata` route |
| Manual project ordering | Projects page → `PUT /projects/order` | `ProjectService.reorder_projects` | Safe; typed repository and Tauri command |
| Archive/unarchive, status, complete/reopen | Project pages → archive/complete endpoints | archive/completion service | Excluded: lifecycle/game/streak semantics |
| Project settings/options, total, work method, folder, cover, daily/streak options | Project edit/pages → mixed project PATCH | `update_project` plus invariants/integrations | Excluded: mixed payload or side effects |
| Create/delete project | project API | lifecycle service, Notes cleanup | Excluded: lifecycle, Notes and backup contract |
| Stage metadata/order/create/delete/complete | stage endpoints | stage service | Excluded: stage/progress/lifecycle coupling |
| Add/edit/delete progress | progress endpoints | progress and game/streak services | Excluded: P3/P6-P7 |

The metadata route is strict (`extra='forbid'`) and delegates validation,
normalization, atomic PKL persistence, and best-effort SQLite mirror rebuild to
the existing Python repository. Rust does not write project SQLite tables.
