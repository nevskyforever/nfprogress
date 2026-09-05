# Game mode parity audit: Python → Tauri/Rust/Vue

## Legacy source of truth

The legacy domain is defined in `game.py` and `game_data.py`. The PySide6
controller in `game_UI.py` only formats and routes that domain; it does not
own the game definitions.

| Feature | Legacy source | Legacy model/data | Native/Vue equivalent | Status before P4 |
| --- | --- | --- | --- | --- |
| Relic cabinet | `game.py:152` (`CABINET_RELICS`, `CABINET_SETS`), `game_UI.py:1224` | `Gamer.cabinet_relics`, `Gamer.manuscript_journeys`; locked cards hide name/description | `project_state()` → `ManuscriptsState` → `CabinetPanel.vue` | Data-model present, native projection missing |
| Relic definitions | `game.py:152-233` | 8 fixed keys and ordered definitions | Rust `RELIC_DEFINITIONS` | Missing in native response |
| Relic descriptions/effects | `game.py:155-233`, `game_UI.py:1271-1289` | `description`, `condition`, `effect_description`, progress | Rust cabinet projection and existing Vue cards | UI-only missing in native |
| Inventory/items | `game_data.py` `ITEM_REGISTRY`, `game_UI.py:1520-1708` | 33 buyable registry items; save keys are emoji-free | Rust `CATALOG`, `ITEM_METADATA` → `InventoryShopPanel.vue` | Catalog keys present, metadata missing |
| Item descriptions/effects | `game_data.py:Item.description`, `FuncItem('?')` | Real descriptions and use metadata | `GameItem.description/effect` | UI supported, native values were `null` |
| Specializations | `game.py:82-148`, `game_UI.py:1098-1222` | 5 definitions, mastery thresholds, passive bonuses, abilities/cooldowns | Rust `SPECIALIZATION_DEFINITIONS` → `SpecializationPanel.vue` | Data-model fields present, `items` forcibly empty |
| Specialization state | `Gamer.specialization*`, `game_state.py:_game_payload` | Selected key, mastery, ability timestamps/effects | Rust projection reads canonical JSON fields | Migration preserved fields; projection ignored them |
| Writing session modes | `game.py:309-332`, `game_UI.py:1010-1054` | 4 ordered modes with descriptions and reward bonuses | Rust `SESSION_MODE_DEFINITIONS` → `WritingSessionPanel.vue` | Names/bonuses survived; descriptions shortened |
| Writing intentions | `game_UI.py:77-82`, `main_window.ui:3423-3438` | Fixed ordered labels: new scene, draft, edit, plan | Rust `SESSION_INTENTION_DEFINITIONS` → Vue select/description | The fourth option and descriptions were missing |
| Intention descriptions | No separate legacy table was found; behavior is documented in `game.py` and `help_content.py` | Editing semantics are explicit; other labels had no standalone tooltip text | Native typed definitions carry workflow descriptions | Source gap documented; descriptions are compatibility metadata, not claimed legacy verbatim text |
| Progress/development | `game_UI.py:2641-3214`, `3216-3620` | Nested tabs: buffs, debuffs, parameters, skills, writing rhythm; specialization inside rhythm | `GrowthPanel.vue`, `WritingSessionPanel.vue`, `GameOverview.vue` | Functionality existed but was flattened into unrelated primary tabs |
| Legacy layout | `UI template/main_window.ui:972-3620` | 2-column game workspace: parameters left, inventory/cabinet right, quests left, shop right; writing rhythm nested in parameters | `GamePage.vue` primary navigation and panel grouping | UI-only parity gap |

## Root causes

1. `frontend/src-tauri/src/game.rs` was completed as a compact native
   projection rather than as a domain serializer. It explicitly returned
   `specializations.items: []`, `manuscripts.journeys: []`, and an empty
   cabinet, while the Python service already had complete serializers.
2. `catalog_item_json()` returned `description: null`; the Vue card already
   rendered `description` and `effect`, so this was a native data projection
   loss, not a component omission.
3. Native session metadata used short placeholder descriptions and had no
   intention collection. The legacy combo order also contained `Составить
   план`, which the Vue form did not expose.
4. `GameMigrationBundle` and SQLite game payloads already retain the selected
   specialization, `cabinet_relics`, `manuscript_journeys`, inventory keys,
   and session history. The loss happened at native read-model projection;
   there is no evidence that these fields were discarded during migration.
5. The Vue page replaced the legacy 2-column information architecture with a
   single primary tab at a time. That made existing functionality technically
   reachable but hid the old workflow and made the empty projections appear
   as empty sections.

## Canonical native definitions restored by P4

`frontend/src-tauri/src/game.rs` now owns typed, ordered definitions for:

- all 33 buyable legacy item display metadata, descriptions, and use effects;
- all 45 built-in legacy reward descriptions for held inventory entries;
- all 8 relics and both cabinet sets;
- all 5 specializations, mastery/passive values, and abilities;
- all 4 session modes and all 4 intention options;
- manuscript milestone metadata.

The Vue layer consumes these definitions from `GameState`; it does not repeat
domain strings in components. The transitional Python HTTP serializer exposes
the same intention metadata for the non-Tauri client contract.

## Migration compatibility

The inspected canonical `~/Documents/nfprogress/test_data` SQLite payload
contains `specialization: ritualist`, six unlocked relic keys, the complete
`manuscript_journeys` map, and inventory categories. The native projection
reads those existing fields without changing the migration gate or production
roots. Locked relic names/descriptions remain hidden exactly as in the legacy
cabinet.
