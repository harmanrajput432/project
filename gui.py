"""CustomTkinter GUI: login/setup screen, dashboard, add/edit, settings."""

import logging
import customtkinter as ctk
from tkinter import messagebox

from config import APP_NAME, WINDOW_SIZE, DEFAULT_THEME, AUTO_LOCK_SECONDS
from database import Database
from encryption import EncryptionManager
from auth import AuthManager
from vault import Vault
from password_generator import PasswordGenerator
from utils import copy_to_clipboard_with_autoclear

logger = logging.getLogger(__name__)

ctk.set_appearance_mode(DEFAULT_THEME)
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    """Root application window. Swaps between Login and Dashboard frames."""

    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry(WINDOW_SIZE)
        self.minsize(900, 600)

        self.db = Database()
        self.encryptor = EncryptionManager()
        self.auth = AuthManager(self.db)
        self.vault = Vault(self.db, self.encryptor)

        self._inactivity_after_id = None
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._show_login()

    # ---------- screen switching ----------
    def _clear(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
        if self._inactivity_after_id:
            self.after_cancel(self._inactivity_after_id)
            self._inactivity_after_id = None

    def _show_login(self) -> None:
        self._clear()
        first_launch = self.auth.is_first_launch()
        LoginFrame(self, first_launch=first_launch).pack(fill="both", expand=True)

    def _show_dashboard(self) -> None:
        self._clear()
        DashboardFrame(self).pack(fill="both", expand=True)
        self._bind_inactivity_watch()

    # ---------- auto-lock ----------
    def _bind_inactivity_watch(self) -> None:
        for seq in ("<Motion>", "<KeyPress>", "<Button>"):
            self.bind_all(seq, self._reset_inactivity_timer)
        self._reset_inactivity_timer()

    def _reset_inactivity_timer(self, _event=None) -> None:
        if self._inactivity_after_id:
            self.after_cancel(self._inactivity_after_id)
        self._inactivity_after_id = self.after(AUTO_LOCK_SECONDS * 1000, self._auto_lock)

    def _auto_lock(self) -> None:
        self.unbind_all("<Motion>")
        self.unbind_all("<KeyPress>")
        self.unbind_all("<Button>")
        messagebox.showinfo(APP_NAME, "Session locked due to inactivity.")
        self._show_login()

    def _on_close(self) -> None:
        self.destroy()


class LoginFrame(ctk.CTkFrame):
    """First-launch master-password setup, or normal login."""

    def __init__(self, app: App, first_launch: bool) -> None:
        super().__init__(app)
        self.app = app
        self.first_launch = first_launch

        container = ctk.CTkFrame(self, width=380)
        container.place(relx=0.5, rely=0.5, anchor="center")

        title = "Create Master Password" if first_launch else "Enter Master Password"
        ctk.CTkLabel(container, text=APP_NAME, font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(20, 5))
        ctk.CTkLabel(container, text=title, font=ctk.CTkFont(size=14)).pack(pady=(0, 15))

        self.pw_entry = ctk.CTkEntry(container, placeholder_text="Master password", show="*", width=260)
        self.pw_entry.pack(pady=6, padx=20)

        if first_launch:
            self.confirm_entry = ctk.CTkEntry(container, placeholder_text="Confirm password", show="*", width=260)
            self.confirm_entry.pack(pady=6, padx=20)

        self.status_label = ctk.CTkLabel(container, text="", text_color="tomato")
        self.status_label.pack(pady=(4, 0))

        btn_text = "Create & Continue" if first_launch else "Unlock"
        ctk.CTkButton(container, text=btn_text, width=260, command=self._submit).pack(pady=15, padx=20)
        self.pw_entry.bind("<Return>", lambda e: self._submit())
        container.pack_configure(pady=40)

    def _submit(self) -> None:
        password = self.pw_entry.get()
        if self.first_launch:
            confirm = self.confirm_entry.get()
            if password != confirm:
                self.status_label.configure(text="Passwords do not match.")
                return
            try:
                self.app.auth.create_master_password(password)
                self.app._show_dashboard()
            except ValueError as exc:
                self.status_label.configure(text=str(exc))
        else:
            try:
                if self.app.auth.verify_master_password(password):
                    self.app._show_dashboard()
                else:
                    self.status_label.configure(text="Incorrect password.")
            except PermissionError as exc:
                self.status_label.configure(text=str(exc))
            except RuntimeError as exc:
                self.status_label.configure(text=str(exc))


class DashboardFrame(ctk.CTkFrame):
    """Main vault view: search, list, add/edit/delete/copy, status bar."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.app = app
        self.vault: Vault = app.vault
        self.selected_id: int | None = None
        self.revealed_ids: set[int] = set()

        top_bar = ctk.CTkFrame(self)
        top_bar.pack(fill="x", padx=10, pady=10)

        self.search_var = ctk.StringVar()
        search_entry = ctk.CTkEntry(top_bar, placeholder_text="Search by website/username...",
                                     textvariable=self.search_var, width=300)
        search_entry.pack(side="left", padx=(0, 10))
        self.search_var.trace_add("write", lambda *_: self.refresh())

        ctk.CTkButton(top_bar, text="+ Add", width=90, command=self._open_add).pack(side="left", padx=4)
        ctk.CTkButton(top_bar, text="Edit", width=90, command=self._open_edit).pack(side="left", padx=4)
        ctk.CTkButton(top_bar, text="Delete", width=90, fg_color="firebrick", command=self._delete_selected).pack(side="left", padx=4)
        ctk.CTkButton(top_bar, text="Copy", width=90, command=self._copy_selected).pack(side="left", padx=4)
        ctk.CTkButton(top_bar, text="Show/Hide", width=100, command=self._toggle_reveal_selected).pack(side="left", padx=4)
        ctk.CTkButton(top_bar, text="Generator", width=100, command=self._open_generator).pack(side="left", padx=4)
        ctk.CTkButton(top_bar, text="Theme", width=80, command=self._toggle_theme).pack(side="right", padx=4)

        self.list_frame = ctk.CTkScrollableFrame(self, label_text="Vault")
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 5))

        self.status_bar = ctk.CTkLabel(self, text="Ready", anchor="w")
        self.status_bar.pack(fill="x", padx=10, pady=(0, 8))

        self.rows: dict[int, ctk.CTkFrame] = {}
        self.refresh()

    def _set_status(self, text: str) -> None:
        self.status_bar.configure(text=text)

    def refresh(self) -> None:
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.rows.clear()

        term = self.search_var.get()
        entries = self.vault.search(term) if term else self.vault.list_all()

        if not entries:
            ctk.CTkLabel(self.list_frame, text="No entries yet.").pack(pady=20)
            self._set_status("0 entries")
            return

        header = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 4))
        for text, w in [("Website", 200), ("Username", 180), ("Password", 160), ("Created", 140)]:
            ctk.CTkLabel(header, text=text, width=w, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)

        for entry in entries:
            row = ctk.CTkFrame(self.list_frame)
            row.pack(fill="x", pady=2)
            row.bind("<Button-1>", lambda e, i=entry.id: self._select(i))

            display_pw = entry.password if entry.id in self.revealed_ids else "••••••••"
            if entry.id in self.revealed_ids:
                display_pw = self.vault.reveal_password(entry.id)

            for text, w in [(entry.website, 200), (entry.username, 180), (display_pw, 160), (entry.created_at, 140)]:
                lbl = ctk.CTkLabel(row, text=text, width=w, anchor="w")
                lbl.pack(side="left", padx=4)
                lbl.bind("<Button-1>", lambda e, i=entry.id: self._select(i))

            self.rows[entry.id] = row

        self._set_status(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}")
        if self.selected_id is not None:
            self._highlight_selected()

    def _select(self, entry_id: int) -> None:
        self.selected_id = entry_id
        self._highlight_selected()

    def _highlight_selected(self) -> None:
        for eid, row in self.rows.items():
            row.configure(fg_color=("gray75", "gray25") if eid == self.selected_id else "transparent")

    def _toggle_reveal_selected(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning(APP_NAME, "Select an entry first.")
            return
        if self.selected_id in self.revealed_ids:
            self.revealed_ids.discard(self.selected_id)
        else:
            self.revealed_ids.add(self.selected_id)
        self.refresh()

    def _copy_selected(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning(APP_NAME, "Select an entry first.")
            return
        plaintext = self.vault.reveal_password(self.selected_id)
        copy_to_clipboard_with_autoclear(plaintext)
        self._set_status("Password copied (clipboard clears in 30s).")

    def _delete_selected(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning(APP_NAME, "Select an entry first.")
            return
        if messagebox.askyesno(APP_NAME, "Delete this entry? This cannot be undone."):
            self.vault.delete_entry(self.selected_id)
            self.selected_id = None
            self.refresh()
            self._set_status("Entry deleted.")

    def _open_add(self) -> None:
        EntryDialog(self.app, self.vault, on_saved=self.refresh)

    def _open_edit(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning(APP_NAME, "Select an entry first.")
            return
        entries = {e.id: e for e in self.vault.list_all()}
        entry = entries.get(self.selected_id)
        if entry:
            entry.password = self.vault.reveal_password(entry.id)
            EntryDialog(self.app, self.vault, on_saved=self.refresh, entry=entry)

    def _open_generator(self) -> None:
        GeneratorDialog(self.app)

    def _toggle_theme(self) -> None:
        current = ctk.get_appearance_mode()
        ctk.set_appearance_mode("light" if current == "Dark" else "dark")


class EntryDialog(ctk.CTkToplevel):
    """Add/Edit password entry dialog.

    All fields (and the Save button) live inside a CTkScrollableFrame so
    they're never pushed off-screen and clipped by a fixed window height —
    that clipping was the root cause of "Save" being unreachable and
    entries silently failing to persist.
    """

    def __init__(self, app: App, vault: Vault, on_saved, entry=None) -> None:
        super().__init__(app)
        self.vault = vault
        self.on_saved = on_saved
        self.entry = entry
        self.title("Edit Entry" if entry else "Add Entry")
        self.geometry("440x560")
        self.minsize(400, 420)
        self.resizable(True, True)

        # grab_set() before the window is mapped can silently no-op on some
        # platforms/window managers, so defer it slightly.
        self.after(50, self._make_modal)

        scroll = ctk.CTkScrollableFrame(self, label_text="")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        self.website_entry = self._labeled_entry(scroll, "Website", entry.website if entry else "")
        self.username_entry = self._labeled_entry(scroll, "Username", entry.username if entry else "")

        pw_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        pw_frame.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(pw_frame, text="Password").pack(anchor="w")
        pw_row = ctk.CTkFrame(pw_frame, fg_color="transparent")
        pw_row.pack(fill="x")
        self.password_entry = ctk.CTkEntry(pw_row, show="*", width=180)
        self.password_entry.pack(side="left", fill="x", expand=True)
        if entry:
            self.password_entry.insert(0, entry.password)
        self.show_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(pw_row, text="Show", variable=self.show_var,
                         command=self._toggle_show, width=60).pack(side="left", padx=6)
        ctk.CTkButton(pw_row, text="Generate", width=80, command=self._generate).pack(side="left")

        self.strength_label = ctk.CTkLabel(scroll, text="")
        self.strength_label.pack(anchor="w", padx=10)
        self.password_entry.bind("<KeyRelease>", self._update_strength)
        self._update_strength()

        self.notes_entry = self._labeled_entry(scroll, "Notes", entry.notes if entry else "")

        self.error_label = ctk.CTkLabel(scroll, text="", text_color="tomato", wraplength=380)
        self.error_label.pack(pady=(8, 0), fill="x", padx=10)

        button_row = ctk.CTkFrame(scroll, fg_color="transparent")
        button_row.pack(pady=15)
        ctk.CTkButton(button_row, text="Save", width=120, command=self._save).pack(side="left", padx=6)
        ctk.CTkButton(button_row, text="Cancel", width=120, fg_color="gray40",
                      command=self.destroy).pack(side="left", padx=6)

        # Allow saving with Enter from any field.
        self.bind("<Return>", lambda e: self._save())

    def _make_modal(self) -> None:
        try:
            self.grab_set()
            self.focus_force()
        except Exception:  # window might already be closed
            pass

    def _labeled_entry(self, parent, label: str, initial: str) -> ctk.CTkEntry:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(frame, text=label).pack(anchor="w")
        entry = ctk.CTkEntry(frame)
        entry.pack(fill="x")
        if initial:
            entry.insert(0, initial)
        return entry

    def _toggle_show(self) -> None:
        self.password_entry.configure(show="" if self.show_var.get() else "*")

    def _generate(self) -> None:
        pwd = PasswordGenerator.generate(16)
        self.password_entry.delete(0, "end")
        self.password_entry.insert(0, pwd)
        self._update_strength()

    def _update_strength(self, _event=None) -> None:
        pwd = self.password_entry.get()
        self.strength_label.configure(text=f"Strength: {PasswordGenerator.strength(pwd)}" if pwd else "")

    def _save(self) -> None:
        website = self.website_entry.get()
        username = self.username_entry.get()
        password = self.password_entry.get()
        notes = self.notes_entry.get()
        try:
            if self.entry:
                self.vault.update_entry(self.entry.id, website, username, password, notes)
            else:
                self.vault.add_entry(website, username, password, notes)
            self.on_saved()
            self.destroy()
        except ValueError as exc:
            self.error_label.configure(text=str(exc))


class GeneratorDialog(ctk.CTkToplevel):
    """Standalone password generator with options and strength indicator."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.title("Password Generator")
        self.geometry("380x360")
        self.grab_set()

        self.length_var = ctk.IntVar(value=16)
        ctk.CTkLabel(self, text="Length").pack(pady=(15, 0))
        ctk.CTkSlider(self, from_=8, to=64, number_of_steps=56,
                       variable=self.length_var, command=lambda v: self.length_label.configure(text=str(int(v)))).pack(fill="x", padx=20)
        self.length_label = ctk.CTkLabel(self, text="16")
        self.length_label.pack()

        self.upper_var = ctk.BooleanVar(value=True)
        self.lower_var = ctk.BooleanVar(value=True)
        self.digits_var = ctk.BooleanVar(value=True)
        self.symbols_var = ctk.BooleanVar(value=True)
        for label, var in [("Uppercase (A-Z)", self.upper_var), ("Lowercase (a-z)", self.lower_var),
                            ("Numbers (0-9)", self.digits_var), ("Symbols (!@#...)", self.symbols_var)]:
            ctk.CTkCheckBox(self, text=label, variable=var).pack(anchor="w", padx=30, pady=3)

        self.result_entry = ctk.CTkEntry(self, width=300)
        self.result_entry.pack(pady=(10, 0), padx=20, fill="x")
        self.strength_label = ctk.CTkLabel(self, text="")
        self.strength_label.pack()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=10)
        ctk.CTkButton(btn_row, text="Generate", command=self._generate).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Copy", command=self._copy).pack(side="left", padx=5)

        self._generate()

    def _generate(self) -> None:
        try:
            pwd = PasswordGenerator.generate(
                self.length_var.get(), self.upper_var.get(), self.lower_var.get(),
                self.digits_var.get(), self.symbols_var.get(),
            )
        except ValueError as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return
        self.result_entry.delete(0, "end")
        self.result_entry.insert(0, pwd)
        self.strength_label.configure(text=f"Strength: {PasswordGenerator.strength(pwd)}")

    def _copy(self) -> None:
        copy_to_clipboard_with_autoclear(self.result_entry.get())
        messagebox.showinfo(APP_NAME, "Copied to clipboard (clears in 30s).")