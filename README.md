# FibreSeek Owner Tools

Unofficial owner-access and recovery tools for the FibreSeek FibreSeeker 3.

This repository documents the USB update workflow used to add an owner's SSH
public key to the stock `anisoprint` Linux account. It builds a small
`.fibrepack`; it is **not replacement printer firmware** and it does not modify
Klipper, Moonraker, passwords, networking, or printer configuration.

The recovery method was validated on a FibreSeeker 3 running the
`2.2.42.831.320` software package. FibreSeek may change the update mechanism in
later releases.

## What gets installed

The generated package:

- adds one owner-supplied Ed25519 public key to
  `/home/anisoprint/.ssh/authorized_keys`;
- preserves existing authorized keys;
- sets the expected SSH directory ownership and permissions; and
- writes `/home/anisoprint/printer_data/logs/ssh_recovery.log`.

No private key is placed in the package or committed to this repository. Each
owner must build a package with their own public key.

## Quick start

Requirements: macOS or Linux, Python 3.9 or newer, OpenSSH, a FAT32/exFAT USB
drive, and physical access to a FibreSeeker 3 you own or are authorized to
administer.

```sh
git clone https://github.com/Tinman-FP/fibreseek-owner-tools.git
cd fibreseek-owner-tools

ssh-keygen -t ed25519 \
  -f "$HOME/.ssh/fibreseek_owner_ed25519" \
  -N '' \
  -C 'fibreseek-owner-access'

python3 scripts/build_fibrepack.py \
  --public-key "$HOME/.ssh/fibreseek_owner_ed25519.pub"
```

The builder writes the package and its SHA-256 checksum to `dist/`.

Continue with the complete [installation instructions](docs/INSTALL.md).

## Troubleshooting tools

The [FibreSeeker troubleshooting field guide](docs/TROUBLESHOOTING.md) records
the neutral, repeatable lessons from commissioning and fault isolation. It
focuses on identifying which software or hardware layer owns a symptom before
changing settings.

A read-only diagnostic collector can capture printer state and the most useful
logs through Moonraker without requiring SSH:

```sh
python3 scripts/collect_diagnostics.py 192.168.50.113
```

It sends HTTP `GET` requests only, redacts common identifiers by default, and
produces a checksummed ZIP suitable for inspection before sharing.

## Repository policy

- Generated `.fibrepack` files are ignored because they authorize a specific
  owner's key.
- Private keys must never be committed, attached to an issue, or copied to the
  printer.
- This project is independent and is not affiliated with or endorsed by
  FibreSeek or Anisoprint.
- Troubleshooting notes describe observed behavior and diagnostic methods, not
  a claim that every FibreSeeker has the same symptoms.

## Tested reference

The original successful owner package was named
`fibreseek-sk3-2.2.42.832.321.fibrepack`. On the printer it appeared as version
`2.2.42.832`. Installation was confirmed by the recovery log, SSH key login,
and passwordless `sudo` for the stock `anisoprint` account.

## License

MIT. See [LICENSE](LICENSE).
