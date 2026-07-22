#!/usr/bin/env python3
import argparse
import hashlib
import struct
import zipfile
from pathlib import Path, PurePosixPath


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_pe(path: Path, *, allow_large_overlay: bool = False) -> str:
    if not path.is_file():
        raise SystemExit(f"Missing PE file: {path}")
    data = path.read_bytes()
    if len(data) < 64 or data[:2] != b"MZ":
        raise SystemExit(f"Invalid DOS/PE header: {path}")
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise SystemExit(f"Invalid PE signature: {path}")

    section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    optional_offset = pe_offset + 24
    section_table = optional_offset + optional_size
    if section_table + section_count * 40 > len(data):
        raise SystemExit(f"Invalid PE section table: {path}")

    image_end = 0
    for index in range(section_count):
        section_offset = section_table + index * 40
        raw_size = struct.unpack_from("<I", data, section_offset + 16)[0]
        raw_offset = struct.unpack_from("<I", data, section_offset + 20)[0]
        image_end = max(image_end, raw_offset + raw_size)

    magic = struct.unpack_from("<H", data, optional_offset)[0]
    if magic not in (0x10B, 0x20B):
        raise SystemExit(f"Unknown PE optional-header format in {path}: 0x{magic:04x}")
    directory_offset = optional_offset + (112 if magic == 0x20B else 96)
    certificate_end = 0
    certificate_size = 0
    security_entry = directory_offset + 8 * 4
    if security_entry + 8 <= section_table:
        certificate_offset, certificate_size = struct.unpack_from("<II", data, security_entry)
        certificate_end = certificate_offset + certificate_size if certificate_size else 0

    known_end = max(image_end, certificate_end)
    overlay_size = max(0, len(data) - known_end)
    if overlay_size > 1024 * 1024 and not allow_large_overlay:
        raise SystemExit(
            f"Unexpected PE overlay in {path}: {overlay_size} bytes. "
            "This may indicate an embedded onefile payload."
        )
    return (
        f"{path.name}: size={len(data)}, sections={section_count}, "
        f"certificate_size={certificate_size}, "
        f"overlay_size={overlay_size}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("package_dir", type=Path)
    parser.add_argument("archive", type=Path)
    parser.add_argument("checksums", type=Path)
    parser.add_argument("--installer", type=Path)
    args = parser.parse_args()

    main_exe = args.package_dir / "nfprogress.exe"
    updater_exe = args.package_dir / "nfprogress-updater.exe"
    runtime_updater = args.package_dir / "updater-runtime" / "nfprogress-updater.exe"
    pe_results = [inspect_pe(executable) for executable in (main_exe, updater_exe, runtime_updater)]
    if args.installer is not None:
        pe_results.append(inspect_pe(args.installer, allow_large_overlay=True))

    with zipfile.ZipFile(args.archive) as archive:
        files = [PurePosixPath(info.filename) for info in archive.infolist() if not info.is_dir()]
        roots = {path.parts[0] for path in files if path.parts}
        if roots != {"nfprogress"}:
            raise SystemExit(f"Archive must have one nfprogress/ root, found: {sorted(roots)}")
        names = {path.as_posix() for path in files}
        required = {
            "nfprogress/nfprogress.exe",
            "nfprogress/nfprogress-updater.exe",
            "nfprogress/updater-runtime/nfprogress-updater.exe",
        }
        missing = required - names
        if missing:
            raise SystemExit(f"Archive is missing: {sorted(missing)}")

    lines = [
        f"{sha256(args.archive)}  {args.archive.name}",
        f"{sha256(main_exe)}  nfprogress.exe",
        f"{sha256(updater_exe)}  nfprogress-updater.exe",
    ]
    if args.installer is not None:
        lines.append(f"{sha256(args.installer)}  {args.installer.name}")
    args.checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")
    pe_report = args.checksums.with_name("pe-inspection-windows.txt")
    pe_report.write_text("\n".join(pe_results) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print("\n".join(pe_results))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
