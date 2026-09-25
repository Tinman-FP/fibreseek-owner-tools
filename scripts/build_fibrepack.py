#!/usr/bin/env python3
"""Build a FibreSeeker 3 owner-access package with an owner's SSH key."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import zipfile


DEFAULT_VERSION = "2.2.42.832.321"
VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){4}$")
PRIVATE_KEY_MARKERS = ("PRIVATE KEY", "OPENSSH PRIVATE")


def die(message: str) -> None:
    raise SystemExit(f"error: {message}")


def read_public_key(path: Path) -> str:
    if not path.is_file():
        die(f"public key not found: {path}")
    raw = path.read_text(encoding="utf-8").strip()
    if any(marker in raw for marker in PRIVATE_KEY_MARKERS):
        die("the supplied file appears to be a private key")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if len(lines) != 1:
        die("the public-key file must contain exactly one non-empty line")
    fields = lines[0].split()
    if len(fields) < 2 or fields[0] != "ssh-ed25519":
        die("an ssh-ed25519 public key is required")
    return lines[0]


def fingerprint(public_key: str) -> str:
    ssh_keygen = shutil.which("ssh-keygen")
    if not ssh_keygen:
        die("ssh-keygen was not found in PATH")
    result = subprocess.run(
        [ssh_keygen, "-lf", "-"],
        input=public_key + "\n",
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        die(f"ssh-keygen rejected the public key: {result.stderr.strip()}")
    fields = result.stdout.split()
    if len(fields) < 2:
        die("could not determine the public-key fingerprint")
    return fields[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-key", required=True, type=Path)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--output-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()

    if not VERSION_RE.fullmatch(args.version):
        die("--version must contain five dot-separated numeric fields")

    repo_root = Path(__file__).resolve().parents[1]
    template_path = repo_root / "payload" / "fibreseek-installer.in"
    template = template_path.read_text(encoding="utf-8")
    public_key = read_public_key(args.public_key.expanduser())
    key_fingerprint = fingerprint(public_key)
    installer = template.replace("__PUBLIC_KEY_SHELL__", shlex.quote(public_key))
    installer = installer.replace(
        "__KEY_FINGERPRINT_SHELL__", shlex.quote(key_fingerprint)
    )
    if "__PUBLIC_KEY_SHELL__" in installer or "__KEY_FINGERPRINT_SHELL__" in installer:
        die("payload template substitution failed")

    syntax = subprocess.run(
        ["bash", "-n"],
        input=installer,
        text=True,
        capture_output=True,
        check=False,
    )
    if syntax.returncode != 0:
        die(f"generated installer failed shell syntax validation: {syntax.stderr.strip()}")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    package = output_dir / f"fibreseek-sk3-{args.version}.fibrepack"
    checksum_path = package.with_suffix(package.suffix + ".sha256")

    info = zipfile.ZipInfo("fibreseek-installer")
    info.date_time = (2026, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100755 & 0xFFFF) << 16
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr(info, installer.encode("utf-8"))

    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    checksum_path.write_text(f"{digest}  {package.name}\n", encoding="ascii")

    print(f"Package: {package}")
    print(f"SHA-256: {digest}")
    print(f"SSH key: {key_fingerprint}")
    print("USB path: FIBRESEEK/" + package.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
