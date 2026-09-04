import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_f11_distribution_policy_separates_os_trust_from_updater_trust():
    signing = (ROOT / "docs/frontend-migration/F11_PRODUCTION_SIGNING.md").read_text(
        encoding="utf-8"
    )
    gates = (ROOT / "docs/frontend-migration/F11_RELEASE_GATE_CHECKLIST.md").read_text(
        encoding="utf-8"
    )
    assert "## Current Distribution Trust Policy" in signing
    assert "known release limitation (`P1`)" in signing
    assert "Tauri updater key remains a separate security gate" in signing
    assert "Developer ID and notarization for macOS" in gates
    assert "Authenticode for Windows" in gates


def test_f11_transition_fixture_keeps_platforms_and_version_boundary_explicit():
    fixture = json.loads(
        (ROOT / "docs/frontend-migration/examples/F10_proposed_manifest_sequence.example.json")
        .read_text(encoding="utf-8")
    )
    assert fixture["legacy_release"]["version"] == "5.3.10"
    assert fixture["transition_release"]["installer"]["darwin-aarch64"]["url"].endswith(
        "6.0.0.dmg"
    )
    assert fixture["tauri_after_transition"]["signature"] == (
        "Tauri generated .sig content, not a URL"
    )
    assert set(fixture["tauri_after_transition"]["platform_keys"]) == {
        "windows-x86_64", "darwin-aarch64", "darwin-x86_64",
    }


def test_macos_signing_container_covers_optional_helper():
    script = (ROOT / "scripts/sign-notarize-macos.sh").read_text(encoding="utf-8")
    assert 'cp -- "$HELPER_PATH" "$STAGING_DIR/nfprogress-migration-helper"' in script
    assert "xcrun notarytool submit" in script
    assert "xcrun stapler validate" in script


def test_f11_initial_scope_and_windows_workflow_are_explicit():
    qualification = (ROOT / "docs/frontend-migration/F11_PLATFORM_QUALIFICATION.md").read_text(
        encoding="utf-8"
    )
    workflow = (ROOT / ".github/workflows/f11-windows-qualification.yml").read_text(
        encoding="utf-8"
    )
    assert "macOS ARM64 and Windows x64" in qualification
    assert "DEFERRED / NOT IN INITIAL RELEASE SCOPE" in qualification
    assert "workflow_dispatch" in workflow
    assert "ref: ${{ github.ref }}" in workflow
    assert "runs-on: windows-latest" in workflow
    assert "x86_64-pc-windows-msvc" in workflow
    assert "f11-windows-x86_64-${{ steps.provenance.outputs.commit_sha }}" in workflow
    assert "update_manifest.json" not in workflow
    assert "update_manifest_legacy.json" not in workflow
