import unittest

import pdf_auto_sender


class SmtpAuthTests(unittest.TestCase):
    def test_login_auth_mode_returns_credentials(self):
        auth_type, username, password = pdf_auto_sender.build_smtp_auth_payload(
            "user@example.com", "secret", "login", ""
        )
        self.assertEqual(auth_type, "login")
        self.assertEqual(username, "user@example.com")
        self.assertEqual(password, "secret")

    def test_xoauth2_auth_mode_requires_access_token(self):
        with self.assertRaises(ValueError):
            pdf_auto_sender.build_smtp_auth_payload(
                "user@example.com", "", "xoauth2", ""
            )

    def test_xoauth2_auth_mode_returns_payload(self):
        auth_type, username, payload = pdf_auto_sender.build_smtp_auth_payload(
            "user@example.com", "", "xoauth2", "token"
        )
        self.assertEqual(auth_type, "xoauth2")
        self.assertEqual(username, "user@example.com")
        self.assertEqual(payload, "token")


if __name__ == "__main__":
    unittest.main()
