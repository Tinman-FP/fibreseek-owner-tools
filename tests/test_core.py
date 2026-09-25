#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from fibreseek_access.core import (
    DEFAULT_VERSION,
    OwnerAccessError,
    build_fibrepack,
    create_usb_installer,
    ensure_keypair,
    suggest_recovery_version,
)


class KeyAndPackageTests(unittest.TestCase):
    def test_key_creation_and_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            key_path = Path(tmp) / "owner_key"
            created = ensure_keypair(key_path)
            reused = ensure_keypair(key_path)
            self.assertTrue(created.created)
            self.assertFalse(reused.created)
            self.assertEqual(created.fingerprint, reused.fingerprint)
            self.assertTrue(created.private_path.is_file())
            self.assertTrue(created.public_path.is_file())

    def test_build_personalized_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = ensure_keypair(root / "owner_key")
            package = build_fibrepack(key.public_path, root / "dist")
            self.assertEqual(package.version, DEFAULT_VERSION)
            self.assertTrue(package.package_path.is_file())
            with zipfile.ZipFile(package.package_path) as archive:
                self.assertEqual(archive.namelist(), ["fibreseek-installer"])
                payload = archive.read("fibreseek-installer").decode()
            self.assertIn(key.public_path.read_text().strip(), payload)
            self.assertNotIn("OPENSSH PRIVATE KEY", payload)

    def test_usb_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "usb").mkdir()
            _, package = create_usb_installer(
                root / "owner_key", root / "usb", DEFAULT_VERSION
            )
            self.assertEqual(
                package.package_path.parent,
                (root / "usb" / "FIBRESEEK").resolve(),
            )

    def test_version_suggestion(self) -> None:
        self.assertEqual(suggest_recovery_version("2.2.42.831.320"), "2.2.42.832.321")
        self.assertEqual(suggest_recovery_version("2.2.42.831"), "2.2.42.832.1")
        self.assertEqual(suggest_recovery_version("unknown"), DEFAULT_VERSION)

    def test_incomplete_keypair_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            key_path = Path(tmp) / "owner_key"
            key_path.write_text("incomplete")
            with self.assertRaises(OwnerAccessError):
                ensure_keypair(key_path)


if __name__ == "__main__":
    unittest.main()
