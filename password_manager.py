from cryptography.fernet import Fernet
import os
import sqlite3
import sys
import tkinter as tk
from tkinter import messagebox

KEY_FILE = "secret.key"
DB_FILE = "passwords.db"

# Load the encryption key, generating it on first run so a fresh clone works.
def load_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)
        try:
            os.chmod(KEY_FILE, 0o600)  # owner-only on Linux/macOS
        except OSError:
            pass  # Windows has no chmod semantics
        return key
    with open(KEY_FILE, "rb") as key_file:
        return key_file.read()

def encrypt_password(password, key):
    cipher = Fernet(key)
    return cipher.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password, key):
    cipher = Fernet(key)
    return cipher.decrypt(encrypted_password.encode()).decode()

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS passwords (site TEXT, username TEXT, password TEXT)")
    conn.commit()
    conn.close()

# Save password to database
def save_password():
    site = site_entry.get()
    username = user_entry.get()
    password = pass_entry.get()

    if not site or not username or not password:
        messagebox.showwarning("Warning", "All fields are required!")
        return

    encrypted_password = encrypt_password(password, key)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO passwords VALUES (?, ?, ?)", (site, username, encrypted_password))
    conn.commit()
    conn.close()
    messagebox.showinfo("Success", "Password saved successfully!")

# Retrieve password
def retrieve_password():
    site = site_entry.get()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username, password FROM passwords WHERE site = ?", (site,))
    result = cursor.fetchone()
    conn.close()

    if result:
        username, encrypted_password = result
        try:
            decrypted_password = decrypt_password(encrypted_password, key)
        except Exception:
            messagebox.showerror("Error", "Could not decrypt this entry. Was secret.key replaced?")
            return
        messagebox.showinfo("Retrieved", f"Username: {username}\nPassword: {decrypted_password}")
    else:
        messagebox.showwarning("Not Found", "No password found for this site!")

# Load encryption key
key = load_key()
init_db()

# GUI Setup
root = tk.Tk()
root.title("Password Manager")

site_label = tk.Label(root, text="Site:")
site_label.grid(row=0, column=0)
site_entry = tk.Entry(root)
site_entry.grid(row=0, column=1)

user_label = tk.Label(root, text="Username:")
user_label.grid(row=1, column=0)
user_entry = tk.Entry(root)
user_entry.grid(row=1, column=1)

pass_label = tk.Label(root, text="Password:")
pass_label.grid(row=2, column=0)
pass_entry = tk.Entry(root, show="*")
pass_entry.grid(row=2, column=1)

save_button = tk.Button(root, text="Save Password", command=save_password)
save_button.grid(row=3, column=0, columnspan=2)

retrieve_button = tk.Button(root, text="Retrieve Password", command=retrieve_password)
retrieve_button.grid(row=4, column=0, columnspan=2)

root.mainloop()
