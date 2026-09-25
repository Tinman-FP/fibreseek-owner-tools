"""Graphical FibreSeek Owner Access setup wizard."""

from __future__ import annotations

from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from fibreseek_access import __version__
from fibreseek_access.core import (
    DEFAULT_VERSION,
    OwnerAccessError,
    create_usb_installer,
    default_private_key_path,
    detect_usb_volumes,
    ensure_keypair,
    open_in_file_manager,
    suggest_recovery_version,
    verify_access,
)


BG = "#f3f5f6"
PANEL = "#ffffff"
INK = "#172126"
MUTED = "#56646b"
TEAL = "#007f78"
TEAL_DARK = "#00645f"
LINE = "#d7dfe2"
SUCCESS = "#197044"
ERROR = "#a12a2a"


class OwnerAccessWizard:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("FibreSeek Owner Access")
        self.root.geometry("760x610")
        self.root.minsize(700, 560)
        self.root.configure(bg=BG)

        self.step = 0
        self.pages: list[ttk.Frame] = []
        self.key_path = tk.StringVar(value=str(default_private_key_path()))
        self.key_status = tk.StringVar(value="No key has been created yet.")
        self.usb_path = tk.StringVar()
        self.installed_version = tk.StringVar()
        self.package_version = tk.StringVar(value=DEFAULT_VERSION)
        self.package_status = tk.StringVar(value="No USB installer has been created yet.")
        self.printer_address = tk.StringVar()
        self.verify_status = tk.StringVar(value="Enter the printer address after installing the package.")
        self.footer_status = tk.StringVar(value="Ready")
        self.last_package_name = "the generated .fibrepack"

        self._configure_styles()
        self._build_layout()
        self._build_pages()
        self._refresh_usb_volumes()
        self._update_key_status()
        self._show_step(0)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=INK, font=("Arial", 12))
        style.configure("Panel.TLabel", background=PANEL, foreground=INK, font=("Arial", 12))
        style.configure("Muted.Panel.TLabel", background=PANEL, foreground=MUTED, font=("Arial", 11))
        style.configure("Title.TLabel", background=INK, foreground="white", font=("Arial", 24, "bold"))
        style.configure("Subtitle.TLabel", background=INK, foreground="#c8d5d8", font=("Arial", 11))
        style.configure("Step.TLabel", background=BG, foreground=TEAL, font=("Arial", 11, "bold"))
        style.configure("Heading.Panel.TLabel", background=PANEL, foreground=INK, font=("Arial", 18, "bold"))
        style.configure("Primary.TButton", font=("Arial", 12, "bold"), padding=(16, 10), foreground="white", background=TEAL)
        style.map("Primary.TButton", background=[("active", TEAL_DARK), ("disabled", "#9cb5b3")])
        style.configure("TButton", font=("Arial", 11), padding=(12, 8))
        style.configure("TEntry", padding=7)
        style.configure("TCombobox", padding=7)

    def _build_layout(self) -> None:
        header = tk.Frame(self.root, bg=INK, height=110)
        header.pack(fill="x")
        header.pack_propagate(False)
        ttk.Label(header, text="FibreSeek Owner Access", style="Title.TLabel").pack(anchor="w", padx=28, pady=(20, 2))
        ttk.Label(
            header,
            text="Create a personal SSH recovery USB without using Terminal",
            style="Subtitle.TLabel",
        ).pack(anchor="w", padx=30)

        progress = ttk.Frame(self.root)
        progress.pack(fill="x", padx=28, pady=(15, 8))
        self.step_label = ttk.Label(progress, style="Step.TLabel")
        self.step_label.pack(side="left")
        self.progress_label = ttk.Label(progress, foreground=MUTED)
        self.progress_label.pack(side="right")

        self.content = ttk.Frame(self.root, style="Panel.TFrame")
        self.content.pack(fill="both", expand=True, padx=28, pady=(0, 12))

        nav = ttk.Frame(self.root)
        nav.pack(fill="x", padx=28, pady=(0, 8))
        self.back_button = ttk.Button(nav, text="Back", command=self._back)
        self.back_button.pack(side="left")
        self.next_button = ttk.Button(nav, text="Next", style="Primary.TButton", command=self._next)
        self.next_button.pack(side="right")

        status = tk.Label(self.root, textvariable=self.footer_status, bg="#e5eaec", fg=MUTED, anchor="w", padx=28, pady=6)
        status.pack(fill="x")

    def _new_page(self) -> ttk.Frame:
        page = ttk.Frame(self.content, style="Panel.TFrame", padding=24)
        self.pages.append(page)
        return page

    def _body(self, parent: ttk.Frame, text: str) -> ttk.Label:
        label = ttk.Label(parent, text=text, style="Panel.TLabel", wraplength=640, justify="left")
        label.pack(anchor="w", pady=(0, 12))
        return label

    def _build_pages(self) -> None:
        welcome = self._new_page()
        ttk.Label(welcome, text="Private access, created on this computer", style="Heading.Panel.TLabel").pack(anchor="w", pady=(0, 14))
        self._body(
            welcome,
            "This wizard creates a unique SSH key on your computer and places only the public key in a personalized FibreSeeker 3 recovery package.",
        )
        self._body(
            welcome,
            "Your private key never goes onto the USB drive or printer. The package does not replace firmware or change Klipper, Moonraker, passwords, networking, or printer configuration.",
        )
        self._body(welcome, "You will need a writable USB drive and physical access to a FibreSeeker 3 you own or are authorized to administer.")

        key_page = self._new_page()
        ttk.Label(key_page, text="Create your owner access key", style="Heading.Panel.TLabel").pack(anchor="w", pady=(0, 12))
        self._body(key_page, "The key is stored in your normal SSH folder. If a matching FibreSeek key already exists, the wizard safely reuses it.")
        ttk.Label(key_page, text="Key location", style="Muted.Panel.TLabel").pack(anchor="w")
        ttk.Entry(key_page, textvariable=self.key_path, state="readonly").pack(fill="x", pady=(4, 10))
        ttk.Label(key_page, textvariable=self.key_status, style="Panel.TLabel", wraplength=640).pack(anchor="w", pady=(0, 14))
        buttons = ttk.Frame(key_page, style="Panel.TFrame")
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Create or Reuse Key", style="Primary.TButton", command=self._create_key).pack(side="left")
        ttk.Button(buttons, text="Open Key Folder", command=self._open_key_folder).pack(side="left", padx=10)

        usb_page = self._new_page()
        ttk.Label(usb_page, text="Create the USB installer", style="Heading.Panel.TLabel").pack(anchor="w", pady=(0, 10))
        self._body(usb_page, "Insert a writable USB drive, select it below, and enter the firmware version shown under Settings > Updates.")
        ttk.Label(usb_page, text="USB drive", style="Muted.Panel.TLabel").pack(anchor="w")
        usb_row = ttk.Frame(usb_page, style="Panel.TFrame")
        usb_row.pack(fill="x", pady=(4, 10))
        self.usb_combo = ttk.Combobox(usb_row, textvariable=self.usb_path)
        self.usb_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(usb_row, text="Refresh", command=self._refresh_usb_volumes).pack(side="left", padx=(8, 0))
        ttk.Button(usb_row, text="Browse", command=self._browse_usb).pack(side="left", padx=(8, 0))

        ttk.Label(usb_page, text="Installed firmware version", style="Muted.Panel.TLabel").pack(anchor="w")
        version_row = ttk.Frame(usb_page, style="Panel.TFrame")
        version_row.pack(fill="x", pady=(4, 10))
        installed = ttk.Entry(version_row, textvariable=self.installed_version)
        installed.pack(side="left", fill="x", expand=True)
        ttk.Button(version_row, text="Suggest Package Version", command=self._suggest_version).pack(side="left", padx=(8, 0))

        ttk.Label(usb_page, text="Recovery package version", style="Muted.Panel.TLabel").pack(anchor="w")
        ttk.Entry(usb_page, textvariable=self.package_version).pack(fill="x", pady=(4, 12))
        ttk.Button(usb_page, text="Create USB Installer", style="Primary.TButton", command=self._create_usb).pack(anchor="w")
        ttk.Label(usb_page, textvariable=self.package_status, style="Panel.TLabel", wraplength=640, justify="left").pack(anchor="w", pady=(12, 0))

        install_page = self._new_page()
        ttk.Label(install_page, text="Install it on the FibreSeeker", style="Heading.Panel.TLabel").pack(anchor="w", pady=(0, 12))
        self.install_instructions = ttk.Label(install_page, style="Panel.TLabel", wraplength=640, justify="left")
        self.install_instructions.pack(anchor="w")

        verify_page = self._new_page()
        ttk.Label(verify_page, text="Verify owner access", style="Heading.Panel.TLabel").pack(anchor="w", pady=(0, 10))
        self._body(verify_page, "After the package has run, enter the printer's IP address or hostname. Verification checks the web API, SSH key login, and administrator access.")
        ttk.Label(verify_page, text="Printer address", style="Muted.Panel.TLabel").pack(anchor="w")
        ttk.Entry(verify_page, textvariable=self.printer_address).pack(fill="x", pady=(4, 12))
        ttk.Button(verify_page, text="Verify Access", style="Primary.TButton", command=self._verify).pack(anchor="w")
        self.verify_output = tk.Text(verify_page, height=10, wrap="word", bg="#f7f9fa", fg=INK, relief="solid", borderwidth=1, font=("Menlo", 10))
        self.verify_output.pack(fill="both", expand=True, pady=(12, 0))
        self._set_verify_text(self.verify_status.get())

    def _show_step(self, index: int) -> None:
        self.step = max(0, min(index, len(self.pages) - 1))
        for page in self.pages:
            page.pack_forget()
        self.pages[self.step].pack(fill="both", expand=True)
        names = ["Welcome", "Access Key", "USB Installer", "Touchscreen Install", "Verify"]
        self.step_label.configure(text=names[self.step])
        self.progress_label.configure(text=f"Step {self.step + 1} of {len(self.pages)}")
        self.back_button.configure(state="disabled" if self.step == 0 else "normal")
        self.next_button.configure(text="Done" if self.step == len(self.pages) - 1 else "Next")
        if self.step == 3:
            self._update_install_instructions()

    def _back(self) -> None:
        self._show_step(self.step - 1)

    def _next(self) -> None:
        if self.step == len(self.pages) - 1:
            self.root.destroy()
            return
        self._show_step(self.step + 1)

    def _set_footer(self, text: str) -> None:
        self.footer_status.set(text)
        self.root.update_idletasks()

    def _update_key_status(self) -> None:
        private_path = Path(self.key_path.get())
        public_path = Path(str(private_path) + ".pub")
        if private_path.exists() and public_path.exists():
            self.key_status.set("A FibreSeek owner key already exists and can be reused.")
        elif private_path.exists() or public_path.exists():
            self.key_status.set("An incomplete keypair exists. Move it aside or restore its matching file.")
        else:
            self.key_status.set("No FibreSeek owner key exists yet. Click Create or Reuse Key.")

    def _create_key(self) -> bool:
        try:
            info = ensure_keypair(Path(self.key_path.get()))
        except OwnerAccessError as exc:
            messagebox.showerror("Could not create key", str(exc), parent=self.root)
            self._set_footer("Key creation failed")
            return False
        action = "Created" if info.created else "Reused"
        self.key_status.set(f"{action} key {info.fingerprint}\nPrivate key: {info.private_path}")
        self._set_footer(f"{action} FibreSeek owner key")
        return True

    def _open_key_folder(self) -> None:
        path = Path(self.key_path.get()).expanduser().parent
        path.mkdir(parents=True, exist_ok=True)
        open_in_file_manager(path)

    def _refresh_usb_volumes(self) -> None:
        volumes = [str(path) for path in detect_usb_volumes()]
        self.usb_combo.configure(values=volumes)
        if volumes and not self.usb_path.get():
            self.usb_path.set(volumes[0])
        self._set_footer(f"Found {len(volumes)} removable USB drive(s)")

    def _browse_usb(self) -> None:
        path = filedialog.askdirectory(title="Select the root of the USB drive")
        if path:
            self.usb_path.set(path)

    def _suggest_version(self) -> None:
        version = suggest_recovery_version(self.installed_version.get())
        self.package_version.set(version)
        self._set_footer(f"Suggested package version {version}")

    def _create_usb(self) -> None:
        if not self._create_key():
            return
        if not self.usb_path.get().strip():
            messagebox.showerror("USB drive required", "Insert or select a writable USB drive.", parent=self.root)
            return
        try:
            key, package = create_usb_installer(
                Path(self.key_path.get()),
                Path(self.usb_path.get()),
                self.package_version.get().strip(),
            )
        except (OwnerAccessError, OSError) as exc:
            messagebox.showerror("Could not create USB installer", str(exc), parent=self.root)
            self._set_footer("USB installer creation failed")
            return
        self.last_package_name = package.package_path.name
        self.package_status.set(
            f"USB installer created successfully.\n"
            f"Package: {package.package_path}\n"
            f"Key: {key.fingerprint}\n"
            f"SHA-256: {package.sha256}"
        )
        self._set_footer("USB installer is ready")
        messagebox.showinfo(
            "USB installer ready",
            "The personalized package and checksum are in the FIBRESEEK folder on the selected USB drive.",
            parent=self.root,
        )

    def _update_install_instructions(self) -> None:
        self.install_instructions.configure(
            text=(
                f"1. Eject the USB drive from this computer.\n\n"
                f"2. Insert it into the FibreSeeker 3 while the printer is idle.\n\n"
                f"3. On the touchscreen, open Settings > Updates.\n\n"
                f"4. Choose Update Firmware via USB.\n\n"
                f"5. Select {self.last_package_name}, tap Upgrade, and confirm.\n\n"
                f"6. Wait at least 30 seconds. The small recovery helper may finish even if the progress screen remains open. Do not install it twice before checking access.\n\n"
                f"7. Return to this wizard and continue to Verify."
            )
        )

    def _set_verify_text(self, text: str) -> None:
        self.verify_output.configure(state="normal")
        self.verify_output.delete("1.0", "end")
        self.verify_output.insert("1.0", text)
        self.verify_output.configure(state="disabled")

    def _verify(self) -> None:
        address = self.printer_address.get().strip()
        if not address:
            messagebox.showerror("Printer address required", "Enter the printer IP address or hostname.", parent=self.root)
            return
        self._set_verify_text("Checking the printer...\n")
        self._set_footer("Verifying owner access")

        def worker() -> None:
            try:
                result = verify_access(address, Path(self.key_path.get()))
                self.root.after(0, lambda: self._verification_finished(result))
            except OwnerAccessError as exc:
                message = str(exc)
                self.root.after(0, lambda message=message: self._verification_error(message))

        threading.Thread(target=worker, daemon=True).start()

    def _verification_finished(self, result) -> None:
        self._set_verify_text(result.details)
        if result.ssh_ok and result.sudo_ok:
            self._set_footer("Owner access verified")
            messagebox.showinfo("Access verified", "SSH key login and administrator access are working.", parent=self.root)
        else:
            self._set_footer("Access was not verified")

    def _verification_error(self, message: str) -> None:
        self._set_verify_text(message)
        self._set_footer("Verification failed")


def main() -> None:
    root = tk.Tk()
    OwnerAccessWizard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
