"""
OpenAI fine-tuning provider (simulated).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from evaluation.vision_finetune.config import FineTuneConfig
from evaluation.vision_finetune.job_manager import FineTuneJobStatus
from evaluation.vision_finetune.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, api_key: str | None = None):
        super().__init__(api_key=api_key)
        self._jobs: dict[str, dict[str, Any]] = {}

    async def start_finetune(self, config: FineTuneConfig, train_path: Path, validation_path: Path) -> str:
        job_id = f"ft-openai-{uuid4().hex[:8]}"
        model_name = f"{config.base_model}-synthetic-ui-{uuid4().hex[:6]}"
        self._jobs[job_id] = {
            "status": FineTuneJobStatus.COMPLETED,
            "train_path": str(train_path),
            "validation_path": str(validation_path),
            "model_name": model_name,
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
        output_path.mkdir(parents=True, exist_ok=True)
        artifact_path = output_path / f"{model_name}.json"
        metadata = {"provider": "openai", "model_name": model_name}
        with open(artifact_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        return artifact_path

    def _count_lines(self, path: Path) -> int:
        count = 0
        with open(path, encoding="utf-8") as f:
            for _ in f:
                count += 1
        return count
