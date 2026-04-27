from __future__ import annotations

"""Download staged CoreML model bundles from their public Hugging Face repos."""

from dataclasses import dataclass
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import shutil

from .app_paths import cache_dir
from .echo_exceptions import DependencyMissingError
from .system import configure_runtime_ssl
from .transcription import (
    DEFAULT_DIARIZER_COREML_DIRNAME,
    DEFAULT_PARAKEET_COREML_DIRNAME,
    _diarizer_coreml_model_dir,
    _diarizer_coreml_models_exist,
    _parakeet_coreml_model_dir,
    _parakeet_coreml_models_exist,
)


@dataclass(frozen=True)
class BootstrapTarget:
    """A staged model bundle that can be mirrored into the local vendor tree."""

    name: str
    repo_id: str
    local_dirname: str
    allow_patterns: tuple[str, ...]


PARAKEET_TARGET = BootstrapTarget(
    name="parakeet",
    repo_id="FluidInference/parakeet-tdt-0.6b-v3-coreml",
    local_dirname=DEFAULT_PARAKEET_COREML_DIRNAME,
    allow_patterns=(
        "Preprocessor.mlmodelc/**",
        "Encoder.mlmodelc/**",
        "Decoder.mlmodelc/**",
        "JointDecision.mlmodelc/**",
        "parakeet_vocab.json",
    ),
)

DIARIZER_TARGET = BootstrapTarget(
    name="diarizer",
    repo_id="FluidInference/speaker-diarization-coreml",
    local_dirname=DEFAULT_DIARIZER_COREML_DIRNAME,
    allow_patterns=(
        "Segmentation.mlmodelc/**",
        "FBank.mlmodelc/**",
        "Embedding.mlmodelc/**",
        "PldaRho.mlmodelc/**",
        "plda-parameters.json",
        "xvector-transform.json",
    ),
)


def bootstrap_models(*, target: str = "all", force: bool = False, vendor_root: Path | None = None) -> dict[str, object]:
    """Download one or both staged CoreML bundles into the repo-local vendor directory."""
    configure_runtime_ssl()
    root = (vendor_root or Path.cwd() / "vendor").resolve()
    root.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, object]] = []
    for item in _select_targets(target):
        local_dir = root / item.local_dirname
        local_dir.mkdir(parents=True, exist_ok=True)
        if not force and _target_is_present(item, local_dir):
            results.append(
                {
                    "target": item.name,
                    "repo_id": item.repo_id,
                    "local_dir": str(local_dir),
                    "downloaded_to": str(local_dir),
                    "force": force,
                    "skipped": True,
                }
            )
            continue

        snapshot_download = _snapshot_download()
        downloaded_to = snapshot_download(
            repo_id=item.repo_id,
            local_dir=str(local_dir),
            allow_patterns=list(item.allow_patterns),
            force_download=force,
        )
        results.append(
            {
                "target": item.name,
                "repo_id": item.repo_id,
                "local_dir": str(local_dir),
                "downloaded_to": str(downloaded_to),
                "force": force,
                "skipped": False,
            }
        )

    return {
        "vendor_root": str(root),
        "results": results,
    }


def ensure_runtime_model_artifacts(command: str) -> dict[str, object] | None:
    """Auto-bootstrap the default staged model bundles for commands that require them."""
    if command not in {"process", "transcribe", "doctor"}:
        return None

    with _bootstrap_lock():
        normalization = normalize_local_model_layout()
        target = _missing_default_targets()
        if target is None:
            return {"bootstrapped": False, "normalized": normalization}

        bootstrap_report = bootstrap_models(target=target)
        normalization = normalize_local_model_layout()
        return {
            "bootstrapped": True,
            "target": target,
            "bootstrap": bootstrap_report,
            "normalized": normalization,
        }


def normalize_local_model_layout(vendor_root: Path | None = None) -> dict[str, object]:
    """Align the local vendor tree with the layout expected from bootstrap-models."""
    root = (vendor_root or Path.cwd() / "vendor").resolve()
    actions: list[str] = []

    diarizer_dir = root / DEFAULT_DIARIZER_COREML_DIRNAME
    nested_xvector = diarizer_dir / "speaker-diarization" / "xvector-transform.json"
    root_xvector = diarizer_dir / "xvector-transform.json"
    if nested_xvector.exists() and not root_xvector.exists():
        root_xvector.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(nested_xvector, root_xvector)
        actions.append(f"copied {nested_xvector} -> {root_xvector}")

    obsolete_paths = (
        root / "parakeet-tdt-0.6b-v3",
        diarizer_dir / "speaker-diarization",
        diarizer_dir / "pyannote_segmentation.mlmodelc",
        diarizer_dir / "wespeaker_v2.mlmodelc",
    )
    for path in obsolete_paths:
        if not path.exists():
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except FileNotFoundError:
            continue
        actions.append(f"removed {path}")

    return {
        "vendor_root": str(root),
        "actions": actions,
    }


def _select_targets(target: str) -> tuple[BootstrapTarget, ...]:
    """Map the CLI selector to the corresponding staged model bundles."""
    if target == "all":
        return (PARAKEET_TARGET, DIARIZER_TARGET)
    if target == "parakeet":
        return (PARAKEET_TARGET,)
    if target == "diarizer":
        return (DIARIZER_TARGET,)
    raise ValueError(f"Unknown bootstrap target: {target}")


def _missing_default_targets() -> str | None:
    """Return which default bundles are missing when using the repo-local model layout."""
    parakeet_missing = "ECHO360_PARAKEET_COREML_DIR" not in os.environ and not _parakeet_coreml_models_exist(
        _parakeet_coreml_model_dir()
    )
    diarizer_missing = "ECHO360_DIARIZER_COREML_DIR" not in os.environ and not _diarizer_coreml_models_exist(
        _diarizer_coreml_model_dir()
    )

    if parakeet_missing and diarizer_missing:
        return "all"
    if parakeet_missing:
        return "parakeet"
    if diarizer_missing:
        return "diarizer"
    return None


def _target_is_present(target: BootstrapTarget, local_dir: Path) -> bool:
    """Return whether the staged local directory already satisfies the target bundle."""
    if target.name == "parakeet":
        return _parakeet_coreml_models_exist(local_dir)
    if target.name == "diarizer":
        return _diarizer_coreml_models_exist(local_dir)
    return False


def _snapshot_download():
    """Import huggingface_hub lazily so non-bootstrap runtime paths stay lean."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:  # pragma: no cover - exercised through CLI error handling
        raise DependencyMissingError(
            "huggingface_hub is required for model bootstrap. Reinstall the package or run `uv sync`."
        ) from exc
    return snapshot_download


@contextmanager
def _bootstrap_lock():
    """Serialize model-layout normalization and auto-bootstrap across processes."""
    lock_dir = cache_dir() / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "bootstrap.lock"
    with lock_path.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
