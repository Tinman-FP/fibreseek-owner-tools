# FibreSeek Owner Access desktop setup

The desktop wizard is the simplest way to create personal SSH access. It does
not require Terminal, Git, Python, or manual key handling.

The application creates the key on the computer first. It never puts the
private key in the recovery package or on the printer.

## What you need

- A FibreSeeker 3 you own or are authorized to administer
- A writable USB drive
- Physical access to the printer touchscreen
- The printer's installed version from **Settings → Updates**
- The printer IP address for final verification

## Choose the download for your computer

- Apple-silicon Mac: `FibreSeek-Owner-Access-macOS-Apple-Silicon.dmg`
- Intel Mac: `FibreSeek-Owner-Access-macOS-Intel.dmg`
- Windows PC: `FibreSeek-Owner-Access-Windows-x64.exe`
- 64-bit Linux: `FibreSeek-Owner-Access-Linux-x64.tar.gz`

Each release also includes a matching `SHA256SUMS` file for checking the
download before opening it.

## macOS installation

1. Download `FibreSeek-Owner-Access-macOS.dmg` from the latest GitHub release.
2. Open the downloaded DMG.
3. Drag **FibreSeek Owner Access** into **Applications**.
4. Open the application.
5. If macOS says the developer cannot be verified, Control-click the application,
   choose **Open**, then confirm **Open**. The current community build is not
   notarized by Apple.

## Windows installation

1. Download `FibreSeek-Owner-Access-Windows-x64.exe` from the latest release.
2. Compare it with `SHA256SUMS-Windows-x64.txt` if you want to verify the
   download.
3. Open the `.exe`; it is a portable application and does not need installation.
4. If Windows SmartScreen appears, verify that the file came from this
   repository before choosing **More info → Run anyway**. The current community
   build is not commercially code-signed.

Windows OpenSSH is used only for the final printer verification. If it is not
installed, the wizard can still make the key and USB package and will clearly
report that the verification client is unavailable.

## Linux installation

1. Download `FibreSeek-Owner-Access-Linux-x64.tar.gz` from the latest release.
2. Extract the archive.
3. Open a terminal in the extracted folder and run:

   ```sh
   chmod +x FibreSeek-Owner-Access-Linux-x64
   ./FibreSeek-Owner-Access-Linux-x64
   ```

The prebuilt Linux application targets 64-bit distributions with a modern
glibc and a graphical desktop. OpenSSH is used for final verification.

## Create the access key

1. On the **Welcome** page, read the description and click **Next**.
2. On **Access Key**, click **Create or Reuse Key**.
3. The application creates a unique key in your normal `.ssh` folder.
4. Leave this key in place. It is the credential your computer will use later.

The application safely reuses its existing FibreSeek key if you run it again.
It will not overwrite an incomplete or mismatched keypair.

## Create the USB installer

1. Insert a writable USB drive into the computer.
2. Click **Next** to open **USB Installer**.
3. Select the USB drive. Click **Refresh** if it was inserted after opening the
   page, or **Browse** to select it manually.
4. Enter the installed firmware version shown on the printer.
5. Click **Suggest Package Version**.
6. Click **Create USB Installer**.
7. Wait for the success message.

The application creates this structure automatically:

```text
USB drive
└── FIBRESEEK
    ├── fibreseek-sk3-<version>.fibrepack
    └── fibreseek-sk3-<version>.fibrepack.sha256
```

Only the public key is inside the `.fibrepack`.

## Install on the printer

1. Eject the USB drive from the computer.
2. Make sure the FibreSeeker is idle.
3. Insert the USB drive into the printer.
4. Open **Settings → Updates** on the touchscreen.
5. Select **Update Firmware via USB**.
6. Select the recovery package version.
7. Tap **Upgrade**, then confirm.
8. Wait at least 30 seconds.

The recovery helper is much smaller than full firmware and does not report the
same multi-stage progress. The screen may remain open after the key is already
installed. Do not run the package twice before attempting verification.

## Verify access

1. Return to the application and click **Next** until **Verify** is shown.
2. Enter the printer IP address, such as `192.168.50.113`.
3. Click **Verify Access**.
4. Wait for all three checks:
   - Printer web API
   - SSH key login
   - Administrator access

When SSH login and administrator access are verified, setup is complete.

## Keep the key

The private key is normally stored at:

- macOS and Linux: `~/.ssh/fibreseek_owner_ed25519`
- Windows: `%USERPROFILE%\.ssh\fibreseek_owner_ed25519`

Do not email, post, or place that private-key file on the USB drive. The `.pub`
file beside it is the public half and is safe to place in a personalized
recovery package.

## Removing access

Use [REMOVE.md](REMOVE.md) to remove the public key from a printer. Removing the
desktop application does not remove a key already authorized by the printer.

## Source and advanced installation

The command-line workflow remains available in [INSTALL.md](INSTALL.md). It
uses the same installer template and package format as the desktop wizard.
Maintainers can reproduce all native packages with [BUILD_DESKTOP.md](BUILD_DESKTOP.md).
