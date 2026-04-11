import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

import app


class AppEntrypointTests(unittest.TestCase):
    def test_run_captures_url_from_browser_when_no_arguments_are_provided(self):
        browser = MagicMock()
        browser.capture_course_url.return_value = "https://echo360.org.au/section/123/home"
        browser.__enter__.return_value = browser
        browser.__exit__.return_value = None

        with patch("builtins.input", return_value=""), patch("app.BrowserSession", return_value=browser), patch(
            "app.main", return_value=0
        ) as main_fn:
            exit_code = app.run([])

        self.assertEqual(exit_code, 0)
        main_fn.assert_called_once_with(["https://echo360.org.au/section/123/home"])

    def test_run_returns_error_when_no_url_can_be_captured(self):
        stderr = MagicMock()
        browser = MagicMock()
        browser.capture_course_url.return_value = ""
        browser.__enter__.return_value = browser
        browser.__exit__.return_value = None

        with patch("builtins.input", return_value=""), patch("app.BrowserSession", return_value=browser), patch(
            "sys.stderr", stderr
        ):
            exit_code = app.run([])

        self.assertEqual(exit_code, 2)
        stderr.write.assert_called()

    def test_run_passes_arguments_through_without_prompting(self):
        with patch("builtins.input") as prompt, patch("app.main", return_value=0) as main_fn:
            exit_code = app.run(["inspect", "https://echo360.org.au/section/123/home"])

        self.assertEqual(exit_code, 0)
        prompt.assert_not_called()
        main_fn.assert_called_once_with(["inspect", "https://echo360.org.au/section/123/home"])

    def test_run_passes_help_through_without_prompting(self):
        with patch("builtins.input") as prompt, patch("app.main", return_value=0) as main_fn:
            exit_code = app.run(["--help"])

        self.assertEqual(exit_code, 0)
        prompt.assert_not_called()
        main_fn.assert_called_once_with(["--help"])
