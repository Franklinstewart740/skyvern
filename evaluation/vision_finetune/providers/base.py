"""
Base provider interface for fine-tuning.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from evaluation.vision_finetune.config import FineTuneConfig


class BaseProvider(ABC):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    @abstractmethod
    async def start_finetune(self, config: FineTuneConfig, train_path: Path, validation_path: Path) -> str:
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    async def get_model_name(self, job_id: str) -> str | None:
        pass

    @abstractmethod
    async def download_model(self, model_name: str, output_path: Path) -> Path:
        pass

    async def cancel_finetune(self, job_id: str) -> None:
        pass
