#!/usr/bin/env python3
"""Collect a read-only, privacy-redacted FibreSeeker diagnostic bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request


CORE_ENDPOINTS = {
    "server-info.json": "/server/info",
    "printer-info.json": "/printer/info",
    "system-info.json": "/machine/system_info",
    "objects.json": "/printer/objects/list",
    "state.json": (
        "/printer/objects/query?print_stats&virtual_sdcard&toolhead&heater_bed"
        "&extruder&extruder1&heater_generic%20chamber&bed_mesh&probe"
        "&filament_switch_sensor%20door_hall_sensor"
    ),
    "history.json": "/server/history/list?limit=25&order=desc",
    "gcode-store.json": "/server/gcode_store?count=500",
    "update-status.json": "/machine/update/status?refresh=false",
    "logs-list.json": "/server/files/list?root=logs",
}

CURRENT_LOGS = {
    "blackbox.log",
    "fibreseek_install.log",
    "fibretouch-ai.log",
    "klippy.log",
    "moonraker.log",
}

SENSITIVE_KEYS = re.compile(
    r"(?:^|_)(?:ip|ip_address|mac|mac_address|machine_id|serial|serial_num|"
    r"hostname|host_name|uuid|email)(?:$|_)",
    re.IGNORECASE,
)
IPV4_RE = re.compile(
    r"(?<![0-9])(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})"
    r"(?:\.(?:25[0-5]|2[0-4][0-9]|1?[0-9]{1,2})){3}(?![0-9])"
)
MAC_RE = re.compile(r"(?i)(?<![0-9a-f])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![0-9a-f])")
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")


def normalize_base(value: str) -> str:
    if "://" not in value:
        value = "http://" + value
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("host must be an IP, hostname, or HTTP URL")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def redact_text(text: str) -> str:
    text = EMAIL_RE.sub("<redacted-email>", text)
    text = MAC_RE.sub("<redacted-mac>", text)
    return IPV4_RE.sub("<redacted-ip>", text)


def redact_json(value: object) -> object:
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            result[key] = "<redacted>" if SENSITIVE_KEYS.search(str(key)) else redact_json(child)
        return result
    if isinstance(value, list):
        return [redact_json(child) for child in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def fetch(base: str, path: str, timeout: float) -> bytes:
    request = urllib.request.Request(
        base + path,
        headers={"User-Agent": "fibreseek-owner-tools-diagnostics/1"},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def write_capture(path: Path, data: bytes, redact: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        value = json.loads(data.decode("utf-8"))
        if redact:
            value = redact_json(value)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        text = data.decode("utf-8", errors="replace")
        if redact:
            text = redact_text(text)
        path.write_text(text, encoding="utf-8")


def latest_touchscreen_log(entries: list[dict[str, object]]) -> str | None:
    candidates = [
        entry
        for entry in entries
        if str(entry.get("path", "")).startswith("print_logs/anisotouch_")
        and str(entry.get("path", "")).endswith(".log")
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda entry: float(entry.get("modified", 0) or 0), reverse=True)
    return str(candidates[0]["path"])


def make_manifest(root: Path, metadata: dict[str, object]) -> None:
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.json":
            continue
        data = path.read_bytes()
        files.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    metadata["files"] = files
    (root / "MANIFEST.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", type=normalize_base, help="printer IP, hostname, or URL")
    parser.add_argument("--output", type=Path, help="output directory")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--include-identifiers",
        action="store_true",
        help="retain identifiers for a private manufacturer-support bundle",
    )
    args = parser.parse_args()

    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    output = (args.output or Path(f"fibreseek-diagnostics-{stamp}")).expanduser().resolve()
    if output.exists():
        raise SystemExit(f"error: output already exists: {output}")
    output.mkdir(parents=True)

    errors: list[dict[str, str]] = []
    captured: dict[str, bytes] = {}
    for name, endpoint in CORE_ENDPOINTS.items():
        try:
            data = fetch(args.host, endpoint, args.timeout)
            write_capture(output / name, data, not args.include_identifiers)
            captured[name] = data
            print(f"saved {name}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append({"item": name, "error": f"{type(exc).__name__}: {exc}"})
            print(f"warning: could not collect {name}: {exc}", file=sys.stderr)

    log_entries: list[dict[str, object]] = []
    if "logs-list.json" in captured:
        try:
            raw_inventory = json.loads(captured["logs-list.json"].decode("utf-8"))
            log_entries = list(raw_inventory.get("result", []))
        except (ValueError, TypeError):
            pass

    wanted = set(CURRENT_LOGS)
    touchscreen = latest_touchscreen_log(log_entries)
    if touchscreen:
        wanted.add(touchscreen)
    available = {str(entry.get("path", "")) for entry in log_entries}
    for log_path in sorted(wanted & available):
        endpoint = "/server/files/logs/" + urllib.parse.quote(log_path, safe="/")
        try:
            data = fetch(args.host, endpoint, args.timeout)
            write_capture(output / "logs" / log_path, data, not args.include_identifiers)
            print(f"saved logs/{log_path}")
        except OSError as exc:
            errors.append({"item": log_path, "error": f"{type(exc).__name__}: {exc}"})
            print(f"warning: could not collect {log_path}: {exc}", file=sys.stderr)

    metadata: dict[str, object] = {
        "collector": "fibreseek-owner-tools",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "identifiers_included": args.include_identifiers,
        "method": "HTTP GET only",
        "errors": errors,
    }
    make_manifest(output, metadata)
    archive = shutil.make_archive(str(output), "zip", root_dir=output.parent, base_dir=output.name)
    digest = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
    Path(archive + ".sha256").write_text(
        f"{digest}  {Path(archive).name}\n", encoding="ascii"
    )

    print(f"Bundle directory: {output}")
    print(f"ZIP archive: {archive}")
    print(f"ZIP SHA-256: {digest}")
    if not args.include_identifiers:
        print("Identifiers: redacted (best effort; inspect before sharing)")
    return 0 if captured else 1


if __name__ == "__main__":
    sys.exit(main())
