#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import package_desktop


class ChecksumManifestTests(unittest.TestCase):
    def test_manifest_forces_lf_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            release_root = Path(tmp)
            artifact = release_root / "artifact.exe"
            artifact.write_bytes(b"release artifact")

            with patch.object(package_desktop, "RELEASE_ROOT", release_root):
                manifest = package_desktop.write_checksums([artifact], "Windows-x64")

            contents = manifest.read_bytes()
            self.assertNotIn(b"\r", contents)
            self.assertTrue(contents.endswith(b"\n"))
            self.assertIn(b"  artifact.exe\n", contents)


if __name__ == "__main__":
    unittest.main()
