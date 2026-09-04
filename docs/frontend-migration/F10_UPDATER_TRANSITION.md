# NFProgress — F10 updater transition

Дата аудита: 2026-09-04. Baseline: `27d0924` (`27d09249f1df88c89d10698b58f2f5fa4515fab0`).
Production manifests intentionally remain outside this change.

## Fact pattern

The legacy Windows updater is `updater_main.py` → `updater_core.py`. It
downloads `nfprogress-update.zip`, verifies the manifest SHA-256, waits for the
parent PID, safely extracts a ZIP whose only root is `nfprogress/`, and requires
both `nfprogress/nfprogress.exe` and `nfprogress/nfprogress-updater.exe`. It
atomically renames the old `nfprogress` directory to `.nfprogress-backup`,
installs the extracted directory, starts `nfprogress.exe`, and restores the old
directory if installation or startup fails. It does not validate Authenticode
and does not understand an NSIS installer.

On macOS the legacy updater is `update_checker.py` plus a detached shell
script. It downloads a ZIP, verifies byte count and SHA-256, searches for the
running `.app` name (then any `.app`, then a nested DMG), moves the current
bundle to `<app>.old`, copies the new bundle into the same path, and opens it.
There is no fixed legacy bundle identifier in Python release metadata; the
observed/expected bundle name is `nfprogress.app`.

The current Tauri contract is:

| Platform | Tauri package | Tauri updater package | Identity |
| --- | --- | --- | --- |
| macOS ARM | `nfprogress.app` in DMG, locally wrapped as `nfprogress-tauri-mac-arm-V.zip` | `.app.tar.gz` plus `.sig` when enabled | `app.nfprogress.tracker` |
| macOS Intel | `nfprogress.app` in DMG, locally wrapped as `nfprogress-tauri-mac-intel-V.zip` | `.app.tar.gz` plus `.sig` when enabled | `app.nfprogress.tracker` |
| Windows x64 | NSIS `*-setup.exe` | signed NSIS installer plus `.sig` | `app.nfprogress.tracker`, current-user install |

The checked-in Windows workflow explicitly builds `x86_64-pc-windows-msvc`
with `--bundles nsis`. The macOS scripts build separate
`aarch64-apple-darwin` and `x86_64-apple-darwin` artifacts. MSI is available
from base `targets: all`, but is not the supported release format.

## Decision: hybrid explicit transition (D, with C installer handoff)

```text
legacy app/data
  → user closes legacy app
  → signed helper detect/preview/prepare/verify
  → READY_FOR_TAURI in the same data root
  → signed platform installer
  → Tauri startup gate and first launch
  → Tauri updater for subsequent releases
```

The old updater must not unpack a Tauri bundle. A transitional Python release
is required to present this handoff and, after explicit confirmation,
download/verify and launch the signed installer. The helper is never silently
executed by an updater. If the helper is unavailable, the explicit Python
bridge remains a fallback and must use the same bundle/import boundary.

Preparation happens before installation. A failed download, helper run, or
installer launch leaves the old app and source files usable. A failed new first
launch leaves the pre-transition backup and signed installer available.

## Identity and data continuity

| Concern | Legacy | Tauri | F10 policy |
| --- | --- | --- | --- |
| User-visible name | `nfprogress` | `nfprogress` | preserve |
| Windows executable | `nfprogress.exe`; updater `nfprogress-updater.exe` | Tauri Cargo package emits `nfprogress-desktop.exe` in the NSIS package; final CI inspection is required | installer owns new shortcuts |
| macOS bundle | expected `nfprogress.app`; legacy binary name is not fixed in source | `nfprogress.app`, binary `Contents/MacOS/nfprogress-desktop` | deterministic replacement |
| macOS identifier | not declared/proven | `app.nfprogress.tracker` | package identity may change; data identity cannot |
| Windows data | `%APPDATA%\nfprogress`; legacy discovery also copies from `%USERPROFILE%\Documents\nfprogress` | `%APPDATA%\nfprogress` | prepare canonical root first |
| macOS data | `~/Documents/nfprogress` | `~/Documents/nfprogress` | same root |

Tauri startup sees legacy files without a complete marker as
`migration_required`, never as a fresh empty workspace. Old and new apps must
not concurrently mutate the profile: after preparation begins, the legacy app
stays closed until transition completion.

## State machine and recovery

```text
legacy_running → data_backup_created → migration_required
  → migration_prepared → installer_ready → installing
  → tauri_installed → tauri_verified → transition_complete

Any failure → transition_failed → unchanged source/backup + diagnostic report
```

The helper supplies source fingerprints, sealed backups, atomic staging/
activation and `READY_FOR_TAURI`. The wrapper records only version,
platform/architecture, stage, backup path and error code; no document bodies or
signing secrets. Same-source retries are idempotent. A changed fingerprint
requires a new preview and backup. Interrupted download, backup, prepare,
installer, install or first launch is recovered by marker/backup inspection;
no partial DB is authoritative.

Software rollback is separate from data rollback. Before schema migration,
reinstalling the old app against unchanged source is allowed. After migration,
stop rollout and fix/retain Tauri, or restore the matching pre-migration backup
before reinstalling the old app. Never blindly downgrade v6.

## Version, trust and rollout

Legacy versions use the existing numeric comparison and must never interpret
Tauri `latest.json` as a legacy release. The transitional manifest has a
distinct installer/helper section and a minimum legacy source version. Tauri
uses SemVer and its embedded public updater key. Legacy updates terminate at
the transitional version; Tauri then uses only its own endpoint, so there is no
downgrade loop.

Every transition download has HTTPS, expected size and SHA-256. Windows also
requires a valid Authenticode signature. macOS requires Developer ID signing,
hardened runtime, notarization and Gatekeeper verification. Tauri update
bundles use generated `.sig` content and the embedded public key. The
documentation fixture is
[`F10_proposed_manifest_sequence.example.json`](examples/F10_proposed_manifest_sequence.example.json).

Rollout is private/developer → selected testers → small cohort → wider cohort
→ stable. Stop rollout by withdrawing transition metadata or pointing the
legacy manifest back to the last safe legacy version. This does not downgrade
already migrated data.

## Qualification result

The safe strategy is selected, but F10 remains **BLOCKED** until a transitional
release is built, signed and rehearsed on copied real data for all supported
platforms. The checked-in manual qualification workflow builds unsigned
evidence only and never publishes.
