"""GUI edge cases with a stubbed tkinter: empty selection and generate-time timer handling."""
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


class GuiEdgeTests(unittest.TestCase):
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
        return gui, root

    def test_select_without_a_selection_leaves_everything_untouched(self):
        gui, _ = self.build()
        gui.table.selection.return_value = []
        gui.select(None)
        for field in ("Site", "Username", "Password"):
            gui.fields[field].insert.assert_not_called()
        gui.status.set.assert_not_called()

    def test_generate_cancels_a_pending_auto_hide(self):
        gui, root = self.build()
        gui.hide_job = "job-9"
        gui.generate()
        root.after_cancel.assert_called_once_with("job-9")
        self.assertIsNone(gui.hide_job)
        inserted = gui.fields["Password"].insert.call_args[0][1]
        self.assertEqual(len(inserted), 20)
        self.assertEqual(gui.status.set.call_args[0][0],
                         "20-character password generated. Save entry to store it.")


if __name__ == "__main__":
    unittest.main()
