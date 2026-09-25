#!/usr/bin/env python3
"""Build native desktop release artifacts on macOS, Windows, or Linux."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile


APP_NAME = "FibreSeek Owner Access"
ASSET_STEM = "FibreSeek-Owner-Access"
REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_ROOT = REPO_ROOT / "build" / "pyinstaller"
DIST_ROOT = REPO_ROOT / "dist-desktop"
BUNDLE_ROOT = DIST_ROOT / "bundle"
RELEASE_ROOT = DIST_ROOT / "release"


def run(*args: str) -> None:
    subprocess.run(args, cwd=REPO_ROOT, check=True)


def normalized_arch() -> str:
    machine = platform.machine().lower()
    if machine in {"amd64", "x86_64"}:
        return "x64"
    if machine in {"arm64", "aarch64"}:
        return "arm64"
    return machine.replace(" ", "-")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(paths: list[Path], label: str) -> Path:
    checksum_path = RELEASE_ROOT / f"SHA256SUMS-{label}.txt"
    lines = [f"{sha256(path)}  {path.name}" for path in paths]
    with checksum_path.open("w", encoding="ascii", newline="\n") as output:
        output.write("\n".join(lines) + "\n")
    return checksum_path


def pyinstaller_args() -> list[str]:
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--paths",
        str(REPO_ROOT),
        "--add-data",
        f"{REPO_ROOT / 'payload' / 'fibreseek-installer.in'}{os.pathsep}payload",
        "--distpath",
        str(BUNDLE_ROOT),
        "--workpath",
        str(BUILD_ROOT / "work"),
        "--specpath",
        str(BUILD_ROOT),
    ]
    if sys.platform != "darwin":
        args.append("--onefile")
    args.append(str(REPO_ROOT / "fibreseek_access" / "app.py"))
    return args


def package_macos() -> list[Path]:
    app_path = BUNDLE_ROOT / f"{APP_NAME}.app"
    run("codesign", "--force", "--deep", "--sign", "-", str(app_path))

    arch_label = "Apple-Silicon" if normalized_arch() == "arm64" else "Intel"
    label = f"macOS-{arch_label}"
    zip_path = RELEASE_ROOT / f"{ASSET_STEM}-{label}.zip"
    dmg_path = RELEASE_ROOT / f"{ASSET_STEM}-{label}.dmg"
    run(
        "ditto",
        "-c",
        "-k",
        "--sequesterRsrc",
        "--keepParent",
        str(app_path),
        str(zip_path),
    )

    with tempfile.TemporaryDirectory(prefix="fibreseek-owner-access-dmg-") as tmp:
        stage = Path(tmp)
        shutil.copytree(app_path, stage / app_path.name, symlinks=True)
        (stage / "Applications").symlink_to("/Applications")
        run(
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
            "-srcfolder",
            str(stage),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        )

    write_checksums([dmg_path, zip_path], label)
    return [dmg_path, zip_path]


def package_windows() -> list[Path]:
    source = BUNDLE_ROOT / f"{APP_NAME}.exe"
    output = RELEASE_ROOT / f"{ASSET_STEM}-Windows-{normalized_arch()}.exe"
    shutil.copy2(source, output)
    write_checksums([output], f"Windows-{normalized_arch()}")
    return [output]


def package_linux() -> list[Path]:
    source = BUNDLE_ROOT / APP_NAME
    binary_name = f"{ASSET_STEM}-Linux-{normalized_arch()}"
    binary_path = RELEASE_ROOT / binary_name
    shutil.copy2(source, binary_path)
    binary_path.chmod(0o755)
    archive_path = RELEASE_ROOT / f"{binary_name}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(binary_path, arcname=binary_name)
    binary_path.unlink()
    write_checksums([archive_path], f"Linux-{normalized_arch()}")
    return [archive_path]


def main() -> None:
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    shutil.rmtree(DIST_ROOT, ignore_errors=True)
    BUILD_ROOT.mkdir(parents=True)
    BUNDLE_ROOT.mkdir(parents=True)
    RELEASE_ROOT.mkdir(parents=True)

    run(*pyinstaller_args())
    if sys.platform == "darwin":
        artifacts = package_macos()
    elif os.name == "nt":
        artifacts = package_windows()
    elif sys.platform.startswith("linux"):
        artifacts = package_linux()
    else:
        raise SystemExit(f"Unsupported desktop build platform: {sys.platform}")

    print("Desktop release artifacts:")
    for artifact in artifacts:
        print(f"  {artifact}")


if __name__ == "__main__":
    main()
