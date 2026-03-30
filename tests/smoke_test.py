"""Smoke test — run against the built wheel and sdist before publishing.

Checks that the package installs cleanly, all public names are importable,
and the CLI entry point is reachable.  Intentionally has no external
dependencies beyond the package itself.
"""

import importlib
import subprocess


def test_public_api() -> None:
    import evalwire

    required = [
        "DatasetUploader",
        "ExperimentRunner",
        "make_membership_evaluator",
        "make_top_k_evaluator",
        "setup_observability",
    ]
    missing = [name for name in required if not hasattr(evalwire, name)]
    assert not missing, f"Missing public names: {missing}"


def test_submodules_importable() -> None:
    for module in [
        "evalwire.evaluators",
        "evalwire.uploader",
        "evalwire.runner",
        "evalwire.observability",
        "evalwire.config",
        "evalwire.cli",
    ]:
        importlib.import_module(module)


def test_cli_entry_point() -> None:
    import shutil

    evalwire_bin = shutil.which("evalwire")
    assert evalwire_bin is not None, "evalwire CLI entry point not found on PATH"
    result = subprocess.run(
        [evalwire_bin, "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI --help failed:\n{result.stderr}"
    assert "evalwire" in result.stdout.lower()


if __name__ == "__main__":
    test_public_api()
    test_submodules_importable()
    test_cli_entry_point()
    print("Smoke test passed.")
