import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from swinydl import main
from swinydl.bootstrap import (
    DIARIZER_TARGET,
    PARAKEET_TARGET,
    bootstrap_models,
    ensure_runtime_model_artifacts,
)


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_models_downloads_both_targets(self):
        calls = []

        def fake_snapshot_download(**kwargs):
            calls.append(kwargs)
            return kwargs["local_dir"]

        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "swinydl.bootstrap._snapshot_download", return_value=fake_snapshot_download
        ):
            report = bootstrap_models(vendor_root=Path(temp_dir))

        self.assertEqual(len(report["results"]), 2)
        self.assertEqual({item["target"] for item in report["results"]}, {"parakeet", "diarizer"})
        self.assertEqual(
            {call["repo_id"] for call in calls},
            {
                "FluidInference/parakeet-tdt-0.6b-v3-coreml",
                "FluidInference/speaker-diarization-coreml",
            },
        )

    def test_cli_bootstrap_models_routes_to_bootstrap_helper(self):
        with patch("swinydl.bootstrap.bootstrap_models", return_value={"results": []}) as bootstrap_fn:
            exit_code = main.main(["bootstrap-models"])

        self.assertEqual(exit_code, 0)
        bootstrap_fn.assert_called_once_with(target="all", force=False)

    def test_bootstrap_patterns_include_recursive_bundle_contents(self):
        all_patterns = set(PARAKEET_TARGET.allow_patterns) | set(DIARIZER_TARGET.allow_patterns)

        self.assertIn("Preprocessor.mlmodelc/**", all_patterns)
        self.assertIn("PldaRho.mlmodelc/**", all_patterns)
        self.assertIn("xvector-transform.json", all_patterns)

    def test_ensure_runtime_model_artifacts_bootstraps_process_when_defaults_are_missing(self):
        with patch("swinydl.bootstrap._missing_default_targets", return_value="all"), patch(
            "swinydl.bootstrap.bootstrap_models",
            return_value={"results": []},
        ) as bootstrap_fn, patch(
            "swinydl.bootstrap.normalize_local_model_layout",
            return_value={"actions": []},
        ):
            report = ensure_runtime_model_artifacts("process")

        self.assertTrue(report["bootstrapped"])
        bootstrap_fn.assert_called_once_with(target="all")

    def test_ensure_runtime_model_artifacts_bootstraps_process_manifest_when_defaults_are_missing(self):
        with patch("swinydl.bootstrap._missing_default_targets", return_value="parakeet"), patch(
            "swinydl.bootstrap.bootstrap_models",
            return_value={"results": []},
        ) as bootstrap_fn, patch(
            "swinydl.bootstrap.normalize_local_model_layout",
            return_value={"actions": []},
        ):
            report = ensure_runtime_model_artifacts("process-manifest")

        self.assertTrue(report["bootstrapped"])
        bootstrap_fn.assert_called_once_with(target="parakeet")

    def test_ensure_runtime_model_artifacts_skips_inspect(self):
        self.assertIsNone(ensure_runtime_model_artifacts("inspect"))

    def test_bootstrap_models_skips_download_when_target_already_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "swinydl.bootstrap._target_is_present",
            return_value=True,
        ), patch(
            "swinydl.bootstrap._snapshot_download"
        ) as snapshot_download:
            report = bootstrap_models(target="parakeet", vendor_root=Path(temp_dir))

        self.assertEqual(report["results"][0]["target"], "parakeet")
        self.assertTrue(report["results"][0]["skipped"])
        snapshot_download.assert_not_called()
