# NFProgress — F10 signing and platform matrix

Дата аудита: 2026-09-04. Status reflects actual repository configuration and
evidence available on the ARM macOS qualification host.

## Platform matrix

| Platform | App artifact/build | Helper | Migration/runtime | OS signing | Notarization | Readiness |
| --- | --- | --- | --- | --- | --- | --- |
| macOS ARM | Final F10 DMG/ZIP, arm64; DMG verified | F10 one-file arm64 helper; packaged detect/preview passed | helper fixture path qualified; signed full transition not rehearsed | ad-hoc/linker-signed, no Team ID | not run | **BLOCKED** |
| macOS Intel | Final F10 DMG/ZIP, x86_64; DMG verified | no Intel artifact on ARM host; Intel runner required | Intel runtime not proven | unsigned/Developer ID not tested | not run | **BLOCKED** |
| Windows x64 | workflow targets `x86_64-pc-windows-msvc` and NSIS | no packaged Windows helper evidence | Windows runtime rehearsal unavailable here | no Authenticode evidence | n/a | **BLOCKED** |

The separate manual `.github/workflows/release-qualification.yml` is the
non-publishing path for ARM, Intel and Windows. It uploads only 14-day Actions
artifacts and does not claim production signing when credentials are absent.

## macOS signing pipeline

[`scripts/sign-notarize-macos.sh`](../../scripts/sign-notarize-macos.sh) is a
fail-closed pipeline:

```text
Tauri app → Developer ID + secure timestamp + hardened runtime
  → codesign --verify --deep --strict → DMG
  → xcrun notarytool submit --keychain-profile ... --wait
  → xcrun stapler staple/validate → spctl assessment
```

The optional helper argument is signed and verified with the same identity.
The helper must be included in the notarization submission used for its
distribution package or submitted as its own notarized command-line artifact;
the final helper container remains a release-owner decision. The script uses a
keychain profile, not credentials in files or command-line arguments.

The current Tauri configuration has no `bundle.macOS.entitlements` and no App
Sandbox entitlement. Security-scoped bookmarks are therefore not required by
the checked-in sandbox configuration. External Word/Scrivener access still
needs a signed/restarted macOS rehearsal, including TCC prompts, and remains
P1. Do not add broad entitlements to silence a signing failure.

Production gates are `codesign`, `spctl`, `notarytool` and `stapler`; ad-hoc
signing is qualification-only. `com.apple.security.get-task-allow` must not be
enabled.

## Windows signing pipeline

The production workflow builds a current-user NSIS installer and Tauri updater
signature:

```text
NSIS -setup.exe
  → Authenticode on installer and inner executable(s)
  → timestamp verification
  → Tauri .sig and latest.json
  → copied-fixture helper smoke
  → Windows install/restart/migration rehearsal
```

The certificate source is external to the repository: OV/EV or a trusted
signing service such as Azure Artifact Signing may be used with the issuer’s
supported workflow. The helper must not be shipped unsigned.

The protected production workflow now invokes
[`scripts/sign-windows-artifacts.ps1`](../../scripts/sign-windows-artifacts.ps1)
only for an explicitly requested production dispatch. It signs the Tauri
executable and NSIS installer with `signtool`, requires a CI-provided PFX and
timestamp URL, and fails unless `Get-AuthenticodeSignature` returns `Valid`.
The qualification workflow intentionally produces unsigned evidence and does
not publish it.

## Tauri updater key continuity

CI creates an ephemeral release overlay containing the public key and GitHub
`latest.json` endpoint. `TAURI_SIGNING_PRIVATE_KEY` and its optional password
are GitHub secrets; `TAURI_UPDATER_PUBLIC_KEY` is a repository variable/secret.
The updater key must be generated once and preserved for subsequent Tauri
releases; rotate only with a planned compatibility release.

## Package boundary and CI secrets

The Tauri bundle has no `externalBin`; it must contain no Python, FastAPI,
Nuitka backend, PKL parser or migration helper. The helper is a separate
one-file PyInstaller artifact, used once before Tauri and not required after
`READY_FOR_TAURI`.

Required secret categories, never values:

- Apple Developer ID and notary profile/API credentials;
- Windows Authenticode certificate or signing-service credentials;
- `TAURI_SIGNING_PRIVATE_KEY` and optional password;
- `TAURI_UPDATER_PUBLIC_KEY`;
- hosting SSH key only in the publish job;
- Telegram credentials only in the notification job.

Signing jobs must run only from trusted branches/tags or approved dispatch,
never forked PRs; build jobs use read-only permissions, short-lived artifacts,
pinned actions and a protected `nfprogress-production` environment. The normal
push workflow now builds but does not publish.

## F11 current distribution policy

The owner currently accepts unsigned/ad-hoc/self-signed distribution.
Developer ID, notarization, and Authenticode are known release limitations
(`P1`) rather than standalone `P0` blockers. Gatekeeper unidentified-developer
and SmartScreen unrecognized-app warnings are expected and must be documented.
The existing signing paths remain optional future hardening and stay
fail-closed when explicitly enabled.

## F11 current conclusion

**BLOCKED** for functional qualification: the ARM helper passed, but the
ARM app launch/restart leg, Windows runtime, full cross-generation handoff,
and production Tauri updater-key path remain unqualified. Intel runtime is
deferred because macOS Intel is not in the initial rollout scope. This status
is not caused by missing OS signing credentials.
