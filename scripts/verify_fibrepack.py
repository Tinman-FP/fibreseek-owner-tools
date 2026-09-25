#!/usr/bin/env python3
"""Inspect a generated FibreSeeker owner-access package."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import stat
import sys
import zipfile


def die(message: str) -> None:
    raise SystemExit(f"error: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--public-key", type=Path)
    args = parser.parse_args()

    package = args.package.expanduser().resolve()
    if not package.is_file():
        die(f"package not found: {package}")

    try:
        with zipfile.ZipFile(package) as archive:
            names = archive.namelist()
            if names != ["fibreseek-installer"]:
                die(f"unexpected archive contents: {names!r}")
            info = archive.getinfo("fibreseek-installer")
            mode = (info.external_attr >> 16) & 0xFFFF
            if not mode or not (mode & stat.S_IXUSR):
                die("fibreseek-installer is not marked executable")
            payload = archive.read(info).decode("utf-8")
    except (zipfile.BadZipFile, UnicodeDecodeError) as exc:
        die(f"invalid package: {exc}")

    if not payload.startswith("#!/bin/bash\n"):
        die("installer does not start with the expected shell header")
    if "PRIVATE KEY" in payload or "OPENSSH PRIVATE" in payload:
        die("package contains a private-key marker")
    if args.public_key:
        expected = args.public_key.expanduser().read_text(encoding="utf-8").strip()
        if expected not in payload:
            die("package does not contain the expected public key")

    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    print(f"OK: {package}")
    print(f"SHA-256: {digest}")
    print("Contents: fibreseek-installer (executable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
