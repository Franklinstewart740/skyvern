"""
Manage fine-tuning jobs and their lifecycle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

LOG = structlog.get_logger(__name__)


class FineTuneJobStatus(str, Enum):
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class FineTuneJob:
    job_id: str
    provider: str
    status: FineTuneJobStatus
    dataset_paths: dict[str, str]
    config: dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metrics: dict[str, Any] = field(default_factory=dict)
    model_name: str | None = None
    output_artifact: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "provider": self.provider,
            "status": self.status.value,
            "dataset_paths": self.dataset_paths,
            "config": self.config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metrics": self.metrics,
            "model_name": self.model_name,
            "output_artifact": self.output_artifact,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "FineTuneJob":
        return FineTuneJob(
            job_id=data["job_id"],
            provider=data["provider"],
            status=FineTuneJobStatus(data["status"]),
            dataset_paths=data.get("dataset_paths", {}),
            config=data.get("config", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            metrics=data.get("metrics", {}),
            model_name=data.get("model_name"),
            output_artifact=data.get("output_artifact"),
        )


class FineTuneJobManager:
    def __init__(self, storage_path: str | Path | None = None):
        self.storage_path = Path(storage_path) if storage_path else None
        self.jobs: dict[str, FineTuneJob] = {}
        if self.storage_path:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self._load()

    def _load(self) -> None:
        if not self.storage_path or not self.storage_path.exists():
            return
        with open(self.storage_path, encoding="utf-8") as f:
            data = json.load(f)
            for job_data in data:
                job = FineTuneJob.from_dict(job_data)
                self.jobs[job.job_id] = job

    def _persist(self) -> None:
        if not self.storage_path:
            return
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump([job.to_dict() for job in self.jobs.values()], f, indent=2)

    def create_job(self, job: FineTuneJob) -> FineTuneJob:
        LOG.info("Creating fine-tune job", job_id=job.job_id, provider=job.provider)
        self.jobs[job.job_id] = job
        self._persist()
        return job

    def update_status(
        self,
        job_id: str,
        status: FineTuneJobStatus,
        metrics: dict[str, Any] | None = None,
        model_name: str | None = None,
        output_artifact: str | None = None,
    ) -> FineTuneJob:
        if job_id not in self.jobs:
            msg = f"Job {job_id} not found"
            raise KeyError(msg)
        job = self.jobs[job_id]
        job.status = status
        job.updated_at = datetime.utcnow().isoformat()
        if metrics:
            job.metrics.update(metrics)
        if model_name:
            job.model_name = model_name
        if output_artifact:
            job.output_artifact = output_artifact
        self._persist()
        LOG.info("Updated fine-tune job", job_id=job_id, status=status.value)
        return job

    def get_job(self, job_id: str) -> FineTuneJob | None:
        return self.jobs.get(job_id)

    def list_jobs(self) -> list[FineTuneJob]:
        return list(self.jobs.values())
