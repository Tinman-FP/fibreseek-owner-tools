"""Core key, package, USB, and verification operations for owner access."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import plistlib
import re
import shlex
import shutil
import string
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


DEFAULT_VERSION = "2.2.42.832.321"
VERSION_RE = re.compile(r"^[0-9]+(?:\.[0-9]+){4}$")
KEY_COMMENT = "fibreseek-owner-access"


class OwnerAccessError(RuntimeError):
    """A recoverable, user-facing owner-access error."""


@dataclass(frozen=True)
class KeyInfo:
    private_path: Path
    public_path: Path
    fingerprint: str
    created: bool


@dataclass(frozen=True)
class PackageInfo:
    package_path: Path
    checksum_path: Path
    sha256: str
    fingerprint: str
    version: str


@dataclass(frozen=True)
class VerificationResult:
    moonraker_ok: bool
    ssh_ok: bool
    sudo_ok: bool
    details: str


def default_private_key_path() -> Path:
    return Path.home() / ".ssh" / "fibreseek_owner_ed25519"


def resource_path(relative: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root / relative


def _normalize_public_key(public_key: str) -> str:
    lines = [line.strip() for line in public_key.splitlines() if line.strip()]
    if len(lines) != 1:
        raise OwnerAccessError("The public-key file must contain one non-empty line.")
    fields = lines[0].split()
    if len(fields) < 2 or fields[0] != "ssh-ed25519":
        raise OwnerAccessError("An Ed25519 SSH public key is required.")
    try:
        decoded = base64.b64decode(fields[1], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise OwnerAccessError("The SSH public key is not valid base64 data.") from exc
    if not decoded:
        raise OwnerAccessError("The SSH public key is empty.")
    return lines[0]


def public_key_fingerprint(public_key: str) -> str:
    normalized = _normalize_public_key(public_key)
    key_blob = base64.b64decode(normalized.split()[1], validate=True)
    digest = base64.b64encode(hashlib.sha256(key_blob).digest()).decode("ascii")
    return "SHA256:" + digest.rstrip("=")


def read_public_key(path: Path) -> str:
    if not path.is_file():
        raise OwnerAccessError(f"Public key not found: {path}")
    raw = path.read_text(encoding="utf-8").strip()
    if "PRIVATE KEY" in raw or "OPENSSH PRIVATE" in raw:
        raise OwnerAccessError("A private key was selected instead of a public key.")
    return _normalize_public_key(raw)


def ensure_keypair(private_path: Path | None = None) -> KeyInfo:
    private_path = (private_path or default_private_key_path()).expanduser().resolve()
    public_path = Path(str(private_path) + ".pub")
    private_path.parent.mkdir(parents=True, exist_ok=True)

    if private_path.exists() != public_path.exists():
        raise OwnerAccessError(
            "Only half of the FibreSeek keypair exists. Move the incomplete file "
            "aside or restore its matching key before continuing."
        )

    if private_path.exists():
        try:
            private_key = serialization.load_ssh_private_key(
                private_path.read_bytes(), password=None
            )
        except (TypeError, ValueError) as exc:
            raise OwnerAccessError(
                "The existing FibreSeek private key could not be read."
            ) from exc
        if not isinstance(private_key, Ed25519PrivateKey):
            raise OwnerAccessError("The existing FibreSeek key is not Ed25519.")
        derived = private_key.public_key().public_bytes(
            serialization.Encoding.OpenSSH,
            serialization.PublicFormat.OpenSSH,
        ).decode("ascii")
        stored = read_public_key(public_path)
        if stored.split()[:2] != derived.split()[:2]:
            raise OwnerAccessError("The existing public and private keys do not match.")
        return KeyInfo(
            private_path, public_path, public_key_fingerprint(stored), False
        )

    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.OpenSSH,
        serialization.NoEncryption(),
    )
    public_base = private_key.public_key().public_bytes(
        serialization.Encoding.OpenSSH,
        serialization.PublicFormat.OpenSSH,
    ).decode("ascii")
    public_key = f"{public_base} {KEY_COMMENT}"

    private_path.write_bytes(private_bytes)
    public_path.write_text(public_key + "\n", encoding="ascii")
    try:
        private_path.chmod(0o600)
        public_path.chmod(0o644)
    except OSError:
        pass

    return KeyInfo(
        private_path, public_path, public_key_fingerprint(public_key), True
    )


def suggest_recovery_version(installed: str) -> str:
    cleaned = installed.strip().lower().lstrip("v")
    numbers = [int(part) for part in re.findall(r"[0-9]+", cleaned)]
    if len(numbers) < 4:
        return DEFAULT_VERSION
    numbers = numbers[:5]
    if len(numbers) == 4:
        numbers.append(0)
    numbers[3] += 1
    numbers[4] += 1
    return ".".join(str(part) for part in numbers)


def build_fibrepack(
    public_key_path: Path,
    output_dir: Path,
    version: str = DEFAULT_VERSION,
) -> PackageInfo:
    if not VERSION_RE.fullmatch(version):
        raise OwnerAccessError(
            "The package version must have five numeric fields, such as "
            "2.2.42.832.321."
        )
    public_key = read_public_key(public_key_path.expanduser())
    fingerprint = public_key_fingerprint(public_key)
    template_path = resource_path("payload/fibreseek-installer.in")
    if not template_path.is_file():
        raise OwnerAccessError("The installer template is missing from the application.")
    template = template_path.read_text(encoding="utf-8")
    installer = template.replace("__PUBLIC_KEY_SHELL__", shlex.quote(public_key))
    installer = installer.replace(
        "__KEY_FINGERPRINT_SHELL__", shlex.quote(fingerprint)
    )
    if "__PUBLIC_KEY_SHELL__" in installer or "__KEY_FINGERPRINT_SHELL__" in installer:
        raise OwnerAccessError("The installer template could not be completed.")

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / f"fibreseek-sk3-{version}.fibrepack"
    checksum_path = package_path.with_suffix(package_path.suffix + ".sha256")
    temp_path = package_path.with_suffix(package_path.suffix + ".tmp")

    info = zipfile.ZipInfo("fibreseek-installer")
    info.date_time = (2026, 1, 1, 0, 0, 0)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (0o100755 & 0xFFFF) << 16
    with zipfile.ZipFile(temp_path, "w") as archive:
        archive.writestr(info, installer.encode("utf-8"))
    temp_path.replace(package_path)

    digest = hashlib.sha256(package_path.read_bytes()).hexdigest()
    checksum_path.write_text(f"{digest}  {package_path.name}\n", encoding="ascii")
    return PackageInfo(package_path, checksum_path, digest, fingerprint, version)


def detect_usb_volumes() -> list[Path]:
    if sys.platform == "darwin":
        return _detect_macos_volumes()
    if os.name == "nt":
        return _detect_windows_volumes()
    return _detect_linux_volumes()


def _detect_macos_volumes() -> list[Path]:
    volumes = []
    root = Path("/Volumes")
    if not root.is_dir():
        return volumes
    for path in sorted(root.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_dir() or not os.access(path, os.W_OK):
            continue
        try:
            result = subprocess.run(
                ["diskutil", "info", "-plist", str(path)],
                capture_output=True,
                check=False,
            )
            info = plistlib.loads(result.stdout) if result.returncode == 0 else {}
            if info.get("RemovableMedia") or info.get("Ejectable"):
                volumes.append(path)
        except (OSError, plistlib.InvalidFileException):
            continue
    return volumes


def _detect_windows_volumes() -> list[Path]:
    import ctypes

    volumes = []
    get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
    for letter in string.ascii_uppercase:
        path = f"{letter}:\\"
        if Path(path).exists() and get_drive_type(path) == 2:
            volumes.append(Path(path))
    return volumes


def _detect_linux_volumes() -> list[Path]:
    roots = [Path("/media") / (os.environ.get("USER") or ""), Path("/run/media") / (os.environ.get("USER") or "")]
    volumes = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in root.iterdir():
            if path.is_dir() and os.access(path, os.W_OK):
                volumes.append(path)
    return sorted(set(volumes), key=lambda item: str(item).lower())


def create_usb_installer(
    private_key_path: Path,
    usb_root: Path,
    version: str,
) -> tuple[KeyInfo, PackageInfo]:
    usb_root = usb_root.expanduser().resolve()
    if not usb_root.is_dir():
        raise OwnerAccessError("The selected USB location is not available.")
    if not os.access(usb_root, os.W_OK):
        raise OwnerAccessError("The selected USB location is not writable.")
    key_info = ensure_keypair(private_key_path)
    package = build_fibrepack(key_info.public_path, usb_root / "FIBRESEEK", version)
    return key_info, package


def _host_from_address(address: str) -> str:
    value = address.strip()
    if not value:
        raise OwnerAccessError("Enter the printer IP address or hostname.")
    parsed = urllib.parse.urlsplit(value if "://" in value else "//" + value)
    host = parsed.hostname
    if not host or any(char.isspace() for char in host):
        raise OwnerAccessError("The printer address is not valid.")
    return host


def verify_access(
    address: str,
    private_key_path: Path,
    timeout: int = 10,
) -> VerificationResult:
    host = _host_from_address(address)
    private_key_path = private_key_path.expanduser().resolve()
    if not private_key_path.is_file():
        raise OwnerAccessError("The local FibreSeek private key was not found.")

    moonraker_ok = False
    details = []
    try:
        with urllib.request.urlopen(f"http://{host}/server/info", timeout=timeout) as response:
            moonraker_ok = 200 <= response.status < 300
            details.append(f"Printer web API: HTTP {response.status}")
    except OSError as exc:
        details.append(f"Printer web API: unavailable ({exc})")

    ssh_binary = shutil.which("ssh")
    if not ssh_binary:
        return VerificationResult(
            moonraker_ok,
            False,
            False,
            "\n".join(details + ["SSH client: not installed on this computer"]),
        )

    command = [
        ssh_binary,
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={timeout}",
        "-o", "IdentitiesOnly=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-i", str(private_key_path),
        f"anisoprint@{host}",
        "printf 'SSH_OK\\n'; id; sudo -n true && printf 'SUDO_OK\\n'; "
        "test -f ~/printer_data/logs/ssh_recovery.log && "
        "cat ~/printer_data/logs/ssh_recovery.log",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        details.append(f"SSH: unavailable ({exc})")
        return VerificationResult(moonraker_ok, False, False, "\n".join(details))

    output = (result.stdout + "\n" + result.stderr).strip()
    ssh_ok = result.returncode == 0 and "SSH_OK" in result.stdout
    sudo_ok = ssh_ok and "SUDO_OK" in result.stdout
    details.append("SSH key login: " + ("verified" if ssh_ok else "not verified"))
    details.append("Administrator access: " + ("verified" if sudo_ok else "not verified"))
    if output:
        details.append("\nDetails:\n" + output)
    return VerificationResult(moonraker_ok, ssh_ok, sudo_ok, "\n".join(details))


def open_in_file_manager(path: Path) -> None:
    path = path.expanduser().resolve()
    if sys.platform == "darwin":
        command = ["open", str(path)]
    elif os.name == "nt":
        command = ["explorer", str(path)]
    else:
        command = ["xdg-open", str(path)]
    subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
