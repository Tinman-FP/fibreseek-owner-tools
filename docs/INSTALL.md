# Install owner SSH access

These instructions reproduce the owner-recovery procedure validated on a
FibreSeeker 3. Read the entire procedure before starting.

## 1. Record the installed version

On the printer, open **Settings → Updates** and record the installed firmware
version. The package filename must contain a version newer than the installed
one or the touchscreen may not offer it.

The tested package version is `2.2.42.832.321`, which the touchscreen displays
as `2.2.42.832`. If the printer is already at that version or newer, pass a
higher five-part version to the builder with `--version`.

This version changes only the recovery package filename. The package does not
replace the printer's firmware.

## 2. Create a dedicated SSH key

Run this on the computer that will administer the printer:

```sh
ssh-keygen -t ed25519 \
  -f "$HOME/.ssh/fibreseek_owner_ed25519" \
  -N '' \
  -C 'fibreseek-owner-access'
```

This creates:

- `~/.ssh/fibreseek_owner_ed25519`: private key; keep it on the computer.
- `~/.ssh/fibreseek_owner_ed25519.pub`: public key; this is embedded in the
  recovery package.

Adding a passphrase is recommended for a portable or shared computer. Omit
`-N ''` and enter the passphrase when prompted.

## 3. Build and verify the package

From the repository root:

```sh
python3 scripts/build_fibrepack.py \
  --public-key "$HOME/.ssh/fibreseek_owner_ed25519.pub"

python3 scripts/verify_fibrepack.py \
  dist/fibreseek-sk3-2.2.42.832.321.fibrepack \
  --public-key "$HOME/.ssh/fibreseek_owner_ed25519.pub"
```

For a newer local package version:

```sh
python3 scripts/build_fibrepack.py \
  --public-key "$HOME/.ssh/fibreseek_owner_ed25519.pub" \
  --version 2.2.42.833.321
```

The verifier confirms that the archive contains exactly one executable named
`fibreseek-installer`, contains the expected public key, and contains no
private-key marker.

## 4. Prepare the USB drive

1. Format a USB drive as FAT32 or exFAT if necessary.
2. Create a folder named `FIBRESEEK` at the root of the drive.
3. Copy the generated `.fibrepack` into that folder.
4. Eject the drive cleanly.

The final layout must be:

```text
FIBRESEEK/
└── fibreseek-sk3-2.2.42.832.321.fibrepack
```

## 5. Install from the touchscreen

1. Make sure the printer is idle.
2. Insert the USB drive into the FibreSeeker 3.
3. Open **Settings → Updates**.
4. Select **Update Firmware via USB**.
5. Select the package version. The tested package appears as `2.2.42.832`.
6. Tap **Upgrade**, then confirm.
7. Wait at least 30 seconds for the installer to run.

This small helper does not emit the multi-stage progress data expected from a
full firmware installer, so the update screen may remain open after the key has
already been installed. Verify the result before repeating the update.

## 6. Find the printer IP address

Read the address from the printer's network settings or your router. The test
printer used `192.168.50.113`; substitute the actual address below.

## 7. Verify SSH access

```sh
ssh -i "$HOME/.ssh/fibreseek_owner_ed25519" \
  anisoprint@192.168.50.113
```

Accept the host-key prompt only if the address is the intended printer. At the
printer shell, run:

```sh
id
hostname
sudo -n true && echo SUDO_NOPASSWD
cat ~/printer_data/logs/ssh_recovery.log
```

A successful installation reports user `anisoprint`, prints
`SUDO_NOPASSWD`, and shows the public-key fingerprint in the recovery log.

## 8. Add an optional SSH alias

Add the following to `~/.ssh/config`, replacing the address:

```sshconfig
Host fs3 fibreseeker3
    HostName 192.168.50.113
    User anisoprint
    IdentityFile ~/.ssh/fibreseek_owner_ed25519
    IdentitiesOnly yes
```

Then connect with:

```sh
ssh fs3
```

## 9. Remove the USB drive

Once SSH is verified, eject the USB drive from the touchscreen if that option
is available, or shut down the printer normally before removing it. Store or
delete the generated package as you would any device-administration credential.

## Troubleshooting

### No package appears

- Confirm the folder name is exactly `FIBRESEEK`.
- Confirm the filename begins with `fibreseek-sk3-` and ends in `.fibrepack`.
- Use a package version newer than the installed printer version.
- Reformat the drive as FAT32 or exFAT and copy only the package folder.

### The update screen does not finish

Wait 30 seconds and try the SSH command. The tested helper installed correctly
even though the touchscreen remained on its progress screen. After SSH works,
the touchscreen application can be restarted without rebooting Klipper:

```sh
ssh -i "$HOME/.ssh/fibreseek_owner_ed25519" \
  anisoprint@192.168.50.113 \
  'systemctl --user restart anisotouch'
```

### SSH says permission denied

- Verify that `-i` points to the private key, not the `.pub` file.
- Verify the public key used by the builder matches that private key:

  ```sh
  ssh-keygen -y -f "$HOME/.ssh/fibreseek_owner_ed25519" | diff - \
    <(awk '{print $1, $2}' "$HOME/.ssh/fibreseek_owner_ed25519.pub")
  ```

- Re-run the package verifier with the expected public key.
- Check whether a later FibreSeek release changed the local update mechanism.

## Removal

See [REMOVE.md](REMOVE.md) to remove a key cleanly.
