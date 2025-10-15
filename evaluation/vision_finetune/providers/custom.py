"""
Custom fine-tuning provider that writes model artifacts locally.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from evaluation.vision_finetune.config import FineTuneConfig
from evaluation.vision_finetune.job_manager import FineTuneJobStatus
from evaluation.vision_finetune.providers.base import BaseProvider


class CustomProvider(BaseProvider):
    def __init__(self, runtime_path: Path | None = None):
        super().__init__(api_key=None)
        self._runtime_path = runtime_path or Path("./custom_models")
        self._jobs: dict[str, dict[str, Any]] = {}

    async def start_finetune(self, config: FineTuneConfig, train_path: Path, validation_path: Path) -> str:
        job_id = f"ft-custom-{uuid4().hex[:8]}"
        model_name = f"custom-vision-{uuid4().hex[:6]}"
        artifact_path = self._runtime_path / f"{model_name}.json"
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "provider": "custom",
            "base_model": config.base_model,
            "train_dataset": str(train_path),
            "validation_dataset": str(validation_path),
            "metadata": config.metadata,
        }
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        self._jobs[job_id] = {
            "status": FineTuneJobStatus.COMPLETED,
            "model_name": model_name,
            "artifact_path": str(artifact_path),
            "metrics": {"train_samples": self._count_lines(train_path), "validation_samples": self._count_lines(validation_path)},
        }
        return job_id

    async def get_job_status(self, job_id: str) -> dict[str, Any]:
        job = self._jobs.get(job_id)
        if not job:
            return {"status": FineTuneJobStatus.FAILED.value}
        return {"status": job["status"].value, "metrics": job.get("metrics", {})}

    async def get_model_name(self, job_id: str) -> str | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        return job.get("model_name")

    async def download_model(self, model_name: str, output_path: Path) -> Path:
        source = self._runtime_path / f"{model_name}.json"
        output_path.mkdir(parents=True, exist_ok=True)
        target = output_path / f"{model_name}.json"
        target.write_bytes(source.read_bytes())
        return target

    def _count_lines(self, path: Path) -> int:
        count = 0
        with open(path, encoding="utf-8") as f:
            for _ in f:
                count += 1
        return count
