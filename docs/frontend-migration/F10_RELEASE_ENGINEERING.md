# NFProgress — F10 release engineering qualification

Дата: 2026-09-04. Baseline HEAD: `27d09249f1df88c89d10698b58f2f5fa4515fab0`.
F10 audits delivery without publishing or changing either production manifest.

## Executive decision

Production status: **BLOCKED**.

The selected path is a hybrid explicit transition: a separately signed helper
prepares data, then a separately signed platform installer hands off to Tauri.
A transitional Python release is required because the current legacy Windows
updater cannot install a Tauri NSIS bundle and the macOS replacement path has
no signed cross-generation proof. No compatibility hack was added.

## Production delivery audit

| Platform | Current artifact | Current executable/app | Package/update | Identifier | Data path | Manifest/updater | Tauri equivalent | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| macOS ARM | hosted `nfprogress-mac-arm-V.zip` | legacy bundle discovered at runtime; expected `nfprogress.app` | legacy ZIP + detached shell replacement | old ID not declared | `~/Documents/nfprogress` | `https://nfproject.ru/app/update_manifest.json` | `nfprogress.app`; Mach-O `Contents/MacOS/nfprogress-desktop`; Tauri updater bundle + `.sig` | ad-hoc F10 build; no signed transition proof |
| macOS Intel | hosted `nfprogress-mac-intel-V.zip` | same discovery | same | old ID not declared | `~/Documents/nfprogress` | same | x86_64 `nfprogress.app`; Mach-O `Contents/MacOS/nfprogress-desktop`; updater bundle | Intel helper/runtime/signing proof pending |
| Windows x64 | hosted `nfprogress-windows-x86_64-V-setup.exe` | `nfprogress.exe`; updater `nfprogress-updater.exe` | legacy ZIP contract; current workflow NSIS | old identity not declared | `%APPDATA%\nfprogress`; legacy Documents copy | flat legacy manifest; Tauri GitHub `latest.json` | NSIS `*-setup.exe`, Tauri `.sig`, `app.nfprogress.tracker` | direct mismatch |

Legacy updater integrity is SHA-256 only. Tauri update integrity is generated
signature content validated by an embedded public key. The Tauri bundle has no
Python sidecar or helper.

## Handoff contract

```text
legacy_running → backup + source fingerprint
  → signed helper detect/preview/prepare/verify
  → READY_FOR_TAURI in canonical data root
  → signed current-user installer
  → Tauri readiness gate
  → first launch/restart on the same SQLite
```

The helper is never invoked automatically by the updater. The legacy app is
closed before prepare and cannot concurrently write the authoritative profile.
Tauri reports `migration_required` rather than creating an empty workspace
when legacy files exist without a complete marker.

Interruption is fail-closed: download failure leaves old app; helper failure
leaves source and backup; installer failure leaves recoverable prepared data;
first-launch failure leaves the pre-migration backup and recovery path. Same
source is idempotent; changed source requires a new preview. Software rollback
is separate from data rollback and never blindly downgrades v6.

## Artifact and trust evidence

The final F10 qualification build is made from the commit reported below.
Its ARM and Intel ZIPs contain the matching source revision and both DMGs
passed `hdiutil verify`; ARM is Mach-O arm64 and Intel is Mach-O x86_64.
These local artifacts are ad-hoc/linker-signed or unsigned without a
Developer ID Team ID, and neither is notarized. They are qualification
artifacts, not production evidence. The ARM helper was rebuilt as a one-file
arm64 Mach-O and passed packaged `detect`/`preview` on an isolated fixture.
Intel helper build and runtime require the Intel runner.

The manual qualification workflow builds ARM, Intel and Windows evidence
without publishing. The macOS signing/notarization script fails if identities
or profiles are absent. Windows still requires real CI artifact,
Authenticode, packaged helper and runtime rehearsal. These gates keep the
result BLOCKED.

See [`F10_UPDATER_TRANSITION.md`](F10_UPDATER_TRANSITION.md) for state,
identity, version, rollback and rollout rules, and
[`F10_SIGNING_AND_PLATFORM_MATRIX.md`](F10_SIGNING_AND_PLATFORM_MATRIX.md) for
signing, sandbox and CI secret policy.

## Test evidence

| Layer | Result |
| --- | --- |
| Python focused migration/recovery/release/updater profile | `64 passed, 2 subtests passed` |
| Rust (`cargo fmt --check`, `cargo check`, `cargo test`) | `32 passed` |
| Frontend typecheck | passed |
| Frontend tests | `261 passed` |
| Frontend build | passed; existing sourcemap/dynamic-import/large-chunk warnings |
| Full Python suite | not rerun in F10; F9 recorded `560 passed, 3 failed, 15 skipped` before known hang |

Known Python failures are the legacy PySide accessibility test, Web OpenAPI
developer-response contract test and weekly-symbol boundary test. No F10 hang
node was reproduced, so no test is newly excluded.

## Rollout and manifest policy

The documentation-only proposed sequence is in
[`examples/F10_proposed_manifest_sequence.example.json`](examples/F10_proposed_manifest_sequence.example.json):

1. ship a final transitional legacy version with helper/installer fields;
2. qualify on copied fixtures privately;
3. offer selected testers, then a small cohort;
4. enable Tauri `latest.json` after first-launch evidence;
5. widen rollout and only then update stable hosting metadata.

Production manifests were not overwritten, regenerated or uploaded. The push
workflow now requires an explicit manual boolean and protected
`nfprogress-production` environment before publish can run. Stop rollout by
withdrawing new transition metadata; do not downgrade migrated profiles.

## Remaining P0 blockers

- transitional release and end-to-end installer rehearsal;
- macOS Developer ID, hardened runtime, notarization/stapling and Gatekeeper
  evidence for ARM and Intel;
- Intel helper and Intel runtime rehearsal;
- Windows CI Tauri artifact, Authenticode, helper and Windows runtime
  migration/restart rehearsal;
- final-commit artifacts and release-owner approval of manifest cutover.

No public release is authorized by F10.
