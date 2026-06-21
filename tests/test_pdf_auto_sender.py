import tempfile
import unittest
from pathlib import Path

import pdf_auto_sender


class PdfAutoSenderTests(unittest.TestCase):
    def test_sanitize_sender_name_replaces_localhost_like_values(self):
        self.assertEqual(pdf_auto_sender.sanitize_sender_name("localhost"), "Microsoft Azure CLI")
        self.assertEqual(pdf_auto_sender.sanitize_sender_name("127.0.0.2"), "Microsoft Azure CLI")
        self.assertEqual(pdf_auto_sender.sanitize_sender_name("Microsoft Azure CLI"), "Microsoft Azure CLI")

    def test_pick_pdf_path_rotates_from_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_dir = Path(tmpdir)
            first = pdf_dir / "a.pdf"
            second = pdf_dir / "b.pdf"
            first.write_bytes(b"%PDF-1.4\n")
            second.write_bytes(b"%PDF-1.5\n")

            self.assertEqual(pdf_auto_sender.pick_pdf_path(pdf_dir, 0), first)
            self.assertEqual(pdf_auto_sender.pick_pdf_path(pdf_dir, 1), second)
            self.assertEqual(pdf_auto_sender.pick_pdf_path(pdf_dir, 2), first)


if __name__ == "__main__":
    unittest.main()
