"""Local password manager. Keep secret.key and passwords.db private."""
from cryptography.fernet import Fernet, InvalidToken
import os
import secrets
import sqlite3
import string
import tkinter as tk
from tkinter import messagebox, ttk

KEY_FILE = "secret.key"
DB_FILE = "passwords.db"


def load_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        # Exclusive creation prevents overwriting a key created by another process.
        try:
            fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(key)
            return key
        except FileExistsError:
            pass
    with open(KEY_FILE, "rb") as handle:
        return handle.read()


def encrypt_password(password, key):
    return Fernet(key).encrypt(password.encode()).decode()


def decrypt_password(encrypted_password, key):
    return Fernet(key).decrypt(encrypted_password.encode()).decode()


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS passwords (site TEXT, username TEXT, password TEXT)")


def store_entry(site, username, password, key):
    site, username = site.strip(), username.strip()
    if not site or not username or not password:
        raise ValueError("Site, username and password are required.")
    encrypted = encrypt_password(password, key)
    with sqlite3.connect(DB_FILE) as conn:
        if conn.execute("SELECT 1 FROM passwords WHERE site = ?", (site,)).fetchone():
            conn.execute("UPDATE passwords SET username = ?, password = ? WHERE site = ?",
                         (username, encrypted, site))
        else:
            conn.execute("INSERT INTO passwords VALUES (?, ?, ?)", (site, username, encrypted))


def read_entry(site, key):
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute("SELECT username, password FROM passwords WHERE site = ?",
                           (site.strip(),)).fetchone()
    return (row[0], decrypt_password(row[1], key)) if row else None


def list_entries(query=""):
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute("SELECT DISTINCT site, username FROM passwords ORDER BY site COLLATE NOCASE").fetchall()
    return [row for row in rows if query.lower() in (row[0] + " " + row[1]).lower()]


def generate_password(length=20):
    alphabet = string.ascii_letters + string.digits + "!@#%+-"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class PasswordManager:
    def __init__(self, root, key):
        self.root, self.key, self.hide_job = root, key, None
        root.title("Password Manager | Local workspace")
        root.geometry("850x700")
        root.minsize(720, 700)
        root.configure(bg="#eef2df")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#eef2df")
        style.configure("Card.TFrame", background="#f9fcf5")
        style.configure("TLabel", background="#eef2df", foreground="#163d2c", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI", 26, "bold"))
        style.configure("Sub.TLabel", foreground="#577365")
        style.configure("TButton", padding=10, background="#e0eee1", foreground="#163d2c", font=("Segoe UI", 10))
        style.configure("Primary.TButton", background="#267b54", foreground="white")
        style.map("Primary.TButton", background=[("active", "#1e6545")])
        style.configure("TEntry", padding=8)
        style.configure("Treeview", background="#f9fcf5", fieldbackground="#f9fcf5", foreground="#163d2c", rowheight=34, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#d9eadc", foreground="#163d2c", font=("Segoe UI", 10, "bold"))
        outer = ttk.Frame(root, padding=28)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="YOUR LOCAL WORKSPACE", style="Sub.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Your passwords. Your space.", style="Title.TLabel").pack(anchor="w", pady=(4, 8))
        ttk.Label(outer, text="Learning project. No master password. Keep the key and database private.", style="Sub.TLabel").pack(anchor="w", pady=(0, 20))
        fields = ttk.Frame(outer)
        fields.pack(fill="x")
        fields.columnconfigure(1, weight=1)
        self.fields = {}
        for i, name in enumerate(("Site", "Username", "Password")):
            ttk.Label(fields, text=name).grid(row=i, column=0, sticky="w", padx=(0, 14), pady=6)
            entry = ttk.Entry(fields, show="*" if name == "Password" else "")
            entry.grid(row=i, column=1, sticky="ew", pady=6)
            self.fields[name] = entry
        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=14)
        for text, cmd, primary in (("Save entry", self.save, True), ("Retrieve", self.retrieve, False),
                                   ("Generate", self.generate, False), ("Hide / clear", self.clear, False)):
            ttk.Button(buttons, text=text, command=cmd, style="Primary.TButton" if primary else "TButton").pack(side="left", padx=(0, 8))
        self.search = tk.StringVar()
        search = ttk.Entry(outer, textvariable=self.search)
        search.pack(fill="x", pady=(6, 10))
        ttk.Label(outer, text="Search accounts above. Select an account to load its details.", style="Sub.TLabel").pack(anchor="w", pady=(0, 8))
        self.table = ttk.Treeview(outer, columns=("site", "user"), show="headings", height=5)
        self.table.heading("site", text="Site")
        self.table.heading("user", text="Username")
        self.table.bind("<<TreeviewSelect>>", self.select)
        self.search.trace_add("write", lambda *_: self.refresh())
        self.status = tk.StringVar(value="Ready. Encrypted storage stays on this computer.")
        ttk.Label(outer, textvariable=self.status, style="Sub.TLabel", wraplength=740).pack(anchor="w", pady=(14, 0))
        self.table.pack(fill="both", expand=True)
        root.bind("<Escape>", lambda _: self.clear())
        self.refresh()

    def refresh(self):
        for item in self.table.get_children():
            self.table.delete(item)
        for row in list_entries(self.search.get().strip()):
            self.table.insert("", "end", values=row)

    def select(self, _):
        selected = self.table.selection()
        if selected:
            site, user = self.table.item(selected[0], "values")
            self.clear()
            for name, value in (("Site", site), ("Username", user)):
                self.fields[name].delete(0, tk.END)
                self.fields[name].insert(0, value)

    def clear(self):
        if self.hide_job:
            self.root.after_cancel(self.hide_job)
            self.hide_job = None
        self.fields["Password"].configure(show="*")
        self.fields["Password"].delete(0, tk.END)
        self.status.set("Password field cleared.")

    def save(self):
        try:
            store_entry(*(self.fields[n].get() for n in ("Site", "Username", "Password")), self.key)
            self.clear()
            self.refresh()
            self.status.set("Entry saved locally. Password field cleared.")
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Could not save", str(exc))

    def retrieve(self):
        try:
            result = read_entry(self.fields["Site"].get(), self.key)
            if not result:
                self.status.set("No entry found for this site.")
                return
            self.clear()
            user, password = result
            self.fields["Username"].delete(0, tk.END)
            self.fields["Username"].insert(0, user)
            self.fields["Password"].insert(0, password)
            self.fields["Password"].configure(show="")
            self.hide_job = self.root.after(15000, self.clear)
            self.status.set("Retrieved locally. Password clears in 15 seconds. Escape clears now.")
        except InvalidToken:
            messagebox.showerror("Could not decrypt", "The key does not match this entry. Do not replace secret.key.")
        except sqlite3.Error as exc:
            messagebox.showerror("Database error", str(exc))

    def generate(self):
        self.clear()
        self.fields["Password"].insert(0, generate_password())
        self.status.set("20-character password generated. Save entry to store it.")


def main():
    try:
        key = load_key()
        Fernet(key)  # Validate before opening the workspace.
        init_db()
    except (OSError, ValueError, sqlite3.Error) as exc:
        raise SystemExit(f"Could not open local vault: {exc}. Keep existing key/database files intact.") from exc
    root = tk.Tk()
    PasswordManager(root, key)
    root.mainloop()


if __name__ == "__main__":
    main()
