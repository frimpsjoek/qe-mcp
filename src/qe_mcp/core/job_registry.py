"""Persistent JSON-backed registry for tracking async QE job submissions."""

import json
from datetime import datetime, timezone
from pathlib import Path


class JobRegistry:
    """
    Maps job_id → submission metadata and status.

    Stored at $QE_WORKDIR/jobs.json. Thread-safety is not guaranteed;
    single-user CLI use is the expected scenario.
    """

    def __init__(self, workdir: Path):
        workdir.mkdir(parents=True, exist_ok=True)
        self._path = workdir / "jobs.json"
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text())
            except Exception:
                self._data = {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2, default=str))

    def register(
        self,
        job_id: str,
        task_id: str,
        runner: str,
        calc_type: str,
        work_dir: str,
        structure: str,
    ) -> None:
        self._data[job_id] = {
            "job_id": job_id,
            "task_id": task_id,
            "runner": runner,
            "calc_type": calc_type,
            "work_dir": work_dir,
            "structure": structure,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "status": "submitted",
            "result": None,
        }
        self._save()

    def get(self, job_id: str) -> dict | None:
        return self._data.get(job_id)

    def update(self, job_id: str, **fields) -> None:
        if job_id in self._data:
            self._data[job_id].update(fields)
            self._save()

    def list_jobs(self, status: str | None = None) -> list[dict]:
        jobs = list(self._data.values())
        return [j for j in jobs if j["status"] == status] if status else jobs
