import os
import tempfile
import unittest
from pathlib import Path

from swinydl.app_paths import cache_dir, default_output_root, temp_dir
from swinydl.auth import CookieSession
from swinydl.models import BrowserCookie


class AppPathTests(unittest.TestCase):
    def test_package_local_output_and_temp_dirs_use_current_install_root(self):
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root).resolve()
            try:
                os.chdir(temp_root)
                self.assertEqual(default_output_root(), root / "swinydl-output")
                self.assertEqual(temp_dir(), root / "temp")
                self.assertEqual(cache_dir(), root / "temp")
            finally:
                os.chdir(original_cwd)

    def test_cookie_export_uses_package_local_temp_folder(self):
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root).resolve()
            try:
                os.chdir(temp_root)
                session = CookieSession(
                    [BrowserCookie(name="sessionid", value="abc123", domain=".echo360.org.au", secure=True)]
                )
                cookie_path = Path(session.cookie_file())
                self.assertTrue(cookie_path.is_file())
                self.assertEqual(cookie_path.parent, root / "temp" / "cookies")
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
