import hashlib
import unittest

from app.auth import AdminSessionManager, extract_bearer_token, get_authorized_admin, hash_password, is_admin_authorized, verify_password


class AuthTests(unittest.TestCase):
    def test_password_hash_and_verify(self) -> None:
        hashed = hash_password('secret')
        self.assertTrue(hashed.startswith('pbkdf2_sha256$'))
        self.assertTrue(verify_password('secret', hashed))
        self.assertFalse(verify_password('not-secret', hashed))

    def test_legacy_hash_compatibility(self) -> None:
        legacy = hashlib.sha256('secret'.encode('utf-8')).hexdigest()
        self.assertTrue(verify_password('secret', legacy))
        self.assertFalse(verify_password('bad', legacy))

    def test_admin_api_key_auth(self) -> None:
        headers = {'X-Admin-Key': 'key-1'}
        self.assertTrue(is_admin_authorized(headers, 'key-1'))
        self.assertFalse(is_admin_authorized(headers, 'key-2'))

    def test_bearer_session_auth(self) -> None:
        manager = AdminSessionManager(ttl_minutes=10)
        session = manager.create_session('admin', 'admin')
        headers = {'Authorization': f'Bearer {session.token}'}
        self.assertTrue(is_admin_authorized(headers, 'wrong-key', session_manager=manager))

    def test_extract_bearer_token(self) -> None:
        self.assertEqual(extract_bearer_token({'Authorization': 'Bearer abc'}), 'abc')
        self.assertIsNone(extract_bearer_token({'Authorization': 'Token abc'}))
        self.assertIsNone(extract_bearer_token({}))

    def test_get_authorized_admin(self) -> None:
        manager = AdminSessionManager(ttl_minutes=10)
        session = manager.create_session('admin-user', 'admin')
        principal = get_authorized_admin({'Authorization': f'Bearer {session.token}'}, 'api-key', manager)
        self.assertEqual(principal['username'], 'admin-user')
        self.assertEqual(principal['role'], 'admin')


if __name__ == '__main__':
    unittest.main()
