# NFProgress — F11 platform qualification

Дата: 2026-09-05. Qualification source is the F11 working HEAD descended
directly from baseline `3b3980d`. This is a private/non-publishing report.

## Current result

| Platform | Build/package | Helper | Functional install/launch/restart | Current status |
| --- | --- | --- | --- | --- |
| macOS ARM | real local Tauri build, arm64, DMG verified, provenance verified | real arm64 one-file helper; detect/preview/prepare/verify passed | not completed: qualification bundle launch was prevented by the already-running `/Applications/nfprogress.app` single-instance process | **BLOCKED — P0 runtime evidence** |
| macOS Intel | no Intel host/runner used | no Intel helper runtime | not tested; cross-build is not evidence | **NOT TESTED — P0** |
| Windows x64 | no Windows runner used; no NSIS artifact | no packaged Windows helper | not tested | **NOT TESTED — P0** |

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
environment. The checked-in manual workflow targets `macos-14` ARM,
`macos-13` Intel, and `windows-latest`, but it was not dispatched here because
the GitHub CLI/runner credentials are unavailable. Any later run must attach
the artifact name, SHA-256, commit SHA, helper smoke output, install path,
first-launch result, restart result, and recovery results.

## Trust limitation

The owner accepts unsigned/ad-hoc/self-signed distribution for this rollout.
Gatekeeper may require an explicit user confirmation on macOS; SmartScreen may
show an unrecognized-app warning on Windows. These are `P1` limitations.
They do not make an artifact integrity check or Tauri updater signature
optional.

## Readiness decision

The intended first-release platform set remains macOS ARM, macOS Intel, and
Windows x64. No intentional Intel/Windows exclusion has been approved, so an
ARM-only rollout is technically possible but not authorized by this matrix.
Current platform-independent status is **BLOCKED** until the functional P0
runtime and transition rehearsals are executed.
