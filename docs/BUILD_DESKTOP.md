# Build the desktop application

The desktop wizard uses the same source on macOS, Windows, and Linux. Native
executables must be built on the operating system where they will run.

Ordinary users should download a ready-made file from the GitHub Releases page.
These instructions are for maintainers and people who want to verify the build.

## macOS

Requirements: Python 3.9 or newer with Tcl/Tk 8.6 or newer, plus the standard
Xcode command-line tools. Apple's legacy system Python is not suitable. With
Homebrew:

```sh
brew install python@3.11 python-tk@3.11
PYTHON_BIN=/opt/homebrew/bin/python3.11 ./scripts/build_desktop_app.sh
```

The build creates an architecture-specific DMG and ZIP in
`dist-desktop/release/`. The community build is ad-hoc signed; it is not Apple
notarized.

## Windows

Requirements: 64-bit Python 3.9 or newer with `py` available in PowerShell.

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build_desktop_app.ps1
```

The build creates a standalone `.exe` in `dist-desktop\release`. It does not
require Python on the computer where it is later run.

## Linux

Requirements: Python 3.9 or newer, Tk, and the usual native build tools. On
Ubuntu or Debian:

```sh
sudo apt-get install python3-venv python3-tk
./scripts/build_desktop_app.sh
```

The build creates a standalone `.tar.gz` in `dist-desktop/release/`.

## Automated release builds

Pushing a version tag such as `v1.2.1` runs the repository release workflow on
native macOS Apple Silicon, macOS Intel, Windows x64, and Linux x64 runners.
After all builds and tests pass, the workflow publishes their artifacts on the
matching GitHub release.
