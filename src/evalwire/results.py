"""Result collection, export, comparison, and reporting for evalwire experiments."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from phoenix.client import Client

_SUPPORTED_FORMATS = {"csv", "json"}


def _rows_from_ran_experiment(ran_experiment: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a RanExperiment into a flat list of row dicts (one per task run)."""
    task_runs: list[Any] = ran_experiment["task_runs"]
    evaluation_runs: list[Any] = ran_experiment["evaluation_runs"]

    eval_by_run_id: dict[str, dict[str, float | None]] = {}
    for ev in evaluation_runs:
        run_id = ev.experiment_run_id
        score: float | None = None
        if ev.result is not None:
            score = ev.result.get("score")
        eval_by_run_id.setdefault(run_id, {})[ev.name] = score

    rows = []
    for run in task_runs:
        row: dict[str, Any] = {
            "run_id": run.id,
            "output": run.output,
            "error": run.error,
        }
        scores = eval_by_run_id.get(run.id, {})
        row.update(scores)
        rows.append(row)
    return rows


def _mean_scores(ran_experiment: dict[str, Any]) -> dict[str, float]:
    """Return mean score per evaluator for a RanExperiment."""
    evaluation_runs: list[Any] = ran_experiment["evaluation_runs"]
    totals: dict[str, list[float]] = {}
    for ev in evaluation_runs:
        if ev.result is not None:
            score = ev.result.get("score")
            if score is not None:
                totals.setdefault(ev.name, []).append(float(score))
    return {name: sum(vals) / len(vals) for name, vals in totals.items()}


class ResultCollector:
    """Fetch, export, compare, and report on evalwire experiment results.

    Parameters
    ----------
    client:
        An initialised ``phoenix.client.Client`` instance.
    """

    def __init__(self, client: Client) -> None:
        self._client = client

    def get(self, experiment_id: str) -> Any:
        """Fetch a completed experiment by its ID.

        Parameters
        ----------
        experiment_id:
            The Phoenix experiment ID.

        Returns
        -------
        dict
            A ``RanExperiment`` dict with ``task_runs`` and ``evaluation_runs``.

        Raises
        ------
        ValueError
            If the experiment is not found.
        """
        return self._client.experiments.get_experiment(experiment_id=experiment_id)

    def export(
        self,
        experiment_id: str,
        format: Literal["csv", "json"],
        path: Path | str,
    ) -> None:
        """Export experiment results to a file.

        Parameters
        ----------
        experiment_id:
            The Phoenix experiment ID.
        format:
            Output format: ``"csv"`` or ``"json"``.
        path:
            Destination file path.

        Raises
        ------
        ValueError
            If *format* is not supported.
        """
        if format not in _SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported format {format!r}. Choose from: {sorted(_SUPPORTED_FORMATS)}"
            )
        ran = self.get(experiment_id)
        rows = _rows_from_ran_experiment(ran)
        path = Path(path)

        if format == "csv":
            fieldnames = list(rows[0].keys()) if rows else ["run_id", "output", "error"]
            with open(path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        else:
            path.write_text(json.dumps(rows, indent=2, default=str))

    def compare(
        self,
        experiment_id_a: str,
        experiment_id_b: str,
    ) -> dict[str, dict[str, float]]:
        """Compare two experiments by their mean evaluator scores.

        Parameters
        ----------
        experiment_id_a:
            ID of the baseline experiment.
        experiment_id_b:
            ID of the comparison experiment.

        Returns
        -------
        dict
            Mapping of evaluator name → ``{"score_a": …, "score_b": …, "delta": …}``.
        """
        ran_a = self.get(experiment_id_a)
        ran_b = self.get(experiment_id_b)
        scores_a = _mean_scores(ran_a)
        scores_b = _mean_scores(ran_b)
        all_names = set(scores_a) | set(scores_b)
        result: dict[str, dict[str, float]] = {}
        for name in all_names:
            a = scores_a.get(name, 0.0)
            b = scores_b.get(name, 0.0)
            result[name] = {"score_a": a, "score_b": b, "delta": b - a}
        return result

    def report(self, experiment_id: str) -> str:
        """Generate a markdown summary report for an experiment.

        Parameters
        ----------
        experiment_id:
            The Phoenix experiment ID.

        Returns
        -------
        str
            A markdown-formatted summary string.
        """
        ran = self.get(experiment_id)
        scores = _mean_scores(ran)
        task_runs: list[Any] = ran["task_runs"]

        lines = [
            f"# Experiment Report: {experiment_id}",
            "",
            f"**Total runs:** {len(task_runs)}",
            "",
            "## Evaluator Scores",
            "",
        ]
        if scores:
            for name, score in sorted(scores.items()):
                lines.append(f"- **{name}**: {score:.4f}")
        else:
            lines.append("_No evaluator scores recorded._")

        return "\n".join(lines)
