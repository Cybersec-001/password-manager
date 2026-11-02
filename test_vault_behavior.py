import os
import sqlite3
import tempfile
import unittest

import password_manager as pm


class EntryBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_key, self.old_db = pm.KEY_FILE, pm.DB_FILE
        pm.KEY_FILE = os.path.join(self.tmp.name, 'secret.key')
        pm.DB_FILE = os.path.join(self.tmp.name, 'passwords.db')
        self.key = pm.load_key()
        pm.init_db()

    def tearDown(self):
        pm.KEY_FILE, pm.DB_FILE = self.old_key, self.old_db
        self.tmp.cleanup()

    def test_store_strips_surrounding_whitespace(self):
        pm.store_entry('  example.com  ', '  alice  ', 'pw', self.key)
        self.assertEqual(pm.read_entry('example.com', self.key), ('alice', 'pw'))

    def test_read_strips_lookup_whitespace(self):
        pm.store_entry('example.com', 'alice', 'pw', self.key)
        self.assertEqual(pm.read_entry('   example.com\n', self.key), ('alice', 'pw'))

    def test_empty_username_and_password_rejected(self):
        with self.assertRaises(ValueError):
            pm.store_entry('site', '   ', 'pw', self.key)
        with self.assertRaises(ValueError):
            pm.store_entry('site', 'alice', '', self.key)

    def test_list_orders_sites_case_insensitively(self):
        pm.store_entry('banana.example', 'u1', 'pw', self.key)
        pm.store_entry('Apple.example', 'u2', 'pw', self.key)
        pm.store_entry('cherry.example', 'u3', 'pw', self.key)
        self.assertEqual([site for site, _ in pm.list_entries()],
                         ['Apple.example', 'banana.example', 'cherry.example'])

    def test_query_matches_username_as_well_as_site(self):
        pm.store_entry('site-a.example', 'bob', 'pw', self.key)
        pm.store_entry('site-b.example', 'carol', 'pw', self.key)
        self.assertEqual(pm.list_entries('CAROL'), [('site-b.example', 'carol')])


if __name__ == '__main__':
    unittest.main()