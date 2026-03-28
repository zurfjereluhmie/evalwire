"""ExperimentRunner — auto-discovers and executes evalwire experiments."""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """Discover, load, and run all experiments under ``experiments_dir``.

    Each subdirectory that contains a ``task.py`` file is treated as one
    experiment. The directory name must match the name of a Phoenix dataset.

    Parameters
    ----------
    experiments_dir:
        Root directory containing per-experiment subdirectories.
    phoenix_client:
        An initialised ``phoenix.client.Client`` instance.
    concurrency:
        Number of experiments to run in parallel. Default: 1 (sequential).
    dry_run:
        If ``True``, run one example per experiment without uploading results.
        If an ``int``, run that many examples.
    """

    def __init__(
        self,
        experiments_dir: Path | str,
        phoenix_client: Any,
        *,
        concurrency: int = 1,
        dry_run: bool | int = False,
    ) -> None:
        self.experiments_dir = Path(experiments_dir)
        self.client = phoenix_client
        self.concurrency = concurrency
        self.dry_run = dry_run

    def run(
        self,
        names: list[str] | None = None,
        *,
        experiment_name_prefix: str = "eval",
        metadata: dict | None = None,
    ) -> list[Any]:
        """Discover, load, and run experiments.

        Parameters
        ----------
        names:
            If provided, only run experiments whose directory names are in
            this list. If ``None``, run all discovered experiments.
        experiment_name_prefix:
            Prefix for the auto-generated experiment name in Phoenix.
            Format: ``"{prefix}_{dataset_name}_{iso_timestamp}"``.
        metadata:
            Extra key/value pairs attached to each experiment record.

        Returns
        -------
        list
            One experiment result object per experiment.
        """
        experiments = self._discover(names)
        if not experiments:
            logger.warning("No experiments found in %s.", self.experiments_dir)
            return []

        results: list[Any] = []
        failed = False

        for exp_name, task, evaluators in experiments:
            dataset = self._get_dataset(exp_name)
            if dataset is None:
                failed = True
                continue

            timestamp = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
            experiment_name = f"{experiment_name_prefix}_{exp_name}_{timestamp}"
            exp_metadata = {"dataset": exp_name, "run_by": "evalwire"}
            if metadata:
                exp_metadata.update(metadata)

            logger.info("Running experiment %r…", experiment_name)
            try:
                result = self.client.experiments.run_experiment(
                    dataset=dataset,
                    task=task,
                    evaluators=evaluators,
                    experiment_name=experiment_name,
                    experiment_metadata=exp_metadata,
                    dry_run=self.dry_run,
                )
                results.append(result)
            except Exception as exc:
                logger.error("Experiment %r failed: %s", experiment_name, exc)
                failed = True

        if failed:
            raise SystemExit(1)

        return results

    def _discover(self, names: list[str] | None) -> list[tuple[str, Any, list[Any]]]:
        """Return a list of ``(name, task, evaluators)`` tuples."""
        found: list[tuple[str, Any, list[Any]]] = []

        if not self.experiments_dir.is_dir():
            logger.error(
                "Experiments directory %s does not exist.", self.experiments_dir
            )
            return found

        # Ensure the parent of experiments_dir is on sys.path so that
        # relative imports inside experiment modules work.
        parent = str(self.experiments_dir.parent.resolve())
        if parent not in sys.path:
            sys.path.insert(0, parent)

        for subdir in sorted(self.experiments_dir.iterdir()):
            if not subdir.is_dir():
                continue
            exp_name = subdir.name
            if names is not None and exp_name not in names:
                continue

            task_file = subdir / "task.py"
            if not task_file.exists():
                logger.debug("Skipping %r — no task.py found.", exp_name)
                continue

            task = self._load_attribute(task_file, "task")
            if task is None:
                logger.warning(
                    "task.py in %r has no 'task' callable; skipping.", exp_name
                )
                continue

            evaluators: list[Any] = []
            for py_file in sorted(subdir.glob("*.py")):
                if py_file.stem in ("task", "__init__"):
                    continue
                evaluator = self._load_attribute(py_file, py_file.stem)
                if evaluator is not None:
                    evaluators.append(evaluator)
                else:
                    logger.warning(
                        "Evaluator file %s has no callable %r; skipping.",
                        py_file,
                        py_file.stem,
                    )

            found.append((exp_name, task, evaluators))
            logger.debug(
                "Discovered experiment %r with %d evaluator(s).",
                exp_name,
                len(evaluators),
            )

        return found

    def _load_attribute(self, path: Path, attribute: str) -> Any:
        """Import a Python file and return the named attribute, or None."""
        module_name = f"_evalwire_exp_{path.parent.name}_{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            return getattr(module, attribute, None)
        except Exception as exc:
            logger.error("Failed to load %s: %s", path, exc)
            return None

    def _get_dataset(self, name: str) -> Any | None:
        try:
            return self.client.datasets.get_dataset(name=name)
        except Exception as exc:
            logger.warning(
                "No Phoenix dataset named %r; skipping experiment (%s).", name, exc
            )
            return None
