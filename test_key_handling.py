import sys
import types

# The vault logic under test never touches the GUI; stub tkinter where it is absent.
for _name in ("tkinter", "tkinter.messagebox", "tkinter.ttk"):
    sys.modules.setdefault(_name, types.ModuleType(_name))

import os
import stat
import tempfile
import unittest
from unittest import mock

from cryptography.fernet import Fernet

import password_manager as pm


class KeyHandlingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_key, self.old_db = pm.KEY_FILE, pm.DB_FILE
        pm.KEY_FILE = os.path.join(self.tmp.name, "secret.key")
        pm.DB_FILE = os.path.join(self.tmp.name, "passwords.db")

    def tearDown(self):
        pm.KEY_FILE, pm.DB_FILE = self.old_key, self.old_db
        self.tmp.cleanup()

    def test_new_key_file_is_owner_only(self):
        pm.load_key()
        self.assertEqual(stat.S_IMODE(os.stat(pm.KEY_FILE).st_mode), 0o600)

    def test_concurrent_key_creation_keeps_the_first_key(self):
        # Another process won the O_EXCL race: its key must be used, not replaced.
        winner = Fernet.generate_key()
        with open(pm.KEY_FILE, "wb") as handle:
            handle.write(winner)
        real_open = os.open

        def raced(path, flags, mode=0o777):
            if path == pm.KEY_FILE and flags & os.O_EXCL:
                raise FileExistsError(path)
            return real_open(path, flags, mode)

        with mock.patch("password_manager.os.path.exists", return_value=False), \
                mock.patch("password_manager.os.open", side_effect=raced):
            self.assertEqual(pm.load_key(), winner)

    def test_unicode_password_roundtrip(self):
        key = pm.load_key()
        pm.init_db()
        secret = "p@ssw0rd-√-密-🔒"
        pm.store_entry("site", "user", secret, key)
        self.assertEqual(pm.read_entry("site", key), ("user", secret))


if __name__ == "__main__":
    unittest.main()
