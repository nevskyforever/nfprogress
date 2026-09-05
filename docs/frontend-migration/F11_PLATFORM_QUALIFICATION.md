# NFProgress — F11 platform qualification

Дата: 2026-09-05. Qualification source is the F11 working HEAD descended
directly from baseline `3b3980d`. This is a private/non-publishing report.

## Current result

| Platform | Build/package | Helper | Functional install/launch/restart | Current status |
| --- | --- | --- | --- | --- |
| macOS ARM | real local Tauri build, arm64, DMG verified, provenance verified | real arm64 one-file helper; detect/preview/prepare/verify passed | not completed: qualification bundle launch was prevented by the already-running `/Applications/nfprogress.app` single-instance process | **BLOCKED — P0 runtime evidence** |
| macOS Intel | Intel build support retained; no Intel host/runner used | no Intel helper runtime | deferred from the initial rollout | **DEFERRED — P1/backlog** |
| Windows x64 | manual run `33921490088` on `windows-latest`; checkout `ff4653d296182da723f1601a0c8a0d8d690fd64b`; Tauri build not reached after helper failure | `.exe` build, `detect`, `preview` passed; `prepare` failed with `[Errno 9] Bad file descriptor` | install/launch/restart not reached | **BLOCKED — P0 helper regression; rerun required** |

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

The first real Windows attempt reached job `101180595526`: frontend and Rust
checks passed (Rust reported 31 tests), Windows path/fallback fixture passed,
the helper `.exe` build/detect/preview passed, and `prepare` failed with exit
code `15` and `{"status":"migration_failed","error":"[Errno 9] Bad file descriptor"}`.
The first fix made directory fsync POSIX-only, but the rerun showed the same
generic error at the next Windows-incompatible descriptor operation:
`_fsync_file()` reopened a generated manifest as `rb` before `os.fsync`; a
Windows read-only CRT descriptor is rejected with `EBADF`. The new fix reopens
generated files as `r+b` without truncation, retains file fsync and atomic
`os.replace` activation, and adds phase/traceback diagnostics to CI. This
evidence is a genuine P0 regression result, not a Windows PASS; the workflow
must be rerun from the new fix commit.

The attached artifact from this run contained the JSON/path evidence but did
not contain the packaged helper itself, although the helper had executed on
the runner. The workflow now copies the helper into runner-temp before the
smoke and uploads that copy, together with a prepare traceback log, so a
failure artifact remains independently inspectable.

The next real run `33948433776`, job `101258604521`, checked out
`d22a9ad7e52e12b2fe032cb7365a4515ff62b26d` and reached
`phase=staging_activation`. Its traceback identified a Windows sharing
violation in `migration_helper._activate`: `os.replace()` could not replace the
staging `nfprogress.db` because SQLite connections opened by
`import_projects_bundle`, `_import_complete_bundle`, and
`read_projects_storage` were only leaving their transaction contexts, not
guaranteeing `connection.close()`. The fix wraps those database contexts in
`contextlib.closing`; backup/restore staging validation uses the same explicit
close rule. This preserves SQLite validation, file fsync, and atomic replace
semantics without retrying a sharing violation. The Windows workflow must be
rerun from the fix commit before helper or transition qualification can pass.

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
