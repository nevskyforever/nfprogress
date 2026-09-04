# NFProgress — F8 release rollout plan

Это план подготовки, не команда публикации. `update_manifest.json` и
`update_manifest_legacy.json` намеренно не изменяются в F8.

## Artifacts and exact later changes

For a future release, publish only after qualification:

- signed macOS ARM artifact and its SHA-256;
- signed macOS Intel artifact and its SHA-256;
- signed Windows x64 NSIS installer, `.sig` and Tauri `latest.json`;
- release notes and a checksum list;
- separately packaged migration helper/bridge artifact, if that is the chosen
  legacy strategy.

The later release owner must update the platform-specific sections in the two
legacy manifests without overwriting unrelated user changes, then verify the
remote manifest and hosted assets. The current legacy manifest shape points to
`nfproject.ru` while the Windows Tauri updater workflow publishes GitHub
Release metadata; this cross-generation contract needs an explicit cutover.

The release config must continue to use identifier `app.nfprogress.tracker`,
Tauri updater signatures, Windows `x86_64-pc-windows-msvc`, and the existing
macOS ARM/Intel targets. No private signing key belongs in the repository.

## Sequence

1. Complete the P0 gates in `F8_RELEASE_QUALIFICATION.md`.
2. Produce fresh artifacts from the release commit and prove the embedded
   source revision equals that commit.
3. Rehearse the local helper and restore flow on copies of representative real
   profiles.
4. Release to developer/private testing.
5. Release to a small tester cohort with manual support coverage.
6. Expand to a wider cohort after migration/restart/restore evidence is clean.
7. Only then enable general availability and update the remote manifests.

No telemetry is introduced by this plan. Support should collect only versions,
state codes, counts and IDs unless the user explicitly enables debug logging;
raw note/document bodies are excluded.

## Rollback

Stop the rollout and revert the remote manifest if a P0/P1 issue appears.
Preserve existing data and all pre-upgrade backups. Do not ask users to launch
an old Python app against a schema it cannot read. A safe rollback is either:

- reinstall the prior app while retaining its unchanged pre-migration profile;
- restore the matching pre-migration backup, then reinstall the prior app;
- keep the new SQLite and fix the new app when the schema is already migrated.

Downgrade is unsupported after schema migration unless a tested matching backup
exists. The release owner must not delete rollback artifacts during the initial
rollout window.

## Current readiness decision

F8 does not authorize publication. Local ARM/Intel qualification artifacts were
built and inspected, but they are unsigned qualification outputs; Windows was
not built locally and signing readiness is configuration-only. Release artifacts
must still be rebuilt and signed by the release pipeline from the final release
commit. The workflow currently contains a publish job; the later rollout change
must add the qualification gate before any production push is used.
