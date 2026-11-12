"""GUI glue with a stubbed tkinter: save, retrieve, generate, clear and select."""
import sys
import types

# The glue under test never opens a window; stub tkinter where it is absent.
for _name in ("tkinter", "tkinter.messagebox", "tkinter.ttk"):
    sys.modules.setdefault(_name, types.ModuleType(_name))

import os
import tempfile
import unittest
from unittest import mock

import password_manager as pm


class GuiGlueTests(unittest.TestCase):
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

    def set_fields(self, gui, site="", username="", password=""):
        gui.fields["Site"].get.return_value = site
        gui.fields["Username"].get.return_value = username
        gui.fields["Password"].get.return_value = password

    def test_save_stores_the_entry_and_clears_the_password_field(self):
        gui, _, _ = self.build()
        self.set_fields(gui, "Example.com", "alice", "s3cret")
        gui.save()
        self.assertEqual(pm.read_entry("Example.com", self.key), ("alice", "s3cret"))
        gui.fields["Password"].delete.assert_called()
        gui.status.set.assert_any_call("Entry saved locally. Password field cleared.")

    def test_save_with_blank_fields_shows_an_error_and_stores_nothing(self):
        gui, _, fake_mb = self.build()
        self.set_fields(gui)
        gui.save()
        fake_mb.showerror.assert_called_once()
        self.assertEqual(pm.list_entries(), [])

    def test_retrieve_fills_the_fields_unmasks_and_schedules_the_hide(self):
        gui, root, _ = self.build()
        pm.store_entry("site", "bob", "top-secret", self.key)
        self.set_fields(gui, site="site")
        gui.retrieve()
        gui.fields["Username"].insert.assert_called_with(0, "bob")
        gui.fields["Password"].insert.assert_called_with(0, "top-secret")
        gui.fields["Password"].configure.assert_called_with(show="")
        root.after.assert_called_with(15000, gui.clear)
        self.assertIsNotNone(gui.hide_job)

    def test_retrieve_with_no_match_only_updates_the_status(self):
        gui, _, _ = self.build()
        self.set_fields(gui, site="absent")
        gui.retrieve()
        gui.status.set.assert_any_call("No entry found for this site.")
        gui.fields["Password"].insert.assert_not_called()

    def test_generate_inserts_a_twenty_character_password(self):
        gui, _, _ = self.build()
        gui.generate()
        args = gui.fields["Password"].insert.call_args[0]
        self.assertEqual(args[0], 0)
        self.assertEqual(len(args[1]), 20)

    def test_clear_cancels_a_pending_hide_and_remasks(self):
        gui, root, _ = self.build()
        gui.hide_job = "job-1"
        gui.clear()
        root.after_cancel.assert_called_once_with("job-1")
        self.assertIsNone(gui.hide_job)
        gui.fields["Password"].configure.assert_called_with(show="*")

    def test_select_loads_the_chosen_row_into_the_fields(self):
        gui, _, _ = self.build()
        gui.table.selection.return_value = ["item-1"]
        gui.table.item.return_value = ("site", "user")
        gui.select(None)
        gui.fields["Site"].insert.assert_called_with(0, "site")
        gui.fields["Username"].insert.assert_called_with(0, "user")


if __name__ == "__main__":
    unittest.main()
