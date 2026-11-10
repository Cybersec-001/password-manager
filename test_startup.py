import sys
import types

# The startup logic under test never opens a window; stub tkinter where it is absent.
for _name in ("tkinter", "tkinter.messagebox", "tkinter.ttk"):
    sys.modules.setdefault(_name, types.ModuleType(_name))

import os
import tempfile
import unittest
from unittest import mock

from cryptography.fernet import Fernet

import password_manager as pm


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_key, self.old_db = pm.KEY_FILE, pm.DB_FILE
        pm.KEY_FILE = os.path.join(self.tmp.name, "secret.key")
        pm.DB_FILE = os.path.join(self.tmp.name, "passwords.db")

    def tearDown(self):
        pm.KEY_FILE, pm.DB_FILE = self.old_key, self.old_db
        self.tmp.cleanup()

    def test_main_creates_key_and_database_then_opens_the_window(self):
        fake_tk = mock.Mock()
        with mock.patch.object(pm, "tk", fake_tk), mock.patch.object(pm, "PasswordManager") as window:
            pm.main()
        self.assertTrue(os.path.exists(pm.KEY_FILE))
        self.assertTrue(os.path.exists(pm.DB_FILE))
        root = fake_tk.Tk.return_value
        with open(pm.KEY_FILE, "rb") as handle:
            window.assert_called_once_with(root, handle.read())
        root.mainloop.assert_called_once_with()

    def test_corrupt_key_file_stops_startup_without_touching_it(self):
        with open(pm.KEY_FILE, "wb") as handle:
            handle.write(b"not-a-fernet-key")
        with mock.patch.object(pm, "tk") as fake_tk:
            with self.assertRaises(SystemExit) as caught:
                pm.main()
        self.assertIn("Could not open local vault", str(caught.exception))
        self.assertIn("intact", str(caught.exception))
        fake_tk.Tk.assert_not_called()
        with open(pm.KEY_FILE, "rb") as handle:
            self.assertEqual(handle.read(), b"not-a-fernet-key")
        self.assertFalse(os.path.exists(pm.DB_FILE))

    def test_unusable_database_stops_startup(self):
        os.mkdir(pm.DB_FILE)  # a directory where the database file should be
        with mock.patch.object(pm, "tk") as fake_tk:
            with self.assertRaises(SystemExit) as caught:
                pm.main()
        self.assertIn("Could not open local vault", str(caught.exception))
        fake_tk.Tk.assert_not_called()

    def test_existing_key_is_reused_not_replaced(self):
        key = Fernet.generate_key()
        with open(pm.KEY_FILE, "wb") as handle:
            handle.write(key)
        with mock.patch.object(pm, "tk"), mock.patch.object(pm, "PasswordManager") as window:
            pm.main()
        self.assertEqual(window.call_args[0][1], key)
        with open(pm.KEY_FILE, "rb") as handle:
            self.assertEqual(handle.read(), key)

    def test_empty_key_file_is_rejected_rather_than_overwritten(self):
        open(pm.KEY_FILE, "wb").close()
        with mock.patch.object(pm, "tk"):
            with self.assertRaises(SystemExit):
                pm.main()
        self.assertEqual(os.path.getsize(pm.KEY_FILE), 0)


if __name__ == "__main__":
    unittest.main()
