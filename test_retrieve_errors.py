"""Retrieve failure paths: wrong key, database error, and refresh row replacement."""
import sys
import types

for _name in ("tkinter", "tkinter.messagebox", "tkinter.ttk"):
    sys.modules.setdefault(_name, types.ModuleType(_name))

import os
import sqlite3
import tempfile
import unittest
from unittest import mock

import password_manager as pm
from cryptography.fernet import Fernet


class RetrieveErrorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_key, self.old_db = pm.KEY_FILE, pm.DB_FILE
        pm.KEY_FILE = os.path.join(self.tmp.name, "secret.key")
        pm.DB_FILE = os.path.join(self.tmp.name, "passwords.db")
        self.key = pm.load_key()
        pm.init_db()

    def tearDown(self):
        pm.KEY_FILE, pm.DB_FILE = self.old_key, self.old_db
        self.tmp.cleanup()

    def build(self):
        fake_tk = mock.MagicMock()
        fake_ttk = mock.MagicMock()
        fake_ttk.Entry.side_effect = lambda *a, **k: mock.MagicMock()
        fake_ttk.Treeview.side_effect = lambda *a, **k: mock.MagicMock(
            **{"get_children.return_value": []})
        fake_mb = mock.MagicMock()
        for target, fake in (("tk", fake_tk), ("ttk", fake_ttk), ("messagebox", fake_mb)):
            patcher = mock.patch.object(pm, target, fake)
            patcher.start()
            self.addCleanup(patcher.stop)
        root = mock.MagicMock()
        gui = pm.PasswordManager(root, self.key)
        gui.search.get.return_value = ""
        return gui, root, fake_mb

    def test_retrieve_with_wrong_key_reports_decrypt_error(self):
        gui, _, mb = self.build()
        pm.store_entry("site", "bob", "top-secret", Fernet.generate_key())
        gui.fields["Site"].get.return_value = "site"
        gui.retrieve()
        mb.showerror.assert_called_once()
        assert mb.showerror.call_args[0][0] == "Could not decrypt"

    def test_retrieve_with_database_error_reports_it(self):
        gui, _, mb = self.build()
        gui.fields["Site"].get.return_value = "site"
        with mock.patch.object(pm, "read_entry", side_effect=sqlite3.Error("disk I/O error")):
            gui.retrieve()
        mb.showerror.assert_called_once_with("Database error", "disk I/O error")

    def test_refresh_replaces_existing_rows(self):
        gui, _, _ = self.build()
        gui.table.get_children.return_value = ["old-1", "old-2"]
        gui.refresh()
        self.assertEqual(gui.table.delete.call_count, 2)
        gui.table.delete.assert_any_call("old-1")
        gui.table.delete.assert_any_call("old-2")


if __name__ == "__main__":
    unittest.main()
