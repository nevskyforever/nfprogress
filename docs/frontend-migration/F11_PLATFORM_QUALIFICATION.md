# NFProgress — F11 platform qualification

Дата: 2026-09-05. Qualification source is the F11 working HEAD descended
directly from baseline `3b3980d`. This is a private/non-publishing report.

## Current result

| Platform | Build/package | Helper | Functional install/launch/restart | Current status |
| --- | --- | --- | --- | --- |
| macOS ARM | real local Tauri build, arm64, DMG verified, provenance verified | real arm64 one-file helper; detect/preview/prepare/verify passed | not completed: qualification bundle launch was prevented by the already-running `/Applications/nfprogress.app` single-instance process | **BLOCKED — P0 runtime evidence** |
| macOS Intel | Intel build support retained; no Intel host/runner used | no Intel helper runtime | deferred from the initial rollout | **DEFERRED — P1/backlog** |
| Windows x64 | separate manual `f11-windows-qualification.yml` targets `windows-latest` and NSIS | packaged helper smoke is required on the hosted runner | not run from this host; workflow is ready for dispatch | **NOT TESTED — P0 evidence pending** |

OS signing limitations are not the reason for any status above. Under the
current policy, macOS ad-hoc and Windows unsigned artifacts are acceptable
with documented Gatekeeper/SmartScreen warnings. The remaining statuses are
functional and cross-generation evidence gaps.

## macOS ARM evidence

The local build used `scripts/build-tauri-local.sh arm` and produced
`build-tauri-arm/nfprogress-tauri-mac-arm-5.3.9.zip`. The archive contains the
`SOURCE_CODE.txt` revision matching the qualification HEAD. The embedded app
binary is Mach-O arm64 and the DMG checksum verification passed.

The existing running `/Applications/nfprogress.app` was verified as an arm64
NFProgress Tauri product, but it was not terminated because its ownership/use
could not be established as a development process. The qualification app
therefore exited immediately when started directly, consistent with the
single-instance gate. No PASS is claimed for first launch or restart.

## macOS Intel and Windows

No Intel runtime and no Windows x64 runtime were available in this
environment. Intel build support remains in the project, but macOS Intel is
explicitly **DEFERRED / NOT IN INITIAL RELEASE SCOPE** and is not a readiness
gate for the first wave. Windows remains in scope and has a dedicated manual
workflow, but it could not be dispatched from this host because GitHub CLI and
runner credentials are unavailable. A Windows run must attach the artifact
name, SHA-256, exact checkout SHA, helper smoke output, resolved data paths,
install path, first-launch result, restart result, and recovery results.

## Trust limitation

The owner accepts unsigned/ad-hoc/self-signed distribution for this rollout.
Gatekeeper may require an explicit user confirmation on macOS; SmartScreen may
show an unrecognized-app warning on Windows. These are `P1` limitations.
They do not make an artifact integrity check or Tauri updater signature
optional.

## Readiness decision

The intended first-release platform set is **macOS ARM64 and Windows x64**.
macOS Intel is **DEFERRED / NOT IN INITIAL RELEASE SCOPE** and may be added in
a later qualification wave. Current status is **BLOCKED** only until the
remaining functional P0 runtime and transition rehearsals are executed on the
two intended platforms; missing OS signing credentials are not P0 blockers.
