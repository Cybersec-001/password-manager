import os
import sqlite3
import tempfile
import unittest
from cryptography.fernet import Fernet, InvalidToken
import password_manager as pm


class VaultTests(unittest.TestCase):
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

    def test_key_persists(self):
        self.assertEqual(self.key, pm.load_key())

    def test_roundtrip_and_ciphertext(self):
        pm.store_entry(' example ', ' user ', 'very-secret', self.key)
        self.assertEqual(pm.read_entry(' example ', self.key), ('user', 'very-secret'))
        with sqlite3.connect(pm.DB_FILE) as conn:
            stored = conn.execute('SELECT password FROM passwords').fetchone()[0]
        self.assertNotIn('very-secret', stored)

    def test_upsert(self):
        pm.store_entry('site', 'old', 'one', self.key)
        pm.store_entry('site', 'new', 'two', self.key)
        self.assertEqual(pm.read_entry('site', self.key), ('new', 'two'))
        self.assertEqual(len(pm.list_entries()), 1)

    def test_existing_database_preserved(self):
        pm.store_entry('legacy', 'user', 'password', self.key)
        pm.init_db()
        self.assertEqual(pm.read_entry('legacy', self.key), ('user', 'password'))

    def test_search_and_missing(self):
        pm.store_entry('Example', 'Alice', 'test', self.key)
        self.assertEqual(pm.list_entries('ALICE'), [('Example', 'Alice')])
        self.assertIsNone(pm.read_entry('absent', self.key))

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            pm.store_entry(' ', 'user', 'password', self.key)

    def test_wrong_key(self):
        pm.store_entry('site', 'user', 'password', self.key)
        with self.assertRaises(InvalidToken):
            pm.read_entry('site', Fernet.generate_key())

    def test_sql_input_is_data(self):
        pm.store_entry("a'; DROP TABLE passwords; --", 'user', 'test', self.key)
        self.assertEqual(len(pm.list_entries()), 1)

    def test_generation(self):
        self.assertEqual(len(pm.generate_password()), 20)
        self.assertNotEqual(pm.generate_password(), pm.generate_password())


if __name__ == '__main__':
    unittest.main()
